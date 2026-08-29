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

The replay controller must have written `stage=complete` and exited
successfully.  There must then be no live `Holmake` before the canonical
controller starts.

## Exact fresh output set

Use the new ordinary directory

`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-6f43450-964406486-attempt-001`

with these initially absent outputs:

- `bootstrap.log`;
- `bootstrap-preflight.json`;
- `bootstrap-provenance.json`; and
- `bootstrap-preflight.json.generated-preimage`.

The receipt parent may exist, but every named output and archive must be
absent.  The three receipts must be distinct and outside the authenticated
Candle, CakeML, and HOL4 worktrees.  The canonical controller creates the log
and two JSON receipts with non-overwriting publication and creates the archive
only when preimages need retaining.  Failed attempts are preserved and retried
under a new attempt directory; their outputs are never overwritten or reused.

## Prelaunch gate

Immediately before launch, require all of the following:

- the exact Candle, CakeML, and HOL4 heads above;
- clean tracked/index/untracked Git status in all three worktrees;
- the cold replay's `stage` file contains exactly `complete`, its
  `finished_utc` exists, and its controller is no longer live;
- the replay's four GNU-time receipts are nonempty and the four required
  output postconditions exist;
- no `Holmake` is live anywhere on the machine;
- at least 120 GiB is available at the start; and
- the attempt directory and all four externally visible outputs are absent.

The bootstrap controller performs its own stronger provenance, Git, path,
host-tool, ELF-closure, output-preimage, lock-inode, and exact-environment
checks.  The outer handoff checks do not replace those controls.

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
seconds, alert at 110 GiB aggregate replay/bootstrap RSS or below 32 GiB
`MemAvailable`, and treat the user's 120 GiB allowance as the exceptional
ceiling.  Any intervention must preserve the bootstrap transcript, preflight,
preimage archive, and partial outputs for diagnosis.

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

Only after the schema-6 link passes should the authenticated, already retained
20-file pilot plan run.  The authenticated 400-file inventory follows only if
the pilot passes.  Parser/runtime failures then feed the batch repair loop;
neither the cold replay nor bootstrap success by itself claims Flyspeck
acceptance.
