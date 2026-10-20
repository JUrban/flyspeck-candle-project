# Response to Review 1 of the first-fast-NL-theorem plan

Date: 2026-10-20 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Conclusion

The review identifies real gaps in the plan.  I agree with its four main
findings after checking them against the active CakeML branch.  In particular,
the first finding changes the critical path: the new square-root Hessian
authentication is currently stated over the original source box, while the
literal historical evaluator applies `q_dim_jet_sqrt_dd` to the
Taylor-completed `value_bound`.  The current generic algebraic bridge remains
useful, but it cannot close the source evaluator until the certificate is
authenticated against that actual operand or a sound bridge to it is proved.

The 4--7 day working estimate in the original plan is therefore withdrawn.
The next defensible estimate will be made only after both an arbitrary genuine
job theorem and a genuine default-clock kernel-dispatch test are green.

The review was based on an earlier snapshot and some of its measurements have
not yet been independently rerun in this worktree.  That does not weaken the
structural findings below, which are visible directly in the current sources.
Numerical claims from the review will be reproduced before they are promoted
to project evidence.

## 1. Square-root operand mismatch

**Assessment: confirmed and critical.**

`bounded_case10173_source_coordinate_sqrt_dd_decimals_exact` currently pairs
the supplied square-root certificate with `source_boxes`.  In contrast,
`candle_cv_fsn_result_sqrt` obtains the second-derivative input by applying
`candle_cv_fs_interval_to_q` to the incoming result's `value_bound`.  Taylor
completion can widen that interval, so equality of the original source box
and the actual operand is neither true in general nor required by the
implementation.

The review's report that the rounded Hessians happen to agree on the two
sample fixtures is useful diagnostic evidence, but it is not the missing
proof.  In particular, it does not establish the literal source domain check,
and a one-unit rounded-endpoint difference is possible near a boundary.

The correction is to authenticate the operand actually consumed by the
literal evaluator.  The preferred route is:

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

## 3. Recursive head-contract drift

**Assessment: confirmed.**

`registered_case10173_decimal_authenticated_head_refines` includes the older
source square-root and decimal predicates but omits the newly introduced
second-derivative predicate.  Therefore the existing recursion cannot consume
the intended new premise as the original plan implied.

The immediate repair is not simply to add the current source-box predicate,
because finding 1 shows that predicate has the wrong operand.  After defining
the corrected actual-operand contract, the authenticator, local head theorem,
and recursive refinement will all refer to one shared versioned packet
contract.  Separate handwritten lists of authentication conjuncts will be
removed or mechanically derived from that contract.

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

## Revised critical sequence

The active work is reorganized as follows.

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

The local algebraic Packet 1 proof can continue because it is generic in its
input interval and is not invalidated by the mismatch.  It will no longer be
reported as closing the source square-root boundary until it is instantiated
with the corrected actual-operand contract.

## Near-term gates and estimates

The next bounded gates are:

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
