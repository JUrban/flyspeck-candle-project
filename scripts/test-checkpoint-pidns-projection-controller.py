#!/usr/bin/python3

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import select
import signal
import struct
import sys
import tempfile
import unittest

import checkpoint_os_authenticator as auth
import checkpoint_pidns_projection_controller as subject


PYTHON = str(Path(sys.executable).resolve(strict=True))
ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def _content(seed: str) -> dict[str, object]:
    return auth.protocol_content_record({"seed": seed})


def _challenges() -> dict[str, object]:
    result: dict[str, object] = {
        "schema": 1,
        "kind": auth.CHALLENGE_KIND,
        "policy": auth.CHALLENGE_POLICY,
        "challenge_id": "1" * 64,
        "diagnostic_pilot_nonce": "2" * 32,
        "origin_attempt_nonce": "3" * 32,
        "checkpoint_token": "4" * 64,
        "resume_nonce": "5" * 32,
        "resume_token": "6" * 64,
        "clean_attempt_nonces": ["7" * 32, "8" * 32],
        "pft_used": False,
    }
    for index, name in enumerate((
        "authenticated_plan", "diagnostic_pilot", "dmtcp_authority",
        "resource_limits", "runtime_environment", "checkpoint_environment",
    )):
        result[name] = _content(f"authority-{index}")
    return result


def _limits() -> object:
    values = {
        "max_address_space_bytes": 1024**3,
        "max_aggregate_rss_kib": 1024**2,
        "max_checkpoint_image_bytes": 1024**3,
        "max_retained_disk_bytes": 2 * 1024**3,
        "sampling_interval_milliseconds": 100,
    }
    return auth._make_observation("resource-limits", values, False)


class PidnsProjectionControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/project")
        self.root = Path(self.temporary.name)
        (self.root / "checkpoints").mkdir()
        stage = self.root / "staging/checkpoint-e"
        stage.mkdir(parents=True)
        target = stage / "only-image.dmtcp"
        target.write_bytes(b"process-only checkpoint fixture\n")
        target.chmod(0o600)
        authority = auth.file_expectation(target)
        self.images = [{
            "path": target.name,
            "bytes": authority["bytes"],
            "sha256": authority["sha256"],
            "md5": authority["md5"],
            "file_type": "ordinary",
            "mode": "0444",
            "link_count": 1,
        }]
        stage.chmod(0o700)

        def ioctl_runner(fd, request, argument, _mutate):
            if request == auth.FS_IOC_MEASURE_VERITY:
                size = os.fstat(fd).st_size
                digest = hashlib.sha256(os.pread(fd, size, 0)).digest()
                struct.pack_into(
                    "=HH", argument, 0,
                    auth.FS_VERITY_HASH_ALGORITHM_SHA256,
                    auth.FS_VERITY_SHA256_DIGEST_BYTES,
                )
                argument[4:36] = digest
            elif request != auth.FS_IOC_ENABLE_VERITY:
                self.fail(f"unexpected fs-verity ioctl {request}")
            return 0

        self.ioctl_runner = ioctl_runner
        self.filesystem = auth.AnchoredFilesystem(self.root)
        self.seal = auth.seal_staged_checkpoint_images_fsverity(
            filesystem=self.filesystem,
            staging_directory="staging/checkpoint-e",
            images=self.images, block_size=4096,
            confirm_irreversible=True, ioctl_runner=self.ioctl_runner,
        )
        self.publication = auth.publish_checkpoint_no_replace(
            filesystem=self.filesystem,
            staging_directory="staging/checkpoint-e",
            publication_parent="checkpoints", images=self.images,
            challenges=_challenges(), resource_limits=_limits(),
        )
        self.projection = self.root / "projection"
        self.projection.mkdir(mode=0o700)

    def tearDown(self) -> None:
        self.publication.close()
        self.filesystem.close()
        self.temporary.cleanup()

    def start(self, code: str, *, timeout: float = 10.0):
        return subject.start_pidns_projection_trace(
            self.publication, self.seal,
            projection_root=self.projection,
            argv_prefix=[PYTHON, "-I", "-S", "-c", code],
            executable_authority=auth.file_expectation(PYTHON),
            environment=ENVIRONMENT, challenge="a" * 64,
            timeout_seconds=timeout, ioctl_runner=self.ioctl_runner,
        )

    def run_workload(self, code: str, *, timeout: float = 10.0):
        return subject.run_pidns_projection_trace_diagnostic(
            self.publication, self.seal,
            projection_root=self.projection,
            argv_prefix=[PYTHON, "-I", "-S", "-c", code],
            executable_authority=auth.file_expectation(PYTHON),
            environment=ENVIRONMENT, challenge="a" * 64,
            timeout_seconds=timeout, ioctl_runner=self.ioctl_runner,
        )

    def test_exact_projection_and_true_task_trace_close(self) -> None:
        marker = self.root / "read-result"
        sentinel = os.open("/dev/null", os.O_RDONLY)
        os.set_inheritable(sentinel, True)
        code = (
            "import errno,os,pathlib,sys;"
            f"\ntry: os.fstat({sentinel})\n"
            "except OSError as error:\n"
            " assert error.errno == errno.EBADF\n"
            "else: raise SystemExit(22)\n"
            f"pathlib.Path({str(marker)!r}).write_text("
            "pathlib.Path(sys.argv[1]).read_text())"
        )
        try:
            observed = self.run_workload(code)
        finally:
            os.close(sentinel)
        self.assertFalse(observed.nonfixture)
        evidence = observed.evidence
        self.assertEqual(evidence["outcome"], "local-task-trace-closed")
        self.assertTrue(evidence["local_process_trace_closed"])
        self.assertTrue(evidence["local_task_trace_closed"])
        self.assertEqual(
            [packet["event"] for packet in evidence["packets"]],
            ["manager", "ready", "exec", "exit-stop", "terminal",
             "result", "done"],
        )
        self.assertEqual(marker.read_text(), "process-only checkpoint fixture\n")
        self.assertEqual(list(self.projection.iterdir()), [])
        ready = evidence["packets"][1]["payload"]
        self.assertEqual(ready["manager"]["inner_pid"], 1)
        self.assertEqual(ready["root_process"]["inner_pid"], 2)
        self.assertEqual(ready["root_process"]["inner_tgid"], 2)
        self.assertEqual(ready["root_task"]["inner_tid"], 2)
        self.assertEqual(ready["root_task"]["inner_tgid"], 2)
        self.assertTrue(ready["root_task"]["task_directory_held"])
        self.assertEqual(ready["root_task"]["birth"]["kind"], "root")
        self.assertEqual(ready["procfs"]["magic"], subject.PROC_SUPER_MAGIC)
        self.assertNotEqual(
            evidence["parent_namespaces"]["pid"]["inode"],
            ready["manager"]["pid_namespace"]["inode"],
        )
        self.assertFalse(evidence["host_pid_namespace_hidden"])
        self.assertTrue(
            evidence["primary_procfs_rooted_in_private_pid_namespace"],
        )
        self.assertEqual(evidence["pft_use_status"], "not-observed-or-excluded")
        for field in (
            "os_evidence_authenticated", "runtime_qualified",
            "promotion_allowed", "s2_evidence", "s3_evidence",
            "pft_exclusion_enforced", "host_filesystem_hidden",
            "network_namespace_private", "dmtcp_compatibility_tested",
            "approval_included", "controller_supplied_pft_input",
        ):
            self.assertIs(evidence[field], False)
        self.assertTrue(evidence["threads_supported"])
        self.assertTrue(evidence["leader_pidfds_only"])
        self.assertEqual(
            evidence["thread_identity_scope"],
            "held-exact-inner-proc-task-directories",
        )

    def test_double_fork_setsid_and_exec_are_closed_without_proc_scan(self) -> None:
        code = """
import os
first = os.fork()
if first == 0:
    os.setsid()
    second = os.fork()
    if second == 0:
        os.execve('/usr/bin/true', ['/usr/bin/true'], {'PATH':'/usr/bin:/bin','LC_ALL':'C'})
    _, status = os.waitpid(second, 0)
    os._exit(os.waitstatus_to_exitcode(status))
_, status = os.waitpid(first, 0)
raise SystemExit(os.waitstatus_to_exitcode(status))
"""
        observed = self.run_workload(code)
        result = next(
            packet["payload"] for packet in observed.evidence["packets"]
            if packet["event"] == "result"
        )
        self.assertEqual(result["event_counts"]["fork"], 2)
        self.assertEqual(result["event_counts"]["exec"], 2)
        self.assertEqual(result["event_counts"]["terminal"], 3)
        self.assertEqual(result["terminal_count"], 3)
        self.assertEqual(len(observed.evidence["transferred_processes"]), 3)

    def test_bad_ready_ack_never_releases_root(self) -> None:
        marker = self.root / "bad-ack-ran"
        session = self.start(
            f"import pathlib;pathlib.Path({str(marker)!r}).write_text('ran')",
        )
        try:
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "manager",
            )
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "ready",
            )
            bad_ack = {
                "schema": subject.SCHEMA,
                "kind": subject.ACK_KIND,
                "policy": subject.POLICY,
                "challenge": session.challenge,
                "controller_outer_pid": session.manager_outer_pid,
                "ready_sha256": "0" * 64,
                "approval_included": False,
                "controller_supplied_pft_input": False,
            }
            session.channel.send(auth.canonical_json_bytes(bad_ack))
            report = subject.finish_pidns_projection_trace(
                session, require_success=False,
            )
        finally:
            if not session.finished:
                subject._abort_session(session)
                session.finished = True
                session.close()
        self.assertFalse(report["local_process_trace_closed"])
        self.assertIn("READY ACK differs", report["errors"][0]["message"])
        self.assertFalse(marker.exists())
        self.assertEqual(list(self.projection.iterdir()), [])

    def test_clone3_fallback_and_escape_rejections(self) -> None:
        clone3_code = f"""
import ctypes, errno
library = ctypes.CDLL(None, use_errno=True)
library.syscall.restype = ctypes.c_long
result = library.syscall(435, 0, 0)
if result != -1 or ctypes.get_errno() != errno.ENOSYS:
    raise SystemExit(21)
"""
        self.assertTrue(
            self.run_workload(clone3_code).evidence[
                "local_process_trace_closed"
            ],
        )
        forbidden = (
            f"import os;os.unshare({subject.CLONE_NEWNS})",
            """
import ctypes, os, signal
library=ctypes.CDLL(None,use_errno=True);library.syscall.restype=ctypes.c_long
library.syscall(56, 0x00800000 | signal.SIGCHLD, 0, 0, 0, 0)
""",
        )
        for code in forbidden:
            with self.subTest(code=code), self.assertRaises(
                subject.PidnsProjectionError,
            ):
                self.run_workload(code)
            self.assertEqual(list(self.projection.iterdir()), [])

    def test_threads_have_held_task_identity_without_task_pidfds(self) -> None:
        code = """
import threading
barrier = threading.Barrier(3)
def worker():
    barrier.wait()
threads = [threading.Thread(target=worker) for _ in range(2)]
for thread in threads: thread.start()
barrier.wait()
for thread in threads: thread.join()
"""
        observed = self.run_workload(code)
        result = next(
            packet["payload"] for packet in observed.evidence["packets"]
            if packet["event"] == "result"
        )
        self.assertEqual(result["event_counts"]["thread-birth"], 2)
        self.assertEqual(result["event_counts"]["process-birth"], 0)
        self.assertEqual(result["event_counts"]["terminal"], 3)
        self.assertEqual(result["active_tasks"], 0)
        thread_births = [
            packet for packet in observed.evidence["packets"]
            if packet["event"] == "clone" and
            packet["payload"]["birth"]["kind"] == "clone-thread"
        ]
        self.assertEqual(len(thread_births), 2)
        for packet in thread_births:
            task = packet["payload"]["task"]
            self.assertNotEqual(task["inner_tid"], task["inner_tgid"])
            self.assertTrue(task["task_directory_held"])
            self.assertFalse(packet["payload"]["transferred_pidfd"])
        # READY transfers the root process pidfd; no thread gets one.
        self.assertEqual(len(observed.evidence["transferred_processes"]), 1)

    def test_mixed_thread_and_fork_births_keep_separate_identity(self) -> None:
        code = """
import os, threading
result = []
def worker():
    child = os.fork()
    if child == 0:
        os._exit(0)
    _, status = os.waitpid(child, 0)
    result.append(os.waitstatus_to_exitcode(status))
thread = threading.Thread(target=worker)
thread.start(); thread.join()
raise SystemExit(result[0])
"""
        observed = self.run_workload(code)
        result = next(
            packet["payload"] for packet in observed.evidence["packets"]
            if packet["event"] == "result"
        )
        self.assertEqual(result["event_counts"]["thread-birth"], 1)
        self.assertEqual(result["event_counts"]["process-birth"], 1)
        self.assertEqual(result["event_counts"]["fork"], 1)
        self.assertEqual(result["event_counts"]["terminal"], 3)
        fork = next(
            packet for packet in observed.evidence["packets"]
            if packet["event"] == "fork"
        )
        self.assertNotEqual(
            fork["payload"]["parent_inner_tid"],
            fork["payload"]["parent_inner_pid"],
        )
        self.assertEqual(
            fork["payload"]["task"]["inner_tid"],
            fork["payload"]["task"]["inner_tgid"],
        )
        for packet in observed.evidence["packets"]:
            if (
                packet["payload"]["transferred_pidfd"] and
                packet["event"] != "ready"
            ):
                task = packet["payload"]["task"]
                self.assertEqual(task["inner_tid"], task["inner_tgid"])
        self.assertEqual(len(observed.evidence["transferred_processes"]), 2)

    def test_nonleader_exec_rekeys_tid_and_records_exec_collapse(self) -> None:
        code = """
import os, threading, time
def worker():
    os.execve('/usr/bin/true', ['/usr/bin/true'],
              {'PATH':'/usr/bin:/bin','LC_ALL':'C'})
threading.Thread(target=worker).start()
while True:
    time.sleep(1)
"""
        observed = self.run_workload(code)
        result = next(
            packet["payload"] for packet in observed.evidence["packets"]
            if packet["event"] == "result"
        )
        self.assertEqual(result["event_counts"]["thread-birth"], 1)
        self.assertEqual(result["event_counts"]["exec-rekey"], 1)
        self.assertGreaterEqual(
            result["event_counts"]["exec-collapse-task"], 1,
        )
        exec_packet = [
            packet for packet in observed.evidence["packets"]
            if packet["event"] == "exec"
        ][-1]
        transition = exec_packet["payload"]["exec_transition"]
        self.assertTrue(transition["nonleader_tid_rekey"])
        self.assertNotEqual(
            transition["former_inner_tid"], transition["event_inner_tid"],
        )
        self.assertIn(
            transition["event_inner_tid"], transition["collapsed_inner_tids"],
        )
        self.assertEqual(
            exec_packet["payload"]["task"]["inner_tid"],
            exec_packet["payload"]["process"]["inner_tgid"],
        )
        self.assertEqual(len(observed.evidence["transferred_processes"]), 1)

    def test_manager_death_tears_down_stopped_namespace(self) -> None:
        session = self.start("import time;time.sleep(30)", timeout=20)
        retained_root_pidfd = -1
        try:
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "manager",
            )
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "ready",
            )
            retained_root_pidfd = os.dup(
                session.transferred_pidfds[-1]["descriptor"],
            )
            signal.pidfd_send_signal(
                session.manager_pidfd, signal.SIGKILL, None, 0,
            )
            report = subject.finish_pidns_projection_trace(
                session, require_success=False,
            )
            poller = select.poll()
            poller.register(retained_root_pidfd, select.POLLIN)
            self.assertTrue(poller.poll(5000))
        finally:
            if retained_root_pidfd >= 0:
                os.close(retained_root_pidfd)
            if not session.finished:
                subject._abort_session(session)
                session.finished = True
                session.close()
        self.assertFalse(report["local_process_trace_closed"])
        self.assertEqual(list(self.projection.iterdir()), [])

    def test_outer_timeout_kills_running_namespace(self) -> None:
        session = self.start("import time;time.sleep(30)", timeout=1.5)
        retained_root_pidfd = -1
        try:
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "manager",
            )
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "ready",
            )
            retained_root_pidfd = os.dup(
                session.transferred_pidfds[-1]["descriptor"],
            )
            subject.acknowledge_pidns_projection_ready(session)
            report = subject.finish_pidns_projection_trace(
                session, require_success=False,
            )
            poller = select.poll()
            poller.register(retained_root_pidfd, select.POLLIN)
            self.assertTrue(poller.poll(5000))
        finally:
            if retained_root_pidfd >= 0:
                os.close(retained_root_pidfd)
            if not session.finished:
                subject._abort_session(session)
                session.finished = True
                session.close()
        self.assertFalse(report["local_process_trace_closed"])
        self.assertIn("timed out", report["collection_error"]["message"])
        self.assertEqual(list(self.projection.iterdir()), [])

    def test_unfinished_session_close_aborts_and_reaps(self) -> None:
        session = self.start("import time;time.sleep(30)", timeout=20)
        retained_root_pidfd = -1
        try:
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "manager",
            )
            self.assertEqual(
                subject.receive_pidns_projection_packet(session)["event"],
                "ready",
            )
            retained_root_pidfd = os.dup(
                session.transferred_pidfds[-1]["descriptor"],
            )
            session.close()
            poller = select.poll()
            poller.register(retained_root_pidfd, select.POLLIN)
            self.assertTrue(poller.poll(5000))
        finally:
            if retained_root_pidfd >= 0:
                os.close(retained_root_pidfd)
            if not session.finished:
                session.close()
        self.assertTrue(session.finished)
        self.assertEqual(list(self.projection.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
