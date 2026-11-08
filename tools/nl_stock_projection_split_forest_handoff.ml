(* ========================================================================== *)
(* Multi-root forest extraction from retained numerical and split topology.  *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  This generic adapter reuses an already proved *)
(* raw numerical batch.  Kernel.compute checks only the encoded postorder    *)
(* topology; the general split-stack soundness theorem supplies the logical  *)
(* stack invariant, from which one closed source theorem is recovered per    *)
(* root.  No numerical cell is evaluated a second time.                      *)
(* ========================================================================== *)

module Candle_nl_stock_projection_split_forest_handoff = struct

open M_verifier;;
open Candle_cv_analytic_expr_jet_prove;;
open Candle_cv_analytic_expr_stable_program_data;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_raw_prove;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stream_sound;;
open Candle_cv_analytic_expr_taylor_model_program_fixed_outer_variable_split_stack_prove;;

type candle_nl_stock_projection_split_forest_result_six = {
  projection_split_forest_stack_result :
    candle_q_dim_taylor_model_fixed_outer_variable_split_stack_result_six;
  projection_split_forest_stack_decode : thm;
  projection_split_forest_root_boxes : term list;
  projection_split_forest_cell_theorems : thm list;
  projection_split_forest_source_theorems : thm list;
};;

let rec aconv_lists left right =
  match left,right with
  | [],[] -> true
  | left_head::left_tail,right_head::right_tail ->
      aconv left_head right_head && aconv_lists left_tail right_tail
  | _ -> false;;

let rec extract_cells count theorem =
  if count <= 0 then
    failwith "projection split forest: empty theorem extraction"
  else if count = 1 then [theorem]
  else
    CONJUNCT1 theorem :: extract_cells (count - 1) (CONJUNCT2 theorem);;

let decode_stack encoded_stack =
  let call = mk_comb (`candle_cv_q_boxes_stack_decode`,encoded_stack) in
  let theorem =
    REWRITE_CONV
      [candle_cv_q_boxes_stack_decode_def;
       candle_cv_q_interval_list_decode_def;
       candle_cv_q_interval_decode_def;candle_cv_q_decode_def;
       candle_cv_lc_z_decode_def;candle_cv_lc_num_decode_def;
       cexp_fst_def;cexp_snd_def;FST;SND]
      call in
  if hyp theorem <> [] || not (aconv (lhand (concl theorem)) call) then
    failwith "projection split forest: stack decode mismatch";
  theorem;;

let candle_nl_stock_projection_split_forest_six
    (raw_result:
      candle_q_dim_taylor_model_fixed_outer_variable_raw_result_six)
    tokens encoded_tokens expected_stack_boxes =
  if expected_stack_boxes = [] then
    failwith "projection split forest: empty expected stack";
  let prepared = raw_result.variable_raw_prepared_source in
  let stack_result =
    candle_q_dim_taylor_model_fixed_outer_variable_split_stack_six
      raw_result tokens encoded_tokens in
  let stack_decode =
    decode_stack stack_result.variable_split_encoded_stack_term in
  let root_boxes =
    dest_list (rand (concl stack_decode)) in
  if not (aconv_lists root_boxes expected_stack_boxes) then
    failwith "projection split forest: root box drift";
  let expanded_stack =
    REWRITE_RULE
      [stack_decode;
       candle_q_dim_taylor_model_fixed_outer_variable_compact_stack_pass_def]
      stack_result.variable_split_stack_theorem in
  let cell_theorems = extract_cells (length root_boxes) expanded_stack in
  let source_theorems =
    map
      (fun theorem ->
        let source =
          REWRITE_RULE [m_cell_pass;prepared.source_theorem] theorem in
        if hyp theorem <> [] || hyp source <> [] then
          failwith "projection split forest: source assumptions";
        source)
      cell_theorems in
  {projection_split_forest_stack_result = stack_result;
   projection_split_forest_stack_decode = stack_decode;
   projection_split_forest_root_boxes = root_boxes;
   projection_split_forest_cell_theorems = cell_theorems;
   projection_split_forest_source_theorems = source_theorems};;

print_endline
  "CANDLE_NL_STOCK_PROJECTION_SPLIT_FOREST_HANDOFF_OK DEVELOPMENT_NON_RELEASE";;

end;;
