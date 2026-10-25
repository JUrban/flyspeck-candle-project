(* DEVELOPMENT / NON-RELEASE first-fast-NL-theorem setup.

   This retains v663's complete normalization refresh and extends the
   authenticated fast-NL support identity table by the exact 11-node closure
   found by audit-fast-nl-support-source-closure.py.  The extension is loaded
   before the ordinary one-shot source-identity configuration. *)
#use "/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/runtime-config-no-trace.ml";;
#use "/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/overlay-data-v355.ml";;
#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/extra-source-identities.ml";;
#use "/project/flyspeck-candle-project/tools/fast_nl_v664_support_identity_extension.ml";;
#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/fast-nl-source-aliases.ml";;

let candle_flyspeck_stratum_source_alias_count =
  candle_flyspeck_stratum_source_alias_count +
  List.length candle_flyspeck_v656_fast_nl_source_aliases;;
let candle_flyspeck_stratum_source_aliases =
  (List.map (fun (alias,canonical,_) -> alias,canonical)
            candle_flyspeck_v656_fast_nl_source_aliases) @
  candle_flyspeck_stratum_source_aliases;;

let candle_flyspeck_v664_old_strictbuild =
  "/project/worktrees/flyspeck-strictbuild-bootstrap-v1/text_formalization/build/strictbuild.hl";;
let candle_flyspeck_v664_base_strictbuild =
  "/project/worktrees/flyspeck-strictbuild-checkpoint-base-9ae969df/text_formalization/build/strictbuild.hl";;
let candle_flyspeck_v664_serialization =
  "/project/worktrees/flyspeck-direct-action296-643bfd12/text_formalization/general/serialization.hl";;
let candle_flyspeck_v664_mk_all_ineq =
  "/project/worktrees/flyspeck-direct-action296-643bfd12/text_formalization/nonlinear/mk_all_ineq.hl";;

let candle_flyspeck_v664_is_rewrite_target target =
  target = candle_flyspeck_v664_old_strictbuild ||
  target = candle_flyspeck_v664_serialization ||
  target = candle_flyspeck_v664_mk_all_ineq;;

let candle_flyspeck_v664_rewrite_normalized_source (source,target,digest) =
  if target = candle_flyspeck_v664_old_strictbuild then
    let _ =
      digest = "88364c468334ed91b661cc2ecc8a484a" ||
      failwith "v664 stale strictbuild normalization identity" in
      (source,candle_flyspeck_v664_base_strictbuild,digest)
  else if target = candle_flyspeck_v664_serialization then
    let _ =
      digest = "f8460ac2a26b291b113ffa2ad2ffaace" ||
      failwith "v664 stale serialization normalization identity" in
      (source,target,"e0766072204d441da563dd688cfe1a7b")
  else if target = candle_flyspeck_v664_mk_all_ineq then
    let _ =
      digest = "3076e3e4143397c5764911906732abb7" ||
      failwith "v664 stale mk_all_ineq normalization identity" in
      (source,target,"e335cb02c223ba4a0f748a62e7b48d87")
  else (source,target,digest);;

let candle_flyspeck_v664_rewrite_count =
  List.length
    (List.filter
      (fun (_,target,_) -> candle_flyspeck_v664_is_rewrite_target target)
      candle_flyspeck_stratum_normalized_sources);;

if candle_flyspeck_v664_rewrite_count <> 3 then
  failwith "v664 incomplete normalization refresh";;

let candle_flyspeck_stratum_normalized_sources =
  List.map candle_flyspeck_v664_rewrite_normalized_source
    candle_flyspeck_stratum_normalized_sources;;

Cakeml.loadPath := [candle_hollight_root; Filename.currentDir];;

#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/flyspeck_stratum_fast_nl_setup.ml";;

print_endline
  "CANDLE_FLYSPECK_V664_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY";;
