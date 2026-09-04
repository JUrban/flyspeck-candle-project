# 2026-09-03 — frontend build scheduling and escape frontier

## Claim boundary

This is an interim roadmap-v1.3 engineering report.  The builds and corpus
observations below are development-only.  They are not inference, evaluation,
a theorem about Flyspeck, S1, S2, S3, or release evidence.  PFT remains an
independent oracle and contributes nothing to direct S2/S3 qualification.

The source authorities at this checkpoint are:

- CakeML frontend batch `a38cba3b4c07ca6c9d960eb168fe5a4b6d4a09a6`;
- Candle `d96929e49c42f0487bc5728397ce3be453dd8376`;
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

## Checked development-link handoff

Project commit `9d46896e46a5edb72e9b7bf3507bb08f609fadae` adds
`scripts/build-nonpromotable-candle-development.py` and three focused tests.
The helper rejects wrong or dirty CakeML/Candle heads, captures the exact
generated assembly and configuration plus all link inputs, applies the Candle
assembly patch, uses a one-job native link, captures `cake --types` from its
actual stderr stream, regenerates insulation, and requires the exact
parser-only capability handshake.  It then publishes hashes, transcripts,
resource timing, and a read-only receipt that hard-codes every promotion and
S1/S2/S3 field false.  This removes an ad-hoc handoff from the rapid parser
loop without weakening the ordinary canonical-link boundary.

The helper's 3/3 tests pass.  Together with the development parser runner's
5/5 tests and the localizer's 7/7 tests, the complete immediate handoff chain
has 15 focused passing tests.  No development output produced by these tools
is release evidence.

A later direct `--candle` smoke exposed a gap in that first handoff contract:
the translated runtime selected the OCaml parser, but initialized the REPL from
`repl_boot.cml` rather than `candle_boot.ml`.  The parser-only capability mode
therefore remained green while ordinary Candle startup was broken.  Project
commit `09b6a79` adds a bounded real-Candle boot/evaluation gate and a negative
regression, raising that helper to 4/4 focused tests.  CakeML commit `a38cba3b4`
also makes boot selection use the same `MEMBER` form as parser selection and
adds semantic known answers.  That CakeML change is not accepted on source
inspection: its translated warm rebuild and the new executable smoke gate are
in progress.

The first warm invocation for that head failed before proof work because the
repository root exposes more than one `cake.S`; that invocation is retained as
an ordinary failed development attempt.  The correctly scoped serial retry
completed the first five of 24 targets and entered `caml_parserProgTheory`.
That theorem process then grew to roughly 50 GiB RSS while three independent
archive-scale probes and the long-running PFT oracle were resident.  The retry
was interrupted deliberately after 1:05:10 to keep aggregate project memory
near the then-current ceiling; this is a resource-scheduling interruption, not
a theorem failure.  It has exit-status receipt 130, build-log SHA-256
`95c420e18319b92855f8472c6c7c89d6295b71351d0f73c4d6d53bf860475f8b`,
and GNU-time receipt SHA-256
`69bbe992642e1a9a97321230b6ddec64eeec47958b9f470946111342ce2db6b7`.
The five completed targets remain in the same path-bound warm cache.  After
the decisive archive probes released memory, attempt 003 restarted
`caml_parserProgTheory` serially from that cache and remains in progress.  The
subsequently authorized 120 GiB project ceiling is treated as a temporary peak
allowance, not a new ordinary target.

## Completed serial recovery and checked retry

The serial recovery completed all nine remaining targets and ended with
`Holmake: [9/9] x64Bootstrap`; `x64Bootstrap` itself took 53m21s.  GNU time
records 5:02:20 total wall time, exit status zero, 58,267,420 KiB maximum RSS,
zero major faults, and zero swaps.  Its retained evidence hashes are:

- build log `c0bd41f232e6b6ba4e02fa957850e34ec073dc08411984f6154f08838e3f0e1d`;
- GNU-time receipt `a7ffa2cbe8434fc466c78a57a294943cf8d7cac829a27b7e1d47f57895edeabf`;
- fresh `cake.S` `05bf1628af01d5fd1d676d2ff0066dfdf8b4e0ecaa83cb70bd5b8f9f0b42bc04`;
  and
