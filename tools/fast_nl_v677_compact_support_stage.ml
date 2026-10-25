(* DEVELOPMENT / NON-RELEASE compact tree/stack proof boundary. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
        "393018a4878384295220afb6fb307ba1")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
      "4f77e1cbc03a58f0ae9819b3f08aaa8a")
     !Cakeml.loadedSourceIds then
  failwith "v677 compact-support predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml";;
needs "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
           "4f77e1cbc03a58f0ae9819b3f08aaa8a")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
           "d5ca10ca9408acb7f9ea82460b8b7005")
          !Cakeml.loadedSourceIds) then
  failwith "v677 compact-support identities did not commit"
else
  print_endline "CANDLE_FLYSPECK_V677_COMPACT_SUPPORT_CHECKPOINT_READY";;
