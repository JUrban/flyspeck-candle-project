# v1.3 checkpoint mount-projection diagnostic — 2026-09-06

## Outcome and claim boundary

Implementation commit `29d5853` adds a private mount-projection diagnostic to
`scripts/checkpoint_os_authenticator.py`.  It projects the exact retained,
fs-verity-sealed checkpoint inodes at stable relative `.dmtcp` names in a
fresh user and mount namespace, then executes a predeclared ELF from a held
descriptor only after the parent validates a kernel-credentialled READY
packet and returns an exact ACK.

This is deliberately not a DMTCP-restart or release implementation.  Every
result is `nonfixture=false` and sets OS authentication, runtime qualification,
promotion, S2, and S3 false.  It also records all of the following limitations
as false rather than treating lexical checks as isolation evidence:

- PFT exclusion is not enforced;
- the host filesystem is not hidden;
- the host PID namespace is not hidden; and
- the network namespace is not private.

`pft_used=false` is therefore only the controller's assertion about the
predeclared diagnostic input.  No PFT process or artifact was inspected,
signalled, consumed, or modified while developing or testing this feature.

## Projection chain

The implementation now performs this fail-closed sequence:

1. Recheck every held publication descriptor against the staged fs-verity
   seal, final authority, inode identity, exact manifest, and kernel digest.
2. Pin the fresh mode-0700 projection directory and caller-predeclared ELF
   executable before `fork`.  The executable authority must have exact typed
   size/hash/mode/owner fields; the held file must be single-link, immutable to
   the caller by mode/ownership, executable ELF64 little-endian x86-64, and
   equal to that authority.
3. In the child, create a new user namespace, install the exact outer-to-inner
   uid/gid mapping, create a new mount namespace, and make mount propagation
   recursively private.
4. Reopen the projection root in the new namespace, require equality with the
   parent-held underlying inode, and mount a fresh 1 MiB `nosuid,nodev,noexec`
   tmpfs on the descriptor-selected mountpoint.
5. Reopen each published pathname in the current mount namespace and require
   exact device/inode/link/mode equality with the inherited publication fd.
   Remeasure both descriptors and require all namespace-invariant fs-verity
   fields and digests to equal the staged seal.  The expected outer uid/gid
   (1001/1001 on this host) becomes 0/0 through the explicitly checked user
   mapping.
6. Bind each current-namespace fd into the held tmpfs-root fd, remount it
   read-only, reopen it relative to that directory fd, and recheck the exact
   inode and `ST_RDONLY`.  Reject omitted or extra names.
7. `fchdir` to the held mounted root and pass only `./<image>.dmtcp` arguments.
   A host-side rename after setup can no longer redirect target lookup because
   the process working directory holds the actual tmpfs mount.
8. Install a little-endian x86-64 seccomp-BPF policy that kills the legacy and
   new mount APIs, `chroot`, `pivot_root`, `setns`, `unshare`, x32 syscalls,
   `clone3`, `fork`, `vfork`, and every legacy `clone` that is not a thread.
   Drop the full capability bounding, permitted, effective, inheritable, and
   ambient sets; lock securebits; and require `no_new_privs=1` and seccomp mode
   2 from `/proc/self/status`.
9. Send canonical READY bytes over `SOCK_SEQPACKET` with kernel
   `SCM_CREDENTIALS`.  The parent compares the packet with the predeclared
   image set, reads the child's mount/user namespaces, cwd inode, capability
   fields, and seccomp state independently through `/proc`, then sends an ACK
   bound to the READY SHA-256.  The child cannot execute before accepting that
   exact kernel-credentialled ACK.
10. Mark every descriptor at or above 3 close-on-exec with `close_range`,
    execute the held ELF fd, and require the directly owned child to exit zero
    within the single total timeout.  Error and timeout paths signal through a
    pidfd when available and synchronously reap the child.

## Rejected approaches and review repairs

