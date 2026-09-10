# S1 report-schema authority correction and dry-run result

Date: 2026-09-10 UTC

## Scope and immutable inputs

This bounded successor finalizer change began at project commit
`a160399783b5d449e5d81679b62b4ee192b289dd`.  The implementation is commit
`2393a94e5379b4df43af9f4421a9be6fd15bdcd3` on branch
`codex/s1-finalizer-schema-authority-v16`.

The qualified Candle checkout and both reports were unchanged:

- Candle head: `5e6362f4df4979d9a35e99c4673d177f32eb3145`;
- report 1 SHA-256:
  `e7e840b36ac3a5901649dca97671c940c46b403510a6c72e658938760f0e9b37`;
- report 2 SHA-256:
  `402aaabdf47b528a5ab5e45c265deb91a3033e8b6920b8698e95d50793332ecc`.

No qualified runtime, source, report, transcript, approval, reference, or other
evidence byte was modified.

## Implemented authority and verification

`scripts/great100_report_schema.py` is the one versioned authority for the
schema-4 report envelope, nested closed key sets, and promotable schema-6
linked-record classification.  The successor finalizer and its generated test
producer fixture consume that authority instead of maintaining independent key
copies.  The historical qualified producer cannot import this new module:
changing `candle/regression.py` would invalidate its audited source closure.
The finalizer therefore applies the authority statically to the captured,
authenticated historical producer bytes before accepting either report.

Committed tool identities at implementation commit `2393a94e...`:

- `scripts/finalize-top100-report.py`: 227886 bytes, SHA-256
  `c4697648f30344947a61d67836de0246d449621c0476a32879d58a0734131f72`;
- `scripts/great100_report_schema.py`: 8619 bytes, SHA-256
  `ad62ced7792ce202713b45a6ed597bd08028d8a015735a8ac282215da4059268`;
- `scripts/dry-run-finalize-top100-report.py`: 14466 bytes, SHA-256
  `64719d5fea45a0c11b15f735705a73894a0aa3689e98167dfa7d34e22e883055`;
- `/usr/bin/python3.12`: SHA-256
  `1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118`;
- `/usr/bin/git`: SHA-256
  `2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668`;
- qualified `candle/build/cake`: SHA-256
  `7c6705199dae8ecf79a72a85d65ab6a4727b411cdfd34f86f999151a2d292ced`.

Focused tests accepted the exact qualified producer SHA-256
`a92c4a5aa13a0710ec93402fc4792bed8f0d059390e260f95b07842cdf83fcfb`
and rejected report-key and promotion-semantic mutations.  The closed promotion
tests rejected a missing record, an extra key, an ineligible record, and linked
schema 7.  The complete finalizer suite passed: 83/83 tests in 497.836 seconds.

## Actual non-authorizing dry run: failed closed after replay

The exact committed tools then processed the two unchanged reports through the
non-authorizing harness.  Control returned successfully from the approval
replay before entering report validation.  This establishes that both 65-item
reference sweeps (130 candidate identity projections and the captured
130-candidate replay) completed.  The harness did not reach its publication
boundary and makes no finalization claim.

Preserved read-only failure report:

- `/project/flyspeck-candle-runs/great100-schema4-5e6362f-finalizer-dry-run-v3-attempt-003.json`;
- 2344 bytes, mode 0444;
- SHA-256:
  `0d79cd83b3201db05e54336c9198afa6475e32dd9e8f7fd651cd1c4f213acc63`.

The first report then failed at target `100/arithmetic_geometric_mean` with:

```text
ValidationError: malformed runtime state for 100/arithmetic_geometric_mean pre-runtime
```

The qualified pre-runtime object has these seven keys:

```text
candle_executable
candle_git_head
candle_git_status
execution_contract_sha256
linked_record_sha256
linked_schema
source_closure_sha256
```

The canonical `runtime_state` shape inherited the finalizer's six-key set and
omits only `linked_schema`; the observed value is integer `6`.  The qualified
producer emits this field and the frozen reports bind it.  This is a
publication-blocking closed-schema defect, not evidence corruption.

The requested destination
`/project/flyspeck-candle-runs/great100-schema4-5e6362f-final-s1-v3` remains
absent, and no `.great100-schema4-5e6362f-final-s1-v3.tmp-*` staging directory
remains.  No authorization v3 was requested or fabricated.

## Bounded next correction

In a successor commit, add `linked_schema` to the canonical version-4
`runtime_state` shape and require an actual integer equal to `6` for promotable
top100 evidence.  Add adversarial coverage for omission, boolean/type
confusion, and value `7`; run the complete finalizer suite; then use a new
absent destination and report path for another non-authorizing dry run.  Any
future authorization must bind that successor project head, finalizer, and
schema-authority identities.  The preserved attempt-003 report is diagnostic
only and cannot authorize publication.
