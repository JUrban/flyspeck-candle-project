# Candle reflected tame-graph classification plan, v2

Date: 2026-10-06 UTC

Status: **DEVELOPMENT / NON-RELEASE**

This is the authoritative tame-graph reflection plan. It supersedes the
scheduling and computation architecture in
`Candle_tame_graph_reflection_plan_2026-10-05.md` and the two-backend and
non-final duplicate-node portions of
`Candle_tame_graph_parameter0_checker_contract_2026-10-06.md`.

The revision incorporates
`docs/advice/Candle_tame_graph_reflection_plan_review_2026-10-06.md` and the
project response beside it. The decisive changes are:

- use one deterministic replay backend with checked hints only at final
  leaves, rather than a whole-tree witness certificate;
- make the general pruning/invariant proof an early workstream and explicit
  gate, rather than postponing it until after a complete prototype;
- measure complete `p = 0` and a representative bounded `p = 2` subtree;
- regenerate final-constant scale counts and apply a numeric go/no-go gate;
  and
- use logical sequential chunk composition, not authenticated external
  frontier files or parallel theorem production.

This S4 lane remains subordinate to the functional-first direct Flyspeck,
LP, and nonlinear lanes. It must not displace a runnable direct/S2/S3 task or
change the existing S3 acceptance contract.

## Exact destination

The lane is complete only when HOL Light running on Candle derives the exact
closed theorem:

```text
|- import_tame_classification
```

where the production definition is:

```text
import_tame_classification =
  (!g. PlaneGraphs g /\ tame g
       ==> (?y. y IN archive /\ iso_fgraph (fgraph g) y))
```

The theorem must use the exact `PlaneGraphs`, `tame`, `archive`, `fgraph`, and
`iso_fgraph` constants loaded by the direct Flyspeck manifest. It must then
discharge the remaining premise of the existing final Flyspeck theorem in a
clean direct Candle run.

No Isabelle theorem import, OCaml HOL Light runtime, external graph generator,
digest, count, or comparison run contributes proof authority. External tools
may generate hints and reference traces, but Candle must check the resulting
ordinary data under general HOL theorems.

## Authenticated historical basis

The repository now retains the AFP release archive:

```text
third_party/afp-flyspeck-tame-2014-08-28/
  afp-Flyspeck-Tame-2014-08-28.tar.gz

SHA-256
54aa014cc8de1bc178ef68cc4e88932aefe9a61dcd17712ae714f39ae411102c
```

The generated inventory records all release members, hashes, extraction
rules, Flyspeck overlaps, and declaration/import inventories. The independent
review also compared the source against the last pre-release AFP mirror
commit.

The corrected overlap baseline is:

- `formal_graph/isabelle_tame` contains 13 theory files;
- eleven overlapping theory files are byte-identical, and those eleven
  already include `Completeness.thy`;
- `Tame.thy` differs only in its source-URL comment;
- `Vector.thy` exists in the Flyspeck checkout with no counterpart in the
  checked AFP entry;
- `Tri.ML`, `Quad.ML`, `Pent.ML`, and `Hex.ML` are byte-identical between the
  checked sources; and
- `import_tame_classification` is defined in
  `general/the_kepler_conjecture.hl`, with a second copy in
  `formal_graph/isabelle_hollight_translation.hl`.

The machine-readable correspondence ledger is presently a source inventory.
A same name, matching statement, or legacy translation entry is only a proof
lead. The proof ledger required below must bind each premise to the exact
constant or theorem actually loaded by the direct manifest.

## Scale baseline

AFP `ArchStat.thy` records this historical `next_tame` search:

| `p` | generated nodes | final visits | archive classes |
| ---: | ---: | ---: | ---: |
| 0 | 312,764 | 501 | 9 |
| 1 | 134,291,356 | 27,050 | 1,105 |
| 2 | 1,401,437,009 | 301,560 | 15,991 |
| 3 | 334,466,383 | 19,120 | 1,657 |
| total | 1,870,507,512 | 348,231 | 18,762 |

