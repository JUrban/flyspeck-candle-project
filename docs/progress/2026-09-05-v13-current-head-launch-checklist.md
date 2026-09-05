# v1.3 current-head post-bootstrap launch checklist

Date: 2026-09-05

This checklist is valid only for the exact source authorities below.  It is a
post-bootstrap operator handoff, not evidence that any command has run.  Do
not start at step 2 until canonical bootstrap attempt 002 exits zero and step
1 accepts the final immutable receipt.

```sh
CANDLE=/project/worktrees/candle-parser-quotation-prep-v13
CAKEML=/project/worktrees/cakeml-flyspeck-frontend-cold-8a8926906-v13
FLYSPECK=/project/worktrees/flyspeck-v13-source
PROJECT=/project/worktrees/flyspeck-project-parser-result-consumer-v2
BOOT=/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-8a8926906-419a96e37-attempt-002

CANDLE_HEAD=419a96e374dba147d21fc6547f7025d6d14e5ff0
CAKEML_HEAD=8a8926906ec97204eeec961496d191103cda3229
HOL4_HEAD=a390cbabd3a4521bab4ee20281e3e42933a8a3ae
FLYSPECK_HEAD=1ce0353008eba83d3c76ae9a25c3c242e4802d53
PROJECT_HEAD=642ad428487e3dfe5d3f146cc141c7bbfc856a7a
PLAN=/project/flyspeck-candle-runs/v13-stratum-plan-419a96e-attempt-002
PLAN_SHA256=310cb1961a4dd2a5e902f1c87baa7f54f51093fa5624139cd62221cbcf573c98
```

Every root must be an exact absolute path, every Git worktree must be clean at
the named head, and every output destination must still be absent immediately
before its command.  A rejected or partially published attempt is retained
and followed by a new attempt number; it is never overwritten or reused.

## 1. Validate the canonical receipt

After the controller exits zero and publishes `bootstrap-provenance.json`:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/cakeml_artifact_provenance.py" \
  check-bootstrap --candle-root "$CANDLE" --cakeml-root "$CAKEML" \
  --record "$BOOT/bootstrap-provenance.json"
```

The final provenance and log modes/hashes must match the controller contract;
mere process exit is insufficient.

## 2. Create and validate the ordinary schema-6 link

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  "$CANDLE/build-local-cakeml.sh" \
  "$CAKEML" "$BOOT/bootstrap-provenance.json"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/cakeml_artifact_provenance.py" \
  check-linked --candle-root "$CANDLE"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/cakeml_bootstrap_transition.py" \
  check-linked --candle-root "$CANDLE"
```

The first checker is deliberately schema-6-only.  The transition dispatcher
also accepts diagnostic schema 7 and therefore cannot replace it.

## 3. Run and independently consume the 20-input parser pilot

```sh
PILOT_PLAN=/project/flyspeck-candle-runs/parser-pilot-materialization-419a96e-attempt-001
PILOT_RESULT=/project/flyspeck-candle-runs/parser-pilot-result-419a96e-attempt-001

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/flyspeck_parser_diagnostic.py" \
  materialize --profile pilot --candle-root "$CANDLE" \
  --flyspeck-root "$FLYSPECK" --output-root "$PILOT_PLAN"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/cakeml_artifact_provenance.py" \
  check-linked --candle-root "$CANDLE"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/flyspeck_parser_diagnostic.py" run \
  --profile pilot --plan-root "$PILOT_PLAN" \
  --candle-root "$CANDLE" --candle-head "$CANDLE_HEAD" \
  --flyspeck-root "$FLYSPECK" --flyspeck-head "$FLYSPECK_HEAD" \
  --timeout-seconds 7200 --max-cpu-seconds 7200 \
  --max-address-space-gib 16 --max-output-mib 1 \
  --cml-heap-size-mib 4096 --output-root "$PILOT_RESULT"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$PROJECT/scripts/check-published-parser-result.py" \
  --project-root "$PROJECT" --project-head "$PROJECT_HEAD" \
  --profile pilot --plan-root "$PILOT_PLAN" --result-root "$PILOT_RESULT" \
  --candle-root "$CANDLE" --candle-head "$CANDLE_HEAD" \
  --flyspeck-root "$FLYSPECK" --flyspeck-head "$FLYSPECK_HEAD"
```

