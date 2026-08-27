(* OCaml 4.14 reference oracle for the failure edges used by pinned Flyspeck
   strictbuild.hl.  This does not execute HOL Light; it checks Toploop.use_file
   and an exact minimized transcription of strictbuild's control flow. *)

#directory "+compiler-libs";;
#load "ocamlcommon.cma";;
#load "ocamlbytecomp.cma";;
#load "ocamltoplevel.cma";;

Toploop.initialize_toplevel_env ();;

let fail label expected actual =
  failwith
    (Printf.sprintf "%s: expected %s, got %s" label expected actual);;

let expect label expected actual =
  if expected <> actual then fail label expected actual;;

let expect_list label expected actual =
  if expected <> actual then
    fail label ("[" ^ String.concat ";" expected ^ "]")
      ("[" ^ String.concat ";" actual ^ "]");;

let with_temp_source contents f =
  let path = Filename.temp_file "flyspeck-needs-oracle" ".ml" in
  let channel = open_out_bin path in
  output_string channel contents;
  close_out channel;
  try
    let result = f path in
    Sys.remove path;
    result
  with exn ->
    Sys.remove path;
    raise exn;;

let show_exception exn =
  match exn with
  | Failure message -> "Failure:" ^ message
  | Invalid_argument message -> "Invalid_argument:" ^ message
  | Sys_error message -> "Sys_error:" ^ message
  | exn -> Printexc.to_string exn;;

let read_lines path =
  let channel = open_in path in
  let rec loop acc =
    try loop (input_line channel :: acc)
    with End_of_file -> close_in channel; List.rev acc in
  loop [];;

let note_source path note =
  Printf.sprintf
    "let c = open_out_gen [Open_append;Open_text] 0o600 %S in output_string c %S; close_out c;;\n"
    path (note ^ "\n");;

let observe_use_file label source_for =
  let event_path = Filename.temp_file "flyspeck-needs-events" ".txt" in
  let source = source_for event_path in
  let outcome =
    try
      with_temp_source source (fun path ->
        try
          if Toploop.use_file Format.std_formatter path
          then "return:true"
          else "return:false"
        with exn -> "raise:" ^ show_exception exn)
    with exn -> Sys.remove event_path; raise exn in
  let effects = read_lines event_path in
  Sys.remove event_path;
  Printf.printf "use_file %-9s outcome=%s effects=[%s]\n%!"
    label outcome (String.concat ";" effects);
  outcome, effects;;

let () =
  let outcome, effects = observe_use_file "success"
      (fun path -> note_source path "success-1" ^ note_source path "success-2") in
  expect "success outcome" "return:true" outcome;
  expect_list "success effects" ["success-1"; "success-2"] effects;

  let outcome, effects = observe_use_file "syntax"
      (fun path -> note_source path "syntax-before" ^
        "let = ;;\n" ^ note_source path "syntax-after") in
  expect "syntax outcome" "return:false" outcome;
  expect_list "syntax effects" [] effects;

  let outcome, effects = observe_use_file "type"
      (fun path -> note_source path "type-before" ^
        "1 + true;;\n" ^ note_source path "type-after") in
  expect "type outcome" "return:false" outcome;
  expect_list "type effects" ["type-before"] effects;

  let outcome, effects = observe_use_file "runtime"
      (fun path -> note_source path "runtime-before" ^
        "failwith \"fixture-runtime\";;\n" ^ note_source path "runtime-after") in
  expect "runtime outcome" "return:false" outcome;
  expect_list "runtime effects" ["runtime-before"] effects;

  let outcome, effects = observe_use_file "runtime-sys"
      (fun path -> note_source path "runtime-sys-before" ^
        "raise (Sys_error \"fixture-runtime-sys\");;\n" ^
        note_source path "runtime-sys-after") in
  expect "runtime Sys_error outcome" "return:false" outcome;
  expect_list "runtime Sys_error effects" ["runtime-sys-before"] effects;;

let use_file_b_min path =
  if not (Sys.file_exists path) then false
  else Toploop.use_file Format.std_formatter path || false;;

let observe_use_file_b label path =
  let outcome =
    try if use_file_b_min path then "return:true" else "return:false"
    with exn -> "raise:" ^ show_exception exn in
  Printf.printf "use_file_b %-7s outcome=%s\n%!" label outcome;
  outcome;;

let () =
  let missing = Filename.temp_file "flyspeck-needs-missing" ".ml" in
  Sys.remove missing;
  expect "use_file_b missing" "return:false"
    (observe_use_file_b "missing" missing);
  let directory = observe_use_file_b "directory" "/" in
  if String.length directory < 16 || String.sub directory 0 15 <> "raise:Sys_error" then
    fail "use_file_b directory" "raise:Sys_error..." directory;;

type snapshot = {
  outcome : string;
  host : string;
  depend : (string * string) list;
  ftable : string list;
  events : string list;
};;

let show_snapshot snapshot =
  Printf.sprintf
    "outcome=%s host=%s depend=[%s] ftable=[%s] events=[%s]"
    snapshot.outcome snapshot.host
    (String.concat ";" (List.map (fun (a,b) -> a ^ "->" ^ b) snapshot.depend))
    (String.concat ";" snapshot.ftable)
    (String.concat ";" snapshot.events);;

let run_control_flow needb neutralize =
  let host = ref "host-0" in
  let depend = ref [] in
  let ftable = ref [] in
  let events = ref [] in
  let note event = events := !events @ [event] in
  let outcome =
    try
      let id = "target" in
      depend := (!host,id) :: !depend;
      note "depend-add";
      let h = !host in
      host := id;
      note "host-set";
      let b = needb note in
      host := h;
      note "host-restore";
      (try
         neutralize note
       with Failure message -> note ("neutralize-Failure-caught:" ^ message));
      if b then begin
        ftable := "target" :: !ftable;
        note "success";
        "return:unit"
      end else begin
        depend := List.filter (fun edge -> edge <> (h,id)) !depend;
        note "depend-remove";
        raise (Failure "Aborting Flyspeck Needs target")
      end
    with exn -> "raise:" ^ show_exception exn in
  { outcome; host = !host; depend = !depend; ftable = !ftable;
    events = !events };;

let check_case label expected needb neutralize =
  let actual = run_control_flow needb neutralize in
  Printf.printf "flow     %-22s %s\n%!" label (show_snapshot actual);
  if expected <> actual then
    fail label (show_snapshot expected) (show_snapshot actual);;

let snap outcome host depend ftable events =
  { outcome; host; depend; ftable; events };;

let needb_false note = note "needb:false"; false;;
let needb_true note = note "needb:true"; true;;
let needb_raise_failure note =
  note "needb:raise-Failure"; raise (Failure "needb");;
let needb_raise_sys note =
  note "needb:raise-Sys_error"; raise (Sys_error "needb");;
let neutral_ok note = note "neutralize:ok";;
let neutral_failure note =
  note "neutralize:raise-Failure"; raise (Failure "neutral");;
let neutral_invalid note =
  note "neutralize:raise-Invalid_argument";
  raise (Invalid_argument "neutral");;

let () =
  check_case "false/neutral-ok"
    (snap "raise:Failure:Aborting Flyspeck Needs target" "host-0" [] []
       ["depend-add"; "host-set"; "needb:false"; "host-restore";
        "neutralize:ok"; "depend-remove"])
    needb_false neutral_ok;
  check_case "false/neutral-Failure"
    (snap "raise:Failure:Aborting Flyspeck Needs target" "host-0" [] []
       ["depend-add"; "host-set"; "needb:false"; "host-restore";
        "neutralize:raise-Failure"; "neutralize-Failure-caught:neutral";
        "depend-remove"])
    needb_false neutral_failure;
  check_case "false/neutral-nonFailure"
    (snap "raise:Invalid_argument:neutral" "host-0"
       [("host-0","target")] []
       ["depend-add"; "host-set"; "needb:false"; "host-restore";
        "neutralize:raise-Invalid_argument"])
    needb_false neutral_invalid;
  check_case "needb-Failure"
    (snap "raise:Failure:needb" "target" [("host-0","target")] []
       ["depend-add"; "host-set"; "needb:raise-Failure"])
    needb_raise_failure neutral_ok;
  check_case "needb-Sys_error"
    (snap "raise:Sys_error:needb" "target" [("host-0","target")] []
       ["depend-add"; "host-set"; "needb:raise-Sys_error"])
    needb_raise_sys neutral_ok;
  check_case "true/neutral-Failure"
    (snap "return:unit" "host-0" [("host-0","target")] ["target"]
       ["depend-add"; "host-set"; "needb:true"; "host-restore";
        "neutralize:raise-Failure"; "neutralize-Failure-caught:neutral";
        "success"])
    needb_true neutral_failure;
  check_case "true/neutral-nonFailure"
    (snap "raise:Invalid_argument:neutral" "host-0"
       [("host-0","target")] []
       ["depend-add"; "host-set"; "needb:true"; "host-restore";
        "neutralize:raise-Invalid_argument"])
    needb_true neutral_invalid;
  print_endline "flyspeck_needs failure oracle: ok";;
