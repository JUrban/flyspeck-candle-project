#define _GNU_SOURCE

#include "v4_held_builder.h"

#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

static const unsigned long expected_namespace_flags[V4_HB_NAMESPACE_COUNT] = {
    CLONE_NEWUSER,
    CLONE_NEWNS,
    CLONE_NEWPID,
    CLONE_NEWNET,
    CLONE_NEWIPC,
};

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
initial_snapshot_is_exact(const struct v4_hb_snapshot *snapshot)
{
    return snapshot->pid > 0 && snapshot->start_ticks > 0 &&
        snapshot->pidfd >= 0 && snapshot->state == V4_HB_GATE_SPINNING &&
        snapshot->gate_value == 0 && snapshot->raw_interrupt_wait_status == 0 &&
        snapshot->seize_count == 0 && snapshot->interrupt_count == 0 &&
        snapshot->interrupt_event_stop_count == 0 &&
        snapshot->resume_count == 0 && snapshot->held_stop_consumed == 0 &&
        initial_namespace_capture_is_exact(snapshot);
}

static bool
held_snapshot_is_exact(const struct v4_hb_snapshot *snapshot)
{
    return snapshot->state == V4_HB_INTERRUPT_HELD &&
        snapshot->gate_value == 0 && snapshot->seize_count == 1 &&
        snapshot->interrupt_count == 1 &&
        snapshot->interrupt_event_stop_count == 1 &&
        snapshot->resume_count == 0 && snapshot->held_stop_consumed == 1 &&
        WIFSTOPPED(snapshot->raw_interrupt_wait_status) &&
        WSTOPSIG(snapshot->raw_interrupt_wait_status) == SIGTRAP &&
        (unsigned int)snapshot->raw_interrupt_wait_status >> 16 ==
            PTRACE_EVENT_STOP && namespace_boundary_is_exact(snapshot);
}

static int
expect_snapshot_splices_reject(
    struct v4_hb_builder *builder,
    const struct v4_hb_snapshot *held,
    struct v4_hb_error *error
)
{
    struct v4_hb_snapshot splice;

    splice = *held;
    ++splice.pid;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.start_ticks;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    splice.raw_interrupt_wait_status ^= 1 << 16;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.pidfd;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    splice.clone_flags ^= CLONE_NEWUTS;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    --splice.namespace_count;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.observer_effective_uid;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    splice.observer_setgroups_denied ^= 1U;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.child_nspid;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.uid_map.outside_id;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.setgroups_deny_write_order;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.child_namespaces[0].inode;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    splice = *held;
    ++splice.parent_namespaces[1].descriptor;
    if (v4_hb_builder_verify_held(builder, &splice, error) != V4_HB_ERROR) {
        return -1;
    }
    return v4_hb_builder_verify_held(builder, held, error) == V4_HB_OK ?
        0 : -1;
}

static int
hold_and_prewalk(
    struct v4_hb_builder *builder,
    const struct v4_orw_output_anchor *anchor,
    struct v4_orw_logical_ledger *ledger,
    struct v4_hb_snapshot *held,
    struct v4_hb_error *error
)
{
    struct v4_orw_walk_result walk;
    struct v4_hb_completion forbidden_completion;
    int code = v4_hb_builder_seize_interrupt(builder, held, error);

    if (code != V4_HB_OK) {
        return code;
    }
    if (!held_snapshot_is_exact(held) ||
        v4_hb_builder_seize_interrupt(builder, held, error) != V4_HB_ERROR ||
        expect_snapshot_splices_reject(builder, held, error) != 0 ||
        v4_hb_builder_release_and_reap(
            builder, &forbidden_completion, error
        ) != V4_HB_ERROR) {
        return V4_HB_ERROR;
    }
    code = v4_hb_builder_run_empty_prewalk(
        builder, anchor, ledger, &walk, error
    );
    if (code != V4_HB_OK) {
        return code;
    }
    if (walk.entry_count != 0 || walk.directory_eof_count != 1) {
        v4_orw_walk_result_destroy(&walk);
        return V4_HB_ERROR;
    }
    v4_orw_walk_result_destroy(&walk);
    return V4_HB_OK;
}

