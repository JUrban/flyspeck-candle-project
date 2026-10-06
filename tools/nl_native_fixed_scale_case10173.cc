#include <array>
#include <chrono>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <initializer_list>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <gmpxx.h>

namespace {

constexpr std::size_t kDimensions = 6;
constexpr std::size_t kSqrtSlots = 7;
const mpz_class kScale("1000000000000");
const mpz_class kTwoScaleSquared = 2 * kScale * kScale;

using Rat = mpq_class;
using Integer = mpz_class;

Rat normalized_rat(const Integer& numerator, const Integer& denominator) {
  Rat result(numerator, denominator);
  result.canonicalize();
  return result;
}

struct Interval {
  Integer lower;
  Integer upper;
};

struct RationalInterval {
  Rat lower;
  Rat upper;
};

using IntervalVector = std::array<Interval, kDimensions>;
using IntervalMatrix = std::array<IntervalVector, kDimensions>;
using IntegerVector = std::array<Integer, kDimensions>;

struct FirstJet {
  Interval value;
  IntervalVector gradient;
};

struct TaylorResult {
  bool domain;
  FirstJet center;
  Interval value_bound;
  IntervalVector gradient_bounds;
  IntervalMatrix hessian;
};

struct PolynomialJet {
  FirstJet center;
  Interval box_value;
  IntervalVector box_gradient;
  IntervalMatrix box_hessian;
};

struct Counters {
  std::uint64_t interval_products = 0;
  std::uint64_t completed_results = 0;
  std::uint64_t polynomial_steps = 0;
  std::uint64_t outer_steps = 0;
  std::uint64_t sqrt_steps = 0;
  std::uint64_t inverse_steps = 0;
  std::uint64_t atan_steps = 0;
};

struct InstructionProfile {
  Counters counters;
  std::uint64_t nanoseconds = 0;
  std::size_t observations = 0;
  std::size_t stack_before = 0;
  std::size_t stack_after = 0;
  std::size_t sqrt_slot_before = 0;
  std::size_t sqrt_slot_after = 0;
};

enum class PolynomialMode {
  kBaseline,
  kFusedAll,
  kFusedDeltaX4,
  kSpecializedAngle,
};

struct Node {
  bool is_pair = false;
  Integer numeral = 0;
  std::size_t left = 0;
  std::size_t right = 0;
};

class CvalParser {
 public:
  explicit CvalParser(const std::string& input) : input_(input) {}

  std::size_t parse() {
    const std::size_t root = parse_node();
    skip_space();
    if (position_ != input_.size()) fail("trailing source-program data");
    return root;
  }

  const std::vector<Node>& nodes() const { return nodes_; }

 private:
  [[noreturn]] void fail(const std::string& message) const {
    throw std::runtime_error(message + " at byte " +
                             std::to_string(position_));
  }

  void skip_space() {
    while (position_ < input_.size() &&
           std::isspace(static_cast<unsigned char>(input_[position_]))) {
      ++position_;
    }
  }

  void expect(char expected) {
    skip_space();
    if (position_ >= input_.size() || input_[position_] != expected) {
      fail(std::string("expected '") + expected + "'");
    }
    ++position_;
  }

  std::size_t parse_node() {
    skip_space();
    if (position_ >= input_.size()) fail("unexpected end of cval");
    if (input_[position_] == 'n') {
      ++position_;
      const std::size_t begin = position_;
      while (position_ < input_.size() &&
             std::isdigit(static_cast<unsigned char>(input_[position_]))) {
        ++position_;
      }
      if (begin == position_) fail("empty cval numeral");
      Node node;
      node.numeral = Integer(input_.substr(begin, position_ - begin));
      nodes_.push_back(node);
      return nodes_.size() - 1;
    }
    if (input_[position_] == 'p') {
      ++position_;
      expect('(');
      const std::size_t left = parse_node();
      expect(',');
      const std::size_t right = parse_node();
      expect(')');
      Node node;
      node.is_pair = true;
      node.left = left;
      node.right = right;
      nodes_.push_back(node);
      return nodes_.size() - 1;
    }
    fail("expected cval numeral or pair");
  }

  const std::string& input_;
  std::size_t position_ = 0;
  std::vector<Node> nodes_;
};

struct Program {
  std::vector<Node> nodes;
  std::vector<std::size_t> instructions;
};

struct Job {
  int index = 0;
  std::array<RationalInterval, kSqrtSlots> box_certificates;
  std::array<RationalInterval, kSqrtSlots> center_certificates;
  std::array<Rat, kDimensions> lower;
  std::array<Rat, kDimensions> upper;
};

std::vector<std::string> split(const std::string& text, char separator) {
  std::vector<std::string> fields;
  std::string field;
  std::istringstream input(text);
  while (std::getline(input, field, separator)) fields.push_back(field);
  return fields;
}

Rat parse_rational(const std::string& text) {
  Rat value(text);
  value.canonicalize();
  return value;
}

template <std::size_t Size>
std::array<Rat, Size> parse_rational_vector(const std::string& text) {
  const std::vector<std::string> values = split(text, ',');
  if (values.size() != Size) throw std::runtime_error("rational vector size drift");
  std::array<Rat, Size> result;
  for (std::size_t index = 0; index < Size; ++index) {
    result[index] = parse_rational(values[index]);
  }
  return result;
}

template <std::size_t Size>
std::array<RationalInterval, Size> parse_interval_vector(
    const std::string& text) {
  const std::vector<std::string> values = split(text, ',');
  if (values.size() != Size) throw std::runtime_error("interval vector size drift");
  std::array<RationalInterval, Size> result;
  for (std::size_t index = 0; index < Size; ++index) {
    const std::vector<std::string> endpoints = split(values[index], ':');
    if (endpoints.size() != 2) throw std::runtime_error("malformed interval");
    result[index] = {parse_rational(endpoints[0]),
                     parse_rational(endpoints[1])};
    if (result[index].lower > result[index].upper) {
      throw std::runtime_error("reversed interval");
    }
  }
  return result;
}

std::string read_single_line(const char* path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error(std::string("cannot open program: ") + path);
  std::string line;
  if (!std::getline(input, line) || line.empty()) {
    throw std::runtime_error("empty source program");
  }
  std::string extra;
  if (std::getline(input, extra) && !extra.empty()) {
    throw std::runtime_error("source program is not one line");
  }
  return line;
}

Program read_program(const char* path) {
  const std::string serialized = read_single_line(path);
  CvalParser parser(serialized);
  const std::size_t root = parser.parse();
  Program program;
  program.nodes = parser.nodes();
  std::size_t current = root;
  while (program.nodes[current].is_pair) {
    program.instructions.push_back(program.nodes[current].left);
    current = program.nodes[current].right;
  }
  if (program.nodes[current].numeral != 0 || program.instructions.size() != 54) {
    throw std::runtime_error("source program spine drift");
  }
  return program;
}

std::vector<Job> read_jobs(const char* path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error(std::string("cannot open jobs: ") + path);
  std::vector<Job> jobs;
  std::string line;
  while (std::getline(input, line)) {
    const std::vector<std::string> fields = split(line, '\t');
    if (fields.size() != 5) throw std::runtime_error("malformed job row");
    Job job;
    job.index = std::stoi(fields[0]);
    if (job.index != static_cast<int>(jobs.size())) {
      throw std::runtime_error("job index drift");
    }
    job.box_certificates = parse_interval_vector<kSqrtSlots>(fields[1]);
    job.center_certificates = parse_interval_vector<kSqrtSlots>(fields[2]);
    job.lower = parse_rational_vector<kDimensions>(fields[3]);
    job.upper = parse_rational_vector<kDimensions>(fields[4]);
    for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
      if (job.lower[coordinate] > job.upper[coordinate]) {
        throw std::runtime_error("empty job box");
      }
    }
    jobs.push_back(job);
  }
  if (jobs.size() != 128) throw std::runtime_error("expected 128 native jobs");
  return jobs;
}

