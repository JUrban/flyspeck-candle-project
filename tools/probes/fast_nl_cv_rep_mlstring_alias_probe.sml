open HolKernel Abbrev Parse boolLib bossLib;

val _ = load "basis_cvTheory";
val _ = load "compute_evalPureTheory";
val _ = new_theory "fastNlCvRepMlstringAliasProbe";

fun theorem_result_type th =
  th |> UNDISCH_ALL |> concl |> rand |> type_of |> dom_rng |> snd;

fun const_identity tm =
  let
    val {Thy,Name,...} = dest_thy_const (repeat rator tm)
  in
    Thy ^ "$" ^ Name
  end;

val canonical = basis_cvTheory.from_mlstring_to_mlstring_mlstring_thm;
val duplicate = compute_evalPureTheory.from_mlstring_to_mlstring_mlstring_thm;
val shared_type = theorem_result_type canonical;
val _ = if shared_type = theorem_result_type duplicate then ()
        else raise Fail "the duplicate converters do not have the same type";

val before_from = cv_typeLib.from_term_for shared_type;
val _ = print ("BEFORE_FROM=" ^ const_identity before_from ^ "\n");

val basis_rep = basis_cvTheory.cv_rep_mlstring_mlstring_mlstring_datatype;
val representative =
  basis_rep |> SPEC_ALL |> CONJUNCTS |> el 2 |> concl |> lhs |> rand;
val _ = print ("REPRESENTATIVE=" ^ term_to_string representative ^ "\n");
val _ = print ("REPRESENTATIVE_TYPE=" ^
               type_to_string (type_of representative) ^ "\n");
val before_probe =
  (cv_repLib.cv_rep_for [] representative; "accepted")
  handle _ => "rejected";
val _ = print ("BEFORE_REP=" ^ before_probe ^ "\n");

val _ = save_thm
  ("canonical_basis_mlstring_cv_rep[cv_rep]", basis_rep);
val mismatch_from = cv_typeLib.from_term_for shared_type;
val mismatch_probe =
  (cv_repLib.cv_rep_for [] representative; "accepted")
  handle HOL_ERR _ => "rejected";
val _ = print ("MISMATCH_FROM=" ^ const_identity mismatch_from ^ "\n");
val _ = print ("MISMATCH_REP=" ^ mismatch_probe ^ "\n");
val _ = if mismatch_probe = "rejected" then ()
        else raise Fail "the namespace-mismatch reproducer unexpectedly passed";

val _ = cv_memLib.cv_from_to_add canonical;
val after = cv_typeLib.from_term_for shared_type;
val _ = print ("AFTER_FROM=" ^ const_identity after ^ "\n");
val _ = if const_identity after =
             "basis_cv$from_mlstring_mlstring_mlstring"
        then ()
        else raise Fail "canonical basis converter did not take precedence";

val after_rep = cv_repLib.cv_rep_for [] representative;
val after_rep_from =
  after_rep |> UNDISCH_ALL |> concl |> cv_miscLib.cv_rep_from;
val _ = print ("AFTER_REP_FROM=" ^ const_identity after_rep_from ^ "\n");
val _ = if const_identity after_rep_from =
             "basis_cv$from_mlstring_mlstring_mlstring"
        then ()
        else raise Fail "derived cv_rep theorem did not use canonical converter";

val _ = print "FAST_NL_CV_REP_MLSTRING_ALIAS_PROBE_OK\n";
