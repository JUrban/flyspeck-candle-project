(* Minimal Candle-front-end reproducer for the Sys.command -> customFFI path.
   The shell command has no filesystem effect. *)
#use "hol_loader.ml";;
loads "candle/build/insulate.ml";;
loads "candle/nums.ml";;
loads "candle/pretty.ml";;
loads "candle/ocaml.ml";;
if Sys.command "exit 7" = 7 then
  print_endline "custom-ffi-system-oracle: ok"
else
  failwith "Sys.command returned the wrong exit status";;