Integer floor_quotient(const Integer& numerator, const Integer& denominator) {
  Integer result;
  mpz_fdiv_q(result.get_mpz_t(), numerator.get_mpz_t(), denominator.get_mpz_t());
  return result;
}

Integer ceil_quotient(const Integer& numerator, const Integer& denominator) {
  Integer result;
  mpz_cdiv_q(result.get_mpz_t(), numerator.get_mpz_t(), denominator.get_mpz_t());
  return result;
}

Integer floor_scaled(const Rat& value) {
  return floor_quotient(value.get_num() * kScale, value.get_den());
}

Integer ceil_scaled(const Rat& value) {
  return ceil_quotient(value.get_num() * kScale, value.get_den());
}

Integer absolute(const Integer& value) { return value < 0 ? -value : value; }

Interval zero_interval() { return {0, 0}; }

Interval one_interval() { return {kScale, kScale}; }

Interval interval_of_q(const RationalInterval& value) {
  return {floor_scaled(value.lower), ceil_scaled(value.upper)};
}

Interval interval_constant(const Rat& value) {
  return {floor_scaled(value), ceil_scaled(value)};
}

Interval interval_neg(const Interval& value) {
  return {-value.upper, -value.lower};
}

Interval interval_add(const Interval& left, const Interval& right) {
  return {left.lower + right.lower, left.upper + right.upper};
}

Interval interval_integer_scale(long coefficient, const Interval& value) {
  if (coefficient >= 0) {
    return {coefficient * value.lower, coefficient * value.upper};
  }
  return {coefficient * value.upper, coefficient * value.lower};
}

Interval interval_sum(std::initializer_list<Interval> values) {
  Interval result = zero_interval();
  for (const Interval& value : values) result = interval_add(result, value);
  return result;
}

Interval raw_interval_mul(const Interval& left, const Interval& right,
                          Counters& counters) {
  ++counters.interval_products;
  const Integer ll = left.lower * right.lower;
  const Integer lu = left.lower * right.upper;
  const Integer ul = left.upper * right.lower;
  const Integer uu = left.upper * right.upper;
  Integer lower = ll;
  if (lu < lower) lower = lu;
  if (ul < lower) lower = ul;
  if (uu < lower) lower = uu;
  Integer upper = ll;
  if (lu > upper) upper = lu;
  if (ul > upper) upper = ul;
  if (uu > upper) upper = uu;
  return {lower, upper};
}

Interval raw_interval_round(const Integer& denominator,
                            const Interval& value) {
  return {floor_quotient(value.lower, denominator),
          ceil_quotient(value.upper, denominator)};
}

Interval interval_mul(const Interval& left, const Interval& right,
                      Counters& counters) {
  return raw_interval_round(kScale, raw_interval_mul(left, right, counters));
}

Integer interval_abs_upper(const Interval& value) {
  const Integer lower = absolute(value.lower);
  const Integer upper = absolute(value.upper);
  return lower > upper ? lower : upper;
}

IntervalVector zero_vector() {
  IntervalVector result;
  for (Interval& item : result) item = zero_interval();
  return result;
}

IntervalMatrix zero_matrix() {
  IntervalMatrix result;
  for (IntervalVector& row : result) row = zero_vector();
  return result;
}

IntervalVector unit_vector(std::size_t variable) {
  IntervalVector result = zero_vector();
  if (variable < kDimensions) result[variable] = one_interval();
  return result;
}

IntervalVector vector_neg(const IntervalVector& value) {
  IntervalVector result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = interval_neg(value[i]);
  }
  return result;
}

IntervalVector vector_add(const IntervalVector& left,
                          const IntervalVector& right) {
  IntervalVector result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = interval_add(left[i], right[i]);
  }
  return result;
}

IntervalMatrix matrix_neg(const IntervalMatrix& value) {
  IntervalMatrix result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = vector_neg(value[i]);
  }
  return result;
}

IntervalMatrix matrix_add(const IntervalMatrix& left,
                          const IntervalMatrix& right) {
  IntervalMatrix result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = vector_add(left[i], right[i]);
  }
  return result;
}

IntervalVector raw_vector_scale(const Interval& scalar,
                                const IntervalVector& value,
                                Counters& counters) {
  IntervalVector result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = raw_interval_mul(scalar, value[i], counters);
  }
  return result;
}

IntervalMatrix raw_matrix_scale(const Interval& scalar,
                                const IntervalMatrix& value,
                                Counters& counters) {
  IntervalMatrix result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = raw_vector_scale(scalar, value[i], counters);
  }
  return result;
}

IntervalMatrix raw_outer(const IntervalVector& left,
                         const IntervalVector& right,
                         Counters& counters) {
  IntervalMatrix result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = raw_vector_scale(left[i], right, counters);
  }
  return result;
}

IntervalVector raw_vector_round(const IntervalVector& value,
                                const Integer& denominator) {
  IntervalVector result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = raw_interval_round(denominator, value[i]);
  }
  return result;
}

IntervalMatrix raw_matrix_round(const IntervalMatrix& value,
                                const Integer& denominator) {
  IntervalMatrix result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = raw_vector_round(value[i], denominator);
  }
  return result;
}

IntervalVector interval_vector_scale(const Interval& scalar,
                                     const IntervalVector& value,
                                     Counters& counters) {
  return raw_vector_round(raw_vector_scale(scalar, value, counters), kScale);
}

IntervalMatrix interval_matrix_scale(const Interval& scalar,
                                     const IntervalMatrix& value,
                                     Counters& counters) {
  return raw_matrix_round(raw_matrix_scale(scalar, value, counters), kScale);
}

IntervalMatrix interval_outer(const IntervalVector& left,
                              const IntervalVector& right,
                              Counters& counters) {
  return raw_matrix_round(raw_outer(left, right, counters), kScale);
}

PolynomialJet polynomial_constant(const Rat& value) {
  const Interval fixed = interval_constant(value);
  return {{fixed, zero_vector()}, fixed, zero_vector(), zero_matrix()};
}

PolynomialJet polynomial_variable(const IntervalVector& center_environment,
                                  const IntervalVector& box_environment,
                                  std::size_t variable) {
  const Interval center = variable < kDimensions
                              ? center_environment[variable]
                              : zero_interval();
  const Interval box = variable < kDimensions
                           ? box_environment[variable]
                           : zero_interval();
  const IntervalVector gradient = unit_vector(variable);
  return {{center, gradient}, box, gradient, zero_matrix()};
}

