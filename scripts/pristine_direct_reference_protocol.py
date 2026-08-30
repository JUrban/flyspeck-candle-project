#!/usr/bin/python3
"""Strict pure protocol for raw pristine direct-reference evidence.

This module validates retained JSON values and their content bindings.  It does
not inspect a filesystem, run HOL Light, authenticate a process, mint a
comparison descriptor, approve S2/S3, or authorize release.  A future producer
must rederive these values from immutable request and transcript bytes before
calling this protocol.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
import struct
from types import ModuleType
from typing import Any, Callable


FINAL_BOUNDARY_ID = "07-final_assembly-through-296"
FINAL_ACTION_COUNT = 297
RAW_PROTOCOL_SCHEMA = 3
REFERENCE_ROLE = "pristine-clean-reference"
REFERENCE_ORDINALS = (1, 2)
REFERENCE_NONCE_KIND = "reference-session-nonce-v1"
PLAN_KIND = "candle-flyspeck-pristine-direct-reference-raw-plan-v3"
REQUEST_KIND = "candle-flyspeck-pristine-direct-reference-request-v3"
TRANSCRIPT_KIND = "candle-flyspeck-pristine-direct-reference-transcript-v3"
NATIVE_CLOSURE_KIND = (
    "candle-flyspeck-pristine-direct-native-execution-closure-v3"
)
RAW_CANDIDATE_KIND = (
    "candle-flyspeck-pristine-direct-reference-raw-candidate-v3"
)
SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-raw-source-rederivation-v3"
)
INCOMPLETE_SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-incomplete-source-rederivation-"
    "diagnostic-v3"
)
SEMANTIC_COMPLETION_KIND = (
    "candle-flyspeck-pristine-direct-semantic-completion-observation-v1"
)
SEMANTIC_COMPLETE_STATUS = "complete-observed-unapproved"
COVERAGE_INCOMPLETE_STATUS = (
    "not-derived-requires-authenticated-inventory-and-generated-inputs"
)
FINAL_THEOREM_NAMES = (
    "Linear_programming_results.linear_programming_results_th",
    "Mk_all_ineq.the_nonlinear_inequalities",
    "The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture",
    "Candle_flyspeck_l2.tame_imp_kepler_conjecture",
)
AUTHORITY_POLICY = (
    "exact-clean-project-hol-light-flyspeck-runtime-tool-and-input-authority-v3"
)
ACTION_POLICY = "authenticated-original-build-sequence-full-v1"
EXECUTION_SELECTION_SEMANTICS = (
    "bind-candle-plan-selection-without-pristine-overlay-execution-claim-v1"
)
LP_INPUT_KIND = "candle-flyspeck-pristine-direct-lp-input-inventory-v1"
LP_SUCCESS_KIND = "candle-flyspeck-pristine-direct-lp-success-stream-v1"
LP_ORDER = "raw-success-marker-order-v1"
LOADER_LEDGER_POLICY = (
    "stock-hol-light-loaded-files-success-ledger-canonical-source-map-v1"
)
LOADER_LEDGER_ORDER = (
    "per-phase-new-loaded-files-delta-reversed-to-success-order-v1"
)
MARKER_PROTOCOL = "candle-flyspeck-pristine-direct-reference-markers-v3"
ENVIRONMENT_POLICY = (
    "fresh-sanitized-single-thread-reference-process-serialization-key-absent-v1"
)
SERIALIZATION_ENVIRONMENT_KEY = "FLYSPECK_SERIALIZATION"
RETAINED_STDOUT_MAX_BYTES = 536870912
RETAINED_STDERR_MAX_BYTES = 0
EMPTY_BYTES_SHA256 = hashlib.sha256(b"").hexdigest()
JSON_INTEGER_MAX_DIGITS = 20
PRODUCER_ENTRYPOINT_PATH = "scripts/collect-pristine-direct-reference.py"
PROTOCOL_PATH = "scripts/pristine_direct_reference_protocol.py"
OUTPUT_PARSER_PATH = "scripts/parse-pristine-direct-reference-output.py"
DIRECT_PROTOCOL_PATH = "scripts/direct_release_protocol.py"
LP_WRAPPER_AFTER_ACTION_INDEX = 177
LP_VERIFY_ACTION_INDEX = 183
LP_CONSUMER_ACTION_INDEX = 184
LP_CERTIFICATE_SOURCE = "flyspeck:formal_lp/hypermap/main/lp_certificate.hl"
LP_VERIFY_SOURCE = "flyspeck:formal_lp/hypermap/verify_all.hl"
LP_CONSUMER_SOURCE = (
    "flyspeck:text_formalization/tame/linear_programming_results.hl"
)
FINAL_TARGET_SOURCE = "candle:candle/flyspeck_l2_target.ml"
SERIALIZER_SOURCE = "candle:candle/fingerprint.ml"
STRICTBUILD_SOURCE = "flyspeck:text_formalization/build/strictbuild.hl"
HOL_LIGHT_SOURCE = "candle:hol.ml"
ACTION_STRATA = (
    "base", "arithmetic", "analysis", "geometry", "lp_support",
    "nonlinear_support", "text_formalization", "final_assembly",
)
CANDLE_ONLY_REFERENCE_EXCLUSIONS = (
    "candle:candle/flyspeck_full_build.ml",
    "candle:candle/build/insulate.ml",
    "candle:candle/flyspeck_source_digests.ml",
    "candle:candle/flyspeck_source_integrity.ml",
)
ENTRYPOINT_SEQUENCE = (
    {
        "index": 0,
        "operation": "start-pristine-hol-light",
        "source": HOL_LIGHT_SOURCE,
    },
    {
        "index": 1,
        "operation": "install-native-loader-ledger-observer",
        "source": "request-local-instrumentation",
    },
    {
        "index": 2,
        "operation": "load-original-strictbuild",
        "source": STRICTBUILD_SOURCE,
    },
    {
        "index": 3,
        "operation": "execute-original-build-sequence",
        "function": "Build.build_sequence_full",
        "loader": "flyspeck_needs",
        "first_action_index": 0,
        "last_action_index": LP_WRAPPER_AFTER_ACTION_INDEX,
    },
    {
        "index": 4,
        "operation": "install-lp-success-wrapper",
        "wrapped_function": "Lp_certificate.read_lp_certificates",
        "after_action_index": LP_WRAPPER_AFTER_ACTION_INDEX,
        "before_action_index": LP_WRAPPER_AFTER_ACTION_INDEX + 1,
        "emit_only_after_success": True,
    },
    {
        "index": 5,
        "operation": "continue-original-build-sequence",
        "function": "Build.build_sequence_full",
        "loader": "flyspeck_needs",
        "first_action_index": LP_WRAPPER_AFTER_ACTION_INDEX + 1,
        "last_action_index": FINAL_ACTION_COUNT - 1,
    },
    {
        "index": 6,
        "operation": "load-final-target",
        "source": FINAL_TARGET_SOURCE,
    },
    {
        "index": 7,
        "operation": "emit-semantic-and-dependency-observations",
        "source": SERIALIZER_SOURCE,
    },
    {
        "index": 8,
        "operation": "emit-native-closure-and-complete",
    },
)
MARKER_CONTRACT = {
    "protocol": MARKER_PROTOCOL,
    "session_start": "CANDLE_PRISTINE_DIRECT_REFERENCE_START_V3",
    "native_load": "CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V3",
    "action_complete": "CANDLE_PRISTINE_DIRECT_ACTION_COMPLETE_V3",
    "lp_success": "CANDLE_PRISTINE_DIRECT_LP_SUCCESS_V3",
    "semantic_observation": "CANDLE_PRISTINE_DIRECT_SEMANTIC_V3",
    "session_complete": "CANDLE_PRISTINE_DIRECT_REFERENCE_COMPLETE_V3",
    "nonce_in_every_marker": True,
}

# Reserved disjoint V4 identities.  The currently available V3 diagnostic
# producer/parser remains separate until the V4 fixed loaders, collector and
# descriptor-rooted postflight exist.  In particular, none of these constants
# causes a V3 value to be relabelled or enables a V4 promotion-bearing value.
V4_RAW_PROTOCOL_SCHEMA = 4
V4_PLAN_KIND = "candle-flyspeck-pristine-direct-reference-raw-plan-v4"
V4_REQUEST_KIND = "candle-flyspeck-pristine-direct-reference-request-v4"
V4_TRANSCRIPT_KIND = (
    "candle-flyspeck-pristine-direct-reference-transcript-v4"
)
V4_NATIVE_CLOSURE_KIND = (
    "candle-flyspeck-pristine-direct-native-execution-closure-v4"
)
V4_SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-raw-source-rederivation-v4"
)
V4_INCOMPLETE_SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-incomplete-source-rederivation-"
    "diagnostic-v4"
)
V4_RAW_CANDIDATE_KIND = (
    "candle-flyspeck-pristine-direct-reference-raw-candidate-v4"
)
V4_MARKER_PROTOCOL = "candle-flyspeck-pristine-direct-reference-markers-v4"
V4_SEMANTIC_COMPLETION_SCHEMA = 2
V4_SEMANTIC_COMPLETION_KIND = (
    "candle-flyspeck-pristine-direct-semantic-completion-observation-v2"
)
V4_CAPTURE_ENVELOPE_SCHEMA = 2
V4_CAPTURE_ENVELOPE_KIND = (
    "candle-flyspeck-pristine-direct-capture-envelope-v2"
)
V4_PENDING_CANDIDATE_SCHEMA = 2
V4_PENDING_CANDIDATE_KIND = (
    "candle-flyspeck-pristine-direct-pending-candidate-v2"
)
V4_CAPTURE_COMPLETION_SCHEMA = 2
V4_CAPTURE_COMPLETION_KIND = (
    "candle-flyspeck-pristine-direct-capture-completion-v2"
)
V4_BUNDLE_SCHEMA = 4
V4_BUNDLE_KIND = "candle-flyspeck-pristine-direct-reference-bundle-v4"
V4_PAIR_SCHEMA = 4
V4_PAIR_KIND = "candle-flyspeck-pristine-direct-reference-pair-v4"
V4_AUTHORITY_POLICY = (
    "exact-clean-project-hol-light-flyspeck-runtime-tool-input-and-capture-"
    "authority-v4"
)
V4_KERNEL_PROFILE_SCHEMA = 2
V4_KERNEL_PROFILE_KIND = "candle-flyspeck-current-kernel-profile-v2"
V4_PREFLIGHT_SCHEMA = 2
V4_PREFLIGHT_KIND = (
    "candle-flyspeck-current-host-seccomp-preflight-v2"
)
V4_POSTFLIGHT_RESULT_SCHEMA = 1
V4_POSTFLIGHT_RESULT_KIND = "candle-flyspeck-pristine-postflight-result-v1"

V4_REQUEST_EXECUTION_POLICY = (
    "private-root-positional-ocaml-script-empty-stdin-v1"
)
V4_STDIN_POLICY = "supervisor-pipe-exact-eof-v1"
V4_STDOUT_POLICY = (
    "supervisor-pipe-bounded-opaque-with-reserved-markers-v1"
)
V4_STDERR_POLICY = "supervisor-pipe-exact-empty-v1"
V4_REQUEST_SCRIPT_ROLE = "positional-request-script"
V4_REQUEST_SCRIPT_PATH = "/candle-pristine/request.ml"
V4_REQUEST_SCRIPT_MODE = "100444"
V4_REQUEST_SCRIPT_INVENTORY_POLICY = "private-root-read-only-object-v1"

V4_GENERATION_AUTHORITY_SCHEMA = 1
V4_GENERATION_AUTHORITY_KIND = (
    "candle-flyspeck-pristine-request-generation-authority-v1"
)
V4_GENERATION_AUTHORITY_POLICY = (
    "captured-fixed-loader-isolated-python-exact-source-v1"
)
V4_GENERATION_RECEIPT_SCHEMA = 1
V4_GENERATION_RECEIPT_KIND = (
    "candle-flyspeck-pristine-request-generation-receipt-v1"
)
V4_GENERATION_RECEIPT_STATUS = "generated-and-captured-unapproved"
V4_COLLECTION_AUTHORITY_SCHEMA = 1
V4_COLLECTION_AUTHORITY_KIND = (
    "candle-flyspeck-pristine-full-run-collection-authority-v1"
)
V4_COLLECTION_AUTHORITY_POLICY = (
    "single-native-supervisor-seize-trace-and-postexit-finalize-v1"
)
V4_COLLECTION_RECEIPT_SCHEMA = 1
V4_COLLECTION_RECEIPT_KIND = (
    "candle-flyspeck-pristine-full-run-collection-authority-receipt-v1"
)
V4_COLLECTION_RECEIPT_STATUS = (
    "captured-current-host-collection-authority-unapproved"
)
V4_NATIVE_CLOSURE_PREIMAGE_KIND = (
    "candle-flyspeck-pristine-native-closure-preimage-v1"
)
V4_SOURCE_REDERIVATION_PREIMAGE_KIND = (
    "candle-flyspeck-pristine-source-rederivation-preimage-v1"
)

V4_NATIVE_SOURCE_TREE_KIND = "candle-flyspeck-native-source-tree-v1"
V4_NATIVE_SOURCE_TREE_SCHEMA = 1
V4_NATIVE_SOURCE_TREE_ROOT_POLICY = (
    "held-root-no-follow-safe-relative-files-v1"
)
V4_NATIVE_SOURCE_TREE_ROLES = (
    "attempt-supervisor",
    "request-generation-python",
    "collection-python",
    "dash-runtime",
)
V4_SAFE_RELATIVE_MAX_BYTES = 4_096
V4_SAFE_PATH_COMPONENT_MAX_BYTES = 255
V4_SOURCE_TREE_DATA_MODE = 33_060
V4_SOURCE_TREE_EXECUTABLE_MODE = 33_133
V4_REGULAR_0600_MODE = 33_152
V4_REGULAR_0444_MODE = 33_060
V4_DIRECTORY_0700_MODE = 16_832
V4_ORDERED_LIST_ENCODING = "compact-canonical-json-list-v1"
V4_TRACE_CHUNK_DIGEST_DOMAIN = "CANDLE_V4_TRACE_CHUNKS_V1"
V4_TRACE_RECORD_DIGEST_DOMAIN = "CANDLE_V4_TRACE_RECORDS_V1"
V4_BUILD_RUNTIME_INPUT_ROLES = (
    "header",
    "startup-object",
    "linker-script",
    "static-library",
    "shared-library",
    "runtime-data",
)
V4_BUILD_RUNTIME_INPUT_MIN = 1
V4_BUILD_INPUT_CLOSURE_SCHEMA = 2
V4_BUILD_INPUT_CLOSURE_KIND = (
    "candle-flyspeck-isolated-native-build-input-closure-v2"
)
V4_BUILD_INPUT_CLOSURE_POLICY = (
    "outside-parent-held-descriptor-chroot-exhaustive-input-tree-v2"
)
V4_BUILD_INPUT_CLOSURE_ENTRY_MAX = 196_608
V4_BUILD_INPUT_CLOSURE_FILE_MAX_BYTES = 1_073_741_824
V4_BUILD_INPUT_CLOSURE_TOTAL_MAX_BYTES = 68_719_476_736
V4_BUILD_EXECUTABLE_VERSION_MAX_BYTES = 4_096
V4_BUILD_INPUT_ENTRY_AUTHORITY_GRAPH_MAX_BYTES = 167_772_160
V4_BUILD_INPUT_ENTRY_AUTHORITY_NODE_MAX = 8_388_608
V4_BUILD_INPUT_ENTRY_AUTHORITY_CONTAINER_MAX = 196_608
V4_BUILD_INPUT_ENTRY_AUTHORITY_STRING_MAX_BYTES = 4_096
V4_BUILD_INPUT_ENTRY_AUTHORITY_KEY_MAX_BYTES = 255
V4_BUILD_INPUT_ENTRY_AUTHORITY_FRAGMENT_MAX_BYTES = 32_768
V4_BUILD_INPUT_CLOSURE_INHERITED_FD_COUNT = 3
V4_BUILD_INPUT_CLOSURE_INHERITED_FD_FIELDS = (
    "fd", "role", "access_mode", "object_identity", "fd_generation",
    "cloexec",
)
V4_BUILD_INPUT_CLOSURE_INHERITED_FD_LAYOUT = (
    (0, "stdin-eof", "read-only"),
    (1, "build-stdout", "write-only"),
    (2, "build-stderr", "write-only"),
)
V4_BUILD_INPUT_CLOSURE_ENTRY_FIELDS = (
    "index", "relative", "object_type", "mode", "bytes", "sha256",
    "selector", "st_nlink", "parent_descriptor_identity", "mount_id",
    "st_dev", "st_ino", "stable_generation",
)
V4_BUILD_INPUT_CLOSURE_OBSERVED_ENTRY_FIELDS = (
    "st_nlink", "parent_descriptor_identity", "mount_id", "st_dev",
    "st_ino", "stable_generation",
)
V4_BUILD_READONLY_DIRECTORY_MODE = 16_749
V4_BUILD_SOURCE_DIRECTORY = "candle-source"
V4_BUILD_OUTPUT_DIRECTORY = "candle-output"
V4_BUILD_ROOT_DERIVATION_MAX_BYTES = 33_554_432
V4_BUILD_FILTER_SCHEMA = 6
V4_BUILD_FILTER_KIND = (
    "candle-flyspeck-isolated-native-build-seccomp-filter-v6"
)
V4_BUILD_FILTER_POLICY = (
    "isolated-native-build-post-chroot-deny-escape-network-ipc-transfer-v6"
)
V4_BUILD_FILTER_ERRNO = 1
V4_BUILD_FILTER_CLONE_SYSCALL = 56
V4_BUILD_FILTER_CLONE_REJECT_MASK = 0xFEDFBE80
V4_BUILD_FILTER_CLONE_ALLOWED_LOW_MASK = 0x0120417F
V4_BUILD_FILTER_AUDIT_ARCH = 0xC000003E
V4_BUILD_FILTER_X32_SYSCALL_BIT = 0x40000000
V4_BUILD_FILTER_INSTRUCTION_COUNT = 136
V4_BUILD_FILTER_INSTRUCTIONS_BYTES = 1_088
V4_BUILD_FILTER_DECODED_RULE_COUNT = 66
V4_BUILD_FILTER_RET_KILL_PROCESS = 0x80000000
V4_BUILD_FILTER_RET_ERRNO = 0x00050001
V4_BUILD_FILTER_RET_ENOSYS = 0x00050026
V4_BUILD_FILTER_RET_ALLOW = 0x7FFF0000
V4_BUILD_FILTER_DENIED_SYSCALLS = (
    (16, "ioctl"),
    (29, "shmget"),
    (30, "shmat"),
    (31, "shmctl"),
    (40, "sendfile"),
    (41, "socket"),
    (53, "socketpair"),
    (64, "semget"),
    (65, "semop"),
    (66, "semctl"),
    (67, "shmdt"),
    (68, "msgget"),
    (69, "msgsnd"),
    (70, "msgrcv"),
    (71, "msgctl"),
    (101, "ptrace"),
    (155, "pivot_root"),
    (161, "chroot"),
    (165, "mount"),
    (166, "umount2"),
    (206, "io_setup"),
    (207, "io_destroy"),
    (208, "io_getevents"),
    (209, "io_submit"),
    (210, "io_cancel"),
    (220, "semtimedop"),
    (240, "mq_open"),
    (241, "mq_unlink"),
    (242, "mq_timedsend"),
    (243, "mq_timedreceive"),
    (244, "mq_notify"),
    (245, "mq_getsetattr"),
    (248, "add_key"),
    (249, "request_key"),
    (250, "keyctl"),
    (272, "unshare"),
    (275, "splice"),
    (276, "tee"),
    (278, "vmsplice"),
    (298, "perf_event_open"),
    (303, "name_to_handle_at"),
    (304, "open_by_handle_at"),
    (308, "setns"),
    (310, "process_vm_readv"),
    (311, "process_vm_writev"),
    (317, "seccomp"),
    (321, "bpf"),
    (323, "userfaultfd"),
    (326, "copy_file_range"),
    (333, "io_pgetevents"),
    (425, "io_uring_setup"),
    (426, "io_uring_enter"),
    (427, "io_uring_register"),
    (428, "open_tree"),
    (429, "move_mount"),
    (430, "fsopen"),
    (431, "fsconfig"),
    (432, "fsmount"),
    (433, "fspick"),
    (435, "clone3"),
    (438, "pidfd_getfd"),
    (442, "mount_setattr"),
)
V4_BUILD_FILTER_ENOSYS_SYSCALLS = (
    (435, "clone3"),
)
V4_BUILD_EXECUTION_OBSERVATION_SCHEMA = 7
V4_BUILD_EXECUTION_OBSERVATION_KIND = (
    "candle-flyspeck-isolated-native-build-execution-observation-v7"
)
V4_BUILD_EXECUTION_OBSERVATION_POLICY = (
    "outside-parent-all-task-source-consumption-and-output-chronology-v7"
)
V4_BUILD_EXECUTION_TASK_MAX = 4_096
V4_BUILD_EXECUTION_EVENT_MAX = 131_072
V4_BUILD_SOURCE_JOIN_MAX = 4_096
V4_BUILD_OUTPUT_JOIN_MAX = 4_096
V4_BUILD_OUTPUT_GENERATION_MAX = 4_096
V4_BUILD_FD_PER_TABLE_MAX = 4_096
V4_BUILD_VMA_PER_ADDRESS_SPACE_MAX = 65_536
V4_BUILD_TRANSITION_PER_EVENT_MAX = 8_194
V4_BUILD_TRANSITION_TOTAL_MAX = 524_288
V4_NATIVE_BUILD_RECEIPT_MAX_BYTES = 134_217_728
V4_NATIVE_BUILD_RECEIPT_READ_MAX_BYTES = 134_217_729
V4_BUILD_INITIAL_STATE_SEED_FIELDS = (
    "capture_boundary", "observer_task_identity", "builder_task_identity",
    "builder_interrupt_stop_event_index",
    "initial_object_edges", "parent_fd_table", "parent_open_descriptions",
    "parent_address_space", "parent_mappings", "parent_fs_state",
    "parent_mount_graph", "builder_mount_graph", "builder_credentials",
    "builder_task_control_state",
    "gate_mapping_index", "inherited_fd_indices", "ordered_state_sha256",
    "complete",
)
V4_BUILD_INITIAL_STATE_CAPTURE_BOUNDARY = (
    "held-interrupt-stop-after-id-maps-before-builder-gate-release-v1"
)
V4_BUILD_INITIAL_STATE_DIGEST_DOMAIN = (
    "candle-flyspeck-v4-initial-state-seed-v5"
)
V4_BUILD_INITIAL_STATE_DIGEST_PREIMAGE = (
    "ascii-domain-nul-canonical-json-array-of-ordered-field-values-v1"
)
V4_BUILD_INITIAL_STATE_DIGEST_FIELDS = (
    "capture_boundary", "observer_task_identity", "builder_task_identity",
    "builder_interrupt_stop_event_index", "initial_object_edges",
    "parent_fd_table", "parent_open_descriptions", "parent_address_space",
    "parent_mappings", "parent_fs_state", "parent_mount_graph",
    "builder_mount_graph",
    "builder_credentials", "builder_task_control_state", "gate_mapping_index",
    "inherited_fd_indices",
)
V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS = (
    "count", "entries", "ordered_entry_sha256",
)
V4_BUILD_INITIAL_FD_TABLE_CONTAINER_FIELDS = (
    "table_id", "generation", "fd_count", "fds", "ordered_fd_sha256",
)
V4_BUILD_INITIAL_ADDRESS_SPACE_FIELDS = (
    "address_space_id", "generation", "mapping_count", "mapping_indices",
    "ordered_mapping_index_sha256",
)
V4_BUILD_INITIAL_OBJECT_EDGE_FIELDS = (
    "index", "domain", "authority_role", "authority_index",
    "root_identity", "root_fd_generation", "input_root_entry_index",
    "stream_role", "setup_role", "parent_descriptor_identity",
    "mount_id", "st_dev", "st_ino", "stable_generation",
    "resolved_relative", "symlink_decisions",
)
V4_BUILD_INITIAL_OBJECT_EDGE_DOMAINS = (
    "input-root", "input-root-entry", "output-root", "stream-endpoint",
    "bootstrap-runtime", "setup-root",
)
V4_BUILD_INITIAL_FD_FIELDS = (
    "index", "fd", "fd_generation", "cloexec", "access_mode",
    "open_description_index",
)
V4_BUILD_INITIAL_OPEN_DESCRIPTION_FIELDS = (
    "index", "open_description_id", "generation", "object_edge_index",
    "access_mode", "status_flags", "offset", "lock_state",
    "descriptor_ref_count",
)
V4_BUILD_LOCK_STATE_FIELDS = ("mode",)
V4_BUILD_LOCK_TYPES = ("unlocked", "shared", "exclusive")
V4_BUILD_INITIAL_MAPPING_FIELDS = (
    "index", "address", "length", "protection", "flags", "file_offset",
    "object_edge_index", "gate_mapping",
)
V4_BUILD_INITIAL_FS_STATE_FIELDS = (
    "root_identity", "cwd_identity", "umask", "generation",
)
V4_BUILD_MOUNT_GRAPH_CONTAINER_FIELDS = (
    "mount_namespace_identity", "generation", "mount_count", "mounts",
    "ordered_mount_sha256", "mountinfo_bytes", "mountinfo_sha256",
    "mountinfo_payload_base64",
)
V4_BUILD_MOUNT_GRAPH_ENTRY_FIELDS = (
    "index", "mount_id", "raw_parent_mount_id", "parent_mount_id",
    "root_identity",
    "mountpoint_identity", "device_major", "device_minor",
    "root_bytes_base64", "mountpoint_bytes_base64", "filesystem_type",
    "mount_source_bytes_base64", "flags", "super_options",
    "optional_fields", "propagation",
)
V4_BUILD_MOUNT_CLONE_FIELDS = (
    "index", "source_mount_id", "child_mount_id",
    "source_raw_parent_mount_id", "child_raw_parent_mount_id",
    "root_identity",
    "mountpoint_identity", "device_major", "device_minor",
    "root_bytes_base64", "mountpoint_bytes_base64", "filesystem_type",
    "mount_source_bytes_base64", "flags", "super_options",
    "source_optional_fields", "child_optional_fields",
    "source_propagation", "child_propagation",
    "source_parent_mount_id", "child_parent_mount_id",
)
V4_BUILD_MOUNT_PROPAGATION_FIELDS = (
    "shared_group_id", "master_group_id", "propagate_from_group_id",
    "unbindable",
)
V4_BUILD_MOUNT_GRAPH_ORDER_POLICY = (
    "root-first-parent-before-child-then-raw-mountpoint-bytes-then-mount-id-v1"
)
V4_BUILD_MOUNT_ROOT_PARENT_POLICY = (
    "index-zero-only-null-normalized-parent-raw-parent-positive-absent-from-"
    "graph;nonroot-raw-parent-equals-normalized-parent-present-earlier-v1"
)
V4_BUILD_MOUNTINFO_CAPTURE_POLICY = (
    "outside-parent-held-proc-pid-mountinfo-complete-bounded-bytes-v1"
)
V4_BUILD_MOUNT_OPTION_LIST_POLICY = (
    "exact-json-list-of-mountinfo-order-nonempty-ascii-tokens-v1"
)
V4_BUILD_MOUNT_NAMESPACE_FILE_POLICY = (
    "reject-source-nsfs-or-mountpoint-rooted-at-proc-namespace-file-v1"
)
V4_BUILD_MOUNT_USERNS_COPY_POLICY = (
    "linux-copy-mnt-ns-visible-shared-to-slave-no-namespace-files-v2"
)
V4_BUILD_MOUNT_PROPAGATION_COPY_POLICY = (
    ("private", "private"),
    ("shared", "slave-same-source-shared-group-as-master"),
    ("slave", "slave-same-master-group"),
    ("shared-slave", "slave-same-source-shared-group-as-master"),
    ("unbindable", "unbindable"),
)
V4_BUILD_MOUNT_INTERNAL_LOCK_POLICY = (
    "not-authority-unobservable-mnt-expire-and-lock-bits-never-relied-on-v1"
)
V4_BUILD_INITIAL_CREDENTIAL_FIELDS = (
    "real_uid", "effective_uid", "saved_uid", "fsuid", "real_gid",
    "effective_gid", "saved_gid", "fsgid", "supplementary_groups",
    "securebits", "capability_sets", "no_new_privileges",
    "seccomp_mode", "seccomp_filter_count",
)
V4_BUILD_SUPPLEMENTARY_GROUP_CONTAINER_FIELDS = (
    "count", "gids", "ordered_gid_sha256",
)
V4_BUILD_SUPPLEMENTARY_GROUP_MAX = 65_536
V4_BUILD_GID_MIN = 0
V4_BUILD_GID_MAX = 0xFFFF_FFFF
V4_BUILD_CAPABILITY_SET_FIELDS = (
    "cap_last_cap", "count", "capabilities", "ordered_capability_sha256",
)
V4_BUILD_CAPABILITY_SETS_FIELDS = (
    "effective", "permitted", "inheritable", "ambient", "bounding",
)
V4_BUILD_CAPABILITY_SET_NAMES = V4_BUILD_CAPABILITY_SETS_FIELDS
V4_BUILD_CREDENTIAL_SCALAR_POLICY_FIELDS = (
    "field", "json_type", "domain", "capture_join",
)
V4_BUILD_CREDENTIAL_SCALAR_POLICY = (
    ("real_uid", "integer-nonbool", ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("effective_uid", "integer-nonbool",
     ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("saved_uid", "integer-nonbool", ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("fsuid", "integer-nonbool", ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("real_gid", "integer-nonbool", ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("effective_gid", "integer-nonbool",
     ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("saved_gid", "integer-nonbool", ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("fsgid", "integer-nonbool", ("inclusive-uint", 0, 0xFFFF_FFFF),
     "exact-proc-credential-snapshot"),
    ("securebits", "integer-nonbool", ("exact-values", 0),
     "derived-exact-zero-from-authenticated-clone-newuser"),
    ("no_new_privileges", "integer-nonbool", ("exact-values", 0, 1),
     "exact-proc-status-join"),
    ("seccomp_mode", "integer-nonbool", ("exact-values", 0, 2),
     "exact-proc-status-join"),
    ("seccomp_filter_count", "integer-nonbool",
     ("inclusive-uint", 0, 4_096),
     "zero-iff-mode-zero-positive-iff-mode-two-proc-status-join"),
)
V4_BUILD_INITIAL_TASK_CONTROL_STATE_FIELDS = (
    "signal_disposition_count", "signal_dispositions",
    "signal_disposition_sha256", "blocked_signal_set",
    "pending_signal_set", "signal_altstack", "fs_base", "gs_base",
    "clear_child_tid", "robust_list_registration", "rseq_registration",
    "personality",
)
V4_BUILD_INITIAL_SIGNAL_DISPOSITION_FIELDS = (
    "signal_number", "action",
)
V4_BUILD_SIGNAL_MIN = 1
V4_BUILD_SIGNAL_MAX = 64
V4_BUILD_SIGNAL_DISPOSITION_COUNT = 64
V4_BUILD_SIGNAL_SET_FIELDS = (
    "raw_u64", "count", "signals", "ordered_signal_sha256",
)
V4_BUILD_SIGNAL_ACTION_FIELDS = (
    "handler", "flags", "restorer", "mask",
)
V4_BUILD_SIGNAL_ACTION_FLAG_MASK = 0xDC00_0C07
V4_BUILD_SIGNAL_ALTSTACK_FIELDS = ("sp", "flags", "size")
V4_BUILD_SIGNAL_ALTSTACK_FLAG_MASK = 0x8000_0003
V4_BUILD_SIGNAL_ALTSTACK_DISABLED = (0, 2, 0)
V4_BUILD_ROBUST_LIST_REGISTRATION_FIELDS = (
    "registered", "head", "length",
)
V4_BUILD_ROBUST_LIST_LENGTHS = (0, 24)
V4_BUILD_RSEQ_REGISTRATION_FIELDS = (
    "registered", "address", "length", "flags", "signature",
)
V4_BUILD_RSEQ_LENGTHS = (0, 32)
V4_BUILD_RSEQ_SIGNATURES = (0, 0x5305_3053)
V4_BUILD_RSEQ_STATE_FLAGS = (0,)
V4_BUILD_PERSONALITY_STICKY_TIMEOUTS = 0x0400_0000
V4_BUILD_PERSONALITY_POLICY = (
    "exact-zero-uint32-nonbool-for-pinned-static-x86-64-exec-profile-v2"
)
V4_BUILD_TASK_CONTROL_DERIVATION_FIELDS = (
    "boundary", "profile", "signal_dispositions", "blocked_signal_set",
    "pending_signal_set", "signal_altstack", "fs_base", "gs_base",
    "clear_child_tid", "robust_list_registration", "rseq_registration",
    "personality",
)
V4_BUILD_CLONE_TASK_CONTROL_DERIVATIONS = (
    (
        "clone", "fork-equivalent-sigchld", "copy-exact", "copy-exact",
        "canonical-empty", "copy-exact", "copy-exact", "copy-exact",
        "canonical-null", "canonical-unregistered",
        "copy-exact-because-clone-vm-clear", "copy-exact-zero",
    ),
    (
        "clone", "dash-child-tid-sigchld", "copy-exact", "copy-exact",
        "canonical-empty", "copy-exact", "copy-exact", "copy-exact",
        "entry-child-tid-pointer-clear-on-exit", "canonical-unregistered",
        "copy-exact-because-clone-vm-clear", "copy-exact-zero",
    ),
    (
        "clone", "glibc-clone-fallback-vfork-vm-sigchld", "copy-exact",
        "copy-exact", "canonical-empty",
        "copy-exact-because-clone-vfork-set", "copy-exact", "copy-exact",
        "canonical-null", "canonical-unregistered",
        "canonical-unregistered-because-clone-vm-set", "copy-exact-zero",
    ),
)
V4_BUILD_EXEC_TASK_CONTROL_DERIVATION = (
    "exec", "pinned-static-linux-x86-64",
    "preserve-sig-ign-handler-one-else-handler-zero-and-clear-every-flags-"
    "restorer-mask", "copy-exact", "copy-exact",
    "canonical-disabled", "canonical-zero", "canonical-zero",
    "canonical-null", "canonical-unregistered", "canonical-unregistered",
    "canonical-zero-require-old-zero",
)
V4_BUILD_NESTED_VALUE_POLICY_FIELDS = (
    "name", "fields", "exact_rules",
)
V4_BUILD_NESTED_VALUE_POLICY = (
    (
        "lock-state", V4_BUILD_LOCK_STATE_FIELDS,
        "exact-dict;mode-is-unlocked-shared-or-exclusive;flock-lock-nb-is-"
        "call-behavior-not-retained-state",
    ),
    (
        "supplementary-groups", V4_BUILD_SUPPLEMENTARY_GROUP_CONTAINER_FIELDS,
        "exact-dict;count-0-through-65536;gids-exact-list-of-count;"
        "strictly-increasing-unique-uint32-nonbool;digest-canonical-gids-list",
    ),
    (
        "capability-set", V4_BUILD_CAPABILITY_SET_FIELDS,
        "exact-dict;cap-last-cap-equals-kernel-profile;count-0-through-"
        "cap-last-cap-plus-one;capabilities-exact-list-of-count;strictly-"
        "increasing-unique-nonbool-integers-0-through-cap-last-cap;"
        "digest-canonical-capabilities-list",
    ),
    (
        "capability-sets", V4_BUILD_CAPABILITY_SETS_FIELDS,
        "exact-dict;each-value-is-capability-set;no-extra-set",
    ),
    (
        "signal-set", V4_BUILD_SIGNAL_SET_FIELDS,
        "exact-dict;raw-u64-uint64-nonbool;count-0-through-64;signals-exact-"
        "list-of-count;bit-signal-minus-one-in-raw-u64-iff-list-membership;strictly-"
        "increasing-unique-nonbool-integers-1-through-64;digest-canonical-"
        "signals-list;blocked-set-excludes-9-and-19",
    ),
    (
        "signal-action", V4_BUILD_SIGNAL_ACTION_FIELDS,
        "exact-dict;handler-and-restorer-uint64-nonbool;flags-uint64-nonbool-"
        "with-no-bit-outside-0xdc000c07;"
        "mask-is-signal-set",
    ),
    (
        "signal-altstack", V4_BUILD_SIGNAL_ALTSTACK_FIELDS,
        "exact-dict;sp-null-or-uint64-nonbool;size-uint64-nonbool;flags-"
        "uint32-nonbool-with-no-bit-outside-0x80000003;disabled-canonical-"
        "form-sp-zero-flags-two-size-zero",
    ),
    (
        "robust-list-registration", V4_BUILD_ROBUST_LIST_REGISTRATION_FIELDS,
        "exact-dict;registered-bool;unregistered-is-false-null-head-length-"
        "zero;registered-is-true-nonzero-uint64-nonbool-head-and-length-24",
    ),
    (
        "rseq-registration", V4_BUILD_RSEQ_REGISTRATION_FIELDS,
        "exact-dict;registered-bool;unregistered-is-false-null-address-length-"
        "zero-flags-zero-signature-zero;registered-is-true-nonzero-uint64-"
        "nonbool-address-length-32-signature-"
        "0x53053053-flags-zero",
    ),
    (
        "mount-propagation", V4_BUILD_MOUNT_PROPAGATION_FIELDS,
        "exact-dict;group-ids-null-or-positive-uint32-nonbool;unbindable-bool;"
        "private-is-all-null-false;shared-has-shared-group;slave-has-master-"
        "group;shared-slave-has-both;propagate-from-requires-master;"
        "unbindable-requires-all-group-ids-null",
    ),
)
V4_BUILD_PRECLONE_SIGNAL_PROFILE = (
    "all-blockable-signals-blocked", "all-dispositions-default",
    "no-pending-signals", "alternate-stack-disabled",
)
V4_BUILD_INITIAL_STATE_CONTAINER_POLICY_FIELDS = (
    "field", "container_fields", "entry_fields", "max_entries",
)
V4_BUILD_MOUNT_GRAPH_MAX = 196_608
V4_BUILD_INITIAL_STATE_CONTAINER_POLICY = (
    ("initial_object_edges", V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS,
     V4_BUILD_INITIAL_OBJECT_EDGE_FIELDS, V4_BUILD_INPUT_CLOSURE_ENTRY_MAX),
    ("parent_fd_table", V4_BUILD_INITIAL_FD_TABLE_CONTAINER_FIELDS,
     V4_BUILD_INITIAL_FD_FIELDS, V4_BUILD_FD_PER_TABLE_MAX),
    ("parent_open_descriptions", V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS,
     V4_BUILD_INITIAL_OPEN_DESCRIPTION_FIELDS, V4_BUILD_FD_PER_TABLE_MAX),
    ("parent_mappings", V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS,
     V4_BUILD_INITIAL_MAPPING_FIELDS, V4_BUILD_VMA_PER_ADDRESS_SPACE_MAX),
    ("parent_mount_graph", V4_BUILD_MOUNT_GRAPH_CONTAINER_FIELDS,
     V4_BUILD_MOUNT_GRAPH_ENTRY_FIELDS, V4_BUILD_MOUNT_GRAPH_MAX),
    ("builder_mount_graph", V4_BUILD_MOUNT_GRAPH_CONTAINER_FIELDS,
     V4_BUILD_MOUNT_GRAPH_ENTRY_FIELDS, V4_BUILD_MOUNT_GRAPH_MAX),
)
V4_BUILD_SETUP_PHASE_FIELDS = (
    "policy", "first_event_index", "filter_install_entry_event_index",
    "filter_install_exit_event_index", "step_count", "steps",
    "ordered_step_sha256", "final_replay_state",
    "final_replay_state_sha256", "final_fd_indices", "final_mapping_indices",
    "final_fs_state", "final_supplementary_groups",
    "final_capability_sets", "no_new_privileges", "seccomp_mode",
    "seccomp_filter_count", "complete",
)
V4_BUILD_SETUP_STEP_FIELDS = (
    "index", "role", "syscall_numbers", "argument_policy",
    "event_indices", "state_before", "state_before_sha256", "state_after",
    "state_after_sha256", "complete",
)
V4_BUILD_SETUP_REPLAY_STATE_FIELDS = (
    "fd_table", "open_descriptions", "address_space", "mappings",
    "fs_state", "mount_graph", "credentials", "task_control_state",
)
V4_BUILD_SETUP_STATE_DIGEST_DOMAIN = (
    "candle-flyspeck-v4-setup-replay-state-v5"
)
V4_BUILD_SETUP_STATE_DIGEST_PREIMAGE = (
    "ascii-domain-nul-canonical-json-array-of-ordered-field-values-v1"
)
V4_BUILD_SETUP_POLICY = (
    "derived-pre-filter-builder-setup-deny-all-other-v6"
)
V4_BUILD_SETUP_SEQUENCE_FIELDS = (
    "index", "role", "syscall_numbers", "argument_policy",
)
V4_BUILD_SETUP_SEQUENCE = (
    (0, "private-mount-propagation", (165,),
     "mount-slash-null-ms-rec-private-0x44000-null-exact"),
    (1, "enter-held-input-root", (81,),
     "fchdir-exact-inherited-input-root-fd-generation"),
    (2, "chroot-into-input-root", (161,),
     "chroot-dot-after-fchdir-held-input-root-exact"),
    (3, "enter-new-root", (80,), "chdir-slash-exact"),
    (4, "select-mapped-gid", (119,), "setresgid-zero-zero-zero-exact"),
    (5, "select-mapped-uid", (117,), "setresuid-zero-zero-zero-exact"),
    (6, "install-build-signal-mask", (14,),
     "rt-sigprocmask-sig-setmask-empty-null-oldset-size-8-exact"),
    (7, "clear-ambient-capabilities", (157,),
     "prctl-pr-cap-ambient-clear-all-zero-zero-zero-exact"),
    (8, "drop-capability-bounding-set", (157,),
     "prctl-pr-capbset-drop-each-profile-cap-descending-exact"),
    (9, "drop-capabilities", (126,),
     "capset-v3-zero-effective-permitted-inheritable-exact"),
    (10, "close-setup-descriptors", (3,),
     "close-each-derived-setup-fd-once-descending-exact"),
    (11, "set-no-new-privileges", (157,),
     "prctl-pr-set-no-new-privs-one-zero-zero-zero-exact"),
    (12, "install-build-filter", (317,),
     "seccomp-set-mode-filter-zero-exact-authority-program"),
)
V4_BUILD_SETUP_CREDENTIAL_TARGETS = (
    ("select-mapped-gid",
     ("real_gid", "effective_gid", "saved_gid", "fsgid")),
    ("select-mapped-uid",
     ("real_uid", "effective_uid", "saved_uid", "fsuid")),
)
V4_BUILD_SETUP_CAPABILITY_TARGETS = (
    ("clear-ambient-capabilities", ("ambient",)),
    ("drop-capability-bounding-set", ("bounding",)),
    ("drop-capabilities", ("effective", "permitted", "inheritable")),
)
V4_BUILD_SETUP_FINAL_FDS = (0, 1, 2)
V4_BUILD_SETUP_FINAL_CAPABILITY_SETS = (
    "effective-empty", "permitted-empty", "inheritable-empty",
    "ambient-empty", "bounding-empty",
)
V4_BUILD_NAMESPACE_CLONE_FLAGS = 0x78020011
V4_BUILD_CLONE_PROFILE_FIELDS = (
    "profile", "flags", "ptrace_event_kind", "address_space_policy",
    "fd_table_policy", "fs_state_policy", "signal_handler_policy",
    "parent_tid_policy", "child_tid_policy",
)
V4_BUILD_CLONE_PROFILES = (
    (
        "fork-equivalent-sigchld", 0x00000011, "fork", "copy", "copy",
        "copy", "copy", "unchanged", "unchanged",
    ),
    (
        "dash-child-tid-sigchld", 0x01200011, "fork", "copy", "copy",
        "copy", "copy", "unchanged", "set-and-clear-child-tid",
    ),
    (
        "glibc-clone-fallback-vfork-vm-sigchld", 0x00004111,
        "vfork", "share-held-until-vfork-done", "copy", "copy",
        "copy", "unchanged", "unchanged",
    ),
)
V4_BUILD_CLONE_PROFILE_POLICY = (
    "exact-unsigned-64-bit-flags-equality-reject-before-resume-v1"
)
V4_BUILD_NAMESPACE_KINDS = (
    "user-namespace",
    "mount-namespace",
    "pid-namespace",
    "network-namespace",
    "ipc-namespace",
)
V4_BUILD_NAMESPACE_INSPECTOR_FIELDS = (
    "task_identity", "inherited_fds", "namespace_descriptor_identity",
    "result_pipe_identity", "result_bytes", "raw_wait_status", "exit_code",
    "complete",
)
V4_BUILD_NETWORK_INTERFACE_FIELDS = (
    "list_index", "ifindex", "name", "mtu", "flags", "operstate",
    "namespace_identity",
)
V4_BUILD_NETWORK_LOOPBACK_FIXED_FIELDS = {
    "list_index": 0,
    "ifindex": 1,
    "name": "lo",
    "mtu": 65_536,
    "flags": 0x8,
    "operstate": "down",
}
V4_BUILD_NETWORK_ROUTE_COUNT = 0
V4_BUILD_NETWORK_SOCKET_COUNT = 0
V4_BUILD_IPC_SYSV_SEGMENT_COUNT = 0
V4_BUILD_IPC_SYSV_SEMAPHORE_COUNT = 0
V4_BUILD_IPC_SYSV_MESSAGE_COUNT = 0
V4_BUILD_IPC_MQUEUE_COUNT = 0
V4_BUILD_PTRACE_OPTIONS = (
    "PTRACE_O_TRACESYSGOOD",
    "PTRACE_O_TRACEFORK",
    "PTRACE_O_TRACEVFORK",
    "PTRACE_O_TRACECLONE",
    "PTRACE_O_TRACEVFORKDONE",
    "PTRACE_O_TRACEEXEC",
    "PTRACE_O_TRACEEXIT",
    "PTRACE_O_EXITKILL",
)
V4_BUILD_EVENT_KINDS = (
    "namespace-clone",
    "interrupt-stop",
    "peer-interrupt-stop",
    "child-initial-stop",
    "signal-delivery-stop",
    "group-stop",
    "syscall-entry",
    "syscall-exit",
    "fork",
    "vfork",
    "clone",
    "vfork-done",
    "exec",
    "exit",
    "terminal-wait",
    "pre-output-walk",
    "post-output-walk",
    "output-hash-barrier",
)
V4_BUILD_EVENT_FIELDS = frozenset({
    "index", "kind", "actor_task_identity", "subject_task_identity",
    "paired_event_index", "syscall_number", "arguments", "return_value",
    "ptrace_event_message", "raw_wait_status", "signal_number", "siginfo",
    "reinject_signal", "entry_capture", "exit_capture",
    "object_edge_count", "object_edges", "fd_transition_count",
    "fd_transitions", "mapping_transition_count", "mapping_transitions",
    "fs_transition_count", "fs_transitions", "task_transition_count",
    "task_transitions",
})
V4_BUILD_EVENT_ALWAYS_NONNULL_FIELDS = (
    "index", "kind", "actor_task_identity",
    "object_edge_count", "object_edges",
    "fd_transition_count", "fd_transitions",
    "mapping_transition_count", "mapping_transitions",
    "fs_transition_count", "fs_transitions",
    "task_transition_count", "task_transitions",
)
V4_BUILD_EVENT_TAGGED_NONNULL_FIELDS = {
    "namespace-clone": (
        "subject_task_identity", "return_value",
    ),
    "interrupt-stop": (
        "subject_task_identity", "raw_wait_status", "signal_number",
        "reinject_signal",
    ),
    "peer-interrupt-stop": (
        "subject_task_identity", "raw_wait_status", "signal_number",
        "reinject_signal",
    ),
    "child-initial-stop": (
        "subject_task_identity", "raw_wait_status", "signal_number",
        "reinject_signal",
    ),
    "signal-delivery-stop": (
        "subject_task_identity", "raw_wait_status",
        "signal_number", "siginfo", "reinject_signal",
    ),
    "group-stop": (
        "subject_task_identity", "raw_wait_status", "signal_number",
        "reinject_signal",
    ),
    "syscall-entry": (
        "subject_task_identity", "syscall_number", "arguments",
        "entry_capture",
    ),
    "syscall-exit": (
        "subject_task_identity", "paired_event_index",
        "syscall_number", "return_value", "exit_capture",
    ),
    "fork": (
        "subject_task_identity", "ptrace_event_message",
    ),
    "vfork": (
        "subject_task_identity", "ptrace_event_message",
    ),
    "clone": (
        "subject_task_identity", "ptrace_event_message",
    ),
    "vfork-done": (
        "subject_task_identity", "ptrace_event_message",
    ),
    "exec": (
        "subject_task_identity", "paired_event_index", "ptrace_event_message",
    ),
    "exit": (
        "subject_task_identity", "paired_event_index",
        "ptrace_event_message",
    ),
    "terminal-wait": (
        "subject_task_identity", "raw_wait_status",
    ),
    "pre-output-walk": (),
    "post-output-walk": (),
    "output-hash-barrier": (),
}
V4_BUILD_EVENT_NONNULL_FIELDS = {
    kind: V4_BUILD_EVENT_ALWAYS_NONNULL_FIELDS + tagged_fields
    for kind, tagged_fields in V4_BUILD_EVENT_TAGGED_NONNULL_FIELDS.items()
}
V4_BUILD_ENTRY_CAPTURE_FIELDS = {
    "scalar-entry": ("kind", "operation"),
    "path-entry": (
        "kind", "operation", "operand_count", "operands", "scalar_flags",
        "pointed_struct", "peer_barrier_index",
    ),
    "exec-entry": (
        "kind", "operation", "executable_operand", "execveat_fd",
        "execveat_fd_generation", "flags", "argv", "environment",
        "cwd_identity", "umask", "peer_barrier_index",
    ),
    "fd-io-entry": (
        "kind", "operation", "fd", "fd_generation", "object_edge_index",
        "explicit_offset", "requested_bytes", "iovec_count", "iovecs",
        "flags", "peer_barrier_index",
    ),
    "mapping-entry": (
        "kind", "operation", "address", "length", "protection", "flags",
        "fd", "fd_generation", "file_offset", "peer_barrier_index",
    ),
    "fd-control-entry": (
        "kind", "operation", "fd", "fd_generation", "command",
        "scalar_argument", "pointed_argument", "peer_barrier_index",
    ),
    "task-create-entry": (
        "kind", "operation", "flags", "child_stack", "parent_tid_pointer",
        "child_tid_pointer", "tls", "peer_barrier_index",
    ),
    "seccomp-install-entry": (
        "kind", "operation", "flags", "sock_fprog", "instructions",
        "peer_barrier_index",
    ),
    "query-entry": (
        "kind", "operation", "input_region_count", "input_regions",
        "peer_barrier_index",
    ),
    "mount-entry": (
        "kind", "operation", "source_operand", "target_operand",
        "filesystem_type_operand", "flags", "data_region",
        "peer_barrier_index",
    ),
}
V4_BUILD_EXIT_CAPTURE_FIELDS = {
    "scalar-exit": ("kind", "operation"),
    "open-exit": (
        "kind", "operation", "returned_fd", "returned_fd_generation",
        "object_edge_index",
    ),
    "io-exit": (
        "kind", "operation", "positive_bytes", "effective_file_offset",
        "resulting_file_offset", "affected_range",
    ),
    "mapping-exit": (
        "kind", "operation", "returned_address", "affected_range",
    ),
    "path-mutation-exit": (
        "kind", "operation", "created_edge_indices", "removed_edge_indices",
        "renamed_edge_pairs",
    ),
    "fd-state-exit": (
        "kind", "operation", "affected_fd", "pre_fd_generation",
        "post_fd_generation", "open_description_id",
        "pre_open_description_generation", "post_open_description_generation",
    ),
    "fd-pair-exit": (
        "kind", "operation", "first_fd", "first_fd_generation",
        "first_open_description_id", "first_open_description_generation",
        "second_fd", "second_fd_generation", "second_open_description_id",
        "second_open_description_generation",
    ),
    "seccomp-install-exit": (
        "kind", "operation", "installed_filter_count", "proc_status_after",
    ),
    "query-exit": (
        "kind", "operation", "output_region_count", "output_regions",
    ),
}
V4_BUILD_QUERY_REGION_FIELDS = (
    "index", "argument_index", "address", "bytes", "sha256",
    "payload_base64",
)
V4_BUILD_QUERY_REGION_MAX = 4_096
V4_BUILD_QUERY_REGION_TOTAL_MAX_BYTES = 1_048_576
V4_BUILD_PATH_OPERAND_FIELDS = (
    "index", "argument_index", "dirfd_argument_index", "dirfd",
    "dirfd_generation", "pointer", "bytes", "sha256", "payload_base64",
    "nul_terminated", "resolution_role",
)
V4_BUILD_OBJECT_EDGE_FIELDS = (
    "index", "domain", "root_identity", "root_fd_generation",
    "input_root_entry_index", "output_generation_index",
    "post_tree_entry_index", "parent_descriptor_identity", "mount_id",
    "st_dev", "st_ino", "stable_generation", "resolved_relative",
    "symlink_decisions",
)
V4_BUILD_OBJECT_EDGE_DOMAINS = (
    "input-root-entry", "output-generation", "output-root",
)
V4_BUILD_SETUP_ROOT_EDGE_SCHEMA = 1
V4_BUILD_SETUP_ROOT_EDGE_KIND = (
    "candle-flyspeck-isolated-native-build-setup-root-edge-v1"
)
V4_BUILD_SETUP_ROOT_EDGE_POLICY = (
    "phase-only-initial-or-held-root-exact-authority-join-v1"
)
V4_BUILD_SETUP_ROOT_EDGE_DOMAINS = (
    "setup-root", "input-root",
)
V4_BUILD_EVENT_OBJECT_EDGE_DOMAINS = (
    V4_BUILD_OBJECT_EDGE_DOMAINS + V4_BUILD_SETUP_ROOT_EDGE_DOMAINS
)
V4_BUILD_SETUP_ROOT_EDGE_POLICY_FIELDS = (
    "role", "domain", "initial_edge_domain", "root_identity_join",
    "root_fd_generation_join", "stable_identity_join",
    "fs_transition_join",
)
V4_BUILD_SETUP_ROOT_EDGE_ROLE_POLICY = (
    (
        "private-mount-propagation", "setup-root", "setup-root",
        "state-before-fs-root-and-unique-initial-setup-root",
        "null",
        "unique-initial-setup-root-and-builder-mount-graph-index-zero",
        "mount-propagation-change-includes-edge-mount-id",
    ),
    (
        "enter-held-input-root", "input-root", "input-root",
        "input-closure-root-and-unique-initial-input-root",
        "input-closure-root-fd-generation-and-live-fchdir-fd",
        "unique-initial-input-root-and-held-root-observation",
        "cwd-change-index-zero-after-identity-equals-edge-root",
    ),
    (
        "chroot-into-input-root", "input-root", "input-root",
        "input-closure-root-and-unique-initial-input-root",
        "input-closure-root-fd-generation-and-live-held-root-fd",
        "unique-initial-input-root-and-held-root-observation",
        "root-change-index-zero-after-identity-equals-edge-root",
    ),
    (
        "enter-new-root", "input-root", "input-root",
        "input-closure-root-and-unique-initial-input-root",
        "input-closure-root-fd-generation-and-live-held-root-fd",
        "unique-initial-input-root-and-held-root-observation",
        "cwd-change-index-zero-after-identity-equals-edge-root",
    ),
)
V4_BUILD_OPEN_HOW_FIELDS = (
    "address", "size", "payload_base64", "sha256", "flags", "mode",
    "resolve",
)
V4_BUILD_IOVEC_FIELDS = (
    "index", "address", "requested_bytes", "payload_sha256",
)
V4_BUILD_PEER_BARRIER_FIELDS = (
    "index", "actor_task_index", "entry_event_index", "terminal_event_index",
    "shared_state_kinds", "peer_task_indices", "peer_stop_event_indices",
    "release_order", "complete",
)
V4_BUILD_PEER_SHARED_STATE_KINDS = (
    "address-space", "fd-table", "fs-state",
)
V4_BUILD_FD_TRANSITION_FIELDS = {
    "fd-table-create": (
        "kind", "index", "task_index", "table_id", "generation",
        "source_table_id", "sharing",
    ),
    "fd-install": (
        "kind", "index", "table_id", "before_generation",
        "after_generation", "fd", "new_fd_generation", "cloexec",
        "access_mode", "open_description_id", "open_description_generation",
    ),
    "open-description-create": (
        "kind", "index", "open_description_id", "generation",
        "object_edge_index", "access_mode", "status_flags", "offset",
    ),
    "fd-duplicate": (
        "kind", "index", "table_id", "before_generation",
        "after_generation", "source_fd", "source_fd_generation",
        "destination_fd", "retired_destination_generation",
        "new_destination_generation", "cloexec", "open_description_id",
        "open_description_generation",
    ),
    "fd-retire": (
        "kind", "index", "table_id", "before_generation",
        "after_generation", "fd", "fd_generation", "open_description_id",
        "open_description_generation", "reason",
    ),
    "open-description-retire": (
        "kind", "index", "open_description_id", "generation", "reason",
    ),
    "fd-cloexec-change": (
        "kind", "index", "table_id", "before_generation",
        "after_generation", "fd", "fd_generation", "cloexec",
    ),
    "open-description-status-change": (
        "kind", "index", "open_description_id", "before_generation",
        "after_generation", "old_status_flags", "new_status_flags",
    ),
    "open-description-offset-change": (
        "kind", "index", "open_description_id", "before_generation",
        "after_generation", "old_offset", "new_offset",
    ),
    "open-description-lock-change": (
        "kind", "index", "open_description_id", "before_generation",
        "after_generation", "old_lock", "new_lock",
    ),
    "fd-table-unshare": (
        "kind", "index", "task_index", "old_table_id", "new_table_id",
        "new_generation",
    ),
}
V4_BUILD_MAPPING_TRANSITION_FIELDS = {
    "address-space-create": (
        "kind", "index", "task_index", "address_space_id", "generation",
        "source_address_space_id", "sharing",
    ),
    "mapping-install": (
        "kind", "index", "address_space_id", "before_generation",
        "after_generation", "address", "length", "protection", "flags",
        "file_offset", "fd_generation", "object_edge_index",
    ),
    "mapping-remove": (
        "kind", "index", "address_space_id", "before_generation",
        "after_generation", "address", "length", "retired_mapping_indices",
    ),
    "mapping-remap": (
        "kind", "index", "address_space_id", "before_generation",
        "after_generation", "old_address", "old_length", "new_address",
        "new_length", "mapping_indices",
    ),
    "mapping-protect": (
        "kind", "index", "address_space_id", "before_generation",
        "after_generation", "address", "length", "old_protection",
        "new_protection", "mapping_indices",
    ),
    "address-space-exec-reset": (
        "kind", "index", "task_index", "address_space_id",
        "before_generation", "after_generation", "retired_mapping_indices",
    ),
}
V4_BUILD_FS_TRANSITION_FIELDS = {
    "fs-state-create": (
        "kind", "index", "task_index", "fs_state_id", "generation",
        "source_fs_state_id", "sharing",
    ),
    "cwd-change": (
        "kind", "index", "fs_state_id", "before_generation",
        "after_generation", "object_edge_index",
    ),
    "root-change": (
        "kind", "index", "fs_state_id", "before_generation",
        "after_generation", "object_edge_index",
    ),
    "umask-change": (
        "kind", "index", "fs_state_id", "before_generation",
        "after_generation", "old_umask", "new_umask",
    ),
    "mount-propagation-change": (
        "kind", "index", "mount_namespace_identity", "before_generation",
        "after_generation", "affected_mount_count", "affected_mount_ids",
        "old_propagations", "new_propagations",
    ),
    "mount-namespace-create": (
        "kind", "index", "task_index", "source_mount_namespace_identity",
        "source_generation", "child_mount_namespace_identity",
        "child_generation", "mount_clone_count", "mount_clones",
    ),
}
V4_BUILD_TASK_TRANSITION_FIELDS = {
    "builder-create": (
        "kind", "index", "task_identity", "clone_flags", "gate_identity",
        "initial_task_control_state",
    ),
    "observer-attached-stop": (
        "kind", "index", "task_index", "ptrace_options",
    ),
    "child-create": (
        "kind", "index", "parent_task_index", "child_task_index",
        "creation_kind", "creation_event_index", "child_task_control_state",
    ),
    "child-attached-stop": (
        "kind", "index", "task_index", "initial_stop_event_index",
    ),
    "vfork-hold": (
        "kind", "index", "parent_task_index", "child_task_index",
        "event_index",
    ),
    "vfork-release": (
        "kind", "index", "parent_task_index", "child_task_index",
        "event_index",
    ),
    "group-listen": (
        "kind", "index", "task_index", "stop_signal",
    ),
    "exec-image": (
        "kind", "index", "old_task_identity", "new_task_identity",
        "former_tid", "exec_entry_event_index", "old_task_control_state",
        "new_task_control_state",
    ),
    "exit-stop": (
        "kind", "index", "task_index", "exit_message", "termination_scope",
        "initiating_task_index", "initiating_entry_event_index",
    ),
    "wait-consumed": (
        "kind", "index", "task_index", "raw_wait_status",
    ),
    "credential-update": (
        "kind", "index", "task_index", "target_fields",
        "before_credentials", "after_credentials", "idempotent",
    ),
    "capability-sets-update": (
        "kind", "index", "task_index", "target_sets",
        "before_capability_sets", "after_capability_sets", "idempotent",
    ),
    "no-new-privileges-change": (
        "kind", "index", "task_index", "old_value", "new_value",
    ),
    "seccomp-change": (
        "kind", "index", "task_index", "old_mode", "new_mode",
        "old_filter_count", "new_filter_count", "filter_sha256",
    ),
    "signal-disposition-change": (
        "kind", "index", "task_index", "signal_number", "old_action",
        "new_action",
    ),
    "signal-mask-change": (
        "kind", "index", "task_index", "old_set", "new_set",
    ),
    "signal-altstack-change": (
        "kind", "index", "task_index", "old_stack", "new_stack",
    ),
    "tls-base-change": (
        "kind", "index", "task_index", "register", "old_base", "new_base",
    ),
    "child-tid-registration-change": (
        "kind", "index", "task_index", "old_address", "new_address",
    ),
    "robust-list-change": (
        "kind", "index", "task_index", "old_head", "old_length",
        "new_head", "new_length",
    ),
    "rseq-registration-change": (
        "kind", "index", "task_index", "old_registration",
        "new_registration",
    ),
    "tracee-wait-consume": (
        "kind", "index", "task_index", "child_task_index",
        "raw_wait_status", "wait_options",
    ),
}
V4_BUILD_OUTPUT_MUTATING_SYSCALLS = (
    (1, "write", "content-write"),
    (2, "open", "open-create-truncate"),
    (9, "mmap", "mapping-state"),
    (10, "mprotect", "mapping-state"),
    (11, "munmap", "mapping-state"),
    (18, "pwrite64", "content-write"),
    (20, "writev", "content-write"),
    (25, "mremap", "mapping-state"),
    (26, "msync", "mapping-state"),
    (76, "truncate", "size-change"),
    (77, "ftruncate", "size-change"),
    (82, "rename", "name-change"),
    (83, "mkdir", "name-create"),
    (84, "rmdir", "name-remove"),
    (85, "creat", "open-create-truncate"),
    (87, "unlink", "name-remove"),
    (90, "chmod", "mode-change"),
    (91, "fchmod", "mode-change"),
    (257, "openat", "open-create-truncate"),
    (258, "mkdirat", "name-create"),
    (263, "unlinkat", "name-remove"),
    (264, "renameat", "name-change"),
    (268, "fchmodat", "mode-change"),
    (296, "pwritev", "content-write"),
    (316, "renameat2", "name-change"),
    (328, "pwritev2", "content-write"),
    (437, "openat2", "open-create-truncate"),
    (452, "fchmodat2", "mode-change"),
)
def _v4_cardinality_spec(bounds: tuple[int, ...]) -> tuple[object, ...]:
    if len(bounds) == 1:
        return ("exact-values", bounds[0])
    if len(bounds) == 2:
        return ("inclusive-range", bounds[0], bounds[1])
    raise ValueError("malformed V4 cardinality bounds")


V4_BUILD_SETUP_OCCURRENCE_SPEC_TAGS = (
    "exact-values", "profile-derived-values", "seed-derived-values",
)
V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY_FIELDS = (
    "role", "syscall_number", "entry_kind", "exit_kind",
    "occurrence_spec", "object_edge_counts", "fd_transition_counts",
    "mapping_transition_counts", "fs_transition_counts",
    "task_transition_counts",
)
V4_BUILD_SETUP_QUERY_REGION_POLICY_FIELDS = (
    "role", "input_region_policy", "output_region_policy",
)
V4_BUILD_SETUP_QUERY_REGION_POLICY = (
    ("select-mapped-gid", (), ()),
    ("select-mapped-uid", (), ()),
    ("install-build-signal-mask",
     ((1, "input", "fixed-bytes", 8, "always-nonnull", "same-as-entry"),),
     ()),
    ("clear-ambient-capabilities", (), ()),
    ("drop-capability-bounding-set", (), ()),
    ("drop-capabilities",
     ((0, "input", "fixed-bytes", 8, "always-nonnull", "same-as-entry"),
      (1, "input", "fixed-bytes", 24, "always-nonnull", "same-as-entry")),
     ()),
    ("set-no-new-privileges", (), ()),
)
V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY = (
    ("private-mount-propagation", 165, "mount-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((1,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,)), _v4_cardinality_spec((0,))),
    ("enter-held-input-root", 81, "fd-control-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((1,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,)), _v4_cardinality_spec((0,))),
    ("chroot-into-input-root", 161, "path-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((1,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,)), _v4_cardinality_spec((0,))),
    ("enter-new-root", 80, "path-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((1,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,)), _v4_cardinality_spec((0,))),
    ("select-mapped-gid", 119, "query-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    ("select-mapped-uid", 117, "query-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    ("install-build-signal-mask", 14, "query-entry", "query-exit",
     ("exact-values", 1), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    ("clear-ambient-capabilities", 157, "query-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    ("drop-capability-bounding-set", 157, "query-entry", "scalar-exit",
     ("profile-derived-values", "cap_last_cap-plus-one"),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,))),
    ("drop-capabilities", 126, "query-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    ("close-setup-descriptors", 3, "fd-control-entry", "fd-state-exit",
     ("seed-derived-values", "setup-fd-count"),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1, 2)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,))),
    ("set-no-new-privileges", 157, "query-entry", "scalar-exit",
     ("exact-values", 1), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    ("install-build-filter", 317, "seccomp-install-entry",
     "seccomp-install-exit", ("exact-values", 1),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,))),
)


_V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY_BOUNDS = (
    (1, "write", "fd-io-entry", "io-exit", (0, 1), (0, 1), (0,), (0,), (0,)),
    (2, "open", "path-entry", "open-exit", (1,), (2,), (0,), (0,), (0,)),
    (9, "mmap", "mapping-entry", "mapping-exit", (0, 1), (0,), (1, 2), (0,), (0,)),
    (10, "mprotect", "mapping-entry", "mapping-exit", (0, 1), (0,), (1,), (0,), (0,)),
    (11, "munmap", "mapping-entry", "mapping-exit", (0, 1), (0,), (1,), (0,), (0,)),
    (18, "pwrite64", "fd-io-entry", "io-exit", (1,), (0,), (0,), (0,), (0,)),
    (20, "writev", "fd-io-entry", "io-exit", (0, 1), (0, 1), (0,), (0,), (0,)),
    (25, "mremap", "mapping-entry", "mapping-exit", (0, 1), (0,), (1, 2), (0,), (0,)),
    (26, "msync", "mapping-entry", "mapping-exit", (0, 1), (0,), (0,), (0,), (0,)),
    (76, "truncate", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (77, "ftruncate", "fd-control-entry", "io-exit", (1,), (0,), (0,), (0,), (0,)),
    (82, "rename", "path-entry", "path-mutation-exit", (2, 3), (0,), (0,), (0,), (0,)),
    (83, "mkdir", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (84, "rmdir", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (85, "creat", "path-entry", "open-exit", (1,), (2,), (0,), (0,), (0,)),
    (87, "unlink", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (90, "chmod", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (91, "fchmod", "fd-control-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (257, "openat", "path-entry", "open-exit", (1,), (2,), (0,), (0,), (0,)),
    (258, "mkdirat", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (263, "unlinkat", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (264, "renameat", "path-entry", "path-mutation-exit", (2, 3), (0,), (0,), (0,), (0,)),
    (268, "fchmodat", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
    (296, "pwritev", "fd-io-entry", "io-exit", (1,), (0,), (0,), (0,), (0,)),
    (316, "renameat2", "path-entry", "path-mutation-exit", (2, 3), (0,), (0,), (0,), (0,)),
    (328, "pwritev2", "fd-io-entry", "io-exit", (1,), (0,), (0,), (0,), (0,)),
    (437, "openat2", "path-entry", "open-exit", (1,), (2,), (0,), (0,), (0,)),
    (452, "fchmodat2", "path-entry", "path-mutation-exit", (1,), (0,), (0,), (0,), (0,)),
)
V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY = tuple(
    row[:4] + tuple(_v4_cardinality_spec(item) for item in row[4:])
    for row in _V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY_BOUNDS
)
V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY_FIELDS = (
    "syscall_number", "operation", "entry_kind", "exit_kind",
    "object_edge_counts", "fd_transition_counts",
    "mapping_transition_counts", "fs_transition_counts",
    "task_transition_counts",
)
_V4_BUILD_STATE_OPERATION_CAPTURE_POLICY_BOUNDS = (
    (0, "read", "fd-io-entry", "io-exit", (0, 1), (0, 1), (0,), (0,), (0,)),
    (3, "close", "fd-control-entry", "fd-state-exit", (0,), (1, 2), (0,), (0,), (0,)),
    (8, "lseek", "fd-control-entry", "fd-state-exit", (0,), (1,), (0,), (0,), (0,)),
    (12, "brk", "scalar-entry", "mapping-exit", (0,), (0,), (0, 1), (0,), (0,)),
    (17, "pread64", "fd-io-entry", "io-exit", (0, 1), (0,), (0,), (0,), (0,)),
    (19, "readv", "fd-io-entry", "io-exit", (0, 1), (0, 1), (0,), (0,), (0,)),
    (22, "pipe", "fd-control-entry", "fd-pair-exit", (0,), (4,), (0,), (0,), (0,)),
    (28, "madvise", "mapping-entry", "scalar-exit", (0,), (0,), (0,), (0,), (0,)),
    (32, "dup", "fd-control-entry", "fd-state-exit", (0,), (1,), (0,), (0,), (0,)),
    (33, "dup2", "fd-control-entry", "fd-state-exit", (0,), (0, 3), (0,), (0,), (0,)),
    (56, "clone", "task-create-entry", "scalar-exit", (0,), (0,), (0,), (0,), (0,)),
    (57, "fork", "task-create-entry", "scalar-exit", (0,), (0,), (0,), (0,), (0,)),
    (58, "vfork", "task-create-entry", "scalar-exit", (0,), (0,), (0,), (0,), (0,)),
    (72, "fcntl", "fd-control-entry", "fd-state-exit", (0,), (0, 1), (0,), (0,), (0,)),
    (80, "chdir", "path-entry", "scalar-exit", (1,), (0,), (0,), (1,), (0,)),
    (81, "fchdir", "fd-control-entry", "scalar-exit", (1,), (0,), (0,), (1,), (0,)),
    (95, "umask", "scalar-entry", "scalar-exit", (0,), (0,), (0,), (1,), (0,)),
    (157, "prctl", "fd-control-entry", "scalar-exit", (0,), (0,), (0,), (0,), (0,)),
    (217, "getdents64", "fd-io-entry", "io-exit", (0, 1), (0, 1), (0,), (0,), (0,)),
    (292, "dup3", "fd-control-entry", "fd-state-exit", (0,), (0, 3), (0,), (0,), (0,)),
    (293, "pipe2", "fd-control-entry", "fd-pair-exit", (0,), (4,), (0,), (0,), (0,)),
    (295, "preadv", "fd-io-entry", "io-exit", (0, 1), (0,), (0,), (0,), (0,)),
    (327, "preadv2", "fd-io-entry", "io-exit", (0, 1), (0,), (0,), (0,), (0,)),
    (436, "close_range", "fd-control-entry", "scalar-exit", (0,), (0, 8_192), (0,), (0,), (0,)),
)
V4_BUILD_STATE_OPERATION_CAPTURE_POLICY = tuple(
    row[:4] + tuple(_v4_cardinality_spec(item) for item in row[4:])
    for row in _V4_BUILD_STATE_OPERATION_CAPTURE_POLICY_BOUNDS
)
V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY_FIELDS = (
    "event_kind", "object_edge_counts", "fd_transition_counts",
    "mapping_transition_counts", "fs_transition_counts",
    "task_transition_counts",
)
_V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY_BOUNDS = (
    ("namespace-clone", (0,), (1,), (1,), (2,), (1,)),
    ("interrupt-stop", (0,), (0,), (0,), (0,), (1,)),
    ("peer-interrupt-stop", (0,), (0,), (0,), (0,), (0,)),
    ("child-initial-stop", (0,), (0,), (0,), (0,), (1,)),
    ("signal-delivery-stop", (0,), (0,), (0,), (0,), (0,)),
    ("group-stop", (0,), (0,), (0,), (0,), (1,)),
    ("fork", (0,), (1,), (1,), (1,), (1,)),
    ("vfork", (0,), (1,), (1,), (1,), (2,)),
    ("clone", (0,), (1,), (1,), (1,), (1,)),
    ("vfork-done", (0,), (0,), (0,), (0,), (1,)),
    ("exec", (1,), (0, 8_192), (1,), (0,), (1,)),
    ("exit", (0,), (0,), (0,), (0,), (1,)),
    ("terminal-wait", (0,), (0,), (0,), (0,), (1,)),
    ("pre-output-walk", (1,), (0,), (0,), (0,), (0,)),
    ("post-output-walk", (2, 4_097), (0,), (0,), (0,), (0,)),
    ("output-hash-barrier", (1, 4_096), (0,), (0,), (0,), (0,)),
)
V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY = tuple(
    (row[0],) + tuple(_v4_cardinality_spec(item) for item in row[1:])
    for row in _V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY_BOUNDS
)
V4_BUILD_FCNTL_COMMAND_POLICY = (
    (0, "F_DUPFD", "fd-duplicate"),
    (1, "F_GETFD", "query"),
    (2, "F_SETFD", "fd-cloexec-change"),
    (3, "F_GETFL", "query"),
    (4, "F_SETFL", "open-description-status-change"),
    (1_030, "F_DUPFD_CLOEXEC", "fd-duplicate"),
)
V4_BUILD_MADVISE_ALLOWED_ADVICE = (
    0, 1, 2, 3, 4, 8, 14, 15, 16, 17, 20, 21, 22, 23, 25,
)
V4_BUILD_MADVISE_REJECTED_ADVICE = (9,)
V4_BUILD_CLOSE_RANGE_ALLOWED_FLAGS = (0, 4)
V4_BUILD_CLOSE_RANGE_REJECTED_FLAGS = (2, 6)
V4_BUILD_MMAP_FIXED_FLAG = 0x10
V4_BUILD_MREMAP_ALLOWED_FLAGS = (0, 1, 3)
V4_BUILD_MREMAP_REJECTED_FLAGS = (2, 4, 5, 6, 7)
V4_BUILD_MREMAP_OLD_SIZE_POLICY = (
    "positive-mapped-range-reject-zero-before-resume-v1"
)
V4_BUILD_RENAMEAT2_ALLOWED_FLAGS = (0, 1)
V4_BUILD_RENAME_EQUAL_OPERAND_POLICY = "reject-before-resume-v1"
V4_BUILD_STATE_CHANGING_FAILURE_POLICY_FIELDS = (
    "syscall_number", "operation", "return_class", "exit_kind",
    "object_edge_counts", "fd_transition_counts",
    "mapping_transition_counts", "fs_transition_counts",
    "task_transition_counts",
)
V4_BUILD_STATE_CHANGING_FAILURE_POLICY = (
    (
        3, "close", "negative-except-ebadf-after-valid-entry-fd",
        "fd-state-exit", _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((1, 2)), _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
    ),
)
V4_BUILD_EXEC_SYSCALLS = (
    (59, "execve"),
    (322, "execveat"),
)
V4_BUILD_NONRETURNING_SYSCALLS = (
    (60, "exit"),
    (231, "exit_group"),
)
V4_BUILD_EXIT_GROUP_POLICY = (
    "exactly-one-live-thread-group-member-reject-before-resume-v1"
)
V4_BUILD_TASK_FIELDS = (
    "index", "task_identity", "thread_group_identity", "parent_task_index",
    "creation_event_index", "initial_stop_event_index", "exec_count",
    "exit_event_index", "terminal_wait_event_index",
)
V4_BUILD_FATAL_SIGNAL_POLICY = (
    "reject-signal-caused-exit-before-authentication-v1"
)
V4_BUILD_REJECTED_CONTROL_SYSCALLS = (
    (15, "rt_sigreturn"),
    (62, "kill"),
    (202, "futex"),
    (219, "restart_syscall"),
    (234, "tgkill"),
)
V4_BUILD_ARCH_PRCTL_ALLOWED_OPERATIONS = (
    (0x1001, "ARCH_SET_GS"),
    (0x1002, "ARCH_SET_FS"),
    (0x1003, "ARCH_GET_FS"),
    (0x1004, "ARCH_GET_GS"),
)
V4_BUILD_FLOCK_ALLOWED_OPERATIONS = (1, 2, 5, 6, 8)
V4_BUILD_CONTROL_OPERATION_CAPTURE_POLICY_FIELDS = (
    "syscall_number", "operation", "entry_kind", "exit_kind",
    "argument_policy", "input_region_policy", "output_region_policy",
    "object_edge_counts", "fd_transition_counts",
    "mapping_transition_counts", "fs_transition_counts",
    "task_transition_counts",
)
V4_BUILD_CONTROL_OPERATION_CAPTURE_POLICY = (
    (13, "rt_sigaction", "query-entry", "query-exit",
     "signal-1-through-64-act-oldact-sigsetsize-8-exact",
     ((1, "input", "fixed-bytes", 32, "if-nonnull", "same-as-entry"),),
     ((2, "output", "fixed-bytes", 32, "if-success-nonnull", "fixed"),),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0, 1))),
    (14, "rt_sigprocmask", "query-entry", "query-exit",
     "sig-block-unblock-setmask-set-oldset-sigsetsize-8-exact",
     ((1, "input", "fixed-bytes", 8, "if-nonnull", "same-as-entry"),),
     ((2, "output", "fixed-bytes", 8, "if-success-nonnull", "fixed"),),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0, 1))),
    (61, "wait4", "query-entry", "query-exit",
     "registered-child-or-minus-one-options-wnohang-wuntraced-wcontinued-exact",
     (),
     ((1, "output", "fixed-bytes", 4, "if-positive-return-nonnull", "fixed"),
      (3, "output", "fixed-bytes", 144, "if-positive-return-nonnull", "fixed")),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0, 1))),
    (73, "flock", "fd-control-entry", "scalar-exit",
     "operation-in-v4-build-flock-allowed-operations-exact",
     (), (),
     _v4_cardinality_spec((1,)), _v4_cardinality_spec((1,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,))),
    (131, "sigaltstack", "query-entry", "query-exit",
     "nullable-new-and-old-stack-x86-64-stack-t-exact",
     ((0, "input", "fixed-bytes", 24, "if-nonnull", "same-as-entry"),),
     ((1, "output", "fixed-bytes", 24, "if-success-nonnull", "fixed"),),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0, 1))),
    (158, "arch_prctl", "query-entry", "query-exit",
     "operation-in-v4-build-arch-prctl-allowed-operations-exact",
     (),
     ((1, "output", "fixed-bytes", 8,
       "if-success-nonnull-get-operation", "fixed"),),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0, 1))),
    (218, "set_tid_address", "query-entry", "scalar-exit",
     "clear-child-tid-pointer-exact", (), (),
     _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((1,))),
    (273, "set_robust_list", "query-entry", "scalar-exit",
     "robust-list-head-pointer-length-24-exact",
     ((0, "input", "fixed-bytes", 24, "always-nonnull", "same-as-entry"),),
     (),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,))),
    (334, "rseq", "query-entry", "scalar-exit",
     "register-or-unregister-rseq-32-signature-0x53053053-exact",
     ((0, "input", "fixed-bytes", 32, "if-nonnull", "same-as-entry"),),
     ((0, "output", "fixed-bytes", 32, "if-success-nonnull", "fixed"),),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
     _v4_cardinality_spec((1,))),
)
V4_BUILD_PRCTL_ALLOWED_OPERATIONS = (
    (21, "PR_GET_SECCOMP"),
    (39, "PR_GET_NO_NEW_PRIVS"),
)
V4_BUILD_PRLIMIT64_POLICY = "query-only-null-new-limit-pointer-v1"
V4_BUILD_REJECTED_STATELESS_SYSCALLS = (
    (23, "select-unobservable-kernel-fdtable-capacity"),
)
V4_BUILD_STATELESS_ALLOWED_SYSCALLS = (
    (4, "stat"),
    (5, "fstat"),
    (6, "lstat"),
    (7, "poll"),
    (21, "access"),
    (24, "sched_yield"),
    (27, "mincore"),
    (35, "nanosleep"),
    (39, "getpid"),
    (63, "uname"),
    (74, "fsync"),
    (75, "fdatasync"),
    (79, "getcwd"),
    (89, "readlink"),
    (96, "gettimeofday"),
    (97, "getrlimit"),
    (98, "getrusage"),
    (99, "sysinfo"),
    (100, "times"),
    (102, "getuid"),
    (104, "getgid"),
    (107, "geteuid"),
    (108, "getegid"),
    (110, "getppid"),
    (111, "getpgrp"),
    (118, "getresuid"),
    (120, "getresgid"),
    (121, "getpgid"),
    (137, "statfs"),
    (138, "fstatfs"),
    (186, "gettid"),
    (201, "time"),
    (228, "clock_gettime"),
    (229, "clock_getres"),
    (230, "clock_nanosleep"),
    (262, "newfstatat"),
    (267, "readlinkat"),
    (271, "ppoll"),
    (277, "sync_file_range"),
    (302, "prlimit64"),
    (318, "getrandom"),
    (332, "statx"),
    (439, "faccessat2"),
)
V4_BUILD_STATELESS_PATH_SYSCALLS = (
    4, 6, 21, 89, 137, 262, 267, 332, 439,
)
V4_BUILD_STATELESS_FD_SYSCALLS = (
    5, 74, 75, 138, 277,
)
V4_BUILD_QUERY_ABI_REGION_POLICY_FIELDS = (
    "argument_index", "direction", "length_kind", "length_value",
    "condition", "post_length_kind",
)
V4_BUILD_QUERY_ABI_LENGTH_KINDS = (
    "fixed-bytes", "argument-bytes", "nfds-times-pollfd-8",
    "pages-covered-by-range",
)
V4_BUILD_QUERY_ABI_LENGTH_FORMULA_FIELDS = (
    "length_kind", "formula", "input_bounds", "overflow_policy",
)
V4_BUILD_QUERY_ABI_LENGTH_FORMULAS = (
    (
        "fixed-bytes", "exact-nonnegative-length-value-bytes",
        "0-through-1048576", "reject-before-copy-if-over-region-cap",
    ),
    (
        "argument-bytes", "unsigned-argument[length_value]",
        "0-through-1048576", "checked-unsigned-64-bit",
    ),
    (
        "nfds-times-pollfd-8", "unsigned-argument[length_value]*8",
        "nfds-0-through-4096", "checked-unsigned-64-bit",
    ),
    (
        "pages-covered-by-range", "(length+4095)//4096",
        "page-aligned-address-and-length-1-through-4294967296",
        "checked-add-unsigned-64-bit-and-result-at-most-1048576",
    ),
)
V4_BUILD_QUERY_ABI_CONDITIONS = (
    "always-nonnull", "if-nonnull", "if-success-nonnull",
    "if-raw-return-minus-516-nonnull", "if-nonnull-after-exit",
    "if-positive-return-nonnull", "if-success-nonnull-get-operation",
    "if-valid-nonzero-ppoll-timeout-nonnull",
)
V4_BUILD_QUERY_ABI_POST_LENGTH_KINDS = (
    "same-as-entry", "fixed", "positive-return",
    "positive-return-clipped-to-region",
)
V4_BUILD_CLOCK_NANOSLEEP_ALLOWED_FLAGS = (0, 1)
V4_BUILD_CLOCK_ID_POLICY = (
    (0, "CLOCK_REALTIME"),
    (1, "CLOCK_MONOTONIC"),
    (2, "CLOCK_PROCESS_CPUTIME_ID"),
    (3, "CLOCK_THREAD_CPUTIME_ID"),
    (4, "CLOCK_MONOTONIC_RAW"),
    (5, "CLOCK_REALTIME_COARSE"),
    (6, "CLOCK_MONOTONIC_COARSE"),
    (7, "CLOCK_BOOTTIME"),
    (8, "CLOCK_REALTIME_ALARM"),
    (9, "CLOCK_BOOTTIME_ALARM"),
    (11, "CLOCK_TAI"),
)
V4_BUILD_CLOCK_GETTIME_ALLOWED_IDS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11)
V4_BUILD_CLOCK_GETRES_ALLOWED_IDS = V4_BUILD_CLOCK_GETTIME_ALLOWED_IDS
V4_BUILD_CLOCK_NANOSLEEP_ALLOWED_CLOCK_IDS = (0, 1, 7, 11)
V4_BUILD_RAW_RESTART_RESULTS = (
    (-512, "ERESTARTSYS"),
    (-513, "ERESTARTNOINTR"),
    (-514, "ERESTARTNOHAND"),
    (-516, "ERESTART_RESTARTBLOCK"),
)
V4_BUILD_RAW_RESTART_POLICY = (
    "capture-required-output-then-reject-at-syscall-exit-without-resume-v1"
)
V4_BUILD_NEWFSTATAT_ALLOWED_FLAGS = (0, 0x100, 0x1000, 0x1100)
V4_BUILD_GETRANDOM_ALLOWED_FLAGS = (0, 1, 2, 3, 4, 5, 6, 7)
V4_BUILD_FACCESSAT2_ALLOWED_FLAG_MASK = 0x1300
V4_BUILD_ACCESS_ALLOWED_MODES = (0, 1, 2, 3, 4, 5, 6, 7)
V4_BUILD_RLIMIT_RESOURCE_POLICY = (
    (0, "RLIMIT_CPU"), (1, "RLIMIT_FSIZE"), (2, "RLIMIT_DATA"),
    (3, "RLIMIT_STACK"), (4, "RLIMIT_CORE"), (5, "RLIMIT_RSS"),
    (6, "RLIMIT_NPROC"), (7, "RLIMIT_NOFILE"), (8, "RLIMIT_MEMLOCK"),
    (9, "RLIMIT_AS"), (10, "RLIMIT_LOCKS"), (11, "RLIMIT_SIGPENDING"),
    (12, "RLIMIT_MSGQUEUE"), (13, "RLIMIT_NICE"),
    (14, "RLIMIT_RTPRIO"), (15, "RLIMIT_RTTIME"),
)
V4_BUILD_RUSAGE_WHO_POLICY = (
    (-1, "RUSAGE_CHILDREN"), (0, "RUSAGE_SELF"), (1, "RUSAGE_THREAD"),
)
V4_BUILD_STATX_ALLOWED_FLAGS = (
    0x0000, 0x0100, 0x0800, 0x0900, 0x1000, 0x1100, 0x1800, 0x1900,
    0x2000, 0x2100, 0x2800, 0x2900, 0x3000, 0x3100, 0x3800, 0x3900,
    0x4000, 0x4100, 0x4800, 0x4900, 0x5000, 0x5100, 0x5800, 0x5900,
)
V4_BUILD_STATX_ALLOWED_MASK = 0x0000_3FFF
_V4_QUERY_INPUT_REGION_POLICIES = {
    7: ((0, "input", "nfds-times-pollfd-8", 1, "if-nonnull", "same-as-entry"),),
    35: ((0, "input", "fixed-bytes", 16, "always-nonnull", "same-as-entry"),),
    230: ((2, "input", "fixed-bytes", 16, "always-nonnull", "same-as-entry"),),
    271: (
        (0, "input", "nfds-times-pollfd-8", 1, "if-nonnull", "same-as-entry"),
        (2, "input", "fixed-bytes", 16, "if-nonnull", "same-as-entry"),
        (3, "input", "argument-bytes", 4, "if-nonnull", "same-as-entry"),
    ),
}
_V4_QUERY_OUTPUT_REGION_POLICIES = {
    4: ((1, "output", "fixed-bytes", 144, "if-success-nonnull", "fixed"),),
    5: ((1, "output", "fixed-bytes", 144, "if-success-nonnull", "fixed"),),
    6: ((1, "output", "fixed-bytes", 144, "if-success-nonnull", "fixed"),),
    7: ((0, "output", "nfds-times-pollfd-8", 1, "if-nonnull-after-exit", "same-as-entry"),),
    27: ((2, "output", "pages-covered-by-range", 1,
          "if-success-nonnull", "fixed"),),
    35: ((1, "output", "fixed-bytes", 16,
          "if-raw-return-minus-516-nonnull", "fixed"),),
    63: ((0, "output", "fixed-bytes", 390, "if-success-nonnull", "fixed"),),
    79: ((0, "output", "argument-bytes", 1, "if-success-nonnull", "positive-return-clipped-to-region"),),
    89: ((1, "output", "argument-bytes", 2, "if-success-nonnull", "positive-return-clipped-to-region"),),
    96: (
        (0, "output", "fixed-bytes", 16, "if-success-nonnull", "fixed"),
        (1, "output", "fixed-bytes", 8, "if-success-nonnull", "fixed"),
    ),
    97: ((1, "output", "fixed-bytes", 16, "if-success-nonnull", "fixed"),),
    98: ((1, "output", "fixed-bytes", 144, "if-success-nonnull", "fixed"),),
    99: ((0, "output", "fixed-bytes", 112, "if-success-nonnull", "fixed"),),
    100: ((0, "output", "fixed-bytes", 32, "if-success-nonnull", "fixed"),),
    118: (
        (0, "output", "fixed-bytes", 4, "if-success-nonnull", "fixed"),
        (1, "output", "fixed-bytes", 4, "if-success-nonnull", "fixed"),
        (2, "output", "fixed-bytes", 4, "if-success-nonnull", "fixed"),
    ),
    120: (
        (0, "output", "fixed-bytes", 4, "if-success-nonnull", "fixed"),
        (1, "output", "fixed-bytes", 4, "if-success-nonnull", "fixed"),
        (2, "output", "fixed-bytes", 4, "if-success-nonnull", "fixed"),
    ),
    137: ((1, "output", "fixed-bytes", 120, "if-success-nonnull", "fixed"),),
    138: ((1, "output", "fixed-bytes", 120, "if-success-nonnull", "fixed"),),
    201: ((0, "output", "fixed-bytes", 8, "if-success-nonnull", "fixed"),),
    228: ((1, "output", "fixed-bytes", 16, "if-success-nonnull", "fixed"),),
    229: ((1, "output", "fixed-bytes", 16, "if-success-nonnull", "fixed"),),
    230: ((3, "output", "fixed-bytes", 16,
           "if-raw-return-minus-516-nonnull", "fixed"),),
    262: ((2, "output", "fixed-bytes", 144, "if-success-nonnull", "fixed"),),
    267: ((2, "output", "argument-bytes", 3, "if-success-nonnull", "positive-return-clipped-to-region"),),
    271: (
        (0, "output", "nfds-times-pollfd-8", 1,
         "if-nonnull-after-exit", "same-as-entry"),
        (2, "output", "fixed-bytes", 16,
         "if-valid-nonzero-ppoll-timeout-nonnull", "fixed"),
    ),
    302: ((3, "output", "fixed-bytes", 16, "if-success-nonnull", "fixed"),),
    318: ((0, "output", "argument-bytes", 1, "if-success-nonnull", "positive-return-clipped-to-region"),),
    332: ((4, "output", "fixed-bytes", 256, "if-success-nonnull", "fixed"),),
}
_V4_STATELESS_ARGUMENT_POLICIES = {
    4: "path-arg0-nul-stat-output-arg1-exact",
    5: "live-fd-arg0-stat-output-arg1-exact",
    6: "path-arg0-nul-lstat-output-arg1-exact",
    7: "nfds-at-most-4096-timeout-signed-int-exact",
    21: "path-arg0-nul-mode-in-v4-build-access-allowed-modes-exact",
    24: "six-zero-arguments-exact",
    27: "mapped-page-aligned-range-exact",
    35: "valid-timespec-exact",
    39: "six-zero-arguments-exact",
    63: "nonnull-utsname-output-arg0-exact",
    74: "live-fd-arg0-six-tail-zero-exact",
    75: "live-fd-arg0-six-tail-zero-exact",
    79: "nonnull-buffer-arg0-size-1-through-4096-exact",
    89: "buffer-length-0-through-1048576-exact",
    96: "nullable-timeval-and-timezone-exact",
    97: "resource-selector-in-v4-build-rlimit-resource-policy-exact",
    98: "who-selector-in-v4-build-rusage-who-policy-exact",
    99: "nonnull-sysinfo-output-arg0-exact",
    100: "nullable-tms-output-arg0-exact",
    102: "six-zero-arguments-exact",
    104: "six-zero-arguments-exact",
    107: "six-zero-arguments-exact",
    108: "six-zero-arguments-exact",
    110: "six-zero-arguments-exact",
    111: "six-zero-arguments-exact",
    118: "three-nonnull-uid32-output-pointers-exact",
    120: "three-nonnull-gid32-output-pointers-exact",
    121: "registered-pid-or-zero-exact",
    137: "path-arg0-nul-statfs-output-arg1-exact",
    138: "live-fd-arg0-statfs-output-arg1-exact",
    186: "six-zero-arguments-exact",
    201: "nullable-time64-output-arg0-exact",
    228: "clock-id-in-v4-build-clock-id-policy-exact",
    229: "clock-id-in-v4-build-clock-id-policy-nullable-result-exact",
    230: "clock-id-in-v4-clock-nanosleep-set-flags-zero-or-one-exact",
    262: "flags-in-v4-build-newfstatat-allowed-flags-exact",
    267: "dirfd-path-buffer-length-0-through-1048576-exact",
    271: "nfds-at-most-4096-timespec-sigmask-size-8-exact",
    277: "live-fd-offset-and-length-u64-flags-zero-exact",
    302: "pid-zero-or-registered-task-resource-in-v4-build-rlimit-policy-null-new-limit-exact",
    318: "length-0-through-1048576-flags-in-v4-getrandom-policy-exact",
    332: "flags-in-v4-build-statx-allowed-flags-mask-subset-v4-build-statx-allowed-mask-exact",
    439: "mode-rwx-or-f-ok-flags-subset-0x1300-exact",
}
V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY_FIELDS = (
    "syscall_number", "operation", "entry_kind", "exit_kind",
    "argument_policy", "input_region_policy", "output_region_policy",
    "object_edge_counts",
    "fd_transition_counts", "mapping_transition_counts",
    "fs_transition_counts", "task_transition_counts",
)
V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY = tuple(
    (
        number,
        operation,
        (
            "path-entry" if number in V4_BUILD_STATELESS_PATH_SYSCALLS
            else "fd-control-entry"
            if number in V4_BUILD_STATELESS_FD_SYSCALLS
            else "query-entry"
        ),
        "query-exit",
        _V4_STATELESS_ARGUMENT_POLICIES.get(
            number, "all-unused-arguments-zero-or-pinned-scalar-abi-exact",
        ),
        _V4_QUERY_INPUT_REGION_POLICIES.get(number, ()),
        _V4_QUERY_OUTPUT_REGION_POLICIES.get(number, ()),
        _v4_cardinality_spec((0, 1))
        if number in (
            V4_BUILD_STATELESS_PATH_SYSCALLS
            + V4_BUILD_STATELESS_FD_SYSCALLS
        )
        else _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)),
    )
    for number, operation in V4_BUILD_STATELESS_ALLOWED_SYSCALLS
)
V4_BUILD_STATELESS_NEGATIVE_RESULT_POLICY = (
    "all-negative-raw-results-reject-at-exit-without-resume-or-publication-v1"
)
V4_BUILD_FILTER_RESULT_OPERATION_CAPTURE_POLICY_FIELDS = (
    "syscall_number", "operation", "entry_kind", "exit_kind",
    "required_raw_return", "object_edge_counts", "fd_transition_counts",
    "mapping_transition_counts", "fs_transition_counts",
    "task_transition_counts",
)
V4_BUILD_FILTER_RESULT_OPERATION_CAPTURE_POLICY = (
    (
        435, "clone3-filter-enosys", "scalar-entry", "scalar-exit", -38,
        _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)),
    ),
)
V4_BUILD_FILTER_RESULT_OPERATION_POLICY = (
    "post-filter-resume-once-require-installed-filter-result-no-effects-v1"
)
V4_BUILD_NONRETURNING_CAPTURE_POLICY_FIELDS = (
    "syscall_number", "operation", "entry_kind", "terminal_kind",
    "entry_object_edge_counts", "entry_fd_transition_counts",
    "entry_mapping_transition_counts", "entry_fs_transition_counts",
    "entry_task_transition_counts",
)
V4_BUILD_NONRETURNING_CAPTURE_POLICY = tuple(
    (
        number, operation, "scalar-entry", "exit",
        _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)), _v4_cardinality_spec((0,)),
        _v4_cardinality_spec((0,)),
    )
    for number, operation in V4_BUILD_NONRETURNING_SYSCALLS
)
V4_BUILD_SYSCALL_DISPOSITION_POLICY = (
    "phase-split-allow-only-modeled-control-query-filter-result-deny-all-"
    "other-native-v4"
)
V4_BUILD_SYSCALL_DISPOSITION_SCHEMA = 4
V4_BUILD_SYSCALL_DISPOSITION_KIND = (
    "candle-flyspeck-isolated-native-build-syscall-disposition-v4"
)
V4_BUILD_REJECTED_OUTPUT_MUTATION_SYSCALLS = (
    (16, "ioctl"),
    (40, "sendfile"),
    (86, "link"),
    (88, "symlink"),
    (92, "chown"),
    (93, "fchown"),
    (94, "lchown"),
    (132, "utime"),
    (133, "mknod"),
    (188, "setxattr"),
    (189, "lsetxattr"),
    (190, "fsetxattr"),
    (197, "removexattr"),
    (198, "lremovexattr"),
    (199, "fremovexattr"),
    (216, "remap_file_pages"),
    (235, "utimes"),
    (259, "mknodat"),
    (260, "fchownat"),
    (261, "futimesat"),
    (265, "linkat"),
    (266, "symlinkat"),
    (275, "splice"),
    (276, "tee"),
    (278, "vmsplice"),
    (280, "utimensat"),
    (285, "fallocate"),
    (326, "copy_file_range"),
    (329, "pkey_mprotect"),
)
V4_BUILD_OUTPUT_GENERATION_FIELDS = (
    "index", "object_type", "creator_task_index", "creation_event_index",
    "initial_identity", "lifecycle_event_indices", "final_state",
    "post_tree_entry_index", "final_identity",
)
V4_BUILD_OUTPUT_GENERATION_FINAL_STATES = ("published", "deleted")
V4_BUILD_OUTPUT_JOIN_FIELDS = (
    "index", "post_tree_entry_index", "output_generation_index",
    "lifecycle_event_indices", "quiescence_event_index", "final_identity",
    "final_mode", "final_st_nlink", "final_bytes", "final_sha256",
    "complete",
)
V4_BUILD_OUTPUT_ROLES = (
    "target-executable",
    "intermediate-object",
    "static-library",
    "shared-library",
    "runtime-data",
)
V4_RUNTIME_MEMBER_ROLES = (
    "python-standard-library",
    "python-native-extension",
    "elf-library",
    "runtime-data",
)
V4_NATIVE_BUILD_RECEIPT_KIND = (
    "candle-flyspeck-isolated-native-build-receipt-v1"
)
V4_PYTHON_RUNTIME_CLOSURE_KIND = (
    "candle-flyspeck-python-runtime-closure-v1"
)
V4_NATIVE_RUNTIME_CLOSURE_KIND = (
    "candle-flyspeck-native-runtime-closure-v1"
)
V4_SECCOMP_FILTER_AUTHORITY_KIND = (
    "candle-flyspeck-seccomp-filter-authority-v1"
)
V4_GLIBC_STUB_PROVENANCE_KIND = (
    "candle-flyspeck-glibc-posix-spawn-stub-provenance-v1"
)
V4_AUTHORITY_CAPSULE_KIND = "candle-flyspeck-pristine-authority-capsule-v1"
V4_AUTHORITY_CAPSULE_POLICY = (
    "retained-inline-canonical-authority-objects-v1"
)
V4_INVENTORY_NORMALIZATION_POLICY = "preserve-bytes-strip-write-bits-v1"

V4_POSITIONAL_REQUEST_BINDING_KIND = (
    "candle-flyspeck-pristine-positional-request-binding-v1"
)
V4_POSITIONAL_REQUEST_BINDING_POLICY = (
    "same-exec-argv-open-private-immutable-object-v1"
)
V4_EMPTY_STDIN_BINDING_KIND = (
    "candle-flyspeck-pristine-empty-stdin-binding-v1"
)
V4_EMPTY_STDIN_BINDING_POLICY = (
    "trace-joined-supervisor-closed-pipe-eof-v1"
)
V4_SOURCE_CONSUMPTION_JOINS_KIND = (
    "candle-flyspeck-pristine-source-consumption-joins-v1"
)
V4_SOURCE_CONSUMPTION_JOINS_POLICY = (
    "stock-ledger-private-object-content-join-v1"
)
V4_LP_DESERIALIZER_JOINS_KIND = (
    "candle-flyspeck-pristine-lp-deserializer-joins-v1"
)
V4_LP_DESERIALIZER_JOINS_POLICY = (
    "successful-deserializer-private-object-marker-join-v1"
)
V4_LP_WRAPPER_CONTRACT = "original-deserializer-return-before-marker-v1"
V4_NAMESPACE_REVALIDATION_KIND = "candle-flyspeck-v4-namespace-revalidation-v1"
V4_NAMESPACE_REVALIDATION_POLICY = (
    "reopen-all-control-and-authority-inventory-edges-v1"
)
V4_ANCHORED_PUBLICATION_POLICY_KIND = (
    "candle-flyspeck-anchored-self-publication-policy-v2"
)
V4_ANCHORED_PUBLICATION_OBSERVATION_KIND = (
    "candle-flyspeck-anchored-self-publication-observation-v2"
)
V4_PUBLICATION_POLICIES = (
    "publish-envelope-v2",
    "publish-pending-candidate-v2",
    "publish-completion-v2",
)
V4_POSTFLIGHT_RUNTIME_ROOT_RECEIPT_KIND = (
    "candle-flyspeck-postflight-runtime-root-receipt-v1"
)
V4_POSTFLIGHT_RUNTIME_ROOT_POLICY = (
    "retained-python-closure-read-only-pivot-root-v1"
)

V4_SEMANTIC_COMPLETE_STATUS = "complete-observed-unapproved"
V4_NATIVE_CLOSURE_STATUS = "full-run-observation-complete-unapproved"
V4_SOURCE_REDERIVATION_STATUS = "complete-unapproved"
V4_CAPTURE_ENVELOPE_STATUS = "captured-awaiting-postflight-unapproved"
V4_PENDING_CANDIDATE_STATUS = "pending-postflight-unapproved"
V4_CAPTURE_COMPLETION_STATUS = "capture-complete-unapproved"
V4_POSTFLIGHT_RESULT_STATUS = "validated-unapproved"
V4_AUTHENTICATION_STATUS = "not-authenticated"

V4_MARKER_CONTRACT = {
    "protocol": V4_MARKER_PROTOCOL,
    "session_start": "CANDLE_PRISTINE_DIRECT_REFERENCE_START_V4",
    "native_load": "CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V4",
    "startup_baseline": "CANDLE_PRISTINE_DIRECT_STARTUP_BASELINE_V4",
    "strictbuild_complete": (
        "CANDLE_PRISTINE_DIRECT_STRICTBUILD_COMPLETE_V4"
    ),
    "action_complete": "CANDLE_PRISTINE_DIRECT_ACTION_COMPLETE_V4",
    "lp_success": "CANDLE_PRISTINE_DIRECT_LP_SUCCESS_V4",
    "semantic_observation": "CANDLE_PRISTINE_DIRECT_SEMANTIC_V4",
    "session_complete": "CANDLE_PRISTINE_DIRECT_REFERENCE_COMPLETE_V4",
    "nonce_in_every_marker": True,
}

V4_CONTROL_MAX_BYTES = 67_108_864
V4_CONTROL_READ_MAX_BYTES = 67_108_865
V4_REQUEST_PAYLOAD_MAX_BYTES = 67_108_864
V4_BUNDLE_MAX_BYTES = 67_108_864
V4_SELF_PUBLICATION_MAX_BYTES = 67_108_864
V4_EVIDENCE_OBJECT_MAX_BYTES = 67_108_864
V4_FAILED_DIAGNOSTIC_MAX_BYTES = 16_777_216
V4_AUTHORITY_CAPSULE_MAX_BYTES = 721_420_288
V4_AUTHORITY_CAPSULE_READ_MAX_BYTES = 721_420_289
V4_POSTFLIGHT_RESULT_MAX_BYTES = 1_073_741_824
V4_POSTFLIGHT_RESULT_READ_MAX_BYTES = 1_073_741_825
V4_TRACE_CHUNK_MAX_BYTES = 67_108_864
V4_TRACE_CHUNK_COUNT_MAX = 4_096
V4_TRACE_TOTAL_MAX_BYTES = 274_877_906_944
V4_AUTHORITY_OBJECT_MAX_BYTES = 33_554_432
V4_AUTHORITY_OBJECT_READ_MAX_BYTES = 33_554_433
V4_FIXED_SOURCE_MAX_BYTES = 16_777_216
V4_STARTUP_DESIGN_MAX_BYTES = 1_048_576
V4_AUTHORITY_CAPSULE_DECODED_MAX_BYTES = 537_919_488
V4_EXACT_JSON_TYPE_NODE_MAX = 262_144
V4_EXACT_JSON_TYPE_DEPTH_MAX = 64
V4_REQUEST_RESULT_PAYLOAD_MAX_BYTES = 67_108_864
V4_REQUEST_RESULT_HEADER_BYTES = 38
V4_COLLECTION_RECORD_MAX_BYTES = 67_108_864
V4_COLLECTION_RECORD_COUNT = 6
V4_COLLECTION_FRAME_MAX_BYTES = 402_653_396
V4_SOURCE_TREE_MEMBER_MAX = 65_536
V4_SOURCE_TREE_FILE_MAX_BYTES = 67_108_864
V4_SOURCE_TREE_TOTAL_MAX_BYTES = 4_294_967_296
V4_BUILD_ENVIRONMENT_MAX = 4_096
V4_SECCOMP_INSTRUCTION_MAX = 4_096
V4_INVENTORY_OBJECT_MAX = 131_072
V4_INVENTORY_FILE_MAX_BYTES = 1_073_741_824
V4_INVENTORY_TOTAL_MAX_BYTES = 68_719_476_736
V4_NAMESPACE_EDGE_MAX = 16_384
V4_TRACE_CHUNK_COUNT_MIN = 1
V4_INPUT_COPY_CHUNK_MAX = 65_536
V4_POSTFLIGHT_MAPPING_MAX = 262_144
V4_POSTFLIGHT_DIRECTORY_MAX = 262_144
V4_EMPTY_STDIN_EVENT_MAX = 4_096

V4_BUNDLE_FIELDS = frozenset({
    "schema", "kind", "role", "reference_ordinal", "nonce_kind",
    "session_nonce", "boundary_id", "plan", "request",
    "request_generation_receipt", "collection_authority_receipt",
    "capture_envelope", "source_rederivation", "coverage",
    "pending_candidate", "capture_completion", "approval_included",
    "pft_used", "s2_eligible", "s3_eligible", "s2_s3_evidence",
})
V4_PAIR_FIELDS = frozenset({
    "schema", "kind", "role", "first", "second", "shared_authority",
    "shared_evidence_contracts", "distinct_attempt_roots",
    "distinct_ordinals", "distinct_nonces", "semantic_equal",
    "coverage_equal", "approval_included", "pft_used", "s2_eligible",
    "s3_eligible", "s2_s3_evidence",
})

HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX32 = re.compile(r"[0-9a-f]{32}")
PFT_NAMESPACE = re.compile(r"(?:^|[/:._-])pft(?:$|[/:._-])", re.IGNORECASE)


class ProtocolError(ValueError):
    """A raw pristine-reference protocol value is malformed or overclaims."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolError(message)


