(* ========================================================================== *)
(* Complete numerical rejection scan for the 161160/23 mixed forest.         *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The 5/4 interval proposals are untrusted.     *)
(* Every accepted chunk is authenticated by the reflected raw checker; a    *)
(* rejected chunk is bisected until every rejecting source leaf is known.    *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_rejection_scan_161160 = struct

open Candle_nl_stock_projection_mixed_forest_161160;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let rec take_drop count values =
  if count = 0 then [],values
  else
    match values with
    | [] -> failwith "projection mixed rejection scan: short split"
    | head :: tail ->
        let left,right = take_drop (count - 1) tail in
        head :: left,right;;

let tested_chunks = ref 0;;
let accepted_chunks = ref 0;;
let rejected_chunks = ref 0;;
let bad0 = ref ([]:int list);;
let bad1 = ref ([]:int list);;

let raw_accepts prepared indexed_cells =
  try
    let _ =
      candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
        prepared (map snd indexed_cells) in
    true
  with Failure message ->
    if message = "fixed outer variable raw prover: raw batch rejected" then
      false
    else failwith message;;

let rec scan selected prepared bad indexed_cells =
  tested_chunks := !tested_chunks + 1;
  let count = length indexed_cells in
  let first_source = fst (hd indexed_cells) in
  let last_source = fst (last indexed_cells) in
  print_endline
    ("CANDLE_NL_STOCK_PROJECTION_MIXED_REJECTION_SCAN|chunk|begin" ^
     "|function=" ^ string_of_int selected ^
     "|first_source=" ^ string_of_int first_source ^
     "|last_source=" ^ string_of_int last_source ^
     "|count=" ^ string_of_int count);
  if raw_accepts prepared indexed_cells then begin
    accepted_chunks := !accepted_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_MIXED_REJECTION_SCAN|chunk|accepted" ^
       "|function=" ^ string_of_int selected ^
       "|first_source=" ^ string_of_int first_source ^
       "|last_source=" ^ string_of_int last_source ^
       "|count=" ^ string_of_int count)
  end else begin
    rejected_chunks := !rejected_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_MIXED_REJECTION_SCAN|chunk|rejected" ^
       "|function=" ^ string_of_int selected ^
       "|first_source=" ^ string_of_int first_source ^
       "|last_source=" ^ string_of_int last_source ^
       "|count=" ^ string_of_int count);
    if count = 1 then bad := first_source :: !bad
    else
      let left_count = count / 2 in
      let left,right = take_drop left_count indexed_cells in
      scan selected prepared bad left;
      scan selected prepared bad right
  end;;

let started = Unix.gettimeofday ();;
let _ = scan 0 (prepared_for 0) bad0 indexed_cells0;;
let _ = scan 1 (prepared_for 1) bad1 indexed_cells1;;
let elapsed = Unix.gettimeofday () -. started;;

let ordered_bad0 = rev !bad0;;
let ordered_bad1 = rev !bad1;;

let rec join_ints = function
  | [] -> ""
  | [value] -> string_of_int value
  | value :: remaining ->
      string_of_int value ^ "," ^ join_ints remaining;;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_MIXED_REJECTION_SCAN_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-1611600345x" ^
   " parameter_index=23 function0_cells=" ^
     string_of_int (length indexed_cells0) ^
   " function1_cells=" ^ string_of_int (length indexed_cells1) ^
   " tested_chunks=" ^ string_of_int !tested_chunks ^
   " accepted_chunks=" ^ string_of_int !accepted_chunks ^
   " rejected_chunks=" ^ string_of_int !rejected_chunks ^
   " function0_bad_count=" ^ string_of_int (length ordered_bad0) ^
   " function0_bad_indices=" ^ join_ints ordered_bad0 ^
   " function1_bad_count=" ^ string_of_int (length ordered_bad1) ^
   " function1_bad_indices=" ^ join_ints ordered_bad1 ^
   " elapsed_seconds=" ^ string_of_float elapsed);;

end;;
