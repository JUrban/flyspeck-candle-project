(* DEVELOPMENT / NON-RELEASE postcheck for the complete tag-10 candidate. *)

let candle_v679d_axioms_after = axioms ();;

if hyp candle_v679d_full_theorem <> [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_checked_sound.candle_case10173_hist_root_record_semantics <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_logical_sound.candle_cv_case10173_hist_program_of_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_sound.candle_cv_case10173_hist_program_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_item_invariant.candle_case10173_hist_result_analytic_invariant <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_analytic_sound.candle_case10173_hist_context_run_analytic_invariant <>
     [] ||
   hyp
     Candle_cv_analytic_expr_fixed_scale_historical_dihedral_first_order_reference_sound.candle_fs_hist_first_order_direct_reference_gradient_contains <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_production_contract_sound.candle_case10173_hist_reference_hessian_is_source <>
     [] ||
   List.length candle_v679d_axioms_after <>
     List.length candle_v679d_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679d_axioms_before)
       candle_v679d_axioms_after) then
  failwith "v679d tag10 complete validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679D_TAG10_FULL_CANDIDATE_OK DEVELOPMENT_NON_RELEASE cells=4173 assumptions=0 axiom_growth=0";;
