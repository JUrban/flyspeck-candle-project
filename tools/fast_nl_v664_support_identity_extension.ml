(* DEVELOPMENT / NON-RELEASE authenticated identity closure for the first
   fast-NL theorem support graph.

   A mechanical traversal from the four support entry points resolves 245
   source nodes and 398 literal dependency edges.  The v656 table covered all
   but these 11 exact bootstrap/formal_ineqs paths.  Keep this as a separate,
   reviewable extension and fail on any count drift before source identities
   are installed. *)
let candle_fast_nl_v664_support_identity_extension = [
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/arith/interval_arith.hl",("interval_arith.hl","0af2e87c2a753e4736e6bf5078a8dca4"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/lib/ssrbool.hl",("ssrbool.hl","aa04bba1f6f142aed2a049b4511106d5"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/lib/ssreflect/sections.hl",("sections.hl","4b207a2e7a8b7ab7f86f9cb9ffd80d88"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/lib/ssreflect/ssreflect.hl",("ssreflect.hl","ee9aa6011f0277ca2a4ed190515e99c9"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/lib/ssrfun.hl",("ssrfun.hl","031939698158f77c7913d12396445f35"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/lib/ssrnat.hl",("ssrnat.hl","16500e2d805ccbe7da700138ce14b87e"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/misc/misc_vars.hl",("misc_vars.hl","74887cce49991876672087f6e9812852"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/misc/report.hl",("report.hl","19cf18cda718471efb4d659bf8aff07c"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/taylor/theory/taylor_interval-compiled.hl",("taylor_interval-compiled.hl","461022ad60f0beaa660e6c8d1df59284"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/trig/matan.hl",("matan.hl","900f6f8aeaab2eb44e20fb1f43674890"));
  ("/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/trig/series.hl",("series.hl","a586ddb93975e3c1fcb10250f062dd6f"));
];;

if List.length candle_fast_nl_v664_support_identity_extension <> 11 then
  failwith "v664 fast-NL support identity extension count mismatch";;

let candle_fast_nl_extra_source_identities =
  candle_fast_nl_v664_support_identity_extension @
  candle_fast_nl_extra_source_identities;;

if List.length candle_fast_nl_extra_source_identities <> 218 then
  failwith "v664 complete fast-NL source identity count mismatch";;
