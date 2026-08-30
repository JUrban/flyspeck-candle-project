#define _GNU_SOURCE

#include "v4_output_root_walk.h"

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/kcmp.h>
#include <linux/openat2.h>
#include <linux/stat.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#ifndef SYS_getdents64
#error "SYS_getdents64 is required"
#endif
#ifndef SYS_kcmp
#error "SYS_kcmp is required"
#endif
#ifndef SYS_openat2
#error "SYS_openat2 is required"
#endif
#ifndef SYS_statx
#error "SYS_statx is required"
#endif

#define V4_ORW_DIRENT_BUFFER_BYTES 32768U
#define V4_ORW_FDINFO_MAX_BYTES 4096U

struct v4_orw_linux_dirent64 {
    uint64_t d_ino;
    int64_t d_off;
    unsigned short d_reclen;
    unsigned char d_type;
    char d_name[];
};

struct v4_orw_name_vector {
    char **names;
    size_t count;
    size_t capacity;
    size_t total_name_bytes;
};

struct v4_orw_pending_vector {
    char **paths;
    size_t count;
    size_t capacity;
    size_t total_path_bytes;
};

static int
v4_orw_fail(
    struct v4_orw_error *error,
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
v4_orw_error_clear(struct v4_orw_error *error)
{
    if (error != NULL) {
        error->saved_errno = 0;
        error->message[0] = '\0';
    }
}

static bool
v4_orw_add_overflows_u64(uint64_t value)
{
    return value == 0 || value == UINT64_MAX;
}

int
v4_orw_logical_ledger_init(
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_error *error
)
{
    v4_orw_error_clear(error);
    if (ledger == NULL) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "logical ledger is null");
    }
    ledger->next_fd_generation = 1;
    ledger->next_ofd_id = 1;
    ledger->next_ofd_generation = 1;
    return V4_ORW_OK;
}

static int
v4_orw_allocate_new_ofd(
    int fd,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_logical_descriptor *descriptor,
    struct v4_orw_error *error
)
{
    if (ledger == NULL || descriptor == NULL || fd < 0 ||
        v4_orw_add_overflows_u64(ledger->next_fd_generation) ||
        v4_orw_add_overflows_u64(ledger->next_ofd_id) ||
        v4_orw_add_overflows_u64(ledger->next_ofd_generation)) {
        return v4_orw_fail(error, V4_ORW_ERROR, EOVERFLOW,
                           "logical descriptor ledger exhausted or malformed");
    }
    descriptor->fd = fd;
    descriptor->fd_generation = ledger->next_fd_generation++;
    descriptor->logical_ofd_id = ledger->next_ofd_id++;
    descriptor->logical_ofd_generation =
        ledger->next_ofd_generation++;
    return V4_ORW_OK;
}

static int
v4_orw_allocate_duplicate(
    int fd,
    const struct v4_orw_logical_descriptor *source,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_logical_descriptor *descriptor,
    struct v4_orw_error *error
)
{
    if (ledger == NULL || source == NULL || descriptor == NULL || fd < 0 ||
        source->logical_ofd_id == 0 ||
        source->logical_ofd_generation == 0 ||
        v4_orw_add_overflows_u64(ledger->next_fd_generation)) {
        return v4_orw_fail(error, V4_ORW_ERROR, EOVERFLOW,
                           "duplicate logical descriptor ledger malformed");
    }
    descriptor->fd = fd;
    descriptor->fd_generation = ledger->next_fd_generation++;
    descriptor->logical_ofd_id = source->logical_ofd_id;
    descriptor->logical_ofd_generation = source->logical_ofd_generation;
    return V4_ORW_OK;
}

static int
v4_orw_openat2(
    int directory_fd,
    const char *path,
    uint64_t flags,
    uint64_t resolve,
    struct v4_orw_error *error
)
{
    struct open_how how;
    int fd;

    memset(&how, 0, sizeof(how));
    how.flags = flags;
    how.resolve = resolve;
    fd = (int)syscall(SYS_openat2, directory_fd, path, &how, sizeof(how));
    if (fd >= 0) {
        return fd;
    }
    if (errno == ENOSYS) {
        (void)v4_orw_fail(error, V4_ORW_UNSUPPORTED, errno,
                          "openat2 is unavailable");
        return -V4_ORW_UNSUPPORTED;
    } else {
        (void)v4_orw_fail(error, V4_ORW_ERROR, errno,
                          "openat2 rejected descriptor-rooted path");
    }
    return -V4_ORW_ERROR;
}

static bool
v4_orw_safe_anchor_name(const char *relative)
{
    size_t index;
    size_t length;

    if (relative == NULL) {
        return false;
    }
    length = strlen(relative);
    if (length == 0 || length > V4_ORW_MAX_COMPONENT_BYTES ||
        strcmp(relative, ".") == 0 || strcmp(relative, "..") == 0) {
        return false;
    }
    for (index = 0; index < length; ++index) {
        unsigned char character = (unsigned char)relative[index];
        if (character < 0x20 || character > 0x7e || character == '/' ||
            character == '\\') {
            return false;
        }
    }
    return true;
}

