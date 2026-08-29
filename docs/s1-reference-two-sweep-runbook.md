# Great100 schema-v7 reference two-sweep runbook

This runbook controls collection of two independent, sequential schema-v7
reference candidates for every Great100 target. Collection is not approval:
every candidate remains `candidate_unapproved`, every aggregate sets
`promotion_allowed` to `false`, and the controller neither creates nor edits an
identity-approval artifact. No real reference sweep was run while implementing
or testing this controller. The first reviewed real launch at Candle `c2b55b1`
later stopped, as required, on sweep 1 target 1: its old list-based serializer
overflowed while hex-encoding the 2,183,544-byte kernel state. That failed root
pins the old serializer and must never be resumed under the repaired contract.

## Pinned inputs

The runnable exact-reference configuration reviewed on 2026-08-29 is:

- project repository: a clean, reviewed checkout containing the committed
  `scripts/run-top100-reference-sweeps.py`; its exact absolute root, full HEAD,
  and controller SHA-256 are mandatory launch arguments;
- Candle collector repository:
  `/project/worktrees/candle-s1-gp-provenance-v13` at
  `fdc7f33cfaf393908545516c4d860d4561af6fd9`;
- `candle/top100_manifest.json` SHA-256
  `e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9`;
- `candle/reference_fingerprints.py` SHA-256
  `3048857c23d798be6b365f58bca7b2566b95fe03b9be710de25c24565fba72af`;
- isolated support module `candle/reference_protocol.py` SHA-256
  `e44ed73330e65058f759e30e90ede0bca0bfdedc7920534d632ecb6806299f68`;
- iterative structural serializer `candle/fingerprint.ml` SHA-256
  `ec150fcb1af48c5554cf535b0b076b0607e44e67d12367b7a0fb8a565e5639ff`;
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
  `c08fd2438693fee0c8544216d11a213c51eff33e2fafc73f80f576430ee52837`;
- project-local PARI/GP package tree
  `/project/deps/pari-gp-2.15.4-2.1build1`, inventory SHA-256
  `fb703986a8bcb2653742020214193a9b802fc0111caf2a26d2d7607e9cc0d810`;
- resolved GP executable SHA-256
  `c9673623cad2eaa7cfe402e7b7d833f1f703689a09837026b6386aaafba6deec`;
- hash-pinned local package archive SHA-256
  `55a95d51afe87688fe0fcfe1bca74bf8c5474533e2a42d3af45c87c1ae0d86fa`;
- read-only GPRC SHA-256
  `473ec0c27f514013b7a1ae2442fbe8e46046df58e6a0be590ea17a03873fc6b1`;
  it sets `nbthreads = 1`, which the exact shell probe verifies before every
  collection plan is accepted;
- empty mode-0555 GP data-tree inventory SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- `/bin/sh` resolves to `/usr/bin/dash`, SHA-256
  `86d31f6fb799e91fa21bad341484564510ca287703a16e9e46c53338776f4f42`;
- `/usr/bin/python3` resolved executable bytes, SHA-256
  `1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118`;
- `/usr/bin/git`, SHA-256
  `2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668`.

The exact reference is a direct child of historical commit
`3170739521d88d04580f61385c95b497690b7002`. Its Great100 diff must contain
exactly `100/e_is_transcendental.ml`, `100/euler.ml`, and `100/lagrange.ml`,
with the selected hashes and rationales in the committed source contract.

Recompute all hashes out of band immediately before use. A changed head, dirty
repository, changed controller/collector/manifest/runtime input, source-policy
mismatch, or changed retained collection contract is a hard failure, not a
reason to update an in-progress artifact root.

## Invocation

Create a new empty ordinary directory, owned by the invoking effective user
with mode exactly `0700`, on an evidence volume outside all three Git
repositories. Do not reuse a directory from another collection contract.
Set the three project values below to literals from the independently reviewed,
clean project checkout; do not derive or change them inside the controller
invocation.

