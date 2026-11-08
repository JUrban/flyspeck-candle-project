(* ========================================================================== *)
(* Complete stock reflected route for projection representative 139514/3.   *)
(* DEVELOPMENT / NON-RELEASE.                                                *)
(* ========================================================================== *)

module Candle_nl_stock_projection_complete_139514 = struct

open Candle_nl_stock_projection_plan_probe;;
open Candle_nl_stock_projection_cells_139514;;
open Candle_nl_stock_projection_repaired_plan_139514;;
open Candle_cv_analytic_expr_disjunctive_fixed_outer_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_complete_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_complete_root_prove;;

let axioms_before = axioms ();;

let _ =
  print_endline "CANDLE_NL_STOCK_PROJECTION_COMPLETE|complete-check|begin";;
let stack_result =
  candle_q_dim_taylor_model_fixed_outer_variable_complete_stack_six
    prepared repaired_cells repaired_tokens repaired_encoded_tokens;;
let _ =
  print_endline "CANDLE_NL_STOCK_PROJECTION_COMPLETE|complete-check|end";;

let _ =
  print_endline "CANDLE_NL_STOCK_PROJECTION_COMPLETE|root-handoff|begin";;
let root =
  candle_q_dim_taylor_model_fixed_outer_variable_complete_handoff_computed_root_six
    prepared repaired_tokens repaired_encoded_tokens
    stack_result.variable_complete_encoded_jobs_term
    stack_result.variable_complete_compute_theorem;;
let root_lower,root_upper =
  candle_disjunctive_fixed_outer_domain_bounds root_domain;;
let root_list_pass =
  Candle_cv_flyspeck_nonlinear_driver.candle_reflected_nl_source_pass_with
    (candle_disjunctive_fixed_outer_function_term prepared)
    (fun actual_lower actual_upper ->
      if not
          (candle_disjunctive_fixed_outer_aconv_lists
             actual_lower root_lower &&
           candle_disjunctive_fixed_outer_aconv_lists
             actual_upper root_upper) then
        failwith "projection complete: root domain drift";
      root.variable_complete_root_source_theorem)
    root_domain;;

if hyp root.variable_complete_root_cell_theorem <> [] ||
   hyp root.variable_complete_root_source_theorem <> [] then
  failwith "projection complete: root handoff assumptions";;
let _ =
  print_endline "CANDLE_NL_STOCK_PROJECTION_COMPLETE|root-handoff|end";;

let _ =
  print_endline "CANDLE_NL_STOCK_PROJECTION_COMPLETE|reconstruction|begin";;
let expanded_general =
  M_verifier_main.normalize_disj_result true
    functions variable_vector standard domain_subset root_list_pass;;
let expanded =
  let theorem = SPEC_ALL expanded_general in
  let bridge = TAUT (mk_imp (concl theorem,converted)) in
  MP bridge theorem;;
let case_theorem = REWRITE_RULE [GSYM expansion] expanded;;
let theorem =
  (SPEC_ALL o REWRITE_RULE [GSYM reconstruction]) case_theorem;;
let digest = Digest.to_hex (Digest.string (string_of_thm theorem));;
let axioms_after = axioms ();;

if hyp theorem <> [] ||
   not (aconv (concl theorem) target) ||
   length axioms_after <> length axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom axioms_before)
       axioms_after) then
  failwith "projection complete: final theorem validation failed";;
let _ =
  print_endline "CANDLE_NL_STOCK_PROJECTION_COMPLETE|reconstruction|end";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_COMPLETE_OK DEVELOPMENT_NON_RELEASE" ^
   " source=" ^ source_id ^
   " parameter_index=" ^ string_of_int parameter_index ^
   " original_cells=521 repaired_cells=534 token_items=1067" ^
   " instructions=201 sqrt_slots=16 assumptions=0 axiom_growth=0" ^
   " theorem_digest=" ^ digest);;

end;;
