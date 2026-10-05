# Candle reflected tame-graph classification plan

Date: 2026-10-05 UTC

Status: **DEVELOPMENT / NON-RELEASE**

This plan adds a parallel S4 lane. It does not displace the direct Flyspeck,
LP, or nonlinear work, and it does not change the current S3 acceptance
contract. Its destination is to remove the last Isabelle premise by proving
the tame-graph classification theorem inside HOL Light running on Candle.

## Exact destination

The current direct build proves the LP and nonlinear premises in HOL and
exports a theorem conditional on the one remaining proposition:

```text
import_tame_classification =
  (!g. PlaneGraphs g /\ tame g
       ==> (?y. y IN archive /\ iso_fgraph (fgraph g) y))
```

The reflected tame-graph lane is complete only when Candle derives a closed
theorem with the exact conclusion:

```text
|- import_tame_classification
```

That theorem can then discharge the hypothesis of the existing final
Flyspeck theorem. The intended production path has no Isabelle process,
Isabelle theorem import, OCaml HOL Light runtime, or trusted external graph
generator. An external program may prepare a certificate, but Candle must
check it as untrusted data under a general HOL soundness theorem.

Archive membership checks, archive counts, digests, agreement with Isabelle,
or successful computation of a list of graphs are useful development
evidence. None of them alone proves the classification theorem.

## Recovered source baseline

The repository contains only 13 files under `formal_graph/isabelle_tame` and
omits important inputs imported by `Completeness.thy`, including
`ArchCompProps`, `ArchComp`, `TameEnum`, `TameEnumProps`, `Generator`,
`GeneratorProps`, `Worklist`, `Arch`, and `Tries`.

The missing historical source is available from the authoritative Archive of
Formal Proofs release made after Flyspeck's July 2014 final-constant update:

```text
https://isa-afp.org/release/afp-Flyspeck-Tame-2014-08-28.tar.gz
sha256 54aa014cc8de1bc178ef68cc4e88932aefe9a61dcd17712ae714f39ae411102c
```

A local audit download gave the following initial provenance checks:

- 11 overlapping theory files are byte-for-byte identical to the partial
  Flyspeck checkout;
- the only difference in overlapping `Tame.thy` is a comment containing an
  old source URL;
- `Completeness.thy` is byte-for-byte identical;
- the four `Tri.ML`, `Quad.ML`, `Pent.ML`, and `Hex.ML` archive files are
  byte-for-byte identical; and
- the release contains the omitted enumeration, pruning, worklist, trie,
  archive-comparison, and correctness theories.

Important recovered file identities include:

| File | SHA-256 |
| --- | --- |
| `ArchComp.thy` | `41547ba123fbf2acce7ffea23c9755a07656af8ccf51675bfa76e1e04c4e7f8a` |
| `ArchCompProps.thy` | `3623d380f3d5adf0aff19ca6fccb97894d23b37292cd70e15f5b57dfbc5bac84` |
| `TameEnum.thy` | `0a29650f0bccd9353ac5f15bb8c5c26e4a5a6a812bd84184436adb8dc606e1c1` |
| `TameEnumProps.thy` | `8b73307c8209f4093d5b1f437a44640a3c917bb6d39dc4b7190f1659e4592c1c` |
| `Generator.thy` | `4082203a4f2122d42682fbb72d0292e0e7bab7e9e38da5bf3ab3e2becd708f08` |
| `GeneratorProps.thy` | `9c67c95c3ef8b11697a00ff2140287389a08c2e64a0b1c3f2c7c36517b0d4616` |
| `Worklist.thy` | `32bbec7cbd5f9c36125c8c485f85adf7d31fc203f15b4760cf37235bb30d04e3` |
| `Arch.thy` | `203c82142ec38e14a766d5c425657cad66e8028e91ff2a94f4e5995e57007de0` |
| `Tries.thy` | `f4604b62495bab8d35811508bba8b63914e609120790bfbf892ddcc889bf4bb7` |
| `Completeness.thy` | `97f94c0c12c6ec314f5cb1fc9d6c8c0fe9e7ca3c2057e44bdeba7263a07eacbe` |

This resolves source discovery, but not yet the formal correspondence task.
The complete archive must be retained under an explicit manifest, and every
definition used by the new HOL theorem must be reconciled with the pinned HOL
Flyspeck definitions.