The historical total is about 5,980 times the `p = 0` search. AFP records an
11-hour generated-PolyML run on hardware of its period.

These are not production counts. They predate the final archive sizes of
9 / 1,253 / 16,080 / 2,373, and the final constants can change both node and
final-visit counts. An instrumented untrusted reference run must regenerate
the counts before a large reflected replay is scheduled.

The first implementation is treated as serial. Different Candle processes
cannot combine independently produced theorems without a theorem-import
mechanism, which this project forbids. Multiple `Kernel.compute` calls may be
composed sequentially inside one kernel state and preserved by checkpoints.

## Isabelle oracle status

AFP is a specification and differential oracle, not a theorem source for this
lane. In `ArchComp.thy`:

- `pre_iso_test3` through `pre_iso_test6` and `same3` use `eval`;
- `same4`, `same5`, and `same6` use `cond_eval`; and
- `cond_eval` invokes `Skip_Proof.cheat_tac` unless
  `ISABELLE_FULL_TEST=true`.

The archives also enter through code-runtime ML definitions. Therefore a
default AFP session does not provide a kernel-evaluated classification fact
for `p = 1,2,3`. Reference code runs remain valuable, but a closed Candle
result will be a stronger independent kernel-level check of the enumeration.

## Existing reusable assets

The following work remains valid under v2:

- authenticated AFP source and generated source/declaration inventory;
- the initial Isabelle-to-HOL correspondence ledger as triage input;
- HOL Flyspeck graph definitions in `tame_defs2.hl` and structural results in
  `tame_list.hl`;
- production tameness, archive, and isomorphism definitions;
- typed reflected face, fgraph, and vertex-map encoders and decoders;
- round-trip and injectivity theorems;
- strict rejecting structural validators and their adversarial tests; and
- the existing proof-producing `Kernel.compute` handoff pattern.

The current data layer does not yet prove canonical ordering, graph
isomorphism, archive binding, enumeration completeness, or any S4 theorem.

## Near-term executable-enumeration milestone

Execution feasibility is tested in parallel with the proof ledger rather than
waiting for every pruning and classification obligation to close.  The first
decision-bearing benchmark will faithfully preserve the AFP graph/state
representation, successor generation, pruning decisions, and deterministic
worklist order.  It will:

1. complete the smallest final-constant partition (`p = 0`);
2. execute a fixed representative bounded prefix of the dominant `p = 2`
   partition;
3. compare visited/pruned/final counts and result-graph identities against the
   independently instrumented Isabelle run; and
4. report cold preparation, encoding/program construction, evaluator work,
   theorem handoff, required repeats, retained state/checkpoint size, peak
   memory, and total elapsed cost.

An ordinary ML implementation may be used as a differential stepping stone,
but it is not the feasibility result and has no proof authority.  The key
measurement must run the intended representation and algorithm through
`Kernel.compute`.  A matching development run is still DEVELOPMENT /
NON-RELEASE evidence until the general refinement, invariant, pruning, and
coverage theorems close.

## Corrected trusted architecture

```text
untrusted reference enumerator / hint producer
                    |
                    v
       final-leaf archive hint stream
                    |
                    v
 typed HOL deterministic next_tame replay
                    |
                    v
     proved refinement to a cval program
                    |
                    v
             Kernel.compute
                    |
                    v
       general HOL coverage theorem
                    |
                    v
        |- import_tame_classification
```

The checker deterministically traverses the complete `next_tame p` tree. A
hint is consumed only at a final graph that the executable refutation
machinery does not reject. It contains:

- an index into the production `tame_archive_lists`, or a proved HOL filter
  of that value;
- an explicit vertex map; and
- any orientation bit needed by the exact map checker.

Every supplied map and archive index is checked. Hint order follows the
deterministic replay order but has no independent mathematical authority.

### Three node outcomes

1. **Expanded:** the graph is non-final; the checker computes the exact
   `next_tame p` successor list and visits every successor.
