(* DEVELOPMENT / NON-RELEASE exact data export from the authenticated prepared
   case-10173 input checkpoint. *)

open Benchmark_cv_compute_analytic_expr_case10173_historical_registered_input;;

let _ =
  let input = candle_case10173_historical_registered_input () in
  let export_root =
    "/project/flyspeck-candle-runs/v679i-fast-nl-prepared-input-export-dev-001" in
  let write name term =
    let text = string_of_term term in
    let path = export_root ^ "/" ^ name ^ ".term" in
    let channel = Stdlib.open_out path in
    Stdlib.output_string channel (text ^ "\n");
    Stdlib.close_out channel;
    if not (aconv (parse_term text) term) then
      failwith ("v679i prepared input roundtrip: " ^ name);
    String.length text in
  let source_bytes =
    write "source-program" input.registered_input_source_program in
  let jobs_bytes =
    write "encoded-jobs" input.registered_input_encoded_jobs in
  let roots_bytes =
    write "roots" input.registered_input_roots in
  if source_bytes <= 0 || jobs_bytes <= 0 || roots_bytes <= 0 ||
     candle_case10173_registered_input_cval_list_length
       input.registered_input_encoded_jobs <> 4173 ||
     candle_case10173_registered_input_cval_list_length
       input.registered_input_roots <> 4173 then
    failwith "v679i prepared input export validation"
  else
    print_endline
      ("CANDLE_FLYSPECK_V679I_PREPARED_INPUT_EXPORT_OK" ^
       " DEVELOPMENT_NON_RELEASE cells=4173" ^
       " source_bytes=" ^ string_of_int source_bytes ^
       " jobs_bytes=" ^ string_of_int jobs_bytes ^
       " roots_bytes=" ^ string_of_int roots_bytes);;
