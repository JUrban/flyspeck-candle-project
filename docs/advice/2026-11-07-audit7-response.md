# Response to Audit 7: require a matched performance gate

Date: 2026-11-07 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Verdict

The audit's main course correction is valid: closing the semantic route is not
enough.  Before paying for G5P or a verified runtime build, the project needs a
matched case-16594 measurement that shows what the fast callback actually buys
and where its remaining time goes.

One important existing result changes the audit's evidence table.  Case 16594
has already run through the stock fixed-outer-variable `Kernel.compute` route,
including theorem handoff and reconstruction to the literal original Flyspeck
statement.  The October 4 result used 875 numerical cells and 1,749 topology
items, produced theorem digest
`8bb2c1bf3d1c1944d497c0da68b88207`, had no assumptions or axiom growth, and
took approximately **481.18 seconds** under machine contention at about
**18.1 GiB** RSS.  This is recorded in
`docs/progress/2026-10-04-v3.18-direct-case16594-production-leaf.md`.

That result makes the current provisional comparison:

| Route | Scope measured | Elapsed | Peak RSS |
|---|---|---:|---:|
| Stock case-16594 fixed-outer-variable route | closed `Kernel.compute` verdict through original theorem | about 481.18 s | about 18.1 GiB |
| G6 fast callback | type-inferred external CakeML callback, successful complete verdict | 282.29 s | 6,142,976 KiB |
| G4 standalone compiled numerical checker | numerical acceptance on the source-tight/padding-one representation | 10.82 s | not recorded in the G4 report |

The observed G6/stock ratio is therefore only about **1.70x**, not a
demonstrated order-of-magnitude theorem speedup.  The 282.29-second G6 run is
also not yet a theorem-to-theorem measurement: G6 executed a semantically
proved generated CakeML program outside the current Candle runtime, whereas
the 481.18-second stock run returned the original HOL theorem.  G7 and the
eventual runtime integration supply the remaining trusted handoff.  The
existing comparison is useful, but it must not be presented as a matched
production result.

## 1. Stock comparison and the current G7 correction

The audit's requested stock case is therefore not absent, and the stock
checker can express the delta-containing case-16594 source.  Repeating the
same old run immediately would add little while the fast payload is still
changing.

A cheap G7 discriminator has now found a more immediate exact mismatch.  The
accepted G6 payload uses center-radius outer boxes with zero radius padding.
The already-proved complete analytic input contract uses source-rounded outer
boxes with one scale-unit of radius padding.  The G6 representation currently
fails that contract before the 875-cell proof.  This is a representation and
analytic-handoff defect, not a numerical rejection and not a failure of the
original Flyspeck theorem.

The bounded next action remains G7:

1. identify separately which source/center/outer/radius correspondence
   conjunct fails on one genuine coordinate;
2. choose one sound canonical geometry that both the compiled checker and the
   analytic theorem accept;
3. rerun only the cheap numerical and one-cell theorem probes; and
4. prove the complete input contract and reconstruct the original theorem only
   after those probes pass.

No full 875-cell proof, G5P generalization, or verified build should run while
this exact geometry is unresolved.  Once the payload is frozen, the matched
stock/fast timing must use that same source, boxes, radii, certificate and
topology wherever the two checker interfaces permit it.  If an interface
requires a different encoding, conversion time and the exact semantic
equivalence must be reported rather than silently comparing different data.

## 2. What the 282 seconds do and do not establish

The measured components currently are:

- the exact G6 numerical matcher: **145.07 seconds** for 875/875 cells under a
  fixed 4 GiB heap;
- direct topology execution: **0.09 seconds** for 875 jobs and 1,749 tokens;
- the integrated positive callback: **282.29 seconds**; and
- therefore **about 137 seconds remain unattributed by measurement**.

The integrated run includes flat-byte parsing, input construction,
authentication, packet work, numerical matching, topology and result handling.
The existing evidence does not justify assigning the extra 137 seconds among
those components.  Nor does it yet show how much of the roughly 26x gap from
10.82 to 282.29 seconds is evaluator overhead, representation conversion,
duplicate packet work, or a workload difference between the two fixtures.

The next timing probe should instrument one frozen complete callback at coarse
phase boundaries rather than open a broad profiler project.  It should record:

1. external read/parse and `cv` construction;
2. source/header/role authentication;
3. certificate and packet preparation or recomputation;
4. numerical execution;
5. topology execution;
6. callback result decoding;
7. theorem handoff and final source reconstruction; and
8. total elapsed, CPU time and peak RSS.

The same exact callback should be run twice from one prepared executable so
cold preparation is not confused with recurring checking.  The stock control
should likewise start from its sealed prepared state.  This is a bounded
experiment: if phase markers themselves require architectural changes, retain
the current total and postpone finer attribution until after G7.

## 3. Projection and G5P decision

The audit is right that the projection remains incomplete.  The sealed
inventory has 812 source IDs, 7,814 selected leaves, 30,244 partition nodes and
a historical summed `Iarg_leaf` estimate of 3.157725 CPU-hours.  It still lacks
the complete join to certificate cell/topology sizes and a matched stratified
stock sample.  Case 16594 should be included as the already-measured
delta-containing control rather than rediscovered.

The proposed **5x** threshold is a useful warning line, but it is not by itself
the production decision.  A reproducible 1.7x corpus-wide improvement could
still save substantial CPU time if the pending projection is near the current
rough 1,158-CPU-hour stock estimate.  Conversely, a large speedup on one
unrepresentative case would not justify G5P.  The owner decision should use:

- matched end-to-end speed and peak RSS on a stratified sample;
- supported and unsupported fractions;
- cold/reusable preparation and recurring costs;
- the measured cost and risk of G5P, one verified build and state
  reconstruction; and
- uncertainty in extrapolating cell and topology counts to the corpus.

The default sequencing is therefore:

1. finish the bounded G7 geometry correction and original-statement adapter;
2. run the frozen matched case-16594 phase timing;
3. finish the certificate/topology join and a 20--30-leaf stratified stock
   sample;
4. publish the one-page CPU-hour/memory projection; and
5. run G5P only if the measured projection shows material total value or the
   phase timing identifies a concrete, bounded recovery that would do so.

No G8 build is authorized by the present evidence.  The first original theorem
through the fast production route remains **0/1**.
