# Response to external speed advice — 2026-08-29

## Conclusion

The advice has two immediately useful principles: run cheap corpus gates before
another expensive bootstrap, and batch frontend changes before rebuilding.
Those principles are already partly active and should be strengthened. The
suggested `Holmake -j2`/`-j4` speedup, cross-worktree theory cache, x64-only
compiler, and theory splitting do not provide a safe immediate shortcut for
the current canonical build. They are development experiments or longer-term
upstream work, not changes to make during the live provenance-bound run.

The supplied note contains `[GitHub][1]` through `[GitHub][4]` references but
does not include their link definitions. This assessment therefore relies on
the checked-out HOL4/CakeML sources and exact local build evidence rather than
unavailable citations.

## Recommendation-by-recommendation assessment

### Parallel `Holmake`

The pinned HOL4 `Holmake` does support `-j n`, `--mt`, and JSON dependency-graph
output. It also has a content-addressed cache interface. That establishes
capability, not useful parallel width.

The current invalidated `cake.S` frontier is a serial chain. The canonical log
declares 18 theory targets. Its 17 rebuilt translation theories extend one
another from the already-built `caml_parserProg` in this exact order, and the
x64 bootstrap is the eighteenth target:

```text
caml_parserProg -> pancake_lexProg -> pancake_parseProg -> reg_allocProg
-> inferProg -> explorerProg -> decodeProg -> sexp_parserProg
-> basis_defProg -> printingProg -> to_word64Prog -> to_target64Prog
-> from_pancake64Prog -> x64Prog -> arm8Prog -> riscvProg -> mipsProg
-> compiler64Prog -> x64Bootstrap/cake.S
```

This is visible in
`compiler/bootstrap/translation/*ProgScript.sml`: every stage uses
`translation_extends` on the preceding theory. Consequently `-j2` or `-j4`
cannot materially shorten this critical frontier. A completely clean CakeML
dependency build has more independent branches and may benefit, but that is a
different workload and must be benchmarked rather than inferred from core
count.

The live canonical record also deliberately pins the exact
`Holmake -j1 cake.S` command and its runtime/tool/preimage contract. Changing
jobs now would invalidate the run. The measured earlier bootstrap reached
64,484,760 KiB, or about 61.5 GiB, RSS. Two simultaneous worst-case
HOL jobs plus the roughly 23.9 GiB PFT oracle would be about 147 GiB before
controller, reference-sweep, and page-cache overhead, exceeding the user's
exceptional 120 GiB project ceiling even if the host could physically
accommodate them. CakeML's `LOCAL_PARALLELISM_LIMIT` is a job-count cap, not a
memory-aware scheduler. No live change is adopted.

Safe later experiment: after the canonical receipt is secured, use a separate
non-promotable worktree to inspect the clean dependency DAG and benchmark a
bounded `-j1` versus `-j2` build on a genuinely parallel subgraph. Record peak
aggregate RSS and require total project memory below 120 GiB. Do not claim the
cached/parallel experiment as the only release build.

### Content-addressed theory caching

The idea is sound for development, and the checked-out `Holmake` already
provides `--use-cache`, `--cache-dir`, `--cachekey`, and cache-key rebuild mode;
the default remains uncached, mtime-based rebuilding.
The project also already avoids recomputing unaffected local theories between
repair iterations. That reuse is why the canonical controller rebuilds an
authenticated 18-theory postimage rather than every CakeML theory.

The native cache stores only `Theory.sml/.sig/.dat` products. It excludes heaps
and arbitrary `.uo/.ui` products, and it cannot cache the x64 bootstrap sibling
group containing non-theory `cake.S`/`config_enc_str.txt` side effects. Its key
hashes scripts and hashable direct dependencies, but does not by itself close
the HOL executable, Poly/ML, `hol.state`, kernel, or complete toolchain. A
private development cache therefore still needs an external namespace binding
those identities.

