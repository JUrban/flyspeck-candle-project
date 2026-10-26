(* DEVELOPMENT / NON-RELEASE preamble for the complete tag-10 candidate. *)

let candle_v679d_verifier_source_root =
  "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6";;

load_path :=
  candle_v679d_verifier_source_root ::
  List.filter
    (fun path -> path <> candle_v679d_verifier_source_root)
    !load_path;;

let candle_v679d_certificate_source =
  file_on_path (!load_path) "formal_ineqs/verifier/certificate.hl";;

let candle_v679d_report_source =
  file_on_path (!load_path) "formal_ineqs/misc/report.hl";;

if candle_v679d_certificate_source <>
     (candle_v679d_verifier_source_root ^
       "/formal_ineqs/verifier/certificate.hl") ||
   candle_v679d_report_source <>
     (candle_v679d_verifier_source_root ^
       "/formal_ineqs/misc/report.hl") then
  failwith "v679d verifier source-root precedence";;

let candle_v679d_target_names =
  ["cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml";
   "cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml";
   "cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml";
   "benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_program_sound.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_item_invariant.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_program_analytic_sound.ml";
   "cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_reference_sound.ml";
   "cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml"];;

let candle_v679d_basename_loaded name =
  List.exists
    (fun (loaded_name,_) -> loaded_name = name)
    !Cakeml.loadedSourceIds;;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   List.exists candle_v679d_basename_loaded candle_v679d_target_names then
  failwith "v679d tag10 full predecessor mismatch";;

let candle_v679d_axioms_before = axioms ();;
