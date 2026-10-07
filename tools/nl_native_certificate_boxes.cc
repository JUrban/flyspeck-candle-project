#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <gmpxx.h>

#include "interval.h"
#include "lineInterval.h"
#include "univariate.h"
#include "secondDerive.h"
#include "taylorData.h"
#include "Lib.h"

typedef mpq_class Rational;

struct Box {
  int index;
  double lower[6];
  double upper[6];
};

static Rational parse_rational(const std::string& text) {
  Rational value(text);
  value.canonicalize();
  if (value.get_den() <= 0 || value.get_num() < 0)
    throw std::runtime_error("box coordinate is not a nonnegative rational: " + text);
  return value;
}

/* Exact comparison of a finite nonnegative binary64 value with n/d. */
static int compare_double_rational(double candidate, const Rational& value) {
  if (!std::isfinite(candidate) || candidate < 0.0)
    throw std::runtime_error("invalid binary64 coordinate candidate");
  const Rational exact_candidate(candidate);
  return exact_candidate < value ? -1 : exact_candidate > value ? 1 : 0;
}

static double directed_rational(const Rational& value, bool upward) {
  double candidate = value.get_d();
  const double direction = upward
    ? std::numeric_limits<double>::infinity()
    : -std::numeric_limits<double>::infinity();
  int comparison = compare_double_rational(candidate, value);
  while ((upward && comparison < 0) || (!upward && comparison > 0)) {
    candidate = std::nextafter(candidate, direction);
    comparison = compare_double_rational(candidate, value);
  }
  return candidate;
}

static std::vector<std::string> split(const std::string& text, char separator) {
  std::vector<std::string> fields;
  std::string field;
  std::istringstream input(text);
  while (std::getline(input, field, separator)) fields.push_back(field);
  return fields;
}

static std::vector<Box> read_boxes(const char* path, std::size_t limit) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error(std::string("cannot open boxes: ") + path);
  std::vector<Box> boxes;
  std::string line;
  while (std::getline(input, line) && boxes.size() < limit) {
    const std::vector<std::string> columns = split(line, '\t');
    if (columns.size() != 3) throw std::runtime_error("malformed box row");
    const std::vector<std::string> lower = split(columns[1], ',');
    const std::vector<std::string> upper = split(columns[2], ',');
    if (lower.size() != 6 || upper.size() != 6)
      throw std::runtime_error("box dimension is not six");
    Box box;
    box.index = std::stoi(columns[0]);
    if (box.index != static_cast<int>(boxes.size()))
      throw std::runtime_error("box index drift");
    for (int coordinate = 0; coordinate < 6; ++coordinate) {
      box.lower[coordinate] =
        directed_rational(parse_rational(lower[coordinate]), false);
      box.upper[coordinate] =
        directed_rational(parse_rational(upper[coordinate]), true);
      if (box.lower[coordinate] > box.upper[coordinate])
        throw std::runtime_error("empty box coordinate");
    }
    boxes.push_back(box);
  }
  if (boxes.empty()) throw std::runtime_error("empty box dataset");
  return boxes;
}

static Function benchmark_function(bool generic) {
  Function angle = Lib::dih_x;
  if (generic) {
    angle =
      Lib::constant6(interval("1.570796326794896619231321691639751442")) +
      Lib::uni(univariate::i_atan,
        (Lib::delta_x4 * interval("-1")) /
        Lib::uni(univariate::i_sqrt, Lib::x1 * Lib::delta_x * interval("4")));
  }
  return
    Lib::constant6(interval("1.277") - interval("0.273298") * interval("2.18") +
      interval("0.273853") * interval("4") - interval("0.708818") * interval("2") +
      interval("0.313988") * interval("4")) +
    Function::uni_slot(univariate::i_sqrt, 0) * interval("0.273298") +
    Function::uni_slot(univariate::i_sqrt, 1) * interval("-0.273853") +
    Function::uni_slot(univariate::i_sqrt, 2) * interval("-0.273853") +
    Function::uni_slot(univariate::i_sqrt, 3) * interval("0.708818") +
    Function::uni_slot(univariate::i_sqrt, 4) * interval("-0.313988") +
    Function::uni_slot(univariate::i_sqrt, 5) * interval("-0.313988") +
    angle * interval("-1");
}

struct Result {
  std::vector<double> upper;
  double wall_seconds;
  double domain_seconds;
  double evalf_seconds;
  double upper_bound_seconds;
  double checksum;
  std::size_t accepted;
  std::size_t unstable_boxes;
};