Require exact `gate=published-parser-result-pass`, `attempt_count=20`, and
`outcome=parse-pass` before the all-inventory run.

## 4. Run and independently consume all 400 parser inputs

```sh
ALL_PLAN=/project/flyspeck-candle-runs/all-inventory-materialization-419a96e-attempt-001
ALL_RESULT=/project/flyspeck-candle-runs/parser-all-inventory-result-419a96e-attempt-001

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/flyspeck_parser_diagnostic.py" \
  materialize --profile all-inventory --candle-root "$CANDLE" \
  --flyspeck-root "$FLYSPECK" --output-root "$ALL_PLAN"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/cakeml_artifact_provenance.py" \
  check-linked --candle-root "$CANDLE"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/flyspeck_parser_diagnostic.py" run \
  --profile all-inventory --plan-root "$ALL_PLAN" \
  --candle-root "$CANDLE" --candle-head "$CANDLE_HEAD" \
  --flyspeck-root "$FLYSPECK" --flyspeck-head "$FLYSPECK_HEAD" \
  --timeout-seconds 7200 --max-cpu-seconds 7200 \
  --max-address-space-gib 24 --max-output-mib 1 \
  --cml-heap-size-mib 16384 --output-root "$ALL_RESULT"

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$PROJECT/scripts/check-published-parser-result.py" \
  --project-root "$PROJECT" --project-head "$PROJECT_HEAD" \
  --profile all-inventory --plan-root "$ALL_PLAN" --result-root "$ALL_RESULT" \
  --candle-root "$CANDLE" --candle-head "$CANDLE_HEAD" \
  --flyspeck-root "$FLYSPECK" --flyspeck-head "$FLYSPECK_HEAD"
```

Require exact `attempt_count=400`.  The consumer at project head
`642ad42` binds the two profiles separately, including their exact
`runtime_environment`; an older consumer must not be substituted.

## 5. Run and independently consume direct d0, then d1

The producer requires Python `utf8_mode=1` and therefore uses `LC_ALL=C`.
The independent consumer requires `utf8_mode=0` and therefore uses
`LC_ALL=C.UTF-8`.  The historical handoff's `C.UTF-8` producer command is not
valid for the current runner.

Immediately before each producer attempt, repeat the schema-6-only
`cakeml_artifact_provenance.py check-linked` command from step 2.  For d0:

```sh
D0=/project/flyspeck-candle-runs/v13-stratum-d0-419a96e-attempt-001

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S "$CANDLE/candle/flyspeck_stratum_runtime.py" \
  --candle-script "$CANDLE/candle.sh" --plan-root "$PLAN" \
  --boundary d0-diagnostic-through-002 --write "$D0" \
  --timeout 86400 --max-cpu-seconds 86400 \
  --max-address-space-gib 48 --max-output-file-gib 8 \
  --cml-heap-size-mib 4096 --evidence-schema 5

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C.UTF-8 \
  /usr/bin/python3 -I -S "$PROJECT/scripts/check-published-direct-result.py" \
  --project-root "$PROJECT" --project-head "$PROJECT_HEAD" \
  --plan-root "$PLAN" --plan-sha256 "$PLAN_SHA256" --result-root "$D0" \
  --boundary d0-diagnostic-through-002 \
  --candle-root "$CANDLE" --candle-head "$CANDLE_HEAD" \
  --cakeml-head "$CAKEML_HEAD" --hol4-head "$HOL4_HEAD" \
  --flyspeck-root "$FLYSPECK" --flyspeck-head "$FLYSPECK_HEAD" \
  --timeout-seconds 86400 --max-cpu-seconds 86400 \
  --max-address-space-gib 48 --max-output-file-gib 8 \
  --cml-heap-size 4096 --evidence-schema 5
```

Require the exact published-result pass with `scheduling_authority=false`.
That diagnostic pass is the operator gate for d1, not direct scheduling
authority.  Repeat with fresh root
`/project/flyspeck-candle-runs/v13-stratum-d1-419a96e-attempt-001` and boundary
`d1-diagnostic-through-018`.  Consume d1 with the same exact substitutions.
Only both accepted diagnostics can authorize preparation for ordinary
boundary `00-base-through-029`; neither result is S2/S3 evidence.

All six named parser/d0/d1 attempt-001 roots were verified absent when this
checklist was written.  Their absence must be checked again immediately before
use.
