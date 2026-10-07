#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cmath>
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

#if defined(CANDLE_NL_FIXED_INT256) || defined(CANDLE_NL_CHECKED_INT128)
#include <boost/multiprecision/cpp_int.hpp>
#endif
#include <gmpxx.h>

namespace {

constexpr std::size_t kDimensions = 6;
constexpr std::size_t kSqrtSlots = 7;
constexpr std::size_t kSymmetricEntries =
    kDimensions * (kDimensions + 1) / 2;

using Rat = mpq_class;
using Integer = mpz_class;
#if defined(CANDLE_NL_CHECKED_INT128)
using Fixed = boost::multiprecision::checked_int128_t;
Fixed kScale = static_cast<Fixed>(1000000000000LL);
constexpr const char* kFixedBackend = "checked-int128";
#elif defined(CANDLE_NL_FIXED_LONG_DOUBLE)
using Fixed = long double;
Fixed kScale = 1000000000000.0L;
constexpr const char* kFixedBackend = "long-double-integer";
#elif defined(CANDLE_NL_FIXED_INT128)
using Fixed = __int128;
Fixed kScale = static_cast<Fixed>(1000000000000LL);
constexpr const char* kFixedBackend = "int128";
#elif defined(CANDLE_NL_FIXED_INT256)
using Fixed = boost::multiprecision::int256_t;
Fixed kScale = static_cast<Fixed>(1000000000000LL);
constexpr const char* kFixedBackend = "fixed-int256";
#else
using Fixed = mpz_class;
Fixed kScale("1000000000000");
constexpr const char* kFixedBackend = "mpz";
#endif
Fixed kTwoScaleSquared = 2 * kScale * kScale;
bool kSkipExactZeroProducts = false;
bool kUseSymmetricHessianOps = false;
bool kUseCompactSupportJets = false;
bool kUseFixedSqrtInverseKernels = false;
bool kUseFixedAtanKernel = false;
bool kVerifyFixedKernelEnclosures = false;
bool kUsePreparedSimplePolynomials = false;
bool kUsePreparedCoordinateSqrtTerms = false;
bool kUsePreparedDihedralChain = false;
bool kUseSpecializedDihedralIdentities = false;
bool kUseHistoricalDihedral = false;
bool kUseHistoricalBlockRounding = false;
bool kUseTightDihedralSqrtCertificates = false;
bool kUseOptimizedDihedralUBounds = false;
bool kUseComputedTightSqrtCertificates = false;
bool kPrecomputeTightSqrtCertificates = false;
bool kUseHardwareSeededIntegerSqrt = false;
bool kUseHardwareSeededFixedQuotient = false;
bool kUseDyadicShiftFixedQuotient = false;
int kDyadicScaleBits = -1;
bool kFuseConsecutiveAdds = false;
bool kUseNarrowFixedProducts = false;
bool kUseUncheckedNarrowFixedProducts = false;
bool kCountFixedQuotients = false;
std::uint64_t kFloorFixedQuotientCalls = 0;
std::uint64_t kCeilFixedQuotientCalls = 0;
std::uint64_t kDyadicShiftFixedQuotientCalls = 0;
std::uint64_t kDyadicFallbackFixedQuotientCalls = 0;

Fixed fixed_product(Fixed left, Fixed right) {
#if defined(CANDLE_NL_FIXED_INT128)
  if (kUseNarrowFixedProducts || kUseUncheckedNarrowFixedProducts) {
    const Fixed minimum =
        static_cast<Fixed>(std::numeric_limits<std::int64_t>::min());
    const Fixed maximum =
        static_cast<Fixed>(std::numeric_limits<std::int64_t>::max());
    if (kUseNarrowFixedProducts &&
        (left < minimum || left > maximum ||
         right < minimum || right > maximum)) {
      throw std::overflow_error("narrow fixed product operand overflow");
    }
    return static_cast<Fixed>(static_cast<std::int64_t>(left)) *
           static_cast<Fixed>(static_cast<std::int64_t>(right));
  }
#endif
  return left * right;
}

#if defined(CANDLE_NL_FIXED_INT128) && \
    defined(CANDLE_NL_FIXED_RANGE_PROFILE)
struct FixedRangeProfile {
  unsigned quotient_numerator_bits = 0;
  unsigned quotient_denominator_bits = 0;
  unsigned quotient_result_bits = 0;
  unsigned multiplication_operand_bits = 0;
  unsigned multiplication_product_bits = 0;
  unsigned addition_result_bits = 0;
  unsigned scaled_input_bits = 0;
  std::uint64_t quotient_results_outside_int64 = 0;
  std::uint64_t multiplication_operands_outside_int64 = 0;
  std::uint64_t addition_results_outside_int64 = 0;
  std::uint64_t scaled_inputs_outside_int64 = 0;
};

FixedRangeProfile kFixedRangeProfile;

unsigned fixed_magnitude_bits(Fixed value) {
  const unsigned __int128 magnitude = value < 0
      ? static_cast<unsigned __int128>(-(value + 1)) + 1
      : static_cast<unsigned __int128>(value);
  if (magnitude == 0) return 0;
  const std::uint64_t upper = static_cast<std::uint64_t>(magnitude >> 64);
  if (upper != 0) {
    return 128U - static_cast<unsigned>(__builtin_clzll(upper));
  }
  return 64U - static_cast<unsigned>(
      __builtin_clzll(static_cast<std::uint64_t>(magnitude)));
}

bool fixed_fits_int64(Fixed value) {
  return value >= static_cast<Fixed>(std::numeric_limits<std::int64_t>::min()) &&
         value <= static_cast<Fixed>(std::numeric_limits<std::int64_t>::max());
}

void update_fixed_bits(unsigned& maximum, Fixed value) {
  maximum = std::max(maximum, fixed_magnitude_bits(value));
}

Fixed range_profile_quotient(Fixed numerator, Fixed denominator,
                             Fixed result) {
  update_fixed_bits(kFixedRangeProfile.quotient_numerator_bits, numerator);
  update_fixed_bits(kFixedRangeProfile.quotient_denominator_bits, denominator);
  update_fixed_bits(kFixedRangeProfile.quotient_result_bits, result);
  if (!fixed_fits_int64(result)) {
    ++kFixedRangeProfile.quotient_results_outside_int64;
  }
  return result;
}

Fixed range_profile_scaled_input(Fixed value) {
  update_fixed_bits(kFixedRangeProfile.scaled_input_bits, value);
  if (!fixed_fits_int64(value)) {
    ++kFixedRangeProfile.scaled_inputs_outside_int64;
  }
  return value;
}
#else
[[maybe_unused]] Fixed range_profile_quotient(
    Fixed, Fixed, Fixed result) { return result; }
Fixed range_profile_scaled_input(Fixed value) { return value; }
#endif

Rat normalized_rat(const Integer& numerator, const Integer& denominator) {
  Rat result(numerator, denominator);
  result.canonicalize();
  return result;
}

struct Interval {
  Fixed lower;
  Fixed upper;
};

#if defined(CANDLE_NL_FIXED_INT128) && \
    defined(CANDLE_NL_FIXED_RANGE_PROFILE)
void range_profile_multiplication(const Interval& left,
                                  const Interval& right,
                                  const Interval& product) {
  for (const Fixed value : {left.lower, left.upper,
                            right.lower, right.upper}) {
    update_fixed_bits(kFixedRangeProfile.multiplication_operand_bits, value);
    if (!fixed_fits_int64(value)) {
      ++kFixedRangeProfile.multiplication_operands_outside_int64;
    }
  }
  update_fixed_bits(kFixedRangeProfile.multiplication_product_bits,
                    product.lower);
  update_fixed_bits(kFixedRangeProfile.multiplication_product_bits,
                    product.upper);
}

void range_profile_addition(const Interval& result) {
  for (const Fixed value : {result.lower, result.upper}) {
    update_fixed_bits(kFixedRangeProfile.addition_result_bits, value);
    if (!fixed_fits_int64(value)) {
      ++kFixedRangeProfile.addition_results_outside_int64;
    }
  }
}
#else
void range_profile_multiplication(const Interval&, const Interval&,
                                  const Interval&) {}
void range_profile_addition(const Interval&) {}
#endif

struct RationalInterval {
  Rat lower;
  Rat upper;
};

using IntervalVector = std::array<Interval, kDimensions>;
using IntervalMatrix = std::array<IntervalVector, kDimensions>;
using IntegerVector = std::array<Fixed, kDimensions>;

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

struct SecondOrderBox {
  Interval value;
  IntervalVector gradient;
  IntervalMatrix hessian;
};

using GradientMask = std::uint8_t;
using HessianMask = std::uint32_t;

struct CompactMatrix {
  std::array<Interval, kSymmetricEntries> entries;
  HessianMask mask = 0;
};

struct CompactTaylorResult {
  bool domain;
  Interval center_value;
  IntervalVector center_gradient;
  GradientMask center_gradient_mask;
  Interval value_bound;
  IntervalVector gradient_bounds;
  GradientMask gradient_bounds_mask;
  CompactMatrix hessian;
};

struct Counters {
  std::uint64_t interval_products = 0;
  std::uint64_t skipped_zero_products = 0;
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

struct RoundingProfile {
  std::uint64_t floor_quotients = 0;
  std::uint64_t ceil_quotients = 0;
  std::uint64_t nanoseconds = 0;
  std::size_t observations = 0;
  std::string label;
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
  enum class SimplePolynomialKind { kUnknown, kConstant, kVariable };
  struct SimplePolynomial {
    SimplePolynomialKind kind = SimplePolynomialKind::kUnknown;
    Rat constant = 0;
    std::size_t variable = 0;
  };
  std::vector<SimplePolynomial> prepared_simple_polynomials;
  struct CoordinateSqrtTerm {
    bool active = false;
    std::size_t variable = 0;
    Rat coefficient = 0;
    std::size_t sqrt_slot = 0;
  };
  std::vector<CoordinateSqrtTerm> prepared_coordinate_sqrt_terms;
  bool prepared_dihedral_chain = false;
};

struct Job {
  int index = 0;
  std::array<RationalInterval, kSqrtSlots> box_certificates;
  std::array<RationalInterval, kSqrtSlots> center_certificates;
  std::array<Interval, kSqrtSlots> fixed_box_certificates;
  std::array<Interval, kSqrtSlots> fixed_center_certificates;
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
  if (jobs.empty()) throw std::runtime_error("empty native job set");
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

#if defined(CANDLE_NL_FIXED_LONG_DOUBLE)
Integer integer_of_fixed(const Fixed& value) {
  constexpr Fixed kLongLongExclusiveUpper = 9223372036854775808.0L;
  if (!std::isfinite(value) || std::trunc(value) != value ||
      value < -kLongLongExclusiveUpper ||
      value >= kLongLongExclusiveUpper) {
    throw std::runtime_error("invalid long-double fixed conversion");
  }
  return Integer(std::to_string(static_cast<long long>(value)));
}

Fixed fixed_of_integer(const Integer& value) {
  return std::stold(value.get_str());
}

Fixed floor_fixed_quotient(Fixed numerator, Fixed denominator) {
  if (kCountFixedQuotients) ++kFloorFixedQuotientCalls;
  if (denominator == 0) {
    throw std::runtime_error("long-double fixed division by zero");
  }
  // This backend is an untrusted performance discriminator.  Padding every
  // quotient by one fixed-scale unit makes its final bounds suitable for the
  // fixture containment gate; it is not a replacement for a proved rounding
  // implementation.
  return std::floor(numerator / denominator) - 1.0L;
}

Fixed ceil_fixed_quotient(Fixed numerator, Fixed denominator) {
  if (kCountFixedQuotients) ++kCeilFixedQuotientCalls;
  if (denominator == 0) {
    throw std::runtime_error("long-double fixed division by zero");
  }
  return std::ceil(numerator / denominator) + 1.0L;
}
#elif defined(CANDLE_NL_FIXED_INT128)
std::string fixed_string(Fixed value) {
  if (value == 0) return "0";
  const bool negative = value < 0;
  unsigned __int128 magnitude = negative
      ? static_cast<unsigned __int128>(-(value + 1)) + 1
      : static_cast<unsigned __int128>(value);
  std::string result;
  while (magnitude != 0) {
    result.push_back(static_cast<char>('0' + magnitude % 10));
    magnitude /= 10;
  }
  if (negative) result.push_back('-');
  std::reverse(result.begin(), result.end());
  return result;
}

Integer integer_of_fixed(Fixed value) { return Integer(fixed_string(value)); }

Fixed fixed_of_integer(const Integer& value) {
  const std::string text = value.get_str();
  const bool negative = !text.empty() && text[0] == '-';
  const std::size_t begin = negative ? 1 : 0;
  const unsigned __int128 positive_limit =
      (~static_cast<unsigned __int128>(0)) >> 1;
  const unsigned __int128 limit =
      negative ? positive_limit + 1 : positive_limit;
  unsigned __int128 magnitude = 0;
  for (std::size_t index = begin; index < text.size(); ++index) {
    const unsigned digit = static_cast<unsigned>(text[index] - '0');
    if (magnitude > (limit - digit) / 10) {
      throw std::overflow_error("fixed int128 conversion overflow");
    }
    magnitude = magnitude * 10 + digit;
  }
  if (!negative) return static_cast<Fixed>(magnitude);
  if (magnitude == positive_limit + 1) {
    return -static_cast<Fixed>(positive_limit) - 1;
  }
  return -static_cast<Fixed>(magnitude);
}

Fixed native_floor_fixed_quotient(Fixed numerator, Fixed denominator) {
  Fixed quotient = numerator / denominator;
  const Fixed remainder = numerator % denominator;
  if (remainder != 0 && ((remainder < 0) != (denominator < 0))) --quotient;
  return quotient;
}

Fixed native_ceil_fixed_quotient(Fixed numerator, Fixed denominator) {
  Fixed quotient = numerator / denominator;
  const Fixed remainder = numerator % denominator;
  if (remainder != 0 && ((remainder < 0) == (denominator < 0))) ++quotient;
  return quotient;
}

Fixed floor_power_of_two_quotient(Fixed numerator, unsigned shift) {
  if (shift == 0 || shift >= 127) {
    throw std::runtime_error("invalid floor power-of-two shift");
  }
  const bool negative = numerator < 0;
  const unsigned __int128 magnitude = negative
      ? static_cast<unsigned __int128>(-(numerator + 1)) + 1
      : static_cast<unsigned __int128>(numerator);
  const unsigned __int128 mask =
      (static_cast<unsigned __int128>(1) << shift) - 1;
  const Fixed quotient = static_cast<Fixed>(magnitude >> shift);
  if (!negative) return quotient;
  return (magnitude & mask) == 0 ? -quotient : -quotient - 1;
}

Fixed ceil_power_of_two_quotient(Fixed numerator, unsigned shift) {
  if (shift == 0 || shift >= 127) {
    throw std::runtime_error("invalid ceil power-of-two shift");
  }
  const bool negative = numerator < 0;
  const unsigned __int128 magnitude = negative
      ? static_cast<unsigned __int128>(-(numerator + 1)) + 1
      : static_cast<unsigned __int128>(numerator);
  const unsigned __int128 mask =
      (static_cast<unsigned __int128>(1) << shift) - 1;
  const Fixed quotient = static_cast<Fixed>(magnitude >> shift);
  if (negative) return -quotient;
  return (magnitude & mask) == 0 ? quotient : quotient + 1;
}

int fixed_dyadic_denominator_shift(Fixed denominator) {
  if (kDyadicScaleBits <= 0) return -1;
  if (denominator == kScale) return kDyadicScaleBits;
  if (denominator == kScale * kScale) return 2 * kDyadicScaleBits;
  if (denominator == kTwoScaleSquared) return 2 * kDyadicScaleBits + 1;
  return -1;
}

void verify_dyadic_shift_quotient_samples() {
  const unsigned __int128 positive_limit =
      (~static_cast<unsigned __int128>(0)) >> 1;
  const Fixed maximum = static_cast<Fixed>(positive_limit);
  const Fixed minimum = -maximum - 1;
  const std::array<Fixed, 13> samples = {
      minimum, minimum + 1, -1001, -1000, -999, -2, -1,
      0, 1, 2, 999, 1000, maximum};
  const std::array<unsigned, 7> shifts = {1, 2, 7, 23, 46, 62, 126};
  for (const unsigned shift : shifts) {
    const Fixed denominator =
        static_cast<Fixed>(static_cast<unsigned __int128>(1) << shift);
    for (const Fixed numerator : samples) {
      if (floor_power_of_two_quotient(numerator, shift) !=
              native_floor_fixed_quotient(numerator, denominator) ||
          ceil_power_of_two_quotient(numerator, shift) !=
              native_ceil_fixed_quotient(numerator, denominator)) {
        throw std::runtime_error("dyadic shift quotient self-check failure");
      }
    }
  }
}

Fixed hardware_seeded_floor_fixed_quotient(Fixed numerator,
                                           Fixed denominator) {
  if (denominator == 0) {
    throw std::runtime_error("hardware-seeded fixed division by zero");
  }
  if (denominator < 0) {
    return native_floor_fixed_quotient(numerator, denominator);
  }
  const long double estimate = std::floor(
      static_cast<long double>(numerator) /
      static_cast<long double>(denominator));
  const long double conversion_limit = std::ldexp(1.0L, 126);
  if (!std::isfinite(estimate) || estimate <= -conversion_limit ||
      estimate >= conversion_limit) {
    throw std::overflow_error("hardware fixed quotient seed overflow");
  }
  Fixed result = static_cast<Fixed>(estimate);
  Fixed product;
  while (true) {
    if (__builtin_mul_overflow(result, denominator, &product)) {
      return native_floor_fixed_quotient(numerator, denominator);
    }
    if (product <= numerator) break;
    --result;
  }
  while (true) {
    if (__builtin_mul_overflow(result + 1, denominator, &product)) break;
    if (product > numerator) break;
    ++result;
  }
  return result;
}

Fixed hardware_seeded_ceil_fixed_quotient(Fixed numerator,
                                          Fixed denominator) {
  if (denominator == 0) {
    throw std::runtime_error("hardware-seeded fixed division by zero");
  }
  if (denominator < 0) {
    return native_ceil_fixed_quotient(numerator, denominator);
  }
  const long double estimate = std::ceil(
      static_cast<long double>(numerator) /
      static_cast<long double>(denominator));
  const long double conversion_limit = std::ldexp(1.0L, 126);
  if (!std::isfinite(estimate) || estimate <= -conversion_limit ||
      estimate >= conversion_limit) {
    throw std::overflow_error("hardware fixed quotient seed overflow");
  }
  Fixed result = static_cast<Fixed>(estimate);
  Fixed product;
  while (true) {
    if (__builtin_mul_overflow(result - 1, denominator, &product)) break;
    if (product < numerator) break;
    --result;
  }
  while (true) {
    if (__builtin_mul_overflow(result, denominator, &product)) {
      return native_ceil_fixed_quotient(numerator, denominator);
    }
    if (product >= numerator) break;
    ++result;
  }
  return result;
}

Fixed floor_fixed_quotient(Fixed numerator, Fixed denominator) {
  if (kCountFixedQuotients) ++kFloorFixedQuotientCalls;
  if (kUseDyadicShiftFixedQuotient) {
    const int shift = fixed_dyadic_denominator_shift(denominator);
    if (shift >= 0) {
      ++kDyadicShiftFixedQuotientCalls;
      return range_profile_quotient(
          numerator, denominator,
          floor_power_of_two_quotient(
              numerator, static_cast<unsigned>(shift)));
    }
    ++kDyadicFallbackFixedQuotientCalls;
  }
  if (kUseHardwareSeededFixedQuotient) {
    return range_profile_quotient(
        numerator, denominator,
        hardware_seeded_floor_fixed_quotient(numerator, denominator));
  }
  return range_profile_quotient(
      numerator, denominator,
      native_floor_fixed_quotient(numerator, denominator));
}

Fixed ceil_fixed_quotient(Fixed numerator, Fixed denominator) {
  if (kCountFixedQuotients) ++kCeilFixedQuotientCalls;
  if (kUseDyadicShiftFixedQuotient) {
    const int shift = fixed_dyadic_denominator_shift(denominator);
    if (shift >= 0) {
      ++kDyadicShiftFixedQuotientCalls;
      return range_profile_quotient(
          numerator, denominator,
          ceil_power_of_two_quotient(
              numerator, static_cast<unsigned>(shift)));
    }
    ++kDyadicFallbackFixedQuotientCalls;
  }
  if (kUseHardwareSeededFixedQuotient) {
    return range_profile_quotient(
        numerator, denominator,
        hardware_seeded_ceil_fixed_quotient(numerator, denominator));
  }
  return range_profile_quotient(
      numerator, denominator,
      native_ceil_fixed_quotient(numerator, denominator));
}
#elif defined(CANDLE_NL_FIXED_INT256) || defined(CANDLE_NL_CHECKED_INT128)
Integer integer_of_fixed(const Fixed& value) {
  return Integer(value.convert_to<std::string>());
}

Fixed fixed_of_integer(const Integer& value) {
  return Fixed(value.get_str());
}

Fixed floor_fixed_quotient(const Fixed& numerator, const Fixed& denominator) {
  if (kCountFixedQuotients) ++kFloorFixedQuotientCalls;
  Fixed quotient = numerator / denominator;
  const Fixed remainder = numerator % denominator;
  if (remainder != 0 && ((remainder < 0) != (denominator < 0))) --quotient;
  return quotient;
}

Fixed ceil_fixed_quotient(const Fixed& numerator, const Fixed& denominator) {
  if (kCountFixedQuotients) ++kCeilFixedQuotientCalls;
  Fixed quotient = numerator / denominator;
  const Fixed remainder = numerator % denominator;
  if (remainder != 0 && ((remainder < 0) == (denominator < 0))) ++quotient;
  return quotient;
}
#else
Integer integer_of_fixed(const Fixed& value) { return value; }
Fixed fixed_of_integer(const Integer& value) { return value; }
Fixed floor_fixed_quotient(const Fixed& numerator, const Fixed& denominator) {
  if (kCountFixedQuotients) ++kFloorFixedQuotientCalls;
  return floor_quotient(numerator, denominator);
}
Fixed ceil_fixed_quotient(const Fixed& numerator, const Fixed& denominator) {
  if (kCountFixedQuotients) ++kCeilFixedQuotientCalls;
  return ceil_quotient(numerator, denominator);
}
#endif

Fixed floor_scaled(const Rat& value) {
  return range_profile_scaled_input(fixed_of_integer(floor_quotient(
      value.get_num() * integer_of_fixed(kScale), value.get_den())));
}

Fixed ceil_scaled(const Rat& value) {
  return range_profile_scaled_input(fixed_of_integer(ceil_quotient(
      value.get_num() * integer_of_fixed(kScale), value.get_den())));
}

Fixed absolute(const Fixed& value) { return value < 0 ? -value : value; }

Interval zero_interval() { return {0, 0}; }

Interval one_interval() { return {kScale, kScale}; }

Interval interval_of_q(const RationalInterval& value) {
  return {floor_scaled(value.lower), ceil_scaled(value.upper)};
}

void prepare_fixed_sqrt_certificates(std::vector<Job>& jobs) {
  for (Job& job : jobs) {
    for (std::size_t slot = 0; slot < kSqrtSlots; ++slot) {
      job.fixed_box_certificates[slot] =
          interval_of_q(job.box_certificates[slot]);
      job.fixed_center_certificates[slot] =
          interval_of_q(job.center_certificates[slot]);
    }
  }
}

Interval interval_constant(const Rat& value) {
  return {floor_scaled(value), ceil_scaled(value)};
}

Interval interval_neg(const Interval& value) {
  return {-value.upper, -value.lower};
}

Interval interval_add(const Interval& left, const Interval& right) {
  const Interval result = {
      left.lower + right.lower, left.upper + right.upper};
  range_profile_addition(result);
  return result;
}

Interval interval_integer_scale(long coefficient, const Interval& value) {
  Interval result;
  if (coefficient >= 0) {
    result = {coefficient * value.lower, coefficient * value.upper};
  } else {
    result = {coefficient * value.upper, coefficient * value.lower};
  }
  range_profile_addition(result);
  return result;
}

Interval interval_sum(std::initializer_list<Interval> values) {
  Interval result = zero_interval();
  for (const Interval& value : values) result = interval_add(result, value);
  return result;
}

Interval raw_interval_mul(const Interval& left, const Interval& right,
                          Counters& counters) {
  if (kSkipExactZeroProducts &&
      ((left.lower == 0 && left.upper == 0) ||
       (right.lower == 0 && right.upper == 0))) {
    ++counters.skipped_zero_products;
    return zero_interval();
  }
  ++counters.interval_products;
  const Fixed ll = fixed_product(left.lower, right.lower);
  const Fixed lu = fixed_product(left.lower, right.upper);
  const Fixed ul = fixed_product(left.upper, right.lower);
  const Fixed uu = fixed_product(left.upper, right.upper);
  Fixed lower = ll;
  if (lu < lower) lower = lu;
  if (ul < lower) lower = ul;
  if (uu < lower) lower = uu;
  Fixed upper = ll;
  if (lu > upper) upper = lu;
  if (ul > upper) upper = ul;
  if (uu > upper) upper = uu;
  const Interval result = {lower, upper};
  range_profile_multiplication(left, right, result);
  return result;
}

Interval raw_interval_round(const Fixed& denominator,
                            const Interval& value) {
  return {floor_fixed_quotient(value.lower, denominator),
          ceil_fixed_quotient(value.upper, denominator)};
}

Interval interval_mul(const Interval& left, const Interval& right,
                      Counters& counters) {
  return raw_interval_round(kScale, raw_interval_mul(left, right, counters));
}

Fixed interval_abs_upper(const Interval& value) {
  const Fixed lower = absolute(value.lower);
  const Fixed upper = absolute(value.upper);
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
  if (kUseSymmetricHessianOps) {
    for (std::size_t row = 0; row < kDimensions; ++row) {
      for (std::size_t column = row; column < kDimensions; ++column) {
        result[row][column] = interval_neg(value[row][column]);
        result[column][row] = result[row][column];
      }
    }
    return result;
  }
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = vector_neg(value[i]);
  }
  return result;
}

IntervalMatrix matrix_add(const IntervalMatrix& left,
                          const IntervalMatrix& right) {
  IntervalMatrix result;
  if (kUseSymmetricHessianOps) {
    for (std::size_t row = 0; row < kDimensions; ++row) {
      for (std::size_t column = row; column < kDimensions; ++column) {
        result[row][column] =
            interval_add(left[row][column], right[row][column]);
        result[column][row] = result[row][column];
      }
    }
    return result;
  }
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
  if (kUseSymmetricHessianOps) {
    for (std::size_t row = 0; row < kDimensions; ++row) {
      for (std::size_t column = row; column < kDimensions; ++column) {
        result[row][column] =
            raw_interval_mul(scalar, value[row][column], counters);
        result[column][row] = result[row][column];
      }
    }
    return result;
  }
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
                                const Fixed& denominator) {
  IntervalVector result;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result[i] = raw_interval_round(denominator, value[i]);
  }
  return result;
}

IntervalMatrix raw_matrix_round(const IntervalMatrix& value,
                                const Fixed& denominator) {
  IntervalMatrix result;
  if (kUseSymmetricHessianOps) {
    for (std::size_t row = 0; row < kDimensions; ++row) {
      for (std::size_t column = row; column < kDimensions; ++column) {
        result[row][column] =
            raw_interval_round(denominator, value[row][column]);
        result[column][row] = result[row][column];
      }
    }
    return result;
  }
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

IntervalMatrix interval_self_outer(const IntervalVector& value,
                                   Counters& counters) {
  if (!kUseSymmetricHessianOps) {
    return interval_outer(value, value, counters);
  }
  IntervalMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      result[row][column] = raw_interval_round(
          kScale, raw_interval_mul(value[row], value[column], counters));
      result[column][row] = result[row][column];
    }
  }
  return result;
}

