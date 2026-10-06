# Response to the native nonlinear comparison audit

Date: 2026-10-06 UTC

Status: **DEVELOPMENT / NON-RELEASE**. This assessment and its diagnostic
programs make no S1, S2, S3, qualification, promotion, or release claim.

## Decision

The audit changes the next nonlinear experiment from another local evaluator
rewrite to a matched **enclosure-quality and execution-boundary comparison on
the genuine captured boxes** of parent `8657368829`.

The smallest useful experiment has three initial lanes:

1. the historical C++ specialized `dih_x` primitive;
2. the historical C++ generic composition of delta, square root, reciprocal,
   arctangent, and arithmetic; and
3. Candle's current proved fixed-nonlinear reflected checker.

All lanes receive the same exported certificate boxes. The primary outputs are
the numerical upper bound and acceptance slack for each box, not only elapsed
time. This directly tests whether the current architecture pays for looser
enclosures and therefore more subdivision, or mostly pays to execute a similar
numerical calculation through the reflected representation.

The C++ generic lane is **not** a native implementation of Candle's exact
fixed-scale algorithm. Consequently, lane 2 versus lane 3 is initially a
combined algorithm/representation/runtime comparison. A literal native port
of the reflected fixed-scale equations is a second-stage discriminator only
if the first comparison leaves that distinction material. Treating the generic
C++ result as a pure interpreter-overhead baseline would overstate what the
audit establishes.

## What the audit adds

The source observations fit the measured project evidence:

- the complete current reflected result for case 10173 spends 434.364 seconds
  in `Kernel.compute` and 46.468 seconds in theorem handoff; removing handoff
  cannot provide an order-of-magnitude gain;
- topology checking is already negligible relative to numerical evaluation;
- the 16 GiB heap removed the previously measured catastrophic GC regime, but
  allocation and residual collection have not been shown to be cheap;
- the exact current formula performs generic dense six-dimensional propagation
  through seven square roots and the composed dihedral expression; and
- the audit's controlled C++ search loses both time and enclosure quality when
  specialized dihedral evaluation is replaced by generic composition.

I reproduced the supplied audit on this currently loaded machine from its
hash-pinned sources and compatibility patch. The accepted local diagnostic
run measured:

| C++ diagnostic | Specialized | Generic composition |
|---|---:|---:|
| Complete search | 0.1414 s, 5,334 visits | 6.9455 s, 84,016 visits |
| 10,000 synthetic subboxes | 0.2123 s | 0.7985 s |

The local absolute times differ from the supplied run, as expected on a
different and concurrently loaded machine. The structural result is stable:
the generic search made **15.75 times** as many visits and took about **49
times** as long in this run. This remains an unverified numerical diagnostic,
not a prediction of Candle speedup.

## Checks against work already completed

The proposed experiment does not repeat the unsuccessful sharing work:

- explicit interval endpoint-product sharing was about eight times slower;
- exact nonlinear `let` sharing regressed the matched 128-cell checker by
  8.04%;
- the proved Hessian-only multiplication projection gave no stable batch
  benefit;
- fixed outer additions and multiplications were indistinguishable from timing
  noise in the duplicate-step profile; and
- the ordinary untrusted executor was another interpreter of the same encoded
  equations and ran 2.6 times slower than `Kernel.compute`; it was not a useful
  native numerical baseline.

There is also an important qualification to the audit's square-root operation
count. The matched current-checker profile found that the seven square-root
steps are the largest aggregate nonlinear class, but their estimated cost per
instruction was similar to inverse/arctangent/pi-half. This does not support a
standalone `sqrt(x_i)` implementation solely from source counts. A sparse
coordinate-square-root instruction remains plausible, but it should follow
the matched bound/timing result or a profile showing that it improves the
actual complete program.

The proved lazy polynomial completion is already the successful form of
avoiding unnecessary intermediate work. It reduced the complete 4,173-cell
checker from a 661.785-second mean to 582.241 seconds while preserving exact
results. It remains available and is not replaced by this experiment.

## Concrete experiment

### Dataset

Export all **4,173** exact final boxes from the authenticated case-10173 plan.
The export contains only the six rational lower and upper endpoints and a
monotone cell index. It does not export or trust a numerical verdict. One
capture is then reusable by every native diagnostic.

