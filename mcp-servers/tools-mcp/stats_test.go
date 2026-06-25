package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// TestLoadRecords verifies JSONL file parsing with timestamp filtering.
func TestLoadRecords(t *testing.T) {
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "test.jsonl")

	// Write test records
	now := time.Now().UTC()
	records := []map[string]any{
		{
			"timestamp": now.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.05,
		},
		{
			"timestamp": now.Add(-2 * 24 * time.Hour).Format(time.RFC3339),
			"tool_name": "tool2",
			"cost_usd":  0.10,
		},
		{
			"timestamp": now.Add(-10 * 24 * time.Hour).Format(time.RFC3339),
			"tool_name": "tool3",
			"cost_usd":  0.15, // Should be filtered out with maxAgeDays=7
		},
	}

	for _, rec := range records {
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Load with 7 day filter
	loaded := loadRecords(logPath, 7)

	if len(loaded) != 2 {
		t.Errorf("record count: got %d, want 2 (filtered out 10-day-old)", len(loaded))
	}

	// Verify oldest is within cutoff
	if len(loaded) > 0 {
		if costStr := fmt.Sprintf("%v", loaded[0]["cost_usd"]); !strings.Contains(costStr, "0.1") && !strings.Contains(costStr, "0.05") {
			t.Errorf("costs: got %v", loaded)
		}
	}
}

// TestLoadRecordsEmpty verifies empty result when file doesn't exist.
func TestLoadRecordsEmpty(t *testing.T) {
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "nonexistent.jsonl")

	loaded := loadRecords(logPath, 7)
	if loaded != nil {
		t.Errorf("should return nil for nonexistent file, got %v", loaded)
	}
}

// TestLoadRecordsWithVariousTimestampFields verifies parsing of different timestamp field names.
func TestLoadRecordsWithVariousTimestampFields(t *testing.T) {
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "test.jsonl")

	now := time.Now().UTC()

	// Record with "ts" field instead of "timestamp"
	rec1 := map[string]any{
		"ts":        now.Format(time.RFC3339),
		"tool_name": "tool1",
	}
	data1, _ := json.Marshal(rec1)
	os.WriteFile(logPath, append(data1, '\n'), 0644)

	// Record with "created_at" field
	rec2 := map[string]any{
		"created_at": now.Format(time.RFC3339),
		"tool_name": "tool2",
	}
	data2, _ := json.Marshal(rec2)
	f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_WRONLY, 0644)
	f.Write(append(data2, '\n'))
	f.Close()

	loaded := loadRecords(logPath, 7)
	if len(loaded) != 2 {
		t.Errorf("should parse both records: got %d", len(loaded))
	}
}

