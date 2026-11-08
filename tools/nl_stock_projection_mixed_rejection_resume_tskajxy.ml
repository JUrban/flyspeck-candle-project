(* ========================================================================== *)
(* Resume the timed-out TSKAJXY/26 rejection scan at its exact clean suffix. *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The preserved first scan fully classified    *)
(* function-0 source indices through 136.  This checks only 137--156 and the *)
(* two smaller selected-function forests.                                    *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_rejection_resume_tskajxy = struct

open Candle_nl_stock_projection_mixed_forest_tskajxy;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let rec take_drop count values =
  if count = 0 then [],values
  else
    match values with
    | [] -> failwith "TSKAJXY rejection resume: short split"
    | head :: tail ->
        let left,right = take_drop (count - 1) tail in
        head :: left,right;;

let tested_chunks = ref 0;;
let accepted_chunks = ref 0;;
let rejected_chunks = ref 0;;
let bad0 = ref ([]:int list);;
let bad1 = ref ([]:int list);;
let bad5 = ref ([]:int list);;

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
  if raw_accepts prepared indexed_cells then begin
    accepted_chunks := !accepted_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_RESUME|accepted" ^
       "|function=" ^ string_of_int selected ^
       "|first_source=" ^ string_of_int first_source ^
       "|last_source=" ^ string_of_int last_source ^
       "|count=" ^ string_of_int count)
  end else begin
    rejected_chunks := !rejected_chunks + 1;
    print_endline
      ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_RESUME|rejected" ^
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

let remaining0 =
  List.filter (fun (source_index,_) -> source_index >= 137) indexed_cells0;;
if length remaining0 <> 19 || fst (hd remaining0) <> 137 ||
   fst (last remaining0) <> 156 then
  failwith "TSKAJXY rejection resume: suffix identity drift";;

let _ = scan 0 (prepared_for 0) bad0 remaining0;;
let _ = scan 1 (prepared_for 1) bad1 indexed_cells1;;
let _ = scan 5 (prepared_for 5) bad5 indexed_cells5;;

let ordered_bad0 = rev !bad0
and ordered_bad1 = rev !bad1
and ordered_bad5 = rev !bad5;;

let rec join_ints = function
  | [] -> ""
  | [value] -> string_of_int value
  | value :: remaining ->
      string_of_int value ^ "," ^ join_ints remaining;;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_REJECTION_RESUME_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 function0_suffix_cells=19 function1_cells=10" ^
   " function5_cells=1 tested_chunks=" ^ string_of_int !tested_chunks ^
   " accepted_chunks=" ^ string_of_int !accepted_chunks ^
   " rejected_chunks=" ^ string_of_int !rejected_chunks ^
   " function0_bad_count=" ^ string_of_int (length ordered_bad0) ^
   " function0_bad_indices=" ^ join_ints ordered_bad0 ^
   " function1_bad_count=" ^ string_of_int (length ordered_bad1) ^
   " function1_bad_indices=" ^ join_ints ordered_bad1 ^
   " function5_bad_count=" ^ string_of_int (length ordered_bad5) ^
   " function5_bad_indices=" ^ join_ints ordered_bad5);;

end;;