PolynomialJet polynomial_neg(const PolynomialJet& value) {
  return {{interval_neg(value.center.value),
           vector_neg(value.center.gradient)},
          interval_neg(value.box_value),
          vector_neg(value.box_gradient),
          matrix_neg(value.box_hessian)};
}

PolynomialJet polynomial_add(const PolynomialJet& left,
                             const PolynomialJet& right) {
  return {{interval_add(left.center.value, right.center.value),
           vector_add(left.center.gradient, right.center.gradient)},
          interval_add(left.box_value, right.box_value),
          vector_add(left.box_gradient, right.box_gradient),
          matrix_add(left.box_hessian, right.box_hessian)};
}

PolynomialJet polynomial_mul(const PolynomialJet& left,
                             const PolynomialJet& right,
                             Counters& counters) {
  const FirstJet raw_center = {
      raw_interval_mul(left.center.value, right.center.value, counters),
      vector_add(raw_vector_scale(right.center.value, left.center.gradient,
                                  counters),
                 raw_vector_scale(left.center.value, right.center.gradient,
                                  counters))};
  const Interval raw_box_value =
      raw_interval_mul(left.box_value, right.box_value, counters);
  const IntervalVector raw_box_gradient = vector_add(
      raw_vector_scale(right.box_value, left.box_gradient, counters),
      raw_vector_scale(left.box_value, right.box_gradient, counters));
  const IntervalMatrix raw_box_hessian = matrix_add(
      matrix_add(raw_matrix_scale(right.box_value, left.box_hessian, counters),
                 raw_outer(left.box_gradient, right.box_gradient, counters)),
      matrix_add(raw_outer(right.box_gradient, left.box_gradient, counters),
                 raw_matrix_scale(left.box_value, right.box_hessian, counters)));
  return {{raw_interval_round(kScale, raw_center.value),
           raw_vector_round(raw_center.gradient, kScale)},
          raw_interval_round(kScale, raw_box_value),
          raw_vector_round(raw_box_gradient, kScale),
          raw_matrix_round(raw_box_hessian, kScale)};
}

Integer dot_abs_upper(const IntegerVector& radii,
                      const IntervalVector& row) {
  Integer result = 0;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result += radii[i] * interval_abs_upper(row[i]);
  }
  return result;
}

Integer weighted_rows_abs_upper(const IntegerVector& radii,
                                const IntervalMatrix& matrix) {
  Integer result = 0;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result += radii[i] * dot_abs_upper(radii, matrix[i]);
  }
  return result;
}

TaylorResult complete_result(const IntegerVector& radii, bool domain,
                             const FirstJet& center,
                             const IntervalMatrix& hessian,
                             Counters& counters) {
  ++counters.completed_results;
  const Integer linear = dot_abs_upper(radii, center.gradient);
  const Integer quadratic = weighted_rows_abs_upper(radii, hessian);
  const Integer error = 2 * kScale * linear + quadratic;
  const Interval raw_value = {
      kTwoScaleSquared * center.value.lower - error,
      kTwoScaleSquared * center.value.upper + error};

  IntervalVector gradient_bounds;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    const Integer variation = dot_abs_upper(radii, hessian[i]);
    gradient_bounds[i] = raw_interval_round(
        kScale, {kScale * center.gradient[i].lower - variation,
                 kScale * center.gradient[i].upper + variation});
  }

  return {domain,
          center,
          raw_interval_round(kTwoScaleSquared, raw_value),
          gradient_bounds,
          hessian};
}

TaylorResult complete_raw_result(const IntegerVector& radii, bool domain,
                                 const FirstJet& raw_center,
                                 const IntervalMatrix& raw_hessian,
                                 Counters& counters) {
  FirstJet center;
  center.value = raw_interval_round(kScale, raw_center.value);
  center.gradient = raw_vector_round(raw_center.gradient, kScale);
  return complete_result(radii, domain, center,
                         raw_matrix_round(raw_hessian, kScale), counters);
}

TaylorResult result_constant(const IntegerVector& radii, const Rat& value,
                             Counters& counters) {
  return complete_result(radii, true,
                         {interval_constant(value), zero_vector()},
                         zero_matrix(), counters);
}

TaylorResult result_variable(const IntegerVector& radii,
                             const IntervalVector& center_environment,
                             std::size_t variable, Counters& counters) {
  const Interval value = variable < kDimensions
                             ? center_environment[variable]
                             : zero_interval();
  return complete_result(radii, true, {value, unit_vector(variable)},
                         zero_matrix(), counters);
}

TaylorResult result_neg(const IntegerVector& radii,
                        const TaylorResult& value, Counters& counters) {
  return complete_result(
      radii, value.domain,
      {interval_neg(value.center.value), vector_neg(value.center.gradient)},
      matrix_neg(value.hessian), counters);
}

TaylorResult result_add(const IntegerVector& radii,
                        const TaylorResult& left,
                        const TaylorResult& right, Counters& counters) {
  return complete_result(
      radii, left.domain && right.domain,
      {interval_add(left.center.value, right.center.value),
       vector_add(left.center.gradient, right.center.gradient)},
      matrix_add(left.hessian, right.hessian), counters);
}

TaylorResult result_mul(const IntegerVector& radii,
                        const TaylorResult& left,
                        const TaylorResult& right, Counters& counters) {
  const FirstJet raw_center = {
      raw_interval_mul(left.center.value, right.center.value, counters),
      vector_add(raw_vector_scale(right.center.value, left.center.gradient,
                                  counters),
                 raw_vector_scale(left.center.value, right.center.gradient,
                                  counters))};
  const IntervalMatrix raw_hessian = matrix_add(
      matrix_add(raw_matrix_scale(right.value_bound, left.hessian, counters),
                 raw_outer(left.gradient_bounds, right.gradient_bounds,
                           counters)),
      matrix_add(raw_outer(right.gradient_bounds, left.gradient_bounds,
                           counters),
                 raw_matrix_scale(left.value_bound, right.hessian, counters)));
  return complete_raw_result(radii, left.domain && right.domain, raw_center,
                             raw_hessian, counters);
}

RationalInterval fixed_to_q(const Interval& value) {
  return {normalized_rat(value.lower, kScale),
          normalized_rat(value.upper, kScale)};
}

RationalInterval rational_interval_neg(const RationalInterval& value) {
  return {-value.upper, -value.lower};
}

RationalInterval rational_interval_add(const RationalInterval& left,
                                       const RationalInterval& right) {
  return {left.lower + right.lower, left.upper + right.upper};
}

RationalInterval rational_interval_mul(const RationalInterval& left,
                                       const RationalInterval& right) {
  const Rat ll = left.lower * right.lower;
  const Rat lu = left.lower * right.upper;
  const Rat ul = left.upper * right.lower;
  const Rat uu = left.upper * right.upper;
  Rat lower = ll;
  if (lu < lower) lower = lu;
  if (ul < lower) lower = ul;
  if (uu < lower) lower = uu;
  Rat upper = ll;
  if (lu > upper) upper = lu;
  if (ul > upper) upper = ul;
  if (uu > upper) upper = uu;
  return {lower, upper};
}