def is_int(value: object) -> bool:
    return type(value) is int


def canonical_value_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_value_bytes(value)).hexdigest()


def v4_ordered_field_digest(
    value: object, fields: tuple[str, ...], domain: str,
) -> str:
    require(type(value) is dict, "V4 ordered-field digest value is not exact dict")
    require(
        type(fields) is tuple and fields and
        all(type(field) is str and field for field in fields) and
        len(set(fields)) == len(fields),
        "V4 ordered-field digest fields are malformed",
    )
    require(
        type(domain) is str and domain.isascii() and domain and "\x00" not in domain,
        "V4 ordered-field digest domain is malformed",
    )
    require(
        all(field in value for field in fields),
        "V4 ordered-field digest field is absent",
    )
    preimage = (
        domain.encode("ascii") + b"\x00" +
        canonical_value_bytes([value[field] for field in fields])
    )
    return hashlib.sha256(preimage).hexdigest()


def _v4_exact_dict(value: object, fields: tuple[str, ...], label: str) -> dict[str, Any]:
    require(
        type(value) is dict and all(type(key) is str for key in value) and
        set(value) == set(fields),
        f"malformed {label}",
    )
    return value


def _v4_uint(value: object, bits: int, label: str) -> int:
    require(
        is_int(value) and 0 <= value < (1 << bits),
        f"malformed {label}",
    )
    return value