## Existing assets and the actual gap

The HOL Flyspeck tree already contains substantial relevant material:

- `tame_defs2.hl` defines the graph enumerator, duplicate-edge filters, face
  subdivision, `next_plane`, and `PlaneGraphs`;
- `tame_list.hl` proves many representation and executable-list facts,
  including a list characterization of `PlaneGraphs`;
- `import_tame_classification.hl` contains the exact HOL notions of tameness,
  graph isomorphism, and the desired imported proposition;
- `isabelle_hollight_translation.hl` is an extensive definition-level
  Isabelle-to-HOL correspondence ledger; and
- `archive_all.ml` contains 19,715 archive graphs, partitioned as 9 triangle,
  1,253 quadrilateral, 16,080 pentagonal, and 2,373 hexagonal cases.

The existing Candle reflection prototype already establishes the basic proof
pattern for Flyspeck list computations:

1. prove a HOL-to-`cval` representation theorem;
2. evaluate the represented program with `Kernel.compute`;
3. decode with a proved round-trip theorem; and
4. return an ordinary kernel theorem.

The gap is not simply executable graph code. It is the general proof that a
finite checked computation covers every tame final graph reachable from the
plane-graph seeds, including all pruning and quotient-by-isomorphism steps.
That proof currently exists in Isabelle, not in HOL Light.

## Proposed trusted architecture

```text
untrusted certificate producer
          |
          v
canonical graph/worklist/archive certificate data
          |
          v
proved HOL decoder + total rejecting checker
          |
          v
Kernel.compute proves checker(data) = true
          |
          v
general HOL checker-soundness theorem
          |
          v
|- import_tame_classification
```

Only the decoder, checker definitions, general HOL proofs, Candle evaluator,
and kernel theorem handoff contribute proof authority. Certificate generation,
search order, hashes, checkpoints, and comparison runs remain untrusted.

Two computation styles should be tested on the smallest complete partition:

1. **Algorithm replay:** reflect the recovered `tameEnumFilter`/`samet`
   computation closely and let `Kernel.compute` perform the enumeration.
2. **Witness-carrying replay:** let an untrusted producer perform search and
   have Candle check a complete frontier/closure certificate, recomputing
   local successors and validating pruning and isomorphism witnesses.

Algorithm replay is closest to the AFP proof and minimizes certificate design.
Witness-carrying replay can avoid repeating expensive search, expose bounded
chunks, and keep the final computed verdict compact. The triangle partition
will measure the tradeoff before the project commits to either as the scaling
backend. Both backends must instantiate the same logical coverage theorem.

## Target theorem decomposition

The main partition theorem should have the following shape, with exact HOL
types substituted during implementation:

```text
check_tame_partition p archive_part certificate = true
==>
!g. (Seed p,g) IN RTranCl (next_plane p) /\
    finalGraph g /\ tame g
    ==> ?y. MEM y archive_part /\ iso_fgraph (fgraph g) y
```

The proof should be uniform in `p`, the archive, and the certificate. It must
not contain four proofs specialized to the successful production data.

The final aggregation theorem then uses the general mathematical facts that:

- a plane graph comes from some seed parameter;
- a tame final graph has seed parameter at most 3;
- `next_tame` (or the chosen checked pruning relation) preserves every tame
  completion reachable through `next_plane`; and
- the four accepted partitions cover parameters 0, 1, 2, and 3.

It concludes the exact definition of `import_tame_classification` over
`tame_archive_lists`.

## Canonical data and certificate design

The initial representation layer should use Candle's existing `cval`
constructors and introduce only proved, typed encoders/decoders for:

- natural numbers, booleans, options, pairs, and lists;
- faces and cyclic face lists;
- graph records: faces, vertex count, faces-at-vertex, and heights;
- archive fgraphs;
- finite maps/tries or a simpler canonical index;
- worklist nodes and successor edges; and
- explicit isomorphism maps.

Every decoder is total and every malformed value causes rejection. Round-trip
and injectivity theorems are required for canonical inputs. Logical theorems
must bind accepted data to `tame_archive_lists`; a byte digest or source-file
count is useful provenance metadata but cannot replace that binding.

A witness-carrying node should say which of these checked cases applies:

