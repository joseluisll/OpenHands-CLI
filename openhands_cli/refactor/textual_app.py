"""Minimal textual app for OpenHands CLI migration.

This is the starting point for migrating from prompt_toolkit to textual.
It creates a basic app with:
- A splash screen showing the OpenHands welcome message
- A main container (Static widget) that takes up most of the screen
- An Input widget at the bottom for user messages
- The Input widget is automatically focused after splash dismissal
"""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Input, Static

from openhands_cli.refactor.splash import create_splash_layout


class OpenHandsApp(App):
    """A minimal textual app for OpenHands CLI with splash screen."""

    CSS = """
    #splash_screen {
        text-align: center;
        content-align: center middle;
    }

    #main_container {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #user_input {
        height: 3;
        margin: 1 0;
    }

    .hidden {
        display: none;
    }
    """

    def __init__(self) -> None:
        """Initialize the app."""
        super().__init__()
        self.show_splash = True

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        # Splash screen (shown initially)
        yield from create_splash_layout()

        # Main chat interface (hidden initially)
        with Container(id="chat_interface", classes="hidden"):
            # Main container that takes up most of the screen
            content = (
                "OpenHands CLI - Textual Version\n\n"
                "This is the main content area.\n"
                "It will display conversation history and agent responses."
            )
            yield Static(content, id="main_container")

            # Input widget at the bottom for user messages
            yield Input(placeholder="Type your message here...", id="user_input")

    def on_mount(self) -> None:
        """Called when app starts."""
        # Show splash screen initially
        pass

    def on_key(self, event) -> None:  # noqa: ARG002
        """Handle key presses."""
        if self.show_splash:
            # Any key press dismisses splash screen
            self.dismiss_splash()

    def dismiss_splash(self) -> None:
        """Hide splash screen and show main chat interface."""
        if not self.show_splash:
            return

        self.show_splash = False

        # Hide splash screen
        splash = self.query_one("#splash_screen")
        splash.add_class("hidden")

        # Show chat interface
        chat_interface = self.query_one("#chat_interface")
        chat_interface.remove_class("hidden")

        # Focus the input widget
        self.query_one("#user_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when user submits input."""
        if self.show_splash:
            return

        user_message = event.value
        if user_message.strip():
            # For now, just display the message in the main container
            main_container = self.query_one("#main_container", Static)
            current_content = str(main_container.content)
            new_content = f"{current_content}\n\n> {user_message}"
            main_container.update(new_content)

            # Clear the input
            event.input.value = ""


def main():
    """Run the textual app."""
    app = OpenHandsApp()
    app.run()


if __name__ == "__main__":
    main()
