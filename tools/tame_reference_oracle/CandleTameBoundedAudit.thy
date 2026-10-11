(* Untrusted bounded differential instrumentation for the reflected tame-graph lane. *)
(* The printed values are benchmark evidence and are never premises of a theorem.     *)

theory CandleTameBoundedAudit
imports TameEnum Worklist
begin

record candle_tame_audit_stats =
  visited_nodes :: nat
  final_visits :: nat
  raw_children :: nat
  next_tame0_children :: nat
  retained_children :: nat
  early_pruned_children :: nat
  final_pruned_children :: nat
  maximum_frontier :: nat
  saw_quadrilateral :: bool
  saw_exceptional_face :: bool
  saw_nonzero_excess :: bool
  saw_multiple_sizes :: bool

definition candle_tame_audit_stats_empty :: candle_tame_audit_stats where
"candle_tame_audit_stats_empty =
  \<lparr> visited_nodes = 0,
    final_visits = 0,
    raw_children = 0,
    next_tame0_children = 0,
    retained_children = 0,
    early_pruned_children = 0,
    final_pruned_children = 0,
    maximum_frontier = 1,
    saw_quadrilateral = False,
    saw_exceptional_face = False,
    saw_nonzero_excess = False,
    saw_multiple_sizes = False \<rparr>"

definition candle_tame_audit_has_face_size :: "nat \<Rightarrow> graph \<Rightarrow> bool" where
"candle_tame_audit_has_face_size n g =
  list_ex (\<lambda>f. length (vertices f) = n) (faces g)"

definition candle_tame_audit_has_exceptional_face :: "graph \<Rightarrow> bool" where
"candle_tame_audit_has_exceptional_face g =
  list_ex (\<lambda>f. 5 \<le> length (vertices f)) (faces g)"

definition candle_tame_audit_bump ::
  "nat \<Rightarrow> graph \<Rightarrow> graph list \<Rightarrow> graph list \<Rightarrow>
   graph list \<Rightarrow> nat \<Rightarrow> candle_tame_audit_stats \<Rightarrow>
   candle_tame_audit_stats" where
"candle_tame_audit_bump p g raw stage0 kept frontier stats =
  stats\<lparr>
    visited_nodes := Suc (visited_nodes stats),
    final_visits := final_visits stats + (if final g then 1 else 0),
    raw_children := raw_children stats + length raw,
    next_tame0_children := next_tame0_children stats + length stage0,
    retained_children := retained_children stats + length kept,
    early_pruned_children :=
      early_pruned_children stats + (length raw - length stage0),
    final_pruned_children :=
      final_pruned_children stats + (length stage0 - length kept),
    maximum_frontier := max (maximum_frontier stats) frontier,
    saw_quadrilateral :=
      saw_quadrilateral stats \<or> candle_tame_audit_has_face_size 4 g,
    saw_exceptional_face :=
      saw_exceptional_face stats \<or> candle_tame_audit_has_exceptional_face g,
    saw_nonzero_excess :=
      saw_nonzero_excess stats \<or> ExcessTable g (vertices g) \<noteq> [],
    saw_multiple_sizes :=
      saw_multiple_sizes stats \<or> 1 < length (polysizes p g)
  \<rparr>"

fun candle_tame_audit_bounded ::
  "nat \<Rightarrow> nat \<Rightarrow> graph list \<Rightarrow> candle_tame_audit_stats
   \<Rightarrow> graph list \<times> candle_tame_audit_stats" where
"candle_tame_audit_bounded 0 p stack stats = (stack,stats)" |
"candle_tame_audit_bounded (Suc fuel) p [] stats = ([],stats)" |
"candle_tame_audit_bounded (Suc fuel) p (g # rest) stats =
   (let raw = next_plane p g;
        stage0 = next_tame0 p g;
        kept = filter (\<lambda>h. \<not> final h \<or> is_tame h) stage0;
        frontier = length kept + length rest
    in candle_tame_audit_bounded fuel p (kept @ rest)
         (candle_tame_audit_bump p g raw stage0 kept frontier stats))"

definition candle_tame_audit_summary ::
  "nat \<Rightarrow> nat \<Rightarrow> nat \<times> candle_tame_audit_stats" where
"candle_tame_audit_summary fuel p =
  (let result = candle_tame_audit_bounded fuel p [Seed p]
     candle_tame_audit_stats_empty
   in (length (fst result), snd result))"

ML "Toplevel.timing := true"

value "candle_tame_audit_summary 10 0"
value "candle_tame_audit_summary 100 0"
value "candle_tame_audit_summary 239 0"
value "candle_tame_audit_summary 240 0"
value "candle_tame_audit_summary 1000 2"

end
