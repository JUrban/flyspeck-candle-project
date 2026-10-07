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
subgraph precisely.  Instructions 31--38 are the `pi/2`, `-delta_x4`,
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

### Fused-polynomial discriminator

A follow-up native prototype tested whether the two dihedral polynomials could
be evaluated as whole value/gradient/Hessian jets and completed only at their
block boundaries.  This is a development diagnostic for a possible generally
proved polynomial instruction, not theorem evidence.

Fusing all 22 polynomial blocks reduced the one-run native time from roughly
0.88 seconds to 0.669 seconds and reduced completed Taylor results from 26,624
to 6,912.  It was rejected: naïve whole-box interval differentiation widened
the final bound enough that only **122 / 128** genuine cells remained accepted.
The failed result is preserved with SHA-256
`9ce5ffb8c29285ee0221a707c9b79653609d0b488bd2a5367e3da2d78cbc1336`.
This is direct evidence that reducing arithmetic work without preserving the
established centered enclosure quality is not a viable optimization.

The constrained variant fuses only the 39-step `-delta_x4` block.  Its Hessian
is constant, so the block can avoid 38 intermediate completions per cell
without losing the established enclosure.  It reproduced all **128 / 128**
final upper bounds exactly and retained all certificate acceptance.  Across
seven alternating warm repetitions:

| Exact-native lane | Mean evaluation time |
|---|---:|
| Established fixed-scale program | 0.858544 s |
| Fused `-delta_x4` block | 0.809125 s |

That is a **5.76%** reduction or **1.061-times** speedup.  The required
completions fell from 26,624 to 21,760, while semantic interval products rose
slightly from 995,840 to 1,005,824 because the fused box jet carries its value
and gradient directly.  The paired timing table has SHA-256
`605d144c67d41c96d44c29105a68334eb87f076c5ff6d38188256171d46e4dd0`;
the seven-pair run, including compilation, took 15.350 seconds.

This exact positive result was too small to justify a new proof layer by
itself, but it identified a safe component for the next prototype.  That
prototype now also replaces the difficult 85-step `4*x1*delta_x` block.  It
computes `delta_x` at the center, uses its explicit linear Hessian identities
over the whole box, obtains tight gradient bounds by one centered Taylor lift,
and then constructs the value, gradient, and Hessian of `4*x1*delta_x`
directly.  The established square-root certificate, inverse, arctangent,
completion, and final source expression remain unchanged.

The first direct-formula attempt used natural interval bounds for the
`delta_x` gradient.  It was fast (0.538 seconds) but accepted only **118 / 128**
cells and is rejected.  Replacing only that loose gradient step with the
center-plus-Hessian bound restored every result.  The centered specialized
prototype reproduced all **128 / 128 established final upper bounds exactly**.

Across seven alternating warm repetitions:

| Exact-native lane | Mean evaluation time |
|---|---:|
| Established fixed-scale program | 0.878711 s |
| Specialized angle polynomials | 0.532084 s |

This is a **39.45%** reduction or **1.651-times** speedup.  Semantic interval
products fell from 995,840 to 694,272, completed Taylor results from 26,624 to
11,008, and interpreted polynomial steps from 22,528 to 11,648.  Peak native
RSS remained negligible relative to Candle.  The paired timing table has
SHA-256
`0ea93927311a332f4989d137c322f1c55c33bfb12f72d888fa08d1f82745ad9e`;
the seven-pair run, including compilation, took 14.253 seconds.  The exact
single-run result ledger has SHA-256
`6953ec551c240217f735cfc66a3ad941a67ce1a9bd5b2cf68dff70b29dd1a99f`.

This clears the numerical gate for a reusable Candle specialization.  The
intended formal boundary is not a fixture-specific theorem: prove the direct
fixed-scale `-delta_x4` and `4*x1*delta_x` jet enclosures for arbitrary valid
six-dimensional boxes, dispatch only on the exact authenticated compiled
polynomial identities, and reuse the existing universal analytic instruction
and source-soundness chain.  Unrecognized polynomials retain the already
proved lazy evaluator.  The native result alone is not proof or production
authority.

### First `Kernel.compute` specialization result

The bounded specialization has now also run through the intended encoded
evaluator on the same 128 genuine boxes.  The first run selected the authentic
85-step polynomial by length.  A second run replaced that temporary condition:
the prepared source supplies the exact compiled polynomial payload and both
patched programs must match it structurally before the specialized operation
is selected.  A formal preparation-to-source theorem is still required before
proof integration.  The numerical operation is the centered direct
`4*x1*delta_x` jet above.  The established 39-step `-delta_x4` block remains on
the generic path in these first Candle tests.

The candidate reproduced all **128 / 128 final upper bounds exactly**, retained
all certificate acceptance, introduced no assumptions, and caused no axiom
growth:

| Matched `Kernel.compute` lane | Time |
|---|---:|
| Existing fixed-scale equations | 13.2292 s |
| Centered angle-polynomial specialization | 8.9611 s |

This first matched run is a **32.26% evaluator-time reduction** or
**1.476-times speedup**.  The timing table has SHA-256
`a43a2281c55b4d70ed0f0055da2426cbfa75bd497424d3921cb91c7c9219c076`.
The preserved run is
`cv-case10173-angle-polynomials-prefix128-v2-dev-001`.  The exact-payload rerun
also matched all 128 outputs and took 12.7172 seconds versus 8.5971 seconds, a
**1.479-times** speedup; its timing table has SHA-256
`b59e8c33010d0606d1a2b7ba9dfcb29fbc0185822e81c088a30efd5f2484697b`.
The agreement between the two runs makes the approximate 1.48-times result a
useful gate, although a longer alternating series would still be needed for a
high-precision performance claim.

This result must not collapse the two performance questions into one.  The
rough **15-times** gap from exact-output-matched native fixed-scale execution to
Candle is an encoded evaluator/representation target.  The separate rough
**340-times** gap from the historical specialized C++ verifier to native
fixed-scale execution is an algorithm and arithmetic target.  The new Candle
instruction improves the first layer by deleting generic work, but neither a
faster evaluator nor this one instruction can close the second layer by
itself.  Exact enclosure equality establishes bound quality; it does not
establish comparable work per box.

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
- rejected whole-program and exact `-delta_x4`-only fused-polynomial
  discriminators with a seven-pair timing driver;
- a centered specialized `4*x1*delta_x` jet prototype with exact matched
  final bounds and a seven-pair timing driver;
- a Candle centered-angle implementation and matched 128-box
  `Kernel.compute` driver, exact on every final bound and 1.476 times faster in
  its first paired run;
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
audit's static operation count.  The exact-native, rejected compact-product,
and exact Candle specialization results now justify the general containment
proof and authenticated instruction dispatch.  The proof work must retain the
generic proved path for every unrecognized polynomial and preserve the two
performance gaps as separate architectural targets.

## Arithmetic/algorithm separation after the angle specialization

Six further native experiments use the same 128 genuine case-10173 boxes.
They preserve complete-program acceptance and charge parsing/preparation
separately from evaluation.  These are untrusted development discriminators,
not theorem evidence.

First, changing only the fixed-point scale from decimal `10^12` to the nearby
dyadic `2^40` did not help.  In 21 warmed, order-balanced pairs, decimal took
0.523792441 seconds and dyadic took 0.525304832 seconds.  The dyadic lane was
0.29% slower, with all 128 cells accepted.  It produced 78 tighter and 50
wider upper bounds, with maximum widening about `2.34e-10`.  Thus denominator
choice and power-of-two rounding alone do not explain the remaining gap.
The paired phase table has SHA-256
`89e730697f89b389c0b7b10accb04f4e645647c51d945a948a64189baf8a62fc`.

Second, keeping the decimal scale and numerical algorithm fixed while
replacing dynamically sized GMP interval endpoints by Boost's fixed-width
`int256_t` was decisive.  In 21 warmed, order-balanced pairs:

| Exact native endpoint backend | Mean evaluation time |
|---|---:|
| GMP `mpz_class` | 0.532914630 s |
| Fixed-width 256-bit integer | 0.172964497 s |

This is a **3.081-times** speedup and a **67.54%** reduction.  Every one of the
128 final upper bounds matched exactly, and every cell remained accepted.
The paired phase table has SHA-256
`3ec46c832c154cac7f63f898a99b4eab0d9879f9123bb59cc2503af7cef9d844`.
An attempted signed 128-bit backend failed with arithmetic overflow, observed
as an invalid square-root domain.  Fixed-width 256-bit arithmetic is therefore
only a useful prototype: a production checker must prove a sufficient range
bound or check overflow explicitly.  Exact fixture output is evidence that no
overflow was observed here, not a general range proof.

A profile of the fixed-256 centered-angle lane attributes approximately 52.25%
of time to polynomial evaluation, 19.67% to square roots, 13.09% to outer
products, 5.50% to arctangent, 3.43% to inverse, and 6.07% to the remaining
linear stack operations.  Fusing every polynomial block of at most six steps
preserved all final outputs but improved one representative run by only about
4%; it is not a large-gap route.