RationalInterval rational_interval_square(const RationalInterval& value) {
  if (value.lower >= 0) {
    return {value.lower * value.lower, value.upper * value.upper};
  }
  if (value.upper <= 0) {
    return {value.upper * value.upper, value.lower * value.lower};
  }
  const Rat lower_square = value.lower * value.lower;
  const Rat upper_square = value.upper * value.upper;
  return {0, lower_square > upper_square ? lower_square : upper_square};
}

bool rational_interval_not_zero(const RationalInterval& value) {
  return value.lower > 0 || value.upper < 0;
}

RationalInterval rational_interval_inv(const RationalInterval& value) {
  if (!rational_interval_not_zero(value)) {
    throw std::runtime_error("inverse interval contains zero");
  }
  return {Rat(1) / value.upper, Rat(1) / value.lower};
}

bool sqrt_certificate(const RationalInterval& input,
                      const RationalInterval& output) {
  return input.lower >= 0 && input.lower <= input.upper &&
         output.lower >= 0 && output.lower <= output.upper &&
         output.lower * output.lower <= input.lower &&
         input.upper <= output.upper * output.upper;
}

Rat atan_pos_lower(const Rat& x) {
  const Rat x2 = x * x;
  return x * (Rat(1) + x2 *
      (-Rat(1, 3) + x2 *
       (Rat(1, 5) + x2 *
        (-Rat(1, 7) + x2 *
         (Rat(1, 9) + x2 * (-Rat(1, 11)))))));
}

Rat atan_pos_upper(const Rat& x) {
  const Rat x2 = x * x;
  return x * (Rat(1) + x2 *
      (-Rat(1, 3) + x2 *
       (Rat(1, 5) + x2 *
        (-Rat(1, 7) + x2 *
         (Rat(1, 9) + x2 *
          (-Rat(1, 11) + x2 * Rat(1, 13)))))));
}

Rat atan_lower(const Rat& x) {
  return x >= 0 ? atan_pos_lower(x) : -atan_pos_upper(-x);
}

Rat atan_upper(const Rat& x) {
  return x >= 0 ? atan_pos_upper(x) : -atan_pos_lower(-x);
}

const Rat kPiHalfLower =
    normalized_rat(Integer(1686629713), Integer(1073741824));
const Rat kPiHalfUpper =
    normalized_rat(Integer(6746518853), Integer(4294967296));

bool atan_range_domain(const Rat& x) { return x != -1 && x != 1; }

Rat atan_range_lower(const Rat& x) {
  if (x <= -1) return atan_lower(-Rat(1) / x) - kPiHalfUpper;
  if (x >= 1) return kPiHalfLower - atan_upper(Rat(1) / x);
  return atan_lower(x);
}

Rat atan_range_upper(const Rat& x) {
  if (x <= -1) return atan_upper(-Rat(1) / x) - kPiHalfLower;
  if (x >= 1) return kPiHalfUpper - atan_lower(Rat(1) / x);
  return atan_upper(x);
}

bool atan_interval_domain(const RationalInterval& input) {
  return input.lower <= input.upper && atan_range_domain(input.lower) &&
         atan_range_domain(input.upper);
}

RationalInterval atan_interval(const RationalInterval& input) {
  return {atan_range_lower(input.lower), atan_range_upper(input.upper)};
}

