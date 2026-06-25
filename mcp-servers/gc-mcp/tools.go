package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func registerTools(s *server.MCPServer) {
	// gc_run
	s.AddTool(mcp.NewTool("gc_run",
		mcp.WithDescription("Execute full garbage collection across all 16 targets"),
		mcp.WithString("cwd", mcp.Description("Working directory for BACKLOG.md rotation (default: $CWD)")),
	), handleGCRun)

	// gc_dry_run
	s.AddTool(mcp.NewTool("gc_dry_run",
		mcp.WithDescription("Preview what would be cleaned without deleting"),
		mcp.WithString("cwd", mcp.Description("Working directory for BACKLOG.md rotation (default: $CWD)")),
	), handleGCDryRun)

	// gc_status
	s.AddTool(mcp.NewTool("gc_status",
		mcp.WithDescription("Show stale artifact counts per target without cleaning"),
		mcp.WithString("cwd", mcp.Description("Working directory for BACKLOG.md rotation (default: $CWD)")),
	), handleGCStatus)
}

func optStr(request mcp.CallToolRequest, key string) string {
	args := request.GetArguments()
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func resolveCwd(request mcp.CallToolRequest) string {
	if v := optStr(request, "cwd"); v != "" {
		return v
	}
	cwd, _ := os.Getwd()
	return cwd
}

func jsonResult(v any) (*mcp.CallToolResult, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("json: %v", err)), nil
	}
	return mcp.NewToolResultText(string(data)), nil
}

func handleGCRun(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	cwd := resolveCwd(request)
	results := runAllCleanups(cwd, false)
	return jsonResult(results)
}

func handleGCDryRun(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	cwd := resolveCwd(request)
	results := runAllCleanups(cwd, true)
	return jsonResult(results)
}

func handleGCStatus(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	cwd := resolveCwd(request)
	results := getStatus(cwd)
	return jsonResult(results)
}