- **expanded:** the checker recomputes the exact `next_tame` successors and
  verifies that every successor is represented by a declared node;
- **duplicate:** an explicit representative and vertex map are checked as an
  isomorphism, rather than trusted as a search result;
- **pruned:** the checker verifies the exact proved pruning predicate and its
  hypotheses;
- **final:** an archive index and explicit isomorphism map are checked; or
- **terminal non-tame:** a proved decidable failure of a required tame
  condition is checked.

Search order and node numbering have no mathematical meaning. The checker
must establish seed inclusion, closure of every open edge, termination of the
finite certificate, and absence of undeclared frontier nodes. This prevents a
producer from silently omitting a difficult branch.

The existential `tame13a`/admissible-weight condition is the most likely
pruning-proof hotspot. Its recovered `is_tame13a` and lower-bound machinery
must be reconciled carefully with the HOL definition. No graph may be pruned
merely because the external producer labels it non-tame.

## Staged implementation

### Stage 0: pin and reconcile the historical basis

1. Vendor or otherwise reproducibly fetch the exact AFP 2014 archive under a
   versioned manifest and record its license, URL, archive hash, member hashes,
   and extraction procedure.
2. Mechanically compare every overlapping theory and all four archive files.
3. Extend `isabelle_hollight_translation.hl` into a machine-readable ledger
   covering the recovered enumeration, pruning, isomorphism, worklist, and
   completeness definitions and the corresponding pinned HOL constants.
4. Classify each Isabelle result as already proved in HOL, straightforwardly
   reusable after a definition rewrite, requiring a new HOL proof, or needed
   only by an implementation strategy that can be avoided.

Exit gate: no computation result is interpreted until its graph, tame,
transition, archive, and isomorphism meanings are tied to the exact HOL terms.

### Stage 1: reflected graph primitives and authentic archive data

1. Add canonical graph and archive encoders, decoders, validators, and
   round-trip theorems.
2. Implement and prove the cheapest useful primitives: vertex/face access,
   rotation normalization, hash/index computation, and direct validation of
   a supplied isomorphism map.
3. Load the genuine nine-entry triangle archive through this path.
4. Reflect its structural well-formedness and `pre_iso_test` facts, comparing
   results with native HOL Light and the AFP `pre_iso_test3` theorem.

Exit gate: one `Kernel.compute` call produces a closed HOL theorem about the
genuine triangle archive, with malformed graph and map mutations rejected.
This is a data-path milestone, not a classification result.

### Stage 2: smallest complete classification prototype

1. Port enough of `next_tame`, the generator, duplicate handling, and the
   archive comparison to process the complete seed-parameter-0 partition.
2. Run both algorithm replay and witness-carrying replay if both remain cheap;
   otherwise retain one and record why the other was abandoned.
3. Compare the computed graph classes and archive witnesses with AFP `same3`,
   native HOL Light, and the nine authentic triangle archive entries.
4. Measure cold preparation, encoding, equation/program construction,
   evaluator execution, theorem handoff, trace size, peak RSS, and retained
   theorem size separately.

Exit gate: every branch of the real parameter-0 search is covered. Hand-picked
graphs or archive self-checks do not satisfy this gate.

### Stage 3: general soundness in HOL

Reprove the required general results in HOL Light, using the recovered AFP
proofs as a specification and proof guide:

- correctness and completeness of graph isomorphism witnesses;
- invariants of generation and face subdivision;
- preservation/completeness of the tame-pruned transition relation;
- worklist or certificate-closure soundness modulo isomorphism;
- correctness of every executable tameness/pruning predicate; and
- the partition theorem stated above.

The proof must be independent of the production certificate. Per-graph or
per-partition theorem scripts are not an acceptable replacement for a general
checker theorem.

Exit gate: the computed parameter-0 verdict instantiates the general theorem
and yields the exact parameter-0 classification theorem with no hypotheses or
new axioms.

### Stage 4: scale through all four partitions

Process parameters 1, 2, and 3 in order. Use bounded certificate chunks such
as worklist-depth/frontier blocks when one monolithic value approaches Candle
term, compute-clock, memory, or theorem-size limits. Chunk composition must be
proved: each accepted block consumes an authenticated frontier and produces
the exact next frontier, and only a closed empty frontier earns coverage.

