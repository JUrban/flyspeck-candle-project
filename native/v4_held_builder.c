#define _GNU_SOURCE

#include "v4_held_builder.h"

#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/kcmp.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <poll.h>
#include <sched.h>
#include <signal.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/ptrace.h>
#include <sys/syscall.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/uio.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef SYS_pidfd_open
#error "SYS_pidfd_open is required"
#endif
#ifndef SYS_pidfd_send_signal
#error "SYS_pidfd_send_signal is required"
#endif
#ifndef SYS_kcmp
#error "SYS_kcmp is required"
#endif
#if !defined(__x86_64__)
#error "the fixed V4 held-builder slice requires Linux x86-64"
#endif

#define V4_HB_PROC_STAT_MAX_BYTES 4096U
#define V4_HB_PROC_STATUS_MAX_BYTES 16384U
#define V4_HB_PROC_MAP_MAX_BYTES 4096U
#define V4_HB_ABORT_WAIT_LIMIT 16U
#define V4_HB_WAIT_ATTEMPT_LIMIT 5000U
#define V4_HB_WAIT_POLL_MILLISECONDS 1
#define V4_HB_PTRACE_GET_SYSCALL_INFO 0x420e
#define V4_HB_PTRACE_SYSCALL_INFO_NONE 0U
#define V4_HB_ROOT_STATUS_FLAGS 0x00230000U
#define V4_HB_ROOT_FDINFO_FLAGS 0x002b0000U

_Static_assert(ATOMIC_INT_LOCK_FREE == 2,
               "the inherited four-byte userspace gate must be lock-free");
_Static_assert(sizeof(unsigned int) == 4,
               "the inherited userspace gate must be four bytes");
_Static_assert(PTRACE_O_TRACESYSGOOD == 0x00000001,
               "unexpected PTRACE_O_TRACESYSGOOD value");
_Static_assert(PTRACE_O_TRACEFORK == 0x00000002,
               "unexpected PTRACE_O_TRACEFORK value");
_Static_assert(PTRACE_O_TRACEVFORK == 0x00000004,
               "unexpected PTRACE_O_TRACEVFORK value");
_Static_assert(PTRACE_O_TRACECLONE == 0x00000008,
               "unexpected PTRACE_O_TRACECLONE value");
_Static_assert(PTRACE_O_TRACEEXEC == 0x00000010,
               "unexpected PTRACE_O_TRACEEXEC value");
_Static_assert(PTRACE_O_TRACEVFORKDONE == 0x00000020,
               "unexpected PTRACE_O_TRACEVFORKDONE value");
_Static_assert(PTRACE_O_TRACEEXIT == 0x00000040,
               "unexpected PTRACE_O_TRACEEXIT value");
_Static_assert(PTRACE_O_EXITKILL == 0x00100000,
               "unexpected PTRACE_O_EXITKILL value");
_Static_assert(AUDIT_ARCH_X86_64 == 0xc000003eU,
               "unexpected Linux x86-64 audit architecture");
_Static_assert((O_PATH | O_DIRECTORY | O_NOFOLLOW) ==
                   V4_HB_ROOT_STATUS_FLAGS,
               "unexpected root-anchor status flags");
_Static_assert((O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC) ==
                   V4_HB_ROOT_FDINFO_FLAGS,
               "unexpected root-anchor fdinfo flags");
_Static_assert(CLONE_NEWNS == 0x00020000,
               "unexpected CLONE_NEWNS value");
_Static_assert(CLONE_NEWIPC == 0x08000000,
               "unexpected CLONE_NEWIPC value");
_Static_assert(CLONE_NEWUSER == 0x10000000,
               "unexpected CLONE_NEWUSER value");
_Static_assert(CLONE_NEWPID == 0x20000000,
               "unexpected CLONE_NEWPID value");
_Static_assert(CLONE_NEWNET == 0x40000000,
               "unexpected CLONE_NEWNET value");
_Static_assert(
    (CLONE_NEWNS | CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET |
     CLONE_NEWIPC | SIGCHLD) == V4_HB_FIXED_CLONE_FLAGS,
    "fixed V4 five-namespace clone flags drifted"
);
_Static_assert(
    (PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK |
     PTRACE_O_TRACECLONE | PTRACE_O_TRACEVFORKDONE | PTRACE_O_TRACEEXEC |
     PTRACE_O_TRACEEXIT | PTRACE_O_EXITKILL) ==
        V4_HB_FIXED_PTRACE_OPTIONS_MASK,
    "fixed V4 ptrace option mask drifted"
);

struct v4_hb_builder {
    pid_t pid;
    uint64_t start_ticks;
    int pidfd;
    int pidfd_guard;
    int pidfd_status_flags;
    _Atomic unsigned int *gate;
    size_t gate_mapping_bytes;
    enum v4_hb_state state;
    int raw_interrupt_wait_status;
    siginfo_t interrupt_siginfo;
    uint32_t seize_count;
    uint32_t interrupt_count;
    uint32_t interrupt_event_stop_count;
    uint32_t resume_count;
    uint32_t held_stop_consumed;
    int proc_root_fd;
    int proc_root_guard;
    int proc_root_status_flags;
    uid_t observer_effective_uid;
    gid_t observer_effective_gid;
    bool observer_setgroups_denied;
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
    int parent_namespace_guards[V4_HB_NAMESPACE_COUNT];
    int child_namespace_guards[V4_HB_NAMESPACE_COUNT];
    struct v4_hb_root_anchor_config root_config;
    bool root_inheritance_verified;
};

struct v4_hb_namespace_specification {
    const char *name;
    unsigned long clone_flag;
};

static const struct v4_hb_namespace_specification
v4_hb_namespace_specifications[V4_HB_NAMESPACE_COUNT] = {
    {"user", CLONE_NEWUSER},
    {"mnt", CLONE_NEWNS},
    {"pid", CLONE_NEWPID},
    {"net", CLONE_NEWNET},
    {"ipc", CLONE_NEWIPC},
};

struct v4_hb_ptrace_syscall_base {
    uint8_t operation;
    uint8_t padding[3];
    uint32_t architecture;
    uint64_t instruction_pointer;
    uint64_t stack_pointer;
};

static int
v4_hb_fail(
    struct v4_hb_error *error,
    int result,
    int saved_errno,
    const char *format,
    ...
)
{
    va_list arguments;

    if (error != NULL) {
        error->saved_errno = saved_errno;
        va_start(arguments, format);
        (void)vsnprintf(error->message, sizeof(error->message), format,
                        arguments);
        va_end(arguments);
    }
    return result;
}

void
v4_hb_error_clear(struct v4_hb_error *error)
{
    if (error != NULL) {
        error->saved_errno = 0;
        error->message[0] = '\0';
    }
}

static bool
v4_hb_unsupported_observation_errno(int saved_errno)
{
    return saved_errno == ENOSYS || saved_errno == EINVAL ||
        saved_errno == ENOENT || saved_errno == ENOTTY ||
        saved_errno == EPERM || saved_errno == EACCES;
}

static int
v4_hb_verify_same_ofd(
    int primary,
    int guard,
    const char *label,
    struct v4_hb_error *error
)
{
    struct stat primary_status;
    struct stat guard_status;
    int primary_descriptor_flags;
    int guard_descriptor_flags;
    int primary_status_flags;
    int guard_status_flags;
    long comparison;

    if (primary < 0 || guard < 0 || primary == guard) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "%s descriptor pair is malformed", label);
    }
    primary_descriptor_flags = fcntl(primary, F_GETFD);
    if (primary_descriptor_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "%s primary F_GETFD failed", label);
    }
    guard_descriptor_flags = fcntl(guard, F_GETFD);
    if (guard_descriptor_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "%s guard F_GETFD failed", label);
    }
    primary_status_flags = fcntl(primary, F_GETFL);
    if (primary_status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "%s primary F_GETFL failed", label);
    }
    guard_status_flags = fcntl(guard, F_GETFL);
    if (guard_status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "%s guard F_GETFL failed", label);
    }
    if (fstat(primary, &primary_status) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "%s primary fstat failed", label);
    }
    if (fstat(guard, &guard_status) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "%s guard fstat failed", label);
    }
    if (primary_descriptor_flags != FD_CLOEXEC ||
        guard_descriptor_flags != FD_CLOEXEC ||
        primary_status_flags != guard_status_flags ||
        primary_status.st_dev != guard_status.st_dev ||
        primary_status.st_ino != guard_status.st_ino ||
        primary_status.st_mode != guard_status.st_mode ||
        primary_status.st_nlink != guard_status.st_nlink) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "%s guarded projection changed", label);
    }
    comparison = syscall(
        SYS_kcmp, getpid(), getpid(), KCMP_FILE,
        (unsigned long)primary, (unsigned long)guard
    );
    if (comparison == 0) {
        return V4_HB_OK;
    }
    if (comparison < 0 &&
        (errno == ENOSYS || errno == EPERM || errno == EACCES)) {
        return v4_hb_fail(error, V4_HB_UNSUPPORTED, errno,
                          "KCMP_FILE cannot verify %s alias", label);
    }
    return v4_hb_fail(
        error, V4_HB_ERROR, comparison < 0 ? errno : EINVAL,
        "%s descriptor no longer names its guarded OFD", label
    );
}

static int
v4_hb_read_bounded_proc_at(
    const struct v4_hb_builder *builder,
    const char *relative_path,
    char *buffer,
    size_t capacity,
    size_t *used,
    struct v4_hb_error *error
)
{
    size_t offset = 0;
    int fd;

    if (builder == NULL || builder->proc_root_fd < 0 ||
        relative_path == NULL || relative_path[0] == '/' ||
        buffer == NULL || capacity == 0 || used == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed descriptor-rooted proc read");
    }
    do {
        fd = openat(builder->proc_root_fd, relative_path,
                    O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    } while (fd < 0 && errno == EINTR);
    if (fd < 0) {
        int saved_errno = errno;
        return v4_hb_fail(error, V4_HB_ERROR, saved_errno,
                          "descriptor-rooted proc read open failed");
    }
    for (;;) {
        ssize_t count = read(fd, buffer + offset, capacity - offset);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            int saved_errno = errno;
            (void)close(fd);
            return v4_hb_fail(error, V4_HB_ERROR, saved_errno,
                              "descriptor-rooted proc read failed");
        }
        if (count == 0) {
            break;
        }
        offset += (size_t)count;
        if (offset == capacity) {
            char extra;
            ssize_t extra_count;
            do {
                extra_count = read(fd, &extra, 1);
            } while (extra_count < 0 && errno == EINTR);
            if (extra_count < 0) {
                int saved_errno = errno;
                (void)close(fd);
                return v4_hb_fail(
                    error, V4_HB_ERROR, saved_errno,
                    "descriptor-rooted proc cap probe failed"
                );
            }
            if (extra_count != 0) {
                (void)close(fd);
                return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                                  "descriptor-rooted proc read exceeds cap");
            }
            break;
        }
    }
    if (close(fd) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "descriptor-rooted proc read close failed");
    }
    *used = offset;
    return V4_HB_OK;
}

static int
v4_hb_capture_proc_root(
    struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    struct statfs filesystem;
    int descriptor_flags;

    do {
        builder->proc_root_fd = open(
            "/proc", O_PATH | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW
        );
    } while (builder->proc_root_fd < 0 && errno == EINTR);
    if (builder->proc_root_fd < 0) {
        int saved_errno = errno;
        return v4_hb_fail(
            error,
            v4_hb_unsupported_observation_errno(saved_errno) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno, "cannot retain the proc root descriptor"
        );
    }
    descriptor_flags = fcntl(builder->proc_root_fd, F_GETFD);
    if (descriptor_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "proc root F_GETFD failed");
    }
    builder->proc_root_status_flags = fcntl(builder->proc_root_fd, F_GETFL);
    if (builder->proc_root_status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "proc root F_GETFL failed");
    }
    if (descriptor_flags != FD_CLOEXEC ||
        (builder->proc_root_status_flags & O_PATH) != O_PATH) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "proc root fcntl projection is malformed");
    }
    if (fstatfs(builder->proc_root_fd, &filesystem) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "proc root fstatfs failed");
    }
    if ((unsigned long)filesystem.f_type != (unsigned long)PROC_SUPER_MAGIC) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "retained proc root is not procfs");
    }
    builder->proc_root_guard = fcntl(
        builder->proc_root_fd, F_DUPFD_CLOEXEC, 3
    );
    if (builder->proc_root_guard < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "cannot retain proc root guard alias");
    }
    return v4_hb_verify_same_ofd(
        builder->proc_root_fd, builder->proc_root_guard, "proc root", error
    );
}

