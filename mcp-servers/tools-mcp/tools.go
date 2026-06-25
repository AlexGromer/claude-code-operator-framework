package main

import (
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func registerTools(s *server.MCPServer) {
	// Group 1: Criteria Freeze (4 tools)
	s.AddTool(mcp.NewTool("criteria_freeze",
		mcp.WithDescription("Freeze acceptance criteria for current task. Once frozen, criteria cannot be changed to match output — iterate implementation instead."),
		mcp.WithString("goal", mcp.Required(), mcp.Description("Task goal description")),
		mcp.WithString("result", mcp.Required(), mcp.Description("Expected result description")),
		mcp.WithString("criteria", mcp.Required(), mcp.Description("Comma-separated acceptance criteria")),
	), handleCriteriaFreeze)

	s.AddTool(mcp.NewTool("criteria_unfreeze",
		mcp.WithDescription("Remove criteria freeze, allowing criteria to be redefined"),
	), handleCriteriaUnfreeze)

	s.AddTool(mcp.NewTool("criteria_check",
		mcp.WithDescription("Check if criteria are currently frozen. Auto-expires after 24h TTL."),
	), handleCriteriaCheck)

	s.AddTool(mcp.NewTool("criteria_list",
		mcp.WithDescription("List current frozen criteria details"),
	), handleCriteriaList)

	// Group 2: Session Management (5 tools)
	s.AddTool(mcp.NewTool("session_start",
		mcp.WithDescription("Create session directory structure (scratchpad/, research/, artifacts/)"),
		mcp.WithString("session_id", mcp.Description("Session ID (auto-detected if not provided)")),
	), handleSessionStart)

	s.AddTool(mcp.NewTool("session_end",
		mcp.WithDescription("Mark session as ended by writing .ended marker with timestamp"),
		mcp.WithString("session_id", mcp.Description("Session ID (auto-detected if not provided)")),
	), handleSessionEnd)

	s.AddTool(mcp.NewTool("session_status",
		mcp.WithDescription("Show session info: age, size, file count, directory structure"),
		mcp.WithString("session_id", mcp.Description("Session ID (auto-detected if not provided)")),
	), handleSessionStatus)

	s.AddTool(mcp.NewTool("session_list",
		mcp.WithDescription("List all sessions with age, size, file count, and ended status"),
	), handleSessionList)

	s.AddTool(mcp.NewTool("session_cleanup",
		mcp.WithDescription("Remove sessions older than N days (default: 7)"),
		mcp.WithString("days", mcp.Description("Remove sessions older than N days (default: 7)")),
	), handleSessionCleanup)

	// Group 3: Usage Statistics (4 tools)
	s.AddTool(mcp.NewTool("usage_record",
		mcp.WithDescription("Write a usage event to usage-log.jsonl"),
		mcp.WithString("tool_name", mcp.Required(), mcp.Description("Name of the tool used")),
		mcp.WithString("model", mcp.Description("Model name (e.g., claude-opus-4-6)")),
		mcp.WithString("cost", mcp.Description("Cost in USD (e.g., 0.05)")),
		mcp.WithString("tokens", mcp.Description("Token count")),
		mcp.WithString("project", mcp.Description("Project name or path")),
	), handleUsageRecord)

	s.AddTool(mcp.NewTool("usage_report",
		mcp.WithDescription("Summary report of usage data: costs, tokens, by project and model"),
		mcp.WithString("period", mcp.Description("Time period: all, today, week, month (default: all)")),
		mcp.WithString("project", mcp.Description("Filter by project name")),
		mcp.WithString("session", mcp.Description("Filter by session ID")),
	), handleUsageReport)

	s.AddTool(mcp.NewTool("usage_top_tools",
		mcp.WithDescription("Most used tools ranked by call count"),
		mcp.WithString("period", mcp.Description("Time period: all, today, week, month (default: all)")),
		mcp.WithString("limit", mcp.Description("Number of top tools to return (default: 10)")),
	), handleUsageTopTools)

	s.AddTool(mcp.NewTool("usage_trends",
		mcp.WithDescription("Usage trends over time grouped by day or week"),
		mcp.WithString("period", mcp.Description("Time period: week, month (default: week)")),
		mcp.WithString("group_by", mcp.Description("Group by: day, week (default: day)")),
	), handleUsageTrends)

	// Group 4: Scope Tracking (2 tools)
	s.AddTool(mcp.NewTool("scope_track",
		mcp.WithDescription("Track a file modification for scope escalation detection. Returns warning when thresholds are reached (files>=4 → Plan Mode, files>=6 + domains>=2 → TeamCreate)."),
		mcp.WithString("file_path", mcp.Required(), mcp.Description("Path of the modified file")),
		mcp.WithString("session_id", mcp.Description("Session ID (auto-detected if not provided)")),
	), handleScopeTrack)

	s.AddTool(mcp.NewTool("scope_status",
		mcp.WithDescription("Show current scope tracking state: files modified, domains touched, live score, tier."),
		mcp.WithString("session_id", mcp.Description("Session ID (auto-detected if not provided)")),
	), handleScopeStatus)
}
