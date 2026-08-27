module Module_functor_order = struct
  type t = string
  let compare = String.compare
end;;

module Module_functor_set = Set.Make(Module_functor_order);;

let module_functor_application_ocaml_ok =
  let values = Module_functor_set.add "b"
    (Module_functor_set.add "a" Module_functor_set.empty) in
  if Module_functor_set.mem "a" values &&
     not (Module_functor_set.mem "c" values)
  then 1
  else failwith "Set.Make oracle differs";;
