"""Tests for modules.core.mapping — resolve_ticket, resolve_pr, MappingRegistry."""

from __future__ import annotations

from datetime import datetime

import pytest

from modules.core.mapping import (
    MappingRegistry,
    WorktreeMapping,
    _normalize_branch,
    resolve_pr,
    resolve_ticket,
)
from modules.git.models import WorktreeInfo
from modules.github.models import PRState, PullRequest
from modules.linear.models import Ticket, TicketStatus

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1)


def make_ticket(branch_name: str, identifier: str = "ENG-1") -> Ticket:
    return Ticket(
        id=identifier,
        identifier=identifier,
        title="Test ticket",
        status=TicketStatus.IN_PROGRESS,
        branch_name=branch_name,
        url="https://linear.app/t/1",
        updated_at=_NOW,
    )


def make_pr(head_branch: str, number: int = 1) -> PullRequest:
    return PullRequest(
        number=number,
        title="Test PR",
        state=PRState.OPEN,
        url="https://github.com/org/repo/pull/1",
        head_branch=head_branch,
        base_branch="main",
        merged=False,
        draft=False,
        updated_at=_NOW,
    )


def make_worktree(branch: str, path: str = "/repo/worktrees/wt") -> WorktreeInfo:
    return WorktreeInfo(path=path, branch=branch)


# ---------------------------------------------------------------------------
# _normalize_branch
# ---------------------------------------------------------------------------


class TestNormalizeBranch:
    def test_strips_refs_heads_prefix(self):
        assert _normalize_branch("refs/heads/feature-x") == "feature-x"

    def test_plain_branch_unchanged(self):
        assert _normalize_branch("feature-x") == "feature-x"

    def test_slash_in_branch_name_preserved(self):
        assert (
            _normalize_branch("refs/heads/eng-123/my-feature") == "eng-123/my-feature"
        )

    def test_empty_string(self):
        assert _normalize_branch("") == ""

    def test_no_partial_strip(self):
        # Should only strip the exact prefix
        assert _normalize_branch("refs/tags/v1.0") == "refs/tags/v1.0"


# ---------------------------------------------------------------------------
# resolve_ticket
# ---------------------------------------------------------------------------


class TestResolveTicket:
    def test_exact_match_returns_ticket(self):
        wt = make_worktree("eng-123-add-auth")
        ticket = make_ticket("eng-123-add-auth")
        assert resolve_ticket(wt, [ticket]) is ticket

    def test_no_match_returns_none(self):
        wt = make_worktree("feature-x")
        ticket = make_ticket("feature-y")
        assert resolve_ticket(wt, [ticket]) is None

    def test_empty_tickets_returns_none(self):
        wt = make_worktree("feature-x")
        assert resolve_ticket(wt, []) is None

    def test_refs_heads_prefix_on_worktree_branch(self):
        wt = make_worktree("refs/heads/eng-123-add-auth")
        ticket = make_ticket("eng-123-add-auth")
        assert resolve_ticket(wt, [ticket]) is ticket

    def test_refs_heads_prefix_on_ticket_branch_name(self):
        wt = make_worktree("eng-123-add-auth")
        ticket = make_ticket("refs/heads/eng-123-add-auth")
        assert resolve_ticket(wt, [ticket]) is ticket

    def test_both_have_refs_heads_prefix(self):
        wt = make_worktree("refs/heads/feature-x")
        ticket = make_ticket("refs/heads/feature-x")
        assert resolve_ticket(wt, [ticket]) is ticket

    def test_returns_first_matching_ticket(self):
        wt = make_worktree("shared-branch")
        t1 = make_ticket("shared-branch", identifier="ENG-1")
        t2 = make_ticket("shared-branch", identifier="ENG-2")
        result = resolve_ticket(wt, [t1, t2])
        assert result is t1

    def test_multiple_tickets_only_matching_one_returned(self):
        wt = make_worktree("eng-5-fix-bug")
        tickets = [
            make_ticket("eng-1-other", "ENG-1"),
            make_ticket("eng-5-fix-bug", "ENG-5"),
            make_ticket("eng-9-another", "ENG-9"),
        ]
        result = resolve_ticket(wt, tickets)
        assert result is tickets[1]

    @pytest.mark.parametrize(
        "branch",
        [
            "eng-123-my-feature",
            "eng-123/my-feature",
            "fix/some-bug",
            "feature-add-login",
            "hotfix-critical",
        ],
        ids=["linear-kebab", "linear-slash", "fix-slash", "feature-kebab", "hotfix"],
    )
    def test_various_branch_formats(self, branch: str):
        wt = make_worktree(branch)
        ticket = make_ticket(branch)
        assert resolve_ticket(wt, [ticket]) is ticket


# ---------------------------------------------------------------------------
# resolve_pr
# ---------------------------------------------------------------------------


