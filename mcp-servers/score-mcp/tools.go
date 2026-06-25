package main

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func registerTools(s *server.MCPServer) {
	// score_discovery — full scoring of a single discovery
	s.AddTool(mcp.NewTool("score_discovery",
		mcp.WithDescription("Full scoring of a single discovery using 5-dimension relevance matrix. Returns total score, priority, and recommended action."),
		mcp.WithString("title", mcp.Required(), mcp.Description("Discovery title")),
		mcp.WithString("description", mcp.Description("Discovery description")),
		mcp.WithString("github_url", mcp.Description("GitHub repository URL for metrics")),
		mcp.WithString("arxiv_id", mcp.Description("arXiv paper ID for citation count")),
		mcp.WithString("category", mcp.Description("Category: prompting, framework, benchmark, model")),
		mcp.WithString("date_discovered", mcp.Description("Date discovered (YYYY-MM-DD)")),
	), handleScoreDiscovery)

	// score_dimensions — individual D1-D5 breakdown
	s.AddTool(mcp.NewTool("score_dimensions",
		mcp.WithDescription("Return individual D1-D5 dimension breakdown for a discovery without total/priority."),
		mcp.WithString("title", mcp.Required(), mcp.Description("Discovery title")),
		mcp.WithString("description", mcp.Description("Discovery description")),
		mcp.WithString("github_url", mcp.Description("GitHub repository URL for metrics")),
		mcp.WithString("arxiv_id", mcp.Description("arXiv paper ID for citation count")),
		mcp.WithString("category", mcp.Description("Category: prompting, framework, benchmark, model")),
		mcp.WithString("date_discovered", mcp.Description("Date discovered (YYYY-MM-DD)")),
	), handleScoreDimensions)

	// score_batch — score multiple discoveries
	s.AddTool(mcp.NewTool("score_batch",
		mcp.WithDescription("Score multiple discoveries in batch. Param is a JSON array of discovery objects."),
		mcp.WithString("discoveries", mcp.Required(), mcp.Description("JSON string — array of discovery objects with title, description, github_url, arxiv_id, category, date_discovered")),
	), handleScoreBatch)
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

func discoveryFromRequest(request mcp.CallToolRequest) (Discovery, error) {
	title, err := request.RequireString("title")
	if err != nil {
		return Discovery{}, fmt.Errorf("title is required")
	}
	return Discovery{
		Title:          title,
		Description:    optStr(request, "description"),
		GitHubURL:      optStr(request, "github_url"),
		ArxivID:        optStr(request, "arxiv_id"),
		Category:       optStr(request, "category"),
		DateDiscovered: optStr(request, "date_discovered"),
	}, nil
}

// --- Handlers ---

func handleScoreDiscovery(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	d, err := discoveryFromRequest(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	result := ScoreDiscovery(d, true)
	return jsonResult(result)
}

func handleScoreDimensions(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	d, err := discoveryFromRequest(request)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	// Fetch external metrics for accurate D2/D4
	var gh *GitHubMetrics
	var citations int
	if d.GitHubURL != "" {
		gh = FetchGitHubMetrics(d.GitHubURL)
	}
	if d.ArxivID != "" {
		citations = FetchArxivCitations(d.ArxivID)
	}

	scores := DimensionScores{
		D1CLIApplicability:  ScoreD1(d),
		D2ProductionReady:   ScoreD2(d, gh),
		D3PerformanceImpact: ScoreD3(d),
		D4AdoptionVelocity:  ScoreD4(gh, citations),
		D5IntegrationEffort: ScoreD5(d),
	}

	type dimensionDetail struct {
		Name   string  `json:"name"`
		Score  int     `json:"score"`
		Max    int     `json:"max"`
		Weight float64 `json:"weight"`
	}

	breakdown := []dimensionDetail{
		{"D1 CLI Applicability", scores.D1CLIApplicability, 30, weightD1},
		{"D2 Production Readiness", scores.D2ProductionReady, 25, weightD2},
		{"D3 Performance Impact", scores.D3PerformanceImpact, 20, weightD3},
		{"D4 Adoption Velocity", scores.D4AdoptionVelocity, 15, weightD4},
		{"D5 Integration Effort", scores.D5IntegrationEffort, 10, weightD5},
	}

	return jsonResult(map[string]any{
		"title":      d.Title,
		"dimensions": breakdown,
		"formatted":  FormatDimensions(scores),
	})
}

func handleScoreBatch(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	raw, err := request.RequireString("discoveries")
	if err != nil {
		return mcp.NewToolResultError("discoveries is required (JSON array string)"), nil
	}

	var discoveries []Discovery
	if err := json.Unmarshal([]byte(raw), &discoveries); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("invalid JSON: %v", err)), nil
	}

	if len(discoveries) == 0 {
		return mcp.NewToolResultError("empty discoveries array"), nil
	}

	type batchItem struct {
		Title    string  `json:"title"`
		Total    float64 `json:"total_score"`
		Priority string  `json:"priority"`
		Action   string  `json:"recommended_action"`
	}

	results := make([]batchItem, 0, len(discoveries))
	for _, d := range discoveries {
		scored := ScoreDiscovery(d, true)
		results = append(results, batchItem{
			Title:    d.Title,
			Total:    scored.TotalScore,
			Priority: scored.Priority,
			Action:   scored.RecommendedAction,
		})
	}

	return jsonResult(map[string]any{
		"count":   len(results),
		"results": results,
	})
}
