# Great100 schema-v6 reference two-sweep runbook

This runbook controls collection of two independent, sequential schema-v6
reference candidates for every Great100 target. Collection is not approval:
every candidate remains `candidate_unapproved`, every aggregate sets
`promotion_allowed` to `false`, and the controller neither creates nor edits an
identity-approval artifact. No real reference sweep was run while implementing
or testing this controller.

## Pinned inputs

The runnable exact-reference configuration reviewed on 2026-08-29 is:

- Candle collector repository:
  `/project/worktrees/candle-s1-reference-policy-v13` at
  `1e1d4e9b311b4aa52f78c4b9859a775e6eab70a7`;
- `candle/top100_manifest.json` SHA-256
  `e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9`;
- `candle/reference_fingerprints.py` SHA-256
  `a15ef4cd61f44140cb35df76e0a2007a51eaa2c64a4866b3adddfb660bde9b59`;
- exact HOL Light reference repository:
  `/project/worktrees/hol-light-s1-exact-reference-v13` at
  `1258c129c3ddf0b239b649ba7024eab677cd953b`;
- reference runtime `/project/worktrees/hol-light-s1-exact-reference-v13/ocaml-hol`,
  SHA-256
  `f531e272e0c7cfa31886496f672a930fd063ee66367146261c339cc1fc753931`;
- runtime stub
  `/project/repos/hol-light/_opam/lib/stublibs/dllzarith.so`, SHA-256
  `dcc2f53493929d85b724998f628a37042facd69cf546f01fb0682a68a8d7ddb5`;
- `/usr/bin/ocamlc`, SHA-256
  `84825ef63ded23b445acd4ef399e1bb0a11081976da4741e1033c8569eaa2bd6`;
- `/usr/bin/ocamlfind`, SHA-256
  `c08fd2438693fee0c8544216d11a213c51eff33e2fafc73f80f576430ee52837`.

The exact reference is a direct child of historical commit
`3170739521d88d04580f61385c95b497690b7002`. Its Great100 diff must contain
exactly `100/e_is_transcendental.ml`, `100/euler.ml`, and `100/lagrange.ml`,
with the selected hashes and rationales in the committed source contract.

Recompute all hashes out of band immediately before use. A changed head, dirty
repository, changed controller/collector/manifest/runtime input, source-policy
mismatch, or changed retained collection contract is a hard failure, not a
reason to update an in-progress artifact root.

## Invocation

Create a new empty ordinary directory on an evidence volume outside both Git
repositories. Do not reuse a directory from another collection contract.

```sh
mkdir -m 700 /external/evidence/great100-reference-v6

python3 scripts/run-top100-reference-sweeps.py \
  --artifact-root /external/evidence/great100-reference-v6 \
  --candle-root /project/worktrees/candle-s1-reference-policy-v13 \
  --candle-head 1e1d4e9b311b4aa52f78c4b9859a775e6eab70a7 \
  --manifest-sha256 e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9 \
  --collector-sha256 a15ef4cd61f44140cb35df76e0a2007a51eaa2c64a4866b3adddfb660bde9b59 \
  --reference-root /project/worktrees/hol-light-s1-exact-reference-v13 \
  --reference-head 1258c129c3ddf0b239b649ba7024eab677cd953b \
  --runtime /project/worktrees/hol-light-s1-exact-reference-v13/ocaml-hol \
  --runtime-sha256 f531e272e0c7cfa31886496f672a930fd063ee66367146261c339cc1fc753931 \
  --runtime-stublib /project/repos/hol-light/_opam/lib/stublibs/dllzarith.so \
  --runtime-stublib-sha256 dcc2f53493929d85b724998f628a37042facd69cf546f01fb0682a68a8d7ddb5 \
  --ocamlc /usr/bin/ocamlc \
  --ocamlc-sha256 84825ef63ded23b445acd4ef399e1bb0a11081976da4741e1033c8569eaa2bd6 \
  --ocamlfind /usr/bin/ocamlfind \
  --ocamlfind-sha256 c08fd2438693fee0c8544216d11a213c51eff33e2fafc73f80f576430ee52837 \
  --collection-wall-seconds 21600 \
  --target-wall-seconds 21660 \
  --validation-wall-seconds 900
```

Only one controller may own an artifact root. It consumes the exact 65-target,
66-source, 97-theorem-request manifest order. For each of 130 target runs it
creates a new `sweep-N/target-NNN/attempt-NNNN` directory and starts the exact
committed collector under a new isolated Python process. The collector builds
the plan and request, launches a fresh HOL Light process, and emits the complete
transcript and unapproved candidate. A second isolated invocation of the same
collector replays candidate validation. The outer per-target deadline exceeds
the collector's internal deadline so the controller can terminate the entire
process group if the inner controller does not return.

## Resume and result interpretation

An exit status of zero means all 130 target runs are present and revalidated;
it does not mean S1 is approved. A nonzero status stops at the first failed
target. Reinvoke the exact same command to resume. The controller never
overwrites an attempt: it retains failures or interrupted partials and assigns
the next contiguous attempt number. Before skipping any successful target on
resume, it rehashes all linked files and reruns the committed candidate
validator. A success after any unresolved manifest-order gap, a reused session
nonce, a missing target, an unexpected file, or changed evidence fails closed.

`collection-contract.json` records the input identities and deadlines.
`status.json` is the current concise result; `receipt.json` is the canonical
complete inventory. Both report exact completed/pending counts and all failed
or interrupted attempts. A closed receipt must say:

```text
target_count = 65
total_target_runs = 130
completed_target_runs = 130
pending_target_runs = 0
closed = true
outcome = complete
approval_status = candidates_unapproved
promotion_allowed = false
```

Subsequent independent review and approval remain separate work. These raw
candidates must not be copied directly into the Great100 manifest or treated as
schema-4 Candle acceptance reports.
