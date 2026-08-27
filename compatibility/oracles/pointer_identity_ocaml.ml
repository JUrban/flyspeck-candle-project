(* OCaml 4.14 reference oracle for the G3 identity distinctions. *)
let left = ref 0;;
let alias = left;;
let equal_but_distinct = ref 0;;

if left = equal_but_distinct && left == alias && left != equal_but_distinct
then () else failwith "OCaml reference identity mismatch";;

(* OCaml ints, chars, and booleans are immediate in the pinned reference. *)
if 1 == 1 && 'x' == 'x' && true != false
then () else failwith "OCaml immediate identity mismatch";;

(* This is value equality, not pointer identity, after local resolution. *)
let (==) x y = x = y in
if [1] == [1] then () else failwith "OCaml local operator resolution mismatch";;

print_endline "pointer-identity-oracle: ok";;
