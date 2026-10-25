(* DEVELOPMENT / NON-RELEASE isolated first-jet matan repair stage. *)
if not
     (List.mem
       ("cv_compute_analytic_expr_certificate_patch_compute.ml",
        "43b9e4ecfdcc3210b9ac3d1c86c2b2c3")
       !Cakeml.loadedSourceIds) ||
   not
     (List.mem
       ("cv_compute_analytic_expr_jet_check.ml",
        "97d9fcfc2cfc664fe45375566a4965c7")
       !Cakeml.loadedSourceIds) ||
   List.mem
     ("cv_compute_analytic_expr_first_jet_program_compute.ml",
      "41e3f459c4c7dd904d44b588d7eccd5e")
     !Cakeml.loadedSourceIds then
  failwith "v677 first-jet predecessor boundary mismatch";;

needs "candle/cv_compute_analytic_expr_first_jet_program_compute.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_first_jet_program_compute.ml",
           "41e3f459c4c7dd904d44b588d7eccd5e")
          !Cakeml.loadedSourceIds) then
  failwith "v677 first-jet source identity did not commit"
else
  print_endline "CANDLE_FLYSPECK_V677_FIRST_JET_CHECKPOINT_READY";;
