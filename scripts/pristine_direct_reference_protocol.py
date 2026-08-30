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
V4_BUILD_INPUT_CLOSURE_SCHEMA = 1
V4_BUILD_INPUT_CLOSURE_KIND = (
    "candle-flyspeck-isolated-native-build-input-closure-v1"
)
V4_BUILD_INPUT_CLOSURE_POLICY = (
    "outside-parent-held-pivot-root-exhaustive-input-tree-v1"
)
V4_BUILD_INPUT_CLOSURE_ENTRY_MAX = 196_608
V4_BUILD_INPUT_CLOSURE_FILE_MAX_BYTES = 1_073_741_824
V4_BUILD_INPUT_CLOSURE_TOTAL_MAX_BYTES = 68_719_476_736
V4_BUILD_READONLY_DIRECTORY_MODE = 16_749
V4_BUILD_SOURCE_DIRECTORY = "candle-source"
V4_BUILD_OUTPUT_DIRECTORY = "candle-output"
V4_BUILD_ROOT_DERIVATION_MAX_BYTES = 33_554_432
V4_BUILD_FILTER_SCHEMA = 1
V4_BUILD_FILTER_KIND = (
    "candle-flyspeck-isolated-native-build-seccomp-filter-v1"
)
V4_BUILD_FILTER_POLICY = (
    "isolated-native-build-post-pivot-deny-escape-network-ipc-v1"
)
V4_BUILD_FILTER_ERRNO = 1
V4_BUILD_FILTER_CLONE_SYSCALL = 56
V4_BUILD_FILTER_CLONE_NAMESPACE_MASK = 0x7E820000
V4_BUILD_FILTER_AUDIT_ARCH = 0xC000003E
V4_BUILD_FILTER_X32_SYSCALL_BIT = 0x40000000
V4_BUILD_FILTER_INSTRUCTION_COUNT = 122
V4_BUILD_FILTER_INSTRUCTIONS_BYTES = 976
V4_BUILD_FILTER_DECODED_RULE_COUNT = 59
V4_BUILD_FILTER_RET_KILL_PROCESS = 0x80000000
V4_BUILD_FILTER_RET_ERRNO = 0x00050001
V4_BUILD_FILTER_RET_ENOSYS = 0x00050026
V4_BUILD_FILTER_RET_ALLOW = 0x7FFF0000
V4_BUILD_FILTER_DENIED_SYSCALLS = (
    (29, "shmget"),
    (30, "shmat"),
    (31, "shmctl"),
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
    (298, "perf_event_open"),
    (303, "name_to_handle_at"),
    (304, "open_by_handle_at"),
    (308, "setns"),
    (310, "process_vm_readv"),
    (311, "process_vm_writev"),
    (321, "bpf"),
    (323, "userfaultfd"),
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
V4_BUILD_EXECUTION_OBSERVATION_SCHEMA = 1
V4_BUILD_EXECUTION_OBSERVATION_KIND = (
    "candle-flyspeck-isolated-native-build-execution-observation-v1"
)
V4_BUILD_EXECUTION_OBSERVATION_POLICY = (
    "outside-parent-all-task-source-consumption-and-output-chronology-v1"
)
V4_BUILD_EXECUTION_TASK_MAX = 4_096
V4_BUILD_EXECUTION_EVENT_MAX = 131_072
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
    "initial-stop",
    "interrupt-stop",
    "signal-delivery-stop",
    "group-stop",
    "syscall-entry",
    "syscall-exit",
    "fork",
    "vfork",
    "clone",
    "vfork-done",
    "exec",
    "exec-tid-rebase",
    "exit",
    "terminal-wait",
    "pre-output-walk",
    "post-output-walk",
    "output-hash-barrier",
)
V4_BUILD_EVENT_NONNULL_FIELDS = {
    "namespace-clone": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "initial-stop": (
        "subject_task_identity", "raw_wait_status", "reinject_signal",
        "task_transition",
    ),
    "interrupt-stop": (
        "subject_task_identity", "raw_wait_status", "signal_number",
        "reinject_signal",
    ),
    "signal-delivery-stop": (
        "subject_task_identity", "raw_wait_status", "signal_number",
        "siginfo", "reinject_signal",
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
        "subject_task_identity", "syscall_number", "return_value",
        "exit_capture",
    ),
    "fork": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "vfork": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "clone": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "vfork-done": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "exec": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "exec-tid-rebase": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "exit": (
        "subject_task_identity", "ptrace_event_message", "task_transition",
    ),
    "terminal-wait": (
        "subject_task_identity", "raw_wait_status", "task_transition",
    ),
    "pre-output-walk": (
        "root_entry_index", "fd_generation", "object_edge",
    ),
    "post-output-walk": (
        "root_entry_index", "fd_generation", "object_edge",
    ),
    "output-hash-barrier": (
        "root_entry_index", "fd_generation", "object_edge",
    ),
}
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
V4_AUTHORITY_CAPSULE_MAX_BYTES = 587_202_560
V4_AUTHORITY_CAPSULE_READ_MAX_BYTES = 587_202_561
V4_POSTFLIGHT_RESULT_MAX_BYTES = 1_073_741_824
V4_POSTFLIGHT_RESULT_READ_MAX_BYTES = 1_073_741_825
V4_TRACE_CHUNK_MAX_BYTES = 67_108_864
V4_TRACE_CHUNK_COUNT_MAX = 4_096
V4_TRACE_TOTAL_MAX_BYTES = 274_877_906_944
V4_AUTHORITY_OBJECT_MAX_BYTES = 33_554_432
V4_AUTHORITY_OBJECT_READ_MAX_BYTES = 33_554_433
V4_FIXED_SOURCE_MAX_BYTES = 16_777_216
V4_STARTUP_DESIGN_MAX_BYTES = 1_048_576
V4_AUTHORITY_CAPSULE_DECODED_MAX_BYTES = 437_256_192
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


def enumerate_isolated_native_build_root_v1(
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


def enumerate_isolated_native_build_filter_v1() -> dict[str, Any]:
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
                V4_BUILD_FILTER_CLONE_NAMESPACE_MASK,
            )
            emit(return_constant, 0, 0, V4_BUILD_FILTER_RET_ERRNO)
            emit(load_word_absolute, 0, 0, 0)
        else:
            emit(jump_equal, 0, 1, syscall_number)
            emit(return_constant, 0, 0, V4_BUILD_FILTER_RET_ERRNO)
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
                "mask": V4_BUILD_FILTER_CLONE_NAMESPACE_MASK,
                "value": None,
            })
        decoded_policy.append({
            "index": len(decoded_policy),
            "architecture": "linux-x86-64",
            "syscall_number": syscall_number,
            "argument_policy": argument_policy,
            "decision": "errno",
            "ret_data": V4_BUILD_FILTER_ERRNO,
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
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_v4_exact_json_types(item, f"{label}[{index}]")
        return
    if type(value) is dict:
        require(all(type(key) is str for key in value),
                f"malformed {label} key type")
        for key, item in value.items():
            _require_v4_exact_json_types(item, f"{label}.{key}")
        return
    raise ProtocolError(f"malformed {label} JSON type")


def validate_isolated_native_build_filter(value: object) -> dict[str, Any]:
    label = "V4 isolated native build filter"
    _require_v4_exact_json_types(value, label)
    require(type(value) is dict, f"malformed {label}")
    require_exact_json(
        value, enumerate_isolated_native_build_filter_v1(), label,
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
