(* ========================================================================== *)
(* Complete stock reflected theorem for projection record 161160/23.         *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  Numerical work comes only from the two       *)
(* retained complete-checker equality theorems.  This stage decodes their   *)
(* forest roots, rejoins the authenticated mixed tree, and reconstructs the  *)
(* literal original production theorem.                                      *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_complete_161160 = struct

open Candle_nl_stock_projection_plan_probe;;
open Candle_nl_stock_projection_mixed_forest_161160;;
open Candle_nl_stock_projection_mixed_complete_compute_161160;;
open Candle_cv_flyspeck_nonlinear_driver;;
open Candle_cv_analytic_expr_disjunctive_fixed_outer_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_complete_forest_prove;;
open Candle_cv_flyspeck_nonlinear_term_order_compat;;

let axioms_before = axioms ();;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|forest-handoff|begin";;
let forest0 =
  candle_q_dim_taylor_model_fixed_outer_variable_complete_handoff_computed_forest_six
    (prepared_for 0) logical_tokens0 encoded_tokens0 encoded_jobs0 compute0
    expected_stack0;;
let forest1 =
  candle_q_dim_taylor_model_fixed_outer_variable_complete_handoff_computed_forest_six
    (prepared_for 1) logical_tokens1 encoded_tokens1 encoded_jobs1 compute1
    expected_stack1;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|forest-handoff|end";;

if length forest0.variable_complete_forest_source_theorems <>
     length components0 ||
   length forest1.variable_complete_forest_source_theorems <>
     length components1 then
  failwith "projection mixed complete: forest cardinality drift";;

let component_pass component source =
  let function_term =
    List.nth functions component.projection_component_selected in
  let expected_lower,expected_upper =
    candle_disjunctive_fixed_outer_domain_bounds
      component.projection_component_domain in
  candle_reflected_nl_source_pass_with function_term
    (fun actual_lower actual_upper ->
      if not
          (candle_disjunctive_fixed_outer_aconv_lists
             actual_lower expected_lower &&
           candle_disjunctive_fixed_outer_aconv_lists
             actual_upper expected_upper) then
        failwith "projection mixed complete: component handoff drift";
      source)
    component.projection_component_domain;;

let pair_components components sources =
  let rec pair components sources =
    match components,sources with
    | [],[] -> []
    | component::remaining_components,source::remaining_sources ->
        (component.projection_component_id,
         component_pass component source) ::
        pair remaining_components remaining_sources
    | _ -> failwith "projection mixed complete: forest pairing drift" in
  pair components sources;;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|component-handoff|begin";;
let component_passes =
  (pair_components
     (rev components0) forest0.variable_complete_forest_source_theorems) @
  (pair_components
     (rev components1) forest1.variable_complete_forest_source_theorems);;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|component-handoff|end";;

let component_table =
  let count = length components in
  let table = Array.make count TRUTH and seen = Array.make count false in
  let rec fill = function
    | [] -> ()
    | (component,theorem)::remaining ->
        if component < 0 || component >= count || seen.(component) then
          failwith "projection mixed complete: component table drift";
        table.(component) <- theorem;
        seen.(component) <- true;
        fill remaining in
  let rec all_seen index =
    index = count || (seen.(index) && all_seen (index + 1)) in
  fill component_passes;
  if not (all_seen 0) then
    failwith "projection mixed complete: component missing";
  table;;

let rec glue = function
  | Projection_mixed_component component -> component_table.(component)
  | Projection_mixed_join (axis,left,right) ->
      let left_theorem = glue left in
      let right_theorem = glue right in
      let appended =
        M_verifier.m_glue_cells_list 6 axis left_theorem right_theorem in
      candle_nonlinear_merge_m_cell_list_pass 6 appended;;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|mixed-reconstruction|begin";;
let root_list_pass = glue skeleton;;
let root_functions,root_domain_term =
  M_verifier.dest_m_cell_list_pass (concl root_list_pass);;
let expected_domain,_,_ = M_taylor.dest_m_cell_domain (concl root_domain);;
let rec remove_aconv target = function
  | [] -> None
  | head :: tail ->
      if aconv target head then Some tail
      else
        (match remove_aconv target tail with
         | None -> None
         | Some remaining -> Some (head :: remaining));;
let rec aconv_permutation left right =
  match left with
  | [] -> right = []
  | head :: tail ->
      (match remove_aconv head right with
       | None -> false
       | Some remaining -> aconv_permutation tail remaining);;
let bool_text value = if value then "true" else "false";;
let root_function_matrix =
  if length root_functions = 2 && length functions = 2 then
    bool_text (aconv (List.nth root_functions 0) (List.nth functions 0)) ^
    "/" ^
    bool_text (aconv (List.nth root_functions 0) (List.nth functions 1)) ^
    "," ^
    bool_text (aconv (List.nth root_functions 1) (List.nth functions 0)) ^
    "/" ^
    bool_text (aconv (List.nth root_functions 1) (List.nth functions 1))
  else "wrong-cardinality";;
print_endline
  ("CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_ROOT_DIAGNOSTIC" ^
   " root_functions=" ^ string_of_int (length root_functions) ^
   " expected_functions=" ^ string_of_int (length functions) ^
   " function_aconv_matrix=" ^ root_function_matrix ^
   " domain_aconv=" ^ bool_text (aconv root_domain_term expected_domain) ^
   " hypotheses=" ^ string_of_int (length (hyp root_list_pass)));;
if not (aconv_permutation root_functions functions) ||
   not (aconv root_domain_term expected_domain) ||
   hyp root_list_pass <> [] then
  failwith "projection mixed complete: root theorem drift";;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|mixed-reconstruction|end";;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|source-reconstruction|begin";;
let expanded_general =
  M_verifier_main.normalize_disj_result true
    functions variable_vector standard domain_subset root_list_pass;;
let expanded =
  let theorem = SPEC_ALL expanded_general in
  let bridge = TAUT (mk_imp (concl theorem,converted)) in
  MP bridge theorem;;
let case_theorem = REWRITE_RULE [GSYM expansion] expanded;;
let theorem =
  (SPEC_ALL o REWRITE_RULE [GSYM reconstruction]) case_theorem;;
let digest = Digest.to_hex (Digest.string (string_of_thm theorem));;
let axioms_after = axioms ();;

if hyp theorem <> [] || not (aconv (concl theorem) target) ||
   length component_passes <> length components ||
   length axioms_after <> length axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom axioms_before)
       axioms_after) then
  failwith "projection mixed complete: final theorem validation failed";;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE|source-reconstruction|end";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_MIXED_COMPLETE_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-1611600345x" ^
   " parameter_index=23 source_leaves=798 components=24" ^
   " complete_verdicts=2 assumptions=0 axiom_growth=0" ^
   " theorem_digest=" ^ digest);;

end;;
