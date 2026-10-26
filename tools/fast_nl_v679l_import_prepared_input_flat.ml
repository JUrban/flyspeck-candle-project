(* DEVELOPMENT / NON-RELEASE exact prepared-input import.  Large values stay
   inside a module so the interactive printer exposes types, not term bytes. *)

module Candle_fast_nl_v679l_prepared_input = struct

open Candle_fast_nl_registered_input_flat_codec;;

let candle_v679l_data_root =
  "/project/flyspeck-candle-runs/v679k-fast-nl-prepared-input-flat-dev-001";;

let candle_v679l_source_terms =
  candle_flat_read_terms (candle_v679l_data_root ^ "/source-program.cvdata");;

let candle_v679l_job_records =
  candle_flat_read_terms (candle_v679l_data_root ^ "/encoded-jobs.cvdata");;

let candle_v679l_root_records =
  candle_flat_read_terms (candle_v679l_data_root ^ "/roots.cvdata");;

let candle_v679l_source_program =
  match candle_v679l_source_terms with
  | [source] -> source
  | _ -> failwith "v679l source-program record count";;

let candle_v679l_encoded_jobs = candle_flat_cval_list candle_v679l_job_records;;
let candle_v679l_roots = candle_flat_cval_list candle_v679l_root_records;;

let candle_v679l_checked_call =
  list_mk_comb
    (`candle_cv_case10173_hist_checked_raw_jobs_check`,
     [candle_v679l_source_program;
      candle_v679l_encoded_jobs;
      candle_v679l_roots]);;

let candle_v679l_valid =
  let operator,arguments = strip_comb candle_v679l_checked_call in
  match arguments with
  | [source;jobs;roots] ->
      length candle_v679l_job_records = 4173 &&
      length candle_v679l_root_records = 4173 &&
      is_const operator &&
      fst (dest_const operator) =
        "candle_cv_case10173_hist_checked_raw_jobs_check" &&
      aconv source candle_v679l_source_program &&
      aconv jobs candle_v679l_encoded_jobs &&
      aconv roots candle_v679l_roots
  | _ -> false;;

end;;

let candle_v679l_axioms_after = axioms ();;

if not Candle_fast_nl_v679l_prepared_input.candle_v679l_valid ||
   List.length candle_v679l_axioms_after <>
     List.length candle_v679l_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679l_axioms_before)
       candle_v679l_axioms_after) then
  failwith "v679l prepared-input validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679L_PREPARED_INPUT_FLAT_CHECKPOINT_READY DEVELOPMENT_NON_RELEASE cells=4173 numerical_compute=0 assumptions=0 axiom_growth=0";;
