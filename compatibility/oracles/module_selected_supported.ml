module type Module_selected_sig = sig
  val value : int
end;;

module Module_selected_source = struct
  let value = 17
end;;

module Module_selected_alias = Module_selected_source;;

module Module_selected_constrained : Module_selected_sig = struct
  let value = 23
end;;

module Module_selected_inline : sig
  val value : int
end = struct
  let value = 29
end;;

module Module_selected_include = struct
  include Module_selected_alias
  let included_value = value + 1
end;;

include Module_selected_constrained;;

let module_selected_supported_oracle_ok =
  if Module_selected_alias.value = 17 &&
     Module_selected_constrained.value = 23 &&
     Module_selected_inline.value = 29 &&
     Module_selected_include.included_value = 18 &&
     value = 23
  then 1
  else failwith "selected module declaration behavior differs";;
