# Response to Audit 8: accept the case-only demonstrator, retain the production boundary

Date: 2026-11-08 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Verdict

The proposed scope is the right next vertical slice: finish one explicitly
case-16594-only runtime demonstrator, obtain the literal original theorem, and
then treat plan-generic G5P as a separate production phase.  The demonstrator
does not make the fast checker usable for all nonlinear Flyspeck records.

The file is an external review, so its `Owner decision` heading is not itself
used as project authority.  Its scope is nevertheless consistent with the
owner's current direction and with the active implementation: the exact
case-16594 branch is tried first, while a proved general evaluator remains the
fallback.  The public production metric remains **0/1 fast original
theorems** until G9 succeeds.

Two factual corrections are important:

1. The 8--10-hour verified executable/bootstrap build has **not** started.
   Current work is closing and canonicalising bounded HOL4/CakeML translation
   layers so that such a build is justified rather than speculative.
2. The new miss path first calls `compute_pure_fast_eval`; if that returns
   `NONE`, `compute_with` falls through to the existing verified evaluator.
   The stock measurements used the current ordinary `Kernel.compute`, not
   this newly composed two-stage miss path.  Therefore comparable fallback
   performance is a required new-binary regression, not an already established
   fact.

## Current implementation boundary

The implementation branch is
`codex/nl-g7-fast-theorem-v1`.  Its current source head is `c11c125a4`.
The callback composition is:

```text
case-16594 authenticated direct checker
  -> on hit: return the checked result
  -> on miss: compute_pure_fast_eval
       -> on its miss: compute_with's existing verified evaluator
```

This is G5C-shaped, payload-generic/program-fixed behavior.  It is not G5P:
the authenticated program, header shape, 875-cell plan and source streams are
still case-specific.

The following canonical build gates are now green:

| Gate | Result | Elapsed | Peak RSS | Swaps |
|---|---|---:|---:|---:|
| direct dispatch, sound chain and translated program state | 3/3 theories | 10m37s | 12,952,328 KiB | 0 |
| standard 123-function Candle kernel translated on top of that saved state | 1/1 theory | 12m42s | 17,596,272 KiB | 0 |

Both artifact sets were rebuilt in their canonical source directories and
checked for scratch-worktree references.  The standard kernel successfully
loaded the direct checker's 881-constant saved translator state and registered
Candle's kernel types above it.  This closes the most immediate representation
mismatch risk; it does not produce a runtime executable or an original theorem.

The next wrapper build was stopped at a loader-only preflight: the freshly
generated `ml_hol_kernel_funsProgTheory.sml.d` dependency record named only
`runtime_checkTheory`, omitting `holAxiomsSyntaxTheory`,
`holKernelPmatchTheory`, `ml_monadStoreTheory` and the direct-checker program
theory.  Merely adding their source directories on the first retry did not
invalidate that cached dependency record, so the retry reproduced the same
failure before wrapper translation.  No wrapper theorem failed.

A 4.6-second dependency-only probe with `--rebuild_deps` and the explicit
canonical include set regenerated the record and now names all five required
theory objects.  A subsequent wrapper probe established the remaining half of
the defect: the existing textual `.uo` loader manifest had been emitted from
the old dependency record and still named only the direct-checker program and
`runtime_checkTheory`.  Updating `.sml.d` does not retroactively rewrite that
loader manifest.  This exact failure is recorded as LR-223.  The generated
`.sig`, `.sml` and `.dat` proof products must be preserved while only the
`.ui`/`.uo` loader manifests are regenerated from the complete dependency
record and then checked directly.  The eventual long kernel build remains
fail-closed until LR-223 has a frozen executable dependency-closure
discriminator.

## Disposition of the audit's preconditions