IntervalMatrix raw_product_hessian(
    const Interval& right_value, const IntervalMatrix& left_hessian,
    const IntervalVector& left_gradient,
    const IntervalVector& right_gradient, const Interval& left_value,
    const IntervalMatrix& right_hessian, Counters& counters) {
  if (!kUseSymmetricHessianOps) {
    return matrix_add(
        matrix_add(raw_matrix_scale(right_value, left_hessian, counters),
                   raw_outer(left_gradient, right_gradient, counters)),
        matrix_add(raw_outer(right_gradient, left_gradient, counters),
                   raw_matrix_scale(left_value, right_hessian, counters)));
  }
  IntervalMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      const Interval value = interval_add(
          interval_add(
              raw_interval_mul(right_value, left_hessian[row][column],
                               counters),
              raw_interval_mul(left_gradient[row], right_gradient[column],
                               counters)),
          interval_add(
              raw_interval_mul(right_gradient[row], left_gradient[column],
                               counters),
              raw_interval_mul(left_value, right_hessian[row][column],
                               counters)));
      result[row][column] = value;
      result[column][row] = value;
    }
  }
  return result;
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
  const IntervalMatrix raw_box_hessian = raw_product_hessian(
      right.box_value, left.box_hessian, left.box_gradient,
      right.box_gradient, left.box_value, right.box_hessian, counters);
  return {{raw_interval_round(kScale, raw_center.value),
           raw_vector_round(raw_center.gradient, kScale)},
          raw_interval_round(kScale, raw_box_value),
          raw_vector_round(raw_box_gradient, kScale),
          raw_matrix_round(raw_box_hessian, kScale)};
}

Fixed dot_abs_upper(const IntegerVector& radii,
                    const IntervalVector& row) {
  Fixed result = 0;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    result += radii[i] * interval_abs_upper(row[i]);
  }
  return result;
}

Fixed weighted_rows_abs_upper(const IntegerVector& radii,
                              const IntervalMatrix& matrix) {
  Fixed result = 0;
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
  const Fixed linear = dot_abs_upper(radii, center.gradient);
  const Fixed quadratic = weighted_rows_abs_upper(radii, hessian);
  const Fixed error = 2 * kScale * linear + quadratic;
  const Interval raw_value = {
      kTwoScaleSquared * center.value.lower - error,
      kTwoScaleSquared * center.value.upper + error};

  IntervalVector gradient_bounds;
  for (std::size_t i = 0; i < kDimensions; ++i) {
    const Fixed variation = dot_abs_upper(radii, hessian[i]);
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
  const IntervalMatrix raw_hessian = raw_product_hessian(
      right.value_bound, left.hessian, left.gradient_bounds,
      right.gradient_bounds, left.value_bound, right.hessian, counters);
  return complete_raw_result(radii, left.domain && right.domain, raw_center,
                             raw_hessian, counters);
}

RationalInterval fixed_to_q(const Interval& value) {
  const Integer scale = integer_of_fixed(kScale);
  return {normalized_rat(integer_of_fixed(value.lower), scale),
          normalized_rat(integer_of_fixed(value.upper), scale)};
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

bool fixed_interval_not_zero(const Interval& value) {
  return value.lower > 0 || value.upper < 0;
}

Interval fixed_interval_inv(const Interval& value) {
  if (!fixed_interval_not_zero(value)) {
    throw std::runtime_error("fixed inverse interval contains zero");
  }
  const Fixed scale_squared = kScale * kScale;
  return {floor_fixed_quotient(scale_squared, value.upper),
          ceil_fixed_quotient(scale_squared, value.lower)};
}

bool fixed_sqrt_certificate(const Interval& input,
                            const Interval& output) {
  return input.lower >= 0 && input.lower <= input.upper &&
         output.lower >= 0 && output.lower <= output.upper &&
         output.lower * output.lower <= input.lower * kScale &&
         input.upper * kScale <= output.upper * output.upper;
}

Fixed floor_integer_sqrt(const Fixed& value) {
  if (value < 0) {
    throw std::runtime_error("integer square root of negative value");
  }
  if (value < 2) return value;
#if defined(CANDLE_NL_FIXED_INT128)
  if (kUseHardwareSeededIntegerSqrt) {
    Fixed result = static_cast<Fixed>(
        std::sqrt(static_cast<long double>(value)));
    if (result < 1) result = 1;
    while (result > value / result) --result;
    while (result + 1 <= value / (result + 1)) ++result;
    return result;
  }
#endif
  Fixed lower = 1;
  Fixed upper = 2;
  while (upper <= value / upper) {
    lower = upper;
    upper *= 2;
  }
  while (upper - lower > 1) {
    const Fixed middle = lower + (upper - lower) / 2;
    if (middle <= value / middle) {
      lower = middle;
    } else {
      upper = middle;
    }
  }
  return lower;
}

Interval fixed_sqrt_enclosure(const Interval& input) {
  if (input.lower < 0 || input.lower > input.upper) {
    throw std::runtime_error("invalid fixed square-root input");
  }
  const Fixed lower_target = input.lower * kScale;
  const Fixed upper_target = input.upper * kScale;
  const Fixed lower = floor_integer_sqrt(lower_target);
  Fixed upper = floor_integer_sqrt(upper_target);
  if (upper * upper < upper_target) ++upper;
  const Interval result = {lower, upper};
  if (!fixed_sqrt_certificate(input, result)) {
    throw std::runtime_error("computed square-root enclosure failure");
  }
  return result;
}

Interval fixed_rational_constant(long numerator, long denominator) {
  const Fixed scaled_numerator = static_cast<Fixed>(numerator) * kScale;
  const Fixed fixed_denominator = static_cast<Fixed>(denominator);
  return {floor_fixed_quotient(scaled_numerator, fixed_denominator),
          ceil_fixed_quotient(scaled_numerator, fixed_denominator)};
}

Interval fixed_interval_square(const Interval& value, Counters& counters) {
  ++counters.interval_products;
  if (value.lower >= 0) {
    return {floor_fixed_quotient(value.lower * value.lower, kScale),
            ceil_fixed_quotient(value.upper * value.upper, kScale)};
  }
  if (value.upper <= 0) {
    return {floor_fixed_quotient(value.upper * value.upper, kScale),
            ceil_fixed_quotient(value.lower * value.lower, kScale)};
  }
  const Fixed lower_square = value.lower * value.lower;
  const Fixed upper_square = value.upper * value.upper;
  const Fixed raw_upper = lower_square > upper_square
                              ? lower_square
                              : upper_square;
  return {0, ceil_fixed_quotient(raw_upper, kScale)};
}

Interval fixed_atan_pos_lower(Fixed x, Counters& counters) {
  const Interval point = {x, x};
  const Interval x2 = fixed_interval_square(point, counters);
  Interval polynomial = fixed_rational_constant(-1, 11);
  polynomial = interval_add(fixed_rational_constant(1, 9),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(-1, 7),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(1, 5),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(-1, 3),
                            interval_mul(x2, polynomial, counters));
  return interval_mul(
      point, interval_add(one_interval(),
                          interval_mul(x2, polynomial, counters)), counters);
}

Interval fixed_atan_pos_upper(Fixed x, Counters& counters) {
  const Interval point = {x, x};
  const Interval x2 = fixed_interval_square(point, counters);
  Interval polynomial = fixed_rational_constant(1, 13);
  polynomial = interval_add(fixed_rational_constant(-1, 11),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(1, 9),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(-1, 7),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(1, 5),
                            interval_mul(x2, polynomial, counters));
  polynomial = interval_add(fixed_rational_constant(-1, 3),
                            interval_mul(x2, polynomial, counters));
  return interval_mul(
      point, interval_add(one_interval(),
                          interval_mul(x2, polynomial, counters)), counters);
}

Fixed fixed_atan_lower_point(Fixed x, Counters& counters) {
  if (absolute(x) >= kScale) {
    throw std::runtime_error("fixed atan argument outside open unit interval");
  }
  if (x >= 0) return fixed_atan_pos_lower(x, counters).lower;
  return -fixed_atan_pos_upper(-x, counters).upper;
}

Fixed fixed_atan_upper_point(Fixed x, Counters& counters) {
  if (absolute(x) >= kScale) {
    throw std::runtime_error("fixed atan argument outside open unit interval");
  }
  if (x >= 0) return fixed_atan_pos_upper(x, counters).upper;
  return -fixed_atan_pos_lower(-x, counters).lower;
}

Interval fixed_atan_interval(const Interval& input, Counters& counters) {
  return {fixed_atan_lower_point(input.lower, counters),
          fixed_atan_upper_point(input.upper, counters)};
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
                            interval_self_outer(value.gradient_bounds,
                                                counters),
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
          interval_self_outer(value.gradient_bounds, counters),
          counters),
      interval_matrix_scale(box_d, value.hessian, counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_inverse_fixed(const IntegerVector& radii,
                                  const TaylorResult& value,
                                  Counters& counters) {
  ++counters.inverse_steps;
  const bool domain = value.domain &&
                      fixed_interval_not_zero(value.center.value) &&
                      fixed_interval_not_zero(value.value_bound);
  if (!domain) throw std::runtime_error("fixed inverse domain failure");
  const Interval r = fixed_interval_inv(value.center.value);
  const Interval r2 = interval_mul(r, r, counters);
  const FirstJet center = {
      r, interval_vector_scale(interval_neg(r2), value.center.gradient,
                               counters)};

  const Interval box_r = fixed_interval_inv(value.value_bound);
  const Interval box_r2 = interval_mul(box_r, box_r, counters);
  const Interval box_r3 = interval_mul(box_r2, box_r, counters);
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(interval_neg(box_r2), value.hessian, counters),
      interval_matrix_scale(
          interval_add(box_r3, box_r3),
          interval_self_outer(value.gradient_bounds, counters), counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_sqrt_fixed(
    const IntegerVector& radii, const Interval& center_certificate,
    const Interval& box_certificate, const TaylorResult& value,
    Counters& counters) {
  ++counters.sqrt_steps;
  const Interval center_sqrt = kUseComputedTightSqrtCertificates
      ? fixed_sqrt_enclosure(value.center.value)
      : center_certificate;
  const Interval box_sqrt = kUseComputedTightSqrtCertificates
      ? fixed_sqrt_enclosure(value.value_bound)
      : box_certificate;
  const Interval center_twice = interval_integer_scale(
      2, center_sqrt);
  const Interval box_twice = interval_integer_scale(2, box_sqrt);
  const Interval input_twice = interval_integer_scale(2, value.value_bound);
  const bool domain = value.domain &&
                      fixed_sqrt_certificate(value.center.value,
                                             center_sqrt) &&
                      fixed_sqrt_certificate(value.value_bound,
                                             box_sqrt) &&
                      fixed_interval_not_zero(center_twice) &&
                      fixed_interval_not_zero(box_twice);
  if (!domain) throw std::runtime_error("fixed sqrt domain failure");

  const Interval center_d = fixed_interval_inv(center_twice);
  const FirstJet center = {
      center_sqrt,
      interval_vector_scale(center_d, value.center.gradient, counters)};

  const Interval box_d = fixed_interval_inv(box_twice);
  const Interval dd_denominator = interval_mul(
      box_twice, input_twice, counters);
  if (!fixed_interval_not_zero(dd_denominator)) {
    throw std::runtime_error("fixed sqrt second derivative domain failure");
  }
  const Interval box_dd = interval_neg(fixed_interval_inv(dd_denominator));
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(
          box_dd, interval_self_outer(value.gradient_bounds, counters),
          counters),
      interval_matrix_scale(box_d, value.hessian, counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_scaled_coordinate_sqrt_fixed(
    const IntegerVector& radii, const Interval& center_certificate,
    const Interval& box_certificate,
    const IntervalVector& center_environment,
    const IntervalVector& box_environment, std::size_t variable,
    const Rat& coefficient_value, Counters& counters) {
  if (variable >= kDimensions) {
    throw std::runtime_error("coordinate sqrt variable outside environment");
  }
  ++counters.sqrt_steps;
  const Interval center_sqrt = kUseComputedTightSqrtCertificates
      ? fixed_sqrt_enclosure(center_environment[variable])
      : center_certificate;
  const Interval box_sqrt = kUseComputedTightSqrtCertificates
      ? fixed_sqrt_enclosure(box_environment[variable])
      : box_certificate;
  const Interval center_twice = interval_integer_scale(
      2, center_sqrt);
  const Interval box_twice = interval_integer_scale(2, box_sqrt);
  const Interval input_twice = interval_integer_scale(
      2, box_environment[variable]);
  const bool domain =
      fixed_sqrt_certificate(center_environment[variable],
                             center_sqrt) &&
      fixed_sqrt_certificate(box_environment[variable], box_sqrt) &&
      fixed_interval_not_zero(center_twice) &&
      fixed_interval_not_zero(box_twice);
  if (!domain) {
    throw std::runtime_error("prepared coordinate sqrt domain failure");
  }

  const Interval dd_denominator = interval_mul(
      box_twice, input_twice, counters);
  if (!fixed_interval_not_zero(dd_denominator)) {
    throw std::runtime_error(
        "prepared coordinate sqrt second derivative domain failure");
  }
  const Interval coefficient = interval_constant(coefficient_value);
  const Interval center_d = fixed_interval_inv(center_twice);
  const Interval box_dd = interval_neg(fixed_interval_inv(dd_denominator));

  IntervalVector center_gradient = zero_vector();
  center_gradient[variable] = interval_mul(
      coefficient, center_d, counters);
  IntervalMatrix hessian = zero_matrix();
  hessian[variable][variable] = interval_mul(
      coefficient, box_dd, counters);
  const FirstJet center = {
      interval_mul(coefficient, center_sqrt, counters),
      center_gradient};
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
          interval_self_outer(value.gradient_bounds, counters),
          counters),
      interval_matrix_scale(box_d, value.hessian, counters));
  return complete_result(radii, domain, center, hessian, counters);
}

TaylorResult result_atan_fixed(const IntegerVector& radii,
                              const TaylorResult& value,
                              Counters& counters) {
  ++counters.atan_steps;
  const Interval center_denominator = interval_add(
      one_interval(), fixed_interval_square(value.center.value, counters));
  const Interval box_denominator = interval_add(
      one_interval(), fixed_interval_square(value.value_bound, counters));
  const bool arguments_in_range =
      absolute(value.center.value.lower) < kScale &&
      absolute(value.center.value.upper) < kScale &&
      absolute(value.value_bound.lower) < kScale &&
      absolute(value.value_bound.upper) < kScale;
  const bool domain = value.domain && arguments_in_range &&
                      fixed_interval_not_zero(center_denominator) &&
                      fixed_interval_not_zero(box_denominator);
  if (!domain) throw std::runtime_error("fixed atan domain failure");

  const Interval center_d = fixed_interval_inv(center_denominator);
  const FirstJet center = {
      fixed_atan_interval(value.center.value, counters),
      interval_vector_scale(center_d, value.center.gradient, counters)};

  const Interval box_d = fixed_interval_inv(box_denominator);
  const Interval box_d2 = interval_mul(box_d, box_d, counters);
  const Interval box_dd = interval_neg(interval_mul(
      interval_add(value.value_bound, value.value_bound), box_d2, counters));
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(
          box_dd, interval_self_outer(value.gradient_bounds, counters),
          counters),
      interval_matrix_scale(box_d, value.hessian, counters));
  return complete_result(radii, domain, center, hessian, counters);
}

void require_interval_contains(const Interval& candidate,
                               const Interval& reference,
                               const std::string& label) {
  if (candidate.lower > reference.lower || candidate.upper < reference.upper) {
    throw std::runtime_error("fixed kernel enclosure failure: " + label);
  }
}

void require_result_contains(const TaylorResult& candidate,
                             const TaylorResult& reference,
                             const std::string& label) {
  if (reference.domain && !candidate.domain) {
    throw std::runtime_error("fixed kernel domain failure: " + label);
  }
  require_interval_contains(candidate.center.value, reference.center.value,
                            label + "/center-value");
  require_interval_contains(candidate.value_bound, reference.value_bound,
                            label + "/value-bound");
  for (std::size_t row = 0; row < kDimensions; ++row) {
    require_interval_contains(candidate.center.gradient[row],
                              reference.center.gradient[row],
                              label + "/center-gradient");
    require_interval_contains(candidate.gradient_bounds[row],
                              reference.gradient_bounds[row],
                              label + "/gradient-bound");
    for (std::size_t column = 0; column < kDimensions; ++column) {
      require_interval_contains(candidate.hessian[row][column],
                                reference.hessian[row][column],
                                label + "/hessian");
    }
  }
}

TaylorResult result_pi_half(const IntegerVector& radii, Counters& counters) {
  return complete_result(radii, true,
                         {interval_of_q({kPiHalfLower, kPiHalfUpper}),
                          zero_vector()},
                         zero_matrix(), counters);
}

bool interval_is_zero(const Interval& value) {
  return value.lower == 0 && value.upper == 0;
}

GradientMask gradient_bit(std::size_t coordinate) {
  return static_cast<GradientMask>(1U << coordinate);
}

std::size_t symmetric_index(std::size_t row, std::size_t column) {
  if (row > column) std::swap(row, column);
  return row * kDimensions - row * (row - 1) / 2 + (column - row);
}

HessianMask hessian_bit(std::size_t row, std::size_t column) {
  return static_cast<HessianMask>(1U << symmetric_index(row, column));
}

const Interval& compact_matrix_at(const CompactMatrix& matrix,
                                  std::size_t row, std::size_t column) {
  return matrix.entries[symmetric_index(row, column)];
}

bool compact_matrix_has(const CompactMatrix& matrix,
                        std::size_t row, std::size_t column) {
  return (matrix.mask & hessian_bit(row, column)) != 0;
}

void compact_matrix_set(CompactMatrix& matrix, std::size_t row,
                        std::size_t column, const Interval& value) {
  const std::size_t index = symmetric_index(row, column);
  const HessianMask bit = static_cast<HessianMask>(1U << index);
  matrix.entries[index] = value;
  if (interval_is_zero(value)) {
    matrix.mask &= ~bit;
  } else {
    matrix.mask |= bit;
  }
}

CompactMatrix compact_matrix_from_dense(const IntervalMatrix& dense) {
  CompactMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      compact_matrix_set(result, row, column, dense[row][column]);
    }
  }
  return result;
}

CompactTaylorResult compact_from_dense(const TaylorResult& dense) {
  GradientMask center_mask = 0;
  GradientMask bounds_mask = 0;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (!interval_is_zero(dense.center.gradient[coordinate])) {
      center_mask |= gradient_bit(coordinate);
    }
    if (!interval_is_zero(dense.gradient_bounds[coordinate])) {
      bounds_mask |= gradient_bit(coordinate);
    }
  }
  return {dense.domain,
          dense.center.value,
          dense.center.gradient,
          center_mask,
          dense.value_bound,
          dense.gradient_bounds,
          bounds_mask,
          compact_matrix_from_dense(dense.hessian)};
}

IntervalVector compact_vector_neg(const IntervalVector& value,
                                  GradientMask mask) {
  IntervalVector result = zero_vector();
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if ((mask & gradient_bit(coordinate)) != 0) {
      result[coordinate] = interval_neg(value[coordinate]);
    }
  }
  return result;
}

