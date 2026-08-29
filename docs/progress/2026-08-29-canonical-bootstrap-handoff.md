# Canonical CakeML bootstrap handoff — 2026-08-29

## Decision

The final runtime build must use Candle
`6f4345057185214016dd7f051a0f3b503950480e`, CakeML
`964406486a52e1a53a94eade4cf86a666dc8055a`, and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  Because the canonical
bootstrap and native link both use the same final Candle commit, the link must
use the ordinary two-argument `build-local-cakeml.sh` form.  This is the
schema-6 release path documented by Candle's README.  The five-argument
bootstrap-transition form is diagnostic-only and must not be used for this
release build.

The canonical bootstrap must not start merely when
`compiler64ProgTheory.uo` finishes.  Its gate is completion of all four cold
replay stages in
`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-964406486`:

1. `cake_compile_heap`;
2. `compiler64ProgTheory.uo`;
3. `x64BootstrapTheory.uo` and its `cake.S`/`config_enc_str.txt` outputs; and
4. `x64BootstrapProofTheory.uo`.

The replay controller must have written `stage=complete` and `finished_utc`;
all four GNU-time receipts must bind the exact expected commands and record
exit status zero; and the replay PID/process group must be gone.  This is the
strongest retained terminal gate because the original launcher did not record
an independently observed Bash exit status.  There must then be no live
`Holmake` before the canonical controller starts.

## Exact fresh output set

Use the new ordinary directory

`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-6f43450-964406486-attempt-001`

with these initially absent outputs:

- `bootstrap.log`;
- `bootstrap-preflight.json`;
- `bootstrap-provenance.json`; and
- `bootstrap-preflight.json.generated-preimage`.

The base parent `/project/flyspeck-candle-runs` may exist, but the attempt
directory itself and every named output must be absent.  The attempt directory
is created exactly once immediately before launch.  The three receipts must be
distinct and outside the authenticated Candle, CakeML, and HOL4 worktrees.  The
canonical controller creates the log and two JSON receipts with non-overwriting
publication.  In this warm-after-cold run, the generated-preimage archive is
expected to be created and populated because the cold replay produced forced
outputs.  Failed attempts are preserved and retried under a new attempt
directory; their outputs are never overwritten or reused.

## Prelaunch gate

Immediately before launch, require all of the following:

- the exact Candle, CakeML, and HOL4 heads above;
- empty nonignored Git porcelain status in all three worktrees (ignored cold
  generated outputs are expected preimages, not dirtiness to delete);
- the cold replay's `stage` file contains exactly `complete`, its
  `finished_utc` exists, and its controller PID/process group are no longer
  live;
- the replay's four GNU-time receipts bind the exact commands and record exit
  status zero, and all six concrete output postconditions exist;
- no `Holmake` is live anywhere on the machine;
- at least 120 GiB is available at the start; and
- inherited CPU-time, file-size, and address-space soft limits are unlimited;
- the attempt directory and all four externally visible outputs are absent.

The bootstrap controller performs its own stronger provenance, Git, path,
host-tool, ELF-closure, output-preimage, lock-inode, and exact-environment
checks.  The outer handoff checks do not replace those controls.

The committed read-only prelaunch gate implements the outer checks.  Run it
immediately before launch and require its JSON result to contain
`"gate":"canonical-cakeml-bootstrap-ready"`:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/flyspeck-project-runtime-gates-aaeb533/scripts/check-canonical-bootstrap-gate.py \
  --project-root /project/worktrees/flyspeck-project-runtime-gates-aaeb533 \
  --project-head aaeb533d7a8c6faccedac63f1f979e74db6674b4 \
  --replay-root /project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-964406486 \
  --replay-controller-pid 2270138 \
  --replay-process-group 2270138 \
  --candle-root /project/worktrees/candle-runtime-pin-964406486 \
  --candle-head 6f4345057185214016dd7f051a0f3b503950480e \
  --cakeml-root /project/worktrees/cakeml-flyspeck-runtime-stack-v13 \
  --cakeml-head 964406486a52e1a53a94eade4cf86a666dc8055a \
  --hol4-root /project/worktrees/HOL-cakeml-dopen-v13 \
  --hol4-head a390cbabd3a4521bab4ee20281e3e42933a8a3ae \
  --attempt-root /project/flyspeck-candle-runs/cakeml-canonical-bootstrap-6f43450-964406486-attempt-001 \
  --minimum-mem-available-gib 120
