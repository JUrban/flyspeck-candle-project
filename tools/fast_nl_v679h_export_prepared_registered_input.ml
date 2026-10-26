(* DEVELOPMENT / NON-RELEASE exact data export from the authenticated prepared
   case-10173 input checkpoint. *)

open Benchmark_cv_compute_analytic_expr_case10173_historical_registered_input;;

let candle_v679h_input =
  candle_case10173_historical_registered_input ();;

let candle_v679h_export_root =
  "/project/flyspeck-candle-runs/v679h-fast-nl-prepared-input-export-dev-001";;

let candle_v679h_write name term =
  let text = string_of_term term in
  let path = candle_v679h_export_root ^ "/" ^ name ^ ".term" in
  let channel = Stdlib.open_out path in
  Stdlib.output_string channel text;
  Stdlib.output_char channel '\n';
  Stdlib.close_out channel;
  if not (aconv (parse_term text) term) then
    failwith ("v679h prepared input roundtrip: " ^ name);
  String.length text;;

let candle_v679h_source_bytes =
  candle_v679h_write "source-program"
    candle_v679h_input.registered_input_source_program;;

let candle_v679h_jobs_bytes =
  candle_v679h_write "encoded-jobs"
    candle_v679h_input.registered_input_encoded_jobs;;

let candle_v679h_roots_bytes =
  candle_v679h_write "roots"
    candle_v679h_input.registered_input_roots;;

if candle_v679h_source_bytes <= 0 ||
   candle_v679h_jobs_bytes <= 0 ||
   candle_v679h_roots_bytes <= 0 ||
   candle_case10173_registered_input_cval_list_length
     candle_v679h_input.registered_input_encoded_jobs <> 4173 ||
   candle_case10173_registered_input_cval_list_length
     candle_v679h_input.registered_input_roots <> 4173 then
  failwith "v679h prepared input export validation"
else
  print_endline
    ("CANDLE_FLYSPECK_V679H_PREPARED_INPUT_EXPORT_OK" ^
     " DEVELOPMENT_NON_RELEASE cells=4173" ^
     " source_bytes=" ^ string_of_int candle_v679h_source_bytes ^
     " jobs_bytes=" ^ string_of_int candle_v679h_jobs_bytes ^
     " roots_bytes=" ^ string_of_int candle_v679h_roots_bytes);;
