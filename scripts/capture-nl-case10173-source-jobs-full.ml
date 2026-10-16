(* ========================================================================== *)
(* Capture all authenticated source-side inputs for the case-10173 fast path. *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE / NON-AUTHORITATIVE.  This emits only the exact  *)
(* rational boxes and square-root intervals already held by the prepared      *)
(* 4,173-cell plan.  It creates no numerical verdict or theorem evidence.     *)
(* ========================================================================== *)

module Capture_nl_case10173_source_jobs_full = struct

open Candle_cv_analytic_expr_jet_prove;;
open Candle_cv_analytic_expr_stable_batch_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_batch_prove;;
open Benchmark_cv_compute_analytic_expr_case10173_variable_raw_plan;;

let rational term =
  Num.string_of_num (rat_of_term term);;

let vector terms =
  String.concat "," (map rational terms);;

let q_data term =
  let signed,denominator_predecessor = dest_pair term in
  let positive,negative = dest_pair signed in
  let numerator =
    Num.sub_num (dest_numeral positive) (dest_numeral negative) in
  let denominator =
    Num.add_num (dest_numeral denominator_predecessor)
      (Num.num_of_int 1) in
  Num.string_of_num (Num.div_num numerator denominator);;

let interval term =
  let lower,upper = dest_pair term in
  q_data lower ^ ":" ^ q_data upper;;

let intervals terms =
  String.concat "," (map interval terms);;

let rec emit index = function
  | [] -> index
  | cell :: cells ->
      let stable = cell.variable_batch_stable_cell in
      if length cell.variable_batch_box_intervals <> 7 ||
         length stable.stable_batch_center_intervals <> 7 ||
         length stable.stable_batch_lower <> 6 ||
         length stable.stable_batch_upper <> 6 then
        failwith "case10173 full source capture: cell shape drift";
      print_endline
        ("CANDLE_CV_NL_NATIVE_JOB\t10173\t" ^ string_of_int index ^ "\t" ^
         intervals cell.variable_batch_box_intervals ^ "\t" ^
         intervals stable.stable_batch_center_intervals ^ "\t" ^
         vector stable.stable_batch_lower ^ "\t" ^
         vector stable.stable_batch_upper);
      emit (index + 1) cells;;

let _ =
  let axioms_before = axioms () in
  let plan = candle_case10173_variable_raw_plan () in
  let count = emit 0 plan.case10173_variable_raw_plan_cells in
  if count <> 4173 then
    failwith "case10173 full source capture: cell count drift";
  let axioms_after = axioms () in
  if length axioms_after <> length axioms_before ||
     not (List.for_all (fun axiom -> List.mem axiom axioms_before) axioms_after)
  then failwith "case10173 full source capture: axiom-set drift";
  print_endline
    "CANDLE_CV_CASE10173_SOURCE_JOBS_FULL_OK DEVELOPMENT_NON_RELEASE cells=4173 sqrt_slots=7 assumptions=0 axiom_growth=0";;

end;;