2. **Final and matched:** the executable test does not refute the graph; the
   checker consumes one hint and proves isomorphism to the indicated
   production archive entry.
3. **Final and rejected:** the executable lower-bound/tameness test rejects;
   a general HOL theorem proves that such a final graph cannot satisfy
   `tame`.

There is no producer-supplied pruning label and no non-final duplicate case.
The latter would require a new theorem that isomorphism preserves the
order-sensitive successor selection. AFP provides no such theorem, and v2
does not depend on one.

The design deliberately avoids porting tries, maps, quasi-orders, AFP
worklists, `samet`, and the searching `iso_test` solely to reproduce archive
deduplication. A future optimization may add such machinery only after a
general proof and a measured benefit; it cannot be assumed in the first
soundness argument.

## Target coverage theorem

Define, with exact HOL types substituted:

```text
covers p A S <=>
  !s g.
    s IN S /\
    (s,g) IN RTranCl (next_plane p) /\
    finalGraph g /\ tame g
    ==> ?a. MEM a A /\ iso_fgraph (fgraph g) a
```

The proof library must establish these general rules:

- `covers p A {}`;
- `covers` distributes over finite union;
- a final state with a checked map to an entry of `A` is covered;
- a final state with a proved executable refutation is covered; and
- an invariant non-final state is covered when the exact set of its
  `next_tame p` successors is covered.

The last rule is the HOL destination of the AFP
`filterout_untame_succs`/`filter_tame_succs`, `untame_negFin`,
`next_tame0_comp`, and `next_tame_comp` argument.

The reflected theorem should be uniform in parameter, archive, fuel, hint
stream, and start stack, with a shape such as:

```text
replay p A fuel hints stack = SOME remaining_hints
==> covers p A (set stack)
```

The production acceptance equation additionally fixes the expected hint
consumption. Fuel exhaustion, malformed data, missing or extra required
hints, wrong indices, and invalid maps reject.

## Archive binding and theorem direction

Hints should index `tame_archive_lists` directly. If partition-specific lists
are useful, define them inside HOL by filtering the production value by
maximum face size. The four `.ML` archive files remain authenticated fixtures
and differential oracles, not the logical source of membership.

The required direction is:

```text
enumerated tame final graphs <= production archive, up to iso_fgraph
```

The converse direction in AFP `samet` is optional consistency evidence.
Archive minimality is not a project goal. Counts and hashes cannot prove
either direction.

The archive representation theorem, including the cost of proving a cval
literal for the roughly 9 MB production term, must be measured as reusable
preparation.

## Typed executable specification

Define the replay and its primitives first as typed HOL list functions. Derive
the cval implementation by proved refinement; do not maintain an independent
handwritten checker algorithm.

AFP's optimized `enum` uses `IArray`, while `Kernel.compute` has no array
representation. The first checker will use the logical `enumerator` function
directly. A list-encoded table may replace it only with a proved equivalence
and a measured benefit.

The current representation module manually duplicates logical functions and
all-variable cval equations. Before porting the larger executable spine,
prototype a narrow first-order HOL-to-cval translator/refinement generator.
The generator is untrusted tooling: generated definitions and refinement
theorems must be checked by the HOL kernel, and unsupported constructs must
fail closed.

## General proof burndown

The proof-risk work begins before full enumeration. Construct a
statement-level HOL skeleton that derives `covers` and the partition theorem
from named premises for:

- graph and generator invariants;
- face-division correctness;
- preservation properties of `next_plane`;
- correctness of all executable pruning predicates;
- lower-bound refutation of final rejected states;
- preservation of every tame completion by `next_tame`; and
- explicit-map correctness against production `iso_fgraph`.

Each premise must record its exact direct HOL constants, AFP theorem leads,
dependency closure, source-line weight, existing HOL leads, and proof status.
The initial proof-risk weight includes:

