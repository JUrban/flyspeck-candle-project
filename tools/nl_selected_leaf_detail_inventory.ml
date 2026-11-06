(* ========================================================================== *)
(* Detailed selected-leaf inventory for the direct Flyspeck NL corpus.       *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  This is a read-only inventory over the        *)
(* already-loaded Break_case_exec data.  It records the historical C++       *)
(* estimate and production iargs path shape for every explicit Iarg_leaf.    *)
(* It does not claim to know the numerical-certificate cell count or the      *)
(* internal certificate topology; those require a separate certificate join. *)
(* ========================================================================== *)

module Candle_nl_selected_leaf_detail_inventory = struct

let marker = "CANDLE_NL_SELECTED_LEAF_DETAIL|";;

let total_sources = ref 0;;
let total_leaves = ref 0;;
let total_nodes = ref 0;;
let total_historical_msec = ref 0;;
let global_max_depth = ref 0;;

let emit_source source_id =
  let source_leaves = ref 0 in
  let source_nodes = ref 0 in
  let source_historical_msec = ref 0 in
  let source_max_depth = ref 0 in
  let rec walk depth bisects facets = function
    | Iarg_leaf historical_msec ->
        let leaf_index = !source_leaves in
        source_leaves := leaf_index + 1;
        source_nodes := !source_nodes + 1;
        source_historical_msec := !source_historical_msec + historical_msec;
        source_max_depth := max !source_max_depth depth;
        print_endline
          (marker ^ source_id ^ "|" ^ string_of_int leaf_index ^ "|" ^
           string_of_int historical_msec ^ "|" ^ string_of_int depth ^ "|" ^
           string_of_int bisects ^ "|" ^ string_of_int facets)
    | Iarg_bisect (_,left,right) ->
        source_nodes := !source_nodes + 1;
        walk (depth + 1) (bisects + 1) facets left;
        walk (depth + 1) (bisects + 1) facets right
    | Iarg_facet (_,_,_,residual) ->
        source_nodes := !source_nodes + 1;
        walk (depth + 1) bisects (facets + 1) residual in
  let _ = walk 0 0 0 (Break_case_exec.get_iarg source_id) in
  total_sources := !total_sources + 1;
  total_leaves := !total_leaves + !source_leaves;
  total_nodes := !total_nodes + !source_nodes;
  total_historical_msec :=
    !total_historical_msec + !source_historical_msec;
  global_max_depth := max !global_max_depth !source_max_depth;
  print_endline
    ("CANDLE_NL_SELECTED_SOURCE_DETAIL|" ^ source_id ^ "|" ^
     string_of_int !source_leaves ^ "|" ^ string_of_int !source_nodes ^ "|" ^
     string_of_int !source_historical_msec ^ "|" ^
     string_of_int !source_max_depth);;

let _ = do_list emit_source Break_case_exec.all_idv;;

if !total_sources <> 812 then
  failwith "NL selected-leaf detail inventory: source-count drift";;

if !total_leaves <> 7814 then
  failwith "NL selected-leaf detail inventory: selected-leaf-count drift";;

print_endline
  ("CANDLE_NL_SELECTED_LEAF_DETAIL_SUMMARY|" ^
   string_of_int !total_sources ^ "|" ^ string_of_int !total_leaves ^ "|" ^
   string_of_int !total_nodes ^ "|" ^
   string_of_int !total_historical_msec ^ "|" ^
   string_of_int !global_max_depth);;

end;;
