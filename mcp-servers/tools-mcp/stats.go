package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

var (
	budgetSpendingLog = filepath.Join(os.Getenv("HOME"), ".claude", "evaluation", "data", "budget_spending.jsonl")
	usageLog          = filepath.Join(os.Getenv("HOME"), ".claude", "usage-log.jsonl")
)

// loadRecords loads JSONL records from a file, filtering by max age in days.
func loadRecords(filepath string, maxAgeDays int) []map[string]any {
	f, err := os.Open(filepath)
	if err != nil {
		return nil
	}
	defer f.Close()

	cutoff := time.Now().UTC().Add(-time.Duration(maxAgeDays) * 24 * time.Hour)
	var records []map[string]any

	scanner := bufio.NewScanner(f)
	// Increase buffer size for potentially long lines
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		var rec map[string]any
		if err := json.Unmarshal([]byte(line), &rec); err != nil {
			continue
		}

		// Extract timestamp from various field names
		tsStr := ""
		for _, key := range []string{"timestamp", "ts", "created_at"} {
			if v, ok := rec[key]; ok {
				if s, ok := v.(string); ok && s != "" {
					tsStr = s
					break
				}
			}
		}

		if tsStr != "" {
			ts, err := parseTimestamp(tsStr)
			if err == nil {
				if ts.Before(cutoff) {
					continue
				}
				rec["_ts"] = ts.Format(time.RFC3339)
				rec["_ts_parsed"] = ts
			}
		}

		records = append(records, rec)
	}

	return records
}

// extractCost extracts cost value from a record, checking multiple field names.
func extractCost(rec map[string]any) float64 {
	for _, key := range []string{"cost_usd", "cost", "estimated_cost"} {
		if v, ok := rec[key]; ok {
			switch val := v.(type) {
			case float64:
				return val
			case string:
				if f, err := strconv.ParseFloat(val, 64); err == nil {
					return f
				}
			}
		}
	}
	return 0
}

// extractTokens extracts token count from a record.
func extractTokens(rec map[string]any) int {
	total := 0
	for _, key := range []string{"tokens", "input_tokens"} {
		if v, ok := rec[key]; ok {
			switch val := v.(type) {
			case float64:
				total += int(val)
			case string:
				if n, err := strconv.Atoi(val); err == nil {
					total += n
				}
			}
		}
	}
	// Add output_tokens separately
	if v, ok := rec["output_tokens"]; ok {
		switch val := v.(type) {
		case float64:
			total += int(val)
		case string:
			if n, err := strconv.Atoi(val); err == nil {
				total += n
			}
		}
	}
	return total
}

// periodFilter returns the cutoff time for a period string.
func periodFilter(period string) time.Time {
	now := time.Now().UTC()
	switch period {
	case "today":
		return time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC)
	case "week":
		return now.Add(-7 * 24 * time.Hour)
	case "month":
		return now.Add(-30 * 24 * time.Hour)
	default:
		return time.Time{} // all time
	}
}

// filterRecords filters records by period, project, and session.
func filterRecords(records []map[string]any, period, project, session string) []map[string]any {
	cutoff := periodFilter(period)
	var filtered []map[string]any

	for _, rec := range records {
		// Filter by period
		if !cutoff.IsZero() {
			if tsParsed, ok := rec["_ts_parsed"].(time.Time); ok {
				if tsParsed.Before(cutoff) {
					continue
				}
			}
		}

		// Filter by project
		if project != "" {
			recProject := ""
			if v, ok := rec["project"]; ok {
				if s, ok := v.(string); ok {
					recProject = s
				}
			}
			if v, ok := rec["working_directory"]; ok && recProject == "" {
				if s, ok := v.(string); ok {
					recProject = s
				}
			}
			if recProject == "" || !containsIgnoreCase(recProject, project) {
				continue
			}
		}

		// Filter by session
		if session != "" {
			recSession := ""
			if v, ok := rec["session_id"]; ok {
				if s, ok := v.(string); ok {
					recSession = s
				}
			}
			if v, ok := rec["session"]; ok && recSession == "" {
				if s, ok := v.(string); ok {
					recSession = s
				}
			}
			if recSession == "" || !containsIgnoreCase(recSession, session) {
				continue
			}
		}

		filtered = append(filtered, rec)
	}

	return filtered
}

