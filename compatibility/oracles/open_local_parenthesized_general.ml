module Parenthesized_general_oracle = struct
  let value = 7
end;;

let value = 100;;

let parenthesized_general_value = Parenthesized_general_oracle.(value + 1);;

let open_local_parenthesized_general_ocaml_ok =
  if parenthesized_general_value = 8 then 1
  else failwith "parenthesized general-expression name resolution differs";;
