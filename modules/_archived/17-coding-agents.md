# Module: Coding Agents Reference
# On-demand reference: Load when working with code agents, IDEs, or coding tools
# Version: 1.0.0 | Created: 2026-02-05

---

## Overview

Reference guide for coding agents, AI-powered IDEs, and code generation tools.

**Gaps Covered:** GAP-CODE-CLI-001/002, GAP-CODE-AUTO-001, GAP-CODE-IDE-001/002/007, GAP-CODE-MODEL-003/007/008, GAP-BROWSER-001

---

## Table of Contents

1. [Claude Code CLI Patterns](#1-claude-code-cli-patterns)
2. [Aider CLI Agent](#2-aider-cli-agent)
3. [SWE-agent (Princeton)](#3-swe-agent)
4. [AI IDEs Comparison](#4-ai-ides-comparison)
5. [Cline Autonomous Agent](#5-cline-autonomous-agent)
6. [Code Model Selection](#6-code-model-selection)
7. [Browser Automation](#7-browser-automation)
8. [Claude Computer Use API](#8-claude-computer-use-api)
9. [Computer Use Comparison](#9-computer-use-comparison)

---

## 1. Claude Code CLI Patterns (GAP-CODE-CLI-001)

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE CLI                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │   Prompt    │──►│   Agent     │──►│   Tools     │       │
│  │   Input     │   │   Loop      │   │   Execution │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│         │                │                  │                │
│         ▼                ▼                  ▼                │
│  [System Prompt]    [ReAct Loop]      [Built-in Tools]      │
│  - CLAUDE.md        - Observe         - Read/Write/Edit     │
│  - rules/           - Think           - Bash                │
│  - modules/         - Act             - Grep/Glob           │
│                     - Repeat          - MCP Servers         │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Configuration Hierarchy

| Level | Location | Priority | Scope |
|-------|----------|----------|-------|
| Global | `~/.claude/CLAUDE.md` | Lowest | All projects |
| Project | `PROJECT/CLAUDE.md` | Higher | Current project |
| Local | `PROJECT/.claude/CLAUDE.md` | Highest | Current project |
| Rules | `~/.claude/rules/*.md` | Auto-loaded | All sessions |

### 1.3 Tool Patterns

**Read-Analyze-Edit Cycle:**

```
1. Read file(s) to understand context
2. Analyze requirements and plan changes
3. Edit with minimal, targeted modifications
4. Verify changes compile/work
```

**Multi-File Refactoring:**

```
1. Use Glob to find all affected files
2. Use Grep to understand usage patterns
3. Plan changes across all files
4. Edit files in dependency order
5. Run tests to verify
```

### 1.4 Best Practices

| Practice | Rationale |
|----------|-----------|
| Read before edit | Understand context |
| Small, atomic edits | Easier to review |
| Test after changes | Catch regressions |
| Use Task for complex work | Subagent isolation |
| Avoid `git add .` | Explicit file staging |

---

## 2. Aider CLI Agent (GAP-CODE-CLI-002)

### 2.1 Overview

**Aider** — AI pair programming in terminal. Works with local Git repos.

| Feature | Details |
|---------|---------|
| Models | GPT-4, Claude, local LLMs |
| Context | Automatic file detection |
| Git | Built-in commit support |
| Multi-file | Handles complex refactors |

### 2.2 Usage Patterns

```bash
# Start session
aider --model claude-3-5-sonnet-20241022

# Add files to context
/add src/main.py src/utils.py

# Make changes
/code Add error handling to the parse function

# Review changes
/diff

# Commit
/commit
```

### 2.3 Architecture Mode

```bash
# Architect mode: plan before code
aider --architect

# Two-step: plan (cheap model) → code (expensive model)
aider --architect --model gpt-4o-mini --editor-model claude-3-5-sonnet
```

### 2.4 Comparison with Claude Code

| Feature | Claude Code | Aider |
|---------|-------------|-------|
| Provider | Anthropic only | Multi-provider |
| Tools | MCP, extensive | Git-focused |
| Context | Manual file add | Auto-detection |
| Integration | IDE plugins | Terminal only |
| Subagents | Yes | No |

---

## 3. SWE-agent (GAP-CODE-AUTO-001)

### 3.1 Overview

**SWE-agent** (Princeton) — autonomous software engineering agent.

| Metric | Value |
|--------|-------|
| SWE-bench score | 12.5% (GPT-4) |
| Task type | Real GitHub issues |
| Approach | Custom interface |

### 3.2 Architecture

```
┌─────────────────────────────────────────┐
│            SWE-agent                     │
├─────────────────────────────────────────┤
│  ┌───────────┐   ┌───────────────────┐ │
│  │ LLM Agent │◄─►│ Agent-Computer    │ │
│  │ (GPT-4)   │   │ Interface (ACI)   │ │
│  └───────────┘   └───────────────────┘ │
│                         │               │
│                         ▼               │
│              ┌───────────────────┐      │
│              │ Container (Docker)│      │
│              │ - File system     │      │
│              │ - Git operations  │      │
│              │ - Test execution  │      │
│              └───────────────────┘      │
└─────────────────────────────────────────┘
```

### 3.3 Key Features

| Feature | Description |
|---------|-------------|
| **ACI** | Custom interface for code navigation |
| **Linting** | Catches syntax errors before commit |
| **Guardrails** | Prevents common mistakes |
| **Containerization** | Safe execution environment |

### 3.4 Running SWE-agent

```bash
# Install
pip install sweagent

# Run on issue
python run.py \
    --model_name gpt4 \
    --data_path issues/test.json \
    --repo_path /path/to/repo
```

---

## 4. AI IDEs Comparison (GAP-CODE-IDE-001, GAP-CODE-IDE-002)

### 4.1 Cursor AI

**Cursor** — AI-first code editor (fork of VS Code).

| Feature | Details |
|---------|---------|
| Base | VS Code fork |
| Models | GPT-4, Claude |
| Pricing | Free tier + Pro ($20/mo) |
| Key feature | Inline AI editing |

**Capabilities:**
- Tab completion (context-aware)
- Cmd+K inline editing
- Chat with codebase
- Multi-file edits
- Terminal integration

### 4.2 Windsurf (Codeium)

**Windsurf** — AI IDE by Codeium (acquired by Cognition 2025).

| Feature | Details |
|---------|---------|
| Base | Custom (not VS Code) |
| Models | Proprietary + GPT-4 |
| Pricing | Free tier + Pro |
| Key feature | Cascade agent |

**Cascade Agent:**
- Multi-step task execution
- Tool use (terminal, browser)
- Context understanding
- Flow-based work

### 4.3 Comparison Matrix

| Feature | Cursor | Windsurf | VS Code + Copilot |
|---------|--------|----------|-------------------|
| Inline completion | ✅ Fast | ✅ Fast | ✅ Fast |
| Multi-file edit | ✅ Good | ✅ Cascade | ❌ Limited |
| Agent mode | ❌ No | ✅ Cascade | ❌ No |
| Terminal | ✅ Built-in | ✅ Built-in | ✅ Built-in |
| Codebase chat | ✅ Yes | ✅ Yes | ⚠️ Limited |
| Price (Pro) | $20/mo | $15/mo | $10/mo |
| Local LLMs | ⚠️ Limited | ❌ No | ⚠️ Via plugins |

---

## 5. Cline Autonomous Agent (GAP-CODE-IDE-007)

### 5.1 Overview

**Cline** (formerly Claude Dev) — autonomous coding agent for VS Code.

| Feature | Details |
|---------|---------|
| Platform | VS Code extension |
| Models | Claude, GPT-4, local |
| Approach | Autonomous with approval |
| Cost | Usage-based (API costs) |

### 5.2 Capabilities

```
┌─────────────────────────────────────────┐
│              CLINE AGENT                 │
├─────────────────────────────────────────┤
│                                          │
│  File Operations:                        │
│  ├─► Read files                         │
│  ├─► Write files (with diff preview)    │
│  └─► Create directories                 │
│                                          │
│  Terminal:                               │
│  ├─► Execute commands                   │
│  ├─► Run tests                          │
│  └─► Install packages                   │
│                                          │
│  Browser:                                │
│  ├─► Launch browser                     │
│  ├─► Screenshot analysis                │
│  └─► Web research                       │
│                                          │
│  MCP Support:                            │
│  └─► Custom tool integration            │
│                                          │
└─────────────────────────────────────────┘
```

### 5.3 Approval Flow

```
User Request → Agent Plans → Shows Diff → User Approves → Executes
                   ↓
              Can reject or modify
```

### 5.4 Best Practices

| Practice | Reason |
|----------|--------|
| Review every diff | Catch mistakes |
| Use auto-approve for read-only | Speed up research |
| Set spending limits | Control costs |
| Use Claude for complex, GPT for simple | Optimize cost/quality |

---

## 6. Code Model Selection (GAP-CODE-MODEL-003, GAP-CODE-MODEL-007, GAP-CODE-MODEL-008)

### 6.1 Code Model Comparison

| Model | Provider | Context | Best For |
|-------|----------|---------|----------|
| **Claude 3.5 Sonnet** | Anthropic | 200K | General coding, complex logic |
| **Claude Opus 4.5** | Anthropic | 200K | Critical systems, architecture |
| **GPT-4o** | OpenAI | 128K | Balanced performance |
| **GPT-4o mini** | OpenAI | 128K | Fast, cheap tasks |
| **DeepSeek Coder V2** | DeepSeek | 128K | Code generation, cost-effective |
| **Mistral Devstral** | Mistral | 32K | European compliance |
| **Codestral** | Mistral | 32K | Code-specific, fast |

### 6.2 Selection Guide

```
Task Complexity?
├─► Critical/Security → Claude Opus 4.5
├─► Complex/Multi-file → Claude Sonnet
├─► Standard coding → GPT-4o / DeepSeek Coder
├─► Simple/Fast → GPT-4o mini / Codestral
└─► Cost-sensitive → DeepSeek Coder V2
```

### 6.3 DeepSeek Coder V2 (GAP-CODE-MODEL-003)

| Metric | Value |
|--------|-------|
| Parameters | 236B (MoE, 21B active) |
| Context | 128K tokens |
| Languages | 338 |
| HumanEval | 90.2% |
| Price | ~10x cheaper than GPT-4 |

**Best for:**
- High-volume code generation
- Multi-language projects
- Cost-sensitive applications

### 6.4 Mistral Devstral (GAP-CODE-MODEL-008)

| Metric | Value |
|--------|-------|
| Parameters | 8B |
| Context | 32K tokens |
| Specialty | Agentic coding |
| SWE-bench Verified | 30.5% |

**Best for:**
- Fast code completion
- European data compliance
- Edge/local deployment

---

## 7. Browser Automation (GAP-BROWSER-001)

### 7.1 Browser Use (Open Source)

**Browser Use** — open-source browser automation for LLM agents.

```python
from browser_use import Agent

# Create agent
agent = Agent(
    task="Find the cheapest flight from NYC to LA",
    llm=ChatAnthropic(model="claude-sonnet-4-20250514")
)

# Run
result = await agent.run()
print(result)
```

### 7.2 Architecture

```
┌─────────────────────────────────────────┐
│           BROWSER USE                    │
├─────────────────────────────────────────┤
│  ┌───────────┐   ┌─────────────────┐   │
│  │ LLM Agent │◄─►│ Browser Control │   │
│  └───────────┘   └─────────────────┘   │
│        │                  │             │
│        ▼                  ▼             │
│  [Actions]          [Playwright]        │
│  - click()          - Chrome/Firefox    │
│  - type()           - Screenshots       │
│  - scroll()         - DOM extraction    │
│  - extract()        - Navigation        │
└─────────────────────────────────────────┘
```

### 7.3 Comparison with Alternatives

| Tool | Type | LLM Support | Ease of Use |
|------|------|-------------|-------------|
| Browser Use | Agent | Multi-model | High |
| Playwright | Framework | DIY | Medium |
| Puppeteer | Framework | DIY | Medium |
| Selenium | Framework | DIY | Low |
| Claude Computer Use | API | Claude only | High |

### 7.4 Integration with Claude Code

```bash
# MCP server for browser
npx -y @anthropic/browser-use-mcp

# Or use built-in WebFetch for simple cases
```

---

## 8. Claude Computer Use API (GAP-COMPUTER-001)

### 8.1 Overview

**Claude Computer Use** — beta API от Anthropic, позволяющая Claude управлять компьютером через screenshots и tool calls.

| Feature | Details |
|---------|---------|
| **Status** | Public beta (Oct 2024+) |
| **Models** | Claude 3.5 Sonnet (2024-10-22+) |
| **Interaction** | Screenshot-based vision + tool execution |
| **Tools** | `computer`, `text_editor`, `bash` |
| **Use Cases** | Browser automation, GUI testing, OS-level tasks |

### 8.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  CLAUDE COMPUTER USE API                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │    Claude    │─────►│  Screenshot  │      │   Desktop    │  │
│  │   3.5 Sonnet │◄─────│   Capture    │◄─────│  Environment │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                                              ▲         │
│         │                                              │         │
│         ▼                                              │         │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Tool Definitions                        │       │
│  ├──────────────────────────────────────────────────────┤       │
│  │  computer:                                           │       │
│  │    - mouse_move(x, y)                                │───────┘
│  │    - left_click()                                    │
│  │    - right_click()                                   │
│  │    - type(text)                                      │
│  │    - screenshot()                                    │
│  │    - cursor_position()                               │
│  │                                                       │
│  │  text_editor:                                        │
│  │    - view(path)                                      │
│  │    - create(path, content)                           │
│  │    - str_replace(path, old, new)                     │
│  │    - insert(path, line, content)                     │
│  │                                                       │
│  │  bash:                                               │
│  │    - execute(command)                                │
│  └──────────────────────────────────────────────────────┘
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Tool Definitions

#### 8.3.1 Computer Tool

**Purpose:** Mouse/keyboard control, screenshot capture.

**Available actions:**

| Action | Parameters | Description |
|--------|------------|-------------|
| `mouse_move` | `x: int, y: int` | Move cursor to coordinates |
| `left_click` | — | Click left mouse button |
| `right_click` | — | Click right mouse button |
| `middle_click` | — | Click middle mouse button |
| `double_click` | — | Double-click left button |
| `type` | `text: str` | Type text at current focus |
| `key` | `text: str` | Press key (Enter, Tab, etc.) |
| `screenshot` | — | Capture current screen |
| `cursor_position` | — | Get current cursor position |

**Example API call:**

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=[
        {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": 1920,
            "display_height_px": 1080,
            "display_number": 1
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "Open Firefox and navigate to example.com"
        }
    ]
)
```

#### 8.3.2 Text Editor Tool

**Purpose:** File editing without screenshots (more efficient).

**Available actions:**

| Action | Parameters | Description |
|--------|------------|-------------|
| `view` | `path: str, view_range?: [int, int]` | View file contents |
| `create` | `path: str, file_text: str` | Create new file |
| `str_replace` | `path, old_str, new_str` | Replace string in file |
| `insert` | `path, insert_line, new_str` | Insert at line number |
| `undo_edit` | `path` | Undo last edit |

**Example:**

```python
tools = [
    {
        "type": "text_editor_20241022",
        "name": "str_replace"
    }
]
```

#### 8.3.3 Bash Tool

**Purpose:** Command execution in shell.

**Available actions:**

| Action | Parameters | Description |
|--------|------------|-------------|
| `execute` | `command: str, restart?: bool` | Run shell command |

**Example:**

```python
tools = [
    {
        "type": "bash_20241022",
        "name": "bash",
        "restart": False
    }
]
```

### 8.4 Screenshot-Based Interaction

#### 8.4.1 Vision Model Processing

**Workflow:**

```
1. Capture screenshot → Base64 PNG
2. Send to Claude with vision → Claude analyzes screen
3. Claude determines action → Returns tool call
4. Execute tool call → Update screen
5. Capture new screenshot → Repeat
```

**Screenshot frequency:**
- Every action: High accuracy, high cost
- Every 3-5 actions: Balanced
- On-demand only: Low cost, lower reliability

#### 8.4.2 Resolution and Scaling

**Supported resolutions:**

| Resolution | Scale | Use Case |
|------------|-------|----------|
| 1920x1080 | 1.0x | Desktop apps |
| 1280x800 | 1.0x | Laptops |
| 3840x2160 | 0.5x | 4K displays (scaled) |

**Scaling considerations:**

```python
# Define display size
tools = [{
    "type": "computer_20241022",
    "display_width_px": 1920,
    "display_height_px": 1080,
    "display_number": 1  # For multi-monitor
}]
```

**Important:** Claude uses absolute coordinates based on defined display size.

#### 8.4.3 Coordinate Mapping

**Challenge:** Screenshots may be scaled for API efficiency.

**Solution:**

```python
# Claude works with logical coordinates
# Scale factor = screenshot_width / display_width_px

# Example:
# Display: 1920x1080
# Screenshot sent: 960x540 (50% scaled)
# Claude clicks at (480, 270) → Maps to (960, 540) on actual display
```

### 8.5 Safety Guardrails

#### 8.5.1 Mandatory Restrictions

**API-level guardrails:**

```
✅ REQUIRED:
- Sandboxed environment (VM, container)
- No access to host system
- Network isolation (optional but recommended)
- Timeout limits (prevent infinite loops)
- User confirmation for destructive actions

❌ PROHIBITED:
- Running on production systems
- Access to real user credentials
- Unsupervised execution on host OS
- File system access outside sandbox
```

#### 8.5.2 Recommended Sandboxing

**Docker container setup:**

```dockerfile
FROM ubuntu:22.04

# Install desktop environment
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    firefox \
    python3 \
    python3-pip

# Create non-root user
RUN useradd -m -s /bin/bash claude

# Set display
ENV DISPLAY=:99

# Start Xvfb
CMD Xvfb :99 -screen 0 1920x1080x24 & \
    fluxbox & \
    python3 /app/agent.py
```

**Run isolated:**

```bash
docker run --rm -it \
    --name claude-computer-use \
    --security-opt seccomp=unconfined \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    claude-computer-use
```

#### 8.5.3 Action Confirmation

**For high-risk actions, request user approval:**

```python
# Before executing destructive command
if is_destructive(action):
    print(f"⚠️  Claude wants to execute: {action}")
    confirm = input("Approve? [y/N]: ")
    if confirm.lower() != 'y':
        return {"status": "denied"}
```

### 8.6 Implementation Patterns

#### 8.6.1 Agentic Loop

```python
import anthropic
import base64
from screenshot import capture_screen

client = anthropic.Anthropic()

messages = [{"role": "user", "content": "Open browser and search for 'AI news'"}]

while True:
    # Capture current screen state
    screenshot = capture_screen()
    screenshot_b64 = base64.b64encode(screenshot).decode()

    # Send to Claude
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        tools=[
            {"type": "computer_20241022", "name": "computer",
             "display_width_px": 1920, "display_height_px": 1080}
        ],
        messages=messages + [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/png",
                        "data": screenshot_b64
                    }}
                ]
            }
        ]
    )

    # Check if task complete
    if response.stop_reason == "end_turn":
        break

    # Execute tool calls
    for block in response.content:
        if block.type == "tool_use":
            result = execute_tool(block.name, block.input)
            messages.append({
                "role": "assistant", "content": response.content
            })
            messages.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": block.id,
                           "content": str(result)}]
            })