struct TaylorUpperBreakdown {
  double center_upper;
  double linear;
  double quadratic;
  double recomposed_upper;
};

struct DirectPlan {
  interval constant;
  interval sqrt_coefficient[6];
  interval angle_coefficient;

  DirectPlan()
      : constant(interval("1.277") -
                 interval("0.273298") * interval("2.18") +
                 interval("0.273853") * interval("4") -
                 interval("0.708818") * interval("2") +
                 interval("0.313988") * interval("4")),
        angle_coefficient("-1") {
    sqrt_coefficient[0] = interval("0.273298");
    sqrt_coefficient[1] = interval("-0.273853");
    sqrt_coefficient[2] = interval("-0.273853");
    sqrt_coefficient[3] = interval("0.708818");
    sqrt_coefficient[4] = interval("-0.313988");
    sqrt_coefficient[5] = interval("-0.313988");
  }
};

struct DirectProfile {
  std::size_t observations = 0;
  double midpoint_seconds = 0.0;
  double sqrt_leaf_seconds = 0.0;
  double angle_tangent_seconds = 0.0;
  double angle_hessian_seconds = 0.0;
  double assembly_seconds = 0.0;
};

static double interval_abs_upper(const interval& value) {
  return interMath::sup(interMath::max(value, -value));
}

static TaylorUpperBreakdown upper_breakdown(const taylorData& data) {
  interMath::up();
  double diagonal = 0.0;
  for (int coordinate = 0; coordinate < 6; ++coordinate) {
    const double width = data.w.getValue(coordinate);
    diagonal += width * width * data.DD[coordinate][coordinate];
  }
  double quadratic = diagonal / 2.0;
  for (int row = 0; row < 6; ++row) {
    for (int column = row + 1; column < 6; ++column) {
      quadratic += data.w.getValue(row) * data.w.getValue(column) *
                   data.DD[row][column];
    }
  }
  const double center_upper = data.tangentVector.f.hi;
  double recomposed_upper = center_upper + quadratic;
  double linear = 0.0;
  for (int coordinate = 0; coordinate < 6; ++coordinate) {
    const double contribution = data.w.getValue(coordinate) *
      interval_abs_upper(data.tangentVector.Df[coordinate]);
    linear += contribution;
    recomposed_upper += contribution;
  }
  return {center_upper, linear, quadratic, recomposed_upper};
}

static void add_direct_primitive(lineInterval& tangent, double DD[6][6],
                                 const lineInterval& primitive_tangent,
                                 const double primitive_DD[6][6],
                                 const interval& coefficient) {
  tangent.f = tangent.f + primitive_tangent.f * coefficient;
  for (int coordinate = 0; coordinate < 6; ++coordinate) {
    tangent.Df[coordinate] = tangent.Df[coordinate] +
      primitive_tangent.Df[coordinate] * coefficient;
  }
  const double absolute_coefficient = interval_abs_upper(coefficient);
  interMath::up();
  for (int row = 0; row < 6; ++row) {
    for (int column = 0; column < 6; ++column) {
      DD[row][column] += primitive_DD[row][column] * absolute_coefficient;
    }
  }
}

