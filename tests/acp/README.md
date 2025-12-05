# ACP Tests

This directory contains tests for the OpenHands ACP (Agent Client Protocol) implementation.

## Status: ✅ Fully Working

**All ACP functionality is now working correctly!**

- ✅ All 68 unit tests passing
- ✅ Integration tests passing  
- ✅ session/new returns valid session IDs
- ✅ Compatible with agent-client-protocol 0.7.0+
- ✅ Works with Zed, Toad, and other ACP clients

**Previous Issue (FIXED)**: The main branch had a bug where `session/new` returned `null` instead of a session ID. This was caused by incompatibility with agent-client-protocol 0.7.0+ which introduced a breaking API change from request objects to kwargs. This has been completely resolved.

## Test Files

### `test_jsonrpc_integration.py` ✅

**Purpose**: Integration tests that verify JSON-RPC protocol compliance.

These tests are the **primary validation** for ACP functionality. They:
- Test actual JSON-RPC message exchange over stdin/stdout
- Verify the exact message format that real clients (Zed, Toad, etc.) will send
- Include a regression test for the null session ID bug
- Validate parameter naming conventions (camelCase in JSON-RPC, snake_case in Python)

**Key Tests**:
- `test_jsonrpc_initialize`: Verifies initialize returns correct structure
- `test_jsonrpc_session_new_returns_session_id`: Ensures session/new returns valid session ID
- `test_jsonrpc_null_result_regression`: **Critical** - Ensures session/new never returns null
- `test_parameter_naming_conventions`: Validates camelCase/snake_case conversion

### `test_agent.py`, `test_acp_advanced.py`, `test_event_subscriber.py` ✅

**Status**: ✅ **FIXED** - All tests updated and passing

These unit tests have been migrated to the new ACP library API (agent-client-protocol 0.7.0+).

**Changes Made**:
- ✅ Updated method calls from `agent.method(request_object)` to `agent.method(**kwargs)`
- ✅ Updated parameter naming from camelCase to snake_case
- ✅ Updated response field assertions from camelCase to snake_case
- ✅ All 68 ACP tests are now passing

**Migration Example**:
```python
# Old API (pre-0.7.0)
request = NewSessionRequest(cwd="/path", mcp_servers=[])
response = await agent.new_session(request)
assert response.sessionId is not None

# New API (0.7.0+) - Current Implementation
response = await agent.new_session(cwd="/path", mcp_servers=[])
assert response.session_id is not None
```

## Running Tests

```bash
# Run all ACP tests
uv run pytest tests/acp/ -v

# Run only integration tests (recommended)
uv run pytest tests/acp/test_jsonrpc_integration.py -v

# Run specific test
uv run pytest tests/acp/test_jsonrpc_integration.py::test_jsonrpc_session_new_returns_session_id -v
```

## ACP Library Version

The project is pinned to `agent-client-protocol==0.7.0` for stability. This version:
- Uses kwargs-based method signatures instead of request objects
- Automatically converts between camelCase (JSON-RPC) and snake_case (Python)
- Provides better typing support

## Debugging ACP Issues

For debugging ACP issues, use the scripts in `scripts/acp/`:

```bash
# Interactive JSON-RPC testing
python scripts/acp/debug_client.py

# Manual JSON-RPC message sending
python scripts/acp/jsonrpc_cli.py
```

## Common Issues

### Session ID is null ✅ FIXED
**Symptom**: `{"jsonrpc":"2.0","id":2,"result":null}` for session/new

**Status**: This issue has been fixed in the current implementation.

**Previous Cause**: Method signature mismatch - agent method didn't match ACP library expectations (used request objects instead of kwargs)

**Solution Applied**: Updated method signature to use kwargs and return proper response object:
```python
async def new_session(self, cwd: str, mcp_servers: list[Any], **_kwargs: Any) -> NewSessionResponse:
    session_id = str(uuid.uuid4())
    # ... implementation ...
    return NewSessionResponse(session_id=session_id)  # Uses snake_case in Python
```

**Verification**: Run `python /tmp/test_acp.py` to verify that session/new returns a valid session ID.

### Parameter naming errors
**Symptom**: Method receives None or wrong values for parameters

**Cause**: Parameter names don't match what ACP library sends (camelCase vs snake_case)

**Fix**: Use snake_case in Python method signatures:
- `protocolVersion` → `protocol_version`
- `mcpServers` → `mcp_servers`
- `sessionId` → `session_id`

The ACP library handles the conversion automatically.
