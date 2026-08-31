# V4 inherited-root checkpoint — 2026-08-31

## Accepted scope

The V4 native branch `codex/flyspeck-v13-v4-validator` now has an
independently accepted process-local prerequisite for binding the future
isolated builder to roots retained by the outside parent.  Functional commit
`a1716fb9d68f80ba5524e5ced86f3020b734842f` takes immutable by-value snapshots
of one input and one output anchor before clone.  Each anchor has a primary
and guarded same-OFD descriptor.  The stopped child's inherited descriptor
numbers are joined back to the parent with cross-process `KCMP_FILE` and
strict descriptor-rooted child `fdinfo` projections at the initial stop and
every later held-state verification.

The held builder's walk API accepts no post-hoc path or anchor.  It walks the
captured input root completely, verifies the child remains held, walks the
captured output root, requires the latter result to be exactly empty, and
verifies the child again.  The positive fixture has a deterministic three-entry
input tree; hostile cases cover config/snapshot/ledger splices, same-object
roots, nonempty output, descriptor/OFD substitutions and parent descriptor
number reuse after clone.  Caller-owned anchor descriptors remain live and
are not closed by builder teardown.

Independent source and lifecycle review found no P0/P1 defect in that limited
claim.  Replay from report commit
`14ab73bda2ebbb3675cda1803321c6fa6ecaffcb` passed all 105 relevant tests in
33.077 seconds, including ordinary and combined ASan/UBSan native builds.
Strict C, GCC `-fanalyzer`, relevant `py_compile`, `git diff --check` and source
identity checks passed.  The retained artifact is:

`/project/flyspeck-candle-runs/v4-bound-roots-independent-a1716fb-attempt-001`

Its `independent.log` SHA-256 is
`c5e70aff0737f01ecb61e463e531c278d7fc65142a5baa9e992c3a819c5767b9`.
Acceptance is recorded by V4 commit
`aee71535b940aca188238b49b5331912a615b53c`.

## Remaining boundary

This checkpoint is not input-closure authority.  In particular, a bounded
walk alone is not stable against a concurrently writable tree.  It does not
yet establish the production-shaped separately mounted `candle-output` edge,
read-only input mount, traced propagation/fchdir/chroot setup, closure of the
child FD surface, credential/capability/filter transitions, compiler exec,
V2 receipt producer or positive authority consumer.  All enclosing approval
consumers remain absent or fail closed.

## Declared nested-output acceptance

That next slice is now independently accepted.  Functional commit
`8e2450a93f6481ce8e29fc15a0035cd3558f2abc` admits only the exact literal
`candle-output` mount edge, binds its complete mount/object/descriptor
projection to the separately retained writable output anchor, records its
same-OFD anchor alias, never recurses through it, and preserves the separately
held exact-empty output walk.  Functional/test successor
`94f670266c5928134efa4e5c26c4ad359db111be` closes the audit's two P2 gaps
with exact errno/message cases for writable input, read-only output,
missing/symbolic/regular literal edges, the same object through a different
mount instance, and an undeclared nested mount.

Independent replay from report head
`baaaa40ab4c40df95177b0cf35d8a2ce97d8feff` passed 105/105 tests, ordinary
and combined ASan/UBSan native executions, strict C, both `-fanalyzer`
compilations, `py_compile`, tree/source identity and `git diff --check`.  The
retained artifact is:

`/project/flyspeck-candle-runs/v4-nested-output-independent-94f6702-attempt-003`

Its `independent.log` SHA-256 is
`ef3762cb27ae7d9cb28029ed36508430707cec7a6f00fb7aa7fa67a73a25dc49`.
V4 acceptance commit is
`c91c671fefb067178f5137c50884c57f5af998c5`; no P0/P1 defect remains in this
scoped prerequisite.

The next functional slice is the parent-traced child setup prefix: prove the
exact setup syscall sequence and observations for private recursive mount
propagation, inherited input-root `fchdir`, `chroot(".")`, and final
`chdir("/")`.  FD-surface closure, credentials/capabilities, filters, exec,
V2 receipt production and outside-parent authority remain later gates.