Use the first 128 boxes for the initial reflected upper-bound probe because the
same prefix already has stable performance measurements. Run the native lanes
on both that prefix and the full 4,173-box dataset; native cost is expected to
be small. If the prefix is unrepresentative in slack or acceptance, select an
easy, median, and tight stratum from the full native results and extend the
reflected probe to those indices before changing the checker.

### Measurements

For each lane record:

- upper bound and `-upper` acceptance slack per box;
- accepted, rejected, and numerically unstable box counts;
- distribution of generic-minus-specialized upper bounds;
- numerical execution time, source/data conversion time, and theorem handoff
  where applicable;
- peak RSS and sampled GC/process behavior for Candle; and
- cold preparation separately from warm recurring batch cost.

The box coordinates are converted to binary64 with exact GMP rational
comparison and outward-directed endpoint adjustment in the C++ diagnostic.
This avoids silently shrinking a rational certificate box during conversion.
It still does not make the C++ result formal evidence.

### Attribution matrix

| Comparison | What it tests |
|---|---|
| Specialized C++ vs generic C++ | Extra mathematical work and enclosure loss from generic composition, without Candle or proof construction |
| Generic C++ vs Candle | Initial combined signal for algorithm details, exact/fixed representation, evaluator, allocation, and GC |
| Exact native fixed-scale port vs Candle, if needed | Representation-independent cost of executing the same reflected numerical algorithm |
| Current Candle vs a proved specialized instruction, later | End-to-end recurring benefit including enclosure tightness and certificate coverage |

### Decision rule

1. If generic composition rejects or becomes materially looser on boxes that
   the specialized routine accepts tightly, implement a reusable specialized
   dihedral enclosure instruction first. Its general correctness theorem can
   extend the existing universal instruction invariant; it must not introduce
   per-expression calculus proofs.
2. If specialized and generic native bounds are close on the genuine boxes but
   Candle remains much slower, build the bounded exact-native fixed-scale
   implementation before changing the proof architecture. That separates the
   scalar representation and numerical equations from `Kernel.compute`, pair
   traffic, allocation, and GC.
3. Consider a sparse `sqrt(x_i)` instruction next only if its complete-program
   timing and bounds justify it. The existing aggregate count alone is
   insufficient.
4. Do not retry endpoint sharing, naive `let` sharing, or Hessian-only
   projection without a new mechanism and a new discriminating prediction.

## Matched genuine-box result

The bounded experiment is now complete.  The Candle exporter reconstructed all
4,173 exact final boxes from the existing case-10173 plan, with contiguous
indices 0--4,172 and no axiom-set growth.  The native driver converted every
rational endpoint outward to binary64 and reported zero library errors and no
unstable boxes.

| Lane | Dataset | Accepted | Numerical wall time |
|---|---:|---:|---:|
| Specialized C++ `dih_x` | 4,173 boxes | 4,173 | 0.0838 s |
| Generic C++ composition | 4,173 boxes | 52 | 0.3302 s |
| Current reflected Candle | matched prefix 128 | 128 | 13.00 s |

The native generic-minus-specialized upper-bound loss is positive throughout
the distribution: minimum 0.00161, median 0.01154, p90 0.02279, and maximum
0.04771.  This explains why the audit's generic native search subdivided much
more: the generic C++ formulation does not certify almost any of the genuine
final boxes.

The current reflected result does **not** follow that loose-bound regime.  On
the matched 128 boxes:

- reflected-minus-specialized has median +0.000125, p90 +0.000260, and maximum
  +0.000634 (with a small negative minimum of -0.0000394);
- reflected-minus-generic has median -0.00739 and remains negative even at its
  maximum (-0.00216); and
- every reflected upper bound is negative, from -0.00361 to -0.0000153.

Thus the present case-10173 certificate has already recovered enclosure quality
much closer to the specialized historical evaluator than to the generic C++
composition.  The first 128 cells also give a recurring-cost comparison on the
same data: 3.12 seconds to encode and 13.00 seconds in `Kernel.compute`, versus
roughly 0.0026 seconds for a proportional share of the full specialized native
batch.  That ratio is not a pure interpreter ratio because the algorithms and
number representations still differ, but it rules out subdivision alone as
the explanation of the remaining gap on these final cells.

The Candle diagnostic returned a closed computation theorem and introduced no
axiom growth.  It intentionally omitted the general soundness handoff, so its
13.00 seconds is the numerical evaluator cost rather than a complete proof
time.  Peak sampled RSS was 17.22 GiB, inherited from the prepared heap rather
than allocated by this 128-cell batch.