// TestUsageRecord verifies writing a usage record to JSONL.
func TestUsageRecord(t *testing.T) {
	origUsageLog := usageLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	usageLog = logPath
	defer func() { usageLog = origUsageLog }()

	ctx := context.Background()
	result, err := handleUsageRecord(ctx, makeRequest(map[string]any{
		"tool_name": "test_tool",
		"model":     "claude-opus-4-6",
		"cost":      "0.05",
		"tokens":    "1000",
		"project":   "test-project",
	}))
	if err != nil {
		t.Fatalf("handleUsageRecord: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "recorded" {
		t.Errorf("status: got %v, want recorded", resp["status"])
	}

	// Verify file was written
	data, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatalf("read usage log: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 1 {
		t.Errorf("should have 1 line, got %d", len(lines))
	}

	var rec map[string]any
	if err := json.Unmarshal([]byte(lines[0]), &rec); err != nil {
		t.Fatalf("parse record: %v", err)
	}

	if toolName, ok := rec["tool_name"].(string); !ok || toolName != "test_tool" {
		t.Errorf("tool_name: got %v", rec["tool_name"])
	}
	if model, ok := rec["model"].(string); !ok || model != "claude-opus-4-6" {
		t.Errorf("model: got %v", rec["model"])
	}
	if cost, ok := rec["cost_usd"].(float64); !ok || cost != 0.05 {
		t.Errorf("cost_usd: got %v, want 0.05", rec["cost_usd"])
	}
}

// TestUsageRecordMissingToolName verifies error when tool_name is missing.
func TestUsageRecordMissingToolName(t *testing.T) {
	origUsageLog := usageLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	usageLog = logPath
	defer func() { usageLog = origUsageLog }()

	ctx := context.Background()
	result, err := handleUsageRecord(ctx, makeRequest(map[string]any{
		"model": "claude-opus-4-6",
	}))
	if err != nil {
		t.Fatalf("handleUsageRecord: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "tool_name") {
		t.Errorf("should contain error about missing tool_name: %s", text)
	}
}

// TestUsageReport verifies aggregation report generation.
func TestUsageReport(t *testing.T) {
	origUsageLog := usageLog
	origBudgetSpendingLog := budgetSpendingLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	budgetPath := filepath.Join(tmpDir, "budget_spending.jsonl")
	usageLog = logPath
	budgetSpendingLog = budgetPath
	defer func() {
		usageLog = origUsageLog
		budgetSpendingLog = origBudgetSpendingLog
	}()

	ctx := context.Background()

	// Write multiple usage records
	now := time.Now().UTC()
	records := []map[string]any{
		{
			"timestamp": now.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.05,
			"tokens":    1000,
			"project":   "project-a",
			"model":     "opus",
		},
		{
			"timestamp": now.Format(time.RFC3339),
			"tool_name": "tool2",
			"cost_usd":  0.10,
			"tokens":    2000,
			"project":   "project-a",
			"model":     "opus",
		},
		{
			"timestamp": now.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.03,
			"tokens":    500,
			"project":   "project-b",
			"model":     "haiku",
		},
	}

	for _, rec := range records {
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Get report
	result, err := handleUsageReport(ctx, makeRequest(map[string]any{
		"period": "all",
	}))
	if err != nil {
		t.Fatalf("handleUsageReport: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if totalCost, ok := resp["total_cost"].(float64); !ok {
		t.Errorf("total_cost not a number: %v", resp["total_cost"])
	} else {
		// Allow for floating point precision (0.18 or very close)
		if totalCost < 0.17 || totalCost > 0.19 {
			t.Errorf("total_cost: got %v, want ~0.18", totalCost)
		}
	}

	if totalTokens, ok := resp["total_tokens"].(float64); !ok || totalTokens != 3500 {
		t.Errorf("total_tokens: got %v, want 3500", resp["total_tokens"])
	}

	// Verify by_project breakdown (should be 2: project-a, project-b)
	if byProject, ok := resp["by_project"].([]any); ok {
		if len(byProject) != 2 {
			t.Errorf("by_project count: got %d, want 2", len(byProject))
		}
	} else {
		t.Error("by_project should be array")
	}

	// Verify by_model breakdown (should be 2: opus, haiku)
	if byModel, ok := resp["by_model"].([]any); ok {
		if len(byModel) != 2 {
			t.Errorf("by_model count: got %d, want 2", len(byModel))
		}
	} else {
		t.Error("by_model should be array")
	}
}

// TestUsageReportFiltering verifies period, project, and session filtering.
func TestUsageReportFiltering(t *testing.T) {
	origUsageLog := usageLog
	origBudgetSpendingLog := budgetSpendingLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	budgetPath := filepath.Join(tmpDir, "budget_spending.jsonl")
	usageLog = logPath
	budgetSpendingLog = budgetPath
	defer func() {
		usageLog = origUsageLog
		budgetSpendingLog = origBudgetSpendingLog
	}()

	ctx := context.Background()

	// Write records with different timestamps
	now := time.Now().UTC()
	today := map[string]any{
		"timestamp": now.Format(time.RFC3339),
		"tool_name": "today_tool",
		"cost_usd":  0.10,
		"tokens":    1000,
		"project":   "proj-a",
	}
	old := map[string]any{
		"timestamp": now.Add(-10 * 24 * time.Hour).Format(time.RFC3339),
		"tool_name": "old_tool",
		"cost_usd":  0.05,
		"tokens":    500,
		"project":   "proj-b",
	}

	for _, rec := range []map[string]any{today, old} {
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Report for today only
	result, err := handleUsageReport(ctx, makeRequest(map[string]any{
		"period": "today",
	}))
	if err != nil {
		t.Fatalf("handleUsageReport: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if recordCount, ok := resp["record_count"].(float64); !ok || recordCount != 1 {
		t.Errorf("today filter: got %d records, want 1", int(recordCount))
	}

	// Report filtered by project
	result, err = handleUsageReport(ctx, makeRequest(map[string]any{
		"period":  "all",
		"project": "proj-a",
	}))
	if err != nil {
		t.Fatalf("handleUsageReport (project filter): %v", err)
	}

	text = extractText(result)
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if recordCount, ok := resp["record_count"].(float64); !ok || recordCount != 1 {
		t.Errorf("project filter: got %d records, want 1", int(recordCount))
	}
}

// TestUsageTopTools verifies tool ranking by call count.
func TestUsageTopTools(t *testing.T) {
	origUsageLog := usageLog
	origBudgetSpendingLog := budgetSpendingLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	budgetPath := filepath.Join(tmpDir, "budget_spending.jsonl")
	usageLog = logPath
	budgetSpendingLog = budgetPath
	defer func() {
		usageLog = origUsageLog
		budgetSpendingLog = origBudgetSpendingLog
	}()

	ctx := context.Background()

	// Write records with different tools
	now := time.Now().UTC()
	records := []map[string]any{
		{"timestamp": now.Format(time.RFC3339), "tool_name": "tool1", "cost_usd": 0.05},
		{"timestamp": now.Format(time.RFC3339), "tool_name": "tool1", "cost_usd": 0.05},
		{"timestamp": now.Format(time.RFC3339), "tool_name": "tool1", "cost_usd": 0.05},
		{"timestamp": now.Format(time.RFC3339), "tool_name": "tool2", "cost_usd": 0.10},
		{"timestamp": now.Format(time.RFC3339), "tool_name": "tool2", "cost_usd": 0.10},
		{"timestamp": now.Format(time.RFC3339), "tool_name": "tool3", "cost_usd": 0.15},
	}

	for _, rec := range records {
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Get top tools
	result, err := handleUsageTopTools(ctx, makeRequest(map[string]any{
		"period": "all",
		"limit":  "2",
	}))
	if err != nil {
		t.Fatalf("handleUsageTopTools: %v", err)
	}

	text := extractText(result)
	var tools []map[string]any
	if err := json.Unmarshal([]byte(text), &tools); err != nil {
		t.Fatalf("parse tools: %v", err)
	}

	if len(tools) != 2 {
		t.Errorf("tool count: got %d, want 2 (limit)", len(tools))
	}

	// Verify sorted by count descending
	if len(tools) >= 1 {
		if name, ok := tools[0]["name"].(string); !ok || name != "tool1" {
			t.Errorf("top tool should be tool1 (count=3), got %v", tools[0]["name"])
		}
		if count, ok := tools[0]["count"].(float64); !ok || count != 3 {
			t.Errorf("top tool count: got %v, want 3", tools[0]["count"])
		}
	}

	if len(tools) >= 2 {
		if name, ok := tools[1]["name"].(string); !ok || name != "tool2" {
			t.Errorf("second tool should be tool2 (count=2), got %v", tools[1]["name"])
		}
	}
}

// TestUsageTopToolsDefault verifies default limit of 10.
func TestUsageTopToolsDefault(t *testing.T) {
	origUsageLog := usageLog
	origBudgetSpendingLog := budgetSpendingLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	budgetPath := filepath.Join(tmpDir, "budget_spending.jsonl")
	usageLog = logPath
	budgetSpendingLog = budgetPath
	defer func() {
		usageLog = origUsageLog
		budgetSpendingLog = origBudgetSpendingLog
	}()

	ctx := context.Background()

	// Write records for 15 different tools
	now := time.Now().UTC()
	for i := 1; i <= 15; i++ {
		for j := 0; j < i; j++ {
			rec := map[string]any{
				"timestamp": now.Format(time.RFC3339),
				"tool_name": fmt.Sprintf("tool%d", i),
				"cost_usd":  0.01,
			}
			data, _ := json.Marshal(rec)
			f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
			f.Write(append(data, '\n'))
			f.Close()
		}
	}

	// Get top tools without specifying limit (should default to 10)
	result, err := handleUsageTopTools(ctx, makeRequest(map[string]any{
		"period": "all",
	}))
	if err != nil {
		t.Fatalf("handleUsageTopTools: %v", err)
	}

	text := extractText(result)
	var tools []map[string]any
	if err := json.Unmarshal([]byte(text), &tools); err != nil {
		t.Fatalf("parse tools: %v", err)
	}

	if len(tools) != 10 {
		t.Errorf("default limit: got %d tools, want 10", len(tools))
	}
}

// TestUsageTrends verifies grouping by day and week.
func TestUsageTrends(t *testing.T) {
	origUsageLog := usageLog
	origBudgetSpendingLog := budgetSpendingLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	budgetPath := filepath.Join(tmpDir, "budget_spending.jsonl")
	usageLog = logPath
	budgetSpendingLog = budgetPath
	defer func() {
		usageLog = origUsageLog
		budgetSpendingLog = origBudgetSpendingLog
	}()

	ctx := context.Background()

	// Write records spanning multiple days
	base := time.Date(2026, 3, 1, 12, 0, 0, 0, time.UTC)

	// Day 1: 2 records
	for i := 0; i < 2; i++ {
		rec := map[string]any{
			"timestamp": base.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.05,
		}
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Day 2: 3 records
	day2 := base.Add(24 * time.Hour)
	for i := 0; i < 3; i++ {
		rec := map[string]any{
			"timestamp": day2.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.03,
		}
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Get trends grouped by day
	result, err := handleUsageTrends(ctx, makeRequest(map[string]any{
		"period":   "week",
		"group_by": "day",
	}))
	if err != nil {
		t.Fatalf("handleUsageTrends: %v", err)
	}

	text := extractText(result)
	var trends []map[string]any
	if err := json.Unmarshal([]byte(text), &trends); err != nil {
		t.Fatalf("parse trends: %v", err)
	}

	if len(trends) != 2 {
		t.Errorf("trend buckets: got %d, want 2", len(trends))
	}

	// Verify sorting by date
	if len(trends) >= 2 {
		date1 := trends[0]["date"].(string)
		date2 := trends[1]["date"].(string)
		if date1 > date2 {
			t.Error("trends should be sorted by date ascending")
		}
	}

	// Verify counts
	if len(trends) >= 1 {
		if count, ok := trends[0]["count"].(float64); !ok || count != 2 {
			t.Errorf("day 1 count: got %v, want 2", trends[0]["count"])
		}
		if cost, ok := trends[0]["cost"].(float64); !ok || cost != 0.10 {
			t.Errorf("day 1 cost: got %v, want 0.10", trends[0]["cost"])
		}
	}

	if len(trends) >= 2 {
		if count, ok := trends[1]["count"].(float64); !ok || count != 3 {
			t.Errorf("day 2 count: got %v, want 3", trends[1]["count"])
		}
		if cost, ok := trends[1]["cost"].(float64); !ok || cost != 0.09 {
			t.Errorf("day 2 cost: got %v, want 0.09", trends[1]["cost"])
		}
	}
}

// TestUsageTrendsWeeklyGrouping verifies week grouping.
func TestUsageTrendsWeeklyGrouping(t *testing.T) {
	origUsageLog := usageLog
	origBudgetSpendingLog := budgetSpendingLog
	tmpDir := t.TempDir()
	logPath := filepath.Join(tmpDir, "usage.jsonl")
	budgetPath := filepath.Join(tmpDir, "budget_spending.jsonl")
	usageLog = logPath
	budgetSpendingLog = budgetPath
	defer func() {
		usageLog = origUsageLog
		budgetSpendingLog = origBudgetSpendingLog
	}()

	ctx := context.Background()

	// Write records for two different weeks
	week1 := time.Date(2026, 2, 23, 12, 0, 0, 0, time.UTC) // Monday of week 8
	week2 := time.Date(2026, 3, 2, 12, 0, 0, 0, time.UTC)  // Monday of week 9

	for i := 0; i < 2; i++ {
		rec := map[string]any{
			"timestamp": week1.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.05,
		}
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	for i := 0; i < 3; i++ {
		rec := map[string]any{
			"timestamp": week2.Format(time.RFC3339),
			"tool_name": "tool1",
			"cost_usd":  0.03,
		}
		data, _ := json.Marshal(rec)
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		f.Write(append(data, '\n'))
		f.Close()
	}

	// Get trends grouped by week
	result, err := handleUsageTrends(ctx, makeRequest(map[string]any{
		"period":   "month",
		"group_by": "week",
	}))
	if err != nil {
		t.Fatalf("handleUsageTrends: %v", err)
	}

	text := extractText(result)
	var trends []map[string]any
	if err := json.Unmarshal([]byte(text), &trends); err != nil {
		t.Fatalf("parse trends: %v", err)
	}

	if len(trends) < 2 {
		t.Errorf("should have at least 2 weeks: got %d", len(trends))
	}

	// Verify week format (YYYY-Www)
	for i, trend := range trends {
		if date, ok := trend["date"].(string); ok {
			if !strings.Contains(date, "-W") {
				t.Errorf("week %d should have ISO week format: %s", i, date)
			}
		}
	}
}