| AFP theory | source lines |
| --- | ---: |
| `FaceDivisionProps` | 4,942 |
| `Invariants` | 2,826 |
| `ScoreProps` | 725 |
| `PlaneProps` | 680 |
| `GeneratorProps` | 537 |
| `GraphProps` | 437 |
| `EnumeratorProps` | 429 |
| `LowerBound` | 297 |
| `TameProps`, `TameEnumProps`, `Plane1Props` | 160 |

Line weight guides triage; it is not an estimate of HOL proof length.
`tame_list.hl` may discharge portions of this work, but only exact theorem
matches against the direct manifest reduce the burndown.

The lane chooses HOL Light reproof rather than Isabelle proof transport.
There is no existing checked Isabelle/HOL-to-HOL-Light importer in the
production path; building one would be a separate foundational project, and
the computed AFP conclusions themselves use code-runtime definitions and
conditionally skipped evaluation. AFP proofs remain specifications and proof
guides. Final authority remains one HOL Light/Candle kernel.

## Logical chunking

Chunk boundaries are computed inside HOL. A proved splitter constructs a
frontier; separate sequential calls cover sublists of it; the finite-union
rule composes their coverage in the same Candle kernel state.

External frontier order, files, counts, and hashes may be recorded as
diagnostics but are not soundness premises. A truncated or changed external
fixture must either decode to the wrong logical value and reject or merely
fail to drive the checker to acceptance.

Stable checkpoints should preserve:

- the graph representation and archive theorem;
- the general soundness library;
- each completed partition theorem; and
- long sequential chunk accumulations at coherent boundaries.

A failed or partially consumed replay state is never continued as evidence.

## Numeric feasibility gate

Before a full `p = 1,2,3` reflected replay, measure:

1. final-constant node, pruned, final, and hint counts from an instrumented
   reference run;
2. complete reflected `p = 0` replay;
3. a deterministic bounded `p = 2` subtree exercising quadrilateral,
   exceptional-face, nonzero-excess, and multiple-size branches;
4. cold source/archive preparation;
5. cval construction and encoding;
6. evaluator wall time and compute-clock use;
7. theorem decoding/handoff and retained theorem size;
8. peak RSS, checkpoint size, and hint bytes; and
9. final-map checking separately from node generation/pruning.

Use the measured final-constant counts and representative `p = 2` per-node
cost, not only a `p = 0` multiplier.

The provisional scheduling gate is:

- at most seven days projected sequential evaluator time for one production
  replay: proceed;
- seven to thirty days: make one bounded, measured representation/evaluator
  optimization and remeasure; and
- over thirty days, or outside the agreed term/checkpoint/memory envelope:
  stop the full replay and revise the checker representation first.

These thresholds are scheduling policy, not logical assumptions, and may be
changed only by an explicit recorded project decision.

## Staged implementation

### Stage 0: historical basis and proof skeleton

1. Retain and audit the authenticated AFP release manifest.
2. Correct the overlap/source-location baseline recorded above.
3. Regenerate the correspondence ledger against the exact direct-source head.
4. Produce the weighted theorem-level proof ledger.
5. State `covers`, its compositional rules, and the final partition theorem;
   derive the latter from explicit named premises.

Exit gate: the missing mathematics is enumerable and tied to production HOL
constants. No computation result is interpreted as classification.

### Stage 1: reflected data and production archive

1. Retain the proved encoders, total decoders, round trips, injectivity, and
   structural rejection tests.
2. Add only the canonical rotation/order properties required by the checker.
3. Implement explicit-map checking and prove it implies exact production
   `iso_fgraph`.
4. Represent `tame_archive_lists` once and prove the cval binding.
5. Run the genuine nine triangle entries through the reflected structural and
   map path, including mutations.

Exit gate: a closed theorem binds authentic reflected archive data to the
production archive constant. This is not classification.

### Stage 2: typed replay and scale prototype

1. Define deterministic list replay in typed HOL.
2. Derive/refine the cval program.
3. Instrument the final-constant native/reference run.
4. Run the complete `p = 0` computation.
5. Run the fixed bounded `p = 2` subtree.
6. Record the full cost decomposition and apply the numeric gate.

