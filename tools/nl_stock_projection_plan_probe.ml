(* ========================================================================== *)
(* Plan-only stock-route probe for one exact NL projection record.            *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  This deliberately stops before any reflected *)
(* numerical evaluation.  It authenticates the exact production parameter,  *)
(* builds the ordinary verifier certificate and adaptive-precision tree, and  *)
(* prepares every reflected source program.                                  *)
(* ========================================================================== *)

module Candle_nl_stock_projection_plan_probe = struct

open Certificate;;
open Candle_cv_flyspeck_direct_source_compat;;
open Candle_cv_analytic_expr_jet_prove;;

module Projection_informal_record = struct
  open Informal_verifier;;
  let f value = value.f;;
  let taylor value = value.taylor;;
end;;

let source_id = "prep-1395142356";;
let parameter_index = 3;;

let marker phase event =
  print_endline
    ("CANDLE_NL_STOCK_PROJECTION_PLAN|" ^ phase ^ "|" ^ event);;

let started = Unix.gettimeofday ();;
let axioms_before = axioms ();;

let _ = marker "production-prepare" "begin";;

let _,preparation,needs_delta = Break_case_exec.get_case source_id;;
let prepared_source =
  Break_case_exec.run_generic
    (fun selected ->
      preparation selected THEN Break_case_exec.check_tac selected)
    needs_delta source_id;;
let production_cases =
  Break_case_exec.mk_case_list prepared_source
    (Break_case_exec.get_iarg source_id);;
let _ = marker "production-prepare" "end";;

if parameter_index < 0 || parameter_index >= length production_cases then
  failwith "projection plan: parameter index outside production case list";;

let target = List.nth production_cases parameter_index;;

let _ = marker "source-reconstruction" "begin";;

let reconstruction = candle_direct_ineqm_conv target;;
if not (aconv (lhand (concl reconstruction)) target) then
  failwith "projection plan: reconstruction source mismatch";;
let _ = marker "source-reconstruction" "end";;

let case_term = rand (concl reconstruction);;
let _ = marker "source-expansion" "begin";;
let base_expansion =
  (REWRITE_CONV
     [TAUT `(P ==> Q) <=> (~P \/ Q)`;
      REAL_ARITH `~(a > b:real) <=> a <= b`;
      REAL_ARITH `~(a < b:real) <=> b <= a`;
      REAL_ARITH `~(a >= b:real) <=> a < b`;
      REAL_ARITH `~(a <= b:real) <=> b < a`]
   THENC candle_direct_expand_ineq_case)
    case_term;;

let projection_expanded_defs =
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

let rec saturate_projection_expansion remaining tm =
  let step = REWRITE_CONV projection_expanded_defs tm in
  let next = rand (concl step) in
  if aconv tm next then step
  else if remaining = 0 then
    failwith "projection plan: expansion did not stabilize"
  else
    TRANS step (saturate_projection_expansion (remaining - 1) next);;

let saturated_expansion =
  saturate_projection_expansion 8 (rand (concl base_expansion));;
let expansion = TRANS base_expansion saturated_expansion;;
let _ = marker "source-expansion" "end";;
let converted = rand (concl expansion);;
let _ = marker "source-dest-ineq" "begin";;
let ineq,variable_names,bounds = M_verifier_main.dest_ineq converted;;
let _ = marker "source-dest-ineq" "end";;
let _ = marker "source-standardize" "begin";;
let standard =
  M_verifier_main.mk_standard_ineq [REAL_POW_1;real_pow] ineq;;
let _ = marker "source-standardize" "end";;
let terms = striplist dest_disj ((lhand o concl) standard);;
let _ = marker "source-vectorize" "begin";;
let functions,variable_vector =
  candle_direct_exprs_to_vector_fun (map lhand terms);;
let _ = marker "source-vectorize" "end";;
let sorted_variable_names =
  map (fst o dest_var) (M_taylor.dest_vector variable_vector);;
let dimension = length sorted_variable_names;;

if dimension <> 6 || functions = [] then
  failwith "projection plan: expected a nonempty six-dimensional source";;

let lo,hi = bounds;;
let named_bounds =
  zip variable_names (zip (dest_list lo) (dest_list hi));;
let _ = marker "domain-order" "begin";;
let ordered_bounds =
  itlist
    (fun name result -> assoc name named_bounds :: result)
    sorted_variable_names [];;
let xx0,zz0 = unzip ordered_bounds;;
let xx = Misc_vars.mk_real_list xx0
and zz = Misc_vars.mk_real_list zz0;;
let _ =
  print_endline
    ("CANDLE_NL_STOCK_PROJECTION_PLAN_BOUNDS lower=" ^
     string_of_term xx ^ " upper=" ^ string_of_term zz);;
let _ = marker "domain-order" "end";;
let _ = marker "float-domain" "begin";;
let domain_subset,(xx1,zz1) = M_verifier_main.mk_float_domain 6 (xx,zz);;
let xx2 = Informal_taylor.convert_to_float_list 6 true xx
and zz2 = Informal_taylor.convert_to_float_list 6 false zz;;
let _ = marker "float-domain" "end";;

(* The sealed predecessor already contains the exact production parameter   *)
(* record used for action 296.  Reuse that immutable value here instead of  *)
(* relying on OCaml record-update syntax, which this Candle frontend does    *)
(* not implement.                                                            *)
let params =
  Candle_cv_analytic_expr_action296_plan.candle_action296_plan_params;;

let _ = marker "verifier-functions" "begin";;
let verifier_started = Unix.gettimeofday ();;
let formal_functions,informal_functions =
  unzip
    (map (M_verifier_main.mk_verification_functions params 6) functions);;
