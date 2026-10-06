# Reflected tame-graph parameter-0 checker contract

> **Partly superseded.** The two-backend, non-final duplicate-node, and
> scheduling provisions in this contract are replaced by
> `docs/Candle_tame_graph_reflection_plan_v2_2026-10-06.md`. The exact theorem,
> production-constant binding, total-decoder, and rejecting-validation
> requirements remain in force.

Date: 2026-10-06 UTC

Status: **DEVELOPMENT / NON-RELEASE**

This contract fixes the logical boundary for the first complete tame-graph
prototype. It does not claim that the Isabelle classification theorem has
been transported, that a graph archive check proves enumeration completeness,
or that any new S4 theorem exists yet.

## Source and destination identities

The historical specification is the authenticated AFP release recorded by:

```text
third_party/afp-flyspeck-tame-2014-08-28/inventory.json
AFP archive SHA-256:
  54aa014cc8de1bc178ef68cc4e88932aefe9a61dcd17712ae714f39ae411102c
```

The production meanings are the constants in the pinned direct Flyspeck
source, especially:

```text
Tame_defs2.PlaneGraphsP
Tame_defs2.next_plane
Tame_defs2.Seed
Import_tame_classification.tame
Import_tame_classification.iso_fgraph
Good_list_archive.tame_archive_lists
```

Names or matching source text do not establish correspondence. The generated
ledger at `docs/tame-graph-correspondence-ledger.json` records each recovered
Isabelle declaration and the legacy HOL translation leads. Every definition
used below must eventually have a kernel theorem connecting the executable
checker meaning to these exact production constants.

## Exact parameter-0 theorem

The first classification milestone is a closed HOL theorem equivalent to:

```text
|- !g.
     g IN PlaneGraphsP 0 /\ tame g
     ==> ?a.
           MEM a (tame_archive_partition 0 tame_archive_lists) /\
           iso_fgraph (fgraph g) a
```

Here `tame_archive_partition` is a proved HOL function, not a host-side slice
or an assumed file boundary. It classifies an archive fgraph by its maximum
face size, matching the historical partition procedure in
`formal_graph/archive/make_archive.hl`:

```text
p = 0  <-> maximum face size = 3
p = 1  <-> maximum face size = 4
p = 2  <-> maximum face size = 5
p = 3  <-> maximum face size = 6
```

For `p = 0`, the selected production list must be proved equal to the nine
graphs decoded from the byte-identical AFP `Archives/Tri.ML`; neither the
number nine nor the archive-file hash is a substitute for that equality.

Using `PlaneGraphsP 0` makes the reachability premise exact:

```text
g IN PlaneGraphsP 0
<=> (Seed 0,g) IN RTranCl (next_plane 0) /\ finalGraph g
```

The final four-part aggregation may rewrite through `PlaneGraphs`, but the
parameter-0 proof must not weaken or replace the production reachability,
tameness, archive, or isomorphism notions.

## Backend-independent acceptance theorem

Both proposed computation backends must instantiate one theorem of this
shape, with concrete HOL datatypes substituted during implementation:

```text
|- !p archive_part certificate.
     tame_partition_check p archive_part certificate = T
     ==> !g.
           g IN PlaneGraphsP p /\ tame g
           ==> ?a.
                 MEM a archive_part /\
                 iso_fgraph (fgraph g) a
```

The production instance is then only:

```text
|- tame_partition_check
     0 (tame_archive_partition 0 tame_archive_lists)
     authentic_parameter0_certificate = T
```

`Kernel.compute` may prove this Boolean equality. The general implication
must be an ordinary HOL theorem proved independently of the production
certificate. Applying the theorem yields the exact closed parameter-0 result.

The checker must be total. Malformed encodings, unknown tags, bad indices,
noncanonical graphs, arithmetic overflow representations, invalid maps,
missing nodes, or unfinished frontiers return `F`; none may raise a trusted
host exception or be interpreted as acceptance.

## Semantic decomposition

The general acceptance theorem is split into three reusable results.

### 1. Executable graph and isomorphism correctness

For every accepted encoded graph and explicit vertex map:

```text
decode_graph encoded = Some logical_graph
check_iso_map encoded1 encoded2 encoded_map = T
==>
iso_fgraph logical_graph1 logical_graph2
```

The converse needed for completeness of duplicate elimination is proved for
the canonical graph domain: if two valid canonical fgraphs are isomorphic,
the producer can supply a map that `check_iso_map` accepts. Hashes and
`pre_iso_test` may select candidates but may never decide isomorphism alone.

### 2. Finite certificate closure

An accepted certificate contains a canonical seed representative and a finite
set of representative nodes. Every node is one of:

- `expanded`: it is non-final; the checker recomputes the exact executable
  `next_tame p` successors, and every successor has an accepted explicit
  isomorphism map to a declared representative;
- `final`: it has no required expansion, and an archive index plus explicit
  map proves isomorphism to that exact `archive_part` entry; or
- `duplicate`: optional in the physical format, but if present it carries an
  explicit map to a declared representative and cannot introduce or suppress
  successors.

The checker rejects duplicate node identities, dangling indices, undeclared
successors, graph/map mismatches, a missing seed, a nonempty output frontier,
and any final node without a valid archive witness. Node order and producer
search order have no logical meaning.

Closure soundness proves that every state reachable by `next_tame p` is
represented modulo `iso_fgraph`, and every reachable final state has an
archive witness. This proof includes the required equivariance result: an
isomorphism between representatives preserves finality and transports
`next_tame` successors. Without that theorem, quotienting the worklist by
isomorphism is unsound.

