(* DEVELOPMENT / NON-RELEASE historical-soundness proof boundary. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
        "cdd7194429afaba9b269370f39ff4e7c")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
      "393018a4878384295220afb6fb307ba1")
     !Cakeml.loadedSourceIds then
  failwith "v677 historical-soundness predecessor mismatch";;

let candle_v677_historical_sound_original =
  "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_sound.ml";;

let candle_v677_historical_sound_candidate =
  "/project/worktrees/candle-fast-nl-historical-sound-v1/candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_sound.ml";;

let rec candle_v677_historical_overlay_lookup key mappings =
  match mappings with
  | [] -> None
  | (original,current)::rest ->
      if original = key then Some current
      else candle_v677_historical_overlay_lookup key rest;;

let candle_v677_historical_existing_overlay =
  match !Cakeml.normalizationOverlay with
  | None -> failwith "v677 historical-soundness overlay absent"
  | Some mappings -> mappings;;

if List.length candle_v677_historical_existing_overlay <> 114 ||
   candle_v677_historical_overlay_lookup
     candle_v677_historical_sound_original
     candle_v677_historical_existing_overlay <> None then
  failwith "v677 historical-soundness overlay precondition mismatch"
else
  Cakeml.normalizationOverlay :=
    Some
      ((candle_v677_historical_sound_original,
        candle_v677_historical_sound_candidate) ::
       candle_v677_historical_existing_overlay);;

if List.length
     (match !Cakeml.normalizationOverlay with
      | None -> []
      | Some mappings -> mappings) <> 115 ||
   candle_v677_historical_overlay_lookup
     candle_v677_historical_sound_original
     (match !Cakeml.normalizationOverlay with
      | None -> []
      | Some mappings -> mappings) <>
     Some candle_v677_historical_sound_candidate then
  failwith "v677 historical-soundness overlay postcondition mismatch";;

needs "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml";;
needs "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
           "393018a4878384295220afb6fb307ba1")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
           "2d043a6136c50c80fcf332000a157558")
          !Cakeml.loadedSourceIds) then
  failwith "v677 historical-soundness identities did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_HISTORICAL_SOUND_CHECKPOINT_READY";;
