#define _GNU_SOURCE

#include "v4_held_builder.h"

#include <errno.h>
#include <fcntl.h>
#ifdef V4_HB_TEST_PROC_NLINK_CHURN
#include <linux/magic.h>
#endif
#include <sched.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#ifdef V4_HB_TEST_PROC_NLINK_CHURN
#include <sys/statfs.h>
#endif
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#ifdef V4_HB_TEST_PROC_NLINK_CHURN
static unsigned int test_proc_root_observation_count;

int __real_fstat(int descriptor, struct stat *status);

int
__wrap_fstat(int descriptor, struct stat *status)
{
    struct statfs filesystem;
    int result = __real_fstat(descriptor, status);

    if (result == 0 && S_ISDIR(status->st_mode) && status->st_ino == 1 &&
        fstatfs(descriptor, &filesystem) == 0 &&
        (unsigned long)filesystem.f_type == (unsigned long)PROC_SUPER_MAGIC) {
        status->st_nlink +=
            (nlink_t)(++test_proc_root_observation_count & 1U);
    }
    return result;
}
#endif

static const unsigned long expected_namespace_flags[V4_HB_NAMESPACE_COUNT] = {
    CLONE_NEWUSER,
    CLONE_NEWNS,
    CLONE_NEWPID,
    CLONE_NEWNET,
    CLONE_NEWIPC,
};

static bool
root_anchor_snapshot_is_exact(
    const struct v4_orw_output_anchor *actual,
    const struct v4_orw_output_anchor *expected
)
{
    return actual->live == 1 && expected->live == 1 &&
        actual->primary.fd == expected->primary.fd &&
        actual->primary.fd_generation == expected->primary.fd_generation &&
        actual->primary.logical_ofd_id == expected->primary.logical_ofd_id &&
        actual->primary.logical_ofd_generation ==
            expected->primary.logical_ofd_generation &&
        actual->guard.fd == expected->guard.fd &&
        actual->guard.fd_generation == expected->guard.fd_generation &&
        actual->guard.logical_ofd_id == expected->guard.logical_ofd_id &&
        actual->guard.logical_ofd_generation ==
            expected->guard.logical_ofd_generation &&
        actual->initial_projection.st_dev ==
            expected->initial_projection.st_dev &&
        actual->initial_projection.st_ino ==
            expected->initial_projection.st_ino &&
        actual->initial_projection.mount_id ==
            expected->initial_projection.mount_id &&
        actual->initial_projection.fd_flags == FD_CLOEXEC &&
        actual->initial_projection.status_flags ==
            (uint64_t)(O_PATH | O_DIRECTORY | O_NOFOLLOW) &&
        actual->initial_projection.fdinfo.flags ==
            (uint64_t)(O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC) &&
        actual->guard_initial_projection.st_dev ==
            expected->guard_initial_projection.st_dev &&
        actual->guard_initial_projection.st_ino ==
            expected->guard_initial_projection.st_ino &&
        actual->guard_initial_projection.mount_id ==
            expected->guard_initial_projection.mount_id &&
        actual->guard_initial_projection.fd_flags == FD_CLOEXEC &&
        actual->guard_initial_projection.status_flags ==
            (uint64_t)(O_PATH | O_DIRECTORY | O_NOFOLLOW) &&
        actual->guard_initial_projection.fdinfo.flags ==
            (uint64_t)(O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
}

static bool
root_binding_snapshot_is_exact(
    const struct v4_hb_snapshot *snapshot,
    const struct v4_hb_root_anchor_config *config,
    uint32_t inheritance_verified
)
{
    const int fds[4] = {
        snapshot->input_root.primary.fd,
        snapshot->input_root.guard.fd,
        snapshot->output_root.primary.fd,
        snapshot->output_root.guard.fd,
    };
    uint32_t first;
    uint32_t second;

    if (snapshot->root_inheritance_verified != inheritance_verified ||
        !root_anchor_snapshot_is_exact(
            &snapshot->input_root, &config->input_root
        ) || !root_anchor_snapshot_is_exact(
            &snapshot->output_root, &config->output_root
        ) ||
        snapshot->input_root.initial_projection.mount_id ==
            snapshot->output_root.initial_projection.mount_id ||
        (snapshot->input_root.initial_projection.st_mode &
             (S_IFMT | 07777U)) != (S_IFDIR | 0555U) ||
        (snapshot->output_root.initial_projection.st_mode &
             (S_IFMT | 07777U)) != (S_IFDIR | 0700U) ||
        (snapshot->input_root.initial_projection.st_dev ==
             snapshot->output_root.initial_projection.st_dev &&
         snapshot->input_root.initial_projection.st_ino ==
             snapshot->output_root.initial_projection.st_ino)) {
        return false;
    }
    for (first = 0; first < 4U; ++first) {
        uint32_t namespace_index;

        if (fds[first] == snapshot->pidfd) {
            return false;
        }
        for (namespace_index = 0;
             namespace_index < V4_HB_NAMESPACE_COUNT;
             ++namespace_index) {
            if (fds[first] ==
                    snapshot->parent_namespaces[namespace_index].descriptor ||
                fds[first] ==
                    snapshot->child_namespaces[namespace_index].descriptor) {
                return false;
            }
        }
        for (second = first + 1U; second < 4U; ++second) {
            if (fds[first] == fds[second]) {
                return false;
            }
        }
    }
    return true;
}

static int
test_fail(const char *message)
{
    (void)fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int
test_v4_oracle_error(struct v4_hb_error *error, const char *message)
{
    error->saved_errno = EINVAL;
    (void)snprintf(error->message, sizeof(error->message), "%s", message);
    return V4_HB_ERROR;
}

static int
test_v4_diagnostic_failure(
    const char *context,
    const char *phase,
    int code,
    struct v4_hb_builder *builder,
    const struct v4_hb_error *error
)
{
    struct v4_hb_snapshot snapshot;
    struct v4_hb_error snapshot_error;
    int snapshot_code = V4_HB_ERROR;

    memset(&snapshot, 0, sizeof(snapshot));
    memset(&snapshot_error, 0, sizeof(snapshot_error));
    if (builder != NULL) {
        snapshot_code = v4_hb_builder_snapshot(
            builder, &snapshot, &snapshot_error
        );
    }
    (void)fprintf(
        stderr, "FAIL: %s: phase=%s code=%d errno=%d message=%s "
        "snapshot_code=%d state=%d poisoned=%u snapshot_errno=%d "
        "snapshot_message=%s\n",
        context, phase != NULL ? phase : "unspecified",
        code, error->saved_errno, error->message,
        snapshot_code, snapshot_code == V4_HB_OK ? (int)snapshot.state : -1,
        snapshot_code == V4_HB_OK && snapshot.state == V4_HB_POISONED ? 1U : 0U,
        snapshot_error.saved_errno, snapshot_error.message
    );
    return 1;
}

static int
test_skip(const char *message)
{
    (void)fprintf(stdout, "SKIP: %s\n", message);
    return V4_HB_UNSUPPORTED;
}

static int
write_text_file(const char *path, const char *text)
{
    size_t length = strlen(text);
    size_t offset = 0;
    int fd = open(path, O_WRONLY | O_CLOEXEC);

    if (fd < 0) {
        return -1;
    }
    while (offset < length) {
        ssize_t count = write(fd, text + offset, length - offset);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count <= 0) {
            (void)close(fd);
            return -1;
        }
        offset += (size_t)count;
    }
    return close(fd);
}

static int
write_file_at(int directory_fd, const char *relative, const char *text)
{
    size_t length = strlen(text);
    size_t offset = 0;
    int descriptor = openat(
        directory_fd, relative,
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600
    );

    if (descriptor < 0) {
        return -1;
    }
    while (offset < length) {
        ssize_t count = write(descriptor, text + offset, length - offset);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count <= 0) {
            (void)close(descriptor);
            return -1;
        }
        offset += (size_t)count;
    }
    return close(descriptor);
}

static int
enter_private_mount_namespace(void)
{
    char mapping[128];
    uid_t outer_uid = getuid();
    gid_t outer_gid = getgid();

    if (unshare(CLONE_NEWUSER | CLONE_NEWNS) != 0) {
        return -1;
    }
    if (write_text_file("/proc/self/setgroups", "deny\n") != 0) {
        return -1;
    }
    if (snprintf(mapping, sizeof(mapping), "0 %lu 1\n",
                 (unsigned long)outer_uid) < 0 ||
        write_text_file("/proc/self/uid_map", mapping) != 0) {
        return -1;
    }
    if (snprintf(mapping, sizeof(mapping), "0 %lu 1\n",
                 (unsigned long)outer_gid) < 0 ||
        write_text_file("/proc/self/gid_map", mapping) != 0) {
        return -1;
    }
    if (setresgid(0, 0, 0) != 0 || setresuid(0, 0, 0) != 0 ||
        mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) != 0) {
        return -1;
    }
    return 0;
}

static bool
initial_namespace_capture_is_exact(const struct v4_hb_snapshot *snapshot)
{
    uint32_t index;

    if (snapshot->clone_flags != V4_HB_FIXED_CLONE_FLAGS ||
        snapshot->namespace_count != V4_HB_NAMESPACE_COUNT ||
        snapshot->observer_effective_uid != (uint32_t)geteuid() ||
        snapshot->observer_effective_gid != (uint32_t)getegid() ||
        snapshot->observer_setgroups_denied > 1U ||
        snapshot->child_nspid != 0U ||
        snapshot->uid_map_write_count != 0U ||
        snapshot->setgroups_deny_write_count != 0U ||
        snapshot->gid_map_write_count != 0U ||
        snapshot->uid_map_write_order != 0U ||
        snapshot->setgroups_deny_write_order != 0U ||
        snapshot->gid_map_write_order != 0U) {
        return false;
    }
    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        const struct v4_hb_namespace_projection *parent =
            &snapshot->parent_namespaces[index];
        const struct v4_hb_namespace_projection *child =
            &snapshot->child_namespaces[index];

        if (parent->index != index ||
            parent->clone_flag != expected_namespace_flags[index] ||
            parent->descriptor < 0 ||
            parent->descriptor_flags != FD_CLOEXEC ||
            (parent->status_flags & O_ACCMODE) != O_RDONLY ||
            parent->device == 0U || parent->inode == 0U ||
            parent->link_count != 1U ||
            (parent->mode & S_IFMT) != S_IFREG ||
            (parent->mode & 07777U) != 0444U ||
            parent->namespace_type != (int)expected_namespace_flags[index] ||
            child->descriptor != -1) {
            return false;
        }
    }
    return true;
}

