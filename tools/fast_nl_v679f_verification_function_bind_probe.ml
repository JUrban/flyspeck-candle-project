(* DEVELOPMENT / NON-RELEASE discriminator for LR-055. *)

open Candle_cv_analytic_expr_action296_fixture;;

let candle_v679f_function = candle_action296_analytic_function;;
let candle_v679f_vector,candle_v679f_body = dest_abs candle_v679f_function;;
let candle_v679f_dimension =
  try M_taylor.get_dim candle_v679f_vector with _ ->
    print_endline "CANDLE_V679F_BIND_PROBE boundary=get-dim-failed";
    0;;

let _ =
  print_endline
    ("CANDLE_V679F_BIND_PROBE boundary=term-shape is_abs=" ^
     (if is_abs candle_v679f_function then "true" else "false") ^
     " dimension=" ^ string_of_int candle_v679f_dimension ^
     " is_poly=" ^
     (if M_verifier_main.is_poly candle_v679f_body then "true" else "false"));;

let candle_v679f_head_name term =
  let head,_ = strip_comb term in
  if is_const head then fst (dest_const head)
  else if is_var head then fst (dest_var head)
  else "nonconstant";;

let rec candle_v679f_probe_arguments path index arguments =
  match arguments with
  | [] -> ()
  | argument :: remaining ->
      candle_v679f_probe_term
        (path ^ "." ^ string_of_int index) argument;
      candle_v679f_probe_arguments path (index + 1) remaining

and candle_v679f_probe_term path term =
  try
    let _ =
      M_verifier_main.mk_funs candle_v679f_dimension 6
        (mk_abs (candle_v679f_vector,term)) in
    print_endline
      ("CANDLE_V679F_BIND_PROBE boundary=mk-funs-ok path=" ^ path ^
       " head=" ^ candle_v679f_head_name term)
  with _ ->
    let _,arguments = strip_comb term in
    print_endline
      ("CANDLE_V679F_BIND_PROBE boundary=mk-funs-failed path=" ^ path ^
       " head=" ^ candle_v679f_head_name term ^
       " argument_count=" ^ string_of_int (length arguments));
    candle_v679f_probe_arguments path 0 arguments;;

let _ =
  if candle_v679f_dimension = 0 then
    print_endline "CANDLE_V679F_BIND_PROBE boundary=mk-funs-skipped"
  else
    candle_v679f_probe_term "root" candle_v679f_body;;

let _ =
  try
    let _ =
      M_verifier_main.mk_verification_functions
        (ref M_verifier_main.default_params) 6 candle_v679f_function in
    print_endline
      "CANDLE_V679F_BIND_PROBE boundary=verification-functions-ok"
  with _ ->
    print_endline
      "CANDLE_V679F_BIND_PROBE boundary=verification-functions-failed";;

print_endline "CANDLE_FLYSPECK_V679F_BIND_PROBE_COMPLETE";;
