(* Minimal OCaml/Candle differential for selected non-ref physical identity. *)
let original = [1];;
let alias = original;;
if original == alias then
  print_endline "pointer-identity-list-oracle: ok"
else
  failwith "alias was not physically equal";;
