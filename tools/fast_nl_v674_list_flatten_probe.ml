(* DEVELOPMENT / NON-RELEASE exact-runtime compatibility probe. *)
module List = struct
  include List
  let flatten xss = Cake.List.concat xss
end;;

candle_assert
  (List.flatten [[1;2];[];[3;4]] = [1;2;3;4] &&
   List.flatten [] = [] &&
   List.flatten [[];[]] = [])
  "fast_nl_v674_list_flatten";;

print_endline "CANDLE_FLYSPECK_V674_LIST_FLATTEN_PROBE_OK";;
