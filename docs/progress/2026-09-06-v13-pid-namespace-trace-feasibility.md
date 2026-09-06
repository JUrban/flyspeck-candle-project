# v1.3 PID-namespace trace feasibility — 2026-09-06

## Question

The held-cwd mount projection at implementation commit `29d5853` deliberately
kills every process-creating syscall.  That makes the pathname primitive
closed against survivor processes, but it is incompatible with
`/usr/local/bin/dmtcp_restart`, which imports `fork@GLIBC_2.2.5` and may need to
recreate more than one checkpointed process.

This read-only feasibility step asks whether a supervisor can instead permit
forks inside a fresh PID namespace and continuously trace the complete tree.
It is not checkpoint, restart, S2, S3, PFT, or release evidence.

## Disposable pilot

A short in-memory Python pilot performed the following sequence without using
the existing host-wide `/proc` descendant scanner:

1. fork a dedicated manager;
2. create a user namespace and exact one-entry uid/gid maps;
3. create a private mount namespace;
4. call `unshare(CLONE_NEWPID)` in the manager;
5. fork the namespace-init tracee;
6. have the tracee enter `PTRACE_TRACEME` and stop before exec;
7. install `TRACEFORK`, `TRACEVFORK`, `TRACECLONE`, `TRACEEXEC`, `TRACEEXIT`,
   and `EXITKILL` from the manager;
8. execute a tiny isolated Python payload that forks one child and waits; and
9. drain every ptrace/wait terminal event until the registered set is empty.

The result was:

```text
ok: true
fork events: 1
exec events: 1
exit-stop events: 2
terminal events: 2
active tracees after drain: 0
manager exit: 0
```

The manager and tracee were reaped.  No persistent file, namespace, mount, or
process remained.  The pilot did not enumerate host `/proc`, inspect or signal
the independent PFT process, or execute Candle/Flyspeck/DMTCP.

## Architectural consequence

The kernel supports the required manager relationship: a process that remains
outside the new PID namespace can trace and reap the namespace-init child and
its forked descendant using their outer PIDs.  If namespace init exits, Linux
also kills the remaining processes in that PID namespace.  Together with
`PTRACE_O_EXITKILL`, this provides a more appropriate failure boundary than
forbidding DMTCP's process creation.

The production diagnostic should preserve the existing held-fd image and
mounted-cwd chain, then:

- let the manager retain the host `/proc` view needed for pidfd and ptrace
  evidence;
- create the workload in a fresh PID namespace;
- give the workload a second private mount namespace and mount a new procfs so
  it cannot see or signal host processes by PID;
- inherit only the held projection cwd and authenticated executable/loader
  closure;
- block `CLONE_UNTRACED`, namespace creation/entry, and mount mutation after
  setup while allowing ordinary fork/vfork/clone needed by DMTCP;
- retain the credentialled READY/ACK gate before any workload exec;
- trace, pidfd-pin, kill, and reap the complete allowed tree; and
- fail if the namespace-init task exits before all expected restart work is
  closed or if any traced identity/namespace changes unexpectedly.

The workload's procfs must be mounted only after it enters the new PID
namespace.  It must not replace the manager's host procfs view, so the workload
needs a second mount-namespace split after the PID-namespace fork.

## Remaining isolation work

A private PID namespace hides the running PFT process but does not hide host
files.  The final restart lane must also expose an authenticated runtime/source
snapshot and required system closure while masking the rest of `/project`
(including all oracle/run roots) before exec.  Supplementary groups, loader
closure, network access, protected challenges, external finalization, and
resource/storage enforcement remain separate open boundaries.

This pilot establishes only that the multi-process supervision topology works
on the current kernel.  The next implementation should combine it with the
mount-projection primitive in a still-nonpromotable controller and first run
tiny fork fixtures, then a disposable DMTCP checkpoint/restart pilot.  It must
not be connected to d0/d1 or an S2/S3 claim before that combined controller is
independently reviewed.
