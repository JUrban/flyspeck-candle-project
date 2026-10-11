# Tame graph p=0 reference audit and bounded benchmark

Status: **DEVELOPMENT / NON-RELEASE**.

## Outcome

The old Isabelle reference job did finish. Its full session log survived even
though its compact wrapper log did not contain the enormous printed value. The
decoded traversal has 312,763 visited states, 501 final visits, 322,944
`next_tame0` children, 312,762 retained children, and maximum frontier 96.
AFP's historical total of 312,764 includes the counter's initial value one
(`ArchStat.thy:61-70`), so the two independent counts agree exactly.

The current reflected Candle result does **not** agree. A fresh run from Candle
commit `755eec9e39d143444bb57eb9d929b2df75ae734c` again terminates after 239
visits with an empty frontier and zero finals. At the same 239-visit boundary,
the fresh Isabelle run has 56 states still on its frontier. This is a semantic
differential failure, not a performance completion result.

No whole `p=0` rerun was started: the recovered run already cost nearly eight
hours, and it supplies enough evidence to refute the 239-state result. No AFP
invariant proof or architectural redesign was attempted.

## Authenticated sources and trust boundary

- `Generator.thy:102-112` defines `polysizes` and `next_tame0`;
  `Plane.thy:11-14` has `maxGon p = p + 3`. Thus `[3]` is the correct complete
  candidate-size range for `p=0`; the mismatch is not explained by omitting
  sizes 4 or 5.
- `TameEnum.thy:10-20` defines `is_tame`, `next_tame`, and `TameEnumP`.
- `Worklist.thy:27-43` fixes the depth-first successor-prepending order used by
  the audit.
- `ArchStat.thy:36-73` independently records 312,764 generated-counter states,
  501 final visits, and 9 isomorphism classes for `p=0`.
- `Archives/Tri.ML` has SHA-256
  `5041a68bb4f69e1121738eae010b02ad759327c791af8ff95544e3d2c9239cd0`
  and contains nine top-level graphs. `ArchComp.thy:37-38` states
  `same3: samet (tameEnumFilter 0) Tri` and proves it by Isabelle `eval`.

The Isabelle values and archive comparison are differential-oracle evidence;
they are not imported into Candle as theorem premises. Conversely, the fresh
Candle result is a theorem returned by its `Kernel.compute` path, but the
missing universal correspondence theorem means it currently proves a fact
about the reflected functions, not yet about AFP `next_tame`.

## Full recovered reference result

The completed run is
`/project/flyspeck-candle-runs/tame-reference-20261006T140228Z-dev-001`.
Its wrapper log SHA-256 is
`ab3c1e9d22188ed487311fe02e199dc4e5d0fb3a7bd0d30e1c6207e991fb242f`.
The surviving compressed session log is
`/home/mptp/.isabelle/Isabelle2014/heaps/polyml-5.5.2_x86_64-linux/log/Candle-Tame-Reference.gz`,
SHA-256
`038b8e7747b096bc4131a0b02aae6269599ec7388e9420c73ab92a6068bb27eb`.

| counter | full Isabelle `p=0` |
| --- | ---: |
| visited states | 312,763 |
| final visits | 501 |
| raw `next_plane` children | 869,959 |
| `next_tame0` children | 322,944 |
| retained `next_tame` children | 312,762 |
| early-pruned children | 547,015 |
| final-pruned children | 10,182 |
| maximum frontier | 96 |
| canonical `Tri` classes | 9 |

The aggregate run did not print the 501 final graph identities. Identity
evidence instead comes from the authenticated nine-entry `Tri.ML` and AFP
`same3`. A fresh identity-emitting full traversal would repeat the eight-hour
work and was outside this bounded packet. Candle's zero final results already
fail the necessary cardinality condition for matching those nine classes.

### Full-run timing

| phase | elapsed |
| --- | ---: |
| `p=0` evaluator | 28,587.332 s |
| bounded `p=2`, fuel 1000 evaluator | 49.527 s |
| all non-`value` theory commands | 1.803 s |
| complete theory | 28,638.690 s |
| wrapper total | 28,658 s |
| wrapper/build startup and handoff beyond command timings | about 19.3 s |

