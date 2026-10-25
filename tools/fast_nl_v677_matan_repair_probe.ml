(* DEVELOPMENT / NON-RELEASE focused semantic proof-load.

   This repeats only the first v677 boundary from the fresh authenticated v676
   predecessor.  It is capped below the project's long-run threshold. *)
#use "/project/flyspeck-candle-project/tools/fast_nl_v677_matan_repair_overlay.ml";;

let candle_flyspeck_v677_repaired_original_identities =
 [("cv_compute_analytic_expr_certificate_patch.ml","7a84867e06ab73da17ba3038e9d41278");
  ("cv_compute_analytic_expr_certificate_patch_compute.ml","43b9e4ecfdcc3210b9ac3d1c86c2b2c3");
  ("cv_compute_analytic_expr_certificate_patch_exact.ml","087a8d240ad7fef9f8901b72988bea5f");
  ("cv_compute_analytic_expr_certificate_variant_prepare.ml","14289599b3141c79c09b840e13198145");
  ("cv_compute_analytic_expr_first_jet_program_compute.ml","41e3f459c4c7dd904d44b588d7eccd5e");
  ("cv_compute_analytic_expr_taylor_model_program_compile_sound.ml","f22b795b191e08854a1872fb4fff81eb");
  ("cv_compute_analytic_expr_taylor_model_program_compute.ml","8094d33d76dbf841f198d009b5225cf1");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml","0b2437383e94614ae9a8b0745ddf9142");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compute.ml","c388bf13687f942a1aa121cd8be907fc");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml","5b69606646e9799c587376c01dda3a6d");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml","274f37dc9603bb6e99b1388597de2f92");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear.ml","16f077760e346af72194e5b267809c4d");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml","cdd7194429afaba9b269370f39ff4e7c");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml","eafcaa12f247044ac203c57776593be9");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_outer.ml","b7b283ed3f55e72597e48505f7451d31");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_compile_sound.ml","80165ef922d79097bd46a87b6d36a93d");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_outer_program_sound.ml","8f699db1434dda0bad728b8df8444a25");
  ("cv_compute_analytic_expr_taylor_model_program_fixed_sound.ml","f580a4a4f8ab44a2ff5b0c34417157cd");
  ("cv_compute_analytic_expr_taylor_model_representation.ml","a658b1e2587c76c8e03e8a21434bfc6d")];;

if List.exists
     (fun identity -> List.mem identity !Cakeml.loadedSourceIds)
     candle_flyspeck_v677_repaired_original_identities then
  failwith "v677 repaired source was already loaded in predecessor";;

let candle_flyspeck_v677_matan_repair_started = Unix.gettimeofday();;
print_endline "CANDLE_FLYSPECK_V677_MATAN_REPAIR_PROOF_LOAD_BEGIN";;

needs "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml";;
needs "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_analytic_expr_certificate_patch.ml",
           "7a84867e06ab73da17ba3038e9d41278")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
           "393018a4878384295220afb6fb307ba1")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
           "2d043a6136c50c80fcf332000a157558")
          !Cakeml.loadedSourceIds) then
  failwith "v677 matan repair proof-load identity did not commit"
else
 (print_endline
    ("CANDLE_FLYSPECK_V677_MATAN_REPAIR_PROOF_LOAD_SECONDS " ^
     string_of_float
       (Unix.gettimeofday() -. candle_flyspeck_v677_matan_repair_started));
  print_endline
    "CANDLE_FLYSPECK_V677_MATAN_REPAIR_PROOF_LOAD_READY");;
