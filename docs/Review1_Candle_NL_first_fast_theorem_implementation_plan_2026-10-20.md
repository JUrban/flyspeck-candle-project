I would keep the overall architecture, but I would not approve the plan unchanged. I found two missing proof obligations, a stale contract, and an underspecified runtime integration step. These could explain further days of apparently “almost finished” work.

  I reviewed the plan at project commit da36090, the newer CakeML work at 133ab2651, and Candle’s NL integration at 65eaad9b.

  1. The new sqrt authentication checks a different input from the one the source actually evaluates.

     The Hessian authentication predicate (review-worktrees/cakeml-fast/candle/prover/compute/compute_boundedCase10173SourceDecimalExactScript.sml:125) checks the reciprocal against the original rational source_box. The literal sqrt implementation (review-worktrees/cakeml-fast/candle/prover/compute/compute_registeredCase10173ResultSqrtEvalScript.sml:52) consumes the variable’s  Taylor-completed value_bound, converted back to rationals.

     Those intervals differ in genuine data. For example, a coordinate whose original lower endpoint is 4 reaches sqrt with lower endpoint 3.999999999999.

     I checked both committed 16-job fixtures: all 192 coordinate operands differed from their original boxes. Their rounded Hessians nevertheless matched in these samples, which is encouraging—but the current authentication does not prove the required connection.

     This distinction can matter: locally, take input [4, 4 + 10⁻¹²] and root certificate [2, 2 + 10⁻¹²]. The certificate passes on that input. Taylor completion expands the lower endpoint below 4, making that same certificate fail the literal source domain check; the rounded second derivative also changes by one unit.

     Required correction: authenticate the domain and Hessian against the actual Taylor operand, or prove an explicit bridge covering that operand. The reported 25,038 comparisons against original source boxes do not settle this obligation. This finding demonstrates a missing refinement step, not an unsound completed theorem.

  2. Existing clock bounds cannot instantiate the registered fast-evaluator theorem.

     The raw-wrapper theorem (review-worktrees/cakeml-fast/candle/prover/compute/compute_registeredCase10173RawWrapperEvalScript.sml:149) requires:

     cv_size encoded_jobs + 7 < clock

     Here cv_size (Num n) = n: it counts numerical magnitude. The first genuine job alone has size 20,035,922,246,620, whereas the registered evaluator requires success at compute_default_clock = 1,000,000,000.

     The root-record bridge has the same problem: its existing bound for the first job exceeds 160 trillion.

     This does not show that execution needs that much fuel. It shows that the current proofs provide bounds too weak for the required seam. Success at a larger clock cannot simply be transferred downward.

     Required correction: prove bounds using list lengths and recursion depth—six coordinates, seven root slots, the fixed program, and 4,173 jobs. Make success within the default clock an explicit gate before kernel registration.

  3. The recursive head contract drops the newly added Hessian condition.

     The authenticated checker now checks bounded_case10173_source_coordinate_sqrt_dd_decimals_exact, but the head-refinement predicate (review-worktrees/cakeml-fast/candle/prover/compute/compute_registeredCase10173AuthenticatedEvalScript.sml:17) does not include it.

     Consequently, packet 1’s intended bridge cannot simply be fed into the existing recursion as described.

     Required correction: update that predicate and its consumers. Prefer one shared packet contract so subsequent authentication changes cannot silently diverge between checker and refinement theorem.

  4. Packet 4 includes substantial kernel integration beyond exporting a checker.

     The compiled kernel currently installs (review-worktrees/cakeml-fast/candle/prover/candle_kernelProgScript.sml:543) older fixed-cell registrations and the existing evaluator chain. It does not install the full authenticated decimal checker. The corrected source-contract export currently prints rejected unconditionally.

     The generic three-payload soundness seam is useful, but its existence does not establish that the eventual executable will use it.

     Required correction: specify the concrete registered checker, where its packed certificates come from, its program-identity check, equation-set match, kernel translation, and corresponding kernel correctness proof. The acceptance test must exercise Candle’s actual theorem-producing Kernel.compute call and demonstrate the authenticated decimal branch was taken.

  There is substantial sound work here. The representation-independent normalization approach is appropriate; the generic historical-item theorem is meaningful progress; and the original-statement adapter exposes explicit computational and topology premises. Retracting the mislabeled runtime result was also correct. I see no present justification for discarding that work and  starting another architecture.

  I would give the worker this revised sequence:

  1. Write the complete conditional composition first, exposing every premise from authenticated packet acceptance through the registered default-clock result to the original theorem.
  2. Correct the sqrt operand contract and rerun the full 25,038-coordinate discriminator against the actual Taylor operands, including domain checks.
  3. Propagate the corrected contract through the head predicate and replace the unusable clock bounds.
  4. Finish the algebraic Hessian bridge and prove one arbitrary authenticated source job.
  5. Exercise a genuine job through the actual kernel dispatch before expanding integration to all 4,173 jobs.
  6. Complete the batch recursion, discharge well-formedness/topology/domain premises, and produce the literal original theorem twice from clean prepared states.
  7. Retain the proposed second-family gate before estimating all-NL work.

  The current 4–7-day estimate is not supported strongly enough to rely on. Re-estimate after the corrected arbitrary-job theorem and an actual kernel-dispatch test pass. The worker has identified the general problem correctly, but has not yet demonstrated that the remaining path is fully mapped.
