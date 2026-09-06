# v1.3 process-only PID-namespace projection controller — 2026-09-06

## Result

Experimental branch `codex/flyspeck-v13-pidns-projection` now contains a
working process-only combination of the fs-verity mount projection and a
private-PID-namespace ptrace supervisor.  The implementation head for this
milestone is `e630bb1` (`0cd8df0` implementation, `caedc33` final anchored
mountpoint repair, preceded by reusable-helper commits `a8590a6` and
`44b8c7a`).

This is a useful diagnostic milestone, not a restart or release milestone.  It
is not connected to d0/d1, S2, S3, or any result consumer.

## Implemented topology

The controller uses four roles:

```text
outer observer O
└── user/PID-namespace bootstrap B
    └── PID-namespace init and ptrace manager M (inner PID 1)
        └── stopped workload T (inner PID 2)
            └── traced fork/vfork/process-clone descendants
```

The important ordering is enforced in code:

1. O rechecks the publication fs-verity seal and pins the projection root,
   its parent, and the exact executable.
2. B enters a one-entry user namespace, installs the UID/GID maps, enters a
   child PID namespace, and forks M as namespace PID 1.
3. B proves it closed its duplicate controller socket before M can emit.
4. M creates a private mount namespace, mounts a new procfs rooted in its PID
   namespace, and builds the exact read-only checkpoint-image projection.
5. M closes inherited image and unrelated descriptors, forks T, and waits for
   T's `PTRACE_TRACEME` stop.
6. T has already installed the workload seccomp policy and dropped all
   capability sets before that stop.
7. M applies `TRACEFORK`, `TRACEVFORK`, `TRACECLONE`, `TRACEEXEC`,
   `TRACEEXIT`, and `EXITKILL`, installs its distinct manager filter, drops its
   capabilities, and sends READY while T remains stopped.
8. O independently checks the manager and root pidfds, start ticks,
   namespaces, cwd, security status, exact projected identities, canonical
   packet, sequence, challenge, and kernel SCM credentials.
9. Only an ACK bound to the exact READY SHA-256 releases T.
10. M consumes kernel birth/exec/exit events without enumerating host `/proc`.
    Provisional children remain stopped until the corresponding parent birth
    event is registered.

The mount helper now reopens the mountpoint's parent in the new mount namespace,
compares it with the preflight-held parent, and then uses the post-reopen parent
FD for both the mount and mounted-root open.  This preserves the necessary
same-namespace mount behavior while closing the earlier ancestor/pathname race.

## Process-only syscall boundary

The workload policy permits `fork`, `vfork`, and ordinary legacy process-form
`clone`.  It kills `CLONE_UNTRACED`, `CLONE_THREAD`, `CLONE_PARENT`,
`CLONE_PTRACE`, namespace-creating clone flags, ptrace and cross-process-memory
APIs, namespace entry/creation, and all audited mount APIs.  `clone3` returns
`ENOSYS`, permitting libc to take the inspected legacy fallback.

Threads are deliberately unsupported because `pidfd_open(nonleader_tid)` is
not valid on this kernel.  The next implementation must split process-leader
pidfd identity from per-task `/proc/<tgid>/task/<tid>` identity and handle the
nonleader-exec TID rekey explicitly.

## Cleanup and protocol

The cleanup chain combines O- and B-owned lifelines, `PDEATHSIG`, manager and
bootstrap pidfds, `PTRACE_O_EXITKILL`, and the kernel rule that terminating PID
namespace init terminates the remaining namespace.  An unfinished public
session `close()` performs the bounded abort/reap rather than merely dropping
descriptors.  SCM_RIGHTS pidfds are received with `MSG_CMSG_CLOEXEC` and remain
owned until their packet binding is validated.

A successful result requires exactly one MANAGER, READY, RESULT, and DONE,
RESULT/DONE as the final pair, a clean bootstrap exit, zero active traced
processes, and an empty outer projection directory.

## Verification

The new seven-test suite passed in 4.6 seconds with about 29 MiB maximum RSS:

- exact projected read, stopped READY gate, inherited-FD closure, and ordinary
  exec/exit closure;
- double fork, `setsid`, descendant exec, and three exact terminal events;
- invalid ACK rejection before workload execution;
- clone3 `ENOSYS` fallback;
- namespace, `CLONE_UNTRACED`, and thread rejection;
- manager-death and outer-timeout PID-namespace teardown; and
- unfinished-session close/abort/reap.

The existing OS-authenticator suite also remained green: 31/31 tests in 6.1
seconds.  Total focused coverage was 38/38.

A disposable real Btrfs/fs-verity one-image run (not the fake ioctl fixture)
also closed successfully:

```text
publication manifest: f336fe20de60ffb088e6f582d9e5617c872c9b60493e92a5cfcaad9b0c8adaae
staged seal:          dc7a86871d8497fc1cebca665e4ff0b97a02dc2dffa80285937616e91e30c098
ordered event SHA:    f6f2b4ceca9bcb1b8f5bcf524f7c7aed43cd76ca92c831c3c839f4404b1cda73
events:               manager, ready, exec, exit-stop, terminal, result, done
outer projection:     empty after completion
```

The disposable directory was removed after the run.  No independent oracle
state was inspected or used.

An independent hostile static audit accepted the final diff for its stated
process-only, nonpromotable scope with no P0/P1 finding.  Its interim broad
PID/PFT claim findings were repaired: `host_pid_namespace_hidden` remains
false, the only positive namespace claim is the narrow
`primary_procfs_rooted_in_private_pid_namespace`, and PFT use is explicitly
`not-observed-or-excluded`.  Its residual provisional-child, unfinished-close,
SCM-FD, result-FSM, and mountpoint-anchor concerns were also repaired before
this milestone was committed.

## Explicit nonclaims

The report keeps OS authentication, runtime qualification, promotion, S2, S3,
host-filesystem hiding, host-PID-namespace hiding, private networking, PFT
exclusion, DMTCP compatibility, and thread support false.  Host paths remain
visible, so arbitrary post-ACK reads are not observed or excluded.  The
controller records only that its supplied pathname/argv filter did not select
the forbidden namespace; it does not claim that the workload did not derive a
path dynamically.

## Next gate

Implement task-aware tracing before trying DMTCP: distinct `ProcessIdentity`
and `TaskIdentity` records, leader-only pidfds, held per-task directory identity,
and explicit `PTRACE_EVENT_EXEC` TID rekey handling.  Then run mixed
thread/fork/nonleader-exec fixtures and repeat the hostile audit.  Only after
that gate should a disposable DMTCP 4.1.0 restart be attempted, still with all
promotion and S2/S3 fields false.

