# Great100 schema-v8 reference two-sweep runbook

This runbook controls collection of two independent, sequential schema-v8
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
  `/project/worktrees/candle-v13-integrated-launch-a0e072f` at
  `a0e072ff4ad8ec4fbc660052ad860c5e01d681a5`;
- `candle/top100_manifest.json` SHA-256
  `e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9`;
- `candle/reference_fingerprints.py` SHA-256
  `272556af3b7b4e3db03f4e243241c19cc0d13ddd144171b3b0c5938f48bcfcb4`;
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
- the authenticated ELF observer route `/bin/bash`, SHA-256
  `bc5945feb8bd26203ebfafea5ce1878bb2e32cb8fb50ab7ae395cfb1e1aaaef1`,
  and `/usr/bin/ldd`, SHA-256
  `4f1d37e25f27535e3f02a5b7da63e1ce18d4982445db2c25fc8f985a3d395cc3`;
- the dynamic-loader cache `/etc/ld.so.cache`, SHA-256
  `0971c6dfbc46998c25774d855b34d8494d78988f90221eb5fe5aa8816203fca1`,
  and the sole present reviewed hardcoded loader route, SHA-256
  `cd4df4f3c7b83673d61189bf2eaebd33ca4f2853ab9772b8a25e025ef99b1e81`;
- `/etc/ld.so.preload` is absent. Its appearance is a hard failure;
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
mismatch, changed ELF observer/loader/cache/preload state, or changed retained
collection contract is a hard failure, not a
reason to update an in-progress artifact root.

## Invocation

Create a new empty ordinary directory, owned by the invoking effective user
with mode exactly `0700`, on an evidence volume outside all three Git
repositories. Do not reuse a directory from another collection contract.
Set the three project values below to literals from the independently reviewed,
clean project checkout; do not derive or change them inside the controller
invocation.

```sh
mkdir -m 700 /project/flyspeck-candle-runs/s1-reference-v8-two-sweep-a0e072f-b142b0b

PROJECT_ROOT=/project/worktrees/flyspeck-project-s1-gp-v8-launch-b142b0b
PROJECT_HEAD=b142b0b6191b1af8b93f79275b6a873b63730d87
CONTROLLER_SHA256=3dd8891eb77ca6636b2d01168a52096518f9de0dda3412fd520cb46bdbaac000

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C LANG=C \
 /usr/bin/python3 -I -S \
 "$PROJECT_ROOT/scripts/run-top100-reference-sweeps.py" \
  --artifact-root /project/flyspeck-candle-runs/s1-reference-v8-two-sweep-a0e072f-b142b0b \
  --project-root "$PROJECT_ROOT" \
  --project-head "$PROJECT_HEAD" \
  --controller-sha256 "$CONTROLLER_SHA256" \
  --python-sha256 1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118 \
  --git-sha256 2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668 \
  --candle-root /project/worktrees/candle-v13-integrated-launch-a0e072f \
  --candle-head a0e072ff4ad8ec4fbc660052ad860c5e01d681a5 \
  --manifest-sha256 e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9 \
  --collector-sha256 272556af3b7b4e3db03f4e243241c19cc0d13ddd144171b3b0c5938f48bcfcb4 \
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
  --elf-bash-sha256 bc5945feb8bd26203ebfafea5ce1878bb2e32cb8fb50ab7ae395cfb1e1aaaef1 \
  --elf-ldd-sha256 4f1d37e25f27535e3f02a5b7da63e1ce18d4982445db2c25fc8f985a3d395cc3 \
  --elf-cache-sha256 0971c6dfbc46998c25774d855b34d8494d78988f90221eb5fe5aa8816203fca1 \
  --elf-loader-sha256 cd4df4f3c7b83673d61189bf2eaebd33ca4f2853ab9772b8a25e025ef99b1e81 \
  --collection-wall-seconds 21600 \
  --target-wall-seconds 21660 \
  --validation-wall-seconds 900
```

Two isolated read-only reconstructions from these exact inputs produced the
same 32,994-byte canonical contract. Its canonical-file SHA-256 is
`5dea7bd7a299509e876b39fff61c9cf6a8bfbca458395848ace0e1d0a40414c8`;
the compact semantic contract SHA-256 recorded in the aggregate receipt is
`76d8ab6eecbaf31be3ce926b06759aba30b3cf6f8d35d313699a5b0d958cb7b5`.
The reconstructed inventory is exactly 65 targets, 66 sources, 97 theorem
requests, and 130 target runs. A different published contract is a hard
failure.

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

`collection-contract.json` records the input identities and deadlines. Schema
v8 additionally retains each raw `/bin/bash /usr/bin/ldd` observation, accepts
only recognized output lines, normalizes only ASLR address tokens, and binds
the exact sorted dependency union. Finalization replays that closure live with
the captured committed validator and archives the observer tools, loader,
cache, requested roots, and every discovered ELF object. It also authenticates
the collection controller against this exact project head, checks the exact
reference Git parent and three reviewed deltas, archives and compares all 66
committed source blobs to the live checkout, and uses the captured validator's
real plan builder to reconstruct the interpreter, `hol.ml`, boot files,
OCaml/findlib trees, complete stub set, GP runtime, fresh-process contract, and
both ELF closures. Every one of the 130 plans must have the same stable runtime
projection while retaining its independently checked target/source/request
bindings.
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
