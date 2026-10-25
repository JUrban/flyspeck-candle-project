(* Generated DEVELOPMENT / NON-RELEASE runtime compatibility block.
   Its exact body is authenticated by flyspeck_nonlinear_verifier_smoke.py;
   it must move into a freshly linked runtime before release use. *)
let candle_assert condition logical_source =
  if condition then ()
  else raise (Assert_failure (logical_source,0,0));;

let infinity = Cake.Double.posinf64;;
let neg_infinity = Cake.Double.neginf64;;
let nan =
  Cake.Double.construct (Cake.Word64.fromInt 0)
    (Cake.Word64.fromInt 2047) (Cake.Word64.fromInt 1);;

let float_ieee_equal left right =
  let left_exponent = Cake.Word64.toInt (Cake.Double.exponent left) and
      right_exponent = Cake.Word64.toInt (Cake.Double.exponent right) and
      left_significand = Cake.Word64.toInt (Cake.Double.significand left) and
      right_significand = Cake.Word64.toInt (Cake.Double.significand right) in
  let left_nan = left_exponent = 2047 && not (left_significand = 0) and
      right_nan = right_exponent = 2047 && not (right_significand = 0) in
  if left_nan || right_nan then false
  else if left_exponent = 0 && left_significand = 0 &&
          right_exponent = 0 && right_significand = 0 then true
  else
    Cake.Double.sign left = Cake.Double.sign right &&
    left_exponent = right_exponent &&
    left_significand = right_significand;;

let float_ieee_lt left right = Cake.Double.(<) left right;;
let float_ieee_le left right = Cake.Double.(<=) left right;;
let float_ieee_gt left right = Cake.Double.(>) left right;;
let float_ieee_ge left right = Cake.Double.(>=) left right;;

(* Standalone form used by authenticated late-state compatibility overlays. *)
let candle_binary64_abs (x:double) : double =
  Cake.Double.construct (Cake.Word64.fromInt 0)
    (Cake.Double.exponent x) (Cake.Double.significand x);;

let candle_array_to_list a =
  let rec collect index result =
    if index < 0 then result
    else collect (index - 1) (Cake.Array.sub a index :: result) in
  collect (Cake.Array.length a - 1) []
;;

let candle_ignore _ = ();;

let candle_std_formatter = Pretty_imp.empty ();;

module Big_int = struct
  type big_int = int

  let zero_big_int = 0

  let big_int_of_string s =
    match Cake.Int.fromString s with
    | None -> failwith "Big_int.big_int_of_string"
    | Some i -> i

  let big_int_of_int value = value

  let sign_big_int value =
    if value < 0 then ~-1 else if value > 0 then 1 else 0

  let abs_big_int value = abs value

  let add_big_int left right = left + right

  let succ_big_int value = value + 1

  let sub_big_int left right = left - right

  let pred_big_int value = value - 1

  let mult_big_int left right = left * right

  let mult_int_big_int left right = left * right

  let quomod_big_int dividend divisor =
    let quotient = dividend / divisor and remainder = dividend mod divisor in
    if remainder < 0 then quotient + 1, remainder - divisor
    else quotient, remainder

  let div_big_int dividend divisor =
    fst (quomod_big_int dividend divisor)

  let mod_big_int dividend divisor =
    snd (quomod_big_int dividend divisor)

  let power_int_positive_int base exponent =
    if exponent < 0 then failwith "Big_int.power_int_positive_int" else
    let rec power accumulator factor remaining =
      if remaining = 0 then accumulator
      else
        let square = factor * factor in
        if remaining mod 2 = 0 then
          power accumulator square (remaining / 2)
        else
          power (accumulator * factor) square (remaining / 2) in
    power 1 base exponent

  let eq_big_int left right = left = right

  let le_big_int left right = left <= right

  let lt_big_int left right = left < right

  (* [Big_int.sqrt_big_int] is floor square root on nonnegative arbitrary
     precision integers.  CakeML integers are already arbitrary precision, so
     Newton descent gives the same exact result without a representation
     conversion or floating-point approximation. *)
  let sqrt_big_int value =
    if value < 0 then failwith "Big_int.sqrt_big_int"
    else if value < 2 then value
    else
      let rec descend estimate =
        let next = (estimate + value / estimate) / 2 in
        if next >= estimate then estimate else descend next in
      descend value
end;;

let num_of_big_int i = Int i
;;

let big_int_of_num n =
  match n with
  | Int i -> i
  | Rat r ->
      if Cake.Rat.denominator r = 1 then Cake.Rat.numerator r
      else failwith "big_int_of_ratio"
;;

let pred_num n =
  match n with
  | Int i -> Int (i - 1)
  | Rat r ->
      let result = Cake.Rat.(-) r (Cake.Rat.fromInt 1) in
      if Cake.Rat.denominator result = 1 then
        Int (Cake.Rat.numerator result)
      else Rat result
;;

let compare_num x y =
  let compare_rat left right =
    if Cake.Rat.(<) left right then -1
    else if Cake.Rat.(>) left right then 1
    else 0 in
  match x, y with
  | Int i, Int j -> if i < j then -1 else if i > j then 1 else 0
  | Int i, Rat r -> compare_rat (Cake.Rat.fromInt i) r
  | Rat r, Int j -> compare_rat r (Cake.Rat.fromInt j)
  | Rat i, Rat j -> compare_rat i j
;;

let approx_num_exp precision value =
  if precision <= 0 then failwith "approx_ratio_exp" else
  let numerator,denominator =
    match value with
    | Int i -> i,1
    | Rat r -> Cake.Rat.numerator r,Cake.Rat.denominator r in
  let negative = numerator < 0 in
  let numerator = abs numerator in
  let rec power accumulator factor exponent =
    if exponent = 0 then accumulator
    else
      let square = factor * factor in
      if exponent mod 2 = 0 then
        power accumulator square (exponent / 2)
      else
        power (accumulator * factor) square (exponent / 2) in
  let power10 exponent = power 1 10 exponent in
  let rec zeroes count result =
    if count <= 0 then result else zeroes (count - 1) ("0" ^ result) in
  let sign = if negative then "-" else "+" in
  if numerator = 0 then sign ^ "0." ^ zeroes precision "" ^ "e0"
  else
    let numerator_digits = Cake.String.size (string_of_int numerator) and
        denominator_digits = Cake.String.size (string_of_int denominator) in
    let candidate = numerator_digits - denominator_digits in
    let below_candidate_power =
      if candidate >= 0 then
        numerator < denominator * power10 candidate
      else
        numerator * power10 (~-candidate) < denominator in
    let exponent = if below_candidate_power then candidate else candidate + 1 in
    let shift = precision - exponent in
    let scaled_numerator,scaled_denominator =
      if shift >= 0 then numerator * power10 shift,denominator
      else numerator,denominator * power10 (~-shift) in
    let quotient = scaled_numerator / scaled_denominator and
        remainder = scaled_numerator mod scaled_denominator in
    let rounded =
      if 2 * remainder >= scaled_denominator then quotient + 1
      else quotient in
    let unit = power10 precision in
    let integer_part = rounded / unit and fraction = rounded mod unit in
    let fraction_string = string_of_int fraction in
    let fraction_string =
      zeroes (precision - Cake.String.size fraction_string) fraction_string in
    sign ^ string_of_int integer_part ^ "." ^ fraction_string ^
      "e" ^ string_of_int exponent
;;

let sign_num = Num.sign_num;;
