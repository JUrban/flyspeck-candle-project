(* DEVELOPMENT / NON-RELEASE tiny namespace and trusted-compute discriminator. *)

let candle_v679m_surface_compute equations tm =
  let theorem = Kernel.compute (COMPUTE_INIT_THMS,equations) tm in
  if hyp theorem <> [] then
    failwith "v679m surface theorem has assumptions";
  theorem;;

let candle_v679m_surface_theorem =
  candle_v679m_surface_compute [] `Cexp_num 1`;;

if hyp candle_v679m_surface_theorem <> [] ||
   not
     (aconv (lhand (concl candle_v679m_surface_theorem)) `Cexp_num 1`) ||
   not
     (aconv (rand (concl candle_v679m_surface_theorem)) `Cexp_num 1`) then
  failwith "v679m Kernel.compute surface validation"
else
  print_endline
    "CANDLE_FLYSPECK_V679M_KERNEL_COMPUTE_SURFACE_OK DEVELOPMENT_NON_RELEASE result=1 assumptions=0";;