Exit gate: the exact program intended for the soundness proof has measured
functional and scaling evidence. No hand-picked archive self-check suffices.

### Stage 3: general soundness

1. Discharge the named invariant and face-division premises.
2. Prove executable pruning/lower-bound correctness.
3. Prove tame-completion preservation under `next_tame`.
4. Prove explicit final-map correctness and replay soundness.
5. Prove logical frontier splitting and union composition.

Exit gate: replay acceptance implies `covers` generally, independently of
the production hint stream.

### Stage 4: close parameter 0

1. Check the complete authentic `p = 0` hint stream with `Kernel.compute`.
2. Apply general soundness to the exact production archive.
3. Obtain the closed exact parameter-0 classification theorem.
4. Run adversarial data/hint/fuel/map mutations.

Exit gate: empty hypotheses, allowed axioms only, stable theorem fingerprint,
and repeat evidence.

### Stage 5: parameters 1, 2, and 3

Process each partition in order. Use proved logical frontier splitting when a
monolithic computation approaches evaluator, compute-clock, term, memory, or
checkpoint limits. Compose chunks sequentially by `covers` union rules.

Exit gate per partition: a closed theorem over the exact production archive,
stable fingerprints, measured costs, and negative mutations.

### Stage 6: final aggregation and direct integration

1. Combine the four partition theorems with the seed-bound theorem.
2. Derive exact `|- import_tame_classification`.
3. Export a stable theorem binding for the direct build.
4. Insert reflected support/check actions at a regenerated manifest boundary.
5. Discharge the existing final Flyspeck premise and verify a closed Kepler
   theorem in a clean direct Candle run.

Exit gate: two clean runs and an authenticated resume agree on partition,
classification, and final-theorem semantic fingerprints, hypotheses, and
axioms.

## Required negative tests

At minimum, the reflected path must reject:

- malformed/noncanonical face, fgraph, archive, map, option, pair, list, or
  numeric encodings;
- changed production archive entries or wrong archive indices;
- vertex maps that are partial, noninjective, out of range, orientation-wrong,
  or fail to consume the exact target faces;
- missing or surplus required final hints;
- hints reordered against deterministic traversal;
- a different seed parameter;
- fuel exhaustion;
- a chunk or frontier with a wrong proved logical value;
- changed successor, pruning, or final-filter computations; and
- any theorem with unexpected hypotheses, free variables, or axiom growth.

Tests for non-final isomorphism representatives, producer-supplied pruning
labels, AFP tries, or bidirectional archive minimality are removed because
those mechanisms are not in v2.

## Immediate bounded work packet

The next tame-graph packet is:

1. generate the named-premise `covers` skeleton and weighted proof ledger;
2. revise the parameter-0 implementation contract to replay plus leaf hints;
3. add final-constant reference instrumentation and freeze its differential
   counts/graph identities;
4. implement the faithful executable enumerator and obtain an initial
   `Kernel.compute` seed/successor measurement;
5. complete the `p = 0` and bounded representative `p = 2` development
   benchmarks with the full cost decomposition;
6. extend the existing data layer through exact explicit-map correctness; and
7. bind the archive representation to `tame_archive_lists`.

Do not build a whole-tree witness certificate, prove non-final isomorphism
quotienting, port tries/worklists only to mimic `samet`, or start a large
reflected replay before the proof-risk and numeric gates are measured.

## Claims deliberately deferred

This plan does not yet claim:

- any tame graph has been classified by Candle;
- the current data tests prove archive membership or completeness;
- the general pruning/invariant proof has been ported;
- the final-constant node counts equal the historical counts;
- a full replay fits the provisional wall-time or memory gate;
- leaf hints have been generated or checked;
- any partition theorem is closed;
- S4 is closed; or
- the unconditional Kepler theorem has been obtained.

Those claims become available only at their stated stage gates.
