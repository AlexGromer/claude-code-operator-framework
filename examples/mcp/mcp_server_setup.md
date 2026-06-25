# Few-Shot Example: MCP Server Setup (GitHub)

## Task
Пользователь: "Настрой MCP сервер для работы с GitHub, чтобы Claude Code мог создавать issues и PRs."

## Solution

### Step 1: Install MCP Server for GitHub

**Option A: From npm (recommended)**
```bash
# Install globally
npm install -g @modelcontextprotocol/server-github

# Verify installation
which mcp-server-github
# Expected: /usr/local/bin/mcp-server-github
```

**Option B: From source**
```bash
git clone https://github.com/modelcontextprotocol/servers.git
cd servers/src/github
npm install
npm run build
npm link
```

### Step 2: Create GitHub Personal Access Token

**Required scopes:**
- ✅ `repo` (Full control of private repositories)
- ✅ `workflow` (Update GitHub Action workflows) — if managing Actions
- ✅ `read:org` (Read org membership) — if using org repositories

**Create token:**
1. Navigate to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: `claude-code-mcp-github`
4. Select scopes: `repo`, `workflow`, `read:org`
5. Click "Generate token"
6. **Copy token immediately** (shown once)

**Store token securely:**
```bash
# Option 1: Environment variable (for testing)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Option 2: Password manager (recommended)
pass insert github/claude-code-mcp-token
# Enter token when prompted

# Option 3: .env file (DO NOT commit)
echo "GITHUB_TOKEN=ghp_xxxxx" >> ~/.env
chmod 600 ~/.env
```

### Step 3: Configure Claude Code to Use MCP Server

**Edit `~/.claude/settings.json`:**
```json
{
  "mcpServers": {
    "github": {
      "command": "mcp-server-github",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**If using password manager (pass):**
```json
{
  "mcpServers": {
    "github": {
      "command": "bash",
      "args": [
        "-c",
        "GITHUB_TOKEN=$(pass show github/claude-code-mcp-token) mcp-server-github"
      ]
    }
  }
}
```

**Full settings.json example with existing config:**
```json
{
  "allowedTools": [
    "Bash",
    "Edit",
    "Grep",
    "Glob",
    "Read",
    "Write",
    "WebSearch",
    "WebFetch"
  ],
  "mcpServers": {
    "github": {
      "command": "mcp-server-github",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"],
      "env": {}
    }
  },
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/session_health_check.py",
            "timeout": 3000
          }
        ]
      }
    ]
  }
}
```

### Step 4: Verify MCP Server Connection

**Test connection:**
```bash
# Start Claude Code session
claude

# In Claude Code, ask:
# "List available tools from GitHub MCP server"
```

**Expected tools:**
- `mcp__github__create_issue`
- `mcp__github__create_pull_request`
- `mcp__github__get_file_contents`
- `mcp__github__search_repositories`
- `mcp__github__search_code`
- `mcp__github__list_issues`
- `mcp__github__create_or_update_file`
- ... (20+ tools total)

**Test tool usage:**
```bash
# In Claude Code session, ask:
# "Create a test issue in my repository test-repo with title 'Test from MCP'"
```

**Expected behavior:**
Claude Code will call `mcp__github__create_issue` with parameters:
```json
{
  "owner": "your-username",
  "repo": "test-repo",
  "title": "Test from MCP",
  "body": "This is a test issue created via MCP server"
}
```

### Step 5: Security Hardening

#### 5.1 Token Scope Minimization

**If only reading public repositories:**
```json
{
  "mcpServers": {
    "github-readonly": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN_READONLY}"
      }
    }
  }
}
```

**Create read-only token with scopes:**
- `public_repo` (Access public repositories)
- `read:user` (Read user profile)

#### 5.2 Repository Allowlist (if MCP server supports)

**Restrict to specific repositories:**
```json
{
  "mcpServers": {
    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "ALLOWED_REPOS": "user/repo1,user/repo2"
      }
    }
  }
}
```

#### 5.3 Audit Logging

**Enable audit log for MCP operations:**
```json
{
  "mcpServers": {
    "github": {
      "command": "bash",
      "args": [
        "-c",
        "GITHUB_TOKEN=$(pass show github/claude-code-mcp-token) mcp-server-github 2>> ~/.claude/logs/mcp_github.log"
      ]
    }
  }
}
```

**Log rotation:**
```bash
# Add to ~/.anacron/anacrontab
7 10 mcp_log_rotate find ~/.claude/logs/mcp_github.log -size +10M -exec gzip {} \; -exec touch ~/.claude/logs/mcp_github.log \;
```

### Step 6: Common Use Cases

#### Use Case 1: Create Issue from Claude Code

**User request:**
> "Claude, создай issue в репозитории my-project с заголовком 'Bug: Login fails' и описанием проблемы."

**Claude Code execution:**
```
✓ Using mcp__github__create_issue tool
  owner: myusername
  repo: my-project
  title: Bug: Login fails
  body:
    ## Problem
    Users cannot log in to the application.

    ## Expected Behavior
    Login form should accept valid credentials.

    ## Actual Behavior
    Error message: "Invalid credentials" even with correct password.

    ## Steps to Reproduce
    1. Navigate to /login
    2. Enter username: test@example.com
    3. Enter password: correct_password
    4. Click "Login"
    5. Observe error

    ## Environment
    - Browser: Chrome 120
    - OS: Ubuntu 22.04