static int
v4_orw_parse_u64(
    const char *text,
    int base,
    uint64_t *value
)
{
    char *end = NULL;
    const char *cursor;
    unsigned long long parsed;

    if (text == NULL || *text == '\0') {
        return -1;
    }
    for (cursor = text; *cursor != '\0'; ++cursor) {
        if ((base == 10 && (*cursor < '0' || *cursor > '9')) ||
            (base == 8 && (*cursor < '0' || *cursor > '7'))) {
            return -1;
        }
    }
    errno = 0;
    parsed = strtoull(text, &end, base);
    if (errno != 0 || end == text || *end != '\0') {
        return -1;
    }
    *value = (uint64_t)parsed;
    return 0;
}

static int
v4_orw_read_fdinfo(
    int fd,
    struct v4_orw_fdinfo_projection *projection,
    struct v4_orw_error *error
)
{
    char path[64];
    char buffer[V4_ORW_FDINFO_MAX_BYTES + 1];
    bool seen_position = false;
    bool seen_flags = false;
    bool seen_mount_id = false;
    bool seen_inode = false;
    size_t used = 0;
    int info_fd;

    if (snprintf(path, sizeof(path), "/proc/self/fdinfo/%d", fd) < 0) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "cannot format fdinfo path");
    }
    info_fd = open(path, O_RDONLY | O_CLOEXEC);
    if (info_fd < 0) {
        int saved_errno = errno;
        int result = (saved_errno == ENOENT || saved_errno == EACCES) ?
            V4_ORW_UNSUPPORTED : V4_ORW_ERROR;
        return v4_orw_fail(error, result, saved_errno,
                           "cannot open exact fdinfo projection");
    }
    for (;;) {
        ssize_t count = read(info_fd, buffer + used,
                             V4_ORW_FDINFO_MAX_BYTES - used);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            int saved_errno = errno;
            (void)close(info_fd);
            return v4_orw_fail(error, V4_ORW_ERROR, saved_errno,
                               "cannot read fdinfo projection");
        }
        if (count == 0) {
            break;
        }
        used += (size_t)count;
        if (used == V4_ORW_FDINFO_MAX_BYTES) {
            char extra;
            ssize_t extra_count = read(info_fd, &extra, 1);
            (void)close(info_fd);
            if (extra_count != 0) {
                return v4_orw_fail(error, V4_ORW_ERROR, EOVERFLOW,
                                   "fdinfo projection exceeds cap");
            }
            break;
        }
    }
    if (close(info_fd) != 0) {
        return v4_orw_fail(error, V4_ORW_ERROR, errno,
                           "cannot close fdinfo projection");
    }
    buffer[used] = '\0';

    {
        char *cursor = buffer;
        while (*cursor != '\0') {
            char *newline = strchr(cursor, '\n');
            char *separator;
            uint64_t parsed;
            int base = 10;
            bool *seen = NULL;
            uint64_t *target = NULL;

            if (newline == NULL) {
                return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                   "unterminated fdinfo projection line");
            }
            *newline = '\0';
            separator = strchr(cursor, ':');
            if (separator == NULL) {
                return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                   "malformed fdinfo projection line");
            }
            *separator = '\0';
            ++separator;
            while (*separator == ' ' || *separator == '\t') {
                ++separator;
            }
            if (strcmp(cursor, "pos") == 0) {
                seen = &seen_position;
                target = &projection->position;
            } else if (strcmp(cursor, "flags") == 0) {
                seen = &seen_flags;
                target = &projection->flags;
                base = 8;
            } else if (strcmp(cursor, "mnt_id") == 0) {
                seen = &seen_mount_id;
                target = &projection->mount_id;
            } else if (strcmp(cursor, "ino") == 0) {
                seen = &seen_inode;
                target = &projection->inode;
            } else {
                return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                   "unknown fdinfo projection field");
            }
            if (*seen || v4_orw_parse_u64(separator, base, &parsed) != 0) {
                return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                   "duplicate or malformed fdinfo field");
            }
            *seen = true;
            *target = parsed;
            cursor = newline + 1;
        }
    }
    if (!seen_position || !seen_flags || !seen_mount_id || !seen_inode) {
        return v4_orw_fail(error, V4_ORW_UNSUPPORTED, ENOTSUP,
                           "required fdinfo projection field is unavailable");
    }
    return V4_ORW_OK;
}

