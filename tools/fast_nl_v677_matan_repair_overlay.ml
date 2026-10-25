(* DEVELOPMENT / NON-RELEASE authenticated compatibility overlay.

   The checkpoint source-identity table continues to authorize the exact
   original logical nodes.  This table changes only the bytes selected for
   those 19 exact paths after both repositories and every byte identity have
   been checked by audit-fast-nl-v677-matan-repair.py. *)
let candle_flyspeck_v677_matan_repair_mappings =
 [("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_certificate_patch.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_certificate_patch.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_certificate_patch_compute.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_certificate_patch_compute.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_certificate_patch_exact.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_certificate_patch_exact.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_certificate_variant_prepare.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_certificate_variant_prepare.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_first_jet_program_compute.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_first_jet_program_compute.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_compile_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_compute.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_compute.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compute.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compute.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_compile_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_compile_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_program_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_program_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_sound.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_sound.ml");
  ("/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_representation.ml",
   "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_representation.ml")];;

let candle_flyspeck_v677_existing_mappings =
  match !Cakeml.normalizationOverlay with
  | None -> failwith "v677 normalization overlay is not configured"
  | Some mappings -> mappings;;

if List.length candle_flyspeck_v677_existing_mappings <> 95 ||
   List.length candle_flyspeck_v677_matan_repair_mappings <> 19 ||
   List.exists
     (fun (original,_) ->
       List.exists
         (fun (existing,_) -> existing = original)
         candle_flyspeck_v677_existing_mappings)
     candle_flyspeck_v677_matan_repair_mappings then
  failwith "v677 matan repair overlay precondition mismatch";;

Cakeml.normalizationOverlay :=
  Some
    (candle_flyspeck_v677_matan_repair_mappings @
     candle_flyspeck_v677_existing_mappings);;

if List.length
     (match !Cakeml.normalizationOverlay with
      | None -> []
      | Some mappings -> mappings) <> 114 then
  failwith "v677 matan repair overlay postcondition mismatch"
else
  print_endline
    "CANDLE_FLYSPECK_V677_MATAN_REPAIR_OVERLAY_READY mappings=19 total=114";;
