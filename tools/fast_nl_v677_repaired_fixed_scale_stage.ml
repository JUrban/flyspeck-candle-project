(* DEVELOPMENT / NON-RELEASE continuation from the proved first-jet boundary. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_first_jet_program_compute.ml",
        "41e3f459c4c7dd904d44b588d7eccd5e")
       !Cakeml.loadedSourceIds) then
  failwith "v677 repaired fixed-scale predecessor mismatch";;

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
  failwith "v677 repaired fixed-scale identity did not commit"
else
  print_endline
    "CANDLE_FLYSPECK_V677_REPAIRED_FIXED_SCALE_CHECKPOINT_READY";;
