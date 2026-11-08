(* ========================================================================== *)
(* Complete stock reflected theorem for TSKAJXY-RIBCYXU-sym/26.             *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The retained numerical theorems are reused   *)
(* unchanged.  This stage computes only three compact topology streams,      *)
(* rejoins their 19 authenticated components, and reconstructs the literal  *)
(* original Flyspeck theorem.                                                *)
(* ========================================================================== *)

module Candle_nl_stock_projection_mixed_complete_tskajxy = struct

open Candle_nl_stock_projection_plan_probe;;
open Candle_nl_stock_projection_mixed_forest_tskajxy;;
open Candle_nl_stock_projection_mixed_repaired_forest_v2_tskajxy;;
open Candle_nl_stock_projection_mixed_repaired_validation_v2_tskajxy;;
open Candle_nl_stock_projection_split_forest_handoff;;
open Candle_cv_flyspeck_nonlinear_driver;;
open Candle_cv_analytic_expr_disjunctive_fixed_outer_prove;;
open Candle_cv_flyspeck_nonlinear_term_order_compat;;

(* Fail closed if the freshly streamed decoded-stack adapter did not replace
   the older support-checkpoint module. *)
let _ = decode_stack;;

let axioms_before = axioms ();;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|topology-handoff|begin";;
let forest0 =
  candle_nl_stock_projection_split_forest_six
    result0 repaired_v2_logical_tokens0 repaired_v2_encoded_tokens0
    expected_stack0;;
let forest1 =
  candle_nl_stock_projection_split_forest_six
    result1 logical_tokens1 encoded_tokens1 expected_stack1;;
let forest5 =
  candle_nl_stock_projection_split_forest_six
    result5 logical_tokens5 encoded_tokens5 expected_stack5;;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|topology-handoff|end";;

if length forest0.projection_split_forest_source_theorems <>
     length components0 ||
   length forest1.projection_split_forest_source_theorems <>
     length components1 ||
   length forest5.projection_split_forest_source_theorems <>
     length components5 then
  failwith "TSKAJXY complete: forest cardinality drift";;

let component_pass component source =
  let function_term =
    List.nth functions component.projection_component_selected in
  let expected_lower,expected_upper =
    candle_disjunctive_fixed_outer_domain_bounds
      component.projection_component_domain in
  (* A split-forest source theorem still names its exact q-interval root.
     Reduce that representation before the live-domain transport, matching
     the established bounded-component handoff. *)
  let logical_source =
    REWRITE_RULE
      [candle_cv_q_interval_list_decode_def;
       candle_cv_q_interval_decode_def;candle_cv_q_decode_def;
       candle_cv_lc_z_decode_def;candle_cv_lc_num_decode_def;
       cexp_fst_def;cexp_snd_def;FST;SND]
      source in
  candle_reflected_nl_source_pass_with function_term
    (fun actual_lower actual_upper ->
      if not
          (candle_disjunctive_fixed_outer_aconv_lists
             actual_lower expected_lower &&
           candle_disjunctive_fixed_outer_aconv_lists
             actual_upper expected_upper) then
        failwith "TSKAJXY complete: component handoff drift";
      logical_source)
    component.projection_component_domain;;

let try_component_pass component source =
  try Some (component_pass component source) with
  | Failure message ->
      if message = "reflected nonlinear driver: cell theorem mismatch" then
        None
      else raise (Failure message);;

(* The split-stack theorem and decoded stack are independently authenticated,
   but their conjunction order is not part of the public adapter contract.
   Pair each closed root theorem with its exact source domain instead of
   depending on an incidental conjunction order.  Requiring exactly one
   match, and consuming it once, keeps the handoff fail-closed. *)
