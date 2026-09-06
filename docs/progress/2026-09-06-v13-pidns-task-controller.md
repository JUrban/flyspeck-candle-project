# v1.3 task-aware PID-namespace projection controller — 2026-09-06

> **Independent-audit erratum:** the implementation and test transcript below
> are preserved as an experimental milestone, but its process-authority and
> observer-closure interpretations were too strong.  The branch is frozen,
> must not be integrated or consumed, and does not establish general thread
> support.  See `2026-09-06-v13-pidns-task-controller-audit-erratum.md`.

## Result

The experimental `codex/flyspeck-v13-pidns-projection` branch now advances
the earlier process-only controller to a task-aware ptrace diagnostic.  The
implementation remains deliberately nonpromotable and is not connected to a
restart result, d0/d1, S2, S3, or any consumer.

The implementation is split across three reviewable commits:

- `20e0515` separates process and task identity, permits traced legacy-clone
  threads, handles exec TID rekey/collapse, and adds the principal fixtures;
- `a5451ae` adds outer event-shape checks, held-task rechecks, and live
  multithreaded manager-death coverage; and
- `37d8987` narrows the observed-exit ESRCH case and attempts to match retained
  process authority by NSpid/TGID and pidfd `fstat` metadata.  The audit found
  that this metadata is shared anon-inode metadata and does not bind a unique
  process lifetime.

## Identity model

`_ProcessIdentity` is keyed by inner TGID.  It alone owns the leader pidfd,
the current process/executable identity, an executable epoch, and the set of
live task IDs.  No pidfd is opened or transferred for a nonleader task.

`_TaskIdentity` is keyed by inner TID.  For every stopped kernel-reported task,
the manager:

