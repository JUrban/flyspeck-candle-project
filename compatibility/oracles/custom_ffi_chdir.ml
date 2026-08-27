(* Minimal Candle-front-end ABI reproducer. Run only in an isolated cwd. *)
let path = "../.." in
let len = String.size path in
let bytes = Word8_array.array (len + 1) (Word8.fromInt 0) in
let _ = Word8_array.copyVec path 0 len bytes 0 in
let _ = Runtime.customFFI "chdir" bytes in
if Word8.toInt (Word8_array.sub bytes 0) = 0 then ()
else failwith "customFFI chdir failed";;
