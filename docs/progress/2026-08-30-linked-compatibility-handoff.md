# Linked Candle compatibility handoff — 2026-08-30

## Scope and order

This is the exact post-link compatibility sequence for Candle
`688d9d1738a7021501f95b6f0ed788e014fa726f` and Flyspeck
`1ce0353008eba83d3c76ae9a25c3c242e4802d53`, using CakeML
`964406486a52e1a53a94eade4cf86a666dc8055a` and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  It is deliberately downstream of
all of these gates:

1. the four-stage cold CakeML/HOL4 proof replay;
2. the independently checked canonical-bootstrap prelaunch gate;
3. the canonical same-head bootstrap and ordinary schema-6 link;
4. the retained 20-file parser pilot and its independent consumer; and
5. the retained 400-file parser inventory and its independent consumer.

Do not use this sequence to skip or replace those gates.  Do not run it
concurrently with a build, parser controller, direct Flyspeck controller, or
another compiled Candle workload in the same Candle worktree.  Stop at the
first failure and preserve the partial result root.  A passing compatibility
run is regression evidence; it is not S1, S2, or S3 evidence and does not
replace the cumulative direct-source run.

The sequence reuses the authenticated, read-only current-head inputs:

- normalization overlay
  `/project/flyspeck-candle-runs/v13-normalized-overlay-688d9d1`, contract
  SHA-256 `491ca5a204e15fde5454faf63a42343f5cf4a281e03b8b212c937013b992de7e`;
- generated inputs
  `/project/flyspeck-candle-runs/v13-generated-lp-688d9d1`, contract SHA-256
  `dc9f9e5d60b3b43a1275a450e643bb1d8ce4843d517cdf4d84a6dc5c318a8816`;
- OCaml 4.14.1 oracle executable `/usr/bin/ocaml`, SHA-256
  `9d4cb9f47b9d44cab338f29323ada69aec3728eb48f9039b0148c02690484306`;
  and
- linked launcher
  `/project/worktrees/candle-runtime-pin-964406486/candle.sh`.

The expected `test_flyspeck_loader_frontier.sh` result is a successful test
whose final message says that execution stopped at the verified Dopen
frontier.  That diagnostic cutpoint is intentionally nonpromotable.  The
following Dopen-prefix test then checks the accepted two-file direct-source
prefix.  Neither result should be relabelled as full-loader acceptance.

## Exact retained run

Use the fresh root
`/project/flyspeck-candle-runs/linked-compatibility-688d9d1-attempt-001`.
If an attempt fails, retain it and increment the attempt number; never delete,
overwrite, or reuse it.  Run this block only after the downstream conditions
above are true:

