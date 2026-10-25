(* DEVELOPMENT / NON-RELEASE support-foundation checkpoint stage. *)

candle_assert
  (List.flatten [[1;2];[];[3;4]] = [1;2;3;4])
  "fast_nl_v675_list_surface";;

needs "candle/cv_compute_polynomial_expr_dim_jet_semantics.ml";;
needs "candle/cv_compute_exact_interval_square_core.ml";;
needs "candle/cv_compute_exact_rational_inv.ml";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("m_verifier_main.hl","ca4991873b0c34b2da24a7080c5f521b")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_polynomial_expr_dim_jet_semantics.ml",
           "2cedcfc47a7658a443847039ea1f25eb")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_exact_interval_square_core.ml",
           "0a342a6887dc5ff35eaae2d3447eba12")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("cv_compute_exact_rational_inv.ml",
           "d2a4afdcb26c9eb12fefc2c6a935602d")
          !Cakeml.loadedSourceIds) then
  failwith "v675 foundation checkpoint identity did not commit"
else
  print_endline "CANDLE_FLYSPECK_V675_FOUNDATION_CHECKPOINT_READY";;
