# CakeML backend Dopen proof repair (2026-08-31)

## Outcome and boundary

The first committed warm reverse-dependency replay of CakeML
`480a9f4fcdeaea0d50ed2b6e1fc7998371610ded` passed 36 of its 50 theory
targets and then failed at `backendProof.source_eval_to_flat_semantics`.  This
was a useful warm-gate failure: no pristine cold replay was started.

The downstream proof is repaired at CakeML commit
`32580b0b76434f69ab545232b25a4b892173f1ae`, tree
`d2423910af63189c956e7d2f936c7190ec1924ae`.  The change is proof-only.  It
adds no admission, assumption, runtime behavior or wider Dopen contract.

## Exact failure

Warm attempt
`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-480a9f4fc-attempt-003`
ran from 01:31:55Z to 04:33:29Z and exited one.  Targets through
`stack_to_labProof` passed; `backendProof` then failed while applying the
strengthened `source_to_flatProof.compile_semantics` precondition.  Its sealed
receipt reports status `failed` and has SHA-256
`e488b3a7aeac5fc867b12971d26af6dd2cea490fba7a1d312a7d464c88483ce8`.
The log SHA-256 is
`8395cd3b40086fa318510e6c5435f07d9355d564b9dbfc36276218a975f4d53d`.
All four retained stage-3 artifact hashes were unchanged across the failed
attempt.

The new Dopen theorem needs exact equality between the source compiler's
initial module/value domains and the primitive semantic environment.  The old
closing `EVAL_TAC` could evaluate all finite constants, but left the extensional
`nsDom`/`nsDomMod` obligations open.  The repair proves locally that a
namespace with an empty module list has module domain `{[]}`, then discharges
the two exact finite initial environments by lookup-domain extensionality.
Both the no-evaluator and evaluator-enabled branches are covered.

## Focused evidence

The cleaned production script rebuilt the complete `backendProof` theory in

`/project/flyspeck-candle-runs/cakeml-backend-dopen-focused-480a9f4fc-attempt-011-clean`.

`Holmake -j1 --mt=1 backendProofTheory.uo` passed in 4:02.88 with maximum RSS
2,173,700 KiB, zero major faults and zero swaps.  The log ends with exported
theory `backendProof` and `Holmake: [1/1] backendProof`.

- `backendProof.log` SHA-256:
  `aaa95ac84b0d8181c70644d432f7f0e50f31eeedb2e362edb47116265a72cf48`
- `backendProof.time` SHA-256:
  `639c54becc0b1bef715afc3889b8fa4a1f039e0588cc0f2d48db26c61a4bb2db`

Earlier attempts 001--009 were diagnostic iterations and are not cited as
positive evidence.  Attempt 010 passed but is superseded by the cleaned
attempt 011.

## Next gate

Run a fresh warm reverse-dependency attempt from exact CakeML `32580b0b7`.
Only if all 50 targets pass may a new pristine cold worktree be frozen at that
commit and handed to the already accepted cold controller.  The earlier cold
worktree pinned to `480a9f4fc` is obsolete and must not be launched.