```

#### 8.6.2 Hybrid Approach (Computer Use + Direct APIs)

**Best practice:** Use Computer Use only when necessary, prefer direct APIs.

```python
# INEFFICIENT: Use Computer Use to click GitHub UI
claude: "Click 'New Issue' button on GitHub"

# EFFICIENT: Use GitHub API directly
import requests
requests.post("https://api.github.com/repos/owner/repo/issues",
              json={"title": "...", "body": "..."})
```

**Decision matrix:**

| Task | Approach | Why |
|------|----------|-----|
| GitHub operations | GitHub API | Faster, cheaper, reliable |
| Browser testing | Computer Use | Need to test actual UI |
| Desktop app control | Computer Use | No API available |
| File editing | `text_editor` tool | More efficient than GUI |

### 8.7 Cost Optimization

#### 8.7.1 Screenshot Frequency

**Cost comparison:**

| Strategy | Screenshots per task | Cost multiplier |
|----------|---------------------|-----------------|
| Every action | 20-50 | 5-10x |
| Every 3 actions | 7-15 | 2-3x |
| State changes only | 3-5 | 1x (baseline) |

**Optimization:**

```python
# Only screenshot after significant actions
screenshot_triggers = [
    "page_load",
    "modal_open",
    "navigation_change",
    "error_state"
]

