# S1 finalizer reference-source-policy schema correction

Date: 2026-09-09 UTC

## Authorized attempt

The project owner and designated external authority authorized the two frozen
Great100 reports through review request SHA-256
`f4e9de44b265baa157eb70d99fb5939795f03f37cd932d9be1bfef74bcec4544`.
The resulting immutable authorization receipt has SHA-256
`4d7286ff53787c51cb4114fc4175967e4fdca115a0f43484ad908fe99f71b953`.

The bound finalizer at project commit
`b7d30ee1e2e1a98e18fcad9feca6f7a291dbd3cb` accepted the receipt and reached
the independent approval replay, but stopped before archive creation with:

```text
ValidationError: malformed or unauthorized collection reference contract
```

The requested destination remained absent. The qualified Candle checkout,
runtime, reports, transcripts, approval, provenance, and reference collection
evidence were not modified.

## Root cause

The real reference collection contract binds its source policy as:

```json
{
  "schema": "candle-s1-reference-source-contract-v1",
  "historical_upstream_commit": "...",
  "exact_source_reference_commit": "...",
  "compatibility_deltas": ["..."]
}
```

The independently reviewed approval deliberately embeds the same policy
without the source-contract serialization's `schema` member. The finalizer
already requires the schema-bearing form for every retained per-run source
contract, but its collection-contract check compared the schema-bearing object
directly with the schema-free approval policy. Its synthetic test fixture also
omitted the schema and therefore concealed the mismatch.

## Correction and verification

The collection-contract validator now constructs the exact expected object by
adding `candle-s1-reference-source-contract-v1` to the approved policy before
comparison. This retains an exact equality check and does not weaken any
evidence requirement. The fixture now represents the producer's real
schema-bearing contract, and a negative regression proves that a changed schema
is rejected.

Verification:

- positive schema-bearing archive regression: PASS;
- changed-schema rejection regression: PASS;
- complete `scripts/test-finalize-top100-report.py`: 70/70 PASS in 458.553 s;
- `git diff --check`: PASS.

Because the finalizer bytes and project commit changed, the earlier external
authorization receipt cannot be reused. A new unsigned review request must bind
the successor project head and finalizer identity while retaining the exact
same two qualified reports and all of their evidence identities.