static int
v4_orw_snapshot_fd(
    int fd,
    struct v4_orw_kernel_projection *projection,
    struct v4_orw_error *error
)
{
    struct stat status;
    struct statx extended;
    int fd_flags;
    int status_flags;
    int result;
    uint64_t expected_fdinfo_flags;

    memset(projection, 0, sizeof(*projection));
    fd_flags = fcntl(fd, F_GETFD);
    if (fd_flags < 0) {
        return v4_orw_fail(error, V4_ORW_ERROR, errno,
                           "F_GETFD failed for retained descriptor");
    }
    status_flags = fcntl(fd, F_GETFL);
    if (status_flags < 0) {
        return v4_orw_fail(error, V4_ORW_ERROR, errno,
                           "F_GETFL failed for retained descriptor");
    }
    if (fstat(fd, &status) != 0) {
        return v4_orw_fail(error, V4_ORW_ERROR, errno,
                           "fstat failed for retained descriptor");
    }
    memset(&extended, 0, sizeof(extended));
    if (syscall(SYS_statx, fd, "",
                AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT,
                STATX_BASIC_STATS | STATX_MNT_ID, &extended) != 0) {
        int saved_errno = errno;
        int code = saved_errno == ENOSYS ?
            V4_ORW_UNSUPPORTED : V4_ORW_ERROR;
        return v4_orw_fail(error, code, saved_errno,
                           "statx AT_EMPTY_PATH failed");
    }
    if ((extended.stx_mask & (STATX_TYPE | STATX_MODE | STATX_NLINK |
                              STATX_INO | STATX_SIZE | STATX_MTIME |
                              STATX_CTIME | STATX_MNT_ID)) !=
        (STATX_TYPE | STATX_MODE | STATX_NLINK | STATX_INO | STATX_SIZE |
         STATX_MTIME | STATX_CTIME | STATX_MNT_ID)) {
        return v4_orw_fail(error, V4_ORW_UNSUPPORTED, ENOTSUP,
                           "statx mount/object fields are unavailable");
    }
    if ((uint64_t)status.st_ino != extended.stx_ino ||
        (uint64_t)status.st_nlink != extended.stx_nlink ||
        (uint64_t)status.st_mode != extended.stx_mode ||
        (uint64_t)status.st_size != extended.stx_size ||
        (int64_t)status.st_mtim.tv_sec != extended.stx_mtime.tv_sec ||
        (uint32_t)status.st_mtim.tv_nsec != extended.stx_mtime.tv_nsec ||
        (int64_t)status.st_ctim.tv_sec != extended.stx_ctime.tv_sec ||
        (uint32_t)status.st_ctim.tv_nsec != extended.stx_ctime.tv_nsec ||
        major(status.st_dev) != extended.stx_dev_major ||
        minor(status.st_dev) != extended.stx_dev_minor ||
        extended.stx_mnt_id == 0) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "fstat/statx projection mismatch");
    }

    projection->st_dev = (uint64_t)status.st_dev;
    projection->st_ino = (uint64_t)status.st_ino;
    projection->st_nlink = (uint64_t)status.st_nlink;
    projection->st_mode = (uint64_t)status.st_mode;
    projection->st_size = (int64_t)status.st_size;
    projection->mtime_seconds = (int64_t)status.st_mtim.tv_sec;
    projection->mtime_nanoseconds = (uint64_t)status.st_mtim.tv_nsec;
    projection->ctime_seconds = (int64_t)status.st_ctim.tv_sec;
    projection->ctime_nanoseconds = (uint64_t)status.st_ctim.tv_nsec;
    projection->statx_dev_major = extended.stx_dev_major;
    projection->statx_dev_minor = extended.stx_dev_minor;
    projection->mount_id = extended.stx_mnt_id;
    projection->fd_flags = (uint32_t)fd_flags;
    projection->status_flags = (uint64_t)(unsigned int)status_flags;
    result = v4_orw_read_fdinfo(fd, &projection->fdinfo, error);
    if (result != V4_ORW_OK) {
        return result;
    }
    expected_fdinfo_flags = projection->status_flags;
    if ((projection->fd_flags & FD_CLOEXEC) != 0) {
        expected_fdinfo_flags |= O_CLOEXEC;
    }
    if (projection->fdinfo.flags != expected_fdinfo_flags ||
        projection->fdinfo.mount_id != projection->mount_id ||
        projection->fdinfo.inode != projection->st_ino) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "fcntl/fstat/statx/fdinfo projection mismatch");
    }
    return V4_ORW_OK;
}

static int
v4_orw_same_open_file_description(
    int first_fd,
    int second_fd,
    struct v4_orw_error *error
)
{
    long comparison = syscall(SYS_kcmp, getpid(), getpid(), KCMP_FILE,
                              (unsigned long)first_fd,
                              (unsigned long)second_fd);
    if (comparison == 0) {
        return V4_ORW_OK;
    }
    if (comparison < 0) {
        int saved_errno = errno;
        int result = (saved_errno == ENOSYS || saved_errno == EPERM ||
                      saved_errno == EACCES) ?
            V4_ORW_UNSUPPORTED : V4_ORW_ERROR;
        return v4_orw_fail(error, result, saved_errno,
                           "KCMP_FILE cannot verify the retained OFD alias");
    }
    return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                       "retained anchor no longer names its logical OFD");
}

