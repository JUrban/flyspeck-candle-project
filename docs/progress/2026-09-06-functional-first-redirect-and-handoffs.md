# Functional-first redirect and queued handoffs — 2026-09-06

## Claim boundary

This checkpoint records a prospective priority change, two read-only handoff
audits, and the exact ordering of already-running or queued diagnostic work.
It does not claim a completed canonical bootstrap, parser pass, direct-source
pass, Great-100 pass, S1, S2, S3, or usable whole-Flyspeck Candle release.
PFT remains an independent oracle and was not enumerated, inspected, signalled,
checkpointed, or consumed by this work.

## Priority decision

The response to `2026-09-06-audit2.md` accepts its main functional-priority
criticism.  The prospective critical path is now:

```text
canonical bootstrap and schema-6 link
  -> parser pilot 20/20
  -> parser inventory 400/400
  -> direct d0/d1 diagnostics
  -> schema-7 Great-100 diagnostic 65/65
  -> freeze repaired Candle head
  -> fresh final-head schema-6 bootstrap and S1
  -> cumulative Flyspeck strata and nonlinear/LP closure
  -> minimum trusted-host checkpoint/resume release work
  -> S2/S3
```

Functional and assurance progress are now tracked separately.  The isolated
PID/mount/checkpoint experiment is frozen at project commit `d1c61b3`; it is
nonpromotable and must not be merged or extended before a new post-functional-
gate priority decision.  Its one DMTCP 4.1.0 attempt is retained as a negative
result: the short-lived coordinator exited before restart joined it, no resume
marker was produced, and cleanup was empty.  A subsequent static audit found
no P0, but found that pidfd anonymous-inode metadata was not unique process
identity and that the outer observer did not reconstruct an independent
complete task/process lifecycle FSM.  Those P1 findings are documented on the
frozen branch rather than repaired on the current critical path.

The supplied audit and the response are committed together in the main
project checkout at `7df06fa` (`Record audit2 redirect discussion`).
A repeat review approved that direction and requested a concrete cheap-probe
limit plus a stricter waiting-time side-work rule.  Both are adopted here:
d0/d1 are bounded to one hour each and cannot start a pre-Great-100 repair
loop; side work must directly reduce the next parser/direct/Great-100 failure
set.

## Canonical and parser handoff

Canonical attempt 002 remains rooted at:

`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-8a8926906-419a96e37-attempt-002`

It binds the clean exact heads:

