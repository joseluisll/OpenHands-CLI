"""MainDisplay widget for rendering conversation content.

This widget wraps VerticalScroll and handles UserInputSubmitted messages
to render user messages in the conversation view. It does not handle
SlashCommandSubmitted - those bubble up to the App for command execution.
"""

from textual import on
from textual.containers import VerticalScroll
from textual.widgets import Static

from openhands_cli.tui.messages import UserInputSubmitted


class MainDisplay(VerticalScroll):
    """Scrollable conversation display that handles user input rendering.
    
    This widget:
    - Renders user messages when UserInputSubmitted is received
    - Lets SlashCommandSubmitted bubble through (doesn't handle it)
    - Provides a scrollable view of the conversation
    
    Messages flow:
        InputField → AppState → MainDisplay → App
        
    MainDisplay intercepts UserInputSubmitted to render the message,
    then allows it to continue bubbling to App for agent processing.
    """
    
    @on(UserInputSubmitted)
    async def on_user_input_submitted(self, event: UserInputSubmitted) -> None:
        """Handle user input by rendering it in the conversation view.
        
        The message continues to bubble up to App for agent processing.
        We don't call event.stop() so the App can also handle it.
        """
        # Render the user message
        user_message_widget = Static(
            f"> {event.content}", 
            classes="user-message", 
            markup=False
        )
        await self.mount(user_message_widget)
        self.scroll_end(animate=False)