if action in screenshot_triggers:
    screenshot = capture_screen()
```

#### 8.7.2 Prompt Caching

**Cache screenshot analysis:**

```python
# First turn: Full screenshot analysis (cache write: 1.25x cost)
# Subsequent turns: Cached analysis (cache read: 0.1x cost)

# Enable caching
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    system=[
        {
            "type": "text",
            "text": "System prompt here...",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    # ... messages
)
```

**Savings:** Up to 90% on repeated screenshot analysis (within 5-minute cache TTL).

#### 8.7.3 Resolution Optimization

**Trade-off:**

| Resolution | Image size | API cost | Accuracy |
|------------|------------|----------|----------|
| 1920x1080 | ~2MB | High | Best |
| 1280x720 | ~1MB | Medium | Good |
| 960x540 | ~500KB | Low | Acceptable |

**Recommendation:** Use 1280x720 for most tasks, 1920x1080 for precision work.

### 8.8 Comparison with Traditional Automation

| Feature | Computer Use | Selenium | Playwright |
|---------|--------------|----------|------------|
| **Learning curve** | Low (natural language) | High (code) | Medium (code) |
| **Reliability** | Medium (vision-based) | High (DOM-based) | High (DOM-based) |
| **Speed** | Slow (screenshots) | Fast | Fast |
| **Cost** | High (API + vision) | Low (OSS) | Low (OSS) |
| **Flexibility** | High (any UI) | Web only | Web only |
| **Debugging** | Hard (black box) | Easy (inspect) | Easy (inspect) |
| **Desktop apps** | ✅ Yes | ❌ No | ❌ No |
| **AI assistance** | ✅ Native | ❌ No | ❌ No |

**When to use Computer Use:**
- ✅ Desktop applications (no API)
- ✅ Legacy UIs (hard to automate)
- ✅ Exploratory testing (AI-driven)
- ✅ One-off tasks (not worth coding)

**When to use Selenium/Playwright:**
- ✅ Production test suites (speed matters)
- ✅ CI/CD pipelines (cost-sensitive)
- ✅ Web-only automation
- ✅ High-volume testing

### 8.9 Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Screenshot lag** | Slow execution | Reduce frequency |
| **Vision errors** | Wrong clicks | Verify before action |
| **No DOM access** | Can't read hidden elements | Use `text_editor` for files |
| **Cost** | High for long tasks | Use direct APIs when possible |
| **Resolution dependency** | Breaks on scaling | Define fixed resolution |

---

## 9. Computer Use Comparison (GAP-COMPUTER-002)

### 9.1 OpenAI Computer-Using Agent (Operator)

**OpenAI Operator** — similar capability от OpenAI (announced Dec 2024, research preview).

| Feature | Details |
|---------|---------|
| **Status** | Research preview (ChatGPT Pro only) |
| **Model** | GPT-4o (vision + reasoning) |
| **Interaction** | Browser-based (CUA in browser) |
| **Capabilities** | Web browsing, form filling, booking |

### 9.2 Anthropic vs OpenAI Comparison

| Aspect | Claude Computer Use | OpenAI Operator |
|--------|---------------------|-----------------|
| **Availability** | Public beta API | ChatGPT Pro only (Jan 2025) |
| **Access** | API (self-hosted agent) | Web UI (managed service) |
| **Scope** | Full OS control | Browser only |
| **Tools** | computer, text_editor, bash | Browser automation |
| **Pricing** | API usage (pay-per-use) | $200/mo (ChatGPT Pro) |
| **Desktop apps** | ✅ Yes | ❌ No (browser only) |
| **Self-hosting** | ✅ Yes | ❌ No |
| **Customization** | ✅ Full control | ⚠️ Limited |
| **Safety** | User-managed sandbox | OpenAI-managed |
| **Use case** | Developers, automation | End users, simple tasks |

### 9.3 Architecture Comparison

**Claude Computer Use:**

```
Developer → API call → Claude → Screenshot analysis → Tool execution → User's machine
                                    ↓
                            computer / text_editor / bash
```

**OpenAI Operator:**

```
User → ChatGPT Pro UI → GPT-4o → Browser control → Web interactions
                                     ↓
                              Managed browser instance
```

### 9.4 Strengths & Weaknesses

#### Claude Computer Use

**Strengths:**
- ✅ Full OS control (desktop apps, terminal, files)
- ✅ API access (integrate into custom agents)
- ✅ Self-hosted (full control)
- ✅ Multiple tool types (computer, bash, text_editor)
- ✅ Developer-focused

**Weaknesses:**
- ❌ Requires infrastructure setup (sandbox)
- ❌ Higher complexity (manage execution environment)
- ❌ No managed service option
- ❌ Vision errors (screenshot-based)

#### OpenAI Operator

**Strengths:**
- ✅ Managed service (no setup)
- ✅ User-friendly (ChatGPT UI)
- ✅ Safe by default (OpenAI-managed sandbox)
- ✅ Easy access (ChatGPT Pro subscription)

**Weaknesses:**
- ❌ Browser only (no desktop apps)
- ❌ No API access (can't integrate)
- ❌ Limited to web tasks
- ❌ ChatGPT Pro required ($200/mo)
- ❌ No self-hosting

### 9.5 Use Case Recommendations

| Use Case | Best Choice | Why |
|----------|-------------|-----|
| **Desktop app automation** | Claude Computer Use | Full OS control |
| **Web browsing for end users** | OpenAI Operator | Managed service |
| **Developer automation** | Claude Computer Use | API access |
| **Complex workflows** | Claude Computer Use | More tools available |
| **Simple web tasks** | OpenAI Operator | Easier to use |
| **CI/CD integration** | Claude Computer Use | API integration |
| **Non-technical users** | OpenAI Operator | ChatGPT UI |
| **Security-sensitive** | Claude Computer Use | Self-hosted sandbox |

### 9.6 Future Directions

**Trends (2025-2026):**

| Trend | Claude | OpenAI | Impact |
|-------|--------|--------|--------|
| **Multi-modal agents** | ✅ Active | ✅ Active | More reliable automation |
| **Reduced hallucination** | ✅ Progress | ✅ Progress | Higher success rates |
| **Cost reduction** | Expected | Expected | Broader adoption |
| **API standardization** | Needed | Needed | Interoperability |
| **Safety guardrails** | Improving | Improving | Production-ready |

**Prediction:** Both will converge on similar capabilities, differentiated by:
- Claude: Developer/API focus, self-hosted
- OpenAI: Consumer/UI focus, managed service

### 9.7 Alternative Approaches

| Approach | Tool | Best For |
|----------|------|----------|
| **Web automation** | Playwright MCP | Web testing, scraping |
| **Browser agent** | Browser Use (OSS) | Custom browser automation |
| **Desktop automation** | PyAutoGUI + LLM | Simple desktop tasks |
| **RPA tools** | UiPath, Automation Anywhere | Enterprise workflows |
| **Traditional testing** | Selenium, Cypress | Production test suites |

**Hybrid strategy:**
- Use Computer Use for exploratory/one-off tasks
- Use traditional tools for production automation
- Use MCP servers for API integrations

---

---

## Уточняющие вопросы (Clarification Questions)

Когда пользователь задаёт задачу в этом домене без достаточных деталей, задайте следующие вопросы:

### Общие вопросы

| Вопрос | Когда задавать | Критичность |
|--------|---------------|-------------|
| Agent platform? (Claude Code, Aider, Cursor, Cline, SWE-agent) | Не указана платформа | 🔴 Критично |
| Task complexity? (simple script, multi-file refactor, full app) | Неясен scope работы | 🔴 Критично |
| Model preference? (Claude Opus/Sonnet, GPT-4o, DeepSeek, local) | Выбор модели влияет на качество и стоимость | 🟡 Важно |
| Budget constraints? (API cost limit) | Задачи могут быть дорогими | 🟡 Важно |
| Automation level? (full autonomous, approval required) | Safety vs convenience | 🟡 Важно |
| Integration needs? (GitHub, CI/CD, IDE plugins) | Workflow integration | 🟢 Желательно |

### Специфические вопросы по типам задач

**Claude Code CLI usage:**
- Working directory? (project path)
- Git operations required? (commit, PR, branch)
- Subagent needed? (complex task >30 min)
- MCP servers? (GitHub, filesystem, custom)
- Budget? (session budget, task budget)

**Aider CLI usage:**
- Model selection? (Claude, GPT-4, local)
- Architect mode? (plan before code)
- Files to include? (context scope)
- Commit strategy? (auto-commit, manual review)

**SWE-agent usage:**
- GitHub issue URL? (real issue или custom)
- Repository path? (local checkout)
- Test suite? (validation criteria)
- Container setup? (Docker для isolation)

**AI IDE selection (Cursor, Windsurf, Cline):**
- IDE preference? (VS Code extension или standalone)
- Features needed? (inline completion, chat, agent mode)
- Budget? (subscription cost $10-20/mo)
- Team collaboration? (shared snippets, consistency)

**Code model selection:**
- Task type? (general coding, architecture, critical systems)
- Language? (Python, JS, Go, Rust, etc.)
- Context size? (32K, 128K, 200K tokens)
- Cost priority? (optimize cost vs quality)
- Latency? (fast completion vs deep reasoning)

**Browser automation:**
- Target site? (web app URL)
- Automation type? (scraping, testing, interaction)
- Authentication? (login required, session management)
- Tool preference? (Browser Use, Playwright, Computer Use API)
- Headless? (background или visible browser)

**Computer Use API:**
- Desktop app? (requires Computer Use, no API alternative)
- Web task? (can use direct API instead)
- Sandbox setup? (Docker, VM, security considerations)
- Resolution? (1920x1080, scaled)
- Cost awareness? (screenshot frequency optimization)

**Model cost optimization:**
- Can use haiku для simple tasks?
- Subagent decomposition для cost savings?
- Cache heavy prompts?
- Batch operations?

### Performance & Quality Questions:

- Response time requirements? (fast completion vs deep analysis)
- Quality bar? (prototype vs production code)
- Code review? (automatic static analysis before delivery)
- Testing? (TDD, coverage target)

---

## Уровни авторизации (Authorization Levels)

| Операция | Уровень | Подтверждение |
|----------|---------|---------------|
| **Чтение кодовой базы** | READ | Нет |
| Read files (Claude Code, Aider) | READ | Нет |
| Analyze code structure | READ | Нет |
| **Планирование** | PLAN | Нет |
| Generate implementation plan | PLAN | Нет |
| Architecture design | PLAN | Нет (не меняет код) |
| **Написание кода** | MODIFY | Да |
| Create new files | MODIFY | Да (показать файлы) |
| Edit existing code | MODIFY | Да (показать diff) |
| Refactoring | MODIFY | Да |
| **Git операции** | MODIFY | Да |
| git add, commit | MODIFY | Да (показать commit message) |
| git push | MODIFY | Да (если не force push) |
| Create Pull Request | MODIFY | Да (показать PR description) |
| **Запуск тестов** | ANALYZE | Нет (если read-only) |
| pytest, npm test | ANALYZE | Нет |
| Static analysis (pylint, eslint) | ANALYZE | Нет |
| **Запуск кода** | MODIFY | Да (может менять состояние) |
| Execute script | MODIFY | Да (показать что запускается) |
| Run build | MODIFY | Да |
| **Browser automation** | NETWORK_ACTIVE | Да |
| Launch browser, navigate | NETWORK_ACTIVE | Да (показать target URL) |
| Fill forms, click buttons | NETWORK_ACTIVE | Да |
| Screenshot capture | ANALYZE | Нет |
| **Computer Use API** | NETWORK_ACTIVE / MODIFY | Да + scope |
| Desktop app control | NETWORK_ACTIVE | Да + sandboxed environment |
| Mouse/keyboard automation | MODIFY | Да (показать actions) |
| File editing via Computer Use | MODIFY | Да (prefer text_editor tool) |
| **Deployment** | INFRASTRUCTURE | Да + rollback plan |
| Deploy to production | INFRASTRUCTURE | Да + approval + monitoring |
| Infrastructure changes | INFRASTRUCTURE | Да + terraform plan review |
| **Model API calls** | MODIFY | Да (budget check) |
| GPT-4o/Claude API calls | MODIFY | Да (если бюджет ограничен) |
| Subagent spawning | MODIFY | Да (cost awareness) |
| **Destructive operations** | DESTRUCTIVE | Да + явное подтверждение |
| Delete files | DESTRUCTIVE | Да + type exact command |
| Force push | DESTRUCTIVE | Да (never to main/master) |
| Drop database | DESTRUCTIVE | Да + backup verification |

---

**Version**: 1.1.0
**Created**: 2026-02-05
**Updated**: 2026-02-06
**Coverage**: CLI agents, IDEs, code models, browser automation, Computer Use API
**Gaps Resolved**: GAP-CODE-CLI-001/002, GAP-CODE-AUTO-001, GAP-CODE-IDE-001/002/007, GAP-CODE-MODEL-003/007/008, GAP-BROWSER-001, GAP-COMPUTER-001, GAP-COMPUTER-002, GAP-CODE-IDE-008, GAP-CODE-IDE-003/004, GAP-CODE-CLI-003/004/005, GAP-CODE-AUTO-002/003, GAP-CODE-MODEL-009, GAP-COMPUTER-004, GAP-CASE-001/002

---

## Coding Agent Best Practices & Case Studies (Gaps: GAP-CODE-IDE-008/003/004, GAP-CODE-CLI-003/004/005, GAP-CODE-AUTO-002/003, GAP-CODE-MODEL-009, GAP-COMPUTER-004, GAP-CASE-001/002)

### IDE Agent Best Practices (GAP-CODE-IDE-008)

```yaml
# Optimal settings for coding agents in IDEs
claude_code_settings:
  model_selection:
    default: sonnet-4.5
    complex_reasoning: opus-4.6
    simple_edits: haiku-4.5

  context_management:
    max_files_in_context: 10
    prioritize_open_files: true
    auto_include_tests: true
    exclude_patterns: [node_modules, .git, dist, build]

  tool_preferences:
    prefer_edit_over_write: true  # Preserve file history
    batch_similar_edits: true
    auto_format_on_save: true
    run_linter_before_commit: true

  safety:
    require_approval_for:
      - file_deletion
      - bulk_refactoring: "> 5 files"
      - dependency_updates
      - config_changes

  performance:
    cache_system_prompts: true
    stream_responses: true
    parallel_file_reads: true
```

### Claude Code Advanced Workflows (GAP-CODE-IDE-003)

**Power User Patterns**:

```bash
# 1. Multi-step workflow automation
claude --workflow "
  1. Read all test files
  2. Identify missing test coverage
  3. Generate tests for uncovered code
  4. Run tests and fix failures
  5. Commit with message 'Add missing tests'
"

# 2. Context-aware refactoring
claude "Refactor auth module: extract common patterns, add type hints, improve error handling" \
  --context "src/auth/*.py" \
  --context "tests/auth/*.py"

# 3. Iterative improvement
claude "Optimize database queries" --iterations 3 \
  --success-criteria "All queries < 100ms"

# 4. Code review automation
claude "Review PR #123: check for security issues, performance problems, and style violations" \
  --review-mode \
  --output review_report.md
```

### Cursor Integration Patterns (GAP-CODE-IDE-004)

```typescript
// Cursor IDE with Claude integration
// .cursor/rules
rules:
  - name: "Always write tests first"
    trigger: "new_function"
    action: "Generate test before implementation"

  - name: "Security checks"
    trigger: "before_commit"
    action: "Scan for secrets, SQL injection, XSS"

  - name: "Code review"
    trigger: "pre_pr"
    action: "Review changes, suggest improvements"

// Cursor + Claude workflow
1. Write test (Cursor autocomplete)
2. Implement function (Claude Code)
3. Refactor (Cursor + Claude collaboration)
4. Commit (Claude pre-commit hooks)
```

### CLI Agent Automation (GAP-CODE-CLI-003)

```bash
#!/bin/bash
# Automate Claude Code workflows

# Daily code quality check
claude-daily-check() {
  claude "Analyze codebase for issues" \
    --output daily_report.md \
    --notify-on-issues

  if [ $? -ne 0 ]; then
    slack-notify "Code quality issues found"
  fi
}

# Automated bug triage
claude-triage-bugs() {
  for issue in $(gh issue list --label bug --json number -q '.[].number'); do
    claude "Analyze issue #$issue and suggest fix" \
      --context "$(gh issue view $issue --json body -q '.body')" \
      --output "triage/issue_$issue.md"
  done
}

# Continuous refactoring
claude-refactor-watch() {
  fswatch -o src/ | while read; do
    claude "Review recent changes and suggest refactorings" \
      --since "10 minutes ago"
  done
}
```

### Agent Hooks Best Practices (GAP-CODE-CLI-004)

```python
# ~/.claude/hooks/custom_hook.py
# Best practices for hook development

class BestPracticeHook:
    def __init__(self):
        self.timeout = 5000  # Always set timeout
        self.log_file = "/home/user/.claude/logs/custom.log"

    def execute(self, context):
        """Hook execution with best practices."""
        try:
            # 1. Fast execution (<5s)
            start = time.time()

            # 2. Idempotent (safe to run multiple times)
            result = self.process(context)

            # 3. Structured logging
            self.log({
                "hook": "custom_hook",
                "duration": time.time() - start,
                "status": "success",
                "context": context
            })

            # 4. Return structured data
            return {"status": "success", "data": result}

        except Exception as e:
            # 5. Graceful error handling
            self.log({"hook": "custom_hook", "status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}

# Hook registration (settings.json)
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "python ~/.claude/hooks/custom_hook.py", "blocking": true, "timeout": 5000}
        ]
      }
    ]
  }
}
```

### Custom Tool Development (GAP-CODE-CLI-005)

```python
# Build custom MCP tools for Claude Code
from mcp.server import Server, Tool
from mcp.types import TextContent