### 3. Pruning completeness

The certificate checker does not trust producer-supplied `pruned` labels. It
recomputes `next_tame`; pruning is justified once, by a general theorem:

```text
|- !p g.
     g IN PlaneGraphsP p /\ tame g
     ==> (Seed p,g) IN RTranCl (next_tame p)
```

Its proof corresponds to the historical `next_tame0_comp`, `untame_negFin`,
and `next_tame_comp` route. In particular, the existential admissible-weight
condition behind `tame13a` must be connected to the executable
`squanderLowerBound`/`is_tame13a` test generally. An external assertion that a
branch is non-tame is never sufficient.

These three results compose to the backend-independent acceptance theorem.

## Two admissible computation backends

### Algorithm replay

Mirror `tameEnumFilter` and its trie/worklist implementation in reflected HOL
data. Acceptance means the executable enumerator terminates with the exact
checked final set and the bidirectional archive comparison succeeds. This is
closest to the AFP computation and is initially attractive for the nine-graph
partition.

### Witness-carrying replay

An untrusted producer supplies the finite representative graph, explicit edge
maps, and final archive maps. Candle recomputes every local successor list and
checks every map, then proves the frontier empty. This can reduce evaluator
search and expose checkpointable chunks, at the cost of larger certificate
data and a general finite-closure proof.

The triangle prototype should measure both only while both remain cheap. A
backend may be dropped for scaling reasons, but it may not gain trust or use a
weaker logical conclusion. Both target the same acceptance theorem above.

## Archive data binding

The genuine nine-entry path has two checked equalities:

1. decoding the authenticated `Tri.ML` data yields an explicit HOL list
   `triangle_archive_data`; and
2. `triangle_archive_data = tame_archive_partition 0 tame_archive_lists`.

The first can be a reflected parser/decoder theorem or generated HOL data with
a proved representation theorem. The second binds the experiment to the
actual archive constant consumed by the final Flyspeck theorem. This prevents
a correct computation over a convenient but unrelated nine-graph fixture.

The archive graph encoding must be canonical and typed. At minimum it checks:

- nonempty faces and vertex lists;
- natural vertex labels in range;
- distinct vertices per face;
- canonical face rotation and graph ordering, where required by the chosen
  representation; and
- decoder round trip and injectivity on valid encodings.

`pre_iso_test3` is the first authentic computed data milestone. It validates
the structural/isomorphism preconditions of all nine entries but does not
classify any reachable plane graph.

## Current correspondence triage

The mechanically generated initial ledger reports:

```text
historical files:                         44
Isabelle theories:                        35
full completeness theory-import closure:  34
parameter-0 theory-import closure:         33
declarations in full closure:            1175
legacy translation entries found:          87
same-name HOL bindings, unvalidated:         2
missing definition correspondences:       158
proof results needing relevance triage:   920
```

These are inventory counts, not remaining-proof estimates. The immediate
lesson is to slice by the acceptance theorem rather than port 33 theories.
The first unresolved executable spine is:

```text
graph/fgraph representation
 -> rotate_min, pre_iso_test, iso_test, explicit isomorphism map
 -> hash/trie or canonical representative index
 -> worklist closure
 -> next_tame / next_tame0
 -> is_tame13a and lower-bound correctness
 -> parameter-0 computed verdict
```

The existing legacy mappings for `PlaneGraphs`, `next_plane`, `tame`,
`fgraph`, `Archive`, and `iso_fgraph` are valuable proof leads. Their ledger
status remains `existing_translation_entry_unvalidated` until the exact HOL
theorem needed by this checker has been checked.

The checked artifact is reproduced from the exact direct-source head with:

```sh
python3 scripts/build-tame-graph-correspondence-ledger.py \
  --inventory third_party/afp-flyspeck-tame-2014-08-28/inventory.json \
  --flyspeck-root ../worktrees/flyspeck-direct-tail-v403 \
  --check docs/tame-graph-correspondence-ledger.json
```

## First implementation slice

The next code packet is intentionally below the expensive enumeration layer:

1. define canonical reflected encodings for a face, fgraph, and explicit
   vertex map;
2. prove total decoder round trips and injectivity for valid encodings;
3. implement `check_iso_map` against the production `iso_fgraph` meaning;
4. encode the nine authentic triangle archive entries and prove the archive
   partition binding; and
5. use one `Kernel.compute` call to prove their structural preconditions,
   with mutation tests for a face, vertex, ordering field, and map.

This slice establishes the data and theorem handoff used by either backend.
It does not require the generator, lower-bound proof, or full Flyspeck replay,
and it can run from a small isolated Candle state.

## Parameter-0 exit gate

The prototype is complete only when all of the following hold:

- the authentic production archive partition is theorem-bound to the nine
  decoded entries;
- one backend checks every branch reachable from `Seed 0`, not a hand-picked
  graph sample;
- the general acceptance theorem has no production-certificate-specific proof
  steps;
- `Kernel.compute` produces a closed acceptance theorem;
- applying general soundness produces the exact closed parameter-0 theorem;
- theorem assumptions are empty and no axiom beyond the existing allowed HOL
  basis is introduced;
- malformed archive, map, successor, seed, and frontier mutations reject; and
- cold preparation, recurring evaluation, theorem handoff, peak RSS, encoded
  bytes, node counts, and retained theorem size are measured separately.

Only after this gate should parameters 1--3 or production chunk formats be
fixed.