IntervalVector compact_vector_add(const IntervalVector& left,
                                  GradientMask left_mask,
                                  const IntervalVector& right,
                                  GradientMask right_mask,
                                  GradientMask* result_mask) {
  IntervalVector result = zero_vector();
  const GradientMask candidates = left_mask | right_mask;
  *result_mask = 0;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    const GradientMask bit = gradient_bit(coordinate);
    if ((candidates & bit) == 0) continue;
    const Interval value = interval_add(left[coordinate], right[coordinate]);
    result[coordinate] = value;
    if (!interval_is_zero(value)) *result_mask |= bit;
  }
  return result;
}

IntervalVector compact_raw_vector_scale(const Interval& scalar,
                                        const IntervalVector& value,
                                        GradientMask mask,
                                        GradientMask* result_mask,
                                        Counters& counters) {
  IntervalVector result = zero_vector();
  *result_mask = 0;
  if (interval_is_zero(scalar)) return result;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    const GradientMask bit = gradient_bit(coordinate);
    if ((mask & bit) == 0) continue;
    const Interval product = raw_interval_mul(
        scalar, value[coordinate], counters);
    result[coordinate] = product;
    if (!interval_is_zero(product)) *result_mask |= bit;
  }
  return result;
}

IntervalVector compact_raw_vector_round(const IntervalVector& value,
                                        GradientMask mask,
                                        const Fixed& denominator,
                                        GradientMask* result_mask) {
  IntervalVector result = zero_vector();
  *result_mask = 0;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    const GradientMask bit = gradient_bit(coordinate);
    if ((mask & bit) == 0) continue;
    const Interval rounded = raw_interval_round(
        denominator, value[coordinate]);
    result[coordinate] = rounded;
    if (!interval_is_zero(rounded)) *result_mask |= bit;
  }
  return result;
}

IntervalVector compact_vector_scale(const Interval& scalar,
                                    const IntervalVector& value,
                                    GradientMask mask,
                                    GradientMask* result_mask,
                                    Counters& counters) {
  GradientMask raw_mask = 0;
  const IntervalVector raw = compact_raw_vector_scale(
      scalar, value, mask, &raw_mask, counters);
  return compact_raw_vector_round(raw, raw_mask, kScale, result_mask);
}

CompactMatrix compact_matrix_neg(const CompactMatrix& value) {
  CompactMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      if (compact_matrix_has(value, row, column)) {
        compact_matrix_set(result, row, column,
                           interval_neg(compact_matrix_at(value, row, column)));
      }
    }
  }
  return result;
}

CompactMatrix compact_matrix_add(const CompactMatrix& left,
                                 const CompactMatrix& right) {
  CompactMatrix result;
  const HessianMask candidates = left.mask | right.mask;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      const HessianMask bit = hessian_bit(row, column);
      if ((candidates & bit) == 0) continue;
      const Interval left_value = compact_matrix_has(left, row, column)
                                      ? compact_matrix_at(left, row, column)
                                      : zero_interval();
      const Interval right_value = compact_matrix_has(right, row, column)
                                       ? compact_matrix_at(right, row, column)
                                       : zero_interval();
      compact_matrix_set(result, row, column,
                         interval_add(left_value, right_value));
    }
  }
  return result;
}

CompactMatrix compact_raw_matrix_scale(const Interval& scalar,
                                       const CompactMatrix& value,
                                       Counters& counters) {
  CompactMatrix result;
  if (interval_is_zero(scalar)) return result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      if (!compact_matrix_has(value, row, column)) continue;
      compact_matrix_set(
          result, row, column,
          raw_interval_mul(scalar, compact_matrix_at(value, row, column),
                           counters));
    }
  }
  return result;
}

CompactMatrix compact_raw_matrix_round(const CompactMatrix& value,
                                       const Fixed& denominator) {
  CompactMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      if (!compact_matrix_has(value, row, column)) continue;
      compact_matrix_set(
          result, row, column,
          raw_interval_round(denominator,
                             compact_matrix_at(value, row, column)));
    }
  }
  return result;
}

CompactMatrix compact_matrix_scale(const Interval& scalar,
                                   const CompactMatrix& value,
                                   Counters& counters) {
  return compact_raw_matrix_round(
      compact_raw_matrix_scale(scalar, value, counters), kScale);
}

CompactMatrix compact_self_outer(const IntervalVector& value,
                                 GradientMask mask, Counters& counters) {
  CompactMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    if ((mask & gradient_bit(row)) == 0) continue;
    for (std::size_t column = row; column < kDimensions; ++column) {
      if ((mask & gradient_bit(column)) == 0) continue;
      compact_matrix_set(
          result, row, column,
          interval_mul(value[row], value[column], counters));
    }
  }
  return result;
}

Fixed compact_dot_abs_upper(const IntegerVector& radii,
                            const IntervalVector& row,
                            GradientMask mask) {
  Fixed result = 0;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if ((mask & gradient_bit(coordinate)) != 0) {
      result += radii[coordinate] * interval_abs_upper(row[coordinate]);
    }
  }
  return result;
}

Fixed compact_weighted_abs_upper(const IntegerVector& radii,
                                 const CompactMatrix& matrix) {
  Fixed result = 0;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      if (!compact_matrix_has(matrix, row, column)) continue;
      Fixed contribution = radii[row] * radii[column] *
                           interval_abs_upper(compact_matrix_at(
                               matrix, row, column));
      if (row != column) contribution *= 2;
      result += contribution;
    }
  }
  return result;
}

CompactTaylorResult compact_complete_result(
    const IntegerVector& radii, bool domain, const Interval& center_value,
    const IntervalVector& center_gradient, GradientMask center_gradient_mask,
    const CompactMatrix& hessian, Counters& counters) {
  ++counters.completed_results;
  const Fixed linear = compact_dot_abs_upper(
      radii, center_gradient, center_gradient_mask);
  const Fixed quadratic = compact_weighted_abs_upper(radii, hessian);
  const Fixed error = 2 * kScale * linear + quadratic;
  const Interval raw_value = {
      kTwoScaleSquared * center_value.lower - error,
      kTwoScaleSquared * center_value.upper + error};

  IntervalVector gradient_bounds = zero_vector();
  GradientMask gradient_bounds_mask = 0;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    Fixed variation = 0;
    for (std::size_t column = 0; column < kDimensions; ++column) {
      if (compact_matrix_has(hessian, row, column)) {
        variation += radii[column] * interval_abs_upper(
            compact_matrix_at(hessian, row, column));
      }
    }
    const GradientMask bit = gradient_bit(row);
    const Interval center = (center_gradient_mask & bit) != 0
                                ? center_gradient[row]
                                : zero_interval();
    const Interval bound = raw_interval_round(
        kScale, {kScale * center.lower - variation,
                 kScale * center.upper + variation});
    gradient_bounds[row] = bound;
    if (!interval_is_zero(bound)) gradient_bounds_mask |= bit;
  }

  return {domain,
          center_value,
          center_gradient,
          center_gradient_mask,
          raw_interval_round(kTwoScaleSquared, raw_value),
          gradient_bounds,
          gradient_bounds_mask,
          hessian};
}

CompactTaylorResult compact_complete_raw_result(
    const IntegerVector& radii, bool domain, const Interval& raw_center_value,
    const IntervalVector& raw_center_gradient,
    GradientMask raw_center_gradient_mask,
    const CompactMatrix& raw_hessian, Counters& counters) {
  GradientMask center_gradient_mask = 0;
  const IntervalVector center_gradient = compact_raw_vector_round(
      raw_center_gradient, raw_center_gradient_mask, kScale,
      &center_gradient_mask);
  return compact_complete_result(
      radii, domain, raw_interval_round(kScale, raw_center_value),
      center_gradient, center_gradient_mask,
      compact_raw_matrix_round(raw_hessian, kScale), counters);
}

CompactTaylorResult compact_result_neg(
    const IntegerVector& radii, const CompactTaylorResult& value,
    Counters& counters) {
  return compact_complete_result(
      radii, value.domain, interval_neg(value.center_value),
      compact_vector_neg(value.center_gradient, value.center_gradient_mask),
      value.center_gradient_mask, compact_matrix_neg(value.hessian), counters);
}

CompactTaylorResult compact_result_add(
    const IntegerVector& radii, const CompactTaylorResult& left,
    const CompactTaylorResult& right, Counters& counters) {
  GradientMask center_mask = 0;
  const IntervalVector center_gradient = compact_vector_add(
      left.center_gradient, left.center_gradient_mask,
      right.center_gradient, right.center_gradient_mask, &center_mask);
  return compact_complete_result(
      radii, left.domain && right.domain,
      interval_add(left.center_value, right.center_value), center_gradient,
      center_mask, compact_matrix_add(left.hessian, right.hessian), counters);
}

CompactMatrix compact_raw_product_hessian(
    const CompactTaylorResult& left, const CompactTaylorResult& right,
    Counters& counters) {
  CompactMatrix result;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      const bool left_hessian = compact_matrix_has(left.hessian, row, column);
      const bool right_hessian = compact_matrix_has(right.hessian, row, column);
      const bool left_right =
          (left.gradient_bounds_mask & gradient_bit(row)) != 0 &&
          (right.gradient_bounds_mask & gradient_bit(column)) != 0;
      const bool right_left =
          (right.gradient_bounds_mask & gradient_bit(row)) != 0 &&
          (left.gradient_bounds_mask & gradient_bit(column)) != 0;
      if (!left_hessian && !right_hessian && !left_right && !right_left) {
        continue;
      }
      const Interval first = left_hessian
          ? raw_interval_mul(right.value_bound,
                             compact_matrix_at(left.hessian, row, column),
                             counters)
          : zero_interval();
      const Interval second = left_right
          ? raw_interval_mul(left.gradient_bounds[row],
                             right.gradient_bounds[column], counters)
          : zero_interval();
      const Interval third = right_left
          ? raw_interval_mul(right.gradient_bounds[row],
                             left.gradient_bounds[column], counters)
          : zero_interval();
      const Interval fourth = right_hessian
          ? raw_interval_mul(left.value_bound,
                             compact_matrix_at(right.hessian, row, column),
                             counters)
          : zero_interval();
      compact_matrix_set(
          result, row, column,
          interval_add(interval_add(first, second),
                       interval_add(third, fourth)));
    }
  }
  return result;
}

CompactTaylorResult compact_result_mul(
    const IntegerVector& radii, const CompactTaylorResult& left,
    const CompactTaylorResult& right, Counters& counters) {
  const Interval raw_center_value = raw_interval_mul(
      left.center_value, right.center_value, counters);
  GradientMask left_scaled_mask = 0;
  GradientMask right_scaled_mask = 0;
  const IntervalVector left_scaled = compact_raw_vector_scale(
      right.center_value, left.center_gradient, left.center_gradient_mask,
      &left_scaled_mask, counters);
  const IntervalVector right_scaled = compact_raw_vector_scale(
      left.center_value, right.center_gradient, right.center_gradient_mask,
      &right_scaled_mask, counters);
  GradientMask raw_center_mask = 0;
  const IntervalVector raw_center_gradient = compact_vector_add(
      left_scaled, left_scaled_mask, right_scaled, right_scaled_mask,
      &raw_center_mask);
  return compact_complete_raw_result(
      radii, left.domain && right.domain, raw_center_value,
      raw_center_gradient, raw_center_mask,
      compact_raw_product_hessian(left, right, counters), counters);
}

CompactTaylorResult compact_result_inverse(
    const IntegerVector& radii, const CompactTaylorResult& value,
    Counters& counters) {
  ++counters.inverse_steps;
  const RationalInterval center_input = fixed_to_q(value.center_value);
  const RationalInterval box_input = fixed_to_q(value.value_bound);
  const bool domain = value.domain && rational_interval_not_zero(center_input) &&
                      rational_interval_not_zero(box_input);
  if (!domain) throw std::runtime_error("compact inverse domain failure");
  const Interval r = interval_of_q(rational_interval_inv(center_input));
  const Interval r2 = interval_mul(r, r, counters);
  GradientMask center_mask = 0;
  const IntervalVector center_gradient = compact_vector_scale(
      interval_neg(r2), value.center_gradient, value.center_gradient_mask,
      &center_mask, counters);

  const Interval box_r = interval_of_q(rational_interval_inv(box_input));
  const Interval box_r2 = interval_mul(box_r, box_r, counters);
  const Interval box_r3 = interval_mul(box_r2, box_r, counters);
  const CompactMatrix hessian = compact_matrix_add(
      compact_matrix_scale(interval_neg(box_r2), value.hessian, counters),
      compact_matrix_scale(
          interval_add(box_r3, box_r3),
          compact_self_outer(value.gradient_bounds,
                             value.gradient_bounds_mask, counters),
          counters));
  return compact_complete_result(radii, domain, r, center_gradient,
                                 center_mask, hessian, counters);
}

CompactTaylorResult compact_result_sqrt(
    const IntegerVector& radii,
    const RationalInterval& center_certificate,
    const RationalInterval& box_certificate,
    const CompactTaylorResult& value, Counters& counters) {
  ++counters.sqrt_steps;
  const RationalInterval center_input = fixed_to_q(value.center_value);
  const RationalInterval box_input = fixed_to_q(value.value_bound);
  const RationalInterval center_twice = rational_interval_add(
      center_certificate, center_certificate);
  const RationalInterval box_twice = rational_interval_add(
      box_certificate, box_certificate);
  const RationalInterval input_twice = rational_interval_add(
      box_input, box_input);
  const bool domain = value.domain &&
                      sqrt_certificate(center_input, center_certificate) &&
                      sqrt_certificate(box_input, box_certificate) &&
                      rational_interval_not_zero(center_twice) &&
                      rational_interval_not_zero(box_twice) &&
                      rational_interval_not_zero(
                          rational_interval_mul(box_twice, input_twice));
  if (!domain) throw std::runtime_error("compact sqrt domain failure");

  const Interval center_result = interval_of_q(center_certificate);
  const RationalInterval center_d_q = rational_interval_inv(center_twice);
  const Interval center_d = interval_of_q(center_d_q);
  GradientMask center_mask = 0;
  const IntervalVector center_gradient = compact_vector_scale(
      center_d, value.center_gradient, value.center_gradient_mask,
      &center_mask, counters);

  const Interval box_d = interval_of_q(rational_interval_inv(box_twice));
  const RationalInterval box_dd_q = rational_interval_neg(
      rational_interval_inv(rational_interval_mul(box_twice, input_twice)));
  const Interval box_dd = interval_of_q(box_dd_q);
  const CompactMatrix hessian = compact_matrix_add(
      compact_matrix_scale(
          box_dd,
          compact_self_outer(value.gradient_bounds,
                             value.gradient_bounds_mask, counters),
          counters),
      compact_matrix_scale(box_d, value.hessian, counters));
  return compact_complete_result(radii, domain, center_result,
                                 center_gradient, center_mask, hessian,
                                 counters);
}

