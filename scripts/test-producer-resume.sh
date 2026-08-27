#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_dir=$(cd -- "$project_dir/.." && pwd)
repos_dir="$workspace_dir/repos"
candle_dir="$repos_dir/candle"
producer_dir="$repos_dir/hol-light-flyspeck"
ocaml_switch="$repos_dir/hol-light/_opam"
test_dir="$candle_dir/candle/pft/tests"
init_script="$test_dir/resume_smoke_init.ml"
export_script="$test_dir/export_resume_smoke.ml"

for command in dmtcp_coordinator dmtcp_launch dmtcp_command dmtcp_restart \
               truncate timeout python3; do
  command -v "$command" >/dev/null
done

resume_tmp=$(mktemp -d /tmp/candle-pft-resume.XXXXXX)
resume_port=
cleanup() {
  local status=$?
  if [[ -n "$resume_port" ]]; then
    DMTCP_COORD_PORT="$resume_port" dmtcp_command -q >/dev/null 2>&1 || true
  fi
  if [[ $status -ne 0 ]]; then
    printf 'resume test failed; diagnostic log tails follow\n' >&2
    for log in "$resume_tmp"/*.log; do
      [[ -f "$log" ]] || continue
      printf '%s\n' "--- $log" >&2
      tail -n 80 "$log" >&2
    done
  fi
  if [[ ${PFT_RESUME_KEEP_TMP:-0} == 1 || $status -ne 0 ]]; then
    printf 'kept resume test files: %s\n' "$resume_tmp"
  else
    rm -rf -- "$resume_tmp"
  fi
  return "$status"
}
trap cleanup EXIT

common_environment=(
  "OCAMLPATH=$ocaml_switch/lib"
  "CAML_LD_LIBRARY_PATH=$ocaml_switch/lib/stublibs:/usr/lib/ocaml/stublibs"
  "HOLLIGHT_DIR=$producer_dir"
  "CANDLE_PFT_RESUME_SCRIPT=$export_script"
)

(
  cd "$producer_dir"
  env "${common_environment[@]}" \
    CANDLE_PFT_OUTPUT="$resume_tmp/baseline.pft.bin" \
    CANDLE_PFT_RESUME_MODE=baseline \
    CANDLE_PFT_RESUME_MARKER="$resume_tmp/baseline.marker" \
    timeout 360 ./ocaml-hol -init "$init_script" </dev/null \
    >"$resume_tmp/baseline.log" 2>&1
)
rg -Fq 'PFT_RESUME_SMOKE_OK commands=304 limits=(63,64,99)' \
  "$resume_tmp/baseline.log"

mkdir "$resume_tmp/checkpoint"
dmtcp_coordinator --daemon --coord-port 0 \
  --port-file "$resume_tmp/port" \
  --ckptdir "$resume_tmp/checkpoint" \
  --coord-logfile "$resume_tmp/coordinator-initial.log" >/dev/null
for _ in 1 2 3 4 5; do
  [[ -s "$resume_tmp/port" ]] && break
  sleep 1
done
resume_port=$(tr -d '[:space:]' <"$resume_tmp/port")
[[ "$resume_port" =~ ^[0-9]+$ ]]

(
  cd "$producer_dir"
  env "${common_environment[@]}" \
    CANDLE_PFT_OUTPUT="$resume_tmp/resumed.pft.bin" \
    CANDLE_PFT_RESUME_MODE=dmtcp \
    CANDLE_PFT_RESUME_MARKER="$resume_tmp/restart.marker" \
    DMTCP_COORD_PORT="$resume_port" \
    timeout 600 dmtcp_launch --join-coordinator \
      --ckptdir "$resume_tmp/checkpoint" \
      ./ocaml-hol -init "$init_script" </dev/null \
      >"$resume_tmp/producer.log" 2>&1
)
rg -Fq 'PFT_CHECKPOINT_READY offset=415 commands=72' \
  "$resume_tmp/producer.log"
rg -q 'Computation was checkpointed and killed' "$resume_tmp/producer.log"

mapfile -t checkpoint_files < <(
  find "$resume_tmp/checkpoint" -maxdepth 1 -type f \
    -name 'ckpt_*.dmtcp' -print | sort
)
[[ ${#checkpoint_files[@]} -gt 0 ]]
checkpoint_bytes=$(du -cb "${checkpoint_files[@]}" | tail -n 1 | cut -f1)

timeout 600 dmtcp_restart --new-coordinator --coord-port 0 \
  --ckptdir "$resume_tmp/checkpoint" "${checkpoint_files[@]}" \
  >"$resume_tmp/restart.log" 2>&1
rg -q '^PFT_CHECKPOINT_RESTORED$' "$resume_tmp/restart.log"
rg -Fq 'PFT_RESUME_SMOKE_OK commands=304 limits=(63,64,99)' \
  "$resume_tmp/restart.log"

cmp "$resume_tmp/baseline.pft.bin" "$resume_tmp/resumed.pft.bin"
resume_sha=$(sha256sum "$resume_tmp/resumed.pft.bin" | cut -d' ' -f1)
[[ "$resume_sha" == \
   7a3c7cefe5649bd70ddb8fa6a8c6c18443068c9e1e522385c9dce2d767aa0dc2 ]]
python3 "$test_dir/inspect_opcodes.py" "$resume_tmp/resumed.pft.bin" \
  >"$resume_tmp/opcodes.json"

timeout 180 "$candle_dir/candle.sh" >"$resume_tmp/replay.log" 2>&1 <<EOF
#use "candle/pft/replay.ml";;
let evidence = replay "$resume_tmp/resumed.pft.bin";;
if pft_result_command_count evidence = 305 &&
   pft_result_table_limits evidence = (63,64,99) &&
   pft_result_peak_live evidence = (63,64,99) &&
   map fst (pft_result_saved_theorems evidence) =
     ["candle\$RESUME_BEFORE"; "candle\$RESUME_AFTER"] &&
   pft_result_axioms evidence = [] &&
   not (pft_result_compute_initialized evidence)
then print_endline "PFT_RESUME_REPLAY_OK"
else failwith "unexpected resume replay evidence";;
EOF
rg -q '^Success!$' "$resume_tmp/replay.log"
rg -q 'PFT_RESUME_REPLAY_OK' "$resume_tmp/replay.log"
if rg -q '^EXCEPTION:' "$resume_tmp/replay.log"; then
  tail -n 40 "$resume_tmp/replay.log" >&2
  exit 1
fi

printf 'PASS: PFT process checkpoint/kill/restore (%s bytes)\n' \
  "$checkpoint_bytes"
printf 'PASS: resumed trace equals baseline (%s)\n' "$resume_sha"
printf 'PASS: resumed trace replays in compiled Candle (305 commands)\n'
