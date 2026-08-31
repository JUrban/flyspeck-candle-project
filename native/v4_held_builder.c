#define _GNU_SOURCE

#include "v4_held_builder.h"

#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/kcmp.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <sys/syscall.h>
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
#define V4_HB_ABORT_WAIT_LIMIT 16U
#define V4_HB_WAIT_ATTEMPT_LIMIT 5000U
#define V4_HB_WAIT_POLL_MILLISECONDS 1
#define V4_HB_PTRACE_GET_SYSCALL_INFO 0x420e
#define V4_HB_PTRACE_SYSCALL_INFO_NONE 0U

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

static int
v4_hb_read_bounded_proc(
    const char *path,
    char *buffer,
    size_t capacity,
    size_t *used,
    struct v4_hb_error *error
)
{
    size_t offset = 0;
    int fd = open(path, O_RDONLY | O_CLOEXEC);

    if (fd < 0) {
        int saved_errno = errno;
        int code = (saved_errno == ENOENT || saved_errno == EACCES ||
                    saved_errno == EPERM) ?
            V4_HB_UNSUPPORTED : V4_HB_ERROR;
        return v4_hb_fail(error, code, saved_errno,
                          "required proc observation is unavailable");
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
                              "required proc observation read failed");
        }
        if (count == 0) {
            break;
        }
        offset += (size_t)count;
        if (offset == capacity) {
            char extra;
            int close_errno;
            int close_result;
            int extra_errno;
            ssize_t extra_count;
            do {
                extra_count = read(fd, &extra, 1);
            } while (extra_count < 0 && errno == EINTR);
            extra_errno = extra_count < 0 ? errno : 0;
            close_result = close(fd);
            close_errno = close_result != 0 ? errno : 0;
            if (extra_count < 0) {
                return v4_hb_fail(
                    error, V4_HB_ERROR, extra_errno,
                    "required proc observation cap probe failed"
                );
            }
            if (extra_count > 0) {
                return v4_hb_fail(error, V4_HB_ERROR, EOVERFLOW,
                                  "required proc observation exceeds cap");
            }
            if (close_result != 0) {
                return v4_hb_fail(error, V4_HB_ERROR, close_errno,
                                  "required proc observation close failed");
            }
            *used = offset;
            return V4_HB_OK;
        }
    }
    if (close(fd) != 0) {
        return v4_hb_fail(error, V4_HB_ERROR, errno,
                          "required proc observation close failed");
    }
    *used = offset;
    return V4_HB_OK;
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

