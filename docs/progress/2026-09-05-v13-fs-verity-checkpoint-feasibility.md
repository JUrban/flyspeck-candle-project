# v1.3 fs-verity checkpoint feasibility — 2026-09-05

## Scope and claim boundary

This checkpoint establishes one host capability and adds a fail-closed helper
for later direct-source checkpoint work.  It does not authenticate a complete
process history, checkpoint publication, DMTCP restart, S2, S3, or release.
The helper always records `approval_included=false` and `pft_used=false`.

No PFT process or artifact was inspected or modified.

## Implemented primitive

`scripts/checkpoint_os_authenticator.py` now provides two descriptor-rooted
operations:

- `measure_fsverity_fd` issues `FS_IOC_MEASURE_VERITY` on an already-held,
  read-only, close-on-exec regular-file descriptor and requires the exact
  SHA-256 algorithm and 32-byte digest; and
- `enable_fsverity_fd` requires a literal irreversible-confirmation flag,
  validates an exact power-of-two block size against the page and filesystem
  block sizes, issues `FS_IOC_ENABLE_VERITY`, rechecks stable inode/content
  metadata, and immediately measures the same held descriptor.

The Linux x86-64 UAPI is pinned explicitly:

```text
FS_IOC_ENABLE_VERITY  = 0x40806685
FS_IOC_MEASURE_VERITY = 0xc0046686
fsverity_enable_arg   = 128 bytes
version               = 1
hash algorithm        = SHA-256 (1)
```

The parameter and error contract was checked against the Linux kernel's
fs-verity user-API documentation at
<https://docs.kernel.org/filesystems/fsverity.html> and the installed
`/usr/include/linux/fsverity.h`.

Injected ioctl runners remain fixture evidence and produce
`nonfixture=false`.  Only calls through the real kernel ioctl path can produce
a nonfixture observation.  Even a real observation claims only kernel-enforced
read integrity for the retained inode.  It does not authenticate the pathname,
source, signer, controller history, or restart namespace.

## Host pilot

The project storage is Btrfs on `/dev/mapper/vg0-btrfs`, mounted read/write with
Zstd compression.  A fresh 26,936-byte disposable copy of `/bin/true` was
opened read-only and passed through the implemented helper with a 4,096-byte
Merkle block:

```text
ordinary SHA-256:
  8a63c98320173f79e263115e10cefc170155e47d1fd4b5a70e4429d2699cae28
fs-verity digest:
  4fc59d2281c845d915f58da18ee58b292a222061cb2cb4099f20f8f04c7481be
measurement algorithm/size: 1 / 32
nonfixture: true
subsequent O_WRONLY open: rejected with EPERM
```

The ordinary SHA-256 was identical before and after enablement.  The pilot
therefore proves that the current kernel and project Btrfs storage can enable
and measure fs-verity on an ordinary file, including a file created under the
mount's normal compression policy.

An ext4 control returned `EOPNOTSUPP`, consistent with that filesystem lacking
the required superblock feature.  An initial Btrfs probe used an invalid zero
Merkle-block size and returned `EINVAL`; Linux 6.8 requires an explicit
supported power-of-two block size, so that result was a pilot error, not a
Btrfs limitation.  The local UAPI header and the corrected 4,096-byte call
agree.  Every disposable pilot file and directory was removed after its
result; no repository or retained evidence artifact was verity-enabled.

## Verification

The checkpoint authenticator suite now has 26 passing tests.  The three new
tests cover:

- exact 128-byte enable and 68-byte measurement buffers;
- explicit irreversible confirmation and exact block-size bounds;
- read-only and close-on-exec descriptor requirements;
- exact SHA-256 algorithm/digest parsing;
- normalized unsupported-ioctl failure;
- rejection of booleans and oversized/non-power-of-two block sizes; and
- retention of negative approval and PFT claims.

```text
PYTHONDONTWRITEBYTECODE=1 \
  python3 -I -S scripts/test-checkpoint-os-authenticator.py

Ran 26 tests in 3.420s
OK
```

`py_compile` and `git diff --check` also pass.

## Remaining authority gap

fs-verity closes only mutation of one inode's contents.  A same-UID process can
still rename or replace a pathname, and DMTCP 4.1.0 accepts checkpoint image
pathnames rather than caller-supplied descriptors.  Release qualification
therefore still needs a controller-owned mount/PID namespace that exposes the
held verity inode at the exact `.dmtcp` pathname, complete restart executable
and loader closure, continuous process-tree authority, and a protected external
launcher/finalizer.  The existing local controller remains intentionally
non-promotable until those boundaries are closed.