static bool
v4_orw_same_anchor_projection(
    const struct v4_orw_kernel_projection *first,
    const struct v4_orw_kernel_projection *second
)
{
    return first->st_dev == second->st_dev &&
        first->st_ino == second->st_ino &&
        first->st_mode == second->st_mode &&
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

int
v4_orw_output_anchor_snapshot(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_kernel_projection *projection,
    struct v4_orw_error *error
)
{
    if (anchor == NULL || projection == NULL || !anchor->live ||
        anchor->primary.fd < 0 || anchor->guard.fd < 0 ||
        anchor->primary.fd_generation == 0 ||
        anchor->primary.logical_ofd_id == 0 ||
        anchor->primary.logical_ofd_generation == 0 ||
        anchor->guard.fd_generation == 0 ||
        anchor->guard.logical_ofd_id != anchor->primary.logical_ofd_id ||
        anchor->guard.logical_ofd_generation !=
            anchor->primary.logical_ofd_generation) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "retained logical output anchor is malformed");
    }
    return v4_orw_snapshot_fd(anchor->primary.fd, projection, error);
}

int
v4_orw_output_anchor_revalidate(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_error *error
)
{
    struct v4_orw_kernel_projection current;
    struct v4_orw_kernel_projection guard_current;
    int result;

    v4_orw_error_clear(error);
    result = v4_orw_output_anchor_snapshot(anchor, &current, error);
    if (result != V4_ORW_OK) {
        return result;
    }
    result = v4_orw_snapshot_fd(anchor->guard.fd, &guard_current, error);
    if (result != V4_ORW_OK) {
        return result;
    }
    if (!S_ISDIR((mode_t)current.st_mode) ||
        (current.status_flags & O_PATH) != O_PATH ||
        (current.status_flags & O_DIRECTORY) != O_DIRECTORY ||
        (current.status_flags & O_NOFOLLOW) != O_NOFOLLOW ||
        current.fd_flags != FD_CLOEXEC ||
        guard_current.fd_flags != FD_CLOEXEC ||
        !v4_orw_same_anchor_projection(&anchor->initial_projection, &current) ||
        !v4_orw_same_anchor_projection(
            &anchor->guard_initial_projection, &guard_current
        ) ||
        !v4_orw_same_anchor_projection(&current, &guard_current)) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "retained output anchor projection changed");
    }
    return v4_orw_same_open_file_description(
        anchor->primary.fd, anchor->guard.fd, error
    );
}

int
v4_orw_output_anchor_open(
    int parent_fd,
    const char *relative,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_output_anchor *anchor,
    struct v4_orw_error *error
)
{
    int primary_fd;
    int guard_fd;
    int result;

    v4_orw_error_clear(error);
    if (parent_fd < 0 || ledger == NULL || anchor == NULL ||
        !v4_orw_safe_anchor_name(relative)) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "unsafe output-anchor relative name");
    }
    memset(anchor, 0, sizeof(*anchor));
    anchor->primary.fd = -1;
    anchor->guard.fd = -1;
    primary_fd = v4_orw_openat2(
        parent_fd, relative,
        O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC,
        RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS,
        error
    );
    if (primary_fd < 0) {
        return primary_fd == -V4_ORW_UNSUPPORTED ?
            V4_ORW_UNSUPPORTED : V4_ORW_ERROR;
    }
    result = v4_orw_allocate_new_ofd(
        primary_fd, ledger, &anchor->primary, error
    );
    if (result != V4_ORW_OK) {
        (void)close(primary_fd);
        memset(anchor, 0, sizeof(*anchor));
        anchor->primary.fd = -1;
        anchor->guard.fd = -1;
        return result;
    }
    guard_fd = fcntl(primary_fd, F_DUPFD_CLOEXEC, 3);
    if (guard_fd < 0) {
        int saved_errno = errno;
        (void)close(primary_fd);
        memset(anchor, 0, sizeof(*anchor));
        anchor->primary.fd = -1;
        anchor->guard.fd = -1;
        return v4_orw_fail(error, V4_ORW_ERROR, saved_errno,
                           "cannot create retained output-anchor guard");
    }
    result = v4_orw_allocate_duplicate(
        guard_fd, &anchor->primary, ledger, &anchor->guard, error
    );
    if (result != V4_ORW_OK) {
        (void)close(guard_fd);
        (void)close(primary_fd);
        memset(anchor, 0, sizeof(*anchor));
        anchor->primary.fd = -1;
        anchor->guard.fd = -1;
        return result;
    }
    anchor->live = 1;
    result = v4_orw_output_anchor_snapshot(
        anchor, &anchor->initial_projection, error
    );
    if (result == V4_ORW_OK) {
        result = v4_orw_snapshot_fd(
            anchor->guard.fd, &anchor->guard_initial_projection, error
        );
    }
    if (result == V4_ORW_OK &&
        (!S_ISDIR((mode_t)anchor->initial_projection.st_mode) ||
         (anchor->initial_projection.status_flags & O_PATH) != O_PATH ||
         (anchor->initial_projection.status_flags & O_DIRECTORY) !=
            O_DIRECTORY ||
         (anchor->initial_projection.status_flags & O_NOFOLLOW) != O_NOFOLLOW ||
         anchor->initial_projection.fd_flags != FD_CLOEXEC ||
         anchor->guard_initial_projection.fd_flags != FD_CLOEXEC ||
         !v4_orw_same_anchor_projection(
             &anchor->initial_projection,
             &anchor->guard_initial_projection))) {
        result = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                             "output anchor lacks exact O_PATH directory form");
    }
    if (result == V4_ORW_OK) {
        result = v4_orw_same_open_file_description(
            anchor->primary.fd, anchor->guard.fd, error
        );
    }
    if (result != V4_ORW_OK) {
        v4_orw_output_anchor_close(anchor);
    }
    return result;
}

