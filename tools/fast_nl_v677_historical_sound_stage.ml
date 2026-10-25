(* DEVELOPMENT / NON-RELEASE historical-soundness proof boundary. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
        "cdd7194429afaba9b269370f39ff4e7c")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
      "393018a4878384295220afb6fb307ba1")
     !Cakeml.loadedSourceIds then
  failwith "v677 historical-soundness predecessor mismatch";;

needs "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml";;
needs "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
           "393018a4878384295220afb6fb307ba1")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
           "2d043a6136c50c80fcf332000a157558")
          !Cakeml.loadedSourceIds) then
  failwith "v677 historical-soundness identities did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_HISTORICAL_SOUND_CHECKPOINT_READY";;