func containsIgnoreCase(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr ||
		len(substr) > 0 && findSubstring(s, substr))
}

func findSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		match := true
		for j := 0; j < len(substr); j++ {
			sc := s[i+j]
			pc := substr[j]
			// Simple case-insensitive
			if sc != pc && sc != pc+32 && sc != pc-32 {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}

func handleUsageRecord(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	toolName, err := reqStr(request, "tool_name")
	if err != nil {
		return errResult(err.Error()), nil
	}

	record := map[string]any{
		"tool_name": toolName,
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	}

	if v := optStr(request, "model"); v != "" {
		record["model"] = v
	}
	if v := optStr(request, "cost"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			record["cost_usd"] = f
		}
	}
	if v := optStr(request, "tokens"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			record["tokens"] = n
		}
	}
	if v := optStr(request, "project"); v != "" {
		record["project"] = v
	}

	// Append to JSONL file
	data, err := json.Marshal(record)
	if err != nil {
		return errResult(fmt.Sprintf("json marshal: %v", err)), nil
	}
	data = append(data, '\n')

	f, err := os.OpenFile(usageLog, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return errResult(fmt.Sprintf("open usage log: %v", err)), nil
	}
	defer f.Close()

	if _, err := f.Write(data); err != nil {
		return errResult(fmt.Sprintf("write usage log: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status": "recorded",
		"file":   usageLog,
		"record": record,
	})
}

func handleUsageReport(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	period := optStr(request, "period")
	if period == "" {
		period = "all"
	}
	project := optStr(request, "project")
	session := optStr(request, "session")

	// Load from both sources
	maxDays := 365
	if period == "today" {
		maxDays = 1
	} else if period == "week" {
		maxDays = 7
	} else if period == "month" {
		maxDays = 30
	}

	allRecords := append(loadRecords(budgetSpendingLog, maxDays), loadRecords(usageLog, maxDays)...)
	filtered := filterRecords(allRecords, period, project, session)

	totalCost := 0.0
	totalTokens := 0
	byProject := make(map[string]*struct {
		Cost   float64 `json:"cost"`
		Tokens int     `json:"tokens"`
		Count  int     `json:"count"`
	})
	byModel := make(map[string]*struct {
		Cost   float64 `json:"cost"`
		Tokens int     `json:"tokens"`
		Count  int     `json:"count"`
	})

	for _, rec := range filtered {
		cost := extractCost(rec)
		tokens := extractTokens(rec)
		totalCost += cost
		totalTokens += tokens

		// By project
		proj := "unknown"
		if v, ok := rec["project"]; ok {
			if s, ok := v.(string); ok && s != "" {
				proj = s
			}
		}
		if v, ok := rec["working_directory"]; ok && proj == "unknown" {
			if s, ok := v.(string); ok && s != "" {
				proj = s
			}
		}
		if _, ok := byProject[proj]; !ok {
			byProject[proj] = &struct {
				Cost   float64 `json:"cost"`
				Tokens int     `json:"tokens"`
				Count  int     `json:"count"`
			}{}
		}
		byProject[proj].Cost += cost
		byProject[proj].Tokens += tokens
		byProject[proj].Count++

		// By model
		model := "unknown"
		if v, ok := rec["model"]; ok {
			if s, ok := v.(string); ok && s != "" {
				model = s
			}
		}
		if _, ok := byModel[model]; !ok {
			byModel[model] = &struct {
				Cost   float64 `json:"cost"`
				Tokens int     `json:"tokens"`
				Count  int     `json:"count"`
			}{}
		}
		byModel[model].Cost += cost
		byModel[model].Tokens += tokens
		byModel[model].Count++
	}

	// Convert to arrays
	type summaryEntry struct {
		Name   string  `json:"name"`
		Cost   float64 `json:"cost"`
		Tokens int     `json:"tokens"`
		Count  int     `json:"count"`
	}

	var projectArray []summaryEntry
	for name, data := range byProject {
		projectArray = append(projectArray, summaryEntry{
			Name:   name,
			Cost:   data.Cost,
			Tokens: data.Tokens,
			Count:  data.Count,
		})
	}
	sort.Slice(projectArray, func(i, j int) bool {
		return projectArray[i].Cost > projectArray[j].Cost
	})

	var modelArray []summaryEntry
	for name, data := range byModel {
		modelArray = append(modelArray, summaryEntry{
			Name:   name,
			Cost:   data.Cost,
			Tokens: data.Tokens,
			Count:  data.Count,
		})
	}
	sort.Slice(modelArray, func(i, j int) bool {
		return modelArray[i].Cost > modelArray[j].Cost
	})

	return jsonResult(map[string]any{
		"total_cost":   totalCost,
		"total_tokens": totalTokens,
		"record_count": len(filtered),
		"period":       period,
		"by_project":   projectArray,
		"by_model":     modelArray,
	})
}

