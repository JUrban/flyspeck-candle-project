# Response to Review 1 of the first-fast-NL-theorem plan

Date: 2026-10-20 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Current-head correction (2026-10-21 UTC)

The review explicitly examined CakeML commit `133ab2651`.  My initial
response below did not keep that snapshot boundary sufficiently clear and
incorrectly described all four findings as gaps in the then-current active
branch.  A direct current-head audit changes the disposition as follows:

| Review finding | Disposition on the active branch | Evidence |
|---|---|---|
| 1. sqrt authentication used the original box rather than the actual Taylor operand | **Valid at `133ab2651`; now closed for the case-10173 source path** | `3d299b4d1` recomputes the Taylor-completed variable and authenticates its actual `value_bound`; the complete discriminator checked all 25,038 genuine coordinates; `e6b0e5fe6` introduced the shared actual-operand contract; `68887a9bf` and later source-prefix commits proved its registered source use. |
| 2. magnitude-based evaluator clocks cannot support the production default-clock theorem | **Still open** | `compute_registeredCase10173RawWrapperEvalScript.sml` still contains `cv_size encoded_jobs + 7 < clock`, and the corresponding production root/wrapper path has not yet been replaced completely by structural bounds. |
| 3. recursive head contract dropped the new Hessian condition | **Valid at `133ab2651`; now closed by the unified contract** | `registered_case10173_decimal_authenticated_head_refines` now requires `bounded_case10173_source_actual_sqrt_contract`; the authenticated stream and head-object decomposition expose that same contract.  It recomputes the actual operand and includes domain, root, conversion, second-derivative, sqrt, and following-product checks. |
| 4. kernel integration was underspecified and absent | **Still open** | The exact full authenticated decimal call is not yet installed and exercised through Candle's theorem-producing `Kernel.compute` dispatch at `compute_default_clock`. |

The full-data result already recorded in
`docs/progress/2026-10-20-v4.177-nl-actual-sqrt-operand-contract.md` is the
missing discriminator requested by finding 1: all 25,038 completed operands
differ from their original source boxes; all 25,038 pass the source square-
root certificate on the actual operand; and all 25,038 source-aligned packet
reciprocals match the direct second derivative on that operand.  The proof
does not identify the two operands merely because their rounded reciprocals
happen to agree on this fixture.

Accordingly, the current critical path should not redo findings 1 or 3.  It
is: finish the packet-parametric checked-head composition using the already
proved actual-operand contract; replace the remaining magnitude clocks with
structural bounds; instantiate the 4,173-record recursion; and exercise the
exact genuine call through real default-clock kernel dispatch.  The original
theorem and second-family gates remain after that.

The sections below preserve the original snapshot assessment and proposed
proof shape.  Statements that call findings 1 and 3 “current gaps” should be
read as applying to the review snapshot, not to the active branch after
commits `3d299b4d1` through `19369884d` and their source-evaluation consumers.

## Conclusion

The review identified four real gaps at its audited snapshot, CakeML commit
`133ab2651`.  It did not, and could not, include the actual-operand and unified-
contract work committed later that day.  Against the active branch, findings
1 and 3 are closed; findings 2 and 4 remain production blockers.  The review
therefore improved the plan, but it is not a current status report and should
not be used to infer that the actual-operand authentication still needs to be
designed or implemented.

The 4--7 day working estimate in the original plan is therefore withdrawn.
The next defensible estimate will be made only after both an arbitrary genuine
job theorem and a genuine default-clock kernel-dispatch test are green.

The review was based on an earlier snapshot and some of its measurements have
not yet been independently rerun in this worktree.  That does not weaken the
structural findings below, which are visible directly in the current sources.
Numerical claims from the review will be reproduced before they are promoted
to project evidence.

## 1. Square-root operand mismatch (review snapshot)

**Assessment: confirmed at `133ab2651`; closed on the active branch.**

At `133ab2651`, `bounded_case10173_source_coordinate_sqrt_dd_decimals_exact`
paired the supplied square-root certificate with `source_boxes`.  In contrast,
`candle_cv_fsn_result_sqrt` obtains the second-derivative input by applying
`candle_cv_fs_interval_to_q` to the incoming result's `value_bound`.  Taylor
completion can widen that interval, so equality of the original source box
and the actual operand is neither true in general nor required by the
implementation.

The review's report that the rounded Hessians happen to agree on the two
sample fixtures is useful diagnostic evidence, but it is not the missing
proof.  In particular, it does not establish the literal source domain check,
and a one-unit rounded-endpoint difference is possible near a boundary.

The correction was to authenticate the operand actually consumed by the
literal evaluator.  The implemented route was:

1. define one canonical per-coordinate square-root contract containing the
   computed Taylor operand, root certificate, domain result, first derivative,
   and second derivative;
2. prove that the literal prefix evaluation produces that operand before the
   square-root instruction;
3. make the packet checker recompute or check that contract rather than trust
   a supplied alias;
4. compare all 25,038 actual operands and all associated domain/Hessian
   results against the unchanged source execution; and
5. retain the original source-box comparison only as a diagnostic, not as the
   theorem premise.

If deriving the Taylor operand within the packet checker is too expensive, a
supplied operand may be used only as untrusted data whose equality to the
recomputed operand is checked.  A mere containment claim is insufficient when
the literal evaluator's exact domain verdict and rounded output are being
identified.

