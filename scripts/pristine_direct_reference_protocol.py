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
V4_BUILD_EXECUTION_OBSERVATION_SCHEMA = 6
V4_BUILD_EXECUTION_OBSERVATION_KIND = (
    "candle-flyspeck-isolated-native-build-execution-observation-v6"
)
V4_BUILD_EXECUTION_OBSERVATION_POLICY = (
    "outside-parent-all-task-source-consumption-and-output-chronology-v6"
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
    "candle-flyspeck-v4-initial-state-seed-v4"
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
    "candle-flyspeck-v4-setup-replay-state-v4"
)
V4_BUILD_SETUP_STATE_DIGEST_PREIMAGE = (
    "ascii-domain-nul-canonical-json-array-of-ordered-field-values-v1"
)
V4_BUILD_SETUP_POLICY = (
    "derived-pre-filter-builder-setup-deny-all-other-v5"
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
