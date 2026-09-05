# v1.3 final-head canonical bootstrap and S1 launch checklist

Date: 2026-09-05

This is a future operator handoff, not evidence that any command has run.  It
is valid only after the current-head parser 20/400 and d0/d1 gates pass and the
schema-7 Great 100 transition diagnostic completes.  The final Candle head
must remain exactly frozen throughout this checklist.

```sh
PROJECT=/project/worktrees/flyspeck-project-candle-repin-prep-v13
REPLAY=/project/flyspeck-candle-runs/cakeml-frontend-cold-8a8926906-attempt-001
FINAL=/project/worktrees/candle-post-bootstrap-integration-prep-v13
CAKEML=/project/worktrees/cakeml-flyspeck-frontend-cold-8a8926906-v13
HOL4=/project/worktrees/HOL-cakeml-dopen-v13

PROJECT_HEAD=e325a3ef6b0cd4e88bcdbf432de170d967364fa3
FINAL_HEAD=32fcb81e0735896f290de88f394ef8f9a3356bcd
CAKEML_HEAD=8a8926906ec97204eeec961496d191103cda3229
HOL4_HEAD=a390cbabd3a4521bab4ee20281e3e42933a8a3ae
REPLAY_PID=1211468
REPLAY_PGID=1211468
REPLAY_START_TICKS=367911279
TERMINAL_SHA256=4a32ffc23f1c78410efaf3236722bc824fd57f48b044d6ec5bdb74a4c14d078d

ATTEMPT=/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-8a8926906-32fcb81e-attempt-001
GATE=/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-8a8926906-32fcb81e-attempt-001.gate.json
S1=/project/flyspeck-candle-runs/great100-ordinary-32fcb81e-attempt-001
```

The project root is intentionally the restored historical gate worktree,
whereas `FINAL` is the final Candle source authority.  Do not substitute the
report worktree for `PROJECT`.  Every named Git worktree must be clean at its
exact head.  Every output destination must be absent immediately before its
producer.  Preserve any rejected or partial attempt and advance its attempt
number; never overwrite or relabel it.

## 1. Revalidate frozen authorities and fresh destinations

Run this only after all earlier gates are retained and no Holmake process is
live:

```sh
test "$(/usr/bin/git -C "$PROJECT" rev-parse HEAD)" = "$PROJECT_HEAD"
test -z "$(/usr/bin/git -C "$PROJECT" status --porcelain=v1 --untracked-files=all)"
test "$(/usr/bin/git -C "$FINAL" rev-parse HEAD)" = "$FINAL_HEAD"
test -z "$(/usr/bin/git -C "$FINAL" status --porcelain=v1 --untracked-files=all)"
test "$(/usr/bin/git -C "$CAKEML" rev-parse HEAD)" = "$CAKEML_HEAD"
test "$(/usr/bin/git -C "$HOL4" rev-parse HEAD)" = "$HOL4_HEAD"
test "$(/usr/bin/sha256sum "$REPLAY/terminal-manifest.json" | /usr/bin/awk '{print $1}')" = "$TERMINAL_SHA256"
test ! -e "$ATTEMPT" && test ! -L "$ATTEMPT"
test ! -e "$GATE" && test ! -L "$GATE"
test ! -e "$S1" && test ! -L "$S1"
test -z "$(/usr/bin/pgrep -x Holmake || true)"
```

CakeML and HOL4 contain authenticated ignored build products and therefore are
not judged by Git status alone.  The gate and bootstrap controller bind their
full expected retained/generated inventories.

## 2. Publish the final-head bootstrap gate receipt

The gate requires at least 120 GiB `MemAvailable`, which is the exceptional
ceiling authorized for this phase, and revalidates the completed cold replay,
its dead controller identity and process group, the historical source bytes,
all exact Git heads, inherited resource limits, and absence of every live
Holmake process.

