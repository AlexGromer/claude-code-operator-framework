package main

import (
	"testing"

	"github.com/mark3labs/mcp-go/server"
)

// TestToolsRegistration verifies all 13 tools are registered correctly.
func TestToolsRegistration(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	// Get the list of tools (returns map[string]*ServerTool)
	toolsMap := s.ListTools()

	if len(toolsMap) != 13 {
		t.Errorf("tool count: got %d, want 13", len(toolsMap))
	}

	// Verify expected tool names
	expectedTools := []string{
		"criteria_freeze",
		"criteria_unfreeze",
		"criteria_check",
		"criteria_list",
		"session_start",
		"session_end",
		"session_status",
		"session_list",
		"session_cleanup",
		"usage_record",
		"usage_report",
		"usage_top_tools",
		"usage_trends",
	}

	for _, expectedName := range expectedTools {
		if _, ok := toolsMap[expectedName]; !ok {
			t.Errorf("missing tool: %s", expectedName)
		}
	}
}

// TestCriteriaFreezeToolProperties verifies criteria_freeze tool has correct properties.
func TestCriteriaFreezeToolProperties(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	freezeTool := s.GetTool("criteria_freeze")
	if freezeTool == nil {
		t.Fatal("criteria_freeze tool not found")
	}

	// Verify tool has spec
	if freezeTool.Tool.Description == "" {
		t.Error("criteria_freeze should have description")
	}

	if freezeTool.Tool.Name != "criteria_freeze" {
		t.Errorf("tool name: got %s, want criteria_freeze", freezeTool.Tool.Name)
	}
}

// TestSessionStartToolProperties verifies session_start tool has correct properties.
func TestSessionStartToolProperties(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	sessionStartTool := s.GetTool("session_start")
	if sessionStartTool == nil {
		t.Fatal("session_start tool not found")
	}

	if sessionStartTool.Tool.Description == "" {
		t.Error("session_start should have description")
	}

	if sessionStartTool.Tool.Name != "session_start" {
		t.Errorf("tool name: got %s, want session_start", sessionStartTool.Tool.Name)
	}
}

// TestUsageRecordToolProperties verifies usage_record tool has correct properties.
func TestUsageRecordToolProperties(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	usageRecordTool := s.GetTool("usage_record")
	if usageRecordTool == nil {
		t.Fatal("usage_record tool not found")
	}

	if usageRecordTool.Tool.Description == "" {
		t.Error("usage_record should have description")
	}

	if usageRecordTool.Tool.Name != "usage_record" {
		t.Errorf("tool name: got %s, want usage_record", usageRecordTool.Tool.Name)
	}
}

// TestServerInfo verifies the ServerInfo function returns correct metadata.
func TestServerInfo(t *testing.T) {
	info := ServerInfo()

	if info.Name != "tools-mcp" {
		t.Errorf("name: got %q, want tools-mcp", info.Name)
	}

	if info.Version != "1.0.0" {
		t.Errorf("version: got %q, want 1.0.0", info.Version)
	}
}

// TestToolsGrouping verifies the 13 tools are correctly grouped into 3 categories.
func TestToolsGrouping(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	toolsMap := s.ListTools()

	// Count by group
	criteriaTools := 0
	sessionTools := 0
	usageTools := 0

	for toolName := range toolsMap {
		switch toolName {
		case "criteria_freeze", "criteria_unfreeze", "criteria_check", "criteria_list":
			criteriaTools++
		case "session_start", "session_end", "session_status", "session_list", "session_cleanup":
			sessionTools++
		case "usage_record", "usage_report", "usage_top_tools", "usage_trends":
			usageTools++
		default:
			t.Errorf("unexpected tool: %s", toolName)
		}
	}

	if criteriaTools != 4 {
		t.Errorf("criteria tools: got %d, want 4", criteriaTools)
	}
	if sessionTools != 5 {
		t.Errorf("session tools: got %d, want 5", sessionTools)
	}
	if usageTools != 4 {
		t.Errorf("usage tools: got %d, want 4", usageTools)
	}
}

// TestAllToolsHaveDescriptions verifies every tool has a description.
func TestAllToolsHaveDescriptions(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	toolsMap := s.ListTools()

	for toolName, tool := range toolsMap {
		if tool.Tool.Description == "" {
			t.Errorf("tool %s missing description", toolName)
		}
	}
}

// TestSessionCleanupToolExists verifies session_cleanup tool exists.
func TestSessionCleanupToolExists(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	cleanupTool := s.GetTool("session_cleanup")
	if cleanupTool == nil {
		t.Fatal("session_cleanup tool not found")
	}

	if cleanupTool.Tool.Description == "" {
		t.Error("session_cleanup should have description")
	}
}

// TestUsageReportToolExists verifies usage_report tool exists.
func TestUsageReportToolExists(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	reportTool := s.GetTool("usage_report")
	if reportTool == nil {
		t.Fatal("usage_report tool not found")
	}

	if reportTool.Tool.Description == "" {
		t.Error("usage_report should have description")
	}
}

// TestUsageTopToolsToolExists verifies usage_top_tools tool exists.
func TestUsageTopToolsToolExists(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	topToolsTool := s.GetTool("usage_top_tools")
	if topToolsTool == nil {
		t.Fatal("usage_top_tools tool not found")
	}

	if topToolsTool.Tool.Description == "" {
		t.Error("usage_top_tools should have description")
	}
}

// TestUsageTrendsToolExists verifies usage_trends tool exists.
func TestUsageTrendsToolExists(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	trendsTool := s.GetTool("usage_trends")
	if trendsTool == nil {
		t.Fatal("usage_trends tool not found")
	}

	if trendsTool.Tool.Description == "" {
		t.Error("usage_trends should have description")
	}
}

// TestCriteriaToolsExist verifies all 4 criteria tools exist.
func TestCriteriaToolsExist(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	criteriaToolNames := []string{
		"criteria_freeze",
		"criteria_unfreeze",
		"criteria_check",
		"criteria_list",
	}

	for _, name := range criteriaToolNames {
		tool := s.GetTool(name)
		if tool == nil {
			t.Errorf("%s tool not found", name)
		}
	}
}

// TestSessionToolsExist verifies all 5 session tools exist.
func TestSessionToolsExist(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	sessionToolNames := []string{
		"session_start",
		"session_end",
		"session_status",
		"session_list",
		"session_cleanup",
	}

	for _, name := range sessionToolNames {
		tool := s.GetTool(name)
		if tool == nil {
			t.Errorf("%s tool not found", name)
		}
	}
}

// TestUsageToolsExist verifies all 4 usage tools exist.
func TestUsageToolsExist(t *testing.T) {
	s := server.NewMCPServer("tools-mcp", "1.0.0", server.WithToolCapabilities(false))
	registerTools(s)

	usageToolNames := []string{
		"usage_record",
		"usage_report",
		"usage_top_tools",
		"usage_trends",
	}

	for _, name := range usageToolNames {
		tool := s.GetTool(name)
		if tool == nil {
			t.Errorf("%s tool not found", name)
		}
	}
}