static int
v4_hb_parse_decimal_u64(
    const char *begin,
    const char *end,
    uint64_t *value
)
{
    uint64_t result = 0;
    const char *cursor;

    if (begin == NULL || end == NULL || begin >= end) {
        return -1;
    }
    for (cursor = begin; cursor < end; ++cursor) {
        unsigned int digit;
        if (*cursor < '0' || *cursor > '9') {
            return -1;
        }
        digit = (unsigned int)(*cursor - '0');
        if (result > (UINT64_MAX - digit) / 10U) {
            return -1;
        }
        result = result * 10U + digit;
    }
    *value = result;
    return 0;
}

static bool
v4_hb_same_root_projection(
    const struct v4_orw_kernel_projection *first,
    const struct v4_orw_kernel_projection *second
)
{
    return first->st_dev == second->st_dev &&
        first->st_ino == second->st_ino &&
        first->st_nlink == second->st_nlink &&
        first->st_mode == second->st_mode &&
        first->st_size == second->st_size &&
        first->mtime_seconds == second->mtime_seconds &&
        first->mtime_nanoseconds == second->mtime_nanoseconds &&
        first->ctime_seconds == second->ctime_seconds &&
        first->ctime_nanoseconds == second->ctime_nanoseconds &&
        first->statx_dev_major == second->statx_dev_major &&
        first->statx_dev_minor == second->statx_dev_minor &&
        first->mount_id == second->mount_id &&
        first->fd_flags == second->fd_flags &&
        first->status_flags == second->status_flags &&
        first->fdinfo.position == second->fdinfo.position &&
        first->fdinfo.flags == second->fdinfo.flags &&
        first->fdinfo.mount_id == second->fdinfo.mount_id &&
        first->fdinfo.inode == second->fdinfo.inode;
}

static bool
v4_hb_same_logical_descriptor(
    const struct v4_orw_logical_descriptor *first,
    const struct v4_orw_logical_descriptor *second
)
{
    return first->fd == second->fd &&
        first->fd_generation == second->fd_generation &&
        first->logical_ofd_id == second->logical_ofd_id &&
        first->logical_ofd_generation == second->logical_ofd_generation;
}

static bool
v4_hb_same_root_anchor(
    const struct v4_orw_output_anchor *first,
    const struct v4_orw_output_anchor *second
)
{
    return first->live == second->live &&
        v4_hb_same_logical_descriptor(&first->primary, &second->primary) &&
        v4_hb_same_logical_descriptor(&first->guard, &second->guard) &&
        v4_hb_same_root_projection(
            &first->initial_projection, &second->initial_projection
        ) && v4_hb_same_root_projection(
            &first->guard_initial_projection,
            &second->guard_initial_projection
        );
}

static int
v4_hb_translate_root_result(
    int result,
    bool unsupported_allowed,
    const struct v4_orw_error *root_error,
    const char *message,
    struct v4_hb_error *error
)
{
    int code = result == V4_ORW_UNSUPPORTED && unsupported_allowed ?
        V4_HB_UNSUPPORTED : V4_HB_ERROR;
    return v4_hb_fail(
        error, code, root_error->saved_errno,
        "%s: %s", message, root_error->message
    );
}

static bool
v4_hb_exact_anchor_flags(const struct v4_orw_kernel_projection *projection)
{
    return projection->fd_flags == FD_CLOEXEC &&
        projection->status_flags == V4_HB_ROOT_STATUS_FLAGS &&
        projection->fdinfo.position == 0U &&
        projection->fdinfo.flags == V4_HB_ROOT_FDINFO_FLAGS &&
        projection->fdinfo.mount_id == projection->mount_id &&
        projection->fdinfo.inode == projection->st_ino &&
        S_ISDIR((mode_t)projection->st_mode);
}

static int
v4_hb_validate_root_config(
    const struct v4_hb_root_anchor_config *config,
    bool unsupported_allowed,
    struct v4_hb_error *error
)
{
    const struct v4_orw_output_anchor *input;
    const struct v4_orw_output_anchor *output;
    struct v4_orw_kernel_projection current;
    struct v4_orw_error root_error;
    struct statvfs input_filesystem;
    struct statvfs output_filesystem;
    const int *fds[4];
    const uint64_t *fd_generations[4];
    uint64_t maximum_fd_generation;
    uint32_t first;
    uint32_t second;
    int result;

    if (config == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "root-anchor config is null");
    }
    input = &config->input_root;
    output = &config->output_root;
    if (input->live != 1 || output->live != 1 ||
        input->primary.fd < 0 || input->guard.fd < 0 ||
        output->primary.fd < 0 || output->guard.fd < 0 ||
        input->primary.fd_generation == 0 ||
        input->guard.fd_generation == 0 ||
        output->primary.fd_generation == 0 ||
        output->guard.fd_generation == 0 ||
        input->primary.logical_ofd_id == 0 ||
        output->primary.logical_ofd_id == 0 ||
        input->primary.logical_ofd_generation == 0 ||
        output->primary.logical_ofd_generation == 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "root-anchor config has malformed logical state");
    }
    fds[0] = &input->primary.fd;
    fds[1] = &input->guard.fd;
    fds[2] = &output->primary.fd;
    fds[3] = &output->guard.fd;
    fd_generations[0] = &input->primary.fd_generation;
    fd_generations[1] = &input->guard.fd_generation;
    fd_generations[2] = &output->primary.fd_generation;
    fd_generations[3] = &output->guard.fd_generation;
    for (first = 0; first < 4U; ++first) {
        for (second = first + 1U; second < 4U; ++second) {
            if (*fds[first] == *fds[second] ||
                *fd_generations[first] == *fd_generations[second]) {
                return v4_hb_fail(
                    error, V4_HB_ERROR, EINVAL,
                    "root descriptors/generations are not pairwise distinct"
                );
            }
        }
    }
    if (input->primary.logical_ofd_id != input->guard.logical_ofd_id ||
        output->primary.logical_ofd_id != output->guard.logical_ofd_id ||
        input->primary.logical_ofd_generation !=
            input->guard.logical_ofd_generation ||
        output->primary.logical_ofd_generation !=
            output->guard.logical_ofd_generation ||
        input->primary.logical_ofd_id == output->primary.logical_ofd_id ||
        input->primary.logical_ofd_generation ==
            output->primary.logical_ofd_generation) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "root anchors lack distinct logical OFDs");
    }
    if (!v4_hb_exact_anchor_flags(&input->initial_projection) ||
        !v4_hb_exact_anchor_flags(&input->guard_initial_projection) ||
        !v4_hb_exact_anchor_flags(&output->initial_projection) ||
        !v4_hb_exact_anchor_flags(&output->guard_initial_projection) ||
        !v4_hb_same_root_projection(
            &input->initial_projection, &input->guard_initial_projection
        ) || !v4_hb_same_root_projection(
            &output->initial_projection, &output->guard_initial_projection
        )) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "root anchors lack exact O_PATH directory form");
    }
    if (input->initial_projection.st_dev ==
            output->initial_projection.st_dev &&
        input->initial_projection.st_ino ==
            output->initial_projection.st_ino) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "input and output root objects are not distinct");
    }
    if (input->initial_projection.mount_id ==
            output->initial_projection.mount_id) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "output root is not a separate nested mount");
    }
    if (fstatvfs(input->primary.fd, &input_filesystem) != 0 ||
        fstatvfs(output->primary.fd, &output_filesystem) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "root mount access projection failed");
    }
    if ((input_filesystem.f_flag & ST_RDONLY) == 0U ||
        (output_filesystem.f_flag & ST_RDONLY) != 0U) {
        return v4_hb_fail(error, V4_HB_ERROR, EROFS,
                          "input/output root mount access is not closed");
    }
    maximum_fd_generation = input->primary.fd_generation;
#define V4_HB_TAKE_MAX_FD_GENERATION(descriptor) \
    do { \
        if ((descriptor).fd_generation > maximum_fd_generation) { \
            maximum_fd_generation = (descriptor).fd_generation; \
        } \
    } while (0)
    V4_HB_TAKE_MAX_FD_GENERATION(input->guard);
    V4_HB_TAKE_MAX_FD_GENERATION(output->primary);
    V4_HB_TAKE_MAX_FD_GENERATION(output->guard);
#undef V4_HB_TAKE_MAX_FD_GENERATION
    if (config->logical_ledger.next_fd_generation == 0 ||
        config->logical_ledger.next_ofd_id == 0 ||
        config->logical_ledger.next_ofd_generation == 0 ||
        config->logical_ledger.next_fd_generation <= maximum_fd_generation ||
        config->logical_ledger.next_ofd_id <=
            input->primary.logical_ofd_id ||
        config->logical_ledger.next_ofd_id <=
            output->primary.logical_ofd_id ||
        config->logical_ledger.next_ofd_generation <=
            input->primary.logical_ofd_generation ||
        config->logical_ledger.next_ofd_generation <=
            output->primary.logical_ofd_generation) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "root-anchor logical ledger is not a successor");
    }
    result = v4_orw_output_anchor_revalidate(input, &root_error);
    if (result != V4_ORW_OK) {
        return v4_hb_translate_root_result(
            result, unsupported_allowed, &root_error,
            "input root revalidation failed", error
        );
    }
    result = v4_orw_output_anchor_snapshot(input, &current, &root_error);
    if (result != V4_ORW_OK) {
        return v4_hb_translate_root_result(
            result, unsupported_allowed, &root_error,
            "input root snapshot failed", error
        );
    }
    if (!v4_hb_same_root_projection(&current, &input->initial_projection)) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "input root full projection changed");
    }
    result = v4_orw_output_anchor_revalidate(output, &root_error);
    if (result != V4_ORW_OK) {
        return v4_hb_translate_root_result(
            result, unsupported_allowed, &root_error,
            "output root revalidation failed", error
        );
    }
    result = v4_orw_output_anchor_snapshot(output, &current, &root_error);
    if (result != V4_ORW_OK) {
        return v4_hb_translate_root_result(
            result, unsupported_allowed, &root_error,
            "output root snapshot failed", error
        );
    }
    if (!v4_hb_same_root_projection(&current, &output->initial_projection)) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "output root full projection changed");
    }
    return V4_HB_OK;
}

static int
v4_hb_verify_root_descriptor_disjointness(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    const int root_fds[4] = {
        builder->root_config.input_root.primary.fd,
        builder->root_config.input_root.guard.fd,
        builder->root_config.output_root.primary.fd,
        builder->root_config.output_root.guard.fd,
    };
    uint32_t root_index;
    uint32_t namespace_index;

    for (root_index = 0; root_index < 4U; ++root_index) {
        int root_fd = root_fds[root_index];

        if (root_fd < 0 || root_fd == builder->pidfd ||
            root_fd == builder->pidfd_guard ||
            root_fd == builder->proc_root_fd ||
            root_fd == builder->proc_root_guard) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "root descriptor overlaps retained control fd");
        }
        for (namespace_index = 0;
             namespace_index < V4_HB_NAMESPACE_COUNT;
             ++namespace_index) {
            if (root_fd ==
                    builder->parent_namespaces[namespace_index].descriptor ||
                root_fd == builder->parent_namespace_guards[namespace_index] ||
                root_fd ==
                    builder->child_namespaces[namespace_index].descriptor ||
                root_fd == builder->child_namespace_guards[namespace_index]) {
                return v4_hb_fail(
                    error, V4_HB_ERROR, EINVAL,
                    "root descriptor overlaps retained namespace fd"
                );
            }
        }
    }
    return V4_HB_OK;
}

static int
v4_hb_parse_octal_u64(
    const char *begin,
    const char *end,
    uint64_t *value
)
{
    uint64_t result = 0;
    const char *cursor;

    if (begin == NULL || end == NULL || begin >= end || value == NULL) {
        return -1;
    }
    for (cursor = begin; cursor < end; ++cursor) {
        unsigned int digit;
        if (*cursor < '0' || *cursor > '7') {
            return -1;
        }
        digit = (unsigned int)(*cursor - '0');
        if (result > (UINT64_MAX - digit) / 8U) {
            return -1;
        }
        result = result * 8U + digit;
    }
    *value = result;
    return 0;
}

