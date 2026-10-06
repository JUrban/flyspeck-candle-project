# AFP Flyspeck-Tame 2014 source pin

This directory preserves the exact Archive of Formal Proofs release selected
as the historical specification for Candle's reflected tame-graph work.

- entry: `Flyspeck I: Tame Graphs`, Gertrud Bauer and Tobias Nipkow;
- release: Isabelle2014, 2014-08-28;
- upstream entry: <https://isa-afp.org/entries/Flyspeck-Tame.html>;
- release archive:
  <https://isa-afp.org/release/afp-Flyspeck-Tame-2014-08-28.tar.gz>;
- license declared by the AFP entry: BSD License; and
- archive SHA-256:
  `54aa014cc8de1bc178ef68cc4e88932aefe9a61dcd17712ae714f39ae411102c`.

The release tarball does not contain a separate license file. The license
field in `inventory.json` therefore records the AFP entry's declaration and
does not claim that a license text was embedded in the archive.

Regenerate or verify the inventory against the current direct Flyspeck source
worktree with:

```sh
python3 scripts/audit-tame-graph-afp.py \
  --archive third_party/afp-flyspeck-tame-2014-08-28/afp-Flyspeck-Tame-2014-08-28.tar.gz \
  --flyspeck-root ../worktrees/flyspeck-direct-tail-v403 \
  --check third_party/afp-flyspeck-tame-2014-08-28/inventory.json
```

The verifier authenticates the tarball before reading it, rejects unsafe,
duplicate, or non-regular members, inventories all 44 files and all 35
Isabelle theories, and compares the overlapping theories and four archive
files byte-for-byte. It records declaration occurrences for reconciliation;
those lexical records are not correspondence proofs.

For an inspection-only extraction, first run the check above and then use:

```sh
mkdir -p /tmp/afp-Flyspeck-Tame-2014-08-28
tar -xzf third_party/afp-flyspeck-tame-2014-08-28/afp-Flyspeck-Tame-2014-08-28.tar.gz \
  -C /tmp/afp-Flyspeck-Tame-2014-08-28
```

This source pin is not part of Candle's logical trust boundary. A source file,
hash, archive count, or successful historical Isabelle computation cannot
replace the required HOL definition correspondence and general checker-
soundness theorems.
