(* DEVELOPMENT / NON-RELEASE direct-input bridge for actions 0--49.

   The historical late overlays intentionally require the original 56-row
   direct-Flyspeck normalization table.  The canonical nonlinear verifier adds
   29 disjoint rows before checkpoint creation.  Hide precisely those rows
   while the unchanged historical action driver executes, then restore them
   before accepting the new checkpoint. *)
let candle_flyspeck_v668_verifier_originals =
  List.map (fun (original,_,_) -> original)
    candle_fast_nl_v665_verifier_normalized_sources;;

let candle_flyspeck_v668_is_verifier_original (original,_) =
  List.mem original candle_flyspeck_v668_verifier_originals;;

let candle_flyspeck_v668_verifier_mappings,
    candle_flyspeck_v668_direct_mappings =
  match !Cakeml.normalizationOverlay with
  | None -> failwith "v668 normalization overlay is not configured"
  | Some mappings ->
      List.filter candle_flyspeck_v668_is_verifier_original mappings,
      List.filter
        (fun mapping -> not (candle_flyspeck_v668_is_verifier_original mapping))
        mappings;;

if List.length candle_flyspeck_v668_verifier_originals <> 29 ||
   List.length candle_flyspeck_v668_verifier_mappings <> 29 ||
   List.length candle_flyspeck_v668_direct_mappings <> 56 then
  failwith "v668 normalization partition mismatch";;

Cakeml.normalizationOverlay := Some candle_flyspeck_v668_direct_mappings;;
print_endline
  "CANDLE_FLYSPECK_V668_ACTION49_OVERLAY_PARTITION_BEGIN direct=56 verifier=29";;

#use "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/action0-through49.ml";;

let candle_flyspeck_v668_updated_direct_mappings =
  match !Cakeml.normalizationOverlay with
  | None -> failwith "v668 historical action removed normalization overlay"
  | Some mappings -> mappings;;

if List.length candle_flyspeck_v668_updated_direct_mappings <> 56 ||
   List.filter candle_flyspeck_v668_is_verifier_original
     candle_flyspeck_v668_updated_direct_mappings <> [] ||
   List.length !candle_flyspeck_stratum_action_events <> 50 ||
   !Cakeml.pendingLoadedSourceIds <> [] then
  failwith "v668 historical action overlay postcondition mismatch";;

let candle_flyspeck_v668_complete_mappings =
  candle_flyspeck_v668_verifier_mappings @
  candle_flyspeck_v668_updated_direct_mappings;;

if List.length candle_flyspeck_v668_complete_mappings <> 85 then
  failwith "v668 restored normalization cardinality mismatch";;

Cakeml.normalizationOverlay := Some candle_flyspeck_v668_complete_mappings;;
print_endline
  "CANDLE_FLYSPECK_V668_ACTION49_CHECKPOINT_READY actions=50 passed=50 normalizations=85";;
