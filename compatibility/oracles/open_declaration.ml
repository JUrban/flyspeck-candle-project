module Open_declaration_probe = struct
  let value = 7;;
end;;

open Open_declaration_probe;;

let open_declaration_oracle_ok = value = 7;;

if open_declaration_oracle_ok then
  print_string "OPEN_DECLARATION_ORACLE_OK\n"
else failwith "declaration-open oracle mismatch";;