class TestResolvePr:
    def test_exact_match_returns_pr(self):
        wt = make_worktree("eng-123-add-auth")
        pr = make_pr("eng-123-add-auth")
        assert resolve_pr(wt, [pr]) is pr

    def test_no_match_returns_none(self):
        wt = make_worktree("feature-x")
        pr = make_pr("feature-y")
        assert resolve_pr(wt, [pr]) is None

    def test_empty_prs_returns_none(self):
        wt = make_worktree("feature-x")
        assert resolve_pr(wt, []) is None

    def test_refs_heads_prefix_on_worktree_branch(self):
        wt = make_worktree("refs/heads/eng-123-add-auth")
        pr = make_pr("eng-123-add-auth")
        assert resolve_pr(wt, [pr]) is pr

    def test_refs_heads_prefix_on_pr_head_branch(self):
        wt = make_worktree("eng-123-add-auth")
        pr = make_pr("refs/heads/eng-123-add-auth")
        assert resolve_pr(wt, [pr]) is pr

    def test_multiple_prs_only_matching_one_returned(self):
        wt = make_worktree("eng-5-fix-bug")
        prs = [
            make_pr("eng-1-other", 1),
            make_pr("eng-5-fix-bug", 5),
            make_pr("eng-9-another", 9),
        ]
        result = resolve_pr(wt, prs)
        assert result is prs[1]

    @pytest.mark.parametrize(
        "branch",
        [
            "eng-123-my-feature",
            "eng-123/my-feature",
            "fix/some-bug",
            "feature-add-login",
        ],
        ids=["linear-kebab", "linear-slash", "fix-slash", "feature-kebab"],
    )
    def test_various_branch_formats(self, branch: str):
        wt = make_worktree(branch)
        pr = make_pr(branch)
        assert resolve_pr(wt, [pr]) is pr


# ---------------------------------------------------------------------------
# MappingRegistry
# ---------------------------------------------------------------------------


class TestMappingRegistryInitial:
    def test_empty_before_refresh(self):
        registry = MappingRegistry()
        assert registry.all_mappings() == []

    def test_get_ticket_returns_none_before_refresh(self):
        registry = MappingRegistry()
        assert registry.get_ticket("/some/path") is None

    def test_get_pr_returns_none_before_refresh(self):
        registry = MappingRegistry()
        assert registry.get_pr("/some/path") is None

    def test_get_mapping_returns_none_before_refresh(self):
        registry = MappingRegistry()
        assert registry.get_mapping("/some/path") is None


class TestMappingRegistryRefresh:
    def test_refresh_populates_mappings(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")
        ticket = make_ticket("feature-x")
        pr = make_pr("feature-x")

        registry.refresh([wt], [ticket], [pr])

        assert len(registry.all_mappings()) == 1

    def test_get_ticket_after_refresh(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")
        ticket = make_ticket("feature-x")

        registry.refresh([wt], [ticket], [])

        assert registry.get_ticket("/repo/wt") is ticket

    def test_get_pr_after_refresh(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")
        pr = make_pr("feature-x")

        registry.refresh([wt], [], [pr])

        assert registry.get_pr("/repo/wt") is pr

    def test_unmatched_worktree_stores_none(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")

        registry.refresh([wt], [], [])

        assert registry.get_ticket("/repo/wt") is None
        assert registry.get_pr("/repo/wt") is None

    def test_unknown_path_returns_none(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")
        registry.refresh([wt], [], [])

        assert registry.get_ticket("/does/not/exist") is None
        assert registry.get_pr("/does/not/exist") is None

    def test_second_refresh_replaces_stale_data(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")
        old_ticket = make_ticket("feature-x", "ENG-1")
        registry.refresh([wt], [old_ticket], [])

        new_ticket = make_ticket("feature-x", "ENG-99")
        registry.refresh([wt], [new_ticket], [])

        assert registry.get_ticket("/repo/wt") is new_ticket

    def test_second_refresh_removes_stale_worktrees(self):
        registry = MappingRegistry()
        wt1 = make_worktree("branch-a", "/repo/wt1")
        wt2 = make_worktree("branch-b", "/repo/wt2")
        registry.refresh([wt1, wt2], [], [])

        # wt2 is gone from the new worktree list
        registry.refresh([wt1], [], [])

        assert registry.get_mapping("/repo/wt2") is None
        assert len(registry.all_mappings()) == 1

    def test_all_mappings_returns_one_entry_per_worktree(self):
        registry = MappingRegistry()
        worktrees = [
            make_worktree("branch-a", "/repo/wt1"),
            make_worktree("branch-b", "/repo/wt2"),
            make_worktree("branch-c", "/repo/wt3"),
        ]
        registry.refresh(worktrees, [], [])

        assert len(registry.all_mappings()) == 3

    def test_get_mapping_returns_full_worktree_mapping(self):
        registry = MappingRegistry()
        wt = make_worktree("feature-x", "/repo/wt")
        ticket = make_ticket("feature-x")
        pr = make_pr("feature-x")

        registry.refresh([wt], [ticket], [pr])

        mapping = registry.get_mapping("/repo/wt")
        assert isinstance(mapping, WorktreeMapping)
        assert mapping.worktree_path == "/repo/wt"
        assert mapping.ticket is ticket
        assert mapping.pr is pr

    def test_refresh_with_empty_worktrees(self):
        registry = MappingRegistry()
        ticket = make_ticket("feature-x")
        registry.refresh([], [ticket], [])

        assert registry.all_mappings() == []
