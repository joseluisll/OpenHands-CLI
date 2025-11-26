"""Tests for ACP confirmation mode functionality."""

import pytest
from acp.schema import (
    AllowedOutcome,
    PermissionOption,
    RequestPermissionRequest,
    RequestPermissionResponse,
)

from openhands_cli.acp_impl.confirmation import ask_user_confirmation_acp
from openhands_cli.user_actions.types import ConfirmationResult


class MockACPConnection:
    """Mock ACP connection for testing."""

    def __init__(self, user_choice: str = "accept"):
        """Initialize mock connection.

        Args:
            user_choice: The choice the user will make ('accept', 'reject', etc.)
        """
        self.user_choice = user_choice
        self.last_request = None

    async def requestPermission(
        self, request: RequestPermissionRequest
    ) -> RequestPermissionResponse:
        """Mock permission request."""
        self.last_request = request
        return RequestPermissionResponse(
            outcome=AllowedOutcome(optionId=self.user_choice, outcome="selected")
        )


class MockAction:
    """Mock action for testing."""

    def __init__(self, action_type: str, args: dict | None = None):
        """Initialize mock action."""
        self.action_type = action_type
        self.args = args or {}
        self.security_risk = "UNKNOWN"

    def to_dict(self):
        """Convert to dict."""
        return {"action_type": self.action_type, "args": self.args}


class TestAskUserConfirmationACP:
    """Test the ACP confirmation function."""

    @pytest.mark.asyncio
    async def test_approve_action(self):
        """Test that approving actions returns ACCEPT."""
        mock_conn = MockACPConnection(user_choice="accept")
        action = MockAction(action_type="run", args={"command": "ls -la"})

        result = await ask_user_confirmation_acp(
            conn=mock_conn,
            session_id="test-session",
            pending_actions=[action],
            using_risk_based_policy=False,
        )

        assert result.decision.value == "accept"
        assert mock_conn.last_request is not None
        assert mock_conn.last_request.sessionId == "test-session"
        assert len(mock_conn.last_request.options) >= 2

    @pytest.mark.asyncio
    async def test_reject_action(self):
        """Test that rejecting actions returns REJECT."""
        mock_conn = MockACPConnection(user_choice="reject")
        action = MockAction(action_type="run", args={"command": "rm -rf /"})

        result = await ask_user_confirmation_acp(
            conn=mock_conn,
            session_id="test-session",
            pending_actions=[action],
            using_risk_based_policy=False,
        )

        assert result.decision.value == "reject"

    @pytest.mark.asyncio
    async def test_multiple_actions(self):
        """Test confirmation with multiple actions."""
        mock_conn = MockACPConnection(user_choice="accept")
        actions = [
            MockAction(action_type="run", args={"command": "ls"}),
            MockAction(action_type="read", args={"path": "/tmp/file"}),
        ]

        result = await ask_user_confirmation_acp(
            conn=mock_conn,
            session_id="test-session",
            pending_actions=actions,
            using_risk_based_policy=False,
        )

        assert result.decision.value == "accept"
        assert mock_conn.last_request is not None


class TestConfirmationOptions:
    """Test the permission options structure."""

    def test_permission_options_structure(self):
        """Test that permission options have the correct structure."""
        approve_opt = PermissionOption(
            optionId="approve", name="Approve action", kind="allow_once"
        )
        reject_opt = PermissionOption(
            optionId="reject", name="Reject action", kind="reject_once"
        )

        assert approve_opt.name == "Approve action"
        assert approve_opt.kind == "allow_once"
        assert reject_opt.name == "Reject action"
        assert reject_opt.kind == "reject_once"