func handleUsageTopTools(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	period := optStr(request, "period")
	if period == "" {
		period = "all"
	}
	limit := optInt(request, "limit", 10)

	maxDays := 365
	if period == "today" {
		maxDays = 1
	} else if period == "week" {
		maxDays = 7
	} else if period == "month" {
		maxDays = 30
	}

	allRecords := append(loadRecords(budgetSpendingLog, maxDays), loadRecords(usageLog, maxDays)...)
	filtered := filterRecords(allRecords, period, "", "")

	type toolStat struct {
		Name  string  `json:"name"`
		Count int     `json:"count"`
		Cost  float64 `json:"cost"`
	}

	byTool := make(map[string]*toolStat)

	for _, rec := range filtered {
		name := "unknown"
		// Try tool_name first, then model
		if v, ok := rec["tool_name"]; ok {
			if s, ok := v.(string); ok && s != "" {
				name = s
			}
		} else if v, ok := rec["model"]; ok {
			if s, ok := v.(string); ok && s != "" {
				name = s
			}
		}

		if _, ok := byTool[name]; !ok {
			byTool[name] = &toolStat{Name: name}
		}
		byTool[name].Count++
		byTool[name].Cost += extractCost(rec)
	}

	// Sort by count descending
	var result []toolStat
	for _, stat := range byTool {
		result = append(result, *stat)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Count > result[j].Count
	})

	// Limit
	if len(result) > limit {
		result = result[:limit]
	}

	return jsonResult(result)
}

func handleUsageTrends(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	period := optStr(request, "period")
	if period == "" {
		period = "week"
	}
	groupBy := optStr(request, "group_by")
	if groupBy == "" {
		groupBy = "day"
	}

	maxDays := 7
	if period == "month" {
		maxDays = 30
	}

	allRecords := append(loadRecords(budgetSpendingLog, maxDays), loadRecords(usageLog, maxDays)...)
	filtered := filterRecords(allRecords, period, "", "")

	type trendBucket struct {
		Date  string  `json:"date"`
		Count int     `json:"count"`
		Cost  float64 `json:"cost"`
	}

	buckets := make(map[string]*trendBucket)

	for _, rec := range filtered {
		var ts time.Time
		if tsParsed, ok := rec["_ts_parsed"].(time.Time); ok {
			ts = tsParsed
		} else {
			ts = time.Now().UTC()
		}

		var bucketKey string
		if groupBy == "week" {
			year, week := ts.ISOWeek()
			bucketKey = fmt.Sprintf("%d-W%02d", year, week)
		} else {
			bucketKey = ts.Format("2006-01-02")
		}

		if _, ok := buckets[bucketKey]; !ok {
			buckets[bucketKey] = &trendBucket{Date: bucketKey}
		}
		buckets[bucketKey].Count++
		buckets[bucketKey].Cost += extractCost(rec)
	}

	// Sort by date
	var result []trendBucket
	for _, b := range buckets {
		result = append(result, *b)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Date < result[j].Date
	})

	return jsonResult(result)
}