static int
v4_hb_read_child_fdinfo(
    const struct v4_hb_builder *builder,
    int descriptor,
    bool unsupported_allowed,
    struct v4_orw_fdinfo_projection *projection,
    struct v4_hb_error *error
)
{
    char path[96];
    char buffer[V4_HB_PROC_MAP_MAX_BYTES + 1U];
    char *cursor;
    size_t used;
    bool seen_position = false;
    bool seen_flags = false;
    bool seen_mount_id = false;
    bool seen_inode = false;
    int count;
    int code;

    if (builder == NULL || builder->pid <= 0 || descriptor < 0 ||
        projection == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed child fdinfo request");
    }
    count = snprintf(
        path, sizeof(path), "%ld/fdinfo/%d",
        (long)builder->pid, descriptor
    );
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child fdinfo path exceeds cap");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, V4_HB_PROC_MAP_MAX_BYTES, &used, error
    );
    if (code != V4_HB_OK) {
        if (unsupported_allowed && error != NULL &&
            v4_hb_unsupported_observation_errno(error->saved_errno)) {
            int saved_errno = error->saved_errno;
            return v4_hb_fail(
                error, V4_HB_UNSUPPORTED, saved_errno,
                "child fdinfo observation is unavailable"
            );
        }
        return code;
    }
    buffer[used] = '\0';
    memset(projection, 0, sizeof(*projection));
    cursor = buffer;
    while (*cursor != '\0') {
        char *newline = strchr(cursor, '\n');
        char *separator;
        const char *value;
        uint64_t parsed;
        bool *seen;
        uint64_t *target;

        if (newline == NULL) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "child fdinfo has unterminated line");
        }
        separator = memchr(cursor, ':', (size_t)(newline - cursor));
        if (separator == NULL) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "child fdinfo line is malformed");
        }
        value = separator + 1;
        while (value < newline && (*value == ' ' || *value == '\t')) {
            ++value;
        }
        seen = NULL;
        target = NULL;
        if ((size_t)(separator - cursor) == sizeof("pos") - 1U &&
            memcmp(cursor, "pos", sizeof("pos") - 1U) == 0) {
            seen = &seen_position;
            target = &projection->position;
            code = v4_hb_parse_decimal_u64(value, newline, &parsed);
        } else if ((size_t)(separator - cursor) == sizeof("flags") - 1U &&
                   memcmp(cursor, "flags", sizeof("flags") - 1U) == 0) {
            seen = &seen_flags;
            target = &projection->flags;
            code = v4_hb_parse_octal_u64(value, newline, &parsed);
        } else if ((size_t)(separator - cursor) == sizeof("mnt_id") - 1U &&
                   memcmp(cursor, "mnt_id", sizeof("mnt_id") - 1U) == 0) {
            seen = &seen_mount_id;
            target = &projection->mount_id;
            code = v4_hb_parse_decimal_u64(value, newline, &parsed);
        } else if ((size_t)(separator - cursor) == sizeof("ino") - 1U &&
                   memcmp(cursor, "ino", sizeof("ino") - 1U) == 0) {
            seen = &seen_inode;
            target = &projection->inode;
            code = v4_hb_parse_decimal_u64(value, newline, &parsed);
        } else {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "child fdinfo has unknown field");
        }
        if (code != 0 || *seen) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "child fdinfo field is duplicate or malformed");
        }
        *seen = true;
        *target = parsed;
        cursor = newline + 1;
    }
    if (!seen_position || !seen_flags || !seen_mount_id || !seen_inode) {
        return v4_hb_fail(
            error,
            unsupported_allowed ? V4_HB_UNSUPPORTED : V4_HB_ERROR,
            ENOTSUP,
                          "child fdinfo projection is incomplete");
    }
    return V4_HB_OK;
}

static int
v4_hb_compare_inherited_root_ofd(
    const struct v4_hb_builder *builder,
    int descriptor,
    bool unsupported_allowed,
    struct v4_hb_error *error
)
{
    long comparison = syscall(
        SYS_kcmp, getpid(), builder->pid, KCMP_FILE,
        (unsigned long)descriptor, (unsigned long)descriptor
    );

    if (comparison == 0) {
        return V4_HB_OK;
    }
    if (comparison < 0) {
        int saved_errno = errno;
        return v4_hb_fail(
            error,
            unsupported_allowed &&
                (saved_errno == ENOSYS || saved_errno == EPERM ||
                 saved_errno == EACCES) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno,
            "cross-process KCMP_FILE cannot prove root inheritance"
        );
    }
    return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                      "child root fd does not share the inherited OFD");
}

static int
v4_hb_verify_root_inheritance(
    const struct v4_hb_builder *builder,
    bool unsupported_allowed,
    struct v4_hb_error *error
)
{
    const struct v4_orw_output_anchor *anchors[2] = {
        &builder->root_config.input_root,
        &builder->root_config.output_root,
    };
    uint32_t anchor_index;
    int code;

    code = v4_hb_validate_root_config(
        &builder->root_config, unsupported_allowed, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_verify_root_descriptor_disjointness(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    for (anchor_index = 0; anchor_index < 2U; ++anchor_index) {
        const struct v4_orw_output_anchor *anchor = anchors[anchor_index];
        const struct v4_orw_logical_descriptor *descriptors[2] = {
            &anchor->primary, &anchor->guard,
        };
        const struct v4_orw_kernel_projection *projections[2] = {
            &anchor->initial_projection, &anchor->guard_initial_projection,
        };
        uint32_t descriptor_index;

        for (descriptor_index = 0; descriptor_index < 2U;
             ++descriptor_index) {
            struct v4_orw_fdinfo_projection child_fdinfo;

            code = v4_hb_compare_inherited_root_ofd(
                builder, descriptors[descriptor_index]->fd,
                unsupported_allowed, error
            );
            if (code != V4_HB_OK) {
                return code;
            }
            code = v4_hb_read_child_fdinfo(
                builder, descriptors[descriptor_index]->fd,
                unsupported_allowed,
                &child_fdinfo, error
            );
            if (code != V4_HB_OK) {
                return code;
            }
            if (child_fdinfo.position !=
                    projections[descriptor_index]->fdinfo.position ||
                child_fdinfo.flags !=
                    projections[descriptor_index]->fdinfo.flags ||
                child_fdinfo.mount_id !=
                    projections[descriptor_index]->fdinfo.mount_id ||
                child_fdinfo.inode !=
                    projections[descriptor_index]->fdinfo.inode ||
                child_fdinfo.flags != V4_HB_ROOT_FDINFO_FLAGS) {
                return v4_hb_fail(
                    error, V4_HB_ERROR, EINVAL,
                    "child inherited root fdinfo projection changed"
                );
            }
        }
    }
    return V4_HB_OK;
}

static bool
v4_hb_same_namespace_projection(
    const struct v4_hb_namespace_projection *first,
    const struct v4_hb_namespace_projection *second,
    bool include_descriptor
)
{
    return first->index == second->index &&
        first->clone_flag == second->clone_flag &&
        (!include_descriptor || first->descriptor == second->descriptor) &&
        first->descriptor_flags == second->descriptor_flags &&
        first->status_flags == second->status_flags &&
        first->device == second->device &&
        first->inode == second->inode &&
        first->link_count == second->link_count &&
        first->mode == second->mode &&
        first->filesystem_type == second->filesystem_type &&
        first->namespace_type == second->namespace_type;
}

static int
v4_hb_observe_namespace_descriptor(
    int descriptor,
    uint32_t index,
    unsigned long clone_flag,
    bool unsupported_allowed,
    struct v4_hb_namespace_projection *projection,
    struct v4_hb_error *error
)
{
    struct stat status;
    struct statfs filesystem;
    int descriptor_flags;
    int status_flags;
    int namespace_type;

    if (descriptor < 0 || index >= V4_HB_NAMESPACE_COUNT ||
        projection == NULL ||
        clone_flag != v4_hb_namespace_specifications[index].clone_flag) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed namespace projection request");
    }
    descriptor_flags = fcntl(descriptor, F_GETFD);
    if (descriptor_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "namespace F_GETFD failed");
    }
    status_flags = fcntl(descriptor, F_GETFL);
    if (status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "namespace F_GETFL failed");
    }
    if (fstat(descriptor, &status) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "namespace fstat failed");
    }
    if (fstatfs(descriptor, &filesystem) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "namespace fstatfs failed");
    }
    namespace_type = ioctl(descriptor, NS_GET_NSTYPE);
    if (namespace_type < 0) {
        int saved_errno = errno;
        return v4_hb_fail(
            error,
            unsupported_allowed &&
                v4_hb_unsupported_observation_errno(saved_errno) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno, "NS_GET_NSTYPE is unavailable"
        );
    }
    if (descriptor_flags != FD_CLOEXEC ||
        (status_flags & O_ACCMODE) != O_RDONLY ||
        !S_ISREG(status.st_mode) ||
        (status.st_mode & 07777U) != 0444U || status.st_nlink != 1 ||
        (unsigned long)filesystem.f_type != (unsigned long)NSFS_MAGIC ||
        (unsigned long)namespace_type != clone_flag) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "namespace descriptor projection is not exact");
    }
    memset(projection, 0, sizeof(*projection));
    projection->index = index;
    projection->clone_flag = clone_flag;
    projection->descriptor = descriptor;
    projection->descriptor_flags = descriptor_flags;
    projection->status_flags = status_flags;
    projection->device = (uint64_t)status.st_dev;
    projection->inode = (uint64_t)status.st_ino;
    projection->link_count = (uint64_t)status.st_nlink;
    projection->mode = (uint32_t)status.st_mode;
    projection->filesystem_type = filesystem.f_type;
    projection->namespace_type = namespace_type;
    return V4_HB_OK;
}

static int
v4_hb_namespace_relative_path(
    char *path,
    size_t capacity,
    pid_t pid,
    uint32_t index
)
{
    int count;

    if (path == NULL || capacity == 0 ||
        index >= V4_HB_NAMESPACE_COUNT || pid < 0) {
        return -1;
    }
    if (pid == 0) {
        count = snprintf(
            path, capacity, "self/ns/%s",
            v4_hb_namespace_specifications[index].name
        );
    } else {
        count = snprintf(
            path, capacity, "%ld/ns/%s", (long)pid,
            v4_hb_namespace_specifications[index].name
        );
    }
    return count >= 0 && (size_t)count < capacity ? 0 : -1;
}

static int
v4_hb_capture_namespace_set(
    struct v4_hb_builder *builder,
    pid_t pid,
    struct v4_hb_namespace_projection projections[V4_HB_NAMESPACE_COUNT],
    int guards[V4_HB_NAMESPACE_COUNT],
    struct v4_hb_error *error
)
{
    uint32_t index;

    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        char path[64];
        int descriptor;
        int code;

        if (v4_hb_namespace_relative_path(
                path, sizeof(path), pid, index
            ) != 0) {
            return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                              "namespace proc path exceeds its cap");
        }
        do {
            descriptor = openat(
                builder->proc_root_fd, path, O_RDONLY | O_CLOEXEC
            );
        } while (descriptor < 0 && errno == EINTR);
        if (descriptor < 0) {
            int saved_errno = errno;
            return v4_hb_fail(
                error,
                pid == 0 &&
                    v4_hb_unsupported_observation_errno(saved_errno) ?
                    V4_HB_UNSUPPORTED : V4_HB_ERROR,
                saved_errno, "cannot retain namespace descriptor"
            );
        }
        projections[index].descriptor = descriptor;
        code = v4_hb_observe_namespace_descriptor(
            descriptor, index,
            v4_hb_namespace_specifications[index].clone_flag,
            true,
            &projections[index], error
        );
        if (code != V4_HB_OK) {
            return code;
        }
        guards[index] = fcntl(descriptor, F_DUPFD_CLOEXEC, 3);
        if (guards[index] < 0) {
            return v4_hb_fail(error, V4_HB_ERROR, errno,
                              "cannot retain namespace guard alias");
        }
        code = v4_hb_verify_same_ofd(
            descriptor, guards[index], "namespace", error
        );
        if (code != V4_HB_OK) {
            return code;
        }
    }
    return V4_HB_OK;
}

static int
v4_hb_verify_proc_root(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    struct statfs filesystem;
    int descriptor_flags;
    int status_flags;
    int code;

    if (builder == NULL || builder->proc_root_fd < 0 ||
        builder->proc_root_guard < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "retained proc root state is malformed");
    }
    descriptor_flags = fcntl(builder->proc_root_fd, F_GETFD);
    if (descriptor_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "retained proc root F_GETFD failed");
    }
    status_flags = fcntl(builder->proc_root_fd, F_GETFL);
    if (status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "retained proc root F_GETFL failed");
    }
    if (descriptor_flags != FD_CLOEXEC ||
        status_flags != builder->proc_root_status_flags) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "retained proc root projection changed");
    }
    if (fstatfs(builder->proc_root_fd, &filesystem) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "retained proc root fstatfs failed");
    }
    if ((unsigned long)filesystem.f_type !=
        (unsigned long)PROC_SUPER_MAGIC) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "retained proc root is no longer procfs");
    }
    code = v4_hb_verify_same_ofd(
        builder->proc_root_fd, builder->proc_root_guard, "proc root", error
    );
    return code;
}

