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
runtimes.  After independent review found that the first schema-v9 validators
retained but did not validate several receipt fields, both validators were
hardened to an exact canonical source/toolchain/recipe/output/probe contract.
They now bind the static `libsdp.a` digest, all eight toolchain fields, ordered
commands, exact CFLAGS and library flags, and strict JSON types.  Schema-v8
validation remains available only with the old v8
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

Verification completed at the repaired selected executable heads:

- Candle `652a18a6735be8969462bf25f3233d23b5a4ed6d`:
  full `candle/test_*.py` discovery 234/234 and focused CSDP validation 25/25,
  including missing, forged, and boolean/type-confused receipt fields.
- Project `95bb84fffade845406af92305baea0a9686ef21f`:
  `test-top100-reference-sweeps.py` 14/14, including CSDP
  source/build/probe/route and exact-CLI rejection paths and complete fresh
  schema-v9 failure/resume and clean two-sweep fixtures.
- Two real no-launch reconstructions from the exact detached launch paths,
  HOL Light reference, and staged external root were byte-identical at 40,231
  bytes, canonical SHA-256 `8270f75b348fe166bde87804b628e92974cac4bc5e43f8400be958beb699e3d7`,
  and compact semantic SHA-256
  `9ce6adff5a24f9634180232351e41fd170a2ed9cdfe3a57d8ea80d9949d2bf66`.
  The earlier development-path hash anchors were rejected and replaced.

The exact receipt validates the audited historical statement; it does not by
itself replay the build or re-hash `libsdp.a`, which is not retained in the
runtime package.  That claim is supported separately by two isolated rebuilds
whose `libsdp.a` and solver outputs matched byte-for-byte.

No old artifact root was changed and no reference collection was launched.
