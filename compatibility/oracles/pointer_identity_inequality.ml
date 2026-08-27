(* Minimal OCaml/Candle differential for selected non-ref physical inequality. *)
let first = [1];;
let second = [1];;
if first != second then
  ()
else
  failwith "separately allocated lists were physically equal";;
