(* DEVELOPMENT / NON-RELEASE exact-interval matan checkpoint stage. *)

candle_assert
  (List.flatten [[1];[];[2;3]] = [1;2;3])
  "fast_nl_v676_list_surface";;

needs "candle/cv_compute_exact_interval_matan_series.ml";;
needs "candle/cv_compute_exact_interval_matan_series_program.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("cv_compute_polynomial_expr_dim_jet_semantics.ml",
           "2cedcfc47a7658a443847039ea1f25eb")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_exact_interval_matan_series.ml",
           "7461529a70e5f006cf0ecc8c45ba4297")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_exact_interval_matan_series_program.ml",
           "8baa6fa6c5cb749377f07339d36f3705")
          !Cakeml.loadedSourceIds) then
  failwith "v676 matan checkpoint identity did not commit"
else
  print_endline "CANDLE_FLYSPECK_V676_MATAN_CHECKPOINT_READY";;