```sh
set -o noclobber
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$PROJECT/scripts/check-canonical-bootstrap-gate.py" \
  --project-root "$PROJECT" --project-head "$PROJECT_HEAD" \
  --replay-root "$REPLAY" \
  --replay-controller-pid "$REPLAY_PID" \
  --replay-process-group "$REPLAY_PGID" \
  --replay-controller-start-ticks "$REPLAY_START_TICKS" \
  --terminal-manifest-sha256 "$TERMINAL_SHA256" \
  --candle-root "$FINAL" --candle-head "$FINAL_HEAD" \
  --cakeml-root "$CAKEML" --cakeml-head "$CAKEML_HEAD" \
  --hol4-root "$HOL4" --hol4-head "$HOL4_HEAD" \
  --attempt-root "$ATTEMPT" --minimum-mem-available-gib 120 >"$GATE"
set +o noclobber
/usr/bin/chmod 0444 "$GATE"
```

Require exact `gate=canonical-cakeml-bootstrap-ready`, the four named heads,
the replay identity and terminal digest above, `attempt_root=$ATTEMPT`, no live
Holmake/replay members, and unlimited inherited CPU/file-size/address-space
soft limits.  A zero exit or an existing output file alone is insufficient.

## 3. Run the exact final-head canonical bootstrap

Create only the fresh attempt directory.  The controller exclusively creates
the three output files, archives the exact generated preimage, and on success
publishes immutable preflight, log, and provenance records.

```sh
/usr/bin/mkdir -m 0700 "$ATTEMPT"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  "$FINAL/build-local-cakeml-bootstrap.sh" \
  "$CAKEML" "$HOL4" \
  "$ATTEMPT/bootstrap.log" \
  "$ATTEMPT/bootstrap-preflight.json" \
  "$ATTEMPT/bootstrap-provenance.json"
```

Do not modify or clean CakeML/HOL4 after a failure.  Retain the complete
attempt and gate receipt and diagnose it in place before assigning a fresh
attempt number.

## 4. Validate and create the ordinary schema-6 link

After the bootstrap controller exits zero:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$FINAL/candle/cakeml_artifact_provenance.py" \
  check-bootstrap --candle-root "$FINAL" --cakeml-root "$CAKEML" \
  --record "$ATTEMPT/bootstrap-provenance.json"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  "$FINAL/build-local-cakeml.sh" \
  "$CAKEML" "$ATTEMPT/bootstrap-provenance.json"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$FINAL/candle/cakeml_artifact_provenance.py" \
  check-linked --candle-root "$FINAL"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$FINAL/candle/cakeml_bootstrap_transition.py" \
  check-linked --candle-root "$FINAL"
```

Both linked checks must accept the ordinary exact-root schema-6 record.  The
earlier schema-7 transition compiler is diagnostic only and must not survive
as the linked authority for S1.

## 5. Run ordinary Great 100 S1 evidence

The committed approval is currently approved for all 65 targets, but the live
runner must independently reauthenticate it and match every observed identity.
Use one worker and the same bounded per-target deadlines as the transition
diagnostic.

```sh
/usr/bin/mkdir -m 0700 "$S1"

(
  cd "$FINAL"
  set -o noclobber
  exec 3>"$S1/controller.stdout"
  exec 4>"$S1/controller.stderr"
  set +o noclobber
  status=0
  /usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
    /usr/bin/python3 -I candle/regression.py \
    --top100 -j 1 \
    --inactivity-timeout 1800 --wall-timeout 14400 \
    --json-report "$S1/report.json" \
    --log-dir "$S1/logs" >&3 2>&4 || status=$?
  exec 3>&-
  exec 4>&-
  /usr/bin/chmod 0444 "$S1/controller.stdout" "$S1/controller.stderr"
  exit "$status"
)
```

A zero exit is necessary but not sufficient.  Re-run both linked checkers,
rehash every retained transcript named by the report, and require:

- `suite=top100`, schema 4, and exactly 65 ordered targets;
- exact clean `candle_git_head=$FINAL_HEAD`;
- linked schema 6 and one identical linked-record hash in every process;
- 65 PASS with no FAIL, timeout, skip, stale identity, or mismatch;
- all 65 approved theorem and post-state identities matched exactly;
- `promotion.eligible=true` and `promotion.s1_evidence=true`; and
- `s1_evidence.suite_closed=true`.

Seal ordinary report/log files to mode 0444 and their directories to 0555 only
after those checks pass.  S1 authorizes the cumulative direct-source strata;
it is not S2 or S3 and does not authorize PFT evidence as a substitute.
