(* DEVELOPMENT / NON-RELEASE.
   Export the exact corrected tag-10 equation environment and a bounded
   genuine 16-record call from the already-authenticated prepared-input
   checkpoint.  This performs no numerical evaluation. *)

#use "/project/worktrees/candle-fast-nl-historical-tag10-v1/candle/benchmark_cv_compute_registered_hol4_export.ml";;

module Candle_fast_nl_export_tag10_hol4_data = struct

open Benchmark_cv_compute_registered_hol4_export;;
open Candle_cv_analytic_expr_case10173_historical_dihedral_checked_compute;;
open Candle_fast_nl_v679l_prepared_input;;

let rec candle_tag10_cval_take count encoded =
  if count = 0 then parse_term "Cexp_num 0"
  else
    let operator,arguments = strip_comb encoded in
    let name,_ = dest_const operator in
    match name,arguments with
    | "Cexp_pair",[head;tail] ->
        list_mk_comb
          (parse_term "Cexp_pair",
           [head;candle_tag10_cval_take (count - 1) tail])
    | _ -> failwith "tag10 HOL4 export: short or malformed cval list";;

let candle_tag10_output_path =
  "/project/flyspeck-candle-runs/v680-fast-nl-tag10-hol4-data-generated-dev-002/compute_registeredCase10173HistoricalChunk16DataScript.sml";;

let candle_tag10_all_equations =
  candle_cv_case10173_hist_checked_program_compute_eqs;;

let candle_tag10_operator,candle_tag10_arguments =
  strip_comb candle_v679l_checked_call;;

let candle_tag10_source,candle_tag10_jobs,candle_tag10_roots =
  match candle_tag10_arguments with
  | [source;jobs;roots] -> source,jobs,roots
  | _ -> failwith "tag10 HOL4 export: malformed checked call";;

let candle_tag10_chunk16_call =
  list_mk_comb
    (candle_tag10_operator,
     [candle_tag10_source;
      candle_tag10_cval_take 16 candle_tag10_jobs;
      candle_tag10_cval_take 16 candle_tag10_roots]);;

let candle_tag10_equations =
  candle_registered_equation_slice
    candle_tag10_all_equations candle_tag10_chunk16_call;;

let _ =
  if length candle_tag10_equations < 344 then
    failwith "tag10 HOL4 export: incomplete reachable equation set";
  let channel = open_out candle_tag10_output_path in
  candle_registered_write_data_theory channel
    "Mechanically exported corrected tag-10 genuine 16-cell case-10173 checked-call prefix."
    "compute_registeredCase10173HistoricalChunk16Data"
    "registered_case10173_historical_chunk16_ceqs"
    "registered_case10173_historical_chunk16_cexp"
    "registered_case10173_historical_chunk16_result"
    candle_tag10_equations candle_tag10_chunk16_call
      (parse_term "Cexp_num 1");
  close_out channel;
  print_endline
    ("CANDLE_FAST_NL_TAG10_HOL4_DATA_EXPORTED DEVELOPMENT_NON_RELEASE" ^
     " cells=16 equations=" ^ string_of_int (length candle_tag10_equations) ^
     " numerical_compute=0 path=" ^
     candle_tag10_output_path);;

end;;
