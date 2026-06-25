package main

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

func makeRequest(args map[string]any) mcp.CallToolRequest {
	return mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: args,
		},
	}
}

func extractText(result *mcp.CallToolResult) string {
	if result == nil || len(result.Content) == 0 {
		return ""
	}
	for _, c := range result.Content {
		if tc, ok := c.(mcp.TextContent); ok {
			return tc.Text
		}
	}
	return ""
}

func TestHandleScoreDiscovery(t *testing.T) {
	ctx := context.Background()

	// Test with no external API calls (no github_url or arxiv_id)
	result, err := handleScoreDiscovery(ctx, makeRequest(map[string]any{
		"title":       "CLI Agent Automation Tool",
		"description": "A terminal-based interactive shell for automation with tool-use",
	}))
	if err != nil {
		t.Fatalf("score_discovery: %v", err)
	}

	text := extractText(result)
	if text == "" {
		t.Fatal("empty result")
	}

	var resp ScoredDiscovery
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp.Discovery.Title != "CLI Agent Automation Tool" {
		t.Errorf("title: got %q", resp.Discovery.Title)
	}
	if resp.TotalScore <= 0 {
		t.Errorf("total_score should be > 0, got %.2f", resp.TotalScore)
	}
	if resp.Priority == "" {
		t.Error("priority should not be empty")
	}
	if resp.RecommendedAction == "" {
		t.Error("recommended_action should not be empty")
	}
	// D1 should be high (multiple CLI keywords)
	if resp.Scores.D1CLIApplicability < 22 {
		t.Errorf("D1 should be >= 22 for CLI tool, got %d", resp.Scores.D1CLIApplicability)
	}
}

func TestHandleScoreDiscovery_MissingTitle(t *testing.T) {
	ctx := context.Background()

	result, err := handleScoreDiscovery(ctx, makeRequest(map[string]any{
		"description": "No title provided",
	}))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "title is required") {
		t.Errorf("expected error about title, got: %s", text)
	}
}

func TestHandleScoreDimensions(t *testing.T) {
	ctx := context.Background()

	result, err := handleScoreDimensions(ctx, makeRequest(map[string]any{
		"title":       "Production Stable API Framework",
		"description": "An enterprise SDK library with documentation and examples. Achieves 35% latency reduction.",
	}))
	if err != nil {
		t.Fatalf("score_dimensions: %v", err)
	}

	text := extractText(result)
	if text == "" {
		t.Fatal("empty result")
	}

	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["title"] != "Production Stable API Framework" {
		t.Errorf("title: got %v", resp["title"])
	}

	dims, ok := resp["dimensions"].([]any)
	if !ok {
		t.Fatal("dimensions should be an array")
	}
	if len(dims) != 5 {
		t.Errorf("dimensions count: got %d, want 5", len(dims))
	}

	formatted, ok := resp["formatted"].(string)
	if !ok || formatted == "" {
		t.Error("formatted should be a non-empty string")
	}
}

func TestHandleScoreBatch(t *testing.T) {
	ctx := context.Background()

	discoveries := []Discovery{
		{
			Title:       "CLI Terminal Tool",
			Description: "An interactive shell automation agent",
		},
		{
			Title:       "Web Dashboard",
			Description: "A visual frontend GUI for monitoring",
		},
		{
			Title:       "API SDK Library",
			Description: "A framework for integration",
		},
	}
	raw, _ := json.Marshal(discoveries)

	result, err := handleScoreBatch(ctx, makeRequest(map[string]any{
		"discoveries": string(raw),
	}))
	if err != nil {
		t.Fatalf("score_batch: %v", err)
	}

	text := extractText(result)
	if text == "" {
		t.Fatal("empty result")
	}

	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	count := int(resp["count"].(float64))
	if count != 3 {
		t.Errorf("count: got %d, want 3", count)
	}

	results, ok := resp["results"].([]any)
	if !ok {
		t.Fatal("results should be an array")
	}
	if len(results) != 3 {
		t.Errorf("results length: got %d, want 3", len(results))
	}

	// Verify CLI tool scores higher than web dashboard
	first := results[0].(map[string]any)
	second := results[1].(map[string]any)
	if first["total_score"].(float64) <= second["total_score"].(float64) {
		t.Errorf("CLI tool (%.2f) should score higher than web dashboard (%.2f)",
			first["total_score"].(float64), second["total_score"].(float64))
	}
}

func TestHandleScoreBatch_InvalidJSON(t *testing.T) {
	ctx := context.Background()

	result, err := handleScoreBatch(ctx, makeRequest(map[string]any{
		"discoveries": "not valid json",
	}))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "invalid JSON") {
		t.Errorf("expected JSON error, got: %s", text)
	}
}

func TestHandleScoreBatch_Empty(t *testing.T) {
	ctx := context.Background()

	result, err := handleScoreBatch(ctx, makeRequest(map[string]any{
		"discoveries": "[]",
	}))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "empty") {
		t.Errorf("expected empty error, got: %s", text)
	}
}

func TestHandleScoreBatch_MissingParam(t *testing.T) {
	ctx := context.Background()

	result, err := handleScoreBatch(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "required") {
		t.Errorf("expected required error, got: %s", text)
	}
}

func TestServerInfo(t *testing.T) {
	info := ServerInfo()
	if info.Name != "score-mcp" {
		t.Errorf("name: got %q, want score-mcp", info.Name)
	}
	if info.Version != "0.1.0" {
		t.Errorf("version: got %q, want 0.1.0", info.Version)
	}
}
