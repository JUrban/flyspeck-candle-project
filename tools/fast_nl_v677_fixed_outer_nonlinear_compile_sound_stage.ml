(* DEVELOPMENT / NON-RELEASE outer/nonlinear compile-sound proof batch. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml",
        "0b2437383e94614ae9a8b0745ddf9142")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
      "cdd7194429afaba9b269370f39ff4e7c")
     !Cakeml.loadedSourceIds then
  failwith "v677 outer/nonlinear compile-sound predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_program_sound.ml",
           "8f699db1434dda0bad728b8df8444a25")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_compile_sound.ml",
           "80165ef922d79097bd46a87b6d36a93d")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml",
           "eafcaa12f247044ac203c57776593be9")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
           "cdd7194429afaba9b269370f39ff4e7c")
          !Cakeml.loadedSourceIds) then
  failwith "v677 outer/nonlinear compile-sound identities did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_FIXED_OUTER_NONLINEAR_COMPILE_SOUND_CHECKPOINT_READY";;
