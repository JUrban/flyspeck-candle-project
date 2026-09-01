(* Mirror the selected simultaneous operator binding and require (==) to
   return a theorem-like value, not the built-in physical-equality bool. *)
let pointer_identity_shadowing_oracle_ok =
  let (+), ( * ), (!), (==) =
    (fun x y -> x + y),
    (fun x y -> x * y),
    (fun x -> x),
    (fun x y -> (x,y)) in
  let theorem_like = (! 1 + ! 2) == (! 3 * ! 4) in
  theorem_like = (3,12);;
