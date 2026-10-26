(* DEVELOPMENT / NON-RELEASE preamble for the isolated tag-10 proof probe. *)

let candle_v679c_fragment_target_names =
  ["cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml"];;

let candle_v679c_fragment_basename_loaded name =
  List.exists
    (fun (loaded_name,_) -> loaded_name = name)
    !Cakeml.loadedSourceIds;;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   List.exists candle_v679c_fragment_basename_loaded
     candle_v679c_fragment_target_names then
  failwith "v679c tag10 fragment predecessor mismatch";;

let candle_v679c_fragment_axioms_before = axioms ();;