static taylorData evaluate_direct_specialized_box(const DirectPlan& plan,
                                                  const domain& lower,
                                                  const domain& upper,
                                                  DirectProfile* profile = nullptr) {
  std::chrono::steady_clock::time_point midpoint_start;
  if (profile != nullptr) midpoint_start = std::chrono::steady_clock::now();
  double midpoint[6];
  double width[6];
  double lower_value[6];
  double upper_value[6];
  interMath::nearest();
  for (int coordinate = 0; coordinate < 6; ++coordinate) {
    lower_value[coordinate] = lower.getValue(coordinate);
    upper_value[coordinate] = upper.getValue(coordinate);
    midpoint[coordinate] =
      (upper_value[coordinate] + lower_value[coordinate]) / 2.0;
  }
  interMath::up();
  for (int coordinate = 0; coordinate < 6; ++coordinate) {
    width[coordinate] = std::max(
      upper_value[coordinate] - midpoint[coordinate],
      midpoint[coordinate] - lower_value[coordinate]);
  }
  const domain center(midpoint);
  const domain widths(width);
  std::chrono::steady_clock::time_point midpoint_finish;
  if (profile != nullptr) midpoint_finish = std::chrono::steady_clock::now();
  lineInterval tangent(plan.constant);
  double DD[6][6] = {};
  static const interval one("1");
  static const interval two("2");
  static const interval four("4");

  for (int coordinate = 0; coordinate < 6; ++coordinate) {
    const interval center_value(midpoint[coordinate], midpoint[coordinate]);
    const interval box_value(lower_value[coordinate], upper_value[coordinate]);
    const interval center_sqrt = interMath::sqrt(center_value);
    lineInterval primitive(center_sqrt);
    primitive.Df[coordinate] = one / (two * center_sqrt);
    double primitive_DD[6][6] = {};
    primitive_DD[coordinate][coordinate] = interval_abs_upper(
      -one / (four * box_value * interMath::sqrt(box_value)));
    add_direct_primitive(tangent, DD, primitive, primitive_DD,
                         plan.sqrt_coefficient[coordinate]);
  }
  std::chrono::steady_clock::time_point sqrt_leaf_finish;
  if (profile != nullptr) sqrt_leaf_finish = std::chrono::steady_clock::now();

  const lineInterval angle_tangent = linearization::dih(center);
  std::chrono::steady_clock::time_point angle_tangent_finish;
  if (profile != nullptr) {
    angle_tangent_finish = std::chrono::steady_clock::now();
  }
  double angle_DD[6][6];
  if (!secondDerive::setAbsDihedral(lower_value, upper_value, angle_DD)) {
    throw unstable::x;
  }
  std::chrono::steady_clock::time_point angle_hessian_finish;
  if (profile != nullptr) {
    angle_hessian_finish = std::chrono::steady_clock::now();
  }
  add_direct_primitive(tangent, DD, angle_tangent, angle_DD,
                       plan.angle_coefficient);
  const taylorData result(tangent, widths, DD);
  if (profile != nullptr) {
    const std::chrono::steady_clock::time_point assembly_finish =
      std::chrono::steady_clock::now();
    ++profile->observations;
    profile->midpoint_seconds += std::chrono::duration<double>(
      midpoint_finish - midpoint_start).count();
    profile->sqrt_leaf_seconds += std::chrono::duration<double>(
      sqrt_leaf_finish - midpoint_finish).count();
    profile->angle_tangent_seconds += std::chrono::duration<double>(
      angle_tangent_finish - sqrt_leaf_finish).count();
    profile->angle_hessian_seconds += std::chrono::duration<double>(
      angle_hessian_finish - angle_tangent_finish).count();
    profile->assembly_seconds += std::chrono::duration<double>(
      assembly_finish - angle_hessian_finish).count();
  }
  return result;
}

static Result evaluate(const Function& function, const std::vector<Box>& boxes) {
  Result result;
  result.checksum = 0.0;
  result.domain_seconds = 0.0;
  result.evalf_seconds = 0.0;
  result.upper_bound_seconds = 0.0;
  result.accepted = 0;
  result.unstable_boxes = 0;
  result.upper.reserve(boxes.size());
  const std::chrono::steady_clock::time_point start =
    std::chrono::steady_clock::now();
  for (std::vector<Box>::const_iterator box = boxes.begin(); box != boxes.end(); ++box) {
    double upper = std::numeric_limits<double>::infinity();
    try {
      const std::chrono::steady_clock::time_point domain_start =
        std::chrono::steady_clock::now();
      const domain lower_domain(box->lower);
      const domain upper_domain(box->upper);
      const std::chrono::steady_clock::time_point domain_finish =
        std::chrono::steady_clock::now();
      const std::chrono::steady_clock::time_point evalf_start = domain_finish;
      const taylorData data = function.evalf(lower_domain, upper_domain);
      const std::chrono::steady_clock::time_point evalf_finish =
        std::chrono::steady_clock::now();
      upper = data.upperBound();
      const std::chrono::steady_clock::time_point upper_bound_finish =
        std::chrono::steady_clock::now();
      result.domain_seconds += std::chrono::duration<double>(
        domain_finish - domain_start).count();
      result.evalf_seconds += std::chrono::duration<double>(
        evalf_finish - evalf_start).count();
      result.upper_bound_seconds += std::chrono::duration<double>(
        upper_bound_finish - evalf_finish).count();
    } catch (unstable) {
      ++result.unstable_boxes;
    }
    result.upper.push_back(upper);
    if (std::isfinite(upper)) result.checksum += upper;
    if (upper < 0.0) ++result.accepted;
  }
  const std::chrono::steady_clock::time_point finish =
    std::chrono::steady_clock::now();
  result.wall_seconds = std::chrono::duration<double>(finish - start).count();
  return result;
}