static int
v4_hb_verify_namespace_set(
    const struct v4_hb_builder *builder,
    pid_t pid,
    const struct v4_hb_namespace_projection projections[
        V4_HB_NAMESPACE_COUNT
    ],
    const int guards[V4_HB_NAMESPACE_COUNT],
    struct v4_hb_error *error
)
{
    uint32_t index;

    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        struct v4_hb_namespace_projection retained;
        struct v4_hb_namespace_projection current;
        char path[64];
        int current_fd;
        int code;

        code = v4_hb_observe_namespace_descriptor(
            projections[index].descriptor, index,
            v4_hb_namespace_specifications[index].clone_flag,
            false,
            &retained, error
        );
        if (code != V4_HB_OK) {
            return code;
        }
        if (!v4_hb_same_namespace_projection(
                &retained, &projections[index], true
            )) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "retained namespace projection changed");
        }
        code = v4_hb_verify_same_ofd(
            projections[index].descriptor, guards[index],
            "namespace", error
        );
        if (code != V4_HB_OK) {
            return code;
        }
        if (v4_hb_namespace_relative_path(
                path, sizeof(path), pid, index
            ) != 0) {
            return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                              "namespace rejoin path exceeds cap");
        }
        do {
            current_fd = openat(
                builder->proc_root_fd, path, O_RDONLY | O_CLOEXEC
            );
        } while (current_fd < 0 && errno == EINTR);
        if (current_fd < 0) {
            return v4_hb_fail(error, V4_HB_ERROR, errno,
                              "cannot reopen namespace for rejoin");
        }
        code = v4_hb_observe_namespace_descriptor(
            current_fd, index,
            v4_hb_namespace_specifications[index].clone_flag,
            false,
            &current, error
        );
        if (close(current_fd) != 0 && code == V4_HB_OK) {
            code = v4_hb_fail(error, V4_HB_ERROR, errno,
                              "namespace rejoin descriptor close failed");
        }
        if (code != V4_HB_OK) {
            return code;
        }
        if (!v4_hb_same_namespace_projection(
                &current, &projections[index], false
            )) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "live namespace does not match retained one");
        }
    }
    return V4_HB_OK;
}

static int
v4_hb_read_start_ticks(
    const struct v4_hb_builder *builder,
    pid_t pid,
    uint64_t *start_ticks,
    struct v4_hb_error *error
)
{
    char path[64];
    char buffer[V4_HB_PROC_STAT_MAX_BYTES + 1];
    char *right_parenthesis;
    char *cursor;
    size_t used;
    uint64_t parsed_pid;
    unsigned int field;
    int code;

    if (builder == NULL || pid <= 0 || start_ticks == NULL ||
        snprintf(path, sizeof(path), "%ld/stat", (long)pid) < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed proc stat request");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, V4_HB_PROC_STAT_MAX_BYTES, &used, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    buffer[used] = '\0';
    right_parenthesis = strrchr(buffer, ')');
    cursor = strchr(buffer, ' ');
    if (cursor == NULL || right_parenthesis == NULL ||
        cursor + 2 > right_parenthesis ||
        v4_hb_parse_decimal_u64(buffer, cursor, &parsed_pid) != 0 ||
        parsed_pid != (uint64_t)pid || right_parenthesis[1] != ' ' ||
        right_parenthesis[2] == '\0' || right_parenthesis[3] != ' ') {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed proc stat identity");
    }
    cursor = right_parenthesis + 4;
    for (field = 4; field <= 22; ++field) {
        char *end = cursor;
        while (*end != '\0' && *end != ' ' && *end != '\n') {
            ++end;
        }
        if (end == cursor) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "truncated proc stat identity");
        }
        if (field == 22) {
            uint64_t value;
            if (v4_hb_parse_decimal_u64(cursor, end, &value) != 0 ||
                value == 0) {
                return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                                  "malformed proc start ticks");
            }
            *start_ticks = value;
            return V4_HB_OK;
        }
        if (*end != ' ') {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "truncated proc stat fields");
        }
        cursor = end + 1;
    }
    return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                      "missing proc start ticks");
}

static int
v4_hb_write_proc_record(
    struct v4_hb_builder *builder,
    const char *relative_path,
    const char *record,
    size_t length,
    struct v4_hb_error *error
)
{
    int descriptor;
    int descriptor_flags;
    int status_flags;
    ssize_t written;

    if (builder == NULL || builder->proc_root_fd < 0 ||
        relative_path == NULL || relative_path[0] == '/' ||
        record == NULL || length == 0 || length > 128U) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed descriptor-rooted proc write");
    }
    do {
        descriptor = openat(
            builder->proc_root_fd, relative_path,
            O_WRONLY | O_CLOEXEC | O_NOFOLLOW
        );
    } while (descriptor < 0 && errno == EINTR);
    if (descriptor < 0) {
        int saved_errno = errno;
        return v4_hb_fail(
            error,
            v4_hb_unsupported_observation_errno(saved_errno) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno, "descriptor-rooted proc write open failed"
        );
    }
    descriptor_flags = fcntl(descriptor, F_GETFD);
    if (descriptor_flags < 0) {
        int saved_errno = errno;
        (void)close(descriptor);
        return v4_hb_fail(error, V4_HB_ERROR, saved_errno,
                          "proc write F_GETFD failed");
    }
    status_flags = fcntl(descriptor, F_GETFL);
    if (status_flags < 0) {
        int saved_errno = errno;
        (void)close(descriptor);
        return v4_hb_fail(error, V4_HB_ERROR, saved_errno,
                          "proc write F_GETFL failed");
    }
    if (descriptor_flags != FD_CLOEXEC ||
        (status_flags & O_ACCMODE) != O_WRONLY) {
        (void)close(descriptor);
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "proc write fcntl projection is malformed");
    }
    do {
        written = write(descriptor, record, length);
    } while (written < 0 && errno == EINTR);
    if (written < 0) {
        int saved_errno = errno;
        (void)close(descriptor);
        return v4_hb_fail(
            error,
            v4_hb_unsupported_observation_errno(saved_errno) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno, "proc record write failed"
        );
    }
    if ((size_t)written != length) {
        (void)close(descriptor);
        return v4_hb_fail(error, V4_HB_ERROR, EIO,
                          "proc record write was partial");
    }
    if (close(descriptor) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "proc write descriptor close failed");
    }
    return V4_HB_OK;
}

static const char *
v4_hb_skip_horizontal_space(const char *cursor, const char *end)
{
    while (cursor < end && (*cursor == ' ' || *cursor == '\t')) {
        ++cursor;
    }
    return cursor;
}

static int
v4_hb_parse_id_map(
    const char *buffer,
    size_t used,
    struct v4_hb_id_map_projection *projection
)
{
    uint64_t values[3];
    const char *cursor = buffer;
    const char *end = buffer + used;
    unsigned int index;

    if (buffer == NULL || projection == NULL || used == 0 ||
        buffer[used - 1] != '\n') {
        return -1;
    }
    for (index = 0; index < 3U; ++index) {
        const char *token_end;
        cursor = v4_hb_skip_horizontal_space(cursor, end);
        token_end = cursor;
        while (token_end < end && *token_end >= '0' && *token_end <= '9') {
            ++token_end;
        }
        if (v4_hb_parse_decimal_u64(cursor, token_end, &values[index]) != 0 ||
            values[index] > UINT32_MAX) {
            return -1;
        }
        cursor = token_end;
    }
    cursor = v4_hb_skip_horizontal_space(cursor, end);
    if (cursor + 1 != end || *cursor != '\n') {
        return -1;
    }
    projection->inside_id = (uint32_t)values[0];
    projection->outside_id = (uint32_t)values[1];
    projection->length = (uint32_t)values[2];
    return 0;
}

static int
v4_hb_read_setgroups_policy(
    const struct v4_hb_builder *builder,
    const char *relative_path,
    bool initial_observation,
    bool *denied,
    struct v4_hb_error *error
)
{
    char buffer[16];
    size_t used;
    int code;

    code = v4_hb_read_bounded_proc_at(
        builder, relative_path, buffer, sizeof(buffer), &used, error
    );
    if (code != V4_HB_OK) {
        if (initial_observation && error != NULL &&
            v4_hb_unsupported_observation_errno(error->saved_errno)) {
            return v4_hb_fail(
                error, V4_HB_UNSUPPORTED, error->saved_errno,
                "setgroups policy observation is unavailable"
            );
        }
        return code;
    }
    if (used == sizeof("allow\n") - 1U &&
        memcmp(buffer, "allow\n", used) == 0) {
        *denied = false;
        return V4_HB_OK;
    }
    if (used == sizeof("deny\n") - 1U &&
        memcmp(buffer, "deny\n", used) == 0) {
        *denied = true;
        return V4_HB_OK;
    }
    return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                      "setgroups policy projection is malformed");
}

static int
v4_hb_require_child_proc_record(
    const struct v4_hb_builder *builder,
    const char *name,
    const char *expected,
    size_t expected_bytes,
    struct v4_hb_error *error
)
{
    char path[64];
    char buffer[V4_HB_PROC_MAP_MAX_BYTES];
    size_t used;
    int count;
    int code;

    count = snprintf(
        path, sizeof(path), "%ld/%s", (long)builder->pid, name
    );
    if (count < 0 || (size_t)count >= sizeof(path) ||
        expected_bytes > sizeof(buffer) ||
        (expected_bytes != 0 && expected == NULL)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child proc record request exceeds cap");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, sizeof(buffer), &used, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    if (used != expected_bytes ||
        (used != 0 && memcmp(buffer, expected, used) != 0)) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child %s precondition mismatch: bytes=%lu/%lu "
                          "prefix=%02x%02x%02x%02x%02x%02x",
                          name, (unsigned long)used,
                          (unsigned long)expected_bytes,
                          used > 0 ? (unsigned char)buffer[0] : 0U,
                          used > 1 ? (unsigned char)buffer[1] : 0U,
                          used > 2 ? (unsigned char)buffer[2] : 0U,
                          used > 3 ? (unsigned char)buffer[3] : 0U,
                          used > 4 ? (unsigned char)buffer[4] : 0U,
                          used > 5 ? (unsigned char)buffer[5] : 0U);
    }
    return V4_HB_OK;
}

static int
v4_hb_read_child_map(
    const struct v4_hb_builder *builder,
    const char *name,
    struct v4_hb_id_map_projection *projection,
    struct v4_hb_error *error
)
{
    char path[64];
    char buffer[V4_HB_PROC_MAP_MAX_BYTES];
    size_t used;
    int count;
    int code;

    count = snprintf(
        path, sizeof(path), "%ld/%s", (long)builder->pid, name
    );
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child map proc path exceeds cap");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, sizeof(buffer), &used, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    if (v4_hb_parse_id_map(buffer, used, projection) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child ID map is malformed");
    }
    return V4_HB_OK;
}

static int
v4_hb_read_setgroups_deny(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    char path[64];
    char buffer[V4_HB_PROC_MAP_MAX_BYTES];
    size_t used;
    int count;
    int code;

    count = snprintf(
        path, sizeof(path), "%ld/setgroups", (long)builder->pid
    );
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child setgroups proc path exceeds cap");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, sizeof(buffer), &used, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    if (used != sizeof("deny\n") - 1U ||
        memcmp(buffer, "deny\n", sizeof("deny\n") - 1U) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child setgroups state is not exact deny");
    }
    return V4_HB_OK;
}

