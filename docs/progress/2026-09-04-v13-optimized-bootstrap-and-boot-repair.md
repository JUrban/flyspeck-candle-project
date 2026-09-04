# 2026-09-04 — optimized bootstrap and Candle boot repair

## Claim boundary

This is an interim roadmap-v1.3 development report.  The warm proof build and
development link below are deliberately non-promotable.  They are not a
pristine-cold replay, canonical bootstrap/link provenance, S1, S2, S3, or
release evidence.  PFT remains an independent oracle and contributes nothing
to the direct S2/S3 count.

## Completed optimized frontend bootstrap

The serial warm `Holmake -j1 cake.S` rebuild of CakeML
`06a639c4d1d71e7999939ca1ab40a912fbe81531` passed all 18 downstream targets.
It ran for 7:25:18, peaked at 78,303,332 KiB maximum RSS, incurred no major
page faults or swaps, and exited zero.  In particular,
`compiler64ProgTheory` saved the parser capability, parser success, parser
error, both exact `caml_parser$run` refinement theorems, and the ordinary
compiler semantics theorem before exporting.  `x64BootstrapTheory` then saved
`compiler64_compiled` and generated fresh assembly and configuration outputs.

The retained development root is
`/project/flyspeck-candle-runs/nonpromotable-frontend-build-06a639c4d-attempt-004`.
Its identities are:

- build log: 694,534 bytes, SHA-256
  `c4d834b60608268b99ab2839cd85a83f9fa9e3af1ab2c0ff473e23ae471055a7`;
- exit-status file: two bytes containing zero, SHA-256
  `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`;
- generated `cake.S`: 41,868,382 bytes, SHA-256
  `f4b3a6282929537c65eae922960e3811dca8b594031a78ba7173cf8892329910`;
- generated `config_enc_str.txt`: 7,191,426 bytes, SHA-256
  `056089bdfb2e41dee57da6d337746d39613c4fd85b290627a593cb4e902a3315`;
- `compiler64ProgTheory.dat`: 96,728,527 bytes, SHA-256
  `baa614fd1fd02b70c8fa17bed50bd61618f27876dc0350bf7c8ff98089a5ab4e`;
  and
- `x64BootstrapTheory.dat`: 479,086,437 bytes, SHA-256
  `a6154e57998a94d6f23f38473ba5a80f38549726cde48e6a531154f29dbc704e`.

The serial scheduling result also explains the earlier parallel failure:
`to_word64Prog` completed in 41m42s when run alone, whereas the earlier `-j2`
attempt lost that target immediately to signal 9 while another large theory
overlapped it.  Serial scheduling is therefore retained for heavy proof
targets.

## Boot-smoke failure and bounded repair

The first development link successfully patched and linked the fresh assembly
and passed the exact parser-capability handshake, but the real `--candle`
smoke failed.  The retained staging directory is
`/project/flyspeck-candle-runs/.nonpromotable-dev-link-06a639c4d-d96929e-attempt-001.pending-vl1lpn10`.
Its empty stderr and stdout show a direct parse failure at line 538, the start
of module `Cakeml`, followed by unsuccessful REPL fallback attempts.  It is a
failed diagnostic artifact and must not be used as a runtime result.

Prefix bisection localized the rejection to the first new source-trace
datatype.  The older parser rejected the identical boot bytes, so this was not
a regression introduced by the latest expression batch.  The private variant
constructors used internal capitals such as `SourceTraceBinding` and
`SourceLoaded`; the verified frontend accepts the already-established
lowercase/underscore constructor tail.  CakeML commit
`8a8926906ec97204eeec961496d191103cda3229` renames only those private
constructors to forms such as `Source_trace_binding` and `Source_loaded`.
There is no control-flow, data, protocol, or output change.

The complete 49,001-byte repaired boot passed the freshly generated direct
parser in 1.49 seconds at 1,053,696 KiB maximum RSS and also passed stock
OCaml's parsing phase.  A follow-up `Holmake -j1 cake.S` scan at the new commit
confirmed that the boot-only source change does not invalidate or rebuild the
compiler assembly target.