The principal development artifacts are pinned by SHA-256: exact boxes
`38923471e3b3d0034687eece42c571b82a50745a304df33d5e2c75a8fb5334d3`,
native results
`8c11a566022de0c1e49980454637f828f5acd95027a39c089c976f44af51b14a`,
reflected bounds
`d2da0475a81b45daa4a7506e0f4224da29921e74c4dda53abba0fcbe0bf4e73f`,
and the matched analysis
`e1d82e652ce1aa226484091fce5aee8a34ddfa6f7856ffde3cd035473d8a067e`.

## Exact-native fixed-scale result

The decision rule selected its second branch, and that bounded discriminator is
now complete.  A native GMP implementation consumes the exact authenticated
54-instruction reflected source program, all seven exact square-root
certificate intervals at the box and center, and the exact rational endpoints
for the same 128 cells.  It implements the current fixed-scale interval,
centered Taylor, polynomial, square-root, reciprocal, arctangent, and
pi-half equations rather than substituting the historical floating-point
generic algorithm.

The native implementation reproduced **128/128 Candle upper bounds exactly**
as rational numbers.  Its measured phases were 0.0116 seconds to parse and
prepare the already exported inputs and 0.8776 seconds to evaluate the batch,
with 4.4 MiB peak RSS.  The corresponding Candle phases were 3.1228 seconds to
encode the jobs and 12.9968 seconds in `Kernel.compute`.  The strictly matched
numerical evaluation ratio is therefore **14.81 times**.  The preparation
figures are deliberately not turned into a ratio: the native measurement
starts from an exported representation whereas Candle constructs its internal
encoded jobs.

A second, larger gap must remain visible alongside that evaluator ratio.  The
exact-native fixed-scale batch costs 0.006856 seconds per cell, whereas the
historical specialized C++ lane costs 0.00002009 seconds per cell over all
4,173 boxes.  The throughput-normalized ratio is therefore about **341
times**.  This comparison is not exact-output matched across arithmetic
representations, but it measures a much larger architectural opportunity than
the Candle/native gap: the current fixed-scale equations do substantially more
arithmetic work per box than the specialized numerical algorithm even though
their final enclosure quality is close on this certificate.

The native operation ledger recorded 995,840 interval products, 26,624
completed centered results, 22,528 polynomial steps, 6,912 outer-product
steps, 896 square-root steps, 128 inverse steps, and 128 arctangent steps.  The
supplied source audit found that the current encoded interval multiplication
expands one semantic interval product into 32 natural multiplications.  On
this batch that means about 31.87 million encoded natural multiplications,
whereas the native signed-integer implementation performs four GMP products
per semantic interval product (about 3.98 million).  This is a concrete reason
to investigate the signed fixed-point/interval primitive boundary, not an
attribution of the full ratio: recursive evaluator traversal, allocation, and
GC remain combined in the Candle measurement.

An instruction-level exact-native profile now locates the generic dihedral
subgraph precisely.  Instructions 31--38 are the `pi/2`, `delta_x4`,
`4*x1*delta_x`, square-root, inverse, product, arctangent, and final-add
sequence.  Across the same 128 jobs they account for:

| Generic-dihedral share | Count/time | Share of complete fixed-scale run |
|---|---:|---:|
| Instrumented native execution | 0.4973 s | 57.00% |
| Fixed interval products | 506,368 | 50.85% |
| Completed Taylor results | 16,640 | 62.50% |
| Polynomial instructions | 15,872 | 70.45% |

The profiled run still matches all 128 Candle bounds exactly.  Profiling adds
clock reads at every outer instruction, so its absolute time is not used as a
new evaluator comparison; its total, 0.8780 seconds, is nevertheless
consistent with the uninstrumented 0.8776-second run.  The final profile
result has SHA-256
`052171126b84477432450c37fd9e911c092a91c4502af1f8addde1a401235b80`.

This also bounds what a specialized dihedral instruction alone can achieve in
the current fixed-scale architecture.  Even eliminating the entire measured
subgraph would give at most about **2.33 times** improvement and would leave
about a **147-times** per-cell gap to the historical specialized C++ lane.
That is an intentionally optimistic ceiling, not a speedup forecast.  It
strengthens the case for the instruction while showing that scalar
representation, sparse/symmetric derivative machinery, completion strategy,
and other specialized arithmetic remain first-class architectural targets.