static bool
namespace_boundary_is_exact(const struct v4_hb_snapshot *snapshot)
{
    uint32_t first;

    if (snapshot->clone_flags != V4_HB_FIXED_CLONE_FLAGS ||
        snapshot->namespace_count != V4_HB_NAMESPACE_COUNT ||
        snapshot->observer_effective_uid != (uint32_t)geteuid() ||
        snapshot->observer_effective_gid != (uint32_t)getegid() ||
        snapshot->observer_setgroups_denied > 1U ||
        snapshot->child_nspid != 1U ||
        snapshot->uid_map_write_count != 1U ||
        snapshot->setgroups_deny_write_count != 1U ||
        snapshot->gid_map_write_count != 1U ||
        snapshot->uid_map_write_order != 1U ||
        snapshot->setgroups_deny_write_order != 2U ||
        snapshot->gid_map_write_order != 3U ||
        snapshot->uid_map.inside_id != 0U ||
        snapshot->uid_map.outside_id != (uint32_t)geteuid() ||
        snapshot->uid_map.length != 1U ||
        snapshot->gid_map.inside_id != 0U ||
        snapshot->gid_map.outside_id != (uint32_t)getegid() ||
        snapshot->gid_map.length != 1U) {
        return false;
    }
    for (first = 0; first < V4_HB_NAMESPACE_COUNT; ++first) {
        const struct v4_hb_namespace_projection *parent =
            &snapshot->parent_namespaces[first];
        const struct v4_hb_namespace_projection *child =
            &snapshot->child_namespaces[first];
        uint32_t second;

        if (parent->index != first || child->index != first ||
            parent->clone_flag != expected_namespace_flags[first] ||
            child->clone_flag != expected_namespace_flags[first] ||
            parent->descriptor < 0 || child->descriptor < 0 ||
            parent->descriptor == child->descriptor ||
            parent->descriptor_flags != FD_CLOEXEC ||
            child->descriptor_flags != FD_CLOEXEC ||
            (parent->status_flags & O_ACCMODE) != O_RDONLY ||
            (child->status_flags & O_ACCMODE) != O_RDONLY ||
            parent->device == 0U || parent->inode == 0U ||
            child->device == 0U || child->inode == 0U ||
            parent->link_count != 1U || child->link_count != 1U ||
            (parent->mode & S_IFMT) != S_IFREG ||
            (child->mode & S_IFMT) != S_IFREG ||
            (parent->mode & 07777U) != 0444U ||
            (child->mode & 07777U) != 0444U ||
            parent->filesystem_type != child->filesystem_type ||
            parent->namespace_type != (int)expected_namespace_flags[first] ||
            child->namespace_type != (int)expected_namespace_flags[first] ||
            (parent->device == child->device &&
             parent->inode == child->inode)) {
            return false;
        }
        for (second = 0; second < V4_HB_NAMESPACE_COUNT; ++second) {
            if (first != second &&
                (parent->descriptor ==
                     snapshot->parent_namespaces[second].descriptor ||
                 child->descriptor ==
                     snapshot->child_namespaces[second].descriptor ||
                 parent->descriptor ==
                     snapshot->child_namespaces[second].descriptor ||
                 child->descriptor ==
                     snapshot->parent_namespaces[second].descriptor)) {
                return false;
            }
        }
    }
    return true;
}

static bool
initial_snapshot_is_exact(
    const struct v4_hb_snapshot *snapshot,
    const struct v4_hb_root_anchor_config *config
)
{
    return snapshot->pid > 0 && snapshot->start_ticks > 0 &&
        snapshot->pidfd >= 0 && snapshot->state == V4_HB_GATE_SPINNING &&
        snapshot->gate_value == 0 && snapshot->raw_interrupt_wait_status == 0 &&
        snapshot->seize_count == 0 && snapshot->interrupt_count == 0 &&
        snapshot->interrupt_event_stop_count == 0 &&
        snapshot->resume_count == 0 && snapshot->held_stop_consumed == 0 &&
        initial_namespace_capture_is_exact(snapshot) &&
        root_binding_snapshot_is_exact(snapshot, config, 0U);
}

static bool
held_snapshot_is_exact(
    const struct v4_hb_snapshot *snapshot,
    const struct v4_hb_root_anchor_config *config
)
{
    return snapshot->state == V4_HB_INTERRUPT_HELD &&
        snapshot->gate_value == 0 && snapshot->seize_count == 1 &&
        snapshot->interrupt_count == 1 &&
        snapshot->interrupt_event_stop_count == 1 &&
        snapshot->resume_count == 0 && snapshot->held_stop_consumed == 1 &&
        WIFSTOPPED(snapshot->raw_interrupt_wait_status) &&
        WSTOPSIG(snapshot->raw_interrupt_wait_status) == SIGTRAP &&
        (unsigned int)snapshot->raw_interrupt_wait_status >> 16 ==
            PTRACE_EVENT_STOP && namespace_boundary_is_exact(snapshot) &&
        root_binding_snapshot_is_exact(snapshot, config, 1U);
}

static int
expect_snapshot_splices_reject(
    struct v4_hb_builder *builder,
    const struct v4_hb_snapshot *held,
    struct v4_hb_error *error
)
{
    struct v4_hb_snapshot splice;
    int verify_code;

#define V4_HB_EXPECT_HELD_SPLICE_REJECT(statement) \
    do { \
        splice = *held; \
        statement; \
        verify_code = v4_hb_builder_verify_held(builder, &splice, error); \
        if (verify_code != V4_HB_ERROR) { \
            if (verify_code != V4_HB_OK) { \
                return verify_code; \
            } \
            return test_v4_oracle_error( \
                error, "held snapshot hostile splice was accepted" \
            ); \
        } \
    } while (0)

    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.pid);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.start_ticks);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(
        splice.raw_interrupt_wait_status ^= 1 << 16
    );
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.pidfd);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(splice.clone_flags ^= CLONE_NEWUTS);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(--splice.namespace_count);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.observer_effective_uid);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(
        splice.observer_setgroups_denied ^= 1U
    );
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.child_nspid);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.uid_map.outside_id);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.setgroups_deny_write_order);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(++splice.child_namespaces[0].inode);
    V4_HB_EXPECT_HELD_SPLICE_REJECT(
        ++splice.parent_namespaces[1].descriptor
    );
    V4_HB_EXPECT_HELD_SPLICE_REJECT(
        ++splice.input_root.primary.fd_generation
    );
    V4_HB_EXPECT_HELD_SPLICE_REJECT(
        ++splice.output_root.initial_projection.st_ino
    );
    V4_HB_EXPECT_HELD_SPLICE_REJECT(
        do { \
            struct v4_orw_output_anchor swapped = splice.input_root; \
            splice.input_root = splice.output_root; \
            splice.output_root = swapped; \
        } while (0)
    );
#undef V4_HB_EXPECT_HELD_SPLICE_REJECT
    return v4_hb_builder_verify_held(builder, held, error);
}

static int
expect_root_config_splices_reject(
    const struct v4_hb_root_anchor_config *config,
    struct v4_hb_error *error
)
{
    struct v4_hb_root_anchor_config splice;
    struct v4_hb_builder *unexpected = NULL;

#define V4_HB_EXPECT_CONFIG_REJECT() \
    do { \
        if (v4_hb_builder_start(&splice, &unexpected, error) != \
                V4_HB_ERROR || unexpected != NULL) { \
            if (unexpected != NULL) { \
                (void)v4_hb_builder_abort(unexpected, error); \
                v4_hb_builder_destroy(unexpected); \
            } \
            return -1; \
        } \
    } while (0)

    splice = *config;
    splice.output_root = splice.input_root;
    V4_HB_EXPECT_CONFIG_REJECT();
    splice = *config;
    splice.input_root.guard.fd_generation =
        splice.input_root.primary.fd_generation;
    V4_HB_EXPECT_CONFIG_REJECT();
    splice = *config;
    splice.input_root.initial_projection.status_flags ^= O_NONBLOCK;
    V4_HB_EXPECT_CONFIG_REJECT();
    splice = *config;
    splice.logical_ledger.next_fd_generation =
        splice.output_root.guard.fd_generation;
    V4_HB_EXPECT_CONFIG_REJECT();
#undef V4_HB_EXPECT_CONFIG_REJECT
    return 0;
}