```

This program is intentionally incapable of launching or repairing a build.  A
rejection leaves the transition manual and fail-closed.

## Canonical launch

After satisfying the gate, create only the fresh attempt directory and replace
the launch shell with this exact sanitized controller invocation:

```sh
run_root=/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-6f43450-964406486-attempt-001
mkdir "$run_root"
exec /usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /project/worktrees/candle-runtime-pin-964406486/build-local-cakeml-bootstrap.sh \
  /project/worktrees/cakeml-flyspeck-runtime-stack-v13 \
  /project/worktrees/HOL-cakeml-dopen-v13 \
  "$run_root/bootstrap.log" \
  "$run_root/bootstrap-preflight.json" \
  "$run_root/bootstrap-provenance.json"
```

Do not add an unrecorded `ulimit` or change the controller's command.  It
records and runs exactly `/usr/bin/time -v HOL_ROOT/bin/Holmake -j1 cake.S`
under the exact three-variable build environment.  Historical measurements
place this serial build near 72 GiB and eight hours.  Monitor it every 30
seconds, alert at 110 GiB aggregate RSS across all concurrent project
workloads or below 32 GiB `MemAvailable`, and treat the user's 120 GiB
allowance as the exceptional ceiling.  Any intervention must preserve the
bootstrap transcript, preflight, preimage archive, and partial outputs for
diagnosis.

The canonical controller handles only `SIGINT`, `SIGTERM`, and `SIGHUP` by
forwarding them to its fresh child session.  If intervention is necessary,
validate the controller PID/start time and send only a positive-PID handled
signal, preferably `SIGTERM` or `SIGINT`.  Never send controller-only
`SIGKILL` or `SIGQUIT`: either can orphan `Holmake` while releasing the
cooperative CakeML lock.  After any abnormal loss, prove both the controller
and its exact child process group absent before preserving the failed attempt
and considering a fresh attempt number.

## Link and post-link gates

On successful atomic publication of the schema-5 bootstrap provenance, with
the Candle and CakeML heads still exact, run the ordinary final-head linker:

```sh
/project/worktrees/candle-runtime-pin-964406486/build-local-cakeml.sh \
  /project/worktrees/cakeml-flyspeck-runtime-stack-v13 \
  /project/flyspeck-candle-runs/cakeml-canonical-bootstrap-6f43450-964406486-attempt-001/bootstrap-provenance.json
```

This creates ignored files under `candle/build`, including the schema-6
`cakeml-build-provenance.json`, and the ignored root aliases
`config_enc_str.txt` and `candle_boot.ml`.  The script performs its own final
`check-linked` after creating those aliases.  Re-run `check-linked` explicitly
before each retained corpus run and require the Candle tracked worktree to
remain clean.

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-runtime-pin-964406486/candle/cakeml_bootstrap_transition.py \
  check-linked \
  --candle-root /project/worktrees/candle-runtime-pin-964406486
```

Only after the schema-6 link passes should the authenticated, already retained
20-file pilot plan run.  The authenticated 400-file inventory follows only if
the pilot passes.  Parser/runtime failures then feed the batch repair loop;
neither the cold replay nor bootstrap success by itself claims Flyspeck
acceptance.

## Exact retained parser sequence

The retained plans bind Candle `6f43450` and Flyspeck `1ce0353`; they are valid
only while those exact authority trees remain clean and unchanged.  Their
published identities are:

- pilot plan SHA-256
  `599f1bad0bd69e6dce39608d7a8ff90fda9ae5e02e3cf739e04ad8fffa1ed5b3`
  and host-materialization SHA-256
  `518e3d4f93df4ebd636e7c92bfc3d19477a623faa80b61c08096ca77eeff895c`;
- all-inventory plan SHA-256
  `816f847dd52331f0c93c9d0ffae6e2c53ebaf25a8757498277f187c0454962fd`
  and host-materialization SHA-256
  `b3eee598a7a820654062638d516880577808886022944c6145aacfc548836242`.

Run the pilot first, using an absent result root and the controller's explicit
per-process limits:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-runtime-pin-964406486/candle/flyspeck_parser_diagnostic.py \
  run \
  --profile pilot \
  --plan-root /project/flyspeck-candle-runs/parser-pilot-materialization-6f43450 \
  --candle-root /project/worktrees/candle-runtime-pin-964406486 \
  --candle-head 6f4345057185214016dd7f051a0f3b503950480e \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  --output-root /project/flyspeck-candle-runs/parser-pilot-result-6f43450-attempt-001 \
  --timeout-seconds 600 \
  --max-cpu-seconds 600 \
  --max-address-space-gib 16 \
  --max-output-mib 1
