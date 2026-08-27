module Parenthesized_open_oracle = struct
  let ( ++ ) left right = left * 10 + right
  module Nested = struct
    let ( **+ ) left right = left * 100 + right
  end
end;;

let ( ++ ) _ _ = 0;;
let ( **+ ) _ _ = 0;;

let parenthesized_open_operator = Parenthesized_open_oracle.(++) 3 4;;
let parenthesized_dotted_operator =
  Parenthesized_open_oracle.Nested.( **+ ) 5 6;;

let open_local_parenthesized_oracle_ok =
  if parenthesized_open_operator = 34 && parenthesized_dotted_operator = 506
  then 1
  else failwith "parenthesized local-open name resolution differs";;
