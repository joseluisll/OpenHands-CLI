# SessionUpdate Implementation for OpenHands CLI ACP

## Overview
This document describes the implementation of real-time event streaming via `sessionUpdate` in the OpenHands CLI ACP (Agent Client Protocol) implementation.

## Implementation Details

### 1. EventSubscriber Class (`openhands_cli/acp_impl/utils.py`)

The `EventSubscriber` class is the core component that converts OpenHands SDK events into ACP session update notifications.

**Key Features:**
- **Real-time streaming**: Events are streamed as they occur during conversation execution
- **General-purpose design**: Works with any event type based on their attributes
- **Three event categories**:
  1. **ActionEvent**: Streams reasoning, thoughts, and tool call notifications
  2. **ObservationEvent/UserRejectObservation/AgentErrorEvent**: Streams tool call update notifications
  3. **LLMConvertibleEvent**: Streams agent message chunks (text and images)

**Methods:**
- `__call__(event)`: Main entry point, dispatches to specific handlers
- `_handle_action_event(event)`: Processes action events
- `_handle_observation_event(event)`: Processes observation and error events
- `_handle_llm_convertible_event(event)`: Processes other LLM-convertible events

### 2. Utility Functions (`openhands_cli/acp_impl/utils.py`)

#### `get_tool_kind(tool_name: str) -> str`
Maps tool names to ACP ToolKind values:
- `execute_bash`, `terminal`, `bash` → `"execute"`
- `str_replace_editor`, `file_editor` → `"edit"`
- `browser_use`, `browser` → `"fetch"`
- `task_tracker` → `"think"`
- Others → `"other"`

#### `_extract_locations(event: ActionEvent) -> list[ToolCallLocation] | None`
Extracts file locations from action events:
- Supports `path` attribute (with optional `view_range` or `insert_line`)
- Supports `directory` attribute
- Returns `None` if no location information available

#### `_rich_text_to_plain(text: Any) -> str`
Converts Rich Text objects to plain strings:
- Checks for `.plain` attribute (Rich Text)
- Falls back to `str()` conversion

### 3. Agent Integration (`openhands_cli/acp_impl/agent.py`)

**Updated `prompt()` method:**
1. Creates an `EventSubscriber` instance for the session
2. Wraps it in a synchronous callback (since Conversation callbacks are sync)
3. Adds the callback to `conversation.callbacks`
4. Runs the conversation (callbacks are triggered in real-time)
5. Removes the callback after completion

**Key Implementation Details:**
```python
# Create event subscriber for streaming updates
subscriber = EventSubscriber(session_id, self._conn)

# Create a synchronous wrapper for the async subscriber
def sync_callback(event):
    """Synchronous wrapper that schedules async event handling."""
    asyncio.create_task(subscriber(event))

# Add the callback to the conversation
conversation.callbacks.append(sync_callback)
```

## Event Flow

```
Conversation.run()
    ↓
Generates events (ActionEvent, ObservationEvent, MessageEvent, etc.)
    ↓
Triggers callbacks
    ↓
sync_callback schedules async EventSubscriber
    ↓
EventSubscriber processes event and determines type
    ↓
Sends appropriate SessionUpdate via conn.sessionUpdate()
```

## ACP Session Update Types

1. **agent_message_chunk** (SessionUpdate2):
   - Used for reasoning content, thoughts, and general text/image responses
   - ContentBlock1 (text) or ContentBlock2 (image)

2. **tool_call** (SessionUpdate4):
   - Used when an action is initiated
   - Includes: toolCallId, title, kind, status="pending", content, locations, rawInput

3. **tool_call_update** (SessionUpdate5):
   - Used when a tool call completes or fails
   - Includes: toolCallId, status=("completed"/"failed"), content, rawOutput

## Design Principles

1. **Generality**: Implementation works with any event type that has standard attributes:
   - `visualize`: For display content
   - `title`: For action titles
   - `tool_call_id`: For linking actions and observations
   - `tool_name`: For tool kind mapping
   - `action`: For accessing action details
   - `observation`: For accessing observation results

2. **Robustness**: All event processing is wrapped in try-except blocks to prevent single event failures from crashing the entire stream

3. **Extensibility**: New event types can be easily added by:
   - Checking event type in `__call__()`
   - Creating a new handler method
   - Using existing ACP SessionUpdate types or defining new ones

## Testing

Comprehensive tests in:
- `tests/acp/test_agent.py`: Integration tests for the agent
- `tests/acp/test_event_subscriber.py`: Unit tests for EventSubscriber

**Test Coverage:**
- ActionEvent handling (reasoning, thought, tool_call)
- ObservationEvent handling (tool_call_update with completed status)
- AgentErrorEvent handling (tool_call_update with failed status)
- MessageEvent handling (agent_message_chunk)
- Empty text filtering
- User message filtering (not sent)
- Image content support

## Differences from software-agent-sdk Reference

1. **Conversation API**: CLI uses `Conversation` class directly vs. `ConversationService`
2. **Callback Pattern**: CLI uses sync callbacks that schedule async tasks
3. **Session Management**: CLI stores `Conversation` objects vs. conversation IDs

## Future Enhancements

Potential improvements:
1. Add support for streaming LLM token-by-token (currently streams complete chunks)
2. Add support for more tool-specific location extraction patterns
3. Add metrics/telemetry for event processing performance
4. Consider batching rapid events to reduce notification overhead
