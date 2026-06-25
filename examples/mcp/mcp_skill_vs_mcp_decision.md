# Few-Shot Example: Skill vs MCP Decision Matrix

## Task
Пользователь: "Когда создавать Skill, а когда использовать MCP server? У меня есть повторяющаяся задача автоматизации деплоя."

## Solution

### Decision Framework

**Quick Answer:**
- **Skill:** Workflow orchestration (Claude Code logic + prompts)
- **MCP Server:** External data/tool access (API calls, filesystem, database)

---

## Part 1: Understanding the Difference

### Skill (Agent Workflow)

**What it is:**
- Structured prompt sequence
- Combines multiple Claude Code tools
- Orchestrates complex multi-step workflows
- Pure prompt engineering (no external code)

**Format:**
```markdown
---
name: deploy
description: Deployment workflow with checks
trigger: "/deploy"
---

# Deployment Workflow

## Phase 1: Pre-flight checks
1. Run tests
2. Check secrets
3. Verify environment

## Phase 2: Deploy
... (structured prompts)
```

**Execution:**
- Runs inside Claude Code agent
- Uses existing tools (Bash, Read, Write, mcp__*)
- No external process
- Prompt-driven logic

### MCP Server (External Tool)

**What it is:**
- External process (Node.js, Python, Go binary)
- Provides new tools/resources to Claude Code
- Handles authentication, API calls, data access
- Actual code execution outside Claude

**Format:**
```json
{
  "mcpServers": {
    "deploy-automation": {
      "command": "node",
      "args": ["~/.claude/mcp-servers/deploy-server.js"]
    }
  }
}
```

**Execution:**
- Separate process
- Communicates via JSON-RPC
- Provides tools like `mcp__deploy__trigger`, `mcp__deploy__status`
- Code-driven logic

---

## Part 2: Decision Matrix

| Criterion | Use Skill | Use MCP Server |
|-----------|-----------|----------------|
| **Logic Type** | Workflow orchestration, decision trees | Data access, API calls, stateful operations |
| **Tools Needed** | Existing tools sufficient (Bash, Read, etc.) | Need custom tool not available |
| **Authentication** | Can use env vars / `pass` via Bash | Needs OAuth 2.1, complex auth flows |
| **State Management** | Stateless or file-based | Needs database, session management |
| **Performance** | I/O bound (file ops, commands) | CPU intensive, long-running tasks |
| **Reusability** | Claude Code only | Can be used by multiple AI agents |
| **Complexity** | <100 lines of prompts | >100 lines of code |
| **Maintenance** | Prompt updates (easy) | Code updates (requires dev work) |
| **Examples** | `/commit`, `/deploy`, `/security-audit` | `github`, `postgres`, `filesystem` |

---

## Part 3: Your Use Case — Deployment Automation

### Scenario Analysis

**Deployment workflow involves:**
1. ✅ Pre-flight checks (tests, secrets scan)
2. ✅ Environment selection (dev/staging/prod)
3. ✅ Kubernetes apply
4. ✅ Rollout monitoring
5. ✅ Rollback if failed
6. ✅ Slack notification

### Decision: **Use Skill** (not MCP)

**Reasoning:**

#### Why NOT MCP Server:
- ❌ No external data source needed (all data in Git)
- ❌ No custom authentication (kubectl uses kubeconfig)
- ❌ No stateful logic (deployment status via kubectl)
- ❌ No CPU-intensive operations
- ❌ Doesn't need to be shared with other agents

#### Why Skill:
- ✅ Orchestrates existing tools (Bash, Read for configs, kubectl)
- ✅ Decision logic (which environment? rollback?) is prompt-driven
- ✅ Uses existing MCP servers (mcp__github for notifications)
- ✅ Easy to modify workflow steps
- ✅ No additional process overhead

---

## Part 4: Implementation

### Option A: Skill (Recommended)

**File:** `~/.claude/skills/deploy.md`

