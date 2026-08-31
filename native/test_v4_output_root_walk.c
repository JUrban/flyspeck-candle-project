#define _GNU_SOURCE

#include "v4_output_root_walk.h"

#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static int
test_fail(const char *message)
{
    (void)fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int
test_skip(const char *message)
{
    (void)fprintf(stdout, "SKIP: %s\n", message);
    return V4_ORW_UNSUPPORTED;
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
    if (setresgid(0, 0, 0) != 0 || setresuid(0, 0, 0) != 0) {
        return -1;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) != 0) {
        return -1;
    }
    return 0;
}

static int
create_regular_at(int directory_fd, const char *relative, const char *bytes)
{
    size_t length = strlen(bytes);
    size_t offset = 0;
    int fd = openat(directory_fd, relative,
                    O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
                    0600);

    if (fd < 0) {
        return -1;
    }
    while (offset < length) {
        ssize_t count = write(fd, bytes + offset, length - offset);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count <= 0) {
            (void)close(fd);
            return -1;
        }
        offset += (size_t)count;
    }
    if (fchmod(fd, 0444) != 0 || close(fd) != 0) {
        return -1;
    }
    return 0;
}

static int
expect_walk_error(
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_logical_ledger *ledger,
    const char *attack
)
{
    struct v4_orw_walk_result result;
    struct v4_orw_error error;
    int code = v4_orw_output_root_walk(anchor, ledger, &result, &error);

    if (code != V4_ORW_ERROR) {
        if (code == V4_ORW_OK) {
            v4_orw_walk_result_destroy(&result);
        }
        (void)fprintf(stderr,
                      "FAIL: %s walk returned %d instead of fail-closed error"
                      " (%s)\n",
                      attack, code, error.message);
        return -1;
    }
    return 0;
}

static bool
entry_is(
    const struct v4_orw_walk_result *result,
    size_t index,
    const char *relative,
    enum v4_orw_object_type object_type
)
{
    return index < result->entry_count &&
        strcmp(result->entries[index].relative, relative) == 0 &&
        result->entries[index].object_type == object_type;
}

