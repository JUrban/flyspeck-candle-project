# Schema-v9 CSDP reference migration

Status: implemented and not launched.

The stopped schema-v8 Great100 collection exposed a missing `csdp` executable
at target 10.  Its existing root remains immutable: the nine successes and the
one failed attempt are not migrated, copied, or treated as schema-v9 evidence.
The replacement route is a completely new schema-4 controller contract whose
collector artifacts are `candle-s1-reference-plan-v9` and
`candle-s1-reference-candidate-v9`.

The Candle collector now authenticates the direct mode-0555 CSDP route, exact
binary size/hash, source archive, duplicate-key-free parsed build receipt,
theta1 input, normalized solver probe and deterministic solution, combined
GP/CSDP package tree, thread-cap environment, and the complete shell/GP/CSDP
ELF closure.  It rejects OpenMP/native build flags and known threaded ELF
runtimes.  Schema-v8 validation remains available only with the old v8
shell/GP policy; schema and policy cannot be crossed.

The project controller independently authenticates the same inputs and runs
its own theta1 probe while constructing the immutable collection contract.
Each v9 plan is mechanically compared to that contract, including PATH,
thread controls, build statement, probe, CSDP route, and three requested ELF
roots.  The collector CLI includes explicit source/build/probe paths, and all
seven new path/hash options are mandatory exactly once at controller startup.

The staged source was rebuilt with one make job and the receipt's exact flags.
Both `libsdp.a` and the final solver matched the receipt, and the rebuilt
solver was byte-identical to the staged executable.  Three direct theta1 runs
had the same solution SHA-256; only the four timing fields varied, so the
normalizer replaces exactly those four numeric values and rejects a missing,
duplicate, or reordered timing record.

Verification completed at the selected executable heads:

- Candle `a6de0957a07ae6276f702659dbbeffd3fa8199aa`:
  full `candle/test_*.py` discovery 233/233 (including focused
  `test_reference_fingerprints.py` 24/24 and `test_top100_manifest.py` 14/14).
- Project `aa496e7fe11dad8e2fc08df353f9ede476685190`:
  `test-top100-reference-sweeps.py` 13/13, including CSDP
  source/build/probe/route and exact-CLI rejection paths and complete fresh
  schema-v9 failure/resume and clean two-sweep fixtures.
- A real no-launch reconstruction against the exact HOL Light reference and
  staged external root produced the contract hashes recorded in
  `docs/s1-reference-v9-csdp-two-sweep-runbook.md`.

No old artifact root was changed and no reference collection was launched.
