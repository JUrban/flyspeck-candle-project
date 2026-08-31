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

The next functional slice is therefore the exact declared nested output-mount
edge: admit only literal `candle-output` during the held input traversal, bind
it to the separately retained output anchor, refuse to recurse through that
edge, reject every other nested mount, and retain the exact-empty output
prewalk.  That work is active in parallel and will stop for another
independent review before child setup is added.