Cross-worktree reuse is not yet an authenticated release path. The current
bootstrap controller records and checks the exact HOL4 and CakeML repositories,
build tools, heap inputs, preimages/postimages, final theories, log, and command.
It archives/removes the forced outputs, requires the exact 18-target serial log,
and hard-codes `Holmake -j1 cake.S`; cache hits are intentionally inadmissible
to this schema. A release cache would need an equally closed key, immutable
object storage, extraction validation, and adversarial tests. Use the built-in
cache only for explicitly diagnostic builds until that model exists; retain at
least one clean release qualification. A fully populated diagnostic theory
cache has a loose wall-time saving ceiling of about 7h42 in the earlier 8h44
run. The explicitly reported predecessor-target times total about 5h52, while
final x64 emission took about 1h03; roughly 1h50 of remaining overhead is not
guaranteed to be cache-eliminable. The normal same-worktree mtime resume also
already captures much of this benefit.

### Cheap corpus-wide frontend gates and batching

This is the highest-value advice. The project already did more of it than the
note implies before the current canonical launch:

- focused parser theory tests completed in about 4m15s at 1.5 GiB RSS;
- the translated `caml_parserProg` proof target completed in about 43m39s at
  32.9 GiB RSS;
- a manifest-bound static audit classified all 12,700 qualified-uppercase
  terminal occurrences as 12,449 theorem/value references, 249
  constructor/exception references, and two module paths, and verified the
  exact 400-source selected graph; and
- parser, Dopen, inference/soundness, CV, and uppercase-value repairs were
  accumulated before restarting the canonical downstream chain.

A reusable whole-corpus parse-only diagnostic now exists at Candle `688d9d1`,
with an exact 400-input materialization awaiting the new linked compiler.  A
combined parse/infer diagnostic does not yet exist and remains worthwhile. It
is not as simple as parsing 400 independent files: the selected HOL Light
route uses directives, generated inputs, normalization contracts, and an
incremental module/value environment. Inference is even more context-dependent.
CakeML's generic `--print_sexp --skip_type_inference=true` route uses the CakeML
`parse_prog` language, not Candle's OCaml parser, and is not a substitute.

The implemented parser gate is a manifest/phrase-aware diagnostic around the
translated OCaml parser `caml_parser$run`, explicitly non-promotable.  It runs a
20-input pilot before the 400-input inventory.  A subsequent infer-only mode
must preserve manifest action order, generated inputs, directives, and the
incremental environment. Once a current linked compiler exists, use the parser
diagnostic to expose latent baseline issues and run it before any subsequent
bootstrap-triggering frontend edit. A linked old parser cannot validate a
newly edited parser, so focused HOL parser/inference tests and the static
feature audit remain the cheap pre-bootstrap gates for a new change.

### Dropping non-x64 architectures

Not a near-term optimization. The generic 64-bit compiler program is built by
extending the translated program through x64, ARM8, RISC-V, and MIPS, and
`compiler64Prog` directly extends `mipsProg`; the x64 bootstrap consumes
`compiler64Prog`. These are not accidentally independent architecture jobs
that can be omitted by a make flag. An x64-only program would require a new
specialized translation/export definition and corresponding correctness and
bootstrap proof. That may be a worthwhile upstream design project only if
many more compiler iterations are expected.

### Splitting giant theories

Potentially useful over a months-long upstream development horizon, but high
cost and high proof risk now. The large translation stages intentionally carry
one accumulated translated program, so splitting a file does not necessarily
split the serial logical computation. Any proposal needs a proof that its
intermediate export/heap boundary preserves the existing compiler theorem and
improves measured incremental rebuild time. It should not delay the current
direct-source gates.

## Adopted actions

1. Keep the live canonical bootstrap unchanged and provenance-valid.
2. Continue batching parser/inference/frontend findings before any later full
   bootstrap.
3. Treat a manifest-ordered whole-corpus frontend diagnostic as the best new
   speed feature: first a 20-node `caml_parser$run` pilot, then all 400 nodes,
   after the current linked compiler is available.
4. Use offline dependency-graph/timing analysis before any `-j2` experiment;
   benchmark only an observed parallel development subgraph and monitor
   aggregate RSS under the 120 GiB ceiling. Do not spend time benchmarking
   `-j2` on the current serial frontier or assume a 2x improvement.
5. Investigate Holmake's native cache for diagnostic work, but require a
   separately designed authenticated cache contract before using it in release
   evidence.
6. Defer x64 specialization and theory splitting unless future measurements
   show that repeated compiler work dominates the remaining direct-source
   schedule.