CompactTaylorResult compact_result_atan(
    const IntegerVector& radii, const CompactTaylorResult& value,
    Counters& counters) {
  ++counters.atan_steps;
  const RationalInterval center_input = fixed_to_q(value.center_value);
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
  if (!domain) throw std::runtime_error("compact atan domain failure");

  const Interval center_d = interval_of_q(
      rational_interval_inv(center_denominator));
  GradientMask center_mask = 0;
  const IntervalVector center_gradient = compact_vector_scale(
      center_d, value.center_gradient, value.center_gradient_mask,
      &center_mask, counters);

  const RationalInterval box_d_q = rational_interval_inv(box_denominator);
  const RationalInterval box_dd_q = rational_interval_neg(
      rational_interval_mul(
          rational_interval_add(box_input, box_input),
          rational_interval_mul(box_d_q, box_d_q)));
  const Interval box_d = interval_of_q(box_d_q);
  const Interval box_dd = interval_of_q(box_dd_q);
  const CompactMatrix hessian = compact_matrix_add(
      compact_matrix_scale(
          box_dd,
          compact_self_outer(value.gradient_bounds,
                             value.gradient_bounds_mask, counters),
          counters),
      compact_matrix_scale(box_d, value.hessian, counters));
  return compact_complete_result(
      radii, domain, interval_of_q(atan_interval(center_input)),
      center_gradient, center_mask, hessian, counters);
}

CompactTaylorResult compact_result_pi_half(
    const IntegerVector& radii, Counters& counters) {
  return compact_complete_result(
      radii, true, interval_of_q({kPiHalfLower, kPiHalfUpper}),
      zero_vector(), 0, CompactMatrix(), counters);
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

Program::SimplePolynomial classify_simple_polynomial(
    const Program& program, std::size_t payload) {
  using Kind = Program::SimplePolynomialKind;
  std::vector<Program::SimplePolynomial> stack;
  const std::vector<std::size_t> instructions =
      decode_list(program, payload, "simple polynomial preparation");
  for (const std::size_t instruction_index : instructions) {
    const Node& instruction = node_at(program, instruction_index);
    if (instruction.is_pair) {
      const Integer tag = require_numeral(
          program, instruction.left, "simple polynomial tag");
      Program::SimplePolynomial value;
      if (tag == 0) {
        value.kind = Kind::kConstant;
        value.constant = decode_q(program, instruction.right);
      } else if (tag == 1) {
        const Integer variable = require_numeral(
            program, instruction.right, "simple polynomial variable");
        if (variable >= 0 && variable < static_cast<long>(kDimensions)) {
          value.kind = Kind::kVariable;
          value.variable = variable.get_ui();
        }
      } else {
        throw std::runtime_error(
            "unknown simple polynomial pair instruction");
      }
      stack.push_back(value);
      continue;
    }

    const unsigned long opcode = instruction.numeral.get_ui();
    if (opcode == 2 || opcode == 5) {
      if (stack.empty()) {
        throw std::runtime_error("simple polynomial stack underflow");
      }
      Program::SimplePolynomial value = stack.back();
      stack.pop_back();
      if (value.kind == Kind::kConstant) {
        if (opcode == 2) {
          value.constant = -value.constant;
        } else {
          value.constant *= value.constant;
        }
      } else {
        value.kind = Kind::kUnknown;
      }
      stack.push_back(value);
    } else if (opcode == 3 || opcode == 4) {
      if (stack.size() < 2) {
        throw std::runtime_error("simple polynomial stack underflow");
      }
      const Program::SimplePolynomial right = stack.back();
      stack.pop_back();
      Program::SimplePolynomial left = stack.back();
      stack.pop_back();
      if (left.kind == Kind::kConstant && right.kind == Kind::kConstant) {
        if (opcode == 3) {
          left.constant += right.constant;
        } else {
          left.constant *= right.constant;
        }
      } else {
        left.kind = Kind::kUnknown;
      }
      stack.push_back(left);
    } else {
      throw std::runtime_error(
          "unknown simple polynomial scalar instruction");
    }
  }
  if (stack.size() != 1) {
    throw std::runtime_error("simple polynomial result stack drift");
  }
  return stack.back();
}

void prepare_simple_polynomials(Program& program) {
  program.prepared_simple_polynomials.assign(
      program.instructions.size(), Program::SimplePolynomial());
  for (std::size_t outer_index = 0;
       outer_index < program.instructions.size(); ++outer_index) {
    const Node& instruction = node_at(
        program, program.instructions[outer_index]);
    if (!instruction.is_pair) continue;
    const Integer tag = require_numeral(
        program, instruction.left, "analytic preparation tag");
    if (tag == 0) {
      program.prepared_simple_polynomials[outer_index] =
          classify_simple_polynomial(program, instruction.right);
    }
  }
}

void prepare_coordinate_sqrt_terms(Program& program) {
  using Kind = Program::SimplePolynomialKind;
  if (program.prepared_simple_polynomials.size() !=
      program.instructions.size()) {
    throw std::runtime_error(
        "coordinate sqrt preparation requires simple polynomials");
  }
  program.prepared_coordinate_sqrt_terms.assign(
      program.instructions.size(), Program::CoordinateSqrtTerm());
  std::size_t sqrt_slot = 0;
  for (std::size_t outer_index = 0;
       outer_index < program.instructions.size(); ++outer_index) {
    const Node& instruction = node_at(
        program, program.instructions[outer_index]);
    if (instruction.is_pair) {
      const Integer tag = require_numeral(
          program, instruction.left, "coordinate sqrt preparation tag");
      if (tag == 1) ++sqrt_slot;
    }
    if (outer_index + 3 >= program.instructions.size()) continue;

    const Program::SimplePolynomial& input =
        program.prepared_simple_polynomials[outer_index];
    const Program::SimplePolynomial& coefficient =
        program.prepared_simple_polynomials[outer_index + 2];
    if (input.kind != Kind::kVariable ||
        coefficient.kind != Kind::kConstant) {
      continue;
    }
    const Node& sqrt_instruction = node_at(
        program, program.instructions[outer_index + 1]);
    const Node& multiply_instruction = node_at(
        program, program.instructions[outer_index + 3]);
    if (!sqrt_instruction.is_pair || multiply_instruction.is_pair) continue;
    const Integer sqrt_tag = require_numeral(
        program, sqrt_instruction.left, "coordinate sqrt operation tag");
    if (sqrt_tag != 1 || multiply_instruction.numeral != 4) continue;

    Program::CoordinateSqrtTerm term;
    term.active = true;
    term.variable = input.variable;
    term.coefficient = coefficient.constant;
    term.sqrt_slot = sqrt_slot;
    program.prepared_coordinate_sqrt_terms[outer_index] = term;
  }
}

void prepare_dihedral_chain(Program& program) {
  if (program.instructions.size() <= 38) {
    throw std::runtime_error("dihedral source chain is missing");
  }
  const auto require_outer_opcode = [&program](std::size_t outer_index,
                                                unsigned long opcode) {
    const Node& instruction = node_at(
        program, program.instructions.at(outer_index));
    if (instruction.is_pair || instruction.numeral != opcode) {
      throw std::runtime_error("dihedral source opcode drift at outer " +
                               std::to_string(outer_index));
    }
  };
  const auto require_outer_tag = [&program](std::size_t outer_index,
                                             long tag) {
    const Node& instruction = node_at(
        program, program.instructions.at(outer_index));
    if (!instruction.is_pair ||
        require_numeral(program, instruction.left,
                        "dihedral source tag") != tag) {
      throw std::runtime_error("dihedral source tag drift at outer " +
                               std::to_string(outer_index));
    }
  };
  require_outer_opcode(31, 8);
  require_outer_tag(32, 0);
  require_outer_tag(33, 0);
  require_outer_tag(34, 1);
  require_outer_opcode(35, 6);
  require_outer_opcode(36, 4);
  require_outer_opcode(37, 7);
  require_outer_opcode(38, 3);
  program.prepared_dihedral_chain = true;
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

Interval delta_gradient_component(std::size_t coordinate,
                                  const IntervalVector& x,
                                  Counters& counters) {
  const auto product = [&counters](const Interval& left,
                                    const Interval& right) {
    return interval_mul(left, right, counters);
  };
  switch (coordinate) {
    case 0:
      return interval_sum({
          interval_integer_scale(-2, product(x[0], x[3])),
          product(x[1], x[3]), product(x[1], x[4]),
          interval_neg(product(x[1], x[5])), product(x[2], x[3]),
          interval_neg(product(x[2], x[4])), product(x[2], x[5]),
          interval_neg(product(x[3], x[3])), product(x[3], x[4]),
          product(x[3], x[5])});
    case 1:
      return interval_sum({
          product(x[0], x[3]), product(x[0], x[4]),
          interval_neg(product(x[0], x[5])),
          interval_integer_scale(-2, product(x[1], x[4])),
          interval_neg(product(x[2], x[3])), product(x[2], x[4]),
          product(x[2], x[5]), product(x[3], x[4]),
          interval_neg(product(x[4], x[4])), product(x[4], x[5])});
    case 2:
      return interval_sum({
          product(x[0], x[3]), interval_neg(product(x[0], x[4])),
          product(x[0], x[5]), interval_neg(product(x[1], x[3])),
          product(x[1], x[4]), product(x[1], x[5]),
          interval_integer_scale(-2, product(x[2], x[5])),
          product(x[3], x[5]), product(x[4], x[5]),
          interval_neg(product(x[5], x[5]))});
    case 3:
      return interval_sum({
          interval_neg(product(x[0], x[0])), product(x[0], x[1]),
          product(x[0], x[2]),
          interval_integer_scale(-2, product(x[0], x[3])),
          product(x[0], x[4]), product(x[0], x[5]),
          interval_neg(product(x[1], x[2])), product(x[1], x[4]),
          product(x[2], x[5]), interval_neg(product(x[4], x[5]))});
    case 4:
      return interval_sum({
          product(x[0], x[1]), interval_neg(product(x[0], x[2])),
          product(x[0], x[3]), interval_neg(product(x[1], x[1])),
          product(x[1], x[2]), product(x[1], x[3]),
          interval_integer_scale(-2, product(x[1], x[4])),
          product(x[1], x[5]), product(x[2], x[5]),
          interval_neg(product(x[3], x[5]))});
    case 5:
      return interval_sum({
          interval_neg(product(x[0], x[1])), product(x[0], x[2]),
          product(x[0], x[3]), product(x[1], x[2]),
          product(x[1], x[4]), interval_neg(product(x[2], x[2])),
          product(x[2], x[3]), product(x[2], x[4]),
          interval_integer_scale(-2, product(x[2], x[5])),
          interval_neg(product(x[3], x[4]))});
    default:
      throw std::runtime_error("delta gradient coordinate out of range");
  }
}

Interval delta_gradient_component_block_rounded(
    std::size_t coordinate, const IntervalVector& x, Counters& counters) {
  const auto product = [&counters](const Interval& left,
                                    const Interval& right) {
    return raw_interval_mul(left, right, counters);
  };
  Interval raw;
  switch (coordinate) {
    case 0:
      raw = interval_sum({
          interval_integer_scale(-2, product(x[0], x[3])),
          product(x[1], x[3]), product(x[1], x[4]),
          interval_neg(product(x[1], x[5])), product(x[2], x[3]),
          interval_neg(product(x[2], x[4])), product(x[2], x[5]),
          interval_neg(product(x[3], x[3])), product(x[3], x[4]),
          product(x[3], x[5])});
      break;
    case 1:
      raw = interval_sum({
          product(x[0], x[3]), product(x[0], x[4]),
          interval_neg(product(x[0], x[5])),
          interval_integer_scale(-2, product(x[1], x[4])),
          interval_neg(product(x[2], x[3])), product(x[2], x[4]),
          product(x[2], x[5]), product(x[3], x[4]),
          interval_neg(product(x[4], x[4])), product(x[4], x[5])});
      break;
    case 2:
      raw = interval_sum({
          product(x[0], x[3]), interval_neg(product(x[0], x[4])),
          product(x[0], x[5]), interval_neg(product(x[1], x[3])),
          product(x[1], x[4]), product(x[1], x[5]),
          interval_integer_scale(-2, product(x[2], x[5])),
          product(x[3], x[5]), product(x[4], x[5]),
          interval_neg(product(x[5], x[5]))});
      break;
    case 3:
      raw = interval_sum({
          interval_neg(product(x[0], x[0])), product(x[0], x[1]),
          product(x[0], x[2]),
          interval_integer_scale(-2, product(x[0], x[3])),
          product(x[0], x[4]), product(x[0], x[5]),
          interval_neg(product(x[1], x[2])), product(x[1], x[4]),
          product(x[2], x[5]), interval_neg(product(x[4], x[5]))});
      break;
    case 4:
      raw = interval_sum({
          product(x[0], x[1]), interval_neg(product(x[0], x[2])),
          product(x[0], x[3]), interval_neg(product(x[1], x[1])),
          product(x[1], x[2]), product(x[1], x[3]),
          interval_integer_scale(-2, product(x[1], x[4])),
          product(x[1], x[5]), product(x[2], x[5]),
          interval_neg(product(x[3], x[5]))});
      break;
    case 5:
      raw = interval_sum({
          interval_neg(product(x[0], x[1])), product(x[0], x[2]),
          product(x[0], x[3]), product(x[1], x[2]),
          product(x[1], x[4]), interval_neg(product(x[2], x[2])),
          product(x[2], x[3]), product(x[2], x[4]),
          interval_integer_scale(-2, product(x[2], x[5])),
          interval_neg(product(x[3], x[4]))});
      break;
    default:
      throw std::runtime_error("delta gradient coordinate out of range");
  }
  return raw_interval_round(kScale, raw);
}

Interval delta_value_block_rounded(const IntervalVector& x,
                                   Counters& counters) {
  const Interval first_linear = interval_sum({
      interval_neg(x[0]), x[1], x[2], interval_neg(x[3]), x[4], x[5]});
  const Interval second_linear = interval_sum({
      x[0], interval_neg(x[1]), x[2], x[3], interval_neg(x[4]), x[5]});
  const Interval third_linear = interval_sum({
      x[0], x[1], interval_neg(x[2]), x[3], x[4], interval_neg(x[5])});
  const auto cubic = [&counters](const Interval& first,
                                  const Interval& second,
                                  const Interval& third) {
    return raw_interval_mul(
        raw_interval_mul(first, second, counters), third, counters);
  };
  const Interval raw = interval_sum({
      cubic(x[0], x[3], first_linear),
      cubic(x[1], x[4], second_linear),
      cubic(x[2], x[5], third_linear),
      interval_neg(cubic(x[1], x[2], x[3])),
      interval_neg(cubic(x[0], x[2], x[4])),
      interval_neg(cubic(x[0], x[1], x[5])),
      interval_neg(cubic(x[3], x[4], x[5]))});
  return raw_interval_round(kScale * kScale, raw);
}

IntervalVector monotone_extremum_environment(
    const IntervalVector& box, const IntervalVector& derivatives,
    bool upper) {
  IntervalVector result = box;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (derivatives[coordinate].lower >= 0) {
      const Fixed endpoint = upper ? box[coordinate].upper
                                   : box[coordinate].lower;
      result[coordinate] = {endpoint, endpoint};
    } else if (derivatives[coordinate].upper <= 0) {
      const Fixed endpoint = upper ? box[coordinate].lower
                                   : box[coordinate].upper;
      result[coordinate] = {endpoint, endpoint};
    }
  }
  return result;
}

SecondOrderBox delta_full_sign_directed(const IntervalVector& box,
                                        Counters& counters,
                                        bool block_rounding = false) {
  SecondOrderBox result;
  result.hessian = delta_hessian(box);
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    const IntervalVector lower_environment = monotone_extremum_environment(
        box, result.hessian[coordinate], false);
    const IntervalVector upper_environment = monotone_extremum_environment(
        box, result.hessian[coordinate], true);
    const Interval lower = block_rounding
        ? delta_gradient_component_block_rounded(
              coordinate, lower_environment, counters)
        : delta_gradient_component(
              coordinate, lower_environment, counters);
    const Interval upper = block_rounding
        ? delta_gradient_component_block_rounded(
              coordinate, upper_environment, counters)
        : delta_gradient_component(
              coordinate, upper_environment, counters);
    result.gradient[coordinate] = {lower.lower, upper.upper};
    if (result.gradient[coordinate].lower >
        result.gradient[coordinate].upper) {
      throw std::runtime_error("sign-directed delta gradient is empty");
    }
  }
  const IntervalVector lower_environment = monotone_extremum_environment(
      box, result.gradient, false);
  const IntervalVector upper_environment = monotone_extremum_environment(
      box, result.gradient, true);
  const Interval lower = block_rounding
      ? delta_value_block_rounded(lower_environment, counters)
      : delta_value(lower_environment, counters);
  const Interval upper = block_rounding
      ? delta_value_block_rounded(upper_environment, counters)
      : delta_value(upper_environment, counters);
  result.value = {lower.lower, upper.upper};
  if (result.value.lower > result.value.upper) {
    throw std::runtime_error("sign-directed delta value is empty");
  }
  return result;
}

bool interval_is_subset(const Interval& candidate,
                        const Interval& reference) {
  return candidate.lower >= reference.lower &&
         candidate.upper <= reference.upper;
}

void require_interval_contains(const Interval& candidate,
                               const Interval& reference,
                               const std::string& label);

void run_delta_full_diagnostics(const std::vector<Job>& jobs) {
  std::vector<SecondOrderBox> generics;
  generics.reserve(jobs.size());
  Counters generic_counters;
  const auto generic_begin = std::chrono::steady_clock::now();
  for (const Job& job : jobs) {
    IntervalVector box;
    for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
      box[coordinate] = interval_of_q(
          {job.lower[coordinate], job.upper[coordinate]});
    }
    generics.push_back({
        delta_value(box, generic_counters),
        delta_gradient_from_products(
            polynomial_pair_products(box, generic_counters)),
        delta_hessian(box)});
  }
  const auto generic_end = std::chrono::steady_clock::now();

  std::vector<SecondOrderBox> candidates;
  candidates.reserve(jobs.size());
  Counters candidate_counters;
  const auto candidate_begin = std::chrono::steady_clock::now();
  for (const Job& job : jobs) {
    IntervalVector box;
    for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
      box[coordinate] = interval_of_q(
          {job.lower[coordinate], job.upper[coordinate]});
    }
    candidates.push_back(delta_full_sign_directed(box, candidate_counters));
  }
  const auto candidate_end = std::chrono::steady_clock::now();

  Counters validation_counters;
  std::size_t narrower_values = 0;
  std::size_t narrower_gradients = 0;
  std::size_t vertex_checks = 0;
  Fixed candidate_value_width_sum = 0;
  Fixed generic_value_width_sum = 0;
  Fixed candidate_gradient_width_sum = 0;
  Fixed generic_gradient_width_sum = 0;
  const auto validation_begin = std::chrono::steady_clock::now();
  for (std::size_t job_index = 0; job_index < jobs.size(); ++job_index) {
    const Job& job = jobs[job_index];
    const SecondOrderBox& generic = generics[job_index];
    const SecondOrderBox& candidate = candidates[job_index];
    IntervalVector box;
    for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
      box[coordinate] = interval_of_q(
          {job.lower[coordinate], job.upper[coordinate]});
    }

    if (!interval_is_subset(candidate.value, generic.value)) {
      throw std::runtime_error(
          "sign-directed delta value is not inside generic enclosure");
    }
    candidate_value_width_sum += candidate.value.upper - candidate.value.lower;
    generic_value_width_sum += generic.value.upper - generic.value.lower;
    if (candidate.value.lower > generic.value.lower ||
        candidate.value.upper < generic.value.upper) {
      ++narrower_values;
    }
    for (std::size_t row = 0; row < kDimensions; ++row) {
      if (!interval_is_subset(candidate.gradient[row],
                              generic.gradient[row])) {
        throw std::runtime_error(
            "sign-directed delta gradient is not inside generic enclosure");
      }
      candidate_gradient_width_sum +=
          candidate.gradient[row].upper - candidate.gradient[row].lower;
      generic_gradient_width_sum +=
          generic.gradient[row].upper - generic.gradient[row].lower;
      if (candidate.gradient[row].lower > generic.gradient[row].lower ||
          candidate.gradient[row].upper < generic.gradient[row].upper) {
        ++narrower_gradients;
      }
      for (std::size_t column = 0; column < kDimensions; ++column) {
        if (candidate.hessian[row][column].lower !=
                generic.hessian[row][column].lower ||
            candidate.hessian[row][column].upper !=
                generic.hessian[row][column].upper) {
          throw std::runtime_error("delta Hessian formula drift");
        }
      }
    }

    for (std::size_t vertex = 0;
         vertex < (static_cast<std::size_t>(1) << kDimensions); ++vertex) {
      IntervalVector point;
      for (std::size_t coordinate = 0;
           coordinate < kDimensions; ++coordinate) {
        const Fixed endpoint =
            (vertex & (static_cast<std::size_t>(1) << coordinate))
                ? box[coordinate].upper
                : box[coordinate].lower;
        point[coordinate] = {endpoint, endpoint};
      }
      require_interval_contains(
          candidate.value, delta_value(point, validation_counters),
          "sign-directed-delta/value-vertex");
      for (std::size_t coordinate = 0;
           coordinate < kDimensions; ++coordinate) {
        require_interval_contains(
            candidate.gradient[coordinate],
            delta_gradient_component(
                coordinate, point, validation_counters),
            "sign-directed-delta/gradient-vertex");
      }
      const IntervalMatrix point_hessian = delta_hessian(point);
      for (std::size_t row = 0; row < kDimensions; ++row) {
        for (std::size_t column = 0; column < kDimensions; ++column) {
          require_interval_contains(
              candidate.hessian[row][column], point_hessian[row][column],
              "sign-directed-delta/hessian-vertex");
        }
      }
      ++vertex_checks;
    }
  }
  const auto validation_end = std::chrono::steady_clock::now();
  const double generic_seconds = std::chrono::duration<double>(
      generic_end - generic_begin).count();
  const double candidate_seconds = std::chrono::duration<double>(
      candidate_end - candidate_begin).count();
  const double validation_seconds = std::chrono::duration<double>(
      validation_end - validation_begin).count();
  std::cout << "CANDLE_NL_NATIVE_DELTA_FULL_SUMMARY"
            << " cells=" << jobs.size()
            << " generic_seconds=" << generic_seconds
            << " candidate_seconds=" << candidate_seconds
            << " validation_seconds=" << validation_seconds
            << " generic_interval_products="
            << generic_counters.interval_products
            << " candidate_interval_products="
            << candidate_counters.interval_products
            << " validation_interval_products="
            << validation_counters.interval_products
            << " narrower_values=" << narrower_values
            << " narrower_gradients=" << narrower_gradients
            << " gradient_entries=" << jobs.size() * kDimensions
            << " vertex_checks=" << vertex_checks
            << " candidate_value_width_units="
            << integer_of_fixed(candidate_value_width_sum).get_str()
            << " generic_value_width_units="
            << integer_of_fixed(generic_value_width_sum).get_str()
            << " candidate_gradient_width_units="
            << integer_of_fixed(candidate_gradient_width_sum).get_str()
            << " generic_gradient_width_units="
            << integer_of_fixed(generic_gradient_width_sum).get_str()
            << " status=DEVELOPMENT_NON_RELEASE\n";
}

