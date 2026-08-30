#ifndef CANDLE_V4_OUTPUT_ROOT_WALK_H
#define CANDLE_V4_OUTPUT_ROOT_WALK_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

/*
 * This primitive records userspace logical generations.  Linux does not
 * expose numeric open-file-description, descriptor-generation, namespace-
 * generation, or inode-generation IDs.  None of the fields named "logical"
 * below claims to be such a kernel ID.
 */

#define V4_ORW_MAX_ENTRIES 196608U
#define V4_ORW_MAX_RELATIVE_BYTES 4096U
#define V4_ORW_MAX_COMPONENT_BYTES 255U
#define V4_ORW_MAX_TOTAL_PATH_BYTES 33554432U

enum v4_orw_result {
    V4_ORW_OK = 0,
    V4_ORW_ERROR = 1,
    V4_ORW_UNSUPPORTED = 77,
};

enum v4_orw_object_type {
    V4_ORW_DIRECTORY = 1,
    V4_ORW_REGULAR_FILE = 2,
};

struct v4_orw_error {
    int saved_errno;
    char message[256];
};

struct v4_orw_logical_ledger {
    uint64_t next_fd_generation;
    uint64_t next_ofd_id;
    uint64_t next_ofd_generation;
};

struct v4_orw_logical_descriptor {
    int fd;
    uint64_t fd_generation;
    uint64_t logical_ofd_id;
    uint64_t logical_ofd_generation;
};

struct v4_orw_fdinfo_projection {
    uint64_t position;
    uint64_t flags;
    uint64_t mount_id;
    uint64_t inode;
};

struct v4_orw_kernel_projection {
    uint64_t st_dev;
    uint64_t st_ino;
    uint64_t st_nlink;
    uint64_t st_mode;
    int64_t st_size;
    int64_t mtime_seconds;
    uint64_t mtime_nanoseconds;
    int64_t ctime_seconds;
    uint64_t ctime_nanoseconds;
    uint32_t statx_dev_major;
    uint32_t statx_dev_minor;
    uint64_t mount_id;
    uint32_t fd_flags;
    uint64_t status_flags;
    struct v4_orw_fdinfo_projection fdinfo;
};

struct v4_orw_output_anchor {
    struct v4_orw_logical_descriptor primary;
    struct v4_orw_logical_descriptor guard;
    struct v4_orw_kernel_projection initial_projection;
    struct v4_orw_kernel_projection guard_initial_projection;
    int live;
};

struct v4_orw_walk_entry {
    char *relative;
    enum v4_orw_object_type object_type;
    /* Historical ledger row: this descriptor is closed before return. */
    struct v4_orw_logical_descriptor descriptor;
    struct v4_orw_kernel_projection projection;
};

struct v4_orw_walk_result {
    /* Historical ledger row: this descriptor is closed before return. */
    struct v4_orw_logical_descriptor root_walk_descriptor;
    struct v4_orw_kernel_projection root_walk_projection;
    size_t opened_descriptor_count;
    size_t entry_count;
    size_t entry_capacity;
    size_t total_relative_bytes;
    size_t directory_eof_count;
    struct v4_orw_walk_entry *entries;
};

void v4_orw_error_clear(struct v4_orw_error *error);

int v4_orw_logical_ledger_init(
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_error *error
);

int v4_orw_output_anchor_open(
    int parent_fd,
    const char *relative,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_output_anchor *anchor,
    struct v4_orw_error *error
);

int v4_orw_output_anchor_snapshot(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_kernel_projection *projection,
    struct v4_orw_error *error
);

int v4_orw_output_anchor_revalidate(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_error *error
);

int v4_orw_output_root_walk(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_walk_result *result,
    struct v4_orw_error *error
);

void v4_orw_walk_result_destroy(struct v4_orw_walk_result *result);

void v4_orw_output_anchor_close(
    struct v4_orw_output_anchor *anchor
);

#endif
