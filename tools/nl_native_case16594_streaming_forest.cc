#include <memory>

#define main candle_nl_fixed_scale_reference_main
#include "nl_native_fixed_scale_case10173.cc"
#undef main

namespace {

struct StreamingNode {
  std::size_t index = 0;
  int component = 0;
  int parent = -1;
  int side = -1;
  int depth = 0;
  bool leaf = false;
  int axis = 0;
  std::array<int, 2> children{{-1, -1}};
};

std::vector<std::string> read_streaming_job_lines(const char* path) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error(std::string("cannot open jobs: ") + path);
  }
  std::vector<std::string> lines;
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty()) throw std::runtime_error("empty job row");
    lines.push_back(line);
  }
  if (lines.empty()) throw std::runtime_error("empty streaming job set");
  return lines;
}

Job parse_streaming_job(const std::string& line, std::size_t expected_index) {
  const std::vector<std::string> fields = split(line, '\t');
  if (fields.size() != 5) throw std::runtime_error("malformed job row");
  Job job;
  job.index = std::stoi(fields[0]);
  if (job.index != static_cast<int>(expected_index)) {
    throw std::runtime_error("streaming job index drift");
  }
  job.box_certificates = parse_interval_vector<kSqrtSlots>(fields[1]);
  job.center_certificates = parse_interval_vector<kSqrtSlots>(fields[2]);
  job.lower = parse_rational_vector<kDimensions>(fields[3]);
  job.upper = parse_rational_vector<kDimensions>(fields[4]);
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (job.lower[coordinate] > job.upper[coordinate]) {
      throw std::runtime_error("empty streaming job box");
    }
  }
  std::vector<Job> singleton;
  singleton.push_back(job);
  prepare_fixed_sqrt_certificates(singleton);
  return singleton.front();
}

std::vector<StreamingNode> read_streaming_topology(
    const char* path, std::size_t expected_nodes,
    std::vector<std::size_t>& roots) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error(std::string("cannot open topology: ") + path);
  }
  std::vector<StreamingNode> nodes;
  std::string line;
  while (std::getline(input, line)) {
    const std::vector<std::string> fields = split(line, '\t');
    if (fields.size() != 7) {
      throw std::runtime_error("malformed streaming topology row");
    }
    StreamingNode node;
    node.index = static_cast<std::size_t>(std::stoull(fields[0]));
    node.component = std::stoi(fields[1]);
    node.parent = std::stoi(fields[2]);
    node.side = std::stoi(fields[3]);
    node.depth = std::stoi(fields[4]);
    if (fields[5] == "leaf") {
      node.leaf = true;
    } else if (fields[5] != "node") {
      throw std::runtime_error("unknown streaming topology node kind");
    }
    node.axis = std::stoi(fields[6]);
    if (node.index != nodes.size() || node.depth < 0 ||
        (node.leaf && node.axis != 0) ||
        (!node.leaf && (node.axis < 1 || node.axis > 6))) {
      throw std::runtime_error("streaming topology node drift");
    }
    nodes.push_back(node);
  }
  if (nodes.size() != expected_nodes) {
    throw std::runtime_error("streaming topology/job count drift");
  }
  for (StreamingNode& node : nodes) {
    if (node.parent == -1) {
      if (node.side != -1 || node.depth != 0) {
        throw std::runtime_error("malformed streaming root");
      }
      roots.push_back(node.index);
      continue;
    }
    if (node.parent < 0 ||
        static_cast<std::size_t>(node.parent) >= node.index ||
        (node.side != 0 && node.side != 1)) {
      throw std::runtime_error("malformed streaming edge");
    }
    StreamingNode& parent = nodes[static_cast<std::size_t>(node.parent)];
    if (parent.leaf || parent.component != node.component ||
        node.depth != parent.depth + 1 ||
        parent.children[static_cast<std::size_t>(node.side)] != -1) {
      throw std::runtime_error("streaming edge identity drift");
    }
    parent.children[static_cast<std::size_t>(node.side)] =
        static_cast<int>(node.index);
  }
  for (const StreamingNode& node : nodes) {
    if (!node.leaf && (node.children[0] < 0 || node.children[1] < 0)) {
      throw std::runtime_error("streaming internal node lacks children");
    }
  }
  if (roots.empty()) throw std::runtime_error("empty streaming root set");
  return nodes;
}