- fresh `config_enc_str.txt`
  `27fbe07f7982489ce714102edd4f97667f0831c41b59bf8b4c9ec2eeccc1fb1c`.

The first development link reproduced a 1,189,748,032-byte runtime with
SHA-256 `3fae88eac213f057a1dd5dae4b740cbc459a1fe42f52967eeafb896477ef436c`,
and its exact 20-input pilot parsed 20/20.  A pre-publication audit then caught
a hand-entered HOL4 label typo in both receipts: `a3904ce...` rather than the
actual verified `a390cbab...`.  The executable bytes were unaffected, but
those receipts are rejected even as development evidence; their 400-input
continuation is retained only as an exploratory failure-discovery run.

Project commit `42bf582` closes the defect.  The link helper now verifies an
exact clean HOL4 worktree just as it verifies CakeML and Candle, and records a
stable relative command rather than a vanished staging path.  The parser
runner no longer accepts three manually copied commit labels: it requires the
immutable development-link receipt beside the runtime, checks the runtime
bytes against that receipt, and derives the three commits from its verified
repository identities.  A new mismatch regression raises the runner suite to
5/5.  Corrected link attempt 002 independently reproduced the same runtime
hash while binding HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`, and its
receipt-bound pilot again passed 20/20.  Its completed 400-input run below is
still categorically non-promotable.

## Authenticated 400-input discovery result

The corrected 400-input run completed in 3,514.963 seconds and published
receipt SHA-256
`9418a3f24e82ac66c72ab81180a4987767059dc622de869b8e1a01f50b56098d`.
It binds the exact corrected development-link receipt, runtime SHA-256
`3fae88eac213f057a1dd5dae4b740cbc459a1fe42f52967eeafb896477ef436c`,
CakeML `58da58c682c279bfbb4a3a92eaa09717f7bc9f75`, Candle `6df8ae5d`,
and HOL4 `a390cbab`.  The result was 384 parse successes, 15 controlled parse
errors, and one runtime failure.  It is development discovery only.

The sole non-parser failure was the 9,099,782-byte, 404,842-line
`formal_graph/archive/archive_all.ml` input.  With the per-process allowance
raised from 600 to 1,800 seconds it no longer timed out: after 826.299 seconds
it exited one with only the native runtime's generic nonzero-exit diagnostic.
This separates the archive scale problem from the 15 syntax classes but does
not make the archive a pass.

The receipt-bound localizer then independently reproduced all 15 controlled
parse failures, found an individually failing OCaml-accepted candidate for
every one, and made 560 parser invocations with no unexplained case.  Its
19,006-byte localization receipt has SHA-256
`707b52a49744626ebbca66ab5ca4c9bd9e2a75c0875617653555b05b895ae5f6`.
The minimized frontier is:

- one trailing sequence semicolon before `in`;
- five files containing tight reserved cons followed by dereference, `::!`;
- three direct applications to structural record literals;
- one `@ if` expression;
- one unknown string escape preserved by OCaml warning 14;
- two tuple elements beginning with `if`;
- one `+ if` expression; and
- the unused OCaml-3.10 branch's mixed recursive datatype/type-abbreviation
  declaration.

## Unselected branch and archive-scale diagnosis

Candle commit `5ef8aaf` resolves the mixed declaration without pretending that
CakeML's datatype AST represents an OCaml recursive group containing both a
type abbreviation and datatypes.  Exact normalization
`PROJECT-TOPLOOP-S3-UPDATE-DATABASE-310-UNSELECTED-001` removes the
compiler-internal OCaml-3.10 implementation behind its pinned source hash and
leaves a fail-closed replacement.  The selected serialization branch remains
the statically authenticated OCaml-4.14 `update_database_400.ml`; the 3.10
source is therefore not registered in the direct loader.  The old translated
runtime parses the normalized inventory input, so this closes the fifteenth
syntax candidate while keeping the semantic boundary honest.

The archive failure is not a bad data entry.  Twenty exact ordered shards of
1,000 entries (the last has 715) cover all 19,715 values; all twenty passed the
translated parser, each in 2:05--3:16 with empty stderr.  The single-list
source fails after 13:46.30, inserting a list boundary every 500 values still
fails after 15:04.65, and putting forty chunk bindings inside one expression
still fails after 16:25.75.  Reverse shadow bindings at chunk sizes 500, 250,
and 100 also fail after 23:59--24:27.  Every translated failure peaks tightly
at 1,051,904--1,052,800 KiB RSS (about 1 GiB), matching `basis_ffi.c`'s
default 1 GiB CakeML heap.

Native OCaml 4.14.1 gives a related scale signal: parse-only accepts the
original, ordinary interface processing stack-overflows with the default
native stack, and the original succeeds with a larger native stack.  A
reverse-shadow representation succeeds with the default native stack.
Executable probes over the original and that representation agree on length
19,715, serialized size 7,240,670, and serialized-value MD5
`e5dc65249008430ca06fc7c51ca0398f`.

Inspection of the actual Candle scanner then showed why all in-module
rewrites failed: `;;` is a phrase boundary only at lexical nesting level zero,
so the complete `module Archive_all = struct ... end` remains one parser input.
A fallback uses forty bounded top-level thunk phrases and forces their final
ordered list only inside `Archive_all`; native OCaml again produces the exact
same serialized value.  A real compiled Candle parsed, inferred, compiled, and
evaluated all forty phrases plus the final module in 28:41.12, with exit zero,
empty stderr, and 4,230,016 KiB maximum RSS.  The exact transformed input has
SHA-256 `ad53b6c2617ed3f4209714f4a46ae2e94306a7aab29562bde127cc8d3b64efb2`;
the Candle stdout and GNU-time receipt have SHA-256
`17a8f558b68cda2013bb77ab5194d7efcf86ca051e6d0d3029c09bd26cba24d0`
and `a2938e25df5cb5c807a5d39e8cb71497414d59a0a7eeef0c31e9c5a57798ba3c`.
This is development feasibility, not S2/S3.

The raw-source resource experiment is now complete.  A 4 GiB parser-protocol
run still exhausted its heap after 1:37:52 at 4,199,552 KiB RSS.  The same
exact pinned bytes passed with empty stderr at both 16 GiB and 32 GiB:

- 16 GiB took 1:01:42 at 16,783,872 KiB RSS; stdout SHA-256 is
  `a711596aae37a91498387a9cb39448878f16347d09ea1d73b1d9c097944dbfb6`
  and GNU-time SHA-256 is
  `0cbe36f4709ef758a831b62ca55d522fabfdb972a813823c18b2bd67690ae5d4`;
- 32 GiB took 53:00.20 at 33,561,472 KiB RSS; stdout SHA-256 is
  `fac35c35076737f0b20a8fa202e5eb34998dee40cde2efe49c8351d2af176945`
  and GNU-time SHA-256 is
  `b05035fe98d1acdfbd320b0cadd6ed91287ed7e3614d589a50dd01d3bfa499f5`.

Both stdout files contain the exact nonce-bound parser success protocol.  The
32 GiB allocation therefore saves only 8m42s over 16 GiB and is not a good
ordinary default.  A real-Candle raw-source run at 16 GiB emitted no error but
hit its explicit four-hour timeout at 17,282,048 KiB RSS; it is not a pass.
Its stderr is empty, stdout SHA-256 is
`5f7e30c361beb1e5f3207e9998e95b687a7559c554a33e00ed59f670e8926056`,
and GNU-time SHA-256 is
`b88fd16f0e23fabe55a4aab7b7633e838a54ec0f233ea167e537978b9ba5d054`.

Raw-source syntax compatibility is thus established for development purposes,
but raw full evaluation is not operationally acceptable.  The production
candidate is the one successful bounded representation: forty reverse-ordered
top-level thunks of at most 500 values, followed by the unchanged
`Archive_all.tame_list` module binding.  The exact normalizer now checks the
source/wrapper, 19,715 item prefixes, ordered reconstruction, chunk count,
identifier grammar, and final size/MD5/SHA-256.  It rejects every drift.  The
transformation depends on ordinary non-recursive lexical shadowing and list
append and introduces one uniquely named ML value; it adds no HOL definition
or axiom.  Native original/normalized serialization equality and the 28:41
compiled-Candle pass support the representation argument, but do not prove it.
Final archive consumption, kernel-state/theorem fingerprints, independent
comparison, and clean direct execution remain mandatory release gates.

Candle commit `50e1e38` records that decision together with explicit,
receipt-bound CakeML heap settings, a mandatory 4 GiB virtual-address headroom
check, and the manifest generator's generated-driver fixed point.  Actual
materialization produced a
20-output read-only overlay; its normalization receipt has SHA-256
`3b2eeb14c3f655a0b8faf7032b697635adee5133b3791029b9c5fa62da3b2ed8`,
and its archive bytes have the expected SHA-256 `ad53b6c2...3b64efb2`.
Manifest `--check`, both parser descriptor checks, and the focused controller
suites pass.  A parser-protocol timing of the exact selected archive at 4 GiB
reached its explicit two-hour limit at 4,197,760 KiB RSS with status 124 and
empty stdout and stderr.  Its exit-status and GNU-time files have SHA-256
`ca2ebdf97d7469496b1f4b78958f9dc8447efdcb623953fee7b6996b762f6fff`
and `b7f699507446c04b116a5868a861a513c5fd2b6f22fe0cacf3b6fd0b79cc6fdf`.
This does not contradict the successful incremental full-Candle evaluation:
the deliberately coarse diagnostic calls `caml_parser$run` over the entire
source and retains the returned AST.  It does show that 4 GiB is not an
operational diagnostic setting for the archive.  The corrected exact 16 GiB
comparison passed in 1:02:04 at 16,782,080 KiB RSS with exit zero, empty
stderr, and the nonce-bound `OK` protocol.  Its stdout and GNU-time files have
SHA-256 `4a64cb04cdfb3c0fbeb6eee8a669e74acd21cd4c731cb6df8d48959db04e0d68`
and `d562dbba8eaa67091f04134486077bd6c3e295ebba95ed3f525ad2bfb045e974`.
Candle follow-up `d96929e` therefore gives the coarse parser diagnostic a
16,384 MiB heap, 24 GiB address space, and 7,200-second wall/CPU defaults while
the direct incremental runtime remains at its independently measured 4,096
MiB heap.  All 56 parser-controller tests pass in 70.57 seconds at 271,496 KiB
maximum RSS.

One first 16 GiB launch is excluded as an invocation error: its hand-entered
nonce was 58 rather than 64 lowercase hexadecimal characters, so the runtime
correctly did not enter diagnostic mode and ordinary compilation rejected the
OCaml source at line one.  The retained run ended in 11.64 seconds at
11,763,584 KiB RSS; it says nothing about archive parsing.  The corrected
attempt validates the nonce length before launch.

## Two proved expression batches

CakeML commit `fd5c47337` parses and converts four bounded Flyspeck forms:
tight `::!`, a trailing semicolon in a sequence, direct application to a
structural record literal, and `@ if`.  Its lexer theorem, PEG well-formedness
and totality, conversion theory, and complete parser test theory passed in the
focused serial build.  The final successful retry took 4:36.29, peaked at
1,472,464 KiB RSS, used no swap, and has build-log SHA-256
`375d01f41629a6487f8288047f82d8446baf3c3bad64308039bb9b8e37853b1b`.

CakeML commit `51513f0df` adds the two remaining live low-precedence forms:
an `if` expression after an additive operator and after a tuple separator.
The additive extension is guarded by an already-consumed operator, and the
focused build reproved every zero-consumption theorem, `PEG_wellformed`, all
three totality theorems, conversion, and the exact AST regressions.  The full
focused build passed in 10:52.64, peaked at 3,744,396 KiB RSS, used no swap,
and has build-log SHA-256
`68e03f178c23abcf555acc83ac5ef04741400ee416c69fdf548c12e2d1b1b4a6`.

Together with the already-committed unknown-escape repair `055fd9e1b`, these
CakeML changes address 14 of the 15 localized syntax candidates.  The exact
unselected-3.10 normalization above closes the remaining candidate without
deleting the converter rejection or producing a misleading AST.

## Warm-head translation regression and selector repair

The serial warm rebuild of CakeML head `a38cba3b4` did not complete within a
reasonable development window.  Attempt 003 spent more than six hours in the
mutual `ptree_Expr` translation after the last saved source-theory boundary.
The active Poly/ML worker continuously consumed approximately one CPU, so this
was not the `-j2` futex deadlock described above.  Its resident set was
observed rising to approximately 36.5 GiB and then falling through several GC
cycles without reaching the next translated-theorem boundary.  It was
interrupted cleanly at 6:01:06 and all build descendants exited.  The retained
development evidence has status 130 and hashes:

- build log
  `dcf9c3dcb4a01795e166b046fd5c8514ec0144cefd0771dffb5b1fbb6cadfece`;
- exit-status file
  `f5bde7eb9f6c71611dc5726e8aca3eb4eba3e386da49e0a4ed5c295a90a73a0d`;
  and
- GNU-time file
  `adbeec8343a44664c11125dc92d5350ab356513a3ebe45e54444d6b072415d4b`.

GNU time measured the waiting Holmake parent and therefore reported only
251,456 KiB maximum RSS and exit zero; those two fields do not describe the
heavy descendant and are explicitly rejected.  The shell-level status and
the directly observed descendant process establish the interruption, not a
theorem failure.

A source audit localized the regression to the three new `nterm_of`-dependent
branches inside the already-large mutual converter.  A first proposed repair
moved those tests into structural `Nd` clauses.  HOL accepted the definition
and generated its induction theorem, but simplification of the enlarged
induction theorem had not reached the next boundary after 25 minutes.  That
experiment was interrupted and rejected.  Its non-promotable build log and
pipeline-status file have SHA-256
`9deb131debd787803008e23ca060d6495f2b4c329b70f06f8dceffac71c4af5d`
and `85a0e6eb5530a682fa88345a5e7a144248f49e5b71b3eb587a9db5cd2957495a`.

CakeML commit `06a639c4d` instead factors the lookahead into the small
`select_expr_nterm` helper, translates that helper separately, and leaves one
recursive converter call at each of the three sites.  It preserves the old
`nterm_of` failure on an impossible leaf and selects exactly the same target
nonterminal for every node, so this is a translation-shape change rather than
an AST change.  The serial focused build passed both
`camlPtreeConversionTheory` and `camlTestsTheory` in 7:15.31, at 2,838,768 KiB
maximum RSS, with no major faults or swaps.  The conversion theory alone took
2m01s.  Its 4,439,041-byte log and exit-status hashes are
`c7245184a75befac9423a9b63d8a2358f712148d01468f28040b7ac76447c905`
and `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`.
The dedicated translated-parser replay for this committed head then passed.
`caml_parserProgTheory` itself exported in 41m59s; the complete two-target
serial invocation took 44:59.03, peaked at 44,955,200 KiB RSS, incurred no
major faults or swaps, and exited zero.  It separately translated
`select_expr_nterm`, saved the mutual expression side/value theorems, proved
and applied `ptree_Expr_preconds`, and translated the public
`caml_parser$run_parser` and `caml_parser$run` entry points.  Its 77,264-byte
log and exit-status hashes are
`2d06effd056af25cb9550a05a82225c6611149b12df00b48aa4984eb55e734ce`
and `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`.
This restores the previously measured approximately 44-minute translation
scale and closes the source-level performance regression.  It remains a warm,
path-bound development result, not release evidence.

The next sequence is therefore:

1. finish the exact selected normalized-archive parser timing and use it to
   set a conservative per-input controller limit;
2. finish the serial warm rebuild of optimized CakeML head `06a639c4d`;
3. require the real-Candle boot smoke and then exact 20/20 and 400/400 parser
   gates; and
4. only then spend on the pristine-cold release bootstrap and formal gates.

This applies the useful part of the speed advice—batch cheap corpus findings
before clean bootstraps—while rejecting unsafe parallelism and unsafe
cross-worktree cache copying on measured evidence.

The reviewed advice file has SHA-256
`01b0a59abe465d10113e5370926784ef1526eff609304a42e2b687830fc48288`.
Its cheap whole-corpus gates and fix batching are adopted.  Its proposed
`Holmake -j2`/`-j4` bootstrap and relocatable generated-product cache are
rejected for this toolchain by the measurements above.  X64-only compiler
specialization and splitting the largest theories remain plausible longer-term
projects, but neither shortens the current compatibility critical path enough
to justify changing the trusted build architecture now.
