# Effective load-path alias repair and independent rereview

Status: scoped PASS; full direct promotion remains blocked.

The first canonical-source alias implementation (`Candle f256d8b`, CakeML
`d63d36d45`) was rejected during independent review.  Its 37-record,
153-occurrence manifest contract modeled the generator's canonical root order,
not the effective runtime order after both stratum setup and `strictbuild.hl`
had prepended roots.  An independent traversal of all 1,013 selected root,
literal, and reviewed-dynamic occurrences found the actual closure to be 47
records and 172 occurrences.  Action 126 (`ssreflect.hl`) alone demonstrated
that the incomplete table would leave the selected lexical path unauthenticated.

Candle `f30bc27` repairs both findings:

- the manifest resolver emulates the exact setup plus strictbuild prepend
  transitions and retains the lexical `..` spellings seen by compiled Candle;
- the generated table is 47 records / 172 occurrences while all canonical
  source selections remain unchanged;
- setup checks the exact five-root post-strictbuild prefix before any cumulative
  Flyspeck action;
- the runtime independently derives the alias contract from build roots and
  source-graph dependencies and compares canonical JSON, so policy, target,
  root index, use provenance, missing fields, string counts, and boolean/integer
  type confusion fail as `ContractError`;
- snapshot relocation and generated configuration retain only relocated alias
  and canonical paths.

Independent rereview reconstructed the exact 47/172 contract byte-for-byte,
verified action 126 and ordinary jHOL/formal-inequalities aliases, exercised
hostile field and type mutations, and checked full-table relocation.  It found
no P0, P1, or P2 issue.  Verification was:

- Candle manifest tests 28/28;
- Candle runtime tests 36/36;
- full Candle Python discovery 227/227;
- exact CakeML alias fixtures 2/2 and nested identity-stack fixture 1/1;
- exact manifest regeneration PASS.

This closes only lexical alias selection and provenance.  The Candle manifest
still pins the older CakeML boot, and no rebuilt compiled runtime has exercised
the repaired alias table or the loader-owned physical source trace.  Therefore
this PASS does not authorize a direct launch or an S2/S3 claim.
