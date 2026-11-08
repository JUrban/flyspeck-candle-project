(* ========================================================================== *)
(* Bounded sparse subdivision repair for projection record 139514/3.        *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  Candidate interval factors and subdivisions  *)
(* are untrusted proposals.  The reflected raw checker authenticates every  *)
(* retained leaf and then the complete repaired batch.                        *)
(* ========================================================================== *)

module Candle_nl_stock_projection_sparse_repair_139514 = struct

open Certificate;;
open Candle_nl_stock_projection_cells_139514;;
open Candle_cv_analytic_expr_stable_program_data;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let rejected_indices =
  [22;36;109;169;218;297;298;309;310;352;356;409;416];;

let root_factor_candidates = [(1001,1000);(101,100);(21,20);(11,10)];;
let child_factor_candidates =
  [(5,4);(1001,1000);(101,100);(21,20);(11,10)];;
let maximum_repair_depth = 6;;

let attempts = ref 0;;
let rejected_attempts = ref 0;;
let accepted_attempts = ref 0;;
let split_count = ref 0;;
let maximum_depth_reached = ref 0;;

let raw_accepts cell =
  try
    let _ =
      candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
        prepared [cell] in
    true
  with Failure message ->
    if message = "fixed outer variable raw prover: raw batch rejected" then
      false
    else failwith message;;

let rec try_factors index depth domain = function
  | [] -> None
  | (numerator,denominator) :: remaining ->
      attempts := !attempts + 1;
      print_endline
        ("CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR|factor|begin|" ^
         string_of_int index ^ "|" ^ string_of_int depth ^ "|" ^
         string_of_int numerator ^ "/" ^ string_of_int denominator);
      let cell = projection_factor_cell numerator denominator domain in
      if raw_accepts cell then begin
        accepted_attempts := !accepted_attempts + 1;
        print_endline
          ("CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR|factor|accepted|" ^
           string_of_int index ^ "|" ^ string_of_int depth ^ "|" ^
           string_of_int numerator ^ "/" ^ string_of_int denominator);
        Some cell
      end else begin
        rejected_attempts := !rejected_attempts + 1;
        print_endline
          ("CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR|factor|rejected|" ^
           string_of_int index ^ "|" ^ string_of_int depth ^ "|" ^
           string_of_int numerator ^ "/" ^ string_of_int denominator);
        try_factors index depth domain remaining
      end;;

let rec repair_leaf index depth domain =
  maximum_depth_reached := max !maximum_depth_reached depth;
  let factors =
    if depth = 0 then root_factor_candidates else child_factor_candidates in
  match try_factors index depth domain factors with
  | Some cell -> Projection_leaf cell
  | None ->
      if depth >= maximum_repair_depth then
        failwith
          ("projection sparse repair: depth cap at cell " ^
           string_of_int index);
      let axis = (depth mod 6) + 1 in
      split_count := !split_count + 1;
      print_endline
        ("CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR|split|" ^
         string_of_int index ^ "|" ^ string_of_int depth ^ "|" ^
         string_of_int axis);
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      let left = repair_leaf index (depth + 1) left_domain in
      let right = repair_leaf index (depth + 1) right_domain in
      Projection_node (axis,left,right);;

let rec build_repaired_shape next_leaf domain = function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index <> 0 || raw_flag then
        failwith "projection sparse repair: unexpected pass selection";
      let shape =
        if List.mem next_leaf rejected_indices then
          repair_leaf next_leaf 0 domain
        else Projection_leaf (projection_cell domain) in
      shape,next_leaf + 1
  | P_result_glue (_,split_index,convex_flag,left,right) ->
      if convex_flag then
        failwith "projection sparse repair: unexpected convex glue";
      let axis = split_index + 1 in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 axis domain in
      let left_shape,after_left =
        build_repaired_shape next_leaf left_domain left in
      let right_shape,after_right =
        build_repaired_shape after_left right_domain right in
      Projection_node (axis,left_shape,right_shape),after_right
  | P_result_mono _ ->
      failwith "projection sparse repair: unexpected monotonicity node"
  | P_result_ref _ ->
      failwith "projection sparse repair: unexpected reference node";;

let repaired_shape,after_repair =
  build_repaired_shape
    0 root_domain Candle_nl_stock_projection_plan_probe.precision_tree;;
let repaired_cells = projection_cells_of_shape repaired_shape;;
let repaired_token_data = projection_tokens_of_shape repaired_shape;;
let repaired_token_items =
  map projection_logical_token repaired_token_data;;
let repaired_tokens =
  mk_list
    (repaired_token_items,
     type_of
       `Candle_q_dim_taylor_model_fixed_outer_variable_compact_leaf`);;
let repaired_encoded_tokens =
  candle_q_dim_stable_program_cval_list
    (map projection_encoded_token repaired_token_data);;

if after_repair <> 521 ||
   length repaired_cells <> 521 + !split_count ||
   length repaired_token_items <> 1041 + 2 * !split_count then
  failwith "projection sparse repair: repaired shape drift";;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR|complete-batch|begin";;
let full_result =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
    prepared repaired_cells;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR|complete-batch|accepted";;

if hyp full_result.variable_raw_accept_theorem <> [] ||
   hyp full_result.variable_raw_representation_theorem <> [] then
  failwith "projection sparse repair: complete checker assumptions";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_SPARSE_REPAIR_OK DEVELOPMENT_NON_RELEASE" ^
   " original_cells=521 repaired_cells=" ^
   string_of_int (length repaired_cells) ^
   " repaired_token_items=" ^ string_of_int (length repaired_token_items) ^
   " sparse_original_leaves=13 splits=" ^ string_of_int !split_count ^
   " attempts=" ^ string_of_int !attempts ^
   " accepted_attempts=" ^ string_of_int !accepted_attempts ^
   " rejected_attempts=" ^ string_of_int !rejected_attempts ^
   " maximum_depth=" ^ string_of_int !maximum_depth_reached ^
   " assumptions=0");;

end;;
