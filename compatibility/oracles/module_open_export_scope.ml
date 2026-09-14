module Module_open_source = struct
  let x = 7;;
end;;

module Module_open_consumer = struct
  open Module_open_source;;
  let y = x;;
end;;

let module_open_visible_oracle = Module_open_consumer.y;;

(* This lookup must fail: [open] affects the following declarations but does
   not add the imported names to the enclosing module's exports. *)
let module_open_export_leak_probe = Module_open_consumer.x;;
