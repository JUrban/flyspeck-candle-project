(* DEVELOPMENT / NON-RELEASE predecessor and axiom guard for the exact
   prepared-input import checkpoint. *)

let candle_v679l_target_names =
  ["cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml";
   "cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml";
   "cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml"];;

let candle_v679l_basename_loaded name =
  List.exists
    (fun (loaded_name,_) -> loaded_name = name)
    !Cakeml.loadedSourceIds;;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   List.exists candle_v679l_basename_loaded candle_v679l_target_names then
  failwith "v679l prepared-input predecessor mismatch";;

let candle_v679l_axioms_before = axioms ();;
