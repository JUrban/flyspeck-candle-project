(* DEVELOPMENT / NON-RELEASE focused algebraic compile-sound stage. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml",
        "5b69606646e9799c587376c01dda3a6d")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml",
      "0b2437383e94614ae9a8b0745ddf9142")
     !Cakeml.loadedSourceIds then
  failwith "v677 fixed-algebraic compile-sound predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml",
           "274f37dc9603bb6e99b1388597de2f92")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml",
           "0b2437383e94614ae9a8b0745ddf9142")
          !Cakeml.loadedSourceIds) then
  failwith "v677 fixed-algebraic compile-sound identities did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_FIXED_ALGEBRAIC_COMPILE_SOUND_CHECKPOINT_READY";;
