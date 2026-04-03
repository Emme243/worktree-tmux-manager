"""Tests for modules.github.models — PRState, PullRequest, Comment."""

from __future__ import annotations

from datetime import datetime

import pytest

from modules.github.models import Comment, PRState, PullRequest

# ---------------------------------------------------------------------------
# PRState
# ---------------------------------------------------------------------------


class TestPRState:
    def test_is_str_enum(self):
        assert isinstance(PRState.OPEN, str)

    @pytest.mark.parametrize(
        "member,value",
        [
            (PRState.OPEN, "open"),
            (PRState.MERGED, "merged"),
            (PRState.CLOSED, "closed"),
            (PRState.DRAFT, "draft"),
        ],
        ids=["open", "merged", "closed", "draft"],
    )
    def test_member_values(self, member: PRState, value: str):
        assert member.value == value

    def test_all_four_members_defined(self):
        assert len(PRState) == 4

    def test_constructible_from_string_value(self):
        assert PRState("merged") is PRState.MERGED

    def test_invalid_value_raises_value_error(self):
        with pytest.raises(ValueError):
            PRState("unknown")


# ---------------------------------------------------------------------------
# PullRequest — construction and defaults
# ---------------------------------------------------------------------------

_UPDATED_AT = datetime(2026, 3, 10, 12, 0, 0)

_PR_REQUIRED = dict(
    number=42,
    title="Fix login bug",
    state=PRState.OPEN,
    url="https://github.com/org/repo/pull/42",
    head_branch="fix/login-bug",
    base_branch="main",
    merged=False,
    draft=False,
    updated_at=_UPDATED_AT,
)


class TestPullRequestRequiredFields:
    def test_number_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.number == 42

    def test_title_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.title == "Fix login bug"

    def test_state_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.state is PRState.OPEN

    def test_url_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.url == "https://github.com/org/repo/pull/42"

    def test_head_branch_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.head_branch == "fix/login-bug"

    def test_base_branch_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.base_branch == "main"

    def test_merged_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.merged is False

    def test_draft_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.draft is False

    def test_updated_at_stored(self):
        pr = PullRequest(**_PR_REQUIRED)
        assert pr.updated_at == _UPDATED_AT


class TestPullRequestOptionalFields:
    def test_unread_comment_count_defaults_to_zero(self):
        assert PullRequest(**_PR_REQUIRED).unread_comment_count == 0

    def test_unread_comment_count_can_be_set(self):
        pr = PullRequest(**_PR_REQUIRED, unread_comment_count=5)
        assert pr.unread_comment_count == 5


class TestPullRequestDataclassSemantics:
    def test_equal_instances_compare_equal(self):
        pr1 = PullRequest(**_PR_REQUIRED)
        pr2 = PullRequest(**_PR_REQUIRED)
        assert pr1 == pr2

    def test_different_number_not_equal(self):
        pr1 = PullRequest(**_PR_REQUIRED)
        pr2 = PullRequest(**{**_PR_REQUIRED, "number": 99})
        assert pr1 != pr2

    def test_different_state_not_equal(self):
        pr1 = PullRequest(**_PR_REQUIRED)
        pr2 = PullRequest(**{**_PR_REQUIRED, "state": PRState.MERGED})
        assert pr1 != pr2

    def test_fields_are_mutable(self):
        pr = PullRequest(**_PR_REQUIRED)
        pr.unread_comment_count = 3
        assert pr.unread_comment_count == 3

    @pytest.mark.parametrize(
        "state",
        list(PRState),
        ids=[s.value for s in PRState],
    )
    def test_all_states_accepted(self, state: PRState):
        pr = PullRequest(**{**_PR_REQUIRED, "state": state})
        assert pr.state is state


# ---------------------------------------------------------------------------
# Comment — construction and defaults
# ---------------------------------------------------------------------------

_CREATED_AT = datetime(2026, 3, 11, 9, 30, 0)

_COMMENT_REQUIRED = dict(
    id=101,
    body="Looks good to me!",
    author="alice",
    created_at=_CREATED_AT,
)


class TestCommentRequiredFields:
    def test_id_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.id == 101

    def test_body_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.body == "Looks good to me!"

    def test_author_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.author == "alice"

    def test_created_at_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.created_at == _CREATED_AT


class TestCommentOptionalFields:
    def test_is_read_defaults_to_false(self):
        assert Comment(**_COMMENT_REQUIRED).is_read is False

    def test_is_read_can_be_set_true(self):
        c = Comment(**_COMMENT_REQUIRED, is_read=True)
        assert c.is_read is True


class TestCommentDataclassSemantics:
    def test_equal_instances_compare_equal(self):
        c1 = Comment(**_COMMENT_REQUIRED)
        c2 = Comment(**_COMMENT_REQUIRED)
        assert c1 == c2

    def test_different_id_not_equal(self):
        c1 = Comment(**_COMMENT_REQUIRED)
        c2 = Comment(**{**_COMMENT_REQUIRED, "id": 999})
        assert c1 != c2

    def test_different_body_not_equal(self):
        c1 = Comment(**_COMMENT_REQUIRED)
        c2 = Comment(**{**_COMMENT_REQUIRED, "body": "Needs changes."})
        assert c1 != c2

    def test_fields_are_mutable(self):
        c = Comment(**_COMMENT_REQUIRED)
        c.is_read = True
        assert c.is_read is True
