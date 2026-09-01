#!/usr/bin/python3
"""Hostile tests for the live checkpoint OS-authenticator companion."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "checkpoint_os_authenticator", HERE / "checkpoint_os_authenticator.py",
)
assert SPEC is not None and SPEC.loader is not None
AUTH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTH
SPEC.loader.exec_module(AUTH)
DIRECT_SPEC = importlib.util.spec_from_file_location(
    "direct_release_protocol_for_os_test", HERE / "direct_release_protocol.py",
)
assert DIRECT_SPEC is not None and DIRECT_SPEC.loader is not None
DIRECT = importlib.util.module_from_spec(DIRECT_SPEC)
sys.modules[DIRECT_SPEC.name] = DIRECT
DIRECT_SPEC.loader.exec_module(DIRECT)


def content_record(seed: bytes) -> dict[str, object]:
    return AUTH.protocol_content_record({"seed": seed.decode()})


def challenges() -> dict[str, object]:
    result: dict[str, object] = {
        "schema": 1,
        "kind": AUTH.CHALLENGE_KIND,
        "policy": AUTH.CHALLENGE_POLICY,
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
        result[name] = content_record(f"authority-{index}".encode())
    return result


def limit_values(interval: int = 100) -> dict[str, int]:
    return {
        "max_address_space_bytes": 1024**3,
        "max_aggregate_rss_kib": 1024**2,
        "max_checkpoint_image_bytes": 1024**3,
        "max_retained_disk_bytes": 2 * 1024**3,
        "sampling_interval_milliseconds": interval,
    }


def fixture_limits(interval: int = 100) -> object:
    return AUTH._make_observation("resource-limits", limit_values(interval), False)


def proc_stat(pid: int, ppid: int, pgid: int, start: int) -> bytes:
    # Fields after comm begin with proc field 3 (state).  These indexes cover
    # ppid/pgrp, utime/stime, starttime, vsize, and rss.
    rest = ["0"] * 22
    rest[0] = "S"
    rest[1] = str(ppid)
    rest[2] = str(pgid)
    rest[11] = "11"
    rest[12] = "13"
    rest[19] = str(start)
    rest[20] = "4096"
    rest[21] = "2"
    return f"{pid} (fixture controller) ".encode() + " ".join(rest).encode() + b"\n"


def make_fake_proc(root: Path, *, pid: int = 4321, pgid: int = 4321,
                   start: int = 98765) -> dict[str, object]:
    boot_id = "12345678-1234-1234-1234-123456789abc"
    (root / "sys/kernel/random").mkdir(parents=True)
    (root / "sys/kernel/random/boot_id").write_text(boot_id + "\n")
    (root / "net").mkdir()
    header = "sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"
    (root / "net/tcp").write_text(header)
    (root / "net/tcp6").write_text(header)
    process = root / str(pid)
    process.mkdir()
    (process / "fd").mkdir()
    (process / "stat").write_bytes(proc_stat(pid, 1, pgid, start))
    argv = ["/usr/local/bin/controller", "--fixture"]
    environment = {
        "CANDLE_CHECKPOINT_CHALLENGE_ID": "1" * 64,
        "MODE": "fixture",
    }
    (process / "cmdline").write_bytes(
        b"\0".join(item.encode() for item in argv) + b"\0"
    )
    (process / "environ").write_bytes(
        b"\0".join(f"{key}={value}".encode()
                    for key, value in environment.items()) + b"\0"
    )
    (process / "maps").write_bytes(
        b"1000-1004 r-xp 00000000 00:00 0 [vdso]\n"
    )
    vdso = b"VDS"
    vdso += b"O"
    (process / "vdso").write_bytes(vdso)
    os.symlink("/usr/local/bin/controller", process / "exe")
    kernel = {
        "release": os.uname().release,
        "machine": os.uname().machine,
        "boot_id": boot_id,
    }
    return {
        "pid": pid,
        "process_group_id": pgid,
        "start_ticks": start,
        "executable": "/usr/local/bin/controller",
        "argv": argv,
        "environment": environment,
        "vdso_sha256": hashlib.sha256(vdso).hexdigest(),
        "kernel": kernel,
    }


def rewrite_fake_process(root: Path, expected: dict[str, object]) -> None:
    process = root / str(expected["pid"])
    (process / "cmdline").write_bytes(
        b"\0".join(item.encode() for item in expected["argv"]) + b"\0"
    )
    (process / "environ").write_bytes(
        b"\0".join(f"{key}={value}".encode()
                    for key, value in expected["environment"].items()) + b"\0"
    )
    (process / "exe").unlink()
    os.symlink(expected["executable"], process / "exe")


def live_process_expected(pid: int) -> dict[str, object]:
    process = Path("/proc") / str(pid)
    stat_value = AUTH._parse_proc_stat((process / "stat").read_bytes())
    argv: list[str] = []
    for _ in range(100):
        argv = AUTH._parse_nul_vector(
            (process / "cmdline").read_bytes(), "argv",
        )
        if argv:
            break
        time.sleep(0.001)
    environment = AUTH._parse_environ((process / "environ").read_bytes())
    pid_fd = os.open(process, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        _, _, vdso = AUTH._read_vdso(
            pid_fd, (process / "maps").read_bytes(), fixture=False,
        )
    finally:
        os.close(pid_fd)
    return {
        "pid": pid,
        "process_group_id": stat_value["process_group_id"],
        "start_ticks": stat_value["start_ticks"],
        "executable": os.readlink(process / "exe"),
        "argv": argv,
        "environment": environment,
        "vdso_sha256": hashlib.sha256(vdso).hexdigest(),
        "kernel": {
            "release": os.uname().release,
            "machine": os.uname().machine,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        },
    }


def receipt(phase: str, identity: dict[str, int], event: str,
            nonce: str, action_index: int | None = None) -> bytes:
    challenge_name, challenge_value = AUTH.phase_challenge(challenges(), phase)
    return AUTH.canonical_json_bytes({
        "schema": 1,
        "kind": "candle-flyspeck-live-phase-receipt-v1",
        "phase": phase,
        "challenge_id": "1" * 64,
        "challenge_name": challenge_name,
        "challenge_value": challenge_value,
        "controller_identity": identity,
        "event": event,
        "event_nonce": nonce,
        "action_index": action_index,
        "pft_used": False,
    })


class AnchoredFilesystemTests(unittest.TestCase):
    def test_pft_and_control_namespaces_are_rejected_lexically(self) -> None:
        for path in (
            "checkpoint/PFT/image.dmtcp", "checkpoint/pFt-image.dmtcp",
            "checkpoint/pft.image.dmtcp",
        ):
            with self.assertRaisesRegex(AUTH.AuthenticationError, "PFT namespace"):
                AUTH._safe_relative(path, "hostile checkpoint path")
        with self.assertRaisesRegex(AUTH.AuthenticationError, "PFT namespace"):
            AUTH._absolute_to_relative(
                "/usr/local/lib/dmtcp/PfT.so", "hostile DMTCP library",
            )
        for path in ("checkpoint/evil\nname", "/usr/local/bin/evil\x7fname"):
            validator = (AUTH._safe_relative if not path.startswith("/")
                         else AUTH._absolute_to_relative)
            with self.assertRaisesRegex(AUTH.AuthenticationError, "malformed"):
                validator(path, "control-character path")

    def test_fd_hash_immutable_and_race_guards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            good = root / "good"
            good.write_bytes(b"trusted\n")
            good.chmod(0o444)
            expected = AUTH.file_expectation(good)
            with AUTH.AnchoredFilesystem(root) as filesystem:
                observed = filesystem.authenticate_file(
                    "good", expected, immutable=True,
                )
                self.assertEqual(observed["sha256"], expected["sha256"])

                os.symlink("good", root / "alias")
                with self.assertRaisesRegex(AUTH.AuthenticationError, "without following"):
                    filesystem.authenticate_file("alias", expected, immutable=True)

                os.link(good, root / "hardlink")
                with self.assertRaisesRegex(AUTH.AuthenticationError, "unalias"):
                    filesystem.authenticate_file("good", expected, immutable=True)
                (root / "hardlink").unlink()

                replacement = root / "replacement"
                replacement.write_bytes(b"trusted\n")
                replacement.chmod(0o444)

                def replace() -> None:
                    os.replace(replacement, good)

                with self.assertRaisesRegex(AUTH.AuthenticationError, "replaced"):
                    filesystem.authenticate_file(
                        "good", expected, immutable=True, after_read_hook=replace,
                    )

    def test_component_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "real").mkdir()
            (root / "real/file").write_bytes(b"x")
            os.symlink("real", root / "linked")
            expected = AUTH.file_expectation(root / "real/file")
            with AUTH.AnchoredFilesystem(root) as filesystem:
                with self.assertRaises(AUTH.AuthenticationError):
                    filesystem.authenticate_file("linked/file", expected, immutable=False)


class AuthorityTests(unittest.TestCase):
    def test_challenge_schema_rejects_bool_and_policy_drift(self) -> None:
        for field, value in (("schema", True), ("policy", "self-selected")):
            hostile = challenges()
            hostile[field] = value
            with self.assertRaisesRegex(
                AUTH.AuthenticationError, "malformed external",
            ):
                AUTH.validate_controller_challenges(hostile)

    def test_fake_dmtcp_exact_roles_and_alias_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for role, path in AUTH.DMTCP_ROLE_PATHS.items():
                target = root / path.removeprefix("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((role + "\n").encode())
                target.chmod(0o755)
            library = root / "usr/local/lib/dmtcp/libdmtcp.so"
            library.parent.mkdir(parents=True)
            library.write_bytes(b"library\n")
            library.chmod(0o755)
            expected = {
                "version": AUTH.DMTCP_VERSION,
                "executables": [{
                    "role": role,
                    "path": path,
                    "authority": AUTH.file_expectation(root / path.removeprefix("/")),
                } for role, path in AUTH.DMTCP_ROLE_PATHS.items()],
                "injected_libraries": [{
                    "path": "/usr/local/lib/dmtcp/libdmtcp.so",
                    "authority": AUTH.file_expectation(library),
                }],
                "elf_closure": [],
            }
            token = AUTH.authenticate_dmtcp_authority(
                expected, filesystem_root=str(root),
                version_runner=lambda _path: "dmtcp (DMTCP) 4.1.0\n",
                readelf_runner=lambda _fd: "Dynamic section has no NEEDED entries\n",
            )
            self.assertFalse(token.nonfixture)

            wrapper = copy.deepcopy(expected)
            wrapper["executables"][0]["path"] = "/project/bin/dmtcp_command"
            with self.assertRaisesRegex(AUTH.AuthenticationError, "/usr/local"):
                AUTH.authenticate_dmtcp_authority(
                    wrapper, filesystem_root=str(root),
                    version_runner=lambda _path: "dmtcp (DMTCP) 4.1.0\n",
                    readelf_runner=lambda _fd: "",
                )

            launch = root / "usr/local/bin/dmtcp_launch"
            launch.unlink()
            os.link(root / "usr/local/bin/dmtcp_command", launch)
            alias = copy.deepcopy(expected)
            alias["executables"][2]["authority"] = AUTH.file_expectation(launch)
            with self.assertRaisesRegex(AUTH.AuthenticationError, "aliases"):
                AUTH.authenticate_dmtcp_authority(
                    alias, filesystem_root=str(root),
                    version_runner=lambda _path: "dmtcp (DMTCP) 4.1.0\n",
                    readelf_runner=lambda _fd: "",
                )

    def test_live_host_role_paths_versions_kernel_and_wrapper(self) -> None:
        for role, path in AUTH.DMTCP_ROLE_PATHS.items():
            self.assertEqual(AUTH._parse_dmtcp_version(
                AUTH._run_dmtcp_version(path)
            ), AUTH.DMTCP_VERSION, role)
            with AUTH.AnchoredFilesystem("/") as filesystem:
                observed = filesystem.authenticate_file(
                    path.removeprefix("/"), AUTH.file_expectation(path),
                    immutable=False,
                )
            self.assertEqual(observed["path"], path.removeprefix("/"))
        self.assertNotEqual(
            os.stat("/project/bin/dmtcp_command").st_ino,
            os.stat("/usr/local/bin/dmtcp_command").st_ino,
        )
        expected = {
            "release": os.uname().release,
            "machine": os.uname().machine,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        }
        self.assertTrue(AUTH.authenticate_kernel(expected).nonfixture)

    def test_live_full_dmtcp_injected_set_and_elf_closure(self) -> None:
        injected_paths = sorted(
            str(path) for path in Path("/usr/local/lib/dmtcp").glob("*.so")
        )
        self.assertTrue(injected_paths)

        def needed(path: str) -> list[str]:
            output = subprocess.run(
                ["/usr/bin/readelf", "-d", path], check=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            ).stdout
            return re.findall(r"Shared library: \[([^\]]+)\]", output)

        search_directories = (
            Path("/lib/x86_64-linux-gnu"), Path("/lib64"),
            Path("/usr/lib/x86_64-linux-gnu"),
        )

        def resolve(soname: str) -> str:
            for directory in search_directories:
                candidate = directory / soname
                if candidate.exists():
                    return os.path.realpath(candidate)
            self.fail(f"cannot resolve live closure soname: {soname}")

        seed_paths = list(AUTH.DMTCP_ROLE_PATHS.values()) + injected_paths
        pending = {
            soname for path in seed_paths for soname in needed(path)
            if soname not in {Path(item).name for item in injected_paths}
        }
        closure_paths: dict[str, str] = {}
        while pending:
            soname = pending.pop()
            if soname in closure_paths:
                continue
            path = resolve(soname)
            closure_paths[soname] = path
            pending.update(
                dependency for dependency in needed(path)
                if dependency not in closure_paths and
                dependency not in {Path(item).name for item in injected_paths}
            )
        expected = {
            "version": AUTH.DMTCP_VERSION,
            "executables": [{
                "role": role, "path": path,
                "authority": AUTH.file_expectation(path),
            } for role, path in AUTH.DMTCP_ROLE_PATHS.items()],
            "injected_libraries": [{
                "path": path, "authority": AUTH.file_expectation(path),
            } for path in injected_paths],
            "elf_closure": [{
                "soname": soname, "path": closure_paths[soname],
                "authority": AUTH.file_expectation(closure_paths[soname]),
            } for soname in sorted(closure_paths)],
        }
        token = AUTH.authenticate_dmtcp_authority(expected)
        self.assertTrue(token.nonfixture)
        self.assertEqual(
            [item["path"] for item in token.evidence["injected_libraries"]],
            injected_paths,
        )

    def test_direct_authority_and_environments_need_external_challenge(self) -> None:
        executables = [{
            "role": role, "path": path, "bytes": index + 10,
            "sha256": f"{index + 1:x}" * 64,
            "md5": f"{index + 1:x}" * 32,
        } for index, (role, path) in enumerate(AUTH.DMTCP_ROLE_PATHS.items())]
        libraries = [{
            "path": "/usr/local/lib/dmtcp/libdmtcp.so", "bytes": 20,
            "sha256": "a" * 64, "md5": "b" * 32,
        }]
        closure_document = {
            "schema": 1,
            "kind": "candle-flyspeck-dmtcp-elf-closure-v1",
            "files": [{
                "soname": "libc.so.6", "path": "/lib/libc.so.6",
                "bytes": 30, "sha256": "c" * 64, "md5": "d" * 32,
            }],
        }
        direct = {
            "schema": 1, "kind": AUTH.DMTCP_AUTHORITY_KIND,
            "version": AUTH.DMTCP_VERSION,
            "executables": executables,
            "injected_libraries": libraries,
            "elf_closure": AUTH.protocol_content_record(closure_document),
            "kernel_trust": {
                "policy": "same-boot-pinned-kernel-vdso-v1",
                "release": "test-release", "machine": "x86_64",
                "vdso_sha256": "e" * 64,
            },
            "environment_policy": AUTH.DMTCP_ENVIRONMENT_POLICY,
            "allowed_environment_names":
                list(AUTH.DMTCP_ALLOWED_ENVIRONMENT_NAMES),
            "forbidden_environment_names":
                list(AUTH.DMTCP_FORBIDDEN_ENVIRONMENT_NAMES),
            "pft_used": False,
        }
        observed = AUTH._make_observation("dmtcp-authority", {
            "executables": copy.deepcopy(executables),
            "injected_libraries": copy.deepcopy(libraries),
            "elf_closure": copy.deepcopy(closure_document["files"]),
        }, False)
        kernel = AUTH._make_observation("kernel", {
            "release": "test-release", "machine": "x86_64",
            "boot_id": "12345678-1234-1234-1234-123456789abc",
        }, False)
        external = challenges()
        external["dmtcp_authority"] = AUTH.protocol_content_record(direct)
        bound = AUTH.bind_dmtcp_controller_authority(
            os_authority=observed, kernel=kernel, direct_authority=direct,
            elf_closure_document=closure_document, challenges=external,
        )
        self.assertFalse(bound.nonfixture)

        coherently_changed = copy.deepcopy(direct)
        coherently_changed["executables"][0]["sha256"] = "f" * 64
        with self.assertRaisesRegex(AUTH.AuthenticationError, "challenged value"):
            AUTH.bind_dmtcp_controller_authority(
                os_authority=observed, kernel=kernel,
                direct_authority=coherently_changed,
                elf_closure_document=closure_document, challenges=external,
            )

        runtime = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}
        checkpoint = {
            "DMTCP_CHECKPOINT_DIR": "checkpoint-staging",
            "DMTCP_COORD_PORT": "43210", "DMTCP_GZIP": "0",
            "DMTCP_QUIET": "2",
            "LD_PRELOAD": "/usr/local/lib/dmtcp/libdmtcp.so",
        }
        external["runtime_environment"] = AUTH.protocol_content_record(runtime)
        external["checkpoint_environment"] = AUTH.protocol_content_record(checkpoint)
        environments = AUTH.authenticate_challenged_environments(
            challenges=external, runtime_environment=runtime,
            checkpoint_environment=checkpoint, dmtcp_authority=bound,
        )
        self.assertEqual(environments.evidence["combined"], {
            **runtime, **checkpoint,
        })
        changed = copy.deepcopy(checkpoint)
        changed["DMTCP_QUIET"] = "1"
        with self.assertRaisesRegex(AUTH.AuthenticationError, "challenged"):
            AUTH.authenticate_challenged_environments(
                challenges=external, runtime_environment=runtime,
                checkpoint_environment=changed, dmtcp_authority=bound,
            )
        limits = limit_values()
        external["resource_limits"] = AUTH.protocol_content_record(limits)
        self.assertTrue(AUTH.authenticate_resource_limits(
            challenges=external, limits=limits,
        ).nonfixture)
        excessive = copy.deepcopy(limits)
        excessive["max_address_space_bytes"] = 121 * 1024**3
        external_tampered = copy.deepcopy(external)
        external_tampered["resource_limits"] = AUTH.protocol_content_record(excessive)
        with self.assertRaisesRegex(AUTH.AuthenticationError, "fixed envelope"):
            AUTH.authenticate_resource_limits(
                challenges=external_tampered, limits=excessive,
            )


class ProcessAndPhaseTests(unittest.TestCase):
    def test_fake_process_splice_and_coordinator_port(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            expected = make_fake_proc(root)
            process = root / str(expected["pid"])
            inode = "99123"
            port = 42424
            line = (
                f"0: 0100007F:{port:04X} 00000000:0000 0A "
                f"00000000:00000000 00:00000000 00000000 0 0 {inode}\n"
            )
            header = (root / "net/tcp").read_text().splitlines()[0] + "\n"
            (root / "net/tcp").write_text(header + line)
            os.symlink(f"socket:[{inode}]", process / "fd/3")
            pin = AUTH.pin_live_process(expected, proc_root=str(root))
            port_observation = AUTH.authenticate_coordinator_port(pin, port)
            self.assertFalse(port_observation.nonfixture)

            changed = copy.deepcopy(expected)
            changed["start_ticks"] += 1
            with self.assertRaisesRegex(AUTH.AuthenticationError, "drifted"):
                AUTH.pin_live_process(changed, proc_root=str(root))
            changed = copy.deepcopy(expected)
            changed["environment"]["MODE"] = "coherently-rehashed"
            with self.assertRaisesRegex(AUTH.AuthenticationError, "drifted"):
                AUTH.pin_live_process(changed, proc_root=str(root))
            pin.close()

    def test_live_self_pin_is_nonfixture_observation(self) -> None:
        expected = live_process_expected(os.getpid())
        pin = AUTH.pin_live_process(expected)
        try:
            self.assertTrue(pin.nonfixture)
            self.assertEqual(pin.evidence["start_ticks"], expected["start_ticks"])
        finally:
            pin.close()

    def test_coordinator_exact_argv_env_port_and_termination(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            expected = make_fake_proc(root)
            expected["executable"] = AUTH.DMTCP_ROLE_PATHS["coordinator"]
            expected["argv"] = [
                AUTH.DMTCP_ROLE_PATHS["coordinator"], "--port", "42424",
            ]
            expected["environment"] = {
                "LC_ALL": "C", "PATH": "/usr/bin:/bin",
                "DMTCP_CHECKPOINT_DIR": "checkpoint-staging",
                "DMTCP_COORD_PORT": "42424", "DMTCP_GZIP": "0",
                "DMTCP_QUIET": "2", "LD_PRELOAD": "/trusted/libdmtcp.so",
            }
            rewrite_fake_process(root, expected)
            process = root / str(expected["pid"])
            inode = "88221"
            line = (
                f"0: 0100007F:{42424:04X} 00000000:0000 0A "
                f"00000000:00000000 00:00000000 00000000 0 0 {inode}\n"
            )
            header = (root / "net/tcp").read_text().splitlines()[0] + "\n"
            (root / "net/tcp").write_text(header + line)
            os.symlink(f"socket:[{inode}]", process / "fd/4")
            pin = AUTH.pin_live_process(expected, proc_root=str(root))
            port = AUTH.authenticate_coordinator_port(pin, 42424)
            shutil.rmtree(process)
            completed = AUTH.complete_parent_owned_process(
                pin, allowed_exit_codes=(0,), fixture_completion={
                    "kind": "exit", "value": 0, "proc_absent": True,
                },
            )
            environment = AUTH._make_observation("challenged-environments", {
                "combined": expected["environment"],
            }, False)
            coordinator = AUTH.authenticate_coordinator_lifecycle(
                pin=pin, port_observation=port, completed_process=completed,
                environments=environment, expected_argv=expected["argv"],
            )
            self.assertFalse(coordinator.nonfixture)
            with self.assertRaisesRegex(AUTH.AuthenticationError, "not exact"):
                AUTH.authenticate_coordinator_lifecycle(
                    pin=pin, port_observation=port,
                    completed_process=completed, environments=environment,
                    expected_argv=expected["argv"] + ["--daemon"],
                )

    def test_parent_owned_pidfd_exit_and_reap(self) -> None:
        child = subprocess.Popen(
            ["/usr/bin/sleep", "60"], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={"LC_ALL": "C"}, start_new_session=True,
        )
        pin = None
        try:
            expected = live_process_expected(child.pid)
            pin = AUTH.pin_live_process(expected)
            os.killpg(child.pid, signal.SIGTERM)
            completed = AUTH.complete_parent_owned_process(
                pin, allowed_signals=(signal.SIGTERM,),
            )
            child.returncode = -signal.SIGTERM
            self.assertTrue(completed.nonfixture)
            self.assertTrue(completed.evidence["reaped"])
            self.assertFalse(Path(f"/proc/{child.pid}").exists())
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            if pin is not None:
                pin.close()

    def test_ptrace_exec_gate_stops_before_target_and_releases(self) -> None:
        kernel = AUTH.authenticate_kernel({
            "release": os.uname().release,
            "machine": os.uname().machine,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        })
        pin = AUTH.spawn_exec_gated_process(
            executable="/usr/bin/sleep", argv=["/usr/bin/sleep", "60"],
            environment={"LC_ALL": "C"}, kernel=kernel,
            new_process_group=True,
        )
        try:
            self.assertTrue(pin.gated_by_authenticator)
            self.assertTrue(pin.trace_attached)
            self.assertFalse(pin.gate_evidence["released"])
            self.assertIn(
                AUTH._parse_proc_stat(Path(f"/proc/{pin.evidence['pid']}/stat").read_bytes())[
                    "state"
                ], {"t", "T"},
            )
            AUTH.release_exec_gated_process(pin)
            self.assertTrue(pin.gate_evidence["released"])
            os.killpg(pin.evidence["pid"], signal.SIGTERM)
            completed = AUTH.complete_parent_owned_process(
                pin, allowed_signals=(signal.SIGTERM,),
            )
            self.assertTrue(completed.nonfixture)
        finally:
            if not pin.completed:
                if pin.trace_attached:
                    AUTH.release_exec_gated_process(pin)
                try:
                    os.killpg(pin.evidence["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    AUTH.complete_parent_owned_process(
                        pin, allowed_signals=(signal.SIGKILL,),
                    )
                except AUTH.AuthenticationError:
                    pin.close()

    def test_live_phase_receipts_cadence_and_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            proc_root = root / "proc"
            proc_root.mkdir()
            expected = make_fake_proc(proc_root)
            pin = AUTH.pin_live_process(expected, proc_root=str(proc_root))
            retained = root / "retained"
            retained.write_bytes(b"12345")
            retained_fd = os.open(retained, os.O_RDONLY | os.O_CLOEXEC)
            output = root / "evidence"
            output.mkdir(mode=0o700)
            try:
                observer = AUTH.LivePhaseObserver(
                    pin=pin, phase="origin", challenges=challenges(),
                    resource_limits=fixture_limits(100),
                    retained_fds=(retained_fd,), fixture_monotonic_ns=100_000_000,
                )
                identity = observer.identity
                observer.receive_event(
                    receipt("origin", identity, "action", "9" * 32, 0),
                    monotonic_ns=110_000_000,
                )
                ack = observer.receive_event(
                    receipt("origin", identity, "READY", "a" * 32),
                    monotonic_ns=120_000_000,
                )
                self.assertTrue(ack.startswith("ACK/READY/"))
                observer.end(monotonic_ns=150_000_000)
                shutil.rmtree(proc_root / str(expected["pid"]))
                completed = AUTH.complete_parent_owned_process(
                    pin, allowed_exit_codes=(0,), fixture_completion={
                        "kind": "exit", "value": 0, "proc_absent": True,
                    },
                )
                with AUTH.AnchoredFilesystem(root) as filesystem:
                    phase = observer.finish(
                        completed, filesystem=filesystem,
                        output_directory="evidence",
                    )
                    self.assertFalse(phase.nonfixture)
                    self.assertEqual(phase.evidence["sample_count"], 2)
                    with self.assertRaisesRegex(
                        AUTH.AuthenticationError, "no-replace",
                    ):
                        observer.finish(
                            completed, filesystem=filesystem,
                            output_directory="evidence",
                        )
            finally:
                os.close(retained_fd)
                pin.close()

    def test_origin_action_after_ready_and_receipt_splice_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            proc_root = Path(raw)
            expected = make_fake_proc(proc_root)
            pin = AUTH.pin_live_process(expected, proc_root=str(proc_root))
            observer = AUTH.LivePhaseObserver(
                pin=pin, phase="origin", challenges=challenges(),
                resource_limits=fixture_limits(100),
                fixture_monotonic_ns=100_000_000,
            )
            identity = observer.identity
            spliced = json.loads(receipt(
                "origin", identity, "READY", "b" * 32,
            ))
            spliced["challenge_value"] = "f" * 32
            with self.assertRaisesRegex(AUTH.AuthenticationError, "spliced"):
                observer.receive_event(
                    AUTH.canonical_json_bytes(spliced),
                    monotonic_ns=110_000_000,
                )
            observer.receive_event(
                receipt("origin", identity, "READY", "c" * 32),
                monotonic_ns=120_000_000,
            )
            with self.assertRaisesRegex(AUTH.AuthenticationError, "nonce was reused"):
                observer.receive_event(
                    receipt("origin", identity, "action", "c" * 32, 1),
                    monotonic_ns=125_000_000,
                )
            observer.receive_event(
                receipt("origin", identity, "action", "d" * 32, 1),
                monotonic_ns=130_000_000,
            )
            with self.assertRaisesRegex(AUTH.AuthenticationError, "after READY"):
                observer.end(monotonic_ns=140_000_000)
            pin.close()

    def test_cadence_gap_fails_live(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            proc_root = Path(raw)
            expected = make_fake_proc(proc_root)
            pin = AUTH.pin_live_process(expected, proc_root=str(proc_root))
            observer = AUTH.LivePhaseObserver(
                pin=pin, phase="pilot", challenges=challenges(),
                resource_limits=fixture_limits(10),
                fixture_monotonic_ns=100_000_000,
            )
            with self.assertRaisesRegex(AUTH.AuthenticationError, "cadence"):
                observer.sample(monotonic_ns=111_000_001)
            pin.close()


class PublicationTests(unittest.TestCase):
    def make_staging(self, root: Path, names: list[str]) -> list[dict[str, object]]:
        (root / "staging").mkdir(exist_ok=True)
        stage = root / "staging/checkpoint-e"
        stage.mkdir()
        images: list[dict[str, object]] = []
        for index, name in enumerate(names):
            target = stage / name
            target.write_bytes(f"image-{index}-{name}\n".encode())
            target.chmod(0o444)
            images.append({"path": name, "authority": AUTH.file_expectation(target)})
        stage.chmod(0o700)
        return images

    def test_no_replace_publish_ordered_restart_rehash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "checkpoints").mkdir()
            images = self.make_staging(root, ["z-image.dmtcp", "a-image.dmtcp"])
            with AUTH.AnchoredFilesystem(root) as filesystem:
                publication = AUTH.publish_checkpoint_no_replace(
                    filesystem=filesystem, staging_directory="staging/checkpoint-e",
                    publication_parent="checkpoints", images=images,
                    challenges=challenges(), resource_limits=fixture_limits(),
                )
                try:
                    direct_files = [{
                        "path": item["path"],
                        **{
                            field: item["authority"][field]
                            for field in ("bytes", "sha256", "md5")
                        },
                    } for item in images]
                    expected_manifest_sha256 = DIRECT.canonical_sha256(direct_files)
                    self.assertEqual(
                        publication.evidence["ordered_manifest_sha256"],
                        expected_manifest_sha256,
                    )
                    self.assertEqual(
                        publication.evidence["direct_protocol_image_files"],
                        direct_files,
                    )
                    self.assertEqual(
                        DIRECT._validate_atomic_checkpoint_publication(
                            publication.evidence[
                                "direct_protocol_atomic_publication"
                            ], expected_manifest_sha256,
                        )["published_path"],
                        f"checkpoints/{expected_manifest_sha256}",
                    )
                    self.assertEqual([
                        Path(item).name for item in
                        publication.evidence["ordered_restart_image_argv"]
                    ], ["z-image.dmtcp", "a-image.dmtcp"])
                    self.assertTrue(all(
                        item.startswith(f"checkpoints/{expected_manifest_sha256}/")
                        and not item.startswith("/")
                        for item in publication.evidence[
                            "ordered_restart_image_argv"
                        ]
                    ))
                    rehash = AUTH.rehash_checkpoint_for_restart(
                        publication, filesystem=filesystem,
                    )
                    self.assertFalse(rehash.nonfixture)
                    self.assertEqual(
                        rehash.evidence["ordered_restart_image_argv"],
                        publication.evidence["ordered_restart_image_argv"],
                    )

                    # Recreating identical staging content cannot replace an
                    # already content-addressed destination.
                    images_again = self.make_staging(
                        root, ["z-image.dmtcp", "a-image.dmtcp"],
                    )
                    with self.assertRaisesRegex(
                        AUTH.AuthenticationError, "no-replace",
                    ):
                        AUTH.publish_checkpoint_no_replace(
                            filesystem=filesystem, staging_directory="staging/checkpoint-e",
                            publication_parent="checkpoints", images=images_again,
                            challenges=challenges(), resource_limits=fixture_limits(),
                        )
                finally:
                    publication.close()

    def test_omitted_extra_hardlinked_and_renamed_images_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "checkpoints").mkdir()
            images = self.make_staging(root, ["one.dmtcp", "two.dmtcp"])
            with AUTH.AnchoredFilesystem(root) as filesystem:
                pft_images = copy.deepcopy(images)
                pft_images[0]["path"] = "PfT-image.dmtcp"
                with self.assertRaisesRegex(
                    AUTH.AuthenticationError, "PFT namespace",
                ):
                    AUTH.publish_checkpoint_no_replace(
                        filesystem=filesystem,
                        staging_directory="staging/checkpoint-e",
                        publication_parent="checkpoints", images=pft_images,
                        challenges=challenges(), resource_limits=fixture_limits(),
                    )
                with self.assertRaisesRegex(AUTH.AuthenticationError, "differs"):
                    AUTH.publish_checkpoint_no_replace(
                        filesystem=filesystem, staging_directory="staging/checkpoint-e",
                        publication_parent="checkpoints", images=images[:1],
                        challenges=challenges(), resource_limits=fixture_limits(),
                    )
                extra = root / "staging/checkpoint-e/extra.dmtcp"
                # Directory is sealed; the fixture owner may deliberately
                # unseal it to model a hostile producer before authentication.
                (root / "staging/checkpoint-e").chmod(0o755)
                extra.write_bytes(b"extra")
                extra.chmod(0o444)
                (root / "staging/checkpoint-e").chmod(0o700)
                with self.assertRaisesRegex(AUTH.AuthenticationError, "differs"):
                    AUTH.publish_checkpoint_no_replace(
                        filesystem=filesystem, staging_directory="staging/checkpoint-e",
                        publication_parent="checkpoints", images=images,
                        challenges=challenges(), resource_limits=fixture_limits(),
                    )
                (root / "staging/checkpoint-e").chmod(0o755)
                extra.unlink()
                (root / "staging/checkpoint-e").chmod(0o700)
                publication = AUTH.publish_checkpoint_no_replace(
                    filesystem=filesystem, staging_directory="staging/checkpoint-e",
                    publication_parent="checkpoints", images=images,
                    challenges=challenges(), resource_limits=fixture_limits(),
                )
                try:
                    directory = Path(publication.evidence["published_directory"])
                    os.link(directory / "one.dmtcp", root / "hostile-hardlink")
                    with self.assertRaisesRegex(AUTH.AuthenticationError, "linked"):
                        AUTH.rehash_checkpoint_for_restart(
                            publication, filesystem=filesystem,
                        )
                    (root / "hostile-hardlink").unlink()
                    moved = root / "checkpoints/moved"
                    directory.rename(moved)
                    with self.assertRaises(AUTH.AuthenticationError):
                        AUTH.rehash_checkpoint_for_restart(
                            publication, filesystem=filesystem,
                        )
                finally:
                    publication.close()

    def test_symlink_replacement_after_publish_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "checkpoints").mkdir()
            images = self.make_staging(root, ["only.dmtcp"])
            with AUTH.AnchoredFilesystem(root) as filesystem:
                publication = AUTH.publish_checkpoint_no_replace(
                    filesystem=filesystem, staging_directory="staging/checkpoint-e",
                    publication_parent="checkpoints", images=images,
                    challenges=challenges(), resource_limits=fixture_limits(),
                )
                try:
                    directory = Path(publication.evidence["published_directory"])
                    replacement = root / "replacement.dmtcp"
                    replacement.write_bytes(b"image-0-only.dmtcp\n")
                    replacement.chmod(0o444)
                    directory.chmod(0o755)
                    (directory / "only.dmtcp").unlink()
                    os.symlink(replacement, directory / "only.dmtcp")
                    with self.assertRaises(AUTH.AuthenticationError):
                        AUTH.rehash_checkpoint_for_restart(
                            publication, filesystem=filesystem,
                        )
                finally:
                    publication.close()


class LifecycleTests(unittest.TestCase):
    def make_publication(self, root: Path) -> tuple[AUTH.AnchoredFilesystem,
                                                    AUTH.PublicationPin]:
        (root / "checkpoints").mkdir()
        (root / "staging").mkdir()
        stage = root / "staging/checkpoint-e"
        stage.mkdir()
        images: list[dict[str, object]] = []
        for index, name in enumerate(("first.dmtcp", "second.dmtcp")):
            target = stage / name
            target.write_bytes(f"checkpoint-{index}\n".encode())
            target.chmod(0o444)
            images.append({"path": name, "authority": AUTH.file_expectation(target)})
        stage.chmod(0o700)
        filesystem = AUTH.AnchoredFilesystem(root)
        publication = AUTH.publish_checkpoint_no_replace(
            filesystem=filesystem, staging_directory="staging/checkpoint-e",
            publication_parent="checkpoints", images=images,
            challenges=challenges(), resource_limits=fixture_limits(),
        )
        return filesystem, publication

    def test_restart_exact_order_omission_extra_and_resumed_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            filesystem, publication = self.make_publication(root)
            proc_root = root / "proc"
            proc_root.mkdir()
            base = make_fake_proc(proc_root)
            environment = {
                "CANDLE_CHECKPOINT_CHALLENGE_ID": "1" * 64,
                "CANDLE_RESUME_NONCE": "5" * 32,
                "CANDLE_RESUME_TOKEN": "6" * 64,
                "CANDLE_CHECKPOINT_PUBLICATION_DIGEST":
                    publication.evidence["ordered_manifest_sha256"],
            }
            expected_argv = [
                AUTH.DMTCP_ROLE_PATHS["restart"], "--join-coordinator",
                "--coord-port", "42424",
                *publication.evidence["ordered_restart_image_argv"],
            ]
            port = AUTH._make_observation("coordinator-port", {
                "process_identity": {
                    "pid": 111, "process_group_id": 111, "start_ticks": 222,
                },
                "port": 42424,
                "socket_inode": "999",
            }, False)
            environments = AUTH._make_observation(
                "challenged-environments", {"combined": environment}, False,
            )
            try:
                for hostile_argv in (
                    expected_argv[:-2] + list(reversed(expected_argv[-2:])),
                    expected_argv[:-1],
                    expected_argv + ["/tmp/extra.dmtcp"],
                ):
                    hostile = copy.deepcopy(base)
                    hostile["executable"] = AUTH.DMTCP_ROLE_PATHS["restart"]
                    hostile["argv"] = hostile_argv
                    hostile["environment"] = environment
                    rewrite_fake_process(proc_root, hostile)
                    pin = AUTH.pin_live_process(hostile, proc_root=str(proc_root))
                    with self.assertRaisesRegex(
                        AUTH.AuthenticationError, "ordered positional",
                    ):
                        AUTH.RestartObserver(
                            launcher_pin=pin, publication=publication,
                            filesystem=filesystem, coordinator_port=port,
                            challenges=challenges(), environments=environments,
                        )
                    pin.close()

                exact = copy.deepcopy(base)
                exact["executable"] = AUTH.DMTCP_ROLE_PATHS["restart"]
                exact["argv"] = expected_argv
                exact["environment"] = environment
                rewrite_fake_process(proc_root, exact)
                pin = AUTH.pin_live_process(exact, proc_root=str(proc_root))
                observer = AUTH.RestartObserver(
                    launcher_pin=pin, publication=publication,
                    filesystem=filesystem, coordinator_port=port,
                    challenges=challenges(), environments=environments,
                )
                shutil.rmtree(proc_root / str(exact["pid"]))
                completed = AUTH.complete_parent_owned_process(
                    pin, allowed_exit_codes=(0,), fixture_completion={
                        "kind": "exit", "value": 0, "proc_absent": True,
                    },
                )
                resumed_process = copy.deepcopy(exact)
                resumed_process.update({
                    "pid": 5001, "process_group_id": 5001,
                    "start_ticks": 500100, "parent_pid": 1,
                })
                resume = AUTH._make_observation("phase", {
                    "phase": "resume", "challenge_name": "resume_nonce",
                    "challenge_value": "5" * 32,
                    "controller": {"process": resumed_process},
                    "receipt_observation_scope":
                        "controller-supplied-bytes-received-and-timestamped-by-parent",
                }, False)
                result = observer.finish(
                    completed_launcher=completed, resumed_phase=resume,
                )
                self.assertFalse(result.nonfixture)
                self.assertEqual(
                    result.evidence["ordered_restart_image_argv"],
                    publication.evidence["ordered_restart_image_argv"],
                )
            finally:
                publication.close()
                filesystem.close()

    def test_killed_tree_omission_and_non_kill_fail(self) -> None:
        identities = [
            {"pid": 10, "process_group_id": 10, "start_ticks": 100},
            {"pid": 11, "process_group_id": 10, "start_ticks": 101},
        ]

        def completed(pid: int, parent: int, *, killed: bool = True) -> object:
            identity = next(item for item in identities if item["pid"] == pid)
            return AUTH._make_observation("completed-process", {
                "process": {
                    **identity, "parent_pid": parent, "state": "S",
                    "executable": "/controller", "argv": ["/controller"],
                    "environment": {}, "vdso_sha256": "a" * 64,
                    "kernel": {},
                },
                "termination": ({"kind": "signal", "value": int(signal.SIGKILL)}
                                if killed else {"kind": "exit", "value": 0}),
                "reaped": True, "proc_absent_after_reap": True,
            }, False)

        tokens = [completed(10, 1), completed(11, 10)]
        tree = AUTH.authenticate_killed_process_tree(
            expected_identities=identities, completed_processes=tokens,
        )
        self.assertFalse(tree.nonfixture)
        with self.assertRaisesRegex(AUTH.AuthenticationError, "omitted"):
            AUTH.authenticate_killed_process_tree(
                expected_identities=identities, completed_processes=tokens[:1],
            )
        with self.assertRaisesRegex(AUTH.AuthenticationError, "not killed"):
            AUTH.authenticate_killed_process_tree(
                expected_identities=identities,
                completed_processes=[tokens[0], completed(11, 10, killed=False)],
            )

    def test_final_candidate_is_ordered_distinct_and_never_qualifies(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            filesystem, publication = self.make_publication(root)
            # White-box only: exercise the final candidate contract with a
            # temporary anchored publication while every trust flag remains false.
            publication.nonfixture = True
            identities = {
                name: {
                    "pid": 6000 + index,
                    "process_group_id": 7000 + index,
                    "start_ticks": 8000 + index,
                } for index, name in enumerate(AUTH.PHASES)
            }
            kernel_evidence = {
                "release": "test-kernel", "machine": "x86_64",
                "boot_id": "12345678-1234-1234-1234-123456789abc",
            }
            vdso_sha256 = "b" * 64
            runtime_environment = {"LC_ALL": "C", "PATH": "/usr/bin:/bin"}
            checkpoint_environment = {"LD_PRELOAD": "/trusted/libdmtcp.so"}
            combined_environment = {
                **runtime_environment, **checkpoint_environment,
            }
            raw_directory = root / "raw-phase-evidence"
            raw_directory.mkdir()
            phase_files: dict[str, tuple[dict[str, object], dict[str, object]]] = {}
            with AUTH.AnchoredFilesystem("/") as root_filesystem:
                for name in AUTH.PHASES:
                    observed: list[dict[str, object]] = []
                    for suffix in ("cadence", "events"):
                        target = raw_directory / f"{name}-{suffix}.json"
                        target.write_bytes(f"{name}-{suffix}\n".encode())
                        target.chmod(0o444)
                        relative = str(target).removeprefix("/")
                        observed.append(root_filesystem.authenticate_file(
                            relative, AUTH.file_expectation(target), immutable=True,
                        ))
                    phase_files[name] = (observed[0], observed[1])

            def phase(name: str) -> object:
                phase_index = AUTH.PHASES.index(name)
                challenge_name, challenge_value = AUTH.phase_challenge(
                    challenges(), name,
                )
                process = {
                    **identities[name],
                    "environment": (runtime_environment if name in {
                        "pilot", "clean-1", "clean-2",
                    } else combined_environment),
                    "vdso_sha256": vdso_sha256,
                    "kernel": kernel_evidence,
                    "executable": f"/usr/bin/controller-{name}",
                }
                return AUTH._make_observation("phase", {
                    "phase": name,
                    "challenge_id": "1" * 64,
                    "challenge_name": challenge_name,
                    "challenge_value": challenge_value,
                    "controller": {"process": process},
                    "resource_limits": limit_values(),
                    "receipt_observation_scope":
                        "controller-supplied-bytes-received-and-timestamped-by-parent",
                    "post_ready_action_receipt_count": 0,
                    "begin_monotonic_ns": 1000 + phase_index * 100,
                    "end_monotonic_ns": 1050 + phase_index * 100,
                    "event_nonces": [f"{phase_index + 1:x}" * 32],
                    "exec_gate": {"released": True},
                    "filesystem_root": "/",
                    "cadence_file": phase_files[name][0],
                    "event_file": phase_files[name][1],
                }, True)

            phase_tokens = [phase(name) for name in AUTH.PHASES]
            coordinator_identity = {
                "pid": 9001, "process_group_id": 9001, "start_ticks": 900100,
            }
            coordinator = AUTH._make_observation("coordinator-lifecycle", {
                "process": {
                    **coordinator_identity, "environment": combined_environment,
                    "vdso_sha256": vdso_sha256, "kernel": kernel_evidence,
                    "executable": AUTH.DMTCP_ROLE_PATHS["coordinator"],
                    "executable_device": 10, "executable_inode": 20,
                },
                "port": 42424,
                "exec_gate": {"released": True},
            }, True)
            tree = AUTH._make_observation("killed-process-tree", {
                "root_identity": identities["origin"],
            }, True)
            restart = AUTH._make_observation("restart-lifecycle", {
                "restarted_controller": {
                    **identities["resume"], "environment": combined_environment,
                    "vdso_sha256": vdso_sha256, "kernel": kernel_evidence,
                },
                "ordered_manifest_sha256": publication.evidence["ordered_manifest_sha256"],
                "ordered_restart_image_argv": publication.evidence[
                    "ordered_restart_image_argv"
                ],
                "coordinator_port": 42424,
                "exec_gate": {"released": True},
                "launcher": {"process": {
                    "environment": combined_environment,
                    "vdso_sha256": vdso_sha256, "kernel": kernel_evidence,
                    "executable": AUTH.DMTCP_ROLE_PATHS["restart"],
                    "executable_device": 11, "executable_inode": 21,
                }},
            }, True)
            with AUTH.AnchoredFilesystem(
                publication.filesystem_root
            ) as root_filesystem:
                restart.evidence["post_restart_images"] = (
                    AUTH.rehash_checkpoint_for_restart(
                        publication, filesystem=root_filesystem,
                    ).evidence["images"]
                )
            dmtcp = AUTH._make_observation("bound-dmtcp-authority", {
                "version": "4.1.0", "vdso_sha256": vdso_sha256,
                "kernel": kernel_evidence,
                "executables": [
                    {"role": "coordinator", "device": 10, "inode": 20,
                     "path": AUTH.DMTCP_ROLE_PATHS["coordinator"]},
                    {"role": "restart", "device": 11, "inode": 21,
                     "path": AUTH.DMTCP_ROLE_PATHS["restart"]},
                ],
                "injected_libraries": [], "elf_closure": [],
            }, True)
            environments = AUTH._make_observation("challenged-environments", {
                "runtime": runtime_environment,
                "checkpoint": checkpoint_environment,
                "combined": combined_environment,
            }, True)
            resource_limits = AUTH._make_observation(
                "resource-limits", limit_values(), True,
            )
            kernel = AUTH._make_observation("kernel", kernel_evidence, True)
            try:
                with self.assertRaisesRegex(AUTH.AuthenticationError, "omits"):
                    AUTH.assemble_unapproved_candidate(
                        challenges=challenges(), dmtcp_authority=dmtcp,
                        environments=environments, kernel=kernel,
                        resource_limits=resource_limits,
                        phases=phase_tokens[:-1],
                        coordinator=coordinator, origin_process_tree=tree,
                        publication=publication, restart=restart,
                    )
                duplicate = copy.deepcopy(identities["origin"])
                bad_clean = AUTH._make_observation("phase", {
                    **phase("clean-1").evidence,
                    "controller": {"process": {
                        **duplicate, "environment": runtime_environment,
                        "vdso_sha256": vdso_sha256, "kernel": kernel_evidence,
                    }},
                }, True)
                spliced = phase_tokens[:]
                spliced[3] = bad_clean
                with self.assertRaisesRegex(AUTH.AuthenticationError, "reuse"):
                    AUTH.assemble_unapproved_candidate(
                        challenges=challenges(), dmtcp_authority=dmtcp,
                        environments=environments, kernel=kernel,
                        resource_limits=resource_limits,
                        phases=spliced, coordinator=coordinator,
                        origin_process_tree=tree, publication=publication,
                        restart=restart,
                    )
                nonce_collision = AUTH._make_observation("phase", {
                    **phase_tokens[3].evidence,
                    "event_nonces": phase_tokens[1].evidence["event_nonces"],
                }, True)
                spliced = phase_tokens[:]
                spliced[3] = nonce_collision
                with self.assertRaisesRegex(AUTH.AuthenticationError, "spliced"):
                    AUTH.assemble_unapproved_candidate(
                        challenges=challenges(), dmtcp_authority=dmtcp,
                        environments=environments, kernel=kernel,
                        resource_limits=resource_limits, phases=spliced,
                        coordinator=coordinator, origin_process_tree=tree,
                        publication=publication, restart=restart,
                    )
                overlap = AUTH._make_observation("phase", {
                    **phase_tokens[3].evidence,
                    "begin_monotonic_ns":
                        phase_tokens[2].evidence["end_monotonic_ns"],
                }, True)
                spliced[3] = overlap
                with self.assertRaisesRegex(AUTH.AuthenticationError, "spliced"):
                    AUTH.assemble_unapproved_candidate(
                        challenges=challenges(), dmtcp_authority=dmtcp,
                        environments=environments, kernel=kernel,
                        resource_limits=resource_limits, phases=spliced,
                        coordinator=coordinator, origin_process_tree=tree,
                        publication=publication, restart=restart,
                    )
                evidence = AUTH.assemble_unapproved_candidate(
                    challenges=challenges(), dmtcp_authority=dmtcp,
                    environments=environments, kernel=kernel,
                    resource_limits=resource_limits,
                    phases=phase_tokens,
                    coordinator=coordinator, origin_process_tree=tree,
                    publication=publication, restart=restart,
                )
                for field in (
                    "lifecycle_complete", "os_evidence_authenticated",
                    "runtime_qualified", "checkpoint_protocol_qualified",
                    "s2_approved", "s3_approved", "release_promoted", "pft_used",
                ):
                    self.assertFalse(evidence[field], field)
                self.assertEqual(
                    AUTH.decode_unapproved_candidate(
                        AUTH.canonical_json_bytes(evidence)
                    ), evidence,
                )
                for field in (
                    "os_evidence_authenticated", "runtime_qualified", "pft_used",
                ):
                    forged = copy.deepcopy(evidence)
                    forged[field] = True
                    payload = copy.deepcopy(forged)
                    del payload["candidate_payload_sha256"]
                    forged["candidate_payload_sha256"] = AUTH.canonical_sha256(payload)
                    with self.assertRaisesRegex(
                        AUTH.AuthenticationError, "overclaims",
                    ):
                        AUTH.validate_unapproved_candidate(forged)
                forged_path = copy.deepcopy(evidence)
                forged_path["checkpoint_publication"][
                    "direct_protocol_image_files"
                ][0]["path"] = "PfT-image.dmtcp"
                payload = copy.deepcopy(forged_path)
                del payload["candidate_payload_sha256"]
                forged_path["candidate_payload_sha256"] = (
                    AUTH.canonical_sha256(payload)
                )
                with self.assertRaisesRegex(
                    AUTH.AuthenticationError, "PFT namespace",
                ):
                    AUTH.validate_unapproved_candidate(forged_path)
                coherently_forged_path = copy.deepcopy(evidence)
                forged_publication = coherently_forged_path[
                    "checkpoint_publication"
                ]
                forged_publication["direct_protocol_image_files"][0][
                    "path"
                ] = "PfT-image.dmtcp"
                forged_publication["ordered_images"][0]["path"] = (
                    "PfT-image.dmtcp"
                )
                forged_manifest = AUTH.direct_ordered_manifest_sha256(
                    forged_publication["direct_protocol_image_files"]
                )
                forged_directory = f"checkpoints/{forged_manifest}"
                forged_publication["ordered_manifest_sha256"] = forged_manifest
                forged_publication["published_directory"] = f"/{forged_directory}"
                forged_publication["published_relative_directory"] = (
                    forged_directory
                )
                forged_publication["direct_protocol_atomic_publication"][
                    "published_path"
                ] = forged_directory
                coherently_forged_path["restart"][
                    "ordered_restart_image_argv"
                ] = [
                    f"{forged_directory}/{item['path']}" for item in
                    forged_publication["direct_protocol_image_files"]
                ]
                payload = copy.deepcopy(coherently_forged_path)
                del payload["candidate_payload_sha256"]
                coherently_forged_path["candidate_payload_sha256"] = (
                    AUTH.canonical_sha256(payload)
                )
                with self.assertRaisesRegex(
                    AUTH.AuthenticationError, "PFT namespace",
                ):
                    AUTH.validate_unapproved_candidate(coherently_forged_path)
                prior = phase_tokens[0].evidence["event_file"]
                target = Path("/") / prior["path"]
                original = target.read_bytes()
                target.unlink()
                target.write_bytes(original)
                target.chmod(0o444)
                with self.assertRaisesRegex(
                    AUTH.AuthenticationError, "changed before final",
                ):
                    AUTH.assemble_unapproved_candidate(
                        challenges=challenges(), dmtcp_authority=dmtcp,
                        environments=environments, resource_limits=resource_limits,
                        kernel=kernel, phases=phase_tokens,
                        coordinator=coordinator, origin_process_tree=tree,
                        publication=publication, restart=restart,
                    )
            finally:
                publication.close()
                filesystem.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
