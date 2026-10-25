(* DEVELOPMENT / NON-RELEASE focused repair proof from compile-sound state. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
        "f22b795b191e08854a1872fb4fff81eb")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml",
      "5b69606646e9799c587376c01dda3a6d")
     !Cakeml.loadedSourceIds then
  failwith "v677 fixed-algebraic-item predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml",
           "5b69606646e9799c587376c01dda3a6d")
          !Cakeml.loadedSourceIds) then
  failwith "v677 fixed-algebraic-item identity did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_FIXED_ALGEBRAIC_ITEM_INVARIANT_CHECKPOINT_READY";;
