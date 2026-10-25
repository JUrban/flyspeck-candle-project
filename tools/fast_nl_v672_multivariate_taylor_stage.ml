(* DEVELOPMENT / NON-RELEASE direct-input stage.  Run only from the sealed
   v671 Taylor-interval predecessor and checkpoint this second expensive leaf
   before loading the enclosing verifier. *)
needs "taylor/theory/multivariate_taylor-compiled.hl";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("taylor_interval-compiled.hl","461022ad60f0beaa660e6c8d1df59284")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("multivariate_taylor-compiled.hl","802f2a19f6ad9680040e89e4ae349c78")
          !Cakeml.loadedSourceIds)
then failwith "v672 multivariate Taylor source identity did not commit"
else print_endline
  "CANDLE_FLYSPECK_V672_MULTIVARIATE_TAYLOR_CHECKPOINT_READY";;
