(* DEVELOPMENT / NON-RELEASE stable prerequisite boundary for matan repair. *)
#use "/project/flyspeck-candle-project/tools/fast_nl_v677_matan_repair_overlay.ml";;

if List.mem
     ("cv_compute_analytic_expr_certificate_patch_compute.ml",
      "43b9e4ecfdcc3210b9ac3d1c86c2b2c3")
     !Cakeml.loadedSourceIds ||
   List.mem
     ("cv_compute_analytic_expr_jet_check.ml",
      "97d9fcfc2cfc664fe45375566a4965c7")
     !Cakeml.loadedSourceIds ||
   List.mem
     ("cv_compute_analytic_expr_first_jet_program_compute.ml",
      "41e3f459c4c7dd904d44b588d7eccd5e")
     !Cakeml.loadedSourceIds then
  failwith "v677 pre-first-jet source already loaded in predecessor";;

needs "candle/cv_compute_analytic_expr_certificate_patch_compute.ml";;
needs "candle/cv_compute_analytic_expr_jet_check.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_certificate_patch_compute.ml",
           "43b9e4ecfdcc3210b9ac3d1c86c2b2c3")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_jet_check.ml",
           "97d9fcfc2cfc664fe45375566a4965c7")
          !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_first_jet_program_compute.ml",
      "41e3f459c4c7dd904d44b588d7eccd5e")
     !Cakeml.loadedSourceIds then
  failwith "v677 pre-first-jet checkpoint boundary mismatch"
else
  print_endline
    "CANDLE_FLYSPECK_V677_PRE_FIRST_JET_CHECKPOINT_READY";;
