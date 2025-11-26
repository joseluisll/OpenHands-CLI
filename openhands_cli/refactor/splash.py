"""Splash screen component for OpenHands CLI textual app."""

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.widgets import Static

from openhands_cli.version_check import check_for_updates


def get_openhands_banner() -> str:
    """Get the OpenHands ASCII art banner."""
    return r"""     ___                    _   _                 _
    /  _ \ _ __   ___ _ __ | | | | __ _ _ __   __| |___
    | | | | '_ \ / _ \ '_ \| |_| |/ _` | '_ \ / _` / __|
    | |_| | |_) |  __/ | | |  _  | (_| | | | | (_| \__ \
    \___ /| .__/ \___|_| |_|_| |_|\__,_|_| |_|\__,_|___/
          |_|"""


def get_welcome_message(conversation_id: str | None = None) -> str:
    """Get the complete welcome message with version info."""
    banner = get_openhands_banner()
    
    # Get version information
    version_info = check_for_updates()
    
    message_parts = [banner, ""]
    
    if conversation_id:
        message_parts.append(f"Initialized conversation {conversation_id}")
    else:
        message_parts.append("Welcome to OpenHands CLI!")
    
    message_parts.append("")
    message_parts.append(f"Version: {version_info.current_version}")
    
    if version_info.needs_update and version_info.latest_version:
        message_parts.append(f"⚠ Update available: {version_info.latest_version}")
        message_parts.append("Run 'uv tool upgrade openhands' to update")
    
    message_parts.extend([
        "",
        "Let's start building!",
        "What do you want to build? Type /help for help",
        "",
        "Press any key to continue..."
    ])
    
    return "\n".join(message_parts)


class SplashScreen(Static):
    """A splash screen widget that displays the OpenHands welcome message."""
    
    def __init__(self, conversation_id: str | None = None) -> None:
        """Initialize the splash screen.
        
        Args:
            conversation_id: Optional conversation ID to display
        """
        welcome_text = get_welcome_message(conversation_id)
        super().__init__(welcome_text, id="splash_screen")


def create_splash_layout(conversation_id: str | None = None) -> ComposeResult:
    """Create a centered splash screen layout.
    
    Args:
        conversation_id: Optional conversation ID to display
        
    Yields:
        Splash screen widget centered on screen
    """
    with Center():
        with Middle():
            yield SplashScreen(conversation_id)