static int
v4_hb_read_child_nspid(
    const struct v4_hb_builder *builder,
    uint32_t *child_nspid,
    struct v4_hb_error *error
)
{
    char path[64];
    char buffer[V4_HB_PROC_STATUS_MAX_BYTES + 1U];
    char *cursor;
    size_t used;
    uint32_t nspid_field_count = 0;
    uint32_t parsed_child_nspid = 0;
    int count;
    int code;

    count = snprintf(path, sizeof(path), "%ld/status", (long)builder->pid);
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child status proc path exceeds cap");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, V4_HB_PROC_STATUS_MAX_BYTES, &used, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    buffer[used] = '\0';
    cursor = buffer;
    while (cursor < buffer + used) {
        char *line_end = memchr(cursor, '\n', (size_t)(buffer + used - cursor));
        if (line_end == NULL) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "child status has an unterminated line");
        }
        if ((size_t)(line_end - cursor) >= sizeof("NSpid:") - 1U &&
            memcmp(cursor, "NSpid:", sizeof("NSpid:") - 1U) == 0) {
            const char *field = cursor + sizeof("NSpid:") - 1U;
            uint64_t previous = 0;
            uint64_t last = 0;
            uint32_t depth = 0;

            ++nspid_field_count;
            if (nspid_field_count != 1U) {
                return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                                  "child status repeats NSpid");
            }

            while (field < line_end) {
                const char *token_end;
                uint64_t value;
                field = v4_hb_skip_horizontal_space(field, line_end);
                if (field == line_end) {
                    break;
                }
                token_end = field;
                while (token_end < line_end &&
                       *token_end >= '0' && *token_end <= '9') {
                    ++token_end;
                }
                if (v4_hb_parse_decimal_u64(
                        field, token_end, &value
                    ) != 0 || value == 0 || value > UINT32_MAX ||
                    depth == UINT32_MAX) {
                    return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                                      "child NSpid list is malformed");
                }
                previous = last;
                last = value;
                ++depth;
                field = token_end;
            }
            if (depth < 2U || previous != (uint64_t)builder->pid ||
                last != 1U) {
                return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                                  "child NSpid tail is not outer-pid/1");
            }
            parsed_child_nspid = (uint32_t)last;
        }
        cursor = line_end + 1;
    }
    if (nspid_field_count == 1U) {
        *child_nspid = parsed_child_nspid;
        return V4_HB_OK;
    }
    return v4_hb_fail(
        error,
        builder->child_nspid == 0U ? V4_HB_UNSUPPORTED : V4_HB_ERROR,
        ENOTSUP,
                      "child NSpid observation is unavailable");
}

static int
v4_hb_configure_child_id_maps(
    struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    char path[64];
    char record[128];
    int count;
    int code;

    code = v4_hb_require_child_proc_record(
        builder, "uid_map", NULL, 0U, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    count = snprintf(
        record, sizeof(record), "0 %lu 1\n",
        (unsigned long)builder->observer_effective_uid
    );
    if (count < 0 || (size_t)count >= sizeof(record)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child uid-map record exceeds cap");
    }
    count = snprintf(path, sizeof(path), "%ld/uid_map", (long)builder->pid);
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child uid-map path exceeds cap");
    }
    code = v4_hb_write_proc_record(
        builder, path, record, strlen(record), error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    builder->uid_map_write_count = 1U;
    builder->uid_map_write_order = 1U;

    code = v4_hb_require_child_proc_record(
        builder, "setgroups",
        builder->observer_setgroups_denied ? "deny\n" : "allow\n",
        builder->observer_setgroups_denied ?
            sizeof("deny\n") - 1U : sizeof("allow\n") - 1U,
        error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    count = snprintf(path, sizeof(path), "%ld/setgroups", (long)builder->pid);
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child setgroups path exceeds cap");
    }
    code = v4_hb_write_proc_record(
        builder, path, "deny\n", sizeof("deny\n") - 1U, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    builder->setgroups_deny_write_count = 1U;
    builder->setgroups_deny_write_order = 2U;

    code = v4_hb_require_child_proc_record(
        builder, "gid_map", NULL, 0U, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    count = snprintf(
        record, sizeof(record), "0 %lu 1\n",
        (unsigned long)builder->observer_effective_gid
    );
    if (count < 0 || (size_t)count >= sizeof(record)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child gid-map record exceeds cap");
    }
    count = snprintf(path, sizeof(path), "%ld/gid_map", (long)builder->pid);
    if (count < 0 || (size_t)count >= sizeof(path)) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "child gid-map path exceeds cap");
    }
    code = v4_hb_write_proc_record(
        builder, path, record, strlen(record), error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    builder->gid_map_write_count = 1U;
    builder->gid_map_write_order = 3U;
    return V4_HB_OK;
}

static int
v4_hb_verify_child_id_maps(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    struct v4_hb_id_map_projection uid_map;
    struct v4_hb_id_map_projection gid_map;
    uint32_t child_nspid;
    int code;

    if (builder->uid_map_write_count != 1U ||
        builder->setgroups_deny_write_count != 1U ||
        builder->gid_map_write_count != 1U ||
        builder->uid_map_write_order != 1U ||
        builder->setgroups_deny_write_order != 2U ||
        builder->gid_map_write_order != 3U ||
        geteuid() != builder->observer_effective_uid ||
        getegid() != builder->observer_effective_gid) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child ID-map authority state is malformed");
    }
    code = v4_hb_read_child_map(builder, "uid_map", &uid_map, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_read_setgroups_deny(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_read_child_map(builder, "gid_map", &gid_map, error);
    if (code != V4_HB_OK) {
        return code;
    }
    if (uid_map.inside_id != 0U ||
        uid_map.outside_id != (uint32_t)builder->observer_effective_uid ||
        uid_map.length != 1U || gid_map.inside_id != 0U ||
        gid_map.outside_id != (uint32_t)builder->observer_effective_gid ||
        gid_map.length != 1U) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child ID maps do not match observer effective IDs");
    }
    if (uid_map.inside_id != builder->uid_map.inside_id ||
        uid_map.outside_id != builder->uid_map.outside_id ||
        uid_map.length != builder->uid_map.length ||
        gid_map.inside_id != builder->gid_map.inside_id ||
        gid_map.outside_id != builder->gid_map.outside_id ||
        gid_map.length != builder->gid_map.length) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child ID-map projection changed");
    }
    code = v4_hb_read_child_nspid(builder, &child_nspid, error);
    if (code != V4_HB_OK) {
        return code;
    }
    if (child_nspid != 1U || child_nspid != builder->child_nspid) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "child NSpid projection changed");
    }
    return V4_HB_OK;
}

static int
v4_hb_verify_parent_namespace_boundary(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    bool current_setgroups_denied;
    int code;

    if (builder == NULL || geteuid() != builder->observer_effective_uid ||
        getegid() != builder->observer_effective_gid) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "observer identity changed at namespace boundary");
    }
    code = v4_hb_verify_proc_root(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_read_setgroups_policy(
        builder, "self/setgroups", false, &current_setgroups_denied, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    if (current_setgroups_denied != builder->observer_setgroups_denied) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "observer setgroups policy changed");
    }
    return v4_hb_verify_namespace_set(
        builder, 0, builder->parent_namespaces,
        builder->parent_namespace_guards, error
    );
}

static int
v4_hb_verify_namespace_boundary(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    uint32_t index;
    int code = v4_hb_verify_parent_namespace_boundary(builder, error);

    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_verify_namespace_set(
        builder, builder->pid, builder->child_namespaces,
        builder->child_namespace_guards, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        if (builder->parent_namespaces[index].device ==
                builder->child_namespaces[index].device &&
            builder->parent_namespaces[index].inode ==
                builder->child_namespaces[index].inode) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "child namespace is not distinct from parent");
        }
    }
    return v4_hb_verify_child_id_maps(builder, error);
}

static int
v4_hb_pidfd_send(
    int pidfd,
    int signal_number,
    struct v4_hb_error *error
)
{
    if (syscall(SYS_pidfd_send_signal, pidfd, signal_number, NULL, 0) == 0) {
        return V4_HB_OK;
    }
    if (errno == ENOSYS || errno == EINVAL || errno == EPERM ||
        errno == EACCES) {
        return v4_hb_fail(error, V4_HB_UNSUPPORTED, errno,
                          "pidfd_send_signal is unavailable");
    }
    return v4_hb_fail(error, V4_HB_ERROR, errno,
                      "pidfd_send_signal failed");
}

static int
v4_hb_verify_pidfd_alias(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    int primary_fd_flags;
    int guard_fd_flags;
    int primary_status_flags;
    int guard_status_flags;
    long comparison;

    if (builder == NULL || builder->pidfd < 0 ||
        builder->pidfd_guard < 0 ||
        builder->pidfd == builder->pidfd_guard) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "retained pidfd alias is malformed");
    }
    primary_fd_flags = fcntl(builder->pidfd, F_GETFD);
    if (primary_fd_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "primary pidfd F_GETFD failed");
    }
    guard_fd_flags = fcntl(builder->pidfd_guard, F_GETFD);
    if (guard_fd_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "guard pidfd F_GETFD failed");
    }
    primary_status_flags = fcntl(builder->pidfd, F_GETFL);
    if (primary_status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "primary pidfd F_GETFL failed");
    }
    guard_status_flags = fcntl(builder->pidfd_guard, F_GETFL);
    if (guard_status_flags < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "guard pidfd F_GETFL failed");
    }
    if (primary_fd_flags != FD_CLOEXEC || guard_fd_flags != FD_CLOEXEC ||
        primary_status_flags != guard_status_flags ||
        primary_status_flags != builder->pidfd_status_flags) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "retained pidfd fcntl projection changed");
    }
    comparison = syscall(
        SYS_kcmp, getpid(), getpid(), KCMP_FILE,
        (unsigned long)builder->pidfd,
        (unsigned long)builder->pidfd_guard
    );
    if (comparison == 0) {
        return V4_HB_OK;
    }
    if (comparison < 0 &&
        (errno == ENOSYS || errno == EPERM || errno == EACCES)) {
        return v4_hb_fail(error, V4_HB_UNSUPPORTED, errno,
                          "KCMP_FILE cannot verify the retained pidfd alias");
    }
    return v4_hb_fail(error, V4_HB_ERROR,
                      comparison < 0 ? errno : EINVAL,
                      "retained pidfd no longer names its original OFD");
}

static void
v4_hb_child_gate_loop(_Atomic unsigned int *gate)
{
    unsigned int value;

    do {
        value = atomic_load_explicit(gate, memory_order_acquire);
#if defined(__x86_64__) || defined(__i386__)
        __asm__ volatile("pause" ::: "memory");
#endif
    } while (value == 0U);
    (void)syscall(SYS_exit, value == 1U ? 0 : 125);
    __builtin_unreachable();
}

static void
v4_hb_discard_resources(struct v4_hb_builder *builder)
{
    uint32_t index;

    if (builder->pidfd >= 0) {
        (void)close(builder->pidfd);
        builder->pidfd = -1;
    }
    if (builder->pidfd_guard >= 0) {
        (void)close(builder->pidfd_guard);
        builder->pidfd_guard = -1;
    }
    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        if (builder->parent_namespaces[index].descriptor >= 0) {
            (void)close(builder->parent_namespaces[index].descriptor);
            builder->parent_namespaces[index].descriptor = -1;
        }
        if (builder->parent_namespace_guards[index] >= 0) {
            (void)close(builder->parent_namespace_guards[index]);
            builder->parent_namespace_guards[index] = -1;
        }
        if (builder->child_namespaces[index].descriptor >= 0) {
            (void)close(builder->child_namespaces[index].descriptor);
            builder->child_namespaces[index].descriptor = -1;
        }
        if (builder->child_namespace_guards[index] >= 0) {
            (void)close(builder->child_namespace_guards[index]);
            builder->child_namespace_guards[index] = -1;
        }
    }
    if (builder->proc_root_fd >= 0) {
        (void)close(builder->proc_root_fd);
        builder->proc_root_fd = -1;
    }
    if (builder->proc_root_guard >= 0) {
        (void)close(builder->proc_root_guard);
        builder->proc_root_guard = -1;
    }
    if (builder->gate != MAP_FAILED && builder->gate != NULL) {
        (void)munmap((void *)builder->gate, builder->gate_mapping_bytes);
        builder->gate = MAP_FAILED;
    }
    builder->state = V4_HB_CLOSED;
}

static int
v4_hb_close_resources_checked(
    struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    int saved_errno = 0;
    uint32_t index;

    if (builder->pidfd >= 0) {
        if (close(builder->pidfd) != 0) {
            saved_errno = errno;
        }
        builder->pidfd = -1;
    }
    if (builder->pidfd_guard >= 0) {
        if (close(builder->pidfd_guard) != 0 && saved_errno == 0) {
            saved_errno = errno;
        }
        builder->pidfd_guard = -1;
    }
    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        if (builder->parent_namespaces[index].descriptor >= 0) {
            if (close(builder->parent_namespaces[index].descriptor) != 0 &&
                saved_errno == 0) {
                saved_errno = errno;
            }
            builder->parent_namespaces[index].descriptor = -1;
        }
        if (builder->parent_namespace_guards[index] >= 0) {
            if (close(builder->parent_namespace_guards[index]) != 0 &&
                saved_errno == 0) {
                saved_errno = errno;
            }
            builder->parent_namespace_guards[index] = -1;
        }
        if (builder->child_namespaces[index].descriptor >= 0) {
            if (close(builder->child_namespaces[index].descriptor) != 0 &&
                saved_errno == 0) {
                saved_errno = errno;
            }
            builder->child_namespaces[index].descriptor = -1;
        }
        if (builder->child_namespace_guards[index] >= 0) {
            if (close(builder->child_namespace_guards[index]) != 0 &&
                saved_errno == 0) {
                saved_errno = errno;
            }
            builder->child_namespace_guards[index] = -1;
        }
    }
    if (builder->proc_root_fd >= 0) {
        if (close(builder->proc_root_fd) != 0 && saved_errno == 0) {
            saved_errno = errno;
        }
        builder->proc_root_fd = -1;
    }
    if (builder->proc_root_guard >= 0) {
        if (close(builder->proc_root_guard) != 0 && saved_errno == 0) {
            saved_errno = errno;
        }
        builder->proc_root_guard = -1;
    }
    if (builder->gate != MAP_FAILED && builder->gate != NULL) {
        if (munmap((void *)builder->gate, builder->gate_mapping_bytes) != 0 &&
            saved_errno == 0) {
            saved_errno = errno;
        }
        builder->gate = MAP_FAILED;
    }
    builder->state = V4_HB_CLOSED;
    if (saved_errno != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, saved_errno,
                          "held-builder resource close failed");
    }
    return V4_HB_OK;
}

