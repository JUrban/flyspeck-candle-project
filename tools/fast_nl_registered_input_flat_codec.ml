(* Canonical flat codec for prepared fast-NL cval data.  The format is a
   whitespace-separated prefix tree: N <decimal> for Cexp_num and P for
   Cexp_pair.  One independent term is stored per line. *)

module Candle_fast_nl_registered_input_flat_codec = struct

type candle_flat_write_task =
  | Candle_flat_term of term
  | Candle_flat_text of string;;

let rec candle_flat_write_tasks channel tasks =
  match tasks with
  | [] -> ()
  | Candle_flat_text text :: remaining ->
      Stdlib.output_string channel text;
      candle_flat_write_tasks channel remaining
  | Candle_flat_term term :: remaining ->
      let operator,arguments = strip_comb term in
      let name,_ = dest_const operator in
      (match name,arguments with
       | "Cexp_num",[numeral] ->
           Stdlib.output_string channel
             ("N " ^ Num.string_of_num (dest_numeral numeral) ^ " ");
           candle_flat_write_tasks channel remaining
       | "Cexp_pair",[left;right] ->
           Stdlib.output_string channel "P ";
           candle_flat_write_tasks channel
             (Candle_flat_term left :: Candle_flat_term right :: remaining)
       | _ -> failwith "fast NL flat codec: unsupported term");;

let candle_flat_write_term channel term =
  candle_flat_write_tasks channel
    [Candle_flat_term term;Candle_flat_text "\n"];;

let candle_flat_fields line =
  let limit = String.length line in
  let space character =
    character = ' ' || character = '\t' ||
    character = '\r' || character = '\n' in
  let rec skip position =
    if position < limit && space (String.get line position) then
      skip (position + 1)
    else position in
  let rec finish position =
    if position < limit && not (space (String.get line position)) then
      finish (position + 1)
    else position in
  let rec fields position result =
    let first = skip position in
    if first >= limit then rev result else
    let last = finish first in
    fields last (String.sub line first (last - first) :: result) in
  fields 0 [];;

let rec candle_flat_decode_tokens tokens =
  match tokens with
  | "N" :: numeral :: remaining ->
      mk_comb
        (`Cexp_num`,mk_numeral (Num.num_of_string numeral)),remaining
  | "P" :: remaining ->
      let left,after_left = candle_flat_decode_tokens remaining in
      let right,after_right = candle_flat_decode_tokens after_left in
      list_mk_comb (`Cexp_pair`,[left;right]),after_right
  | _ -> failwith "fast NL flat codec: malformed prefix data";;

let candle_flat_decode_line line =
  let term,remaining = candle_flat_decode_tokens (candle_flat_fields line) in
  if remaining <> [] then
    failwith "fast NL flat codec: trailing prefix data"
  else term;;

let candle_flat_write_terms path terms =
  let channel = Stdlib.open_out path in
  let rec write count remaining =
    match remaining with
    | [] -> Stdlib.close_out channel; count
    | term :: tail ->
        candle_flat_write_term channel term;
        write (count + 1) tail in
  write 0 terms;;

let candle_flat_read_terms path =
  let channel = Stdlib.open_in path in
  let rec read result =
    try
      let term = candle_flat_decode_line (Stdlib.input_line channel) in
      read (term :: result)
    with End_of_file ->
      Stdlib.close_in channel;
      rev result in
  read [];;

let candle_flat_cval_view encoded =
  let operator,arguments = strip_comb encoded in
  let name,_ = dest_const operator in
  match name,arguments with
  | "Cexp_num",[zero] when dest_numeral zero =/ Num.num_of_int 0 -> None
  | "Cexp_pair",[head;tail] -> Some (head,tail)
  | _ -> failwith "fast NL flat codec: malformed cval list";;

let rec candle_flat_cval_elements encoded result =
  match candle_flat_cval_view encoded with
  | None -> rev result
  | Some (head,tail) -> candle_flat_cval_elements tail (head :: result);;

let candle_flat_cval_list terms =
  itlist
    (fun term result -> list_mk_comb (`Cexp_pair`,[term;result]))
    terms `Cexp_num 0`;;

end;;