The expected archive partition sizes are useful consistency checks:

```text
p=0:     9
p=1: 1,253
p=2: 16,080
p=3: 2,373
total: 19,715
```

Counts and hashes remain diagnostic. Each final graph needs a checked archive
membership/isomorphism witness, and every reachable branch needs checked
coverage.

Exit gate for each partition: a closed theorem from the seed to its exact
archive part, deterministic repeat results, stable theorem fingerprints, and
successful negative certificate mutations.

### Stage 5: final aggregation and direct-build integration

1. Combine the four partition theorems with the general seed-bound theorem.
2. Rewrite the resulting archive union to the exact
   `tame_archive_lists`/`archive` used by `the_kepler_conjecture.hl`.
3. Export
   `Candle_tame_graph_reflection.import_tame_classification_th` with conclusion
   `|- import_tame_classification`.
4. Add the reflected support and certificate actions after the stable tame
   definitions/archive are loaded and before the final theorem export. The
   current action 294 definition/final-assembly position is the integration
   reference; final numbering should be regenerated rather than patched by
   hand.
5. Apply the theorem to the existing LP-plus-nonlinear conclusion and verify a
   closed Kepler theorem in a clean direct Candle run.

Exit gate: two clean runs and one authenticated resume agree on all partition,
classification, and final-theorem semantic fingerprints, and the final theorem
has the expected assumptions and axiom set.

## Performance and checkpoint policy

The project should pay reusable preparation once and charge recurring work
honestly. For every authentic partition or chunk, report:

- source/certificate preparation outside Candle;
- checked decoding and structural validation;
- `Kernel.compute` equation/program construction;
- evaluator wall time and compute-clock use;
- theorem decoding/handoff and aggregation;
- checkpoint write/restore time;
- peak RSS and certificate/checkpoint sizes; and
- graph nodes expanded, pruned, deduplicated, finalized, and compared.

Stable checkpoints should be placed after the graph representation and
general soundness libraries, before changing certificate adapters, and after
each closed partition theorem. Experiments should use fresh copies of the
nearest compatible checkpoint. A failed or partially consumed worklist state
must never be reused as proof evidence.

The likely scaling risks are evaluator time, huge encoded graph/certificate
terms, trie/map behavior, isomorphism checking, and the global compute-clock
limit. These should be measured on the complete parameter-0 partition before
optimizing. Certificate chunking and explicit isomorphism maps are preferred
first responses to scale; adding trust to the producer is not.

## Required negative tests

At minimum, the checker must reject:

- a changed archive face, vertex, partition, or graph order where order is
  declared canonical;
- a malformed graph or noncanonical encoding;
- a missing, duplicated, or undeclared successor/frontier node;
- an invalid pruning label or weight/lower-bound witness;
- a wrong representative or isomorphism map;
- an archive index referring to a non-isomorphic graph;
- a certificate from a different seed parameter;
- truncated or reordered chunks;
- a chunk with the wrong input or output frontier; and
- changed bytes under retained metadata or a retained digest.

## First bounded work packet

The immediate parallel packet is deliberately smaller than the current LP or
nonlinear compute jobs:

1. preserve a manifest of the AFP 2014 source and generate a complete
   Isabelle-to-HOL definition/theorem inventory;
2. identify the minimal dependency closure for `pre_iso_test3`, `same3`, and
   parameter-0 completeness;
3. implement canonical face/fgraph encodings and a checked explicit
   isomorphism-map primitive on a separate Candle branch;
4. run the real nine-entry triangle archive through the existing small
   `Kernel.compute` harness; and
5. write the exact parameter-0 checker contract before expanding the port.

This packet can run beside the direct and nonlinear lanes without another
full Flyspeck replay. Any expensive integration load waits until the small
authentic computation and the correspondence ledger make the proof boundary
clear.

## Claims deliberately deferred

This plan does not yet claim:

- that the AFP theorem has been transported to HOL Light;
- that current Candle graph reflection classifies any plane graph;
- that archive validation proves enumeration completeness;
- that the 19,715-graph computation fits in one Candle call;
- that the witness-carrying design is faster than faithful algorithm replay;
  or
- that S4 or the unconditional Kepler theorem is closed.

Those claims become available only at their explicit stage gates.