Third, holding the fixed-256 arithmetic and centered angle specialization
fixed, the native driver directly evaluated the 39-step numerator polynomial
instead of interpreting its scalar instructions.  A subsequent exact payload
decode found an important sign error in the first development shortcut: the
source polynomial is **`-delta_x4`**, while that shortcut had returned
`delta_x4`.  The earlier apparent tightening by about 0.436 and all timings
downstream of that sign-wrong shortcut are superseded.  No proved Candle
specialization used this shortcut.

The corrected driver negates value, gradient, and Hessian, restricts the
development dispatch to pinned outer position 32, and checks the source
payload independently with exact rational polynomial normalization.  The
same check establishes that outer position 33 is `4*x0*delta`.  It emits
`CANDLE_NL_CASE10173_ANGLE_PAYLOAD_IDENTITIES_OK`; the pinned program has
SHA-256
`b044687f3c3f77b50d8dfd7afd8ebb9c7af1fb30637acc2b629107cee6e67b01`.

In 21 warmed, order-balanced corrected pairs:

| Fixed-256 centered-angle lane | Mean evaluation time |
|---|---:|
| Interpreted `-delta_x4` polynomial | 0.171291644 s |
| Direct `-delta_x4` jet | 0.148842708 s |

This is a further **1.151-times** speedup and a **13.11%** reduction.  All 128
cells remained accepted, and at scale `10^12` the direct lane reproduced all
128 established final bounds exactly.  The paired phase table has SHA-256
`1eeab30c0ca3955f34cfa1812916294e77c5bae3835a8f2255e0445e00157ae1`.
It reduced semantic interval products from 694,272 to 564,480 and interpreted
polynomial steps from 11,648 to 6,656.  This corrected result is the only
direct-numerator result used below.

Fourth, a minimal sparsity discriminator kept the fixed-256 arithmetic,
direct `-delta_x4`, all dense jet objects, all rounding, and the numerical
algorithm fixed.  It only bypassed interval multiplication when either input
was the exact zero interval.  In 21 warmed, order-balanced pairs it reduced
evaluation from 0.151343951 to 0.137435641 seconds, a **1.101-times** speedup
or **9.19%** reduction.  The exact 128-result stream was byte-identical between
the two lanes and all cells remained accepted.  It bypassed 479,872 of 564,480
attempted interval products.  The paired phase table has SHA-256
`d2386e07ebf68cc6720bd366482002baa2ab3e06b73214dcadb5dc3ddd41a04a`;
both result streams have SHA-256
`21533ccc3e2ea18d0031fb2382d59b3e87d316944faad1706bac56455e01da7c`.

This is informative precisely because the timing gain is much smaller than
the product-count reduction.  With fixed-width endpoints, multiplication by
zero is cheap; dense traversal, object movement, additions, comparisons, and
rounding still occur.  A useful sparse experiment must therefore use a compact
representation and omit absent gradient/Hessian entries end to end.  Merely
adding zero tests to the dense checker is not a serious architecture.

Fifth, a symmetric-Hessian discriminator kept fixed-256 arithmetic, decimal
rounding, direct `-delta_x4`, and exact-zero bypass fixed.  It computed only the
upper triangle of every known-symmetric Hessian operation and mirrored the
result, while deliberately retaining the existing dense in-memory object.  In
21 warmed, order-balanced pairs:

| Fixed-256 zero-bypass lane | Mean evaluation time |
|---|---:|
| Dense Hessian operations | 0.136614395 s |
| Upper-triangle Hessian operations | 0.113362306 s |

This is a **1.205-times** speedup and a **17.02%** reduction.  The 128-result
streams were byte-identical and all cells remained accepted.  Semantic
interval products fell from 84,608 to 58,496; bypassed zero products fell from
479,872 to 292,864 because the duplicate lower-triangle operations no longer
occurred.  The paired phase table has SHA-256
`b1083b9d8bc7dabf9d4ec28f2648818102382b7c75ea7a26279f31b3cc77ac78`;
both result streams again have SHA-256
`21533ccc3e2ea18d0031fb2382d59b3e87d316944faad1706bac56455e01da7c`.
This isolates useful generic derivative/Taylor redundancy while holding
arithmetic and rounding fixed, but its size rules out symmetry alone as the
large-gap explanation.

Sixth, a checked-width discriminator held the complete symmetric numerical
algorithm and decimal scale `10^10` fixed while changing only the endpoint
backend from fixed 256-bit integers to Boost's overflow-checking 128-bit
integers.  In 21 warmed, order-balanced pairs:

| Endpoint backend | Mean preparation | Mean evaluation | Mean 128-box batch |
|---|---:|---:|---:|
| Fixed 256-bit | 0.008070501 s | 0.106953259 s | 0.115023760 s |
| Checked 128-bit | 0.007275976 s | 0.065849656 s | 0.073125631 s |

The evaluation speedup is **1.624 times** (38.43% reduction); including
program/job parsing, the recurring 128-box batch speedup is **1.573 times**.
Both backends produced byte-identical result streams, all 128 cells remained
accepted, and the lower-scale bounds differed from the `10^12` fixture only
by outward-rounding amounts (maximum widening about `6.22e-8`).
The paired phase table has SHA-256
`dcaf0c32680202dc075702c4dc118347169bacab1b17f1fbf06403e6cd69fa95`;
both result streams have SHA-256
`7541bcd5a81792844c8da7f4f2c886203a601c89594eb16b3845a4ecee890355`.
The same checked backend rejects scale `10^12` with an explicit multiplication
overflow.  Scale `10^10` is therefore a measured fixture result, not a general
range argument; a production choice still requires checked arithmetic or a
proved global range.

These results keep the performance layers explicit.  Relative to the
historical specialized-C++ per-cell time, the original exact native
fixed-scale lane was about **341 times** slower, the centered-angle GMP lane
about **207 times** slower, the centered-angle fixed-256 lane about **67
times** slower, and the direct negated-numerator fixed-256 lane about **59 times**
slower.  The dense exact-zero bypass diagnostic lowers the last figure only to
about **54 times**, and upper-triangle Hessian execution lowers it to about
**45 times**.  At the lower scale, checked 128-bit evaluation is still about
**26 times** slower than historical specialized throughput.  The compact
support-aware lane below lowers that to about **25 times**; including its
128-box parsing/preparation makes the recurring batch ratio about **29
times**.  Separately, executing the exact-output-matched original
equations in `Kernel.compute` was about **15 times** slower than executing them
in native C++.  Fixed-width arithmetic substantially reduces the much larger native
algorithm/arithmetic gap, but it does not remove it and says nothing yet about
the encoded-evaluator gap.

### Compact-support discriminator: useful, but only a local gain

The next native discriminator held the following fixed on the same 128
genuine case-10173 boxes:

- the specialized-angle and direct-`-delta_x4` polynomial choices;
- the generic analytic instruction sequence and Taylor formulas;
- decimal scale `10^10`, checked signed 128-bit endpoints, and every
  outward-rounding point; and
- the input program, square-root certificates, boxes, and expected results.

It changed only the outer analytic jet representation and execution.  The
control kept dense six-entry gradients and symmetric dense matrices.  The
candidate carried explicit gradient support masks and a 21-entry
upper-triangular Hessian with a support mask, and did not traverse or dispatch
known-absent entries.  Polynomial subprograms still use the established dense
or specialized evaluators and are converted at their result boundary; this is
therefore a bounded outer-jet discriminator, not a claim that every possible
sparse compiler optimization has been exhausted.

Thirty alternating paired repetitions produced:

| Lane | Mean preparation | Mean evaluation | Mean complete batch | Accepted |
|---|---:|---:|---:|---:|
| Dense symmetric control | 0.008698347 s | 0.067140066 s | 0.075838413 s | 128/128 |
| Compact support-aware outer jets | 0.009185835 s | 0.063152007 s | 0.072337842 s | 128/128 |

The recurring evaluation gain is **1.0632 times**, or **5.94%**; including
parsing/preparation in this paired sample, the batch gain is **1.0484 times**.
Both lanes performed
the same 58,496 nonzero interval products.  The compact lane reduced
zero-product dispatches from 292,864 to 159,744, yet both 128-result streams
are byte-identical with SHA-256
`7541bcd5a81792844c8da7f4f2c886203a601c89594eb16b3845a4ecee890355`.
The phase table has SHA-256
`f60e1e14238e877e02b5460f5363992517fd61781d1550a4a28f3883deee7b60`
in development run
`nl-native-case10173-compact-support-checked128-v3-sign-guarded-dev-001`.

This rejects dense zero-entry traversal as the principal explanation of the
remaining native/specialized gap on this fixture.  Completing a general
sparse plan may still be worthwhile as reusable engineering, but the measured
gain is too local to justify making it the next major proof project.  It also
sharpens the distinction between the two gaps: arithmetic width and outer
support-aware execution have reduced native time, while the historical
specialized implementation still avoids substantially more numerical work
per accepted box.