app = Server("custom-tools")

@app.tool()
async def analyze_codebase(path: str) -> list[TextContent]:
    """Analyze codebase complexity."""
    # Implement analysis
    complexity = calculate_complexity(path)

    return [TextContent(
        type="text",
        text=f"Complexity: {complexity}\nRecommendation: ..."
    )]

@app.tool()
async def generate_documentation(module: str) -> list[TextContent]:
    """Auto-generate documentation."""
    docs = extract_docstrings(module)
    markdown = format_as_markdown(docs)

    return [TextContent(type="text", text=markdown)]

# Run server
# python custom_tools.py

# Use in Claude Code
# claude "Use analyze_codebase tool on src/"
```

### Autonomous Coding Patterns (GAP-CODE-AUTO-002)

```python
# AI-driven development patterns
class AutonomousCodingAgent:
    def develop_feature(self, requirement):
        """Fully autonomous feature development."""

        # 1. Requirement analysis
        analysis = self.analyze_requirement(requirement)

        # 2. Architecture decision
        architecture = self.design_architecture(analysis)

        # 3. TDD approach
        tests = self.generate_tests(architecture)

        # 4. Implementation
        code = self.implement_feature(tests)

        # 5. Iterative refinement
        while not self.all_tests_pass(code, tests):
            code = self.fix_failing_tests(code, tests)

        # 6. Code review
        issues = self.self_review(code)

        # 7. Refactoring
        if issues:
            code = self.refactor(code, issues)

        # 8. Documentation
        docs = self.generate_documentation(code)

        # 9. Commit
        self.git_commit(code, tests, docs, message=f"Implement {requirement}")

        return {"code": code, "tests": tests, "docs": docs}