Interval delta_x4_value(const IntervalVector& x, Counters& counters) {
  const Interval linear = interval_sum({
      interval_neg(x[0]), x[1], x[2], interval_neg(x[3]), x[4], x[5]});
  return interval_sum({
      interval_neg(interval_mul(x[1], x[2], counters)),
      interval_neg(interval_mul(x[0], x[3], counters)),
      interval_mul(x[1], x[4], counters),
      interval_mul(x[2], x[5], counters),
      interval_neg(interval_mul(x[4], x[5], counters)),
      interval_mul(x[0], linear, counters)});
}

IntervalVector delta_x4_gradient(const IntervalVector& x) {
  IntervalVector gradient;
  gradient[0] = interval_sum({
      interval_integer_scale(-2, x[0]), x[1], x[2],
      interval_integer_scale(-2, x[3]), x[4], x[5]});
  gradient[1] = interval_sum({x[0], interval_neg(x[2]), x[4]});
  gradient[2] = interval_sum({x[0], interval_neg(x[1]), x[5]});
  gradient[3] = interval_integer_scale(-2, x[0]);
  gradient[4] = interval_sum({x[0], x[1], interval_neg(x[5])});
  gradient[5] = interval_sum({x[0], x[2], interval_neg(x[4])});
  return gradient;
}

IntervalMatrix delta_x4_hessian() {
  IntervalMatrix hessian = zero_matrix();
  const Interval one = one_interval();
  const auto set_symmetric = [&hessian](std::size_t row,
                                        std::size_t column,
                                        const Interval& value) {
    hessian[row][column] = value;
    hessian[column][row] = value;
  };
  set_symmetric(0, 0, interval_integer_scale(-2, one));
  set_symmetric(0, 1, one);
  set_symmetric(0, 2, one);
  set_symmetric(0, 3, interval_integer_scale(-2, one));
  set_symmetric(0, 4, one);
  set_symmetric(0, 5, one);
  set_symmetric(1, 2, interval_neg(one));
  set_symmetric(1, 4, one);
  set_symmetric(2, 5, one);
  set_symmetric(4, 5, interval_neg(one));
  return hessian;
}

TaylorResult evaluate_neg_delta_x4_specialized(
    const IntegerVector& radii,
    const IntervalVector& center_environment, Counters& counters) {
  const FirstJet center = {
      interval_neg(delta_x4_value(center_environment, counters)),
      vector_neg(delta_x4_gradient(center_environment))};
  return complete_result(radii, true, center,
                         matrix_neg(delta_x4_hessian()), counters);
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
    const Fixed variation = dot_abs_upper(
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

Interval neg_delta_x4_monotone_box_value(
    const IntervalVector& box_environment, const Interval& fallback,
    Counters& counters) {
  const IntervalVector gradient = vector_neg(
      delta_x4_gradient(box_environment));
  IntervalVector minimum_point;
  IntervalVector maximum_point;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (gradient[coordinate].lower >= 0) {
      minimum_point[coordinate] = {
          box_environment[coordinate].lower,
          box_environment[coordinate].lower};
      maximum_point[coordinate] = {
          box_environment[coordinate].upper,
          box_environment[coordinate].upper};
    } else if (gradient[coordinate].upper <= 0) {
      minimum_point[coordinate] = {
          box_environment[coordinate].upper,
          box_environment[coordinate].upper};
      maximum_point[coordinate] = {
          box_environment[coordinate].lower,
          box_environment[coordinate].lower};
    } else {
      return fallback;
    }
  }
  const Interval minimum = interval_neg(
      delta_x4_value(minimum_point, counters));
  const Interval maximum = interval_neg(
      delta_x4_value(maximum_point, counters));
  return {minimum.lower, maximum.upper};
}

struct ValueGradient {
  Interval value;
  IntervalVector gradient;
};

ValueGradient optimized_triangle_u(
    const IntervalVector& box_environment,
    const std::array<std::size_t, 3>& variables, Counters& counters,
    bool block_rounding = false) {
  std::array<Interval, 3> x = {
      box_environment[variables[0]], box_environment[variables[1]],
      box_environment[variables[2]]};
  std::array<Interval, 3> local_gradient = {
      interval_integer_scale(
          2, interval_sum({interval_neg(x[0]), x[1], x[2]})),
      interval_integer_scale(
          2, interval_sum({x[0], interval_neg(x[1]), x[2]})),
      interval_integer_scale(
          2, interval_sum({x[0], x[1], interval_neg(x[2])}))};

  std::array<Interval, 3> upper_negative;
  std::array<Interval, 3> upper_positive;
  std::array<Interval, 3> lower_negative;
  std::array<Interval, 3> lower_positive;
  for (std::size_t index = 0; index < 3; ++index) {
    const Interval lower_point = {x[index].lower, x[index].lower};
    const Interval upper_point = {x[index].upper, x[index].upper};
    upper_negative[index] = lower_point;
    upper_positive[index] = upper_point;
    lower_negative[index] = upper_point;
    lower_positive[index] = lower_point;
    if (local_gradient[index].lower >= 0) {
      upper_negative[index] = upper_point;
      lower_negative[index] = lower_point;
    } else if (local_gradient[index].upper <= 0) {
      upper_positive[index] = lower_point;
      lower_positive[index] = upper_point;
    }
  }

  const auto value_formula = [&counters, block_rounding](
      const std::array<Interval, 3>& negative,
      const std::array<Interval, 3>& positive) {
    const auto product = [&counters, block_rounding](
        const Interval& left, const Interval& right) {
      return block_rounding
          ? raw_interval_mul(left, right, counters)
          : interval_mul(left, right, counters);
    };
    const Interval value = interval_sum({
        interval_neg(product(negative[0], negative[0])),
        interval_neg(product(negative[1], negative[1])),
        interval_neg(product(negative[2], negative[2])),
        interval_integer_scale(2, product(positive[0], positive[1])),
        interval_integer_scale(2, product(positive[1], positive[2])),
        interval_integer_scale(2, product(positive[2], positive[0]))});
    return block_rounding ? raw_interval_round(kScale, value) : value;
  };
  const Interval lower_value = value_formula(
      lower_negative, lower_positive);
  const Interval upper_value = value_formula(
      upper_negative, upper_positive);

  IntervalVector gradient = zero_vector();
  for (std::size_t index = 0; index < 3; ++index) {
    gradient[variables[index]] = local_gradient[index];
  }
  return {{lower_value.lower, upper_value.upper}, gradient};
}

SecondOrderBox delta_x4_full_sign_directed(
    const IntervalVector& box, Counters& counters,
    bool block_rounding = false) {
  SecondOrderBox result;
  result.gradient = delta_x4_gradient(box);
  result.hessian = delta_x4_hessian();
  const IntervalVector lower_environment = monotone_extremum_environment(
      box, result.gradient, false);
  const IntervalVector upper_environment = monotone_extremum_environment(
      box, result.gradient, true);
  const auto value = [&counters, block_rounding](
      const IntervalVector& environment) {
    if (!block_rounding) {
      return delta_x4_value(environment, counters);
    }
    const auto product = [&counters](const Interval& left,
                                      const Interval& right) {
      return raw_interval_mul(left, right, counters);
    };
    const Interval linear = interval_sum({
        interval_neg(environment[0]), environment[1], environment[2],
        interval_neg(environment[3]), environment[4], environment[5]});
    const Interval raw = interval_sum({
        interval_neg(product(environment[1], environment[2])),
        interval_neg(product(environment[0], environment[3])),
        product(environment[1], environment[4]),
        product(environment[2], environment[5]),
        interval_neg(product(environment[4], environment[5])),
        product(environment[0], linear)});
    return raw_interval_round(kScale, raw);
  };
  const Interval lower = value(lower_environment);
  const Interval upper = value(upper_environment);
  result.value = {lower.lower, upper.upper};
  if (result.value.lower > result.value.upper) {
    throw std::runtime_error("sign-directed delta-x4 value is empty");
  }
  return result;
}

SecondOrderBox delta_full_direct(const IntervalVector& environment,
                                 Counters& counters) {
  return {delta_value(environment, counters),
          delta_gradient_from_products(
              polynomial_pair_products(environment, counters)),
          delta_hessian(environment)};
}

SecondOrderBox delta_x4_full_direct(const IntervalVector& environment,
                                    Counters& counters) {
  return {delta_x4_value(environment, counters),
          delta_x4_gradient(environment), delta_x4_hessian()};
}

SecondOrderBox second_order_sqrt(const SecondOrderBox& input,
                                 Counters& counters) {
  if (input.value.lower <= 0) {
    throw std::runtime_error("second-order square-root domain failure");
  }
  ++counters.sqrt_steps;
  SecondOrderBox result;
  result.value = fixed_sqrt_enclosure(input.value);
  const Interval derivative = fixed_interval_inv(
      interval_integer_scale(2, result.value));
  result.gradient = interval_vector_scale(
      derivative, input.gradient, counters);
  const Interval logarithmic_derivative = interval_neg(
      fixed_interval_inv(interval_integer_scale(2, input.value)));
  for (std::size_t row = 0; row < kDimensions; ++row) {
    const Interval scaled_row = interval_mul(
        logarithmic_derivative, input.gradient[row], counters);
    for (std::size_t column = row;
         column < kDimensions; ++column) {
      const Interval inside = interval_add(
          interval_mul(input.gradient[column], scaled_row, counters),
          input.hessian[row][column]);
      const Interval value = interval_mul(derivative, inside, counters);
      result.hessian[row][column] = value;
      result.hessian[column][row] = value;
    }
  }
  return result;
}

SecondOrderBox historical_dihedral_second_order(
    const IntervalVector& environment, bool use_sign_directed_bounds,
    Counters& counters) {
  const SecondOrderBox delta = use_sign_directed_bounds
      ? delta_full_sign_directed(
            environment, counters, kUseHistoricalBlockRounding)
      : delta_full_direct(environment, counters);
  const SecondOrderBox root_delta = second_order_sqrt(delta, counters);
  const SecondOrderBox delta_x4 = use_sign_directed_bounds
      ? delta_x4_full_sign_directed(
            environment, counters, kUseHistoricalBlockRounding)
      : delta_x4_full_direct(environment, counters);
  const ValueGradient u126 = optimized_triangle_u(
      environment, std::array<std::size_t, 3>{{0, 1, 5}}, counters,
      kUseHistoricalBlockRounding);
  const ValueGradient u135 = optimized_triangle_u(
      environment, std::array<std::size_t, 3>{{0, 2, 4}}, counters,
      kUseHistoricalBlockRounding);
  if (u126.value.lower <= 0 || u135.value.lower <= 0) {
    throw std::runtime_error("historical dihedral U domain failure");
  }

  ++counters.sqrt_steps;
  const Interval root_four_x0 = fixed_sqrt_enclosure(
      interval_integer_scale(4, environment[0]));
  const Interval b = interval_mul(
      root_delta.value, root_four_x0, counters);
  if (!fixed_interval_not_zero(b)) {
    throw std::runtime_error("historical dihedral denominator failure");
  }
  const Interval two_over_root_four_x0 = interval_mul(
      interval_integer_scale(2, one_interval()),
      fixed_interval_inv(root_four_x0), counters);

  IntervalVector b_gradient = interval_vector_scale(
      root_four_x0, root_delta.gradient, counters);
  b_gradient[0] = interval_add(
      b_gradient[0],
      interval_mul(root_delta.value, two_over_root_four_x0, counters));

  IntervalMatrix b_hessian = interval_matrix_scale(
      root_four_x0, root_delta.hessian, counters);
  for (std::size_t coordinate = 1;
       coordinate < kDimensions; ++coordinate) {
    const Interval correction = interval_mul(
        root_delta.gradient[coordinate], two_over_root_four_x0, counters);
    b_hessian[0][coordinate] = interval_add(
        b_hessian[0][coordinate], correction);
    b_hessian[coordinate][0] = b_hessian[0][coordinate];
  }
  const Interval twice_first_correction = interval_integer_scale(
      2, interval_mul(root_delta.gradient[0],
                      two_over_root_four_x0, counters));
  const Interval diagonal_denominator = interval_integer_scale(
      2, environment[0]);
  if (!fixed_interval_not_zero(diagonal_denominator)) {
    throw std::runtime_error(
        "historical dihedral first-coordinate domain failure");
  }
  const Interval diagonal_subtraction = interval_mul(
      interval_mul(root_delta.value, two_over_root_four_x0, counters),
      fixed_interval_inv(diagonal_denominator), counters);
  b_hessian[0][0] = interval_add(
      b_hessian[0][0],
      interval_add(twice_first_correction,
                   interval_neg(diagonal_subtraction)));

  IntervalVector c;
  for (std::size_t coordinate = 0;
       coordinate < kDimensions; ++coordinate) {
    c[coordinate] = interval_add(
        interval_neg(interval_mul(
            delta_x4.gradient[coordinate], b, counters)),
        interval_mul(delta_x4.value, b_gradient[coordinate], counters));
  }
  const Interval u_product = interval_mul(
      u126.value, u135.value, counters);
  if (!fixed_interval_not_zero(u_product)) {
    throw std::runtime_error("historical dihedral U product failure");
  }
  const Interval reciprocal_u = fixed_interval_inv(u_product);

  SecondOrderBox result;
  result.gradient = interval_vector_scale(reciprocal_u, c, counters);
  const Interval two_root_delta = interval_integer_scale(
      2, root_delta.value);
  if (!fixed_interval_not_zero(two_root_delta)) {
    throw std::runtime_error("historical dihedral delta root failure");
  }
  result.gradient[3] = interval_mul(
      root_four_x0, fixed_interval_inv(two_root_delta), counters);

  IntervalVector logarithmic_u_gradient;
  const Interval reciprocal_u126 = fixed_interval_inv(u126.value);
  const Interval reciprocal_u135 = fixed_interval_inv(u135.value);
  for (std::size_t coordinate = 0;
       coordinate < kDimensions; ++coordinate) {
    logarithmic_u_gradient[coordinate] = interval_add(
        interval_mul(u126.gradient[coordinate], reciprocal_u126, counters),
        interval_mul(u135.gradient[coordinate], reciprocal_u135, counters));
  }

  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row;
         column < kDimensions; ++column) {
      Interval identity;
      if (row == column) {
        identity = interval_add(
            interval_neg(interval_mul(
                b, delta_x4.hessian[row][column], counters)),
            interval_mul(delta_x4.value,
                         b_hessian[row][column], counters));
      } else {
        identity = interval_sum({
            interval_neg(interval_mul(
                b, delta_x4.hessian[row][column], counters)),
            interval_neg(interval_mul(
                delta_x4.gradient[row], b_gradient[column], counters)),
            interval_mul(delta_x4.gradient[column],
                         b_gradient[row], counters),
            interval_mul(delta_x4.value,
                         b_hessian[row][column], counters)});
      }
      const Interval value = interval_add(
          interval_mul(reciprocal_u, identity, counters),
          interval_neg(interval_mul(
              result.gradient[row],
              logarithmic_u_gradient[column], counters)));
      result.hessian[row][column] = value;
      result.hessian[column][row] = value;
    }
  }

  const Interval quotient = interval_mul(
      interval_neg(delta_x4.value), fixed_interval_inv(b), counters);
  if (absolute(quotient.lower) >= kScale ||
      absolute(quotient.upper) >= kScale) {
    throw std::runtime_error("historical dihedral atan domain failure");
  }
  ++counters.atan_steps;
  result.value = interval_add(
      interval_of_q({kPiHalfLower, kPiHalfUpper}),
      fixed_atan_interval(quotient, counters));
  return result;
}

TaylorResult evaluate_historical_dihedral(
    const IntegerVector& radii,
    const IntervalVector& center_environment,
    const IntervalVector& box_environment,
    Counters& counters) {
  const SecondOrderBox center = historical_dihedral_second_order(
      center_environment, false, counters);
  const SecondOrderBox box = historical_dihedral_second_order(
      box_environment, true, counters);
  return complete_result(
      radii, true, {center.value, center.gradient}, box.hessian, counters);
}