static Result evaluate_direct(const DirectPlan& plan,
                              const std::vector<Box>& boxes,
                              DirectProfile* profile = nullptr) {
  Result result;
  result.checksum = 0.0;
  result.domain_seconds = 0.0;
  result.evalf_seconds = 0.0;
  result.upper_bound_seconds = 0.0;
  result.accepted = 0;
  result.unstable_boxes = 0;
  result.upper.reserve(boxes.size());
  const std::chrono::steady_clock::time_point start =
    std::chrono::steady_clock::now();
  for (std::vector<Box>::const_iterator box = boxes.begin();
       box != boxes.end(); ++box) {
    double upper = std::numeric_limits<double>::infinity();
    try {
      const std::chrono::steady_clock::time_point domain_start =
        std::chrono::steady_clock::now();
      const domain lower_domain(box->lower);
      const domain upper_domain(box->upper);
      const std::chrono::steady_clock::time_point domain_finish =
        std::chrono::steady_clock::now();
      const std::chrono::steady_clock::time_point evalf_start = domain_finish;
      const taylorData data = evaluate_direct_specialized_box(
        plan, lower_domain, upper_domain, profile);
      const std::chrono::steady_clock::time_point evalf_finish =
        std::chrono::steady_clock::now();
      upper = data.upperBound();
      const std::chrono::steady_clock::time_point upper_bound_finish =
        std::chrono::steady_clock::now();
      result.domain_seconds += std::chrono::duration<double>(
        domain_finish - domain_start).count();
      result.evalf_seconds += std::chrono::duration<double>(
        evalf_finish - evalf_start).count();
      result.upper_bound_seconds += std::chrono::duration<double>(
        upper_bound_finish - evalf_finish).count();
    } catch (unstable) {
      ++result.unstable_boxes;
    }
    result.upper.push_back(upper);
    if (std::isfinite(upper)) result.checksum += upper;
    if (upper < 0.0) ++result.accepted;
  }
  const std::chrono::steady_clock::time_point finish =
    std::chrono::steady_clock::now();
  result.wall_seconds =
    std::chrono::duration<double>(finish - start).count();
  return result;
}

static void print_angle_diagnostics(const Function& angle,
                                    const std::vector<Box>& boxes) {
  for (std::vector<Box>::const_iterator box = boxes.begin();
       box != boxes.end(); ++box) {
    const taylorData data = angle.evalf(
        domain(box->lower), domain(box->upper));
    const lineInterval tangent = data.tangentVectorOf();
    std::cout << "CANDLE_NL_NATIVE_ANGLE_DIAGNOSTIC"
              << " index=" << box->index
              << " lower=" << data.lowerBound()
              << " upper=" << data.upperBound()
              << " center=" << tangent.f.lo << ":" << tangent.f.hi
              << " center_gradient=";
    for (int coordinate = 0; coordinate < 6; ++coordinate) {
      if (coordinate != 0) std::cout << ",";
      std::cout << tangent.Df[coordinate].lo << ":"
                << tangent.Df[coordinate].hi;
    }
    std::cout << " hessian_abs=";
    bool first = true;
    for (int row = 0; row < 6; ++row) {
      for (int column = row; column < 6; ++column) {
        if (!first) std::cout << ",";
        first = false;
        std::cout << data.DD[row][column];
      }
    }
    std::cout << "\n";
  }
}

static void print_stage_diagnostic(const char* prefix, int index,
                                   const taylorData& data) {
    const lineInterval tangent = data.tangentVectorOf();
    const TaylorUpperBreakdown breakdown = upper_breakdown(data);
    const double upper = data.upperBound();
    std::cout << prefix
              << " index=" << index
              << " center=" << tangent.f.lo << ":" << tangent.f.hi
              << " widths=";
    for (int coordinate = 0; coordinate < 6; ++coordinate) {
      if (coordinate != 0) std::cout << ",";
      std::cout << data.w.getValue(coordinate);
    }
    std::cout << " center_gradient=";
    for (int coordinate = 0; coordinate < 6; ++coordinate) {
      if (coordinate != 0) std::cout << ",";
      std::cout << tangent.Df[coordinate].lo << ":"
                << tangent.Df[coordinate].hi;
    }
    std::cout << " hessian_abs=";
    bool first = true;
    for (int row = 0; row < 6; ++row) {
      for (int column = row; column < 6; ++column) {
        if (!first) std::cout << ",";
        first = false;
        std::cout << data.DD[row][column];
      }
    }
    std::cout << " linear=" << breakdown.linear
              << " quadratic=" << breakdown.quadratic
              << " recomposed_upper=" << breakdown.recomposed_upper
              << " upper=" << upper
              << " upper_match=" << (breakdown.recomposed_upper == upper ? 1 : 0)
              << " accept=" << (upper < 0.0 ? 1 : 0)
              << "\n";
}

