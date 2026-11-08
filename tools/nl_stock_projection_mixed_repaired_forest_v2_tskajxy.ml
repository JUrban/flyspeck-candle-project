(* ========================================================================== *)
(* Two-level sparse repair of the TSKAJXY/26 function-0 forest.             *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The exact child scan proved that only 11L,   *)
(* 11R, 19L, 19R, and 27L reject after the first axis-1 split.  Those five  *)
(* children alone are bisected on axis 2.  Every retained cell remains an   *)
(* untrusted proposal until the reflected checker accepts it.                *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_repaired_forest_v2_tskajxy = struct

open Candle_nl_stock_projection_mixed_forest_tskajxy;;
open Candle_nl_stock_projection_mixed_repaired_forest_tskajxy;;

let second_level_children =
  [(11,0);(11,1);(19,0);(19,1);(27,0)];;

let child_needs_second_level source_index side =
  List.mem (source_index,side) second_level_children;;

let repaired_v2_child_cells source_index side domain =
  if child_needs_second_level source_index side then
    let left_domain,right_domain =
      M_verifier.split_domain 6 6 2 domain in
    [source_index,projection_mixed_cell 0 left_domain;
     source_index,projection_mixed_cell 0 right_domain]
  else [source_index,projection_mixed_cell 0 domain];;

let repaired_v2_child_tokens source_index side =
  if child_needs_second_level source_index side then
    [Projection_mixed_token_leaf;
     Projection_mixed_token_leaf;
     Projection_mixed_token_glue 2]
  else [Projection_mixed_token_leaf];;

let rec repaired_v2_indexed_cells = function
  | Projection_mixed_leaf (source_index,selected,_,domain,cell) ->
      if List.mem source_index repaired_source_indices then begin
        if selected <> 0 then
          failwith "TSKAJXY repaired v2 forest: repaired nonzero function";
        let left_domain,right_domain =
          M_verifier.split_domain 6 6 1 domain in
        repaired_v2_child_cells source_index 0 left_domain @
        repaired_v2_child_cells source_index 1 right_domain
      end else [source_index,cell]
  | Projection_mixed_node (_,_,left,right) ->
      repaired_v2_indexed_cells left @ repaired_v2_indexed_cells right;;

let rec repaired_v2_tokens = function
  | Projection_mixed_leaf (source_index,_,_,_,_) ->
      if List.mem source_index repaired_source_indices then
        repaired_v2_child_tokens source_index 0 @
        repaired_v2_child_tokens source_index 1 @
        [Projection_mixed_token_glue 1]
      else [Projection_mixed_token_leaf]
  | Projection_mixed_node (axis,_,left,right) ->
      repaired_v2_tokens left @ repaired_v2_tokens right @
      [Projection_mixed_token_glue axis];;

let repaired_v2_indexed_cells0 =
  List.flatten
    (map
      (fun component ->
        repaired_v2_indexed_cells component.projection_component_shape)
      components0);;
let repaired_v2_cells0 = map snd repaired_v2_indexed_cells0;;
let repaired_v2_token_data0 =
  List.flatten
    (map
      (fun component ->
        repaired_v2_tokens component.projection_component_shape)
      components0);;
let repaired_v2_token_items0 =
  map projection_mixed_logical_token repaired_v2_token_data0;;
let repaired_v2_logical_tokens0 = logical_tokens repaired_v2_token_items0;;
let repaired_v2_encoded_tokens0 = encoded_tokens repaired_v2_token_data0;;

let rec repaired_v2_focus_cells = function
  | [] -> []
  | (source_index,side) :: remaining ->
      let rec find_shape = function
        | Projection_mixed_leaf (index,_,_,domain,_) ->
            if index = source_index then Some domain else None
        | Projection_mixed_node (_,_,left,right) ->
            (match find_shape left with
             | Some domain -> Some domain
             | None -> find_shape right) in
      let rec find_components = function
        | [] -> None
        | component :: rest ->
            (match find_shape component.projection_component_shape with
             | Some domain -> Some domain
             | None -> find_components rest) in
      let original_domain =
        match find_components components0 with
        | Some domain -> domain
        | None ->
            failwith "TSKAJXY repaired v2 forest: missing focus source" in
      let left_domain,right_domain =
        M_verifier.split_domain 6 6 1 original_domain in
      let child_domain = if side = 0 then left_domain else right_domain in
      let grandchild_left,grandchild_right =
        M_verifier.split_domain 6 6 2 child_domain in
      projection_mixed_cell 0 grandchild_left ::
      projection_mixed_cell 0 grandchild_right ::
      repaired_v2_focus_cells remaining;;

let repaired_v2_focus_cells0 =
  repaired_v2_focus_cells second_level_children;;

if length second_level_children <> 5 ||
   length repaired_v2_focus_cells0 <> 10 ||
   length repaired_v2_cells0 <> 193 ||
   length repaired_v2_token_items0 <> 378 then
  failwith "TSKAJXY repaired v2 forest: accounting drift";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED_FOREST_V2_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 original_function0_cells=148" ^
   " first_level_source_leaves=40 second_level_children=5" ^
   " repaired_function0_cells=193 repaired_function0_tokens=378" ^
   " first_split_axis=1 second_split_axis=2 maximum_added_depth=2");;

end;;