| Proposed precondition | Disposition now |
|---|---|
| 1. Equation/call-shape freeze | **Required, not yet closed.** Freeze only after the wrapper and semantic bridge sources are green. Hash the exact recognized equations, literal payload/call encoder, callback definitions and generated translation artifacts. Re-export the call from the current Candle construction and byte-compare it immediately before the verified runtime build. No callback-contract edits after that freeze without cancelling the build authorization. |
| 2. Minimal prepared state | **Required, still open.** The old v521 stock checkpoint is useful as a workload reference but cannot be restored into a changed binary. Name and rehearse the minimal source replay on the current binary, then construct and time it afresh on the new binary. Record cold construction, ready marker, peak RSS and retained-state size separately. |
| 3. Exact build preflight | **Partially closed.** The first two bounded translation layers now have measured cones and costs above. Still required before the full executable build are the wrapper, thin `candle_kernelProg`, semantic `candle_kernel_funs` proof, exact compiler/link cone, per-stage caps and the 8--10-hour baseline reconciliation. Silence never authorizes a timeout increase. |
| 4. Exact integrated call on the G6 executable | **Required, not yet repeated on the final bytes.** The old complete G6 run was valuable, but the final source-rounded/padding-one call and the exact frozen callback must be tested together. The same call-construction code intended for G9 must return `SOME`; any mismatch stops the route before bootstrap. |
| 5. Non-16594 fallback regression | **Required after the new binary exists.** `139514/3` is a good control because its exact original theorem and controlled stock timing already exist. Require identical conclusion digest, assumptions and axiom delta. Measure the new two-stage miss path rather than claiming that the old stock measurement already covered it. |

The equation freeze and integrated-call check are preconditions to the
**full verified runtime/bootstrap build**.  The bounded proof/translation
builds above are the probes needed to make that freeze meaningful; they are
not being reported as G8 completion.

## G9 exit contract

The audit's proposed G9 contract is accepted, with one additional explicit
observation: evidence must show that the genuine call hit the case-16594
branch, rather than merely obtaining a theorem after fallback.

G9 therefore requires all of the following on a fresh compatible state:

1. the exact frozen call is authenticated and the fast branch is observed;
2. `Kernel.compute` returns the result used by the existing analytic adapter;
3. the literal original case-16594 theorem is reconstructed with conclusion
   digest `8bb2c1bf3d1c1944d497c0da68b88207`;
4. the theorem has no assumptions and no axiom growth;
5. cold prepared-state construction, recurring `Kernel.compute`, decoding and
   handoff, reconstruction, total CPU/wall time and peak RSS are separated;
6. the result is compared with the controlled stock median of 479.50 CPU
   seconds post-restore and 463.07 CPU seconds in `Kernel.compute`; and
7. the non-16594 fallback control produces the same original theorem and a
   reported performance ratio.

If the genuine call misses the branch, the exact equation, call-shape, payload
or representation mismatch is the result.  It must not be patched around
inside the long build or hidden by the fallback.

## Parallel suggestions

The suggested side work is useful but subordinate to the first theorem:

- G5P remains the next architecture phase, not part of this demonstrator.
  A four-hour definition/semantic discriminator is reasonable after the
  frozen G5C call has passed its final executable probe.
- Exact theorems already exist for `161160/23` and `TSKAJXY/26`, but their
  controlled phase timings remain open as recorded in v4.390.  They should
  run only on capacity that does not contend with the production build.
- The current 17.223-GiB stock peak is not yet a measurement of the new
  binary's minimal prepared state.  That state needs its own cold-build and
  retained-size measurement.
- Existing restored-state scripts supply useful pieces of a stock batch
  runner, but a full corpus scheduler with bounded retries and shared
  preparation is not yet claimed.

The immediate sequence is therefore: close the bounded wrapper and semantic
bridge; freeze and hash the exact callback/call contract; run the final G6
integrated-call probe; publish the measured full-build plan and stop rules;
then make one verified demonstrator build and attempt G9.  G5P follows the
first theorem rather than being conflated with it.

## Implementation note after the review

The bounded work continued after this response was drafted; the full verified
runtime/bootstrap build still has not started.

1. A non-mutating direct load of the repaired
   `ml_hol_kernel_funsProgTheory` manifest passed in 129.378 seconds with
   6,746,036 KiB peak RSS.  It loaded all six required references, emitted one
   authenticated success marker, changed no file in the 6,643-file canonical
   object snapshot, and confirmed that the proved `.dat`, `.sig` and `.sml`
   products retained their pre-repair hashes.
