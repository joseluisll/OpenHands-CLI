"""Tests for the textual app functionality."""

import unittest.mock as mock

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Input, Static

from openhands_cli.refactor.textual_app import OpenHandsApp


class TestOpenHandsApp:
    """Tests for the OpenHandsApp class."""

    def test_app_initialization(self):
        """Test that the app initializes correctly."""
        app = OpenHandsApp()
        assert isinstance(app, OpenHandsApp)
        assert hasattr(app, "CSS")
        assert isinstance(app.CSS, str)

    def test_css_contains_required_styles(self):
        """Test that CSS contains all required style definitions."""
        app = OpenHandsApp()
        css = app.CSS

        # Check for main layout styles
        assert "Screen" in css
        assert "layout: vertical" in css

        # Check for main display styles
        assert "#main_display" in css
        assert "height: 1fr" in css

        # Check for input area styles
        assert "#input_area" in css
        assert "dock: bottom" in css

        # Check for user input styles
        assert "#user_input" in css
        assert "border: solid" in css

    @mock.patch("openhands_cli.refactor.textual_app.get_welcome_message")
    async def test_compose_creates_correct_widgets(self, mock_welcome):
        """Test that compose method creates the correct widgets."""
        mock_welcome.return_value = "Test welcome message"

        app = OpenHandsApp()
        async with app.run_test() as pilot:
            # Check that main display exists and is a VerticalScroll
            main_display = pilot.app.query_one("#main_display", VerticalScroll)
            assert isinstance(main_display, VerticalScroll)
            assert main_display.id == "main_display"

            # Check that input area exists
            input_area = pilot.app.query_one("#input_area")
            assert input_area.id == "input_area"

            # Check that user input exists
            user_input = pilot.app.query_one("#user_input", Input)
            assert isinstance(user_input, Input)
            assert user_input.id == "user_input"

    @mock.patch("openhands_cli.refactor.textual_app.get_welcome_message")
    async def test_on_mount_adds_welcome_message(self, mock_welcome):
        """Test that on_mount adds welcome message to display."""
        from openhands_cli.refactor.theme import OPENHANDS_THEME

        welcome_text = "Test welcome message"
        mock_welcome.return_value = welcome_text

        app = OpenHandsApp()
        async with app.run_test() as pilot:
            # Verify welcome message was called with theme
            mock_welcome.assert_called_once_with(theme=OPENHANDS_THEME)

            # Verify main display exists (welcome message should be added during mount)
            main_display = pilot.app.query_one("#main_display", VerticalScroll)
            assert main_display is not None

            # Verify input exists and has focus
            user_input = pilot.app.query_one("#user_input", Input)
            assert user_input is not None

    def test_on_input_submitted_handles_empty_input(self):
        """Test that empty input is ignored."""
        app = OpenHandsApp()

        # Mock the query_one method
        mock_main_display = mock.MagicMock(spec=VerticalScroll)
        app.query_one = mock.MagicMock(return_value=mock_main_display)

        # Create mock event with empty input
        mock_event = mock.MagicMock()
        mock_event.value = ""
        mock_event.input.value = ""

        # Call the method
        app.on_input_submitted(mock_event)

        # mount should not be called for empty input
        mock_main_display.mount.assert_not_called()

        # Input value should not be cleared
        assert mock_event.input.value == ""

    def test_on_input_submitted_handles_whitespace_only_input(self):
        """Test that whitespace-only input is ignored."""
        app = OpenHandsApp()

        # Mock the query_one method
        mock_main_display = mock.MagicMock(spec=VerticalScroll)
        app.query_one = mock.MagicMock(return_value=mock_main_display)

        # Create mock event with whitespace-only input
        mock_event = mock.MagicMock()
        mock_event.value = "   \t\n  "
        mock_event.input.value = "   \t\n  "

        # Call the method
        app.on_input_submitted(mock_event)

        # mount should not be called for whitespace-only input
        mock_main_display.mount.assert_not_called()

        # Input value should not be cleared
        assert mock_event.input.value == "   \t\n  "

    @pytest.mark.parametrize(
        "user_input",
        [
            "hello world",
            "test message",
            "multi\nline\ninput",
            "special chars: !@#$%^&*()",
            "unicode: 🚀 ✨ 🎉",
        ],
    )
    def test_on_input_submitted_handles_valid_input(self, user_input):
        """Test that valid input is processed correctly."""
        app = OpenHandsApp()

        # Mock the query_one method
        mock_main_display = mock.MagicMock(spec=VerticalScroll)
        app.query_one = mock.MagicMock(return_value=mock_main_display)

        # Mock the conversation runner
        mock_conversation_runner = mock.MagicMock()
        mock_conversation_runner.is_running = False
        app.conversation_runner = mock_conversation_runner

        # Create mock event with valid input
        mock_event = mock.MagicMock()
        mock_event.value = user_input
        mock_event.input.value = user_input

        # Call the method
        app.on_input_submitted(mock_event)

        # mount should be called three times:
        # user message + processing + placeholder
        assert mock_main_display.mount.call_count == 3

        # First call should be the user message widget
        first_call_widget = mock_main_display.mount.call_args_list[0][0][0]
        # The widget should be a Static widget with user-message class
        assert first_call_widget.__class__.__name__ == 'Static'
        assert 'user-message' in first_call_widget.classes
        # The widget content should contain the user input
        assert user_input in str(first_call_widget.content)

        # Second call should be the processing message widget
        second_call_widget = mock_main_display.mount.call_args_list[1][0][0]
        assert "Processing message" in str(second_call_widget.content)

        # Third call should be the placeholder message widget
        third_call_widget = mock_main_display.mount.call_args_list[2][0][0]
        assert "conversation runner" in str(third_call_widget.content)

        # Input value should be cleared
        assert mock_event.input.value == ""

    def test_on_input_submitted_message_format(self):
        """Test that input messages are formatted correctly."""
        app = OpenHandsApp()

        # Mock the query_one method
        mock_main_display = mock.MagicMock(spec=VerticalScroll)
        app.query_one = mock.MagicMock(return_value=mock_main_display)

        # Mock the conversation runner
        mock_conversation_runner = mock.MagicMock()
        mock_conversation_runner.is_running = False
        app.conversation_runner = mock_conversation_runner

        # Create mock event
        mock_event = mock.MagicMock()
        mock_event.value = "test message"
        mock_event.input.value = "test message"

        # Call the method
        app.on_input_submitted(mock_event)

        # Check the exact format of the first message (user input)
        first_call_widget = mock_main_display.mount.call_args_list[0][0][0]
        widget_content = str(first_call_widget.content)
        assert widget_content == "> test message"
        assert widget_content.startswith("> ")

    @mock.patch("openhands_cli.refactor.textual_app.get_welcome_message")
    @mock.patch("openhands_cli.refactor.textual_app.MinimalConversationRunner")
    async def test_input_functionality_integration(
        self, mock_runner_class, mock_welcome
    ):
        """Test that input functionality works end-to-end."""
        mock_welcome.return_value = "Welcome!"

        # Mock the conversation runner to avoid actual API calls
        mock_runner = mock.MagicMock()
        mock_runner.is_running = False

        # Make process_message_async return an async function
        async def mock_process_message_async(message):
            pass

        mock_runner.process_message_async = mock_process_message_async
        mock_runner_class.return_value = mock_runner

        app = OpenHandsApp()
        async with app.run_test() as pilot:
            # Type a message (avoid words that trigger autocomplete)
            await pilot.press("t", "e", "s", "t")

            # Get the input widget
            user_input = pilot.app.query_one("#user_input", Input)
            assert user_input.value == "test"

            # Submit the input
            await pilot.press("enter")

            # Input should be cleared after submission
            assert user_input.value == ""

            # Check that message was added to the display
            # The VerticalScroll should contain both welcome message and user input
            # We can't easily check the exact content, but we can verify it exists
            pilot.app.query_one("#main_display", VerticalScroll)

    @mock.patch("openhands_cli.refactor.textual_app.get_welcome_message")
    async def test_welcome_message_called_on_mount(self, mock_welcome):
        """Test that get_welcome_message is called during on_mount."""
        from openhands_cli.refactor.theme import OPENHANDS_THEME

        mock_welcome.return_value = "Test message"

        app = OpenHandsApp()
        async with app.run_test():
            # Verify get_welcome_message was called with theme during app initialization
            mock_welcome.assert_called_once_with(theme=OPENHANDS_THEME)

    @mock.patch("openhands_cli.refactor.textual_app.get_welcome_message")
    async def test_widget_ids_are_set_correctly(self, mock_welcome):
        """Test that widgets have correct IDs set."""
        mock_welcome.return_value = "test"

        app = OpenHandsApp()
        async with app.run_test() as pilot:
            # Check main display ID
            main_display = pilot.app.query_one("#main_display")
            assert main_display.id == "main_display"

            # Check input area ID
            input_area = pilot.app.query_one("#input_area")
            assert input_area.id == "input_area"

            # Check user input ID
            user_input = pilot.app.query_one("#user_input")
            assert user_input.id == "user_input"

    @mock.patch("openhands_cli.refactor.textual_app.get_welcome_message")
    async def test_main_display_configuration(self, mock_welcome):
        """Test that main display is configured correctly."""
        mock_welcome.return_value = "test"

        app = OpenHandsApp()
        async with app.run_test() as pilot:
            main_display = pilot.app.query_one("#main_display", VerticalScroll)

            # Check VerticalScroll configuration
            assert isinstance(main_display, VerticalScroll)
            assert main_display.id == "main_display"

    def test_custom_theme_properties(self):
        """Test that custom OpenHands theme has correct colors."""
        from openhands_cli.refactor.theme import OPENHANDS_THEME

        # Check theme has correct properties
        assert OPENHANDS_THEME.name == "openhands"
        assert OPENHANDS_THEME.primary == "#ffe165"  # Logo, cursor color
        assert OPENHANDS_THEME.secondary == "#ffffff"  # Borders, plain text
        assert OPENHANDS_THEME.accent == "#277dff"  # Special text
        assert OPENHANDS_THEME.foreground == "#ffffff"  # Default text color
        assert OPENHANDS_THEME.background == "#222222"  # Background color
        assert OPENHANDS_THEME.dark is True

        # Check custom variables
        assert "input-placeholder-foreground" in OPENHANDS_THEME.variables
        assert OPENHANDS_THEME.variables["input-placeholder-foreground"] == "#727987"
        assert OPENHANDS_THEME.variables["input-selection-background"] == "#ffe165 20%"

    def test_theme_registration_and_activation(self):
        """Test that theme is registered and set as active."""
        app = OpenHandsApp()

        # Check that theme is set as active
        assert app.theme == "openhands"

    def test_cursor_css_styling(self):
        """Test that CSS includes cursor styling."""
        app = OpenHandsApp()

        # Check that CSS includes cursor styling
        assert "Input .input--cursor" in app.CSS
        assert "background: $primary" in app.CSS
        assert "color: $background" in app.CSS


class TestCommandsAndAutocomplete:
    """Tests for command handling and autocomplete functionality."""