void validate_streaming_partition(
    const StreamingNode& parent_node, const Job& parent,
    const Job& left, const Job& right) {
  const std::size_t axis = static_cast<std::size_t>(parent_node.axis - 1);
  for (std::size_t coordinate = 0; coordinate < kDimensions; ++coordinate) {
    if (coordinate == axis) {
      if (left.lower[coordinate] != parent.lower[coordinate] ||
          left.upper[coordinate] != right.lower[coordinate] ||
          right.upper[coordinate] != parent.upper[coordinate] ||
          left.lower[coordinate] > left.upper[coordinate] ||
          right.lower[coordinate] > right.upper[coordinate]) {
        throw std::runtime_error("streaming split boundary drift");
      }
    } else if (left.lower[coordinate] != parent.lower[coordinate] ||
               left.upper[coordinate] != parent.upper[coordinate] ||
               right.lower[coordinate] != parent.lower[coordinate] ||
               right.upper[coordinate] != parent.upper[coordinate]) {
      throw std::runtime_error("streaming nonsplit coordinate drift");
    }
  }
}

void configure_streaming_lane(bool historical, bool coordinate_sqrt_values,
                              bool whole_box_jet) {
  Integer binary_scale = 1;
  mpz_mul_2exp(binary_scale.get_mpz_t(), binary_scale.get_mpz_t(), 40);
  kScale = fixed_of_integer(binary_scale);
  kTwoScaleSquared = 2 * kScale * kScale;
  kDyadicScaleBits = 40;
  kCountFixedQuotients = true;
  kUseDyadicShiftFixedQuotient = true;
  kUseSignSpecializedIntervalProducts = true;
  kUseFixedSqrtInverseKernels = true;
  kUseFixedAtanKernel = true;
  kUseTaylorReconstructedBox = true;
  kUseSpecializedDeltaRadicands = true;
  kUseSpecializedDeltaDerivatives = true;
  kUsePreparedSimplePolynomials = true;
  kUseSourceDagCache = true;
  kUseComputedTightSqrtCertificates = true;
  kUseSpecializedDeltaHistoricalDihedrals = historical;
  kUsePreparedCoordinateSqrtValues = coordinate_sqrt_values;
  kUseWholeBoxJet = whole_box_jet;
}

