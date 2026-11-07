(* ========================================================================== *)
(* Exact structural coverage probe for the 24-record NL projection sample.   *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  Every record is reconstructed through the     *)
(* production Break_case_exec preparation and parameter index.  The probe    *)
(* applies the proved Flyspeck expansions and the current reflected-language  *)
(* structural discriminator, but deliberately performs no certificate search *)
(* and no Kernel.compute call.                                                *)
(* ========================================================================== *)

module Candle_nl_stock_projection_sample_structure = struct

open Candle_cv_flyspeck_direct_source_compat;;
open Candle_cv_analytic_expr_reify;;
open Candle_cv_exact_interval_reify;;

let marker = "CANDLE_NL_STOCK_PROJECTION_STRUCTURE|";;

let sample =
  ["acs","prep-8055810915",0;
   "acs+arc_hhn","prep-SDCCMGA b",0;
   "asn","prep-1965189142 a",0;
   "hminus","prep-GLFVCVK4 2477216213 split(31/64)",0;
   "hminus","prep-GLFVCVK4 2477216213 split(4/64)",36;
   "hminus","prep-GLFVCVK4 2477216213 split(36/64)",88;
   "hminus","prep-GLFVCVK4 2477216213 split(36/64)",67;
   "matan","prep-TSKAJXY-GXSABWC DIV",0;
   "matan","prep-7796879304",36;
   "matan","prep-7796879304",5;
   "matan","prep-7796879304",4;
   "supported","prep-ZTGIJCF0",0;
   "supported","prep-BIXPCGW 9455898160 split(0/2)",40;
   "supported","prep-TSKAJXY-RIBCYXU sym",26;
   "supported","prep-OXLZLEZ 6346351218 1 9",17;
   "supported","prep-OXLZLEZ 6346351218 1 8",57;
   "supported","prep-FHBVYXZv2 a split(1/2)",7;
   "supported","prep-OXLZLEZ 6346351218 4 35",36;
   "supported","prep-1395142356",3;
   "supported","prep-1611600345x",23;
   "supported","prep-8293089898",264;
   "supported","prep-7550003505 0 2 4",123;
   "supported","prep-8673686234 b",151;
   "supported","prep-8293089898",278];;

let rec string_mem needle = function
  | [] -> false
  | value :: rest -> needle = value || string_mem needle rest;;

let union_strings left right =
  itlist
    (fun value result ->
      if string_mem value result then result else value :: result)
    left right;;

let string_set_equal left right =
  length left = length right &&
  forall (fun value -> string_mem value right) left &&
  forall (fun value -> string_mem value left) right;;

let join_strings separator = function
  | [] -> ""
  | first :: rest ->
      itlist (fun value result -> value ^ separator ^ result) rest first;;

let scan_head tm =
  let head,_ = strip_comb tm in
  try fst (dest_const head)
  with Failure _ ->
    if is_var head then "VARIABLE_HEAD" else "NONCONSTANT_HEAD";;

let rec scan_expression variables tm =
  if candle_analytic_is_pi_half tm ||
     candle_analytic_is_pi_half_expanded tm ||
     candle_analytic_is_pi tm ||
     candle_analytic_is_acs_third tm then []
  else if candle_q_is_unary `(--):real->real` tm ||
          candle_q_is_unary `inv:real->real` tm ||
          candle_q_is_unary `sqrt:real->real` tm ||
          candle_q_is_unary `atn:real->real` tm then
    scan_expression variables (rand tm)
  else if candle_q_is_binary `(+):real->real->real` tm then
    let left,right = candle_q_dest_binary `(+):real->real->real` tm in
    union_strings (scan_expression variables left)
      (scan_expression variables right)
  else if candle_q_is_binary `(-):real->real->real` tm then
    let left,right = candle_q_dest_binary `(-):real->real->real` tm in
    union_strings (scan_expression variables left)
      (scan_expression variables right)
  else if candle_q_is_binary `(*):real->real->real` tm then
    let left,right = candle_q_dest_binary `(*):real->real->real` tm in
    union_strings (scan_expression variables left)
      (scan_expression variables right)
  else if candle_q_is_binary `(/):real->real->real` tm then
    let left,right = candle_q_dest_binary `(/):real->real->real` tm in
    union_strings (scan_expression variables left)
      (scan_expression variables right)
  else if candle_q_is_binary `(pow):real->num->real` tm then
    let base,exponent = candle_q_dest_binary `(pow):real->num->real` tm in
    if is_numeral exponent && dest_small_numeral exponent = 2 then
      scan_expression variables base
    else ["UNSUPPORTED_POWER"]
  else if candle_analytic_polynomial_candidate variables tm then []
  else [scan_head tm];;

let expanded_defs =
  candle_direct_flyspeck_defs @
  Break_case_exec.nonlin_rewrites @
  map snd Break_case_exec.trig_expansions1 @
  [Sphere.sqrt8;
   Sphere.sqrt2;
   Sphere.sqrt3;
   Sphere.tau0;
   Sphere.mm1;
   Sphere.mm2;
   Sphere.h0;
   Sphere.hplus;
   Sphere.rh0;
   Sphere.rotate4;
   Sphere.rotate5;
   Sphere.rotate6];;

let expected_residual = function
  | "supported" -> []
  | "hminus" -> ["hminus"]
  | "matan" -> ["matan"]
  | "acs" -> ["acs"]
  | "asn" -> ["asn"]
  | "acs+arc_hhn" -> ["acs";"arc_hhn"]
  | group -> failwith ("unknown projection group: " ^ group);;

