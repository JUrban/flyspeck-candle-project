# Live PFT final-certificate diagnosis — 2026-08-31

## Outcome

The long-running PFT oracle is healthy by all observable resource and stream
signals, but `19715 / 19715` is not a completion marker and the process is not
merely flushing a completed traversal.  In pinned `good_list_archive.hl`, the
counter is printed before `eval_good_list0`.  The live process has therefore
started the final certificate and is still constructing and synchronously
streaming that proof (or assembling the concluding `all_conv_univ` result).
The decisive theorem-level marker is the still-absent `Done` line.

This oracle remains subordinate diagnostic evidence.  It cannot replace the
direct CakeML/Candle S2/S3 path.

## Live evidence

At approximately 03:53 UTC, PID `1122095` was in runnable state at 99.9% CPU.
Its accumulated CPU time was essentially its 50.3-hour live elapsed time.
RSS was `40658932` KiB, peak RSS `41706252` KiB, and process swap was zero.
The output descriptor remained open and its position advanced with
`/project/flyspeck-candle-runs/full-l2-direct-truncate.pft.bin`, then
`36462199740` bytes.

Across the preceding two hours, 717 of 718 ten-second samples grew; the
longest observed no-growth interval was ten seconds and RSS was stable.  From
23:29:07 to 03:53:16 the stream grew by `956097468` bytes in 15,849 seconds,
about 60.3 KB/s or 207 MiB/hour on average.  Recent 15-minute, one-hour and
two-hour rates were about 160, 164 and 171 MiB/hour respectively.  The stream
has the expected `PFT\0`, `0.1.0`, `candle` header and no terminal footer while
it remains open.

The live source/configuration identities are:

- producer `1ea3b9a8c614ffee4116789e23a6dcaa03bdc0b9`;
- Flyspeck `2ea440e9f7c55734d1e47738e44a6129ce0ecf5a`;
- Candle `177a9c1e759355a325842650d224b56a3d4437dd`;
- producer `pft.ml` SHA-256
  `5df5b361702e3d5ff080481529ac9ca28150184056dfc418f0972c07becb8ea4`.

The exporter and `good_list_archive.hl` descriptors still match the configured
Flyspeck commit blobs.  The most recent logical checkpoint is after build item
170 at PFT offset `22218151427`; its `24500183040`-byte DMTCP image dates from
August 28 and the current generation resumed August 29.

## Remaining work and forecast

`good_list_archive.hl` is build item 171 of 297.  Another 126 declared build
entries remain after it, followed by target loading and finalization.  Even
the eventual `Done: |- ALL good_list tame_archive_list` marker will therefore
not mean the full export is complete.

Neither the source nor the run metadata provides a remaining command or byte
count for the final certificate.  At the recent stream rate, each additional
GiB would take roughly 6.2--6.4 hours.  “Hours, possibly more than a day” is a
reasonable qualitative range for this theorem, not a statistical ETA.  The
whole export cannot yet be bounded honestly and may still take days because
the remaining 126 entries have highly unequal proof costs.

More CPUs cannot accelerate this one ordered HOL Light computation, more RAM
is unnecessary at the observed stable working set, and storage is not the
bottleneck (about 5.38 TB was free).  The external advice about parallel
`Holmake`, CakeML caches and frontend gates does not apply to this live serial
PFT stream.

## Monitoring and future optimization

Continue the existing ten-second resource sampler.  At 10--30 minute
intervals, compare CPU ticks, output descriptor position/file size, RSS/swap
and log modification time.  Watch for `Done`, the next build-file log,
`status.tsv` advancement and final `CANDLE_RESTARTABLE_BUILD_OK`.  A write
pause with CPU still advancing may be legitimate proof work or GC; investigate
only if both CPU and output stop advancing for 30--60 minutes.  Do not checksum
or parse the complete growing file, checkpoint/restart it, or attach a debugger
to the live run.

For a future run, add a completion record after every certificate with elapsed
time, emitted bytes and command count, and design coordinated checkpoints
inside the 19,715-certificate loop.  The current checkpoint granularity leaves
roughly 50 hours and 14.2 GB of work exposed to a crash.  These improvements
cannot safely retrofit or speed the already-running process.
