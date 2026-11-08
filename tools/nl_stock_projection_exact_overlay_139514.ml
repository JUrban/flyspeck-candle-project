(* ========================================================================== *)
(* Exact-box repair probe for the sparse rejected cells of record 139514/3. *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The exact intervals below are untrusted input *)
(* proposals.  The same reflected raw checker authenticates every singleton *)
(* and the complete 521-cell batch before this probe reports success.         *)
(* ========================================================================== *)

module Candle_nl_stock_projection_exact_overlay_139514 = struct

open Candle_nl_stock_projection_cells_139514;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;

let rejected_indices =
  [22;36;109;169;218;297;298;309;310;352;356;409;416];;

let exact_shape,after_exact =
  projection_shape_build_overlay
    0 rejected_indices root_domain
    Candle_nl_stock_projection_plan_probe.precision_tree;;
let exact_cells = projection_cells_of_shape exact_shape;;

let rec selected index values = function
  | [] -> []
  | wanted :: remaining ->
      (match values with
       | [] -> failwith "projection exact overlay: index outside cell list"
       | cell :: tail ->
           if index = wanted then cell :: selected (index + 1) tail remaining
           else selected (index + 1) tail (wanted :: remaining));;

let repaired_cells = selected 0 exact_cells rejected_indices;;

if after_exact <> 521 ||
   length exact_cells <> 521 || length repaired_cells <> 13 then
  failwith "projection exact overlay: cell count drift";;

let rec check_singletons indices values =
  match indices,values with
  | [],[] -> ()
  | index :: remaining_indices,cell :: remaining_cells ->
      print_endline
        ("CANDLE_NL_STOCK_PROJECTION_EXACT_OVERLAY|singleton|begin|" ^
         string_of_int index);
      let _ =
        candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
          prepared [cell] in
      print_endline
        ("CANDLE_NL_STOCK_PROJECTION_EXACT_OVERLAY|singleton|accepted|" ^
         string_of_int index);
      check_singletons remaining_indices remaining_cells
  | _ -> failwith "projection exact overlay: singleton alignment";;

let _ = check_singletons rejected_indices repaired_cells;;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_EXACT_OVERLAY|complete-batch|begin";;
let full_result =
  candle_q_dim_taylor_model_fixed_outer_variable_raw_prove_six
    prepared exact_cells;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_EXACT_OVERLAY|complete-batch|accepted";;

if hyp full_result.variable_raw_accept_theorem <> [] ||
   hyp full_result.variable_raw_representation_theorem <> [] then
  failwith "projection exact overlay: unexpected checker assumptions";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_EXACT_OVERLAY_OK DEVELOPMENT_NON_RELEASE" ^
   " cells=521 exact_replacements=13 assumptions=0" ^
   " rejected_indices=22,36,109,169,218,297,298,309,310,352,356,409,416");;

end;;
