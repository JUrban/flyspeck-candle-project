# Long-run preflight policy

Date: 2026-10-25 UTC

Status: **DEVELOPMENT / NON-RELEASE**

The project treats any run with a declared maximum over one hour as an
integration run, not as an exploratory edit/test loop.  Before such a run can
start, `scripts/check-long-run-hazards.py` must produce `status=0` for the
exact controller and the current `docs/long-run-hazard-ledger.json` bytes.

The JSON ledger is the durable database of observed and credible long-run
failure modes.  Each active entry records its symptom, root cause, first
evidence, enforcement phase, and executable check.  An entry without a known
check blocks the gate.  A new failure must be appended to the ledger and must
receive a cheap discriminator before a retry is allowed.

The ledger is intentionally append-oriented.  A hazard may be retired only
when the obsolete architecture is no longer reachable; the historical entry
and evidence remain.  A passed preflight is not a theorem claim and does not
guarantee success.  It establishes the narrower, useful statement that every
recorded failure class has been checked against the exact planned run.

For the first fast NL theorem, the gate covers verified-runtime provenance,
clean pinned worktrees, normalization and source identity closure, explicit
module/load ordering, checkpoint hashes, fresh output targets, resource
headroom, phase caps, fast-branch evidence, exact theorem acceptance, and the
two-fresh-restore requirement.  The v664 implicit-module omission is seeded
as an active failing hazard, so another long replay is forbidden until that
audit is green.