static int
hold_and_prewalk(
    struct v4_hb_builder *builder,
    const struct v4_hb_root_anchor_config *config,
    struct v4_hb_snapshot *held,
    const char **failure_phase,
    struct v4_hb_error *error
)
{
    struct v4_hb_bound_root_walks walks;
    struct v4_hb_completion forbidden_completion;
    int code;

    *failure_phase = "held seize/interrupt";
    code = v4_hb_builder_seize_interrupt(builder, held, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = "held snapshot oracle";
    if (!held_snapshot_is_exact(held, config)) {
        return test_v4_oracle_error(error, "held snapshot oracle mismatch");
    }
    *failure_phase = "forbidden second seize/interrupt";
    code = v4_hb_builder_seize_interrupt(builder, held, error);
    if (code != V4_HB_ERROR) {
        if (code != V4_HB_OK) {
            return code;
        }
        return test_v4_oracle_error(
            error, "second held seize/interrupt was accepted"
        );
    }
    *failure_phase = "held snapshot splice hostility";
    code = expect_snapshot_splices_reject(builder, held, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = "forbidden early release/reap";
    code = v4_hb_builder_release_and_reap(
        builder, &forbidden_completion, error
    );
    if (code != V4_HB_ERROR) {
        if (code != V4_HB_OK) {
            return code;
        }
        return test_v4_oracle_error(
            error, "early held release/reap was accepted"
        );
    }
    *failure_phase = "held bound-root walks";
    code = v4_hb_builder_run_bound_root_walks(builder, &walks, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = "bound-root walk oracle";
    if (walks.input_root.entry_count != 4U ||
        walks.input_root.opened_descriptor_count != 7U ||
        walks.input_root.directory_eof_count != 2U ||
        walks.input_root.declared_mount_edge_count != 1U ||
        walks.input_root.total_relative_bytes != 37U ||
        walks.input_root.root_walk_descriptor.fd_generation == 0U ||
        walks.input_root.root_walk_descriptor.logical_ofd_id == 0U ||
        strcmp(walks.input_root.entries[0].relative, "alpha.txt") != 0 ||
        walks.input_root.entries[0].object_type != V4_ORW_REGULAR_FILE ||
        (walks.input_root.entries[0].projection.st_mode &
             (S_IFMT | 07777U)) != (S_IFREG | 0444U) ||
        strcmp(walks.input_root.entries[1].relative,
               V4_ORW_DECLARED_OUTPUT_EDGE) != 0 ||
        walks.input_root.entries[1].object_type != V4_ORW_DIRECTORY ||
        (walks.input_root.entries[1].projection.st_mode &
             (S_IFMT | 07777U)) != (S_IFDIR | 0700U) ||
        walks.input_root.entries[1].is_declared_mount_edge != 1 ||
        walks.input_root.entries[1].has_directory_walk_descriptor != 0 ||
        walks.input_root.entries[1].projection.mount_id !=
            config->output_root.initial_projection.mount_id ||
        walks.input_root.entries[1].projection.st_dev !=
            config->output_root.initial_projection.st_dev ||
        walks.input_root.entries[1].projection.st_ino !=
            config->output_root.initial_projection.st_ino ||
        walks.input_root.entries[1].declared_anchor_alias_descriptor.
                logical_ofd_id !=
            config->output_root.primary.logical_ofd_id ||
        walks.input_root.entries[1].declared_anchor_alias_descriptor.
                logical_ofd_generation !=
            config->output_root.primary.logical_ofd_generation ||
        walks.input_root.entries[1].declared_anchor_alias_projection.
                mount_id !=
            config->output_root.initial_projection.mount_id ||
        strcmp(walks.input_root.entries[2].relative, "sub") != 0 ||
        walks.input_root.entries[2].object_type != V4_ORW_DIRECTORY ||
        (walks.input_root.entries[2].projection.st_mode &
             (S_IFMT | 07777U)) != (S_IFDIR | 0555U) ||
        strcmp(walks.input_root.entries[3].relative, "sub/beta.txt") != 0 ||
        walks.input_root.entries[3].object_type != V4_ORW_REGULAR_FILE ||
        (walks.input_root.entries[3].projection.st_mode &
             (S_IFMT | 07777U)) != (S_IFREG | 0444U) ||
        walks.output_root.entry_count != 0 ||
        walks.output_root.declared_mount_edge_count != 0U ||
        walks.output_root.directory_eof_count != 1 ||
        walks.output_root.opened_descriptor_count != 1 ||
        walks.output_root.root_walk_descriptor.fd_generation <=
            walks.input_root.entries[3].descriptor.fd_generation ||
        walks.output_root.root_walk_descriptor.logical_ofd_id == 0U) {
        v4_hb_bound_root_walks_destroy(&walks);
        return test_v4_oracle_error(error, "bound-root walk oracle mismatch");
    }
    v4_hb_bound_root_walks_destroy(&walks);
    *failure_phase = NULL;
    return V4_HB_OK;
}

static bool
setup_prefix_is_exact(
    const struct v4_hb_setup_prefix_observation *setup,
    const struct v4_hb_root_anchor_config *config
)
{
    static const int64_t numbers[V4_HB_SETUP_PREFIX_OPERATION_COUNT] = {
        SYS_mount, SYS_fchdir, SYS_chroot, SYS_chdir,
        SYS_setresgid, SYS_setresuid, SYS_rt_sigprocmask
    };
    static const uint8_t empty_signal_mask[V4_HB_KERNEL_SIGSET_BYTES] = {0};
    uint32_t index;

    if (setup->operation_count != V4_HB_SETUP_PREFIX_OPERATION_COUNT ||
        setup->stop_count != V4_HB_SETUP_PREFIX_STOP_COUNT ||
        setup->ptrace_syscall_resume_count !=
            V4_HB_SETUP_PREFIX_STOP_COUNT ||
        setup->input_root_fd != config->input_root.primary.fd ||
        setup->input_root_fd_generation !=
            config->input_root.primary.fd_generation ||
        setup->input_root_logical_ofd_id !=
            config->input_root.primary.logical_ofd_id ||
        setup->input_root_logical_ofd_generation !=
            config->input_root.primary.logical_ofd_generation ||
        setup->recursive_private_syscall_observed != 1U ||
        setup->private_mountinfo_observed != 1U ||
        setup->mountinfo_byte_count == 0U ||
        setup->mountinfo_row_count == 0U ||
        setup->credential_status_byte_count == 0U ||
        setup->credential_status_row_count != 2U ||
        setup->observer_credential_ids.real_uid != (uint32_t)geteuid() ||
        setup->observer_credential_ids.effective_uid != (uint32_t)geteuid() ||
        setup->observer_credential_ids.saved_uid != (uint32_t)geteuid() ||
        setup->observer_credential_ids.filesystem_uid != (uint32_t)geteuid() ||
        setup->observer_credential_ids.real_gid != (uint32_t)getegid() ||
        setup->observer_credential_ids.effective_gid != (uint32_t)getegid() ||
        setup->observer_credential_ids.saved_gid != (uint32_t)getegid() ||
        setup->observer_credential_ids.filesystem_gid != (uint32_t)getegid() ||
        setup->inner_credential_ids.real_uid != 0U ||
        setup->inner_credential_ids.effective_uid != 0U ||
        setup->inner_credential_ids.saved_uid != 0U ||
        setup->inner_credential_ids.filesystem_uid != 0U ||
        setup->inner_credential_ids.real_gid != 0U ||
        setup->inner_credential_ids.effective_gid != 0U ||
        setup->inner_credential_ids.saved_gid != 0U ||
        setup->inner_credential_ids.filesystem_gid != 0U ||
        setup->live_signal_mask_observed != 1U ||
        setup->live_signal_mask_byte_count != V4_HB_KERNEL_SIGSET_BYTES ||
        memcmp(setup->live_signal_mask_bytes, empty_signal_mask,
               sizeof(empty_signal_mask)) != 0 ||
        setup->root_projection.device !=
            config->input_root.initial_projection.st_dev ||
        setup->root_projection.inode !=
            config->input_root.initial_projection.st_ino ||
        setup->root_projection.mount_id !=
            config->input_root.initial_projection.mount_id ||
        setup->root_projection.mode !=
            config->input_root.initial_projection.st_mode ||
        setup->cwd_projection.device != setup->root_projection.device ||
        setup->cwd_projection.inode != setup->root_projection.inode ||
        setup->cwd_projection.mount_id != setup->root_projection.mount_id ||
        setup->cwd_projection.mode != setup->root_projection.mode) {
        return false;
    }
    for (index = 0U; index < V4_HB_SETUP_PREFIX_OPERATION_COUNT; ++index) {
        const struct v4_hb_setup_syscall_observation *operation =
            &setup->operations[index];
        uint32_t argument_index;
        uint32_t path_count =
            (index == 0U || index == 2U || index == 3U) ?
                V4_HB_SETUP_PATH_CAP : 0U;
        uint32_t payload_count = index == 6U ?
            V4_HB_KERNEL_SIGSET_BYTES : 0U;
        uint8_t path = index == 2U ? '.' : '/';

        if (operation->operation_index != index ||
            operation->operation !=
                (enum v4_hb_setup_operation)(index + 1U) ||
            operation->syscall_number != numbers[index] ||
            operation->path_byte_count != path_count ||
            (path_count != 0U &&
             (operation->path_bytes[0] != path ||
              operation->path_bytes[1] != '\0')) ||
            (path_count == 0U &&
             (operation->path_bytes[0] != 0U ||
              operation->path_bytes[1] != 0U)) ||
            operation->payload_byte_count != payload_count ||
            memcmp(operation->payload_bytes, empty_signal_mask,
                   sizeof(empty_signal_mask)) != 0 ||
            operation->entry_stop_index != index * 2U ||
            operation->exit_stop_index != index * 2U + 1U ||
            !WIFSTOPPED(operation->raw_entry_wait_status) ||
            WSTOPSIG(operation->raw_entry_wait_status) !=
                (SIGTRAP | 0x80) ||
            !WIFSTOPPED(operation->raw_exit_wait_status) ||
            WSTOPSIG(operation->raw_exit_wait_status) !=
                (SIGTRAP | 0x80) ||
            operation->entry_instruction_pointer == 0U ||
            operation->entry_stack_pointer == 0U ||
            operation->exit_instruction_pointer == 0U ||
            operation->exit_stack_pointer == 0U ||
            operation->return_value != 0 ||
            operation->return_is_error != 0U) {
            return false;
        }
        if (index == 0U) {
            if (operation->arguments[0] != 0U ||
                operation->arguments[1] == 0U ||
                operation->arguments[2] != 0U ||
                operation->arguments[3] != V4_HB_SETUP_MOUNT_FLAGS ||
                operation->arguments[4] != 0U ||
                operation->arguments[5] != 0U) {
                return false;
            }
        } else if (index == 1U) {
            if (operation->arguments[0] !=
                    (uint64_t)config->input_root.primary.fd) {
                return false;
            }
            for (argument_index = 1U; argument_index < 6U;
                 ++argument_index) {
                if (operation->arguments[argument_index] != 0U) {
                    return false;
                }
            }
        } else if (index == 2U || index == 3U) {
            if (operation->arguments[0] == 0U) {
                return false;
            }
            for (argument_index = 1U; argument_index < 6U;
                 ++argument_index) {
                if (operation->arguments[argument_index] != 0U) {
                    return false;
                }
            }
        } else if (index == 4U || index == 5U) {
            for (argument_index = 0U; argument_index < 6U;
                 ++argument_index) {
                if (operation->arguments[argument_index] != 0U) {
                    return false;
                }
            }
        } else if (operation->arguments[0] != SIG_SETMASK ||
                   operation->arguments[1] == 0U ||
                   operation->arguments[2] != 0U ||
                   operation->arguments[3] != V4_HB_KERNEL_SIGSET_BYTES ||
                   operation->arguments[4] != 0U ||
                   operation->arguments[5] != 0U) {
            return false;
        }
    }
    return true;
}

static int
expect_setup_prefix_splices_reject(
    struct v4_hb_builder *builder,
    const struct v4_hb_setup_prefix_observation *setup,
    struct v4_hb_error *error
)
{
    struct v4_hb_setup_prefix_observation splice;
    int verify_code;

#define V4_HB_EXPECT_SETUP_SPLICE_REJECT(statement) \
    do { \
        splice = *setup; \
        statement; \
        verify_code = v4_hb_builder_verify_setup_prefix( \
            builder, &splice, error \
        ); \
        if (verify_code != V4_HB_ERROR) { \
            if (verify_code != V4_HB_OK) { \
                return verify_code; \
            } \
            return test_v4_oracle_error( \
                error, "setup-prefix hostile splice was accepted" \
            ); \
        } \
    } while (0)

    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operation_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.stop_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.ptrace_syscall_resume_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.input_root_fd);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.input_root_fd_generation);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        ++splice.input_root_logical_ofd_generation
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.recursive_private_syscall_observed = 0U
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.private_mountinfo_observed = 0U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.mountinfo_byte_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.mountinfo_row_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.credential_status_byte_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.credential_status_row_count);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        ++splice.observer_credential_ids.saved_uid
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        ++splice.inner_credential_ids.filesystem_gid
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.live_signal_mask_observed = 0U
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        --splice.live_signal_mask_byte_count
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.live_signal_mask_bytes[0] = 1U
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.root_projection.inode);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.cwd_projection.mount_id);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[0].operation_index);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[0].exit_stop_index);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[1].syscall_number);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[1].arguments[0]);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[4].syscall_number);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[4].arguments[5]);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[5].arguments[0]);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[6].operation);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(++splice.operations[6].syscall_number);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].arguments[0] = 0U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].arguments[1] = 0U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].arguments[2] = 1U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].arguments[3] = 7U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].arguments[4] = 1U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].arguments[5] = 1U);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        --splice.operations[6].payload_byte_count
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.operations[6].payload_bytes[0] = 1U
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        --splice.operations[6].entry_stop_index
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        --splice.operations[6].exit_stop_index
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.operations[6].raw_exit_wait_status ^= 1
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[6].return_value = -1);
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.operations[6].return_is_error = 1U
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[2].path_bytes[0] = '/');
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        splice.operations[3].raw_entry_wait_status ^= 1
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(
        ++splice.operations[3].exit_instruction_pointer
    );
    V4_HB_EXPECT_SETUP_SPLICE_REJECT(splice.operations[0].return_value = -1);
#undef V4_HB_EXPECT_SETUP_SPLICE_REJECT

    {
        const struct v4_hb_setup_syscall_observation *operation;
        char expected_message[sizeof(error->message)];

        splice = *setup;
        splice.operations[0].raw_exit_wait_status ^= 1;
        operation = &splice.operations[0];
        (void)snprintf(
            expected_message, sizeof(expected_message),
            "stored setup syscall observation is malformed: index=%u "
            "operation=%u nr=%lld path=%u/%u,%u waits=%x,%x "
            "ip=%llu,%llu sp=%llu,%llu return=%lld/%u",
            0U, (unsigned int)operation->operation,
            (long long)operation->syscall_number,
            operation->path_byte_count,
            (unsigned int)operation->path_bytes[0],
            (unsigned int)operation->path_bytes[1],
            (unsigned int)operation->raw_entry_wait_status,
            (unsigned int)operation->raw_exit_wait_status,
            (unsigned long long)operation->entry_instruction_pointer,
            (unsigned long long)operation->exit_instruction_pointer,
            (unsigned long long)operation->entry_stack_pointer,
            (unsigned long long)operation->exit_stack_pointer,
            (long long)operation->return_value,
            operation->return_is_error
        );
        verify_code = v4_hb_builder_verify_setup_prefix(
            builder, &splice, error
        );
        if (verify_code != V4_HB_ERROR) {
            if (verify_code != V4_HB_OK) {
                return verify_code;
            }
            return test_v4_oracle_error(
                error, "malformed setup-prefix observation was accepted"
            );
        }
        if (error->saved_errno != EINVAL ||
            strcmp(error->message, expected_message) != 0) {
            return test_v4_oracle_error(
                error, "malformed setup-prefix diagnostic oracle mismatch"
            );
        }
    }

    return v4_hb_builder_verify_setup_prefix(builder, setup, error);
}

