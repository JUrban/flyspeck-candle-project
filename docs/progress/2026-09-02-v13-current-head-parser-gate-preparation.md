# 2026-09-02 — current-head parser-gate preparation

## Scope and claim boundary

This is an interim direct-source frontend report under roadmap v1.3.  Every
parser plan, development runtime, parser observation, and localization named
here is categorically non-promotable.  None is inference, evaluation, a
theorem, S1, S2, S3, or release evidence.  PFT continues independently as an
oracle and contributes nothing to the direct S2/S3 count.

The authorities at this cut are:

- Candle `6df8ae5d8f8781cb5c2a63c2a2ea6784ada9d853` on
  `codex/flyspeck-v13-parser-quotation-prep`;
- CakeML `58da58c682c279bfbb4a3a92eaa09717f7bc9f75` on
  `codex/flyspeck-v13-frontend-batch`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`;
- Flyspeck `1ce0353008eba83d3c76ae9a25c3c242e4802d53`; and
- project/controller `73c195bf14a6993db81384bc429e08b857c0523e` on
  `codex/flyspeck-v13-candle-repin-prep-report`.

All three worktrees were clean after the commits recorded below.

## Batched CakeML frontend repairs

The current CakeML head contains five bounded frontend commits above the
proved Dopen/runtime base `c2e26f43c...`:

| Commit | Repair |
| --- | --- |
| `a5690401e` | path-only OCaml `include` declarations |
| `14f25006e` | trailing semicolons at expression delimiters |
| `bffa9107e` | parenthesized annotated recursive binders |
| `60f1f95ea` | Flyspeck structural records, projections, updates, mutable fields and assignments |
| `58da58c68` | unparenthesized tuple function arguments |

The aggregate diff is four files, 499 insertions and 62 deletions.  Focused
`camlPEGTheory`, `camlPtreeConversionTheory`, and `camlTestsTheory` builds pass.
The combined current-head `caml_parserProgTheory` translation also passes;
that replay took 43:58.71 and peaked at 35,637,532 KiB RSS without swap.  It
translated the new tuple path and the complete structural-record conversion
path and proved the public parser preconditions.  These results are proof
builds of the frontend implementation, not corpus acceptance results.

A warm, development-only `Holmake -j2 cake.S` build is active at
`nonpromotable-frontend-build-58da58c68-attempt-001`.  Its full log and GNU
time receipt are retained there.  It is deliberately not a clean release
qualification and must not be promoted.

## Candle authority refresh

Candle `7921a8f...` normalized the unused `eval_command` optional argument.
Because that changed authenticated manifest and normalization bytes, the
pilot and all-inventory descriptors and the aggregate ordered source pins were
regenerated rather than hand-relabeled.  Candle `6df8ae5...` records that
refresh.

The exact descriptor and authority identities are:

| Object | SHA-256 |
| --- | --- |
| pilot descriptor | `fb4e9aebed2f40f64a401df3401e8a9bbb5d2e9512f378cc329f2a407dc97756` |
| all-inventory descriptor | `6d09a97224c7a2014bff4e6ae515ee104c6c66de6328d03daa0b9eb51c1fcc4a` |
| manifest | `4baf80219b48f2ca2e46a7279c2815de2c938f1a2e22d4be69d8219100312486` |
| normalization contract | `1f99191ec9bcc486880e932d7ca9f597b71316bde85923730ca530f046bd6581` |
| ordered effective-input list | `28da884be27f19419a819befa5bf8567bb99467b71dff0ca4133ce0caccd2eaa` |
| ordered prepared-input list | `9ebae984d55c09c561484ec2d6fbed4532a107950b3da5e0e49aded4818a85ef` |

Both isolated official checks pass: 20 exact pilot nodes and 400 exact
all-inventory nodes.  The two focused suites pass 56/56 and 17/17.  A complete
lightweight discovery at `6df8ae5...` passes 346/346 in 3:06.87, with peak RSS
335,500 KiB and no swap.

Fresh immutable source plans were then materialized:

| Profile | Root | Plan SHA-256 | Host receipt SHA-256 |
| --- | --- | --- | --- |
| 20-input pilot | `parser-pilot-materialization-6df8ae5` | `4a586ef9dc03fe32a4efecab841bc0d9df424c23f3c4e7ed8b2cd0744376378b` | `c51cbb76ff4edb2333438a051c164349eea5c24460471ffad6547a2f6e236164` |
| all 400 | `all-inventory-materialization-6df8ae5` | `b4ef595bd4c95dc0bd7a5a15c301404b0039c9acf8eb50dc4acdb102fc01fdfd` | `a9b46787866772bab5e0f5dd314be825866890891a6602a03a2d3a7b7f7dd2cc` |

These are authenticated source preparations only.  They execute no runtime.

## Reproducible development runner

Project commit `f179bc6...` added
`scripts/run-nonpromotable-parser-development.py` and four focused tests.  It
validates the immutable plan and every prepared input, captures and privately
executes the exact runtime bytes, requires the parser-only capability line,
applies per-process limits, retains separate transcripts, and hard-codes all
promotion/S1/S2/S3 fields false.  Project commit `34ae669...` taught the
existing failure localizer to accept that schema while preserving and testing
the historical schema-1 route.

The first real-runtime smoke exposed a controller defect: the runner sent the
diagnostic flag without the required 64-hex request nonce.  Its honest 0/20
runtime-failure receipt remains at
`nonpromotable-dev-parser-runner-smoke-f179bc6-attempt-001`, summary SHA-256
`488e70fcf4565db2298d76f83d653f97cb1c0115ff540a2b9a8891c2aa1b1ac8`.
It is not a parser regression.

Project commit `73c195b...` repaired the protocol and strengthened the fake
runtime test.  The runner now uses deterministic index nonces, requires the
exact echoed nonce, and records it per attempt.  Eleven combined
runner/localizer tests pass.  A real-ELF retry against the retained old
diagnostic runtime passes 20/20:

- root `nonpromotable-dev-parser-runner-smoke-73c195b-attempt-002`;
- summary SHA-256
  `78d4f6f2f0480b907dddc18bb56048077885aa61c5256af5a6b06305a170c74f`;
- exact plan SHA-256 `4a586ef9dc03fe32a4efecab841bc0d9df424c23f3c4e7ed8b2cd0744376378b`;
- runtime SHA-256
  `22e4421df9dc50b123ea6d5a617128d330f9e5caf6708ff56f419306acda980a`;
  and
- runner-source SHA-256
  `92abf9c9f5c4f106f269b717b7d052aa53a0e68bb2dee5f5284036c3e023268d`.

The old runtime smoke validates only the runner protocol.  It says nothing
about the current CakeML frontend batch.

## Speed-advice assessment and next gate

The useful external recommendations are being applied: batch frontend repairs,
require the 20 then 400 parser gates before another clean bootstrap, reuse warm
artifacts only for development, and let `Holmake -j2` schedule independent
theories.  Raising to `-j4` during 15--40 GiB HOL stages is not justified while
the PFT oracle remains resident.  Cross-worktree copying of native HOL caches
was already found unsafe because generated dependencies bind absolute paths.
An x64-only compiler specialization and major theory splitting remain possible
longer-term projects, but neither should delay the present corpus gate.

When the current development `cake.S` completes, the next exact sequence is:

1. make a fresh, explicitly non-promotable link from the captured assembly and
   current Candle patch;
2. require the current runtime to pass the exact 20-input plan;
3. run the exact 400-input plan and retain all transcripts;
4. localize and batch any remaining parser errors before another expensive
   rebuild; and
5. only after 400/400 is quiet, run pristine-cold proof qualification,
   canonical bootstrap, ordinary same-head link, and the formal parser gates.

Direct compatibility, Great-100, Flyspeck strata, nonlinear/LP closure, and
the full S2/S3 source run remain after that frontend boundary.  No milestone is
closed early by this report.
