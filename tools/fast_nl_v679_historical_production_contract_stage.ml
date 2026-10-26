(* DEVELOPMENT / NON-RELEASE six-source production-contract boundary. *)

let candle_v679b_expected_source_ids =
  [("cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml",
    "f70e3d9ede852ce86da639727d759349");
   ("cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml",
    "5a92d27ab7a9763aef6a92e174a54b76");
   ("cv_compute_analytic_expr_case10173_historical_dihedral_item_invariant.ml",
    "a9b754bcbf641721667faf038a55292a");
   ("cv_compute_analytic_expr_case10173_historical_dihedral_program_analytic_sound.ml",
    "67e8175c0001aaf624ee3d3eeebbff1f");
   ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_reference_sound.ml",
    "2d1c81105e5fc337289f1570b45840a1");
   ("cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml",
    "26b1e42b37df603928eedf7db65a5b02")];;

let candle_v679b_basename_loaded (name,_) =
  List.exists
    (fun (loaded_name,_) -> loaded_name = name)
    !Cakeml.loadedSourceIds;;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   List.exists candle_v679b_basename_loaded candle_v679b_expected_source_ids then
  failwith "v679b production-contract predecessor mismatch";;

let candle_v679b_axioms_before = axioms ();;

needs "candle/cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml";;

let candle_v679b_axioms_after = axioms ();;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not
     (List.for_all
       (fun identity -> List.mem identity !Cakeml.loadedSourceIds)
       candle_v679b_expected_source_ids) ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_item_sound.candle_cv_case10173_hist_item_correct <>
     [] ||
   hyp
     Candle_cv_analytic_expr_case10173_historical_dihedral_program_logical_sound.candle_cv_case10173_hist_program_of_correct <>
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
   List.length candle_v679b_axioms_after <>
     List.length candle_v679b_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679b_axioms_before)
       candle_v679b_axioms_after) then
  failwith "v679b production-contract validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679B_HISTORICAL_PRODUCTION_CONTRACT_CHECKPOINT_READY";;