2. The one-theory direct-compute wrapper then exported successfully.  The
   logical build took 5m23s; the complete Holmake invocation took 9m34s and
   peaked at 19,150,160 KiB with zero swaps.  It produced
   `compute_case16594_direct_genuine_fast_v_thm`, `compute_v_def` and
   `compute_v_thm`.  An independent load showed that `compute_v_thm` has zero
   hypotheses and exactly relates `compute_v` to
   `compute_case16594_direct_genuine_fast`.  Holmake returned status 1 only
   after reporting `[1/1]` and exporting the theory, because it also requested
   the unrelated absent `misc/cakeml-heap` target; the exported theory was
   authenticated directly rather than rebuilt.
3. The thin `candle_kernelProg` probe then found two further cache defects and
   stopped at each one.  First, `print_thmTheory` dated 2026-10-21 recorded the
   identity of a `holKernelTheory` parent which had been rebuilt on 2026-10-31.
   The small child theory was refreshed alone in 31 seconds, with its old
   artifacts retained under a hash receipt; a 14-second direct load of its
   zero-hypothesis theorem then passed.
4. The next probe exposed a stale
   `candle_kernelProgScript.sml.d` generated for the superseded monolithic
   kernel source.  It directly named more than one hundred objects in the old
   dirty `cakeml-nl-packed-refinement-v1` worktree, including obsolete
   case-10173 theories, and therefore loaded an incompatible historical
   dihedral parent pair.  A bounded dependency-only regeneration from the
   current 67-line source took 5.03 seconds.  That first reduced record had 13
   inputs and removed every dirty-root, case-10173 and historical-dihedral
   entry, but a subsequent static compile probe correctly showed it had also
   omitted four libraries declared by the source.  No one-library retry was
   made.  A new executable preflight now compares every `Libs` and `Ancestors`
   declaration with the record.  It rejected all four omissions together;
   regeneration with the complete canonical include set then produced and
   froze a 17-input record containing all six libraries and all three
   ancestors, with zero dirty or obsolete entries.  All canonical `.uo` and
   `.ui` manifests were separately scanned and already had zero dirty-root
   paths.
5. After the semantic bridge edit, a nominal `candle_kernel_funs` target
   announced eight theory nodes and began rebuilding local invariant
   prerequisites because dependency-file regeneration had made their metadata
   newer than the copied theory products.  The run was terminated after 49
   seconds rather than accepting an unplanned cone.  Its completed
   `ast_extras` product was byte-identical to established copies; its
   interrupted `perms` product was restored to the observed pre-run `.dat`
   hash from an identical-source artifact copy.  The proof lane is now split
   into four isolated, retained stages: `candle_kernel_vals`,
   `candle_prover_inv`, `candle_kernel_perms`, then `candle_kernel_funs`.
   Historical costs are about 1m48s for values, 5m45s for permissions and
   2m45s for final soundness; each stage receives its own cap and must finish
   before the next starts.

6. The thin `candle_kernelProg` theory subsequently exported and was
   authenticated in a fresh process.  Its build took 6m28s, peaked at
   19,002,632 KiB and swapped zero pages.  Both its `candle_prog_thm` and the
   direct wrapper's `compute_v_thm` have zero hypotheses.  A separate
   semantic probe also loaded the direct case-16594 theorem in 1m12s and
   confirmed its zero-hypothesis, state-preserving success contract.  These
   results close the thin-program layer; they do not close the kernel
   soundness proof or build a runtime.
7. The first isolated `candle_kernel_vals` stage stopped after 2m39s, with
   7,461,388 KiB peak RSS and before any later proof stage was started.  The
   exact failure is a missing theorem named
   `bounded_case16594_prepared_program_ok_refs_def`.  The translated program
   theory does contain the closed Boolean value theorem and the associated
   `bounded_case16594_prepared_program_ok_refs` constant, but the translator
   did not export the reference-store definition.  Its translator code treats
   that reference-definition simplification as best effort and silently
   catches a failure, while the generic `candle_kernel_vals` proof later
   assumes every closed value mentioned by `the_context` has a saved
   `_refs_def` theorem.  This is a narrow proof-plumbing mismatch, not a
   failure of the numerical checker or its semantic theorem.