def validate_v4_build_lock_state(value: object) -> dict[str, Any]:
    result = _v4_exact_dict(value, V4_BUILD_LOCK_STATE_FIELDS,
                            "V4 build OFD lock state")
    require(result["mode"] in V4_BUILD_LOCK_TYPES,
            "malformed V4 build OFD lock mode")
    return result


def validate_v4_build_supplementary_groups(value: object) -> dict[str, Any]:
    label = "V4 build supplementary groups"
    result = _v4_exact_dict(
        value, V4_BUILD_SUPPLEMENTARY_GROUP_CONTAINER_FIELDS, label,
    )
    gids = result.get("gids")
    require(
        is_int(result.get("count")) and
        0 <= result["count"] <= V4_BUILD_SUPPLEMENTARY_GROUP_MAX and
        type(gids) is list and len(gids) == result["count"],
        f"malformed {label} count/list",
    )
    previous = -1
    for index, gid in enumerate(gids):
        _v4_uint(gid, 32, f"{label} GID {index}")
        require(previous < gid, f"unordered or duplicate {label}")
        previous = gid
    require(
        type(result.get("ordered_gid_sha256")) is str and
        result["ordered_gid_sha256"] == canonical_sha256(gids),
        f"{label} digest mismatch",
    )
    return result


def validate_v4_build_capability_set(
    value: object, cap_last_cap: object,
) -> dict[str, Any]:
    label = "V4 build capability set"
    expected_last = _v4_uint(cap_last_cap, 32, f"{label} cap_last_cap")
    result = _v4_exact_dict(value, V4_BUILD_CAPABILITY_SET_FIELDS, label)
    capabilities = result.get("capabilities")
    require(
        is_int(result.get("cap_last_cap")) and
        result["cap_last_cap"] == expected_last and
        is_int(result.get("count")) and
        0 <= result["count"] <= expected_last + 1 and
        type(capabilities) is list and len(capabilities) == result["count"],
        f"malformed {label} count/list",
    )
    previous = -1
    for index, capability in enumerate(capabilities):
        require(
            is_int(capability) and 0 <= capability <= expected_last and
            previous < capability,
            f"malformed, unordered or duplicate {label} member {index}",
        )
        previous = capability
    require(
        type(result.get("ordered_capability_sha256")) is str and
        result["ordered_capability_sha256"] == canonical_sha256(capabilities),
        f"{label} digest mismatch",
    )
    return result


