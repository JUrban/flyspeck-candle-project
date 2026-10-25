(* DEVELOPMENT / NON-RELEASE setup for the first fast original NL theorem.

   This extends the already authenticated direct-Flyspeck setup with the exact
   canonical 90-source nonlinear-verifier closure, its 29 normalization
   overlays, and the two explicit matan bridge prerequisites.  All data is
   installed before the one-shot loader configuration in
   flyspeck_stratum_fast_nl_setup.ml. *)
#use "/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/runtime-config-no-trace.ml";;
#use "/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/overlay-data-v355.ml";;
#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/extra-source-identities.ml";;
#use "/project/flyspeck-candle-project/tools/fast_nl_v665_verifier_data.ml";;
#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/fast-nl-source-aliases.ml";;

let candle_fast_nl_extra_source_identities =
  candle_fast_nl_v665_verifier_source_identities @
  candle_fast_nl_extra_source_identities;;

if List.length candle_fast_nl_extra_source_identities <> 283 then
  failwith "v665 complete fast-NL source identity count mismatch";;

let candle_flyspeck_stratum_source_alias_count =
  candle_flyspeck_stratum_source_alias_count +
  List.length candle_flyspeck_v656_fast_nl_source_aliases;;
let candle_flyspeck_stratum_source_aliases =
  (List.map (fun (alias,canonical,_) -> alias,canonical)
            candle_flyspeck_v656_fast_nl_source_aliases) @
  candle_flyspeck_stratum_source_aliases;;

let candle_flyspeck_v665_old_strictbuild =
  "/project/worktrees/flyspeck-strictbuild-bootstrap-v1/text_formalization/build/strictbuild.hl";;
let candle_flyspeck_v665_base_strictbuild =
  "/project/worktrees/flyspeck-strictbuild-checkpoint-base-9ae969df/text_formalization/build/strictbuild.hl";;
let candle_flyspeck_v665_serialization =
  "/project/worktrees/flyspeck-direct-action296-643bfd12/text_formalization/general/serialization.hl";;
let candle_flyspeck_v665_mk_all_ineq =
  "/project/worktrees/flyspeck-direct-action296-643bfd12/text_formalization/nonlinear/mk_all_ineq.hl";;

let candle_flyspeck_v665_is_rewrite_target target =
  target = candle_flyspeck_v665_old_strictbuild ||
  target = candle_flyspeck_v665_serialization ||
  target = candle_flyspeck_v665_mk_all_ineq;;

let candle_flyspeck_v665_rewrite_normalized_source (source,target,digest) =
  if target = candle_flyspeck_v665_old_strictbuild then
    let _ =
      digest = "88364c468334ed91b661cc2ecc8a484a" ||
      failwith "v665 stale strictbuild normalization identity" in
      (source,candle_flyspeck_v665_base_strictbuild,digest)
  else if target = candle_flyspeck_v665_serialization then
    let _ =
      digest = "f8460ac2a26b291b113ffa2ad2ffaace" ||
      failwith "v665 stale serialization normalization identity" in
      (source,target,"e0766072204d441da563dd688cfe1a7b")
  else if target = candle_flyspeck_v665_mk_all_ineq then
    let _ =
      digest = "3076e3e4143397c5764911906732abb7" ||
      failwith "v665 stale mk_all_ineq normalization identity" in
      (source,target,"e335cb02c223ba4a0f748a62e7b48d87")
  else (source,target,digest);;

let candle_flyspeck_v665_rewrite_count =
  List.length
    (List.filter
      (fun (_,target,_) -> candle_flyspeck_v665_is_rewrite_target target)
      candle_flyspeck_stratum_normalized_sources);;

if candle_flyspeck_v665_rewrite_count <> 3 then
  failwith "v665 incomplete normalization refresh";;

let candle_flyspeck_stratum_normalized_sources =
  candle_fast_nl_v665_verifier_normalized_sources @
  (List.map candle_flyspeck_v665_rewrite_normalized_source
    candle_flyspeck_stratum_normalized_sources);;
let candle_flyspeck_stratum_normalization_count =
  candle_flyspeck_stratum_normalization_count + 29;;

if List.length candle_flyspeck_stratum_normalized_sources <> 85 ||
   candle_flyspeck_stratum_normalization_count <> 85 then
  failwith "v665 complete normalization count mismatch";;

Cakeml.loadPath := [candle_hollight_root; Filename.currentDir];;

#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/flyspeck_stratum_fast_nl_setup.ml";;

print_endline
  "CANDLE_FLYSPECK_V665_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY";;
