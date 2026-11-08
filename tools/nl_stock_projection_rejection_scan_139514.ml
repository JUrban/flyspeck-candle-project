(* Divide-and-conquer numerical rejection scan for the 521-cell plan. *)

module Candle_nl_stock_projection_rejection_scan_139514 = struct

open Candle_nl_stock_projection_cells_139514;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let rec take_drop count values =
  if count = 0 then [],values
  else
    match values with
    | [] -> failwith "projection rejection scan: short split"
    | head :: tail ->
        let left,right = take_drop (count - 1) tail in
        head :: left,right;;

let raw_accepts selected =
  try
    let _ =
      candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
        prepared selected in
    true
  with Failure message ->
    if message = "fixed outer variable raw prover: raw batch rejected" then
      false
    else failwith message;;

let bad_indices = ref ([]:int list);;
let tested_chunks = ref 0;;
let accepted_chunks = ref 0;;
let rejected_chunks = ref 0;;

let rec scan first_index selected =
  tested_chunks := !tested_chunks + 1;
  let count = length selected in
  print_endline
    ("CANDLE_NL_STOCK_PROJECTION_REJECTION_SCAN|chunk|begin|" ^
     string_of_int first_index ^ "|" ^ string_of_int count);
  if raw_accepts selected then begin
    accepted_chunks := !accepted_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_REJECTION_SCAN|chunk|accepted|" ^
       string_of_int first_index ^ "|" ^ string_of_int count)
  end else begin
    rejected_chunks := !rejected_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_REJECTION_SCAN|chunk|rejected|" ^
       string_of_int first_index ^ "|" ^ string_of_int count);
    if count = 1 then
      bad_indices := first_index :: !bad_indices
    else
      let left_count = count / 2 in
      let left,right = take_drop left_count selected in
      scan first_index left;
      scan (first_index + left_count) right
  end;;

let _ = scan 0 cells;;

let rec join_ints = function
  | [] -> ""
  | [value] -> string_of_int value
  | value :: remaining ->
      string_of_int value ^ "," ^ join_ints remaining;;

let ordered_bad = rev !bad_indices;;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_REJECTION_SCAN_OK DEVELOPMENT_NON_RELEASE" ^
   " cells=521 tested_chunks=" ^ string_of_int !tested_chunks ^
   " accepted_chunks=" ^ string_of_int !accepted_chunks ^
   " rejected_chunks=" ^ string_of_int !rejected_chunks ^
   " bad_count=" ^ string_of_int (length ordered_bad) ^
   " bad_indices=" ^ join_ints ordered_bad);;

end;;
