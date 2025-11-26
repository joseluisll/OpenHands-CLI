"""Tests for the commands module."""

import pytest
from unittest import mock
from textual.widgets import RichLog
from textual_autocomplete import DropdownItem

from openhands_cli.refactor.commands import COMMANDS, show_help


class TestCommands:
    """Tests for command definitions and handlers."""

    def test_commands_list_structure(self):
        """Test that COMMANDS list has correct structure."""
        assert isinstance(COMMANDS, list)
        assert len(COMMANDS) == 2
        
        # Check that all items are DropdownItems
        for command in COMMANDS:
            assert isinstance(command, DropdownItem)
            assert hasattr(command, 'main')
            # main is a Content object, not a string
            assert hasattr(command.main, '__str__')

    @pytest.mark.parametrize(
        "expected_command,expected_description",
        [
            ("/help", "Display available commands"),
            ("/exit", "Exit the application"),
        ],
    )
    def test_commands_content(self, expected_command, expected_description):
        """Test that commands contain expected content."""
        command_strings = [str(cmd.main) for cmd in COMMANDS]
        
        # Find the command that starts with expected_command
        matching_command = None
        for cmd_str in command_strings:
            if cmd_str.startswith(expected_command):
                matching_command = cmd_str
                break
        
        assert matching_command is not None, f"Command {expected_command} not found"
        assert expected_description in matching_command
        assert " - " in matching_command  # Should have separator

    def test_show_help_function_signature(self):
        """Test that show_help has correct function signature."""
        import inspect
        
        sig = inspect.signature(show_help)
        params = list(sig.parameters.keys())
        
        assert len(params) == 1
        assert params[0] == "main_display"

    @pytest.mark.parametrize(
        "expected_content",
        [
            "OpenHands CLI Help",
            "/help",
            "/exit", 
            "Display available commands",
            "Exit the application",
            "Tips:",
            "Type / and press Tab",
            "Use arrow keys to navigate",
            "Press Enter to select",
        ],
    )
    def test_show_help_content_elements(self, expected_content):
        """Test that show_help includes all expected content elements."""
        mock_richlog = mock.MagicMock(spec=RichLog)
        
        show_help(mock_richlog)
        
        # Get the help text that was written
        mock_richlog.write.assert_called_once()
        help_text = mock_richlog.write.call_args[0][0]
        
        assert expected_content in help_text

    def test_show_help_uses_theme_colors(self):
        """Test that show_help uses theme color references."""
        mock_richlog = mock.MagicMock(spec=RichLog)
        
        show_help(mock_richlog)
        
        help_text = mock_richlog.write.call_args[0][0]
        
        # Should use theme color references, not hardcoded colors
        assert "$primary" in help_text
        assert "$secondary" in help_text
        
        # Should not use hardcoded colors
        assert "yellow" not in help_text.lower()
        assert "white" not in help_text.lower()

    def test_show_help_formatting(self):
        """Test that show_help has proper Rich markup formatting."""
        mock_richlog = mock.MagicMock(spec=RichLog)
        
        show_help(mock_richlog)
        
        help_text = mock_richlog.write.call_args[0][0]
        
        # Check for proper Rich markup
        assert "[bold $primary]" in help_text
        assert "[/bold $primary]" in help_text
        assert "[$secondary]" in help_text
        assert "[/$secondary]" in help_text
        assert "[dim]" in help_text
        
        # Should start and end with newlines for proper spacing
        assert help_text.startswith("\n")
        assert help_text.endswith("\n")