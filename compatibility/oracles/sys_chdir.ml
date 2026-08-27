(* Pinned OCaml reference: changing to the current directory succeeds and
   preserves the observable working directory.  The selected Candle route
   deliberately keeps this capability fail-closed. *)
let before = Sys.getcwd ();;
Sys.chdir ".";;
if Sys.getcwd () <> before then failwith "Sys.chdir current-directory drift";;
print_endline "SYS_CHDIR_REFERENCE_OK";;
