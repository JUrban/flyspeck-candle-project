(* DEVELOPMENT / NON-RELEASE exact 4,173-record tag-10 regression. *)

open Candle_cv_analytic_expr_jet_prove;;
open Candle_cv_analytic_expr_case10173_historical_dihedral_checked_compute;;
open Benchmark_cv_compute_analytic_expr_case10173_historical_registered_input;;

let candle_v679d_input =
  candle_case10173_historical_registered_input ();;

candle_q_dim_analytic_jet_profile_event "v679d-tag10-full-compute-begin";;

let candle_v679d_full_theorem =
  candle_q_dim_analytic_jet_compute
    candle_cv_case10173_hist_checked_program_compute_eqs
    candle_v679d_input.registered_input_checked_call;;

candle_q_dim_analytic_jet_profile_event "v679d-tag10-full-compute-end";;

if hyp candle_v679d_full_theorem <> [] ||
   not
     (aconv (lhand (concl candle_v679d_full_theorem))
       candle_v679d_input.registered_input_checked_call) ||
   not (aconv (rand (concl candle_v679d_full_theorem)) `Cexp_num 1`)
then failwith "v679d tag10 full batch validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679D_TAG10_FULL_BATCH_OK DEVELOPMENT_NON_RELEASE cells=4173 result=1 authenticated_aux_roots=16692 assumptions=0";;
