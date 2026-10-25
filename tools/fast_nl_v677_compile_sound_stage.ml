(* DEVELOPMENT / NON-RELEASE isolated repaired compile-sound proof stage. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_certified_compute.ml",
        "55f64b9c3e367d9e1579133e17bf8c86")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
      "f22b795b191e08854a1872fb4fff81eb")
     !Cakeml.loadedSourceIds then
  failwith "v677 compile-sound predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_taylor_model_program_compile_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
           "f22b795b191e08854a1872fb4fff81eb")
          !Cakeml.loadedSourceIds) then
  failwith "v677 compile-sound source identity did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_COMPILE_SOUND_CHECKPOINT_READY";;
