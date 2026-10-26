(* DEVELOPMENT / NON-RELEASE bounded exact data export from the authenticated
   prepared case-10173 input checkpoint. *)

open Benchmark_cv_compute_analytic_expr_case10173_historical_registered_input;;

let _ =
  let input = candle_case10173_historical_registered_input () in
  let export_root =
    "/project/flyspeck-candle-runs/v679j-fast-nl-prepared-input-chunks-dev-001" in
  let zero = `Cexp_num 0` in
  let write name term =
    let text = string_of_term term in
    let channel = Stdlib.open_out (export_root ^ "/" ^ name ^ ".term") in
    Stdlib.output_string channel (text ^ "\n");
    Stdlib.close_out channel;
    if not (aconv (parse_term text) term) then
      failwith ("v679j prepared chunk roundtrip: " ^ name) in
  let rec append left right =
    match candle_case10173_registered_input_cval_list_view left with
    | None -> right
    | Some (head,tail) ->
        list_mk_comb (`Cexp_pair`,[head;append tail right]) in
  let rec combine chunks =
    match chunks with
    | [] -> zero
    | head :: tail -> append head (combine tail) in
  let rec export_chunks role index remaining chunks_rev =
    let remaining_count =
      candle_case10173_registered_input_cval_list_length remaining in
    if remaining_count = 0 then List.rev chunks_rev
    else
      let count = if remaining_count < 16 then remaining_count else 16 in
      let chunk =
        candle_case10173_registered_input_cval_list_take count remaining in
      let rest =
        candle_case10173_registered_input_cval_list_drop count remaining in
      let name = role ^ "-" ^ string_of_int index in
      write name chunk;
      export_chunks role (index + 1) rest (chunk :: chunks_rev) in
  write "source-program" input.registered_input_source_program;
  let job_chunks =
    export_chunks "jobs" 0 input.registered_input_encoded_jobs [] in
  let root_chunks =
    export_chunks "roots" 0 input.registered_input_roots [] in
  let rebuilt_jobs = combine job_chunks
  and rebuilt_roots = combine root_chunks in
  if length job_chunks <> 261 || length root_chunks <> 261 ||
     not (aconv rebuilt_jobs input.registered_input_encoded_jobs) ||
     not (aconv rebuilt_roots input.registered_input_roots) ||
     candle_case10173_registered_input_cval_list_length rebuilt_jobs <> 4173 ||
     candle_case10173_registered_input_cval_list_length rebuilt_roots <> 4173
  then failwith "v679j prepared chunk recombination validation"
  else
    print_endline
      "CANDLE_FLYSPECK_V679J_PREPARED_INPUT_CHUNKS_OK DEVELOPMENT_NON_RELEASE cells=4173 jobs_chunks=261 roots_chunks=261 chunk_limit=16";;
