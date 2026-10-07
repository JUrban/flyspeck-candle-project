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
  double checksum;
  std::size_t accepted;
  std::size_t unstable_boxes;
};

static Result evaluate(const Function& function, const std::vector<Box>& boxes) {
  Result result;
  result.checksum = 0.0;
  result.accepted = 0;
  result.unstable_boxes = 0;
  result.upper.reserve(boxes.size());
  const std::chrono::steady_clock::time_point start =
    std::chrono::steady_clock::now();
  for (std::vector<Box>::const_iterator box = boxes.begin(); box != boxes.end(); ++box) {
    double upper = std::numeric_limits<double>::infinity();
    try {
      const taylorData data = function.evalf(domain(box->lower), domain(box->upper));
      upper = data.upperBound();
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

int main(int argc, char** argv) {
  try {
    if (argc < 2 || argc > 4) {
      std::cerr << "usage: " << argv[0]
                << " BOXES.tsv [LIMIT] [--angle-diagnostics]\n";
      return 2;
    }
    std::size_t limit = std::numeric_limits<std::size_t>::max();
    bool angle_diagnostics = false;
    for (int index = 2; index < argc; ++index) {
      const std::string option(argv[index]);
      if (option == "--angle-diagnostics") {
        angle_diagnostics = true;
      } else {
        limit = static_cast<std::size_t>(std::stoul(option));
      }
    }
    const std::vector<Box> boxes = read_boxes(argv[1], limit);
    const Function angle = Lib::dih_x;
    const Function specialized = benchmark_function(false);
    const Function generic = benchmark_function(true);
    const Result specialized_result = evaluate(specialized, boxes);
    const Result generic_result = evaluate(generic, boxes);
    std::cout << std::setprecision(17);
    std::cout << "CANDLE_NL_NATIVE_BOX_SUMMARY mode=specialized boxes=" << boxes.size()
              << " accepted=" << specialized_result.accepted
              << " unstable=" << specialized_result.unstable_boxes
              << " wall_seconds=" << specialized_result.wall_seconds
              << " checksum=" << specialized_result.checksum << "\n";
    std::cout << "CANDLE_NL_NATIVE_BOX_SUMMARY mode=generic boxes=" << boxes.size()
              << " accepted=" << generic_result.accepted
              << " unstable=" << generic_result.unstable_boxes
              << " wall_seconds=" << generic_result.wall_seconds
              << " checksum=" << generic_result.checksum << "\n";
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
    if (angle_diagnostics) print_angle_diagnostics(angle, boxes);
    std::cout << "CANDLE_NL_NATIVE_CERTIFICATE_BOX_COMPARE_OK"
              << " DEVELOPMENT_NON_RELEASE boxes=" << boxes.size()
              << " errors=" << error::get_error_count() << "\n";
    return error::get_error_count() == 0 ? 0 : 1;
  } catch (const std::exception& error) {
    std::cerr << "native certificate box comparison failed: " << error.what() << "\n";
    return 1;
  }
}
