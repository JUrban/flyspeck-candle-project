(* ========================================================================== *)
(* One-level sparse repair of the TSKAJXY/26 function-0 forest.              *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The exact rejection scans identified 40      *)
(* source leaves.  Each is bisected once on axis 1; both child cells retain  *)
(* the ordinary 5/4 proposal and are authenticated by the reflected checker. *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_repaired_forest_tskajxy = struct

open Candle_nl_stock_projection_mixed_forest_tskajxy;;

let repaired_source_indices =
  [2;3;4;5;7;11;12;13;15;19;20;21;23;27;38;39;43;44;48;49;
   61;62;65;66;70;71;75;76;85;88;91;95;98;101;102;106;107;111;
   112;149];;

let rec repaired_indexed_cells = function
  | Projection_mixed_leaf (source_index,selected,_,domain,cell) ->
      if List.mem source_index repaired_source_indices then
        let left_domain,right_domain =
          M_verifier.split_domain 6 6 1 domain in
        [source_index,projection_mixed_cell selected left_domain;
         source_index,projection_mixed_cell selected right_domain]
      else [source_index,cell]
  | Projection_mixed_node (_,_,left,right) ->
      repaired_indexed_cells left @ repaired_indexed_cells right;;

let rec repaired_tokens = function
  | Projection_mixed_leaf (source_index,_,_,_,_) ->
      if List.mem source_index repaired_source_indices then
        [Projection_mixed_token_leaf;
         Projection_mixed_token_leaf;
         Projection_mixed_token_glue 1]
      else [Projection_mixed_token_leaf]
  | Projection_mixed_node (axis,_,left,right) ->
      repaired_tokens left @ repaired_tokens right @
      [Projection_mixed_token_glue axis];;

let repaired_indexed_cells0 =
  List.flatten
    (map
      (fun component ->
        repaired_indexed_cells component.projection_component_shape)
      components0);;
let repaired_cells0 = map snd repaired_indexed_cells0;;
let repaired_token_data0 =
  List.flatten
    (map
      (fun component -> repaired_tokens component.projection_component_shape)
      components0);;
let repaired_token_items0 =
  map projection_mixed_logical_token repaired_token_data0;;
let repaired_logical_tokens0 = logical_tokens repaired_token_items0;;
let repaired_encoded_tokens0 = encoded_tokens repaired_token_data0;;

let rec count_occurrences target = function
  | [] -> 0
  | value :: remaining ->
      (if value = target then 1 else 0) + count_occurrences target remaining;;
let repaired_source_stream = map fst repaired_indexed_cells0;;

if length repaired_source_indices <> 40 ||
   length repaired_cells0 <> 188 ||
   length repaired_token_items0 <> 368 ||
   not
     (List.for_all
       (fun source_index ->
         count_occurrences source_index repaired_source_stream = 2)
       repaired_source_indices) then
  failwith "TSKAJXY repaired forest: accounting drift";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REPAIRED_FOREST_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 original_function0_cells=148 repaired_leaves=40" ^
   " repaired_function0_cells=188 original_function0_tokens=288" ^
   " repaired_function0_tokens=368 split_axis=1 maximum_added_depth=1");;

end;;
