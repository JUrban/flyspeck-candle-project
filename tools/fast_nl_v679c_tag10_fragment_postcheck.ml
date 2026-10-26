(* DEVELOPMENT / NON-RELEASE postcheck for the isolated tag-10 proof probe. *)

let candle_v679c_fragment_axioms_after = axioms ();;

if hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_compute.candle_cv_case10173_hist_program_run_compute <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_item_sound.candle_cv_case10173_hist_item_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_logical_sound.candle_cv_case10173_hist_step_ordinary_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_logical_sound.candle_cv_case10173_hist_program_of_correct <>
     [] ||
   List.length candle_v679c_fragment_axioms_after <>
     List.length candle_v679c_fragment_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679c_fragment_axioms_before)
       candle_v679c_fragment_axioms_after) then
  failwith "v679c tag10 fragment proof validation"
else
  print_endline "CANDLE_FLYSPECK_V679C_TAG10_FRAGMENT_LOGICAL_PROOF_OK";;