def validate_v4_build_capability_sets(
    value: object, cap_last_cap: object,
) -> dict[str, Any]:
    result = _v4_exact_dict(
        value, V4_BUILD_CAPABILITY_SETS_FIELDS, "V4 build capability sets",
    )
    for name in V4_BUILD_CAPABILITY_SET_NAMES:
        validate_v4_build_capability_set(result[name], cap_last_cap)
    return result


def validate_v4_build_signal_set(
    value: object, *, blocked: bool = False,
) -> dict[str, Any]:
    label = "V4 build blocked signal set" if blocked else "V4 build signal set"
    require(type(blocked) is bool, "malformed V4 build signal-set context")
    result = _v4_exact_dict(value, V4_BUILD_SIGNAL_SET_FIELDS, label)
    raw = _v4_uint(result.get("raw_u64"), 64, f"{label} raw_u64")
    signals = result.get("signals")
    require(
        is_int(result.get("count")) and
        0 <= result["count"] <= V4_BUILD_SIGNAL_MAX and
        type(signals) is list and len(signals) == result["count"],
        f"malformed {label} count/list",
    )
    previous = 0
    derived_raw = 0
    for index, signal_number in enumerate(signals):
        require(
            is_int(signal_number) and
            V4_BUILD_SIGNAL_MIN <= signal_number <= V4_BUILD_SIGNAL_MAX and
            previous < signal_number,
            f"malformed, unordered or duplicate {label} member {index}",
        )
        require(
            not blocked or signal_number not in {9, 19},
            f"unblockable signal in {label}",
        )
        previous = signal_number
        derived_raw |= 1 << (signal_number - 1)
    require(raw == derived_raw, f"{label} raw/list mismatch")
    require(
        type(result.get("ordered_signal_sha256")) is str and
        result["ordered_signal_sha256"] == canonical_sha256(signals),
        f"{label} digest mismatch",
    )
    return result


def validate_v4_build_signal_action(value: object) -> dict[str, Any]:
    label = "V4 build signal action"
    result = _v4_exact_dict(value, V4_BUILD_SIGNAL_ACTION_FIELDS, label)
    _v4_uint(result.get("handler"), 64, f"{label} handler")
    flags = _v4_uint(result.get("flags"), 64, f"{label} flags")
    require(flags & ~V4_BUILD_SIGNAL_ACTION_FLAG_MASK == 0,
            f"unknown {label} flag")
    _v4_uint(result.get("restorer"), 64, f"{label} restorer")
    validate_v4_build_signal_set(result.get("mask"))
    return result


def validate_v4_build_signal_altstack(value: object) -> dict[str, Any]:
    label = "V4 build signal altstack"
    result = _v4_exact_dict(value, V4_BUILD_SIGNAL_ALTSTACK_FIELDS, label)
    sp = _v4_uint(result.get("sp"), 64, f"{label} sp")
    flags = _v4_uint(result.get("flags"), 32, f"{label} flags")
    size = _v4_uint(result.get("size"), 64, f"{label} size")
    require(flags & ~V4_BUILD_SIGNAL_ALTSTACK_FLAG_MASK == 0,
            f"unknown {label} flag")
    if flags & 2:
        require((sp, flags, size) == V4_BUILD_SIGNAL_ALTSTACK_DISABLED,
                f"noncanonical disabled {label}")
    else:
        require(sp > 0 and size > 0, f"malformed enabled {label}")
    return result


def validate_v4_build_robust_list_registration(value: object) -> dict[str, Any]:
    label = "V4 build robust-list registration"
    result = _v4_exact_dict(
        value, V4_BUILD_ROBUST_LIST_REGISTRATION_FIELDS, label,
    )
    require(type(result.get("registered")) is bool,
            f"malformed {label} registration flag")
    if result["registered"]:
        head = _v4_uint(result.get("head"), 64, f"{label} head")
        length = _v4_uint(result.get("length"), 64, f"{label} length")
        require(head > 0 and length == 24,
                f"malformed registered {label}")
    else:
        length = _v4_uint(result.get("length"), 64, f"{label} length")
        require(result.get("head") is None and length == 0,
                f"malformed unregistered {label}")
    return result


def validate_v4_build_rseq_registration(value: object) -> dict[str, Any]:
    label = "V4 build rseq registration"
    result = _v4_exact_dict(value, V4_BUILD_RSEQ_REGISTRATION_FIELDS, label)
    require(type(result.get("registered")) is bool,
            f"malformed {label} registration flag")
    length = _v4_uint(result.get("length"), 64, f"{label} length")
    flags = _v4_uint(result.get("flags"), 32, f"{label} flags")
    signature = _v4_uint(result.get("signature"), 32, f"{label} signature")
    if result["registered"]:
        address = _v4_uint(result.get("address"), 64, f"{label} address")
        require(
            address > 0 and length == 32 and flags == 0 and
            signature == 0x5305_3053,
            f"malformed registered {label}",
        )
    else:
        require(
            result.get("address") is None and length == 0 and flags == 0 and
            signature == 0,
            f"malformed unregistered {label}",
        )
    return result


def validate_v4_build_credentials(
    value: object, cap_last_cap: object,
) -> dict[str, Any]:
    label = "V4 build credentials"
    result = _v4_exact_dict(value, V4_BUILD_INITIAL_CREDENTIAL_FIELDS, label)
    for field in (
        "real_uid", "effective_uid", "saved_uid", "fsuid", "real_gid",
        "effective_gid", "saved_gid", "fsgid",
    ):
        _v4_uint(result.get(field), 32, f"{label} {field}")
    validate_v4_build_supplementary_groups(result.get("supplementary_groups"))
    securebits = _v4_uint(result.get("securebits"), 32, f"{label} securebits")
    require(securebits == 0, f"nonzero {label} securebits")
    validate_v4_build_capability_sets(result.get("capability_sets"), cap_last_cap)
    require(is_int(result.get("no_new_privileges")) and
            result["no_new_privileges"] in {0, 1},
            f"malformed {label} no-new-privileges")
    require(is_int(result.get("seccomp_mode")) and
            result["seccomp_mode"] in {0, 2},
            f"malformed {label} seccomp mode")
    require(
        is_int(result.get("seccomp_filter_count")) and
        0 <= result["seccomp_filter_count"] <= V4_SECCOMP_INSTRUCTION_MAX and
        (
            (result["seccomp_mode"] == 0 and
             result["seccomp_filter_count"] == 0) or
            (result["seccomp_mode"] == 2 and
             result["seccomp_filter_count"] > 0)
        ),
        f"malformed {label} seccomp state",
    )
    return result


def validate_v4_build_task_control_state(value: object) -> dict[str, Any]:
    label = "V4 build task-control state"
    result = _v4_exact_dict(
        value, V4_BUILD_INITIAL_TASK_CONTROL_STATE_FIELDS, label,
    )
    dispositions = result.get("signal_dispositions")
    require(
        is_int(result.get("signal_disposition_count")) and
        result["signal_disposition_count"] ==
        V4_BUILD_SIGNAL_DISPOSITION_COUNT and
        type(dispositions) is list and
        len(dispositions) == V4_BUILD_SIGNAL_DISPOSITION_COUNT,
        f"malformed {label} signal-disposition count/list",
    )
    for index, disposition in enumerate(dispositions):
        item_label = f"{label} signal disposition {index}"
        item = _v4_exact_dict(
            disposition, V4_BUILD_INITIAL_SIGNAL_DISPOSITION_FIELDS, item_label,
        )
        require(is_int(item.get("signal_number")) and
                item["signal_number"] == index + 1,
                f"malformed {item_label} number")
        validate_v4_build_signal_action(item.get("action"))
    require(
        type(result.get("signal_disposition_sha256")) is str and
        result["signal_disposition_sha256"] == canonical_sha256(dispositions),
        f"{label} signal-disposition digest mismatch",
    )
    validate_v4_build_signal_set(result.get("blocked_signal_set"), blocked=True)
    validate_v4_build_signal_set(result.get("pending_signal_set"))
    validate_v4_build_signal_altstack(result.get("signal_altstack"))
    _v4_uint(result.get("fs_base"), 64, f"{label} fs_base")
    _v4_uint(result.get("gs_base"), 64, f"{label} gs_base")
    clear_child_tid = result.get("clear_child_tid")
    require(clear_child_tid is None or is_int(clear_child_tid),
            f"malformed {label} clear_child_tid type")
    if clear_child_tid is not None:
        _v4_uint(clear_child_tid, 64, f"{label} clear_child_tid")
    validate_v4_build_robust_list_registration(
        result.get("robust_list_registration"),
    )
    validate_v4_build_rseq_registration(result.get("rseq_registration"))
    personality = _v4_uint(result.get("personality"), 32,
                           f"{label} personality")
    require(personality == 0, f"nonzero {label} personality")
    return result