Two direct inherited-fd approaches failed in disposable namespace pilots on
Linux 6.8.  Binding from `/proc/self/fd/<inherited-fd>` after creating the mount
namespace returned `EINVAL`, because the inherited fd named a mount belonging
to the old namespace.  `open_tree(..., AT_EMPTY_PATH | OPEN_TREE_CLONE)` on the
same cross-namespace fd also returned `EINVAL`.  The compatible route is to
reopen the published name after entering the mount namespace, compare it to
the still-held inode and fs-verity digest, and bind from that new descriptor.
The syscall contract was checked against the installed headers and the
[`open_tree(2)` manual](https://man7.org/linux/man-pages/man2/open_tree.2.html).

An independent hostile review caught and drove fixes for the following before
commit:

- a missing kill helper on rejection paths;
- a `waitpid(WNOHANG)` assignment that could falsely classify a running child
  as wait status zero;
- execution before parent acceptance, repaired with the READY/ACK gate;
- descendant escape after a successful direct-child exit, repaired for this
  bounded diagnostic by killing every process-creating syscall;
- an x32 syscall-number bypass in the BPF comparisons;
- inherited descriptor leakage across exec;
- use of an undefined namespace helper;
- user-namespace uid/gid translation in fs-verity evidence;
- textual projection-root and executable races, repaired with held fds,
  descriptor-relative construction, held cwd, relative image names, and
  fd-based exec; and
- weak packet checking, tightened to exact schemas and parent-side `/proc`
  revalidation before ACK.

The final independent verdict was acceptance for this explicitly bounded
diagnostic, with no remaining critical or high-severity issue inside that
scope.

## Verification

The complete authenticator suite passes 31/31 tests in 6.139 seconds with a
35,584 KiB maximum RSS:

```text
/usr/bin/time -v \
  python3 -I -S scripts/test-checkpoint-os-authenticator.py

Ran 31 tests in 6.139s
OK
Maximum resident set size: 35584 kbytes
```

The two new tests exercise:

- exact two-image projection and reads through relative held-cwd paths;
- both ordinary and mount-level write rejection;
- distinct user/mount namespace identities;
- all capability sets zero, `no_new_privs`, and active seccomp;
- closure of an explicitly inheritable sentinel descriptor across exec;
- actual seccomp kills for `fork`, `unshare(CLONE_NEWNS)`, and an x32 syscall;
- refusal to execute when the parent rejects READY; and
- a real timeout, pidfd kill, synchronous reap, and absence from `/proc`.

`py_compile` and `git diff --check` also pass.

## Real Btrfs/fs-verity pilot

A fresh disposable two-image pilot used the real kernel ioctls on the project
Btrfs filesystem, the actual no-replace publication path, the new projection,
and held-fd execution of `/usr/bin/true` (SHA-256
`8a63c98320173f79e263115e10cefc170155e47d1fd4b5a70e4429d2699cae28`).
It passed with:

```text
manifest SHA-256:
  e5570b86c152372ead8de13b56c039b384eba335cfa1da769601d505809e7b7d
ordered seal SHA-256:
  cc63e1e808630f83be03a0dcecc3a0bff1fe91e878496269a2058f157ce59a9a
fs-verity digest 1:
  06212028a78dc0741ff59b39d0dd11011e7efc91bcdbdaca37fcf7c5f2a46f0f
fs-verity digest 2:
  d61fad094e1d0620b9b563ea2de030e90b9b0cd08e2b72a8ecab8ab8da096302
READY SHA-256:
  1e896b563952e97753fdc2f53eba9ded283c6ed6c12137e8f95489d38752513c
targets:
  ./first-image.dmtcp
  ./second-image.dmtcp
exit: 0
mount namespace changed: true
user namespace changed: true
all capability sets: zero
host projection root empty after exit: true
runtime/S2/S3 qualification: false/false/false
```

The pilot used 19,712 KiB maximum RSS and 0.39 seconds wall time.  Its temporary
directory and verity-enabled files were removed; no repository or retained
evidence artifact was made immutable.

## Blocking boundary and next design step

This single-process containment policy cannot be wired directly into a real
DMTCP restart.  `/usr/local/bin/dmtcp_restart` at SHA-256
`f43b31bc4483901d4b49dc0aba10daa1667ef12e4a262a3a39c4897977cd3fb9`
imports `fork@GLIBC_2.2.5`, and a multi-process checkpoint necessarily needs
process creation.  The present filter would kill that path by design.

The next checkpoint iteration must retain the held-cwd mount projection while
allowing a complete, supervised restart tree.  The promising route is to
combine the projection setup with the existing continuous ptrace controller
inside a fresh PID namespace, or a delegated cgroup of equivalent strength,
so every allowed descendant remains enumerated, killable, and reaped.  It also
needs a separately challenged DMTCP executable/loader closure, host-filesystem
and PFT isolation, protected external challenges/finalization, and a tested
multi-image restart.  Until those are implemented and independently reviewed,
this result closes only the pathname-projection mechanism, not the roadmap's
checkpoint or resume acceptance gate.