```sh
/usr/bin/env -i \
  PATH=/usr/bin:/bin \
  LC_ALL=C \
  /usr/bin/bash --noprofile --norc <<'COMPATIBILITY_RUN'
set -euo pipefail

candle_root=/project/worktrees/candle-runtime-pin-964406486
candle_head=688d9d1738a7021501f95b6f0ed788e014fa726f
cakeml_root=/project/worktrees/cakeml-flyspeck-runtime-stack-v13
cakeml_head=964406486a52e1a53a94eade4cf86a666dc8055a
hol4_root=/project/worktrees/HOL-cakeml-dopen-v13
hol4_head=a390cbabd3a4521bab4ee20281e3e42933a8a3ae
flyspeck_root=/project/worktrees/flyspeck-v13-source
flyspeck_head=1ce0353008eba83d3c76ae9a25c3c242e4802d53
overlay_root=/project/flyspeck-candle-runs/v13-normalized-overlay-688d9d1
generated_root=/project/flyspeck-candle-runs/v13-generated-lp-688d9d1
result_root=/project/flyspeck-candle-runs/linked-compatibility-688d9d1-attempt-001
completion=$result_root.complete
completion_preimage=$result_root.complete.preimage
candle=$candle_root/candle.sh
provenance=$candle_root/candle/cakeml_artifact_provenance.py
ocaml=/usr/bin/ocaml
ocaml_sha256=9d4cb9f47b9d44cab338f29323ada69aec3728eb48f9039b0148c02690484306

test ! -e "$result_root"
test ! -e "$completion"
test ! -e "$completion_preimage"
test "$(/usr/bin/git -C "$candle_root" rev-parse HEAD)" = "$candle_head"
test "$(/usr/bin/git -C "$cakeml_root" rev-parse HEAD)" = "$cakeml_head"
test "$(/usr/bin/git -C "$hol4_root" rev-parse HEAD)" = "$hol4_head"
test "$(/usr/bin/git -C "$flyspeck_root" rev-parse HEAD)" = "$flyspeck_head"
candle_status=$(/usr/bin/git -C "$candle_root" status --porcelain=v1 --untracked-files=all)
cakeml_status=$(/usr/bin/git -C "$cakeml_root" status --porcelain=v1 --untracked-files=all)
hol4_status=$(/usr/bin/git -C "$hol4_root" status --porcelain=v1 --untracked-files=all)
flyspeck_status=$(/usr/bin/git -C "$flyspeck_root" status --porcelain=v1 --untracked-files=all)
test -z "$candle_status"
test -z "$cakeml_status"
test -z "$hol4_status"
test -z "$flyspeck_status"
test -x "$candle"
test "$(/usr/bin/sha256sum "$ocaml" | /usr/bin/cut -d' ' -f1)" = \
  "$ocaml_sha256"
/usr/bin/mkdir "$result_root"
ocaml_version=$($ocaml -version 2>&1)
test "$ocaml_version" = 'The OCaml toplevel, version 4.14.1'
/usr/bin/printf '%s\n' "$ocaml_version" >"$result_root/ocaml-version.txt"

run_gate () {
  gate=$1
  shift
  /usr/bin/time -v -o "$result_root/$gate.time" \
    "$@" >"$result_root/$gate.log" 2>&1
}

run_gate 00-check-linked-pre \
  /usr/bin/python3 -I -S "$provenance" check-linked \
  --candle-root "$candle_root"

run_gate 01-toplevel-normalization \
  /usr/bin/env FLYSPECK_ROOT="$flyspeck_root" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_toplevel_normalization.sh"
run_gate 02-dopen-runtime \
  /usr/bin/bash "$candle_root/candle/test_dopen_runtime.sh" "$candle"
run_gate 03-multiline-string-runtime \
  /usr/bin/bash "$candle_root/candle/test_multiline_string_runtime.sh" "$candle"
run_gate 04-static-load-directive \
  /usr/bin/bash "$candle_root/candle/test_static_load_directive.sh" "$candle"
run_gate 05-filename-compat \
  /usr/bin/env CANDLE_BINARY="$candle" \
  /usr/bin/bash "$candle_root/candle/test_filename_compat.sh"
run_gate 06-flyspeck-needs-directive \
  /usr/bin/env CANDLE_BINARY="$candle" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_needs_directive.sh"
run_gate 07-immediate-normalization \
  /usr/bin/env CANDLE_BINARY="$candle" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_immediate_normalization.sh"
run_gate 08-identity-normalization \
  /usr/bin/env CANDLE_BINARY="$candle" FLYSPECK_ROOT="$flyspeck_root" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_identity_normalization.sh"
run_gate 09-parser-orpattern-normalization \
  /usr/bin/env CANDLE_BINARY="$candle" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_parser_orpattern_normalization.sh"
run_gate 10-set-make-normalization \
  /usr/bin/env CANDLE_BINARY="$candle" FLYSPECK_ROOT="$flyspeck_root" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_set_make_normalization.sh"
run_gate 11-digest-compat \
  /usr/bin/env OCAML_414="$ocaml" \
  /usr/bin/bash "$candle_root/candle/test_digest_compat.sh" "$candle"
run_gate 12-str-compat \
  /usr/bin/env OCAML_414="$ocaml" \
  /usr/bin/bash "$candle_root/candle/test_str_compat.sh" "$candle"
run_gate 13-unix-metadata \
  /usr/bin/bash "$candle_root/candle/test_unix_metadata.sh" "$candle"
run_gate 14-flyspeck-ocaml-slice \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_ocaml_slice.sh" "$candle"
run_gate 15-flyspeck-source-digests \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_source_digests.sh" \
  "$candle" "$flyspeck_root"
run_gate 16-flyspeck-loader-guard \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_loader_guard.sh" \
  "$candle" "$flyspeck_root"
run_gate 17-flyspeck-loader-frontier \
  /usr/bin/env \
  CANDLE_FLYSPECK_FRONTIER_LOG="$result_root/17-flyspeck-loader-frontier.candle.log" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_loader_frontier.sh" \
  "$candle" "$flyspeck_root" "$overlay_root" "$generated_root"
run_gate 18-flyspeck-dopen-prefix \
  /usr/bin/env \
  CANDLE_FLYSPECK_DOPEN_LOG="$result_root/18-flyspeck-dopen-prefix.candle.log" \
  /usr/bin/bash "$candle_root/candle/test_flyspeck_dopen_prefix.sh" \
  "$candle" "$flyspeck_root" "$overlay_root" "$generated_root"

run_gate 19-check-linked-post \
  /usr/bin/python3 -I -S "$provenance" check-linked \
  --candle-root "$candle_root"

{
  /usr/bin/printf 'candle_head=%s\n' "$candle_head"
  /usr/bin/printf 'cakeml_head=%s\n' "$cakeml_head"
  /usr/bin/printf 'hol4_head=%s\n' "$hol4_head"
  /usr/bin/printf 'flyspeck_head=%s\n' "$flyspeck_head"
  /usr/bin/printf 'overlay_contract_sha256=%s\n' \
    491ca5a204e15fde5454faf63a42343f5cf4a281e03b8b212c937013b992de7e
  /usr/bin/printf 'generated_contract_sha256=%s\n' \
    dc9f9e5d60b3b43a1275a450e643bb1d8ce4843d517cdf4d84a6dc5c318a8816
  /usr/bin/printf 'ocaml_sha256=%s\n' "$ocaml_sha256"
  /usr/bin/printf 'gate_count=20\n'
  /usr/bin/printf 'compiled_test_count=17\n'
  /usr/bin/printf 'retained_file_count=45\n'
  /usr/bin/printf 'tests_outcome=passed\n'
  /usr/bin/printf 'publication_status=pending\n'
} >"$result_root/result.txt"

(
  cd "$result_root"
  /usr/bin/find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 |
    /usr/bin/sort -z |
    /usr/bin/xargs -0 /usr/bin/sha256sum >SHA256SUMS
)
/usr/bin/find "$result_root" -type f -exec /usr/bin/chmod 0444 {} +
/usr/bin/find "$result_root" -mindepth 1 -depth -type d \
  -exec /usr/bin/chmod 0555 {} +
(
  cd "$result_root"
  /usr/bin/sha256sum -c SHA256SUMS
  shopt -s dotglob nullglob
  retained_files=(./*)
  expected_files=(
    00-check-linked-pre.log 00-check-linked-pre.time
    01-toplevel-normalization.log 01-toplevel-normalization.time
    02-dopen-runtime.log 02-dopen-runtime.time
    03-multiline-string-runtime.log 03-multiline-string-runtime.time
    04-static-load-directive.log 04-static-load-directive.time
    05-filename-compat.log 05-filename-compat.time
    06-flyspeck-needs-directive.log 06-flyspeck-needs-directive.time
    07-immediate-normalization.log 07-immediate-normalization.time
    08-identity-normalization.log 08-identity-normalization.time
    09-parser-orpattern-normalization.log 09-parser-orpattern-normalization.time
    10-set-make-normalization.log 10-set-make-normalization.time
    11-digest-compat.log 11-digest-compat.time
    12-str-compat.log 12-str-compat.time
    13-unix-metadata.log 13-unix-metadata.time
    14-flyspeck-ocaml-slice.log 14-flyspeck-ocaml-slice.time
    15-flyspeck-source-digests.log 15-flyspeck-source-digests.time
    16-flyspeck-loader-guard.log 16-flyspeck-loader-guard.time
    17-flyspeck-loader-frontier.candle.log
    17-flyspeck-loader-frontier.log 17-flyspeck-loader-frontier.time
    18-flyspeck-dopen-prefix.candle.log
    18-flyspeck-dopen-prefix.log 18-flyspeck-dopen-prefix.time
    19-check-linked-post.log 19-check-linked-post.time
    ocaml-version.txt result.txt SHA256SUMS
  )
  test "${#retained_files[@]}" = 45
  test "${#expected_files[@]}" = 45
  for expected_file in "${expected_files[@]}"; do
    retained_file=./$expected_file
    test -f "$retained_file"
    test ! -L "$retained_file"
    test "$(/usr/bin/stat -c %a "$retained_file")" = 444
    test "$(/usr/bin/stat -c %h "$retained_file")" = 1
  done
)
/usr/bin/chmod 0555 "$result_root"
test "$(/usr/bin/stat -c %a "$result_root")" = 555
root_manifest_sha256=$(
  /usr/bin/sha256sum "$result_root/SHA256SUMS" | /usr/bin/cut -d' ' -f1
)
set -o noclobber
{
  /usr/bin/printf 'schema=1\n'
  /usr/bin/printf 'kind=linked-candle-compatibility-completion\n'
  /usr/bin/printf 'result_root=%s\n' "$result_root"
  /usr/bin/printf 'root_manifest_sha256=%s\n' "$root_manifest_sha256"
  /usr/bin/printf 'outcome=compatibility-pass\n'
} >"$completion_preimage"
set +o noclobber
/usr/bin/chmod 0444 "$completion_preimage"
/usr/bin/ln -- "$completion_preimage" "$completion"
/usr/bin/unlink "$completion_preimage"
test ! -e "$completion_preimage"
test "$(/usr/bin/stat -c %a "$completion")" = 444
test "$(/usr/bin/stat -c %h "$completion")" = 1
COMPATIBILITY_RUN
```