The next large-gap experiment will therefore hold checked fixed-scale
arithmetic and the genuine boxes fixed while replacing the complete generic
dihedral derivative/composition path with a faithful native port of the
historical specialized dihedral enclosure structure.  It will record final
upper-bound width, 128-box acceptance, preparation/evaluation time, interval
operation counts, and peak memory.  If that lane has a material complete-batch
win, it will be extended to the full 4,173-box certificate before any broad
formalization.  If it does not, the next discriminator will keep that
specialized algorithm fixed and compare checked fixed-scale endpoints with
outward-rounded machine arithmetic, separating algorithmic work from endpoint
representation and rounding.

The full-certificate historical target has also now been measured directly,
using the hash-pinned audit build on the exported 4,173 genuine case-10173
boxes.  Across 21 repetitions:

| Historical C++ lane | Mean numerical time | Minimum acceptance |
|---|---:|---:|
| Specialized dihedral | 0.082490265 s | 4,173/4,173 |
| Equivalent generic composition | 0.326891192 s | 52/4,173 |

The generic lane is 3.96 times slower on this already partitioned batch and,
more importantly, is far too loose to validate the certificate.  The result
therefore supplies a concrete target rather than a production comparison:
the fixed-scale specialized port must preserve complete-certificate
acceptance, and its preparation plus recurring checking must be reported
separately.  The one complete resource-observed run used 5,376 KiB peak RSS;
its two numerical phases were 0.083103199 and 0.323921624 seconds.  The
21-run phase table has SHA-256
`f5b52a607504dfb07e96e5c3c0a2a65d5a154a4420b0f3b6bd710ac56972be22`
in development run `nl-historical-case10173-full4173-v1-dev-001`.

This measurement also prevents an attractive but invalid shortcut: a native
lane that runs quickly while accepting only a small fraction of the existing
boxes has not improved certificate verification.  Complete-batch acceptance
and time remain the joint gate.

### Bounded proof work and the larger-gap plan

The first bounded proof boundary is now complete at Candle commit `d70c17ea`.
The specialized `4*x0*delta` executable has assumption-free logical
representation theorems for its interval operations, delta value/gradient/
Hessian, product gradient/Hessian, fixed-scale result, and rational-input
wrapper.  A clean checkpoint replay emitted
`CANDLE_CV_FIXED_SCALE_ANGLE_POLYNOMIALS_SOUND_OK assumptions=0`.  This is a
representation result, not yet the analytic containment theorem or the
authenticated dispatch theorem, and it makes no certificate claim.

The remaining Candle angle-specialization proof is deliberately bounded.  It
will establish the reusable containment theorem plus authenticated
exact-payload dispatch with fallback to the generic proved path.  It will not
grow into a collection of fixture-specific arithmetic proofs merely because
the first instruction passed its benchmark.

The zero-skip, upper-triangle, and compact-support discriminators now bound
the immediate representation opportunity.  The compact-support lane held the
checked arithmetic and outward rounding fixed while removing a large subset
of absent-entry work at the outer analytic boundary; its 5.94% evaluation
improvement is real but local.  A fully compiled sparse plan remains a
plausible reusable
implementation step, but it is no longer the next large-gap experiment.

The three controlled tests now bracket the causes.  Avoiding duplicate
symmetric derivative work buys 1.21 times, unchanged-plan narrow arithmetic
buys 1.62 times, and compact outer support execution buys a further local 1.06
times against its dense checked-128 control.  None closes most of the gap.
The next major native prototype is therefore a complete specialized-dihedral
instruction modeled on the historical algorithm rather than another sequence
of jet micro-optimizations.  The specialized instruction must still emit the
data needed by the general Taylor contract, and its eventual proof should be
one reusable instruction theorem plus authenticated source-to-plan checking.

The staged route is:

1. keep the present representation/dispatch proof bounded and retain generic
   fallback;
2. retain checked fixed-width arithmetic and compact support-aware jets as
   measured implementation candidates, without broadening their proof surface
   before the architecture gate;
3. test a faithful complete-dihedral numerical instruction on genuine boxes,
   then separate its algorithmic gain from endpoint/rounding cost if needed;
4. add generally useful source operations such as `delta_x`, `delta_x4`,
   `ups_x`, coordinate square root, and complete dihedral only when their
   end-to-end batch benchmarks justify them;
5. gate architecture choices on the complete 4,173-box certificate, charging
   reusable preparation once and recording acceptance, elapsed time, peak
   memory, and required subdivisions; and
6. formalize one general sparse-jet/Taylor soundness theorem and a checked
   expression-to-plan correspondence, rather than per-expression calculus
   proofs.

An outward-rounded hardware floating-point lane may provide a useful lower
bound on attainable numerical time, but it is secondary to the exact
fixed-width/sparse-plan discriminator because changing representation,
rounding, and algorithm simultaneously would not identify which improvement
matters.  The deciding result remains total accepted-certificate throughput,
with preparation and theorem handoff visible and amortized honestly.

The immediate decision sequence is therefore concrete and bounded.  The
compact-support gate is complete with only a local gain:

1. retain the compact-support implementation and result as a measured
   lower-level optimization, but do not expand its proof surface now;
2. port the historical complete-dihedral numerical structure into the native
   harness with explicit outward rounding and the same box inputs;
3. record bound width, acceptance, complete-batch preparation/evaluation time,
   and operation counts for generic compact and specialized-dihedral lanes;
4. only after a native specialized lane demonstrates a material end-to-end
   win, prove one general instruction soundness theorem and authenticate its
   source-expression/parameter correspondence; and
5. then measure the encoded instruction in `Kernel.compute`, treating the
   approximately 15-times encoded/native execution gap as a separate problem
   from the still approximately 25-times native-specialized numerical gap.

The complete 4,173-box fixture remains the architecture gate.  The current
128-box family is sufficient to reject weak ideas cheaply, but not to claim a
certificate-wide speedup or to select a production scale/range contract.

## Fixed nonlinear-kernel factorial: arithmetic is material, not sufficient

The next controlled native experiment is complete.  It held the genuine
128-box fixture, specialized angle-polynomial plan, direct authenticated
`-delta_x4`, dense symmetric Taylor formulas, decimal scale `10^10`, and every
fixed interval rounding point constant.  It varied two independent factors:

1. native signed `int128` versus Boost overflow-checking signed `int128`, with
   identical fixed operations; and
2. GMP-rational implementations of square root handoff, reciprocal, and
   arctangent versus outward-rounded fixed-scale implementations, with the
   surrounding generic derivative/Taylor algorithm unchanged.

Thirty warmed, order-balanced repetitions produced:

| Endpoint lane | Nonlinear kernels | Preparation | Evaluation | Complete batch | Accepted |
|---|---|---:|---:|---:|---:|
| unchecked `int128` | rational | 0.009500554 s | 0.047123691 s | 0.056624245 s | 128/128 |
| unchecked `int128` | fixed | 0.012249432 s | 0.029603075 s | 0.041852507 s | 128/128 |
| checked `int128` | rational | 0.008929249 s | 0.067840680 s | 0.076769929 s | 128/128 |
| checked `int128` | fixed | 0.011986593 s | 0.049043404 s | 0.061029997 s | 128/128 |

Holding the generic numerical plan fixed, removing rational nonlinear kernels
improved checked evaluation by **1.383 times**.  Removing overflow checks as a
diagnostic improved the fixed-kernel lane by another **1.657 times**; the
combined rational-checked to fixed-unchecked evaluation ratio is **2.292
times**.  The unchecked lane is not a checker candidate: identical fixture
outputs do not establish the absence of signed overflow.  Its purpose is to
bound the cost of the current checked endpoint representation.

The fixed implementations use integer inequalities for supplied square-root
certificates, outward integer division for reciprocal bounds, and lower/upper
alternating arctangent polynomials on the open unit interval.  A validation
mode ran the fixed and exact-rational nonlinear paths side by side after each
nonlinear instruction and required the complete candidate value, gradient,
and Hessian result to enclose the rational reference.  All 896 square-root,
128 reciprocal, and 128 arctangent results passed at each of scales `10^10`
and `10^12`.  The `10^12` fixed-256 run accepted 128/128 cells; 89 final bounds
were exact and 39 were wider by exactly `10^-12`.  The `10^10` checked run also
accepted 128/128, with maximum widening about `6.22e-8`.  These checks are
strong development diagnostics, not formal soundness proofs.

The phase table is SHA-256
`c79a152dea988d364b01033339610c62acb0ce2adecc967b24e234d65c2c1bc2`
in run
`nl-native-case10173-fixed-kernel-factorial-v3-crosschecked-dev-001`.
The two cross-check logs have SHA-256
`7cea1ff17705e4e2c9c545721d911776a4928618c184477e67b15b52f4009474`
and
`8a7c2acd0ee1bcc867ccacfb7f6811dd4618d256278511c0686b087e27cc170e`.

This materially revises, but does not close, the large-gap diagnosis.  The
original exact GMP fixed-scale lane was about 341 times slower per box than
the historical specialized C++ batch.  The best fixed-kernel unchecked
diagnostic is now about **11.70 times** slower per box, and the soundness-
plausible checked lane is about **19.38 times** slower.  Those ratios compare
different arithmetic representations and remain 128-box projections, not
full-certificate results.  They show that arithmetic representation and
nonlinear conversion were major costs, while leaving a large recurring
algorithmic gap.  The separately measured roughly 15-times
`Kernel.compute`/exact-native gap also remains an encoded-execution question;
it must be remeasured after a proved fixed-kernel operation exists rather than
combined arithmetically with these native ratios.