let verifier_seconds = Unix.gettimeofday () -. verifier_started;;
let _ = marker "verifier-functions" "end";;

let search_options =
  Candle_cv_analytic_expr_action296_plan.
    candle_action296_plan_search_options;;
let search_functions =
  map
    (fun f ->
      Projection_informal_record.f f,
      Projection_informal_record.taylor f)
    informal_functions;;
let informal_domain = Informal_taylor.mk_m_center_domain 6 xx2 zz2;;

let _ = marker "certificate-search" "begin";;
let search_started = Unix.gettimeofday ();;
let certificate =
  Informal_search.construct_certificate
    search_options informal_domain search_functions;;
let search_seconds = Unix.gettimeofday () -. search_started;;
let _ = marker "certificate-search" "end";;
let stats = Certificate.result_stats certificate;;

let _ = marker "adaptive-precision" "begin";;
let adaptive_started = Unix.gettimeofday ();;
let precision_tree,_ =
  Informal_verifier.m_verify_raw0
    6 1 6 informal_functions certificate xx2 zz2;;
let adaptive_seconds = Unix.gettimeofday () -. adaptive_started;;
let _ = marker "adaptive-precision" "end";;

let function_counts = map (fun _ -> ref 0) functions;;
let precision_leaves = ref 0;;
let precision_glues = ref 0;;
let precision_raw = ref 0;;
let precision_mono = ref 0;;
let rec count_precision_tree = function
  | P_result_pass (_,function_index,raw_flag) ->
      if function_index < 0 || function_index >= length functions then
        failwith "projection plan: function index outside source function list";
      precision_leaves := !precision_leaves + 1;
      if raw_flag then precision_raw := !precision_raw + 1;
      let count = List.nth function_counts function_index in
      count := !count + 1
  | P_result_glue (_,_,convex_flag,left,right) ->
      precision_glues := !precision_glues + 1;
      if convex_flag then precision_mono := !precision_mono + 1;
      count_precision_tree left;
      count_precision_tree right
  | P_result_mono _ -> precision_mono := !precision_mono + 1
  | P_result_ref _ ->
      failwith "projection plan: unexpected reference node";;
let _ = count_precision_tree precision_tree;;

(* Placeholder intervals make the source programs concrete.  They are not  *)
(* accepted as numerical evidence and are replaced by per-cell certificates *)
(* in the actual fixed-outer checker.                                         *)
let sqrt_count = ref 0;;
let placeholder_sqrt_interval _ =
  sqrt_count := !sqrt_count + 1;
  `((((0,0),0),((100,0),0)):
      ((num#num)#num)#((num#num)#num))`;;

let _ = marker "source-preparation" "begin";;
let prepare_started = Unix.gettimeofday ();;
let reflected_prepared =
  map
    (candle_q_dim_analytic_jet_prepare_six_with placeholder_sqrt_interval)
    functions;;
let prepare_seconds = Unix.gettimeofday () -. prepare_started;;
let _ = marker "source-preparation" "end";;
let instruction_counts =
  map
    (fun prepared -> length (dest_list prepared.program_term))
    reflected_prepared;;

if hyp domain_subset <> [] ||
   !precision_leaves <> stats.pass + stats.pass_raw + stats.pass_mono ||
   !precision_glues <> stats.glue + stats.glue_convex ||
   not
     (List.for_all
       (fun prepared ->
         hyp prepared.valid_theorem = [] &&
         hyp prepared.source_theorem = [] &&
         hyp prepared.compile_theorem = [] &&
         hyp prepared.program_representation = [])
       reflected_prepared) then
  failwith "projection plan: authenticated state mismatch";;

let axioms_after = axioms ();;
if length axioms_after <> length axioms_before ||
   not (List.for_all (fun theorem -> List.mem theorem axioms_before) axioms_after)
then failwith "projection plan changed the global axiom set";;

let join_ints values =
  match values with
  | [] -> ""
  | first :: rest ->
      itlist
        (fun value result -> string_of_int value ^ "," ^ result)
        rest (string_of_int first);;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_PLAN_RESULT DEVELOPMENT_NON_RELEASE" ^
   " source=" ^ source_id ^
   " parameter_index=" ^ string_of_int parameter_index ^
   " production_cases=" ^ string_of_int (length production_cases) ^
   " dimension=" ^ string_of_int dimension ^
   " disjuncts=" ^ string_of_int (length functions) ^
   " certificate_pass=" ^ string_of_int stats.pass ^
   " certificate_pass_raw=" ^ string_of_int stats.pass_raw ^
   " certificate_pass_mono=" ^ string_of_int stats.pass_mono ^
   " certificate_glue=" ^ string_of_int stats.glue ^
   " certificate_glue_convex=" ^ string_of_int stats.glue_convex ^
   " precision_leaves=" ^ string_of_int !precision_leaves ^
   " precision_glues=" ^ string_of_int !precision_glues ^
   " precision_raw=" ^ string_of_int !precision_raw ^
   " precision_mono=" ^ string_of_int !precision_mono ^
   " function_counts=" ^ join_ints (map (fun count -> !count) function_counts) ^
   " instruction_counts=" ^ join_ints instruction_counts ^
   " sqrt_occurrences=" ^ string_of_int !sqrt_count ^
   " verifier_seconds=" ^ string_of_float verifier_seconds ^
   " search_seconds=" ^ string_of_float search_seconds ^
   " adaptive_seconds=" ^ string_of_float adaptive_seconds ^
   " prepare_seconds=" ^ string_of_float prepare_seconds ^
   " total_seconds=" ^ string_of_float (Unix.gettimeofday () -. started));;

print_endline
  "CANDLE_NL_STOCK_PROJECTION_PLAN_OK DEVELOPMENT_NON_RELEASE";;

end;;
