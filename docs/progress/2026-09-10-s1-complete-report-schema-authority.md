# Complete S1 report-schema authority and authorization-v3 review material

Date: 2026-09-10 UTC

## Exact implementation

The complete implementation is commit
`da94b8011011cfdd34886f8bc6ec564a4b93620b` on branch
`codex/s1-finalizer-schema-authority-v16`.  It replaces handwritten report
shape approximations with a deterministic authority mechanically derived from
both qualified schema-4 reports:

- 35 object paths and all observed closed-key variants;
- 10 array paths and all observed length/item-kind variants;
- 147 scalar paths and all observed primitive JSON-kind variants;
- 25 exact discriminant/schema paths;
- 15 named shape bindings used by the finalizer.

The checked definition is `scripts/great100_report_schema_v4.json`; the
deterministic checker is `scripts/generate-great100-report-schema.py`.  The
authority includes `linked_schema` in both pre- and post-runtime shapes and
requires an actual integer with value `6`.  The authority module and generated
definition are independently bound by finalizer preflight, authorization,
archive inventory, and postflight.

Exact implementation identities:

- finalizer: 230300 bytes, SHA-256
  `aaa5a4a4469c5140fb1cd3552629451143d5358c5c020b896a689eb9ba3aaba6`;
- authority module: 16603 bytes, SHA-256
  `70b90b0c0dd8fc387b66843c2d17159db4fcb45052b8e2bb6f12b3f80ea372d1`;
- derived definition: 37959 bytes, SHA-256
  `5eba42126dd40f76c74401d91a3de0ac73afe38e576c06169526a89b254676a0`;
- generator/checker: 2072 bytes, SHA-256
  `574879d63c7173518991ca964c8e34f2e133a2e0d7fb8d12fe2b9533e585a4cc`;
- non-authorizing harness: 14848 bytes, SHA-256
  `85a34e085185d5d25226c166f4772e3af2e2e92863337a990d7f4855e454f887`.

The complete finalizer suite passed 85/85 tests in 493.733 seconds.  The
mechanical comparison matched all 35 object, 10 array, 147 scalar, and 25
discriminant paths.  Adversarial coverage rejects nested extra/missing keys,
array length and item-kind drift, scalar type confusion, changed discriminants,
and changed generated definitions.

## Non-authorizing publication-boundary result

The exact clean implementation head processed the unchanged reports and
reached the intercepted publication boundary.  The preserved report is:

- `/project/flyspeck-candle-runs/great100-schema4-5e6362f-finalizer-dry-run-v3-attempt-004.json`;
- mode 0444, 2986 bytes;
- SHA-256
  `a652230e5aee006f24468aaaa13b562c47e04a050d910ca8f25af2b0e6efb05c`.

The result records two validated 65-result runs, 130 reference-projection
validations, 130 replayed candidates, two retained 65-log sets, exact semantic
agreement, and one deliberate non-authorizing predicate bypass.  The staged
bundle SHA-256 was
`303477ac39c3e5f7abc4ff5267a989b6a0f6b00eaf17e60362b5f993fcb5fc3a`;
the staged checksum file SHA-256 was
`76a5eb1a44b53fdf260cd4552c12d443fc2c0d0f54080fc5b1aa6c92d45dc4a9`.
All 7,337 checksum entries were audited, staging cleanup completed, and the
requested destination
`/project/flyspeck-candle-runs/great100-schema4-5e6362f-final-s1-v3` remains
absent with no matching temporary staging directory.  No S1 finalization or
promotion is claimed.

## Qualified-evidence immutability

Immediately before the dry run, the qualified Candle checkout was clean at
`5e6362f4df4979d9a35e99c4673d177f32eb3145`.  The qualified producer remained
SHA-256 `a92c4a5aa13a0710ec93402fc4792bed8f0d059390e260f95b07842cdf83fcfb`.
The reports remained:

- run 1: 367897 bytes, SHA-256
  `e7e840b36ac3a5901649dca97671c940c46b403510a6c72e658938760f0e9b37`;
- run 2: 367888 bytes, SHA-256
  `402aaabdf47b528a5ab5e45c265deb91a3033e8b6920b8698e95d50793332ecc`.

The linked record SHA-256 remains
`048ccb79ea115180bbe85338c09bc4f81d3ca2106ce0bcf49bf8495e33b81e5f`,
the source-closure SHA-256 remains
`0622733a060fb1529ff8962b041f9ae01cb02e0a6538c0f010085ffb90481e3c`,
and the independent approval remains 540523 bytes with SHA-256
`d82d0e8a413fdb78ded902e5a6d8537d95da65ef5bb194a39883b80a751a3de8`.
No qualified runtime, source, report, transcript, approval, reference, or other
evidence byte was changed.

## Unsigned authorization-v3 review request

The exact review material is preserved at:

- `/project/flyspeck-candle-runs/great100-schema4-5e6362f-finalization-review-request-v3.json`;
- mode 0444, 7708 bytes;
- SHA-256
  `cf94ee624d2dde05229112937a99c012344378cff48c805a077b4af7bc5a2861`.

Its proposed receipt binds the unchanged report, nonce, linked-record,
source-closure, semantic-projection, approval, Python, Git, finalizer,
authority-module, authority-definition, and exact project-head identities.
The proposed `authority` and `issued_utc` fields are null.  The file has review
kind `candle-great100-finalization-authorization-review-request`, explicitly
forbids use as a receipt, and is not authorization.  An independent authority
must review it, create a separate receipt, and convey that receipt's digest out
of band.  Any authorized run must use an exact clean checkout of implementation
commit `da94b8011011cfdd34886f8bc6ec564a4b93620b`; this documentation-only
successor commit is not substituted for that reviewed head.
