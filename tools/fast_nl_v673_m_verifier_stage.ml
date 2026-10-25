(* DEVELOPMENT / NON-RELEASE checkpoint stage.  This file may run only from
   the authenticated v672 state containing both compiled Taylor theories. *)

let candle_fast_nl_v673_add_load_path path =
  if List.mem path !load_path then () else load_path := path :: !load_path;;

List.iter candle_fast_nl_v673_add_load_path
  ["/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs";
   "/project/worktrees/flyspeck-strictbuild-bootstrap-v1";
   "/project/worktrees/candle-direct-fast-nl-runtime-v1";
   "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6/formal_ineqs"];;

candle_assert
  (!Arith_options.base = 200 &&
   float_ieee_equal (float_of_string "1.25") 1.25 &&
   int_of_float (float_of_int 7) = 7 &&
   float_ieee_equal (floor 1.25) 1.0 &&
   float_ieee_equal (abs_float (~-. 1.25)) 1.25)
  "fast_nl_v673_predecessor_surface";;

needs "verifier/m_verifier_main.hl";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("taylor_interval-compiled.hl","461022ad60f0beaa660e6c8d1df59284")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("multivariate_taylor-compiled.hl","802f2a19f6ad9680040e89e4ae349c78")
          !Cakeml.loadedSourceIds) ||
   not (List.mem
          ("m_verifier_main.hl","ca4991873b0c34b2da24a7080c5f521b")
          !Cakeml.loadedSourceIds) then
  failwith "v673 m_verifier checkpoint identity did not commit"
else
  let _ = M_verifier_main.verify_ineq in
  print_endline "CANDLE_FLYSPECK_V673_M_VERIFIER_CHECKPOINT_READY";;