- Candle `419a96e374dba147d21fc6547f7025d6d14e5ff0`;
- CakeML `8a8926906ec97204eeec961496d191103cda3229`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`; and
- Flyspeck `1ce0353008eba83d3c76ae9a25c3c242e4802d53` for the downstream plans.

The controller remains the exact serial `Holmake -j1 cake.S` run.  At this
checkpoint target 17/18, `compiler64Prog`, was active.  It was using one CPU
and about 39 GiB RSS while the host retained about 135 GiB available memory.
No terminal bootstrap receipt existed yet.  These are run-local observations,
not portable authority.

The existing automation waits for atomic publication of the canonical
receipt and then performs, in order:

1. exact bootstrap-record validation;
2. ordinary schema-6 runtime installation and both linked checks;
3. execution and independent consumption of the sealed 20-input pilot;
4. fresh materialization of the all-inventory plan only after the pilot pass;
5. execution and independent consumption of all 400 manifest source nodes.

The independent parser consumer remains clean at
`642ad428487e3dfe5d3f146cc141c7bbfc856a7a`.  A fresh read-only audit found no
P0.  It confirmed the exact head, root, plan, receipt, CLI, and source-inventory
contracts.  It also identified two scope limits that must accompany results:

- the 7,200-second CPU/wall and 1-MiB stream limits are installed per child,
  not as a global 400-input campaign limit; and
- 400/400 covers 90 Candle and 310 Flyspeck manifest source nodes.  The 43
  identity-bound generated inputs are intentionally not consumed by this
  parser-only profile and remain work for the direct strata.

The consumer is repository-independent but reuses authenticated producer
validation functions, so it is not implementation-independent.  This does not
weaken the current functional gate, but it must not be overstated as a diverse
semantic implementation.

## Queued d0/d1 handoff

A separate zero-load waiter is queued behind successful completion of the
parser automation.  It independently rechecks the all-inventory result and
the ordinary schema-6 link before it can start compiled direct work.  It then
runs and consumes these fresh diagnostics serially:

| Label | Boundary | Actions | Result root |
| --- | --- | ---: | --- |
| d0 | `d0-diagnostic-through-002` | 3 | `v13-stratum-d0-419a96e-attempt-001` |
| d1 | `d1-diagnostic-through-018` | 19 | `v13-stratum-d1-419a96e-attempt-001` |

Both use plan
`v13-stratum-plan-419a96e-attempt-002`, whose exact `plan.json` SHA-256 is
`310cb1961a4dd2a5e902f1c87baa7f54f51093fa5624139cd62221cbcf573c98`.
The producer uses direct evidence schema 5, a 4,096-MiB CakeML heap, a 48-GiB
address-space limit, a 3,600-second CPU/wall limit, and an 8-GiB output-file
limit.  The clean independent consumer remains pinned at
`9a7922443a8bcfd01d1df657884ad2227cf422fd` and must return
`published-direct-result-pass` with `scheduling_authority=false`.  These two
cutpoints are reconnaissance only; neither authorizes an ordinary stratum.

Every result, producer stream, and consumer stream destination was absent
before the waiter was launched.  A parser failure, dirty authority, stale link,
or existing destination stops the chain closed.  A d0 producer/consumer
failure is preserved and skips d1; a d1 failure is likewise preserved.  Either
direct diagnostic outcome ends this bounded handoff without starting a repair
loop, but does not prevent the separately gated Great-100 diagnostic.

## Queued Great-100 transition diagnostic

A second zero-load waiter is queued behind completion of the bounded direct
handoff.  It independently rechecks parser 400/400 and the source schema-6
link, so it may proceed after a preserved d0/d1 nonpass but cannot proceed
after a parser or authority failure.  The read-only launch audit found no
implementation P0 or P1.  It confirmed:

- clean diagnostic Candle head
  `32fcb81e0735896f290de88f394ef8f9a3356bcd`;
- unchanged transition input blobs between source head `419a96e` and the
  diagnostic head;
- the already-complete independently audited reference artifact at 130/130;
- approved identities for 65 targets and 97 theorem requests;
- exact closure of 65 targets, 66 distinct load files, and 97 requests; and
- fresh transition-record, build, report, and log destinations.

After those independent prerequisite checks, the waiter records and checks the
authenticated transition, uses the five-argument transition build to install
a schema-7 diagnostic link, checks that link, and runs:

```text
regression.py --top100-transition-diagnostic -j 1
  --inactivity-timeout 1800 --wall-timeout 14400
```

The 6,000-MiB Candle heap and one-worker schedule keep this below the current
resource policy.  The timeout is per target rather than campaign-global.  The
runner continues across target failures and publishes the complete diagnostic
batch.  The post-run check requires a schema-4 report for exactly 65 targets
and the explicit schema-7 nonpromotion record.  In particular,
`promotion.eligible`, `promotion.s1_evidence`, and
`s1_evidence.suite_closed` must all remain false.

The independent schema-6 S1 finalizer must not consume this result.  Even a
65/65 transition pass only authorizes freezing the candidate and paying once
for a fresh final-head canonical bootstrap.  One known P2 documentation defect
is deliberately not allowed to move the diagnostic head: the older
`S1_CLOSURE_CHECKLIST.md` still describes the superseded 0/65/null identity
state, while the current integration report and live manifest record the
approved 65/65 state.

## Next decision point

The next development decision is evidence-driven:

- if parser, d0/d1, or Great 100 fails, preserve the complete result and batch
  fixes by shared compatibility cause at the cheapest faithful reproducer;
- if the diagnostic Great 100 is 65/65, freeze that exact Candle head and
  begin the final cache-disabled schema-6 bootstrap and two clean S1 runs.

No new checkpoint-security feature, receipt schema, cache architecture,
x64-only specialization, or large-theory split is scheduled before that
decision point.
