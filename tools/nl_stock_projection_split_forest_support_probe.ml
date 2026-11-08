(* Cheap restored-state surface check before the TSKAJXY theorem handoff. *)

module Candle_nl_stock_projection_split_forest_support_probe = struct

open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_split_validate;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_split_compute;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_split_stack_prove;;
open Candle_nl_stock_projection_split_forest_handoff;;

let _ =
  candle_q_dim_taylor_model_fixed_outer_variable_split_validate_six;;
let _ =
  candle_q_dim_taylor_model_fixed_outer_variable_split_compute_six;;
let _ =
  candle_q_dim_taylor_model_fixed_outer_variable_split_stack_six;;
let _ = decode_stack;;
let _ = candle_nl_stock_projection_split_forest_six;;

end;;

(* Keep the retained-checkpoint marker outside the module.  Candle prints the
   complete module signature before evaluating this phrase, so a runner that
   checkpoints on the marker cannot capture a large pending signature. *)
print_endline
  "CANDLE_NL_STOCK_PROJECTION_SPLIT_FOREST_SUPPORT_PROBE_OK DEVELOPMENT_NON_RELEASE";;
