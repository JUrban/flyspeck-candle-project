(* ========================================================================== *)
(* Reusable exact cell/topology preparation for projection record 139514/3.  *)
(* DEVELOPMENT / NON-RELEASE.                                                *)
(* ========================================================================== *)

module Candle_nl_stock_projection_cells_139514 = struct

open Certificate;;
open Candle_nl_stock_projection_plan_probe;;
open Candle_cv_analytic_expr_certificate_variant_prepare;;
open Candle_cv_analytic_expr_disjunctive_fixed_outer_prove;;
open Candle_cv_analytic_expr_stable_batch_prove;;
open Candle_cv_analytic_expr_stable_program_data;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_batch_prove;;

type projection_shape =
  | Projection_leaf of
      candle_q_dim_taylor_model_fixed_outer_variable_batch_cell_six
  | Projection_node of int * projection_shape * projection_shape;;

type projection_token =
  | Projection_token_leaf
  | Projection_token_glue of int;;

let prepared = hd reflected_prepared;;
let point_plan = candle_q_dim_taylor_model_point_plan_six prepared;;
let root_domain = M_taylor.mk_m_center_domain 6 6 xx1 zz1;;

let projection_factor_cell numerator denominator domain =
  let lower,upper = candle_disjunctive_fixed_outer_domain_bounds domain in
  let center_intervals =
    candle_q_dim_taylor_model_point_plan_intervals_six
      point_plan lower upper in
  let box_intervals =
    map
      (candle_disjunctive_fixed_outer_widen numerator denominator)
      center_intervals in
  {variable_batch_box_intervals = box_intervals;
   variable_batch_stable_cell =
     {stable_batch_center_intervals = center_intervals;
      stable_batch_lower = lower;
      stable_batch_upper = upper}};;

let projection_cell domain = projection_factor_cell 5 4 domain;;

let projection_exact_cell domain =
  let lower,upper = candle_disjunctive_fixed_outer_domain_bounds domain in
  let center_intervals,box_intervals =
    candle_disjunctive_fixed_outer_exact_intervals
      point_plan lower upper in
  {variable_batch_box_intervals = box_intervals;
   variable_batch_stable_cell =
     {stable_batch_center_intervals = center_intervals;
      stable_batch_lower = lower;
      stable_batch_upper = upper}};;

let rec projection_shape_build domain = function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index <> 0 || raw_flag then
        failwith "projection cells: unexpected pass selection";
      Projection_leaf (projection_cell domain)
  | P_result_glue (_,split_index,convex_flag,left,right) ->
      if convex_flag then
        failwith "projection cells: unexpected convex glue";
      let axis = split_index + 1 in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      Projection_node
        (axis,
         projection_shape_build left_domain left,
         projection_shape_build right_domain right)
  | P_result_mono _ ->
      failwith "projection cells: unexpected monotonicity node"
  | P_result_ref _ ->
      failwith "projection cells: unexpected reference node";;

let rec projection_shape_build_overlay next_leaf exact_indices domain =
  function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index <> 0 || raw_flag then
        failwith "projection cells: unexpected overlay pass selection";
      (Projection_leaf
         ((if List.mem next_leaf exact_indices
           then projection_exact_cell
           else projection_cell) domain),
       next_leaf + 1)
  | P_result_glue (_,split_index,convex_flag,left,right) ->
      if convex_flag then
        failwith "projection cells: unexpected overlay convex glue";
      let axis = split_index + 1 in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      let left_shape,after_left =
        projection_shape_build_overlay
          next_leaf exact_indices left_domain left in
      let right_shape,after_right =
        projection_shape_build_overlay
          after_left exact_indices right_domain right in
      Projection_node (axis,left_shape,right_shape),after_right
  | P_result_mono _ ->
      failwith "projection cells: unexpected overlay monotonicity node"
  | P_result_ref _ ->
      failwith "projection cells: unexpected overlay reference node";;

let rec projection_indexed_domains next_leaf domain = function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index <> 0 || raw_flag then
        failwith "projection cells: unexpected indexed pass selection";
      [(next_leaf,domain)],next_leaf + 1
  | P_result_glue (_,split_index,convex_flag,left,right) ->
      if convex_flag then
        failwith "projection cells: unexpected indexed convex glue";
      let axis = split_index + 1 in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      let left_domains,after_left =
        projection_indexed_domains next_leaf left_domain left in
      let right_domains,after_right =
        projection_indexed_domains after_left right_domain right in
      (left_domains @ right_domains),after_right
  | P_result_mono _ ->
      failwith "projection cells: unexpected indexed monotonicity node"
  | P_result_ref _ ->
      failwith "projection cells: unexpected indexed reference node";;

let rec projection_cells_of_shape = function
  | Projection_leaf cell -> [cell]
  | Projection_node (_,left,right) ->
      projection_cells_of_shape left @ projection_cells_of_shape right;;

let rec projection_tokens_of_shape = function
  | Projection_leaf _ -> [Projection_token_leaf]
  | Projection_node (axis,left,right) ->
      projection_tokens_of_shape left @ projection_tokens_of_shape right @
      [Projection_token_glue axis];;

let projection_logical_token = function
  | Projection_token_leaf ->
      `Candle_q_dim_taylor_model_fixed_outer_variable_compact_leaf`
  | Projection_token_glue axis ->
      mk_comb
        (`Candle_q_dim_taylor_model_fixed_outer_variable_compact_glue`,
         mk_small_numeral axis);;

let projection_encoded_token = function
  | Projection_token_leaf -> `Cexp_num 0`
  | Projection_token_glue axis ->
      candle_q_dim_stable_program_cval_pair
        (mk_comb (`Cexp_num`,mk_small_numeral axis)) `Cexp_num 0`;;

let _ = print_endline "CANDLE_NL_STOCK_PROJECTION_CELLS|preparation|begin";;
let shape = projection_shape_build root_domain precision_tree;;
let cells = projection_cells_of_shape shape;;
let token_data = projection_tokens_of_shape shape;;
let token_items = map projection_logical_token token_data;;
let tokens =
  mk_list
    (token_items,
     type_of
       `Candle_q_dim_taylor_model_fixed_outer_variable_compact_leaf`);;
let encoded_tokens =
  candle_q_dim_stable_program_cval_list
    (map projection_encoded_token token_data);;

if length cells <> 521 || length token_items <> 1041 then
  failwith "projection cells: plan shape drift";;

print_endline
  "CANDLE_NL_STOCK_PROJECTION_CELLS_OK DEVELOPMENT_NON_RELEASE cells=521 token_items=1041";;

end;;
