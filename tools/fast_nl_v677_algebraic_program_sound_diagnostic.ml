(* DEVELOPMENT / NON-RELEASE residual-goal diagnostic in an isolated tree. *)
let candle_v677_program_sound_original =
  "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml";;

let candle_v677_program_sound_diagnostic =
  "/project/worktrees/candle-fast-nl-matan-diagnostic-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml";;

let candle_v677_inherited_overlay =
  match !Cakeml.normalizationOverlay with
  | None -> failwith "v677 diagnostic normalization overlay absent"
  | Some mappings -> mappings;;

if List.length candle_v677_inherited_overlay <> 114 ||
   Alist.lookup candle_v677_inherited_overlay
     candle_v677_program_sound_original <>
     Some
       "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml" then
  failwith "v677 diagnostic overlay predecessor mismatch";;

let candle_v677_diagnostic_overlay =
  map
    (fun (original,current) ->
      if original = candle_v677_program_sound_original then
        (original,candle_v677_program_sound_diagnostic)
      else (original,current))
    candle_v677_inherited_overlay;;

if List.length candle_v677_diagnostic_overlay <> 114 ||
   Alist.lookup candle_v677_diagnostic_overlay
     candle_v677_program_sound_original <>
     Some candle_v677_program_sound_diagnostic then
  failwith "v677 diagnostic overlay replacement mismatch"
else
  Cakeml.normalizationOverlay := Some candle_v677_diagnostic_overlay;;

needs "candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml";;

failwith "v677 diagnostic unexpectedly completed without a residual goal";;