static int
v4_hb_reap_untraced_child(pid_t pid)
{
    unsigned int attempt;
    int status;

    if (pid <= 0) {
        return 0;
    }
    (void)kill(pid, SIGKILL);
    for (attempt = 0; attempt < V4_HB_WAIT_ATTEMPT_LIMIT; ++attempt) {
        pid_t waited;
        do {
            waited = waitpid(pid, &status, WNOHANG);
        } while (waited < 0 && errno == EINTR);
        if (waited == pid) {
            return 0;
        }
        if (waited < 0) {
            return -1;
        }
        if (poll(NULL, 0, V4_HB_WAIT_POLL_MILLISECONDS) < 0 &&
            errno != EINTR) {
            return -1;
        }
    }
    return -1;
}

int
v4_hb_builder_start(
    const struct v4_hb_root_anchor_config *config,
    struct v4_hb_builder **builder_out,
    struct v4_hb_error *error
)
{
    struct v4_hb_builder *builder;
    uint64_t second_start_ticks;
    uint64_t observer_uid;
    uint64_t observer_gid;
    uint32_t index;
    pid_t pid;
    int pidfd;
    int code;

    v4_hb_error_clear(error);
    if (builder_out == NULL || config == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "builder start input is null");
    }
    *builder_out = NULL;
    code = v4_hb_validate_root_config(config, true, error);
    if (code != V4_HB_OK) {
        return code;
    }
    builder = calloc(1, sizeof(*builder));
    if (builder == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, ENOMEM,
                          "cannot allocate held-builder state");
    }
    builder->pidfd = -1;
    builder->pidfd_guard = -1;
    builder->proc_root_fd = -1;
    builder->proc_root_guard = -1;
    builder->root_config = *config;
    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        builder->parent_namespaces[index].descriptor = -1;
        builder->child_namespaces[index].descriptor = -1;
        builder->parent_namespace_guards[index] = -1;
        builder->child_namespace_guards[index] = -1;
    }
    observer_uid = (uint64_t)geteuid();
    observer_gid = (uint64_t)getegid();
    if (observer_uid > UINT32_MAX || observer_gid > UINT32_MAX) {
        free(builder);
        return v4_hb_fail(error, V4_HB_UNSUPPORTED, EOVERFLOW,
                          "observer effective IDs exceed V4 uint32 bounds");
    }
    builder->observer_effective_uid = (uid_t)observer_uid;
    builder->observer_effective_gid = (gid_t)observer_gid;
    code = v4_hb_capture_proc_root(builder, error);
    if (code == V4_HB_OK) {
        code = v4_hb_read_setgroups_policy(
            builder, "self/setgroups", true,
            &builder->observer_setgroups_denied, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_capture_namespace_set(
            builder, 0, builder->parent_namespaces,
            builder->parent_namespace_guards, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_validate_root_config(
            &builder->root_config, true, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_verify_root_descriptor_disjointness(builder, error);
    }
    if (code != V4_HB_OK) {
        v4_hb_discard_resources(builder);
        free(builder);
        return code;
    }
    builder->gate_mapping_bytes = sizeof(*builder->gate);
    builder->gate = mmap(
        NULL, builder->gate_mapping_bytes, PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_ANONYMOUS, -1, 0
    );
    if (builder->gate == MAP_FAILED) {
        int saved_errno = errno;
        v4_hb_discard_resources(builder);
        free(builder);
        return v4_hb_fail(
            error,
            (saved_errno == ENOSYS || saved_errno == EINVAL ||
             saved_errno == EPERM || saved_errno == EACCES) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno,
                          "shared userspace gate mmap failed");
    }
    atomic_init(builder->gate, 0U);
    pid = (pid_t)syscall(
        SYS_clone, V4_HB_FIXED_CLONE_FLAGS, NULL, NULL, NULL, 0UL
    );
    if (pid < 0) {
        int saved_errno = errno;
        v4_hb_discard_resources(builder);
        free(builder);
        return v4_hb_fail(
            error,
            (saved_errno == ENOSYS || saved_errno == EPERM ||
             saved_errno == EACCES) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno,
                          "held builder clone failed");
    }
    if (pid == 0) {
        v4_hb_child_gate_loop(builder->gate);
    }
    builder->pid = pid;
    pidfd = (int)syscall(SYS_pidfd_open, pid, 0U);
    if (pidfd < 0) {
        int saved_errno = errno;
        int reap_result = v4_hb_reap_untraced_child(pid);
        v4_hb_discard_resources(builder);
        free(builder);
        if (reap_result != 0) {
            return v4_hb_fail(error, V4_HB_ERROR, EIO,
                              "cannot reap builder after pidfd_open failure");
        }
        return v4_hb_fail(
            error,
            (saved_errno == ENOSYS || saved_errno == EINVAL ||
             saved_errno == EPERM || saved_errno == EACCES) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno, "pidfd_open is unavailable"
        );
    }
    builder->pidfd = pidfd;
    code = V4_HB_OK;
    builder->pidfd_status_flags = fcntl(pidfd, F_GETFL);
    if (builder->pidfd_status_flags < 0) {
        code = v4_hb_fail(error, V4_HB_ERROR, errno,
                          "cannot capture pidfd status flags");
    } else {
        builder->pidfd_guard = fcntl(pidfd, F_DUPFD_CLOEXEC, 3);
    }
    if (code == V4_HB_OK && builder->pidfd_guard < 0) {
        code = v4_hb_fail(error, V4_HB_ERROR, errno,
                          "cannot retain a pidfd guard alias");
    } else if (code == V4_HB_OK) {
        code = v4_hb_verify_pidfd_alias(builder, error);
    }
    if (code == V4_HB_OK) {
        code = v4_hb_verify_root_descriptor_disjointness(builder, error);
    }
    if (code == V4_HB_OK) {
        code = v4_hb_pidfd_send(pidfd, 0, error);
    }
    if (code == V4_HB_OK) {
        code = v4_hb_read_start_ticks(
            builder, pid, &builder->start_ticks, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_read_start_ticks(
            builder, pid, &second_start_ticks, error
        );
    }
    if (code == V4_HB_OK && second_start_ticks != builder->start_ticks) {
        code = v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "builder identity changed during capture");
    }
    if (code != V4_HB_OK) {
        int reap_result;
        (void)syscall(SYS_pidfd_send_signal, pidfd, SIGKILL, NULL, 0);
        reap_result = v4_hb_reap_untraced_child(pid);
        v4_hb_discard_resources(builder);
        free(builder);
        if (reap_result != 0) {
            return v4_hb_fail(error, V4_HB_ERROR, EIO,
                              "cannot reap builder after capture failure");
        }
        return code;
    }
    builder->state = V4_HB_GATE_SPINNING;
    *builder_out = builder;
    return V4_HB_OK;
}

int
v4_hb_builder_snapshot(
    const struct v4_hb_builder *builder,
    struct v4_hb_snapshot *snapshot,
    struct v4_hb_error *error
)
{
    uint32_t index;

    v4_hb_error_clear(error);
    if (builder == NULL || snapshot == NULL ||
        builder->gate == NULL || builder->gate == MAP_FAILED) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder snapshot input is malformed");
    }
    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->pid = builder->pid;
    snapshot->start_ticks = builder->start_ticks;
    snapshot->pidfd = builder->pidfd;
    snapshot->state = builder->state;
    snapshot->gate_value = atomic_load_explicit(
        builder->gate, memory_order_acquire
    );
    snapshot->raw_interrupt_wait_status = builder->raw_interrupt_wait_status;
    snapshot->seize_count = builder->seize_count;
    snapshot->interrupt_count = builder->interrupt_count;
    snapshot->interrupt_event_stop_count =
        builder->interrupt_event_stop_count;
    snapshot->resume_count = builder->resume_count;
    snapshot->held_stop_consumed = builder->held_stop_consumed;
    snapshot->clone_flags = V4_HB_FIXED_CLONE_FLAGS;
    snapshot->namespace_count = V4_HB_NAMESPACE_COUNT;
    snapshot->observer_effective_uid =
        (uint32_t)builder->observer_effective_uid;
    snapshot->observer_effective_gid =
        (uint32_t)builder->observer_effective_gid;
    snapshot->observer_setgroups_denied =
        builder->observer_setgroups_denied ? 1U : 0U;
    snapshot->root_inheritance_verified =
        builder->root_inheritance_verified ? 1U : 0U;
    snapshot->child_nspid = builder->child_nspid;
    snapshot->uid_map_write_count = builder->uid_map_write_count;
    snapshot->setgroups_deny_write_count =
        builder->setgroups_deny_write_count;
    snapshot->gid_map_write_count = builder->gid_map_write_count;
    snapshot->uid_map_write_order = builder->uid_map_write_order;
    snapshot->setgroups_deny_write_order =
        builder->setgroups_deny_write_order;
    snapshot->gid_map_write_order = builder->gid_map_write_order;
    snapshot->uid_map = builder->uid_map;
    snapshot->gid_map = builder->gid_map;
    for (index = 0; index < V4_HB_NAMESPACE_COUNT; ++index) {
        snapshot->parent_namespaces[index] =
            builder->parent_namespaces[index];
        snapshot->child_namespaces[index] = builder->child_namespaces[index];
    }
    snapshot->input_root = builder->root_config.input_root;
    snapshot->output_root = builder->root_config.output_root;
    return V4_HB_OK;
}

static bool
v4_hb_exact_snapshot(
    const struct v4_hb_snapshot *first,
    const struct v4_hb_snapshot *second
)
{
    uint32_t index;
    bool exact = first->pid == second->pid &&
        first->start_ticks == second->start_ticks &&
        first->pidfd == second->pidfd &&
        first->state == second->state &&
        first->gate_value == second->gate_value &&
        first->raw_interrupt_wait_status ==
            second->raw_interrupt_wait_status &&
        first->seize_count == second->seize_count &&
        first->interrupt_count == second->interrupt_count &&
        first->interrupt_event_stop_count ==
            second->interrupt_event_stop_count &&
        first->resume_count == second->resume_count &&
        first->held_stop_consumed == second->held_stop_consumed &&
        first->clone_flags == second->clone_flags &&
        first->namespace_count == second->namespace_count &&
        first->observer_effective_uid == second->observer_effective_uid &&
        first->observer_effective_gid == second->observer_effective_gid &&
        first->observer_setgroups_denied ==
            second->observer_setgroups_denied &&
        first->root_inheritance_verified ==
            second->root_inheritance_verified &&
        first->child_nspid == second->child_nspid &&
        first->uid_map_write_count == second->uid_map_write_count &&
        first->setgroups_deny_write_count ==
            second->setgroups_deny_write_count &&
        first->gid_map_write_count == second->gid_map_write_count &&
        first->uid_map_write_order == second->uid_map_write_order &&
        first->setgroups_deny_write_order ==
            second->setgroups_deny_write_order &&
        first->gid_map_write_order == second->gid_map_write_order &&
        first->uid_map.inside_id == second->uid_map.inside_id &&
        first->uid_map.outside_id == second->uid_map.outside_id &&
        first->uid_map.length == second->uid_map.length &&
        first->gid_map.inside_id == second->gid_map.inside_id &&
        first->gid_map.outside_id == second->gid_map.outside_id &&
        first->gid_map.length == second->gid_map.length;

    for (index = 0; exact && index < V4_HB_NAMESPACE_COUNT; ++index) {
        exact = v4_hb_same_namespace_projection(
            &first->parent_namespaces[index],
            &second->parent_namespaces[index], true
        ) && v4_hb_same_namespace_projection(
            &first->child_namespaces[index],
            &second->child_namespaces[index], true
        );
    }
    return exact &&
        v4_hb_same_root_anchor(&first->input_root, &second->input_root) &&
        v4_hb_same_root_anchor(&first->output_root, &second->output_root);
}

static int
v4_hb_waitid_pidfd_ptrace_event(
    const struct v4_hb_builder *builder,
    unsigned int expected_event,
    struct v4_hb_error *error
)
{
    siginfo_t information;
    unsigned int attempt;

    for (attempt = 0; attempt < V4_HB_WAIT_ATTEMPT_LIMIT; ++attempt) {
        memset(&information, 0, sizeof(information));
        if (waitid(P_PIDFD, (id_t)builder->pidfd, &information,
                   WSTOPPED | WNOWAIT | WNOHANG) != 0) {
            int saved_errno = errno;
            return v4_hb_fail(
                error,
                (saved_errno == EINVAL || saved_errno == ENOSYS ||
                 saved_errno == EPERM) ? V4_HB_UNSUPPORTED : V4_HB_ERROR,
                saved_errno, "pidfd wait observation failed"
            );
        }
        if (information.si_pid != 0) {
            break;
        }
        if (poll(NULL, 0, V4_HB_WAIT_POLL_MILLISECONDS) < 0 &&
            errno != EINTR) {
            return v4_hb_fail(error, V4_HB_ERROR, errno,
                              "pidfd event wait pause failed");
        }
    }
    if (attempt == V4_HB_WAIT_ATTEMPT_LIMIT) {
        return v4_hb_fail(error, V4_HB_ERROR, ETIMEDOUT,
                          "pidfd ptrace event wait timed out");
    }
    if (information.si_pid != builder->pid ||
        information.si_code != CLD_TRAPPED ||
        information.si_status !=
            (int)((expected_event << 8) | (unsigned int)SIGTRAP)) {
        return v4_hb_fail(
            error, V4_HB_ERROR, EINVAL,
            "pidfd stop observation mismatch: pid=%ld/%ld code=%d/%d "
            "status=%d/%u",
            (long)information.si_pid, (long)builder->pid,
            information.si_code, CLD_TRAPPED,
            information.si_status,
            (expected_event << 8) | (unsigned int)SIGTRAP
        );
    }
    return V4_HB_OK;
}

static int
v4_hb_read_held_proc_status(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    char path[64];
    char buffer[V4_HB_PROC_STATUS_MAX_BYTES + 1];
    char *cursor;
    size_t used;
    unsigned int state_count = 0;
    unsigned int tracer_count = 0;
    int code;

    if (snprintf(path, sizeof(path), "%ld/status",
                 (long)builder->pid) < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "cannot format builder proc status path");
    }
    code = v4_hb_read_bounded_proc_at(
        builder, path, buffer, V4_HB_PROC_STATUS_MAX_BYTES, &used, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    buffer[used] = '\0';
    cursor = buffer;
    while (*cursor != '\0') {
        char *newline = strchr(cursor, '\n');
        if (newline == NULL) {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "unterminated builder proc status line");
        }
        if (strncmp(cursor, "State:\t", 7) == 0) {
            ++state_count;
            if (cursor[7] != 't') {
                return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                                  "builder is not in a tracing stop");
            }
        } else if (strncmp(cursor, "TracerPid:\t", 11) == 0) {
            uint64_t tracer_pid;
            ++tracer_count;
            if (v4_hb_parse_decimal_u64(
                    cursor + 11, newline, &tracer_pid
                ) != 0 || tracer_pid != (uint64_t)getpid()) {
                return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                                  "builder tracer identity mismatch");
            }
        }
        cursor = newline + 1;
    }
    if (state_count != 1 || tracer_count != 1) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "builder proc status fields are incomplete");
    }
    return V4_HB_OK;
}