1. uses the exact `/proc/<tid>` alias only to learn its TGID;
2. opens `/proc/<tgid>/task/<tid>` with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`;
3. reads `status` and `stat` relative to that held directory FD;
4. checks TID, TGID, NSpid, NStgid, start ticks, and stable directory/stat
   identity; and
5. retains the task-directory FD until an exact terminal wait or an explicit
   exec-collapse transition.

The recorded proc `PPid` observation is named untrusted and is never used to
bind a child to a parent.  A provisional child remains stopped without a birth
claim.  Only its parent's `PTRACE_EVENT_FORK`, `VFORK`, or `CLONE` event and
`PTRACE_GETEVENTMSG` child TID register the edge.  Each registered birth has a
unique sequence, kind, parent TID, and parent TGID.

The outer observer retains every transferred process pidfd and compares a
later task event's inner TGID/NSpid tail and pidfd `fstat` dictionary.  The
independent audit found this insufficient: Linux pidfds normally expose shared
anon-inode device/inode/mode metadata, so the dictionary does not distinguish
a stale pidfd after numeric TGID reuse.  Thread events are required not to
carry pidfds, but unique process-lifetime binding is not established.

## Thread and exec behavior

The workload seccomp filter now permits `CLONE_THREAD` through the inspected
legacy `clone` path.  It continues to kill `CLONE_UNTRACED`, `CLONE_PTRACE`,
`CLONE_PARENT`, namespace-creating flags, ptrace/process-memory APIs,
namespace transitions, and mount APIs.  `clone3` still returns `ENOSYS`, so a
library must use its legacy-clone fallback.

For `PTRACE_EVENT_EXEC`, the manager always reads `PTRACE_GETEVENTMSG`.  When a
nonleader executes, the wait PID is the TGID and the message is the former TID.
The controller:

- finds the former task in the existing TGID process record;
- retains the existing process-leader pidfd, which the manager treats as
  continuity state but the outer observer does not uniquely authenticate;
- explicitly records and retires every sibling task as exec-collapsed;
- does not require per-task start ticks to remain stable across the rekey;
- opens and authenticates the new exact `<tgid>/task/<tgid>` directory; and
- refreshes the process identity and increments its executable epoch.

The emitted exec transition includes former and event TIDs, the nonleader
rekey flag, every collapsed task identity, previous/current process start
ticks, and the executable epoch.  The observer checks packet shape and local
task-group relationships; it does not independently maintain a lifecycle FSM
or recompute complete birth/exec-collapse/terminal closure.

## Exit and cleanup behavior

On this kernel, a nonleader that forked can intermittently return `ESRCH` to
`PTRACE_CONT` after its already-observed `PTRACE_EVENT_EXIT`.  The exception is
confined to a dedicated exit-event continuation helper.  Every other ptrace
stop treats `ESRCH` as an error.  Even in the narrow accepted case, the task
record and held directory FD remain live and success still requires the exact
later terminal wait.  The result exposes an `exit-resume-esrch` count.

Failure cleanup sends one kill per process rather than per task.  It uses the
pidfd API when available but has an audited P2 numeric-PID fallback that is not
safe against reuse.  The manager and bootstrap death chain, PID-namespace-init
teardown, `EXITKILL`, outer timeout, and unfinished-session abort remain in
place.  A live fixture with two running worker threads confirms that killing
the manager makes the retained root pidfd readable and leaves the outer
projection empty.

## Focused verification

The task-aware controller suite passed 12/12 tests in 5.7 seconds, with 30,744
KiB maximum RSS.  Coverage includes:

- exact projection, stopped READY, descriptor closure, and root exec/exit;
- double fork, `setsid`, and descendant exec;
- invalid ACK rejection before execution;
- clone3 `ENOSYS` and namespace/`CLONE_UNTRACED` rejection;
- two concurrent worker threads with held task identities and no task pidfds;
- a fork issued by a nonleader thread;
- nonleader exec TID rekey and sibling exec-collapse;
- synthetic same-TGID/different-`fstat`-dictionary rejection, which does not
  exercise real stale-pidfd/TGID reuse;
- synthetic ESRCH rejection outside the dedicated exit-event helper;
- stopped and live-multithreaded manager-death teardown;
- outer timeout; and
- unfinished-session close/abort/reap.

The mixed thread/fork fixture and nonleader-exec fixture also each passed ten
consecutive stress repetitions.  The existing OS-authenticator regression
suite passed 31/31 tests in 6.2 seconds, with 37,392 KiB maximum RSS.  Total
focused coverage is 43/43.

Only the new PID-namespace controller suite and the OS-authenticator suite
were run.  The older host-scanning trace-controller tests were not run.  No
independent-oracle or PFT process state was inspected or used.

## Explicit nonclaims and residual risks

This remains a same-UID, x86-64 diagnostic.  OS evidence authentication,
runtime qualification, promotion, S2, S3, host-filesystem hiding,
host-PID-namespace hiding, private networking, PFT exclusion, and DMTCP
compatibility remain false.  The fresh primary procfs is rooted in the private
PID namespace, but host paths remain visible and arbitrary dynamically derived
post-ACK reads are not observed or excluded.

The successful low-thread-count fixtures do not justify the broad emitted
`threads_supported=true` field; consumers must treat that field as invalid.
The task-aware model has not completed a real DMTCP restart.  `clone3` remains
an intentional compatibility gap; a workload without legacy fallback fails
closed.  An exec-collapse packet currently carries every retired sibling task,
so an extremely large thread group could exceed the 128 KiB packet bound and
fail closed.  Held task-directory identities are manager-local diagnostic
evidence, not an outer transferable task handle.  The missing unique
process-lifetime binding and independently recomputed observer closure are P1
gaps, so this branch is not an integration or consumption candidate.

## Frozen disposition

Do not run another restart, extend this controller, integrate the branch, or
consume its records before the higher-priority post-G3/G4 review redirects the
work.  A later repair would require a real per-process lifetime binding and an
outer lifecycle FSM that recomputes closure; neither is implemented here.