# Guardrails for autonomous coding
guardrails = {
    "max_files_modified": 10,
    "require_human_approval_for": ["security", "breaking_changes"],
    "test_coverage_threshold": 0.8,
    "max_iterations": 5
}
```

### Code Review Automation (GAP-CODE-AUTO-003)

```yaml
# Automated PR review workflow
pr_review_automation:
  triggers:
    - pull_request_opened
    - pull_request_synchronized

  checks:
    - name: Security scan
      tool: semgrep
      blocking: true

    - name: Code quality
      tool: sonarqube
      threshold: B rating

    - name: AI code review
      agent: claude-opus-4.6
      prompts:
        - "Check for security vulnerabilities"
        - "Review error handling"
        - "Check performance implications"
        - "Verify test coverage"

    - name: Style check
      tool: pylint
      threshold: 8.0/10

  actions:
    on_issues_found:
      - comment_on_pr
      - request_changes
      - notify_author

    on_pass:
      - approve_pr
      - add_label: "ready-to-merge"
```

### Code Model Comparison (GAP-CODE-MODEL-009)

| Model | Strengths | Weaknesses | Best For |
|-------|-----------|------------|----------|
| **Claude Opus 4.6** | Complex reasoning, full-stack | Expensive, slower | Architecture, debugging |
| **Claude Sonnet 4.5** | Balanced, fast | Less reasoning depth | General coding |
| **GPT-4 Turbo** | Broad knowledge | Weaker at complex logic | Documentation |
| **Codestral** | Code-specialized | Limited reasoning | Code completion |
| **DeepSeek Coder V2** | Open source, fast | Less capable | Cost-sensitive tasks |
| **Gemini 1.5 Pro** | Long context (2M tokens) | Inconsistent quality | Large codebases |

### Computer Use Security (GAP-COMPUTER-004)

```python
# Security best practices for computer use API
class ComputerUseSecurity:
    def __init__(self):
        self.allowed_actions = set()
        self.blocked_patterns = []

    def validate_action(self, action):
        """Validate computer use action."""

        # 1. Allowlist approach
        if action.type not in self.allowed_actions:
            raise SecurityError(f"Action not allowed: {action.type}")

        # 2. Block dangerous patterns
        for pattern in self.blocked_patterns:
            if re.match(pattern, action.command):
                raise SecurityError(f"Blocked pattern: {pattern}")

        # 3. Sandbox validation
        if action.type == "run_command":
            if not self.is_sandboxed(action.command):
                raise SecurityError("Command must run in sandbox")

        # 4. Rate limiting
        if self.action_rate_exceeded():
            raise RateLimitError("Too many actions")

        return True