```markdown
---
name: deploy
description: Deployment workflow with pre-flight checks and rollback
trigger: "/deploy"
args: [environment, app_name]
examples:
  - "/deploy production api-service"
  - "/deploy staging web-frontend"
---

# Deployment Workflow

## Input Validation

Required arguments:
- `environment`: dev | staging | production
- `app_name`: Name of the application to deploy

## Phase 1: Pre-Flight Checks

### 1.1 Run Tests
```bash
cd /path/to/app
pytest tests/ --cov --cov-report=term
```

Exit if tests fail.

### 1.2 Security Scan
```bash
trivy config ./k8s/ --severity HIGH,CRITICAL
gitleaks detect --no-git
```

Exit if vulnerabilities found.

### 1.3 Verify Environment
- Check kubectl context: `kubectl config current-context`
- Verify namespace exists: `kubectl get namespace ${app_name}`
- Check resource quotas: `kubectl describe quota -n ${app_name}`

## Phase 2: Deployment

### 2.1 Apply Kubernetes Manifests
```bash
kubectl apply -f k8s/${environment}/ -n ${app_name}
```

### 2.2 Monitor Rollout
```bash
kubectl rollout status deployment/${app_name} -n ${app_name} --timeout=5m
```

If rollout fails → proceed to Phase 3 (Rollback).

## Phase 3: Rollback (if needed)

```bash
kubectl rollout undo deployment/${app_name} -n ${app_name}
kubectl rollout status deployment/${app_name} -n ${app_name}
```

## Phase 4: Verification

### 4.1 Check Pods
```bash
kubectl get pods -n ${app_name} -l app=${app_name}
```

All pods should be Running.

### 4.2 Health Check
```bash
kubectl exec -n ${app_name} deploy/${app_name} -- curl -f http://localhost:8080/health
```

## Phase 5: Notification

Send notification using GitHub MCP (create deployment issue):

```
mcp__github__create_issue:
  owner: my-org
  repo: deployments
  title: "Deployed ${app_name} to ${environment}"
  body: |
    ## Deployment Summary
    - App: ${app_name}
    - Environment: ${environment}
    - Status: SUCCESS
    - Time: $(date -Iseconds)

    ## Changes
    $(git log --oneline -5)
```

## Success Criteria

- ✅ All pre-flight checks passed
- ✅ Deployment rollout successful
- ✅ Health check returns 200 OK
- ✅ Notification sent
```

**Usage:**
```bash
# In Claude Code session
/deploy production api-service
```

**What Claude Code does:**
1. Loads `~/.claude/skills/deploy.md`
2. Parses arguments (`production`, `api-service`)
3. Executes each phase using existing tools:
   - `Bash` for kubectl commands
   - `Read` for reading k8s manifests
   - `mcp__github__create_issue` for notification
4. Makes decisions (rollback if failed)
5. Returns structured output

**Cost:** ~$0.01 per deployment (sonnet model)

---

### Option B: MCP Server (Overkill for this case)

**File:** `~/.claude/mcp-servers/deploy-server.js`

```javascript
#!/usr/bin/env node
// MCP Server for deployment automation
// WARNING: This is OVERKILL for simple deployment workflows!

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

class DeployServer {
  constructor() {
    this.server = new Server({
      name: 'deploy-automation',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {}
      }
    });

    this.setupToolHandlers();
  }

  setupToolHandlers() {
    // Tool 1: Deploy application
    this.server.setRequestHandler('tools/call', async (request) => {
      if (request.params.name === 'mcp__deploy__trigger') {
        const { environment, app_name } = request.params.arguments;

        try {
          // Pre-flight checks
          await execAsync(`pytest tests/ --cov`);
          await execAsync(`trivy config ./k8s/`);

          // Deploy
          await execAsync(`kubectl apply -f k8s/${environment}/ -n ${app_name}`);
          await execAsync(`kubectl rollout status deployment/${app_name} -n ${app_name} --timeout=5m`);

          return {
            content: [{ type: 'text', text: `Deployment successful: ${app_name} to ${environment}` }]
          };
        } catch (error) {
          // Rollback
          await execAsync(`kubectl rollout undo deployment/${app_name} -n ${app_name}`);
          return {
            content: [{ type: 'text', text: `Deployment failed, rolled back: ${error.message}` }],
            isError: true
          };
        }
      }
    });

    // Tool 2: Get deployment status
    this.server.setRequestHandler('tools/list', async () => {
      return {
        tools: [
          {
            name: 'mcp__deploy__trigger',
            description: 'Deploy application to Kubernetes',
            inputSchema: {
              type: 'object',
              properties: {
                environment: { type: 'string', enum: ['dev', 'staging', 'production'] },
                app_name: { type: 'string' }
              },
              required: ['environment', 'app_name']
            }
          },
          {
            name: 'mcp__deploy__status',
            description: 'Get deployment status',
            inputSchema: {
              type: 'object',
              properties: {
                app_name: { type: 'string' }
              },
              required: ['app_name']
            }
          }
        ]
      };
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

const server = new DeployServer();
server.run().catch(console.error);
```

**Configuration:** `~/.claude/settings.json`
```json
{
  "mcpServers": {
    "deploy": {
      "command": "node",
      "args": ["~/.claude/mcp-servers/deploy-server.js"]
    }
  }
}
```

**Usage:**
```bash
# In Claude Code session
"Deploy api-service to production using the deploy MCP server"
```

