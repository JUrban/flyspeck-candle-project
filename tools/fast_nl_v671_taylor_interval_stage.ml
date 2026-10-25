(* DEVELOPMENT / NON-RELEASE direct-input stage.  Preserve the first expensive
   stable analytic boundary before attempting multivariate Taylor or the
   remaining verifier closure. *)
#use "/project/flyspeck-candle-project/tools/fast_nl_v665_verifier_runtime_compat.ml";;

let float_of_int x = Cake.Double.fromInt x;;
let int_of_float x = Cake.Double.toInt x;;
let floor x = Cake.Double.floor x;;
let float_of_string s =
  match Double.fromString s with
  | None -> failwith "float_of_string"
  | Some value -> value
;;
let abs_float = candle_binary64_abs;;

let candle_fast_nl_v671_add_load_path path =
  if List.mem path !load_path then () else load_path := path :: !load_path;;

List.iter candle_fast_nl_v671_add_load_path
  ["/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs";
   "/project/worktrees/flyspeck-strictbuild-bootstrap-v1";
   "/project/worktrees/candle-direct-fast-nl-runtime-v1";
   "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6/formal_ineqs"];;

let candle_fast_nl_v671_runtime_surface_probe = float_of_string "1.25";;
candle_assert
  (float_ieee_equal candle_fast_nl_v671_runtime_surface_probe 1.25 &&
   int_of_float (float_of_int 7) = 7 &&
   float_ieee_equal (floor candle_fast_nl_v671_runtime_surface_probe) 1.0 &&
   float_ieee_equal
     (abs_float (~-. candle_fast_nl_v671_runtime_surface_probe)) 1.25)
  "fast_nl_v671_runtime_surface";;

needs "arith_options.hl";;
Arith_options.base := 200;;
needs "taylor/theory/taylor_interval-compiled.hl";;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not (List.mem
          ("taylor_interval-compiled.hl","461022ad60f0beaa660e6c8d1df59284")
          !Cakeml.loadedSourceIds)
then failwith "v671 Taylor interval source identity did not commit"
else print_endline
  "CANDLE_FLYSPECK_V671_TAYLOR_INTERVAL_CHECKPOINT_READY";;