# Secure configuration
security = ComputerUseSecurity()
security.allowed_actions = {"click", "type", "screenshot"}
security.blocked_patterns = [
    r"rm -rf /",  # Destructive
    r"curl.*\| bash",  # Remote code execution
    r"nc .*-e",  # Reverse shell
]
```

### Agent Success Case Studies (GAP-CASE-001)

**Case Study 1: Automated Migration (Success)**

```yaml
project: Migrate Flask app to FastAPI
duration: 4 hours (estimated 40 hours manual)
approach:
  - Phase 1: Analysis (Claude Opus) — 30 min
  - Phase 2: Route conversion (3x Sonnet subagents, parallel) — 1 hour
  - Phase 3: Test generation (Sonnet) — 1 hour
  - Phase 4: Integration (Opus) — 1.5 hours

results:
  - 95% automated
  - All tests passing
  - 90% code coverage
  - Zero breaking changes

key_success_factors:
  - Comprehensive test suite before migration
  - Parallel subagent approach
  - Iterative validation
  - Human approval for breaking changes
```

**Case Study 2: Security Audit (Success)**

```yaml
project: Security audit of 50K LOC codebase
duration: 2 hours (vs 2 weeks manual)
approach:
  - Static analysis (Semgrep + AI review)
  - Dependency scanning (Snyk)
  - AI-powered threat modeling (Claude Opus)
  - Manual validation of findings