def validate_v4_build_capability_sets_update(
    value: object, cap_last_cap: object,
    expected_target_sets: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    label = "V4 build capability-sets update"
    result = _v4_exact_dict(
        value, V4_BUILD_TASK_TRANSITION_FIELDS["capability-sets-update"], label,
    )
    require(result.get("kind") == "capability-sets-update" and
            is_int(result.get("index")) and result["index"] >= 0 and
            is_int(result.get("task_index")) and result["task_index"] >= 0,
            f"malformed {label} identity")
    target_sets = result.get("target_sets")
    require(
        type(target_sets) is list and target_sets and
        all(type(item) is str for item in target_sets),
        f"malformed {label} target-set list",
    )
    canonical = [
        name for name in V4_BUILD_CAPABILITY_SET_NAMES if name in target_sets
    ]
    require(target_sets == canonical,
            f"unordered, duplicate or unknown {label} target-set list")
    if expected_target_sets is not None:
        require(
            type(expected_target_sets) is tuple and
            target_sets == list(expected_target_sets),
            f"unexpected {label} target-set list",
        )
    before = validate_v4_build_capability_sets(
        result.get("before_capability_sets"), cap_last_cap,
    )
    after = validate_v4_build_capability_sets(
        result.get("after_capability_sets"), cap_last_cap,
    )
    target_set = set(target_sets)
    require(
        all(
            name in target_set or canonical_value_bytes(before[name]) ==
            canonical_value_bytes(after[name])
            for name in V4_BUILD_CAPABILITY_SET_NAMES
        ),
        f"untargeted {label} member changed",
    )
    idempotent = result.get("idempotent")
    require(type(idempotent) is bool, f"malformed {label} idempotent flag")
    all_targets_unchanged = all(
        canonical_value_bytes(before[name]) == canonical_value_bytes(after[name])
        for name in target_sets
    )
    require(idempotent is all_targets_unchanged,
            f"wrong {label} idempotent flag")
    return result


def _validate_v4_indexed_list_container(
    value: object, container_fields: tuple[str, ...], entry_fields: tuple[str, ...],
    maximum: int, label: str,
) -> list[dict[str, Any]]:
    result = _v4_exact_dict(value, container_fields, label)
    entries = result.get("entries")
    require(
        is_int(result.get("count")) and
        0 <= result["count"] <= maximum and
        type(entries) is list and len(entries) == result["count"],
        f"malformed {label} count/list",
    )
    for index, entry in enumerate(entries):
        item = _v4_exact_dict(entry, entry_fields, f"{label} entry {index}")
        require(
            is_int(item.get("index")) and item["index"] == index,
            f"nonconsecutive {label} index",
        )
    require(
        type(result.get("ordered_entry_sha256")) is str and
        result["ordered_entry_sha256"] == canonical_sha256(entries),
        f"{label} digest mismatch",
    )
    return entries


def _validate_v4_initial_object_edges(
    value: object,
) -> list[dict[str, Any]]:
    edges = _validate_v4_indexed_list_container(
        value, V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS,
        V4_BUILD_INITIAL_OBJECT_EDGE_FIELDS, V4_BUILD_INPUT_CLOSURE_ENTRY_MAX,
        "V4 initial object edges",
    )
    require(
        all(edge.get("domain") in V4_BUILD_INITIAL_OBJECT_EDGE_DOMAINS
            for edge in edges),
        "unknown V4 initial object-edge domain",
    )
    return edges


def _validate_v4_parent_fd_open_descriptions(
    fd_table: object, open_descriptions: object,
    initial_edges: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    table_label = "V4 initial fd table"
    table = _v4_exact_dict(
        fd_table, V4_BUILD_INITIAL_FD_TABLE_CONTAINER_FIELDS, table_label,
    )
    fds = table.get("fds")
    table_id = _v4_uint(table.get("table_id"), 64, f"{table_label} ID")
    generation = _v4_uint(
        table.get("generation"), 64, f"{table_label} generation",
    )
    require(
        table_id > 0 and generation > 0 and
        is_int(table.get("fd_count")) and
        0 <= table["fd_count"] <= V4_BUILD_FD_PER_TABLE_MAX and
        type(fds) is list and len(fds) == table["fd_count"],
        f"malformed {table_label} count/list",
    )
    previous_fd = -1
    for index, fd in enumerate(fds):
        item = _v4_exact_dict(
            fd, V4_BUILD_INITIAL_FD_FIELDS, f"{table_label} entry {index}",
        )
        fd_number = _v4_uint(item.get("fd"), 32, f"{table_label} fd")
        fd_generation = _v4_uint(
            item.get("fd_generation"), 64,
            f"{table_label} fd generation",
        )
        require(
            is_int(item.get("index")) and item["index"] == index and
            previous_fd < fd_number < V4_BUILD_FD_PER_TABLE_MAX and
            fd_generation > 0 and
            type(item.get("cloexec")) is bool and
            item.get("access_mode") in {
                "read-only", "write-only", "read-write", "read-search-only",
            } and
            is_int(item.get("open_description_index")),
            f"malformed {table_label} entry {index}",
        )
        previous_fd = fd_number
    require(
        type(table.get("ordered_fd_sha256")) is str and
        table["ordered_fd_sha256"] == canonical_sha256(fds),
        f"{table_label} digest mismatch",
    )

    descriptions = _validate_v4_indexed_list_container(
        open_descriptions, V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS,
        V4_BUILD_INITIAL_OPEN_DESCRIPTION_FIELDS, V4_BUILD_FD_PER_TABLE_MAX,
        "V4 initial open descriptions",
    )
    references = [0] * len(descriptions)
    for fd in fds:
        selected = fd["open_description_index"]
        require(0 <= selected < len(descriptions),
                "V4 initial fd selects absent open description")
        description = descriptions[selected]
        require(fd["access_mode"] == description.get("access_mode"),
                "V4 initial fd/OFD access mismatch")
        references[selected] += 1
    open_description_ids: set[int] = set()
    for index, description in enumerate(descriptions):
        label = f"V4 initial open description {index}"
        open_description_id = _v4_uint(
            description.get("open_description_id"), 64, f"{label} ID",
        )
        generation = _v4_uint(
            description.get("generation"), 64, f"{label} generation",
        )
        status_flags = _v4_uint(
            description.get("status_flags"), 64, f"{label} status flags",
        )
        _v4_uint(description.get("offset"), 64, f"{label} offset")
        access_mode = description.get("access_mode")
        access_bits = status_flags & 0x03
        o_path = 0x20_0000
        o_directory = 0x01_0000
        o_nofollow = 0x02_0000
        o_cloexec = 0x08_0000
        require(
            status_flags & o_cloexec == 0,
            f"{label} status flags contain descriptor-only O_CLOEXEC",
        )
        if access_mode == "read-search-only":
            require(
                status_flags & o_path == o_path and access_bits == 0 and
                status_flags & ~(o_path | o_directory | o_nofollow) == 0,
                f"malformed {label} O_PATH status flags",
            )
        else:
            require(
                status_flags & o_path == 0 and access_bits != 3 and
                access_mode == (
                    "read-only" if access_bits == 0 else
                    "write-only" if access_bits == 1 else "read-write"
                ),
                f"{label} access/status mismatch",
            )
        require(
            open_description_id > 0 and
            open_description_id not in open_description_ids and
            generation > 0 and
            is_int(description.get("object_edge_index")) and
            0 <= description["object_edge_index"] < len(initial_edges) and
            access_mode in {
                "read-only", "write-only", "read-write", "read-search-only",
            } and
            is_int(description.get("descriptor_ref_count")) and
            description["descriptor_ref_count"] == references[index] and
            references[index] > 0,
            f"malformed {label}",
        )
        open_description_ids.add(open_description_id)
        validate_v4_build_lock_state(description.get("lock_state"))
    return table, fds, descriptions


def validate_v4_build_parent_fd_state(
    initial_object_edges: object, fd_table: object,
    open_descriptions: object, inherited_fd_indices: object,
) -> dict[str, Any]:
    """Validate and snapshot the complete inherited parent FD/OFD state."""
    label = "V4 parent FD state"
    values = (
        initial_object_edges, fd_table, open_descriptions,
        inherited_fd_indices,
    )
    _require_v4_exact_json_types(list(values), label)
    edges = _validate_v4_initial_object_edges(initial_object_edges)
    _, fds, _ = _validate_v4_parent_fd_open_descriptions(
        fd_table, open_descriptions, edges,
    )
    require(
        type(inherited_fd_indices) is list and
        inherited_fd_indices == list(range(len(fds))) and
        all(is_int(index) for index in inherited_fd_indices),
        "V4 inherited fd indexes do not select every fd exactly once",
    )
    return json.loads(canonical_value_bytes({
        "initial_object_edges": initial_object_edges,
        "fd_table": fd_table,
        "open_descriptions": open_descriptions,
        "inherited_fd_indices": inherited_fd_indices,
    }))


def _validate_v4_bootstrap_mapping_edge(
    edge: dict[str, Any], label: str,
) -> None:
    authority_index = _v4_uint(
        edge.get("authority_index"), 32, f"{label} authority index",
    )
    root_fd_generation = _v4_uint(
        edge.get("root_fd_generation"), 64,
        f"{label} root fd generation",
    )
    mount_id = _v4_uint(edge.get("mount_id"), 32, f"{label} mount ID")
    _v4_uint(edge.get("st_dev"), 64, f"{label} st_dev")
    st_ino = _v4_uint(edge.get("st_ino"), 64, f"{label} st_ino")
    stable_generation = _v4_uint(
        edge.get("stable_generation"), 64,
        f"{label} stable generation",
    )
    require(
        edge.get("domain") == "bootstrap-runtime" and
        type(edge.get("authority_role")) is str and
        bool(edge["authority_role"]) and
        authority_index >= 0 and
        type(edge.get("root_identity")) is dict and
        root_fd_generation > 0 and
        edge.get("input_root_entry_index") is None and
        edge.get("stream_role") is None and
        edge.get("setup_role") is None and
        type(edge.get("parent_descriptor_identity")) is dict and
        mount_id > 0 and st_ino > 0 and stable_generation > 0 and
        type(edge.get("symlink_decisions")) is list,
        f"malformed {label} bootstrap object edge",
    )
    _printable(edge["authority_role"], f"{label} authority role")
    _v4_source_tree_relative(
        edge.get("resolved_relative"), f"{label} resolved relative",
    )


def _validate_v4_parent_address_space_mappings(
    address_space: object, mappings: object,
    initial_edges: list[dict[str, Any]], gate_mapping_index: object,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    space_label = "V4 initial address space"
    space = _v4_exact_dict(
        address_space, V4_BUILD_INITIAL_ADDRESS_SPACE_FIELDS, space_label,
    )
    mapping_indices = space.get("mapping_indices")
    address_space_id = _v4_uint(
        space.get("address_space_id"), 64, f"{space_label} ID",
    )
    generation = _v4_uint(
        space.get("generation"), 64, f"{space_label} generation",
    )
    require(
        address_space_id > 0 and generation > 0 and
        is_int(space.get("mapping_count")) and
        1 <= space["mapping_count"] <= V4_BUILD_VMA_PER_ADDRESS_SPACE_MAX and
        type(mapping_indices) is list and
        mapping_indices == list(range(space["mapping_count"])) and
        all(is_int(index) for index in mapping_indices) and
        type(space.get("ordered_mapping_index_sha256")) is str and
        space["ordered_mapping_index_sha256"] == canonical_sha256(
            mapping_indices,
        ),
        f"malformed {space_label}",
    )
    rows = _validate_v4_indexed_list_container(
        mappings, V4_BUILD_INITIAL_LIST_CONTAINER_FIELDS,
        V4_BUILD_INITIAL_MAPPING_FIELDS, V4_BUILD_VMA_PER_ADDRESS_SPACE_MAX,
        "V4 initial mappings",
    )
    require(
        len(rows) == space["mapping_count"],
        "V4 address-space mapping count mismatch",
    )
    require(
        is_int(gate_mapping_index) and 0 <= gate_mapping_index < len(rows),
        "malformed V4 gate mapping index",
    )

    page_size = 4_096
    map_shared = 0x01
    map_private = 0x02
    map_anonymous = 0x20
    previous_end = 0
    gate_rows: list[dict[str, Any]] = []
    for index, mapping in enumerate(rows):
        label = f"V4 initial mapping {index}"
        address = _v4_uint(mapping.get("address"), 64, f"{label} address")
        length = _v4_uint(mapping.get("length"), 64, f"{label} length")
        protection = _v4_uint(
            mapping.get("protection"), 32, f"{label} protection",
        )
        flags = _v4_uint(mapping.get("flags"), 64, f"{label} flags")
        file_offset = _v4_uint(
            mapping.get("file_offset"), 64, f"{label} file offset",
        )
        require(
            address % page_size == 0 and length > 0 and
            length % page_size == 0 and address + length <= (1 << 64) and
            address >= previous_end,
            f"malformed or overlapping {label} range",
        )
        previous_end = address + length
        require(
            protection & ~0x07 == 0 and
            flags & (map_shared | map_private) in {map_shared, map_private},
            f"malformed {label} mode/class",
        )
        object_edge_index = mapping.get("object_edge_index")
        if object_edge_index is None:
            require(
                file_offset == 0 and flags & map_anonymous == map_anonymous,
                f"anonymous {label} lacks canonical flags/offset",
            )
        else:
            require(
                is_int(object_edge_index) and
                0 <= object_edge_index < len(initial_edges) and
                file_offset % page_size == 0 and
                flags & map_anonymous == 0,
                f"malformed file-backed {label}",
            )
            _validate_v4_bootstrap_mapping_edge(
                initial_edges[object_edge_index], label,
            )
        require(type(mapping.get("gate_mapping")) is bool,
                f"malformed {label} gate flag")
        if mapping["gate_mapping"]:
            gate_rows.append(mapping)

    require(
        len(gate_rows) == 1 and gate_rows[0]["index"] == gate_mapping_index,
        "V4 gate mapping selector is not unique and exact",
    )
    gate = gate_rows[0]
    require(
        gate["length"] == page_size and gate["protection"] == 0x03 and
        gate["flags"] == map_shared | map_anonymous and
        gate["file_offset"] == 0 and gate["object_edge_index"] is None,
        "malformed V4 shared anonymous gate mapping",
    )
    return space, rows


def validate_v4_build_parent_address_space(
    initial_object_edges: object, address_space: object, mappings: object,
    gate_mapping_index: object,
) -> dict[str, Any]:
    """Validate and snapshot the complete parent address-space/VMA state."""
    label = "V4 parent address space"
    values = (
        initial_object_edges, address_space, mappings, gate_mapping_index,
    )
    _require_v4_exact_json_types(list(values), label)
    edges = _validate_v4_initial_object_edges(initial_object_edges)
    _validate_v4_parent_address_space_mappings(
        address_space, mappings, edges, gate_mapping_index,
    )
    return json.loads(canonical_value_bytes({
        "initial_object_edges": initial_object_edges,
        "address_space": address_space,
        "mappings": mappings,
        "gate_mapping_index": gate_mapping_index,
    }))


def _validate_v4_root_stable_identity(
    edge: dict[str, Any], label: str,
) -> None:
    require(
        type(edge.get("root_identity")) is dict and
        type(edge.get("parent_descriptor_identity")) is dict and
        is_int(edge.get("mount_id")) and edge["mount_id"] > 0 and
        is_int(edge.get("st_dev")) and edge["st_dev"] >= 0 and
        is_int(edge.get("st_ino")) and edge["st_ino"] > 0 and
        is_int(edge.get("stable_generation")) and
        edge["stable_generation"] > 0 and
        edge.get("resolved_relative") == "." and
        edge.get("symlink_decisions") == [],
        f"malformed {label} stable identity",
    )


def _validate_v4_initial_root_edge(
    edge: dict[str, Any], domain: str, root_identity: object,
    root_fd_generation: object,
) -> dict[str, Any]:
    label = f"V4 initial {domain} edge"
    require(edge.get("domain") == domain, f"wrong {label} domain")
    _validate_v4_root_stable_identity(edge, label)
    require(
        edge.get("root_fd_generation") == root_fd_generation and
        edge.get("input_root_entry_index") is None and
        edge.get("stream_role") is None,
        f"wrong {label} root join",
    )
    require_exact_json(edge.get("root_identity"), root_identity,
                       f"{label} root identity")
    if domain == "setup-root":
        require(
            edge.get("authority_role") is None and
            edge.get("authority_index") is None and
            edge.get("setup_role") == "builder-initial-root" and
            root_fd_generation is None,
            f"malformed {label} selectors",
        )
    else:
        require(
            edge.get("authority_role") == "native-build-input-closure" and
            is_int(edge.get("authority_index")) and
            edge["authority_index"] == 0 and
            edge.get("setup_role") is None and
            is_int(edge.get("root_fd_generation")) and
            is_int(root_fd_generation) and root_fd_generation > 0,
            f"malformed {label} selectors",
        )
    return edge


def _v4_decode_canonical_base64(
    value: object, maximum_bytes: int, label: str, *, nonempty: bool,
) -> bytes:
    require(type(value) is str and value.isascii(), f"malformed {label}")
    encoded = value.encode("ascii")
    require(
        len(encoded) <= 4 * ((maximum_bytes + 2) // 3),
        f"{label} encoded bytes exceed cap",
    )
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ProtocolError(f"malformed {label}: {error}") from error
    require(
        len(decoded) <= maximum_bytes and (not nonempty or decoded) and
        base64.b64encode(decoded) == encoded,
        f"noncanonical or over-cap {label}",
    )
    return decoded


def _v4_mount_ascii_token(value: object, label: str) -> str:
    require(type(value) is str and value.isascii(), f"malformed {label}")
    encoded = value.encode("ascii")
    require(
        1 <= len(encoded) <= V4_SAFE_RELATIVE_MAX_BYTES and
        all(0x21 <= byte <= 0x7E for byte in encoded),
        f"malformed {label}",
    )
    return value


def _v4_mount_token_list(value: object, label: str) -> list[str]:
    require(
        type(value) is list and len(value) <= V4_SAFE_RELATIVE_MAX_BYTES,
        f"malformed {label} list",
    )
    for index, token in enumerate(value):
        _v4_mount_ascii_token(token, f"{label} token {index}")
    return value


def _v4_mount_decimal(value: bytes, label: str, *, positive: bool) -> int:
    require(
        1 <= len(value) <= 20 and (
            value == b"0" or
            value[:1] in b"123456789" and
            (len(value) == 1 or value[1:].isdigit())
        ),
        f"noncanonical {label}",
    )
    result = int(value)
    require(
        result < (1 << 64) and (not positive or result > 0),
        f"out-of-range {label}",
    )
    return result


def _v4_unescape_mountinfo_field(value: bytes, label: str) -> bytes:
    require(not any(byte in {0x09, 0x0A, 0x20} for byte in value),
            f"unescaped whitespace in {label}")
    result = bytearray()
    index = 0
    escapes = {
        b"040": 0x20, b"011": 0x09, b"012": 0x0A, b"134": 0x5C,
    }
    while index < len(value):
        if value[index] != 0x5C:
            result.append(value[index])
            index += 1
            continue
        code = value[index + 1:index + 4]
        require(len(code) == 3 and code in escapes,
                f"malformed {label} mountinfo escape")
        result.append(escapes[code])
        index += 4
    require(b"\x00" not in result, f"NUL in {label}")
    return bytes(result)


def _v4_mountinfo_ascii(value: bytes, label: str) -> str:
    try:
        result = value.decode("ascii")
    except UnicodeDecodeError as error:
        raise ProtocolError(f"non-ASCII {label}") from error
    return _v4_mount_ascii_token(result, label)


def _validate_v4_mount_propagation(
    value: object, label: str,
) -> tuple[dict[str, Any], str]:
    result = _v4_exact_dict(value, V4_BUILD_MOUNT_PROPAGATION_FIELDS, label)
    group_ids: dict[str, int | None] = {}
    for field in (
        "shared_group_id", "master_group_id", "propagate_from_group_id",
    ):
        candidate = result.get(field)
        if candidate is None:
            group_ids[field] = None
        else:
            group_id = _v4_uint(candidate, 32, f"{label} {field}")
            require(group_id > 0, f"zero {label} {field}")
            group_ids[field] = group_id
    require(type(result.get("unbindable")) is bool,
            f"malformed {label} unbindable")
    shared = group_ids["shared_group_id"]
    master = group_ids["master_group_id"]
    propagate_from = group_ids["propagate_from_group_id"]
    if result["unbindable"]:
        require(shared is None and master is None and propagate_from is None,
                f"grouped unbindable {label}")
        kind = "unbindable"
    elif shared is None and master is None:
        require(propagate_from is None, f"orphan propagate-from in {label}")
        kind = "private"
    elif shared is not None and master is None:
        require(propagate_from is None, f"orphan propagate-from in {label}")
        kind = "shared"
    elif shared is None:
        kind = "slave"
    else:
        kind = "shared-slave"
    return result, kind


def _v4_mountinfo_propagation(
    optional_fields: list[str], label: str,
) -> dict[str, Any]:
    values: dict[str, int | None] = {
        "shared_group_id": None,
        "master_group_id": None,
        "propagate_from_group_id": None,
    }
    prefixes = {
        "shared": "shared_group_id",
        "master": "master_group_id",
        "propagate_from": "propagate_from_group_id",
    }
    unbindable = False
    for token in optional_fields:
        if token == "unbindable":
            require(not unbindable, f"duplicate {label} unbindable")
            unbindable = True
            continue
        prefix, separator, suffix = token.partition(":")
        if prefix not in prefixes:
            continue
        require(separator == ":" and values[prefixes[prefix]] is None,
                f"duplicate or malformed {label} {prefix}")
        group_id = _v4_mount_decimal(
            suffix.encode("ascii"), f"{label} {prefix}", positive=True,
        )
        require(group_id < (1 << 32), f"out-of-range {label} {prefix}")
        values[prefixes[prefix]] = group_id
    result = {**values, "unbindable": unbindable}
    _validate_v4_mount_propagation(result, label)
    return result


def _v4_parse_mountinfo(payload: bytes, label: str) -> list[dict[str, Any]]:
    require(payload and payload.endswith(b"\n") and b"\r" not in payload,
            f"malformed {label} framing")
    lines = payload[:-1].split(b"\n")
    require(lines and all(lines), f"empty {label} line")
    records: list[dict[str, Any]] = []
    mount_ids: set[int] = set()
    for index, line in enumerate(lines):
        fields = line.split(b" ")
        separators = [
            candidate for candidate in range(6, len(fields))
            if fields[candidate] == b"-" and len(fields) == candidate + 4
        ]
        require(all(fields) and len(separators) == 1,
                f"malformed {label} line {index}")
        separator = separators[0]
        require(len(fields) == separator + 4,
                f"malformed {label} field count {index}")
        mount_id = _v4_mount_decimal(
            fields[0], f"{label} mount id {index}", positive=True,
        )
        parent_id = _v4_mount_decimal(
            fields[1], f"{label} parent id {index}", positive=True,
        )
        require(mount_id not in mount_ids, f"duplicate {label} mount id")
        mount_ids.add(mount_id)
        device = fields[2].split(b":")
        require(len(device) == 2, f"malformed {label} device {index}")
        device_major = _v4_mount_decimal(
            device[0], f"{label} device major {index}", positive=False,
        )
        device_minor = _v4_mount_decimal(
            device[1], f"{label} device minor {index}", positive=False,
        )
        require(device_major < (1 << 32) and device_minor < (1 << 32),
                f"out-of-range {label} device {index}")
        root_raw, mountpoint_raw = fields[3], fields[4]
        require(
            1 <= len(root_raw) <= V4_SAFE_RELATIVE_MAX_BYTES and
            1 <= len(mountpoint_raw) <= V4_SAFE_RELATIVE_MAX_BYTES,
            f"over-cap {label} path field {index}",
        )
        root = _v4_unescape_mountinfo_field(
            root_raw, f"{label} root {index}",
        )
        mountpoint = _v4_unescape_mountinfo_field(
            mountpoint_raw, f"{label} mountpoint {index}",
        )
        require(root.startswith(b"/") and mountpoint.startswith(b"/"),
                f"nonabsolute {label} path {index}")
        mount_flags = _v4_mountinfo_ascii(
            fields[5], f"{label} flags field {index}",
        ).split(",")
        optional_fields = [
            _v4_mountinfo_ascii(field, f"{label} optional field {index}")
            for field in fields[6:separator]
        ]
        filesystem_type = _v4_mountinfo_ascii(
            fields[separator + 1], f"{label} filesystem type {index}",
        )
        mount_source_raw = fields[separator + 2]
        super_options = _v4_mountinfo_ascii(
            fields[separator + 3], f"{label} super-options field {index}",
        ).split(",")
        _v4_mount_token_list(mount_flags, f"{label} flags {index}")
        _v4_mount_token_list(optional_fields, f"{label} optional fields {index}")
        require(1 <= len(mount_source_raw) <= V4_SAFE_RELATIVE_MAX_BYTES,
                f"over-cap {label} mount source {index}")
        _v4_unescape_mountinfo_field(
            mount_source_raw, f"{label} mount source {index}",
        )
        _v4_mount_token_list(super_options,
                             f"{label} super options {index}")
        records.append({
            "mount_id": mount_id,
            "raw_parent_mount_id": parent_id,
            "device_major": device_major,
            "device_minor": device_minor,
            "root_raw": root_raw,
            "root": root,
            "mountpoint_raw": mountpoint_raw,
            "mountpoint": mountpoint,
            "filesystem_type": filesystem_type,
            "mount_source_raw": mount_source_raw,
            "flags": mount_flags,
            "super_options": super_options,
            "optional_fields": optional_fields,
            "propagation": _v4_mountinfo_propagation(
                optional_fields, f"{label} propagation {index}",
            ),
        })
    return records


def _v4_proc_namespace_relative(path: bytes) -> bool:
    components = [component for component in path.split(b"/") if component]
    if not components:
        return False
    first = components[0]
    pid_like = first in {b"self", b"thread-self"} or first.isdigit()
    if not pid_like:
        return False
    if len(components) >= 3 and components[1] == b"ns":
        return True
    return (
        len(components) >= 5 and components[1] == b"task" and
        components[2].isdigit() and components[3] == b"ns"
    )


def _v4_path_relative_to(path: bytes, root: bytes) -> bytes | None:
    if root == b"/":
        return path[1:] if path.startswith(b"/") else None
    if path == root:
        return b""
    prefix = root.rstrip(b"/") + b"/"
    return path[len(prefix):] if path.startswith(prefix) else None


def _v4_path_below_mount_root(root: bytes, relative: bytes) -> bytes:
    require(root.startswith(b"/"), "nonabsolute V4 mount root")
    if not relative:
        return root
    if root == b"/":
        return b"/" + relative
    return root.rstrip(b"/") + b"/" + relative


def validate_v4_build_mount_graph(
    value: object, *, source_graph: object,
) -> dict[str, Any]:
    label = "V4 source mount graph" if source_graph is True else "V4 builder mount graph"
    require(type(source_graph) is bool, "malformed V4 mount graph role")
    _require_v4_exact_json_types(value, label)
    result = _v4_exact_dict(value, V4_BUILD_MOUNT_GRAPH_CONTAINER_FIELDS, label)
    mounts = result.get("mounts")
    require(
        type(result.get("mount_namespace_identity")) is dict and
        is_int(result.get("generation")) and 0 < result["generation"] < (1 << 64) and
        is_int(result.get("mount_count")) and
        1 <= result["mount_count"] <= V4_BUILD_MOUNT_GRAPH_MAX and
        type(mounts) is list and len(mounts) == result["mount_count"],
        f"malformed {label} count/list",
    )
    require(
        type(result.get("ordered_mount_sha256")) is str and
        HEX64.fullmatch(result["ordered_mount_sha256"]) is not None and
        result["ordered_mount_sha256"] == canonical_sha256(mounts),
        f"{label} digest mismatch",
    )
    payload_value = result.get("mountinfo_payload_base64")
    require(type(payload_value) is str and payload_value.isascii() and
            len(payload_value) <= V4_NATIVE_BUILD_RECEIPT_MAX_BYTES,
            f"over-cap {label} mountinfo payload")
    payload = _v4_decode_canonical_base64(
        payload_value, V4_NATIVE_BUILD_RECEIPT_MAX_BYTES,
        f"{label} mountinfo payload", nonempty=True,
    )
    require(
        is_int(result.get("mountinfo_bytes")) and
        result["mountinfo_bytes"] == len(payload) and
        type(result.get("mountinfo_sha256")) is str and
        HEX64.fullmatch(result["mountinfo_sha256"]) is not None and
        result["mountinfo_sha256"] == hashlib.sha256(payload).hexdigest(),
        f"{label} mountinfo content mismatch",
    )
    parsed = _v4_parse_mountinfo(payload, f"{label} mountinfo")
    require(len(parsed) == len(mounts), f"{label} mountinfo count mismatch")
    parsed_by_id = {record["mount_id"]: record for record in parsed}
    mount_ids: set[int] = set()
    rows_by_id: dict[int, dict[str, Any]] = {}
    for index, mount in enumerate(mounts):
        row = _v4_exact_dict(
            mount, V4_BUILD_MOUNT_GRAPH_ENTRY_FIELDS,
            f"{label} entry {index}",
        )
        require(
            is_int(row.get("index")) and row["index"] == index and
            is_int(row.get("mount_id")) and 0 < row["mount_id"] < (1 << 64) and
            row["mount_id"] not in mount_ids and
            is_int(row.get("raw_parent_mount_id")) and
            0 < row["raw_parent_mount_id"] < (1 << 64) and
            (row.get("parent_mount_id") is None or
             is_int(row["parent_mount_id"]) and
             0 < row["parent_mount_id"] < (1 << 64)) and
            type(row.get("root_identity")) is dict and
            type(row.get("mountpoint_identity")) is dict and
            is_int(row.get("device_major")) and
            0 <= row["device_major"] < (1 << 32) and
            is_int(row.get("device_minor")) and
            0 <= row["device_minor"] < (1 << 32),
            f"malformed {label} entry {index} identity",
        )
        root_raw = _v4_decode_canonical_base64(
            row.get("root_bytes_base64"), V4_SAFE_RELATIVE_MAX_BYTES,
            f"{label} entry {index} root", nonempty=True,
        )
        mountpoint_raw = _v4_decode_canonical_base64(
            row.get("mountpoint_bytes_base64"), V4_SAFE_RELATIVE_MAX_BYTES,
            f"{label} entry {index} mountpoint", nonempty=True,
        )
        source_raw = _v4_decode_canonical_base64(
            row.get("mount_source_bytes_base64"), V4_SAFE_RELATIVE_MAX_BYTES,
            f"{label} entry {index} source", nonempty=True,
        )
        _v4_mount_ascii_token(
            row.get("filesystem_type"), f"{label} entry {index} filesystem",
        )
        _v4_mount_token_list(row.get("flags"), f"{label} entry {index} flags")
        _v4_mount_token_list(
            row.get("super_options"), f"{label} entry {index} super options",
        )
        _v4_mount_token_list(
            row.get("optional_fields"), f"{label} entry {index} optional fields",
        )
        propagation, _ = _validate_v4_mount_propagation(
            row.get("propagation"), f"{label} entry {index} propagation",
        )
        observed = parsed_by_id.get(row["mount_id"])
        require(observed is not None, f"{label} entry absent from mountinfo")
        require(
            row["raw_parent_mount_id"] == observed["raw_parent_mount_id"] and
            row["device_major"] == observed["device_major"] and
            row["device_minor"] == observed["device_minor"] and
            root_raw == observed["root_raw"] and
            mountpoint_raw == observed["mountpoint_raw"] and
            source_raw == observed["mount_source_raw"] and
            row["filesystem_type"] == observed["filesystem_type"],
            f"{label} entry {index} differs from mountinfo",
        )
        require_exact_json(row["flags"], observed["flags"],
                           f"{label} entry {index} flags")
        require_exact_json(row["super_options"], observed["super_options"],
                           f"{label} entry {index} super options")
        require_exact_json(row["optional_fields"], observed["optional_fields"],
                           f"{label} entry {index} optional fields")
        require_exact_json(propagation, observed["propagation"],
                           f"{label} entry {index} propagation")
        mount_ids.add(row["mount_id"])
        rows_by_id[row["mount_id"]] = row
    roots = [row for row in mounts if row["parent_mount_id"] is None]
    require(len(roots) == 1 and roots[0] is mounts[0],
            f"{label} does not have one index-zero root")
    root = roots[0]
    require(root["raw_parent_mount_id"] not in mount_ids,
            f"{label} root raw parent is visible")
    for row in mounts[1:]:
        require(
            row["parent_mount_id"] in mount_ids and
            row["raw_parent_mount_id"] == row["parent_mount_id"],
            f"{label} nonroot parent mismatch",
        )
    emitted: set[int] = set()
    remaining = set(mount_ids)
    for index, row in enumerate(mounts):
        eligible = [
            mount_id for mount_id in remaining
            if rows_by_id[mount_id]["parent_mount_id"] is None or
            rows_by_id[mount_id]["parent_mount_id"] in emitted
        ]
        require(eligible, f"cyclic {label} topology")
        expected = min(eligible, key=lambda mount_id: (
            parsed_by_id[mount_id]["mountpoint_raw"], mount_id,
        ))
        require(row["mount_id"] == expected,
                f"noncanonical {label} order at index {index}")
        emitted.add(expected)
        remaining.remove(expected)
    if source_graph:
        require(all(row["filesystem_type"] != "nsfs" for row in mounts),
                f"{label} contains nsfs")
        proc_mounts = [
            (
                parsed_by_id[row["mount_id"]]["mountpoint"],
                parsed_by_id[row["mount_id"]]["root"],
            )
            for row in mounts
            if row["filesystem_type"] == "proc"
        ]
        for row in mounts:
            observed = parsed_by_id[row["mount_id"]]
            if row["filesystem_type"] == "proc":
                require(not _v4_proc_namespace_relative(observed["root"]),
                        f"{label} is rooted at a proc namespace file")
            for proc_mountpoint, proc_root in proc_mounts:
                relative = _v4_path_relative_to(
                    observed["mountpoint"], proc_mountpoint,
                )
                require(
                    relative is None or not _v4_proc_namespace_relative(
                        _v4_path_below_mount_root(proc_root, relative)
                    ),
                    f"{label} mounts a proc namespace file",
                )
    return result


def _validate_v4_builder_mount_root(
    value: object, setup_root_edge: dict[str, Any],
) -> dict[str, Any]:
    label = "V4 builder mount graph"
    result = validate_v4_build_mount_graph(value, source_graph=False)
    mounts = result["mounts"]
    root = mounts[0]
    require(root["mount_id"] == setup_root_edge["mount_id"],
            f"{label} root mount id does not join initial setup root")
    require_exact_json(
        root["mountpoint_identity"], setup_root_edge["root_identity"],
        f"{label} root mountpoint identity",
    )
    return root


def _v4_nonpropagation_optional_fields(tokens: list[str]) -> list[str]:
    result = []
    for token in tokens:
        prefix = token.partition(":")[0]
        if token == "unbindable" or prefix in {
            "shared", "master", "propagate_from",
        }:
            continue
        result.append(token)
    return result


def _v4_expected_cloned_propagation(
    source: dict[str, Any], label: str,
) -> dict[str, Any]:
    source, kind = _validate_v4_mount_propagation(source, label)
    if kind in {"private", "slave", "unbindable"}:
        return json.loads(canonical_value_bytes(source))
    return {
        "shared_group_id": None,
        "master_group_id": source["shared_group_id"],
        "propagate_from_group_id": None,
        "unbindable": False,
    }


def validate_v4_build_mount_namespace_clone(
    value: object, parent_mount_graph: object, builder_mount_graph: object,
) -> dict[str, Any]:
    label = "V4 mount-namespace clone"
    _require_v4_exact_json_types(
        [value, parent_mount_graph, builder_mount_graph], label,
    )
    source_graph = validate_v4_build_mount_graph(
        parent_mount_graph, source_graph=True,
    )
    child_graph = validate_v4_build_mount_graph(
        builder_mount_graph, source_graph=False,
    )
    result = _v4_exact_dict(
        value, V4_BUILD_FS_TRANSITION_FIELDS["mount-namespace-create"], label,
    )
    clones = result.get("mount_clones")
    require(
        result.get("kind") == "mount-namespace-create" and
        is_int(result.get("index")) and result["index"] >= 0 and
        is_int(result.get("task_index")) and result["task_index"] >= 0 and
        is_int(result.get("source_generation")) and
        result["source_generation"] == source_graph["generation"] and
        is_int(result.get("child_generation")) and
        result["child_generation"] == child_graph["generation"] and
        is_int(result.get("mount_clone_count")) and
        result["mount_clone_count"] == source_graph["mount_count"] and
        result["mount_clone_count"] == child_graph["mount_count"] and
        type(clones) is list and len(clones) == result["mount_clone_count"],
        f"malformed {label} identity/count",
    )
    require_exact_json(
        result.get("source_mount_namespace_identity"),
        source_graph["mount_namespace_identity"],
        f"{label} source namespace",
    )
    require_exact_json(
        result.get("child_mount_namespace_identity"),
        child_graph["mount_namespace_identity"],
        f"{label} child namespace",
    )
    require(
        canonical_value_bytes(source_graph["mount_namespace_identity"]) !=
        canonical_value_bytes(child_graph["mount_namespace_identity"]),
        f"{label} namespaces are not distinct",
    )
    source_rows = source_graph["mounts"]
    child_by_id = {
        row["mount_id"]: row for row in child_graph["mounts"]
    }
    source_ids = {row["mount_id"] for row in source_rows}
    require(source_ids.isdisjoint(child_by_id),
            f"{label} source and child mount IDs overlap")
    source_to_child: dict[int, int] = {}
    child_ids: set[int] = set()
    clone_rows: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for index, clone in enumerate(clones):
        row = _v4_exact_dict(
            clone, V4_BUILD_MOUNT_CLONE_FIELDS, f"{label} row {index}",
        )
        source_row = source_rows[index]
        require(
            is_int(row.get("index")) and row["index"] == index and
            is_int(row.get("source_mount_id")) and
            row["source_mount_id"] == source_row["mount_id"] and
            is_int(row.get("child_mount_id")) and row["child_mount_id"] > 0 and
            row["source_mount_id"] not in source_to_child and
            row["child_mount_id"] not in child_ids,
            f"malformed or duplicate {label} ID row {index}",
        )
        child_row = child_by_id.get(row["child_mount_id"])
        require(child_row is not None, f"{label} row selects absent child")
        source_to_child[row["source_mount_id"]] = row["child_mount_id"]
        child_ids.add(row["child_mount_id"])
        clone_rows.append((row, source_row, child_row))
    require(child_ids == set(child_by_id), f"{label} child mapping is not total")
    preserved_scalar_fields = (
        "device_major", "device_minor", "root_bytes_base64",
        "mountpoint_bytes_base64", "filesystem_type",
        "mount_source_bytes_base64", "flags", "super_options",
    )
    for index, (row, source_row, child_row) in enumerate(clone_rows):
        require(
            is_int(row.get("source_raw_parent_mount_id")) and
            row["source_raw_parent_mount_id"] > 0 and
            is_int(row.get("child_raw_parent_mount_id")) and
            row["child_raw_parent_mount_id"] > 0 and
            (row.get("source_parent_mount_id") is None or
             is_int(row["source_parent_mount_id"]) and
             row["source_parent_mount_id"] > 0) and
            (row.get("child_parent_mount_id") is None or
             is_int(row["child_parent_mount_id"]) and
             row["child_parent_mount_id"] > 0) and
            row["source_raw_parent_mount_id"] ==
            source_row["raw_parent_mount_id"] and
            row["child_raw_parent_mount_id"] ==
            child_row["raw_parent_mount_id"] and
            row["source_parent_mount_id"] == source_row["parent_mount_id"] and
            row["child_parent_mount_id"] == child_row["parent_mount_id"],
            f"{label} row {index} parent splice",
        )
        expected_child_parent = (
            None if source_row["parent_mount_id"] is None else
            source_to_child[source_row["parent_mount_id"]]
        )
        require(child_row["parent_mount_id"] == expected_child_parent,
                f"{label} row {index} parent translation mismatch")
        require_exact_json(row["root_identity"], source_row["root_identity"],
                           f"{label} row {index} source root identity")
        require_exact_json(row["root_identity"], child_row["root_identity"],
                           f"{label} row {index} child root identity")
        require_exact_json(
            row["mountpoint_identity"], source_row["mountpoint_identity"],
            f"{label} row {index} source mountpoint identity",
        )
        require_exact_json(
            row["mountpoint_identity"], child_row["mountpoint_identity"],
            f"{label} row {index} child mountpoint identity",
        )
        for field in preserved_scalar_fields:
            require_exact_json(row[field], source_row[field],
                               f"{label} row {index} source {field}")
            require_exact_json(row[field], child_row[field],
                               f"{label} row {index} child {field}")
        require_exact_json(
            row["source_optional_fields"], source_row["optional_fields"],
            f"{label} row {index} source optional fields",
        )
        require_exact_json(
            row["child_optional_fields"], child_row["optional_fields"],
            f"{label} row {index} child optional fields",
        )
        require_exact_json(
            row["source_propagation"], source_row["propagation"],
            f"{label} row {index} source propagation",
        )
        require_exact_json(
            row["child_propagation"], child_row["propagation"],
            f"{label} row {index} child propagation",
        )
        require_exact_json(
            child_row["propagation"], _v4_expected_cloned_propagation(
                source_row["propagation"],
                f"{label} row {index} propagation transform",
            ),
            f"{label} row {index} propagation transform",
        )
        require_exact_json(
            _v4_nonpropagation_optional_fields(source_row["optional_fields"]),
            _v4_nonpropagation_optional_fields(child_row["optional_fields"]),
            f"{label} row {index} nonpropagation optional fields",
        )
    return result


def _validate_v4_initial_fd_ofd_roots(
    fd_table: object, open_descriptions: object,
    initial_edges: list[dict[str, Any]], input_root_edge: dict[str, Any],
    input_root_fd_generation: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _, fds, descriptions = _validate_v4_parent_fd_open_descriptions(
        fd_table, open_descriptions, initial_edges,
    )

    input_description_indices = [
        index for index, description in enumerate(descriptions)
        if description["object_edge_index"] == input_root_edge["index"]
    ]
    require(len(input_description_indices) == 1,
            "input root does not select exactly one initial OFD")
    input_description = descriptions[input_description_indices[0]]
    input_fds = [
        fd for fd in fds
        if fd["open_description_index"] == input_description_indices[0]
    ]
    require(
        len(input_fds) == 1 and
        input_fds[0]["fd_generation"] == input_root_fd_generation and
        input_description["access_mode"] == input_fds[0]["access_mode"] and
        input_description["descriptor_ref_count"] == 1,
        "input root fd/OFD join mismatch",
    )
    return input_fds[0], input_description


_v4_root_authority_input_fields = (
    "initial_object_edges", "fd_table", "open_descriptions", "fs_state",
    "builder_mount_graph", "input_root_identity",
    "input_root_fd_generation",
)


def _derive_v4_build_initial_root_authority(
    initial_object_edges: object, fd_table: object, open_descriptions: object,
    fs_state: object, builder_mount_graph: object,
    input_root_identity: object, input_root_fd_generation: object,
) -> dict[str, Any]:
    label = "V4 initial root authority"
    _require_v4_exact_json_types(
        [initial_object_edges, fd_table, open_descriptions, fs_state,
         builder_mount_graph, input_root_identity, input_root_fd_generation],
        label,
    )
    require(
        type(input_root_identity) is dict and
        is_int(input_root_fd_generation) and input_root_fd_generation > 0,
        f"malformed {label} input closure join",
    )
    edges = _validate_v4_initial_object_edges(initial_object_edges)
    setup_roots = [edge for edge in edges if edge["domain"] == "setup-root"]
    input_roots = [edge for edge in edges if edge["domain"] == "input-root"]
    require(len(setup_roots) == 1 and len(input_roots) == 1,
            "V4 initial roots are not unique")
    state = _v4_exact_dict(fs_state, V4_BUILD_INITIAL_FS_STATE_FIELDS,
                           "V4 initial FS state")
    require(
        type(state.get("root_identity")) is dict and
        type(state.get("cwd_identity")) is dict and
        is_int(state.get("umask")) and 0 <= state["umask"] <= 0o777 and
        is_int(state.get("generation")) and state["generation"] > 0,
        "malformed V4 initial FS state",
    )
    setup_root = _validate_v4_initial_root_edge(
        setup_roots[0], "setup-root", state["root_identity"], None,
    )
    input_root = _validate_v4_initial_root_edge(
        input_roots[0], "input-root", input_root_identity,
        input_root_fd_generation,
    )
    mount_root = _validate_v4_builder_mount_root(
        builder_mount_graph, setup_root,
    )
    input_fd, input_description = _validate_v4_initial_fd_ofd_roots(
        fd_table, open_descriptions, edges, input_root,
        input_root_fd_generation,
    )
    return {
        "setup_root_edge": setup_root,
        "input_root_edge": input_root,
        "input_root_fd": input_fd,
        "input_root_open_description": input_description,
        "initial_fs_state": state,
        "builder_mount_root": mount_root,
        "builder_mounts": builder_mount_graph["mounts"],
        "builder_mount_namespace_identity": builder_mount_graph[
            "mount_namespace_identity"
        ],
        "builder_mount_generation": builder_mount_graph["generation"],
    }


def validate_v4_build_initial_root_authority(
    initial_object_edges: object, fd_table: object, open_descriptions: object,
    fs_state: object, builder_mount_graph: object,
    input_root_identity: object, input_root_fd_generation: object,
) -> dict[str, Any]:
    """Validate and snapshot every input needed to rederive setup authority."""
    values = (
        initial_object_edges, fd_table, open_descriptions, fs_state,
        builder_mount_graph, input_root_identity, input_root_fd_generation,
    )
    _derive_v4_build_initial_root_authority(*values)
    return json.loads(canonical_value_bytes(dict(zip(
        _v4_root_authority_input_fields, values, strict=True,
    ))))


def _validate_v4_event_object_edge(
    value: object, index: int, allowed_domains: tuple[str, ...], label: str,
) -> dict[str, Any]:
    edge = _v4_exact_dict(value, V4_BUILD_OBJECT_EDGE_FIELDS, label)
    require(
        is_int(edge.get("index")) and edge["index"] == index and
        edge.get("domain") in allowed_domains and
        type(edge.get("root_identity")) is dict and
        is_int(edge.get("root_fd_generation")) and
        edge["root_fd_generation"] > 0 and
        type(edge.get("parent_descriptor_identity")) is dict and
        is_int(edge.get("mount_id")) and edge["mount_id"] > 0 and
        is_int(edge.get("st_dev")) and edge["st_dev"] >= 0 and
        is_int(edge.get("st_ino")) and edge["st_ino"] > 0 and
        is_int(edge.get("stable_generation")) and
        edge["stable_generation"] > 0 and
        type(edge.get("resolved_relative")) is str and
        type(edge.get("symlink_decisions")) is list,
        f"malformed {label}",
    )
    domain = edge["domain"]
    if domain == "input-root-entry":
        require(
            is_int(edge.get("input_root_entry_index")) and
            edge["input_root_entry_index"] >= 0 and
            edge.get("output_generation_index") is None and
            edge.get("post_tree_entry_index") is None and
            edge["resolved_relative"] != ".",
            f"malformed {label} input selector",
        )
    elif domain == "output-generation":
        require(
            edge.get("input_root_entry_index") is None and
            is_int(edge.get("output_generation_index")) and
            edge["output_generation_index"] >= 0 and
            (
                edge.get("post_tree_entry_index") is None or
                is_int(edge["post_tree_entry_index"]) and
                edge["post_tree_entry_index"] >= 0
            ) and edge["resolved_relative"] != ".",
            f"malformed {label} output selector",
        )
    else:
        require(
            domain == "output-root" and
            edge.get("input_root_entry_index") is None and
            edge.get("output_generation_index") is None and
            edge.get("post_tree_entry_index") is None and
            edge["resolved_relative"] == "." and
            edge["symlink_decisions"] == [],
            f"malformed {label} output-root selector",
        )
    if edge["resolved_relative"] != ".":
        _v4_source_tree_relative(
            edge["resolved_relative"], f"{label} resolved relative",
        )
    return edge


def _validate_v4_root_authority_context(value: object) -> dict[str, Any]:
    label = "V4 root-authority input snapshot"
    _require_v4_exact_json_types(value, label)
    result = _v4_exact_dict(value, _v4_root_authority_input_fields, label)
    return _derive_v4_build_initial_root_authority(*(
        result[field] for field in _v4_root_authority_input_fields
    ))


def validate_v4_build_event_object_edges(
    value: object, *, phase: object, setup_step_index: object = None,
    root_authority: object = None,
) -> list[dict[str, Any]]:
    label = "V4 build event object edges"
    _require_v4_exact_json_types([value, phase, setup_step_index], label)
    require(type(value) is list and len(value) <= V4_BUILD_TRANSITION_PER_EVENT_MAX,
            f"malformed {label} list")
    if phase == "setup":
        require(
            is_int(setup_step_index) and
            0 <= setup_step_index < len(V4_BUILD_SETUP_SEQUENCE),
            f"malformed {label} setup step",
        )
        setup_row = V4_BUILD_SETUP_SEQUENCE[setup_step_index]
        capture_row = V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY[setup_step_index]
        require(setup_row[0] == setup_step_index and
                capture_row[0] == setup_row[1],
                f"misordered {label} setup policy")
        object_count_policy = capture_row[5]
        require(object_count_policy[0] == "exact-values",
                f"nonexact {label} setup cardinality")
        expected_count = object_count_policy[1]
        require(len(value) == expected_count,
                f"wrong {label} setup cardinality")
        if expected_count == 0:
            require(root_authority is None,
                    f"unexpected {label} root authority")
            return value
        authority = _validate_v4_root_authority_context(root_authority)
        role = setup_row[1]
        initial_edge = (
            authority["setup_root_edge"]
            if role == "private-mount-propagation"
            else authority["input_root_edge"]
        )
        expected = enumerate_isolated_native_build_setup_root_edge_v1(
            role, initial_edge,
            authority["setup_root_edge"]["root_identity"],
            authority["input_root_edge"]["root_identity"],
            authority["input_root_fd"]["fd_generation"],
        )
        require_exact_json(value[0], expected, f"{label} setup root")
        return value
    require(phase == "post-filter" and setup_step_index is None and
            root_authority is None,
            f"malformed {label} phase dispatch")
    for index, edge in enumerate(value):
        _validate_v4_event_object_edge(
            edge, index, V4_BUILD_OBJECT_EDGE_DOMAINS,
            f"{label} post-filter entry {index}",
        )
    return value


def _validate_v4_setup_fs_state(value: object, label: str) -> dict[str, Any]:
    state = _v4_exact_dict(value, V4_BUILD_INITIAL_FS_STATE_FIELDS, label)
    require(
        type(state.get("root_identity")) is dict and
        type(state.get("cwd_identity")) is dict and
        is_int(state.get("umask")) and 0 <= state["umask"] <= 0o777 and
        is_int(state.get("generation")) and state["generation"] > 0,
        f"malformed {label}",
    )
    return state


def _derive_v4_setup_root_fs_states(
    root_authority: dict[str, Any], step_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    initial = root_authority["initial_fs_state"]
    setup_root = root_authority["setup_root_edge"]["root_identity"]
    input_root = root_authority["input_root_edge"]["root_identity"]
    generation = initial["generation"]
    states = [json.loads(canonical_value_bytes(initial))]
    states.append({
        **states[-1], "cwd_identity": input_root,
        "generation": generation + 1,
    })
    states.append({
        **states[-1], "root_identity": input_root,
        "generation": generation + 2,
    })
    states.append({
        **states[-1], "cwd_identity": input_root,
        "generation": generation + 3,
    })
    require_exact_json(states[0]["root_identity"], setup_root,
                       "V4 setup initial FS root")
    if step_index == 0:
        return states[0], states[0]
    return states[step_index - 1], states[step_index]


_v4_build_setup_root_observation_fields = (
    "step_index", "role", "entry_capture", "object_edge_count",
    "object_edges", "fs_transition_count", "fs_transitions",
    "state_before_fs", "state_after_fs",
)


def _validate_v4_setup_path_operand(
    value: object, argument_index: int, path: str, label: str,
) -> dict[str, Any]:
    operand = _v4_exact_dict(value, V4_BUILD_PATH_OPERAND_FIELDS, label)
    payload = path.encode("ascii") + b"\x00"
    require(
        is_int(operand.get("index")) and operand["index"] == 0 and
        is_int(operand.get("argument_index")) and
        operand["argument_index"] == argument_index and
        operand.get("dirfd_argument_index") is None and
        operand.get("dirfd") is None and
        operand.get("dirfd_generation") is None and
        is_int(operand.get("pointer")) and operand["pointer"] > 0 and
        operand.get("bytes") == len(payload) and
        operand.get("sha256") == hashlib.sha256(payload).hexdigest() and
        operand.get("payload_base64") == base64.b64encode(payload).decode("ascii") and
        operand.get("nul_terminated") is True and
        type(operand.get("resolution_role")) is str and
        bool(operand["resolution_role"]),
        f"malformed {label}",
    )
    return operand


def validate_v4_build_setup_root_observation(
    value: object, root_authority: object,
) -> dict[str, Any]:
    label = "V4 build setup-root observation"
    _require_v4_exact_json_types(value, label)
    result = _v4_exact_dict(
        value, _v4_build_setup_root_observation_fields, label,
    )
    authority = _validate_v4_root_authority_context(root_authority)
    step_index = result.get("step_index")
    require(is_int(step_index) and 0 <= step_index <= 3,
            f"malformed {label} step index")
    sequence = V4_BUILD_SETUP_SEQUENCE[step_index]
    require(result.get("role") == sequence[1], f"misordered {label} role")
    entry_kind = V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY[step_index][2]
    entry = _v4_exact_dict(
        result.get("entry_capture"), V4_BUILD_ENTRY_CAPTURE_FIELDS[entry_kind],
        f"{label} entry capture",
    )
    expected_operations = (
        "mount", "fchdir", "chroot", "chdir",
    )
    require(
        entry.get("kind") == entry_kind and
        entry.get("operation") == expected_operations[step_index] and
        (
            entry.get("peer_barrier_index") is None or
            is_int(entry["peer_barrier_index"]) and
            entry["peer_barrier_index"] >= 0
        ),
        f"wrong {label} entry capture",
    )
    if step_index == 0:
        require(
            entry.get("source_operand") is None and
            entry.get("filesystem_type_operand") is None and
            entry.get("flags") == 0x44000 and
            entry.get("data_region") is None,
            f"wrong {label} mount arguments",
        )
        _validate_v4_setup_path_operand(
            entry.get("target_operand"), 1, "/", f"{label} mount target",
        )
    elif step_index == 1:
        input_fd = authority["input_root_fd"]
        require(
            is_int(entry.get("fd")) and entry["fd"] == input_fd["fd"] and
            is_int(entry.get("fd_generation")) and
            entry["fd_generation"] == input_fd["fd_generation"] and
            entry.get("command") is None and
            entry.get("scalar_argument") is None and
            entry.get("pointed_argument") is None,
            f"wrong {label} fchdir fd/OFD join",
        )
    else:
        require(
            is_int(entry.get("operand_count")) and
            entry["operand_count"] == 1 and
            type(entry.get("operands")) is list and
            len(entry["operands"]) == 1 and
            entry.get("scalar_flags") is None and
            entry.get("pointed_struct") is None,
            f"wrong {label} path arguments",
        )
        _validate_v4_setup_path_operand(
            entry["operands"][0], 0, "." if step_index == 2 else "/",
            f"{label} path operand",
        )
    edges = result.get("object_edges")
    require(is_int(result.get("object_edge_count")) and
            result["object_edge_count"] == 1 and type(edges) is list,
            f"wrong {label} object-edge count")
    validate_v4_build_event_object_edges(
        edges, phase="setup", setup_step_index=step_index,
        root_authority=root_authority,
    )
    transitions = result.get("fs_transitions")
    require(
        is_int(result.get("fs_transition_count")) and
        result["fs_transition_count"] == 1 and
        type(transitions) is list and len(transitions) == 1,
        f"wrong {label} FS-transition count",
    )
    before = _validate_v4_setup_fs_state(
        result.get("state_before_fs"), f"{label} state before",
    )
    after = _validate_v4_setup_fs_state(
        result.get("state_after_fs"), f"{label} state after",
    )
    expected_before, expected_after = _derive_v4_setup_root_fs_states(
        authority, step_index,
    )
    require_exact_json(before, expected_before, f"{label} state before")
    require_exact_json(after, expected_after, f"{label} state after")
    edge = edges[0]
    if step_index == 0:
        transition = _v4_exact_dict(
            transitions[0],
            V4_BUILD_FS_TRANSITION_FIELDS["mount-propagation-change"],
            f"{label} mount transition",
        )
        affected = transition.get("affected_mount_ids")
        builder_mounts = authority["builder_mounts"]
        expected_affected = [mount["mount_id"] for mount in builder_mounts]
        expected_old = [mount["propagation"] for mount in builder_mounts]
        private_propagation = {
            "shared_group_id": None, "master_group_id": None,
            "propagate_from_group_id": None, "unbindable": False,
        }
        require(
            transition.get("kind") == "mount-propagation-change" and
            is_int(transition.get("index")) and transition["index"] == 0 and
            is_int(transition.get("before_generation")) and
            transition["before_generation"] ==
            authority["builder_mount_generation"] and
            is_int(transition.get("after_generation")) and
            transition["after_generation"] ==
            authority["builder_mount_generation"] + 1 and
            is_int(transition.get("affected_mount_count")) and
            type(affected) is list and
            all(is_int(mount_id) and mount_id > 0 for mount_id in affected) and
            len(affected) == transition["affected_mount_count"] and
            affected == expected_affected and
            edge["mount_id"] in affected and
            type(transition.get("old_propagations")) is list and
            type(transition.get("new_propagations")) is list,
            f"wrong {label} mount transition join",
        )
        require_exact_json(
            transition["mount_namespace_identity"],
            authority["builder_mount_namespace_identity"],
            f"{label} mount namespace identity",
        )
        require_exact_json(transition["old_propagations"], expected_old,
                           f"{label} old propagations")
        require_exact_json(
            transition["new_propagations"],
            [private_propagation for _ in builder_mounts],
            f"{label} new propagations",
        )
    else:
        transition_kind = (
            "root-change" if step_index == 2 else "cwd-change"
        )
        transition = _v4_exact_dict(
            transitions[0], V4_BUILD_FS_TRANSITION_FIELDS[transition_kind],
            f"{label} {transition_kind}",
        )
        require(
            transition.get("kind") == transition_kind and
            is_int(transition.get("index")) and transition["index"] == 0 and
            is_int(transition.get("fs_state_id")) and
            transition["fs_state_id"] > 0 and
            is_int(transition.get("before_generation")) and
            transition["before_generation"] == before["generation"] and
            is_int(transition.get("after_generation")) and
            transition["after_generation"] == after["generation"] and
            is_int(transition.get("object_edge_index")) and
            transition["object_edge_index"] == 0,
            f"wrong {label} FS transition join",
        )
    return result


def require_exact_json(value: Any, expected: Any, label: str) -> None:
    try:
        value_bytes = canonical_value_bytes(value)
        expected_bytes = canonical_value_bytes(expected)
    except (TypeError, ValueError) as error:
        raise ProtocolError(f"malformed exact JSON {label}: {error}") from error
    require(value_bytes == expected_bytes, f"exact JSON {label} mismatch")


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def content_record(value: Any) -> dict[str, object]:
    encoded = canonical_json_bytes(value)
    return {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ProtocolError(f"non-finite JSON number: {value}")


def _bounded_json_integer(value: str, max_digits: int) -> int:
    digits = value[1:] if value.startswith("-") else value
    require(
        1 <= len(digits) <= max_digits,
        "JSON integer exceeds decimal digit cap",
    )
    return int(value)


def _finite_json_float(value: str) -> float:
    result = float(value)
    require(math.isfinite(result), "non-finite JSON number")
    return result


def decode_object(
    data: bytes, label: str, *, integer_max_digits: int | None = None,
) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_int=(
                int if integer_max_digits is None else
                lambda item: _bounded_json_integer(item, integer_max_digits)
            ),
            parse_float=_finite_json_float,
            parse_constant=_reject_nonfinite,
        )
    except ProtocolError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError,
            RecursionError) as error:
        raise ProtocolError(f"cannot decode {label}: {error}") from error
    require(isinstance(value, dict), f"{label} is not a JSON object")
    return value


def validate_canonical_bytes(
    data: bytes, label: str, validator: Callable[[object], dict[str, Any]], *,
    integer_max_digits: int | None = None,
) -> dict[str, Any]:
    require(type(data) is bytes, f"{label} is not immutable bytes")
    value = decode_object(
        data, label, integer_max_digits=integer_max_digits,
    )
    try:
        canonical = canonical_json_bytes(value)
    except ProtocolError:
        raise
    except (TypeError, ValueError, RecursionError) as error:
        raise ProtocolError(f"cannot canonicalize {label}: {error}") from error
    require(data == canonical, f"{label} is not canonical JSON")
    return validator(value)


def _hex(value: object, pattern: re.Pattern[str], label: str) -> str:
    require(isinstance(value, str) and pattern.fullmatch(value) is not None,
            f"malformed {label}")
    return value


def _printable(value: object, label: str) -> str:
    require(isinstance(value, str) and value and
            all(32 <= ord(character) < 127 for character in value),
            f"malformed {label}")
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return value


def _safe_relative(value: object, label: str) -> str:
    text = _printable(value, label)
    require("\\" not in text, f"malformed {label}")
    path = PurePosixPath(text)
    require(not path.is_absolute() and path.as_posix() == text and
            all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe {label}")
    return text


def _v4_source_tree_relative(value: object, label: str) -> str:
    require(
        type(value) is str and value and
        all(32 <= ord(character) < 127 for character in value),
        f"malformed {label}",
    )
    encoded = value.encode("ascii")
    require(
        len(encoded) <= V4_SAFE_RELATIVE_MAX_BYTES and
        not value.startswith("/") and "\\" not in value and "\x00" not in value,
        f"unsafe {label}",
    )
    components = value.split("/")
    require(
        all(
            component not in {"", ".", ".."} and
            len(component.encode("ascii")) <= V4_SAFE_PATH_COMPONENT_MAX_BYTES
            for component in components
        ),
        f"unsafe {label}",
    )
    require(
        PFT_NAMESPACE.search(value) is None,
        f"PFT namespace is forbidden in {label}",
    )
    return value


def _safe_absolute(value: object, label: str) -> str:
    text = _printable(value, label)
    require(len(text) <= 4096 and "\\" not in text and
            text.startswith("/") and not text.startswith("//"),
            f"malformed {label}")
    path = PurePosixPath(text)
    require(text != "/" and path.is_absolute() and path.as_posix() == text and
            all(part not in {"", ".", ".."} and len(part) <= 255
                for part in path.parts[1:]),
            f"unsafe {label}")
    return text


def _logical_key(value: object, label: str) -> str:
    text = _printable(value, label)
    repository, separator, relative = text.partition(":")
    require(separator == ":" and repository in {"candle", "flyspeck"},
            f"malformed {label} namespace")
    _safe_relative(relative, label)
    require(text not in CANDLE_ONLY_REFERENCE_EXCLUSIONS,
            f"Candle-only control or setup harness is forbidden in {label}")
    return text


def _content_record(
    value: object, label: str, *, allow_empty: bool = False,
) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {"bytes", "sha256"} and
            is_int(value.get("bytes")) and
            (value["bytes"] >= 0 if allow_empty else value["bytes"] > 0),
            f"malformed {label} content record")
    _hex(value.get("sha256"), HEX64, f"{label} SHA-256")
    return value


def _named_content_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "path", "bytes", "sha256",
            }, f"malformed {label}")
    _safe_relative(value.get("path"), f"{label} path")
    _content_record(
        {"bytes": value.get("bytes"), "sha256": value.get("sha256")}, label,
    )
    return value


def validate_native_source_tree(value: object) -> dict[str, Any]:
    label = "V4 native source tree"
    require(type(value) is dict and
            all(type(key) is str for key in value) and set(value) == {
                "schema", "kind", "authority_role", "root_policy",
                "file_count", "total_bytes", "ordered_file_sha256", "files",
            }, f"malformed {label}")
    require(
        is_int(value.get("schema")) and
        value["schema"] == V4_NATIVE_SOURCE_TREE_SCHEMA and
        type(value.get("kind")) is str and
        value.get("kind") == V4_NATIVE_SOURCE_TREE_KIND and
        type(value.get("authority_role")) is str and
        value.get("authority_role") in V4_NATIVE_SOURCE_TREE_ROLES and
        type(value.get("root_policy")) is str and
        value.get("root_policy") == V4_NATIVE_SOURCE_TREE_ROOT_POLICY and
        is_int(value.get("file_count")) and
        1 <= value["file_count"] <= V4_SOURCE_TREE_MEMBER_MAX and
        is_int(value.get("total_bytes")) and
        0 <= value["total_bytes"] <= V4_SOURCE_TREE_TOTAL_MAX_BYTES and
        type(value.get("files")) is list and
        len(value["files"]) == value["file_count"],
        f"malformed {label} header",
    )
    require(type(value.get("ordered_file_sha256")) is str,
            f"malformed {label} ordered-file SHA-256 type")
    _hex(
        value.get("ordered_file_sha256"), HEX64,
        f"{label} ordered-file SHA-256",
    )

    total_bytes = 0
    previous_relative: bytes | None = None
    for index, record in enumerate(value["files"]):
        record_label = f"{label} file {index}"
        require(type(record) is dict and
                all(type(key) is str for key in record) and set(record) == {
                    "index", "relative", "mode", "bytes", "sha256",
                }, f"malformed {record_label}")
        require(
            is_int(record.get("index")) and record["index"] == index and
            is_int(record.get("mode")) and record["mode"] in {
                V4_SOURCE_TREE_DATA_MODE, V4_SOURCE_TREE_EXECUTABLE_MODE,
            } and
            is_int(record.get("bytes")) and
            0 < record["bytes"] <= V4_SOURCE_TREE_FILE_MAX_BYTES,
            f"malformed {record_label} fields",
        )
        relative = _v4_source_tree_relative(
            record.get("relative"), f"{record_label} relative path",
        )
        relative_bytes = relative.encode("ascii")
        require(
            previous_relative is None or previous_relative < relative_bytes,
            f"unordered or duplicate {label} relative path",
        )
        previous_relative = relative_bytes
        require(type(record.get("sha256")) is str,
                f"malformed {record_label} SHA-256 type")
        _hex(record.get("sha256"), HEX64, f"{record_label} SHA-256")
        total_bytes += record["bytes"]
        require(
            total_bytes <= V4_SOURCE_TREE_TOTAL_MAX_BYTES,
            f"{label} total bytes exceed cap",
        )

    require(total_bytes == value["total_bytes"],
            f"{label} total-byte mismatch")
    require(
        value["ordered_file_sha256"] == canonical_sha256(value["files"]),
        f"{label} ordered-file digest mismatch",
    )
    return value


def validate_canonical_native_source_tree_bytes(data: bytes) -> dict[str, Any]:
    label = "V4 native source-tree authority"
    require(type(data) is bytes, f"{label} is not immutable bytes")
    require(len(data) <= V4_AUTHORITY_OBJECT_MAX_BYTES,
            f"{label} exceeds retained cap")
    return validate_canonical_bytes(
        data, label, validate_native_source_tree,
        integer_max_digits=JSON_INTEGER_MAX_DIGITS,
    )


def classify_isolated_native_build_runtime_input_v1(path: object) -> str:
    text = _v4_source_tree_relative(path, "V4 native build runtime-input path")
    basename = text.rsplit("/", 1)[-1]
    if basename.endswith((".h", ".hh", ".hpp", ".hxx", ".inc")):
        return "header"
    if re.fullmatch(r"crt[^/]*\.o", basename) is not None:
        return "startup-object"
    if basename.endswith((".ld", ".lds")):
        return "linker-script"
    if basename.endswith(".a"):
        return "static-library"
    if re.search(r"\.so(?:\.[0-9]+)*$", basename) is not None:
        return "shared-library"
    return "runtime-data"


def _v4_full_regular_mode(value: object, label: str) -> int:
    require(
        is_int(value) and value == (0o100000 | (value & 0o777)),
        f"malformed {label} regular-file mode",
    )
    return value


def _v4_native_build_executable_record(
    value: object, label: str,
) -> dict[str, Any]:
    require(type(value) is dict and
            all(type(key) is str for key in value) and set(value) == {
                "argument_path", "resolved_path", "bytes", "sha256", "mode",
                "version",
            }, f"malformed {label}")
    require(type(value.get("argument_path")) is str and
            type(value.get("resolved_path")) is str,
            f"malformed {label} path type")
    _safe_absolute(value["argument_path"], f"{label} argument path")
    _safe_absolute(value["resolved_path"], f"{label} resolved path")
    require(is_int(value.get("bytes")) and
            0 < value["bytes"] <= V4_BUILD_INPUT_CLOSURE_FILE_MAX_BYTES,
            f"malformed {label} byte count")
    require(type(value.get("sha256")) is str, f"malformed {label} SHA-256 type")
    _hex(value["sha256"], HEX64, f"{label} SHA-256")
    mode = _v4_full_regular_mode(value.get("mode"), label)
    require(mode & 0o111 != 0, f"non-executable {label} mode")
    require(type(value.get("version")) is str and value["version"] and
            len(value["version"]) <= V4_BUILD_EXECUTABLE_VERSION_MAX_BYTES and
            all(32 <= ord(character) < 127 for character in value["version"]),
            f"malformed {label} version")
    return value


def _validate_v4_native_build_runtime_inputs(value: object) -> list[dict[str, Any]]:
    label = "V4 native build runtime inputs"
    require(type(value) is list and
            V4_BUILD_RUNTIME_INPUT_MIN <= len(value) <=
            V4_SOURCE_TREE_MEMBER_MAX,
            f"malformed {label}")
    previous_key: tuple[int, bytes] | None = None
    total_bytes = 0
    role_rank = {
        role: index for index, role in enumerate(V4_BUILD_RUNTIME_INPUT_ROLES)
    }
    for index, record in enumerate(value):
        record_label = f"{label} record {index}"
        require(type(record) is dict and
                all(type(key) is str for key in record) and set(record) == {
                    "index", "role", "mode", "content",
                }, f"malformed {record_label}")
        require(is_int(record.get("index")) and record["index"] == index and
                type(record.get("role")) is str and
                record["role"] in V4_BUILD_RUNTIME_INPUT_ROLES,
                f"malformed {record_label} index or role")
        require(is_int(record.get("mode")) and record["mode"] in {
                    V4_SOURCE_TREE_DATA_MODE,
                    V4_SOURCE_TREE_EXECUTABLE_MODE,
                }, f"malformed {record_label} mode")
        content = record.get("content")
        require(type(content) is dict and
                all(type(key) is str for key in content) and set(content) == {
                    "path", "bytes", "sha256",
                }, f"malformed {record_label} content")
        path = _v4_source_tree_relative(
            content.get("path"), f"{record_label} content path",
        )
        require(path.split("/", 1)[0] not in {
                    V4_BUILD_SOURCE_DIRECTORY,
                    V4_BUILD_OUTPUT_DIRECTORY,
                }, f"reserved {record_label} content path")
        require(is_int(content.get("bytes")) and
                0 < content["bytes"] <=
                V4_BUILD_INPUT_CLOSURE_FILE_MAX_BYTES,
                f"malformed {record_label} byte count")
        require(type(content.get("sha256")) is str,
                f"malformed {record_label} SHA-256 type")
        _hex(content["sha256"], HEX64, f"{record_label} SHA-256")
        require(
            record["role"] ==
            classify_isolated_native_build_runtime_input_v1(path),
            f"misclassified {record_label}",
        )
        order_key = (role_rank[record["role"]], path.encode("ascii"))
        require(previous_key is None or previous_key < order_key,
                f"unordered or duplicate {label}")
        previous_key = order_key
        total_bytes += content["bytes"]
        require(total_bytes <= V4_BUILD_INPUT_CLOSURE_TOTAL_MAX_BYTES,
                f"{label} total bytes exceed cap")
    return value


def enumerate_isolated_native_build_root_v2(
    compiler: object, linker: object, source_tree: object,
    runtime_inputs: object,
) -> list[dict[str, Any]]:
    compiler_record = _v4_native_build_executable_record(
        compiler, "V4 native build compiler",
    )
    linker_record = _v4_native_build_executable_record(
        linker, "V4 native build linker",
    )
    source = validate_native_source_tree(source_tree)
    inputs = _validate_v4_native_build_runtime_inputs(runtime_inputs)

    files: dict[str, dict[str, Any]] = {}

    def add_file(
        relative: str, mode: int, byte_count: int, sha256: str,
        selector: dict[str, Any],
    ) -> None:
        _v4_source_tree_relative(relative, "V4 native build root file path")
        require(relative not in files, "duplicate V4 native build root file")
        files[relative] = {
            "relative": relative,
            "object_type": "ordinary-file",
            "mode": mode,
            "bytes": byte_count,
            "sha256": sha256,
            "selector": selector,
        }

    for role, executable in (
        ("build-compiler", compiler_record),
        ("build-linker", linker_record),
    ):
        relative = executable["resolved_path"][1:]
        require(relative.split("/", 1)[0] not in {
                    V4_BUILD_SOURCE_DIRECTORY,
                    V4_BUILD_OUTPUT_DIRECTORY,
                }, f"reserved {role} resolved path")
        add_file(
            relative,
            0o100000 | (executable["mode"] & 0o555),
            executable["bytes"], executable["sha256"], {"kind": role},
        )

    for index, member in enumerate(source["files"]):
        add_file(
            f"{V4_BUILD_SOURCE_DIRECTORY}/{member['relative']}",
            member["mode"], member["bytes"], member["sha256"],
            {"kind": "source-tree-member", "member_index": index},
        )

    for index, item in enumerate(inputs):
        content = item["content"]
        add_file(
            content["path"], item["mode"], content["bytes"],
            content["sha256"],
            {"kind": "build-runtime-input", "input_index": index},
        )

    total_bytes = sum(entry["bytes"] for entry in files.values())
    require(total_bytes <= V4_BUILD_INPUT_CLOSURE_TOTAL_MAX_BYTES,
            "V4 native build root total bytes exceed cap")

    def new_trie_node() -> dict[str, Any]:
        return {"children": {}, "file": None, "explicit_directory": False}

    trie = new_trie_node()
    node_count = 0
    derived_path_bytes = 0

    def insert_path(
        relative: str, file_record: dict[str, Any] | None,
    ) -> None:
        nonlocal node_count, derived_path_bytes
        node = trie
        prefix_bytes = 0
        components = relative.split("/")
        for component_index, component in enumerate(components):
            prefix_bytes += len(component.encode("ascii"))
            if component_index:
                prefix_bytes += 1
            children = node["children"]
            child = children.get(component)
            if child is None:
                require(
                    node_count < V4_BUILD_INPUT_CLOSURE_ENTRY_MAX,
                    "V4 native build root entry count exceeds cap",
                )
                require(
                    derived_path_bytes + prefix_bytes <=
                    V4_BUILD_ROOT_DERIVATION_MAX_BYTES,
                    "V4 native build root derivation work exceeds cap",
                )
                child = new_trie_node()
                children[component] = child
                node_count += 1
                derived_path_bytes += prefix_bytes
            node = child
            if component_index + 1 < len(components):
                require(
                    node["file"] is None,
                    "ordinary file is an ancestor in V4 native build root",
                )
        if file_record is None:
            require(node["file"] is None,
                    "directory collides with V4 native build root file")
            node["explicit_directory"] = True
        else:
            require(
                node["file"] is None and not node["children"] and
                not node["explicit_directory"],
                "file collides with V4 native build root path",
            )
            node["file"] = file_record

    insert_path(V4_BUILD_OUTPUT_DIRECTORY, None)
    insert_path(V4_BUILD_SOURCE_DIRECTORY, None)
    for relative, file_record in files.items():
        insert_path(relative, file_record)

    entries: list[dict[str, Any]] = []
    stack = [
        (component, child)
        for component, child in sorted(
            trie["children"].items(), reverse=True,
        )
    ]
    while stack:
        relative, node = stack.pop()
        if node["file"] is not None:
            entry = node["file"]
        else:
            entry = {
                "relative": relative,
                "object_type": "directory",
                "mode": (
                    V4_DIRECTORY_0700_MODE
                    if relative == V4_BUILD_OUTPUT_DIRECTORY else
                    V4_BUILD_READONLY_DIRECTORY_MODE
                ),
                "bytes": 0,
                "sha256": EMPTY_BYTES_SHA256,
                "selector": None,
            }
        entries.append({"index": len(entries), **entry})
        for component, child in sorted(
            node["children"].items(), reverse=True,
        ):
            stack.append((f"{relative}/{component}", child))

    require(4 <= len(entries) == node_count,
            "V4 native build root entry count mismatch")
    return entries


_v4_build_input_closure_entry_authority_fields = (
    "entry_count", "total_file_bytes", "ordered_entry_sha256", "entries",
    "compiler_entry_index", "linker_entry_index", "source_entry_count",
    "source_entry_indices", "runtime_input_entry_count",
    "runtime_input_entry_indices", "output_root_entry_index",
)


def _v4_resource_checked_json_graph(
    value: object, label: str,
) -> object:
    node_count = 0
    string_bytes = 0
    active_containers: set[int] = set()
    integer_limit = 10 ** JSON_INTEGER_MAX_DIGITS

    def account_text(text: str, maximum: int, text_label: str) -> None:
        nonlocal string_bytes
        require(len(text) <= maximum, f"{text_label} exceeds character cap")
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ProtocolError(f"malformed {text_label}: {error}") from error
        require(len(encoded) <= maximum, f"{text_label} exceeds byte cap")
        string_bytes += len(encoded)
        require(
            string_bytes <= V4_BUILD_INPUT_ENTRY_AUTHORITY_GRAPH_MAX_BYTES,
            f"{label} string bytes exceed graph cap",
        )

    def visit(item: object, depth: int) -> object:
        nonlocal node_count
        require(
            depth <= V4_EXACT_JSON_TYPE_DEPTH_MAX,
            f"{label} JSON depth exceeds cap",
        )
        node_count += 1
        require(
            node_count <= V4_BUILD_INPUT_ENTRY_AUTHORITY_NODE_MAX,
            f"{label} JSON node count exceeds cap",
        )
        if item is None or type(item) is bool:
            return item
        if type(item) is int:
            require(
                -integer_limit < item < integer_limit,
                f"{label} integer exceeds digit cap",
            )
            return item
        if type(item) is str:
            account_text(
                item, V4_BUILD_INPUT_ENTRY_AUTHORITY_STRING_MAX_BYTES,
                f"{label} string",
            )
            return item
        if type(item) not in {list, dict}:
            raise ProtocolError(f"malformed {label} JSON type")
        length = len(item)
        require(
            length <= V4_BUILD_INPUT_ENTRY_AUTHORITY_CONTAINER_MAX,
            f"{label} JSON container exceeds member cap",
        )
        identity = id(item)
        require(
            identity not in active_containers,
            f"cyclic {label} JSON graph",
        )
        active_containers.add(identity)
        try:
            if type(item) is list:
                result_list = []
                for index in range(length):
                    child = visit(item[index], depth + 1)
                    result_list.append(child)
                require(len(item) == length,
                        f"{label} changed during resource preflight")
                return result_list
            keys = tuple(item.keys())
            result_dict = {}
            for key in keys:
                require(type(key) is str, f"malformed {label} key type")
                account_text(
                    key, V4_BUILD_INPUT_ENTRY_AUTHORITY_KEY_MAX_BYTES,
                    f"{label} key",
                )
                child = visit(item[key], depth + 1)
                result_dict[key] = child
            require(tuple(item.keys()) == keys,
                    f"{label} changed during resource preflight")
            return result_dict
        except (IndexError, KeyError, RuntimeError) as error:
            raise ProtocolError(
                f"{label} changed during resource preflight: {error}"
            ) from error
        finally:
            active_containers.remove(identity)

    return visit(value, 0)


def _v4_bounded_compact_canonical_digest(
    value: object, maximum_bytes: int, label: str,
) -> tuple[int, str]:
    require(is_int(maximum_bytes) and maximum_bytes >= 0,
            f"malformed {label} encoded cap")
    encoder = json.JSONEncoder(
        sort_keys=True, separators=(",", ":"), allow_nan=False,
        ensure_ascii=True,
    )
    byte_count = 0
    digest = hashlib.sha256()
    try:
        for fragment in encoder.iterencode(value):
            require(
                len(fragment) <=
                V4_BUILD_INPUT_ENTRY_AUTHORITY_FRAGMENT_MAX_BYTES,
                f"{label} canonical fragment exceeds cap",
            )
            encoded = fragment.encode()
            byte_count += len(encoded)
            require(byte_count <= maximum_bytes,
                    f"{label} exceeds encoded cap")
            digest.update(encoded)
    except (TypeError, ValueError) as error:
        raise ProtocolError(f"malformed {label}: {error}") from error
    return byte_count, digest.hexdigest()


def validate_v4_build_input_closure_inherited_fds(
    value: object,
) -> dict[str, Any]:
    """Validate and snapshot the structural builder inherited-FD authority."""
    label = "V4 native build input-closure inherited FDs"
    first_frozen = _v4_resource_checked_json_graph(value, label)
    first_size, first_digest = _v4_bounded_compact_canonical_digest(
        first_frozen, V4_AUTHORITY_OBJECT_MAX_BYTES, label,
    )
    frozen = _v4_resource_checked_json_graph(value, label)
    frozen_size, frozen_digest = _v4_bounded_compact_canonical_digest(
        frozen, V4_AUTHORITY_OBJECT_MAX_BYTES, label,
    )
    require(
        (frozen_size, frozen_digest) == (first_size, first_digest),
        f"{label} changed while freezing",
    )
    result = _v4_exact_dict(
        frozen, ("inherited_fd_count", "inherited_fds"), label,
    )
    inherited_fds = result.get("inherited_fds")
    require(
        is_int(result.get("inherited_fd_count")) and
        result["inherited_fd_count"] ==
        V4_BUILD_INPUT_CLOSURE_INHERITED_FD_COUNT and
        type(inherited_fds) is list and
        len(inherited_fds) == V4_BUILD_INPUT_CLOSURE_INHERITED_FD_COUNT and
        len(V4_BUILD_INPUT_CLOSURE_INHERITED_FD_LAYOUT) ==
        V4_BUILD_INPUT_CLOSURE_INHERITED_FD_COUNT,
        f"malformed {label} count/list",
    )
    encoded_identities: set[bytes] = set()
    for index, expected in enumerate(
        V4_BUILD_INPUT_CLOSURE_INHERITED_FD_LAYOUT,
    ):
        row_label = f"{label} row {index}"
        row = _v4_exact_dict(
            inherited_fds[index],
            V4_BUILD_INPUT_CLOSURE_INHERITED_FD_FIELDS,
            row_label,
        )
        fd, role, access_mode = expected
        generation = _v4_uint(
            row.get("fd_generation"), 64, f"{row_label} generation",
        )
        identity = row.get("object_identity")
        require(
            is_int(row.get("fd")) and row["fd"] == fd and
            type(row.get("role")) is str and row["role"] == role and
            type(row.get("access_mode")) is str and
            row["access_mode"] == access_mode and
            type(identity) is dict and generation > 0 and
            type(row.get("cloexec")) is bool and not row["cloexec"],
            f"malformed {row_label}",
        )
        identity_bytes = canonical_value_bytes(identity)
        require(
            identity_bytes not in encoded_identities,
            f"duplicate {label} object identity",
        )
        encoded_identities.add(identity_bytes)
    return result


def validate_v4_build_input_closure_entry_authority(
    compiler: object, linker: object, source_tree: object,
    runtime_inputs: object, value: object,
) -> dict[str, Any]:
    """Validate and snapshot the derived entry/selector closure authority."""
    label = "V4 native build input-closure entry authority"
    raw_graph = {
        "compiler": compiler,
        "linker": linker,
        "source_tree": source_tree,
        "runtime_inputs": runtime_inputs,
        "entry_authority": value,
    }
    first_frozen = _v4_resource_checked_json_graph(raw_graph, label)
    first_size, first_digest = _v4_bounded_compact_canonical_digest(
        first_frozen, V4_BUILD_INPUT_ENTRY_AUTHORITY_GRAPH_MAX_BYTES, label,
    )
    frozen = _v4_resource_checked_json_graph(raw_graph, label)
    require(type(frozen) is dict, f"malformed frozen {label}")
    frozen_size, frozen_digest = _v4_bounded_compact_canonical_digest(
        frozen, V4_BUILD_INPUT_ENTRY_AUTHORITY_GRAPH_MAX_BYTES, label,
    )
    require(
        (frozen_size, frozen_digest) == (first_size, first_digest),
        f"{label} changed while freezing",
    )
    compiler = frozen["compiler"]
    linker = frozen["linker"]
    source_tree = frozen["source_tree"]
    runtime_inputs = frozen["runtime_inputs"]
    value = frozen["entry_authority"]
    result = _v4_exact_dict(
        value, _v4_build_input_closure_entry_authority_fields, label,
    )
    expected = enumerate_isolated_native_build_root_v2(
        compiler, linker, source_tree, runtime_inputs,
    )
    entries = result.get("entries")
    require(
        is_int(result.get("entry_count")) and
        4 <= result["entry_count"] <= V4_BUILD_INPUT_CLOSURE_ENTRY_MAX and
        type(entries) is list and len(entries) == result["entry_count"] and
        len(entries) == len(expected),
        f"malformed {label} entry count/list",
    )

    observed_fields = set(V4_BUILD_INPUT_CLOSURE_OBSERVED_ENTRY_FIELDS)
    total_file_bytes = 0
    stable_objects: set[tuple[int, int, int]] = set()
    for index, entry in enumerate(entries):
        entry_label = f"{label} entry {index}"
        item = _v4_exact_dict(
            entry, V4_BUILD_INPUT_CLOSURE_ENTRY_FIELDS, entry_label,
        )
        projected = {
            key: item[key] for key in V4_BUILD_INPUT_CLOSURE_ENTRY_FIELDS
            if key not in observed_fields
        }
        require_exact_json(projected, expected[index],
                           f"{entry_label} derived projection")
        st_nlink = _v4_uint(
            item.get("st_nlink"), 64, f"{entry_label} st_nlink",
        )
        if item["object_type"] == "ordinary-file":
            require(st_nlink == 1, f"wrong {entry_label} file link count")
            total_file_bytes += item["bytes"]
            require(
                total_file_bytes <= V4_BUILD_INPUT_CLOSURE_TOTAL_MAX_BYTES,
                f"{label} total bytes exceed cap",
            )
        else:
            require(st_nlink > 0, f"wrong {entry_label} directory link count")
        parent_identity = item.get("parent_descriptor_identity")
        require(type(parent_identity) is dict,
                f"malformed {entry_label} parent descriptor identity")
        _require_v4_exact_json_types(
            parent_identity, f"{entry_label} parent descriptor identity",
        )
        mount_id = _v4_uint(
            item.get("mount_id"), 32, f"{entry_label} mount ID",
        )
        st_dev = _v4_uint(
            item.get("st_dev"), 64, f"{entry_label} st_dev",
        )
        st_ino = _v4_uint(item.get("st_ino"), 64, f"{entry_label} st_ino")
        generation = _v4_uint(
            item.get("stable_generation"), 64,
            f"{entry_label} stable generation",
        )
        require(
            mount_id > 0 and st_ino > 0 and generation > 0,
            f"malformed {entry_label} observed identity",
        )
        stable_object = (mount_id, st_dev, st_ino)
        require(
            stable_object not in stable_objects,
            f"duplicate {entry_label} stable object identity",
        )
        stable_objects.add(stable_object)

    require(
        is_int(result.get("total_file_bytes")) and
        result["total_file_bytes"] == total_file_bytes,
        f"{label} total-byte mismatch",
    )
    _, entry_digest = _v4_bounded_compact_canonical_digest(
        entries, V4_AUTHORITY_OBJECT_MAX_BYTES, f"{label} entries",
    )
    require(
        type(result.get("ordered_entry_sha256")) is str and
        result["ordered_entry_sha256"] == entry_digest,
        f"{label} ordered-entry digest mismatch",
    )

    compiler_indices: list[int] = []
    linker_indices: list[int] = []
    source_by_member: dict[int, int] = {}
    runtime_by_input: dict[int, int] = {}
    output_root_indices: list[int] = []
    for entry in expected:
        selector = entry["selector"]
        if selector is None:
            if entry["relative"] == V4_BUILD_OUTPUT_DIRECTORY:
                output_root_indices.append(entry["index"])
            continue
        kind = selector["kind"]
        if kind == "build-compiler":
            compiler_indices.append(entry["index"])
        elif kind == "build-linker":
            linker_indices.append(entry["index"])
        elif kind == "source-tree-member":
            source_by_member[selector["member_index"]] = entry["index"]
        else:
            require(kind == "build-runtime-input",
                    f"unknown {label} derived selector")
            runtime_by_input[selector["input_index"]] = entry["index"]
    source_count = source_tree["file_count"]
    runtime_count = len(runtime_inputs)
    require(
        len(compiler_indices) == 1 and len(linker_indices) == 1 and
        len(output_root_indices) == 1 and
        set(source_by_member) == set(range(source_count)) and
        set(runtime_by_input) == set(range(runtime_count)),
        f"incomplete {label} derived selectors",
    )
    expected_source_indices = [
        source_by_member[index] for index in range(source_count)
    ]
    expected_runtime_indices = [
        runtime_by_input[index] for index in range(runtime_count)
    ]
    require(
        is_int(result.get("compiler_entry_index")) and
        result["compiler_entry_index"] == compiler_indices[0] and
        is_int(result.get("linker_entry_index")) and
        result["linker_entry_index"] == linker_indices[0] and
        is_int(result.get("source_entry_count")) and
        result["source_entry_count"] == source_count and
        type(result.get("source_entry_indices")) is list and
        all(is_int(item) for item in result["source_entry_indices"]) and
        result["source_entry_indices"] == expected_source_indices and
        is_int(result.get("runtime_input_entry_count")) and
        result["runtime_input_entry_count"] == runtime_count and
        type(result.get("runtime_input_entry_indices")) is list and
        all(is_int(item) for item in result["runtime_input_entry_indices"]) and
        result["runtime_input_entry_indices"] == expected_runtime_indices and
        is_int(result.get("output_root_entry_index")) and
        result["output_root_entry_index"] == output_root_indices[0],
        f"{label} selector projection mismatch",
    )
    _v4_bounded_compact_canonical_digest(
        result, V4_AUTHORITY_OBJECT_MAX_BYTES, label,
    )
    return frozen


def enumerate_isolated_native_build_filter_v6() -> dict[str, Any]:
    load_word_absolute = 0x20
    jump_equal = 0x15
    jump_mask_nonzero = 0x45
    return_constant = 0x06
    instructions: list[dict[str, int]] = []

    def emit(code: int, jump_true: int, jump_false: int, constant: int) -> None:
        instructions.append({
            "index": len(instructions),
            "code": code,
            "jt": jump_true,
            "jf": jump_false,
            "k": constant,
        })

    emit(load_word_absolute, 0, 0, 4)
    emit(jump_equal, 1, 0, V4_BUILD_FILTER_AUDIT_ARCH)
    emit(return_constant, 0, 0, V4_BUILD_FILTER_RET_KILL_PROCESS)
    emit(load_word_absolute, 0, 0, 0)
    emit(jump_mask_nonzero, 0, 1, V4_BUILD_FILTER_X32_SYSCALL_BIT)
    emit(return_constant, 0, 0, V4_BUILD_FILTER_RET_ENOSYS)

    denied = dict(V4_BUILD_FILTER_DENIED_SYSCALLS)
    for syscall_number in sorted((*denied, V4_BUILD_FILTER_CLONE_SYSCALL)):
        if syscall_number == V4_BUILD_FILTER_CLONE_SYSCALL:
            emit(jump_equal, 0, 4, syscall_number)
            emit(load_word_absolute, 0, 0, 16)
            emit(
                jump_mask_nonzero, 0, 1,
                V4_BUILD_FILTER_CLONE_REJECT_MASK,
            )
            emit(return_constant, 0, 0, V4_BUILD_FILTER_RET_ERRNO)
            emit(load_word_absolute, 0, 0, 0)
        else:
            emit(jump_equal, 0, 1, syscall_number)
            emit(
                return_constant, 0, 0,
                V4_BUILD_FILTER_RET_ENOSYS
                if syscall_number in dict(V4_BUILD_FILTER_ENOSYS_SYSCALLS)
                else V4_BUILD_FILTER_RET_ERRNO,
            )
    emit(return_constant, 0, 0, V4_BUILD_FILTER_RET_ALLOW)

    require(
        len(instructions) == V4_BUILD_FILTER_INSTRUCTION_COUNT,
        "V4 native build filter instruction-count mismatch",
    )
    for instruction in instructions:
        if instruction["code"] in {jump_equal, jump_mask_nonzero}:
            for jump in (instruction["jt"], instruction["jf"]):
                require(
                    instruction["index"] + 1 + jump < len(instructions),
                    "V4 native build filter jump escapes program",
                )
    payload = b"".join(
        struct.pack(
            "<HBBI", instruction["code"], instruction["jt"],
            instruction["jf"], instruction["k"],
        )
        for instruction in instructions
    )
    require(
        len(payload) == V4_BUILD_FILTER_INSTRUCTIONS_BYTES,
        "V4 native build filter payload-size mismatch",
    )

    decoded_policy: list[dict[str, Any]] = [{
        "index": 0,
        "architecture": "not-linux-x86-64",
        "syscall_number": -1,
        "argument_policy": [],
        "decision": "kill-process",
        "ret_data": 0,
    }]
    decoded_policy.append({
        "index": len(decoded_policy),
        "architecture": "linux-x86-64-x32-number",
        "syscall_number": -1,
        "argument_policy": [{
            "index": 0,
            "argument_index": -1,
            "operation": "masked-nonzero",
            "mask": V4_BUILD_FILTER_X32_SYSCALL_BIT,
            "value": None,
        }],
        "decision": "errno",
        "ret_data": 38,
    })
    for syscall_number in sorted((*denied, V4_BUILD_FILTER_CLONE_SYSCALL)):
        argument_policy: list[dict[str, Any]] = []
        if syscall_number == V4_BUILD_FILTER_CLONE_SYSCALL:
            argument_policy.append({
                "index": 0,
                "argument_index": 0,
                "operation": "masked-nonzero",
                "mask": V4_BUILD_FILTER_CLONE_REJECT_MASK,
                "value": None,
            })
        decoded_policy.append({
            "index": len(decoded_policy),
            "architecture": "linux-x86-64",
            "syscall_number": syscall_number,
            "argument_policy": argument_policy,
            "decision": "errno",
            "ret_data": (
                38 if syscall_number in dict(V4_BUILD_FILTER_ENOSYS_SYSCALLS)
                else V4_BUILD_FILTER_ERRNO
            ),
        })
    decoded_policy.append({
        "index": len(decoded_policy),
        "architecture": "linux-x86-64",
        "syscall_number": -1,
        "argument_policy": [],
        "decision": "allow",
        "ret_data": 0,
    })
    require(
        len(decoded_policy) == V4_BUILD_FILTER_DECODED_RULE_COUNT,
        "V4 native build filter decoded-rule-count mismatch",
    )
    return {
        "schema": V4_BUILD_FILTER_SCHEMA,
        "kind": V4_BUILD_FILTER_KIND,
        "policy": V4_BUILD_FILTER_POLICY,
        "architecture": "linux-x86-64",
        "audit_arch": V4_BUILD_FILTER_AUDIT_ARCH,
        "instruction_count": len(instructions),
        "instructions_bytes": len(payload),
        "instructions_sha256": hashlib.sha256(payload).hexdigest(),
        "instructions_payload_base64": base64.b64encode(payload).decode("ascii"),
        "decoded_rule_count": len(decoded_policy),
        "decoded_policy": decoded_policy,
        "policy_sha256": canonical_sha256(decoded_policy),
    }


def _require_v4_exact_json_types(value: object, label: str) -> None:
    stack = [(value, label, 0)]
    node_count = 1
    while stack:
        item, item_label, depth = stack.pop()
        require(depth <= V4_EXACT_JSON_TYPE_DEPTH_MAX,
                f"{label} JSON depth exceeds cap")
        if item is None or type(item) in {bool, int, str}:
            continue
        if type(item) is list:
            child_count = len(item)
            require(
                node_count + child_count <= V4_EXACT_JSON_TYPE_NODE_MAX,
                f"{label} JSON node count exceeds cap",
            )
            node_count += child_count
            for index, child in enumerate(item):
                stack.append((child, f"{item_label}[{index}]", depth + 1))
            continue
        if type(item) is dict:
            require(all(type(key) is str for key in item),
                    f"malformed {item_label} key type")
            child_count = len(item)
            require(
                node_count + child_count <= V4_EXACT_JSON_TYPE_NODE_MAX,
                f"{label} JSON node count exceeds cap",
            )
            node_count += child_count
            for key, child in item.items():
                stack.append((child, f"{item_label}.{key}", depth + 1))
            continue
        raise ProtocolError(f"malformed {item_label} JSON type")


def enumerate_isolated_native_build_setup_root_edge_v1(
    role: object,
    initial_edge: object,
    setup_root_identity: object,
    input_root_identity: object,
    input_root_fd_generation: object,
) -> dict[str, Any]:
    """Derive the sole setup-event edge for a root-selection operation."""
    label = "V4 isolated native build setup root edge"
    _require_v4_exact_json_types(
        [role, initial_edge, setup_root_identity, input_root_identity,
         input_root_fd_generation],
        label,
    )
    require(type(role) is str, f"malformed {label} role")
    require(
        type(setup_root_identity) is dict and
        type(input_root_identity) is dict and
        is_int(input_root_fd_generation) and
        input_root_fd_generation > 0,
        f"malformed {label} authority joins",
    )
    policies = {
        row[0]: row for row in V4_BUILD_SETUP_ROOT_EDGE_ROLE_POLICY
    }
    require(role in policies, f"unknown {label} role")
    require(
        type(initial_edge) is dict and
        set(initial_edge) == set(V4_BUILD_INITIAL_OBJECT_EDGE_FIELDS),
        f"malformed {label} initial edge",
    )
    policy = policies[role]
    expected_domain = policy[1]
    expected_initial_domain = policy[2]
    require(
        expected_domain in V4_BUILD_SETUP_ROOT_EDGE_DOMAINS and
        expected_domain in V4_BUILD_EVENT_OBJECT_EDGE_DOMAINS and
        expected_domain not in V4_BUILD_OBJECT_EDGE_DOMAINS,
        f"unregistered {label} domain",
    )
    require(
        initial_edge["domain"] == expected_initial_domain,
        f"wrong {label} initial edge domain",
    )
    require(
        is_int(initial_edge["index"]) and initial_edge["index"] >= 0,
        f"malformed {label} initial edge index",
    )
    require(
        initial_edge["input_root_entry_index"] is None and
        initial_edge["resolved_relative"] == "." and
        initial_edge["symlink_decisions"] == [],
        f"malformed {label} root selection",
    )
    require(
        type(initial_edge["parent_descriptor_identity"]) is dict and
        is_int(initial_edge["mount_id"]) and initial_edge["mount_id"] > 0 and
        is_int(initial_edge["st_dev"]) and initial_edge["st_dev"] >= 0 and
        is_int(initial_edge["st_ino"]) and initial_edge["st_ino"] > 0 and
        is_int(initial_edge["stable_generation"]) and
        initial_edge["stable_generation"] > 0,
        f"incomplete {label} stable identity",
    )
    if expected_domain == "setup-root":
        expected_root_identity = setup_root_identity
        expected_root_fd_generation = None
    else:
        expected_root_identity = input_root_identity
        expected_root_fd_generation = input_root_fd_generation
    require(
        type(expected_root_identity) is dict and
        initial_edge["root_identity"] == expected_root_identity,
        f"wrong {label} root identity join",
    )
    require(
        initial_edge["root_fd_generation"] == expected_root_fd_generation,
        f"wrong {label} root fd generation join",
    )
    return {
        "index": 0,
        "domain": expected_domain,
        "root_identity": json.loads(canonical_value_bytes(
            expected_root_identity
        )),
        "root_fd_generation": expected_root_fd_generation,
        "input_root_entry_index": None,
        "output_generation_index": None,
        "post_tree_entry_index": None,
        "parent_descriptor_identity": json.loads(canonical_value_bytes(
            initial_edge["parent_descriptor_identity"]
        )),
        "mount_id": initial_edge["mount_id"],
        "st_dev": initial_edge["st_dev"],
        "st_ino": initial_edge["st_ino"],
        "stable_generation": initial_edge["stable_generation"],
        "resolved_relative": ".",
        "symlink_decisions": [],
    }


def validate_isolated_native_build_filter(value: object) -> dict[str, Any]:
    label = "V4 isolated native build filter"
    _require_v4_exact_json_types(value, label)
    require(type(value) is dict, f"malformed {label}")
    require_exact_json(
        value, enumerate_isolated_native_build_filter_v6(), label,
    )
    return value


def _repository_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "path", "git_head", "git_status",
            } and value.get("git_status") == "", f"malformed {label}")
    _safe_absolute(value.get("path"), f"{label} path")
    _hex(value.get("git_head"), HEX40, f"{label} Git head")
    return value


def _executable_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "argument_path", "resolved_path", "bytes", "sha256", "mode",
            } and value.get("mode") == "100755", f"malformed {label}")
    _safe_absolute(value.get("argument_path"), f"{label} argument path")
    _safe_absolute(value.get("resolved_path"), f"{label} resolved path")
    _content_record(
        {"bytes": value.get("bytes"), "sha256": value.get("sha256")}, label,
    )
    return value