```sh
mkdir -m 700 /external/evidence/great100-reference-v7

PROJECT_ROOT=/absolute/reviewed/flyspeck-candle-project
PROJECT_HEAD=REVIEWED_FULL_40_HEX_PROJECT_HEAD
CONTROLLER_SHA256=REVIEWED_64_HEX_CONTROLLER_SHA256

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C LANG=C \
 /usr/bin/python3 -I -S \
 "$PROJECT_ROOT/scripts/run-top100-reference-sweeps.py" \
  --artifact-root /external/evidence/great100-reference-v7 \
  --project-root "$PROJECT_ROOT" \
  --project-head "$PROJECT_HEAD" \
  --controller-sha256 "$CONTROLLER_SHA256" \
  --python-sha256 1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118 \
  --git-sha256 2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668 \
  --candle-root /project/worktrees/candle-s1-gp-provenance-v13 \
  --candle-head fdc7f33cfaf393908545516c4d860d4561af6fd9 \
  --manifest-sha256 e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9 \
  --collector-sha256 3048857c23d798be6b365f58bca7b2566b95fe03b9be710de25c24565fba72af \
  --protocol-sha256 e44ed73330e65058f759e30e90ede0bca0bfdedc7920534d632ecb6806299f68 \
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
  --pari-gp-root /project/deps/pari-gp-2.15.4-2.1build1 \
  --pari-gp-sha256 c9673623cad2eaa7cfe402e7b7d833f1f703689a09837026b6386aaafba6deec \
  --pari-gp-package /project/deps/apt-noble-pari/packages/pari-gp_2.15.4-2.1build1_amd64.deb \
  --pari-gp-package-sha256 55a95d51afe87688fe0fcfe1bca74bf8c5474533e2a42d3af45c87c1ae0d86fa \
  --pari-gp-gprc-sha256 473ec0c27f514013b7a1ae2442fbe8e46046df58e6a0be590ea17a03873fc6b1 \
  --pari-gp-tree-sha256 fb703986a8bcb2653742020214193a9b802fc0111caf2a26d2d7607e9cc0d810 \
  --pari-gp-data-tree-sha256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 \
  --command-shell /bin/sh \
  --command-shell-sha256 86d31f6fb799e91fa21bad341484564510ca287703a16e9e46c53338776f4f42 \
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

The outer `env -i`/Python command is part of the contract. The controller
rejects any inherited environment entry, missing `-I`/`-S`, non-absolute or
noncommitted controller path, duplicate/unknown CLI option, changed Python or
Git executable, dirty or moved project checkout, Git replacement/graft state,
or assume-unchanged/skip-worktree index flag. The collector and its isolated
protocol support file must both be exact committed bytes.

The artifact-root flock descriptor is passed unchanged to every collector and
validator. The collector passes that same descriptor to the HOL process without
placing it in the HOL environment. Thus an uncatchable controller `SIGKILL`
does not permit a second controller while an orphaned collector or HOL process
can still write. Handled `TERM` and `HUP` terminate and wait for the active
process group before the controller releases its lock.

## Resume and result interpretation

An exit status of zero means all 130 target runs are present and revalidated;
it does not mean S1 is approved. A nonzero status stops at the first failed
target. Reinvoke the exact same command to resume. The controller never
overwrites an attempt: it retains failures or interrupted partials and assigns
the next contiguous attempt number. Before skipping any successful target on
resume, it rehashes all linked files and reruns the committed candidate
validator. A success after any unresolved manifest-order gap, a reused session
nonce, a missing target, an unexpected file, or changed evidence fails closed.

Terminal contract, success, and failure JSON is published crash-consistently.
The controller first writes and fsyncs a private pending inode, seals it
read-only, and then uses a no-overwrite hard link plus directory fsyncs to
publish the terminal name before removing the pending alias. A success or
failure pending without its terminal is retained as interrupted evidence and
is never promoted; a later run uses a new attempt. A complete pending contract
may be promoted only when its bytes exactly equal the freshly recomputed
contract. Partial contract pendings are retained and inventoried. Conflicting
terminal/pending pairs, extra hard links, symlinks, unexpected modes, duplicate
pendings, or an existing malformed terminal fail closed without overwriting
evidence. The aggregate `.receipt.json.new` and `.status.json.new` files remain
separate, regenerable snapshots rather than terminal attempt evidence.

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

Subsequent independent review and approval remain separate work. Approval
schema v2 must attach this run's exact `collection-contract.json`, closed
`receipt.json`, all 130 per-attempt `success.json` files, and their bound
collector/validator outputs in addition to the candidate/plan/request/
transcript records. These raw candidates must not be copied directly into the
Great100 manifest or treated as schema-4 Candle acceptance reports.
