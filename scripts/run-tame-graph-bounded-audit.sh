#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "$0")/.." && pwd)
isabelle_root=${CANDLE_ISABELLE2014_ROOT:-/project/tools/Isabelle2014}
isabelle_archive=${CANDLE_ISABELLE2014_ARCHIVE:-/project/tools/Isabelle2014_linux.tar.gz}
afp_archive=${CANDLE_TAME_AFP_ARCHIVE:-${project_root}/third_party/afp-flyspeck-tame-2014-08-28/afp-Flyspeck-Tame-2014-08-28.tar.gz}
afp_source=${CANDLE_TAME_AFP_SOURCE:-/project/tools/afp2014-flyspeck-tame}
output_root=${CANDLE_TAME_AUDIT_OUTPUT:-/project/flyspeck-candle-runs}
cpu_set=${CANDLE_TAME_AUDIT_CPUS:-0,1}

expected_isabelle=5e8aa384f41727d2a3d40d5dab564f6bdd3553f4a6bb533251732b4a39bf017d
expected_afp=54aa014cc8de1bc178ef68cc4e88932aefe9a61dcd17712ae714f39ae411102c

test "$(sha256sum "$isabelle_archive" | cut -d' ' -f1)" = "$expected_isabelle"
test "$(sha256sum "$afp_archive" | cut -d' ' -f1)" = "$expected_afp"
test -x "${isabelle_root}/bin/isabelle"
test -f "${afp_source}/ROOT"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir="${output_root}/tame-bounded-audit-${stamp}-dev-001"
test ! -e "$run_dir"
mkdir -p "$run_dir"

sha256sum \
  "$isabelle_archive" \
  "$afp_archive" \
  "${afp_source}/ROOT" \
  "${afp_source}/TameEnum.thy" \
  "${project_root}/tools/tame_reference_oracle/CandleTameBoundedAudit.thy" \
  "${project_root}/tools/tame_reference_oracle/ROOT" > "$run_dir/inputs.sha256"

# The evaluator is single-threaded.  Cap Java before applying the 20 GiB
# virtual-memory ceiling; otherwise Java sizes its default heap from the much
# larger host and fails during reservation before Isabelle starts.
export _JAVA_OPTIONS="${_JAVA_OPTIONS:-} -Xmx1024m"
ulimit -v 20971520
start_epoch=$(date +%s)
{
  printf 'CANDLE_TAME_BOUNDED_AUDIT_BEGIN utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'CANDLE_TAME_BOUNDED_AUDIT_ISABELLE '
  "${isabelle_root}/bin/isabelle" version
  /usr/bin/time -v -o "$run_dir/build.time" \
    taskset -c "$cpu_set" "${isabelle_root}/bin/isabelle" build \
      -j 1 -o threads=1 -o document=false \
      -d "$afp_source" \
      -D "${project_root}/tools/tame_reference_oracle"
  end_epoch=$(date +%s)
  printf 'CANDLE_TAME_BOUNDED_AUDIT_END utc=%s total_elapsed_seconds=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$((end_epoch - start_epoch))"
} 2>&1 | tee "$run_dir/reference.log"

session_log="${ISABELLE_HOME_USER:-${HOME}/.isabelle/Isabelle2014}/heaps/polyml-5.5.2_x86_64-linux/log/Candle-Tame-Bounded-Audit.gz"
test -f "$session_log"
cp "$session_log" "$run_dir/Candle-Tame-Bounded-Audit.gz"
sha256sum \
  "$run_dir/reference.log" \
  "$run_dir/build.time" \
  "$run_dir/Candle-Tame-Bounded-Audit.gz" > "$run_dir/output.sha256"
printf '%s\n' "$run_dir"