static void
v4_orw_name_vector_destroy(struct v4_orw_name_vector *vector)
{
    size_t index;
    for (index = 0; index < vector->count; ++index) {
        free(vector->names[index]);
    }
    free(vector->names);
    memset(vector, 0, sizeof(*vector));
}

static int
v4_orw_name_compare(const void *left, const void *right)
{
    const char *const *left_name = left;
    const char *const *right_name = right;
    return strcmp(*left_name, *right_name);
}

static int
v4_orw_name_vector_append(
    struct v4_orw_name_vector *vector,
    const char *name,
    struct v4_orw_error *error
)
{
    char **grown;
    char *copy;
    size_t length = strlen(name);
    size_t new_capacity;

    if (vector->count >= V4_ORW_MAX_ENTRIES ||
        length > V4_ORW_MAX_TOTAL_PATH_BYTES - vector->total_name_bytes) {
        return v4_orw_fail(error, V4_ORW_ERROR, EOVERFLOW,
                           "directory name count/byte budget exceeds cap");
    }
    if (vector->count == vector->capacity) {
        new_capacity = vector->capacity == 0 ? 8 : vector->capacity * 2;
        if (new_capacity > V4_ORW_MAX_ENTRIES) {
            new_capacity = V4_ORW_MAX_ENTRIES;
        }
        grown = realloc(vector->names, new_capacity * sizeof(*grown));
        if (grown == NULL) {
            return v4_orw_fail(error, V4_ORW_ERROR, ENOMEM,
                               "cannot allocate directory-name vector");
        }
        vector->names = grown;
        vector->capacity = new_capacity;
    }
    copy = strdup(name);
    if (copy == NULL) {
        return v4_orw_fail(error, V4_ORW_ERROR, ENOMEM,
                           "cannot allocate directory name");
    }
    vector->names[vector->count++] = copy;
    vector->total_name_bytes += length;
    return V4_ORW_OK;
}

static int
v4_orw_list_directory(
    int directory_fd,
    struct v4_orw_name_vector *names,
    struct v4_orw_walk_result *walk,
    struct v4_orw_error *error
)
{
    unsigned char buffer[V4_ORW_DIRENT_BUFFER_BYTES];
    bool eof = false;
    int result = V4_ORW_OK;

    memset(names, 0, sizeof(*names));
    while (!eof) {
        long count = syscall(SYS_getdents64, directory_fd, buffer,
                             sizeof(buffer));
        size_t offset = 0;
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            result = v4_orw_fail(error, V4_ORW_ERROR, errno,
                                 "getdents64 failed");
            break;
        }
        if (count == 0) {
            eof = true;
            ++walk->directory_eof_count;
            break;
        }
        while (offset < (size_t)count) {
            struct v4_orw_linux_dirent64 *entry =
                (struct v4_orw_linux_dirent64 *)(buffer + offset);
            size_t header = offsetof(struct v4_orw_linux_dirent64, d_name);
            size_t available;
            size_t length;

            if ((size_t)count - offset < header + 1 ||
                entry->d_reclen < header + 1 ||
                entry->d_reclen > (size_t)count - offset) {
                result = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                     "malformed getdents64 record");
                break;
            }
            available = entry->d_reclen - header;
            length = strnlen(entry->d_name, available);
            if (length == available) {
                result = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                     "unterminated getdents64 name");
                break;
            }
            if (strcmp(entry->d_name, ".") != 0 &&
                strcmp(entry->d_name, "..") != 0) {
                if (!v4_orw_safe_anchor_name(entry->d_name)) {
                    result = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                         "unsafe directory entry name");
                    break;
                }
                result = v4_orw_name_vector_append(names, entry->d_name,
                                                   error);
                if (result != V4_ORW_OK) {
                    break;
                }
            }
            offset += entry->d_reclen;
        }
        if (result != V4_ORW_OK) {
            break;
        }
    }
    if (result != V4_ORW_OK) {
        v4_orw_name_vector_destroy(names);
        return result;
    }
    if (names->count > 1) {
        qsort(names->names, names->count, sizeof(*names->names),
              v4_orw_name_compare);
    }
    {
        size_t index;
        for (index = 1; index < names->count; ++index) {
            if (strcmp(names->names[index - 1], names->names[index]) == 0) {
                v4_orw_name_vector_destroy(names);
                return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                   "duplicate directory entry name");
            }
        }
    }
    return V4_ORW_OK;
}

