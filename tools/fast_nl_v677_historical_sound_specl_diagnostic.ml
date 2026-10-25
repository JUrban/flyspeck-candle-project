(* DEVELOPMENT / NON-RELEASE: localize the v677t SPECL failure. *)
let candle_v677_original_SPECL = SPECL;;
let candle_v677_specl_call_count = ref 0;;

let SPECL terms theorem =
  (candle_v677_specl_call_count := !candle_v677_specl_call_count + 1;
   try candle_v677_original_SPECL terms theorem with Failure message ->
     (print_endline
        ("CANDLE_V677_SPECL_FAILURE call=" ^
         string_of_int !candle_v677_specl_call_count ^
         " term_count=" ^ string_of_int (List.length terms));
      print_endline
        ("CANDLE_V677_SPECL_THEOREM " ^ string_of_term (concl theorem));
      failwith message));;

needs "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml";;

failwith "v677 historical SPECL diagnostic unexpectedly completed";;
