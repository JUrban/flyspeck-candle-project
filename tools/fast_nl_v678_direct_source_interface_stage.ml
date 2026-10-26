(* DEVELOPMENT / NON-RELEASE direct-source rewrite-interface boundary. *)
let candle_v678_interface_original =
  "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/cv_compute_flyspeck_direct_source_compat.ml";;

let candle_v678_interface_candidate =
  "/project/worktrees/candle-fast-nl-direct-source-interface-v1/candle/cv_compute_flyspeck_direct_source_compat.ml";;

let rec candle_v678_overlay_lookup key mappings =
  match mappings with
  | [] -> None
  | (original,current)::rest ->
      if original = key then Some current
      else candle_v678_overlay_lookup key rest;;

let candle_v678_existing_overlay =
  match !Cakeml.normalizationOverlay with
  | None -> failwith "v678 direct-source interface overlay absent"
  | Some mappings -> mappings;;

if List.length candle_v678_existing_overlay <> 115 ||
   candle_v678_overlay_lookup
     candle_v678_interface_original candle_v678_existing_overlay <> None ||
   List.mem
     ("cv_compute_flyspeck_direct_source_compat.ml",
      "6da54e8de2098d8281bc7e4a8a4dd62a")
     !Cakeml.loadedSourceIds ||
   List.mem
     ("cv_compute_analytic_expr_case10173_fixture.ml",
      "35dabab93dfae8612e9378f752412b75")
     !Cakeml.loadedSourceIds then
  failwith "v678 direct-source interface predecessor mismatch";;

let candle_v678_axioms_before = axioms ();;

Cakeml.normalizationOverlay :=
  Some
    ((candle_v678_interface_original,candle_v678_interface_candidate) ::
     candle_v678_existing_overlay);;

if List.length
     (match !Cakeml.normalizationOverlay with
      | None -> []
      | Some mappings -> mappings) <> 116 ||
   candle_v678_overlay_lookup
     candle_v678_interface_original
     (match !Cakeml.normalizationOverlay with
      | None -> []
      | Some mappings -> mappings) <>
     Some candle_v678_interface_candidate then
  failwith "v678 direct-source interface overlay postcondition";;

needs "candle/cv_compute_analytic_expr_case10173_fixture.ml";;

let candle_v678_axioms_after = axioms ();;

if !Cakeml.pendingLoadedSourceIds <> [] ||
   not
     (List.mem
       ("cv_compute_flyspeck_direct_source_compat.ml",
        "6da54e8de2098d8281bc7e4a8a4dd62a")
       !Cakeml.loadedSourceIds) ||
   not
     (List.mem
       ("cv_compute_analytic_expr_case10173_fixture.ml",
        "35dabab93dfae8612e9378f752412b75")
       !Cakeml.loadedSourceIds) ||
   hyp
     Candle_cv_flyspeck_direct_source_compat.candle_direct_subat_rules <> [] ||
   hyp
     Candle_cv_flyspeck_direct_source_compat.candle_direct_subat_explicit <> [] ||
   hyp
     Candle_cv_flyspeck_direct_source_compat.candle_direct_bisect_left_frac <> [] ||
   hyp
     Candle_cv_flyspeck_direct_source_compat.candle_direct_bisect_right_frac <> [] ||
   hyp Candle_cv_flyspeck_direct_source_compat.candle_direct_ineq6m <> [] ||
   hyp Candle_cv_flyspeck_direct_source_compat.candle_direct_ineq9m <> [] ||
   hyp
     Candle_cv_analytic_expr_case10173_fixture.candle_case10173_analytic_reconstruction <>
     [] ||
   not
     (aconv
       (lhand
         (concl
           Candle_cv_analytic_expr_case10173_fixture.candle_case10173_analytic_reconstruction))
       Candle_cv_analytic_expr_case10173_fixture.candle_case10173_analytic_target) ||
   List.length candle_v678_axioms_after <>
     List.length candle_v678_axioms_before ||
   not
     (List.for_all
       (fun axiom -> List.mem axiom candle_v678_axioms_before)
       candle_v678_axioms_after) then
  failwith "v678 direct-source interface validation"
else
  print_endline
    "CANDLE_FLYSPECK_V678_DIRECT_SOURCE_INTERFACE_CHECKPOINT_READY";;