TaylorResult evaluate_dihedral_chain_specialized(
    const IntegerVector& radii, const IntervalVector& center_environment,
    const IntervalVector& box_environment,
    const Interval& center_sqrt_certificate,
    const Interval& box_sqrt_certificate, Counters& counters) {
  const TaylorResult numerator = evaluate_neg_delta_x4_specialized(
      radii, center_environment, counters);
  const TaylorResult radicand = evaluate_four_x1_delta_specialized(
      radii, center_environment, box_environment, counters);

  ++counters.sqrt_steps;
  ++counters.inverse_steps;
  const bool sqrt_domain =
      fixed_sqrt_certificate(radicand.center.value,
                             center_sqrt_certificate) &&
      fixed_sqrt_certificate(radicand.value_bound,
                             box_sqrt_certificate) &&
      fixed_interval_not_zero(center_sqrt_certificate) &&
      fixed_interval_not_zero(box_sqrt_certificate);
  if (!sqrt_domain) {
    throw std::runtime_error("prepared dihedral square-root domain failure");
  }

  const Interval center_inverse_root = fixed_interval_inv(
      center_sqrt_certificate);
  const Interval box_inverse_root = fixed_interval_inv(box_sqrt_certificate);
  const Interval center_inverse_root2 = interval_mul(
      center_inverse_root, center_inverse_root, counters);
  const Interval center_inverse_root3 = interval_mul(
      center_inverse_root2, center_inverse_root, counters);
  const Interval box_inverse_root2 = interval_mul(
      box_inverse_root, box_inverse_root, counters);
  const Interval box_inverse_root3 = interval_mul(
      box_inverse_root2, box_inverse_root, counters);
  const Interval box_inverse_root5 = interval_mul(
      interval_mul(box_inverse_root3, box_inverse_root, counters),
      box_inverse_root, counters);
  const Interval center_inverse_root_d = interval_mul(
      fixed_rational_constant(-1, 2), center_inverse_root3, counters);
  const Interval box_inverse_root_d = interval_mul(
      fixed_rational_constant(-1, 2), box_inverse_root3, counters);
  const Interval box_inverse_root_dd = interval_mul(
      fixed_rational_constant(3, 4), box_inverse_root5, counters);

  const FirstJet inverse_root_center = {
      center_inverse_root,
      interval_vector_scale(center_inverse_root_d,
                            radicand.center.gradient, counters)};
  const IntervalVector inverse_root_box_gradient = interval_vector_scale(
      box_inverse_root_d, radicand.gradient_bounds, counters);
  const IntervalMatrix inverse_root_hessian = matrix_add(
      interval_matrix_scale(
          box_inverse_root_dd,
          interval_self_outer(radicand.gradient_bounds, counters), counters),
      interval_matrix_scale(
          box_inverse_root_d, radicand.hessian, counters));
  const PolynomialJet inverse_root = {
      inverse_root_center, box_inverse_root, inverse_root_box_gradient,
      inverse_root_hessian};
  const PolynomialJet numerator_jet = {
      numerator.center, numerator.value_bound, numerator.gradient_bounds,
      numerator.hessian};
  const PolynomialJet quotient = polynomial_mul(
      numerator_jet, inverse_root, counters);

  ++counters.atan_steps;
  const bool atan_domain =
      absolute(quotient.center.value.lower) < kScale &&
      absolute(quotient.center.value.upper) < kScale &&
      absolute(quotient.box_value.lower) < kScale &&
      absolute(quotient.box_value.upper) < kScale;
  if (!atan_domain) {
    throw std::runtime_error("prepared dihedral arctangent domain failure");
  }
  const Interval center_denominator = interval_add(
      one_interval(), fixed_interval_square(quotient.center.value, counters));
  const Interval box_denominator = interval_add(
      one_interval(), fixed_interval_square(quotient.box_value, counters));
  const Interval center_atan_d = fixed_interval_inv(center_denominator);
  const Interval box_atan_d = fixed_interval_inv(box_denominator);
  const Interval box_atan_d2 = interval_mul(
      box_atan_d, box_atan_d, counters);
  const Interval box_atan_dd = interval_neg(interval_mul(
      interval_add(quotient.box_value, quotient.box_value),
      box_atan_d2, counters));
  const FirstJet center = {
      interval_add(interval_of_q({kPiHalfLower, kPiHalfUpper}),
                   fixed_atan_interval(quotient.center.value, counters)),
      interval_vector_scale(
          center_atan_d, quotient.center.gradient, counters)};
  const IntervalMatrix hessian = matrix_add(
      interval_matrix_scale(
          box_atan_dd,
          interval_self_outer(quotient.box_gradient, counters), counters),
      interval_matrix_scale(box_atan_d, quotient.box_hessian, counters));
  return complete_result(radii, true, center, hessian, counters);
}

TaylorResult evaluate_dihedral_identities_specialized(
    const IntegerVector& radii, const IntervalVector& center_environment,
    const IntervalVector& box_environment,
    const Interval& center_sqrt_certificate,
    const Interval& box_sqrt_certificate, Counters& counters) {
  const TaylorResult numerator = evaluate_neg_delta_x4_specialized(
      radii, center_environment, counters);
  const TaylorResult radicand = evaluate_four_x1_delta_specialized(
      radii, center_environment, box_environment, counters);
  const Interval numerator_box_value = neg_delta_x4_monotone_box_value(
      box_environment, numerator.value_bound, counters);
  const IntervalVector numerator_box_gradient = vector_neg(
      delta_x4_gradient(box_environment));
  const Interval center_sqrt =
      (kUseTightDihedralSqrtCertificates ||
       kUseComputedTightSqrtCertificates)
      ? fixed_sqrt_enclosure(radicand.center.value)
      : center_sqrt_certificate;
  const Interval box_sqrt =
      (kUseTightDihedralSqrtCertificates ||
       kUseComputedTightSqrtCertificates)
      ? fixed_sqrt_enclosure(radicand.value_bound)
      : box_sqrt_certificate;
  ++counters.sqrt_steps;
  ++counters.inverse_steps;
  ++counters.atan_steps;
  const bool sqrt_domain =
      fixed_sqrt_certificate(radicand.center.value,
                             center_sqrt) &&
      fixed_sqrt_certificate(radicand.value_bound,
                             box_sqrt) &&
      fixed_interval_not_zero(center_sqrt) &&
      fixed_interval_not_zero(box_sqrt);
  if (!sqrt_domain) {
    throw std::runtime_error(
        "specialized dihedral square-root domain failure");
  }

  const Interval center_sqrt_d = fixed_interval_inv(
      interval_integer_scale(2, center_sqrt));
  const Interval box_sqrt_d = fixed_interval_inv(
      interval_integer_scale(2, box_sqrt));
  const Interval box_sqrt_dd_denominator = interval_mul(
      interval_integer_scale(2, box_sqrt),
      interval_integer_scale(2, radicand.value_bound), counters);
  if (!fixed_interval_not_zero(box_sqrt_dd_denominator)) {
    throw std::runtime_error(
        "specialized dihedral sqrt Hessian domain failure");
  }
  const Interval box_sqrt_dd = interval_neg(
      fixed_interval_inv(box_sqrt_dd_denominator));
  const IntervalVector center_sqrt_gradient = interval_vector_scale(
      center_sqrt_d, radicand.center.gradient, counters);
  const IntervalVector box_sqrt_gradient = interval_vector_scale(
      box_sqrt_d, radicand.gradient_bounds, counters);
  const IntervalMatrix box_sqrt_hessian = matrix_add(
      interval_matrix_scale(
          box_sqrt_dd,
          interval_self_outer(radicand.gradient_bounds, counters), counters),
      interval_matrix_scale(box_sqrt_d, radicand.hessian, counters));

  if (!fixed_interval_not_zero(radicand.center.value) ||
      !fixed_interval_not_zero(radicand.value_bound)) {
    throw std::runtime_error("specialized dihedral radicand domain failure");
  }
  // The historical route uses 1 / (U126 * U135), with the identity
  // U126*U135 = 4*x0*delta + delta_x4^2.  The numerator is -delta_x4,
  // so its square supplies the second summand without changing the sign.
  const Interval center_denominator = interval_add(
      radicand.center.value,
      fixed_interval_square(numerator.center.value, counters));
  Interval box_denominator = interval_add(
      radicand.value_bound,
      fixed_interval_square(numerator_box_value, counters));
  ValueGradient u126;
  ValueGradient u135;
  if (kUseOptimizedDihedralUBounds) {
    u126 = optimized_triangle_u(
        box_environment, std::array<std::size_t, 3>{{0, 1, 5}}, counters);
    u135 = optimized_triangle_u(
        box_environment, std::array<std::size_t, 3>{{0, 2, 4}}, counters);
    box_denominator = interval_mul(u126.value, u135.value, counters);
  }
  if (!fixed_interval_not_zero(center_denominator) ||
      !fixed_interval_not_zero(box_denominator)) {
    throw std::runtime_error(
        "specialized dihedral denominator domain failure");
  }
  const Interval center_ru = fixed_interval_inv(center_denominator);
  const Interval box_ru = fixed_interval_inv(box_denominator);

  IntervalVector center_c;
  IntervalVector box_c;
  IntervalVector center_gradient;
  IntervalVector box_gradient;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    center_c[coordinate] = interval_add(
        interval_mul(numerator.center.gradient[coordinate],
                     center_sqrt, counters),
        interval_neg(interval_mul(numerator.center.value,
                                  center_sqrt_gradient[coordinate],
                                  counters)));
    box_c[coordinate] = interval_add(
        interval_mul(numerator_box_gradient[coordinate],
                     box_sqrt, counters),
        interval_neg(interval_mul(numerator_box_value,
                                  box_sqrt_gradient[coordinate],
                                  counters)));
    center_gradient[coordinate] = interval_mul(
        center_c[coordinate], center_ru, counters);
    box_gradient[coordinate] = interval_mul(
        box_c[coordinate], box_ru, counters);
  }
  // Historical setDihedral uses the exact opposite-edge identity
  // d(dih)/dx3 = sqrt(4*x0)/(2*sqrt(delta)) = 2*x0/sqrt(4*x0*delta).
  center_gradient[3] = interval_mul(
      interval_integer_scale(2, center_environment[0]),
      fixed_interval_inv(center_sqrt), counters);
  box_gradient[3] = interval_mul(
      interval_integer_scale(2, box_environment[0]),
      fixed_interval_inv(box_sqrt), counters);

  IntervalVector logarithmic_u_gradient;
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (kUseOptimizedDihedralUBounds) {
      logarithmic_u_gradient[coordinate] = interval_add(
          interval_mul(u126.gradient[coordinate],
                       fixed_interval_inv(u126.value), counters),
          interval_mul(u135.gradient[coordinate],
                       fixed_interval_inv(u135.value), counters));
    } else {
      const Interval denominator_gradient = interval_add(
          radicand.gradient_bounds[coordinate],
          interval_integer_scale(
              2, interval_mul(numerator_box_value,
                              numerator_box_gradient[coordinate], counters)));
      logarithmic_u_gradient[coordinate] = interval_mul(
          denominator_gradient, box_ru, counters);
    }
  }

  IntervalMatrix hessian = zero_matrix();
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      const Interval identity_numerator = interval_sum({
          interval_mul(box_sqrt,
                       numerator.hessian[row][column], counters),
          interval_mul(numerator_box_gradient[row],
                       box_sqrt_gradient[column], counters),
          interval_neg(interval_mul(numerator_box_gradient[column],
                                    box_sqrt_gradient[row], counters)),
          interval_neg(interval_mul(numerator_box_value,
                                    box_sqrt_hessian[row][column],
                                    counters))});
      const Interval value = interval_add(
          interval_mul(box_ru, identity_numerator, counters),
          interval_neg(interval_mul(box_gradient[row],
                                    logarithmic_u_gradient[column],
                                    counters)));
      hessian[row][column] = value;
      hessian[column][row] = value;
    }
  }

  const Interval center_quotient = interval_mul(
      numerator.center.value,
      fixed_interval_inv(center_sqrt), counters);
  if (absolute(center_quotient.lower) >= kScale ||
      absolute(center_quotient.upper) >= kScale) {
    throw std::runtime_error(
        "specialized dihedral arctangent domain failure");
  }
  const FirstJet center = {
      interval_add(interval_of_q({kPiHalfLower, kPiHalfUpper}),
                   fixed_atan_interval(center_quotient, counters)),
      center_gradient};
  return complete_result(radii, true, center, hessian, counters);
}

struct Evaluation {
  Rat upper;
  Counters counters;
};

TaylorResult evaluate_dihedral_identity_diagnostic(const Job& job) {
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
  if (kUseHistoricalDihedral) {
    return evaluate_historical_dihedral(
        radii, center_environment, box_environment, counters);
  }
  return evaluate_dihedral_identities_specialized(
      radii, center_environment, box_environment,
      job.fixed_center_certificates[6], job.fixed_box_certificates[6],
      counters);
}

void print_dihedral_identity_diagnostic(std::size_t index,
                                        const TaylorResult& result) {
  const RationalInterval value = fixed_to_q(result.value_bound);
  const RationalInterval center = fixed_to_q(result.center.value);
  std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_ANGLE_DIAGNOSTIC"
            << " index=" << index
            << " lower=" << value.lower.get_str()
            << " upper=" << value.upper.get_str()
            << " center=" << center.lower.get_str() << ":"
            << center.upper.get_str()
            << " center_gradient=";
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (coordinate != 0) std::cout << ",";
    const RationalInterval entry = fixed_to_q(
        result.center.gradient[coordinate]);
    std::cout << entry.lower.get_str() << ":" << entry.upper.get_str();
  }
  std::cout << " hessian=";
  bool first = true;
  for (std::size_t row = 0; row < kDimensions; ++row) {
    for (std::size_t column = row; column < kDimensions; ++column) {
      if (!first) std::cout << ",";
      first = false;
      const RationalInterval entry = fixed_to_q(result.hessian[row][column]);
      std::cout << entry.lower.get_str() << ":" << entry.upper.get_str();
    }
  }
  std::cout << "\n";
}

void precompute_tight_sqrt_certificates(
    const Program& program, std::vector<Job>& jobs) {
  if (!program.prepared_dihedral_chain) {
    throw std::runtime_error(
        "tight square-root preparation requires authenticated dihedral "
        "source shape");
  }
  std::array<bool, kSqrtSlots> seen{};
  for (const Program::CoordinateSqrtTerm& term :
       program.prepared_coordinate_sqrt_terms) {
    if (!term.active) continue;
    if (term.sqrt_slot >= kSqrtSlots || seen[term.sqrt_slot]) {
      throw std::runtime_error(
          "tight square-root preparation slot drift");
    }
    seen[term.sqrt_slot] = true;
  }
  for (std::size_t slot = 0; slot < 6; ++slot) {
    if (!seen[slot]) {
      throw std::runtime_error(
          "tight square-root preparation missing coordinate slot");
    }
  }
  seen[6] = true;

  for (Job& job : jobs) {
    IntervalVector center_environment;
    IntervalVector box_environment;
    IntegerVector radii;
    for (std::size_t coordinate = 0;
         coordinate < kDimensions; ++coordinate) {
      const Rat midpoint =
          (job.lower[coordinate] + job.upper[coordinate]) / 2;
      const Rat radius =
          (job.upper[coordinate] - job.lower[coordinate]) / 2;
      center_environment[coordinate] = interval_constant(midpoint);
      box_environment[coordinate] = interval_of_q(
          {job.lower[coordinate], job.upper[coordinate]});
      radii[coordinate] = ceil_scaled(radius);
    }

    for (const Program::CoordinateSqrtTerm& term :
         program.prepared_coordinate_sqrt_terms) {
      if (!term.active) continue;
      job.fixed_center_certificates[term.sqrt_slot] =
          fixed_sqrt_enclosure(center_environment[term.variable]);
      job.fixed_box_certificates[term.sqrt_slot] =
          fixed_sqrt_enclosure(box_environment[term.variable]);
    }

    Counters counters;
    const TaylorResult radicand = evaluate_four_x1_delta_specialized(
        radii, center_environment, box_environment, counters);
    job.fixed_center_certificates[6] =
        fixed_sqrt_enclosure(radicand.center.value);
    job.fixed_box_certificates[6] =
        fixed_sqrt_enclosure(radicand.value_bound);
  }
}

void add_counters(Counters& total, const Counters& value) {
  total.interval_products += value.interval_products;
  total.skipped_zero_products += value.skipped_zero_products;
  total.completed_results += value.completed_results;
  total.polynomial_steps += value.polynomial_steps;
  total.outer_steps += value.outer_steps;
  total.sqrt_steps += value.sqrt_steps;
  total.inverse_steps += value.inverse_steps;
  total.atan_steps += value.atan_steps;
}

Counters subtract_counters(const Counters& value, const Counters& baseline) {
  return {value.interval_products - baseline.interval_products,
          value.skipped_zero_products - baseline.skipped_zero_products,
          value.completed_results - baseline.completed_results,
          value.polynomial_steps - baseline.polynomial_steps,
          value.outer_steps - baseline.outer_steps,
          value.sqrt_steps - baseline.sqrt_steps,
          value.inverse_steps - baseline.inverse_steps,
          value.atan_steps - baseline.atan_steps};
}