static void
v4_orw_pending_destroy(struct v4_orw_pending_vector *pending)
{
    size_t index;
    for (index = 0; index < pending->count; ++index) {
        free(pending->paths[index]);
    }
    free(pending->paths);
    memset(pending, 0, sizeof(*pending));
}

static int
v4_orw_pending_push_owned(
    struct v4_orw_pending_vector *pending,
    char *path,
    size_t committed_path_bytes,
    struct v4_orw_error *error
)
{
    char **grown;
    size_t new_capacity;
    size_t length = strlen(path);

    if (pending->count >= V4_ORW_MAX_ENTRIES ||
        committed_path_bytes > V4_ORW_MAX_TOTAL_PATH_BYTES ||
        pending->total_path_bytes >
            V4_ORW_MAX_TOTAL_PATH_BYTES - committed_path_bytes ||
        length > V4_ORW_MAX_TOTAL_PATH_BYTES - committed_path_bytes -
            pending->total_path_bytes) {
        free(path);
        return v4_orw_fail(error, V4_ORW_ERROR, EOVERFLOW,
                           "pending tree entry/path budget exceeds cap");
    }
    if (pending->count == pending->capacity) {
        new_capacity = pending->capacity == 0 ? 8 : pending->capacity * 2;
        if (new_capacity > V4_ORW_MAX_ENTRIES) {
            new_capacity = V4_ORW_MAX_ENTRIES;
        }
        grown = realloc(pending->paths, new_capacity * sizeof(*grown));
        if (grown == NULL) {
            free(path);
            return v4_orw_fail(error, V4_ORW_ERROR, ENOMEM,
                               "cannot allocate pending tree vector");
        }
        pending->paths = grown;
        pending->capacity = new_capacity;
    }
    pending->paths[pending->count++] = path;
    pending->total_path_bytes += length;
    return V4_ORW_OK;
}

static char *
v4_orw_join_relative(
    const char *parent,
    const char *name,
    struct v4_orw_error *error
)
{
    size_t parent_length = strlen(parent);
    size_t name_length = strlen(name);
    size_t length = name_length + (parent_length == 0 ? 0 : parent_length + 1);
    char *result;

    if (length == 0 || length > V4_ORW_MAX_RELATIVE_BYTES) {
        (void)v4_orw_fail(error, V4_ORW_ERROR, ENAMETOOLONG,
                          "tree-relative path exceeds cap");
        return NULL;
    }
    result = malloc(length + 1);
    if (result == NULL) {
        (void)v4_orw_fail(error, V4_ORW_ERROR, ENOMEM,
                          "cannot allocate tree-relative path");
        return NULL;
    }
    if (parent_length == 0) {
        memcpy(result, name, name_length + 1);
    } else {
        memcpy(result, parent, parent_length);
        result[parent_length] = '/';
        memcpy(result + parent_length + 1, name, name_length + 1);
    }
    return result;
}

static int
v4_orw_push_children_reverse(
    struct v4_orw_pending_vector *pending,
    const char *parent,
    struct v4_orw_name_vector *names,
    size_t committed_path_bytes,
    struct v4_orw_error *error
)
{
    size_t index = names->count;
    while (index > 0) {
        char *joined;
        --index;
        joined = v4_orw_join_relative(parent, names->names[index], error);
        if (joined == NULL) {
            return V4_ORW_ERROR;
        }
        if (v4_orw_pending_push_owned(
                pending, joined, committed_path_bytes, error
            ) != V4_ORW_OK) {
            return V4_ORW_ERROR;
        }
    }
    return V4_ORW_OK;
}

