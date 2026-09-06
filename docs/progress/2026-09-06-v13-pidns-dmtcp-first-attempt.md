# v1.3 task-aware PID-namespace DMTCP first attempt — 2026-09-06

> **Disposition update:** the independent task-controller audit found two P1
> lifecycle-authority gaps.  The experimental branch is frozen and must not be
> integrated or consumed; see
> `2026-09-06-v13-pidns-task-controller-audit-erratum.md`.

## Result

The first bounded real-DMTCP attempt failed closed before a live restart could
join its coordinator.  The task-aware controller reported exactly:

```text
PID-namespace projection diagnostic failed: projected root process did not exit zero
```

No resumed receipt was created.  The projected tree was empty after cleanup,
both disposable coordinators exited, and all origin/restart launcher sessions
were reaped.  There was no restart retry or DMTCP-specific controller change
after this single attempt.

This negative result does not establish or refute DMTCP compatibility with the
task-aware controller.  The attempted `--join-coordinator` target had already
expired, so the restored-process and low-thread-count paths were not reached.

## Fresh origin and real publication

All inputs came from the fresh disposable root
`/project/dmtcp-task-pilot.sYMaPnfc`.  A new harmless Python fixture started one
main task and two worker threads, then waited for a fresh external marker.  Its
origin record was:

```json
{"main_tid":40000,"pid":40000,"thread_count":3,"worker_tids":[40004,40006]}
```

DMTCP 4.1.0 produced one uncompressed 43,200,512-byte image.  The origin was
then killed through its fresh coordinator and reaped.  The image was moved into
a private mode-0700 staging directory on Btrfs, sealed with the real
`FS_IOC_ENABLE_VERITY`/`FS_IOC_MEASURE_VERITY` path, changed from mode 0600 to
0444, and published by no-replace rename into a mode-0555 directory.

Exact image/publication identities were:

```text
manifest SHA-256: 2a955ab362235d127b14b75dc2c907dc0492e16fb222c274ac51d8b701657396
image SHA-256:    cfcc3b13215a4cbeb0e499b0ea3cd0dba952912868c4f06fb192e1d8b5903cc3
image MD5:        fa0b3885ce28c66ef18f45b89769f834
fs-verity SHA-256:a1145ace64ef2179c6568722aa7df2c1c292ae7597dd40ea33fccba630077ba8
device/inode:     37/73136727
mode/link count:  0444/1
```

The exact installed restart authority was
`/usr/local/bin/dmtcp_restart`, DMTCP 4.1.0, device/inode
`66306/59005790`, 5,062,336 bytes, mode 0755, UID/GID 65534/65534, SHA-256
`f43b31bc4483901d4b49dc0aba10daa1667ef12e4a262a3a39c4897977cd3fb9`.

## Attempt and failure classification

The controller received the exact minimal environment
`PATH=/usr/bin:/bin`, `LC_ALL=C` and constructed this projected invocation:

```text
/usr/local/bin/dmtcp_restart --join-coordinator --coord-port 40947 \
  ./ckpt_python3.12_d26a4556-40000-d6a0fbfe43a36.dmtcp
```

The fresh restart coordinator deliberately had a short stale timeout.  Its
own status record shows start at `01:58:45 UTC` and exit at `01:59:02 UTC`.
The controller failure record was written later, at `01:59:08 UTC`.  Therefore
the exact join target was already dead when the restart executable ran.  The
restart root closed nonzero, which the controller rejected; this is a setup
lifetime failure rather than evidence of a seccomp, ptrace, thread-recreation,
or image-projection incompatibility.

The external diagnostic records remain outside Git at the disposable root:

```text
attempt-summary.json SHA-256:
  c395c5a81ff78c978dd8bf86779fe205709842d8163e39b1ab4be81edbea09eb
controller-failure.json SHA-256:
  336e951f968f143e6177c9e76e8a1cd2d45055dc904f60f1b36ff1cd4d0435c0
```

The sealed 43 MiB publication is retained there with the records for bounded
postmortem reproducibility.  It is not a project input or release artifact.

## Claims and next scope

OS evidence authentication, runtime qualification, DMTCP compatibility,
promotion, S2, S3, host-filesystem hiding, host-PID-namespace hiding, private
networking, and PFT exclusion all remain false.  No independent-oracle process
or artifact was inspected, hashed, signalled, or used.  The canonical CakeML
build and parser pipeline were not touched.

Any later restart attempt would need to start its fresh coordinator immediately
before the controller or give the coordinator a lifetime that exceeds
setup/sealing time.  No such retry belongs to this record.  The branch is
frozen pending post-G3/G4 prioritization and must not be integrated or consumed.