✓ Issue created: https://github.com/myusername/my-project/issues/42
```

#### Use Case 2: Search Code Across Repositories

**User request:**
> "Найди все использования функции `authenticateUser` в моих репозиториях."

**Claude Code execution:**
```
✓ Using mcp__github__search_code tool
  q: authenticateUser user:myusername

Results:
1. myusername/auth-service/src/auth.js:45
   function authenticateUser(username, password) { ... }

2. myusername/api-gateway/middleware/auth.js:23
   const result = await authenticateUser(req.body.username, req.body.password);

3. myusername/admin-panel/lib/security.js:102
   import { authenticateUser } from '../auth';

Found 3 matches across 3 repositories.
```

#### Use Case 3: Create Pull Request

**User request:**
> "Создай PR в репозитории test-project из ветки feature/new-api в main с описанием изменений."

**Claude Code execution:**
```
✓ Using mcp__github__create_pull_request tool
  owner: myusername
  repo: test-project
  title: Add new API endpoints for user management
  head: feature/new-api
  base: main
  body:
    ## Summary
    - Added GET /api/users endpoint
    - Added POST /api/users endpoint
    - Added PUT /api/users/:id endpoint
    - Added DELETE /api/users/:id endpoint

    ## Changes
    - `src/api/users.js` - New API endpoints
    - `src/routes/index.js` - Route registration
    - `tests/api/users.test.js` - Test coverage

    ## Test Plan
    - ✅ Unit tests passing (42 tests)
    - ✅ Integration tests passing
    - ✅ Manual testing completed

    ## Related Issues
    Closes #123

✓ Pull request created: https://github.com/myusername/test-project/pull/45
```

### Step 7: Troubleshooting

#### Problem: "MCP server not found"

**Error:**
```
Error: Command not found: mcp-server-github
```

**Solution:**
```bash
# Check if installed globally
npm list -g @modelcontextprotocol/server-github

# If not found, install
npm install -g @modelcontextprotocol/server-github

# Verify PATH includes npm global bin
echo $PATH | grep "$(npm config get prefix)/bin"

# If not, add to ~/.bashrc or ~/.zshrc
export PATH="$(npm config get prefix)/bin:$PATH"
```

#### Problem: "Authentication failed"

**Error:**
```
Error: GitHub API error: 401 Unauthorized
```

**Solution:**
1. Verify token is valid:
   ```bash
   curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
   ```
2. Check token scopes:
   ```bash
   curl -I -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep X-OAuth-Scopes
   ```
3. Generate new token if expired

#### Problem: "Rate limit exceeded"

**Error:**
```
Error: GitHub API rate limit exceeded
```

**Solution:**
```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Output:
# {
#   "resources": {
#     "core": {
#       "limit": 5000,
#       "remaining": 0,
#       "reset": 1672531200
#     }
#   }
# }

# Wait until reset time or use different token
```

#### Problem: "Permission denied"

**Error:**
```
Error: Resource not accessible by integration
```

**Solution:**
- Add required scopes to token (repo, workflow, read:org)
- For organization repositories: ensure you have admin access
- Check repository settings → Collaborators & teams

### Step 8: Advanced Configuration

#### Multi-Account Support

**Scenario:** Work with multiple GitHub accounts (personal + work)

```json
{
  "mcpServers": {
    "github-personal": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN_PERSONAL}"
      }
    },
    "github-work": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN_WORK}",
        "GITHUB_API_URL": "https://github.company.com/api/v3"
      }
    }
  }
}
```

**Usage:**
Claude Code will automatically choose the appropriate MCP server based on repository owner.

#### Custom GitHub Enterprise

```json
{
  "mcpServers": {
    "github-enterprise": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_ENTERPRISE_TOKEN}",
        "GITHUB_API_URL": "https://github.company.com/api/v3"
      }
    }
  }
}
```

---

## Verification Checklist

After setup, verify:

- ✅ MCP server binary installed and accessible
- ✅ GitHub token created with correct scopes
- ✅ Token stored securely (not in plaintext)
- ✅ `settings.json` configured correctly
- ✅ Claude Code can list GitHub tools
- ✅ Test issue creation works
- ✅ Test repository search works
- ✅ Audit logging enabled
- ✅ Token rotation scheduled (every 90 days)

---

## Maintenance

### Token Rotation (every 90 days)

1. Generate new token with same scopes
2. Update environment variable / password manager
3. Test MCP server connection
4. Revoke old token
5. Document rotation in audit log

### MCP Server Updates

```bash
# Check for updates
npm outdated -g @modelcontextprotocol/server-github

# Update
npm update -g @modelcontextprotocol/server-github

# Restart Claude Code session to load new version
```

---

**Authoritative Sources:**
- MCP GitHub Server: https://github.com/modelcontextprotocol/servers/tree/main/src/github
- GitHub API Documentation: https://docs.github.com/en/rest
- MCP Specification: https://modelcontextprotocol.io/
- Claude Code MCP Integration: https://docs.anthropic.com/en/docs/agents/claude-code/mcp