static int
v4_orw_walk_append(
    struct v4_orw_walk_result *walk,
    char *relative,
    const struct v4_orw_logical_descriptor *descriptor,
    const struct v4_orw_kernel_projection *projection,
    struct v4_orw_error *error
)
{
    struct v4_orw_walk_entry *grown;
    struct v4_orw_walk_entry *entry;
    size_t length = strlen(relative);
    size_t new_capacity;

    if (walk->entry_count >= V4_ORW_MAX_ENTRIES ||
        length > V4_ORW_MAX_TOTAL_PATH_BYTES - walk->total_relative_bytes) {
        return v4_orw_fail(error, V4_ORW_ERROR, EOVERFLOW,
                           "walk entry/path budget exceeds cap");
    }
    if (walk->entry_count == walk->entry_capacity) {
        new_capacity = walk->entry_capacity == 0 ? 16 :
            walk->entry_capacity * 2;
        if (new_capacity > V4_ORW_MAX_ENTRIES) {
            new_capacity = V4_ORW_MAX_ENTRIES;
        }
        grown = realloc(walk->entries, new_capacity * sizeof(*grown));
        if (grown == NULL) {
            return v4_orw_fail(error, V4_ORW_ERROR, ENOMEM,
                               "cannot allocate walk result");
        }
        walk->entries = grown;
        walk->entry_capacity = new_capacity;
    }
    entry = &walk->entries[walk->entry_count];
    memset(entry, 0, sizeof(*entry));
    entry->relative = relative;
    entry->object_type = S_ISDIR((mode_t)projection->st_mode) ?
        V4_ORW_DIRECTORY : V4_ORW_REGULAR_FILE;
    entry->descriptor = *descriptor;
    entry->projection = *projection;
    ++walk->entry_count;
    walk->total_relative_bytes += length;
    return V4_ORW_OK;
}

void
v4_orw_walk_result_destroy(struct v4_orw_walk_result *result)
{
    size_t index;
    if (result == NULL) {
        return;
    }
    for (index = 0; index < result->entry_count; ++index) {
        free(result->entries[index].relative);
    }
    free(result->entries);
    memset(result, 0, sizeof(*result));
    result->root_walk_descriptor.fd = -1;
}

static int
v4_orw_open_walk_directory(
    int anchor_fd,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_logical_descriptor *descriptor,
    struct v4_orw_error *error
)
{
    int fd = v4_orw_openat2(
        anchor_fd, ".",
        O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC,
        RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS |
            RESOLVE_NO_XDEV,
        error
    );
    if (fd < 0) {
        return fd == -V4_ORW_UNSUPPORTED ?
            V4_ORW_UNSUPPORTED : V4_ORW_ERROR;
    }
    if (v4_orw_allocate_new_ofd(fd, ledger, descriptor, error) != V4_ORW_OK) {
        (void)close(fd);
        return V4_ORW_ERROR;
    }
    return V4_ORW_OK;
}