findings:
  - 23 vulnerabilities detected
  - 5 critical (SQL injection, XSS)
  - 100% verified (no false positives)

outcome:
  - All issues patched within 24 hours
  - 95% automated fix generation
  - Comprehensive security report generated
```

### Agent Failure Case Studies (GAP-CASE-002)

**Case Study 1: Over-refactoring (Failure)**

```yaml
project: "Clean up codebase"
approach: Autonomous agent with "improve code quality" goal
duration: 8 hours

failure_mode:
  - Agent refactored entire codebase without approval
  - Changed 200+ files
  - Broke 40% of tests
  - Introduced subtle bugs

root_cause:
  - Unclear success criteria
  - No approval gates
  - Too much autonomy

lessons_learned:
  - Define clear scope before autonomous execution
  - Require approval for changes >10 files
  - Set test coverage as exit criteria
  - Incremental refactoring > big bang
```

**Case Study 2: Hallucinated Dependencies (Failure)**

```yaml
project: Add authentication to API
approach: Claude Code autonomous implementation

failure_mode:
  - Agent hallucinated npm package "auth-magic-v2"
  - Added non-existent dependency to package.json
  - Generated code using fake API
  - Build failed

root_cause:
  - Agent not connected to package registry
  - No verification of package existence

lessons_learned:
  - Verify external dependencies before using
  - Use tools to check package registry
  - Add pre-commit hook: validate dependencies
  - Test in isolated environment first
