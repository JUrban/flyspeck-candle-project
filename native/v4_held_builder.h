#ifndef CANDLE_V4_HELD_BUILDER_H
#define CANDLE_V4_HELD_BUILDER_H

#include "v4_output_root_walk.h"

#include <stdint.h>
#include <sys/types.h>

/*
 * This is a process-local lifecycle primitive, not an authority record.
 * start_ticks, namespace projections and ID maps are live kernel/procfs
 * observations retained and rejoined by this one long-lived native parent.
 * Counters and state are process-local logical values; it does not claim a
 * kernel descriptor/OFD generation.  Nothing in this header is a serialized
 * receipt or authority record.
 */

#define V4_HB_PTRACE_OPTION_COUNT 8U
#define V4_HB_FIXED_PTRACE_OPTIONS_MASK 0x0010007fUL
#define V4_HB_NAMESPACE_COUNT 5U
#define V4_HB_FIXED_CLONE_FLAGS 0x78020011UL

enum v4_hb_result {
    V4_HB_OK = 0,
    V4_HB_ERROR = 1,
    V4_HB_UNSUPPORTED = 77,
};

enum v4_hb_state {
    V4_HB_GATE_SPINNING = 1,
    V4_HB_INTERRUPT_HELD = 2,
    V4_HB_BOUND_ROOT_WALKS_COMPLETE = 3,
    V4_HB_RELEASED = 4,
    V4_HB_POISONED = 5,
    V4_HB_CLOSED = 6,
};

struct v4_hb_error {
    int saved_errno;
    char message[256];
};

struct v4_hb_namespace_projection {
    uint32_t index;
    unsigned long clone_flag;
    int descriptor;
    int descriptor_flags;
    int status_flags;
    uint64_t device;
    uint64_t inode;
    uint64_t link_count;
    uint32_t mode;
    long filesystem_type;
    int namespace_type;
};

struct v4_hb_id_map_projection {
    uint32_t inside_id;
    uint32_t outside_id;
    uint32_t length;
};

/*
 * The caller owns and must keep all four anchor descriptors live until the
 * builder reaches CLOSED.  Start takes a detached value snapshot; it neither
 * closes the caller's descriptors nor observes later config-struct changes.
 */
struct v4_hb_root_anchor_config {
    struct v4_orw_output_anchor input_root;
    struct v4_orw_output_anchor output_root;
    struct v4_orw_logical_ledger logical_ledger;
};

struct v4_hb_bound_root_walks {
    struct v4_orw_walk_result input_root;
    struct v4_orw_walk_result output_root;
};

struct v4_hb_snapshot {
    pid_t pid;
    uint64_t start_ticks;
    int pidfd;
    enum v4_hb_state state;
    uint32_t gate_value;
    int raw_interrupt_wait_status;
    uint32_t seize_count;
    uint32_t interrupt_count;
    uint32_t interrupt_event_stop_count;
    uint32_t resume_count;
    uint32_t held_stop_consumed;
    unsigned long clone_flags;
    uint32_t namespace_count;
    uint32_t observer_effective_uid;
    uint32_t observer_effective_gid;
    uint32_t observer_setgroups_denied;
    uint32_t root_inheritance_verified;
    uint32_t child_nspid;
    uint32_t uid_map_write_count;
    uint32_t setgroups_deny_write_count;
    uint32_t gid_map_write_count;
    uint32_t uid_map_write_order;
    uint32_t setgroups_deny_write_order;
    uint32_t gid_map_write_order;
    struct v4_hb_id_map_projection uid_map;
    struct v4_hb_id_map_projection gid_map;
    struct v4_hb_namespace_projection parent_namespaces[
        V4_HB_NAMESPACE_COUNT
    ];
    struct v4_hb_namespace_projection child_namespaces[
        V4_HB_NAMESPACE_COUNT
    ];
    struct v4_orw_output_anchor input_root;
    struct v4_orw_output_anchor output_root;
};

struct v4_hb_completion {
    int raw_exit_event_wait_status;
    unsigned long exit_event_message;
    int raw_final_wait_status;
    int exit_code;
};

struct v4_hb_builder;

void v4_hb_error_clear(struct v4_hb_error *error);

int v4_hb_builder_start(
    const struct v4_hb_root_anchor_config *config,
    struct v4_hb_builder **builder,
    struct v4_hb_error *error
);

int v4_hb_builder_snapshot(
    const struct v4_hb_builder *builder,
    struct v4_hb_snapshot *snapshot,
    struct v4_hb_error *error
);

int v4_hb_builder_seize_interrupt(
    struct v4_hb_builder *builder,
    struct v4_hb_snapshot *held_snapshot,
    struct v4_hb_error *error
);

int v4_hb_builder_verify_held(
    const struct v4_hb_builder *builder,
    const struct v4_hb_snapshot *expected,
    struct v4_hb_error *error
);

int v4_hb_builder_run_bound_root_walks(
    struct v4_hb_builder *builder,
    struct v4_hb_bound_root_walks *walks,
    struct v4_hb_error *error
);

void v4_hb_bound_root_walks_destroy(
    struct v4_hb_bound_root_walks *walks
);

int v4_hb_builder_release_and_reap(
    struct v4_hb_builder *builder,
    struct v4_hb_completion *completion,
    struct v4_hb_error *error
);

int v4_hb_builder_abort(
    struct v4_hb_builder *builder,
    struct v4_hb_error *error
);

void v4_hb_builder_destroy(struct v4_hb_builder *builder);

#endif