Program prepare_streaming_program(const char* path, bool historical,
                                  bool coordinate_sqrt_values,
                                  bool whole_box_jet) {
  configure_streaming_lane(
      historical, coordinate_sqrt_values, whole_box_jet);
  Program program = read_program(path);
  prepare_simple_polynomials(program);
  if (coordinate_sqrt_values) prepare_coordinate_sqrt_values(program);
  prepare_specialized_delta_radicands(program);
  prepare_specialized_delta_derivatives(program);
  if (historical) prepare_specialized_delta_dihedral_chains(program);
  prepare_source_dag_cache(program);
  return program;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 5) {
      std::cerr << "usage: " << argv[0]
                << " PROGRAM.cval JOBS.tsv TOPOLOGY.tsv "
                << "dag|historical|historical-coordinate|"
                << "historical-whole\n";
      return 2;
    }
    const std::string lane(argv[4]);
    if (lane != "dag" && lane != "historical" &&
        lane != "historical-coordinate" &&
        lane != "historical-whole") {
      throw std::runtime_error("unknown streaming lane");
    }
    const bool historical = lane != "dag";
    const bool coordinate_sqrt_values = lane == "historical-coordinate";
    const bool whole_box_jet = lane == "historical-whole";
    const auto total_begin = std::chrono::steady_clock::now();

    const auto input_begin = std::chrono::steady_clock::now();
    const std::vector<std::string> job_lines =
        read_streaming_job_lines(argv[2]);
    std::vector<std::size_t> roots;
    const std::vector<StreamingNode> nodes = read_streaming_topology(
        argv[3], job_lines.size(), roots);
    const auto input_end = std::chrono::steady_clock::now();

    const auto preparation_begin = std::chrono::steady_clock::now();
    Program program = prepare_streaming_program(
        argv[1], historical, coordinate_sqrt_values, whole_box_jet);
    const auto preparation_end = std::chrono::steady_clock::now();

    std::vector<std::unique_ptr<Job>> parsed_jobs(nodes.size());
    const auto ensure_job = [&job_lines, &parsed_jobs](std::size_t index)
        -> const Job& {
      if (parsed_jobs[index] == nullptr) {
        parsed_jobs[index] = std::make_unique<Job>(
            parse_streaming_job(job_lines[index], index));
      }
      return *parsed_jobs[index];
    };

    std::vector<std::size_t> stack;
    for (auto root = roots.rbegin(); root != roots.rend(); ++root) {
      stack.push_back(*root);
    }
    Counters total_counters;
    std::size_t visit = 0;
    std::size_t terminal_nodes = 0;
    std::size_t terminal_internal_nodes = 0;
    std::size_t rejected_internal_nodes = 0;
    std::size_t rejected_leaves = 0;
    std::size_t domain_subdivisions = 0;
    std::size_t representation_subdivisions = 0;
    std::size_t maximum_depth = 0;
    const auto traversal_begin = std::chrono::steady_clock::now();
    while (!stack.empty()) {
      const std::size_t index = stack.back();
      stack.pop_back();
      const StreamingNode& node = nodes[index];
      const Job& job = ensure_job(index);
      maximum_depth = std::max(
          maximum_depth, static_cast<std::size_t>(node.depth));

      Evaluation evaluation{};
      bool domain_subdivision = false;
      bool representation_subdivision = false;
      try {
        evaluation = whole_box_jet
            ? evaluate_job_whole_box(program, job)
            : evaluate_job(
                program, job, PolynomialMode::kBaseline, -1, -1, false,
                nullptr, nullptr);
      } catch (const std::exception& error) {
        const std::string message(error.what());
        if (message == "invalid fixed square-root input" ||
            message.find("domain failure") != std::string::npos) {
          domain_subdivision = true;
          ++domain_subdivisions;
        } else if (message == "invalid hardware fixed conversion" ||
                   message == "computed square-root enclosure failure") {
          representation_subdivision = true;
          ++representation_subdivisions;
        } else {
          throw std::runtime_error(
              "streaming node " + std::to_string(index) + ": " +
              error.what());
        }
      }
      add_counters(total_counters, evaluation.counters);

      std::string decision;
      if (evaluation.upper < 0) {
        decision = "prune";
        ++terminal_nodes;
        if (!node.leaf) ++terminal_internal_nodes;
      } else if (node.leaf) {
        decision = "reject";
        ++rejected_leaves;
      } else {
        decision = "split";
        ++rejected_internal_nodes;
        const std::size_t left = static_cast<std::size_t>(node.children[0]);
        const std::size_t right = static_cast<std::size_t>(node.children[1]);
        const Job& left_job = ensure_job(left);
        const Job& right_job = ensure_job(right);
        validate_streaming_partition(node, job, left_job, right_job);
        stack.push_back(right);
        stack.push_back(left);
      }
      std::cout << "CANDLE_NL_NATIVE_STREAMING_RESULT"
                << " visit=" << visit
                << " node=" << index
                << " upper=" << evaluation.upper.get_str()
                << " decision=" << decision
                << " domain_subdivision="
                << (domain_subdivision ? 1 : 0)
                << " representation_subdivision="
                << (representation_subdivision ? 1 : 0) << "\n";
      ++visit;
    }
    const auto traversal_end = std::chrono::steady_clock::now();
    const auto total_end = traversal_end;
    const auto seconds = [](const auto& begin, const auto& end) {
      return std::chrono::duration<double>(end - begin).count();
    };
    std::cout << std::setprecision(17)
              << "CANDLE_NL_NATIVE_STREAMING_SUMMARY"
              << " mode=" << lane
              << " backend=" << kFixedBackend
              << " total_nodes=" << nodes.size()
              << " components=" << roots.size()
              << " visited_nodes=" << visit
              << " terminal_nodes=" << terminal_nodes
              << " terminal_internal_nodes=" << terminal_internal_nodes
              << " rejected_internal_nodes=" << rejected_internal_nodes
              << " rejected_leaves=" << rejected_leaves
              << " domain_subdivisions=" << domain_subdivisions
              << " representation_subdivisions="
              << representation_subdivisions
              << " maximum_depth=" << maximum_depth
              << " input_seconds=" << seconds(input_begin, input_end)
              << " reusable_preparation_seconds="
              << seconds(preparation_begin, preparation_end)
              << " traversal_seconds="
              << seconds(traversal_begin, traversal_end)
              << " total_seconds=" << seconds(total_begin, total_end)
              << " floor_quotients=" << kFloorFixedQuotientCalls
              << " ceil_quotients=" << kCeilFixedQuotientCalls
              << " dyadic_shift_quotients="
              << kDyadicShiftFixedQuotientCalls
              << " dyadic_fallback_quotients="
              << kDyadicFallbackFixedQuotientCalls
              << " interval_products=" << total_counters.interval_products
              << " interval_endpoint_products="
              << total_counters.interval_endpoint_products
              << " completed_results="
              << total_counters.completed_results
              << " sqrt_steps=" << total_counters.sqrt_steps
              << " inverse_steps=" << total_counters.inverse_steps
              << " atan_steps=" << total_counters.atan_steps << "\n";
    if (rejected_leaves != 0) {
      throw std::runtime_error("streaming forest has rejected leaves");
    }
    std::cout << "CANDLE_NL_NATIVE_STREAMING_FOREST_OK "
              << "DEVELOPMENT_NON_RELEASE mode=" << lane << "\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "CANDLE_NL_NATIVE_STREAMING_FOREST_ERROR: "
              << error.what() << "\n";
    return 1;
  }
}
