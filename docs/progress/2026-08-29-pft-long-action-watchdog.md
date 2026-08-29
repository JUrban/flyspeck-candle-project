# PFT long-action watchdog repair

Date: 2026-08-29 UTC

## Finding

The full Flyspeck PFT oracle lane reached its safe exporter boundary 170 at
trace offset 22,218,151,427 on 2026-08-28.  The next source action opens
`text_formalization/tame/good_list_archive.hl`.  Generation 0029 then used its
entire fixed 24-hour timeout without reaching boundary 180, and generation
0030 restored the same boundary at 2026-08-29 01:37 UTC.

At the audit checkpoint, generation 0030 had run for another 16 hours.  The
producer was not hung: it retained 99.9% CPU, 23,925,408 KiB RSS, no tracked
swap, a healthy one-peer DMTCP coordinator, and continued appending exact
65,536-byte trace bursts.  The durable status correctly remained at boundary
170 because the current source action had not completed.  The prior
generation's expiration therefore discarded 24 hours of useful work, and the
same fixed watchdog would have discarded the second attempt near 2026-08-30
01:37 UTC.

The original Bash supervisor was already gone.  GNU `timeout` PID 1122093,
the DMTCP producer PID 1122095, and coordinator PID 1122097 were all orphaned
to PID 1 except that the producer still had `timeout` as its immediate parent.
Consequently, timeout expiration could neither execute the supervisor's
recovery loop nor launch generation 0031.

## Independent audit and controlled live repair

An independent read-only audit rejected stopping the timeout wrapper.  A
stopped wrapper retains its alarm and can forward a pending TERM after any
later continuation.  The audit instead recommended an exact PID-only KILL of
the wrapper: KILL cannot be caught or forwarded, while the producer remains
alive after reparenting.  Signals to the producer, coordinator, or process
group were explicitly forbidden.

Two isolated dummy-process tests established both boundaries before the live
repair: stopping only a timeout parent leaves its command running past the
deadline but retains a pending alarm, while killing only the timeout parent
reparents the unchanged command to PID 1 and destroys the old timer.  No
`PR_SET_PDEATHSIG` dependency was found in the installed DMTCP restart path.

Immediately before intervention, a pidfd was opened for PID 1122093 and all of
the following identities were revalidated:

- timeout start ticks 308340664, executable `/usr/bin/timeout`, PPID 1, and
  exact `timeout 86400 dmtcp_restart ... generation-0030` command line;
- producer start ticks 308340665, executable
  `/usr/local/bin/mtcp_restart`, PPID 1122093, PGID 1122093, and sole matching
  `DMTCP:ocaml-hol` process;
- coordinator start ticks 308340667, port 45831, one peer, and running state;
- producer fd 5 bound to trace inode 72823313 and fd 6 bound to the exact
  `good_list_archive.hl` inode;
- durable status `resumed 170`, the finalized 24,500,183,040-byte safe
  checkpoint, and absence of `.dmtcp.temp` files.

`SIGKILL` was then sent only through the validated timeout pidfd.  PID 1122093
disappeared; producer PID 1122095 retained the same start ticks, PGID, open
files, running state, and was reparented to PID 1.  The coordinator retained
the same identity and healthy port.  No proof or coordinator process received
a signal.

The old sampler correctly exited because its monitored wrapper disappeared.
A replacement sampler now binds producer PID 1122095 directly; its PID is
recorded in `resource-sampler-orphan-0030.pid` and `resource-sampler.pid`, with
log `logs/resource-sampler-orphan-0030.log`.  After repair, the trace advanced
from 22,301,838,470 through 22,301,904,006 to 22,301,969,542 bytes in two
separate exact bursts while the producer remained at 99.9% CPU.  This closes
the immediate liveness check without claiming a new safe trace boundary.

## Future supervisor policy

Project commit `504fa8d6c89069d7896b0c95f192ab0c7678b33d` replaces the fixed
24-hour DMTCP generation limit with a finite, configurable 72-hour default.
`CANDLE_PFT_GENERATION_TIMEOUT_SECONDS` accepts another positive integer when
operationally justified.  The value is not a logical input and does not alter
PFT bytes or evidence status.  Bash syntax and two structural watchdog
regressions pass; the old one-day DMTCP launch/restart forms are absent.

When the live producer next exits, a new boundary will be accepted only after
the finalized checkpoint, restart script, status, stable size/mtime, and lack
of temporary images are all verified.  The old safe checkpoint is retained
until then.  If no valid new checkpoint exists, the speculative trace tail
must be discarded only after producer death and generation 0031 restarted
from boundary 170 under the repaired supervisor.

This work preserves only the independent P1/reference oracle lane.  It cannot
satisfy direct-source S2 or S3 and does not change the primary runtime/link and
direct-execution critical path.
