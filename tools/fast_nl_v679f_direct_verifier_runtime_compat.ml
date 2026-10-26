(* DEVELOPMENT / NON-RELEASE restored-state reuse of two audited direct-state
   compatibility repairs.  This changes ML dispatch only; no theorem or
   logical constant is introduced. *)

module M_taylor = struct
include M_taylor;;

let get_dim tm =
  let _,type_arguments =
    Kernel.dest_type (Kernel.call_type_of tm) in
  let dimension_type =
    match type_arguments with
    | _ :: dimension :: _ -> dimension
    | _ -> failwith "get_dim" in
  let rec find_dimension index =
    if index > max_dim then failwith "get_dim"
    else if dimension_type = n_type_array.(index) then index
    else find_dimension (index + 1) in
  find_dimension 1;;

end;;

let _ =
  if M_taylor.get_dim `x:real^6` <> 6 then
    failwith "v679f direct verifier runtime dimension compatibility"
  else
    print_endline
      "CANDLE_V679F_DIRECT_VERIFIER_RUNTIME_COMPAT dimension=6";;
