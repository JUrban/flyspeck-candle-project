module Module_include_source = struct
  let x = 7;;
end;;

module Module_include_consumer = struct
  include Module_include_source;;
  let y = x;;
end;;

let module_include_x_oracle = Module_include_consumer.x;;
let module_include_y_oracle = Module_include_consumer.y;;