TaylorResult result_inverse(const IntegerVector& radii,
                            const TaylorResult& value, Counters& counters) {
  ++counters.inverse_steps;
  const RationalInterval center_input = fixed_to_q(value.center.value);
  const RationalInterval box_input = fixed_to_q(value.value_bound);
  const bool domain = value.domain && rational_interval_not_zero(center_input) &&
                      rational_interval_not_zero(box_input);
  if (!domain) throw std::runtime_error("inverse domain failure");
  const Interval r = interval_of_q(rational_interval_inv(center_input));
  const Interval r2 = interval_mul(r, r, counters);
  FirstJet center = {r, interval_vector_scale(interval_neg(r2),
                                               value.center.gradient, counters)};

  const Interval box_r = interval_of_q(rational_interval_inv(box_input));
  const Interval box_r2 = interval_mul(box_r, box_r, counters);
  const Interval box_r3 = interval_mul(box_r2, box_r, counters);
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(interval_neg(box_r2), value.hessian, counters),
      interval_matrix_scale(interval_add(box_r3, box_r3),
                            interval_outer(value.gradient_bounds,
                                           value.gradient_bounds, counters),
                            counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_sqrt(const IntegerVector& radii,
                         const RationalInterval& center_certificate,
                         const RationalInterval& box_certificate,
                         const TaylorResult& value, Counters& counters) {
  ++counters.sqrt_steps;
  const RationalInterval center_input = fixed_to_q(value.center.value);
  const RationalInterval box_input = fixed_to_q(value.value_bound);
  const RationalInterval center_twice = rational_interval_add(
      center_certificate, center_certificate);
  const RationalInterval box_twice = rational_interval_add(
      box_certificate, box_certificate);
  const RationalInterval input_twice = rational_interval_add(box_input, box_input);
  const bool domain = value.domain &&
      sqrt_certificate(center_input, center_certificate) &&
      sqrt_certificate(box_input, box_certificate) &&
      rational_interval_not_zero(center_twice) &&
      rational_interval_not_zero(box_twice) &&
      rational_interval_not_zero(rational_interval_mul(box_twice, input_twice));
  if (!domain) throw std::runtime_error("sqrt domain failure");

  const Interval center_d = interval_of_q(rational_interval_inv(center_twice));
  const FirstJet center = {
      interval_of_q(center_certificate),
      interval_vector_scale(center_d, value.center.gradient, counters)};

  const Interval box_d = interval_of_q(rational_interval_inv(box_twice));
  const Interval box_dd = interval_of_q(rational_interval_neg(
      rational_interval_inv(rational_interval_mul(box_twice, input_twice))));
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(
          box_dd,
          interval_outer(value.gradient_bounds, value.gradient_bounds,
                         counters),
          counters),
      interval_matrix_scale(box_d, value.hessian, counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_atan(const IntegerVector& radii,
                         const TaylorResult& value, Counters& counters) {
  ++counters.atan_steps;
  const RationalInterval center_input = fixed_to_q(value.center.value);
  const RationalInterval box_input = fixed_to_q(value.value_bound);
  const RationalInterval one = {1, 1};
  const RationalInterval center_denominator = rational_interval_add(
      one, rational_interval_square(center_input));
  const RationalInterval box_denominator = rational_interval_add(
      one, rational_interval_square(box_input));
  const bool domain = value.domain && atan_interval_domain(center_input) &&
                      atan_interval_domain(box_input) &&
                      rational_interval_not_zero(center_denominator) &&
                      rational_interval_not_zero(box_denominator);
  if (!domain) throw std::runtime_error("atan domain failure");

  const RationalInterval center_d_q = rational_interval_inv(center_denominator);
  const Interval center_d = interval_of_q(center_d_q);
  const FirstJet center = {
      interval_of_q(atan_interval(center_input)),
      interval_vector_scale(center_d, value.center.gradient, counters)};

  const RationalInterval box_d_q = rational_interval_inv(box_denominator);
  const RationalInterval box_dd_q = rational_interval_neg(
      rational_interval_mul(
          rational_interval_add(box_input, box_input),
          rational_interval_mul(box_d_q, box_d_q)));
  const Interval box_d = interval_of_q(box_d_q);
  const Interval box_dd = interval_of_q(box_dd_q);
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(
          box_dd,
          interval_outer(value.gradient_bounds, value.gradient_bounds,
                         counters),
          counters),
      interval_matrix_scale(box_d, value.hessian, counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_pi_half(const IntegerVector& radii, Counters& counters) {
  return complete_result(radii, true,
                         {interval_of_q({kPiHalfLower, kPiHalfUpper}),
                          zero_vector()},
                         zero_matrix(), counters);
}

const Node& node_at(const Program& program, std::size_t index) {
  if (index >= program.nodes.size()) throw std::runtime_error("cval node index drift");
  return program.nodes[index];
}

const Node& require_pair(const Program& program, std::size_t index,
                         const char* context) {
  const Node& node = node_at(program, index);
  if (!node.is_pair) throw std::runtime_error(std::string(context) + ": expected pair");
  return node;
}

Integer require_numeral(const Program& program, std::size_t index,
                        const char* context) {
  const Node& node = node_at(program, index);
  if (node.is_pair) throw std::runtime_error(std::string(context) + ": expected numeral");
  return node.numeral;
}

Rat decode_q(const Program& program, std::size_t index) {
  const Node& rational = require_pair(program, index, "rational");
  const Node& signed_value = require_pair(program, rational.left, "signed rational");
  const Integer positive = require_numeral(program, signed_value.left, "positive");
  const Integer negative = require_numeral(program, signed_value.right, "negative");
  const Integer denominator_predecessor =
      require_numeral(program, rational.right, "denominator");
  return normalized_rat(positive - negative, denominator_predecessor + 1);
}

std::vector<std::size_t> decode_list(const Program& program,
                                     std::size_t root,
                                     const char* context) {
  std::vector<std::size_t> result;
  std::size_t current = root;
  while (node_at(program, current).is_pair) {
    const Node& pair = node_at(program, current);
    result.push_back(pair.left);
    current = pair.right;
  }
  if (node_at(program, current).numeral != 0) {
    throw std::runtime_error(std::string(context) + ": nonzero list tail");
  }
  return result;
}

TaylorResult evaluate_polynomial(const Program& program,
                                 std::size_t payload,
                                 const IntegerVector& radii,
                                 const IntervalVector& center_environment,
                                 Counters& counters) {
  std::vector<TaylorResult> stack;
  const std::vector<std::size_t> instructions =
      decode_list(program, payload, "polynomial program");
  for (const std::size_t instruction_index : instructions) {
    ++counters.polynomial_steps;
    const Node& instruction = node_at(program, instruction_index);
    if (instruction.is_pair) {
      const Integer tag = require_numeral(program, instruction.left, "polynomial tag");
      if (tag == 0) {
        stack.push_back(result_constant(radii, decode_q(program, instruction.right),
                                        counters));
      } else if (tag == 1) {
        const Integer variable =
            require_numeral(program, instruction.right, "polynomial variable");
        stack.push_back(result_variable(radii, center_environment,
                                        variable.get_ui(), counters));
      } else {
        throw std::runtime_error("unknown polynomial pair instruction");
      }
      continue;
    }

    const unsigned long opcode = instruction.numeral.get_ui();
    if (opcode == 2 || opcode == 5) {
      if (stack.empty()) throw std::runtime_error("polynomial stack underflow");
      TaylorResult value = stack.back();
      stack.pop_back();
      stack.push_back(opcode == 2 ? result_neg(radii, value, counters)
                                  : result_mul(radii, value, value, counters));
    } else if (opcode == 3 || opcode == 4) {
      if (stack.size() < 2) throw std::runtime_error("polynomial stack underflow");
      TaylorResult right = stack.back();
      stack.pop_back();
      TaylorResult left = stack.back();
      stack.pop_back();
      stack.push_back(opcode == 3 ? result_add(radii, left, right, counters)
                                  : result_mul(radii, left, right, counters));
    } else {
      throw std::runtime_error("unknown polynomial scalar instruction");
    }
  }
  if (stack.size() != 1) throw std::runtime_error("polynomial result stack drift");
  return stack.back();
}

TaylorResult evaluate_polynomial_fused(
    const Program& program, std::size_t payload,
    const IntegerVector& radii,
    const IntervalVector& center_environment,
    const IntervalVector& box_environment, Counters& counters) {
  std::vector<PolynomialJet> stack;
  const std::vector<std::size_t> instructions =
      decode_list(program, payload, "fused polynomial program");
  for (const std::size_t instruction_index : instructions) {
    ++counters.polynomial_steps;
    const Node& instruction = node_at(program, instruction_index);
    if (instruction.is_pair) {
      const Integer tag = require_numeral(
          program, instruction.left, "fused polynomial tag");
      if (tag == 0) {
        stack.push_back(polynomial_constant(
            decode_q(program, instruction.right)));
      } else if (tag == 1) {
        const Integer variable = require_numeral(
            program, instruction.right, "fused polynomial variable");
        stack.push_back(polynomial_variable(
            center_environment, box_environment, variable.get_ui()));
      } else {
        throw std::runtime_error("unknown fused polynomial pair instruction");
      }
      continue;
    }

    const unsigned long opcode = instruction.numeral.get_ui();
    if (opcode == 2 || opcode == 5) {
      if (stack.empty()) {
        throw std::runtime_error("fused polynomial stack underflow");
      }
      PolynomialJet value = stack.back();
      stack.pop_back();
      stack.push_back(opcode == 2
                          ? polynomial_neg(value)
                          : polynomial_mul(value, value, counters));
    } else if (opcode == 3 || opcode == 4) {
      if (stack.size() < 2) {
        throw std::runtime_error("fused polynomial stack underflow");
      }
      PolynomialJet right = stack.back();
      stack.pop_back();
      PolynomialJet left = stack.back();
      stack.pop_back();
      stack.push_back(opcode == 3
                          ? polynomial_add(left, right)
                          : polynomial_mul(left, right, counters));
    } else {
      throw std::runtime_error("unknown fused polynomial scalar instruction");
    }
  }
  if (stack.size() != 1) {
    throw std::runtime_error("fused polynomial result stack drift");
  }
  return complete_result(radii, true, stack.back().center,
                         stack.back().box_hessian, counters);
}

IntervalMatrix polynomial_pair_products(const IntervalVector& values,
                                        Counters& counters) {
  IntervalMatrix products = zero_matrix();
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      products[row][column] = interval_mul(
          values[row], values[column], counters);
      products[column][row] = products[row][column];
    }
  }
  return products;
}

IntervalVector delta_gradient_from_products(const IntervalMatrix& p) {
  IntervalVector gradient;
  gradient[0] = interval_sum({
      interval_integer_scale(-2, p[0][3]), p[1][3], p[1][4],
      interval_neg(p[1][5]), p[2][3], interval_neg(p[2][4]), p[2][5],
      interval_neg(p[3][3]), p[3][4], p[3][5]});
  gradient[1] = interval_sum({
      p[0][3], p[0][4], interval_neg(p[0][5]),
      interval_integer_scale(-2, p[1][4]), interval_neg(p[2][3]),
      p[2][4], p[2][5], p[3][4], interval_neg(p[4][4]), p[4][5]});
  gradient[2] = interval_sum({
      p[0][3], interval_neg(p[0][4]), p[0][5],
      interval_neg(p[1][3]), p[1][4], p[1][5],
      interval_integer_scale(-2, p[2][5]), p[3][5], p[4][5],
      interval_neg(p[5][5])});
  gradient[3] = interval_sum({
      interval_neg(p[0][0]), p[0][1], p[0][2],
      interval_integer_scale(-2, p[0][3]), p[0][4], p[0][5],
      interval_neg(p[1][2]), p[1][4], p[2][5], interval_neg(p[4][5])});
  gradient[4] = interval_sum({
      p[0][1], interval_neg(p[0][2]), p[0][3],
      interval_neg(p[1][1]), p[1][2], p[1][3],
      interval_integer_scale(-2, p[1][4]), p[1][5], p[2][5],
      interval_neg(p[3][5])});
  gradient[5] = interval_sum({
      interval_neg(p[0][1]), p[0][2], p[0][3], p[1][2], p[1][4],
      interval_neg(p[2][2]), p[2][3], p[2][4],
      interval_integer_scale(-2, p[2][5]), interval_neg(p[3][4])});
  return gradient;
}

Interval delta_value(const IntervalVector& x, Counters& counters) {
  const Interval first_linear = interval_sum({
      interval_neg(x[0]), x[1], x[2], interval_neg(x[3]), x[4], x[5]});
  const Interval second_linear = interval_sum({
      x[0], interval_neg(x[1]), x[2], x[3], interval_neg(x[4]), x[5]});
  const Interval third_linear = interval_sum({
      x[0], x[1], interval_neg(x[2]), x[3], x[4], interval_neg(x[5])});
  const Interval first = interval_mul(
      interval_mul(x[0], x[3], counters), first_linear, counters);
  const Interval second = interval_mul(
      interval_mul(x[1], x[4], counters), second_linear, counters);
  const Interval third = interval_mul(
      interval_mul(x[2], x[5], counters), third_linear, counters);
  const Interval fourth = interval_mul(
      interval_mul(x[1], x[2], counters), x[3], counters);
  const Interval fifth = interval_mul(
      interval_mul(x[0], x[2], counters), x[4], counters);
  const Interval sixth = interval_mul(
      interval_mul(x[0], x[1], counters), x[5], counters);
  const Interval seventh = interval_mul(
      interval_mul(x[3], x[4], counters), x[5], counters);
  return interval_sum({first, second, third, interval_neg(fourth),
                       interval_neg(fifth), interval_neg(sixth),
                       interval_neg(seventh)});
}

IntervalMatrix delta_hessian(const IntervalVector& x) {
  IntervalMatrix hessian = zero_matrix();
  const auto set_symmetric = [&hessian](std::size_t row,
                                        std::size_t column,
                                        const Interval& value) {
    hessian[row][column] = value;
    hessian[column][row] = value;
  };
  set_symmetric(0, 0, interval_integer_scale(-2, x[3]));
  set_symmetric(0, 1, interval_sum({x[3], x[4], interval_neg(x[5])}));
  set_symmetric(0, 2, interval_sum({x[3], interval_neg(x[4]), x[5]}));
  set_symmetric(0, 3, interval_sum({
      interval_integer_scale(-2, x[0]), x[1], x[2],
      interval_integer_scale(-2, x[3]), x[4], x[5]}));
  set_symmetric(0, 4, interval_sum({x[1], interval_neg(x[2]), x[3]}));
  set_symmetric(0, 5, interval_sum({interval_neg(x[1]), x[2], x[3]}));
  set_symmetric(1, 1, interval_integer_scale(-2, x[4]));
  set_symmetric(1, 2, interval_sum({interval_neg(x[3]), x[4], x[5]}));
  set_symmetric(1, 3, interval_sum({x[0], interval_neg(x[2]), x[4]}));
  set_symmetric(1, 4, interval_sum({
      x[0], interval_integer_scale(-2, x[1]), x[2], x[3],
      interval_integer_scale(-2, x[4]), x[5]}));
  set_symmetric(1, 5, interval_sum({interval_neg(x[0]), x[2], x[4]}));
  set_symmetric(2, 2, interval_integer_scale(-2, x[5]));
  set_symmetric(2, 3, interval_sum({x[0], interval_neg(x[1]), x[5]}));
  set_symmetric(2, 4, interval_sum({interval_neg(x[0]), x[1], x[5]}));
  set_symmetric(2, 5, interval_sum({
      x[0], x[1], interval_integer_scale(-2, x[2]), x[3], x[4],
      interval_integer_scale(-2, x[5])}));
  set_symmetric(3, 3, interval_integer_scale(-2, x[0]));
  set_symmetric(3, 4, interval_sum({x[0], x[1], interval_neg(x[5])}));
  set_symmetric(3, 5, interval_sum({x[0], x[2], interval_neg(x[4])}));
  set_symmetric(4, 4, interval_integer_scale(-2, x[1]));
  set_symmetric(4, 5, interval_sum({x[1], x[2], interval_neg(x[3])}));
  set_symmetric(5, 5, interval_integer_scale(-2, x[2]));
  return hessian;
}

TaylorResult evaluate_four_x1_delta_specialized(
    const IntegerVector& radii,
    const IntervalVector& center_environment,
    const IntervalVector& box_environment, Counters& counters) {
  const Interval center_delta = delta_value(center_environment, counters);
  const IntervalVector center_delta_gradient = delta_gradient_from_products(
      polynomial_pair_products(center_environment, counters));
  const IntervalMatrix box_delta_hessian = delta_hessian(box_environment);
  IntervalVector box_delta_gradient;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    const Integer variation = dot_abs_upper(
        radii, box_delta_hessian[coordinate]);
    box_delta_gradient[coordinate] = raw_interval_round(
        kScale,
        {kScale * center_delta_gradient[coordinate].lower - variation,
         kScale * center_delta_gradient[coordinate].upper + variation});
  }

  FirstJet center;
  center.value = interval_integer_scale(
      4, interval_mul(center_environment[0], center_delta, counters));
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    Interval value = interval_mul(
        center_environment[0], center_delta_gradient[coordinate], counters);
    if (coordinate == 0) value = interval_add(value, center_delta);
    center.gradient[coordinate] = interval_integer_scale(4, value);
  }

  IntervalMatrix hessian = zero_matrix();
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = 0; column < kDimensions; ++column) {
      Interval value = interval_mul(
          box_environment[0], box_delta_hessian[row][column], counters);
      if (row == 0) {
        value = interval_add(value, box_delta_gradient[column]);
      }
      if (column == 0) {
        value = interval_add(value, box_delta_gradient[row]);
      }
      hessian[row][column] = interval_integer_scale(4, value);
    }
  }
  return complete_result(radii, true, center, hessian, counters);
}