(* Preparing a source is materially more expensive than selecting one of its
   parameter records.  Cache the exact production case list so repeated sample
   records from the same source pay that cost once in this live session. *)
let prepared_case_cache = ref ([]:(string * term list) list);;

let prepared_cases source_id =
  try assoc source_id !prepared_case_cache
  with Failure _ ->
    let _,preparation,needs_delta = Break_case_exec.get_case source_id in
    let prepared =
      Break_case_exec.run_generic
        (fun selected ->
          preparation selected THEN Break_case_exec.check_tac selected)
        needs_delta source_id in
    let cases =
      Break_case_exec.mk_case_list prepared
        (Break_case_exec.get_iarg source_id) in
    prepared_case_cache := (source_id,cases) :: !prepared_case_cache;
    cases;;

let selected_target source_id parameter_index =
  let cases = prepared_cases source_id in
  if parameter_index < 0 || parameter_index >= length cases then
    failwith
      ("projection parameter index outside production case list: " ^
       source_id ^ "," ^ string_of_int parameter_index);
  List.nth cases parameter_index;;

let target_formula target =
  let stripped = snd (strip_forall target) in
  let head,arguments = strip_comb stripped in
  if is_const head then
    match fst (dest_const head),arguments with
    | "ineqm",[_;_;formula] -> formula
    | "ineq",[_;formula] -> formula
    | _ -> stripped
  else stripped;;

let rec saturate_expanded_defs remaining tm =
  let step = REWRITE_CONV expanded_defs tm in
  let next = rand (concl step) in
  if aconv tm next then step
  else if remaining = 0 then
    failwith "projection expansion did not stabilize"
  else TRANS step (saturate_expanded_defs (remaining - 1) next);;

let scan_target target =
  let formula = target_formula target in
  let expansion =
    (REWRITE_CONV
       [TAUT `(P ==> Q) <=> (~P \/ Q)`;
        REAL_ARITH `~(a > b:real) <=> a <= b`;
        REAL_ARITH `~(a < b:real) <=> b <= a`;
        REAL_ARITH `~(a >= b:real) <=> a < b`;
        REAL_ARITH `~(a <= b:real) <=> b < a`]
     THENC candle_direct_expand_ineq_case)
      formula in
  let expanded =
    TRANS expansion (saturate_expanded_defs 8 (rand (concl expansion))) in
  let expansion =
    TRANS expanded (DEPTH_CONV let_CONV (rand (concl expanded))) in
  let inequality = rand (concl expansion) in
  let standard =
    M_verifier_main.mk_standard_ineq [REAL_POW_1;real_pow] inequality in
  let disjuncts = striplist dest_disj ((lhand o concl) standard) in
  let expressions = map lhand disjuncts in
  let functions,_ = candle_direct_exprs_to_vector_fun expressions in
  let dimension = length (unions (map frees expressions)) in
  let function_vector =
    match functions with
    | [] -> failwith "projection sample: empty expanded function list"
    | first :: _ -> fst (dest_abs first) in
  let variables =
    Candle_cv_polynomial_expr_flyspeck_reify.candle_poly_vector_components
      function_vector dimension in
  let unsupported =
    itlist
      (fun function_term result ->
        let _,body = dest_abs function_term in
        union_strings (scan_expression variables body) result)
      functions [] in
  dimension,length disjuncts,unsupported;;

let supported_count = ref 0;;
let residual_count = ref 0;;
let error_count = ref 0;;
let started = Unix.gettimeofday ();;

let emit (group,source_id,parameter_index) =
  let record_started = Unix.gettimeofday () in
  try
    let target = selected_target source_id parameter_index in
    let dimension,disjuncts,unsupported = scan_target target in
    let expected = expected_residual group in
    if not (string_set_equal unsupported expected) then
      failwith
        ("projection structural residual drift: expected=" ^
         join_strings "," expected ^ " actual=" ^
         join_strings "," unsupported);
    if expected = [] then supported_count := !supported_count + 1
    else residual_count := !residual_count + 1;
    print_endline
      (marker ^ "OK|" ^ group ^ "|" ^ source_id ^ "|" ^
       string_of_int parameter_index ^ "|" ^
       string_of_int dimension ^ "|" ^ string_of_int disjuncts ^ "|" ^
       join_strings "," unsupported ^ "|" ^
       string_of_int (String.length (string_of_term target)) ^ "|" ^
       string_of_float (Unix.gettimeofday () -. record_started))
  with Failure message ->
    error_count := !error_count + 1;
    print_endline
      (marker ^ "ERROR|" ^ group ^ "|" ^ source_id ^ "|" ^
       string_of_int parameter_index ^ "|" ^ message);;

let _ = do_list emit sample;;

if !supported_count <> 13 || !residual_count <> 11 || !error_count <> 0 then
  failwith "NL stock projection structural sample failed closed";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_STRUCTURE_OK DEVELOPMENT_NON_RELEASE" ^
   " records=" ^ string_of_int (length sample) ^
   " supported=" ^ string_of_int !supported_count ^
   " residual=" ^ string_of_int !residual_count ^
   " prepared_sources=" ^ string_of_int (length !prepared_case_cache) ^
   " elapsed_seconds=" ^ string_of_float (Unix.gettimeofday () -. started));;

end;;
