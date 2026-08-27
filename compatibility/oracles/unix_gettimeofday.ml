let unix_gettimeofday_observation = Unix.gettimeofday ();;

let unix_gettimeofday_observation_is_zero =
  Float.compare unix_gettimeofday_observation Float.zero = 0;;

print_endline
  (if unix_gettimeofday_observation_is_zero then
     "UNIX_GETTIMEOFDAY_ZERO"
   else
     "UNIX_GETTIMEOFDAY_POSITIVE");;