def _identity_fields(value: object, label: str) -> tuple[str, int, str, str]:
    require(isinstance(value, dict), f"malformed {label}")
    key = _logical_key(value.get("selected_source"), f"{label} source")
    require(is_int(value.get("original_bytes")) and value["original_bytes"] > 0,
            f"malformed {label} byte count")
    sha256 = _hex(value.get("original_sha256"), HEX64, f"{label} SHA-256")
    md5 = _hex(value.get("original_md5"), HEX32, f"{label} MD5")
    return key, value["original_bytes"], sha256, md5


def _execution_selection(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"malformed {label}")
    if value.get("mode") == "original-source":
        require(set(value) == {"mode"}, f"malformed {label}")
        return value
    require(set(value) == {
                "mode", "id", "kind", "normalized_bytes",
                "normalized_sha256", "normalized_md5", "operation_count",
            } and value.get("mode") == "candle-normalization-bound" and
            value.get("kind") == "exact_bytes_replace_sequence" and
            is_int(value.get("normalized_bytes")) and
            value["normalized_bytes"] > 0 and
            is_int(value.get("operation_count")) and
            value["operation_count"] > 0, f"malformed {label}")
    _printable(value.get("id"), f"{label} ID")
    _hex(value.get("normalized_sha256"), HEX64, f"{label} normalized SHA-256")
    _hex(value.get("normalized_md5"), HEX32, f"{label} normalized MD5")
    return value