### Next controlled discriminator and proof boundary

One further cheap profile changed the order of this work.  In the checked
fixed-kernel lane, outer instructions 31--38--the complete dihedral subgraph--
used 0.009772 seconds of a 0.049766-second mean evaluation over 15 runs.  Even
deleting the subgraph entirely would be capped at about **1.244 times**.  In
contrast, instructions 0--30 used 0.032302 seconds.  Most of that prelude is
repeated interpretation of semantically constant polynomials and six
coordinate-square-root terms.  The profile-mean and dihedral-share files have
SHA-256
`634907a57abee50077d1f35af97ebbefe95d747341d0a09101f1130de0f07426`
and
`afef2faaf780ddae214934faf1df41d2aef6b23b1636397e86641ae506d2faa5`.

The first preparation experiment is therefore already complete.  A general
exact-rational source pass recognizes constant-only polynomial programs and
direct coordinate projections from their actual instruction payloads.  It
prepared 20 of the 22 ordinary polynomial payloads once; the two nonlinear
angle polynomials retained their separately authenticated implementations.
At evaluation time the prepared constants and projections enter the unchanged
Taylor operations directly.  This is semantic classification of the supplied
program, not a basename, outer-index, or fixture-value whitelist.

Fifty warmed, order-balanced checked-`int128` pairs gave:

| Source execution | Preparation | Evaluation | Complete batch | Accepted |
|---|---:|---:|---:|---:|
| Reinterpret simple polynomials per box | 0.010694550 s | 0.047929378 s | 0.058623928 s | 128/128 |
| Prepare 20 simple polynomials once | 0.009617546 s | 0.032469574 s | 0.042087120 s | 128/128 |

Every final result is byte-identical.  The evaluation gain is **1.476 times**
and the full measured batch gain, including preparation, is **1.393 times**.
The phase table has SHA-256
`a9a48fa4c6130ce38a4cf1cf605292c6c54f66ad16d50134033f4c08f03d7225`
in run `nl-native-case10173-prepared-simple-v1-dev-001`.  The result stream is
the same fixed-kernel stream with SHA-256
`82d86f072427c309ccb1c9038445358fa28c9464b0dd3e51e6e00d6901e10ba9`.

The prepared profile moved the remaining cost rather than hiding it:
instructions 0--30 still use 53.3% of profiled instruction time, now primarily
the six generic coordinate-square-root and scaling paths; the dihedral uses
31.6%, final additions 11.5%, and final scale/multiply 3.6%.

That next native lane is now complete.  A general plan pass recognizes the
actual four-instruction pattern
`coordinate; sqrt; constant coefficient; multiply` after exact simple-program
classification.  It found six terms.  Each compiled term checks the same
source-derived square-root certificates and directly constructs only its one
nonzero gradient and Hessian entry.  Unknown patterns retain the unchanged
generic path.

Fifty warmed, order-balanced checked-`int128` pairs gave:

| Prepared execution | Preparation | Evaluation | Complete batch | Accepted |
|---|---:|---:|---:|---:|
| Simple constants/coordinates only | 0.013193098 s | 0.034747861 s | 0.047940960 s | 128/128 |
| Six compiled coordinate-square-root terms | 0.013081843 s | 0.025099001 s | 0.038180844 s | 128/128 |

The incremental gain is **1.384 times** in evaluation and **1.256 times** for
the complete measured batch.  Every final result is byte-identical and all
128 cells remain accepted.  A validation run also required each compiled term
to enclose the full exact-rational generic value/gradient/Hessian result at
scale `10^10`; the same check passed with fixed-256 endpoints at scale
`10^12`.  At the larger scale, 89 final results remain exact and 39 are wider
by exactly `10^-12`, unchanged from the fixed-kernel control.

The paired phase table has SHA-256
`93cfb5b60498d2c2c37a626a18358cd8a04cfd2015eb70232d01e56823d0f508`
in run `nl-native-case10173-coordinate-sqrt-v2-crosschecked-dev-001`.
The checked and fixed-256 cross-check logs have SHA-256
`6841604dedb430efa8467ee40c8c503e993bb97fd61f61c5b13c0b8eb5679949`
and
`983932b9ded142ce2ef1f9ae7758f8783cdcc7416c424e3abc343008e2817188`.

Against the historical specialized batch, the new checked evaluation is
still about **9.92 times** slower per box.  Projecting the observed per-box
evaluation uniformly over all 4,173 boxes and charging the observed
preparation once gives about 0.831 seconds versus the historical 0.08249
seconds, or **10.08 times**.  That is only a projection; full-certificate
inputs and acceptance remain required before it becomes a certificate-wide
claim.  The result nevertheless clears the bounded native gate and makes the
complete specialized dihedral plan the next measured algorithmic target.

The first whole-dihedral candidate has also been run and rejected.  It kept
the authenticated specialized numerator/radicand, fixed certificates,
checked `int128`, and outward rounding, but combined inverse square root,
quotient, and arctangent through a single box jet before the final Taylor
completion.  It reduced one observed evaluation from 0.025484 to 0.024236
seconds, but accepted only **1 / 128** cells.  Every bound widened, with
maximum widening about 0.01317.  A side-by-side validation established that
the candidate full jet enclosed the exact-rational generic full jet, so the
failure is enclosure quality rather than an observed containment defect.

This candidate is not a proof target and its speed does not count as progress.
The failure rules out generic whole-chain fusion as the intended specialized
dihedral plan.  The next implementation must faithfully port the historical
specialized derivative identities--in particular its `U126`/`U135`-based
gradient and Hessian route--under the same checked fixed arithmetic.  That is
the controlled way to test whether specialized mathematics, rather than
fewer completion boundaries alone, closes the remaining gap.

The rejected run is
`nl-native-case10173-dihedral-chain-rejected-v1-dev-001`; its summary and
cross-check logs have SHA-256
`a1df5f2950ace1517ec179631ac2c24ed2fa91bbd54fb7f46303843ffeff24a0`
and
`ef3bc68733dee2581650bf1d5ab306f0f60b209246536495fe5e7e9c7e1f9548`.

A matched historical/fixed diagnostic later invalidated the reported 89/128
interpretation.  The development candidate had used the false identity
`4*x0*delta = U126*U135`.  The correct identity is

`U126*U135 = 4*x0*delta + delta_x4^2`.

Its center-gradient intervals consequently did not always overlap the
historical derivative values.  The candidate was already rejected,
development-only, and received no proof work, but its 89/128 coverage and
timing must not be used as evidence.  The preserved failed run remains useful
only as an audit trail of the defect.

The corrected formula was then tested at the exact angle boundary on the same
128 genuine boxes.  With the supplied square-root certificates it accepted
28/128; computing scale-`10^10` square-root enclosures internally raised this
to 99/128.  Adding fixed-point versions of the historical sign-directed
`U126` and `U135` range bounds reached 128/128.  At that point the mean angle
width was 1.00167 times the historical width.  Center and linear Taylor terms
agreed to approximately `10^-8`; the remaining difference was Hessian range.
This identifies certificate precision and specialized range evaluation as
enclosure-quality issues, not evidence that the specialized composition is
faster.

The decisive complete-batch gate then rejected the corrected specialization
as an integration/proof target.  In 20 order-balanced runs over all 4,173
boxes, both the generic fixed-native lane and the corrected specialized lane
accepted every box:

| Fixed-native lane | Preparation | Evaluation | Complete batch |
|---|---:|---:|---:|
| Generic derivative composition | 0.191086213 s | 0.939053166 s | 1.130139379 s |
| Corrected specialized identities | 0.188424105 s | 0.950126066 s | 1.138550171 s |

The specialization was 1.18% slower in evaluation and 0.74% slower including
preparation.  It produced a wider final bound on 3,863/4,173 boxes and reduced
the smallest acceptance margin from `8.5845e-5` to `4.00273e-5`.  It therefore
receives no analytic-containment or dispatch proof.  Boundary-analysis hashes
for supplied certificates, tight certificates, and optimized U bounds are
`7cf7853395e2ddf3817f62b972d1d87f374eb7f61a31a5c7c912f00af3fff52c`,
`bf63f8fe150df286be3988b268a495e16821c6d0c081d19e38e4230c64725ce1`,
and `293e622a1eb8a2692d36049f61c779008dc98ddd9f0890689b2751cff0fc12b4`.
The full phase table and bound comparison have hashes
`6f9b2d02697702c3da32ec51614cadba38a223b4b56136f4abd6dddf5193b111`
and `a073ff37f7a5ea56eca95d33e25663317a110531770449d1a75c88fd7a1e9845`.

The broader arithmetic investigation remains active.  Holding the accepted
generic algorithm, scale, rounding, and all 4,173 outputs fixed, 20 paired
runs gave 0.939891708 seconds for checked `int128` evaluation and 0.632799861
seconds for native unchecked `int128`.  The bounds were byte-identical.  Thus
overflow checks account for a measured factor of 1.485 in evaluation, but the
unchecked diagnostic remains 7.671 times slower than the 0.082490265-second
historical specialized batch.  It is not a proposed proof backend.

