(* DEVELOPMENT / NON-RELEASE five-source checked-sound boundary. *)

let candle_v679a_expected_source_ids =
  [("cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml",
    "2e8599bb01a8f4f6bc5831529ce5ed16");
   ("cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml",
    "7d22d16ee9e6f3ab5e168ad8558e3bc2");
   ("cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml",
    "2bd8e34a1d1f84e3b25488224fcf275d");
   ("cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml",
    "f036de23d1b2264130e28727b1eb0766");
   ("cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml",
    "c8fa029635719e79a1c8f8ca0cf19678")];;

let candle_v679a_basename_loaded (name,_) =
  List.exists
    (fun (loaded_name,_) -> loaded_name = name)
    !Cakeml.loadedSourceIds;;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   List.exists candle_v679a_basename_loaded candle_v679a_expected_source_ids then
  failwith "v679a checked-sound predecessor mismatch";;

let candle_v679a_axioms_before = axioms ();;

needs "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml";;

let candle_v679a_axioms_after = axioms ();;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not
     (List.for_all
       (fun identity -> List.mem identity !Cakeml.loadedSourceIds)
       candle_v679a_expected_source_ids) ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_compute.candle_cv_case10173_hist_program_run_compute <>
     [] ||
   hyp
     Candle_cv_analytic_expr_fixed_scale_historical_root_certificate_sound.candle_fs_hist_root_certificate_sound <>
     [] ||
   hyp
     Candle_cv_analytic_expr_fixed_scale_historical_root_certificate_compute.candle_cv_fs_hist_root_certificate_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_checked_compute.candle_cv_case10173_hist_checked_raw_jobs_accept <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_checked_sound.candle_cv_case10173_hist_production_guard_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_checked_sound.candle_case10173_hist_root_record_semantics <>
     [] ||
   List.length candle_v679a_axioms_after <>
     List.length candle_v679a_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679a_axioms_before)
       candle_v679a_axioms_after) then
  failwith "v679a checked-sound validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679A_HISTORICAL_CHECKED_SOUND_CHECKPOINT_READY";;