def _action_target(value: object, selected_source: str, label: str) -> str:
    text = _printable(value, label)
    require("\\" not in text, f"malformed {label}")
    path = PurePosixPath(text)
    parts = path.parts
    require(not path.is_absolute() and path.as_posix() == text and parts and
            all(part not in {"", "."} for part in parts) and
            sum(part == ".." for part in parts) <= 1 and
            (".." not in parts or parts[0] == ".."), f"unsafe {label}")
    resolved = ["text_formalization"]
    for part in parts:
        if part == "..":
            require(len(resolved) == 1, f"unsafe {label}")
            resolved.pop()
        else:
            resolved.append(part)
    require(resolved and selected_source == f"flyspeck:{'/'.join(resolved)}",
            f"{label} does not resolve to selected source")
    return text


def _validate_role_nonce(value: dict[str, Any], label: str) -> None:
    require(value.get("role") == REFERENCE_ROLE and
            is_int(value.get("reference_ordinal")) and
            value["reference_ordinal"] in REFERENCE_ORDINALS and
            value.get("nonce_kind") == REFERENCE_NONCE_KIND,
            f"malformed {label} role/ordinal/nonce kind")
    _hex(value.get("session_nonce"), HEX64, f"{label} session nonce")


def _validate_authority(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "policy", "producer", "repositories", "runtime", "inputs",
            } and value.get("policy") == AUTHORITY_POLICY,
            "malformed pristine reference authority")
    producer = value.get("producer")
    require(isinstance(producer, dict) and set(producer) == {
                "entrypoint", "protocol", "output_parser",
                "direct_release_protocol",
            }, "malformed pristine reference producer authority")
    _named_content_record(producer.get("entrypoint"), "producer entrypoint")
    protocol = _named_content_record(producer.get("protocol"), "producer protocol")
    output_parser = _named_content_record(
        producer.get("output_parser"), "producer output parser",
    )
    direct_protocol = _named_content_record(
        producer.get("direct_release_protocol"),
        "producer direct-release protocol",
    )
    require(producer["entrypoint"]["path"] == PRODUCER_ENTRYPOINT_PATH and
            protocol["path"] == PROTOCOL_PATH and
            output_parser["path"] == OUTPUT_PARSER_PATH and
            direct_protocol["path"] == DIRECT_PROTOCOL_PATH,
            "pristine reference producer/protocol/parser/direct-protocol "
            "path mismatch")

    repositories = value.get("repositories")
    require(isinstance(repositories, dict) and set(repositories) == {
                "project", "hol_light", "flyspeck",
            }, "malformed pristine reference repository authority")
    for name, record in repositories.items():
        _repository_record(record, f"{name} repository")

    runtime = value.get("runtime")
    require(isinstance(runtime, dict) and set(runtime) == {
                "ocaml_hol", "gp", "csdp", "runtime_elf_closure",
            }, "malformed pristine reference runtime authority")
    for name in ("ocaml_hol", "gp", "csdp"):
        _executable_record(runtime[name], f"{name} executable")
    _content_record(runtime.get("runtime_elf_closure"), "runtime ELF closure")

    inputs = value.get("inputs")
    require(isinstance(inputs, dict) and set(inputs) == {
                "action_plan", "source_inventory", "generated_inputs",
                "serializer", "final_target",
            }, "malformed pristine reference input authority")
    for name in ("action_plan", "source_inventory", "generated_inputs",
                 "final_target"):
        record = inputs[name]
        _named_content_record(record, f"{name} input")
    serializer = inputs["serializer"]
    require(isinstance(serializer, dict) and set(serializer) == {
                "path", "bytes", "sha256", "md5",
            }, "malformed serializer input")
    _safe_relative(serializer.get("path"), "serializer input path")
    _content_record(
        {"bytes": serializer.get("bytes"), "sha256": serializer.get("sha256")},
        "serializer input",
    )
    _hex(serializer.get("md5"), HEX32, "serializer input MD5")
    require(inputs["serializer"]["path"] == "candle/fingerprint.ml" and
            inputs["final_target"]["path"] ==
            "candle/flyspeck_l2_target.ml",
            "pristine reference serializer/final-target authority mismatch")
    return value