struct Evaluation {
  Rat upper;
  Counters counters;
};

void add_counters(Counters& total, const Counters& value) {
  total.interval_products += value.interval_products;
  total.completed_results += value.completed_results;
  total.polynomial_steps += value.polynomial_steps;
  total.outer_steps += value.outer_steps;
  total.sqrt_steps += value.sqrt_steps;
  total.inverse_steps += value.inverse_steps;
  total.atan_steps += value.atan_steps;
}

Counters subtract_counters(const Counters& value, const Counters& baseline) {
  return {value.interval_products - baseline.interval_products,
          value.completed_results - baseline.completed_results,
          value.polynomial_steps - baseline.polynomial_steps,
          value.outer_steps - baseline.outer_steps,
          value.sqrt_steps - baseline.sqrt_steps,
          value.inverse_steps - baseline.inverse_steps,
          value.atan_steps - baseline.atan_steps};
}

std::string instruction_label(const Program& program,
                              std::size_t instruction_index) {
  const Node& instruction = node_at(program, instruction_index);
  if (instruction.is_pair) {
    const Integer tag = require_numeral(program, instruction.left,
                                        "analytic profile tag");
    if (tag == 0) {
      return "poly:" + std::to_string(
          decode_list(program, instruction.right,
                      "profile polynomial program").size());
    }
    if (tag == 1) return "sqrt";
    return "pair:" + tag.get_str();
  }
  const unsigned long opcode = instruction.numeral.get_ui();
  if (opcode == 2) return "neg";
  if (opcode == 3) return "add";
  if (opcode == 4) return "mul";
  if (opcode == 5) return "square";
  if (opcode == 6) return "inverse";
  if (opcode == 7) return "atan";
  if (opcode == 8) return "pi_half";
  return "opcode:" + instruction.numeral.get_str();
}

