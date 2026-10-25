(* DEVELOPMENT / NON-RELEASE direct-input bridge for the nonlinear verifier's
   complete recorded floating-runtime surface.  The exact linked development
   binary predates these top-level OCaml aliases even though its source tree
   contains them.  Recreate the central definitions before loading support. *)
#use "/project/flyspeck-candle-project/tools/fast_nl_v665_verifier_runtime_compat.ml";;

let float_of_int x = Cake.Double.fromInt x;;
let int_of_float x = Cake.Double.toInt x;;
let floor x = Cake.Double.floor x;;
let float_of_string s =
  match Double.fromString s with
  | None -> failwith "float_of_string"
  | Some value -> value
;;
let abs_float = candle_binary64_abs;;

let candle_fast_nl_v670_runtime_surface_probe = float_of_string "1.25";;
candle_assert
  (float_ieee_equal candle_fast_nl_v670_runtime_surface_probe 1.25 &&
   int_of_float (float_of_int 7) = 7 &&
   float_ieee_equal
     (floor candle_fast_nl_v670_runtime_surface_probe) 1.0 &&
   float_ieee_equal
     (abs_float (~-. candle_fast_nl_v670_runtime_surface_probe)) 1.25)
  "fast_nl_v670_runtime_surface";;
let _ = log candle_fast_nl_v670_runtime_surface_probe;;
let _ = infinity;;
let _ = nan;;
print_endline
  "CANDLE_FLYSPECK_V670_RUNTIME_SYMBOL_SURFACE_OK identifiers=9";;

#use "/project/flyspeck-candle-project/tools/fast_nl_v665_support.ml";;