static int
v4_hb_verify_held_internal(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    struct user_regs_struct registers;
    struct v4_hb_ptrace_syscall_base syscall_information;
    struct iovec vector;
    siginfo_t current_siginfo;
    uint64_t current_start_ticks;
    int unexpected_status;
    pid_t waited;
    int code;

    if (builder == NULL ||
        (builder->state != V4_HB_INTERRUPT_HELD &&
         builder->state != V4_HB_BOUND_ROOT_WALKS_COMPLETE) ||
        builder->pid <= 0 || builder->pidfd < 0 ||
        builder->start_ticks == 0 || builder->gate == MAP_FAILED ||
        atomic_load_explicit(builder->gate, memory_order_acquire) != 0U ||
        builder->seize_count != 1 || builder->interrupt_count != 1 ||
        builder->interrupt_event_stop_count != 1 ||
        builder->resume_count != 0 ||
        builder->held_stop_consumed != 1 ||
        !builder->root_inheritance_verified ||
        !WIFSTOPPED(builder->raw_interrupt_wait_status) ||
        WSTOPSIG(builder->raw_interrupt_wait_status) != SIGTRAP ||
        (unsigned int)builder->raw_interrupt_wait_status >> 16 !=
            PTRACE_EVENT_STOP) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder logical state is malformed");
    }
    code = v4_hb_verify_pidfd_alias(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_pidfd_send(builder->pidfd, 0, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_read_start_ticks(
        builder, builder->pid, &current_start_ticks, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    if (current_start_ticks != builder->start_ticks) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder PID/start-ticks identity changed");
    }
    code = v4_hb_read_held_proc_status(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_verify_namespace_boundary(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_verify_root_inheritance(builder, false, error);
    if (code != V4_HB_OK) {
        return code;
    }
    memset(&current_siginfo, 0, sizeof(current_siginfo));
    {
        int siginfo_result = ptrace(
            PTRACE_GETSIGINFO, builder->pid, NULL, &current_siginfo
        );
        if (siginfo_result != 0 ||
            current_siginfo.si_signo !=
                builder->interrupt_siginfo.si_signo ||
            current_siginfo.si_errno !=
                builder->interrupt_siginfo.si_errno ||
            current_siginfo.si_code != builder->interrupt_siginfo.si_code ||
            current_siginfo.si_pid != builder->interrupt_siginfo.si_pid ||
            current_siginfo.si_uid != builder->interrupt_siginfo.si_uid) {
            return v4_hb_fail(
                error, V4_HB_ERROR,
                siginfo_result != 0 ? errno : EINVAL,
                "held-builder ptrace siginfo changed"
            );
        }
    }
    memset(&registers, 0, sizeof(registers));
    vector.iov_base = &registers;
    vector.iov_len = sizeof(registers);
    if (ptrace(PTRACE_GETREGSET, builder->pid,
               (void *)(uintptr_t)NT_PRSTATUS, &vector) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "held-builder GETREGSET failed");
    }
    if (vector.iov_len != sizeof(registers)) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder register projection size mismatch");
    }
    memset(&syscall_information, 0, sizeof(syscall_information));
    {
        long information_bytes = ptrace(
            (enum __ptrace_request)V4_HB_PTRACE_GET_SYSCALL_INFO,
            builder->pid, (void *)sizeof(syscall_information),
            &syscall_information
        );
        if (information_bytes < (long)sizeof(syscall_information) ||
            syscall_information.operation !=
                V4_HB_PTRACE_SYSCALL_INFO_NONE ||
            syscall_information.architecture != AUDIT_ARCH_X86_64 ||
            syscall_information.instruction_pointer != registers.rip ||
            syscall_information.stack_pointer != registers.rsp ||
            syscall_information.instruction_pointer == 0 ||
            syscall_information.stack_pointer == 0) {
            int saved_errno = information_bytes < 0 ? errno : EINVAL;
            int result = information_bytes < 0 &&
                    (saved_errno == EIO || saved_errno == EINVAL) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR;
            return v4_hb_fail(
                error, result, saved_errno,
                "held builder is not an observed userspace non-syscall stop"
            );
        }
    }
    do {
        waited = waitpid(builder->pid, &unexpected_status,
                         __WALL | WNOHANG);
    } while (waited < 0 && errno == EINTR);
    if (waited != 0) {
        return v4_hb_fail(error, V4_HB_ERROR,
                          waited < 0 ? errno : EINVAL,
                          "unexpected additional held-builder wait event");
    }
    return V4_HB_OK;
}

int
v4_hb_builder_verify_held(
    const struct v4_hb_builder *builder,
    const struct v4_hb_snapshot *expected,
    struct v4_hb_error *error
)
{
    struct v4_hb_snapshot actual;
    int code;

    v4_hb_error_clear(error);
    if (expected == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "expected held-builder snapshot is null");
    }
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    code = v4_hb_builder_snapshot(builder, &actual, error);
    if (code != V4_HB_OK) {
        return code;
    }
    if (!v4_hb_exact_snapshot(&actual, expected)) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder snapshot splice rejected");
    }
    return V4_HB_OK;
}

int
v4_hb_builder_seize_interrupt(
    struct v4_hb_builder *builder,
    struct v4_hb_snapshot *held_snapshot,
    struct v4_hb_error *error
)
{
    int status;
    pid_t waited;
    uint64_t current_start_ticks;
    int code;

    v4_hb_error_clear(error);
    if (builder == NULL || held_snapshot == NULL ||
        builder->state != V4_HB_GATE_SPINNING ||
        builder->seize_count != 0 || builder->interrupt_count != 0 ||
        builder->interrupt_event_stop_count != 0 ||
        atomic_load_explicit(builder->gate, memory_order_acquire) != 0U) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held builder is not at its seize boundary");
    }
    code = v4_hb_verify_parent_namespace_boundary(builder, error);
    if (code != V4_HB_OK) {
        return code;
    }
    if (ptrace(PTRACE_SEIZE, builder->pid, NULL,
               (void *)(uintptr_t)V4_HB_FIXED_PTRACE_OPTIONS_MASK) != 0) {
        int saved_errno = errno;
        return v4_hb_fail(
            error,
            (saved_errno == EINVAL || saved_errno == ENOSYS ||
             saved_errno == EPERM || saved_errno == EACCES) ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            saved_errno, "PTRACE_SEIZE with fixed V4 options failed"
        );
    }
    builder->seize_count = 1;
    if (ptrace(PTRACE_INTERRUPT, builder->pid, NULL, NULL) != 0) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "single PTRACE_INTERRUPT failed");
    }
    builder->interrupt_count = 1;
    code = v4_hb_waitid_pidfd_ptrace_event(
        builder, PTRACE_EVENT_STOP, error
    );
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    do {
        waited = waitpid(builder->pid, &status, __WALL | WNOHANG);
    } while (waited < 0 && errno == EINTR);
    if (waited == builder->pid && WIFSTOPPED(status)) {
        builder->held_stop_consumed = 1;
    }
    if (waited != builder->pid || !WIFSTOPPED(status) ||
        WSTOPSIG(status) != SIGTRAP ||
        (unsigned int)status >> 16 != PTRACE_EVENT_STOP) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR,
                          waited < 0 ? errno : EAGAIN,
                          "unexpected initial ptrace wait status");
    }
    memset(&builder->interrupt_siginfo, 0,
           sizeof(builder->interrupt_siginfo));
    if (ptrace(PTRACE_GETSIGINFO, builder->pid, NULL,
               &builder->interrupt_siginfo) != 0) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "interrupt event siginfo is unavailable");
    }
    if (builder->interrupt_siginfo.si_signo != SIGTRAP) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "interrupt event siginfo signal mismatch");
    }
    code = v4_hb_read_start_ticks(
        builder, builder->pid, &current_start_ticks, error
    );
    if (code != V4_HB_OK || current_start_ticks != builder->start_ticks) {
        builder->state = V4_HB_POISONED;
        if (code == V4_HB_OK) {
            (void)v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                             "builder identity changed at interrupt stop");
        }
        return code == V4_HB_UNSUPPORTED ? V4_HB_UNSUPPORTED : V4_HB_ERROR;
    }
    code = v4_hb_configure_child_id_maps(builder, error);
    if (code == V4_HB_OK) {
        builder->uid_map.inside_id = 0U;
        builder->uid_map.outside_id =
            (uint32_t)builder->observer_effective_uid;
        builder->uid_map.length = 1U;
        builder->gid_map.inside_id = 0U;
        builder->gid_map.outside_id =
            (uint32_t)builder->observer_effective_gid;
        builder->gid_map.length = 1U;
        code = v4_hb_capture_namespace_set(
            builder, builder->pid, builder->child_namespaces,
            builder->child_namespace_guards, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_read_child_nspid(
            builder, &builder->child_nspid, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_verify_namespace_boundary(builder, error);
    }
    if (code == V4_HB_OK) {
        code = v4_hb_verify_root_inheritance(builder, true, error);
    }
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    builder->root_inheritance_verified = true;
    builder->raw_interrupt_wait_status = status;
    builder->interrupt_event_stop_count = 1;
    builder->state = V4_HB_INTERRUPT_HELD;
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    return v4_hb_builder_snapshot(builder, held_snapshot, error);
}

void
v4_hb_bound_root_walks_destroy(struct v4_hb_bound_root_walks *walks)
{
    if (walks == NULL) {
        return;
    }
    v4_orw_walk_result_destroy(&walks->input_root);
    v4_orw_walk_result_destroy(&walks->output_root);
}

int
v4_hb_builder_run_bound_root_walks(
    struct v4_hb_builder *builder,
    struct v4_hb_bound_root_walks *walks,
    struct v4_hb_error *error
)
{
    struct v4_orw_error walk_error;
    int code;

    v4_hb_error_clear(error);
    if (walks == NULL || builder == NULL ||
        builder->state != V4_HB_INTERRUPT_HELD) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "bound root walks are not at the held boundary");
    }
    memset(walks, 0, sizeof(*walks));
    walks->input_root.root_walk_descriptor.fd = -1;
    walks->output_root.root_walk_descriptor.fd = -1;
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    code = v4_orw_input_root_walk(
        &builder->root_config.input_root,
        &builder->root_config.output_root,
        &builder->root_config.logical_ledger,
        &walks->input_root, &walk_error
    );
    if (code != V4_ORW_OK) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(
            error,
            code == V4_ORW_UNSUPPORTED ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            walk_error.saved_errno,
            "held input-root walk failed: %s", walk_error.message
        );
    }
    if (walks->input_root.declared_mount_edge_count != 1U) {
        v4_hb_bound_root_walks_destroy(walks);
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held input root lacks its one output mount edge");
    }
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        v4_hb_bound_root_walks_destroy(walks);
        builder->state = V4_HB_POISONED;
        return code;
    }
    code = v4_orw_output_root_walk(
        &builder->root_config.output_root,
        &builder->root_config.logical_ledger,
        &walks->output_root, &walk_error
    );
    if (code != V4_ORW_OK) {
        v4_hb_bound_root_walks_destroy(walks);
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(
            error,
            code == V4_ORW_UNSUPPORTED ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            walk_error.saved_errno,
            "held output-root pre-walk failed: %s", walk_error.message
        );
    }
    if (walks->output_root.entry_count != 0 ||
        walks->output_root.total_relative_bytes != 0 ||
        walks->output_root.directory_eof_count != 1 ||
        walks->output_root.opened_descriptor_count != 1) {
        v4_hb_bound_root_walks_destroy(walks);
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held output-root pre-walk is not exactly empty");
    }
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        v4_hb_bound_root_walks_destroy(walks);
        builder->state = V4_HB_POISONED;
        return code;
    }
    builder->state = V4_HB_BOUND_ROOT_WALKS_COMPLETE;
    return V4_HB_OK;
}

