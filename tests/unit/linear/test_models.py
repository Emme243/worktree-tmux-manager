"""Tests for linear models — Ticket, TicketStatus, TicketWorkflowState, Comment."""

from __future__ import annotations

from datetime import datetime

import pytest

from modules.linear.models import Comment, Ticket, TicketStatus, TicketWorkflowState

# ---------------------------------------------------------------------------
# TicketStatus
# ---------------------------------------------------------------------------


class TestTicketStatus:
    def test_is_str_enum(self):
        assert isinstance(TicketStatus.NOT_STARTED, str)

    @pytest.mark.parametrize(
        "member,value",
        [
            (TicketStatus.NOT_STARTED, "NotStarted"),
            (TicketStatus.IN_PROGRESS, "InProgress"),
            (TicketStatus.IN_REVIEW, "InReview"),
            (TicketStatus.DONE, "Done"),
            (TicketStatus.CANCELLED, "Cancelled"),
        ],
        ids=["not_started", "in_progress", "in_review", "done", "cancelled"],
    )
    def test_member_values(self, member: TicketStatus, value: str):
        assert member.value == value

    def test_all_five_members_defined(self):
        assert len(TicketStatus) == 5

    def test_constructible_from_string_value(self):
        assert TicketStatus("InProgress") is TicketStatus.IN_PROGRESS

    def test_invalid_value_raises_value_error(self):
        with pytest.raises(ValueError):
            TicketStatus("Unknown")


# ---------------------------------------------------------------------------
# TicketWorkflowState
# ---------------------------------------------------------------------------


class TestTicketWorkflowState:
    def test_is_str_enum(self):
        assert isinstance(TicketWorkflowState.NOT_STARTED, str)

    @pytest.mark.parametrize(
        "member,value",
        [
            (TicketWorkflowState.NOT_STARTED, "Not Started"),
            (TicketWorkflowState.WORKTREE_CREATED, "Worktree Created"),
            (TicketWorkflowState.CODING_IN_PROGRESS, "Coding in Progress"),
            (TicketWorkflowState.UNDER_REVIEW, "Under Review"),
        ],
        ids=["not_started", "worktree_created", "coding_in_progress", "under_review"],
    )
    def test_member_values(self, member: TicketWorkflowState, value: str):
        assert member.value == value

    def test_all_four_members_defined(self):
        assert len(TicketWorkflowState) == 4

    def test_constructible_from_string_value(self):
        assert (
            TicketWorkflowState("Worktree Created")
            is TicketWorkflowState.WORKTREE_CREATED
        )


# ---------------------------------------------------------------------------
# Ticket — construction and defaults
# ---------------------------------------------------------------------------

_UPDATED_AT = datetime(2026, 1, 15, 10, 0, 0)

_REQUIRED = dict(
    id="abc123",
    identifier="ENG-42",
    title="Fix the thing",
    status=TicketStatus.IN_PROGRESS,
    branch_name="eng-42-fix-the-thing",
    url="https://linear.app/team/issue/ENG-42",
    updated_at=_UPDATED_AT,
)


class TestTicketRequiredFields:
    def test_id_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.id == "abc123"

    def test_identifier_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.identifier == "ENG-42"

    def test_title_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.title == "Fix the thing"

    def test_status_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.status is TicketStatus.IN_PROGRESS

    def test_branch_name_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.branch_name == "eng-42-fix-the-thing"

    def test_url_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.url == "https://linear.app/team/issue/ENG-42"

    def test_updated_at_stored(self):
        t = Ticket(**_REQUIRED)
        assert t.updated_at == _UPDATED_AT


class TestTicketOptionalFields:
    def test_assignee_defaults_to_none(self):
        assert Ticket(**_REQUIRED).assignee is None

    def test_unread_comment_count_defaults_to_zero(self):
        assert Ticket(**_REQUIRED).unread_comment_count == 0

    def test_assignee_can_be_set(self):
        t = Ticket(**_REQUIRED, assignee="Alice")
        assert t.assignee == "Alice"

    def test_unread_comment_count_can_be_set(self):
        t = Ticket(**_REQUIRED, unread_comment_count=3)
        assert t.unread_comment_count == 3


# ---------------------------------------------------------------------------
# Ticket — equality and immutability behaviour (dataclass semantics)
# ---------------------------------------------------------------------------


class TestTicketDataclassSemantics:
    def test_equal_instances_compare_equal(self):
        t1 = Ticket(**_REQUIRED)
        t2 = Ticket(**_REQUIRED)
        assert t1 == t2

    def test_different_id_not_equal(self):
        t1 = Ticket(**_REQUIRED)
        t2 = Ticket(**{**_REQUIRED, "id": "other"})
        assert t1 != t2

    def test_different_status_not_equal(self):
        t1 = Ticket(**_REQUIRED)
        t2 = Ticket(**{**_REQUIRED, "status": TicketStatus.DONE})
        assert t1 != t2

    def test_fields_are_mutable(self):
        t = Ticket(**_REQUIRED)
        t.unread_comment_count = 5
        assert t.unread_comment_count == 5

    @pytest.mark.parametrize(
        "status",
        list(TicketStatus),
        ids=[s.value for s in TicketStatus],
    )
    def test_all_statuses_accepted(self, status: TicketStatus):
        t = Ticket(**{**_REQUIRED, "status": status})
        assert t.status is status


# ---------------------------------------------------------------------------
# Comment — construction and defaults
# ---------------------------------------------------------------------------

_CREATED_AT = datetime(2026, 3, 10, 8, 0, 0)
_COMMENT_UPDATED_AT = datetime(2026, 3, 10, 9, 0, 0)

_COMMENT_REQUIRED = dict(
    id="comment_abc",
    body="Looks good!",
    user_name="Bob",
    created_at=_CREATED_AT,
    updated_at=_COMMENT_UPDATED_AT,
)


class TestCommentRequiredFields:
    def test_id_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.id == "comment_abc"

    def test_body_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.body == "Looks good!"

    def test_user_name_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.user_name == "Bob"

    def test_created_at_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.created_at == _CREATED_AT

    def test_updated_at_stored(self):
        c = Comment(**_COMMENT_REQUIRED)
        assert c.updated_at == _COMMENT_UPDATED_AT


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
        c2 = Comment(**{**_COMMENT_REQUIRED, "id": "other"})
        assert c1 != c2
