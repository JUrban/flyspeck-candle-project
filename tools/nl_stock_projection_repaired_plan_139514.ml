(* ========================================================================== *)
(* Frozen sparse numerical plan for projection record 139514/3.             *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The 13 one-level splits were discovered by   *)
(* nl_stock_projection_sparse_repair_139514.ml.  This module only rebuilds   *)
(* that plan as data; the complete reflected checker remains authoritative.   *)
(* ========================================================================== *)

module Candle_nl_stock_projection_repaired_plan_139514 = struct

open Certificate;;
open Candle_nl_stock_projection_cells_139514;;
open Candle_cv_analytic_expr_stable_program_data;;

let split_indices =
  [22;36;109;169;218;297;298;309;310;352;356;409;416];;

let rec build next_leaf domain = function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index <> 0 || raw_flag then
        failwith "projection repaired plan: unexpected pass selection";
      let shape =
        if List.mem next_leaf split_indices then
          let left_domain,right_domain =
            M_verifier.split_domain 6 6 1 domain in
          Projection_node
            (1,
             Projection_leaf (projection_cell left_domain),
             Projection_leaf (projection_cell right_domain))
        else Projection_leaf (projection_cell domain) in
      shape,next_leaf + 1
  | P_result_glue (_,split_index,convex_flag,left,right) ->
      if convex_flag then
        failwith "projection repaired plan: unexpected convex glue";
      let axis = split_index + 1 in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      let left_shape,after_left = build next_leaf left_domain left in
      let right_shape,after_right = build after_left right_domain right in
      Projection_node (axis,left_shape,right_shape),after_right
  | P_result_mono _ ->
      failwith "projection repaired plan: unexpected monotonicity node"
  | P_result_ref _ ->
      failwith "projection repaired plan: unexpected reference node";;

let repaired_shape,after_repair =
  build 0 root_domain
    Candle_nl_stock_projection_plan_probe.precision_tree;;
let repaired_cells = projection_cells_of_shape repaired_shape;;
let repaired_token_data = projection_tokens_of_shape repaired_shape;;
let repaired_token_items = map projection_logical_token repaired_token_data;;
let repaired_tokens =
  mk_list
    (repaired_token_items,
     type_of
       `Candle_q_dim_taylor_model_fixed_outer_variable_compact_leaf`);;
let repaired_encoded_tokens =
  candle_q_dim_stable_program_cval_list
    (map projection_encoded_token repaired_token_data);;

if after_repair <> 521 ||
   length repaired_cells <> 534 ||
   length repaired_token_items <> 1067 then
  failwith "projection repaired plan: shape drift";;

print_endline
  "CANDLE_NL_STOCK_PROJECTION_REPAIRED_PLAN_OK DEVELOPMENT_NON_RELEASE original_cells=521 repaired_cells=534 token_items=1067 splits=13 maximum_added_depth=1";;

end;;
