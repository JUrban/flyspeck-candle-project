(* DEVELOPMENT / NON-RELEASE serialization/break-case bridge boundary. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
        "4f77e1cbc03a58f0ae9819b3f08aaa8a")
       !Cakeml.loadedSourceIds) ||
   List.mem ("serialization.hl","9228eaf6a96159d9f59fea40fcc2a12f")
     !Cakeml.loadedSourceIds ||
   List.mem ("break_case_exec.hl","736fb16a1dab5f13102fdb185a0a1c08")
     !Cakeml.loadedSourceIds then
  failwith "v677 direct-bridge predecessor mismatch";;

needs "/project/flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck/text_formalization/general/serialization.hl";;
needs "/project/flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck/text_formalization/nonlinear/break_case_exec.hl";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem ("serialization.hl","9228eaf6a96159d9f59fea40fcc2a12f")
          !Cakeml.loadedSourceIds) ||
   not (List.mem ("break_case_exec.hl","736fb16a1dab5f13102fdb185a0a1c08")
          !Cakeml.loadedSourceIds) then
  failwith "v677 direct-bridge identities did not commit"
else
  print_endline "CANDLE_FLYSPECK_V677_DIRECT_BRIDGE_CHECKPOINT_READY";;
