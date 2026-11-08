(* ========================================================================== *)
(* First authenticated leaf of the plan-only NL projection representative.   *)
(* DEVELOPMENT / NON-RELEASE.                                                *)
(* ========================================================================== *)

module Candle_nl_stock_projection_first_leaf_probe = struct

open Certificate;;
open Candle_nl_stock_projection_plan_probe;;
open Candle_cv_analytic_expr_certificate_variant_prepare;;
open Candle_cv_analytic_expr_disjunctive_fixed_outer_prove;;
open Candle_cv_analytic_expr_stable_batch_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_stable_batch_prove;;

let rec first_leaf_domain domain = function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index <> 0 || raw_flag then
        failwith "projection first leaf: unexpected pass selection";
      domain
  | P_result_glue (_,split_index,convex_flag,left,_) ->
      if convex_flag then
        failwith "projection first leaf: unexpected convex glue";
      let left_domain,_ =
        M_verifier.split_domain 6 6 (split_index + 1) domain in
      first_leaf_domain left_domain left
  | P_result_mono _ ->
      failwith "projection first leaf: unexpected monotonicity node"
  | P_result_ref _ ->
      failwith "projection first leaf: unexpected reference node";;

let root_domain = M_taylor.mk_m_center_domain 6 6 xx1 zz1;;
let leaf_domain = first_leaf_domain root_domain precision_tree;;
let prepared = hd reflected_prepared;;
let point_plan = candle_q_dim_taylor_model_point_plan_six prepared;;

(* The production helper currently contains a case-16594-specific assertion *)
(* that every source has exactly ten square-root slots.  The underlying      *)
(* batch checker and soundness theorem are list-generic.  Keep this bounded  *)
(* probe local and derive the required count from the authenticated plan.    *)
let projection_handoff
    prepared domain lower upper center_intervals box_intervals =
  let slot_count =
    candle_disjunctive_fixed_outer_point_plan_program_count point_plan in
  if length box_intervals <> slot_count ||
     length center_intervals <> slot_count then
    failwith "projection first leaf: square-root slot drift";
  let cell =
    {stable_batch_center_intervals = center_intervals;
     stable_batch_lower = lower;
     stable_batch_upper = upper} in
  let aggregate =
    candle_q_dim_taylor_model_fixed_outer_stable_batch_prove_six
      prepared box_intervals [cell] in
  let source =
    candle_q_dim_taylor_model_fixed_outer_stable_batch_cell_source_six
      aggregate cell in
  Candle_cv_flyspeck_nonlinear_driver.candle_reflected_nl_source_pass_with
    (candle_disjunctive_fixed_outer_function_term prepared)
    (fun actual_lower actual_upper ->
      if not
          (candle_disjunctive_fixed_outer_aconv_lists
             actual_lower lower &&
           candle_disjunctive_fixed_outer_aconv_lists
             actual_upper upper) then
        failwith "projection first leaf: unexpected handoff box";
      source)
    domain;;

let projection_attempt prepared point_plan domain =
  let lower,upper = candle_disjunctive_fixed_outer_domain_bounds domain in
  let center_intervals =
    candle_q_dim_taylor_model_point_plan_intervals_six
      point_plan lower upper in
  let box_intervals =
    map (candle_disjunctive_fixed_outer_widen 5 4) center_intervals in
  projection_handoff
    prepared domain lower upper center_intervals box_intervals;;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_FIRST_LEAF|kernel-and-handoff|begin";;
let leaf_theorem =
  projection_attempt prepared point_plan leaf_domain;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_FIRST_LEAF|kernel-and-handoff|end";;

if hyp leaf_theorem <> [] then
  failwith "projection first leaf: unexpected assumptions";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_FIRST_LEAF_OK DEVELOPMENT_NON_RELEASE" ^
   " source=" ^ source_id ^
   " parameter_index=" ^ string_of_int parameter_index ^
   " function=0 factor=5/4 assumptions=0");;

end;;