let pair_components label components sources =
  let indexed_sources =
    let rec index next = function
      | [] -> []
      | source::remaining ->
          (next,source) :: index (next + 1) remaining in
    index 0 sources in
  let rec remove_index target = function
    | [] -> failwith "TSKAJXY complete: matched source disappeared"
    | (index,source)::remaining ->
        if index = target then remaining
        else (index,source) :: remove_index target remaining in
  let matching component candidates =
    let rec collect = function
      | [] -> []
      | (index,source)::remaining ->
          (match try_component_pass component source with
           | None -> collect remaining
           | Some theorem ->
               (index,theorem) :: collect remaining) in
    collect candidates in
  let rec pair remaining_sources = function
    | [] ->
        if remaining_sources = [] then []
        else failwith "TSKAJXY complete: unused forest source theorem"
    | component::remaining_components ->
        (match matching component remaining_sources with
         | [(source_index,theorem)] ->
             print_endline
               ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPONENT_MAP" ^
                " forest=" ^ label ^
                " component=" ^
                  string_of_int component.projection_component_id ^
                " source_index=" ^ string_of_int source_index);
             (component.projection_component_id,theorem) ::
             pair
               (remove_index source_index remaining_sources)
               remaining_components
         | [] -> failwith "TSKAJXY complete: unmatched component theorem"
         | _ -> failwith "TSKAJXY complete: ambiguous component theorem") in
  pair indexed_sources components;;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|component-handoff|begin";;
let component_passes =
  (pair_components
     "function0" components0
     forest0.projection_split_forest_source_theorems) @
  (pair_components
     "function1" components1
     forest1.projection_split_forest_source_theorems) @
  (pair_components
     "function5" components5
     forest5.projection_split_forest_source_theorems);;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|component-handoff|end";;

let component_table =
  let count = length components in
  let table = Array.make count TRUTH and seen = Array.make count false in
  let rec fill = function
    | [] -> ()
    | (component,theorem)::remaining ->
        if component < 0 || component >= count || seen.(component) then
          failwith "TSKAJXY complete: component table drift";
        table.(component) <- theorem;
        seen.(component) <- true;
        fill remaining in
  let rec all_seen index =
    index = count || (seen.(index) && all_seen (index + 1)) in
  fill component_passes;
  if not (all_seen 0) then
    failwith "TSKAJXY complete: component missing";
  table;;

let rec glue = function
  | Projection_mixed_component component -> component_table.(component)
  | Projection_mixed_join (axis,left,right) ->
      let left_theorem = glue left in
      let right_theorem = glue right in
      let appended =
        M_verifier.m_glue_cells_list 6 axis left_theorem right_theorem in
      candle_nonlinear_merge_m_cell_list_pass 6 appended;;

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

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|mixed-reconstruction|begin";;
let root_list_pass = glue skeleton;;
let root_functions,root_domain_term =
  M_verifier.dest_m_cell_list_pass (concl root_list_pass);;
let expected_root_functions =
  [List.nth functions 0;List.nth functions 1;List.nth functions 5];;
let expected_domain,_,_ = M_taylor.dest_m_cell_domain (concl root_domain);;
print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE_ROOT_DIAGNOSTIC" ^
   " root_functions=" ^ string_of_int (length root_functions) ^
   " selected_functions=" ^ string_of_int (length expected_root_functions) ^
   " source_functions=" ^ string_of_int (length functions) ^
   " selected_permutation=" ^
     bool_text (aconv_permutation root_functions expected_root_functions) ^
   " domain_aconv=" ^ bool_text (aconv root_domain_term expected_domain) ^
   " hypotheses=" ^ string_of_int (length (hyp root_list_pass)));;
if not (aconv_permutation root_functions expected_root_functions) ||
   not (aconv root_domain_term expected_domain) ||
   hyp root_list_pass <> [] then
  failwith "TSKAJXY complete: root theorem drift";;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|mixed-reconstruction|end";;

let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|source-reconstruction|begin";;
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
  failwith "TSKAJXY complete: final theorem validation failed";;
let _ =
  print_endline
    "CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE|source-reconstruction|end";;

print_endline
  ("CANDLE_NL_STOCK_PROJECTION_TSKAJXY_COMPLETE_OK" ^
   " DEVELOPMENT_NON_RELEASE source=prep-TSKAJXY-RIBCYXU_sym" ^
   " parameter_index=26 source_leaves=159 components=19" ^
   " numerical_batches=3 topology_verdicts=3 assumptions=0 axiom_growth=0" ^
   " theorem_digest=" ^ digest);;

end;;
