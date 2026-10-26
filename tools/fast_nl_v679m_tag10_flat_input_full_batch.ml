(* DEVELOPMENT / NON-RELEASE exact 4,173-record tag-10 computation from the
   authenticated flat-input checkpoint.  Keep the large theorem inside a
   module so the interactive printer exposes only its type. *)

module Candle_fast_nl_v679m_tag10_full_batch = struct

open Candle_cv_analytic_expr_jet_prove;;
open Candle_cv_analytic_expr_case10173_historical_dihedral_checked_compute;;
open Candle_fast_nl_v679l_prepared_input;;

let candle_v679m_axioms_before = axioms ();;

let _ =
  candle_q_dim_analytic_jet_profile_event
    "v679m-tag10-flat-input-full-compute-begin";;

let candle_v679m_full_theorem =
  candle_q_dim_analytic_jet_compute
    candle_cv_case10173_hist_checked_program_compute_eqs
    candle_v679l_checked_call;;

let _ =
  candle_q_dim_analytic_jet_profile_event
    "v679m-tag10-flat-input-full-compute-end";;

let candle_v679m_valid =
  hyp candle_v679m_full_theorem = [] &&
  aconv (lhand (concl candle_v679m_full_theorem))
    candle_v679l_checked_call &&
  aconv (rand (concl candle_v679m_full_theorem)) `Cexp_num 1`;;

end;;

let candle_v679m_axioms_after = axioms ();;

if not Candle_fast_nl_v679m_tag10_full_batch.candle_v679m_valid ||
   List.length candle_v679m_axioms_after <>
     List.length
       Candle_fast_nl_v679m_tag10_full_batch.candle_v679m_axioms_before ||
   not
     (List.for_all
       (fun axiom ->
         List.mem axiom
           Candle_fast_nl_v679m_tag10_full_batch.candle_v679m_axioms_before)
       candle_v679m_axioms_after) then
  failwith "v679m tag10 full batch validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679M_TAG10_FLAT_INPUT_FULL_BATCH_READY DEVELOPMENT_NON_RELEASE cells=4173 result=1 authenticated_aux_roots=16692 assumptions=0 axiom_growth=0";;
