# Few-Shot Example: MCP Tool Testing

## Task
Пользователь: "Как протестировать MCP-сервер перед деплоем?"

## Solution

**Reference:** `~/.claude/modules/16-testing-reference.md` (MCP Testing)

---

## Step 1: Unit Test MCP Tool

```python
# tests/test_mcp_metrics.py
import json
import subprocess

def test_mcp_server_starts():
    """MCP server should start without errors."""
    proc = subprocess.Popen(
        ["python", "mcp_metrics_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5
    )
    proc.terminate()
    assert proc.returncode is None or proc.returncode == -15  # SIGTERM

def test_mcp_tool_list():
    """MCP server should expose expected tools."""
    # Use MCP inspector or direct protocol test
    result = subprocess.run(
        ["npx", "@modelcontextprotocol/inspector", "python", "mcp_metrics_server.py"],
        capture_output=True, text=True, timeout=10
    )
    assert "tools" in result.stdout
```

## Step 2: Integration Test

```python
def test_mcp_tool_invocation():
    """Test actual tool invocation through MCP protocol."""
    # Start server, send JSON-RPC request, verify response
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_metrics", "arguments": {"type": "session"}},
        "id": 1
    }
    # Send via stdio protocol and verify response structure
```

## Step 3: Verify in Claude Code

```bash
# Check MCP server is registered
grep "metrics" ~/.claude/.mcp.json

# Verify tool is available
# In Claude Code session, the tool should appear as mcp__metrics__*
```

---

## Verification

- Server starts without errors
- Tools are listed in MCP inspector
- Tool invocation returns expected format
- Server is properly registered in .mcp.json