Evaluation evaluate_job(const Program& program, const Job& job,
                        PolynomialMode polynomial_mode,
                        std::vector<InstructionProfile>* profiles) {
  IntervalVector center_environment;
  IntervalVector box_environment;
  IntegerVector radii;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    const Rat midpoint = (job.lower[coordinate] + job.upper[coordinate]) / 2;
    const Rat radius = (job.upper[coordinate] - job.lower[coordinate]) / 2;
    center_environment[coordinate] = interval_constant(midpoint);
    box_environment[coordinate] = interval_of_q(
        {job.lower[coordinate], job.upper[coordinate]});
    radii[coordinate] = ceil_scaled(radius);
  }

  Counters counters;
  std::vector<TaylorResult> stack;
  std::size_t sqrt_slot = 0;
  for (std::size_t outer_index = 0;
       outer_index < program.instructions.size(); ++outer_index) {
    const std::size_t instruction_index = program.instructions[outer_index];
    const Counters counters_before = counters;
    const std::size_t stack_before = stack.size();
    const std::size_t sqrt_slot_before = sqrt_slot;
    std::chrono::steady_clock::time_point instruction_begin;
    if (profiles != nullptr) {
      instruction_begin = std::chrono::steady_clock::now();
    }
    ++counters.outer_steps;
    const Node& instruction = node_at(program, instruction_index);
    if (instruction.is_pair) {
      const Integer tag = require_numeral(program, instruction.left, "analytic tag");
      if (tag == 0) {
        const std::size_t polynomial_steps = decode_list(
            program, instruction.right, "polynomial mode selection").size();
        const bool use_fused_polynomial =
            polynomial_mode == PolynomialMode::kFusedAll ||
            ((polynomial_mode == PolynomialMode::kFusedDeltaX4 ||
              polynomial_mode == PolynomialMode::kSpecializedAngle) &&
             polynomial_steps == 39);
        if (polynomial_mode == PolynomialMode::kSpecializedAngle &&
            polynomial_steps == 85) {
          stack.push_back(evaluate_four_x1_delta_specialized(
              radii, center_environment, box_environment, counters));
        } else {
          stack.push_back(use_fused_polynomial
                              ? evaluate_polynomial_fused(
                                    program, instruction.right, radii,
                                    center_environment, box_environment, counters)
                              : evaluate_polynomial(
                                    program, instruction.right, radii,
                                    center_environment, counters));
        }
      } else if (tag == 1) {
        if (sqrt_slot >= kSqrtSlots || stack.empty()) {
          throw std::runtime_error("sqrt slot/stack drift");
        }
        TaylorResult value = stack.back();
        stack.pop_back();
        stack.push_back(result_sqrt(radii, job.center_certificates[sqrt_slot],
                                    job.box_certificates[sqrt_slot], value,
                                    counters));
        ++sqrt_slot;
      } else {
        throw std::runtime_error("unknown analytic pair instruction");
      }
    } else {
      const unsigned long opcode = instruction.numeral.get_ui();
      if (opcode == 2 || opcode == 5 || opcode == 6 || opcode == 7) {
        if (stack.empty()) throw std::runtime_error("analytic stack underflow");
        TaylorResult value = stack.back();
        stack.pop_back();
        if (opcode == 2) stack.push_back(result_neg(radii, value, counters));
        if (opcode == 5) stack.push_back(result_mul(radii, value, value, counters));
        if (opcode == 6) stack.push_back(result_inverse(radii, value, counters));
        if (opcode == 7) stack.push_back(result_atan(radii, value, counters));
      } else if (opcode == 3 || opcode == 4) {
        if (stack.size() < 2) throw std::runtime_error("analytic stack underflow");
        TaylorResult right = stack.back();
        stack.pop_back();
        TaylorResult left = stack.back();
        stack.pop_back();
        stack.push_back(opcode == 3 ? result_add(radii, left, right, counters)
                                    : result_mul(radii, left, right, counters));
      } else if (opcode == 8) {
        stack.push_back(result_pi_half(radii, counters));
      } else {
        throw std::runtime_error("unknown analytic scalar instruction");
      }
    }
    if (profiles != nullptr) {
      const auto instruction_end = std::chrono::steady_clock::now();
      InstructionProfile& profile = profiles->at(outer_index);
      if (profile.observations == 0) {
        profile.stack_before = stack_before;
        profile.stack_after = stack.size();
        profile.sqrt_slot_before = sqrt_slot_before;
        profile.sqrt_slot_after = sqrt_slot;
      } else if (profile.stack_before != stack_before ||
                 profile.stack_after != stack.size() ||
                 profile.sqrt_slot_before != sqrt_slot_before ||
                 profile.sqrt_slot_after != sqrt_slot) {
        throw std::runtime_error("instruction profile shape drift");
      }
      ++profile.observations;
      profile.nanoseconds += static_cast<std::uint64_t>(
          std::chrono::duration_cast<std::chrono::nanoseconds>(
              instruction_end - instruction_begin).count());
      add_counters(profile.counters,
                   subtract_counters(counters, counters_before));
    }
  }
  if (sqrt_slot != kSqrtSlots || stack.size() != 1 || !stack.back().domain) {
    throw std::runtime_error("final analytic result shape/domain drift");
  }
  return {normalized_rat(stack.back().value_bound.upper, kScale), counters};
}

