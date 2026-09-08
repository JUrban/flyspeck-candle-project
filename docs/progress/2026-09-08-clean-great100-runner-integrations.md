# Clean Great100 runner integrations at the final-S1 boundary

Date: 2026-09-08 UTC

## Outcome

The clean Great100 runner now carries the three exact source normalizations
that were required by the completed G100-S campaign and a fail-closed,
identity-pinned CSDP request bridge for Ceva and Thales.  A clean focused run
at candidate head `5e6362f4df4979d9a35e99c4673d177f32eb3145` passed all four affected
targets with exact approved theorem and full post-state identities.

The approved Great100 source inventory remains byte-identical.  The
normalizations are derived at runtime only after checking the approved source
SHA-256 values, and `candle/regression.py` is already part of the schema-4
execution contract.  No theorem statement, proof intent, allowed axiom, or
S1 requirement was weakened.

## Diagnosis of the first clean run

The first schema-6 clean run was retained at:

```text
/project/flyspeck-candle-runs/great100-s1-4c0ab63-schema6-run-001
```

It was stopped after establishing that it could not be valid final evidence:

- `100/heron` reproduced the missing comparator-normalization type error;
- `100/ceva` entered unbounded increasing SOS search depths because the clean
  runner did not service the CSDP request protocol used in G100-S;
- 35 other completed targets passed before shutdown;
- no `report.json` was emitted, so the retained directory is failure evidence,
  not a partial or promotable Great100 result.

Directly editing `Examples/sos.ml`, `100/ramsey.ml`, or `100/heron.ml` would
invalidate the independently approved source inventory.  Those attempted
source edits were therefore fully reverted.  The original identities remain:

```text
Examples/sos.ml  137f9c7f8a4d9cfb7ed840bc8257345137b4ce447db582675b825bafc3590d83
100/ramsey.ml    c27a2197fd0faa1a8197523ec8b7e8182a122959c3ce3b76f0f0f70326ced94f
100/heron.ml     de7cd4bd92e9d6fa19076ae2195d58fe6c68901307a15da05c366bc0b2b40763
```

## Integrated execution contract

Candle commit:

```text
5e6362f4df4979d9a35e99c4673d177f32eb3145
Integrate Great100 runtime normalizations and CSDP bridge
```

The runner now materializes only the three normalizations recorded by the
authoritative G100-S comparison contract:

```text
Examples/sos.ml -> 7618018fe0437d3ebaa77c56ed17f7fdfd9612aedacee980f0efe2274a6adfd3
100/ramsey.ml   -> d48947f2ffb6b5dc20da21eafcc704e08cf709b40bdb2236f8fe81b315cae17c
100/heron.ml    -> c8a2de1a36931331d156196fa1578f14ffa85043f3b541393ae1f553f813bc59
```

For Ceva and Thales, the runner accepts only the exact private request paths,
executes only this pinned solver, verifies the previously observed return-code
sequence, and rehashes the solver, setup, and all request artifacts before the
target can pass:

```text
/project/deps/hol-light-external-tools-v9/usr/bin/csdp
SHA-256 50a07f934ffac42b774e0991ff5e44cc68a6d8db180258a8fc1d1676cc7e898d
mode 0555
```

CSDP remains only a numerical-certificate proposer.  HOL reconstructs and
checks the exact rational certificates.

## Validation

The new focused unit suite passed 10/10.  The existing timeout, schema-4,
fingerprint, and Top100 manifest suites passed 57/57.  The standalone manifest
check also passed with exactly 65 targets, 66 covered sources, and one
exclusion.

The old canonical bootstrap at `4c0ab63` was preserved at its receipt-bound
path.  A byte-identical schema-7 transition to the clean candidate passed and
produced:

```text
/project/flyspeck-candle-runs/cakeml-transition-4c0ab63-5e6362f-clean-runner-001/bootstrap-transition.json
SHA-256 df830910fd506bad455d575a3ad86f52d1b6551d0587ab95ba72141c1615043a

/project/worktrees/candle-final-s1-clean-runner-v13/candle/build/cakeml-build-provenance.json
SHA-256 6422dda861c34b5af07aa7a9eccf7667381123e875280cc0c831ce75dadeec13
```

Focused exact run:

```text
/project/flyspeck-candle-runs/focused-g100-clean-runner-5e6362f-schema7-001/report.json
SHA-256 594844ecc0c252a7786e90510ccaf81251e347df0128eb82052ce49910eb89f4
```

| Target | Result | Exact-state SHA-256 | CSDP exchanges |
|---|---:|---|---:|
| `100/heron` | PASS | `7d6d0b01d66261cc944b0f5678eb4741218b69d1ffb02af815f94136c6c39dfd` | n/a |
| `100/ramsey` | PASS | `91c508e52572a16b1fd400c978dd6e4aa25fd33085758ba95cbeba8649c2c6d9` | n/a |
| `100/ceva` | PASS | `5dbe681061d7ff693feeb30eb6d1cae5d86e5dfa8ab246ad74b6e839b7265d0f` | 26/26 |
| `100/thales` | PASS | `7b7ddebbfa6ff65d347ef970261c9a924afbcaca91d44f9d953e2f43486e4bea` | 32/32 |

This focused schema-7 run is diagnostic and cannot close S1.

## Next binding step

Freeze `5e6362f`, run a fresh cache-disabled canonical schema-6 bootstrap
rooted at that exact clean commit, link and validate it, then run the two
required full clean schema-4 Great100 executions before external authorization
and S1 finalization.
