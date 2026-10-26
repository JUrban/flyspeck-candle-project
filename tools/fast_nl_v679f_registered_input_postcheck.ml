(* DEVELOPMENT / NON-RELEASE registered-input preparation discriminator. *)

open Benchmark_cv_compute_analytic_expr_case10173_historical_registered_input;;

let candle_v679f_input =
  candle_case10173_historical_registered_input ();;

let candle_v679f_operator,candle_v679f_arguments =
  strip_comb candle_v679f_input.registered_input_checked_call;;

let candle_v679f_axioms_after = axioms ();;

if not (is_const candle_v679f_operator) ||
   fst (dest_const candle_v679f_operator) <>
     "candle_cv_case10173_hist_checked_raw_jobs_check" ||
   length candle_v679f_arguments <> 3 ||
   candle_case10173_registered_input_cval_list_length
     candle_v679f_input.registered_input_encoded_jobs <> 4173 ||
   candle_case10173_registered_input_cval_list_length
     candle_v679f_input.registered_input_roots <> 4173 ||
   List.length candle_v679f_axioms_after <>
     List.length candle_v679d_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v679d_axioms_before)
       candle_v679f_axioms_after) then
  failwith "v679f registered input preparation validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679F_REGISTERED_INPUT_PREPARATION_OK DEVELOPMENT_NON_RELEASE cells=4173 numerical_compute=0";;