static int
run_setup_prefix(
    struct v4_hb_builder *builder,
    const struct v4_hb_root_anchor_config *config,
    struct v4_hb_setup_prefix_observation *setup,
    struct v4_hb_snapshot *snapshot,
    const char **failure_phase,
    struct v4_hb_error *error
)
{
    struct v4_hb_setup_prefix_observation forbidden_second;
    int code;

    *failure_phase = "setup-prefix traced execution";
    code = v4_hb_builder_run_setup_prefix(builder, setup, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = "positive setup-prefix observation oracle";
    if (!setup_prefix_is_exact(setup, config)) {
        return test_v4_oracle_error(
            error, "positive setup-prefix observation oracle mismatch"
        );
    }
    *failure_phase = "forbidden second setup-prefix run";
    code = v4_hb_builder_run_setup_prefix(
        builder, &forbidden_second, error
    );
    if (code != V4_HB_ERROR) {
        if (code != V4_HB_OK) {
            return code;
        }
        return test_v4_oracle_error(
            error, "second setup-prefix run was accepted"
        );
    }
    *failure_phase = "setup-prefix splice hostility";
    code = expect_setup_prefix_splices_reject(builder, setup, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = "setup-prefix snapshot call";
    code = v4_hb_builder_snapshot(builder, snapshot, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = "setup-prefix snapshot state";
    if (snapshot->state != V4_HB_SETUP_PREFIX_COMPLETE) {
        return test_v4_oracle_error(
            error, "setup-prefix snapshot state mismatch"
        );
    }
    *failure_phase = "setup-prefix snapshot gate";
    if (snapshot->gate_value != 1U) {
        return test_v4_oracle_error(
            error, "setup-prefix snapshot gate mismatch"
        );
    }
    *failure_phase = "setup-prefix snapshot resume count";
    if (snapshot->resume_count != V4_HB_SETUP_PREFIX_STOP_COUNT) {
        return test_v4_oracle_error(
            error, "setup-prefix snapshot resume count mismatch"
        );
    }
    *failure_phase = "setup-prefix snapshot held-stop ownership";
    if (snapshot->held_stop_consumed != 1U) {
        return test_v4_oracle_error(
            error, "setup-prefix snapshot held-stop ownership mismatch"
        );
    }
    *failure_phase = "setup-prefix held verification";
    code = v4_hb_builder_verify_held(builder, snapshot, error);
    if (code != V4_HB_OK) {
        return code;
    }
    *failure_phase = NULL;
    return V4_HB_OK;
}

static int
expect_start_rejection(
    const struct v4_hb_root_anchor_config *config,
    int expected_errno,
    const char *expected_message,
    struct v4_hb_error *error
)
{
    struct v4_hb_builder *builder = NULL;
    int code = v4_hb_builder_start(config, &builder, error);
    int saved_errno = error->saved_errno;
    char message[sizeof(error->message)];

    (void)snprintf(message, sizeof(message), "%s", error->message);
    if (builder != NULL) {
        (void)v4_hb_builder_abort(builder, error);
        v4_hb_builder_destroy(builder);
    }
    if (code != V4_HB_ERROR || builder != NULL ||
        saved_errno != expected_errno ||
        strcmp(message, expected_message) != 0) {
        (void)fprintf(
            stderr,
            "FAIL: start rejection code=%d errno=%d/%d message=%s/%s\n",
            code, saved_errno, expected_errno, message, expected_message
        );
        return -1;
    }
    return 0;
}

static int
expect_bound_walk_rejection(
    const struct v4_hb_root_anchor_config *config,
    int expected_errno,
    const char *expected_message,
    struct v4_hb_error *error
)
{
    struct v4_hb_builder *builder = NULL;
    struct v4_hb_bound_root_walks walks;
    struct v4_hb_snapshot held;
    int code = v4_hb_builder_start(config, &builder, error);
    int walk_code;
    int walk_errno;
    int abort_code;
    char message[sizeof(error->message)];

    if (code != V4_HB_OK || builder == NULL) {
        if (builder != NULL) {
            (void)v4_hb_builder_abort(builder, error);
            v4_hb_builder_destroy(builder);
        }
        return -1;
    }
    if (v4_hb_builder_seize_interrupt(builder, &held, error) != V4_HB_OK) {
        (void)v4_hb_builder_abort(builder, error);
        v4_hb_builder_destroy(builder);
        return -1;
    }
    walk_code = v4_hb_builder_run_bound_root_walks(
        builder, &walks, error
    );
    walk_errno = error->saved_errno;
    (void)snprintf(message, sizeof(message), "%s", error->message);
    v4_hb_bound_root_walks_destroy(&walks);
    abort_code = v4_hb_builder_abort(builder, error);
    v4_hb_builder_destroy(builder);
    if (walk_code != V4_HB_ERROR || walk_errno != expected_errno ||
        strcmp(message, expected_message) != 0 || abort_code != V4_HB_OK) {
        (void)fprintf(
            stderr,
            "FAIL: walk rejection code=%d errno=%d/%d abort=%d "
            "message=%s/%s\n",
            walk_code, walk_errno, expected_errno, abort_code,
            message, expected_message
        );
        return -1;
    }
    return 0;
}

static int
expect_status_credential_rejection(
    const char *payload,
    size_t payload_bytes,
    int expected_errno,
    const char *expected_message
)
{
    struct v4_hb_status_credential_ids ids;
    struct v4_hb_error error;
    int code = v4_hb_parse_status_credential_rows(
        payload, payload_bytes, &ids, &error
    );

    if (code != V4_HB_ERROR || error.saved_errno != expected_errno ||
        strcmp(error.message, expected_message) != 0) {
        return -1;
    }
    return 0;
}

static int
test_status_credential_parser(void)
{
    static const char valid[] =
        "Name:\tbuilder\n"
        "Uid:\t11\t12\t13\t14\n"
        "Gid:\t21\t22\t23\t24\n"
        "State:\tt (tracing stop)\n";
    static const char duplicate[] =
        "Uid:\t1\t1\t1\t1\nUid:\t1\t1\t1\t1\nGid:\t2\t2\t2\t2\n";
    static const char missing[] = "Uid:\t1\t1\t1\t1\n";
    static const char bad_prefix[] =
        "Uid: 1\t1\t1\t1\nGid:\t2\t2\t2\t2\n";
    static const char extra_token[] =
        "Uid:\t1\t1\t1\t1\t1\nGid:\t2\t2\t2\t2\n";
    static const char overflow[] =
        "Uid:\t4294967296\t1\t1\t1\nGid:\t2\t2\t2\t2\n";
    static const char reversed[] =
        "Gid:\t2\t2\t2\t2\nUid:\t1\t1\t1\t1\n";
    static const char leading_zero[] =
        "Uid:\t01\t1\t1\t1\nGid:\t2\t2\t2\t2\n";
    static const char empty_token[] =
        "Uid:\t1\t\t1\t1\nGid:\t2\t2\t2\t2\n";
    static const char unterminated[] =
        "Uid:\t1\t1\t1\t1\nGid:\t2\t2\t2\t2";
    static const char embedded_nul[] =
        "Uid:\t1\t1\0\t1\t1\nGid:\t2\t2\t2\t2\n";
    struct v4_hb_status_credential_ids ids;
    struct v4_hb_error error;
    char over_cap[16385U];

    memset(over_cap, 'X', sizeof(over_cap));
    over_cap[sizeof(over_cap) - 1U] = '\n';

    if (v4_hb_parse_status_credential_rows(
            valid, sizeof(valid) - 1U, &ids, &error
        ) != V4_HB_OK ||
        ids.real_uid != 11U || ids.effective_uid != 12U ||
        ids.saved_uid != 13U || ids.filesystem_uid != 14U ||
        ids.real_gid != 21U || ids.effective_gid != 22U ||
        ids.saved_gid != 23U || ids.filesystem_gid != 24U ||
        expect_status_credential_rejection(
            duplicate, sizeof(duplicate) - 1U, EINVAL,
            "status credential row is duplicate"
        ) != 0 ||
        expect_status_credential_rejection(
            missing, sizeof(missing) - 1U, EINVAL,
            "status credential rows are incomplete"
        ) != 0 ||
        expect_status_credential_rejection(
            bad_prefix, sizeof(bad_prefix) - 1U, EINVAL,
            "status credential row prefix is malformed"
        ) != 0 ||
        expect_status_credential_rejection(
            extra_token, sizeof(extra_token) - 1U, EINVAL,
            "status credential row values are malformed"
        ) != 0 ||
        expect_status_credential_rejection(
            overflow, sizeof(overflow) - 1U, EINVAL,
            "status credential row values are malformed"
        ) != 0 ||
        expect_status_credential_rejection(
            reversed, sizeof(reversed) - 1U, EINVAL,
            "status credential row order is malformed"
        ) != 0 ||
        expect_status_credential_rejection(
            leading_zero, sizeof(leading_zero) - 1U, EINVAL,
            "status credential row values are malformed"
        ) != 0 ||
        expect_status_credential_rejection(
            empty_token, sizeof(empty_token) - 1U, EINVAL,
            "status credential row values are malformed"
        ) != 0 ||
        expect_status_credential_rejection(
            unterminated, sizeof(unterminated) - 1U, EINVAL,
            "status credential payload is not exact text"
        ) != 0 ||
        expect_status_credential_rejection(
            embedded_nul, sizeof(embedded_nul) - 1U, EINVAL,
            "status credential payload is not exact text"
        ) != 0 ||
        expect_status_credential_rejection(
            over_cap, sizeof(over_cap), EOVERFLOW,
            "status credential payload exceeds cap"
        ) != 0) {
        return -1;
    }
    return 0;
}

static int
expect_status_capability_rejection(
    const char *payload,
    size_t payload_bytes,
    int expected_errno,
    const char *expected_message
)
{
    struct v4_hb_status_capability_masks masks;
    struct v4_hb_error error;
    int code = v4_hb_parse_status_capability_rows(
        payload, payload_bytes, &masks, &error
    );

    if (code != V4_HB_ERROR || error.saved_errno != expected_errno ||
        strcmp(error.message, expected_message) != 0) {
        return -1;
    }
    return 0;
}

static int
test_status_capability_parser(void)
{
    static const char valid[] =
        "Name:\tbuilder\n"
        "CapInh:\t0000000000000001\n"
        "CapPrm:\t0000000000000010\n"
        "CapEff:\t0000000000000100\n"
        "CapBnd:\t0000000000001000\n"
        "CapAmb:\t8000000000000000\n"
        "State:\tt (tracing stop)\n";
    static const char duplicate[] =
        "CapInh:\t0000000000000000\n"
        "CapInh:\t0000000000000000\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    static const char missing[] =
        "CapInh:\t0000000000000000\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n";
    static const char reversed[] =
        "CapPrm:\t0000000000000000\n"
        "CapInh:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    static const char uppercase[] =
        "CapInh:\t000000000000000A\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    static const char short_value[] =
        "CapInh:\t000000000000000\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    static const char extra_token[] =
        "CapInh:\t0000000000000000 0\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    static const char bad_name[] =
        "CapFoo:\t0000000000000000\n"
        "CapInh:\t0000000000000000\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    static const char embedded_nul[] =
        "CapInh:\t0000000000000000\n"
        "CapPrm:\t0000000000000000\n"
        "CapEff:\t00000000\0" "00000000\n"
        "CapBnd:\t0000000000000000\n"
        "CapAmb:\t0000000000000000\n";
    struct v4_hb_status_capability_masks masks;
    struct v4_hb_error error;
    char over_cap[16385U];

    memset(over_cap, 'X', sizeof(over_cap));
    over_cap[sizeof(over_cap) - 1U] = '\n';
    if (v4_hb_parse_status_capability_rows(
            valid, sizeof(valid) - 1U, &masks, &error
        ) != V4_HB_OK || masks.inheritable != UINT64_C(0x1) ||
        masks.permitted != UINT64_C(0x10) ||
        masks.effective != UINT64_C(0x100) ||
        masks.bounding != UINT64_C(0x1000) ||
        masks.ambient != UINT64_C(0x8000000000000000) ||
        expect_status_capability_rejection(
            duplicate, sizeof(duplicate) - 1U, EINVAL,
            "status capability row order is malformed"
        ) != 0 || expect_status_capability_rejection(
            missing, sizeof(missing) - 1U, EINVAL,
            "status capability rows are incomplete"
        ) != 0 || expect_status_capability_rejection(
            reversed, sizeof(reversed) - 1U, EINVAL,
            "status capability row order is malformed"
        ) != 0 || expect_status_capability_rejection(
            uppercase, sizeof(uppercase) - 1U, EINVAL,
            "status capability row value is malformed"
        ) != 0 || expect_status_capability_rejection(
            short_value, sizeof(short_value) - 1U, EINVAL,
            "status capability row value is malformed"
        ) != 0 || expect_status_capability_rejection(
            extra_token, sizeof(extra_token) - 1U, EINVAL,
            "status capability row value is malformed"
        ) != 0 || expect_status_capability_rejection(
            bad_name, sizeof(bad_name) - 1U, EINVAL,
            "status capability row name is malformed"
        ) != 0 || expect_status_capability_rejection(
            embedded_nul, sizeof(embedded_nul) - 1U, EINVAL,
            "status capability payload is not exact text"
        ) != 0 || expect_status_capability_rejection(
            over_cap, sizeof(over_cap), EOVERFLOW,
            "status capability payload exceeds cap"
        ) != 0) {
        return -1;
    }
    return 0;
}

enum hostile_literal_kind {
    HOSTILE_LITERAL_MISSING = 0,
    HOSTILE_LITERAL_SYMLINK = 1,
    HOSTILE_LITERAL_REGULAR = 2,
};

static int
populate_hostile_literal_fixture(
    int parent_fd,
    const char *relative,
    enum hostile_literal_kind kind
)
{
    int root_fd = openat(
        parent_fd, relative,
        O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
    );
    int result = 0;

    if (root_fd < 0) {
        return -1;
    }
    if (kind == HOSTILE_LITERAL_SYMLINK) {
        result = symlinkat(
            ".", root_fd, V4_ORW_DECLARED_OUTPUT_EDGE
        );
    } else if (kind == HOSTILE_LITERAL_REGULAR) {
        result = write_file_at(
            root_fd, V4_ORW_DECLARED_OUTPUT_EDGE, "not a directory\n"
        );
        if (result == 0) {
            result = fchmodat(
                root_fd, V4_ORW_DECLARED_OUTPUT_EDGE, 0444, 0
            );
        }
    }
    if (result == 0) {
        result = fchmodat(parent_fd, relative, 0555, 0);
    }
    if (close(root_fd) != 0 && result == 0) {
        result = -1;
    }
    return result;
}

int
main(void)
{
    char temporary[512] = {0};
    char input_path[512] = {0};
    char output_path[512] = {0};
    char wrong_output_path[512] = {0};
    char nested_attack_path[512] = {0};
    char missing_input_path[512] = {0};
    char symlink_input_path[512] = {0};
    char regular_input_path[512] = {0};
    char output_alias_path[512] = {0};
    struct v4_orw_logical_ledger ledger;
    struct v4_orw_output_anchor input_anchor;
    struct v4_orw_output_anchor output_anchor;
    struct v4_orw_output_anchor wrong_output_anchor;
    struct v4_orw_output_anchor same_mount_anchor;
    struct v4_orw_output_anchor missing_input_anchor;
    struct v4_orw_output_anchor symlink_input_anchor;
    struct v4_orw_output_anchor regular_input_anchor;
    struct v4_orw_output_anchor output_alias_anchor;
    struct v4_hb_root_anchor_config config;
    struct v4_hb_root_anchor_config expected_config;
    struct v4_hb_root_anchor_config nonempty_config;
    struct v4_hb_root_anchor_config wrong_output_config;
    struct v4_hb_root_anchor_config same_mount_config;
    struct v4_hb_root_anchor_config missing_literal_config;
    struct v4_hb_root_anchor_config symlink_literal_config;
    struct v4_hb_root_anchor_config regular_literal_config;
    struct v4_hb_root_anchor_config output_alias_config;
    struct v4_orw_error walk_error;
    struct v4_hb_builder *builder = NULL;
    struct v4_hb_builder *attack_builder = NULL;
    struct v4_hb_builder *exit_builder = NULL;
    struct v4_hb_builder *alias_builder = NULL;
    struct v4_hb_builder *nonempty_builder = NULL;
    struct v4_hb_builder *wrong_output_builder = NULL;
    struct v4_hb_snapshot initial;
    struct v4_hb_snapshot held;
    struct v4_hb_snapshot completed;
    struct v4_hb_snapshot setup_snapshot;
    struct v4_hb_setup_prefix_observation setup;
    struct v4_hb_completion completion;
    struct v4_hb_error error;
    const char *held_failure_phase = NULL;
    const char *setup_failure_phase = NULL;
    const char *temporary_parent = getenv("TMPDIR");
    int root_fd = -1;
    int input_fd = -1;
    int saved_pidfd = -1;
    int saved_parent_namespace_fds[V4_HB_NAMESPACE_COUNT];
    int saved_child_namespace_fds[V4_HB_NAMESPACE_COUNT];
    uint32_t namespace_index;
    int status = 1;
    bool input_mounted = false;
    bool output_mounted = false;
    bool wrong_output_mounted = false;
    bool nested_attack_mounted = false;
    bool missing_input_mounted = false;
    bool symlink_input_mounted = false;
    bool regular_input_mounted = false;
    bool output_alias_mounted = false;
    int code;
    int temporary_path_length;

    if (temporary_parent == NULL || temporary_parent[0] == '\0') {
        temporary_parent = "/tmp";
    }
    temporary_path_length = snprintf(
        temporary, sizeof(temporary), "%s%s%s",
        temporary_parent,
        temporary_parent[strlen(temporary_parent) - 1U] == '/' ? "" : "/",
        "candle-v4-held-builder.XXXXXX"
    );
    if (temporary_parent[0] != '/' || temporary_path_length < 0 ||
        (size_t)temporary_path_length >= sizeof(temporary) ||
        (size_t)temporary_path_length >
            sizeof(temporary) -
                sizeof("/candle-input/" V4_ORW_DECLARED_OUTPUT_EDGE)) {
        return test_fail("TMPDIR does not admit a bounded native fixture path");
    }

    if (V4_HB_FIXED_PTRACE_OPTIONS_MASK != 0x0010007fUL ||
        V4_HB_PTRACE_OPTION_COUNT != 8U ||
        V4_HB_FIXED_CLONE_FLAGS != 0x78020011UL ||
        V4_HB_NAMESPACE_COUNT != 5U ||
        V4_HB_SETUP_PREFIX_OPERATION_COUNT != 7U ||
        V4_HB_SETUP_PREFIX_STOP_COUNT != 14U) {
        return test_fail("fixed V4 ptrace/namespace identity drifted");
    }
    if (test_status_credential_parser() != 0) {
        return test_fail("status credential parser hostility failed");
    }
    if (test_status_capability_parser() != 0) {
        return test_fail("status capability parser hostility failed");
    }
    if (mkdtemp(temporary) == NULL) {
        return test_fail("mkdtemp failed");
    }
    if (enter_private_mount_namespace() != 0) {
        (void)rmdir(temporary);
        return test_skip("unprivileged user/mount namespaces unavailable");
    }
    memset(&input_anchor, 0, sizeof(input_anchor));
    memset(&output_anchor, 0, sizeof(output_anchor));
    memset(&wrong_output_anchor, 0, sizeof(wrong_output_anchor));
    memset(&same_mount_anchor, 0, sizeof(same_mount_anchor));
    memset(&missing_input_anchor, 0, sizeof(missing_input_anchor));
    memset(&symlink_input_anchor, 0, sizeof(symlink_input_anchor));
    memset(&regular_input_anchor, 0, sizeof(regular_input_anchor));
    memset(&output_alias_anchor, 0, sizeof(output_alias_anchor));
    input_anchor.primary.fd = -1;
    input_anchor.guard.fd = -1;
    output_anchor.primary.fd = -1;
    output_anchor.guard.fd = -1;
    wrong_output_anchor.primary.fd = -1;
    wrong_output_anchor.guard.fd = -1;
    same_mount_anchor.primary.fd = -1;
    same_mount_anchor.guard.fd = -1;
    missing_input_anchor.primary.fd = -1;
    missing_input_anchor.guard.fd = -1;
    symlink_input_anchor.primary.fd = -1;
    symlink_input_anchor.guard.fd = -1;
    regular_input_anchor.primary.fd = -1;
    regular_input_anchor.guard.fd = -1;
    output_alias_anchor.primary.fd = -1;
    output_alias_anchor.guard.fd = -1;
    root_fd = open(temporary,
                   O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root_fd < 0 || mkdirat(root_fd, "candle-input", 0700) != 0 ||
        mkdirat(root_fd, "wrong-output", 0700) != 0 ||
        mkdirat(root_fd, "missing-input", 0700) != 0 ||
        mkdirat(root_fd, "symlink-input", 0700) != 0 ||
        mkdirat(root_fd, "regular-input", 0700) != 0 ||
        mkdirat(root_fd, "output-alias", 0700) != 0 ||
        snprintf(input_path, sizeof(input_path), "%s/candle-input",
                 temporary) < 0 ||
        snprintf(output_path, sizeof(output_path),
                 "%s/candle-input/%s", temporary,
                 V4_ORW_DECLARED_OUTPUT_EDGE) < 0 ||
        snprintf(wrong_output_path, sizeof(wrong_output_path),
                 "%s/wrong-output", temporary) < 0 ||
        snprintf(nested_attack_path, sizeof(nested_attack_path),
                 "%s/candle-input/sub", temporary) < 0 ||
        snprintf(missing_input_path, sizeof(missing_input_path),
                 "%s/missing-input", temporary) < 0 ||
        snprintf(symlink_input_path, sizeof(symlink_input_path),
                 "%s/symlink-input", temporary) < 0 ||
        snprintf(regular_input_path, sizeof(regular_input_path),
                 "%s/regular-input", temporary) < 0 ||
        snprintf(output_alias_path, sizeof(output_alias_path),
                 "%s/output-alias", temporary) < 0) {
        (void)test_fail("cannot construct held-builder roots");
        goto cleanup;
    }
    if (mount("tmpfs", input_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=16777216,mode=0700") != 0) {
        status = test_skip("private input tmpfs mount unavailable");
        goto cleanup;
    }
    input_mounted = true;
    if (mount("tmpfs", wrong_output_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0700") != 0) {
        status = test_skip("private hostile output mount unavailable");
        goto cleanup;
    }
    wrong_output_mounted = true;
    if (mount("tmpfs", missing_input_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0700") != 0) {
        status = test_skip("private missing-literal input mount unavailable");
        goto cleanup;
    }
    missing_input_mounted = true;
    if (mount("tmpfs", symlink_input_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0700") != 0) {
        status = test_skip("private symlink-literal input mount unavailable");
        goto cleanup;
    }
    symlink_input_mounted = true;
    if (mount("tmpfs", regular_input_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0700") != 0) {
        status = test_skip("private regular-literal input mount unavailable");
        goto cleanup;
    }
    regular_input_mounted = true;
    if (populate_hostile_literal_fixture(
            root_fd, "missing-input", HOSTILE_LITERAL_MISSING
        ) != 0 ||
        populate_hostile_literal_fixture(
            root_fd, "symlink-input", HOSTILE_LITERAL_SYMLINK
        ) != 0 ||
        populate_hostile_literal_fixture(
            root_fd, "regular-input", HOSTILE_LITERAL_REGULAR
        ) != 0 ||
        mount(NULL, missing_input_path, NULL,
              MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0 ||
        mount(NULL, symlink_input_path, NULL,
              MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0 ||
        mount(NULL, regular_input_path, NULL,
              MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0) {
        (void)test_fail("cannot seal hostile literal input fixtures");
        goto cleanup;
    }
    input_fd = openat(
        root_fd, "candle-input",
        O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
    );
    if (input_fd < 0 || mkdirat(input_fd, "sub", 0700) != 0 ||
        mkdirat(input_fd, V4_ORW_DECLARED_OUTPUT_EDGE, 0700) != 0 ||
        write_file_at(input_fd, "alpha.txt", "alpha\n") != 0 ||
        write_file_at(input_fd, "sub/beta.txt", "beta\n") != 0 ||
        fchmodat(input_fd, "alpha.txt", 0444, 0) != 0 ||
        fchmodat(input_fd, "sub/beta.txt", 0444, 0) != 0 ||
        fchmodat(input_fd, "sub", 0555, 0) != 0 ||
        fchmodat(root_fd, "candle-input", 0555, 0) != 0) {
        (void)test_fail("cannot populate deterministic input root");
        goto cleanup;
    }
    if (mount("tmpfs", output_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0700") != 0) {
        status = test_skip("private nested output tmpfs mount unavailable");
        goto cleanup;
    }
    output_mounted = true;
    if (mount(output_path, output_alias_path, NULL, MS_BIND, NULL) != 0) {
        status = test_skip("private output bind-mount alias unavailable");
        goto cleanup;
    }
    output_alias_mounted = true;
    if (write_file_at(
            input_fd, V4_ORW_DECLARED_OUTPUT_EDGE "/unexpected",
            "unexpected\n"
        ) != 0 ||
        mount(NULL, input_path, NULL,
              MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0 ||
        v4_orw_logical_ledger_init(&ledger, &walk_error) != V4_ORW_OK) {
        (void)test_fail("cannot populate hostile nonempty output root");
        goto cleanup;
    }
    code = v4_orw_output_anchor_open(
        root_fd, "candle-input", &ledger, &input_anchor, &walk_error
    );
    if (code == V4_ORW_UNSUPPORTED) {
        status = test_skip(walk_error.message);
        goto cleanup;
    }
    if (code != V4_ORW_OK) {
        (void)test_fail("cannot retain input anchor");
        goto cleanup;
    }
    code = v4_orw_output_anchor_open(
        input_fd, V4_ORW_DECLARED_OUTPUT_EDGE,
        &ledger, &output_anchor, &walk_error
    );
    if (code == V4_ORW_UNSUPPORTED) {
        status = test_skip(walk_error.message);
        goto cleanup_anchor;
    }
    if (code != V4_ORW_OK) {
        (void)test_fail("cannot retain output anchor");
        goto cleanup_anchor;
    }
    nonempty_config.input_root = input_anchor;
    nonempty_config.output_root = output_anchor;
    nonempty_config.logical_ledger = ledger;
    if (close(input_fd) != 0) {
        (void)test_fail("cannot retire input fixture setup descriptor");
        goto cleanup_anchor;
    }
    input_fd = -1;
    if (close(root_fd) != 0) {
        (void)test_fail("cannot retire fixture root setup descriptor");
        goto cleanup_anchor;
    }
    root_fd = -1;

    code = v4_hb_builder_start(
        &nonempty_config, &nonempty_builder, &error
    );
    if (code != V4_HB_OK) {
        if (code == V4_HB_UNSUPPORTED) {
            status = test_skip(error.message);
        } else {
            (void)test_fail("cannot start nonempty-output hostile builder");
        }
        goto cleanup_anchor;
    }
    {
        struct v4_hb_bound_root_walks rejected_walks;
        char rejection[sizeof(error.message)];
        int walk_code;
        int abort_code;

        if (v4_hb_builder_seize_interrupt(
                nonempty_builder, &held, &error
            ) != V4_HB_OK ||
            !held_snapshot_is_exact(&held, &nonempty_config)) {
            (void)test_fail("cannot establish nonempty output boundary");
            goto cleanup_anchor;
        }
        walk_code = v4_hb_builder_run_bound_root_walks(
            nonempty_builder, &rejected_walks, &error
        );
        (void)snprintf(rejection, sizeof(rejection), "%s", error.message);
        abort_code = v4_hb_builder_abort(nonempty_builder, &error);
        if (walk_code != V4_HB_ERROR ||
            strcmp(
                rejection,
                "held output-root pre-walk is not exactly empty"
            ) != 0 || abort_code != V4_HB_OK) {
            (void)test_fail("nonempty held output root did not fail closed");
            goto cleanup_anchor;
        }
        v4_hb_bound_root_walks_destroy(&rejected_walks);
    }
    v4_hb_builder_destroy(nonempty_builder);
    nonempty_builder = NULL;

    if (unlinkat(
            output_anchor.primary.fd, "unexpected", 0
        ) != 0) {
        (void)test_fail("cannot clear the hostile output fixture");
        goto cleanup_anchor;
    }
    v4_orw_output_anchor_close(&output_anchor);
    v4_orw_output_anchor_close(&input_anchor);
    root_fd = open(temporary,
                   O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    input_fd = root_fd < 0 ? -1 : openat(
        root_fd, "candle-input",
        O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
    );
    if (root_fd < 0 || input_fd < 0 ||
        v4_orw_output_anchor_open(
            root_fd, "candle-input", &ledger,
            &input_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            input_fd, V4_ORW_DECLARED_OUTPUT_EDGE, &ledger,
            &output_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            root_fd, "wrong-output", &ledger,
            &wrong_output_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            input_fd, "sub", &ledger,
            &same_mount_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            root_fd, "missing-input", &ledger,
            &missing_input_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            root_fd, "symlink-input", &ledger,
            &symlink_input_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            root_fd, "regular-input", &ledger,
            &regular_input_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_open(
            root_fd, "output-alias", &ledger,
            &output_alias_anchor, &walk_error
        ) != V4_ORW_OK) {
        (void)test_fail("cannot retain production/hostile root anchors");
        goto cleanup_anchor;
    }
    config.input_root = input_anchor;
    config.output_root = output_anchor;
    config.logical_ledger = ledger;
    expected_config = config;
    wrong_output_config = config;
    wrong_output_config.output_root = wrong_output_anchor;
    same_mount_config = config;
    same_mount_config.output_root = same_mount_anchor;
    missing_literal_config = config;
    missing_literal_config.input_root = missing_input_anchor;
    missing_literal_config.output_root = wrong_output_anchor;
    symlink_literal_config = config;
    symlink_literal_config.input_root = symlink_input_anchor;
    symlink_literal_config.output_root = wrong_output_anchor;
    regular_literal_config = config;
    regular_literal_config.input_root = regular_input_anchor;
    regular_literal_config.output_root = wrong_output_anchor;
    output_alias_config = config;
    output_alias_config.output_root = output_alias_anchor;
    if (expect_root_config_splices_reject(&config, &error) != 0) {
        (void)test_fail("malformed root-anchor config was accepted");
        goto cleanup_anchor;
    }
    if (mount(NULL, input_path, NULL,
              MS_REMOUNT | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0) {
        (void)test_fail("cannot make input mount writable for attack");
        goto cleanup_anchor;
    }
    code = expect_start_rejection(
        &config, EROFS, "input/output root mount access is not closed",
        &error
    );
    if (mount(NULL, input_path, NULL,
              MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0 || code != 0) {
        (void)test_fail("writable input mount did not fail closed");
        goto cleanup_anchor;
    }
    if (mount(NULL, output_path, NULL,
              MS_REMOUNT | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0) {
        (void)test_fail("cannot make output mount read-only for attack");
        goto cleanup_anchor;
    }
    code = expect_start_rejection(
        &config, EROFS, "input/output root mount access is not closed",
        &error
    );
    if (mount(NULL, output_path, NULL,
              MS_REMOUNT | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) != 0 || code != 0) {
        (void)test_fail("read-only output mount did not fail closed");
        goto cleanup_anchor;
    }
    {
        struct v4_hb_builder *unexpected = NULL;
        int same_mount_code = v4_hb_builder_start(
            &same_mount_config, &unexpected, &error
        );

        if (same_mount_code != V4_HB_ERROR || unexpected != NULL ||
            strcmp(
                error.message,
                "output root is not a separate nested mount"
            ) != 0) {
            if (unexpected != NULL) {
                (void)v4_hb_builder_abort(unexpected, &error);
                v4_hb_builder_destroy(unexpected);
            }
            (void)test_fail("same-mount output root was accepted");
            goto cleanup_anchor;
        }
    }
    if (close(input_fd) != 0 || close(root_fd) != 0) {
        (void)test_fail("cannot retire production fixture descriptors");
        goto cleanup_anchor;
    }
    input_fd = -1;
    root_fd = -1;
    v4_orw_output_anchor_close(&same_mount_anchor);

    if (output_alias_anchor.initial_projection.st_dev !=
            output_anchor.initial_projection.st_dev ||
        output_alias_anchor.initial_projection.st_ino !=
            output_anchor.initial_projection.st_ino ||
        output_alias_anchor.initial_projection.mount_id ==
            output_anchor.initial_projection.mount_id) {
        (void)test_fail("bind-mount alias lacks same-object/new-mount shape");
        goto cleanup_anchor;
    }
    if (expect_bound_walk_rejection(
            &missing_literal_config, ENOENT,
            "held input-root walk failed: declared output mount edge is "
            "missing", &error
        ) != 0 ||
        expect_bound_walk_rejection(
            &symlink_literal_config, ELOOP,
            "held input-root walk failed: literal output edge is symbolic",
            &error
        ) != 0 ||
        expect_bound_walk_rejection(
            &regular_literal_config, ENOTDIR,
            "held input-root walk failed: literal output edge is not a "
            "directory", &error
        ) != 0 ||
        expect_bound_walk_rejection(
            &output_alias_config, EINVAL,
            "held input-root walk failed: literal output edge does not "
            "match its declared mount", &error
        ) != 0) {
        (void)test_fail("literal or bind-mount edge attack was accepted");
        goto cleanup_anchor;
    }
    v4_orw_output_anchor_close(&output_alias_anchor);
    v4_orw_output_anchor_close(&regular_input_anchor);
    v4_orw_output_anchor_close(&symlink_input_anchor);
    v4_orw_output_anchor_close(&missing_input_anchor);

    code = v4_hb_builder_start(
        &wrong_output_config, &wrong_output_builder, &error
    );
    if (code != V4_HB_OK) {
        (void)test_fail("cannot start wrong-output hostile builder");
        goto cleanup_anchor;
    }
    {
        struct v4_hb_bound_root_walks rejected_walks;
        char rejection[sizeof(error.message)];
        int walk_code;
        int abort_code;

        if (v4_hb_builder_seize_interrupt(
                wrong_output_builder, &held, &error
            ) != V4_HB_OK) {
            (void)test_fail("cannot establish wrong-output boundary");
            goto cleanup_anchor;
        }
        walk_code = v4_hb_builder_run_bound_root_walks(
            wrong_output_builder, &rejected_walks, &error
        );
        (void)snprintf(rejection, sizeof(rejection), "%s", error.message);
        abort_code = v4_hb_builder_abort(wrong_output_builder, &error);
        if (walk_code != V4_HB_ERROR ||
            strcmp(
                rejection,
                "held input-root walk failed: literal output edge does not "
                "match its declared mount"
            ) != 0 || abort_code != V4_HB_OK) {
            (void)test_fail("wrong output edge did not fail closed");
            goto cleanup_anchor;
        }
        v4_hb_bound_root_walks_destroy(&rejected_walks);
    }
    v4_hb_builder_destroy(wrong_output_builder);
    wrong_output_builder = NULL;
    v4_orw_output_anchor_close(&wrong_output_anchor);

    if (mount("tmpfs", nested_attack_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0555") != 0) {
        (void)test_fail("cannot construct undeclared nested-mount attack");
        goto cleanup_anchor;
    }
    nested_attack_mounted = true;
    code = v4_hb_builder_start(&config, &attack_builder, &error);
    if (code != V4_HB_OK) {
        (void)test_fail("cannot start nested-mount hostile builder");
        goto cleanup_anchor;
    }
    {
        struct v4_hb_bound_root_walks rejected_walks;
        char rejection[sizeof(error.message)];
        int walk_code;
        int rejection_errno;
        int abort_code;

        if (v4_hb_builder_seize_interrupt(
                attack_builder, &held, &error
            ) != V4_HB_OK) {
            (void)test_fail("cannot establish nested-mount boundary");
            goto cleanup_anchor;
        }
        walk_code = v4_hb_builder_run_bound_root_walks(
            attack_builder, &rejected_walks, &error
        );
        rejection_errno = error.saved_errno;
        (void)snprintf(rejection, sizeof(rejection), "%s", error.message);
        abort_code = v4_hb_builder_abort(attack_builder, &error);
        if (walk_code != V4_HB_ERROR || rejection_errno != EXDEV ||
            strcmp(
                rejection,
                "held input-root walk failed: undeclared nested mount is "
                "forbidden"
            ) != 0 || abort_code != V4_HB_OK) {
            (void)test_fail("undeclared nested mount did not fail closed");
            goto cleanup_anchor;
        }
        v4_hb_bound_root_walks_destroy(&rejected_walks);
    }
    v4_hb_builder_destroy(attack_builder);
    attack_builder = NULL;
    if (umount2(nested_attack_path, MNT_DETACH) != 0) {
        (void)test_fail("cannot detach undeclared nested-mount attack");
        goto cleanup_anchor;
    }
    nested_attack_mounted = false;

    code = v4_hb_builder_start(&config, &builder, &error);
    if (code == V4_HB_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup_anchor;
    }
    ++config.input_root.primary.fd_generation;
    if (code != V4_HB_OK ||
        v4_hb_builder_snapshot(builder, &initial, &error) != V4_HB_OK ||
        !initial_snapshot_is_exact(&initial, &expected_config) ||
        v4_hb_builder_release_and_reap(
            builder, &completion, &error
        ) != V4_HB_ERROR) {
        (void)test_fail("initial userspace-gate boundary is malformed");
        goto cleanup_anchor;
    }
    config = expected_config;
    code = hold_and_prewalk(
        builder, &config, &held, &held_failure_phase, &error
    );
    if (code == V4_HB_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup_anchor;
    }
    if (code != V4_HB_OK ||
        v4_hb_builder_snapshot(builder, &completed, &error) != V4_HB_OK ||
        completed.state != V4_HB_BOUND_ROOT_WALKS_COMPLETE ||
        completed.gate_value != 0 || completed.pid != held.pid ||
        completed.start_ticks != held.start_ticks ||
        completed.raw_interrupt_wait_status !=
            held.raw_interrupt_wait_status ||
        v4_hb_builder_verify_held(builder, &completed, &error) != V4_HB_OK) {
        (void)fprintf(
            stderr,
            "FAIL: held bound-root walk boundary is malformed: code=%d "
            "state=%d gate=%u pid=%ld/%ld ticks=%llu/%llu wait=%x/%x %s\n",
            code, (int)completed.state, completed.gate_value,
            (long)completed.pid, (long)held.pid,
            (unsigned long long)completed.start_ticks,
            (unsigned long long)held.start_ticks,
            (unsigned int)completed.raw_interrupt_wait_status,
            (unsigned int)held.raw_interrupt_wait_status, error.message
        );
        goto cleanup_anchor;
    }
    code = run_setup_prefix(
        builder, &config, &setup, &setup_snapshot,
        &setup_failure_phase, &error
    );
    if (code == V4_HB_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup_anchor;
    }
    if (code != V4_HB_OK ||
        setup_snapshot.pid != completed.pid ||
        setup_snapshot.start_ticks != completed.start_ticks ||
        setup_snapshot.raw_interrupt_wait_status !=
            completed.raw_interrupt_wait_status) {
        (void)test_v4_diagnostic_failure(
            "traced setup prefix is malformed",
            setup_failure_phase != NULL ? setup_failure_phase :
                "post-helper identity join",
            code, builder, &error
        );
        goto cleanup_anchor;
    }
    saved_pidfd = completed.pidfd;
    for (namespace_index = 0;
         namespace_index < V4_HB_NAMESPACE_COUNT;
         ++namespace_index) {
        saved_parent_namespace_fds[namespace_index] =
            completed.parent_namespaces[namespace_index].descriptor;
        saved_child_namespace_fds[namespace_index] =
            completed.child_namespaces[namespace_index].descriptor;
    }
    if (v4_hb_builder_release_and_reap(
            builder, &completion, &error
        ) != V4_HB_OK ||
        !WIFSTOPPED(completion.raw_exit_event_wait_status) ||
        WSTOPSIG(completion.raw_exit_event_wait_status) != SIGTRAP ||
        (unsigned int)completion.raw_exit_event_wait_status >> 16 !=
            PTRACE_EVENT_EXIT ||
        completion.exit_event_message != 0UL ||
        !WIFEXITED(completion.raw_final_wait_status) ||
        completion.exit_code != 0 ||
        fcntl(saved_pidfd, F_GETFD) != -1 || errno != EBADF) {
        (void)fprintf(stderr, "FAIL: controlled release: %s\n", error.message);
        goto cleanup_anchor;
    }
    for (namespace_index = 0;
         namespace_index < V4_HB_NAMESPACE_COUNT;
         ++namespace_index) {
        if (fcntl(saved_parent_namespace_fds[namespace_index], F_GETFD) != -1 ||
            errno != EBADF ||
            fcntl(saved_child_namespace_fds[namespace_index], F_GETFD) != -1 ||
            errno != EBADF) {
            (void)test_fail("retained namespace descriptors were not closed");
            goto cleanup_anchor;
        }
    }
    if (v4_orw_output_anchor_revalidate(
            &input_anchor, &walk_error
        ) != V4_ORW_OK ||
        v4_orw_output_anchor_revalidate(
            &output_anchor, &walk_error
        ) != V4_ORW_OK) {
        (void)test_fail("builder ambiguously consumed caller-owned anchors");
        goto cleanup_anchor;
    }
    v4_hb_builder_destroy(builder);
    builder = NULL;

    held_failure_phase = "setup-oracle builder start";
    code = v4_hb_builder_start(&config, &attack_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            attack_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish setup-oracle attack boundary",
            held_failure_phase, code, attack_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        struct v4_hb_root_anchor_config hostile_config = config;
        struct v4_hb_error rejection;
        int setup_code;
        int abort_code;

        ++hostile_config.input_root.primary.fd_generation;
        setup_code = run_setup_prefix(
            attack_builder, &hostile_config, &setup, &setup_snapshot,
            &setup_failure_phase, &error
        );
        rejection = error;
        abort_code = v4_hb_builder_abort(attack_builder, &error);
        if (setup_code != V4_HB_ERROR ||
            strcmp(setup_failure_phase,
                   "positive setup-prefix observation oracle") != 0 ||
            rejection.saved_errno != EINVAL ||
            strcmp(
                rejection.message,
                "positive setup-prefix observation oracle mismatch"
            ) != 0 || abort_code != V4_HB_OK) {
            (void)fprintf(
                stderr,
                "FAIL: setup oracle phase=%s code=%d errno=%d abort=%d "
                "message=%s/%s\n",
                setup_failure_phase, setup_code, rejection.saved_errno,
                abort_code, rejection.message, error.message
            );
            goto cleanup_anchor;
        }
    }
    v4_hb_builder_destroy(attack_builder);
    attack_builder = NULL;

    held_failure_phase = "live signal-mask builder start";
    setup_failure_phase = NULL;
    code = v4_hb_builder_start(&config, &attack_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            attack_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code == V4_HB_OK) {
        code = run_setup_prefix(
            attack_builder, &config, &setup, &setup_snapshot,
            &setup_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish live signal-mask attack boundary",
            setup_failure_phase != NULL ? setup_failure_phase :
                held_failure_phase,
            code, attack_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        uint64_t hostile_signal_mask =
            UINT64_C(1) << ((unsigned int)SIGUSR2 - 1U);
        char verify_message[sizeof(error.message)];
        char release_message[sizeof(error.message)];
        struct v4_hb_snapshot poisoned;
        int verify_code;
        int release_code;
        int snapshot_code;
        int abort_code;

        if (ptrace(
                PTRACE_SETSIGMASK, held.pid,
                (void *)(uintptr_t)V4_HB_KERNEL_SIGSET_BYTES,
                &hostile_signal_mask
            ) != 0) {
            (void)test_fail("cannot mutate held child signal mask");
            goto cleanup_anchor;
        }
        verify_code = v4_hb_builder_verify_setup_prefix(
            attack_builder, &setup, &error
        );
        (void)snprintf(
            verify_message, sizeof(verify_message), "%s", error.message
        );
        release_code = v4_hb_builder_release_and_reap(
            attack_builder, &completion, &error
        );
        (void)snprintf(
            release_message, sizeof(release_message), "%s", error.message
        );
        snapshot_code = v4_hb_builder_snapshot(
            attack_builder, &poisoned, &error
        );
        abort_code = v4_hb_builder_abort(attack_builder, &error);
        if (verify_code != V4_HB_ERROR ||
            strcmp(verify_message,
                   "live child signal mask is not exact empty") != 0 ||
            release_code != V4_HB_ERROR ||
            strcmp(release_message,
                   "live child signal mask is not exact empty") != 0 ||
            snapshot_code != V4_HB_OK ||
            poisoned.state != V4_HB_POISONED ||
            poisoned.gate_value != 1U ||
            poisoned.resume_count != V4_HB_SETUP_PREFIX_STOP_COUNT ||
            poisoned.held_stop_consumed != 1U || abort_code != V4_HB_OK) {
            (void)fprintf(
                stderr,
                "FAIL: live signal-mask mismatch verify=%d release=%d "
                "snapshot=%d abort=%d messages=%s/%s/%s\n",
                verify_code, release_code, snapshot_code, abort_code,
                verify_message, release_message, error.message
            );
            goto cleanup_anchor;
        }
    }
    v4_hb_builder_destroy(attack_builder);
    attack_builder = NULL;

    held_failure_phase = "setup-stop builder start";
    code = v4_hb_builder_start(&config, &attack_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            attack_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish setup-stop attack boundary",
            held_failure_phase, code, attack_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        char rejection[sizeof(error.message)];
        struct v4_hb_snapshot poisoned;
        int setup_code;
        int snapshot_code;
        int rejection_errno;
        int abort_code;

        if (syscall(SYS_pidfd_send_signal, held.pidfd,
                    SIGUSR1, NULL, 0) != 0) {
            (void)test_fail("cannot queue intermediate setup signal");
            goto cleanup_anchor;
        }
        setup_code = run_setup_prefix(
            attack_builder, &config, &setup, &setup_snapshot,
            &setup_failure_phase, &error
        );
        rejection_errno = error.saved_errno;
        (void)snprintf(rejection, sizeof(rejection), "%s", error.message);
        snapshot_code = v4_hb_builder_snapshot(
            attack_builder, &poisoned, &error
        );
        abort_code = v4_hb_builder_abort(attack_builder, &error);
        if (setup_code != V4_HB_ERROR ||
            strcmp(setup_failure_phase,
                   "setup-prefix traced execution") != 0 ||
            rejection_errno != EINVAL ||
            strcmp(rejection,
                   "non-TRACESYSGOOD syscall stop observed") != 0 ||
            snapshot_code != V4_HB_OK ||
            poisoned.state != V4_HB_POISONED ||
            poisoned.gate_value != 1U || poisoned.resume_count != 1U ||
            poisoned.held_stop_consumed != 0U ||
            abort_code != V4_HB_OK) {
            (void)fprintf(
                stderr,
                "FAIL: intermediate setup stop phase=%s code=%d errno=%d "
                "abort=%d message=%s/%s\n",
                setup_failure_phase, setup_code, rejection_errno,
                abort_code, rejection, error.message
            );
            goto cleanup_anchor;
        }
    }
    v4_hb_builder_destroy(attack_builder);
    attack_builder = NULL;

    code = v4_hb_builder_start(&config, &attack_builder, &error);
    if (code != V4_HB_OK) {
        if (code == V4_HB_UNSUPPORTED) {
            status = test_skip(error.message);
        } else {
            (void)test_fail("cannot start unexpected-stop builder");
        }
        goto cleanup_anchor;
    }
    code = hold_and_prewalk(
        attack_builder, &config, &held, &held_failure_phase, &error
    );
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish unexpected-stop boundary",
            held_failure_phase, code, attack_builder, &error
        );
        goto cleanup_anchor;
    }
    code = run_setup_prefix(
        attack_builder, &config, &setup, &setup_snapshot,
        &setup_failure_phase, &error
    );
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish unexpected-stop setup boundary",
            setup_failure_phase, code, attack_builder, &error
        );
        goto cleanup_anchor;
    }
    if (syscall(SYS_pidfd_send_signal, held.pidfd, SIGUSR1, NULL, 0) != 0 ||
        v4_hb_builder_release_and_reap(
            attack_builder, &completion, &error
        ) != V4_HB_ERROR ||
        v4_hb_builder_abort(attack_builder, &error) != V4_HB_OK) {
        (void)test_fail("unexpected signal-delivery stop did not fail closed");
        goto cleanup_anchor;
    }
    v4_hb_builder_destroy(attack_builder);
    attack_builder = NULL;

    code = v4_hb_builder_start(&config, &exit_builder, &error);
    if (code != V4_HB_OK) {
        if (code == V4_HB_UNSUPPORTED) {
            status = test_skip(error.message);
        } else {
            (void)test_fail("cannot start unexpected-exit builder");
        }
        goto cleanup_anchor;
    }
    code = hold_and_prewalk(
        exit_builder, &config, &held, &held_failure_phase, &error
    );
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish unexpected-exit boundary",
            held_failure_phase, code, exit_builder, &error
        );
        goto cleanup_anchor;
    }
    code = run_setup_prefix(
        exit_builder, &config, &setup, &setup_snapshot,
        &setup_failure_phase, &error
    );
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish unexpected-exit setup boundary",
            setup_failure_phase, code, exit_builder, &error
        );
        goto cleanup_anchor;
    }
    if (syscall(SYS_pidfd_send_signal, held.pidfd, SIGKILL, NULL, 0) != 0 ||
        v4_hb_builder_release_and_reap(
            exit_builder, &completion, &error
        ) != V4_HB_ERROR ||
        v4_hb_builder_abort(exit_builder, &error) != V4_HB_OK) {
        (void)test_fail("unexpected builder exit did not fail closed");
        goto cleanup_anchor;
    }
    v4_hb_builder_destroy(exit_builder);
    exit_builder = NULL;

    held_failure_phase = "pidfd-substitution builder start";
    code = v4_hb_builder_start(&config, &alias_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            alias_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish pidfd-substitution boundary",
            held_failure_phase, code, alias_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        int replacement;
        int primary = held.pidfd;

        if (close(primary) != 0) {
            (void)test_fail("cannot close primary pidfd for attack");
            goto cleanup_anchor;
        }
        replacement = (int)syscall(SYS_pidfd_open, held.pid, 0U);
        if (replacement < 0) {
            (void)test_fail("cannot reopen pidfd for substitution attack");
            goto cleanup_anchor;
        }
        if (replacement != primary &&
            (dup3(replacement, primary, O_CLOEXEC) < 0 ||
             close(replacement) != 0)) {
            (void)test_fail("cannot force pidfd-number reuse attack");
            goto cleanup_anchor;
        }
        code = v4_hb_builder_verify_held(alias_builder, &held, &error);
        if (code != V4_HB_ERROR) {
            (void)fprintf(
                stderr, "FAIL: pidfd substitution verify=%d: %s\n",
                code, error.message
            );
            goto cleanup_anchor;
        }
        code = v4_hb_builder_abort(alias_builder, &error);
        if (code != V4_HB_OK) {
            (void)fprintf(
                stderr, "FAIL: pidfd substitution abort=%d: %s\n",
                code, error.message
            );
            goto cleanup_anchor;
        }
    }
    v4_hb_builder_destroy(alias_builder);
    alias_builder = NULL;

    held_failure_phase = "namespace-OFD builder start";
    code = v4_hb_builder_start(&config, &alias_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            alias_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish namespace-OFD boundary",
            held_failure_phase, code, alias_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        char path[64];
        int replacement;
        int primary = held.child_namespaces[0].descriptor;

        int count = snprintf(
            path, sizeof(path), "/proc/%ld/ns/user", (long)held.pid
        );

        if (count < 0 || (size_t)count >= sizeof(path)) {
            (void)test_fail("namespace-OFD substitution path exceeds cap");
            goto cleanup_anchor;
        }
        if (close(primary) != 0) {
            (void)fprintf(
                stderr, "FAIL: cannot close namespace primary: errno=%d\n",
                errno
            );
            goto cleanup_anchor;
        }
        replacement = open(path, O_RDONLY | O_CLOEXEC);
        if (replacement < 0) {
            (void)fprintf(
                stderr, "FAIL: cannot reopen child user namespace: errno=%d\n",
                errno
            );
            goto cleanup_anchor;
        }
        if (replacement != primary &&
            dup3(replacement, primary, O_CLOEXEC) < 0) {
            (void)fprintf(
                stderr, "FAIL: cannot reuse namespace descriptor: errno=%d\n",
                errno
            );
            goto cleanup_anchor;
        }
        if (replacement != primary && close(replacement) != 0) {
            (void)fprintf(
                stderr, "FAIL: cannot close replacement namespace: errno=%d\n",
                errno
            );
            goto cleanup_anchor;
        }
        {
            struct v4_hb_error rejection;
            struct v4_hb_snapshot rejected_snapshot;
            int snapshot_code;
            int abort_code;

            code = v4_hb_builder_verify_held(alias_builder, &held, &error);
            rejection = error;
            snapshot_code = v4_hb_builder_snapshot(
                alias_builder, &rejected_snapshot, &error
            );
            abort_code = v4_hb_builder_abort(alias_builder, &error);
            if (code != V4_HB_ERROR || snapshot_code != V4_HB_OK ||
                rejected_snapshot.state != V4_HB_BOUND_ROOT_WALKS_COMPLETE ||
                abort_code != V4_HB_OK) {
                (void)fprintf(
                    stderr,
                    "FAIL: namespace-OFD substitution verify=%d errno=%d "
                    "snapshot=%d state=%d abort=%d message=%s/%s\n",
                    code, rejection.saved_errno, snapshot_code,
                    snapshot_code == V4_HB_OK ?
                        (int)rejected_snapshot.state : -1,
                    abort_code, rejection.message, error.message
                );
                goto cleanup_anchor;
            }
        }
    }
    v4_hb_builder_destroy(alias_builder);
    alias_builder = NULL;

    held_failure_phase = "namespace-splice builder start";
    code = v4_hb_builder_start(&config, &alias_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            alias_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish namespace-splice boundary",
            held_failure_phase, code, alias_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        int child_descriptor = held.child_namespaces[0].descriptor;
        int parent_descriptor = held.parent_namespaces[0].descriptor;

        if (dup3(parent_descriptor, child_descriptor, O_CLOEXEC) < 0 ||
            v4_hb_builder_verify_held(
                alias_builder, &held, &error
            ) != V4_HB_ERROR ||
            v4_hb_builder_abort(alias_builder, &error) != V4_HB_OK) {
            (void)test_fail("parent/child namespace splice did not fail closed");
            goto cleanup_anchor;
        }
    }
    v4_hb_builder_destroy(alias_builder);
    alias_builder = NULL;

    held_failure_phase = "root-anchor reuse builder start";
    code = v4_hb_builder_start(&config, &alias_builder, &error);
    if (code == V4_HB_OK) {
        code = hold_and_prewalk(
            alias_builder, &config, &held, &held_failure_phase, &error
        );
    }
    if (code != V4_HB_OK) {
        (void)test_v4_diagnostic_failure(
            "cannot establish root-anchor reuse boundary",
            held_failure_phase, code, alias_builder, &error
        );
        goto cleanup_anchor;
    }
    {
        int primary = config.output_root.primary.fd;
        int guard = config.output_root.guard.fd;
        int replacement;

        if (close(primary) != 0 || close(guard) != 0) {
            (void)test_fail("cannot close parent output anchor pair for attack");
            goto cleanup_anchor;
        }
        replacement = open(
            output_path, O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC
        );
        if (replacement < 0 ||
            (replacement != primary &&
             (dup3(replacement, primary, O_CLOEXEC) < 0 ||
              close(replacement) != 0)) ||
            dup3(primary, guard, O_CLOEXEC) < 0) {
            (void)test_fail("cannot force parent root-fd number reuse");
            goto cleanup_anchor;
        }
        code = v4_hb_builder_verify_held(alias_builder, &held, &error);
        {
            char verify_message[sizeof(error.message)];
            int abort_code;

            (void)snprintf(
                verify_message, sizeof(verify_message), "%s", error.message
            );
            abort_code = v4_hb_builder_abort(alias_builder, &error);
            if (code != V4_HB_ERROR ||
                strcmp(
                    verify_message,
                    "child root fd does not share the inherited OFD"
                ) != 0 ||
                abort_code != V4_HB_OK) {
                (void)fprintf(
                    stderr,
                    "FAIL: parent root-fd reuse verify=%d abort=%d: %s / %s\n",
                    code, abort_code, verify_message, error.message
                );
                goto cleanup_anchor;
            }
        }
    }
    v4_hb_builder_destroy(alias_builder);
    alias_builder = NULL;

#ifdef V4_HB_TEST_PROC_NLINK_CHURN
    if (test_proc_root_observation_count < 2U) {
        (void)test_fail("proc-root link-count hostility was not exercised");
        goto cleanup_anchor;
    }
#endif
    status = 0;
    (void)fprintf(stdout, "PASS: native V4 held-builder boundary\n");

cleanup_anchor:
    if (wrong_output_builder != NULL) {
        (void)v4_hb_builder_abort(wrong_output_builder, &error);
        v4_hb_builder_destroy(wrong_output_builder);
    }
    if (nonempty_builder != NULL) {
        (void)v4_hb_builder_abort(nonempty_builder, &error);
        v4_hb_builder_destroy(nonempty_builder);
    }
    if (alias_builder != NULL) {
        (void)v4_hb_builder_abort(alias_builder, &error);
        v4_hb_builder_destroy(alias_builder);
    }
    if (exit_builder != NULL) {
        (void)v4_hb_builder_abort(exit_builder, &error);
        v4_hb_builder_destroy(exit_builder);
    }
    if (attack_builder != NULL) {
        (void)v4_hb_builder_abort(attack_builder, &error);
        v4_hb_builder_destroy(attack_builder);
    }
    if (builder != NULL) {
        (void)v4_hb_builder_abort(builder, &error);
        v4_hb_builder_destroy(builder);
    }
    v4_orw_output_anchor_close(&same_mount_anchor);
    v4_orw_output_anchor_close(&wrong_output_anchor);
    v4_orw_output_anchor_close(&output_alias_anchor);
    v4_orw_output_anchor_close(&regular_input_anchor);
    v4_orw_output_anchor_close(&symlink_input_anchor);
    v4_orw_output_anchor_close(&missing_input_anchor);
    v4_orw_output_anchor_close(&output_anchor);
    v4_orw_output_anchor_close(&input_anchor);
cleanup:
    if (input_fd >= 0) {
        (void)close(input_fd);
    }
    if (root_fd >= 0) {
        (void)close(root_fd);
    }
    if (nested_attack_mounted) {
        (void)umount2(nested_attack_path, MNT_DETACH);
    }
    if (output_alias_mounted) {
        (void)umount2(output_alias_path, MNT_DETACH);
    }
    if (output_mounted) {
        (void)umount2(output_path, MNT_DETACH);
    }
    if (input_mounted) {
        (void)umount2(input_path, MNT_DETACH);
    }
    if (wrong_output_mounted) {
        (void)umount2(wrong_output_path, MNT_DETACH);
    }
    if (missing_input_mounted) {
        (void)umount2(missing_input_path, MNT_DETACH);
    }
    if (symlink_input_mounted) {
        (void)umount2(symlink_input_path, MNT_DETACH);
    }
    if (regular_input_mounted) {
        (void)umount2(regular_input_path, MNT_DETACH);
    }
    if (input_path[0] != '\0') {
        (void)rmdir(input_path);
    }
    if (wrong_output_path[0] != '\0') {
        (void)rmdir(wrong_output_path);
    }
    if (missing_input_path[0] != '\0') {
        (void)rmdir(missing_input_path);
    }
    if (symlink_input_path[0] != '\0') {
        (void)rmdir(symlink_input_path);
    }
    if (regular_input_path[0] != '\0') {
        (void)rmdir(regular_input_path);
    }
    if (output_alias_path[0] != '\0') {
        (void)rmdir(output_alias_path);
    }
    (void)rmdir(temporary);
    return status;
}