Holding that unchecked algorithm fixed and varying only fixed precision gave
another material diagnostic.  Scale `10^7` accepted 4,173/4,173 in 0.407803029
seconds, versus 0.638215640 seconds at scale `10^10`, a factor of 1.565.
Scale `10^6` was faster in one run but accepted only 4,149/4,173 and is
rejected.  The accepted `10^7` diagnostic is still 4.944 times slower than
historical specialized C++.  Its paired phase-table SHA-256 is
`e399df6206ec7ab66ed8ef09152ed595fbc23ab8a49644b645371d3c25844bc6`.

These results separate three issues.  Checked arithmetic is material;
fixed-point magnitude/precision is material; and a roughly fivefold native
gap remains even after removing both costs as far as this accepted experiment
allows.  The next cheap native experiment should therefore hold the accepted
operation graph fixed while replacing integer square-root and/or endpoint
arithmetic with a hardware-rounded diagnostic implementation.  It must keep
all 4,173 boxes accepted and report complete-batch time.  Only a material
winner will justify reusable rounding/square-root proofs and Candle dispatch.
No unchecked lane, rejected scale, or current dihedral specialization will
receive proof work.

## Update: reusable square-root preparation is bounded

The scale-`10^7` unchecked diagnostic was next used to separate reusable
untrusted square-root preparation from recurring validation.  All seven roots
per box were either computed during numerical evaluation or computed once in
the preparation phase and then consumed through the same squaring-based
certificate checks.  Twenty order-balanced full-batch pairs gave:

| Root schedule | Preparation | Evaluation | Complete batch | Accepted |
|---|---:|---:|---:|---:|
| Compute during evaluation | 0.183491426 s | 0.408547342 s | 0.592038768 s | 4,173/4,173 |
| Prepare, then validate | 0.345616653 s | 0.324471469 s | 0.670088122 s | 4,173/4,173 |

The output bounds are byte-identical.  Reusable preparation therefore buys a
1.259-fold recurring-evaluation improvement, but recomputing it for one cold
batch loses 13.2% overall.  The phase table has SHA-256
`bc24631c75e60e6d1f2bf6c89b0ad813c7f58e0dd2f6ad94105ad2188d995f02`.

A hardware floating-point seed followed by exact integer correction was also
tested for preparation.  The seed is not trusted; the corrected integer result
and existing certificate squares determine the output.  Twenty pairs reduced
preparation from 0.336249406 to 0.262807649 seconds and the cold batch from
0.658988161 to 0.585664867 seconds, with byte-identical 4,173/4,173 results.
Its phase-table SHA-256 is
`b12e908da2eba00d6032b50b9654810cb80465de390d27fc9c9ab684b3b3a6fc`.

This is a bounded improvement, not the larger architecture.  Even removing
root generation from recurring evaluation leaves about 0.3245 seconds, close
in order of magnitude to the historical generic-composition batch's 0.3302
seconds but still 3.93 times the historical specialized 0.08249 seconds.
Those implementations do not produce the same enclosures--the historical
generic lane accepted only 52 boxes--so the timing similarity is diagnostic,
not a controlled equivalence claim.  It nevertheless shows that square-root
generation cannot explain the remaining orders-of-magnitude objective.

The next large-gap experiment should compare a hardware-rounded endpoint
implementation of the accepted operation graph with a genuinely low-work
specialized primitive, while preserving the complete acceptance and bound-
tightness gates.  The current rejected dihedral composition remains closed,
and neither hardware-seeded untrusted preparation nor unchecked arithmetic is
a proof backend.

A bounded source-surface review also confirms that the genuine historical
primitive is not the small identity substitution already rejected.  Its
optimized `U126`/`U135`, `setDeltaFull`, `setDeltaX4`, `Dsqrt`, and
`setDihedral` path spans roughly 430 lines of sign-directed value, gradient,
and Hessian range code before shared interval machinery.  Porting and proving
that path could still be worthwhile at Flyspeck scale, but it is a substantial
reusable numerical-library project.  It should first be reproduced as a
complete native prototype; the existing dense specialization should not grow
through more isolated formula patches.

## Update: endpoint arithmetic is not the remaining large lever

The proposed hardware-endpoint discriminator is complete on the full 4,173-box
fixture.  It holds the accepted operation graph, scale `10^7`, prepared square
roots, and Taylor completion fixed.  The candidate stores integral fixed-scale
endpoints in `long double`, pads every quotient outwards by one fixed-scale
unit, and then converts only the final upper bound to the exact comparison
type.  This is an untrusted attainable-time experiment, not a sound rounding
backend.  The gate requires every candidate upper bound to contain the native
`int128` upper bound and requires the complete certificate to remain accepted.

Twenty warmed, order-balanced pairs gave:

| Endpoint lane | Preparation | Evaluation | Complete batch | Accepted |
|---|---:|---:|---:|---:|
| Native `int128` | 0.343606176 s | 0.324682706 s | 0.668288882 s | 4,173/4,173 |
| Padded `long double` | 0.303689110 s | 0.329609298 s | 0.633298407 s | 4,173/4,173 |

The hardware lane is **1.5% slower** in recurring evaluation and only **1.055
times faster** for a cold complete batch because its preparation happens to be
cheaper.  All 4,173 final bounds are wider than the exact native bounds; none
is tighter.  The median widening is `8.26e-5`, the maximum is `5.979e-4`, and
the smallest acceptance margin falls from `7.94e-5` to `6.31e-5` while still
remaining positive.  Its evaluation remains **3.996 times** the historical
specialized C++ batch.

The paired timing and containment files have SHA-256
`ff560c24e5b8ad5840c462584f6b2ec3c0de301ba896f7ab56dd904640985725`
and
`052849188f6859893c73017333aa5f4447872cac177f19f0416e4fc1ae370dd5`
in run
`nl-native-case10173-full4173-long-double-paired-v3-dev-001`.

This separates the two remaining questions more sharply.  Native integer
representation and division rounding are not responsible for the roughly
fourfold current native/specialized gap on this fixture.  The original
approximately 341-fold native/specialized result remains important as the
starting architectural diagnosis, but the accepted scale, compiled-source,
support-aware, fixed-kernel, and reusable-preparation changes have already
reduced that particular native ratio to approximately four.  The independent
encoded-Candle/native ratio must still be remeasured after a winning operation
graph is chosen; the old approximately 15-fold figure must not be multiplied
by the current native ratio as though all measurements used the same program.

The next experiment will therefore change mathematical work while holding the
accepted fixed endpoint representation and complete-batch gate fixed.  It is a
bounded native port of the historical sign-directed route, staged as follows:

1. port the source-derived `setDeltaFull` value/gradient/Hessian enclosure as
   one fixed-scale primitive, retaining the current surrounding graph;
2. add `setDeltaX4` and the derivative-square-root handoff, checking every
   intermediate enclosure against the historical diagnostic fixture;
3. complete `setU126`/`setU135` and `setDihedral`, then measure all 4,173 boxes;
4. record preparation, recurring execution, complete-batch time, operation
   counts, peak memory, acceptance, and final-bound differences at each stage;
5. stop before proof integration unless the complete low-work route preserves
   4,173/4,173 acceptance and produces a material end-to-end win.

The previously corrected dense `U126`/`U135` composition remains rejected and
will receive no bespoke proof.  General interval/Taylor lemmas that the
low-work port needs may be reused, but proof work for a new primitive remains
bounded behind the native complete-batch gate.  If the low-work port wins, its
proof target is one reusable instruction theorem over all valid expressions
and boxes, followed by a fresh Candle/native measurement and a representative
multi-certificate batch.  That preserves the orders-of-magnitude objective
without treating another small arithmetic improvement as the architecture.

## Update: first low-work stage

The fixed-scale `setDeltaFull` stage is now executable.  It follows the
historical monotonicity structure rather than merely evaluating the same
polynomial interval expression: Hessian signs select endpoint environments for
each gradient component, and gradient signs select endpoint environments for
the value.  Mixed-sign coordinates remain intervals.  The Hessian formulas
are shared with the already checked direct polynomial implementation.

Twenty warmed full-fixture measurements gave:

| Delta enclosure | Mean time, 4,173 boxes | Interval products |
|---|---:|---:|
| Generic interval polynomial | 0.033646651 s | 146,055 |
| Historical sign-directed structure | 0.051894936 s | 617,604 |

The sign-directed stage is **1.542 times slower** by itself.  It nevertheless
tightens every one of the 4,173 value enclosures and every one of the 25,038
gradient enclosures.  Aggregate value width is 14.34% of generic, and aggregate
gradient width is 42.04% of generic.  The Hessian streams are identical.

A development validation pass checked every value, gradient, and Hessian at
all 64 corners of every box--267,072 vertex checks--and also required the new
enclosures to be subsets of the generic enclosures.  It passed with both native
and overflow-checked `int128`, producing identical aggregate widths.  This is
strong implementation evidence but is not a soundness proof.  The full native
validation pass costs about 1.22 seconds and is charged separately from the
candidate timing.

