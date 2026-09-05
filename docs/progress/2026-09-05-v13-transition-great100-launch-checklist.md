# v1.3 schema-7 Great 100 transition diagnostic checklist

Date: 2026-09-05

This checklist is diagnostic only.  It is valid only for the exact clean
source and final Candle heads below and only after current-head bootstrap,
ordinary schema-6 link, parser 20/400, and d0/d1 diagnostic gates have all
passed.  Nothing in this checklist can establish S1, S2, or S3.

```sh
SOURCE=/project/worktrees/candle-parser-quotation-prep-v13
FINAL=/project/worktrees/candle-post-bootstrap-integration-prep-v13
CAKEML=/project/worktrees/cakeml-flyspeck-frontend-cold-8a8926906-v13
BOOT=/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-8a8926906-419a96e37-attempt-002/bootstrap-provenance.json
TRANSITION=/project/flyspeck-candle-runs/cakeml-bootstrap-transition-419a96e-to-32fcb81-attempt-001.json
ATTEMPT=/project/flyspeck-candle-runs/great100-transition-32fcb81-attempt-001

SOURCE_HEAD=419a96e374dba147d21fc6547f7025d6d14e5ff0
FINAL_HEAD=32fcb81e0735896f290de88f394ef8f9a3356bcd
```

The transition and attempt paths were absent when this checklist was written.
Recheck that they are absent immediately before use.  Preserve any failed
attempt and advance its number; never overwrite or relabel it.

## 1. Revalidate all live authorities

Require exact clean heads, then independently revalidate the canonical source
receipt before deriving the transition:

```sh
test "$(/usr/bin/git -C "$SOURCE" rev-parse HEAD)" = "$SOURCE_HEAD"
test -z "$(/usr/bin/git -C "$SOURCE" status --porcelain=v1 --untracked-files=all)"
test "$(/usr/bin/git -C "$FINAL" rev-parse HEAD)" = "$FINAL_HEAD"
test -z "$(/usr/bin/git -C "$FINAL" status --porcelain=v1 --untracked-files=all)"
test ! -e "$TRANSITION"
test ! -L "$TRANSITION"
test ! -e "$ATTEMPT"
test ! -L "$ATTEMPT"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$SOURCE/candle/cakeml_artifact_provenance.py" \
  check-bootstrap --candle-root "$SOURCE" --cakeml-root "$CAKEML" \
  --record "$BOOT"
```

Ignored build outputs are allowed by Git status only because the linked-record
validators authenticate them separately.  Do not infer a valid compiler from
clean Git status.

## 2. Record and independently reconstruct the transition

Use the transition controller committed at the final head:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$FINAL/candle/cakeml_bootstrap_transition.py" \
  record-transition \
  --source-candle-root "$SOURCE" --source-candle-head "$SOURCE_HEAD" \
  --final-candle-root "$FINAL" --final-candle-head "$FINAL_HEAD" \
  --cakeml-root "$CAKEML" --bootstrap-record "$BOOT" \
  --write "$TRANSITION"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$FINAL/candle/cakeml_bootstrap_transition.py" \
  check-transition \
  --source-candle-root "$SOURCE" --source-candle-head "$SOURCE_HEAD" \
  --final-candle-root "$FINAL" --final-candle-head "$FINAL_HEAD" \
  --cakeml-root "$CAKEML" --bootstrap-record "$BOOT" \
  --record "$TRANSITION"
```

The transition must reconstruct byte-for-byte equality of the five bootstrap
inputs and exact CakeML/HOL pins; ancestry alone is insufficient.

## 3. Create and validate the final-head schema-7 link

The five-argument form is deliberately distinct from the ordinary link:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  "$FINAL/build-local-cakeml.sh" \
  "$CAKEML" "$BOOT" "$SOURCE" "$SOURCE_HEAD" "$TRANSITION"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$FINAL/candle/cakeml_bootstrap_transition.py" \
  check-linked --candle-root "$FINAL"
```

Require linked schema 7, promotion status
`diagnostic-only-requires-final-head-canonical-bootstrap`, transition mode
`byte-identical-canonical-bootstrap-rebinding-v1`, and exact final Candle head.
Do not run the schema-6-only provenance checker against this intentional
schema-7 link, and never copy this linked record into S1 evidence.

## 4. Run the full 65-target diagnostic

Create only the fresh parent; `regression.py` exclusively creates the report
and log directory.  Launch with a minimal controller environment.  One worker
keeps the 6000 MiB CakeML heap and resource sampling well below the project
ceiling.

```sh
/usr/bin/mkdir -m 0700 "$ATTEMPT"

(
  cd "$FINAL"
  set -o noclobber
  exec 3>"$ATTEMPT/controller.stdout"
  exec 4>"$ATTEMPT/controller.stderr"
  set +o noclobber
  status=0
  /usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
    /usr/bin/python3 -I candle/regression.py \
    --top100-transition-diagnostic -j 1 \
    --inactivity-timeout 1800 --wall-timeout 14400 \
    --json-report "$ATTEMPT/report.json" \
    --log-dir "$ATTEMPT/logs" >&3 2>&4 || status=$?
  exec 3>&-
  exec 4>&-
  /usr/bin/chmod 0444 \
    "$ATTEMPT/controller.stdout" "$ATTEMPT/controller.stderr"
  exit "$status"
)
```

A zero exit is necessary but not sufficient.  Re-run `check-linked`, require
65 PASS and zero FAIL/TIMEOUT records, rehash every transcript named by the
report, and require:

- `suite=top100-transition-diagnostic`;
- `schema=4` and `test_count=65`;
- exact `candle_git_head=$FINAL_HEAD` and clean status;
- linked schema 7 and the exact linked-record hash in every process;
- all expected theorem and post-state identities matched;
- `promotion.eligible=false` and `promotion.s1_evidence=false`; and
- `s1_evidence.suite_closed=false`.

After validation, seal ordinary report/log files to 0444 and their directories
to 0555.  Any failing target is a compatibility diagnosis to fix on a new
branch.  Even a perfect 65/65 result only authorizes freezing the final source
head and starting a fresh canonical bootstrap rooted exactly there.

## 5. Mandatory successor

The schema-7 compiler is never promoted.  The successor sequence is:

1. freeze the actual final Candle commit;
2. run a fresh canonical bootstrap using that exact Candle root/head and fresh
   external log/preflight/provenance destinations;
3. validate the receipt and perform the ordinary two-argument link;
4. require both schema-6-only and exact-root linked checks; and
5. run fresh ordinary `--top100` evidence.

Any source commit after the final-head bootstrap invalidates that compiler
authority and requires the bootstrap and ordinary link again.
