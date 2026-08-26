# Gate 1 compiled-soundness audit — 2026-08-26

## Artifact identity

All PFT acceptance and rejection tests run in the compiled executable at
`repos/candle/candle/build/cake`, invoked with `--candle`.  Its SHA-256 is
`d361be3839f31811328d5a0da1ecea15a8a73f369c77e34a288355f16bb930d3`.
The executable's own `--version` report identifies CakeML source commit
`4e312c0f7e18b9c5789c8ac4e0af257bff895cf5` and HOL4 commit
`63f2eb9c146352dfd0bab8c5604a096d1e554d03`.  The downloaded archive, patched
assembly, patched basis FFI, Candle boot program, and encoded configuration are
all separately pinned in `manifest.lock.toml` and checked by
`scripts/verify-lock.sh`.

## The theorem covering the executable

At the artifact's exact CakeML source commit,
`compiler/bootstrap/compilation/x64/64/proofs/x64BootstrapProofScript.sml`
proves and checks both `cake_compiled_thm` and `candle_top_level_soundness`.
The latter states, in summary:

- if the x86-64 machine state is ready to run the verified REPL;
- and `res` is a behavior of that machine under the modeled basis FFI;
- then the behavior is not `Fail`; and
- every emitted event satisfies `ok_event`.

At the same commit, `ok_event` requires every output on the private
`kernel_ffi` channel to be the byte serialization of some `th` and `ctxt` for
which the deep Candle judgment `THM ctxt th` holds.  The proof reaches this
machine-level result through compiler correctness, `candle_soundness`, and the
Candle kernel invariant.

This is the theorem connection relevant to PFT replay.  `replay.ml` is loaded
as a dynamic REPL program, but the REPL admits only declarations satisfying
`safe_dec`.  In particular, dynamic code cannot construct the protected kernel
representations and cannot invoke `kernel_ffi`; it can obtain theorems only
through the verified Candle kernel interface.  The successful compiled loads
of `pft.ml` and `replay.ml` are also runtime evidence that the endpoint lies in
that admitted source subset.

## What this does and does not establish

The theorem connection establishes that accepting a hostile trace cannot make
the compiled endpoint emit a forged Candle theorem, subject to the theorem's
machine/FFI readiness assumptions.  PFT `EXPECT` then checks the reconstructed
theorem's hypotheses and conclusion against the trace's independently decoded
terms, while the replay result records canonical identities.

It does not prove that:

- the PFT parser terminates or stays within a particular resource bound;
- an allowed HOL Light axiom is true (the exact three axioms remain explicit
  assumptions, with infinity handled by the selected HOL consistency model);
- the dynamically loaded PFT orchestration code is trusted or correct beyond
  the fact that it cannot forge protected kernel values; or
- the locally patched C `customFFI` implementation refines the CakeML FFI
  model.  The endpoint no longer shells out while parsing a footer and does not
  use `customFFI`, but that C patch remains an explicit platform trust item for
  the overall executable.

The artifact predates later convenience theorems named
`candle_top_level_consistency_*`; those are not attributed retroactively to this
binary.  Gate 1 remains `in progress` until command-surface negative coverage
is audited, but the previously open binary-to-soundness identification is now
resolved.
