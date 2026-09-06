# v1.3 fs-verity checkpoint feasibility — 2026-09-05

## Scope and claim boundary

This checkpoint establishes one host capability and adds a fail-closed helper
for later direct-source checkpoint work.  It does not independently authenticate
a complete process history, checkpoint publication, DMTCP restart, S2, S3, or
release.  The helper always records `approval_included=false` and
`pft_used=false`.

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

## Exact publication-set integration

The descriptor primitive is now connected to the existing exact checkpoint
publication model without changing the direct-release evidence schema.
`seal_staged_checkpoint_images_fsverity` authenticates a path-sorted,
single-link, mode-0600 staging set against the final mode-0444 image manifest;
enables and measures each held inode; changes it to mode 0444; rehashes it; and
rechecks the exact staging directory inode and contents.  The operation records
that a partial multi-image failure requires discarding the entire unpublished
staging directory.  It never publishes a partly sealed set.

`recheck_checkpoint_publication_fsverity` then requires the staged-seal image
order, final content authorities, inode identities, and manifest digest to
equal the retained no-replace publication.  It remeasures every published held
descriptor and rejects any measurement change.  Both observations remain
explicitly unapproved and non-promotable.

This order is required in practice.  A first disposable integration attempt
tried to enable verity after the existing publication transition and received
`EACCES`.  A controlled mode comparison on otherwise identical Btrfs files
then gave:

```text
mode 0644: FS_IOC_ENABLE_VERITY pass
mode 0444: FS_IOC_ENABLE_VERITY EACCES
```

The corrected path seals while the owner-write bit is still present but all
producer writers are closed.  A separate disposable writer-closure pilot
returned `ETXTBSY` while an `O_WRONLY` descriptor remained open and passed on
the same inode immediately after that descriptor was closed.  Only after
successful enablement does the implementation transition to the manifest's
mode 0444 and call the existing atomic publisher.

A fresh real-kernel two-image pilot passed this complete sequence.  The exact
published manifest SHA-256 was
`39207707ae6ca0be01b52fd9284abf3b3fada089733c787923b8f576e21d91d1`;
the ordered seal SHA-256 was
`6610c76b20d98f1f3883d483269f3ffb5530e5f873193add3f0b2db8e19cc203`;
and the two Btrfs verity digests were distinct.  Both final measurements had
mode 0444 and matched again through the retained publication descriptors.
Every file used by the failed and successful integration pilots was disposable
and has been removed.

## Verification

The checkpoint authenticator suite now has 29 passing tests.  The initial
three primitive tests and three publication-set tests cover:

- exact 128-byte enable and 68-byte measurement buffers;
- explicit irreversible confirmation and exact block-size bounds;
- read-only and close-on-exec descriptor requirements;
- exact SHA-256 algorithm/digest parsing;
- normalized unsupported-ioctl failure;
- rejection of booleans and oversized/non-power-of-two block sizes; and
- retention of negative approval and PFT claims;
- exact seal-before-publish ordering and the 0600-to-0444 transition;
- binding of the ordered manifest, paths, authorities, and inode identities;
- rejection of a changed measurement or spliced seal; and
- rejection of a staging-tree mutation during enablement.

```text
PYTHONDONTWRITEBYTECODE=1 \
  python3 -I -S scripts/test-checkpoint-os-authenticator.py

Ran 29 tests
OK
```

`py_compile` and `git diff --check` also pass.

The fresh complete project regression at implementation commit `46d4319`
passed all 22 `scripts/test-*.py` programs and all 342 discovered test methods
in 852.577 seconds.  This includes 49 direct-release protocol tests, 67 hostile
S1 finalizer tests, 14 top-100 sweep-controller tests, and the 29 checkpoint
authenticator tests.  The finalizer and sweep programs took 428.645 and 286.604
seconds respectively; every program exited zero.

## Remaining authority gap

fs-verity closes only mutation of one inode's contents.  A same-UID process can
still rename or replace a pathname, and DMTCP 4.1.0 accepts checkpoint image
pathnames rather than caller-supplied descriptors.  Release qualification
therefore still needs a controller-owned mount/PID namespace that exposes the
held verity inode at the exact `.dmtcp` pathname, complete restart executable
and loader closure, continuous process-tree authority, and a protected external
launcher/finalizer.  The existing local controller remains intentionally
non-promotable until those boundaries are closed.
