(* Minimal OCaml/Candle differential for the selected n == 1 shape. *)
let n = 1;;
if n == 1 then
  print_endline "pointer-identity-immediate-oracle: ok"
else
  failwith "equal immediate ints were not physically equal";;
