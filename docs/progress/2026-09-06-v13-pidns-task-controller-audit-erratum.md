# v1.3 PID-namespace task controller audit erratum — 2026-09-06

## Verdict

An independent static audit of the completed experimental branch reported no
P0 finding and two P1 findings.  They invalidate the branch as an integration
or evidence-consumption candidate despite the passing functional fixtures.

1. A pidfd's `fstat` device/inode/mode normally identifies the shared pidfd
   anon-inode type, not one process lifetime.  Matching that dictionary plus a
   numeric inner TGID/NSpid tail therefore cannot distinguish a stale retained
   pidfd after TGID reuse.  The hostile unit test mutates the dictionary; it
   does not reproduce or close the real reuse case.
2. The outer observer validates packet schemas and local relationships but
   does not maintain an independent process/task lifecycle FSM or recompute
   birth, exec-collapse, terminal, and zero-active closure.  It accepts the
   manager's result summary, so the purported outer closure is not independent.

The emitted `threads_supported=true` field is consequently too broad.  The
tests establish only that the listed low-thread-count fixtures completed under
this diagnostic; they do not establish a consumable thread-support contract.

## P2 notes

The audit also retained two P2 concerns: process authority can race around the
READY/ACK boundary, and `_kill_pidfd` falls back to numeric `kill(2)` when
`signal.pidfd_send_signal` is unavailable.  The latter can target a reused PID
and must not be part of any portable security claim.

## Disposition

The first real-DMTCP attempt remains recorded separately as a setup-lifetime
failure: its short-lived coordinator expired before the join.  It adds no
compatibility evidence and was not retried.

This branch is frozen pending post-G3/G4 prioritization.  It must not be
merged, integrated, used by a consumer, or cited as OS-authenticated,
runtime-qualified, DMTCP-compatible, promotion, S2, S3, process-lifetime, or
independently recomputed lifecycle evidence.  No code repair or further pilot
is authorized in this frozen milestone.