## Passing development runtime

The second development link passed patching, native linking, type inventory,
insulation generation, the exact parser-only capability handshake, and a real
Candle boot/evaluation smoke.  Its immutable output root is
`/project/flyspeck-candle-runs/nonpromotable-dev-link-8a8926906-d96929e-attempt-002`.
It binds clean heads CakeML `8a8926906ec97204eeec961496d191103cda3229`,
Candle `d96929e49c42f0487bc5728397ce3be453dd8376`, and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.

- linked runtime: 1,189,757,088 bytes, SHA-256
  `dd8a693bc88b75b5599a91777b93629417993cdb5338bb7cb0f40d38d246190f`;
- development receipt SHA-256
  `c6ca836c5e73d13b753a259113363883997fe2cbd4650b0a9797c0e4d47b42bb`;
- checksum manifest SHA-256
  `305b8eca27851caab5b00c2c9e7dd0eee11126a88427aaba8744aa9ed9d9cffb`;
  and
- Candle smoke stdout SHA-256
  `f9be69f37f1ecf3eb5e2176deee1dc62fec9784c264a25b1963006390071b561`,
  with empty stderr and exit zero.

The next gates remain the fresh current-head 20-input parser pilot, independent
consumption, and then the exact 400-input inventory.  Only after those pass is
the pristine-cold/canonical replay justified.

## Explicit development heap and passing pilot

Prelaunch review found that the development parser runner bounded virtual
address space but inherited the runtime's one-GiB C default heap.  That would
not execute the intended 4-GiB pilot and 16-GiB archive measurements.  Project
commit `7a681e53e2a80eb7954c4461d715dd78ad9af909` therefore adds an explicit
`--cml-heap-size-mib` option, passes only the fixed child environment including
that value, records it in the result receipt, and requires at least four GiB
of address-space headroom.  Six runner tests and seven localizer tests pass.
The committed runner has SHA-256
`57e0339f1cb7d892e7645ec7c4486216f656926142bb9bfbb3627a59cceaba26`.

The fresh Candle-`d96929e` pilot materialization is
`/project/flyspeck-candle-runs/parser-pilot-materialization-d96929e`.
Its plan and host-materialization SHA-256 identities are
`95dbee3a5797da4a92285501f2440ed3ff714f7160868cb3db1780f195ec9d71`
and `1198676f083d0df912cb97c0db7cee4ea738b22efa8bfa622134ddab5bfea9dd`.
It contains exactly 20 ready inputs and no unsupported input.

The exact pilot then passed 20/20 in 14.156415 seconds with a 4,096-MiB heap,
16-GiB address limit, and 7,200-second wall/CPU limits.  Its sealed result is
`/project/flyspeck-candle-runs/nonpromotable-parser-pilot-result-8a8926906-d96929e-attempt-001`,
whose receipt has SHA-256
`cb6d631fa63c18fa35197da4ab8f5352ef2e3100cf134354df6a196afe81f9c0`.
An independent shell-side validation required its exact 44-file and two-
directory mode closure, all receipt fields and negative promotion claims, all
20 transcript hashes, exact nonce-bound `OK` lines, and empty stderr files.
That validation passed.

The pilot authorized fresh materialization of the 400-input profile at
`/project/flyspeck-candle-runs/all-inventory-materialization-d96929e`.
It has exactly 400 ready inputs, zero unsupported, plan SHA-256
`e4308994f28211ff3982925a25a71231b16d0384c017362ba73c62797f597e82`,
and host-materialization SHA-256
`86556f695a54c16845b3fd50dac83d06a5596bfde9809b0534334599a199225c`.
The 9,103,338-byte normalized archive is input 256.  Its 400-input run is
active with a receipt-bound 16,384-MiB heap and 24-GiB address limit; it remains
development-only until completion and independent result validation.