`gate_count=20` includes the pre-suite/post-suite linked-provenance checks and
the one source-only normalization gate.  `compiled_test_count=17` counts only
the compiled compatibility scripts.  `result.txt` records only that the tests
passed while publication is pending.  The sibling `.complete` marker publishes
`outcome=compatibility-pass` only after all 20 commands return zero, every
retained hash and mode is rechecked, and the result root is sealed.  A result
root without that exact ordinary, mode-0444, single-link marker is incomplete.

Several underlying compatibility helpers remove their private temporary logs
on some early failures.  The outer gate/time logs and the two explicit
frontier/prefix Candle logs are retained, but they may not diagnose every
timeout or pre-marker failure.  Such an attempt still fails closed and remains
preserved; reproduce the failing current-head helper under a new diagnostic
attempt if its retained outer transcript is insufficient.

## Next transition

After a complete pass, independently inspect the sibling `.complete` marker,
`SHA256SUMS`, every GNU-time exit status, the final marker in each gate log,
the detailed frontier/prefix logs, and both exact schema-6 `check-linked`
transcripts.  Only then start the two nonpromotable
diagnostic direct prefixes, followed by the eight cumulative direct boundaries
from fresh authenticated processes.  Any compiled failure is classified and
batched with the complete parser-inventory result before considering a Candle
source change or another canonical bootstrap.
