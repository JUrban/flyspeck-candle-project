(* ========================================================================== *)
(* Exact hminus interval setup for stock nonlinear projection probes.         *)
(*                                                                            *)
(* DEVELOPMENT / NON-RELEASE.  The three exclusion intervals are checked by  *)
(* Flyspeck's ordinary proof-producing verifier.  The final enclosure uses    *)
(* the already-proved production theorem Nonlinear_lemma.hminus_prop, avoiding *)
(* the standalone formal_tests/hminus.hl continuity-test dependencies.       *)
(* ========================================================================== *)

module Candle_nl_stock_projection_hminus_setup = struct

open M_verifier_main;;

let lmfun_cond_le =
  (UNDISCH_ALL o prove)
    (`x <= h0 ==> lmfun x = (h0 - x) / (h0 - &1)`,
     REWRITE_TAC[Sphere.lmfun] THEN REAL_ARITH_TAC);;

let lmfun_cond_ge =
  (UNDISCH_ALL o prove)
    (`h0 <= x ==> lmfun x = &0`,
     ONCE_REWRITE_TAC
       [REAL_ARITH `a <= b <=> ~(b <= a) \/ a = b`] THEN
     STRIP_TAC THEN ASM_REWRITE_TAC[Sphere.lmfun] THEN REAL_ARITH_TAC);;

let eq_tm = `marchal_quartic x - lmfun x`;;
let eq_th1,eq_th2 =
  let ths = [Sphere.marchal_quartic;Sphere.h0;Sphere.hplus] in
  REWRITE_CONV (lmfun_cond_le :: ths) eq_tm,
  REWRITE_CONV (REAL_SUB_RZERO :: lmfun_cond_ge :: ths) eq_tm;;

let eq_tm1 = (rand o concl) eq_th1
and eq_tm2 = (rand o concl) eq_th2;;

let ineq1_concl = mk_binary "real_lt" (eq_tm1,`&0`)
and ineq2_concl = mk_binary "real_lt" (`&0`,eq_tm1)
and ineq3_concl = mk_binary "real_lt" (`&0`,eq_tm2);;

let bounds1 = `#1.2 <= x /\ x <= #1.2317544220903043901`
and bounds2 = `#1.2317544220903047 <= x /\ x <= #1.26`
and bounds3 = `#1.26 <= x /\ x <= #1.3`;;

let ineq1_tm = mk_imp (bounds1,ineq1_concl)
and ineq2_tm = mk_imp (bounds2,ineq2_concl)
and ineq3_tm = mk_imp (bounds3,ineq3_concl);;

let ineq1_th,_ = verify_ineq default_params 12 ineq1_tm;;
let ineq2_th,_ = verify_ineq default_params 12 ineq2_tm;;
let ineq3_th,_ = verify_ineq default_params 12 ineq3_tm;;

let outside_excluded =
  prove
    (`(#1.2 <= x /\ x < #1.3) /\
      ~(#1.2317544220903043901 <= x /\
        x <= #1.2317544220903047)
      ==> ~(marchal_quartic x = lmfun x)`,
     REWRITE_TAC[DE_MORGAN_THM;REAL_NOT_LE] THEN
     ONCE_REWRITE_TAC[REAL_ARITH `a = b <=> a - b = &0`] THEN
     STRIP_TAC THENL
      [MP_TAC (SPEC_ALL ineq1_th) THEN
       ASM_SIMP_TAC[REAL_LT_IMP_LE] THEN
       MP_TAC (DISCH_ALL eq_th1) THEN REWRITE_TAC[Sphere.h0] THEN
       ANTS_TAC THENL
        [REPEAT (POP_ASSUM MP_TAC) THEN REAL_ARITH_TAC; ALL_TAC] THEN
       DISCH_THEN (fun th -> REWRITE_TAC[GSYM th]) THEN REAL_ARITH_TAC;
       ALL_TAC] THEN
     DISJ_CASES_TAC (REAL_ARITH `x <= #1.26 \/ #1.26 <= x`) THENL
      [MP_TAC (SPEC_ALL ineq2_th) THEN
       ASM_SIMP_TAC[REAL_LT_IMP_LE] THEN
       MP_TAC (DISCH_ALL eq_th1) THEN ASM_REWRITE_TAC[Sphere.h0] THEN
       DISCH_THEN (fun th -> REWRITE_TAC[GSYM th]) THEN REAL_ARITH_TAC;
       ALL_TAC] THEN
     MP_TAC (SPEC_ALL ineq3_th) THEN
     ASM_SIMP_TAC[REAL_LT_IMP_LE] THEN
     MP_TAC (DISCH_ALL eq_th2) THEN ASM_REWRITE_TAC[Sphere.h0] THEN
     DISCH_THEN (fun th -> REWRITE_TAC[GSYM th]) THEN REAL_ARITH_TAC);;

let hminus_interval =
  prove
    (`interval_arith hminus
       (#1.2317544220903043901,#1.2317544220903047)`,
     REWRITE_TAC[Interval_arith.interval_arith] THEN
     MP_TAC (INST [`hminus:real`,`x:real`] outside_excluded) THEN
     MP_TAC Nonlinear_lemma.hminus_prop THEN MESON_TAC[]);;

let _ = add_constant_interval hminus_interval;;

end;;