static void print_full_diagnostics(const Function& function,
                                   const std::vector<Box>& boxes) {
  for (std::vector<Box>::const_iterator box = boxes.begin();
       box != boxes.end(); ++box) {
    const taylorData data = function.evalf(
        domain(box->lower), domain(box->upper));
    print_stage_diagnostic(
      "CANDLE_NL_NATIVE_SPECIALIZED_STAGE", box->index, data);
  }
}

static void print_direct_diagnostics(const DirectPlan& plan,
                                     const std::vector<Box>& boxes) {
  for (std::vector<Box>::const_iterator box = boxes.begin();
       box != boxes.end(); ++box) {
    const taylorData data = evaluate_direct_specialized_box(
      plan, domain(box->lower), domain(box->upper));
    print_stage_diagnostic(
      "CANDLE_NL_NATIVE_DIRECT_STAGE", box->index, data);
  }
}

int main(int argc, char** argv) {
  try {
    if (argc < 2 || argc > 7) {
      std::cerr << "usage: " << argv[0]
                << " BOXES.tsv [LIMIT] [--angle-diagnostics]"
                << " [--full-diagnostics] [--direct-specialized]"
                << " [--direct-profile]\n";
      return 2;
    }
    std::size_t limit = std::numeric_limits<std::size_t>::max();
    bool angle_diagnostics = false;
    bool full_diagnostics = false;
    bool direct_specialized = false;
    bool direct_profile_enabled = false;
    for (int index = 2; index < argc; ++index) {
      const std::string option(argv[index]);
      if (option == "--angle-diagnostics") {
        angle_diagnostics = true;
      } else if (option == "--full-diagnostics") {
        full_diagnostics = true;
      } else if (option == "--direct-specialized") {
        direct_specialized = true;
      } else if (option == "--direct-profile") {
        direct_specialized = true;
        direct_profile_enabled = true;
      } else {
        limit = static_cast<std::size_t>(std::stoul(option));
      }
    }
    const std::vector<Box> boxes = read_boxes(argv[1], limit);
    const Function angle = Lib::dih_x;
    const std::chrono::steady_clock::time_point specialized_prepare_start =
      std::chrono::steady_clock::now();
    const Function specialized = benchmark_function(false);
    const std::chrono::steady_clock::time_point specialized_prepare_finish =
      std::chrono::steady_clock::now();
    const std::chrono::steady_clock::time_point generic_prepare_start =
      specialized_prepare_finish;
    const Function generic = benchmark_function(true);
    const std::chrono::steady_clock::time_point generic_prepare_finish =
      std::chrono::steady_clock::now();
    const std::chrono::steady_clock::time_point direct_prepare_start =
      generic_prepare_finish;
    const DirectPlan direct_plan;
    const std::chrono::steady_clock::time_point direct_prepare_finish =
      std::chrono::steady_clock::now();
    const double specialized_preparation_seconds =
      std::chrono::duration<double>(specialized_prepare_finish -
                                    specialized_prepare_start).count();
    const double generic_preparation_seconds =
      std::chrono::duration<double>(generic_prepare_finish -
                                    generic_prepare_start).count();
    const double direct_preparation_seconds =
      std::chrono::duration<double>(direct_prepare_finish -
                                    direct_prepare_start).count();
    const Result specialized_result = evaluate(specialized, boxes);
    const Result generic_result = evaluate(generic, boxes);
    Result direct_result;
    DirectProfile direct_profile;
    if (direct_specialized) {
      direct_result = evaluate_direct(
        direct_plan, boxes,
        direct_profile_enabled ? &direct_profile : nullptr);
    }
    std::cout << std::setprecision(17);
    std::cout << "CANDLE_NL_NATIVE_BOX_SUMMARY mode=specialized boxes=" << boxes.size()
              << " accepted=" << specialized_result.accepted
              << " unstable=" << specialized_result.unstable_boxes
              << " preparation_seconds=" << specialized_preparation_seconds
              << " wall_seconds=" << specialized_result.wall_seconds
              << " domain_seconds=" << specialized_result.domain_seconds
              << " evalf_seconds=" << specialized_result.evalf_seconds
              << " upper_bound_seconds="
              << specialized_result.upper_bound_seconds
              << " checksum=" << specialized_result.checksum << "\n";
    std::cout << "CANDLE_NL_NATIVE_BOX_SUMMARY mode=generic boxes=" << boxes.size()
              << " accepted=" << generic_result.accepted
              << " unstable=" << generic_result.unstable_boxes
              << " preparation_seconds=" << generic_preparation_seconds
              << " wall_seconds=" << generic_result.wall_seconds
              << " domain_seconds=" << generic_result.domain_seconds
              << " evalf_seconds=" << generic_result.evalf_seconds
              << " upper_bound_seconds=" << generic_result.upper_bound_seconds
              << " checksum=" << generic_result.checksum << "\n";
    if (direct_specialized) {
      std::cout << "CANDLE_NL_NATIVE_BOX_SUMMARY mode=direct-specialized boxes="
                << boxes.size()
                << " accepted=" << direct_result.accepted
                << " unstable=" << direct_result.unstable_boxes
                << " preparation_seconds=" << direct_preparation_seconds
                << " wall_seconds=" << direct_result.wall_seconds
                << " domain_seconds=" << direct_result.domain_seconds
                << " evalf_seconds=" << direct_result.evalf_seconds
                << " upper_bound_seconds="
                << direct_result.upper_bound_seconds
                << " checksum=" << direct_result.checksum << "\n";
      if (direct_profile_enabled) {
        std::cout << "CANDLE_NL_NATIVE_DIRECT_PROFILE"
                  << " observations=" << direct_profile.observations
                  << " midpoint_seconds=" << direct_profile.midpoint_seconds
                  << " sqrt_leaf_seconds="
                  << direct_profile.sqrt_leaf_seconds
                  << " angle_tangent_seconds="
                  << direct_profile.angle_tangent_seconds
                  << " angle_hessian_seconds="
                  << direct_profile.angle_hessian_seconds
                  << " assembly_seconds="
                  << direct_profile.assembly_seconds
                  << "\n";
      }
    }
    for (std::size_t index = 0; index < boxes.size(); ++index) {
      std::cout << "CANDLE_NL_NATIVE_BOX_RESULT index=" << boxes[index].index
                << " specialized_upper=" << specialized_result.upper[index]
                << " generic_upper=" << generic_result.upper[index]
                << " generic_minus_specialized="
                << generic_result.upper[index] - specialized_result.upper[index]
                << " specialized_accept=" << (specialized_result.upper[index] < 0.0 ? 1 : 0)
                << " generic_accept=" << (generic_result.upper[index] < 0.0 ? 1 : 0)
                << "\n";
    }
    if (direct_specialized) {
      std::size_t exact_matches = 0;
      double maximum_absolute_difference = 0.0;
      for (std::size_t index = 0; index < boxes.size(); ++index) {
        const double difference =
          direct_result.upper[index] - specialized_result.upper[index];
        if (difference == 0.0) ++exact_matches;
        maximum_absolute_difference = std::max(
          maximum_absolute_difference, std::fabs(difference));
        std::cout << "CANDLE_NL_NATIVE_DIRECT_RESULT index="
                  << boxes[index].index
                  << " direct_upper=" << direct_result.upper[index]
                  << " specialized_upper=" << specialized_result.upper[index]
                  << " direct_minus_specialized=" << difference
                  << " direct_accept="
                  << (direct_result.upper[index] < 0.0 ? 1 : 0)
                  << "\n";
      }
      std::cout << "CANDLE_NL_NATIVE_DIRECT_COMPARE"
                << " boxes=" << boxes.size()
                << " exact_matches=" << exact_matches
                << " maximum_absolute_difference="
                << maximum_absolute_difference
                << "\n";
    }
    if (angle_diagnostics) print_angle_diagnostics(angle, boxes);
    if (full_diagnostics) print_full_diagnostics(specialized, boxes);
    if (full_diagnostics && direct_specialized) {
      print_direct_diagnostics(direct_plan, boxes);
    }
    std::cout << "CANDLE_NL_NATIVE_CERTIFICATE_BOX_COMPARE_OK"
              << " DEVELOPMENT_NON_RELEASE boxes=" << boxes.size()
              << " errors=" << error::get_error_count() << "\n";
    return error::get_error_count() == 0 ? 0 : 1;
  } catch (const std::exception& error) {
    std::cerr << "native certificate box comparison failed: " << error.what() << "\n";
    return 1;
  }
}