At that point the next permitted retry was only the isolated values stage,
after a cheap proof established the correct treatment of all closed values'
reference stores.  It was not permitted to synthesize an unjustified equation
or skip the generic kernel-location obligation.  The subsequent bounded retry
and its more fundamental finding are recorded below.  `candle_prover_inv`,
`candle_kernel_perms`, `candle_kernel_funs`, the executable/compiler build and
the 8--10-hour verified runtime build have not started.  LR-223 through LR-225
require dependency-record, parent-identity and actual execution-cone checks
before any long kernel build; the full runtime build remains fail-closed.

## Further bounded result: representation mismatch found before the long build

The reference-store issue was enumerated rather than patched one theorem at a
time.  Of 50 closed values in `the_context`, 38 have exported definitions
showing an empty reference contribution and 12 do not.  The missing set is the
two prepared-program values and ten closed arctangent constants.  Inspection
of `ml_translatorLib.sml` explains the pattern: the translator saves a
`*_refs_def` only when its syntactic `no_change_refs` proof succeeds, and
silently replaces failure with `TRUTH`; closed values computed through
function application therefore need not receive such a theorem.

A symbolic repair was then tested in an isolated copy.  It retained the 12
reference-list constants symbolically rather than assuming that they are
empty, and separately proved the generic `refs_defs` and `kernel_locs`
obligations.  This run reached the real `evaluate_tm_check` proof in 4m29s,
peaked at 7,522,832 KiB and used no swap.  Thus the missing exported equations
were not the final blocker.

The proof then exposed a genuine translated-representation mismatch.  The
first diagnostic compared the composed relation with the pattern at the point
of failure:

```text
HOL term constructor in TERM_TYPE_def:       TypeStamp «Var_1» 39
Candle kernel pattern expected by the proof: TypeStamp «Var»   39
```

The saved translator state confirms the allocation order:

```text
compute_syntax.compute_exp.Var -> «Var»
holSyntax.term.Var             -> «Var_1»
compute_exec.ce.Var            -> «Var_2»
```

An authenticated comparison with a genuinely stock Candle artifact then made
the mismatch more precise: stock `TERM_TYPE_def` is
`TypeStamp «Var» 22`, not either side of the composed `Var_1/39` relation.
The `39` in the initial diagnostic was already a symptom of registering the
direct-checker datatypes before the standard kernel datatypes.  A stale
non-stock artifact elsewhere also contained `Var_1/39`; it was rejected as a
reference rather than used to normalize the mistake.

The source-level cause is bounded and reproducible.  Commit `7239dc511`
changed `ml_hol_kernel_funsProg` from extending `basisProg` to extending the
case-16594 checker program.  That put the checker datatype registrations ahead
of the kernel registrations, shifting both the constructor name and the type
stamp.  A successful `Var` pattern therefore cannot establish the generated
`TERM_TYPE` relation.  This is not a numerical-checker failure and cannot be
repaired soundly by changing only the final tactic or theorem.

The candidate correction establishes the exact standard kernel datatype ABI
as an explicit program prefix before adding any checker types.  The ordinary
kernel translation later consumes those already-registered types; ordinary
datatype registration is idempotent, while the exception registration is
looked up rather than repeated.  This keeps the monadic checker layout and
avoids rebasing it after a monadic kernel program.

This finding materially strengthens audit preconditions 1 and 3.  The frozen
contract must include not only equations and call shape but also the translated
constructor-name/stamp ownership used by the standard kernel.  A cheap type-
registration probe must show, at minimum, that `holSyntax.term.Var` owns
`«Var»` at stock stamp 22 and that direct-checker constructors receive
non-conflicting names before any affected translation cone or runtime
bootstrap is admitted.

The smallest prefix probe is green: it produces `holSyntax.term.Var -> Var`
and `TERM_TYPE_def` at `Var/22`.  The canonical prefix and the complete
30-node program cone through `compute_evalPureBaseProg` have now also rebuilt
under per-theory five-minute caps.  The final theory independently emitted
`compute_syntax.compute_exp.Var -> Var_1` at stamp 40.  Its 4m10s wall time
was the longest final-stage measurement, its peak RSS was 10,922,588 KiB, and
it swapped zero pages.  The exact remaining downstream checker-program cone
must be rebuilt with the same discipline before the isolated values proof is
retried.  It is explicitly not permitted to edit `evaluate_tm_check` to
accept the wrong representation.

