(* DEVELOPMENT / NON-RELEASE fixed-scale analytic checkpoint stage. *)

candle_assert
  (List.flatten [[1];[];[2;3]] = [1;2;3])
  "fast_nl_v677_list_surface";;

needs "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml";;
needs "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_exact_interval_matan_series_program.ml",
           "8baa6fa6c5cb749377f07339d36f3705")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
           "393018a4878384295220afb6fb307ba1")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
           "2d043a6136c50c80fcf332000a157558")
          !Cakeml.loadedSourceIds) then
  failwith "v677 fixed-scale checkpoint identity did not commit"
else
  print_endline "CANDLE_FLYSPECK_V677_FIXED_SCALE_CHECKPOINT_READY";;
