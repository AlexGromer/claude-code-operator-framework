package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

var validCategories = []string{
	"hooks", "skills", "tools", "mcp", "budget",
	"rules", "modules", "tests", "logs", "anacron",
}

func registerTools(s *server.MCPServer) {
	// doctor_check — single category
	s.AddTool(mcp.NewTool("doctor_check",
		mcp.WithDescription("Run a single category check (hooks/skills/tools/mcp/budget/rules/modules/tests/logs/anacron)"),
		mcp.WithString("category", mcp.Required(), mcp.Description("Category to check: hooks, skills, tools, mcp, budget, rules, modules, tests, logs, anacron")),
	), handleCheck)

	// doctor_full — all checks, dashboard text
	s.AddTool(mcp.NewTool("doctor_full",
		mcp.WithDescription("Run all 10 category checks, return dashboard-style text output"),
	), handleFull)

	// doctor_json — all checks, JSON output
	s.AddTool(mcp.NewTool("doctor_json",
		mcp.WithDescription("Run all 10 category checks, return machine-readable JSON output"),
	), handleJSON)
}

// --- Helpers ---

func optStr(request mcp.CallToolRequest, key string) string {
	args := request.GetArguments()
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func jsonResult(v any) (*mcp.CallToolResult, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("json: %v", err)), nil
	}
	return mcp.NewToolResultText(string(data)), nil
}

func isValidCategory(cat string) bool {
	for _, c := range validCategories {
		if c == cat {
			return true
		}
	}
	return false
}

// --- Handlers ---

func handleCheck(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	cat, err := request.RequireString("category")
	if err != nil {
		return mcp.NewToolResultError("category is required"), nil
	}
	cat = strings.TrimSpace(strings.ToLower(cat))

	if !isValidCategory(cat) {
		return mcp.NewToolResultError(fmt.Sprintf("invalid category: %q (valid: %s)", cat, strings.Join(validCategories, ", "))), nil
	}

	result := runCheck(cat)
	return jsonResult(checkResultToMap(result))
}

func handleFull(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	results := runAllChecks()
	dashboard := formatDashboard(results)
	return mcp.NewToolResultText(dashboard), nil
}

func handleJSON(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	results := runAllChecks()
	return jsonResult(allResultsToMap(results))
}

// --- Formatting ---

func checkResultToMap(r CheckResult) map[string]any {
	issues := make([]map[string]string, 0, len(r.Issues))
	for _, iss := range r.Issues {
		issues = append(issues, map[string]string{
			"level":   iss.Level,
			"message": iss.Message,
			"fix":     iss.Fix,
		})
	}
	return map[string]any{
		"name":     r.Name,
		"status":   r.Status(),
		"passed":   r.Passed,
		"failed":   r.Failed,
		"warnings": r.Warnings,
		"details":  r.Details,
		"issues":   issues,
	}
}

func allResultsToMap(results []CheckResult) map[string]any {
	checks := make([]map[string]any, 0, len(results))
	totalPassed := 0
	totalFailed := 0
	totalWarnings := 0
	catsOK := 0

	for _, r := range results {
		checks = append(checks, checkResultToMap(r))
		totalPassed += r.Passed
		totalFailed += r.Failed
		totalWarnings += r.Warnings
		if r.Status() == "OK" {
			catsOK++
		}
	}

	return map[string]any{
		"checks": checks,
		"summary": map[string]any{
			"total_passed":    totalPassed,
			"total_failed":    totalFailed,
			"total_warnings":  totalWarnings,
			"categories_ok":   catsOK,
			"categories_total": len(results),
		},
	}
}

func formatDashboard(results []CheckResult) string {
	var sb strings.Builder

	totalPassed := 0
	totalFailed := 0
	totalWarnings := 0
	catsOK := 0

	for _, r := range results {
		totalPassed += r.Passed
		totalFailed += r.Failed
		totalWarnings += r.Warnings
		if r.Status() == "OK" {
			catsOK++
		}
	}

	var overall string
	if totalFailed == 0 && totalWarnings == 0 {
		overall = "HEALTHY"
	} else if totalFailed == 0 {
		overall = "WARNINGS"
	} else {
		overall = "ISSUES FOUND"
	}

	sb.WriteString("CLAUDE CODE DOCTOR\n")
	sb.WriteString(strings.Repeat("=", 60) + "\n\n")

	for _, r := range results {
		icon := "[OK]"
		if r.Status() == "WARN" {
			icon = "[WARN]"
		} else if r.Status() == "FAIL" {
			icon = "[FAIL]"
		}

		detail := r.SummaryLine()

		// Add extras from details
		var extras []string
		if v, ok := r.Details["files_on_disk"]; ok {
			extras = append(extras, fmt.Sprintf("%v files", v))
		}
		if v, ok := r.Details["registered"]; ok {
			extras = append(extras, fmt.Sprintf("%v registered", v))
		}
		if v, ok := r.Details["total"]; ok {
			extras = append(extras, fmt.Sprintf("%v total", v))
		}
		if v, ok := r.Details["total_mb"]; ok {
			extras = append(extras, fmt.Sprintf("%v MB", v))
		}
		if v, ok := r.Details["jobs"]; ok {
			extras = append(extras, fmt.Sprintf("%v jobs", v))
		}
		if v, ok := r.Details["configured"]; ok {
			extras = append(extras, fmt.Sprintf("%v configured", v))
		}

		extraStr := ""
		if len(extras) > 0 {
			extraStr = " (" + strings.Join(extras, ", ") + ")"
		}

		sb.WriteString(fmt.Sprintf("  %-6s %-18s %s%s\n", icon, r.Name, detail, extraStr))
	}

	sb.WriteString(fmt.Sprintf("\n  Overall: %s (%d/%d categories OK)\n", overall, catsOK, len(results)))

	// Print issues
	hasIssues := false
	for _, r := range results {
		for _, iss := range r.Issues {
			if iss.Level == "FAIL" || iss.Level == "WARN" {
				if !hasIssues {
					sb.WriteString("\nIssues:\n")
					hasIssues = true
				}
				prefix := "FAIL"
				if iss.Level == "WARN" {
					prefix = "WARN"
				}
				sb.WriteString(fmt.Sprintf("  [%s] [%s] %s\n", prefix, r.Name, iss.Message))
				if iss.Fix != "" {
					sb.WriteString(fmt.Sprintf("     FIX: %s\n", iss.Fix))
				}
			}
		}
	}

	return sb.String()
}
