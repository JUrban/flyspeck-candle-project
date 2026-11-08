(* ========================================================================== *)
(* Retained complete-checker computations for the 161160/23 mixed forests.   *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  This is the only stage that repeats the two  *)
(* numerical batches after their rejection scan.  Its compute theorems are  *)
(* retained and checkpointed before forest handoff or source reconstruction. *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_complete_compute_161160 = struct

open Candle_nl_stock_projection_mixed_forest_161160;;
open Candle_cv_analytic_expr_jet_prove;;
open Candle_cv_analytic_expr_stable_program_data;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_complete_compute;;

let encoded_jobs0 =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_encode_cells_six
    cells0;;
let encoded_jobs1 =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_encode_cells_six
    cells1;;

let complete_call prepared encoded_tokens encoded_jobs =
  list_mk_comb
    (`candle_cv_q_dim_taylor_model_fixed_outer_variable_complete_check`,
     [prepared.program_representation_term;`Cexp_num 6`;encoded_tokens;
      encoded_jobs]);;

let call0 = complete_call (prepared_for 0) encoded_tokens0 encoded_jobs0;;
let call1 = complete_call (prepared_for 1) encoded_tokens1 encoded_jobs1;;

let axioms_before = axioms ();;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_COMPUTE|function0|begin";;
let compute0 =
  candle_q_dim_analytic_jet_compute
    (candle_cv_q_dim_taylor_model_fixed_outer_variable_complete_compute_eqs ())
    call0;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_COMPUTE|function0|end";;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_COMPUTE|function1|begin";;
let compute1 =
  candle_q_dim_analytic_jet_compute
    (candle_cv_q_dim_taylor_model_fixed_outer_variable_complete_compute_eqs ())
    call1;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_COMPUTE|function1|end";;

let computed_accepts label call theorem =
  let numerical,topology =
    candle_q_dim_stable_program_dest_cval_pair
      (label ^ " reflected result") (rand (concl theorem)) in
  let topology_success,topology_payload =
    candle_q_dim_stable_program_dest_cval_pair
      (label ^ " topology result") topology in
  let remaining_jobs,_ =
    candle_q_dim_stable_program_dest_cval_pair
      (label ^ " topology payload") topology_payload in
  hyp theorem = [] && aconv (lhand (concl theorem)) call &&
  aconv numerical `Cexp_num 1` &&
  aconv topology_success `Cexp_num 1` &&
  aconv remaining_jobs `Cexp_num 0`;;

let axioms_after = axioms ();;

if not (computed_accepts "projection function0" call0 compute0) ||
   not (computed_accepts "projection function1" call1 compute1) ||
   length axioms_after <> length axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom axioms_before)
       axioms_after) then
  failwith "projection mixed complete compute: validation failed";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_COMPUTE_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-1611600345x" ^
   " parameter_index=23 complete_verdicts=2" ^
   " function0_cells=" ^ string_of_int (length cells0) ^
   " function1_cells=" ^ string_of_int (length cells1) ^
   " function0_tokens=" ^ string_of_int (length token_items0) ^
   " function1_tokens=" ^ string_of_int (length token_items1) ^
   " assumptions=0 axiom_growth=0");;

end;;
