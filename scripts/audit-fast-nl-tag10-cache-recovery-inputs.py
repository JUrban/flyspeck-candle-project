#!/usr/bin/env python3
"""Authenticate the exact donors for the three damaged generated theories."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


INTEGRATION = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1"
)
COMPUTE = INTEGRATION / "candle/prover/compute"
OBJECTS = COMPUTE / ".hol/objs"
SCRATCH = COMPUTE / "tag10_probe_scratch"
SCRATCH_OBJECTS = SCRATCH / ".hol/objs"
BASE_DONOR = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-tag10-v1"
)
BASE_OBJECTS = BASE_DONOR / "candle/prover/compute/.hol/objs"
INTEGRATION_HEAD = "839017e696dea5fbbb2e03bfeff02c6679724e00"
BASE_HEAD = "b3fb54e9f822fd462b929843e816d1fa1dd46cfd"
MISSING_SUFFIXES = ("sml", "sig", "dat", "cachekey")

THEORIES = {
    "compute_evalPure": {
        "source": "compute_evalPureScript.sml",
        "source_sha256":
            "fb4a042e882da76bd73b6f406cb332758a02f5e2216f532b2596bc1125cd77b9",
        "donor_objects": BASE_OBJECTS,
        "artifact_sha256": {
            "sml": "22a74feab5709fc6795fc48ce4a5b11080724f10acbbcd1170b9df886ec1f850",
            "sig": "0b64ebe375cd2cc44aaa660cda9bf74e6f803efa1c655eb6262b5abaa0b8b5f1",
            "dat": "720cfe735e429a4566b213f67e0bc99bb4706735ac5917c359368d53362dd711",
            "cachekey": "4c59c32a9f3014ce6e1edee0269b899fe25a68964386427558153c6704c18e6b",
        },
        "retained_sha256": {
            "ui": "600f0bc8e2a1a5b084ef6b6dc938b268feaea91265f6b9fd3da4a8086acb5901",
            "uo": "3a677122a540c04ce11ed7c386d1b51d7a1f91fd70589af5b642ddc255b76320",
        },
    },
    "compute_registeredCase10173Tag10HistItemCongruence": {
        "source": "compute_registeredCase10173Tag10HistItemCongruenceScript.sml",
        "source_sha256":
            "1f36ce9900b9d7694ea977eaf05258c328ed0e747bb8c77ff10354a681cd5417",
        "donor_objects": SCRATCH_OBJECTS,
        "artifact_sha256": {
            "sml": "a10b57a9a751be61ca1a68fea3b7563d7bbc4dc12224a8f53e72641c37a9b27d",
            "sig": "26909a1fa948a716114b9c22833524d897b639baf0fe40396597e2fb7a05c9fe",
            "dat": "302946b0aa46c438583b365270ddbef46cfd6d7b6612a396ca45d5707dab8f5a",
            "cachekey": "66ab7969ee38dd259938033a881615db0e7db3618990d7244d2831c5284c41df",
        },
        "retained_sha256": {
            "ui": "0d4e4474b62cb10de7916859490c9d45aa7a160f6bdada609c1dd414cccded56",
            "uo": "cfb806498f316124dad11ceaa99ec6f74d75cb00700cc8effa1dc3d3d1e8cab0",
        },
    },
    "compute_registeredCase10173Tag10OrdinaryReachable": {
        "source": "compute_registeredCase10173Tag10OrdinaryReachableScript.sml",
        "source_sha256":
            "1a0bc5734ca415c19f830bc0aa5ba69933239296045622db9a1c88f55397a078",
        "donor_objects": SCRATCH_OBJECTS,
        "artifact_sha256": {
            "sml": "3569b7d30b1bee5881d54aa16755369d8fe350ef56e444e7af6b0833313355a9",
            "sig": "cf1657190a9bf4316253e02ed89c95a8f11623e16f7a6202f1b7109cfd370f94",
            "dat": "c5e8980f56f75a373ab7001b5b87d1e85b161946c9ef8b609f3241bf56e533df",
            "cachekey": "802b8d9c1af582cb8947b1418b8118d946b495a7757d6f4a0263fb3bff12afd0",
        },
        "retained_sha256": {
            "ui": "a8b1bfde8ef90949e9f5a0d5384592a43ec08dd504bcf433bf784be0bad913ca",
            "uo": "1b6bf958d4a5cd5d29ca6c43ca53bd22951d13ee47d0c5a3a5c5f51a464d5982",
        },
    },
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def head(worktree: pathlib.Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> int:
    if head(INTEGRATION) != INTEGRATION_HEAD or head(BASE_DONOR) != BASE_HEAD:
        return fail("repository_head")
    if subprocess.check_output(
        ["git", "-C", str(INTEGRATION), "status", "--porcelain",
         "--untracked-files=no"], text=True
    ):
        return fail("integration_tracked_dirty")

    for theory, contract in THEORIES.items():
        source = COMPUTE / str(contract["source"])
        donor_source = (
            BASE_DONOR / "candle/prover/compute" / str(contract["source"])
            if contract["donor_objects"] == BASE_OBJECTS
            else SCRATCH / str(contract["source"])
        )
        expected_source = str(contract["source_sha256"])
        if sha256(source) != expected_source or sha256(donor_source) != expected_source:
            return fail(f"source_identity:{theory}")

        for suffix in MISSING_SUFFIXES:
            target = OBJECTS / f"{theory}Theory.{suffix}"
            if target.exists():
                return fail(f"damaged_target_not_missing:{theory}:{suffix}")
            donor = pathlib.Path(contract["donor_objects"]) / f"{theory}Theory.{suffix}"
            expected = contract["artifact_sha256"][suffix]
            if not donor.is_file() or donor.is_symlink() or sha256(donor) != expected:
                return fail(f"donor_identity:{theory}:{suffix}")

        for suffix, expected in contract["retained_sha256"].items():
            retained = OBJECTS / f"{theory}Theory.{suffix}"
            if not retained.is_file() or retained.is_symlink():
                return fail(f"retained_artifact_missing:{theory}:{suffix}")
            if sha256(retained) != expected:
                return fail(f"retained_artifact_identity:{theory}:{suffix}")

    base_log = BASE_DONOR / "candle/prover/compute/.hol/logs/compute_evalPureTheory"
    base_text = base_log.read_text(encoding="utf-8", errors="replace")
    for marker in (
        'Exporting theory "compute_evalPure" ... done.',
        'Theory "compute_evalPure" took 31.3s to build',
    ):
        if marker not in base_text:
            return fail(f"base_donor_log:{marker}")

    hist_log = SCRATCH / "tag10-hist-item-congruence-build-v3.log"
    hist_text = hist_log.read_text(encoding="utf-8", errors="replace")
    for marker in (
        'Exporting theory "compute_registeredCase10173Tag10HistItemCongruence" ... done.',
        "Holmake: [1/1] compute_registeredCase10173Tag10HistItemCongruence",
    ):
        if marker not in hist_text:
            return fail(f"hist_item_donor_log:{marker}")

    ordinary_log = SCRATCH / "tag10-cache-normalization-build-v1.log"
    ordinary_text = ordinary_log.read_text(encoding="utf-8", errors="replace")
    for marker in (
        'Exporting theory "compute_registeredCase10173Tag10OrdinaryReachable" ... done.',
        "Holmake: [3/20] compute_registeredCase10173Tag10OrdinaryReachable",
    ):
        if marker not in ordinary_text:
            return fail(f"ordinary_donor_log:{marker}")

    print("status=0")
    print(f"integration_head={INTEGRATION_HEAD}")
    print(f"base_donor_head={BASE_HEAD}")
    print("damaged_theory_count=3")
    print("missing_artifact_count=12")
    print("retained_manifest_count=6")
    print("donor_export_log_count=3")
    print("source_identity_match=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
