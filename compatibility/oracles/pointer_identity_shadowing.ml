(* Local name resolution must override the built-in reference-only operator. *)
let pointer_identity_shadowing_oracle_ok =
  let (==) x y = x = y in
  [1] == [1];;
