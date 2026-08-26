# Three-class Flyspeck producer route selection — 2026-08-26

## Outcome

The direct HOL Light producer route now has compiled replay evidence for all
three representative Phase 2 classes:

1. ordinary set/MESON source: `IMAGE_DELETE_INJ_COMPAT` and
   `HAS_SIZE_2_EXISTS` from the complete Flyspeck file
   `general/hol-library.hl`;
2. list/refinement: `Basics.LENGTH3`; and
3. real-arithmetic/refinement:
   `Vukhacky_tactics.REDUCE_WITH_DIV_Euler_lemma`.

The ordinary artifact loads its complete source file.  The latter two use a
Flyspeck-side route-selection harness at commit
`0e2f9e331b0eded8aca3dbacfe26df92fc84bcac`.  The harness verifies the OCaml
digests of `leg/basics.hl` and `general/vukhacky_tactics.hl`, copies the pinned
theorem statements and proof lists, and supplies only the tactic definitions
those proof blocks use.  It is explicitly not a replacement for
`strictbuild.hl` or evidence that either complete source file loaded.

## Refinement artifact

`flyspeck-refinement-leaves.pft.bin` has SHA-256
`acc76842744d52667c42fd9831bb370e8a812f77668fa7a6ce5f2b6fbefef101`.
The compiled endpoint reports:

- 547,811 commands including the header;
- table limits and peak live objects `(44830,143185,288314)`;
- exact empty-assumption identities for both named targets;
- exactly the three structurally authorized HOL Light axioms; and
- no compute initialization.

The trace crosses the 250,000-command producer checkpoint and positively
exercises `DEL_TYPE_RANGE`, `DEL_TERM_RANGE`, and garbage-collected theorem
deletion/reuse.  The full Candle regression harness passes with both Flyspeck
artifacts and the malformed/unauthorized matrix.

## Resource-driven route decision

An attempted full `vectors.ml` plus Flyspeck tactic load crossed the 10 GiB RSS
guard while still in generic vector proofs and was stopped; only its incomplete
temporary trace was removed.  In contrast, the checked extraction completed at
the core-only scale (about 5.1 GiB observed RSS) and produced a 5.2 MiB trace.

This evidence selects direct, minimal-dependency HOL Light emission for leaf
validation.  It does not solve full-foundation loading.  Full L2 still requires
a restartable continuation design, a source-aligned positive compute path, and
the nonlinear/LP certificate connections.

## Acceptance status

G3 is proved at its stated producer/three-leaf/clean-manifest scope.  G2, G8,
G9, G11, and the full Gate 2–4 conclusions remain open or in progress; no
full-Flyspeck claim follows from these leaf artifacts.