void record_rounding_profile(std::vector<RoundingProfile>* profiles,
                             std::size_t profile_index,
                             const std::string& label,
                             std::uint64_t floor_before,
                             std::uint64_t ceil_before,
                             std::chrono::steady_clock::time_point begin) {
  if (profiles == nullptr) return;
  RoundingProfile& profile = profiles->at(profile_index);
  if (profile.observations == 0) {
    profile.label = label;
  } else if (profile.label != label) {
    throw std::runtime_error("rounding profile label drift");
  }
  profile.floor_quotients += kFloorFixedQuotientCalls - floor_before;
  profile.ceil_quotients += kCeilFixedQuotientCalls - ceil_before;
  profile.nanoseconds += static_cast<std::uint64_t>(
      std::chrono::duration_cast<std::chrono::nanoseconds>(
          std::chrono::steady_clock::now() - begin).count());
  ++profile.observations;
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
                        int fused_polynomial_outer_index,
                        int fused_polynomial_max_steps,
                        bool direct_delta_x4,
                        std::vector<InstructionProfile>* profiles,
                        std::vector<RoundingProfile>* rounding_profiles) {
  std::uint64_t setup_floor_before = 0;
  std::uint64_t setup_ceil_before = 0;
  std::chrono::steady_clock::time_point setup_begin;
  if (rounding_profiles != nullptr) {
    setup_floor_before = kFloorFixedQuotientCalls;
    setup_ceil_before = kCeilFixedQuotientCalls;
    setup_begin = std::chrono::steady_clock::now();
  }
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
  if (rounding_profiles != nullptr) {
    record_rounding_profile(rounding_profiles, 0, "job_setup",
                            setup_floor_before, setup_ceil_before, setup_begin);
  }

  Counters counters;
  std::vector<TaylorResult> stack;
  std::size_t sqrt_slot = 0;
  bool direct_delta_x4_used = false;
  for (std::size_t outer_index = 0;
       outer_index < program.instructions.size(); ++outer_index) {
    const std::size_t profile_outer_index = outer_index;
    std::uint64_t rounding_floor_before = 0;
    std::uint64_t rounding_ceil_before = 0;
    std::chrono::steady_clock::time_point rounding_begin;
    if (rounding_profiles != nullptr) {
      rounding_floor_before = kFloorFixedQuotientCalls;
      rounding_ceil_before = kCeilFixedQuotientCalls;
      rounding_begin = std::chrono::steady_clock::now();
    }
    std::string rounding_label;
    const Program::CoordinateSqrtTerm* coordinate_sqrt_term =
        program.prepared_coordinate_sqrt_terms.empty()
            ? nullptr
            : &program.prepared_coordinate_sqrt_terms.at(outer_index);
    if (kUsePreparedCoordinateSqrtTerms &&
        coordinate_sqrt_term != nullptr && coordinate_sqrt_term->active) {
      if (sqrt_slot != coordinate_sqrt_term->sqrt_slot ||
          sqrt_slot >= kSqrtSlots) {
        throw std::runtime_error("prepared coordinate sqrt slot drift");
      }
      const TaylorResult candidate = result_scaled_coordinate_sqrt_fixed(
          radii, job.fixed_center_certificates[sqrt_slot],
          job.fixed_box_certificates[sqrt_slot], center_environment,
          box_environment, coordinate_sqrt_term->variable,
          coordinate_sqrt_term->coefficient, counters);
      if (kVerifyFixedKernelEnclosures) {
        Counters reference_counters;
        const TaylorResult variable = result_variable(
            radii, center_environment, coordinate_sqrt_term->variable,
            reference_counters);
        const TaylorResult root = result_sqrt(
            radii, job.center_certificates[sqrt_slot],
            job.box_certificates[sqrt_slot], variable, reference_counters);
        const TaylorResult coefficient = result_constant(
            radii, coordinate_sqrt_term->coefficient, reference_counters);
        const TaylorResult reference = result_mul(
            radii, root, coefficient, reference_counters);
        require_result_contains(
            candidate, reference, "prepared-coordinate-sqrt");
      }
      stack.push_back(candidate);
      ++sqrt_slot;
      counters.outer_steps += 4;
      if (rounding_profiles != nullptr) {
        record_rounding_profile(rounding_profiles, outer_index + 1,
                                "prepared_coordinate_sqrt",
                                rounding_floor_before, rounding_ceil_before,
                                rounding_begin);
      }
      outer_index += 3;
      continue;
    }
    if (kUseHistoricalDihedral && outer_index == 31) {
      if (!program.prepared_dihedral_chain || sqrt_slot != 6 ||
          sqrt_slot >= kSqrtSlots) {
        throw std::runtime_error("historical dihedral source/slot drift");
      }
      stack.push_back(evaluate_historical_dihedral(
          radii, center_environment, box_environment, counters));
      ++sqrt_slot;
      counters.outer_steps += 8;
      direct_delta_x4_used = true;
      if (rounding_profiles != nullptr) {
        record_rounding_profile(rounding_profiles, outer_index + 1,
                                "historical_dihedral",
                                rounding_floor_before, rounding_ceil_before,
                                rounding_begin);
      }
      outer_index += 7;
      continue;
    }
    if (kUseSpecializedDihedralIdentities && outer_index == 31) {
      if (!program.prepared_dihedral_chain || sqrt_slot != 6 ||
          sqrt_slot >= kSqrtSlots) {
        throw std::runtime_error("specialized dihedral source/slot drift");
      }
      const TaylorResult candidate = evaluate_dihedral_identities_specialized(
          radii, center_environment, box_environment,
          job.fixed_center_certificates[sqrt_slot],
          job.fixed_box_certificates[sqrt_slot], counters);
      stack.push_back(candidate);
      ++sqrt_slot;
      counters.outer_steps += 8;
      direct_delta_x4_used = true;
      if (rounding_profiles != nullptr) {
        record_rounding_profile(rounding_profiles, outer_index + 1,
                                "specialized_dihedral",
                                rounding_floor_before, rounding_ceil_before,
                                rounding_begin);
      }
      outer_index += 7;
      continue;
    }
    if (kUsePreparedDihedralChain && outer_index == 31) {
      if (!program.prepared_dihedral_chain || sqrt_slot != 6 ||
          sqrt_slot >= kSqrtSlots) {
        throw std::runtime_error("prepared dihedral source/slot drift");
      }
      const TaylorResult candidate = evaluate_dihedral_chain_specialized(
          radii, center_environment, box_environment,
          job.fixed_center_certificates[sqrt_slot],
          job.fixed_box_certificates[sqrt_slot], counters);
      if (kVerifyFixedKernelEnclosures) {
        Counters reference_counters;
        const TaylorResult pi_half = result_pi_half(
            radii, reference_counters);
        const TaylorResult numerator = evaluate_neg_delta_x4_specialized(
            radii, center_environment, reference_counters);
        const TaylorResult radicand = evaluate_four_x1_delta_specialized(
            radii, center_environment, box_environment, reference_counters);
        const TaylorResult root = result_sqrt(
            radii, job.center_certificates[sqrt_slot],
            job.box_certificates[sqrt_slot], radicand, reference_counters);
        const TaylorResult inverse = result_inverse(
            radii, root, reference_counters);
        const TaylorResult quotient = result_mul(
            radii, numerator, inverse, reference_counters);
        const TaylorResult angle = result_atan(
            radii, quotient, reference_counters);
        const TaylorResult reference = result_add(
            radii, pi_half, angle, reference_counters);
        require_result_contains(candidate, reference,
                                "prepared-dihedral-chain");
      }
      stack.push_back(candidate);
      ++sqrt_slot;
      counters.outer_steps += 8;
      direct_delta_x4_used = true;
      if (rounding_profiles != nullptr) {
        record_rounding_profile(rounding_profiles, outer_index + 1,
                                "prepared_dihedral_chain",
                                rounding_floor_before, rounding_ceil_before,
                                rounding_begin);
      }
      outer_index += 7;
      continue;
    }
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
        const Program::SimplePolynomial* prepared =
            program.prepared_simple_polynomials.empty()
                ? nullptr
                : &program.prepared_simple_polynomials.at(outer_index);
        const bool use_fused_polynomial =
            polynomial_mode == PolynomialMode::kFusedAll ||
            ((polynomial_mode == PolynomialMode::kFusedDeltaX4 ||
              polynomial_mode == PolynomialMode::kSpecializedAngle) &&
             polynomial_steps == 39) ||
            static_cast<int>(outer_index) == fused_polynomial_outer_index ||
            (fused_polynomial_max_steps >= 0 &&
             polynomial_steps <=
                 static_cast<std::size_t>(fused_polynomial_max_steps));
        // The pinned case-10173 source payload at outer index 32 is
        // -delta_x4, not delta_x4.  Do not dispatch merely by program length.
        if (kUsePreparedSimplePolynomials && prepared != nullptr &&
            prepared->kind == Program::SimplePolynomialKind::kConstant) {
          stack.push_back(result_constant(
              radii, prepared->constant, counters));
        } else if (kUsePreparedSimplePolynomials && prepared != nullptr &&
                   prepared->kind == Program::SimplePolynomialKind::kVariable) {
          stack.push_back(result_variable(
              radii, center_environment, prepared->variable, counters));
        } else if (direct_delta_x4 && outer_index == 32 &&
                   polynomial_steps == 39) {
          stack.push_back(evaluate_neg_delta_x4_specialized(
              radii, center_environment, counters));
          direct_delta_x4_used = true;
        } else if (polynomial_mode == PolynomialMode::kSpecializedAngle &&
                   outer_index == 33 && polynomial_steps == 85) {
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
        if (kUseFixedSqrtInverseKernels) {
          const TaylorResult candidate = result_sqrt_fixed(
              radii, job.fixed_center_certificates[sqrt_slot],
              job.fixed_box_certificates[sqrt_slot], value, counters);
          if (kVerifyFixedKernelEnclosures) {
            Counters reference_counters;
            const TaylorResult reference = result_sqrt(
                radii, job.center_certificates[sqrt_slot],
                job.box_certificates[sqrt_slot], value, reference_counters);
            require_result_contains(candidate, reference, "sqrt");
          }
          stack.push_back(candidate);
        } else {
          stack.push_back(result_sqrt(
              radii, job.center_certificates[sqrt_slot],
              job.box_certificates[sqrt_slot], value, counters));
        }
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
        if (opcode == 6) {
          if (kUseFixedSqrtInverseKernels) {
            const TaylorResult candidate =
                result_inverse_fixed(radii, value, counters);
            if (kVerifyFixedKernelEnclosures) {
              Counters reference_counters;
              const TaylorResult reference =
                  result_inverse(radii, value, reference_counters);
              require_result_contains(candidate, reference, "inverse");
            }
            stack.push_back(candidate);
          } else {
            stack.push_back(result_inverse(radii, value, counters));
          }
        }
        if (opcode == 7) {
          if (kUseFixedAtanKernel) {
            const TaylorResult candidate =
                result_atan_fixed(radii, value, counters);
            if (kVerifyFixedKernelEnclosures) {
              Counters reference_counters;
              const TaylorResult reference =
                  result_atan(radii, value, reference_counters);
              require_result_contains(candidate, reference, "atan");
            }
            stack.push_back(candidate);
          } else {
            stack.push_back(result_atan(radii, value, counters));
          }
        }
      } else if (opcode == 3 || opcode == 4) {
        if (stack.size() < 2) throw std::runtime_error("analytic stack underflow");
        if (opcode == 3 && kFuseConsecutiveAdds) {
          std::size_t add_count = 1;
          while (outer_index + add_count < program.instructions.size()) {
            const Node& next = node_at(
                program, program.instructions[outer_index + add_count]);
            if (next.is_pair || next.numeral.get_ui() != 3) break;
            ++add_count;
          }
          if (stack.size() < add_count + 1) {
            throw std::runtime_error("fused add stack underflow");
          }
          TaylorResult sum = stack.back();
          stack.pop_back();
          for (std::size_t add_index = 0; add_index < add_count;
               ++add_index) {
            const TaylorResult left = stack.back();
            stack.pop_back();
            sum.domain = left.domain && sum.domain;
            sum.center = {
                interval_add(left.center.value, sum.center.value),
                vector_add(left.center.gradient, sum.center.gradient)};
            sum.hessian = matrix_add(left.hessian, sum.hessian);
          }
          stack.push_back(complete_result(
              radii, sum.domain, sum.center, sum.hessian, counters));
          counters.outer_steps += add_count - 1;
          outer_index += add_count - 1;
          if (rounding_profiles != nullptr) {
            rounding_label = "fused_add:" + std::to_string(add_count);
          }
        } else {
          TaylorResult right = stack.back();
          stack.pop_back();
          TaylorResult left = stack.back();
          stack.pop_back();
          stack.push_back(opcode == 3
                              ? result_add(radii, left, right, counters)
                              : result_mul(radii, left, right, counters));
        }
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
    if (rounding_profiles != nullptr) {
      if (rounding_label.empty()) {
        rounding_label = instruction_label(
            program, program.instructions[profile_outer_index]);
      }
      record_rounding_profile(
          rounding_profiles, profile_outer_index + 1, rounding_label,
          rounding_floor_before, rounding_ceil_before, rounding_begin);
    }
  }
  if (direct_delta_x4 && !direct_delta_x4_used) {
    throw std::runtime_error("negated delta_x4 source position drift");
  }
  if (sqrt_slot != kSqrtSlots || stack.size() != 1 || !stack.back().domain) {
    throw std::runtime_error("final analytic result shape/domain drift");
  }
  return {normalized_rat(integer_of_fixed(stack.back().value_bound.upper),
                         integer_of_fixed(kScale)),
          counters};
}

Evaluation evaluate_job_compact(const Program& program, const Job& job,
                                PolynomialMode polynomial_mode,
                                int fused_polynomial_outer_index,
                                int fused_polynomial_max_steps,
                                bool direct_delta_x4) {
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
  std::vector<CompactTaylorResult> stack;
  std::size_t sqrt_slot = 0;
  bool direct_delta_x4_used = false;
  for (std::size_t outer_index = 0;
       outer_index < program.instructions.size(); ++outer_index) {
    ++counters.outer_steps;
    const std::size_t instruction_index = program.instructions[outer_index];
    const Node& instruction = node_at(program, instruction_index);
    if (instruction.is_pair) {
      const Integer tag = require_numeral(
          program, instruction.left, "compact analytic tag");
      if (tag == 0) {
        const std::size_t polynomial_steps = decode_list(
            program, instruction.right,
            "compact polynomial mode selection").size();
        const bool use_fused_polynomial =
            polynomial_mode == PolynomialMode::kFusedAll ||
            ((polynomial_mode == PolynomialMode::kFusedDeltaX4 ||
              polynomial_mode == PolynomialMode::kSpecializedAngle) &&
             polynomial_steps == 39) ||
            static_cast<int>(outer_index) == fused_polynomial_outer_index ||
            (fused_polynomial_max_steps >= 0 &&
             polynomial_steps <=
                 static_cast<std::size_t>(fused_polynomial_max_steps));
        TaylorResult dense;
        // The pinned case-10173 source payload at outer index 32 is
        // -delta_x4, not delta_x4.  Do not dispatch merely by program length.
        if (direct_delta_x4 && outer_index == 32 && polynomial_steps == 39) {
          dense = evaluate_neg_delta_x4_specialized(
              radii, center_environment, counters);
          direct_delta_x4_used = true;
        } else if (polynomial_mode == PolynomialMode::kSpecializedAngle &&
                   outer_index == 33 && polynomial_steps == 85) {
          dense = evaluate_four_x1_delta_specialized(
              radii, center_environment, box_environment, counters);
        } else {
          dense = use_fused_polynomial
                      ? evaluate_polynomial_fused(
                            program, instruction.right, radii,
                            center_environment, box_environment, counters)
                      : evaluate_polynomial(
                            program, instruction.right, radii,
                            center_environment, counters);
        }
        stack.push_back(compact_from_dense(dense));
      } else if (tag == 1) {
        if (sqrt_slot >= kSqrtSlots || stack.empty()) {
          throw std::runtime_error("compact sqrt slot/stack drift");
        }
        CompactTaylorResult value = stack.back();
        stack.pop_back();
        stack.push_back(compact_result_sqrt(
            radii, job.center_certificates[sqrt_slot],
            job.box_certificates[sqrt_slot], value, counters));
        ++sqrt_slot;
      } else {
        throw std::runtime_error("unknown compact analytic pair instruction");
      }
      continue;
    }

    const unsigned long opcode = instruction.numeral.get_ui();
    if (opcode == 2 || opcode == 5 || opcode == 6 || opcode == 7) {
      if (stack.empty()) {
        throw std::runtime_error("compact analytic stack underflow");
      }
      CompactTaylorResult value = stack.back();
      stack.pop_back();
      if (opcode == 2) {
        stack.push_back(compact_result_neg(radii, value, counters));
      } else if (opcode == 5) {
        stack.push_back(compact_result_mul(radii, value, value, counters));
      } else if (opcode == 6) {
        stack.push_back(compact_result_inverse(radii, value, counters));
      } else {
        stack.push_back(compact_result_atan(radii, value, counters));
      }
    } else if (opcode == 3 || opcode == 4) {
      if (stack.size() < 2) {
        throw std::runtime_error("compact analytic stack underflow");
      }
      CompactTaylorResult right = stack.back();
      stack.pop_back();
      CompactTaylorResult left = stack.back();
      stack.pop_back();
      stack.push_back(opcode == 3
                          ? compact_result_add(radii, left, right, counters)
                          : compact_result_mul(radii, left, right, counters));
    } else if (opcode == 8) {
      stack.push_back(compact_result_pi_half(radii, counters));
    } else {
      throw std::runtime_error("unknown compact analytic scalar instruction");
    }
  }
  if (direct_delta_x4 && !direct_delta_x4_used) {
    throw std::runtime_error("compact negated delta_x4 source position drift");
  }
  if (sqrt_slot != kSqrtSlots || stack.size() != 1 ||
      !stack.back().domain) {
    throw std::runtime_error("final compact analytic result shape/domain drift");
  }
  return {normalized_rat(integer_of_fixed(stack.back().value_bound.upper),
                         integer_of_fixed(kScale)),
          counters};
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
    if (argc < 4 || argc > 30) {
      std::cerr << "usage: " << argv[0]
                << " PROGRAM.cval JOBS.tsv EXPECTED-BOUNDS.tsv"
                << " [--profile]"
                << " [--fused-polynomial|--fused-delta-x4|"
                << "--specialized-angle-polynomials]"
                << " [--fused-polynomial-index=N]"
                << " [--fused-polynomial-max-steps=N]"
                << " [--direct-delta-x4]"
                << " [--skip-exact-zero-products]"
                << " [--symmetric-hessian-ops]"
                << " [--compact-support-jets]"
                << " [--fixed-sqrt-inverse-kernels]"
                << " [--fixed-atan-kernel]"
                << " [--verify-fixed-kernel-enclosures]"
                << " [--prepared-simple-polynomials]"
                << " [--prepared-coordinate-sqrt-terms]"
                << " [--prepared-dihedral-chain]"
                << " [--specialized-dihedral-identities]"
                << " [--historical-dihedral]"
                << " [--historical-block-rounding]"
                << " [--tight-dihedral-sqrt-certificates]"
                << " [--optimized-dihedral-u-bounds]"
                << " [--computed-tight-sqrt-certificates]"
                << " [--precompute-tight-sqrt-certificates]"
                << " [--hardware-seeded-integer-sqrt]"
                << " [--hardware-seeded-fixed-quotient]"
                << " [--dyadic-shift-fixed-quotient]"
                << " [--fuse-consecutive-adds]"
                << " [--narrow-fixed-products]"
                << " [--unchecked-narrow-fixed-products]"
                << " [--count-fixed-quotients]"
                << " [--rounding-profile]"
                << " [--dihedral-identity-diagnostics]"
                << " [--delta-full-diagnostics]"
                << " [--decimal-scale=N]"
                << " [--binary-scale-bits=N]"
                << " [--dyadic-scale]\n";
      return 2;
    }
    bool profile_enabled = false;
    bool rounding_profile_enabled = false;
    bool dyadic_scale = false;
    int fused_polynomial_outer_index = -1;
    int fused_polynomial_max_steps = -1;
    bool direct_delta_x4 = false;
    bool dihedral_identity_diagnostics = false;
    bool delta_full_diagnostics = false;
    bool custom_decimal_scale = false;
    bool custom_binary_scale = false;
    int requested_binary_scale_bits = 40;
    Integer requested_decimal_scale("1000000000000");
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
      } else if (option == "--dyadic-scale") {
        dyadic_scale = true;
      } else if (option.rfind("--fused-polynomial-index=", 0) == 0) {
        fused_polynomial_outer_index = std::stoi(
            option.substr(std::string("--fused-polynomial-index=").size()));
        if (fused_polynomial_outer_index < 0) {
          throw std::runtime_error("negative fused polynomial index");
        }
      } else if (option.rfind("--fused-polynomial-max-steps=", 0) == 0) {
        fused_polynomial_max_steps = std::stoi(option.substr(
            std::string("--fused-polynomial-max-steps=").size()));
        if (fused_polynomial_max_steps < 0) {
          throw std::runtime_error("negative fused polynomial step bound");
        }
      } else if (option == "--direct-delta-x4") {
        direct_delta_x4 = true;
      } else if (option == "--skip-exact-zero-products") {
        kSkipExactZeroProducts = true;
      } else if (option == "--symmetric-hessian-ops") {
        kUseSymmetricHessianOps = true;
      } else if (option == "--compact-support-jets") {
        kUseCompactSupportJets = true;
      } else if (option == "--fixed-sqrt-inverse-kernels") {
        kUseFixedSqrtInverseKernels = true;
      } else if (option == "--fixed-atan-kernel") {
        kUseFixedAtanKernel = true;
      } else if (option == "--verify-fixed-kernel-enclosures") {
        kVerifyFixedKernelEnclosures = true;
      } else if (option == "--prepared-simple-polynomials") {
        kUsePreparedSimplePolynomials = true;
      } else if (option == "--prepared-coordinate-sqrt-terms") {
        kUsePreparedCoordinateSqrtTerms = true;
      } else if (option == "--prepared-dihedral-chain") {
        kUsePreparedDihedralChain = true;
      } else if (option == "--specialized-dihedral-identities") {
        kUseSpecializedDihedralIdentities = true;
      } else if (option == "--historical-dihedral") {
        kUseHistoricalDihedral = true;
      } else if (option == "--historical-block-rounding") {
        kUseHistoricalBlockRounding = true;
      } else if (option == "--tight-dihedral-sqrt-certificates") {
        kUseTightDihedralSqrtCertificates = true;
      } else if (option == "--optimized-dihedral-u-bounds") {
        kUseOptimizedDihedralUBounds = true;
      } else if (option == "--computed-tight-sqrt-certificates") {
        kUseComputedTightSqrtCertificates = true;
      } else if (option == "--precompute-tight-sqrt-certificates") {
        kPrecomputeTightSqrtCertificates = true;
      } else if (option == "--hardware-seeded-integer-sqrt") {
        kUseHardwareSeededIntegerSqrt = true;
      } else if (option == "--hardware-seeded-fixed-quotient") {
        kUseHardwareSeededFixedQuotient = true;
      } else if (option == "--dyadic-shift-fixed-quotient") {
        kUseDyadicShiftFixedQuotient = true;
      } else if (option == "--fuse-consecutive-adds") {
        kFuseConsecutiveAdds = true;
      } else if (option == "--narrow-fixed-products") {
        kUseNarrowFixedProducts = true;
      } else if (option == "--unchecked-narrow-fixed-products") {
        kUseUncheckedNarrowFixedProducts = true;
      } else if (option == "--count-fixed-quotients") {
        kCountFixedQuotients = true;
      } else if (option == "--rounding-profile") {
        rounding_profile_enabled = true;
        kCountFixedQuotients = true;
      } else if (option == "--dihedral-identity-diagnostics") {
        dihedral_identity_diagnostics = true;
      } else if (option == "--delta-full-diagnostics") {
        delta_full_diagnostics = true;
      } else if (option.rfind("--decimal-scale=", 0) == 0) {
        requested_decimal_scale = Integer(
            option.substr(std::string("--decimal-scale=").size()));
        if (requested_decimal_scale <= 0) {
          throw std::runtime_error("nonpositive decimal scale");
        }
        custom_decimal_scale = true;
      } else if (option.rfind("--binary-scale-bits=", 0) == 0) {
        requested_binary_scale_bits = std::stoi(option.substr(
            std::string("--binary-scale-bits=").size()));
        if (requested_binary_scale_bits <= 0 ||
            requested_binary_scale_bits >= 63) {
          throw std::runtime_error("invalid binary scale bit count");
        }
        dyadic_scale = true;
        custom_binary_scale = true;
      } else {
        throw std::runtime_error("unknown optional argument: " + option);
      }
    }
    if (dyadic_scale && custom_decimal_scale) {
      throw std::runtime_error("conflicting scale selections");
    }
    if (custom_binary_scale && custom_decimal_scale) {
      throw std::runtime_error("conflicting custom scale selections");
    }
    if (kUseDyadicShiftFixedQuotient && !dyadic_scale) {
      throw std::runtime_error(
          "dyadic shift quotients require a binary scale");
    }
    if (kUseDyadicShiftFixedQuotient &&
        kUseHardwareSeededFixedQuotient) {
      throw std::runtime_error("conflicting fixed quotient diagnostics");
    }
    if (kUseNarrowFixedProducts && kUseUncheckedNarrowFixedProducts) {
      throw std::runtime_error("conflicting narrow product diagnostics");
    }
    if (profile_enabled && rounding_profile_enabled) {
      throw std::runtime_error(
          "timing and rounding profiles cannot be combined");
    }
    if (kFuseConsecutiveAdds && profile_enabled) {
      throw std::runtime_error(
          "fused add runs cannot be combined with the legacy timing profile");
    }
    if (rounding_profile_enabled && kUseCompactSupportJets) {
      throw std::runtime_error(
          "rounding profiling is not implemented for compact support jets");
    }
    if (kUsePreparedCoordinateSqrtTerms) {
      kUsePreparedSimplePolynomials = true;
    }
    if (profile_enabled && kUseCompactSupportJets) {
      throw std::runtime_error(
          "instruction profiling is not implemented for compact support jets");
    }
    if (profile_enabled && kUsePreparedCoordinateSqrtTerms) {
      throw std::runtime_error(
          "instruction profiling is not implemented for prepared coordinate "
          "sqrt terms");
    }
    if (profile_enabled && kUsePreparedDihedralChain) {
      throw std::runtime_error(
          "instruction profiling is not implemented for the prepared "
          "dihedral chain");
    }
    if (profile_enabled && kUseSpecializedDihedralIdentities) {
      throw std::runtime_error(
          "instruction profiling is not implemented for specialized "
          "dihedral identities");
    }
    if (profile_enabled && kUseHistoricalDihedral) {
      throw std::runtime_error(
          "instruction profiling is not implemented for the historical "
          "dihedral path");
    }
    if (kUseCompactSupportJets &&
        (kUseFixedSqrtInverseKernels || kUseFixedAtanKernel ||
         kUsePreparedSimplePolynomials || kUsePreparedDihedralChain ||
         kUseSpecializedDihedralIdentities || kUseHistoricalDihedral)) {
      throw std::runtime_error(
          "compact support jets do not yet implement fixed nonlinear kernels "
          "or prepared simple polynomials");
    }
    if (kVerifyFixedKernelEnclosures &&
        !(kUseFixedSqrtInverseKernels || kUseFixedAtanKernel)) {
      throw std::runtime_error(
          "fixed kernel verification requires a fixed nonlinear kernel");
    }
    if (kUsePreparedCoordinateSqrtTerms &&
        !kUseFixedSqrtInverseKernels) {
      throw std::runtime_error(
          "prepared coordinate sqrt terms require fixed sqrt kernels");
    }
    if (kUsePreparedDihedralChain &&
        (!kUseFixedSqrtInverseKernels || !kUseFixedAtanKernel ||
         polynomial_mode != PolynomialMode::kSpecializedAngle ||
         !direct_delta_x4)) {
      throw std::runtime_error(
          "prepared dihedral chain requires fixed nonlinear kernels and "
          "both authenticated angle polynomial modes");
    }
    if (static_cast<int>(kUsePreparedDihedralChain) +
            static_cast<int>(kUseSpecializedDihedralIdentities) +
            static_cast<int>(kUseHistoricalDihedral) >
        1) {
      throw std::runtime_error("conflicting prepared dihedral modes");
    }
    if (kUseSpecializedDihedralIdentities &&
        (!kUseFixedSqrtInverseKernels || !kUseFixedAtanKernel ||
         polynomial_mode != PolynomialMode::kSpecializedAngle ||
         !direct_delta_x4)) {
      throw std::runtime_error(
          "specialized dihedral identities require fixed nonlinear kernels "
          "and both authenticated angle polynomial modes");
    }
    if (kUseSpecializedDihedralIdentities &&
        kVerifyFixedKernelEnclosures) {
      throw std::runtime_error(
          "specialized dihedral identity cross-check is not yet implemented");
    }
    if (kUseHistoricalDihedral &&
        (!kUseFixedSqrtInverseKernels || !kUseFixedAtanKernel ||
         polynomial_mode != PolynomialMode::kSpecializedAngle ||
         !direct_delta_x4)) {
      throw std::runtime_error(
          "historical dihedral requires fixed nonlinear kernels and both "
          "authenticated angle polynomial modes");
    }
    if (kUseHistoricalBlockRounding && !kUseHistoricalDihedral) {
      throw std::runtime_error(
          "historical block rounding requires the historical dihedral path");
    }
    if (dihedral_identity_diagnostics &&
        !kUseSpecializedDihedralIdentities && !kUseHistoricalDihedral) {
      throw std::runtime_error(
          "dihedral diagnostics require a specialized dihedral path");
    }
    if (kUseTightDihedralSqrtCertificates &&
        !kUseSpecializedDihedralIdentities) {
      throw std::runtime_error(
          "tight dihedral square-root certificates require specialized "
          "identities");
    }
    if (kUseOptimizedDihedralUBounds &&
        !kUseSpecializedDihedralIdentities) {
      throw std::runtime_error(
          "optimized dihedral U bounds require specialized identities");
    }
    if (kUseComputedTightSqrtCertificates &&
        !kUseFixedSqrtInverseKernels) {
      throw std::runtime_error(
          "computed tight square-root certificates require fixed kernels");
    }
    if (kPrecomputeTightSqrtCertificates &&
        (!kUseFixedSqrtInverseKernels ||
         !kUsePreparedCoordinateSqrtTerms ||
         polynomial_mode != PolynomialMode::kSpecializedAngle ||
         !direct_delta_x4)) {
      throw std::runtime_error(
          "tight square-root preparation requires fixed kernels, prepared "
          "coordinate roots, and authenticated angle polynomials");
    }
    if (kPrecomputeTightSqrtCertificates &&
        kUseComputedTightSqrtCertificates) {
      throw std::runtime_error(
          "conflicting precomputed and evaluation-time square roots");
    }
