#!/usr/bin/python3

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import platform
import select
import signal
import socket
import struct
import sys
import time
import unittest


SUBJECT_PATH = Path(__file__).with_name("checkpoint_trace_controller.py")
SPEC = importlib.util.spec_from_file_location(
    "checkpoint_trace_controller", SUBJECT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)

PYTHON = str(Path(sys.executable).resolve(strict=True))
TRUE = str(Path("/usr/bin/true").resolve(strict=True))
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def process_packets(report, event):
    return [packet for packet in report["packets"] if packet["event"] == event]


class TraceControllerTests(unittest.TestCase):
    def test_true_trace_is_closed_but_permanently_unapproved(self):
        report = subject.run_trace([TRUE], ENVIRONMENT, 10)
        self.assertEqual(report["outcome"], "local-trace-closed")
        self.assertTrue(report["local_trace_closed"])
        self.assertEqual(
            [packet["event"] for packet in report["packets"]],
            [
                "controller", "tracee-launch", "exec", "exit-stop",
                "terminal", "result", "done",
            ],
        )
        terminal = process_packets(report, "terminal")[0]["payload"]
        self.assertEqual(terminal["exit_code"], 0)
        self.assertIsNone(terminal["signal"])
        for field in (
            "os_evidence_authenticated", "trusted_lifecycle",
            "promotion_allowed", "s2_evidence", "s3_evidence", "pft_used",
        ):
            self.assertIs(report[field], False)
        self.assertEqual(report["approval_status"], "unapproved-local-prototype")

    def test_transient_double_fork_setsid_and_exec_are_traced(self):
        code = """
import os
first = os.fork()
if first == 0:
    os.setsid()
    second = os.fork()
    if second == 0:
        os.execve('/usr/bin/true', ['/usr/bin/true'], {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    _, status = os.waitpid(second, 0)
    os._exit(os.waitstatus_to_exitcode(status))
_, status = os.waitpid(first, 0)
raise SystemExit(os.waitstatus_to_exitcode(status))
"""
        report = subject.run_trace(
            [PYTHON, "-I", "-S", "-c", code], ENVIRONMENT, 10,
        )
        self.assertTrue(report["local_trace_closed"])
        summary = process_packets(report, "result")[0]["payload"]
        self.assertEqual(summary["event_counts"]["fork"], 2)
        self.assertEqual(summary["event_counts"]["exec"], 2)
        self.assertEqual(summary["event_counts"]["exit-stop"], 3)
        self.assertEqual(summary["event_counts"]["terminal"], 3)
        true_execs = [
            packet["payload"]["process"]
            for packet in process_packets(report, "exec")
            if packet["payload"]["process"]["executable"]["path"] == TRUE
        ]
        self.assertEqual(len(true_execs), 1)
        self.assertNotEqual(
            true_execs[0]["session_id"],
            process_packets(report, "tracee-launch")[0]["payload"]
                ["process"]["session_id"],
        )

    def test_sender_credentials_are_not_self_asserted(self):
        socket_type = socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0)
        receiver, sender = socket.socketpair(socket.AF_UNIX, socket_type)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        child = os.fork()
        if child == 0:
            receiver.close()
            packet = {
                "schema": subject.PACKET_SCHEMA,
                "kind": subject.PACKET_KIND,
                "controller_pid": os.getppid(),
                "sequence": 0,
                "monotonic_ns": time.monotonic_ns(),
                "event": "forged",
                "payload": {},
            }
            sender.send(subject.canonical_json_bytes(packet))
            sender.close()
            os._exit(0)
        sender.close()
        session = subject.TraceSession(os.getpid(), -1, receiver)
        try:
            with self.assertRaisesRegex(
                subject.TraceControllerError, "sender credentials",
            ):
                subject.receive_packet(session)
        finally:
            receiver.close()
            os.waitpid(child, 0)

    def test_pid_identity_change_is_rejected(self):
        def packet(sequence, ticks, inode):
            return {
                "sequence": sequence,
                "event": "identity-fixture",
                "payload": {
                    "process": {
                        "pid": 123,
                        "start_ticks": ticks,
                        "pidfd": {"device": 5, "inode": inode},
                    },
                },
            }

        subject._validate_identity_stream([packet(0, 100, 200), packet(1, 100, 200)])
        for changed in (packet(1, 101, 200), packet(1, 100, 201)):
            with self.assertRaisesRegex(subject.TraceControllerError, "pid identity"):
                subject._validate_identity_stream([packet(0, 100, 200), changed])

    def test_controller_death_exitkills_complete_tracee_tree(self):
        code = """
import os
import time
first = os.fork()
if first == 0:
    os.setsid()
    os.fork()
time.sleep(30)
"""
        session = subject.start_trace(
            [PYTHON, "-I", "-S", "-c", code], ENVIRONMENT, 40,
        )
        root_pid = None
        tracee_pidfds = {}
        try:
            while (root_pid is None or
                   len(process_packets(
                       {"packets": session.packets}, "fork",
                   )) < 2):
                packet = subject.receive_packet(session)
                self.assertIsNotNone(packet)
                if packet["event"] == "tracee-launch":
                    root_pid = packet["payload"]["root_pid"]
            tracee_pids = {root_pid} | {
                packet["payload"]["child"]["pid"]
                for packet in process_packets(
                    {"packets": session.packets}, "fork",
                )
            }
            self.assertEqual(len(tracee_pids), 3)
            tracee_pidfds = {
                pid: os.pidfd_open(pid, 0) for pid in tracee_pids
            }
            signal.pidfd_send_signal(
                session.controller_pidfd, signal.SIGKILL, None, 0,
            )
            with self.assertRaisesRegex(
                subject.TraceControllerError, "did not close",
            ):
                subject.collect_trace(session)
            for pid, descriptor in tracee_pidfds.items():
                poller = select.poll()
                poller.register(descriptor, select.POLLIN)
                self.assertTrue(
                    poller.poll(5000),
                    f"EXITKILL did not terminate tracee {pid}",
                )
        finally:
            for pid, descriptor in tracee_pidfds.items():
                try:
                    signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
                except ProcessLookupError:
                    pass
                os.close(descriptor)
            if not session.collected:
                try:
                    signal.pidfd_send_signal(
                        session.controller_pidfd, signal.SIGKILL, None, 0,
                    )
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(session.controller_pid, 0)
                except ChildProcessError:
                    pass
                session.close()

    def test_observer_timeout_kills_controller_and_tracee(self):
        session = subject.start_trace(
            [PYTHON, "-I", "-S", "-c", "import time; time.sleep(30)"],
            ENVIRONMENT, 40,
        )
        root_pidfd = -1
        try:
            while not process_packets({"packets": session.packets}, "tracee-launch"):
                self.assertIsNotNone(subject.receive_packet(session))
            root_pid = process_packets(
                {"packets": session.packets}, "tracee-launch",
            )[0]["payload"]["root_pid"]
            root_pidfd = os.pidfd_open(root_pid, 0)
            session.channel.settimeout(0.01)
            with self.assertRaisesRegex(
                subject.TraceControllerError, "event stream timed out",
            ):
                subject.collect_trace(session)
            poller = select.poll()
            poller.register(root_pidfd, select.POLLIN)
            self.assertTrue(poller.poll(5000), "timeout did not EXITKILL tracee")
        finally:
            if root_pidfd >= 0:
                try:
                    signal.pidfd_send_signal(root_pidfd, signal.SIGKILL, None, 0)
                except ProcessLookupError:
                    pass
                os.close(root_pidfd)
            if not session.collected:
                try:
                    signal.pidfd_send_signal(
                        session.controller_pidfd, signal.SIGKILL, None, 0,
                    )
                except ProcessLookupError:
                    pass
                try:
                    os.waitpid(session.controller_pid, 0)
                except ChildProcessError:
                    pass
                session.close()

    @unittest.skipUnless(platform.machine() == "x86_64", "x86_64 clone syscall fixture")
    def test_clone_untraced_is_detected_and_rejected(self):
        code = """
import ctypes
import os
import signal
import time
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
child = libc.syscall(56, 0x00800000 | signal.SIGCHLD, 0, 0, 0, 0)
if child == 0:
    time.sleep(2)
    os._exit(0)
if child < 0:
    raise OSError(ctypes.get_errno(), 'clone')
time.sleep(1)
os.waitpid(child, 0)
"""
        report = subject.run_trace(
            [PYTHON, "-I", "-S", "-c", code], ENVIRONMENT, 10,
        )
        self.assertFalse(report["local_trace_closed"])
        self.assertEqual(report["outcome"], "local-trace-rejected")
        self.assertEqual(len(report["errors"]), 1)
        self.assertIn("CLONE_UNTRACED", report["errors"][0]["message"])
        for field in (
            "os_evidence_authenticated", "trusted_lifecycle",
            "promotion_allowed", "s2_evidence", "s3_evidence", "pft_used",
        ):
            self.assertIs(report[field], False)

    def test_launch_contract_rejects_alias_and_forbidden_namespace(self):
        with self.assertRaisesRegex(subject.TraceControllerError, "canonical"):
            subject.start_trace(["/usr/bin/python3", "-c", "pass"], ENVIRONMENT)
        with self.assertRaisesRegex(subject.TraceControllerError, "forbidden"):
            subject.start_trace([TRUE, "p" + "ft-control"], ENVIRONMENT)
        with self.assertRaisesRegex(subject.TraceControllerError, "environment"):
            subject.start_trace([TRUE], {"BAD=NAME": "1"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
