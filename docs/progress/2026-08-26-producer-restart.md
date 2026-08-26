# Restartable bounded producer — 2026-08-26

## Outcome

The direct HOL Light producer can now resume an open PFT stream after a process
checkpoint.  `prepare_pft_stream_checkpoint` forces collection, drains safe
theorem releases, emits any due type/term range checkpoint, flushes the output,
and records its byte offset, command count, and peak slot limits.  After DMTCP
restore, `restore_pft_stream_checkpoint` rejects mismatched in-memory state,
truncates the physical trace to the recorded byte boundary, and seeks the
channel before proof production continues.

The implementation is committed on both producer branches:

- current HOL Light: `d52a9a847c4dff2509231b3a05199de922547916`;
- Flyspeck-tested compatibility branch:
  `ead33fbf82d7499919dead57b4ce8b2b06256f55`.

## Forced recovery evidence

The smoke producer saved `candle$RESUME_BEFORE`, prepared a boundary at byte
415 and command 72, wrote a deliberately invalid post-checkpoint tail, and was
terminated by `dmtcp_command -kc`.  A new coordinator restored the compressed
image, the producer removed the stale tail, derived `candle$RESUME_AFTER` from
the theorem that existed before the checkpoint, and finished normally.

The resumed and uninterrupted traces were byte-identical with SHA-256
`7a3c7cefe5649bd70ddb8fa6a8c6c18443068c9e1e522385c9dce2d767aa0dc2`.
Compiled Candle replay reports 305 commands, limits and peak live objects
`(63,64,99)`, both exact targets, no axioms, and no compute context.  The
checkpointed producer was about 5.1 GiB RSS and its compressed image about
1.2 GiB.  All temporary process images (2.3 GiB from the final manual trials)
were deleted after validation.

The packaged acceptance run completed checkpoint/kill/restore and byte
comparison.  Its first invocation then found only a presentation mismatch—the
interactive Candle prompt preceded the final marker.  The corrected matcher
and the same locked compiled replay were validated without creating another
large process image.  The ordinary Candle regression suite also passes the
pinned resumed trace alongside compute, Flyspeck, bootstrap, and malformed
fixtures.

## Real-build workflow

Flyspeck commit `f884cba58cf962e7b67231c81290dcafd72d22b3` adds
`export_restartable_build.hl`.  It starts streaming before
`Multivariate/flyspeck.ml`, disables post-core axioms, follows the checked-in
`Build.build_sequence_main_statement` or `Build.build_sequence_full`, records a
recovery boundary after the foundation and at configurable source-file
batches, and saves the corresponding final theorem.

`scripts/run-restartable-flyspeck-export.sh` supervises this driver.  A state
directory pins all repository heads and arguments, records source index and PFT
state, restarts the newest image after checkpoint-and-kill or an interruption,
keeps at most the newest generation, structurally inspects the completed trace,
and by default replays it through the compiled Candle executable.

## Trust and remaining scope

DMTCP images are executable local process memory.  They are never proof
artifacts and must not be restored from an untrusted source.  The resumed final
PFT remains hostile input; only compiled Candle replay supplies logical
evidence.

This proves restart mechanics and implements the real-build workflow, but the
full sequence has not yet completed under it.  G2 and G8 therefore remain in
progress pending target reachability, total time/disk/RSS/slot measurements,
and final compiled replay.  Nonlinear/LP closure and full L2 also remain open.
