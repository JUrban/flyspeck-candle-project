# Great100 schema-v9 CSDP two-sweep runbook

This is a new collection contract.  It must not resume or append to
`s1-reference-v8-two-sweep-a0e072f-b142b0b`: that schema-v8 root retains its
nine successful target runs and its CSDP-missing failure as historical
evidence.  Schema v9 starts at sweep 1, target 1 in a new mode-0700 root.

The selected executable project commit is
`95bb84fffade845406af92305baea0a9686ef21f`; the selected Candle commit is
`652a18a6735be8969462bf25f3233d23b5a4ed6d`.  Create clean detached worktrees
at those exact commits before launch, for example:

```sh
git -C /project/flyspeck-candle-project worktree add --detach \
  /project/worktrees/flyspeck-project-reference-v9-launch-95bb84f \
  95bb84fffade845406af92305baea0a9686ef21f
git -C /project/repos/candle worktree add --detach \
  /project/worktrees/candle-reference-v9-launch-652a18a \
  652a18a6735be8969462bf25f3233d23b5a4ed6d
```

Do not launch from either development branch.  Recheck both frozen worktrees
are clean, have no grafts or replacement refs, and have no assume-unchanged or
skip-worktree entries.  The controller repeats these checks and fails closed.

The staged CSDP 6.2.0 binary was independently rebuilt with the receipt's
single-thread flags.  The rebuilt `libsdp.a` SHA-256 was
`ede58dd5bf3620aa08045aa767fd1280fefe1e76d6ece276e8a674d6156bca25`;
the rebuilt solver was byte-identical to the staged executable at SHA-256
`50a07f934ffac42b774e0991ff5e44cc68a6d8db180258a8fc1d1676cc7e898d`.
The theta1 probe succeeds with equal `2.3000000e+01` objectives and produces
the deterministic solution SHA-256
`2f1d7f430b48eddbe1279d955a5f11f2aaa9a9aace90338b846aef742ea4487f`.
The observed ELF closure contains reference BLAS/LAPACK and no OpenMP,
OpenBLAS, or pthread runtime; the runtime environment also caps the standard
thread controls at one.  Both the Candle-side collector and project-side
controller require the receipt's exact source-package claim, eight-field
toolchain, ordered commands, CFLAGS, library flags, static `libsdp.a` digest,
solver identity, probe, and runtime policy; missing fields, alternative values,
and boolean/integer type confusion fail closed.

After independent review, create a new empty root and invoke exactly:

```sh
mkdir -m 700 /project/flyspeck-candle-runs/s1-reference-v9-csdp-two-sweep-652a18a-95bb84f

PROJECT_ROOT=/project/worktrees/flyspeck-project-reference-v9-launch-95bb84f

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C LANG=C \
 /usr/bin/python3 -I -S \
 "$PROJECT_ROOT/scripts/run-top100-reference-sweeps.py" \
  --artifact-root /project/flyspeck-candle-runs/s1-reference-v9-csdp-two-sweep-652a18a-95bb84f \
  --project-root "$PROJECT_ROOT" \
  --project-head 95bb84fffade845406af92305baea0a9686ef21f \
  --controller-sha256 a703c01f1153bd8774f2f1ab4342950469011cbfee6d7f605485cc71d87f6301 \
  --python-sha256 1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118 \
  --git-sha256 2a8c18fbf43da9f692d75474c72bea9dfd796c260b0f3dfe456376abc3bbd668 \
  --candle-root /project/worktrees/candle-reference-v9-launch-652a18a \
  --candle-head 652a18a6735be8969462bf25f3233d23b5a4ed6d \
  --manifest-sha256 e021a1f11d2307ca65c29eb6ab56fc04e5f4be2dbc4f7702f63ad3e1b7bfdae9 \
  --collector-sha256 f91d1fdb6314938b8b9f88a641364059e4a20812acf805ce87d96ef12468355a \
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
  --pari-gp-root /project/deps/hol-light-external-tools-v9 \
  --pari-gp-sha256 c9673623cad2eaa7cfe402e7b7d833f1f703689a09837026b6386aaafba6deec \
  --csdp-sha256 50a07f934ffac42b774e0991ff5e44cc68a6d8db180258a8fc1d1676cc7e898d \
  --pari-gp-package /project/deps/apt-noble-pari/packages/pari-gp_2.15.4-2.1build1_amd64.deb \
  --pari-gp-package-sha256 55a95d51afe87688fe0fcfe1bca74bf8c5474533e2a42d3af45c87c1ae0d86fa \
  --pari-gp-gprc-sha256 473ec0c27f514013b7a1ae2442fbe8e46046df58e6a0be590ea17a03873fc6b1 \
  --pari-gp-tree-sha256 84bd5e8b1a8e1c253cc2c45fd19fafaa22b7f6ea5109a646631b5f2b10bb7732 \
  --pari-gp-data-tree-sha256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 \
  --csdp-source /project/deps/hol-light-external-tools-v9/candle-csdp-source.tar.gz \
  --csdp-source-sha256 7f202a15f33483ee205dcfbd0573fdbd74911604bb739a04f8baa35f8a055c5b \
  --csdp-build-receipt /project/deps/hol-light-external-tools-v9/candle-csdp-build.json \
  --csdp-build-receipt-sha256 530b7d8c93574e188045277e484cbe2a40c634a3ae0b6cc24240aff2bf726b22 \
  --csdp-probe-input /project/deps/hol-light-external-tools-v9/candle-csdp-theta1.dat-s \
  --csdp-probe-input-sha256 0529ef48291c872fa1edd1e3b6ba4da3364377c613756c496b6fefd2afed2173 \
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

The selected inputs reconstruct a 40,231-byte canonical schema-4 contract,
canonical-file SHA-256
`8270f75b348fe166bde87804b628e92974cac4bc5e43f8400be958beb699e3d7`,
and compact semantic SHA-256
`9ce6adff5a24f9634180232351e41fd170a2ed9cdfe3a57d8ea80d9949d2bf66`.
They cover 65 targets, 66 sources, 97 theorem requests, and 130 target runs.
Reinvocation is permitted only with the byte-identical command and root.  A
changed pin or contract requires another new root.

The two frozen worktrees named above were created and checked clean.  At the
time this launch section was written, no v9 artifact root had been created.
The exact run was subsequently launched at
`/project/flyspeck-candle-runs/s1-reference-v9-csdp-two-sweep-652a18a-95bb84f`;
it must be resumed only by its existing controller and must not be relaunched
from this command block.