int
main(void)
{
    char temporary[] = "/tmp/candle-v4-held-builder.XXXXXX";
    struct v4_orw_logical_ledger ledger;
    struct v4_orw_output_anchor anchor;
    struct v4_orw_error walk_error;
    struct v4_hb_builder *builder = NULL;
    struct v4_hb_builder *attack_builder = NULL;
    struct v4_hb_builder *exit_builder = NULL;
    struct v4_hb_builder *alias_builder = NULL;
    struct v4_hb_snapshot initial;
    struct v4_hb_snapshot held;
    struct v4_hb_snapshot completed;
    struct v4_hb_completion completion;
    struct v4_hb_error error;
    int root_fd = -1;
    int saved_pidfd = -1;
    int saved_parent_namespace_fds[V4_HB_NAMESPACE_COUNT];
    int saved_child_namespace_fds[V4_HB_NAMESPACE_COUNT];
    uint32_t namespace_index;
    int status = 1;
    bool mounted = false;
    int code;

    if (V4_HB_FIXED_PTRACE_OPTIONS_MASK != 0x0010007fUL ||
        V4_HB_PTRACE_OPTION_COUNT != 8U ||
        V4_HB_FIXED_CLONE_FLAGS != 0x78020011UL ||
        V4_HB_NAMESPACE_COUNT != 5U) {
        return test_fail("fixed V4 ptrace/namespace identity drifted");
    }
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
    mounted = true;
    root_fd = open(temporary,
                   O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root_fd < 0 || mkdirat(root_fd, "candle-output", 0700) != 0 ||
        v4_orw_logical_ledger_init(&ledger, &walk_error) != V4_ORW_OK) {
        (void)test_fail("cannot construct held-builder output root");
        goto cleanup;
    }
    code = v4_orw_output_anchor_open(
        root_fd, "candle-output", &ledger, &anchor, &walk_error
    );
    if (code == V4_ORW_UNSUPPORTED) {
        status = test_skip(walk_error.message);
        goto cleanup;
    }
    if (code != V4_ORW_OK) {
        (void)test_fail("cannot retain output anchor");
        goto cleanup;
    }

    code = v4_hb_builder_start(&builder, &error);
    if (code == V4_HB_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup_anchor;
    }
    if (code != V4_HB_OK ||
        v4_hb_builder_snapshot(builder, &initial, &error) != V4_HB_OK ||
        !initial_snapshot_is_exact(&initial) ||
        v4_hb_builder_release_and_reap(
            builder, &completion, &error
        ) != V4_HB_ERROR) {
        (void)test_fail("initial userspace-gate boundary is malformed");
        goto cleanup_anchor;
    }
    code = hold_and_prewalk(builder, &anchor, &ledger, &held, &error);
    if (code == V4_HB_UNSUPPORTED) {
        status = test_skip(error.message);
        goto cleanup_anchor;
    }
    if (code != V4_HB_OK ||
        v4_hb_builder_snapshot(builder, &completed, &error) != V4_HB_OK ||
        completed.state != V4_HB_EMPTY_PREWALK_COMPLETE ||
        completed.gate_value != 0 || completed.pid != held.pid ||
        completed.start_ticks != held.start_ticks ||
        completed.raw_interrupt_wait_status !=
            held.raw_interrupt_wait_status ||
        v4_hb_builder_verify_held(builder, &completed, &error) != V4_HB_OK) {
        (void)fprintf(
            stderr,
            "FAIL: held empty pre-walk boundary is malformed: code=%d "
            "state=%d gate=%u pid=%ld/%ld ticks=%llu/%llu wait=%x/%x %s\n",
            code, (int)completed.state, completed.gate_value,
            (long)completed.pid, (long)held.pid,
            (unsigned long long)completed.start_ticks,
            (unsigned long long)held.start_ticks,
            completed.raw_interrupt_wait_status,
            held.raw_interrupt_wait_status, error.message
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
    v4_hb_builder_destroy(builder);
    builder = NULL;

    code = v4_hb_builder_start(&attack_builder, &error);
    if (code != V4_HB_OK) {
        if (code == V4_HB_UNSUPPORTED) {
            status = test_skip(error.message);
        } else {
            (void)test_fail("cannot start unexpected-stop builder");
        }
        goto cleanup_anchor;
    }
    code = hold_and_prewalk(
        attack_builder, &anchor, &ledger, &held, &error
    );
    if (code != V4_HB_OK) {
        (void)test_fail("cannot establish unexpected-stop boundary");
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

    code = v4_hb_builder_start(&exit_builder, &error);
    if (code != V4_HB_OK) {
        if (code == V4_HB_UNSUPPORTED) {
            status = test_skip(error.message);
        } else {
            (void)test_fail("cannot start unexpected-exit builder");
        }
        goto cleanup_anchor;
    }
    code = hold_and_prewalk(
        exit_builder, &anchor, &ledger, &held, &error
    );
    if (code != V4_HB_OK) {
        (void)test_fail("cannot establish unexpected-exit boundary");
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

    code = v4_hb_builder_start(&alias_builder, &error);
    if (code != V4_HB_OK ||
        hold_and_prewalk(
            alias_builder, &anchor, &ledger, &held, &error
        ) != V4_HB_OK) {
        (void)test_fail("cannot establish pidfd-substitution boundary");
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

    code = v4_hb_builder_start(&alias_builder, &error);
    if (code != V4_HB_OK ||
        hold_and_prewalk(
            alias_builder, &anchor, &ledger, &held, &error
        ) != V4_HB_OK) {
        (void)test_fail("cannot establish namespace-OFD boundary");
        goto cleanup_anchor;
    }
    {
        char path[64];
        int replacement;
        int primary = held.child_namespaces[0].descriptor;

        if (snprintf(path, sizeof(path), "/proc/%ld/ns/user",
                     (long)held.pid) < 0 || close(primary) != 0) {
            (void)test_fail("cannot begin namespace-OFD substitution");
            goto cleanup_anchor;
        }
        replacement = open(path, O_RDONLY | O_CLOEXEC);
        if (replacement < 0 ||
            (replacement != primary &&
             (dup3(replacement, primary, O_CLOEXEC) < 0 ||
              close(replacement) != 0))) {
            (void)test_fail("cannot force namespace-OFD number reuse");
            goto cleanup_anchor;
        }
        if (v4_hb_builder_verify_held(
                alias_builder, &held, &error
            ) != V4_HB_ERROR ||
            v4_hb_builder_abort(alias_builder, &error) != V4_HB_OK) {
            (void)test_fail("namespace-OFD substitution did not fail closed");
            goto cleanup_anchor;
        }
    }
    v4_hb_builder_destroy(alias_builder);
    alias_builder = NULL;

    code = v4_hb_builder_start(&alias_builder, &error);
    if (code != V4_HB_OK ||
        hold_and_prewalk(
            alias_builder, &anchor, &ledger, &held, &error
        ) != V4_HB_OK) {
        (void)test_fail("cannot establish namespace-splice boundary");
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

    status = 0;
    (void)fprintf(stdout, "PASS: native V4 held-builder boundary\n");

cleanup_anchor:
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
    v4_orw_output_anchor_close(&anchor);
cleanup:
    if (root_fd >= 0) {
        (void)close(root_fd);
    }
    if (mounted) {
        (void)umount2(temporary, MNT_DETACH);
    }
    (void)rmdir(temporary);
    return status;
}
