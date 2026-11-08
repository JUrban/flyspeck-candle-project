(* ========================================================================== *)
(* Classify only the 80 one-level repair children for TSKAJXY/26.            *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The 108 unchanged function-0 cells and both  *)
(* smaller function forests already passed the exact rejection scans.  This *)
(* bounded binary scan distinguishes the left/right children that still need *)
(* refinement without replaying those known-good cells at every scan level.  *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_repaired_child_scan_tskajxy = struct

open Candle_nl_stock_projection_mixed_forest_tskajxy;;
open Candle_nl_stock_projection_mixed_repaired_forest_tskajxy;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let rec take_drop count values =
  if count = 0 then [],values
  else
    match values with
    | [] -> failwith "TSKAJXY repaired child scan: short split"
    | head :: tail ->
        let left,right = take_drop (count - 1) tail in
        head :: left,right;;

let rec label_repaired_children seen = function
  | [] -> []
  | (source_index,cell) :: remaining ->
      if List.mem source_index repaired_source_indices then
        let side = if List.mem source_index seen then 1 else 0 in
        let next_seen =
          if side = 0 then source_index :: seen else seen in
        (source_index,side,cell) ::
          label_repaired_children next_seen remaining
      else label_repaired_children seen remaining;;

let repaired_children =
  label_repaired_children [] repaired_indexed_cells0;;

let tested_chunks = ref 0;;
let accepted_chunks = ref 0;;
let rejected_chunks = ref 0;;
let bad_children = ref ([]:(int * int) list);;

let raw_accepts indexed_cells =
  try
    let _ =
      candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
        (prepared_for 0)
        (map (fun (_,_,cell) -> cell) indexed_cells) in
    true
  with Failure message ->
    if message = "fixed outer variable raw prover: raw batch rejected" then
      false
    else failwith message;;

let child_name (source_index,side,_) =
  string_of_int source_index ^ (if side = 0 then "L" else "R");;

let rec scan indexed_cells =
  tested_chunks := !tested_chunks + 1;
  let count = length indexed_cells in
  let first_name = child_name (hd indexed_cells) in
  let last_name = child_name (last indexed_cells) in
  print_endline
    ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_CHILD_SCAN|begin" ^
     "|first=" ^ first_name ^ "|last=" ^ last_name ^
     "|count=" ^ string_of_int count);
  if raw_accepts indexed_cells then begin
    accepted_chunks := !accepted_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_CHILD_SCAN|accepted" ^
       "|first=" ^ first_name ^ "|last=" ^ last_name ^
       "|count=" ^ string_of_int count)
  end else begin
    rejected_chunks := !rejected_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_CHILD_SCAN|rejected" ^
       "|first=" ^ first_name ^ "|last=" ^ last_name ^
       "|count=" ^ string_of_int count);
    if count = 1 then
      let source_index,side,_ = hd indexed_cells in
      bad_children := (source_index,side) :: !bad_children
    else
      let left_count = count / 2 in
      let left,right = take_drop left_count indexed_cells in
      scan left;
      scan right
  end;;

let rec join_children = function
  | [] -> ""
  | [(source_index,side)] ->
      string_of_int source_index ^ (if side = 0 then "L" else "R")
  | (source_index,side) :: remaining ->
      string_of_int source_index ^ (if side = 0 then "L," else "R,") ^
      join_children remaining;;

if length repaired_children <> 80 then
  failwith "TSKAJXY repaired child scan: candidate count drift";;

let started = Unix.gettimeofday ();;
let _ = scan repaired_children;;
let elapsed = Unix.gettimeofday () -. started;;
let ordered_bad_children = rev !bad_children;;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_CHILD_SCAN_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 candidate_children=80 tested_chunks=" ^
   string_of_int !tested_chunks ^
   " accepted_chunks=" ^ string_of_int !accepted_chunks ^
   " rejected_chunks=" ^ string_of_int !rejected_chunks ^
   " bad_child_count=" ^ string_of_int (length ordered_bad_children) ^
   " bad_children=" ^ join_children ordered_bad_children ^
   " elapsed_seconds=" ^ string_of_float elapsed);;

end;;
