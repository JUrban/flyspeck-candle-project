(* DEVELOPMENT / NON-RELEASE support boundary for the first fast original NL
   theorem.  This file is run only from a fresh authenticated action-49
   predecessor. *)
#use "/project/flyspeck-candle-project/tools/fast_nl_v665_verifier_runtime_compat.ml";;

let candle_flyspeck_v665_add_load_path path =
  if List.mem path !load_path then () else load_path := path :: !load_path;;

List.iter candle_flyspeck_v665_add_load_path
  ["/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs";
   "/project/worktrees/flyspeck-strictbuild-bootstrap-v1";
   "/project/worktrees/candle-direct-fast-nl-runtime-v1";
   "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6/formal_ineqs"];;

let candle_flyspeck_v665_support_started = Unix.gettimeofday();;
print_endline "CANDLE_FLYSPECK_V665_FAST_NL_SUPPORT_BEGIN";;

(* The base must be selected before arith_num.hl is evaluated. *)
needs "arith_options.hl";;
Arith_options.base := 200;;
needs "verifier/m_verifier_main.hl";;

(* Explicit replacements for modules inherited from the historical analytic
   development checkpoint.  Order is part of the static closure contract. *)
needs "candle/cv_compute_polynomial_expr_dim_jet_semantics.ml";;
needs "candle/cv_compute_exact_interval_square_core.ml";;
needs "candle/cv_compute_exact_rational_inv.ml";;
needs "candle/cv_compute_exact_interval_matan_series.ml";;
needs "candle/cv_compute_exact_interval_matan_series_program.ml";;
needs "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml";;
needs "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml";;
needs "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml";;
needs "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml";;
needs "/project/flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck/text_formalization/general/serialization.hl";;
needs "/project/flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck/text_formalization/nonlinear/break_case_exec.hl";;

(* Existing exact theorem support entries. *)
needs "candle/cv_compute_analytic_expr_case10173_historical_registered_original_prove.ml";;
needs "candle/benchmark_cv_compute_registered_hol4_export.ml";;
needs "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml";;
needs "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_topology_capture.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("m_verifier_main.hl","ca4991873b0c34b2da24a7080c5f521b")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_exact_interval_matan_series_program.ml",
           "8baa6fa6c5cb749377f07339d36f3705")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_case10173_historical_registered_original_prove.ml",
           "fb6b3b74f0bcd5f336a8072ac3edd4be")
          !Cakeml.loadedSourceIds) then
  failwith "v665 fast NL support loader identity did not commit"
else
  let _ = M_verifier_main.verify_ineq in
  (print_endline
     ("CANDLE_FLYSPECK_V665_FAST_NL_SUPPORT_SECONDS " ^
      string_of_float
        (Unix.gettimeofday() -. candle_flyspeck_v665_support_started));
   print_endline
     "CANDLE_FLYSPECK_V665_FAST_NL_SUPPORT_CHECKPOINT_READY");;