Peak RSS was not measured by the 2026-10-06 harness and cannot be recovered
after process exit. The failed predecessor consumed 272 seconds before a source
definition error. A second abandoned launch has no completion or exact elapsed
marker and is not assigned an invented duration.

## Fresh bounded Isabelle audit

The successful bounded run is
`/project/flyspeck-candle-runs/tame-bounded-audit-20261011T112034Z-dev-001`.
Its saved session log SHA-256 is
`aff5339a9a8e08e672d77ad6516c123502ee91f788e667177c090a5d8ae1cc9e`.
It was pinned to CPUs 0 and 1 and capped at 20 GiB virtual memory.

| prefix | visited | frontier | raw | stage 0 | retained | final pruned | max frontier |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `p=0`, 10 | 10 | 25 | 36 | 35 | 34 | 1 | 25 |
| `p=0`, 100 | 100 | 71 | 421 | 171 | 170 | 1 | 73 |
| `p=0`, 239 | 239 | 56 | 875 | 295 | 294 | 1 | 74 |
| `p=0`, 240 | 240 | 55 | 879 | 295 | 294 | 1 | 74 |
| `p=2`, 1000 | 1,000 | 766 | 33,902 | 1,772 | 1,765 | 7 | 813 |

The `p=2` result exactly repeats every counter and Boolean feature flag from
the old reference session. This is the requested representative bounded larger
partition signal.

| phase | elapsed |
| --- | ---: |
| four `p=0` prefix values | 2.774 s |
| `p=2`, fuel 1000 evaluator | 37.447 s |
| non-`value` theory commands | 1.883 s |
| complete theory | 42.139 s |
| build process | 57.96 s |
| wrapper total | 58 s |
| peak RSS | 1,818,916 KiB |

Two pre-evaluator harness repeats are retained. The first failed after 6.85 s
because the virtual-memory limit preceded an explicit Java heap cap. The second
was interrupted after a 5.33 s measured build command when CPU affinity was
added. Neither loaded the audit theory. The successful run capped Java at 1
GiB and pinned the complete Isabelle process tree to two CPUs.

## Fresh Candle reproduction and direct comparison

The fresh Candle run is
`/project/flyspeck-candle-runs/tame-candle-p0-audit-20261011T112335Z-dev-001`.
The transcript SHA-256 is
`d34e92dbb8dfc2db25153dcd2bf27ee6cb8a6dc3e85c88096c02816c5d3fea32`.
It ran from the clean isolated worktree
`/project/worktrees/candle-tame-reference-audit-v1` at commit `755eec9e`.

| counter at visit 239 | Isabelle | Candle |
| --- | ---: | ---: |
| frontier | 56 | 0 |
| `next_tame0` children | 295 | 239 |
| retained children | 294 | 238 |
| final-pruned children | 1 | 1 |
| maximum frontier | 74 | 30 |
| final visits | 0 | 0 |

Candle preparation took 138.195125 s, the 239-state evaluator plus output
took 0.099041 s, process handoff took 0.114367 s, and total elapsed was
138.408532 s. Peak child RSS was 1,093,120 KiB under the two-CPU/20-GiB cap.

The already checked exact first transition agrees with Isabelle, while the
committed Candle ledger's 10-node prefix has frontier 30 and the fresh Isabelle
10-node prefix has frontier 25. Therefore the divergence is after transition
one and no later than visit ten. This is a bound, not a diagnosis.

## Stop boundary

The next bounded task is a state-by-state identity comparison for visits 2
through 10, followed by a universal typed transition correspondence theorem.
Until that discrepancy is localized and fixed, the 239-state result must not
be described as the AFP `p=0` enumeration, and a reflected `p=2` performance
run would benchmark the wrong transition relation. This packet deliberately
stops there.

Machine-readable counters and artifact identities are in
`2026-10-11-tame-p0-reference-audit.json`. The reusable bounded oracle,
resource-capped launchers, and unary-log decoder live under
`tools/tame_reference_oracle/` and `scripts/`.