def _validate_actions(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "policy", "execution_selection_semantics", "record_count",
                "ordered_record_sha256", "records",
            } and value.get("policy") == ACTION_POLICY and
            value.get("execution_selection_semantics") ==
            EXECUTION_SELECTION_SEMANTICS and
            is_int(value.get("record_count")) and
            value["record_count"] == FINAL_ACTION_COUNT,
            "malformed pristine reference action plan")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == FINAL_ACTION_COUNT,
            "pristine reference action plan is not exactly 297 records")
    fields = {
        "index", "selected_source", "target", "stratum", "original_bytes",
        "original_sha256", "original_md5", "candle_plan_execution_selection",
    }
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == fields and
                is_int(record.get("index")) and record["index"] == index and
                record.get("stratum") in ACTION_STRATA,
                f"malformed pristine reference action: {index}")
        selected_source, _, _, _ = _identity_fields(
            record, f"pristine reference action: {index}",
        )
        _action_target(record.get("target"), selected_source,
                       f"pristine reference action target: {index}")
        _execution_selection(
            record.get("candle_plan_execution_selection"),
            f"pristine reference action selection: {index}",
        )
    require(value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference action plan digest mismatch")
    required = {
        LP_WRAPPER_AFTER_ACTION_INDEX: LP_CERTIFICATE_SOURCE,
        LP_VERIFY_ACTION_INDEX: LP_VERIFY_SOURCE,
        LP_CONSUMER_ACTION_INDEX: LP_CONSUMER_SOURCE,
    }
    for index, source in required.items():
        require(records[index]["selected_source"] == source,
                f"pristine reference LP action identity mismatch: {index}")
    return value


def _validate_lp_inputs(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "schema", "kind", "order", "record_count",
                "ordered_record_sha256", "records",
            } and is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == LP_INPUT_KIND and
            value.get("order") == "canonical-relative-path-lexicographic-v1" and
            is_int(value.get("record_count")) and value["record_count"] == 39,
            "malformed pristine reference LP input inventory")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 39,
            "pristine reference LP input inventory is not exactly 39 records")
    previous: str | None = None
    prepared = 0
    identities: set[tuple[str, str, int, str]] = set()
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "class", "relative", "bytes", "sha256",
                } and is_int(record.get("index")) and record["index"] == index and
                record.get("class") in {
                    "lp-certificate", "lp-certificate-prepared",
                } and is_int(record.get("bytes")) and record["bytes"] > 0,
                f"malformed pristine reference LP input: {index}")
        relative = _safe_relative(
            record.get("relative"), f"pristine reference LP input path: {index}",
        )
        require(previous is None or previous < relative,
                f"pristine reference LP input order mismatch: {index}")
        previous = relative
        sha256 = _hex(record.get("sha256"), HEX64,
                      f"pristine reference LP input SHA-256: {index}")
        identity = (record["class"], relative, record["bytes"], sha256)
        require(identity not in identities,
                f"duplicate pristine reference LP input: {index}")
        identities.add(identity)
        prepared += record["class"] == "lp-certificate-prepared"
    require(prepared == 1 and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference LP input identity/digest mismatch")
    return value


def validate_raw_plan(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "fresh_process_replay_from_action_zero",
        "process_state_checkpoint", "serialization_environment",
        "environment_policy", "thread_count", "authority", "actions",
        "lp_certificate_inputs", "retained_stdout_max_bytes",
        "retained_stderr_max_bytes", "retained_input_artifact_root",
        "approval_included", "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and
            value["schema"] == RAW_PROTOCOL_SCHEMA and
            value.get("kind") == PLAN_KIND and
            value.get("boundary_id") == FINAL_BOUNDARY_ID and
            value.get("fresh_process_replay_from_action_zero") is True and
            value.get("process_state_checkpoint") is None and
            value.get("environment_policy") == ENVIRONMENT_POLICY and
            is_int(value.get("thread_count")) and value["thread_count"] == 1 and
            is_int(value.get("retained_stdout_max_bytes")) and
            value["retained_stdout_max_bytes"] == RETAINED_STDOUT_MAX_BYTES and
            is_int(value.get("retained_stderr_max_bytes")) and
            value["retained_stderr_max_bytes"] == RETAINED_STDERR_MAX_BYTES and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine reference raw plan")
    _validate_role_nonce(value, "pristine reference raw plan")
    serialization = value.get("serialization_environment")
    require(isinstance(serialization, dict) and set(serialization) == {
                "key", "present",
            } and serialization.get("key") == SERIALIZATION_ENVIRONMENT_KEY and
            serialization.get("present") is False,
            "FLYSPECK_SERIALIZATION must be absent from pristine reference plan")
    _validate_authority(value.get("authority"))
    _validate_actions(value.get("actions"))
    _validate_lp_inputs(value.get("lp_certificate_inputs"))
    _safe_absolute(
        value.get("retained_input_artifact_root"),
        "retained input artifact root",
    )
    return value


def _same_run(value: dict[str, Any], plan: dict[str, Any], label: str) -> None:
    require(value.get("role") == plan["role"] and
            value.get("reference_ordinal") == plan["reference_ordinal"] and
            value.get("nonce_kind") == plan["nonce_kind"] and
            value.get("session_nonce") == plan["session_nonce"] and
            value.get("boundary_id") == plan["boundary_id"],
            f"{label} run identity differs from plan")


def validate_raw_request(value: object, plan: object) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request_source",
        "entrypoint_sequence", "marker_contract", "action_count",
        "serialization_environment", "fresh_process_replay_from_action_zero",
        "process_state_checkpoint", "retained_stdout_max_bytes",
        "retained_stderr_max_bytes", "retained_input_artifact_root",
        "approval_included", "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and
            value["schema"] == RAW_PROTOCOL_SCHEMA and
            value.get("kind") == REQUEST_KIND and
            is_int(value.get("action_count")) and
            value["action_count"] == FINAL_ACTION_COUNT and
            value.get("fresh_process_replay_from_action_zero") is True and
            value.get("process_state_checkpoint") is None and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine reference request")
    require_exact_json(
        value.get("entrypoint_sequence"), list(ENTRYPOINT_SEQUENCE),
        "pristine reference request entrypoint sequence",
    )
    require_exact_json(
        value.get("marker_contract"), MARKER_CONTRACT,
        "pristine reference request marker contract",
    )
    require_exact_json(
        value.get("serialization_environment"),
        plan["serialization_environment"],
        "pristine reference request serialization environment",
    )
    for field in (
        "retained_stdout_max_bytes", "retained_stderr_max_bytes",
        "retained_input_artifact_root",
    ):
        require_exact_json(
            value.get(field), plan[field],
            f"pristine reference request {field}",
        )
    _validate_role_nonce(value, "pristine reference request")
    _same_run(value, plan, "pristine reference request")
    require_exact_json(
        value.get("plan"), content_record(plan),
        "pristine reference request plan content",
    )
    _named_content_record(value.get("request_source"), "reference request source")
    return value


def _validate_action_completions(
    value: object, plan: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "record_count", "ordered_record_sha256", "initial_ledger_count",
        "final_ledger_count", "records",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("record_count")) and
            value["record_count"] == FINAL_ACTION_COUNT and
            is_int(value.get("initial_ledger_count")) and
            value["initial_ledger_count"] >= 0 and
            is_int(value.get("final_ledger_count")) and
            value["final_ledger_count"] >= value["initial_ledger_count"],
            "malformed pristine reference action completions")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == FINAL_ACTION_COUNT,
            "pristine reference transcript is not exactly 297 actions")
    expected_start = value["initial_ledger_count"]
    fields = {
        "index", "session_nonce", "selected_source", "source_sha256",
        "completion_status", "ledger_start_index", "ledger_end_index",
        "ordered_ledger_delta_sha256", "loader_outcome",
        "selected_ledger_index",
    }
    plan_actions = plan["actions"]["records"]
    for index, (record, action) in enumerate(zip(records, plan_actions, strict=True)):
        require(isinstance(record, dict) and set(record) == fields and
                is_int(record.get("index")) and record["index"] == index and
                record.get("session_nonce") == plan["session_nonce"] and
                record.get("selected_source") == action["selected_source"] and
                record.get("source_sha256") == action["original_sha256"] and
                record.get("completion_status") == "completed-observed-unapproved" and
                is_int(record.get("ledger_start_index")) and
                record["ledger_start_index"] == expected_start and
                is_int(record.get("ledger_end_index")) and
                record["ledger_end_index"] >= record["ledger_start_index"] and
                record.get("loader_outcome") in {"loaded", "already-loaded"} and
                is_int(record.get("selected_ledger_index")) and
                record["selected_ledger_index"] >= 0,
                f"malformed pristine reference action completion: {index}")
        _hex(record.get("ordered_ledger_delta_sha256"), HEX64,
             f"action completion loader delta SHA-256: {index}")
        expected_start = record["ledger_end_index"]
    require(expected_start == value["final_ledger_count"] and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference action completion count/digest mismatch")
    return value


def _validate_lp_successes(
    value: object, plan: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema", "kind", "order", "record_count", "ordered_record_sha256",
        "records",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == LP_SUCCESS_KIND and value.get("order") == LP_ORDER and
            is_int(value.get("record_count")) and value["record_count"] == 39,
            "malformed pristine reference LP success stream")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 39,
            "pristine reference transcript is not exactly 39 LP successes")
    inputs = plan["lp_certificate_inputs"]["records"]
    input_indices: set[int] = set()
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "session_nonce", "action_index", "input_index",
                    "class", "relative", "bytes", "sha256",
                    "successful_deserialization_count",
                } and is_int(record.get("index")) and record["index"] == index and
                record.get("session_nonce") == plan["session_nonce"] and
                is_int(record.get("action_index")) and
                record["action_index"] == LP_CONSUMER_ACTION_INDEX and
                is_int(record.get("input_index")) and
                0 <= record["input_index"] < 39 and
                is_int(record.get("successful_deserialization_count")) and
                record["successful_deserialization_count"] == 1,
                f"malformed pristine reference LP success: {index}")
        input_index = record["input_index"]
        require(input_index not in input_indices,
                f"duplicate pristine reference LP success: {index}")
        input_indices.add(input_index)
        expected = inputs[input_index]
        require(all(record[field] == expected[field] for field in (
                    "class", "relative", "bytes", "sha256",
                )), f"pristine reference LP success differs from input: {index}")
    require(input_indices == set(range(39)) and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference LP success identity/digest mismatch")
    return value


def validate_raw_transcript(
    value: object, plan: object, request: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request", "marker_protocol",
        "stdout", "stderr", "exit_code", "timed_out", "session_started",
        "session_completed", "action_completions", "lp_successes", "status",
        "approval_included", "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and
            value["schema"] == RAW_PROTOCOL_SCHEMA and
            value.get("kind") == TRANSCRIPT_KIND and
            value.get("marker_protocol") == MARKER_PROTOCOL and
            is_int(value.get("exit_code")) and value["exit_code"] == 0 and
            value.get("timed_out") is False and
            value.get("session_started") is True and
            value.get("session_completed") is True and
            value.get("status") == "process-complete-unapproved" and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine reference transcript")
    _validate_role_nonce(value, "pristine reference transcript")
    _same_run(value, plan, "pristine reference transcript")
    require_exact_json(
        value.get("plan"), content_record(plan),
        "pristine reference transcript plan content",
    )
    require_exact_json(
        value.get("request"), content_record(request),
        "pristine reference transcript request content",
    )
    _content_record(value.get("stdout"), "reference stdout")
    stderr = _content_record(
        value.get("stderr"), "reference stderr", allow_empty=True,
    )
    require(stderr["bytes"] == RETAINED_STDERR_MAX_BYTES and
            stderr["sha256"] == EMPTY_BYTES_SHA256,
            "pristine reference stderr is not the exact empty-byte record")
    _validate_action_completions(value.get("action_completions"), plan)
    _validate_lp_successes(value.get("lp_successes"), plan)
    return value


def _validate_loader_events(
    value: object, session_nonce: str,
) -> list[dict[str, Any]]:
    require(isinstance(value, list) and value,
            "pristine native loader ledger is empty")
    identities: set[str] = set()
    fields = {
        "index", "session_nonce", "phase", "action_index", "logical_source",
        "basename", "bytes", "sha256", "md5",
    }
    for index, record in enumerate(value):
        require(isinstance(record, dict) and set(record) == fields and
                is_int(record.get("index")) and record["index"] == index and
                record.get("session_nonce") == session_nonce and
                record.get("phase") in {"bootstrap", "action", "post-action"} and
                is_int(record.get("bytes")) and record["bytes"] > 0,
                f"malformed pristine native loader event: {index}")
        key = _logical_key(record.get("logical_source"),
                           f"native loader event source: {index}")
        relative = key.partition(":")[2]
        require(record.get("basename") == PurePosixPath(relative).name,
                f"native loader event basename mismatch: {index}")
        sha256 = _hex(record.get("sha256"), HEX64,
                      f"native loader event SHA-256: {index}")
        md5 = _hex(record.get("md5"), HEX32,
                   f"native loader event MD5: {index}")
        require(key not in identities,
                f"duplicate pristine native loader identity: {index}")
        identities.add(key)
        action_index = record.get("action_index")
        if record["phase"] == "action":
            require(is_int(action_index) and 0 <= action_index < FINAL_ACTION_COUNT,
                    f"native loader action index mismatch: {index}")
        else:
            require(action_index is None,
                    f"non-action loader event has action index: {index}")
    return value


def validate_native_execution_closure(
    value: object, plan: object, request: object, transcript: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    transcript = validate_raw_transcript(transcript, plan, request)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request", "transcript",
        "loader_policy", "loader_order", "loader_parentage_observed",
        "loader_cache_outcomes_observed", "loader_ledger_artifact",
        "loader_event_count", "ordered_loader_event_sha256", "loader_events",
        "pre_action_event_count", "post_action_event_count", "action_bindings",
        "lp_success_artifact", "lp_successes", "raw_lp_order_retained",
        "unsupported_identity_count", "status", "approval_included", "pft_used",
        "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and
            value["schema"] == RAW_PROTOCOL_SCHEMA and
            value.get("kind") == NATIVE_CLOSURE_KIND and
            value.get("loader_policy") == LOADER_LEDGER_POLICY and
            value.get("loader_order") == LOADER_LEDGER_ORDER and
            value.get("loader_parentage_observed") is False and
            value.get("loader_cache_outcomes_observed") is False and
            value.get("raw_lp_order_retained") is True and
            is_int(value.get("unsupported_identity_count")) and
            value["unsupported_identity_count"] == 0 and
            value.get("status") == "native-observation-complete-unapproved" and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine native execution closure")
    _validate_role_nonce(value, "pristine native execution closure")
    _same_run(value, plan, "pristine native execution closure")
    require_exact_json(
        value.get("plan"), content_record(plan),
        "pristine native closure plan content",
    )
    require_exact_json(
        value.get("request"), content_record(request),
        "pristine native closure request content",
    )
    require_exact_json(
        value.get("transcript"), content_record(transcript),
        "pristine native closure transcript content",
    )
    _content_record(value.get("loader_ledger_artifact"),
                    "native loader-ledger artifact")
    _content_record(value.get("lp_success_artifact"), "native LP-success artifact")

    events = _validate_loader_events(
        value.get("loader_events"), plan["session_nonce"],
    )
    require(is_int(value.get("loader_event_count")) and
            value["loader_event_count"] == len(events) and
            value.get("ordered_loader_event_sha256") == canonical_sha256(events),
            "pristine native loader event count/digest mismatch")
    action_bindings = value.get("action_bindings")
    require_exact_json(
        action_bindings, transcript["action_completions"],
        "native action bindings versus transcript",
    )
    initial = action_bindings["initial_ledger_count"]
    final = action_bindings["final_ledger_count"]
    require(is_int(value.get("pre_action_event_count")) and
            value["pre_action_event_count"] == initial and
            is_int(value.get("post_action_event_count")) and
            value["post_action_event_count"] == len(events) - final and
            0 <= initial <= final <= len(events),
            "native loader phase cardinality mismatch")
    require(all(event["phase"] == "bootstrap" and event["action_index"] is None
                for event in events[:initial]) and
            all(event["phase"] == "post-action" and
                event["action_index"] is None for event in events[final:]),
            "native loader bootstrap/post-action phase mismatch")
    bootstrap_keys = [event["logical_source"] for event in events[:initial]]
    require(HOL_LIGHT_SOURCE in bootstrap_keys and
            STRICTBUILD_SOURCE in bootstrap_keys and
            bootstrap_keys.index(HOL_LIGHT_SOURCE) <
            bootstrap_keys.index(STRICTBUILD_SOURCE),
            "native bootstrap lacks ordered HOL Light/strictbuild anchors")

    plan_actions = plan["actions"]["records"]
    for index, (binding, action) in enumerate(zip(
        action_bindings["records"], plan_actions, strict=True,
    )):
        start = binding["ledger_start_index"]
        end = binding["ledger_end_index"]
        require(end <= final and
                all(event["phase"] == "action" and
                    event["action_index"] == index for event in events[start:end]) and
                binding["ordered_ledger_delta_sha256"] ==
                canonical_sha256(events[start:end]),
                f"native loader delta differs from action binding: {index}")
        selected_index = binding["selected_ledger_index"]
        if binding["loader_outcome"] == "loaded":
            require(start <= selected_index < end,
                    f"loaded action lacks selected ledger event: {index}")
        else:
            require(selected_index < start,
                    f"already-loaded action lacks prior ledger event: {index}")
        selected = events[selected_index]
        require(selected["logical_source"] == action["selected_source"] and
                selected["bytes"] == action["original_bytes"] and
                selected["sha256"] == action["original_sha256"] and
                selected["md5"] == action["original_md5"],
                f"native selected loader identity differs from action: {index}")

    post_keys = [event["logical_source"] for event in events[final:]]
    require(post_keys.count(FINAL_TARGET_SOURCE) == 1 and
            post_keys.count(SERIALIZER_SOURCE) == 1 and
            post_keys[-2:] == [FINAL_TARGET_SOURCE, SERIALIZER_SOURCE],
            "native closure lacks ordered final-target/serializer suffix")
    inputs = plan["authority"]["inputs"]
    by_key = {event["logical_source"]: event for event in events[final:]}
    for key, input_name in (
        (FINAL_TARGET_SOURCE, "final_target"),
        (SERIALIZER_SOURCE, "serializer"),
    ):
        event = by_key[key]
        claimed = inputs[input_name]
        require(event["bytes"] == claimed["bytes"] and
                event["sha256"] == claimed["sha256"],
                f"native {input_name} differs from authority")
        if input_name == "serializer":
            require(event["md5"] == claimed["md5"],
                    "native serializer MD5 differs from authority")

    lp_successes = _validate_lp_successes(value.get("lp_successes"), plan)
    require_exact_json(
        lp_successes, transcript["lp_successes"],
        "native LP successes versus transcript",
    )
    return value


_DIRECT_PROTOCOL: ModuleType | None = globals().get(
    "_TRUSTED_DIRECT_PROTOCOL_MODULE_INPUT"
)


def _direct_protocol() -> ModuleType:
    module = _DIRECT_PROTOCOL
    require(isinstance(module, ModuleType),
            "trusted exact direct-release protocol activation is required")
    require(type(getattr(module, "FINAL_ACTION_COUNT", None)) is int and
            module.FINAL_ACTION_COUNT == FINAL_ACTION_COUNT and
            getattr(module, "FINAL_BOUNDARY_ID", None) == FINAL_BOUNDARY_ID and
            getattr(module, "REFERENCE_COMPARISON_ROLE", None) ==
            REFERENCE_ROLE and
            getattr(module, "REFERENCE_COMPARISON_NONCE_KIND", None) ==
            REFERENCE_NONCE_KIND and
            tuple(getattr(module, "FINAL_THEOREM_NAMES", ())) ==
            FINAL_THEOREM_NAMES and
            isinstance(getattr(module, "CROSS_RUNTIME_EXCLUDED_LOGICAL_KEYS", None),
                       tuple) and
            all(type(item) is str for item in
                module.CROSS_RUNTIME_EXCLUDED_LOGICAL_KEYS) and
            module.CROSS_RUNTIME_EXCLUDED_LOGICAL_KEYS ==
            CANDLE_ONLY_REFERENCE_EXCLUSIONS,
            "incompatible direct-release protocol sibling")
    return module


def validate_semantic_completion_observation(
    value: object, plan: object, request: object, transcript: object,
    semantic_projection: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    transcript = validate_raw_transcript(transcript, plan, request)
    direct = _direct_protocol()
    try:
        semantic_projection = direct.validate_semantic_projection(
            semantic_projection,
        )
    except direct.ProtocolError as error:
        raise ProtocolError(
            f"invalid pristine semantic projection: {error}"
        ) from error
    fields = {
        "schema", "kind", "status", "role", "reference_ordinal",
        "nonce_kind", "session_nonce", "boundary_id", "plan", "request",
        "transcript", "theorem_count", "dependency_count",
        "ordered_theorem_name_sha256", "semantic_projection",
        "approved_reference_present", "dependency_history_is_kernel_trace",
        "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == SEMANTIC_COMPLETION_KIND and
            value.get("status") == SEMANTIC_COMPLETE_STATUS and
            is_int(value.get("theorem_count")) and
            value["theorem_count"] == len(FINAL_THEOREM_NAMES) and
            is_int(value.get("dependency_count")) and
            value["dependency_count"] == len(FINAL_THEOREM_NAMES) and
            value.get("ordered_theorem_name_sha256") ==
            canonical_sha256(list(FINAL_THEOREM_NAMES)) and
            value.get("approved_reference_present") is False and
            value.get("dependency_history_is_kernel_trace") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine semantic completion observation")
    _validate_role_nonce(value, "pristine semantic completion observation")
    _same_run(value, plan, "pristine semantic completion observation")
    for field, expected in (
        ("plan", content_record(plan)),
        ("request", content_record(request)),
        ("transcript", content_record(transcript)),
        ("semantic_projection", content_record(semantic_projection)),
    ):
        require_exact_json(
            value.get(field), expected,
            f"pristine semantic completion {field} content",
        )
    return value


def validate_source_rederivation(
    value: object, plan: object, request: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request", "stdout",
        "stderr", "process_result", "transcript", "native_execution_closure",
        "semantic_projection", "semantic_completion_observation",
        "cross_runtime_coverage", "semantic_status", "coverage_status",
        "authentication_status", "candidate_included", "approval_included",
        "promotion_allowed", "pft_used", "s2_eligible", "s3_eligible",
        "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and
            value["schema"] == RAW_PROTOCOL_SCHEMA and
            value.get("kind") == SOURCE_REDERIVATION_KIND and
            value.get("semantic_status") == SEMANTIC_COMPLETE_STATUS and
            value.get("coverage_status") == COVERAGE_INCOMPLETE_STATUS and
            value.get("cross_runtime_coverage") is None and
            value.get("authentication_status") == "not-authenticated" and
            value.get("candidate_included") is False and
            value.get("approval_included") is False and
            value.get("promotion_allowed") is False and
            value.get("pft_used") is False and
            value.get("s2_eligible") is False and
            value.get("s3_eligible") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine source rederivation")
    _validate_role_nonce(value, "pristine source rederivation")
    _same_run(value, plan, "pristine source rederivation")
    require_exact_json(
        value.get("plan"), content_record(plan),
        "pristine source rederivation plan content",
    )
    require_exact_json(
        value.get("request"), content_record(request),
        "pristine source rederivation request content",
    )
    stdout = _content_record(
        value.get("stdout"), "source-rederivation stdout",
    )
    stderr = _content_record(
        value.get("stderr"), "source-rederivation stderr", allow_empty=True,
    )
    require(stdout["bytes"] <= plan["retained_stdout_max_bytes"] and
            stderr["bytes"] == plan["retained_stderr_max_bytes"],
            "source-rederivation output content exceeds retained caps")
    require(stderr["sha256"] == EMPTY_BYTES_SHA256,
            "source-rederivation stderr is not the exact empty-byte record")
    process_result = value.get("process_result")
    require(isinstance(process_result, dict) and set(process_result) == {
                "exit_code", "timed_out",
            } and is_int(process_result.get("exit_code")) and
            process_result["exit_code"] == 0 and
            process_result.get("timed_out") is False,
            "source-rederivation process result is not exact success")
    transcript = validate_raw_transcript(
        value.get("transcript"), plan, request,
    )
    require_exact_json(
        stdout, transcript["stdout"],
        "source-rederivation stdout versus transcript",
    )
    require_exact_json(
        stderr, transcript["stderr"],
        "source-rederivation stderr versus transcript",
    )
    require(process_result["exit_code"] == transcript["exit_code"] and
            process_result["timed_out"] is transcript["timed_out"],
            "source-rederivation process result differs from transcript")
    native_closure = validate_native_execution_closure(
        value.get("native_execution_closure"), plan, request, transcript,
    )
    direct = _direct_protocol()
    try:
        semantic_projection = direct.validate_semantic_projection(
            value.get("semantic_projection"),
        )
    except direct.ProtocolError as error:
        raise ProtocolError(
            f"invalid source-rederivation semantic projection: {error}"
        ) from error
    serializer_event = native_closure["loader_events"][-1]
    require(
        semantic_projection["serializer"] == {
            "path": serializer_event["logical_source"].partition(":")[2],
            "sha256": serializer_event["sha256"],
        },
        "source-rederivation semantic serializer differs from native closure",
    )
    validate_semantic_completion_observation(
        value.get("semantic_completion_observation"), plan, request,
        transcript, semantic_projection,
    )
    return value


def validate_raw_candidate(
    value: object, plan: object, request: object, transcript: object,
    native_closure: object, semantic_projection: object,
    coverage_projection: object,
) -> dict[str, Any]:
    # Schema v3 candidates require the descriptor-rooted capture envelope,
    # coverage adapter, pending publication, and terminal postflight specified
    # by the accepted design.  None exists in this pure migration slice.  Keep
    # the legacy signature fail closed so no value-only caller can mint or
    # consume an underspecified v3 candidate.
    raise ProtocolError(
        "schema-v3 raw candidate validation requires the future held collector "
        "and descriptor-rooted terminal postflight"
    )


BUNDLE_FIELDS = {
    "plan", "request", "request_source_capture", "transcript",
    "native_execution_closure", "semantic_projection",
    "semantic_completion_observation", "cross_runtime_coverage",
    "source_rederivation", "capture_envelope", "candidate",
    "capture_completion",
}


def validate_reference_bundle(value: object) -> dict[str, Any]:
    raise ProtocolError(
        "schema-v3 bundle consumption requires the future descriptor-rooted "
        "capture-bundle validator"
    )


def validate_distinct_reference_pair(
    first: object, second: object,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raise ProtocolError(
        "schema-v3 reference-pair consumption requires two future "
        "descriptor-rooted capture bundles"
    )


def _v4_consumption_disabled(label: str) -> None:
    """Reject before decoding or traversing any caller-supplied V4 value."""
    raise ProtocolError(
        f"V4 {label} consumption is disabled until the captured supervisor, "
        "pending publication and terminal descriptor-rooted postflight exist"
    )


def validate_v4_raw_candidate(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("raw candidate")


def validate_v4_capture_envelope(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("capture envelope")


def validate_v4_pending_candidate(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("pending candidate")


def validate_v4_capture_completion(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("capture completion")


def validate_v4_reference_bundle(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("reference bundle")


def validate_v4_distinct_reference_pair(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("reference pair")


def validate_v4_postflight_result(value: object) -> dict[str, Any]:
    del value
    _v4_consumption_disabled("postflight result")


def validate_canonical_v4_raw_candidate_bytes(data: bytes) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical raw candidate")


def validate_canonical_v4_capture_envelope_bytes(
    data: bytes,
) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical capture envelope")


def validate_canonical_v4_pending_candidate_bytes(
    data: bytes,
) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical pending candidate")


def validate_canonical_v4_capture_completion_bytes(
    data: bytes,
) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical capture completion")


def validate_canonical_v4_reference_bundle_bytes(
    data: bytes,
) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical reference bundle")


def validate_canonical_v4_distinct_reference_pair_bytes(
    data: bytes,
) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical reference pair")


def validate_canonical_postflight_result_bytes(data: bytes) -> dict[str, Any]:
    del data
    _v4_consumption_disabled("canonical postflight result")


def validate_canonical_raw_plan_bytes(data: bytes) -> dict[str, Any]:
    return validate_canonical_bytes(data, "pristine raw plan", validate_raw_plan)


def validate_canonical_raw_request_bytes(
    data: bytes, plan: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine raw request", lambda value: validate_raw_request(value, plan),
    )


def validate_canonical_raw_transcript_bytes(
    data: bytes, plan: object, request: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine raw transcript",
        lambda value: validate_raw_transcript(value, plan, request),
    )


def validate_canonical_native_closure_bytes(
    data: bytes, plan: object, request: object, transcript: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine native closure",
        lambda value: validate_native_execution_closure(
            value, plan, request, transcript,
        ),
    )


def validate_canonical_source_rederivation_bytes(
    data: bytes, plan: object, request: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine source rederivation",
        lambda value: validate_source_rederivation(value, plan, request),
    )


def validate_canonical_raw_candidate_bytes(
    data: bytes, plan: object, request: object, transcript: object,
    native_closure: object, semantic_projection: object,
    coverage_projection: object,
) -> dict[str, Any]:
    raise ProtocolError(
        "schema-v3 canonical raw candidate decoding is disabled until the "
        "future held collector and descriptor-rooted terminal postflight"
    )
