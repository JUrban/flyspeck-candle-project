(* ========================================================================== *)
(* Exact mixed-disjunct forest for TSKAJXY-RIBCYXU-sym/26.                   *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  Maximal same-function subtrees become three  *)
(* independent reflected forests for the selected functions 0, 1, and 5.    *)
(* Their closed roots retain the exact mixed-function skeleton for handoff.  *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_forest_tskajxy = struct

open Certificate;;
open Candle_nl_stock_projection_plan_probe;;
open Candle_cv_exact_interval_reify;;
open Candle_cv_analytic_expr_certificate_variant_prepare;;
open Candle_cv_analytic_expr_disjunctive_fixed_outer_prove;;
open Candle_cv_analytic_expr_stable_batch_prove;;
open Candle_cv_analytic_expr_stable_program_data;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_batch_prove;;

type projection_mixed_shape =
  | Projection_mixed_leaf of
      int * int * bool * thm *
      candle_q_dim_taylor_model_fixed_outer_variable_batch_cell_six
  | Projection_mixed_node of
      int * thm * projection_mixed_shape * projection_mixed_shape;;

type projection_mixed_component = {
  projection_component_id : int;
  projection_component_selected : int;
  projection_component_domain : thm;
  projection_component_shape : projection_mixed_shape;
};;

type projection_mixed_skeleton =
  | Projection_mixed_component of int
  | Projection_mixed_join of
      int * projection_mixed_skeleton * projection_mixed_skeleton;;

type projection_mixed_token =
  | Projection_mixed_token_leaf
  | Projection_mixed_token_glue of int;;

let prepared_for selected =
  if selected < 0 || selected >= length reflected_prepared then
    failwith "TSKAJXY mixed forest: selected function outside source list"
  else List.nth reflected_prepared selected;;

let point_plans =
  map candle_q_dim_taylor_model_point_plan_six reflected_prepared;;

let point_plan_for selected =
  if selected < 0 || selected >= length point_plans then
    failwith "TSKAJXY mixed forest: point-plan selection drift"
  else List.nth point_plans selected;;

let projection_mixed_cell selected domain =
  let lower,upper =
    candle_disjunctive_fixed_outer_domain_bounds domain in
  let center_intervals =
    candle_q_dim_taylor_model_point_plan_intervals_six
      (point_plan_for selected) lower upper in
  let box_intervals =
    map (candle_disjunctive_fixed_outer_widen 5 4) center_intervals in
  {variable_batch_box_intervals = box_intervals;
   variable_batch_stable_cell =
     {stable_batch_center_intervals = center_intervals;
      stable_batch_lower = lower;
      stable_batch_upper = upper}};;

let rec projection_mixed_shape_build next_leaf domain = function
  | P_result_pass (_,selected,raw_flag) ->
      (Projection_mixed_leaf
         (next_leaf,selected,raw_flag,domain,
          projection_mixed_cell selected domain),
       next_leaf + 1,1,0,(if raw_flag then 1 else 0))
  | P_result_glue (_,split_index,convex_flag,left,right) ->
      if convex_flag then
        failwith "TSKAJXY mixed forest: unexpected convex glue";
      let axis = split_index + 1 in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      let left_shape,after_left,left_cells,left_glues,left_raw =
        projection_mixed_shape_build next_leaf left_domain left in
      let right_shape,after_right,right_cells,right_glues,right_raw =
        projection_mixed_shape_build after_left right_domain right in
      (Projection_mixed_node (axis,domain,left_shape,right_shape),
       after_right,left_cells + right_cells,1 + left_glues + right_glues,
       left_raw + right_raw)
  | P_result_mono _ ->
      failwith "TSKAJXY mixed forest: unexpected monotonicity node"
  | P_result_ref _ ->
      failwith "TSKAJXY mixed forest: unexpected reference node";;

let projection_mixed_shape_domain = function
  | Projection_mixed_leaf (_,_,_,domain,_) -> domain
  | Projection_mixed_node (_,domain,_,_) -> domain;;

let rec projection_mixed_shape_selection = function
  | Projection_mixed_leaf (_,selected,_,_,_) -> Some selected
  | Projection_mixed_node (_,_,left,right) ->
      (match projection_mixed_shape_selection left,
             projection_mixed_shape_selection right with
       | Some left_selected,Some right_selected
           when left_selected = right_selected -> Some left_selected
       | _ -> None);;

let rec projection_mixed_skeletonize next_component shape =
  match projection_mixed_shape_selection shape with
  | Some selected ->
      let component =
        {projection_component_id = next_component;
         projection_component_selected = selected;
         projection_component_domain = projection_mixed_shape_domain shape;
         projection_component_shape = shape} in
      (Projection_mixed_component next_component,
       next_component + 1,[component])
  | None ->
      (match shape with
       | Projection_mixed_node (axis,_,left,right) ->
           let left_skeleton,after_left,left_components =
             projection_mixed_skeletonize next_component left in
           let right_skeleton,after_right,right_components =
             projection_mixed_skeletonize after_left right in
           (Projection_mixed_join
              (axis,left_skeleton,right_skeleton),
            after_right,left_components @ right_components)
       | Projection_mixed_leaf _ ->
           failwith "TSKAJXY mixed forest: mixed leaf");;

let rec projection_mixed_shape_indexed_cells = function
  | Projection_mixed_leaf (source_index,_,_,_,cell) ->
      [(source_index,cell)]
  | Projection_mixed_node (_,_,left,right) ->
      projection_mixed_shape_indexed_cells left @
      projection_mixed_shape_indexed_cells right;;

let rec projection_mixed_shape_tokens = function
  | Projection_mixed_leaf _ -> [Projection_mixed_token_leaf]
  | Projection_mixed_node (axis,_,left,right) ->
      projection_mixed_shape_tokens left @
      projection_mixed_shape_tokens right @
      [Projection_mixed_token_glue axis];;

let projection_mixed_q_interval lower upper =
  mk_pair
    (candle_q_term (rat_of_term lower),
     candle_q_term (rat_of_term upper));;

let projection_mixed_component_boxes component =
  let lower,upper =
    candle_disjunctive_fixed_outer_domain_bounds
      component.projection_component_domain in
  mk_list
    (map2 projection_mixed_q_interval lower upper,
     candle_q_interval_type);;

let projection_mixed_encode_token = function
  | Projection_mixed_token_leaf -> `Cexp_num 0`
  | Projection_mixed_token_glue axis ->
      candle_q_dim_stable_program_cval_pair
        (mk_comb (`Cexp_num`,mk_small_numeral axis)) `Cexp_num 0`;;

let projection_mixed_logical_token = function
  | Projection_mixed_token_leaf ->
      `Candle_q_dim_taylor_model_fixed_outer_variable_compact_leaf`
  | Projection_mixed_token_glue axis ->
      mk_comb
        (`Candle_q_dim_taylor_model_fixed_outer_variable_compact_glue`,
         mk_small_numeral axis);;

let projection_mixed_forest components =
  let indexed_cells =
    List.flatten
      (map
        (fun component ->
          projection_mixed_shape_indexed_cells
            component.projection_component_shape)
        components) in
  let tokens =
    List.flatten
      (map
        (fun component ->
          projection_mixed_shape_tokens
            component.projection_component_shape)
        components) in
  let expected_stack =
    rev (map projection_mixed_component_boxes components) in
  indexed_cells,tokens,expected_stack;;

let root_domain = M_taylor.mk_m_center_domain 6 6 xx1 zz1;;
let shape,after_leaf,numerical_cells,glue_nodes,raw_leaves =
  projection_mixed_shape_build 0 root_domain precision_tree;;
let skeleton,after_component,components =
  projection_mixed_skeletonize 0 shape;;
let components0 =
  List.filter
    (fun component -> component.projection_component_selected = 0)
    components;;
let components1 =
  List.filter
    (fun component -> component.projection_component_selected = 1)
    components;;
let components5 =
  List.filter
    (fun component -> component.projection_component_selected = 5)
    components;;
let indexed_cells0,tokens0,expected_stack0 =
  projection_mixed_forest components0;;
let indexed_cells1,tokens1,expected_stack1 =
  projection_mixed_forest components1;;
let indexed_cells5,tokens5,expected_stack5 =
  projection_mixed_forest components5;;
let cells0 = map snd indexed_cells0
and cells1 = map snd indexed_cells1
and cells5 = map snd indexed_cells5;;
let token_items0 = map projection_mixed_logical_token tokens0
and token_items1 = map projection_mixed_logical_token tokens1
and token_items5 = map projection_mixed_logical_token tokens5;;
let logical_tokens items =
  mk_list
    (items,
     type_of
       `Candle_q_dim_taylor_model_fixed_outer_variable_compact_leaf`);;
let logical_tokens0 = logical_tokens token_items0
and logical_tokens1 = logical_tokens token_items1
and logical_tokens5 = logical_tokens token_items5;;
let encoded_tokens tokens =
  candle_q_dim_stable_program_cval_list
    (map projection_mixed_encode_token tokens);;
let encoded_tokens0 = encoded_tokens tokens0
and encoded_tokens1 = encoded_tokens tokens1
and encoded_tokens5 = encoded_tokens tokens5;;

let selected_component_count =
  length components0 + length components1 + length components5;;
let selected_token_count =
  length token_items0 + length token_items1 + length token_items5;;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_FOREST_DIAGNOSTIC" ^
   " source=" ^ source_id ^
   " parameter_index=" ^ string_of_int parameter_index ^
   " after_leaf=" ^ string_of_int after_leaf ^
   " numerical_cells=" ^ string_of_int numerical_cells ^
   " glue_nodes=" ^ string_of_int glue_nodes ^
   " raw_leaves=" ^ string_of_int raw_leaves ^
   " components=" ^ string_of_int (length components) ^
   " function0_components=" ^ string_of_int (length components0) ^
   " function1_components=" ^ string_of_int (length components1) ^
   " function5_components=" ^ string_of_int (length components5) ^
   " function0_cells=" ^ string_of_int (length cells0) ^
   " function1_cells=" ^ string_of_int (length cells1) ^
   " function5_cells=" ^ string_of_int (length cells5) ^
   " function0_tokens=" ^ string_of_int (length token_items0) ^
   " function1_tokens=" ^ string_of_int (length token_items1) ^
   " function5_tokens=" ^ string_of_int (length token_items5));;

if source_id <> "prep-TSKAJXY-RIBCYXU sym" || parameter_index <> 26 ||
   length functions <> 9 || after_leaf <> 159 || numerical_cells <> 159 ||
   glue_nodes <> 158 || raw_leaves <> 11 ||
   after_component <> length components ||
   selected_component_count <> length components ||
   length cells0 <> 148 || length cells1 <> 10 || length cells5 <> 1 ||
   selected_token_count <> 2 * numerical_cells - length components then
  failwith "TSKAJXY mixed forest: final accounting drift";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_FOREST_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 source_leaves=159 source_glues=158 raw_leaves=11" ^
   " components=" ^ string_of_int (length components) ^
   " function0_components=" ^ string_of_int (length components0) ^
   " function1_components=" ^ string_of_int (length components1) ^
   " function5_components=" ^ string_of_int (length components5) ^
   " function0_cells=148 function1_cells=10 function5_cells=1" ^
   " function0_tokens=" ^ string_of_int (length token_items0) ^
   " function1_tokens=" ^ string_of_int (length token_items1) ^
   " function5_tokens=" ^ string_of_int (length token_items5));;

end;;