```

Require the aggregate published outcome to be `parse-pass`, the attempt count
to be exactly 20, and every individual attempt outcome to be `parse-ok`.  A
published `parse-failure` is retained diagnostic evidence, not a passing
command merely because the controller itself exited normally.  Only a complete
pilot pass permits the corresponding 400-input run:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-runtime-pin-964406486/candle/flyspeck_parser_diagnostic.py \
  run \
  --profile all-inventory \
  --plan-root /project/flyspeck-candle-runs/all-inventory-materialization-6f43450 \
  --candle-root /project/worktrees/candle-runtime-pin-964406486 \
  --candle-head 6f4345057185214016dd7f051a0f3b503950480e \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  --output-root /project/flyspeck-candle-runs/parser-all-inventory-result-6f43450-attempt-001 \
  --timeout-seconds 600 \
  --max-cpu-seconds 600 \
  --max-address-space-gib 16 \
  --max-output-mib 1
```

The controller launches inputs serially, one fresh parser process per input,
and seals one authenticated runtime image for the run.  These 16 GiB limits
apply independently to each parser process; the 120 GiB bootstrap exception is
neither needed nor inherited.  Preserve every result root.  If either profile
reports failures, classify the complete ordered failure set before changing
code and rematerialize both plans after any committed Candle authority change.

The per-input 600-second wall limit implies conservative worst cases of about
3.3 hours for 20 attempts and 66.7 hours for 400 attempts, plus the capability
handshake and snapshot publication.  Actual parser-only times should be far
smaller and must be measured from the pilot before estimating the 400-file run.
Do not terminate a parser controller with controller-only `SIGTERM`, `SIGHUP`,
or `SIGKILL`, because its current child owns a fresh session.  Prefer a
verified controller `SIGINT`, whose stack unwinding reaches child-process-group
cleanup, and confirm that child session is gone before any retry.

Published result trees are mode-0555/mode-0444 but are not immutable against
the same user.  Before a retained result is consumed, an independent
consumer-side validation must revalidate the ordinary-file/mode closure,
closed snapshot and transcript inventory, current plan/profile and linked
schema-6 authority, top-level `outcome == "parse-pass"`, exact attempt count,
and every individual `outcome == "parse-ok"`.  A top-level JSON string or
controller exit status alone is never an acceptance gate.  Run the committed
consumer immediately after the pilot, then again for any later consumption:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/flyspeck-project-runtime-gates-aaeb533/scripts/check-published-parser-result.py \
  --project-root /project/worktrees/flyspeck-project-runtime-gates-aaeb533 \
  --project-head aaeb533d7a8c6faccedac63f1f979e74db6674b4 \
  --profile pilot \
  --plan-root /project/flyspeck-candle-runs/parser-pilot-materialization-6f43450 \
  --result-root /project/flyspeck-candle-runs/parser-pilot-result-6f43450-attempt-001 \
  --candle-root /project/worktrees/candle-runtime-pin-964406486 \
  --candle-head 6f4345057185214016dd7f051a0f3b503950480e \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53
```

Require its exact `published-parser-result-pass` gate before the pilot
authorizes the 400-input run.  Revalidate the 400-input result with the exact
corresponding command:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/flyspeck-project-runtime-gates-aaeb533/scripts/check-published-parser-result.py \
  --project-root /project/worktrees/flyspeck-project-runtime-gates-aaeb533 \
  --project-head aaeb533d7a8c6faccedac63f1f979e74db6674b4 \
  --profile all-inventory \
  --plan-root /project/flyspeck-candle-runs/all-inventory-materialization-6f43450 \
  --result-root /project/flyspeck-candle-runs/parser-all-inventory-result-6f43450-attempt-001 \
  --candle-root /project/worktrees/candle-runtime-pin-964406486 \
  --candle-head 6f4345057185214016dd7f051a0f3b503950480e \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53
```

The consumer stable-reads and Git-blob
authenticates the committed Candle
controller, independently reconstructs the current plan authority, holds the
linked-runtime lock, requires ordinary schema 6, rebuilds the canonical
receipt, and rehashes the complete published tree through pinned directory
descriptors.  Both executable gates come from the separate clean authority
worktree at exact project commit `aaeb533d7a8c6faccedac63f1f979e74db6674b4`;
they reject authority-head, committed-blob, dirty-status, symlink, active
graft, or replacement-ref drift before returning a pass.

Finally, the schema-5 canonical bootstrap receipt does not incorporate these
cold replay logs or `x64BootstrapProofTheory.uo`; the cold replay remains a
separate operational proof gate.  It also authenticates `cake_compile_heap` as
an input rather than independently rederiving it.  No bootstrap or parser
receipt should be described as attesting those separate derivations.
