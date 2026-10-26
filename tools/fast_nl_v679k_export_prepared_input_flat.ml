(* DEVELOPMENT / NON-RELEASE flat exact data export from the authenticated
   prepared case-10173 input checkpoint. *)

open Benchmark_cv_compute_analytic_expr_case10173_historical_registered_input;;
open Candle_fast_nl_registered_input_flat_codec;;

let _ =
  let input = candle_case10173_historical_registered_input () in
  let export_root =
    "/project/flyspeck-candle-runs/v679k-fast-nl-prepared-input-flat-dev-001" in
  let source_path = export_root ^ "/source-program.cvdata"
  and jobs_path = export_root ^ "/encoded-jobs.cvdata"
  and roots_path = export_root ^ "/roots.cvdata" in
  let source_count =
    candle_flat_write_terms source_path
      [input.registered_input_source_program] in
  let jobs =
    candle_flat_cval_elements input.registered_input_encoded_jobs [] in
  let roots = candle_flat_cval_elements input.registered_input_roots [] in
  let jobs_count = candle_flat_write_terms jobs_path jobs
  and roots_count = candle_flat_write_terms roots_path roots in
  let source_rebuilt = candle_flat_read_terms source_path
  and jobs_rebuilt = candle_flat_cval_list (candle_flat_read_terms jobs_path)
  and roots_rebuilt = candle_flat_cval_list (candle_flat_read_terms roots_path) in
  if source_count <> 1 || jobs_count <> 4173 || roots_count <> 4173 ||
     length source_rebuilt <> 1 ||
     not (aconv (hd source_rebuilt) input.registered_input_source_program) ||
     not (aconv jobs_rebuilt input.registered_input_encoded_jobs) ||
     not (aconv roots_rebuilt input.registered_input_roots) then
    failwith "v679k prepared flat data validation"
  else
    print_endline
      "CANDLE_FLYSPECK_V679K_PREPARED_INPUT_FLAT_OK DEVELOPMENT_NON_RELEASE cells=4173 jobs_records=4173 roots_records=4173 codec=prefix-pair-num-v1";;
