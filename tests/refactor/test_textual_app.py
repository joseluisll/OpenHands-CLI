"""Tests for the main textual app functionality."""

from unittest.mock import Mock

from openhands.sdk.security.confirmation_policy import AlwaysConfirm
from openhands_cli.refactor.textual_app import OpenHandsApp


class TestOpenHandsApp:
    """Test cases for OpenHandsApp."""

    def test_action_open_settings_blocked_when_conversation_running(self):
        """Test that settings screen is blocked when conversation is running."""
        app = OpenHandsApp(exit_confirmation=False)
        
        # Mock a running conversation
        mock_conversation_runner = Mock()
        mock_conversation_runner.is_running = True
        app.conversation_runner = mock_conversation_runner
        
        # Mock the notify method to capture the call
        app.notify = Mock()
        
        # Try to open settings
        app.action_open_settings()
        
        # Verify that notify was called with the warning message
        app.notify.assert_called_once_with(
            "Settings are not available while a conversation is running. "
            "Please wait for the current conversation to complete.",
            severity="warning",
            timeout=5.0,
        )

    def test_action_open_settings_allowed_when_no_conversation(self):
        """Test that settings screen opens when no conversation is running."""
        app = OpenHandsApp(exit_confirmation=False)
        
        # No conversation runner
        app.conversation_runner = None
        
        # Mock push_screen to capture the call
        app.push_screen = Mock()
        
        # Try to open settings
        app.action_open_settings()
        
        # Verify that push_screen was called with a SettingsScreen
        app.push_screen.assert_called_once()
        args = app.push_screen.call_args[0]
        assert len(args) == 1
        # Check that the settings screen has the callback set
        settings_screen = args[0]
        assert settings_screen.on_settings_saved is not None

    def test_action_open_settings_allowed_when_conversation_not_running(self):
        """Test that settings screen opens when conversation exists but not running."""
        app = OpenHandsApp(exit_confirmation=False)
        
        # Mock a non-running conversation
        mock_conversation_runner = Mock()
        mock_conversation_runner.is_running = False
        app.conversation_runner = mock_conversation_runner
        
        # Mock push_screen to capture the call
        app.push_screen = Mock()
        
        # Try to open settings
        app.action_open_settings()
        
        # Verify that push_screen was called with a SettingsScreen
        app.push_screen.assert_called_once()

    def test_on_settings_updated_reloads_conversation_runner(self):
        """Test that settings update reloads the conversation runner."""
        app = OpenHandsApp(exit_confirmation=False)
        
        # Mock existing conversation runner
        mock_conversation_runner = Mock()
        mock_confirmation_policy = AlwaysConfirm()
        mock_conversation_runner.get_confirmation_policy.return_value = (
            mock_confirmation_policy
        )
        app.conversation_runner = mock_conversation_runner
        
        # Mock create_conversation_runner to return a new mock
        new_mock_conversation_runner = Mock()
        app.create_conversation_runner = Mock(return_value=new_mock_conversation_runner)
        
        # Call the settings updated method
        app._on_settings_updated()
        
        # Verify that a new conversation runner was created
        app.create_conversation_runner.assert_called_once()
        
        # Verify that the confirmation policy was restored
        new_mock_conversation_runner.set_confirmation_policy.assert_called_once_with(
            mock_confirmation_policy
        )
        
        # Verify that the app's conversation runner was updated
        assert app.conversation_runner == new_mock_conversation_runner

    def test_on_settings_updated_does_nothing_when_no_conversation_runner(self):
        """Test that settings update does nothing when no conversation runner exists."""
        app = OpenHandsApp(exit_confirmation=False)
        
        # No conversation runner
        app.conversation_runner = None
        
        # Mock create_conversation_runner to ensure it's not called
        app.create_conversation_runner = Mock()
        
        # Call the settings updated method
        app._on_settings_updated()
        
        # Verify that no new conversation runner was created
        app.create_conversation_runner.assert_not_called()

