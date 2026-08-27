module Module_functor_replacement = struct
  type elt = string
  type t = string list

  let empty = []

  let rec mem value = function
    [] -> false
  | head::tail -> value = head || mem value tail

  let add value values =
    if mem value values then values else value::values
end;;

let module_functor_replacement_oracle_ok =
  let values = Module_functor_replacement.add "b"
    (Module_functor_replacement.add "a"
      (Module_functor_replacement.add "a"
        Module_functor_replacement.empty)) in
  if Module_functor_replacement.mem "a" values &&
     Module_functor_replacement.mem "b" values &&
     not (Module_functor_replacement.mem "c" values)
  then 1
  else failwith "Set.Make replacement oracle differs";;
