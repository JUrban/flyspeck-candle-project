(* DEVELOPMENT / NON-RELEASE focused proof of the tag-10 historical repair. *)

let candle_v679c_candidate_root =
  "/project/worktrees/candle-fast-nl-historical-tag10-v1";;

let candle_v679c_target_name =
  "cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml";;

if List.exists
     (fun (name,_) -> name = candle_v679c_target_name)
     !loaded_files then
  failwith "v679c tag10 target already loaded";;

load_path := candle_v679c_candidate_root :: !load_path;;

let candle_v679c_axioms_before = axioms ();;

needs "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml";;

let candle_v679c_axioms_after = axioms ();;

if not
     (List.mem
       ("cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml",
        "67332cced0162c8437725bae7c177249")
       !loaded_files) ||
   not
     (List.mem
       ("cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml",
        "4378e7db1f0300eb21b259e1ad499f83")
       !loaded_files) ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_logical_sound.candle_cv_case10173_hist_step_ordinary_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_logical_sound.candle_cv_case10173_hist_program_of_correct <>
     [] ||
   List.length candle_v679c_axioms_after <>
     List.length candle_v679c_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679c_axioms_before)
       candle_v679c_axioms_after) then
  failwith "v679c tag10 logical proof validation"
else
  print_endline "CANDLE_FLYSPECK_V679C_TAG10_LOGICAL_PROOF_OK";;
