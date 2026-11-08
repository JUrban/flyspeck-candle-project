(* ========================================================================== *)
(* Validate the exact Flyspeck hminus enclosure after loading its source.     *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The preceding source body is the upstream     *)
(* nonlinear/formal_tests/hminus.hl proof, including its registration in the *)
(* formal and informal interval evaluators.                                  *)
(* ========================================================================== *)

module Candle_nl_stock_projection_hminus_setup_marker = struct

let expected =
  `interval_arith hminus
     (#1.2317544220903043901,#1.2317544220903047)`;;

let hminus_interval =
  Candle_nl_stock_projection_hminus_setup.hminus_interval;;

if hyp hminus_interval <> [] then
  failwith "hminus setup: interval theorem has assumptions";;
if not (aconv (concl hminus_interval) expected) then
  failwith "hminus setup: interval theorem conclusion drift";;

let registered =
  Eval_interval.eval_interval_fun 6
    (Eval_interval.build_interval_fun `hminus:real`) [] [];;
if hyp registered <> [] then
  failwith "hminus setup: registered evaluation has assumptions";;

print_endline
  "CANDLE_NL_STOCK_PROJECTION_HMINUS_SETUP_OK DEVELOPMENT_NON_RELEASE";;

end;;