```
# Content to Add to modules/17-coding-agents.md

---

## 9. No-Code Agent Platforms (GAP-NOCODE-001)

**Purpose:** Build and deploy agents without writing code, using visual interfaces.

### 9.1 Platform Comparison

| Platform | Type | Target User | Strengths | Limitations |
|----------|------|-------------|-----------|-------------|
| **Zapier Central** | Workflow automation | Non-technical | Easy integrations, 6000+ apps | Limited AI capabilities |
| **Make (Integromat)** | Visual automation | Power users | Complex logic, visual flow | Learning curve |
| **n8n** | Open-source automation | Developers | Self-hosted, extensible | Requires hosting |
| **Flowise** | LLM app builder | Non-technical | Drag-and-drop LLM chains | Limited customization |
| **LangFlow** | Visual LangChain | Developers | Full LangChain support | Still requires coding for complex logic |
| **Relevance AI** | Agent platform | Business users | Pre-built agents, multi-agent | Expensive |
| **Voiceflow** | Conversational AI | Designers | Voice + chat, visual design | Conversation-focused |
| **Bubble** | Full-stack no-code | Entrepreneurs | Complete app builder | Not AI-native |

### 9.2 Use Case Mapping

**When to Use No-Code Platforms:**

| Use Case | Recommended Platform | Why |
|----------|---------------------|-----|
| **Simple automation** | Zapier Central | Easiest, fastest setup |
| **Complex workflows** | Make | Advanced logic, branching |
| **RAG chatbot** | Flowise | Drag-and-drop, no coding |
| **Custom agent logic** | LangFlow | Visual + code when needed |
| **Self-hosted** | n8n | Data privacy, control |
| **Business process** | Relevance AI | Pre-built templates |
| **Voice assistant** | Voiceflow | Voice/chat design tools |

### 9.3 Example: Flowise for RAG Agent

**Flowise Overview:**
- Visual builder for LLM applications
- Drag-and-drop nodes (LLMs, vector stores, tools)
- No coding required for basic RAG
- Export to code when needed

**Building a RAG Agent in Flowise (No Code):**

1. **Add Document Loader Node**
   - Type: Directory Loader
   - Path: `/docs`
   - File types: `.md`, `.txt`, `.pdf`

2. **Add Text Splitter Node**
   - Type: Recursive Character Text Splitter
   - Chunk size: 1000
   - Chunk overlap: 200

3. **Add Embeddings Node**
   - Type: OpenAI Embeddings
   - Model: `text-embedding-3-small`

4. **Add Vector Store Node**
   - Type: Pinecone / Qdrant / Chroma
   - Connect to embeddings

5. **Add LLM Node**
   - Type: ChatAnthropic
   - Model: `claude-opus-4.6`

6. **Add Retrieval QA Chain Node**
   - Connect: Vector Store → Retrieval QA
   - Connect: LLM → Retrieval QA

7. **Deploy as API**
   - Click "Deploy"
   - Get API endpoint

**Result:** Fully functional RAG agent with zero code.

### 9.4 Example: LangFlow for Multi-Agent System

**LangFlow Features:**
- Visual LangChain builder
- Code export to Python
- Custom components (write Python when needed)

**Building Multi-Agent System in LangFlow:**

1. **Create Agent 1: Code Generator**
   - Node: OpenAI Functions Agent
   - Tools: Python REPL
   - LLM: `gpt-4`

2. **Create Agent 2: Code Reviewer**
   - Node: OpenAI Functions Agent
   - Tools: Custom Code Review Tool
   - LLM: `claude-opus-4.6`

3. **Create Orchestrator**
   - Node: Sequential Chain
   - Flow: Input → Code Gen → Code Review → Output

4. **Add Conditional Logic**
   - Node: Router Chain
   - Condition: If review score < 7 → Retry Code Gen

5. **Export to Code**
   - Click "Export"
   - Get Python script
   - Customize further if needed

### 9.5 Limitations of No-Code Platforms

**When No-Code is NOT Sufficient:**

| Requirement | Why No-Code Fails | Solution |
|-------------|-------------------|----------|
| **Complex logic** | Visual gets messy | Hybrid: Export + code |
| **Performance** | No optimization | Write custom code |
| **Security** | No custom guardrails | Code-based agents |
| **Integration** | Platform limitations | API development |
| **Scale** | Platform rate limits | Self-hosted / custom |

**Recommendation:**

- **Prototype in no-code** (Flowise, LangFlow)
- **Validate use case** (test with users)
- **Export to code** when:
  - Logic becomes complex (>10 nodes)
  - Performance matters
  - Custom security needed
  - Scale beyond platform limits

### 9.6 Hybrid Approach: No-Code + Code

**Best Practice:** Start no-code, graduate to code when needed.

**Example Workflow:**

```
PHASE 1: PROTOTYPE (No-Code)
├─► Build in Flowise/LangFlow (1-2 days)
├─► Test with 10 users
└─► Validate use case

PHASE 2: ENHANCE (Hybrid)
├─► Export to Python
├─► Add custom logic (5-10% code)
├─► Keep visual for 90% of flow
└─► Test with 50 users

PHASE 3: PRODUCTION (Code)
├─► Rewrite in pure code (if needed)
├─► Optimize performance
├─► Add security, monitoring
└─► Scale to production
```

### 9.7 Quick Start: Flowise RAG in 5 Minutes

```bash
# 1. Install Flowise
npm install -g flowise

# 2. Start Flowise
npx flowise start

# 3. Open browser
# http://localhost:3000

# 4. Build RAG agent (drag-and-drop):
#    - Document Loader
#    - Text Splitter
#    - OpenAI Embeddings
#    - Pinecone Vector Store
#    - ChatAnthropic
#    - Retrieval QA Chain

# 5. Deploy as API
# Click "Deploy" → Get API endpoint

# 6. Test
curl -X POST http://localhost:3000/api/v1/prediction/<chatflow-id> \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'
```

### 9.8 No-Code Platform Selection Criteria

| Criterion | Flowise | LangFlow | n8n | Zapier |
|-----------|---------|----------|-----|--------|
| **Ease of use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **AI capabilities** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Customization** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Self-hosting** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| **Cost** | Free/OSS | Free/OSS | Free/OSS | Paid |
| **Learning curve** | Low | Medium | Medium | Low |

**Recommendation:**
- **Beginners:** Flowise (easiest for AI apps)
- **Developers:** LangFlow (code export, full control)
- **Enterprise:** n8n (self-hosted, secure)
- **Non-AI automation:** Zapier (integrations)

---

**Gap Resolved:** GAP-NOCODE-001
