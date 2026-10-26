let candle_v679_loaded_source_ledger = rev !loaded_files;;

if !Cakeml.pendingLoadedSourceIds <> [] then
  failwith "v679 pending source identity before loader-ledger probe";;

print_endline
  ("CANDLE_FLYSPECK_V679_LOADED_SOURCE_LEDGER_BEGIN count=" ^
   string_of_int (List.length candle_v679_loaded_source_ledger));;

List.iter
  (fun (name,digest) ->
     print_endline
       ("CANDLE_FLYSPECK_V679_LOADED_SOURCE identity=" ^
        name ^ ":" ^ digest))
  candle_v679_loaded_source_ledger;;

print_endline "CANDLE_FLYSPECK_V679_LOADED_SOURCE_LEDGER_END";;
