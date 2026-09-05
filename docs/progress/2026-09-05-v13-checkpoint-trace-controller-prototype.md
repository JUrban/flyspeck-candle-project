# v1.3 checkpoint lifecycle trace-controller prototype

Date: 2026-09-05

## Outcome

Branch `codex/flyspeck-v13-trace-controller-prototype` now contains a
standalone continuous ptrace diagnostic.  It addresses a concrete gap in the
existing checkpoint scaffold: the older exec gate detaches after the first
exec and later reconstructs the process group by scanning `/proc`, so it does
not continuously observe fork/clone/exec/exit lifecycle events.

This prototype is permanently non-promotable in its current form.  The
controller and observer share the same ordinary uid, no independently
protected service supplies a challenge or signature, and no delegated cgroup
or protected checkpoint store exists.  A successful report therefore sets
all of these fields to false:

- `os_evidence_authenticated`;
- `trusted_lifecycle`;
- `promotion_allowed`;
- `s2_evidence`; and
- `s3_evidence`.

It also records `approval_status=unapproved-local-prototype` and
`pft_used=false`.  It has not been connected to any PFT process or evidence.

## Implemented diagnostic boundary

The controller becomes a child subreaper before creating the tracee.  The
tracee enters `PTRACE_TRACEME`, stops before exec, and receives the following
options before it can execute the requested program:

- `PTRACE_O_TRACEFORK`;
- `PTRACE_O_TRACEVFORK`;
- `PTRACE_O_TRACECLONE`;
- `PTRACE_O_TRACEEXEC`;
- `PTRACE_O_TRACEEXIT`; and
- `PTRACE_O_EXITKILL`.

The controller drains `waitpid(-1, __WALL)` for the complete registered tree.
It pins each task with a pidfd and records the process start ticks, executable
device/inode, process group, session, and mount/net/pid/user namespace
identities.  PID reuse or identity drift within the stream is rejected.

Linux can expose an automatically traced child's initial stop before the
parent's corresponding fork event.  The controller handles that legal order
by registering the stopped child provisionally against its already traced
parent and requiring the later fork event to close the registration.

The controller sends canonical, sequence-numbered JSON packets over a fresh
anonymous `SOCK_SEQPACKET` channel.  The observer enables `SO_PASSCRED` and
requires every kernel-supplied `SCM_CREDENTIALS` tuple to identify the exact
controller pid/uid/gid.  Duplicate JSON keys, noncanonical bytes, sequence
gaps, truncation, extra terminal markers, and process-identity changes fail
closed.  These credentials prevent a different process from being mistaken
for the selected local controller; they do not protect against compromise by
the same uid.

## Escape handling

`PTRACE_O_TRACECLONE` alone does not close `CLONE_UNTRACED`.  Before
`PTRACE_TRACEME` and exec, the prototype sets `no_new_privs` and installs an
inherited classic seccomp-BPF filter.  It traps a legacy `clone` carrying
`CLONE_UNTRACED`.  Because classic BPF cannot dereference the `clone3`
argument pointer, it conservatively traps every `clone3` call.  A `SIGSYS`
stop is a diagnostic rejection.  A periodic descendant scan remains as
defense in depth and kills a detected escape through a newly acquired pidfd.

Rejecting all `clone3` calls can change workload behavior and is not a final
compatibility policy.  A production controller needs either a protected
launcher with a stronger kernel policy or a reviewed architecture-specific
syscall-entry mechanism that validates the pointed-to `clone_args` safely.

## Tests

`scripts/test-checkpoint-trace-controller.py` contains eight live Linux tests:

1. ordinary exec/exit lifecycle closure with every assurance flag false;
2. transient double fork, `setsid`, and descendant exec closure;
3. rejection of packets from the wrong kernel-reported sender pid;
4. simulated PID start-time and pidfd-identity reuse rejection;
5. controller death causing a double-fork/`setsid` tracee tree to terminate
   through inherited `EXITKILL`;
6. observer timeout killing the controller and tracee;
7. seccomp rejection of an actual `CLONE_UNTRACED` syscall; and
8. canonical-path, namespace, and environment launch rejections.

The suite passes once and in 50 consecutive repetitions after strengthening
the controller-death case to cover all three traced processes.  Earlier
variants also passed 20 repeated timeout-cleanup suites and 25 repeated suites
both before and after the seccomp addition.  These are tiny fixtures only;
they are not checkpoint, Candle, or Flyspeck executions.

The complete project regression set also passes on the clean candidate: 22
test programs and 324 tests, including the 67-case Great 100 finalizer, the
49-case direct release protocol, the existing 23 checkpoint-scaffold tests,
and these 8 new trace-controller tests.  That full pass applies to the
executable/test sources at candidate parent `33b2c25`; this paragraph is the
only subsequent change.

Run the focused tests with:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C.UTF-8 \
  /usr/bin/python3 -B -I -S \
  scripts/test-checkpoint-trace-controller.py
```

An ordinary diagnostic invocation is:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -B -I -S scripts/checkpoint_trace_controller.py \
  --timeout-seconds 10 -- /usr/bin/true
```

Tracee standard streams are redirected to `/dev/null`; the only CLI output is
the canonical diagnostic report.

## Remaining production requirements

This prototype must not be wired into G6 approval.  The unresolved trust
boundary still requires an externally protected launcher/finalizer and fresh
challenge, a delegated cgroup or equivalent complete task boundary, enforced
resource/storage quotas, immutable or protected checkpoint backing, exact
namespace/path projection across restart, and an independently authenticated
restart closure.  Only after those facilities exist can the lifecycle
mechanism be redesigned and reviewed as possible release evidence.
