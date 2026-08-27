# Full PFT validation: first boundary incident — 2026-08-27

## Preserved boundary

The uncompressed full validation run reached its first source boundary and
cleanly asked DMTCP to checkpoint and kill the producer.  The preserved state
is:

```text
phase             checkpoint
index             0
next source       Multivariate/flyspeck.ml
trace bytes       8,427,171,576
PFT commands      954,134,966
peak type slots   104,393
peak term slots   243,740
peak theorem slots 30,827,635
checkpoint bytes  22,013,091,840
trace SHA-256     32b4bb835331521c7b4de2ff548e2fa047612e6f81f47ae466a782212667ac15
checkpoint SHA-256 850130ee4dedd7b0a211a1b66244cdac31189d96d1623b3fc0ba12af47ffcf1f
```

`file` identifies the checkpoint as raw data rather than gzip, matching the
locked `checkpoint_gzip=0` configuration.  The producer log ends with
`Computation was checkpointed and killed.`  Candle, Flyspeck, and the producer
repositories still have the exact heads recorded in `run.conf`.

## Supervisor incident

The shell supervisor did not start generation 1.  It reported a syntax error
after the initial generation returned, even though the checked-out script
passes `bash -n`.  The initial process began before resource-reporting commits
modified the same script.  Bash may read a long-running script incrementally,
so replacing its source beneath the active process can splice incompatible
read buffers.

The supervisor now re-executes once from a complete in-memory copy.  A later
project commit can no longer change the program of an active supervisor.  The
saved trace and DMTCP image were not modified while this was diagnosed.

Generation 1 then restored the hashed image with a new coordinator and
published the exact status

```text
resumed  0  Multivariate/flyspeck.ml  8427171576  954134966  104393  243740  30827635
```

The trace subsequently grew beyond the boundary while the restored producer
held the same approximately 21 GiB resident set.  `/proc` confirms the active
supervisor has `CANDLE_PFT_SUPERVISOR_IN_MEMORY=1` and the pinned project
directory in its environment.  This establishes usable checkpoint recovery;
it does not yet establish completion of the full validation run.

## Cross-run byte comparison

An older gzip-checkpoint run used identical Candle, producer, Flyspeck, and
evidence-input heads.  Its trace first differs from this run at byte
863,680,444, and its source-0 boundary has different byte and command counts.
This is not source drift: the two producer logs follow the same proof progress
and differ only in CPU-time measurements.

The streaming producer documentation explicitly permits this representation
difference.  GC finalizers enqueue safe theorem-slot releases, so collection
timing can move `DEL_THEOREM` commands and subsequent slot reuse.  Streaming
PFT is logically deterministic but not necessarily byte deterministic.
Consequently raw trace SHA equality is not a promotion requirement.  Required
equivalence evidence is successful compiled replay under the same axiom
policy plus canonical fingerprints of every saved theorem, hypotheses, and
assumptions.  The direct S3 production path remains independent of both PFT
runs.

## Second live restart

The repaired run subsequently checkpointed again and generation 2 restored
that image.  The exact resumed status was:

```text
resumed  10  leg/AFF_SGN_TAC.hl  8640234160  976213989  103364  243740  30911288
```

The replacement uncompressed checkpoint is 22,073,835,520 bytes.  Generation
1 ended with `Computation was checkpointed and killed.`, and generation 2 is
actively producing proof output beyond the 8,640,234,160-byte boundary.  This
is a second successful full-scale restore and confirms that the direct
`Unix.ftruncate` repair is active beyond the initial source-0 smoke.  It is
still live PFT validation evidence only: completion, compiled replay, saved
theorem fingerprints, and the direct S3 run all remain open.

## Fourth live generation

Generations 2 and 3 also ended at real source boundaries with
`Computation was checkpointed and killed.`.  Generation 4 restored the newest
image and published:

```text
resumed  30  general/vukhacky_tactics.hl  9112182798  1029056448  103364  243740  30911288
```

At the observation point the trace had grown to 9,320,133,886 bytes and was
still changing.  The current uncompressed checkpoint is 22,077,128,704 bytes;
the resumed producer uses about 21 GiB RSS and one core.  This extends the
restart evidence through four generations and 30 full-build source entries.
It still carries no direct-source milestone: PFT remains an independent
oracle/validation lane under the amended v1.3 roadmap.
