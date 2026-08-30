#!/usr/bin/python3
"""Tests for the read-only canonical bootstrap resource sampler."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/sample-canonical-bootstrap-resources.py"
SPEC = importlib.util.spec_from_file_location("canonical_resource_sampler", SOURCE)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


def stat_line(
    pid: int, comm: str, ppid: int, process_group: int, start_ticks: int,
    user_ticks: int = 0, system_ticks: int = 0,
) -> str:
    fields = [
        "R", str(ppid), str(process_group), "0", "0", "0", "0", "0", "0",
        "0", "0", str(user_ticks), str(system_ticks), "0", "0", "0", "0",
        "0", "0", str(start_ticks), "0", "0",
    ]
    return f"{pid} ({comm}) " + " ".join(fields) + "\n"


class FakeProc:
    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "meminfo").write_text(
            "MemAvailable:       209715200 kB\n", encoding="ascii",
        )
        (root / "vmstat").write_text(
            "pswpin 100\npswpout 200\n", encoding="ascii",
        )

    def process(
        self, pid: int, comm: str, ppid: int, process_group: int,
        start_ticks: int, rss_kib: int, user_ticks: int = 0,
    ) -> None:
        directory = self.root / str(pid)
        directory.mkdir()
        (directory / "stat").write_bytes(stat_line(
            pid, comm, ppid, process_group, start_ticks, user_ticks,
        ).encode("latin-1"))
        (directory / "status").write_bytes(
            f"Name:\t{comm}\nVmRSS:\t{rss_kib} kB\n".encode("latin-1")
        )


class ResourceSamplerTests(unittest.TestCase):
    def test_stat_parser_accepts_spaces_and_parentheses_in_comm(self) -> None:
        parsed = subject.parse_stat(
            stat_line(12, "odd ) command", 3, 4, 55, 6, 7), 12,
        )
        self.assertEqual(parsed, (3, 4, 55, 13))

    def test_scope_union_deduplicates_and_binds_anchor_identities(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeProc(root)
            fake.process(10, "controller", 1, 10, 100, 1000, 10)
            fake.process(11, "child", 10, 11, 101, 2000, 20)
            fake.process(20, "pft", 1, 20, 200, 3000, 30)
            fake.process(21, "coordinator", 1, 20, 201, 4000, 40)
            scopes = (
                subject.Scope("canonical", 10, 100, "tree", None, True),
                subject.Scope("pft", 20, 200, "group", 20, False),
            )
            sample, swap, cpu, _, tracking = subject.make_sample(
                0, scopes, root, None, {}, None,
                100 * subject.GIB_KIB, 120 * subject.GIB_KIB,
                32 * subject.GIB_KIB, 10.0, initial=True,
            )
            self.assertEqual(sample["member_pids"], [10, 11, 20, 21])
            self.assertEqual(sample["aggregate_rss_kib"], 10000)
            self.assertEqual(sample["scope_members"]["canonical"], [10, 11])
            self.assertEqual(sample["scope_members"]["pft"], [20, 21])
            self.assertEqual(sample["alerts"], [])
            self.assertEqual(swap, (100, 200))
            self.assertEqual(len(cpu), 4)
            self.assertEqual(set(tracking), {"canonical", "pft"})

            mismatched = (
                subject.Scope("canonical", 10, 999, "tree", None, True),
            )
            with self.assertRaisesRegex(subject.SampleError, "identity changed"):
                subject.make_sample(
                    0, mismatched, root, None, {}, None,
                    100, 120, 32, 10.0, initial=True,
                )

    def test_kernel_thread_without_vmrss_remains_in_topology(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeProc(root)
            fake.process(10, "controller", 1, 10, 100, 1000)
            child = root / "11"
            child.mkdir()
            (child / "stat").write_text(
                stat_line(11, "kernel child", 10, 10, 101), encoding="ascii",
            )
            (child / "status").write_text(
                "Name:\tkernel child\n", encoding="ascii",
            )
            snapshot = subject.process_snapshot(root)
            self.assertEqual(subject.tree_members(snapshot.processes, 10), {10, 11})
            self.assertEqual(snapshot.processes[11].rss_kib, 0)

    def test_group_anchor_exit_drains_members_before_closing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeProc(root)
            fake.process(10, "controller", 1, 10, 100, 1)
            fake.process(20, "pft", 1, 20, 200, 2)
            fake.process(21, "orphan", 1, 20, 201, 999999)
            scopes = (
                subject.Scope("canonical", 10, 100, "tree", None, True),
                subject.Scope("pft", 20, 200, "group", 20, False),
            )
            first, swap, cpu, monotonic, tracking = subject.make_sample(
                0, scopes, root, None, {}, None, 100000, 900000, 1, 10.0,
                initial=True,
            )
            self.assertEqual(first["scope_states"]["pft"], "live")
            for name in ("stat", "status"):
                (root / "20" / name).unlink()
            (root / "20").rmdir()
            # Both the reused anchor PID and a wholly new process now occupy
            # the old numeric group.  Neither identity was authenticated while
            # the original anchor was live.
            fake.process(20, "replacement", 1, 20, 999, 888888)
            fake.process(22, "new-group-member", 1, 20, 202, 777777)
            second, swap, cpu, monotonic, tracking = subject.make_sample(
                1, scopes, root, swap, cpu, monotonic, 100000, 900000, 1, 10.0,
                initial=False, scope_tracking=tracking,
            )
            self.assertEqual(second["scope_states"]["pft"], "draining")
            self.assertEqual(second["scope_members"]["pft"], [21])
            self.assertIn("aggregate-rss-ceiling", second["alerts"])
            self.assertNotIn(
                {"pid": 22, "start_ticks": 202},
                second["scope_tracked_identities"]["pft"],
            )
            for name in ("stat", "status"):
                (root / "21" / name).unlink()
            (root / "21").rmdir()
            third, *_ = subject.make_sample(
                2, scopes, root, swap, cpu, monotonic, 100000, 900000, 1, 10.0,
                initial=False, scope_tracking=tracking,
            )
            self.assertEqual(third["scope_states"]["pft"], "closed")

    def test_non_ascii_unrelated_comm_and_pid_reuse_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeProc(root)
            fake.process(10, "controller", 1, 10, 100, 1000)
            fake.process(99, "odd-ÿ-name", 1, 99, 999, 9999)
            self.assertEqual(
                set(subject.process_snapshot(root).processes), {10, 99},
            )

            original_reader = subject.read_proc_file
            target_calls = 0

            def recycled_reader(directory_fd: int, name: str) -> bytes:
                nonlocal target_calls
                value = original_reader(directory_fd, name)
                directory_name = Path(
                    os.readlink(f"/proc/self/fd/{directory_fd}")
                ).name
                if name == "stat" and directory_name == "10":
                    target_calls += 1
                    if target_calls == 2:
                        text = value.decode("latin-1").rstrip("\n")
                        prefix, separator, suffix = text.rpartition(") ")
                        fields = suffix.split()
                        fields[19] = str(int(fields[19]) + 1)
                        return (prefix + separator + " ".join(fields) + "\n").encode(
                            "latin-1",
                        )
                return value

            with mock.patch.object(subject, "read_proc_file",
                                   side_effect=recycled_reader):
                snapshot = subject.process_snapshot(root)
            self.assertNotIn(10, snapshot.processes)

    def test_unreadable_anchor_fails_closed_but_unrelated_pid_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeProc(root)
            fake.process(10, "controller", 1, 10, 100, 1000)
            fake.process(11, "child", 10, 10, 101, 2000)
            fake.process(99, "unrelated", 1, 99, 999, 9999)
            original_reader = subject.read_proc_file

            def deny_pid(denied_pid: int):
                def reader(directory_fd: int, name: str) -> bytes:
                    directory_name = Path(
                        os.readlink(f"/proc/self/fd/{directory_fd}")
                    ).name
                    if int(directory_name) == denied_pid:
                        raise PermissionError("synthetic permission churn")
                    return original_reader(directory_fd, name)
                return reader

            with mock.patch.object(
                subject, "read_proc_file", side_effect=deny_pid(99),
            ):
                snapshot = subject.process_snapshot(root)
            self.assertEqual(set(snapshot.processes), {10, 11})
            self.assertEqual(snapshot.unreadable_pids, frozenset({99}))

            scopes = (
                subject.Scope("canonical", 10, 100, "tree", None, True),
            )
            (_sample, swap, cpu, monotonic, tracking) = subject.make_sample(
                0, scopes, root, None, {}, None,
                10000, 12000, 32, 10.0, initial=True,
            )
            with mock.patch.object(
                subject, "read_proc_file", side_effect=deny_pid(11),
            ):
                with self.assertRaisesRegex(
                    subject.SampleError,
                    "tracked scope members are unreadable: canonical: \\[11\\]",
                ):
                    subject.make_sample(
                        1, scopes, root, swap, cpu, monotonic,
                        10000, 12000, 32, 10.0, initial=False,
                        scope_tracking=tracking,
                    )
            with mock.patch.object(
                subject, "read_proc_file", side_effect=deny_pid(10),
            ):
                with self.assertRaisesRegex(
                    subject.SampleError, "scope anchor is unreadable: canonical",
                ):
                    subject.make_sample(
                        0, scopes, root, None, {}, None,
                        100, 120, 32, 10.0, initial=True,
                    )

    def test_thresholds_and_paging_are_alerts_not_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeProc(root)
            fake.process(10, "controller", 1, 10, 100, 13000)
            (root / "meminfo").write_text(
                "MemAvailable:       0 kB\n", encoding="ascii",
            )
            (root / "vmstat").write_text(
                "pswpin 101\npswpout 202\n", encoding="ascii",
            )
            sample, *_ = subject.make_sample(
                1,
                (subject.Scope("canonical", 10, 100, "tree", None, True),),
                root, (100, 200), {(10, 100): 0}, subject.time.monotonic() - 1,
                10000, 12000, 32, 10.0, initial=False,
                scope_tracking={
                    "canonical": subject.ScopeTracking(
                        False, frozenset({(10, 100)}),
                    ),
                },
            )
            self.assertEqual(sample["alerts"], [
                "aggregate-rss-ceiling", "low-mem-available", "paging-activity",
            ])
            self.assertFalse(hasattr(subject, "kill"))

    def test_cli_creates_closed_nonoverwriting_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / "proc"
            proc.mkdir()
            fake = FakeProc(proc)
            fake.process(10, "controller", 1, 10, 100, 1000)
            output = root / "samples.jsonl"
            old_argv = subject.os.sys.argv
            subject.os.sys.argv = [
                str(SOURCE), "--output", str(output),
                "--controller-pid", "10", "--controller-start-ticks", "100",
                "--proc-root", str(proc), "--once", "--quiet",
            ]
            try:
                self.assertEqual(subject.main(), 0)
            finally:
                subject.os.sys.argv = old_argv
            lines = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["kind"],
                             "candle-canonical-bootstrap-resource-monitor")
            self.assertEqual(lines[1]["member_pids"], [10])
            self.assertEqual(output.stat().st_mode & 0o777, 0o444)

            subject.os.sys.argv = [
                str(SOURCE), "--output", str(output),
                "--controller-pid", "10", "--controller-start-ticks", "100",
                "--proc-root", str(proc), "--once", "--quiet",
            ]
            try:
                with self.assertRaisesRegex(subject.SampleError, "could not create"):
                    subject.main()
            finally:
                subject.os.sys.argv = old_argv

    def test_cli_seals_normal_controller_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / "proc"
            proc.mkdir()
            FakeProc(proc).process(10, "controller", 1, 10, 100, 1000)
            output = root / "samples.jsonl"
            old_argv = subject.os.sys.argv
            subject.os.sys.argv = [
                str(SOURCE), "--output", str(output),
                "--controller-pid", "10", "--controller-start-ticks", "100",
                "--proc-root", str(proc), "--interval-seconds", "1", "--quiet",
            ]

            def remove_anchor(_seconds: int) -> None:
                (proc / "10" / "stat").unlink()

            try:
                with mock.patch.object(subject.time, "sleep", side_effect=remove_anchor):
                    self.assertEqual(subject.main(), 0)
            finally:
                subject.os.sys.argv = old_argv
            lines = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(len(lines), 4)
            self.assertEqual(lines[-1], {
                "kind": "candle-canonical-bootstrap-resource-monitor-terminal",
                "outcome": "controller-exited",
                "sample_count": 2,
                "schema": 1,
                "utc": lines[-1]["utc"],
            })
            self.assertEqual(lines[-2]["scope_states"]["canonical"], "closed")
            self.assertEqual(output.stat().st_mode & 0o777, 0o444)

    def test_output_replacement_is_rejected_without_chmodding_alien(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "samples.jsonl"
            output = subject.open_exclusive(path)
            try:
                output.write(b"authentic\n")
                output.sync()
                path.unlink()
                path.write_bytes(b"alien\n")
                with self.assertRaisesRegex(
                    subject.SampleError, "no longer names the created inode",
                ):
                    output.seal()
            finally:
                output.close()
            self.assertEqual(path.read_bytes(), b"alien\n")
            self.assertNotEqual(path.stat().st_mode & 0o777, 0o444)

    def test_parent_replacement_before_open_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "output"
            displaced = root / "displaced"
            parent.mkdir()
            path = parent / "samples.jsonl"
            original_open = subject.os.open
            replaced = False

            def replace_before_open(name, flags, *args, **kwargs):
                nonlocal replaced
                if not replaced and name == parent and flags & os.O_DIRECTORY:
                    replaced = True
                    parent.rename(displaced)
                    parent.mkdir()
                return original_open(name, flags, *args, **kwargs)

            with mock.patch.object(
                subject.os, "open", side_effect=replace_before_open,
            ):
                with self.assertRaisesRegex(
                    subject.SampleError, "output parent changed before it was opened",
                ):
                    subject.open_exclusive(path)
            self.assertTrue(replaced)
            self.assertFalse(path.exists())
            self.assertFalse((displaced / path.name).exists())


if __name__ == "__main__":
    unittest.main()