Evidence is in `nl-native-case10173-delta-full-v3-dev-001`; the paired phase
table has SHA-256
`72d86c9d0de947e939042e71dc695021c98c893fd4b0898c9b3351469ce0d706`.
The single checked-arithmetic cross-check is in
`nl-native-case10173-delta-full-checked-v1-dev-001`.

This stage is not an end-to-end speed win and therefore receives no standalone
proof.  It remains useful for the bounded complete port because the historical
algorithm spends tighter delta derivatives to avoid substantially more generic
Taylor/chain-rule work later.  The next stage combines this enclosure with the
historical derivative-square-root and `setDeltaX4` data.  Only the complete
dihedral replacement can answer the performance gate; the intermediate
1.542-times delta cost is explicitly carried into that total rather than
reported as a speedup.

## Update: complete low-work gate

The bounded complete port is now executable through the authenticated source
operation: sign-directed delta and delta-X4 enclosures, derivative square root,
optimized U126/U135 data, the historical dihedral gradient/Hessian identities,
fixed arctangent, and final Taylor handoff.  A block-rounding variant retains
raw fixed-point numerators across each delta/U polynomial and rounds once per
polynomial result rather than after every multiplication.

Twenty warmed, rotation-balanced runs over all 4,173 boxes gave:

| Numerical lane | Preparation | Evaluation | Complete batch | Accepted |
|---|---:|---:|---:|---:|
| Current generic fixed graph, native `int128` | 0.333467640 s | 0.320894934 s | 0.654362575 s | 4,173/4,173 |
| Historical formulas, native `int128` | 0.336173574 s | 0.384837947 s | 0.721011521 s | 4,173/4,173 |
| Historical formulas with block rounding, native `int128` | 0.333579927 s | 0.363728468 s | 0.697308395 s | 4,173/4,173 |
| Same block graph, padded `long double` endpoints | 0.295859555 s | 0.367438752 s | 0.663298307 s | 4,173/4,173 |

The unblocked historical port is 1.199 times slower than the generic fixed
graph.  Block rounding improves it by 1.058 times but leaves it 1.134 times
slower.  On the same block graph, padded hardware endpoints are 1.0% slower
than native integer endpoints in recurring execution.  Their cheaper
preparation happens to make the cold complete batch nearly equal to the
generic integer batch, but that untrusted lane widens every final bound and is
not a material winner.

The block historical integer lane has a smallest acceptance margin of
`5.23e-5`, versus `7.94e-5` for the generic fixed lane.  It is tighter on 1,334
final bounds, wider on 2,834, and equal on five.  The padded hardware lane
contains all 4,173 block-integer final bounds and reduces the smallest margin
to `4.27e-5`.

A separate full-fixture boundary diagnostic compares the port with the
historical C++ angle data.  At scale `10^7`, the fixed/historical mean angle
width ratio is 0.99858, the median is 0.99923, and the maximum is 1.00016.  All
4,173 full inequalities remain accepted.  The fixed result is allowed to be
tighter than the floating implementation; this is matched development
evidence, not a substitute for the general soundness proof.

The paired timing, generic-bound comparison, and hardware-containment hashes
are respectively
`ee98e27bb79ebfac1bba80c197541d5e5f83fe37ee1be7c3fd5e9aa0bef26741`,
`01df9faa14ec15e40a07dad3365a79e6704a77805599e3521a08e8760b92312a`,
and
`3c9bf65de653730e4e06611a4849fb4e02732c54d176994eaee59060b78ae7ac`
in run
`nl-native-case10173-historical-dihedral-paired-v3-dev-001`.  The boundary
analysis has SHA-256
`82ea757364d0f36bdf441c40eb9991a7e6e94746f94857442232211cb40fbdeb`.

### Revised larger-gap plan

This complete gate closes the current formula-specialization proof branch.
Neither the corrected dense specialization nor the source-derived historical
fixed port beats the accepted generic fixed graph, so neither receives a new
Candle instruction theorem.  The 6% block-rounding gain is retained as useful
machinery, not promoted as the architecture.

The original historical specialized C++ batch is still 4.409 times faster
than the best source-derived fixed port.  Because hardware endpoints did not
help while retaining fixed-scale division/floor at every interval operation,
the next bounded native discriminator is a genuinely whole-block,
directed-rounding implementation of the same compact historical data flow--not
another endpoint typedef.  It must report the same full acceptance and angle
boundary diagnostics.  Its purpose is to separate:

1. global/direct rounding and absence of repeated scale division;
2. compact data layout and control flow;
3. the remaining mathematical work.

If that direct-rounded lane approaches the 0.08249-second reference, the proof
design target becomes a compact whole-instruction checker with a small
rounding certificate or word-level implementation, rather than thousands of
individually normalized interval operations.  If it does not, the port/data
flow difference is inspected before any proof investment.

In parallel, the approximately 15-fold encoded-Candle/native gap remains an
independent target.  The current generic fixed graph is still the native
winner and remains the baseline for compact instruction representation,
one-time evaluator setup, and machine-word/overflow experiments.  It will be
remeasured on complete batches; the 4.409 and approximately 15 factors remain
separate and are not multiplied as if they were one controlled benchmark.

## Update: rounding-boundary count and exact quotient seed

The fixed evaluator now has an opt-in diagnostic counter around every exact
fixed quotient.  On the full 4,173-box fixture it reports:

| Lane | Preparation quotients | Evaluation quotients | Quotients/cell |
|---|---:|---:|---:|
| Current generic fixed graph | 759,486 | 5,691,972 | 1,364 |
| Historical block graph | 759,486 | 7,344,480 | 1,760 |

Thus the historical block graph crosses 29.0% more exact rounding boundaries
than the generic winner.  This explains why tighter local formulas do not
translate into native throughput.  The count table has SHA-256
`45e6df7379191933d0c60b5c6c057f78b2be0094ebd5765e02f8208996b7a526`
in `nl-native-case10173-rounding-counts-v2-dev-001`.

A second experiment tested whether individual signed-`int128` divisions could
be accelerated without changing their exact result.  An untrusted
`long double` quotient supplies an initial floor/ceiling estimate; exact
integer multiplication comparisons then correct it to the true quotient.
Overflow or unsupported denominator cases fall back to ordinary integer
division.  All 4,173 outputs are byte-identical to the normal lane.

Twenty warmed, order-balanced pairs gave:

| Quotient implementation | Preparation | Evaluation | Complete batch |
|---|---:|---:|---:|
| Native integer division | 0.331863378 s | 0.337879698 s | 0.669743076 s |
| Hardware seed plus exact correction | 0.357526351 s | 0.475566127 s | 0.833092478 s |

The seeded implementation is 40.7% slower in recurring evaluation and 24.4%
slower for the complete batch.  It is rejected and receives no proof or
integration work.  The paired timing-table SHA-256 is
`6251536eade496363c9213a3ac3b0138cfdd66215c876dc176b9dc9f30db7022`
in `nl-native-case10173-full4173-quotient-seed-paired-v1-dev-001`.

The architectural consequence is more specific than “division is slow.”
There are millions of rounding boundaries, but accelerating each one in
isolation loses.  The next numerical prototype must remove or amortize them
across a whole proved block.  It should start with the current generic winner,
not the slower historical graph, and must account for complete-batch
acceptance and theorem handoff.  The direct-rounded historical C++ result
continues to show the attainable scale, while this experiment prevents an
unproductive per-division optimization branch.

## Update: rounding attribution and controlled separation

The broader investigation remains active; the exact-bound specialization is
not being treated as the final architecture. A measurement correction is
important: the first committed profiler constructed labels even when disabled.
That changed timing only; numerical outputs, counts, and acceptance were
unchanged. All figures below come from corrected exact-source reruns with no
disabled-profile work. A new profile reconciles all
5,691,972 exact evaluation quotients on the 4,173 genuine boxes with their
outer source stages. The largest individual consumers are arctangent
(901,368), the 85-step angle polynomial (759,486), inverse (676,026), and
square root (667,680). All outer additions together consume 817,908 because
each intermediate addition performs another theorem-shaped Taylor
completion.

This led to two controlled experiments which separate generic mathematical
work from arithmetic implementation.

First, fusing only consecutive additions leaves the center jet and Hessian
calculation unchanged and delays completion until the result is next
observable. It removes 701,064 quotients, produces byte-identical final
bounds, accepts all 4,173 boxes, and improves 20-pair recurring evaluation
from 0.346915612 to 0.315135187 seconds (1.101 times). The cold complete batch
improves only 1.048 times. This is useful general lazy-completion machinery,
not an orders-of-magnitude result.

Second, both lanes used the same signed-128 graph and the same `2^23` scale.
The candidate replaced exact division by exact signed directed shifts only at
power-of-two scale denominators; arbitrary inverse and other denominators
still use division. Startup edge tests cross-check the signed shift formulas
against exact division. The candidate covers 95.60% of evaluation quotients,
produces byte-identical lane outputs, and retains 4,173/4,173 acceptance.
Twenty paired runs improve evaluation from 0.345876875 to 0.281755697 seconds
(1.228 times) and the cold complete batch from 0.693301632 to 0.620105444
seconds (1.118 times).

