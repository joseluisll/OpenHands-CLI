#!/usr/bin/env python3
"""Test script to reproduce the exit modal button visibility issue."""

from textual.app import App, ComposeResult
from textual.widgets import Button

from openhands_cli.refactor.modals.exit_modal import ExitConfirmationModal


class TestApp(App):
    """Simple test app to show the exit modal."""

    def compose(self) -> ComposeResult:
        yield Button("Show Exit Modal", id="show_modal")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show_modal":
            self.push_screen(ExitConfirmationModal())


if __name__ == "__main__":
    app = TestApp()
    app.run()