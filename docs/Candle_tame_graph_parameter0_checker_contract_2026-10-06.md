# Reflected tame-graph parameter-0 checker contract

> **Revised for plan v2.** This contract now specifies the single deterministic
> replay plus final-leaf-hint architecture selected by
> `docs/Candle_tame_graph_reflection_plan_v2_2026-10-06.md`. The earlier
> whole-tree witness, non-final duplicate-node, and two-backend provisions are
> removed. The exact theorem, production-constant binding, total-decoder, and
> rejecting-validation requirements remain in force.

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

## Deterministic replay acceptance theorem

The checker is one typed HOL deterministic depth-first replay. It computes
the exact successor list itself. Untrusted data supplies hints only for final
states which are not rejected by the executable lower-bound/tameness test.
The general theorem has this shape, with concrete HOL datatypes substituted
during implementation:

```text
|- !p archive_part fuel hints.
     tame_partition_replay p archive_part fuel hints [Seed p]
       = Some []
     ==> !g.
           g IN PlaneGraphsP p /\ tame g
           ==> ?a.
                 MEM a archive_part /\
                 iso_fgraph (fgraph g) a
```

The production instance is then only:

```text
|- tame_partition_replay
     0 (tame_archive_partition 0 tame_archive_lists)
     authentic_parameter0_fuel authentic_parameter0_hints [Seed 0]
       = Some []
```

`Kernel.compute` may prove this Boolean equality. The general implication
must be an ordinary HOL theorem proved independently of the production
certificate. Applying the theorem yields the exact closed parameter-0 result.

The checker must be total. Malformed encodings, unknown tags, bad indices,
noncanonical graphs, arithmetic overflow representations, invalid maps,
missing or surplus required hints, fuel exhaustion, or an unfinished
frontier reject; none may raise a trusted host exception or be interpreted as
acceptance. Hint order is only the deterministic replay order and carries no
mathematical authority.

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

No converse is required for non-final duplicate elimination, because replay
does not quotient non-final states. The untrusted hint producer may search for
a final map however it likes; Candle accepts it only through the proved
one-way implication above. Hashes and `pre_iso_test` may select candidates but
may never decide isomorphism alone.

### 2. Deterministic replay closure

The replay stack starts at the exact production `Seed p`. A non-final state
is replaced by the exact typed HOL `next_tame p` successor list. A final state
has exactly one of two outcomes:

- the executable rejection predicate proves that the invariant final state
  cannot be tame; or
- one hint supplies an archive index, explicit vertex map, and orientation
  bit, all of which are checked against that exact final graph and production
  archive entry.

The replay soundness theorem states its starting-state requirements
explicitly. Seed validity establishes the invariant for the initial stack,
and a general successor-preservation theorem maintains it. A separate
completion-preservation theorem proves that pruning cannot discard any tame
final completion. Acceptance therefore covers every relevant final graph; no
non-final quotient, duplicate representative, external frontier identity, or
producer-supplied pruning label appears in the argument.

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

These three results compose to the deterministic replay acceptance theorem.

## Single computation backend

The only production backend is the typed HOL deterministic replay above,
refined to a cval program by checked equations. It does not reproduce AFP's
trie, `samet`, or archive-deduplication worklist, and it does not accept a
whole-tree witness certificate. External reference enumeration may produce
the ordered final-leaf hints and performance traces, but Candle recomputes
all successor, final, rejection, and explicit-map decisions.

If a monolithic replay approaches resource limits, a proved HOL splitter may
construct a logical frontier and sequential replay calls may be composed by
the `covers` finite-union theorem in the same Candle kernel state. External
frontier files, counts, or hashes are never soundness premises.

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
`fgraph`, `archive`, and `iso_fgraph` are valuable proof leads. Their ledger
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
   with mutation tests for a face, vertex, ordering field, and map;
6. instrument the exact final-constant reference replay to count generated,
   retained, rejected, final, and hint-consuming states; and
7. define a deterministic bounded parameter-2 fixture that exercises
   quadrilateral, exceptional-face, nonzero-excess, and multiple-size
   branches.

This slice establishes the data and theorem handoff used by deterministic
replay. Data, map, archive, and soundness experiments can run from a small
isolated Candle state. The instrumentation and bounded parameter-2 fixture
use the generator in a separate reference state; neither requires the full
Flyspeck replay or contributes proof authority.

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
- cold preparation, recurring evaluation, theorem handoff, required failed
  and successful repeats, peak RSS, encoded bytes, node counts, and retained
  theorem size are measured separately; and
- the feasibility decision reports total elapsed cost as well as evaluator
  time, charging reusable preparation once and all required repeats.

Only after this gate should parameters 1--3 or production chunk formats be
fixed.
