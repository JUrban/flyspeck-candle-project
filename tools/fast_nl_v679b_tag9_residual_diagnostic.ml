(* DEVELOPMENT / NON-RELEASE residual-goal diagnostic for LR-049. *)

needs "candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml";;

open Candle_cv_analytic_expr_program_compute;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_algebraic_program_sound;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound;;
open Candle_cv_analytic_expr_case10173_historical_dihedral_program_compute;;
open Candle_cv_analytic_expr_case10173_historical_dihedral_item_sound;;

let candle_v679b_tag9_statement =
  parse_term
   ("!center_instruction box_instruction center_boxes boxes radii stack " ^
    "center_root_delta center_root_four_x0 box_root_delta box_root_four_x0. " ^
    "candle_cv_case10173_hist_step " ^
    "(candle_cv_q_interval_list center_boxes) " ^
    "(candle_cv_q_interval_list boxes) (candle_cv_q_list radii) " ^
    "(candle_cv_fs_interval_list " ^
    "[center_root_delta;center_root_four_x0;" ^
    "box_root_delta;box_root_four_x0]) " ^
    "(candle_cv_analytic_instruction center_instruction) " ^
    "(candle_cv_analytic_instruction box_instruction) " ^
    "(candle_cv_fsa_logical_stack_encode stack) = " ^
    "candle_cv_fsa_logical_stack_encode " ^
    "(candle_fsn_logical_program_step center_boxes boxes radii " ^
    "center_instruction box_instruction stack)");;

let (_,candle_v679b_tag9_residual_goals,_) =
 (REPEAT GEN_TAC THEN
  STRUCT_CASES_TAC
    (SPEC (parse_term "center_instruction:candle_analytic_instruction")
      (cases "candle_analytic_instruction")) THEN
  STRUCT_CASES_TAC
    (SPEC (parse_term "box_instruction:candle_analytic_instruction")
      (cases "candle_analytic_instruction")) THEN
  REWRITE_TAC[candle_cv_case10173_hist_step_def;
              candle_cv_analytic_instruction_def;
              cexp_eq_def; cexp_if_def; distinctness "cval";
              injectivity "cval"; NOT_SUC;
              candle_cv_fsn_logical_program_step_correct] THEN
  CONV_TAC NUM_REDUCE_CONV THEN
  REWRITE_TAC[cexp_if_def])
 ([],candle_v679b_tag9_statement);;

let (_,candle_v679b_tag9_residual_goal) =
  hd candle_v679b_tag9_residual_goals;;

print_endline
  ("CANDLE_FLYSPECK_V679B_TAG9_RESIDUAL goal=" ^
   string_of_term candle_v679b_tag9_residual_goal);;

print_endline "CANDLE_FLYSPECK_V679B_TAG9_RESIDUAL_DIAGNOSTIC_OK";;