#if !defined(CANDLE_NL_FIXED_INT128)
    if (kUseHardwareSeededIntegerSqrt) {
      throw std::runtime_error(
          "hardware-seeded integer square root is a native int128 "
          "diagnostic only");
    }
    if (kUseHardwareSeededFixedQuotient) {
      throw std::runtime_error(
          "hardware-seeded fixed quotient is a native int128 diagnostic "
          "only");
    }
    if (kUseDyadicShiftFixedQuotient) {
      throw std::runtime_error(
          "dyadic shift fixed quotient is a native int128 diagnostic only");
    }
    if (kUseNarrowFixedProducts) {
      throw std::runtime_error(
          "narrow fixed products are a native int128 diagnostic only");
    }
    if (kUseUncheckedNarrowFixedProducts) {
      throw std::runtime_error(
          "unchecked narrow fixed products are a native int128 diagnostic "
          "only");
    }
#endif
    if (dyadic_scale) {
      Integer binary_scale = 1;
      mpz_mul_2exp(binary_scale.get_mpz_t(), binary_scale.get_mpz_t(),
                   static_cast<mp_bitcnt_t>(requested_binary_scale_bits));
      kScale = fixed_of_integer(binary_scale);
      kTwoScaleSquared = 2 * kScale * kScale;
      kDyadicScaleBits = requested_binary_scale_bits;
    } else if (custom_decimal_scale) {
      kScale = fixed_of_integer(requested_decimal_scale);
      kTwoScaleSquared = 2 * kScale * kScale;
    }
#if defined(CANDLE_NL_FIXED_INT128)
    if (kUseDyadicShiftFixedQuotient) {
      verify_dyadic_shift_quotient_samples();
    }
#endif

    const std::uint64_t preparation_floor_begin =
        kFloorFixedQuotientCalls;
    const std::uint64_t preparation_ceil_begin =
        kCeilFixedQuotientCalls;
    const std::uint64_t preparation_dyadic_shift_begin =
        kDyadicShiftFixedQuotientCalls;
    const std::uint64_t preparation_dyadic_fallback_begin =
        kDyadicFallbackFixedQuotientCalls;
    const auto preparation_begin = std::chrono::steady_clock::now();
    Program program = read_program(argv[1]);
    if (kUsePreparedSimplePolynomials) {
      prepare_simple_polynomials(program);
    }
    if (kUsePreparedCoordinateSqrtTerms) {
      prepare_coordinate_sqrt_terms(program);
    }
    if (kUsePreparedDihedralChain || kUseSpecializedDihedralIdentities ||
        kUseHistoricalDihedral || kPrecomputeTightSqrtCertificates) {
      prepare_dihedral_chain(program);
    }
    std::vector<Job> jobs = read_jobs(argv[2]);
    if (kUseFixedSqrtInverseKernels) {
      prepare_fixed_sqrt_certificates(jobs);
    }
    if (kPrecomputeTightSqrtCertificates) {
      precompute_tight_sqrt_certificates(program, jobs);
    }
    const std::vector<Rat> expected = read_expected_bounds(argv[3]);
    if (expected.size() != jobs.size()) {
      throw std::runtime_error("expected-bound count drift");
    }
    const auto preparation_end = std::chrono::steady_clock::now();
    const std::uint64_t preparation_floor_calls =
        kFloorFixedQuotientCalls - preparation_floor_begin;
    const std::uint64_t preparation_ceil_calls =
        kCeilFixedQuotientCalls - preparation_ceil_begin;
    const std::uint64_t preparation_dyadic_shift_calls =
        kDyadicShiftFixedQuotientCalls - preparation_dyadic_shift_begin;
    const std::uint64_t preparation_dyadic_fallback_calls =
        kDyadicFallbackFixedQuotientCalls - preparation_dyadic_fallback_begin;

    std::size_t prepared_simple_polynomial_count = 0;
    for (const Program::SimplePolynomial& polynomial :
         program.prepared_simple_polynomials) {
      if (polynomial.kind != Program::SimplePolynomialKind::kUnknown) {
        ++prepared_simple_polynomial_count;
      }
    }
    std::size_t prepared_coordinate_sqrt_term_count = 0;
    for (const Program::CoordinateSqrtTerm& term :
         program.prepared_coordinate_sqrt_terms) {
      if (term.active) ++prepared_coordinate_sqrt_term_count;
    }

    Counters total;
    std::vector<Rat> results;
    results.reserve(jobs.size());
    std::vector<InstructionProfile> profiles(
        profile_enabled ? program.instructions.size() : 0);
    // Slot zero covers per-job environment setup. Instruction i is stored in
    // slot i + 1 so the sum can be reconciled with the evaluation total.
    std::vector<RoundingProfile> rounding_profiles(
        rounding_profile_enabled ? program.instructions.size() + 1 : 0);
    std::size_t mismatches = 0;
    std::size_t accepted = 0;
    std::size_t tighter = 0;
    std::size_t equal = 0;
    std::size_t wider = 0;
    Rat maximum_upper_minus_expected;
    bool have_difference = false;
    const std::uint64_t evaluation_floor_begin =
        kFloorFixedQuotientCalls;
    const std::uint64_t evaluation_ceil_begin =
        kCeilFixedQuotientCalls;
    const std::uint64_t evaluation_dyadic_shift_begin =
        kDyadicShiftFixedQuotientCalls;
    const std::uint64_t evaluation_dyadic_fallback_begin =
        kDyadicFallbackFixedQuotientCalls;
    const auto evaluation_begin = std::chrono::steady_clock::now();
    for (std::size_t index = 0; index < jobs.size(); ++index) {
      const Evaluation evaluation = kUseCompactSupportJets
          ? evaluate_job_compact(
                program, jobs[index], polynomial_mode,
                fused_polynomial_outer_index, fused_polynomial_max_steps,
                direct_delta_x4)
          : evaluate_job(
                program, jobs[index], polynomial_mode,
                fused_polynomial_outer_index, fused_polynomial_max_steps,
                direct_delta_x4, profile_enabled ? &profiles : nullptr,
                rounding_profile_enabled ? &rounding_profiles : nullptr);
      results.push_back(evaluation.upper);
      add_counters(total, evaluation.counters);
      if (evaluation.upper != expected[index]) ++mismatches;
      if (evaluation.upper < 0) ++accepted;
      const Rat difference = evaluation.upper - expected[index];
      if (difference < 0) {
        ++tighter;
      } else if (difference == 0) {
        ++equal;
      } else {
        ++wider;
      }
      if (!have_difference || difference > maximum_upper_minus_expected) {
        maximum_upper_minus_expected = difference;
        have_difference = true;
      }
    }
    const auto evaluation_end = std::chrono::steady_clock::now();
    const std::uint64_t evaluation_floor_calls =
        kFloorFixedQuotientCalls - evaluation_floor_begin;
    const std::uint64_t evaluation_ceil_calls =
        kCeilFixedQuotientCalls - evaluation_ceil_begin;
    const std::uint64_t evaluation_dyadic_shift_calls =
        kDyadicShiftFixedQuotientCalls - evaluation_dyadic_shift_begin;
    const std::uint64_t evaluation_dyadic_fallback_calls =
        kDyadicFallbackFixedQuotientCalls - evaluation_dyadic_fallback_begin;

    const double preparation_seconds =
        std::chrono::duration<double>(preparation_end - preparation_begin).count();
    const double evaluation_seconds =
        std::chrono::duration<double>(evaluation_end - evaluation_begin).count();
    std::cout << std::setprecision(17);
    std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY"
              << " cells=" << jobs.size()
              << " backend=" << kFixedBackend
              << " arithmetic="
              << (dyadic_scale ? "dyadic"
                               : custom_decimal_scale ? "decimal-custom"
                                                      : "decimal-1e12")
              << " binary_scale_bits="
              << (dyadic_scale ? requested_binary_scale_bits : -1)
              << " scale=" << integer_of_fixed(kScale).get_str()
              << " mode="
              << (polynomial_mode == PolynomialMode::kFusedAll
                      ? "fused-polynomial"
                      : polynomial_mode == PolynomialMode::kFusedDeltaX4
                            ? "fused-delta-x4"
                            : polynomial_mode == PolynomialMode::kSpecializedAngle
                                  ? "specialized-angle-polynomials"
                                  : "baseline")
              << " fused_outer_index=" << fused_polynomial_outer_index
              << " fused_max_steps=" << fused_polynomial_max_steps
              << " direct_delta_x4=" << (direct_delta_x4 ? 1 : 0)
              << " direct_delta_x4_source_sign=negated"
              << " skip_exact_zero_products="
              << (kSkipExactZeroProducts ? 1 : 0)
              << " symmetric_hessian_ops="
              << (kUseSymmetricHessianOps ? 1 : 0)
              << " compact_support_jets="
              << (kUseCompactSupportJets ? 1 : 0)
              << " fixed_sqrt_inverse_kernels="
              << (kUseFixedSqrtInverseKernels ? 1 : 0)
              << " fixed_atan_kernel=" << (kUseFixedAtanKernel ? 1 : 0)
              << " verify_fixed_kernel_enclosures="
              << (kVerifyFixedKernelEnclosures ? 1 : 0)
              << " prepared_simple_polynomials="
              << (kUsePreparedSimplePolynomials ? 1 : 0)
              << " prepared_simple_polynomial_count="
              << prepared_simple_polynomial_count
              << " prepared_coordinate_sqrt_terms="
              << (kUsePreparedCoordinateSqrtTerms ? 1 : 0)
              << " prepared_coordinate_sqrt_term_count="
              << prepared_coordinate_sqrt_term_count
              << " prepared_dihedral_chain="
              << (kUsePreparedDihedralChain ? 1 : 0)
              << " specialized_dihedral_identities="
              << (kUseSpecializedDihedralIdentities ? 1 : 0)
              << " historical_dihedral="
              << (kUseHistoricalDihedral ? 1 : 0)
              << " historical_block_rounding="
              << (kUseHistoricalBlockRounding ? 1 : 0)
              << " tight_dihedral_sqrt_certificates="
              << (kUseTightDihedralSqrtCertificates ? 1 : 0)
              << " optimized_dihedral_u_bounds="
              << (kUseOptimizedDihedralUBounds ? 1 : 0)
              << " computed_tight_sqrt_certificates="
              << (kUseComputedTightSqrtCertificates ? 1 : 0)
              << " precompute_tight_sqrt_certificates="
              << (kPrecomputeTightSqrtCertificates ? 1 : 0)
              << " hardware_seeded_integer_sqrt="
              << (kUseHardwareSeededIntegerSqrt ? 1 : 0)
              << " hardware_seeded_fixed_quotient="
              << (kUseHardwareSeededFixedQuotient ? 1 : 0)
              << " dyadic_shift_fixed_quotient="
              << (kUseDyadicShiftFixedQuotient ? 1 : 0)
              << " fuse_consecutive_adds="
              << (kFuseConsecutiveAdds ? 1 : 0)
              << " narrow_fixed_products="
              << (kUseNarrowFixedProducts ? 1 : 0)
              << " unchecked_narrow_fixed_products="
              << (kUseUncheckedNarrowFixedProducts ? 1 : 0)
              << " count_fixed_quotients="
              << (kCountFixedQuotients ? 1 : 0)
              << " matched=" << (jobs.size() - mismatches)
              << " mismatches=" << mismatches
              << " accepted=" << accepted
              << " tighter=" << tighter
              << " equal=" << equal
              << " wider=" << wider
              << " maximum_upper_minus_expected="
              << maximum_upper_minus_expected.get_str()
              << " preparation_seconds=" << preparation_seconds
              << " evaluation_seconds=" << evaluation_seconds
              << " preparation_floor_quotients="
              << preparation_floor_calls
              << " preparation_ceil_quotients="
              << preparation_ceil_calls
              << " preparation_dyadic_shift_quotients="
              << preparation_dyadic_shift_calls
              << " preparation_dyadic_fallback_quotients="
              << preparation_dyadic_fallback_calls
              << " evaluation_floor_quotients="
              << evaluation_floor_calls
              << " evaluation_ceil_quotients="
              << evaluation_ceil_calls
              << " evaluation_dyadic_shift_quotients="
              << evaluation_dyadic_shift_calls
              << " evaluation_dyadic_fallback_quotients="
              << evaluation_dyadic_fallback_calls
#if defined(CANDLE_NL_FIXED_INT128) && \
    defined(CANDLE_NL_FIXED_RANGE_PROFILE)
              << " fixed_range_profile=1"
              << " range_quotient_numerator_bits="
              << kFixedRangeProfile.quotient_numerator_bits
              << " range_quotient_denominator_bits="
              << kFixedRangeProfile.quotient_denominator_bits
              << " range_quotient_result_bits="
              << kFixedRangeProfile.quotient_result_bits
              << " range_quotient_results_outside_int64="
              << kFixedRangeProfile.quotient_results_outside_int64
              << " range_multiplication_operand_bits="
              << kFixedRangeProfile.multiplication_operand_bits
              << " range_multiplication_operands_outside_int64="
              << kFixedRangeProfile.multiplication_operands_outside_int64
              << " range_multiplication_product_bits="
              << kFixedRangeProfile.multiplication_product_bits
              << " range_addition_result_bits="
              << kFixedRangeProfile.addition_result_bits
              << " range_addition_results_outside_int64="
              << kFixedRangeProfile.addition_results_outside_int64
              << " range_scaled_input_bits="
              << kFixedRangeProfile.scaled_input_bits
              << " range_scaled_inputs_outside_int64="
              << kFixedRangeProfile.scaled_inputs_outside_int64
#endif
              << " interval_products=" << total.interval_products
              << " skipped_zero_products=" << total.skipped_zero_products
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
                  << " skipped_zero_products="
                  << profile.counters.skipped_zero_products
                  << " completed_results=" << profile.counters.completed_results
                  << " polynomial_steps=" << profile.counters.polynomial_steps
                  << " outer_steps=" << profile.counters.outer_steps
                  << " sqrt_steps=" << profile.counters.sqrt_steps
                  << " inverse_steps=" << profile.counters.inverse_steps
                  << " atan_steps=" << profile.counters.atan_steps << "\n";
      }
    }
    if (rounding_profile_enabled) {
      std::uint64_t profiled_floor_quotients = 0;
      std::uint64_t profiled_ceil_quotients = 0;
      for (std::size_t profile_index = 0;
           profile_index < rounding_profiles.size(); ++profile_index) {
        const RoundingProfile& profile = rounding_profiles[profile_index];
        if (profile.observations == 0) continue;
        profiled_floor_quotients += profile.floor_quotients;
        profiled_ceil_quotients += profile.ceil_quotients;
        std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_ROUNDING_PROFILE"
                  << " index="
                  << (profile_index == 0
                          ? -1
                          : static_cast<long long>(profile_index - 1))
                  << " label=" << profile.label
                  << " observations=" << profile.observations
                  << " nanoseconds=" << profile.nanoseconds
                  << " floor_quotients=" << profile.floor_quotients
                  << " ceil_quotients=" << profile.ceil_quotients
                  << " total_quotients="
                  << profile.floor_quotients + profile.ceil_quotients
                  << "\n";
      }
      if (profiled_floor_quotients != evaluation_floor_calls ||
          profiled_ceil_quotients != evaluation_ceil_calls) {
        throw std::runtime_error(
            "rounding profile does not reconcile with evaluation total");
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
    if (delta_full_diagnostics) {
      run_delta_full_diagnostics(jobs);
    }
    if (dihedral_identity_diagnostics) {
      for (std::size_t index = 0; index < jobs.size(); ++index) {
        print_dihedral_identity_diagnostic(
            index, evaluate_dihedral_identity_diagnostic(jobs[index]));
      }
    }
    if (!dyadic_scale && polynomial_mode == PolynomialMode::kBaseline &&
        mismatches != 0) {
      std::cerr << "fixed-scale native comparison found " << mismatches
                << " mismatches\n";
      return 1;
    }
    if ((dyadic_scale || polynomial_mode != PolynomialMode::kBaseline) &&
        accepted != jobs.size()) {
      std::cerr << "development comparison accepted " << accepted
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
    if (dyadic_scale) {
      std::cout << "CANDLE_NL_NATIVE_FIXED_SCALE_DYADIC_OK"
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