int
v4_orw_output_root_walk(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_logical_ledger *ledger,
    struct v4_orw_walk_result *result,
    struct v4_orw_error *error
)
{
    struct v4_orw_kernel_projection root_projection;
    struct v4_orw_name_vector root_names;
    struct v4_orw_pending_vector pending;
    struct v4_orw_logical_descriptor root_walk_descriptor;
    int code;

    v4_orw_error_clear(error);
    if (anchor == NULL || ledger == NULL || result == NULL) {
        return v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "walk input is null");
    }
    memset(result, 0, sizeof(*result));
    result->root_walk_descriptor.fd = -1;
    memset(&root_names, 0, sizeof(root_names));
    memset(&pending, 0, sizeof(pending));
    code = v4_orw_output_anchor_revalidate(anchor, error);
    if (code != V4_ORW_OK) {
        return code;
    }
    code = v4_orw_open_walk_directory(
        anchor->primary.fd, ledger, &root_walk_descriptor, error
    );
    if (code != V4_ORW_OK) {
        return code;
    }
    result->root_walk_descriptor = root_walk_descriptor;
    result->opened_descriptor_count = 1;
    code = v4_orw_snapshot_fd(root_walk_descriptor.fd, &root_projection, error);
    if (code == V4_ORW_OK) {
        result->root_walk_projection = root_projection;
    }
    if (code == V4_ORW_OK &&
        (root_projection.st_dev != anchor->initial_projection.st_dev ||
         root_projection.st_ino != anchor->initial_projection.st_ino ||
         root_projection.mount_id != anchor->initial_projection.mount_id ||
         !S_ISDIR((mode_t)root_projection.st_mode))) {
        code = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                           "walk root differs from retained anchor");
    }
    if (code == V4_ORW_OK) {
        code = v4_orw_list_directory(root_walk_descriptor.fd, &root_names,
                                     result, error);
    }
    if (close(root_walk_descriptor.fd) != 0 && code == V4_ORW_OK) {
        code = v4_orw_fail(error, V4_ORW_ERROR, errno,
                           "cannot close root walk descriptor");
    }
    if (code == V4_ORW_OK) {
        code = v4_orw_push_children_reverse(
            &pending, "", &root_names, result->total_relative_bytes, error
        );
    }
    v4_orw_name_vector_destroy(&root_names);

    while (code == V4_ORW_OK && pending.count > 0) {
        char *relative = pending.paths[--pending.count];
        struct v4_orw_logical_descriptor object_descriptor;
        struct v4_orw_kernel_projection projection;
        int object_fd;

        pending.total_path_bytes -= strlen(relative);
        object_fd = v4_orw_openat2(
            anchor->primary.fd, relative,
            O_PATH | O_NOFOLLOW | O_CLOEXEC,
            RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS |
                RESOLVE_NO_MAGICLINKS | RESOLVE_NO_XDEV,
            error
        );
        if (object_fd < 0) {
            free(relative);
            code = object_fd == -V4_ORW_UNSUPPORTED ?
                V4_ORW_UNSUPPORTED : V4_ORW_ERROR;
            break;
        }
        code = v4_orw_allocate_new_ofd(
            object_fd, ledger, &object_descriptor, error
        );
        if (code == V4_ORW_OK) {
            ++result->opened_descriptor_count;
            code = v4_orw_snapshot_fd(object_fd, &projection, error);
        }
        if (code == V4_ORW_OK &&
            projection.mount_id != anchor->initial_projection.mount_id) {
            code = v4_orw_fail(error, V4_ORW_ERROR, EXDEV,
                               "nested output mount is forbidden");
        }
        if (code == V4_ORW_OK &&
            !S_ISDIR((mode_t)projection.st_mode) &&
            !S_ISREG((mode_t)projection.st_mode)) {
            code = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                               "special or symbolic output entry is forbidden");
        }
        if (code == V4_ORW_OK &&
            S_ISREG((mode_t)projection.st_mode) && projection.st_nlink != 1) {
            code = v4_orw_fail(error, V4_ORW_ERROR, EMLINK,
                               "hard-linked output file is forbidden");
        }
        if (code == V4_ORW_OK) {
            code = v4_orw_walk_append(
                result, relative, &object_descriptor, &projection, error
            );
            if (code == V4_ORW_OK) {
                relative = NULL;
            }
        }
        if (code == V4_ORW_OK && S_ISDIR((mode_t)projection.st_mode)) {
            struct v4_orw_logical_descriptor directory_descriptor;
            struct v4_orw_kernel_projection directory_projection;
            struct v4_orw_name_vector names;

            memset(&names, 0, sizeof(names));
            memset(&directory_descriptor, 0, sizeof(directory_descriptor));
            directory_descriptor.fd = -1;
            code = v4_orw_open_walk_directory(
                object_fd, ledger, &directory_descriptor, error
            );
            if (code == V4_ORW_OK) {
                ++result->opened_descriptor_count;
                code = v4_orw_snapshot_fd(
                    directory_descriptor.fd, &directory_projection, error
                );
            }
            if (code == V4_ORW_OK &&
                (directory_projection.st_dev != projection.st_dev ||
                 directory_projection.st_ino != projection.st_ino ||
                 directory_projection.mount_id != projection.mount_id)) {
                code = v4_orw_fail(error, V4_ORW_ERROR, EINVAL,
                                   "directory walk descriptor changed object");
            }
            if (code == V4_ORW_OK) {
                struct v4_orw_walk_entry *entry =
                    &result->entries[result->entry_count - 1];
                entry->has_directory_walk_descriptor = 1;
                entry->directory_walk_descriptor = directory_descriptor;
                entry->directory_walk_projection = directory_projection;
            }
            if (code == V4_ORW_OK) {
                code = v4_orw_list_directory(
                    directory_descriptor.fd, &names, result, error
                );
            }
            if (directory_descriptor.fd >= 0 &&
                close(directory_descriptor.fd) != 0 && code == V4_ORW_OK) {
                code = v4_orw_fail(error, V4_ORW_ERROR, errno,
                                   "cannot close directory walk descriptor");
            }
            if (code == V4_ORW_OK) {
                code = v4_orw_push_children_reverse(
                    &pending,
                    result->entries[result->entry_count - 1].relative,
                    &names, result->total_relative_bytes, error
                );
            }
            v4_orw_name_vector_destroy(&names);
        }
        free(relative);
        if (close(object_fd) != 0 && code == V4_ORW_OK) {
            code = v4_orw_fail(error, V4_ORW_ERROR, errno,
                               "cannot close object walk descriptor");
        }
    }
    v4_orw_pending_destroy(&pending);
    if (code == V4_ORW_OK) {
        code = v4_orw_output_anchor_revalidate(anchor, error);
    }
    if (code != V4_ORW_OK) {
        v4_orw_walk_result_destroy(result);
    }
    return code;
}

void
v4_orw_output_anchor_close(struct v4_orw_output_anchor *anchor)
{
    if (anchor == NULL) {
        return;
    }
    if (anchor->primary.fd >= 0) {
        (void)close(anchor->primary.fd);
    }
    if (anchor->guard.fd >= 0 && anchor->guard.fd != anchor->primary.fd) {
        (void)close(anchor->guard.fd);
    }
    memset(anchor, 0, sizeof(*anchor));
    anchor->primary.fd = -1;
    anchor->guard.fd = -1;
}