The profile, fused-add, and dyadic phase-table SHA-256 values are respectively
`c7119f2ab85a638fa05a0f99bb7cf3acbe13c2b0aff3950c3fba431e1f8b3076`,
`2f210939d9b2aef9a4b101838e94acb21d271118ac95921e673aac282cea2a41`,
and
`9d6640d3dbf273c12df730e95343e0718ac1fcae9369f98b6ea18e2918e42a34`.
The development runs are
`nl-native-case10173-rounding-profile-v4-dev-001`,
`nl-native-case10173-fused-add-paired-v4-dev-001`, and
`nl-native-case10173-dyadic-shift-paired-v4-dev-001`.

### Larger-gap decision

The original measured decomposition remains explicit: about 15 times from
the exact-output-matched native equations to encoded Candle, and about 341
times from the original generic native fixed-scale equations to historical
specialized C++. The latter is a historical starting gap, not the residual
ratio of every later native candidate. The dyadic-shift candidate is now
3.416 times the 0.082490265-second historical specialized batch on this
fixture. It is still an unproved native diagnostic and therefore has not yet
reduced the end-to-end formal cost.

The composition gate is now complete. Twenty rotated full-batch repetitions
put decimal division at 0.346125667 seconds of evaluation, dyadic shifts at
0.278252326 seconds, and dyadic shifts plus fused additions at 0.256804446
seconds. The two dyadic result streams are byte-identical; every lane accepts
4,173/4,173. The composition improves recurring evaluation by 1.348 times and
the cold complete batch by 1.166 times over decimal division, but remains
3.113 times the historical specialized batch. The phase-table SHA-256 is
`5c24cb1eb8e8241d4130edc5e1e1063c484ab8e60847a46fc84340920c2c7545`
in `nl-native-case10173-rounding-composed-paired-v2-dev-001`.

Their proof work stays bounded: reuse the general lazy-completion result for
addition runs and prove one general signed dyadic-rounding theorem with the
required range/scale argument. Neither should delay the next native
large-gap experiment.

A complementary spot check held dyadic shifts fixed and substituted the
source-derived historical derivative/dihedral graph. It remained slower at
about 0.335 seconds, so extra exact division was not the only reason that
graph lost. That branch remains rejected. The next large-gap native experiment
should hold the winning dyadic arithmetic fixed while reducing the complete
derivative/Taylor work per box through a compact specialized
square-root/dihedral or complete low-work box instruction. It must be judged
on the complete 4,173-box batch, acceptance, enclosure quality, preparation,
recurring time, and memory. Only a material winner earns a reusable general
instruction theorem and a new Candle/native measurement.

## Update: corrected winning-lane stage profile

The corrected composition measurement is 0.346125667 seconds for decimal
evaluation, 0.278252326 seconds for dyadic shifts, and 0.256804446 seconds for
dyadic shifts plus fused additions. The last lane is 1.348 times faster than
the decimal control, while cold preparation plus evaluation improves 1.166
times. All lanes still accept 4,173/4,173, and the same-arithmetic dyadic
streams remain byte-identical. The residual to the 0.082490265-second
historical specialized batch is 3.113 times.

An elapsed-time profile of that exact winning lane attributes 98.03% of its
instrumented evaluation. Exact rational-to-fixed job geometry is 23.50%, the
complete source indices 31--38 dihedral subgraph is 31.93%, the six prepared
coordinate-root blocks are 14.39%, five-step polynomials are 10.44%, and the
final source tail is 10.70%. Within the dihedral subgraph, no single operation
exceeds 6.45% of profiled time. The instruction and aggregate table hashes are
`2f526baf90582dbe6c0abd0d7035aa34f159cf77d84fdba92e6deac0b8bf73f3`
and
`48413ab306df793dc2f1e68a3de5f8266d94bed57b8374c9411cc72298059251`
in `nl-native-case10173-composed-stage-profile-v1-dev-001`.

This rules out treating another isolated nonlinear primitive as the large
architecture. The next cheap native discriminator is a whole-graph range
audit followed, if the range permits, by signed-64 normalized endpoints with
signed-128 raw products and accumulators. It holds the authenticated
derivative/Taylor graph and rounding choices fixed while testing the
distributed representation cost. Exact job-geometry conversion is tracked as
reusable preparation but is not credited as a cold-batch speedup merely by
moving it between phases. A generally proved complete-box checker remains the
larger target.

## Update: fixed range and narrow-product gate

The complete 4,173-box composed lane was range-profiled without changing its
mathematics. Rounded quotient results and interval multiplication operands
reach at most 45 magnitude bits; interval additions reach 44 bits and scaled
exact inputs 26 bits. None exceeds signed 64 bits. Raw products reach 68 bits
and Taylor/quotient numerators 83 bits, so wide raw accumulators remain
necessary. The range summary has SHA-256
`59029a58357522eab6ace97c2fd57f3e0787cb590e724ea4177418cf457f2405`
in `nl-native-case10173-fixed-range-profile-v1-dev-001`.

A bounded proxy then performed interval endpoint multiplication through
signed-64 operands into exact signed-128 products while leaving storage and
all other operations unchanged. Twenty rotated complete-batch repetitions
gave 0.278570053 seconds for wide products, 0.282200035 seconds with dynamic
narrow range checks, and 0.274445421 seconds for an explicitly untrusted
unchecked narrow diagnostic. Every output is byte-identical and every lane
accepts 4,173/4,173.

The unchecked recurring gain is only 1.015 times; checked execution is 1.3%
slower. The phase-table SHA-256 is
`f114fc7069929d166bf44b294c6eb5106104276db77f7b4f63f6763fe08e06cf`
in `nl-native-case10173-narrow-products-paired-v1-dev-001`.

This rejects a split-width container refactor and range proof as the next
investment. The residual cost is distributed whole-graph work, not ordinary
endpoint multiplication width. The next native gate must remove work across a
substantial authenticated source block or the complete box while retaining
certificate coverage and charging reusable geometry preparation honestly.

## Update: center tangent versus discarded center Hessian

A controlled full-fixture experiment now holds the fixed-point arithmetic,
directed rounding, authenticated formula, box Hessian, and final Taylor
handoff constant while removing one class of generic derivative work. The
historical-formula lane had built a complete second-order jet at the center,
although only its value and gradient survive. The candidate computes that
center tangent directly.

Across twenty rotated 4,173-box pairs, evaluation fell from 0.421083508 to
0.376574926 seconds, a 1.118-times gain; complete preparation plus evaluation
fell from 0.759238146 to 0.716522144 seconds. It removed 759,486 interval
products. Every box remained accepted and all emitted bounds are
byte-identical. The timing and common-bound hashes are
`70c4a446eaaad73ba2b66cd0048aeaf68a316e2b728c0fb30ba004dbac3551ba`
and
`0cb9afcfb27561526728fed8b498a25bda337b8baaa2a35aa8c92bf8093c51c1`
in `nl-native-case10173-center-tangent-paired-v1-dev-001`.

This is useful attribution, not the next proof target. The candidate remains
4.565 times the historical specialized C++ batch and is slower than the best
generic dyadic/fused native lane. No standalone center-tangent instruction
proof will be started. The code is retained only as reusable machinery for a
complete raw primitive.

The next concrete factorial comparison will accumulate center tangents and
box Hessians for the complete authenticated formula and perform Taylor
completion once. It will first use the current exact dyadic arithmetic; a
material winner will then run through a development-only direct outward
hardware-endpoint backend with the same numerical graph. That separates
derivative/Taylor architecture from representation and rounding on the same
genuine boxes. Acceptance, enclosure quality, memory, reusable preparation,
recurring execution, and cold total remain mandatory gates, followed by a
small multi-certificate batch before proof investment.

## Update: complete additive-leaf handoff

The authenticated expression has thirteen polynomial/coordinate-root leaves
whose value and gradient bounds are unused until they join the final sum. A
new source-shape-checked lane carries their center tangents and box Hessians
directly and performs one final Taylor handoff. It leaves the dihedral
subgraph, fixed dyadic arithmetic, and final acceptance calculation unchanged.

Twenty rotated 4,173-box pairs reduced completed results from 100,152 to
45,903 and dyadic shift quotients from 4,740,528 to 3,981,042. Evaluation fell
from 0.272384195 to 0.251070965 seconds, a 1.085-times gain. Preparation plus
evaluation improved only 1.028 times, from 0.596344441 to 0.579948695 seconds.
Every box is accepted and every result is byte-identical. Peak RSS in one
full-run observation remained about 38 MB. The timing table has SHA-256
`e6898734703a4d0c2cdd70fbf847bf37696e7337c03a84e56e742a076869777b`
in `nl-native-case10173-additive-completion-paired-v1-dev-001`.

This mechanism remains a component, not an independent proof target: the
candidate is still 3.044 times the specialized C++ batch. The next cheap
factorial lane will hold this graph fixed and compare padded fixed-grid
long-double normalization with an explicitly untrusted unrounded-quotient
lower bound. A large difference would justify building a genuinely outward
hardware-endpoint backend; a small difference would redirect effort to a
complete specialized primitive. Neither diagnostic changes the requirement
for full acceptance, enclosure-quality reporting, cold total cost, and a
multi-certificate gate before proof work.

