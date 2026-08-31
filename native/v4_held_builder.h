#ifndef CANDLE_V4_HELD_BUILDER_H
#define CANDLE_V4_HELD_BUILDER_H

#include "v4_output_root_walk.h"

#include <stdint.h>
#include <sys/types.h>

/*
 * This is a process-local lifecycle primitive, not an authority record.
 * start_ticks is observed from procfs.  The counters and state are logical
 * values owned by this one long-lived native parent.
 */

#define V4_HB_PTRACE_OPTION_COUNT 8U
#define V4_HB_FIXED_PTRACE_OPTIONS_MASK 0x0010007fUL

enum v4_hb_result {
    V4_HB_OK = 0,
    V4_HB_ERROR = 1,
    V4_HB_UNSUPPORTED = 77,
};

enum v4_hb_state {
    V4_HB_GATE_SPINNING = 1,
    V4_HB_INTERRUPT_HELD = 2,
    V4_HB_EMPTY_PREWALK_COMPLETE = 3,
    V4_HB_RELEASED = 4,
    V4_HB_POISONED = 5,
    V4_HB_CLOSED = 6,
};

struct v4_hb_error {
    int saved_errno;
    char message[256];
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

int v4_hb_builder_run_empty_prewalk(
    struct v4_hb_builder *builder,
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_walk_result *walk,
    struct v4_hb_error *error
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