int
main(void)
{
    char temporary[] = "/tmp/candle-v4-output-walk.XXXXXX";
    char nested_path[512];
    struct v4_orw_logical_ledger ledger;
    struct v4_orw_logical_ledger exhausted_ledger;
    struct v4_orw_output_anchor anchor;
    struct v4_orw_output_anchor rejected_anchor;
    struct v4_orw_walk_result walk;
    struct v4_orw_error error;
    uint64_t previous_generation;
    int root_fd = -1;
    int code;
    int replacement_fd;
    int primary_number;
    int status = 1;
    bool root_mounted = false;
    bool nested_mounted = false;

    if (mkdtemp(temporary) == NULL) {
        return test_fail("mkdtemp failed");
    }
    if (enter_private_mount_namespace() != 0) {
        (void)rmdir(temporary);
        return test_skip("unprivileged user/mount namespaces unavailable");
    }
    if (mount("tmpfs", temporary, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=16777216,mode=0700") != 0) {
        (void)rmdir(temporary);
        return test_skip("private tmpfs mount unavailable");
    }
    root_mounted = true;
    root_fd = open(temporary,
                   O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root_fd < 0 ||
        mkdirat(root_fd, "candle-output", 0700) != 0) {
        (void)test_fail("cannot construct isolated output root");
        goto cleanup;
    }

    if (v4_orw_logical_ledger_init(&ledger, &error) != V4_ORW_OK) {
        (void)test_fail("logical ledger initialization failed");
        goto cleanup;
    }
    exhausted_ledger = ledger;
    exhausted_ledger.next_fd_generation = UINT64_MAX;
    code = v4_orw_output_anchor_open(
        root_fd, "candle-output", &exhausted_ledger, &rejected_anchor, &error
    );
    if (code != V4_ORW_ERROR || rejected_anchor.primary.fd != -1 ||
        rejected_anchor.guard.fd != -1 || rejected_anchor.live != 0) {
        if (code == V4_ORW_OK) {
            v4_orw_output_anchor_close(&rejected_anchor);
        }
        (void)test_fail("exhausted ledger did not reject with a safe anchor");
        goto cleanup;
    }
    code = v4_orw_output_anchor_open(
        root_fd, "../candle-output", &ledger, &rejected_anchor, &error
    );
    if (code != V4_ORW_ERROR) {
        (void)test_fail("unsafe output-anchor name did not reject");
        goto cleanup;
    }
    if (symlinkat("candle-output", root_fd, "output-link") != 0) {
        (void)test_fail("cannot construct anchor symlink attack");
        goto cleanup;
    }
    code = v4_orw_output_anchor_open(
        root_fd, "output-link", &ledger, &rejected_anchor, &error
    );
    if (code != V4_ORW_ERROR) {
        if (code == V4_ORW_OK) {
            v4_orw_output_anchor_close(&rejected_anchor);
        }
        (void)test_fail("symlink output anchor did not reject");
        goto cleanup;
    }
    if (unlinkat(root_fd, "output-link", 0) != 0) {
        (void)test_fail("cannot remove anchor symlink attack");
        goto cleanup;
    }

    code = v4_orw_output_anchor_open(
        root_fd, "candle-output", &ledger, &anchor, &error
    );
    if (code == V4_ORW_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup;
    }
    if (code != V4_ORW_OK) {
        (void)fprintf(stderr, "FAIL: anchor open: %s\n", error.message);
        goto cleanup;
    }
    if (anchor.primary.fd == anchor.guard.fd ||
        anchor.primary.fd_generation == anchor.guard.fd_generation ||
        anchor.primary.logical_ofd_id != anchor.guard.logical_ofd_id ||
        anchor.primary.logical_ofd_generation !=
            anchor.guard.logical_ofd_generation ||
        (anchor.initial_projection.fd_flags & FD_CLOEXEC) == 0 ||
        (anchor.initial_projection.status_flags & O_PATH) != O_PATH ||
        (anchor.initial_projection.status_flags & O_DIRECTORY) != O_DIRECTORY ||
        (anchor.initial_projection.status_flags & O_NOFOLLOW) != O_NOFOLLOW ||
        (anchor.initial_projection.status_flags & O_ACCMODE) != O_RDONLY ||
        anchor.initial_projection.fdinfo.position != 0 ||
        anchor.initial_projection.mount_id == 0) {
        (void)test_fail("anchor projection or logical alias is malformed");
        goto cleanup_anchor;
    }
    if (fcntl(anchor.guard.fd, F_SETFD, 0) != 0 ||
        v4_orw_output_anchor_revalidate(&anchor, &error) != V4_ORW_ERROR ||
        fcntl(anchor.guard.fd, F_SETFD, FD_CLOEXEC) != 0 ||
        v4_orw_output_anchor_revalidate(&anchor, &error) != V4_ORW_OK) {
        (void)test_fail("guard descriptor flag mutation was not detected");
        goto cleanup_anchor;
    }

    code = v4_orw_output_root_walk(&anchor, &ledger, &walk, &error);
    if (code == V4_ORW_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup_anchor;
    }
    if (code != V4_ORW_OK || walk.entry_count != 0 ||
        walk.directory_eof_count != 1 ||
        walk.opened_descriptor_count != 1 ||
        walk.declared_mount_edge_count != 0 ||
        walk.root_walk_descriptor.fd < 0 ||
        walk.root_walk_descriptor.fd_generation == 0 ||
        walk.root_walk_projection.mount_id !=
            anchor.initial_projection.mount_id) {
        (void)fprintf(stderr, "FAIL: exact empty walk: %s\n", error.message);
        if (code == V4_ORW_OK) {
            v4_orw_walk_result_destroy(&walk);
        }
        goto cleanup_anchor;
    }
    previous_generation = walk.root_walk_descriptor.fd_generation;
    v4_orw_walk_result_destroy(&walk);

    if (mkdirat(anchor.primary.fd, "alpha", 0700) != 0 ||
        create_regular_at(anchor.primary.fd, "alpha/a.txt", "alpha\n") != 0 ||
        create_regular_at(anchor.primary.fd, "z.txt", "zeta\n") != 0) {
        (void)test_fail("cannot construct populated output tree");
        goto cleanup_anchor;
    }
    code = v4_orw_output_root_walk(&anchor, &ledger, &walk, &error);
    if (code != V4_ORW_OK || walk.entry_count != 3 ||
        walk.directory_eof_count != 2 ||
        walk.opened_descriptor_count != 5 ||
        !entry_is(&walk, 0, "alpha", V4_ORW_DIRECTORY) ||
        !entry_is(&walk, 1, "alpha/a.txt", V4_ORW_REGULAR_FILE) ||
        !entry_is(&walk, 2, "z.txt", V4_ORW_REGULAR_FILE) ||
        walk.root_walk_descriptor.fd_generation <= previous_generation ||
        walk.entries[0].descriptor.fd_generation <=
            walk.root_walk_descriptor.fd_generation ||
        walk.entries[0].has_directory_walk_descriptor != 1 ||
        walk.entries[0].is_declared_mount_edge != 0 ||
        walk.entries[0].declared_anchor_alias_descriptor.fd != -1 ||
        walk.entries[0].directory_walk_descriptor.fd_generation <=
            walk.entries[0].descriptor.fd_generation ||
        walk.entries[1].has_directory_walk_descriptor != 0 ||
        walk.entries[1].is_declared_mount_edge != 0 ||
        walk.entries[1].declared_anchor_alias_descriptor.fd != -1 ||
        walk.entries[2].has_directory_walk_descriptor != 0 ||
        walk.entries[2].is_declared_mount_edge != 0 ||
        walk.entries[2].declared_anchor_alias_descriptor.fd != -1 ||
        walk.entries[0].projection.mount_id !=
            anchor.initial_projection.mount_id ||
        walk.entries[1].projection.st_nlink != 1 ||
        walk.entries[2].projection.st_nlink != 1) {
        (void)fprintf(stderr, "FAIL: deterministic populated walk: %s\n",
                      error.message);
        if (code == V4_ORW_OK) {
            v4_orw_walk_result_destroy(&walk);
        }
        goto cleanup_anchor;
    }
    v4_orw_walk_result_destroy(&walk);
    if (v4_orw_output_anchor_revalidate(&anchor, &error) != V4_ORW_OK) {
        (void)test_fail("anchor did not survive pre/post walk revalidation");
        goto cleanup_anchor;
    }

    if (symlinkat("z.txt", anchor.primary.fd, "bad-link") != 0 ||
        expect_walk_error(&anchor, &ledger, "symlink") != 0 ||
        unlinkat(anchor.primary.fd, "bad-link", 0) != 0) {
        goto cleanup_anchor;
    }
    if (mkfifoat(anchor.primary.fd, "bad-fifo", 0600) != 0 ||
        expect_walk_error(&anchor, &ledger, "FIFO") != 0 ||
        unlinkat(anchor.primary.fd, "bad-fifo", 0) != 0) {
        goto cleanup_anchor;
    }
    if (create_regular_at(anchor.primary.fd, "hard-one", "hard\n") != 0 ||
        linkat(anchor.primary.fd, "hard-one", anchor.primary.fd,
               "hard-two", 0) != 0 ||
        expect_walk_error(&anchor, &ledger, "hard link") != 0 ||
        unlinkat(anchor.primary.fd, "hard-two", 0) != 0 ||
        unlinkat(anchor.primary.fd, "hard-one", 0) != 0) {
        goto cleanup_anchor;
    }

    if (mkdirat(anchor.primary.fd, "nested", 0700) != 0 ||
        snprintf(nested_path, sizeof(nested_path), "%s/candle-output/nested",
                 temporary) < 0 ||
        mount("tmpfs", nested_path, "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "size=1048576,mode=0700") != 0) {
        (void)test_fail("cannot construct nested-mount attack");
        goto cleanup_anchor;
    }
    nested_mounted = true;
    if (expect_walk_error(&anchor, &ledger, "nested mount") != 0) {
        goto cleanup_anchor;
    }
    if (umount2(nested_path, MNT_DETACH) != 0) {
        (void)test_fail("cannot detach nested-mount attack");
        goto cleanup_anchor;
    }
    nested_mounted = false;
    if (unlinkat(anchor.primary.fd, "nested", AT_REMOVEDIR) != 0) {
        (void)test_fail("cannot remove nested-mount attack");
        goto cleanup_anchor;
    }

    primary_number = anchor.primary.fd;
    if (close(primary_number) != 0) {
        (void)test_fail("cannot close primary descriptor for reuse attack");
        goto cleanup_anchor;
    }
    replacement_fd = openat(root_fd, "candle-output",
                            O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (replacement_fd < 0) {
        anchor.primary.fd = -1;
        (void)test_fail("cannot open replacement descriptor");
        goto cleanup_anchor;
    }
    if (replacement_fd != primary_number) {
        if (dup3(replacement_fd, primary_number, O_CLOEXEC) < 0 ||
            close(replacement_fd) != 0) {
            anchor.primary.fd = -1;
            (void)test_fail("cannot force descriptor-number reuse attack");
            goto cleanup_anchor;
        }
    }
    if (v4_orw_output_anchor_revalidate(&anchor, &error) != V4_ORW_ERROR) {
        (void)test_fail("same-inode descriptor substitution was not detected");
        goto cleanup_anchor;
    }

    status = 0;
    (void)fprintf(stdout, "PASS: native V4 output-root anchor/walk\n");

cleanup_anchor:
    v4_orw_output_anchor_close(&anchor);
cleanup:
    if (nested_mounted) {
        (void)umount2(nested_path, MNT_DETACH);
    }
    if (root_fd >= 0) {
        (void)close(root_fd);
    }
    if (root_mounted) {
        (void)umount2(temporary, MNT_DETACH);
    }
    (void)rmdir(temporary);
    return status;
}
