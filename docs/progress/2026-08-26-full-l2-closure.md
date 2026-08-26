# Full L2 endpoint and certificate inventory — 2026-08-26

The previous full exporter stopped at
`The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture`, whose statement
still assumes both `import_tame_classification` and
`the_nonlinear_inequalities`.  That is not the selected L2 endpoint.

Flyspeck commit `2ea440e9f7c55734d1e47738e44a6129ce0ecf5a` adds a separate
full-target script.  It saves and exact-checks, in order:

1. `Linear_programming_results.linear_programming_results_th`;
2. `Mk_all_ineq.the_nonlinear_inequalities`;
3. `The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture`; and
4. `Candle_flyspeck_l2.tame_imp_kepler_conjecture`.

The fourth theorem is constructed only with `ASSUME`, `CONJ`, `MATCH_MP`, and
`DISCH`; its statement is
`import_tame_classification ==> the_kepler_conjecture`.  Thus the HOL-side LP
and nonlinear premises are discharged while the roadmap-selected Isabelle
tame-classification premise remains explicit.  Splitting main and full target
files also avoids typechecking references to modules not loaded by the main
sequence.

`Good_list_archive.test_archive_ids` is empty, so the LP path selects the full
archive.  An independent lightweight decoder read every checked-in certificate
shard, including compressed `hard_7`: 39 files contain 19,715 unique IDs.  The
checked-in archive also contains 19,715 unique IDs, with zero missing, extra,
or duplicate IDs.  The aggregate certificate hash and the archive, nonlinear
preparation, and break-case-log hashes are locked in `manifest.lock.toml`.

The long-running path is now restartable inside its two largest source files.
LP verification invokes a proof-neutral hook after each certificate shard;
serialized nonlinear reconstruction invokes it after each prepared case, with
a configurable default checkpoint every 25 cases.  The hook is a no-op in an
ordinary Flyspeck build.  The exporter flushes and records its PFT boundary
before each DMTCP checkpoint-and-kill, and makes one final boundary before
saving targets.

This implements and pins the G9 connection and improves G2/G8 restart
granularity.  G2, G8, G9, and G11 remain incomplete until the full sequence
finishes, the compiled Candle executable replays all four saved targets under
the exact three-standard-axiom policy, and its resource envelope is recorded.
