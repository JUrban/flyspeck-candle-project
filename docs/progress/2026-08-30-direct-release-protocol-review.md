# Direct S2/S3 protocol review (2026-08-30)

## Verdict

A read-only hostile review of project `b5b4587a53a82b64ad78ab83f7eb0344e67fcbe9`
found no P0 issue, four P1 design gaps, and three P2 gaps.  The P1 findings are
accepted and the direct-release design is corrected in
`2026-08-29-v1.3-direct-release-gates-design.md`.  This report records the
implementation boundary; it does not approve a direct result or S2/S3 claim.

## Accepted P1 findings

1. A direct finalizer cannot equate successful direct S3 mathematical coverage
   with release-level v1.3 S3.  The latter also requires a machine-validated
   evidence manifest closing every S3-required G1--G9 row and mandatory
   release artifact.
2. Cross-run equality needs two canonical projections.  The semantic projection
   contains only the serializer, four ordered theorem fingerprints, structural
   post-state, and four ordered dependency-history records.  The coverage
   projection is nonce-free.  Raw schema-5 semantic coverage hashes a
   nonce-bearing physical observation and cannot be compared byte-for-byte
   across honest runs.
3. Candle schema 5 authenticates 39 certificate inputs but explicitly states
   that consumption is not traced.  A disjoint runtime evidence schema must
   bind certificate consumption before direct S3 coverage can be approved.
4. `check-published-direct-result.py` is a scheduling gate, not a finalizer
   capture API.  It omits the content-bound evidence needed by a finalizer and
   grants scheduling authority to every ordinary prefix.  Only exact final
   boundary `07-final_assembly-through-296`, with 297 cumulative actions, can
   enter clean/full/resume comparison.

## Accepted P2 findings

- The older design called action outcomes, source closure, dependency history,
  and serialization-output closure missing even though Candle `688d9d1...`
  implements them.  They remain unexecuted and unapproved, not unimplemented.
- "Materially cheaper resume" needs a numerical threshold and frozen timing
  policy before the diagnostic pilot.
- The direct archive must reuse the S1 finalizer's semantic controls but adopt
  the newer descriptor/inode-bound, no-replace, failed-staging-retaining
  publication pattern.

## Smallest sound implementation order

1. Add a project-side direct protocol module and hostile tests for strict,
   disjoint canonical schemas: semantic projection, nonce-free coverage,
   unapproved candidate, independent approval, checkpoint/resume, external
   authorization, final archive, and release-evidence manifest.
2. Add a new Candle producer/validator schema for exact certificate consumption
   and clean-versus-resume evidence.  Leave schema 5 unchanged and
   nonpromotable.
3. Extend the independent result consumer with a content-bound capture result
   held under its pinned descriptors and shared lock.  Keep its existing
   scheduling output nonpromotable.
4. Implement two pristine direct reference sweeps and a disjoint independent
   approval validator.
5. Implement the direct finalizer with two clean full results, one resume,
   approved semantic equality, nonce-free coverage equality, external
   authorization, closed archive, and categorical PFT rejection.
6. Implement the v1.3 release-manifest validator.  It alone may raise
   `v1_3_s3_release_approved` after all ledger rows and artifacts close.

Schemas, validators, hostile fixtures, reference collection machinery,
finalizer staging logic, and the release-manifest checker can be implemented
before real direct results exist.  Actual clean/resume artifacts, timing and
negative matrices, external authorization, final archive, and any approval
boolean necessarily wait for the current linked runtime and direct executions.