## 2. Clock bounds

**Assessment: confirmed as a production seam blocker.**

`registered_case10173_hist_checked_raw_jobs_check_authenticated` requires
`cv_size encoded_jobs + 7 < clock`.  Since `cv_size (Num n) = n`, this is a
magnitude bound, not a recursion-depth bound.  It cannot justify execution at
`compute_default_clock = 1,000,000,000` for genuine numerical payloads of the
reported size.  The analogous root-record proofs must be audited at the same
boundary.

This is a weakness of the proof bound, not evidence that the executable needs
that much fuel.  The durable repair is to prove structural bounds for the
specific traversals: list lengths, fixed tuple shapes, six coordinate steps,
seven root slots, fixed program depth, and 4,173 jobs.  Success at the default
clock is now an explicit prerequisite for kernel registration.  Running at a
larger clock and attempting to transfer success downward is not acceptable.

The first independent reproduction will evaluate the actual current bound for
the first and largest representative jobs and identify every theorem on the
production composition path whose premise exceeds the default clock.  The
result will be a finite clock-obligation ledger, not another isolated bound
patch.

## 3. Recursive head-contract drift (review snapshot)

**Assessment: confirmed at `133ab2651`; closed on the active branch.**

At `133ab2651`, `registered_case10173_decimal_authenticated_head_refines`
included the older source square-root and decimal predicates but omitted the
newly introduced second-derivative predicate.  Therefore that snapshot's
recursion could not consume the intended new premise as the original plan
implied.

The repair was not simply to add the source-box predicate, because finding 1
showed that predicate had the wrong operand.  The corrected authenticator,
local head theorem, and recursive refinement now refer to the shared actual-
operand contract instead of carrying a separate incomplete list of
authentication conjuncts.

## 4. Kernel integration

**Assessment: confirmed; the original Packet 4 named the area but did not map
the proof boundary precisely enough.**

Exporting a closed checker is not by itself a theorem-producing production
route.  The concrete exit test must include all of the following:

- the exact closed checker constant and packed evidence source;
- source-program identity and packed-certificate/job/root identities;
- equation-set identity at the registered call;
- a default-clock ordinary-semantics theorem for that exact call;
- translation and installation in the kernel program;
- the kernel correctness theorem that permits `Kernel.compute` to use the
  specialized implementation;
- mutation tests for each authenticated input boundary; and
- positive trace evidence that the authenticated decimal branch, rather than
  the generic evaluator or a precomputed verdict, produced acceptance.

The generic three-payload seam is reusable machinery, but it does not discharge
any of these call-specific obligations automatically.

## Historical revised sequence from the initial response

The sequence below records how the review was first translated into work.  On
the active branch, steps 2 and the contract-propagation part of step 4 are
complete.  The current sequence is the shorter one stated in the current-head
correction above.

The initial response reorganized the work as follows.

1. **Conditional composition skeleton.**  State the complete theorem chain
   from corrected packet acceptance and default-clock registered evaluation to
   the literal original Flyspeck theorem.  Record every premise in a proof
   ledger before filling the remaining proofs.
2. **Actual Taylor-operand contract.**  Implement the canonical shared
   contract, reproduce the review's mismatch measurements, and run the full
   25,038-coordinate operand/domain/Hessian discriminator.
3. **Local square-root bridge.**  Finish the representation-independent
   endpoint, normalization, negative conversion, and evaluator lemmas now in
   progress, then instantiate them with the actual operand contract.
4. **Unified head theorem and structural clocks.**  propagate the shared
   contract through authentication and recursion, and replace every
   magnitude-based production clock premise with proved structural bounds.
5. **One arbitrary and one closed genuine job.**  Prove the parameterized
   head theorem, instantiate it on genuine data, and exercise the exact call
   through real kernel dispatch at the default clock.
6. **Complete 4,173-job recursion and executable.**  prove exact stream
   consumption, run mutations, and measure preparation, execution, decoding,
   and theorem handoff separately.
7. **Literal original theorem.**  discharge analytic, topology, and
   well-formedness premises and reproduce the theorem twice from clean
   prepared states.
8. **Second-family gate.**  only then estimate the all-NL rollout.

The local algebraic Packet 1 proof could continue because it is generic in its
input interval and was not invalidated by the mismatch.  It was not counted as
closing the source square-root boundary until instantiated with the corrected
actual-operand contract.

## Historical near-term gates and estimates

These were the bounded gates proposed from the review snapshot:

| Gate | Evidence | Focused effort estimate |
|---|---|---:|
| A. Composition/clock ledger | complete conditional theorem statement and every current clock premise enumerated | 3--6 h |
| B. Actual-operand discriminator | two fixtures plus all 25,038 genuine coordinates checked for operand, domain, and Hessian identity | 4--10 h |
| C. Corrected arbitrary-job theorem | one shared contract feeds the literal six-coordinate source evaluation | 8--20 h |
| D. Real default-clock dispatch | exact genuine call produces a theorem through the installed specialized branch | 8--24 h |

These ranges are suitable for controlling the next work packets, not for
predicting completion of the literal theorem.  A new end-to-end estimate will
be issued after gates C and D pass.  If either exposes another semantic or
kernel boundary, work will stop at that boundary for a new bounded diagnosis
rather than continue describing the result as imminent.
