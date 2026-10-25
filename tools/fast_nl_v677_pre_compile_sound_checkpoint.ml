(* DEVELOPMENT / NON-RELEASE stable boundary before changing compile sound. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_first_jet_program_compute.ml",
        "41e3f459c4c7dd904d44b588d7eccd5e")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
      "f22b795b191e08854a1872fb4fff81eb")
     !Cakeml.loadedSourceIds then
  failwith "v677 pre-compile-sound predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_fixed_scale_invariant.ml";;
needs "candle/cv_compute_analytic_expr_taylor_model_program_nonlinear_sound.ml";;
needs "candle/cv_compute_analytic_expr_taylor_model_certified_compute.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_invariant.ml",
           "2b2da6871d5867cea459cb052dcdedde")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_nonlinear_sound.ml",
           "20bfda01c785ef1d74d8e4725e7d43e6")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_certified_compute.ml",
           "55f64b9c3e367d9e1579133e17bf8c86")
          !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
      "f22b795b191e08854a1872fb4fff81eb")
     !Cakeml.loadedSourceIds then
  failwith "v677 pre-compile-sound checkpoint boundary mismatch"
else
  print_endline
    "CANDLE_FLYSPECK_V677_PRE_COMPILE_SOUND_CHECKPOINT_READY";;
