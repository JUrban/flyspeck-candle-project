(* ========================================================================== *)
(* Authenticate the complete repaired TSKAJXY/26 numerical forest.           *)
(* DEVELOPMENT / NON-RELEASE.                                               *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_repaired_validation_tskajxy = struct

open Candle_nl_stock_projection_mixed_forest_tskajxy;;
open Candle_nl_stock_projection_mixed_repaired_forest_tskajxy;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let axioms_before = axioms ();;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED|function0|begin";;
let result0 =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
    (prepared_for 0) repaired_cells0;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED|function0|accepted";;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED|function1|begin";;
let result1 =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
    (prepared_for 1) cells1;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED|function1|accepted";;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED|function5|begin";;
let result5 =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
    (prepared_for 5) cells5;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED|function5|accepted";;

let results = [result0;result1;result5];;
let axioms_after = axioms ();;

if not
     (List.for_all
       (fun result ->
         hyp result.variable_raw_accept_theorem = [] &&
         hyp result.variable_raw_representation_theorem = [])
       results) ||
   length axioms_after <> length axioms_before ||
   not (List.for_all (fun axiom -> List.mem axiom axioms_before) axioms_after)
then failwith "TSKAJXY repaired validation: theorem validation failed";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED_VALIDATION_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 function0_cells=188 function1_cells=10" ^
   " function5_cells=1 repaired_source_leaves=40 assumptions=0" ^
   " axiom_growth=0");;

end;;