static int
v4_hb_waitid_pidfd_exit(
    const struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    siginfo_t information;
    unsigned int attempt;

    for (attempt = 0; attempt < V4_HB_WAIT_ATTEMPT_LIMIT; ++attempt) {
        memset(&information, 0, sizeof(information));
        if (waitid(P_PIDFD, (id_t)builder->pidfd, &information,
                   WEXITED | WNOWAIT | WNOHANG) != 0) {
            int saved_errno = errno;
            return v4_hb_fail(
                error,
                (saved_errno == EINVAL || saved_errno == ENOSYS ||
                 saved_errno == EPERM) ? V4_HB_UNSUPPORTED : V4_HB_ERROR,
                saved_errno, "pidfd terminal observation failed"
            );
        }
        if (information.si_pid != 0) {
            break;
        }
        if (poll(NULL, 0, V4_HB_WAIT_POLL_MILLISECONDS) < 0 &&
            errno != EINTR) {
            return v4_hb_fail(error, V4_HB_ERROR, errno,
                              "pidfd terminal wait pause failed");
        }
    }
    if (attempt == V4_HB_WAIT_ATTEMPT_LIMIT) {
        return v4_hb_fail(error, V4_HB_ERROR, ETIMEDOUT,
                          "pidfd terminal wait timed out");
    }
    if (information.si_pid != builder->pid ||
        information.si_code != CLD_EXITED || information.si_status != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "pidfd terminal observation mismatch");
    }
    return V4_HB_OK;
}

int
v4_hb_builder_release_and_reap(
    struct v4_hb_builder *builder,
    struct v4_hb_completion *completion,
    struct v4_hb_error *error
)
{
    uint64_t current_start_ticks;
    unsigned long event_message = 0UL;
    unsigned int old_gate;
    int status;
    int extra_status;
    pid_t waited;
    struct pollfd poll_descriptor;
    int code;

    v4_hb_error_clear(error);
    if (builder == NULL || completion == NULL ||
        builder->state != V4_HB_BOUND_ROOT_WALKS_COMPLETE) {
        return v4_hb_fail(error, V4_HB_ERROR, EPERM,
                          "gate release requires both completed root walks");
    }
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    memset(completion, 0, sizeof(*completion));
    old_gate = atomic_exchange_explicit(
        builder->gate, 1U, memory_order_release
    );
    if (old_gate != 0U) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder gate was already released");
    }
    builder->state = V4_HB_RELEASED;
    if (ptrace(PTRACE_CONT, builder->pid, NULL, NULL) != 0) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "held-builder release resume failed");
    }
    builder->resume_count = 1;
    builder->held_stop_consumed = 0;
    code = v4_hb_waitid_pidfd_ptrace_event(
        builder, PTRACE_EVENT_EXIT, error
    );
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    do {
        waited = waitpid(builder->pid, &status, __WALL | WNOHANG);
    } while (waited < 0 && errno == EINTR);
    if (waited == builder->pid && WIFSTOPPED(status)) {
        builder->held_stop_consumed = 1;
    }
    if (waited != builder->pid || !WIFSTOPPED(status) ||
        WSTOPSIG(status) != SIGTRAP ||
        (unsigned int)status >> 16 != PTRACE_EVENT_EXIT) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR,
                          waited < 0 ? errno : EAGAIN,
                          "unexpected held-builder release stop or exit");
    }
    if (ptrace(PTRACE_GETEVENTMSG, builder->pid, NULL, &event_message) != 0) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "held-builder PTRACE_GETEVENTMSG failed");
    }
    if (event_message != 0UL) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder exit event message mismatch");
    }
    code = v4_hb_read_start_ticks(
        builder, builder->pid, &current_start_ticks, error
    );
    if (code != V4_HB_OK || current_start_ticks != builder->start_ticks) {
        builder->state = V4_HB_POISONED;
        if (code != V4_HB_OK) {
            return code;
        }
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder exit event identity mismatch");
    }
    completion->raw_exit_event_wait_status = status;
    completion->exit_event_message = event_message;
    if (ptrace(PTRACE_CONT, builder->pid, NULL, NULL) != 0) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "held-builder final exit resume failed");
    }
    builder->resume_count = 2;
    builder->held_stop_consumed = 0;
    code = v4_hb_waitid_pidfd_exit(builder, error);
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    do {
        waited = waitpid(builder->pid, &status, __WALL | WNOHANG);
    } while (waited < 0 && errno == EINTR);
    if (waited != builder->pid || !WIFEXITED(status) ||
        WEXITSTATUS(status) != 0) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR,
                          waited < 0 ? errno : EAGAIN,
                          "held-builder terminal wait mismatch");
    }
    completion->raw_final_wait_status = status;
    completion->exit_code = WEXITSTATUS(status);
    do {
        waited = waitpid(builder->pid, &extra_status, __WALL | WNOHANG);
    } while (waited < 0 && errno == EINTR);
    if (waited >= 0 || errno != ECHILD) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR,
                          waited < 0 ? errno : EINVAL,
                          "held-builder wait set was not exhausted");
    }
    poll_descriptor.fd = builder->pidfd;
    poll_descriptor.events = POLLIN;
    poll_descriptor.revents = 0;
    {
        int poll_result = poll(&poll_descriptor, 1, 0);
        if (poll_result != 1 ||
            (poll_descriptor.revents & POLLIN) == 0) {
            builder->state = V4_HB_POISONED;
            return v4_hb_fail(
                error, V4_HB_ERROR, poll_result < 0 ? errno : EINVAL,
                "reaped builder pidfd is not terminal"
            );
        }
    }
    code = v4_hb_verify_pidfd_alias(builder, error);
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    return v4_hb_close_resources_checked(builder, error);
}

int
v4_hb_builder_abort(
    struct v4_hb_builder *builder,
    struct v4_hb_error *error
)
{
    unsigned int waits = 0;
    unsigned int idle_attempts = 0;
    bool terminal = false;
    int status;

    v4_hb_error_clear(error);
    if (builder == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder abort input is null");
    }
    if (builder->state == V4_HB_CLOSED) {
        return V4_HB_OK;
    }
    if (builder->pidfd_guard < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held-builder abort pidfd guard is unavailable");
    }
    if (syscall(SYS_pidfd_send_signal, builder->pidfd_guard,
                SIGKILL, NULL, 0) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "held-builder abort signal failed");
    }
    if (builder->held_stop_consumed != 0) {
        if (ptrace(PTRACE_CONT, builder->pid, NULL,
                   (void *)(uintptr_t)SIGKILL) != 0 && errno != ESRCH) {
            return v4_hb_fail(error, V4_HB_ERROR, errno,
                              "held-builder abort initial resume failed");
        }
        builder->held_stop_consumed = 0;
    }
    while (!terminal && waits < V4_HB_ABORT_WAIT_LIMIT) {
        pid_t waited;
        do {
            waited = waitpid(
                builder->pid, &status, __WALL | WNOHANG
            );
        } while (waited < 0 && errno == EINTR);
        if (waited == 0) {
            ++idle_attempts;
            if (idle_attempts >= V4_HB_WAIT_ATTEMPT_LIMIT) {
                return v4_hb_fail(error, V4_HB_ERROR, ETIMEDOUT,
                                  "held-builder abort wait timed out");
            }
            if (poll(NULL, 0, V4_HB_WAIT_POLL_MILLISECONDS) < 0 &&
                errno != EINTR) {
                return v4_hb_fail(error, V4_HB_ERROR, errno,
                                  "held-builder abort wait pause failed");
            }
            continue;
        }
        if (waited != builder->pid) {
            return v4_hb_fail(error, V4_HB_ERROR,
                              waited < 0 ? errno : EINVAL,
                              "held-builder abort wait failed");
        }
        idle_attempts = 0;
        ++waits;
        if (WIFEXITED(status) || WIFSIGNALED(status)) {
            terminal = true;
        } else if (WIFSTOPPED(status)) {
            if (ptrace(PTRACE_CONT, builder->pid, NULL,
                       (void *)(uintptr_t)SIGKILL) != 0 && errno != ESRCH) {
                return v4_hb_fail(error, V4_HB_ERROR, errno,
                                  "held-builder abort resume failed");
            }
            builder->held_stop_consumed = 0;
        } else {
            return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                              "unexpected held-builder abort wait status");
        }
    }
    if (!terminal) {
        return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                          "held-builder abort wait cap exceeded");
    }
    {
        int extra_status;
        pid_t extra_wait;
        struct pollfd poll_descriptor;

        do {
            extra_wait = waitpid(
                builder->pid, &extra_status, __WALL | WNOHANG
            );
        } while (extra_wait < 0 && errno == EINTR);
        if (extra_wait >= 0 || errno != ECHILD) {
            return v4_hb_fail(
                error, V4_HB_ERROR,
                extra_wait < 0 ? errno : EINVAL,
                "held-builder abort wait set was not exhausted"
            );
        }
        poll_descriptor.fd = builder->pidfd;
        poll_descriptor.events = POLLIN;
        poll_descriptor.revents = 0;
        {
            int poll_result = poll(&poll_descriptor, 1, 0);
            if (poll_result != 1 ||
                (poll_descriptor.revents & POLLIN) == 0) {
                return v4_hb_fail(
                    error, V4_HB_ERROR,
                    poll_result < 0 ? errno : EINVAL,
                    "aborted builder pidfd is not terminal"
                );
            }
        }
    }
    return v4_hb_close_resources_checked(builder, error);
}

void
v4_hb_builder_destroy(struct v4_hb_builder *builder)
{
    if (builder == NULL) {
        return;
    }
    if (builder->state != V4_HB_CLOSED) {
        struct v4_hb_error ignored;
        (void)v4_hb_builder_abort(builder, &ignored);
    }
    if (builder->state == V4_HB_CLOSED) {
        free(builder);
    }
}
