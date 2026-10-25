# Long-run preflight policy

Date: 2026-10-25 UTC

Status: **DEVELOPMENT / NON-RELEASE**

The project treats any run with a declared maximum over 30 minutes as an
integration run, not as an exploratory edit/test loop.  This includes the
segmented 3,300-second support-checkpoint stages.  Before such a run can
start, `scripts/check-long-run-hazards.py` must produce `status=0` for the
exact controller and the current `docs/long-run-hazard-ledger.json` bytes.

The JSON ledger is the durable database of observed and credible long-run
failure modes.  Each active entry records its symptom, root cause, first
evidence, enforcement phase, and executable check.  An entry without a known
check blocks the gate.  A new failure must be appended to the ledger and must
receive a cheap discriminator before a retry is allowed.

The checks are deliberately layered.  Purely static checks establish source
identity, normalization, literal-load, module, and load-order closure.  A
bounded disposable runtime probe must then restore the real predecessor and
reach the proposed readiness marker with the exact setup/support bytes.  Its
receipt is bound to the verified runtime hash, predecessor checkpoint hash,
and a canonical manifest hash of every candidate input.  Editing any one of
those bytes invalidates the probe automatically.  The probe cap may not exceed
one hour.

The ledger is intentionally append-oriented.  A hazard may be retired only
when the obsolete architecture is no longer reachable; the historical entry
and evidence remain.  A passed preflight is not a theorem claim and does not
guarantee success.  It establishes the narrower, useful statement that every
recorded failure class has been checked against the exact planned run.

The gate has separate `theorem` and `support-stage` profiles.  The latter
requires a literal fresh output target, a phase cap of at most one hour, the
exact stage audit and driver hash, the authenticated predecessor chain, static
source/module closure, parser acceptance, pinned runtime/worktrees, adequate
memory, and no competing stage controller.  Its receipt is written outside
the proposed output directory, so the freshness assertion remains true at
launch.  A support-stage controller that does not invoke this profile fails
closed.

For a segmented support stage, old admitted ancestors are checked through the
ordered receipt lineage without rereading every historical heap.  The
immediate predecessor's receipt, completion log, and independent fresh-restart
probe are checked in full.  The phase runner then verifies that predecessor's
checkpoint SHA-256 immediately before restore.  This avoids duplicate
full-chain I/O while still detecting changed bytes at the boundary actually
consumed by the proposed run.  The failed v670 monolithic probe remains
historical evidence; it is a theorem-profile requirement until replaced by a
byte-bound complete-support probe, not a blocker on already segmented stages.

For the first fast NL theorem, the gate covers verified-runtime provenance,
clean pinned worktrees, normalization and source identity closure, explicit
module/load ordering, checkpoint hashes, fresh output targets, resource
headroom, a byte-bound short runtime probe, phase caps, fast-branch evidence,
exact theorem acceptance, and the two-fresh-restore requirement.  The v664
implicit-module omission and absent short-probe receipt are active failing
hazards, so another long replay is forbidden until both gates are green.

The source-identity configuration is also part of checkpoint lineage.  A
later setup file cannot extend an already restored checkpoint because Candle
installs this table exactly once.  The gate therefore requires the support
predecessor to descend from a base receipt with the complete candidate source
count and binds the exact setup/data files through that base's SHA-256 input
manifest.

Historical compatibility overlays may assert the cardinality of the direct
Flyspeck normalization table.  Adding a disjoint side-lane normalization set
must not falsify that local invariant.  The action replay therefore partitions
the exact 29 verifier rows from the exact 56 direct rows, executes the unchanged
historical overlay/action driver on its original table, and restores all 85
rows before checkpoint acceptance.  A static discriminator proves disjointness
and authenticates the historical 50/50 replay evidence before this bridge may
run.
