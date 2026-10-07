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

The next native lane will keep checked `int128`, scale `10^10`, fixed nonlinear
kernels, outward rounding, and the genuine boxes fixed.  It will change only
the generic derivative/Taylor work by replacing the complete dihedral
subgraph with a faithful specialized value/gradient/Hessian plan.  The 128-box
gate will require complete acceptance, report bound widening, preparation,
evaluation, memory, and operation counts, and compare against the checked
fixed-kernel control above.  A fast lane that loses any current cell does not
pass.

If that lane materially wins, the native-input capture will be extended to
all 4,173 boxes and the same comparison will charge shared preparation once.
Only after the full batch passes will the specialized algorithm be held fixed
while endpoint representation is varied, including a checked fixed-width
lane and an outward-rounded hardware lane as an attainable-time diagnostic.
That ordering separates generic analytic work from representation/rounding
instead of changing both at once.

Formal work stays bounded in parallel.  The current angle specialization may
receive its one general analytic-containment theorem and exact authenticated
dispatch/fallback theorem; it will not grow into fixture-specific rewrites.
The fixed nonlinear kernels are also plausible reusable proof targets--their
contracts reduce to general integer rounding, square-root certificate, and
alternating-series lemmas--but integration waits for the complete numerical
plan decision.  No proof effort will target unchecked arithmetic.  The
complete 4,173-box accepted time, including reusable preparation and theorem
handoff, remains the architecture-selection gate.