static int
v4_hb_read_start_ticks(
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

    if (pid <= 0 || start_ticks == NULL ||
        snprintf(path, sizeof(path), "/proc/%ld/stat", (long)pid) < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "malformed proc stat request");
    }
    code = v4_hb_read_bounded_proc(
        path, buffer, V4_HB_PROC_STAT_MAX_BYTES, &used, error
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
    if (builder->pidfd >= 0) {
        (void)close(builder->pidfd);
        builder->pidfd = -1;
    }
    if (builder->pidfd_guard >= 0) {
        (void)close(builder->pidfd_guard);
        builder->pidfd_guard = -1;
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
    struct v4_hb_builder **builder_out,
    struct v4_hb_error *error
)
{
    struct v4_hb_builder *builder;
    uint64_t second_start_ticks;
    pid_t pid;
    int pidfd;
    int code;

    v4_hb_error_clear(error);
    if (builder_out == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "builder output is null");
    }
    *builder_out = NULL;
    builder = calloc(1, sizeof(*builder));
    if (builder == NULL) {
        return v4_hb_fail(error, V4_HB_ERROR, ENOMEM,
                          "cannot allocate held-builder state");
    }
    builder->pidfd = -1;
    builder->pidfd_guard = -1;
    builder->gate_mapping_bytes = sizeof(*builder->gate);
    builder->gate = mmap(
        NULL, builder->gate_mapping_bytes, PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_ANONYMOUS, -1, 0
    );
    if (builder->gate == MAP_FAILED) {
        int saved_errno = errno;
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
        SYS_clone, (unsigned long)SIGCHLD, NULL, NULL, NULL, 0UL
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
        code = v4_hb_pidfd_send(pidfd, 0, error);
    }
    if (code == V4_HB_OK) {
        code = v4_hb_read_start_ticks(
            pid, &builder->start_ticks, error
        );
    }
    if (code == V4_HB_OK) {
        code = v4_hb_read_start_ticks(pid, &second_start_ticks, error);
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
    return V4_HB_OK;
}

static bool
v4_hb_exact_snapshot(
    const struct v4_hb_snapshot *first,
    const struct v4_hb_snapshot *second
)
{
    return first->pid == second->pid &&
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
        first->held_stop_consumed == second->held_stop_consumed;
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

    if (snprintf(path, sizeof(path), "/proc/%ld/status",
                 (long)builder->pid) < 0) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "cannot format builder proc status path");
    }
    code = v4_hb_read_bounded_proc(
        path, buffer, V4_HB_PROC_STATUS_MAX_BYTES, &used, error
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
         builder->state != V4_HB_EMPTY_PREWALK_COMPLETE) ||
        builder->pid <= 0 || builder->pidfd < 0 ||
        builder->start_ticks == 0 || builder->gate == MAP_FAILED ||
        atomic_load_explicit(builder->gate, memory_order_acquire) != 0U ||
        builder->seize_count != 1 || builder->interrupt_count != 1 ||
        builder->interrupt_event_stop_count != 1 ||
        builder->resume_count != 0 ||
        builder->held_stop_consumed != 1 ||
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
        builder->pid, &current_start_ticks, error
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
        builder->pid, &current_start_ticks, error
    );
    if (code != V4_HB_OK || current_start_ticks != builder->start_ticks) {
        builder->state = V4_HB_POISONED;
        if (code == V4_HB_OK) {
            (void)v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                             "builder identity changed at interrupt stop");
        }
        return code == V4_HB_UNSUPPORTED ? V4_HB_UNSUPPORTED : V4_HB_ERROR;
    }
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

int
v4_hb_builder_run_empty_prewalk(
    struct v4_hb_builder *builder,
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_walk_result *walk,
    struct v4_hb_error *error
)
{
    struct v4_orw_error walk_error;
    int code;

    v4_hb_error_clear(error);
    if (walk == NULL || builder == NULL ||
        builder->state != V4_HB_INTERRUPT_HELD) {
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "empty pre-walk is not at the held boundary");
    }
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        builder->state = V4_HB_POISONED;
        return code;
    }
    code = v4_orw_output_root_walk(anchor, ledger, walk, &walk_error);
    if (code != V4_ORW_OK) {
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(
            error,
            code == V4_ORW_UNSUPPORTED ?
                V4_HB_UNSUPPORTED : V4_HB_ERROR,
            walk_error.saved_errno,
            "held empty pre-walk failed: %s", walk_error.message
        );
    }
    if (walk->entry_count != 0 || walk->total_relative_bytes != 0 ||
        walk->directory_eof_count != 1 ||
        walk->opened_descriptor_count != 1) {
        v4_orw_walk_result_destroy(walk);
        builder->state = V4_HB_POISONED;
        return v4_hb_fail(error, V4_HB_ERROR, EINVAL,
                          "held output-root pre-walk is not exactly empty");
    }
    code = v4_hb_verify_held_internal(builder, error);
    if (code != V4_HB_OK) {
        v4_orw_walk_result_destroy(walk);
        builder->state = V4_HB_POISONED;
        return code;
    }
    builder->state = V4_HB_EMPTY_PREWALK_COMPLETE;
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
        builder->state != V4_HB_EMPTY_PREWALK_COMPLETE) {
        return v4_hb_fail(error, V4_HB_ERROR, EPERM,
                          "gate release requires a completed held pre-walk");
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
        builder->pid, &current_start_ticks, error
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