## Bottom line after review

Audit 8 is useful as an acceptance checklist and its case-only demonstrator
scope matches the owner's current direction.  It is not itself an owner
authorization despite its heading, and its parallel-work suggestions are
optional rather than prerequisites.  The critical path remains the
case-16594 demonstrator; G5P and extra projection timings should not contend
with it.

The work is progressing through short discriminating stages rather than an
unobserved long build.  The current public metric is still **0 fast original
theorems**.  The constructor-ownership probe is now green against the stock
`Var/22` ABI, and the first complete 30-node affected program cone preserves
the distinct checker `Var_1/40` ABI.  The correction is not yet accepted until
the remaining downstream program nodes and the isolated `candle_kernel_vals`
proof pass with that same state.  That values proof is the next
evidence-bearing milestone.  Only after all remaining bounded proof stages,
the representation and equation/call freeze, and the exact integrated-call
check pass is the one long demonstrator build justified.

## Post-review downstream stop

The next exact cone was enumerated before execution: eleven program theories
connect `compute_evalPureBaseProg` to
`compute_boundedCase16594WordWholeDirectFastChainProg`.  The same runner used
one fresh process per theory, a fixed 300-second cap, an exact-one-created-
theory check, a changed-artifact check and a zero-swap check.

The first node, `compute_boundedCase16594WordConversionProg`, passed in 3m27s
with 6,876,156 KiB peak RSS and zero swap.  The second node,
`compute_boundedCase16594WordRuntimeBaseProg`, reached the translation of
`bounded_case16594_object_dispatch_cell0_ceqs` but hit the unchanged
300-second cap and produced no completed theory artifact.  The runner stopped
with status 124; none of the remaining nine nodes ran.  No timeout was raised
and no retry was started.

This is not a semantic, ABI or numerical failure.  It is a bounded build-cost
finding about translating one 104,726-byte closed definition containing 175
CEQ entries above the newly corrected prefix.  Before any retry, the next
decision must be based on a cheaper discriminator: either demonstrate a
sound way to retain or split that exact value translation while preserving its
logical value and call identity, or establish an independently justified
stage budget.  Repeating the same five-minute attempt or silently extending
it would violate the stop rule.

## Bounded resolution of the oversized CEQ translation

The required cheap discriminator has now been run.  It did not alter the
case-16594 source data or relax the five-minute cap.

The original constant is a 175-entry closed list.  Three independent
translation probes above the same corrected predecessor state established
that the problem is monolithic translation cost rather than one pathological
entry:

| Probe | Translation only | Cold total | Peak RSS | Swap |
|---|---:|---:|---:|---:|
| entries 0--15 | 36.663s | 3m52s | 7,770,316 KiB | 0 |
| entries 16--31 | 40.267s | 3m46s | 7,657,096 KiB | 0 |
| heavy tail, entries 167--174 | 37.910s | 3m56s | 10,723,516 KiB | 0 |

The tail includes the approximately 10-KiB specialized dispatch term, so the
probe covers the largest individual payload rather than only easy prefix
data.  More importantly, this was followed by a sound assembly experiment,
not merely a timing extrapolation.  HOL proved that the unchanged first
32-entry literal equals the append of two separately translated 16-entry
constants, and the translator then emitted the value theorem for the
original constant from that proved alternative equation.  Assembly
translation took 51.129 seconds; the cold process took 4m49s, peaked at
6,525,280 KiB and used no swap.

The production implementation therefore divides the unchanged 175-entry
constant into eleven sequential chunks of at most sixteen entries.  A single
assembly theory proves exact equality between their append and the original
constant and translates that theorem.  The downstream runtime continues to
refer to the original constant; no callback equation, entry, order or call
identity is changed.  Each chunk, the assembly proof, and the runtime-base
theory is a separate fresh process with the original 300-second cap and
artifact/zero-swap checks.  This staged production rebuild is in progress as
of this update; it is not the verified runtime/bootstrap build and it will
stop at its first failed stage.