std::vector<Rat> read_expected_bounds(const char* path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error(std::string("cannot open expected bounds: ") + path);
  std::vector<Rat> bounds;
  std::string line;
  while (std::getline(input, line)) {
    const std::vector<std::string> fields = split(line, '\t');
    if (fields.size() != 2 || std::stoi(fields[0]) != static_cast<int>(bounds.size())) {
      throw std::runtime_error("expected-bound row drift");
    }
    bounds.push_back(parse_rational(fields[1]));
  }
  return bounds;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 4 || argc > 6) {
      std::cerr << "usage: " << argv[0]
                << " PROGRAM.cval JOBS.tsv EXPECTED-BOUNDS.tsv"
                << " [--profile]"
                << " [--fused-polynomial|--fused-delta-x4|"
                << "--specialized-angle-polynomials]\n";
      return 2;
    }
    bool profile_enabled = false;
    PolynomialMode polynomial_mode = PolynomialMode::kBaseline;
    for (int index = 4; index < argc; ++index) {
      const std::string option(argv[index]);
      if (option == "--profile") {
        profile_enabled = true;
      } else if (option == "--fused-polynomial") {
        polynomial_mode = PolynomialMode::kFusedAll;
      } else if (option == "--fused-delta-x4") {
        polynomial_mode = PolynomialMode::kFusedDeltaX4;
      } else if (option == "--specialized-angle-polynomials") {
        polynomial_mode = PolynomialMode::kSpecializedAngle;
      } else {
        throw std::runtime_error("unknown optional argument: " + option);
      }
    }

    const auto preparation_begin = std::chrono::steady_clock::now();
    const Program program = read_program(argv[1]);
    const std::vector<Job> jobs = read_jobs(argv[2]);
    const std::vector<Rat> expected = read_expected_bounds(argv[3]);
    if (expected.size() != jobs.size()) {
      throw std::runtime_error("expected-bound count drift");
    }
    const auto preparation_end = std::chrono::steady_clock::now();

    Counters total;
    std::vector<Rat> results;
    results.reserve(jobs.size());
    std::vector<InstructionProfile> profiles(
        profile_enabled ? program.instructions.size() : 0);
    std::size_t mismatches = 0;
    std::size_t accepted = 0;
    const auto evaluation_begin = std::chrono::steady_clock::now();
    for (std::size_t index = 0; index < jobs.size(); ++index) {
      const Evaluation evaluation = evaluate_job(
          program, jobs[index], polynomial_mode,
          profile_enabled ? &profiles : nullptr);
      results.push_back(evaluation.upper);
      add_counters(total, evaluation.counters);
      if (evaluation.upper != expected[index]) ++mismatches;
      if (evaluation.upper < 0) ++accepted;
    }
    const auto evaluation_end = std::chrono::steady_clock::now();

    const double preparation_seconds =
        std::chrono::duration<double>(preparation_end - preparation_begin).count();
    const double evaluation_seconds =
        std::chrono::duration<double>(evaluation_end - evaluation_begin).count();
    std::cout << std::setprecision(17);
    std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY"
              << " cells=" << jobs.size()
              << " mode="
              << (polynomial_mode == PolynomialMode::kFusedAll
                      ? "fused-polynomial"
                      : polynomial_mode == PolynomialMode::kFusedDeltaX4
                            ? "fused-delta-x4"
                            : polynomial_mode == PolynomialMode::kSpecializedAngle
                                  ? "specialized-angle-polynomials"
                                  : "baseline")
              << " matched=" << (jobs.size() - mismatches)
              << " mismatches=" << mismatches
              << " accepted=" << accepted
              << " preparation_seconds=" << preparation_seconds
              << " evaluation_seconds=" << evaluation_seconds
              << " interval_products=" << total.interval_products
              << " completed_results=" << total.completed_results
              << " polynomial_steps=" << total.polynomial_steps
              << " outer_steps=" << total.outer_steps
              << " sqrt_steps=" << total.sqrt_steps
              << " inverse_steps=" << total.inverse_steps
              << " atan_steps=" << total.atan_steps << "\n";
    if (profile_enabled) {
      for (std::size_t index = 0; index < profiles.size(); ++index) {
        const InstructionProfile& profile = profiles[index];
        std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE"
                  << " index=" << index
                  << " label=" << instruction_label(
                       program, program.instructions[index])
                  << " observations=" << profile.observations
                  << " stack_before=" << profile.stack_before
                  << " stack_after=" << profile.stack_after
                  << " sqrt_slot_before=" << profile.sqrt_slot_before
                  << " sqrt_slot_after=" << profile.sqrt_slot_after
                  << " nanoseconds=" << profile.nanoseconds
                  << " interval_products=" << profile.counters.interval_products
                  << " completed_results=" << profile.counters.completed_results
                  << " polynomial_steps=" << profile.counters.polynomial_steps
                  << " outer_steps=" << profile.counters.outer_steps
                  << " sqrt_steps=" << profile.counters.sqrt_steps
                  << " inverse_steps=" << profile.counters.inverse_steps
                  << " atan_steps=" << profile.counters.atan_steps << "\n";
      }
    }
    for (std::size_t index = 0; index < results.size(); ++index) {
      std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_RESULT"
                << " index=" << index
                << " upper=" << results[index].get_str()
                << " expected=" << expected[index].get_str()
                << " upper_minus_expected="
                << Rat(results[index] - expected[index]).get_str()
                << " match=" << (results[index] == expected[index] ? 1 : 0)
                << "\n";
    }
    if (polynomial_mode == PolynomialMode::kBaseline && mismatches != 0) {
      std::cerr << "fixed-scale native comparison found " << mismatches
                << " mismatches\n";
      return 1;
    }
    if (polynomial_mode != PolynomialMode::kBaseline &&
        accepted != jobs.size()) {
      std::cerr << "optimized polynomial comparison accepted " << accepted
                << " of " << jobs.size() << " jobs\n";
      return 1;
    }
    if (polynomial_mode == PolynomialMode::kFusedAll) {
      std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_FUSED_POLYNOMIAL_OK"
                << " DEVELOPMENT_NON_RELEASE cells=" << jobs.size() << "\n";
    }
    if (polynomial_mode == PolynomialMode::kFusedDeltaX4) {
      std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_FUSED_DELTA_X4_OK"
                << " DEVELOPMENT_NON_RELEASE cells=" << jobs.size() << "\n";
    }
    if (polynomial_mode == PolynomialMode::kSpecializedAngle) {
      std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_SPECIALIZED_ANGLE_POLYNOMIALS_OK"
                << " DEVELOPMENT_NON_RELEASE cells=" << jobs.size() << "\n";
    }
    std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_OK"
              << " DEVELOPMENT_NON_RELEASE cells=" << jobs.size() << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "native fixed-scale comparison failed: " << error.what() << "\n";
    return 1;
  }
}
