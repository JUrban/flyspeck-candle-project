# PFT restored-stream truncation repair — 2026-08-27

This report concerns the parallel PFT validation lane.  It does not advance
the governing v1.3 S3 direct-source claim.

## Incident

The uncompressed full-L2 validation run reached and successfully restored the
source-file boundaries 0 and 10.  At source 20 it preserved a flushed trace
boundary of 9,011,458,364 bytes and 1,018,546,750 commands in
`jordan/parse_ext_override_interface.hl`.  Every subsequent DMTCP generation
restored the saved process, but the producer then raised:

```text
Sys_error "truncate -s 9011458364 ...: No child processes"
```

The old checkpoint and exact-boundary trace remain incident artifacts, not a
resumable validation run.  Retrying the same executable image cannot acquire a
producer source fix, and mixing producer heads in one trace is forbidden.

## Repair

The producer formerly invoked external `truncate` through `Sys.command`.
After DMTCP restore, OCaml's inherited child/wait state can make that call
raise `ECHILD`, even when the child has already changed the file.  Both HOL
Light producer branches now flush the stream and call `Unix.ftruncate` on the
already-open output descriptor, then seek to the checkpoint offset.  This
removes the subprocess and narrows the mutation to the owned stream.

Pinned repair heads are:

- HOL Light: `a2674c3005da788bb6f1ac9046444edbc70983aa`;
- Flyspeck compatibility producer:
  `1ea3b9a8c614ffee4116789e23a6dcaa03bdc0b9`.

The producer explicitly loads `unix.cma`; the intermediate
`Unix.LargeFile.ftruncate` form was rejected by the pinned HOL parser and the
first direct `Unix.ftruncate` form exposed the missing runtime dependency.
Those failed smoke attempts were retained until the final repair was proved.

## Fresh process-resume evidence

`DMTCP_GZIP=0 ./scripts/test-producer-resume.sh` passed with:

- uncompressed checkpoint bytes: 5,556,011,008;
- baseline/resumed trace SHA-256:
  `7a3c7cefe5649bd70ddb8fa6a8c6c18443068c9e1e522385c9dce2d767aa0dc2`;
- exact byte equality between baseline and resumed traces;
- 305 commands accepted by the compiled Candle replay, with targets
  `candle$RESUME_BEFORE` and `candle$RESUME_AFTER` and no axioms.

DMTCP can restore standard descriptors either to the original producer log or
to the restart invocation's log.  The harness therefore validates its two
exact success markers across that closed pair of owned logs.  Restart stdin is
explicitly `/dev/null` in both the smoke harness and full supervisor, avoiding
terminal job-control stops when a restored process is placed in a background
process group.

The next full PFT validation attempt must start under these new locked heads
and use new output/state paths.  The source-20 image is preserved only as
diagnostic evidence and must not be resumed or promoted.