**Problems with MCP approach:**
- ❌ **Overhead:** Separate process, JSON-RPC communication
- ❌ **Maintenance:** Requires Node.js code updates, testing
- ❌ **Debugging:** Harder to debug than prompt-based Skill
- ❌ **Flexibility:** Changing workflow requires code changes
- ❌ **Overkill:** All logic can be done with existing tools

**Cost:** ~$0.01 per deployment + MCP server overhead

---

## Part 5: When to Use MCP Server

### Valid Use Cases for MCP

#### Use Case 1: Database Access

**Scenario:** Need to query PostgreSQL database for monitoring data.

**Why MCP:**
- ✅ Requires persistent connection pooling
- ✅ Needs authentication (username/password)
- ✅ Complex queries with prepared statements
- ✅ Transaction management

**Implementation:**
```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/db"]
    }
  }
}
```

#### Use Case 2: Custom API with OAuth

**Scenario:** Integrate with Jira API (OAuth 2.0).

**Why MCP:**
- ✅ OAuth 2.1 PKCE flow required
- ✅ Token refresh logic
- ✅ API rate limiting
- ✅ Webhook handling

**Implementation:**
```javascript
// MCP server handles OAuth flow, token refresh, API calls
class JiraMCPServer {
  async authenticate() { /* OAuth PKCE flow */ }
  async refreshToken() { /* Token refresh */ }
  async createIssue(params) { /* API call with rate limiting */ }
}
```

#### Use Case 3: Real-Time Data Stream

**Scenario:** Monitor Kubernetes events in real-time.

**Why MCP:**
- ✅ WebSocket connection to K8s API
- ✅ Event streaming
- ✅ State management (track seen events)

**Implementation:**
```javascript
// MCP server maintains WebSocket connection
class K8sEventsMCPServer {
  async watchEvents(namespace) {
    const stream = k8sClient.watch('/api/v1/events');
    stream.on('data', event => this.handleEvent(event));
  }
}
```

---

## Part 6: Decision Tree

```
┌─────────────────────────────────────────────────────────┐
│  Do you need to ACCESS EXTERNAL DATA not in filesystem? │
│  (Database, API, cloud service)                         │
└────────────┬──────────────────────────────┬─────────────┘
             │ YES                          │ NO
             ▼                              ▼
┌─────────────────────────┐   ┌────────────────────────────┐
│  Does it require OAUTH  │   │  Can existing tools handle  │
│  or complex auth?       │   │  it? (Bash, mcp__github__)  │
└────────┬─────────┬──────┘   └────────┬─────────┬─────────┘
         │ YES     │ NO                │ YES     │ NO
         ▼         ▼                   ▼         ▼
    ┌────────┐ ┌───────────┐     ┌────────┐ ┌─────────┐
    │  MCP   │ │  Skill +  │     │ Skill  │ │  MCP    │
    │ Server │ │  Bash/API │     │        │ │ Server  │
    └────────┘ └───────────┘     └────────┘ └─────────┘
```

---

## Summary Table

| Feature | Skill | MCP Server |
|---------|-------|------------|
| **Development Time** | 30 min - 2 hours | 4 hours - 2 days |
| **Maintenance** | Easy (prompt updates) | Medium (code updates) |
| **Debugging** | Easy (visible in conversation) | Hard (external process logs) |
| **Performance** | Fast (no IPC overhead) | Slower (JSON-RPC overhead) |
| **Flexibility** | Very flexible (prompt changes) | Less flexible (code changes) |
| **Reusability** | Claude Code only | Multi-agent compatible |
| **Cost** | $0.001 - $0.01 per run | $0.01 - $0.05 per run + server overhead |
| **Best For** | Workflows, orchestration | External data access, complex auth |

---

## Recommendation for Your Case

**For deployment automation → Use Skill**

**Implementation:**
1. Create `~/.claude/skills/deploy.md` (as shown above)
2. Use existing tools:
   - `Bash` for kubectl, pytest, trivy
   - `Read` for reading k8s manifests
   - `mcp__github__create_issue` for notifications
3. Keep logic in prompts (easy to modify)
4. No external process overhead

**When to migrate to MCP:**
- If you need deployment history database
- If you integrate with external deployment platform (Spinnaker, ArgoCD API)
- If you need OAuth with deployment service
- If you want to share deployment tools across multiple AI agents

---

**Authoritative Sources:**
- MCP Specification: https://modelcontextprotocol.io/introduction
- Claude Code Skills: https://github.com/anthropics/agent-skills
- Skills Marketplace: https://agentskills.io/
- MCP Servers: https://github.com/modelcontextprotocol/servers