This closes the ambiguity left by the first native comparison.  Extra generic
mathematical work explains the historical C++ subdivision explosion, but it
does **not** explain Candle's remaining recurring cost on these certificate
boxes.  The current reflected equations produce specialized-quality bounds;
executing those same equations through the current encoded representation is
one large measured gap.  Producing those bounds with the current dense,
generic fixed-scale algorithm rather than specialized arithmetic is the other,
substantially larger measured throughput gap.  Good enclosure quality does
not imply comparable work per box.

The exact-native result is an untrusted performance diagnostic, not theorem
evidence.  Its usefulness comes from exact cross-checking against the closed
Candle computation result, not from trusting the C++ implementation.  The
native result file has SHA-256
`f4dfbf401e0e7b81ca465ddda1332ace10048d1eca8f5b5a1853f24c66b219fc`.

## Compact-product result and updated implementation choice

The bounded compact signed-product experiment is also complete.  Four
constructor-specific user equations would express the desired operation most
directly, but `Kernel.compute` rejected them because its user-equation contract
requires variable arguments.  A HOL conditional implementation was then
proved equal to the existing product but rejected because user-equation
right-hand sides must remain in the cexp language.  Both failures occurred
before computation and are preserved.

The accepted candidate stays inside that contract.  It redirects the existing
raw product to a generally proved cexp function: canonical signed operands use
one natural multiplication, while noncanonical values use the unchanged
four-product formula.  The redirect replaces exactly one equation by identity,
leaves every public function and theorem interface unchanged, and retains the
original rule as a semantic fallback.

On the same 128 genuine boxes it reproduced the baseline theorem result
exactly, with no assumptions and no axiom growth, but it was slower:

| Matched `Kernel.compute` lane | Time |
|---|---:|
| Existing fixed-scale equations | 13.3351 s |
| Proved canonical-product redirect | 17.4195 s |

The candidate is **1.306 times slower** (30.6%) and must not be integrated.
This is consistent with the verified evaluator's call-by-value cexp boundary:
expressing the sign dispatch with ordinary cexp operations does not create the
cheap constructor dispatch that the native implementation uses.  It also
confirms that repeating the prior source-level sharing strategy in another
surface form is not the route to the 14.81-times gap.  A truly compact signed
primitive would require an intentional change to the fixed `Kernel.compute`
primitive contract and its verified implementation; that is no longer the
next bounded NL experiment.

A specialized dihedral instruction remains attractive because it can remove a
large generic instruction subgraph, but the measured justification is now
reduced work per box, not expected certificate shrinkage.  The approximately
341-times native fixed-scale/specialized throughput gap makes this an
independent architectural target rather than merely a fallback after compact
encoded multiplication.  The next bounded prototype should therefore add a
reusable specialized dihedral operation to the universal instruction invariant
and measure it on these same boxes.  It should first be exercised as a
numerical development path, then receive the general correctness theorem if
the complete-program result is promising.  It must compare
complete-program time and preserve the present bounds or at least all current
certificate acceptance.  The sparse-coordinate square-root idea remains
secondary: the prior complete-program profile did not show an exceptional
per-step square-root cost, and the current matched bounds give no reason to
trade tightness for that optimization.

## Implementation started

The isolated development sources now include:

- a Candle exporter for all exact case-10173 certificate boxes;
- a Candle `Kernel.compute` diagnostic returning the exact current-checker
  upper bound for the first 128 boxes;
- a proved canonical signed-product discriminator and matched baseline driver;
- an exact-native per-instruction profiler identifying the generic dihedral
  subgraph's measured share;
- a native C++ driver evaluating specialized and generic formulations on the
  exported boxes; and
- repeatable drivers that preserve inputs, logs, phase profiles, timings, and
  hashes.

The native driver and both Candle fragments have now passed on clean compatible
checkpoint restores.  The first box postprocessor and the first two reflected
wrapper attempts failed closed; those failures are preserved.  They exposed,
respectively, an OCaml prompt prefix on the first emitted line, an inappropriate
result projection, and missing standard `LET_END_DEF` normalization.  The final
drivers handle the prompt explicitly and reuse the production certified-check
pair and equation normalization without changing any checker equation.

No specialized numerical instruction should be integrated merely from the
audit's static operation count.  The exact-native and compact-product results
now justify a bounded specialized-dihedral prototype on matched data.  General
proof integration should follow only if that prototype reduces complete-
program recurring cost without losing the already strong bound quality or
certificate coverage.