## Update: unrounded hardware lower bound

The compacted graph was run in a controlled long-double factorial comparison.
Both lanes execute exactly 4,231,422 quotients and 2,220,036 interval products;
exact-zero skipping is disabled so rounding cannot alter control flow. The
control uses padded fixed-grid floor/ceiling, while an explicitly untrusted
lane performs raw hardware division without outward rounding.

Twenty rotated full-batch pairs reduced evaluation from 0.272611681 to
0.253648174 seconds, only 1.075 times. Cold preparation plus evaluation
improved 1.035 times. Both lanes report 4,173 accepted boxes, but the unrounded
lane is tighter on every box because it has discarded sound outward rounding;
it is timing evidence only. The timing and bound-comparison hashes are
`8cbba2b3495af427084384af40d9649f6c320256776700a3e33373c23e323e3f`
and
`0568af8acbf785018a218c5388213a1c15c834e92f806d0c22f1f1571108ee05`
in `nl-native-case10173-unrounded-lower-bound-paired-v1-dev-001`.

The lower bound remains 3.075 times the specialized C++ batch and is close to
the separately measured exact int128/dyadic lane. Directed normalization is
therefore not the missing multi-fold factor, and a proved outward hardware
backend is not the next investment. A preliminary same-arithmetic historical
graph run was only about 2% faster than the generic graph. The next cheap
factorial test holds those unsafe graphs fixed and changes scalar width/layout
from `long double` to the historical verifier's `double`; that decides whether
to pursue representation/layout or a more faithful whole-checker port.

## Update: hardware width and graph factorial

The same unrounded diagnostic was crossed over hardware `long double` versus
`double` and generic versus source-derived historical derivative graphs.
Twenty rotated 4,173-box repetitions put generic evaluation at 0.255428156
seconds for `long double` and 0.171455856 seconds for `double`, a 1.490-times
gain. The historical graph took 0.257828089 and 0.177338674 seconds
respectively, making it 3.4% slower than generic on `double`. Both width pairs
produced identical records for all boxes. The timing-table SHA-256 is
`a9f88cc2f51c40c4a519eef36e3fa57be0b72adfde78fa2273de439052207681`
in `nl-native-case10173-hardware-width-factorial-v1-dev-001`.

A matched `double` rounding control measured 0.186921510 seconds with padded
fixed-grid normalization and 0.172295763 seconds without it. Thus rounding
accounts for only another 1.085 times; the conservative diagnostic remains
2.266 times the specialized C++ batch. Its timing-table SHA-256 is
`4dd3a3870f1f92ed5eff3f559da4658a94f1b31de962f11699f5b58be4f1c24f`
in `nl-native-case10173-double-rounding-paired-v1-dev-001`.

The width/layout effect is real, while the remaining approximately 2.1-times
unsafe-native gap is whole-checker/dataflow rather than quotient rounding or
the tested historical formula graph. A source audit then ruled out treating
CakeML runtime words as an existing reflected primitive: the proof-producing
compute language contains only unbounded `Cexp_num` values and pairs, with no
word node or word multiplication.

The next bounded gate will therefore measure a closed, assumption-free
two/three-limb multiply/shift/round microkernel using the current compute
contract. The observed range requires at most 45-bit rounded values, 68-bit
products, and 83-bit Taylor/quotient numerators. Only a material reflected
win advances to one generally proved outward dyadic engine and complete-box
checker. A loss redirects work to whole-checker layout/control; it does not
justify extending the trusted compute datatype. The unsafe floating lanes
remain diagnostics and can never support a formal claim.

## Update: reflected limb rejection and the next bridge experiment

The bounded representation gate has now run inside the existing
proof-producing evaluator. A closed benchmark repeated one exact 68-bit
multiply followed by a 23-bit downshift 32,768 times. The control used one
unbounded natural; the candidate used two 30-bit limbs and reconstructed the
same quotient from low, cross, and high products. Both lanes produced exactly
the same closed, assumption-free theorem.

Because Candle's internal clock is deterministic, the existing read-only
phase observer supplied wall and process times. One balanced run measured
0.096525104 seconds for the natural lane and 0.105102460 seconds for the limb
lane, a 1.089-times limb slowdown. A second run's warm samples measured
0.125032158 and 0.132089458 seconds, a 1.056-times limb slowdown. The first
sample of the second run was an isolated 0.204-second control outlier and is
preserved rather than hidden in an aggregate. The accepted run is
`cv-nl-limb-mul-shift-v9-dev-001`; its phase-profile SHA-256 is
`5a3fc5350fc2aa164291cc8d8a483f9aa80007630a9f827d2bc483f7cf8fcf66`.

This rejects the limb engine. It did not win before charging signed interval
structure, pair handling, range validation, or its reusable correctness proof,
so no such proof or complete limb checker will be developed.

The broader investigation remains active. The most informative controls now
point in different directions:

- the hash-pinned historical C++ implementation changes from 0.082490265
  seconds and 4,173/4,173 acceptance under its specialized route to about
  0.326891 seconds and 52/4,173 under generic composition on the same genuine
  boxes, holding that library's endpoint representation fixed;
- the current native generic graph gains 1.490 times from `long double` to
  `double`, and only 1.085 times from removing padded normalization, while the
  tested historical-formula substitution does not win;
- the original approximately 15-times encoded-Candle/exact-native gap and
  approximately 341-times generic-native/specialized-C++ starting gap therefore
  remain separate. Later native candidates reduce the latter only as untrusted
  diagnostics; those gains have not yet become a formal checker.

The next native gate will be a faithful complete-box bridge. The pinned C++
specialized route will export center/tangent, derivative/Hessian or table-use,
Taylor-remainder, final-bound, and primitive-count boundaries for genuine
boxes. The current native harness will reproduce that complete data flow using
the same hardware-`double` arithmetic. Only after those boundaries and full
acceptance agree will the same algorithm be crossed with exact outward dyadic
arithmetic. This first holds arithmetic fixed while changing the
derivative/enclosure algorithm, then holds that algorithm fixed while changing
arithmetic.

The existing `historical-dihedral` lane is not this experiment: it inserted
historical formulas into the current theorem-shaped Taylor machinery and was
slower. The bridge must include the specialized bound/table choices and
complete-box handoff that produce the C++ acceptance behavior. Preparation,
recurring execution, cold total, memory, bound tightness, and all 4,173
acceptances remain mandatory gates. Only a material full-batch winner earns
one authenticated complete-box instruction theorem; the dyadic-rounding and
deferred-completion proofs remain bounded candidate components rather than
independent projects.

## Update: matched Taylor-stage and cost-boundary factorial

The first complete-box bridge measurement is now available in
`nl-native-stage-factorial-v4-dev-001`.  Seven runs of the pinned historical
C++ implementation separate domain construction, `evalf`, and final
`upperBound` work:

| Route | Complete evaluation | `evalf` | Final bound | Accepted |
|---|---:|---:|---:|---:|
| Specialized C++ | 0.083159749 s | 0.080885290 s | 0.001299143 s | 4,173/4,173 |
| Generic C++ composition | 0.324105190 s | 0.321779319 s | 0.001333550 s | 52/4,173 |

Thus 97.27% of specialized evaluation is in `evalf`, generic `evalf` is 3.978
times slower, and the final Taylor aggregation is only 1.56% of specialized
evaluation.  The principal historical advantage is construction of the
derivative/enclosure data, not the final sum.

The matching first-16 stage records also change the interpretation of bound
quality.  The current exact fixed-scale generic graph accepts all 16 and has a
mean quadratic term 0.0001130003 smaller than the specialized C++ route.  Its
mean final upper bound is 0.0001096317 more negative.  The old specialized
algorithm is therefore faster despite slightly looser final bounds on this
sample.  Replacing only the current dihedral subgraph with the source-derived
historical formula makes the mean quadratic term 3.3% larger and the final
bound 0.0000407098 less negative, while prior full-batch evidence makes that
lane slightly slower.  That shim is rejected as the bridge.

The next bounded native prototype will reproduce the pinned specialized
center/gradient/Hessian data flow as a small POD hardware-double path and
match the exported 16-box stages before running all 4,173 boxes.  Only a
full-batch winner with complete acceptance, bound containment, and measured
preparation/recurring/memory costs advances to the same-algorithm exact-dyadic
crossing.  Only that successful crossing advances to one generally proved
complete-box instruction in `Kernel.compute`.

This keeps both original gaps visible.  The roughly 341-fold value is the
starting generic-native/specialized-C++ baseline; later untrusted native work
has reduced its numerical portion to roughly 3.9 times with exact `int128` and
2.1 times with unsafe hardware `double`.  The separate roughly 15-fold
encoded-Candle/exact-native gap has not been eliminated.  A formal speedup
claim requires crossing both boundaries rather than reporting the improved
native diagnostic as if it were already a Candle result.

The current exact-bound specialization proof remains limited to its small
reusable lemma and one integration test.  It may close if cheap, but it will
not grow into another per-expression proof layer before the full-batch native
gate demonstrates the recurring benefit.
