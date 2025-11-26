"""OpenHands Agent Client Protocol (ACP) server implementation."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from acp import (
    Agent as ACPAgent,
    AgentSideConnection,
    InitializeRequest,
    InitializeResponse,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    RequestError,
    SessionNotification,
    stdio_streams,
)
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    AuthenticateRequest,
    AuthenticateResponse,
    AvailableCommandsUpdate,
    CancelNotification,
    Implementation,
    LoadSessionRequest,
    LoadSessionResponse,
    McpCapabilities,
    PromptCapabilities,
    SessionModelState,
    SetSessionModelRequest,
    SetSessionModelResponse,
    SetSessionModeRequest,
    SetSessionModeResponse,
    TextContentBlock,
)

from openhands.sdk import (
    BaseConversation,
    Conversation,
    Message,
    Workspace,
)
from openhands.sdk.event import Event
from openhands.sdk.security.confirmation_policy import AlwaysConfirm, NeverConfirm
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands_cli import __version__
from openhands_cli.acp_impl.event import EventSubscriber
from openhands_cli.acp_impl.runner import ACPConversationRunner
from openhands_cli.acp_impl.slash_commands import (
    SlashCommandRegistry,
    parse_slash_command,
)
from openhands_cli.acp_impl.utils import (
    RESOURCE_SKILL,
    convert_acp_mcp_servers_to_agent_format,
    convert_acp_prompt_to_message_content,
    get_available_models,
)
from openhands_cli.locations import CONVERSATIONS_DIR, WORK_DIR
from openhands_cli.setup import MissingAgentSpec, load_agent_specs


logger = logging.getLogger(__name__)


class OpenHandsACPAgent(ACPAgent):
    """OpenHands Agent Client Protocol implementation."""

    def __init__(self, conn: AgentSideConnection):
        """Initialize the OpenHands ACP agent.

        Args:
            conn: ACP connection for sending notifications
        """
        self._conn = conn
        # Cache of active conversations to preserve state (pause, confirmation, etc.)
        # across multiple operations on the same session
        self._active_sessions: dict[str, BaseConversation] = {}
        # Track running tasks for each session to ensure proper cleanup on cancel
        self._running_tasks: dict[str, asyncio.Task] = {}
        # Track confirmation mode state per session
        self._confirmation_mode: dict[str, bool] = {}
        # Slash commands registry
        self._slash_commands = self._setup_slash_commands()

        logger.info("OpenHands ACP Agent initialized")

    def _setup_slash_commands(self) -> SlashCommandRegistry:
        """Set up slash commands registry.

        Returns:
            SlashCommandRegistry with all available commands
        """
        registry = SlashCommandRegistry()

        registry.register(
            "help",
            "Show available slash commands",
            self._cmd_help,
        )

        registry.register(
            "confirm",
            "Control confirmation mode (on/off/toggle)",
            self._cmd_confirm,
        )

        return registry

    def _cmd_help(self) -> str:
        """Handle /help command."""
        commands = self._slash_commands.get_available_commands()
        lines = ["Available slash commands:", ""]
        for cmd in commands:
            lines.append(f"  {cmd.name} - {cmd.description}")
        return "\n".join(lines)

    async def _cmd_confirm(self, session_id: str, argument: str = "") -> str:
        """Handle /confirm command.

        Args:
            session_id: The session ID
            argument: Command argument (on/off/toggle)

        Returns:
            Status message
        """
        arg = argument.lower().strip()

        # Get current state
        current_state = self._confirmation_mode.get(session_id, False)

        if arg in ("on", "enable", "yes"):
            new_state = True
        elif arg in ("off", "disable", "no"):
            new_state = False
        elif arg in ("toggle", ""):
            new_state = not current_state
        else:
            return (
                f"Unknown argument: {argument}\n"
                f"Usage: /confirm [on|off|toggle]\n"
                f"Current state: {'enabled' if current_state else 'disabled'}"
            )

        # Update confirmation mode for this session
        await self._set_confirmation_mode(session_id, new_state)

        message_part1 = f"Confirmation mode {'enabled' if new_state else 'disabled'}.\n"
        message_part2 = (
            "Agent will ask for permission before executing actions."
            if new_state
            else "Agent will execute actions without asking."
        )
        return message_part1 + message_part2

    async def _set_confirmation_mode(self, session_id: str, enabled: bool) -> None:
        """Enable or disable confirmation mode for a session.

        Args:
            session_id: The session ID
            enabled: Whether to enable confirmation mode
        """
        # Update state
        self._confirmation_mode[session_id] = enabled

        # Update conversation if it exists
        if session_id in self._active_sessions:
            conversation = self._active_sessions[session_id]

            if enabled:
                # Enable confirmation mode
                conversation.set_security_analyzer(LLMSecurityAnalyzer())  # type: ignore[attr-defined]
                conversation.set_confirmation_policy(AlwaysConfirm())  # type: ignore[attr-defined]
                logger.info(f"Enabled confirmation mode for session {session_id}")
            else:
                # Disable confirmation mode
                conversation.set_confirmation_policy(NeverConfirm())  # type: ignore[attr-defined]
                # Note: We don't remove the security analyzer here - just setting
                # NeverConfirm policy is sufficient
                logger.info(f"Disabled confirmation mode for session {session_id}")

        logger.debug(
            f"Confirmation mode for session {session_id}: "
            f"{'enabled' if enabled else 'disabled'}"
        )

    def _get_or_create_conversation(
        self,
        session_id: str,
        working_dir: str | None = None,
        mcp_servers: dict[str, dict[str, Any]] | None = None,
    ) -> BaseConversation:
        """Get an active conversation from cache or create/load it.

        This maintains conversation state (pause, confirmation, etc.) across
        multiple operations on the same session.

        Args:
            session_id: Session/conversation ID (UUID string)
            working_dir: Working directory for workspace (only for new sessions)
            mcp_servers: MCP servers config (only for new sessions)

        Returns:
            Cached or newly created/loaded conversation
        """
        # Check if we already have this conversation active
        if session_id in self._active_sessions:
            logger.debug(f"Using cached conversation for session {session_id}")
            return self._active_sessions[session_id]

        # Create/load new conversation
        logger.debug(f"Creating new conversation for session {session_id}")
        conversation = self._setup_acp_conversation(
            session_id=session_id,
            working_dir=working_dir,
            mcp_servers=mcp_servers,
        )

        # Cache it for future operations
        self._active_sessions[session_id] = conversation
        return conversation

    def _setup_acp_conversation(
        self,
        session_id: str,
        working_dir: str | None = None,
        mcp_servers: dict[str, dict[str, Any]] | None = None,
    ) -> BaseConversation:
        """Set up a conversation for ACP with event streaming support.

        This function reuses the resume logic from
        openhands_cli.setup.setup_conversation but adapts it for ACP by using
        EventSubscriber instead of CLIVisualizer.

        The SDK's Conversation class automatically:
        - Loads from disk if conversation_id exists in persistence_dir
        - Creates a new conversation if it doesn't exist

        Args:
            session_id: Session/conversation ID (UUID string)
            working_dir: Working directory for the workspace. Defaults to WORK_DIR.
            mcp_servers: Optional MCP servers configuration

        Returns:
            Configured conversation that's either loaded from disk or newly created

        Raises:
            MissingAgentSpec: If agent configuration is missing
        """
        # Load agent specs (same as setup_conversation)
        agent = load_agent_specs(
            conversation_id=session_id,
            mcp_servers=mcp_servers,
            skills=[RESOURCE_SKILL],
        )

        # Validate and setup workspace
        if working_dir is None:
            working_dir = WORK_DIR
        working_path = Path(working_dir)

        if not working_path.exists():
            logger.warning(
                f"Working directory {working_dir} doesn't exist, creating it"
            )
            working_path.mkdir(parents=True, exist_ok=True)

        if not working_path.is_dir():
            raise RequestError.invalid_params(
                {"reason": f"Working directory path is not a directory: {working_dir}"}
            )

        workspace = Workspace(working_dir=str(working_path))

        # Create event subscriber for streaming updates (ACP-specific)
        subscriber = EventSubscriber(session_id, self._conn)

        # Get the current event loop for the callback
        loop = asyncio.get_event_loop()

        def sync_callback(event: Event) -> None:
            """Synchronous wrapper that schedules async event handling."""
            asyncio.run_coroutine_threadsafe(subscriber(event), loop)

        # Create conversation with persistence support
        # The SDK automatically loads from disk if conversation_id exists
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
            persistence_dir=CONVERSATIONS_DIR,
            conversation_id=UUID(session_id),
            callbacks=[sync_callback],
            visualizer=None,  # No visualizer needed for ACP
        )

        # # Set up security analyzer (same as setup_conversation with confirmation mode)
        # conversation.set_security_analyzer(LLMSecurityAnalyzer())
        # conversation.set_confirmation_policy(AlwaysConfirm())
        # TODO: implement later

        return conversation

    async def initialize(self, params: InitializeRequest) -> InitializeResponse:
        """Initialize the ACP protocol."""
        logger.info(f"Initializing ACP with protocol version: {params.protocolVersion}")

        # Check if agent is configured
        try:
            load_agent_specs()
            auth_methods = []
            logger.info("Agent configured, no authentication required")
        except MissingAgentSpec:
            # Agent not configured - this shouldn't happen in production
            # but we'll return empty auth methods for now
            auth_methods = []
            logger.warning("Agent not configured - users should run 'openhands' first")

        return InitializeResponse(
            protocolVersion=params.protocolVersion,
            authMethods=auth_methods,
            agentCapabilities=AgentCapabilities(
                loadSession=True,
                mcpCapabilities=McpCapabilities(http=True, sse=True),
                promptCapabilities=PromptCapabilities(
                    audio=False,
                    embeddedContext=True,
                    image=True,
                ),
            ),
            agentInfo=Implementation(
                name="OpenHands CLI ACP Agent",
                version=__version__,
            ),
        )

    async def authenticate(
        self, params: AuthenticateRequest
    ) -> AuthenticateResponse | None:
        """Authenticate the client (no-op for now)."""
        logger.info(f"Authentication requested with method: {params.methodId}")
        return AuthenticateResponse()

    async def newSession(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())

        try:
            # Convert ACP MCP servers to Agent format
            mcp_servers_dict = None
            if params.mcpServers:
                mcp_servers_dict = convert_acp_mcp_servers_to_agent_format(
                    params.mcpServers
                )

            # Validate working directory
            working_dir = params.cwd or str(Path.cwd())
            logger.info(f"Using working directory: {working_dir}")

            # Create conversation and cache it for future operations
            # This reuses the same pattern as openhands --resume
            conversation = self._get_or_create_conversation(
                session_id=session_id,
                working_dir=working_dir,
                mcp_servers=mcp_servers_dict,
            )

            # Get current model and available models
            current_model = conversation.agent.llm.model  # type: ignore[attr-defined]
            available_models = get_available_models(conversation)

            # Build SessionModelState
            model_state = None
            if available_models:
                model_state = SessionModelState(
                    availableModels=available_models,
                    currentModelId=current_model,
                )
                logger.debug(
                    f"Loaded {len(available_models)} available models for new session"
                )

            logger.info(f"Created new session {session_id} with model: {current_model}")

            # Send available slash commands to client
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=AvailableCommandsUpdate(
                        sessionUpdate="available_commands_update",
                        availableCommands=self._slash_commands.get_available_commands(),
                    ),
                )
            )

            return NewSessionResponse(sessionId=session_id, models=model_state)

        except MissingAgentSpec as e:
            logger.error(f"Agent not configured: {e}")
            raise RequestError.internal_error(
                {
                    "reason": "Agent not configured",
                    "details": "Please run 'openhands' to configure the agent first.",
                }
            )
        except RequestError:
            # Re-raise RequestError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to create new session: {e}", exc_info=True)
            raise RequestError.internal_error(
                {"reason": "Failed to create new session", "details": str(e)}
            )

    async def prompt(self, params: PromptRequest) -> PromptResponse:
        """Handle a prompt request."""
        session_id = params.sessionId

        try:
            # Get or create conversation (preserves state like pause/confirmation)
            conversation = self._get_or_create_conversation(session_id=session_id)

            # Convert ACP prompt format to OpenHands message content
            message_content = convert_acp_prompt_to_message_content(params.prompt)

            if not message_content:
                return PromptResponse(stopReason="end_turn")

            # Check if this is a slash command
            # For simplicity, check if the entire message content is a single text block
            # that starts with "/"
            slash_cmd = None
            if isinstance(message_content, list) and len(message_content) == 1:
                first_content = message_content[0]
                # Check if it's a text block (has 'text' attribute and it's a string)
                if hasattr(first_content, "text") and isinstance(
                    getattr(first_content, "text"), str
                ):
                    text = getattr(first_content, "text").strip()
                    slash_cmd = parse_slash_command(text)

            if slash_cmd:
                command, argument = slash_cmd
                logger.info(f"Executing slash command: /{command} {argument}")

                # Execute the slash command
                response_text = await self._slash_commands.execute(
                    command, session_id, argument
                )

                # Send response to client
                if response_text:
                    await self._conn.sessionUpdate(
                        SessionNotification(
                            sessionId=session_id,
                            update=AgentMessageChunk(
                                sessionUpdate="agent_message_chunk",
                                content=TextContentBlock(
                                    type="text", text=response_text
                                ),
                            ),
                        )
                    )

                return PromptResponse(stopReason="end_turn")

            # Send the message with potentially multiple content types
            # (text + images)
            message = Message(role="user", content=message_content)
            conversation.send_message(message)

            # Run the conversation with or without confirmation mode
            # Track the running task so cancel() can wait for proper cleanup
            confirmation_enabled = self._confirmation_mode.get(session_id, False)

            if confirmation_enabled:
                # Run with confirmation mode
                runner = ACPConversationRunner(
                    conversation=conversation,
                    conn=self._conn,
                    session_id=session_id,
                )
                run_task = asyncio.create_task(runner.run_with_confirmation())
            else:
                # Run without confirmation mode (standard execution)
                run_task = asyncio.create_task(asyncio.to_thread(conversation.run))

            self._running_tasks[session_id] = run_task
            try:
                await run_task
            finally:
                # Clean up task tracking
                self._running_tasks.pop(session_id, None)

            # Return the final response
            return PromptResponse(stopReason="end_turn")

        except RequestError:
            # Re-raise RequestError as-is
            raise
        except Exception as e:
            logger.error(f"Error processing prompt: {e}", exc_info=True)
            # Send error notification to client
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=AgentMessageChunk(
                        sessionUpdate="agent_message_chunk",
                        content=TextContentBlock(type="text", text=f"Error: {str(e)}"),
                    ),
                )
            )
            raise RequestError.internal_error(
                {"reason": "Failed to process prompt", "details": str(e)}
            )

    async def _wait_for_task_completion(
        self, task: asyncio.Task, session_id: str, timeout: float = 10.0
    ) -> None:
        """Wait for a task to complete and handle cancellation if needed."""
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except TimeoutError:
            logger.warning(
                f"Conversation thread did not stop within timeout for session "
                f"{session_id}"
            )
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            logger.error(f"Error while waiting for conversation to stop: {e}")
            raise RequestError.internal_error(
                {
                    "reason": "Error during conversation cancellation",
                    "details": str(e),
                }
            )

    async def cancel(self, params: CancelNotification) -> None:
        """Cancel the current operation."""
        logger.info(f"Cancel requested for session: {params.sessionId}")

        try:
            conversation = self._get_or_create_conversation(session_id=params.sessionId)
            conversation.pause()

            running_task = self._running_tasks.get(params.sessionId)
            if not running_task or running_task.done():
                return

            logger.debug(
                f"Waiting for conversation thread to terminate for session "
                f"{params.sessionId}"
            )
            await self._wait_for_task_completion(running_task, params.sessionId)

        except RequestError:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel session {params.sessionId}: {e}")
            raise RequestError.internal_error(
                {"reason": "Failed to cancel session", "details": str(e)}
            )

    async def loadSession(
        self, params: LoadSessionRequest
    ) -> LoadSessionResponse | None:
        """Load an existing session and replay conversation history.

        This implements the same logic as 'openhands --resume <session_id>':
        - Uses _setup_acp_conversation which calls the SDK's Conversation constructor
        - The SDK automatically loads from persistence_dir if conversation_id exists
        - Streams the loaded history back to the client

        Per ACP spec (https://agentclientprotocol.com/protocol/session-setup#loading-sessions):
        - Server should load the session state from persistent storage
        - Replay the conversation history to the client via sessionUpdate notifications
        """
        session_id = params.sessionId
        logger.info(f"Loading session: {session_id}")

        try:
            # Validate session ID format
            try:
                UUID(session_id)
            except ValueError:
                raise RequestError.invalid_params(
                    {"reason": "Invalid session ID format", "sessionId": session_id}
                )

            # Get or create conversation (loads from disk if not in cache)
            # The SDK's Conversation class automatically loads from disk if the
            # conversation_id exists in persistence_dir
            conversation = self._get_or_create_conversation(session_id=session_id)

            # Check if there's actually any history to load
            if not conversation.state.events:
                logger.warning(
                    f"Session {session_id} has no history (new or empty session)"
                )
                return LoadSessionResponse()

            # Stream conversation history to client by reusing EventSubscriber
            # This ensures consistent event handling with live conversations
            logger.info(
                f"Streaming {len(conversation.state.events)} events from "
                f"conversation history"
            )
            subscriber = EventSubscriber(session_id, self._conn)
            for event in conversation.state.events:
                await subscriber(event)

            # Get current model and available models
            current_model = conversation.agent.llm.model  # type: ignore[attr-defined]
            available_models = get_available_models(conversation)

            # Build SessionModelState
            model_state = None
            if available_models:
                model_state = SessionModelState(
                    availableModels=available_models,
                    currentModelId=current_model,
                )
                logger.debug(
                    f"Loaded {len(available_models)} available models for session"
                )

            logger.info(f"Successfully loaded session {session_id}")

            # Send available slash commands to client
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=AvailableCommandsUpdate(
                        sessionUpdate="available_commands_update",
                        availableCommands=self._slash_commands.get_available_commands(),
                    ),
                )
            )

            return LoadSessionResponse(models=model_state)

        except RequestError:
            # Re-raise RequestError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}", exc_info=True)
            raise RequestError.internal_error(
                {"reason": "Failed to load session", "details": str(e)}
            )

    async def setSessionMode(
        self, params: SetSessionModeRequest
    ) -> SetSessionModeResponse | None:
        """Set session mode (no-op for now)."""
        logger.info(f"Set session mode requested: {params.sessionId}")
        return SetSessionModeResponse()

    async def setSessionModel(
        self, params: SetSessionModelRequest
    ) -> SetSessionModelResponse | None:
        """Set session model (no-op for now)."""
        logger.info(f"Set session model requested: {params.sessionId}")
        return SetSessionModelResponse()

    async def extMethod(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Extension method (not supported)."""
        logger.info(f"Extension method '{method}' requested with params: {params}")
        return {"error": "extMethod not supported"}

    async def extNotification(self, method: str, params: dict[str, Any]) -> None:
        """Extension notification (no-op for now)."""
        logger.info(f"Extension notification '{method}' received with params: {params}")


async def run_acp_server() -> None:
    """Run the OpenHands ACP server."""
    logger.info("Starting OpenHands ACP server...")

    reader, writer = await stdio_streams()

    def create_agent(conn: AgentSideConnection) -> OpenHandsACPAgent:
        return OpenHandsACPAgent(conn)

    AgentSideConnection(create_agent, writer, reader)

    # Keep the server running
    await asyncio.Event().wait()
