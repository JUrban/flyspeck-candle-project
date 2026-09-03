# 2026-09-03 — frontend build scheduling and escape frontier

## Claim boundary

This is an interim roadmap-v1.3 engineering report.  The builds and corpus
observations below are development-only.  They are not inference, evaluation,
a theorem about Flyspeck, S1, S2, S3, or release evidence.  PFT remains an
independent oracle and contributes nothing to direct S2/S3 qualification.

The source authorities at this checkpoint are:

- CakeML frontend batch `58da58c682c279bfbb4a3a92eaa09717f7bc9f75`;
- CakeML next frontend repair `055fd9e1b865fd7a68adb789b62aa8046d9491a7`;
- Candle `6df8ae5d8f8781cb5c2a63c2a2ea6784ada9d853`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`; and
- Flyspeck `1ce0353008eba83d3c76ae9a25c3c242e4802d53`.

## `Holmake -j2` is unsafe for this bootstrap target

The warm development build at
`nonpromotable-frontend-build-58da58c68-attempt-001` reached 86/95 targets.
It then printed `Starting work on to_word64ProgTheory`, but the forked child
remained a `Holmake -j2 cake.S` process rather than executing HOL.  Its target
log stayed empty, it accumulated only one voluntary context switch, and both
child and parent slept in `futex` for more than six hours.  This is strong
process-level evidence of a fork-after-threads deadlock, not a long theorem.

The exact stuck child ignored `TERM` and was killed explicitly.  Holmake then
reported `to_word64ProgTheory ... FAIL<Signal 9>` and exited nonzero.  The
complete failed receipt records:

- wall time 9:29:34;
- peak RSS 24,413,684 KiB and zero swaps;
- build-log SHA-256
  `de21778a763d00362891004232c62158fa8f78a73ba49bfe69e9aa15f7f6ab52`;
- GNU-time receipt SHA-256
  `d0a081deb669226cdd88b5f5cf7d38f91abdf8ee4b87c840f6eb74accac9c96c`;
  and
- exit status 1.

The warm cache was preserved and a serial recovery was started at
`nonpromotable-frontend-build-58da58c68-attempt-002` with `Holmake -j1
cake.S`.  It resumed the nine remaining theories at `to_word64ProgTheory`.
The final clean release route already requires `-j1`; development now uses the
same scheduling discipline for this target.  The external advice to benchmark
`-j2` was reasonable, but the benchmark result is negative on this HOL4 /
Poly/ML target.  Raising it to `-j4` would compound the risk and is rejected.

## One additional lexer layer

An exact byte-lexical scan of the 400 prepared inputs found one otherwise
unknown string escape: `\_` at prepared input 138, source
`text_formalization/nonlinear/ineq.hl`.  OCaml 4.14.1 accepts that source with
warning 14 and retains both bytes.  CakeML's lexer instead returned an error
when `scan_escseq` returned `NONE`.

CakeML commit `055fd9e1b` now preserves the backslash and following character
for otherwise unknown string escapes.  It intentionally leaves malformed
numeric escapes and the existing line-continuation behavior unchanged.  The
commit adds both a concrete lexer theorem and an end-to-end parser/AST test for
`"\_"`, requiring the result to be the two characters `CHR 92` and `CHR 95`.

The full isolated `camlTestsTheory` rebuild passed 10/10 targets in 14:36.41,
peaked at 3,466,284 KiB RSS, and reported zero swaps.  This proves the focused
frontend behavior but is not yet the translated parser proof or a corpus
acceptance result.

## Cache decision and next gate

An attempted `caml_parserProgTheory` build in the new worktree disclosed a
186-theory cold dependency closure.  It was interrupted after 1:24 rather than
duplicating hours of work already cached in the active batch worktree.  Its
honest interrupted receipt remains at
`nonpromotable-caml-parser-translation-055fd9e1b-attempt-001`; no parser
translation success is claimed from it.  Generated HOL artifacts bind absolute
worktree paths, so they will not be copied across worktrees.

The next sequence is therefore:

1. finish the serial warm `58da58c68` runtime build;
2. link it non-promotably and run the exact 20 then 400 development parser
   plans to expose the current layered frontier;
3. fast-forward `055fd9e1b` and any newly localized bounded fixes into the
   warm build worktree;
4. rebuild and prove only the invalidated closure there; and
5. require 20/20 then 400/400 before spending on the pristine-cold release
   bootstrap and formal gates.

This applies the useful part of the speed advice—batch cheap corpus findings
before clean bootstraps—while rejecting unsafe parallelism and unsafe
cross-worktree cache copying on measured evidence.
