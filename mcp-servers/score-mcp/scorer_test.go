package main

import (
	"testing"
)

func TestScoreD1_HighKeywords(t *testing.T) {
	d := Discovery{
		Title:       "CLI Agent Automation Tool",
		Description: "A terminal-based interactive shell for agent automation with tool-use and function-calling",
	}
	score := ScoreD1(d)
	if score != 28 {
		t.Errorf("D1 high keywords: got %d, want 28", score)
	}
}

func TestScoreD1_SingleHighKeyword(t *testing.T) {
	d := Discovery{
		Title:       "New Agent Framework",
		Description: "Build powerful agents with this tool",
	}
	score := ScoreD1(d)
	if score != 22 {
		t.Errorf("D1 single high: got %d, want 22", score)
	}
}

func TestScoreD1_MediumKeywords(t *testing.T) {
	d := Discovery{
		Title:       "API SDK for Data Processing",
		Description: "A library and framework for data pipelines",
	}
	score := ScoreD1(d)
	if score != 15 {
		t.Errorf("D1 medium: got %d, want 15", score)
	}
}

func TestScoreD1_LowKeywords(t *testing.T) {
	d := Discovery{
		Title:       "Visual Dashboard Builder",
		Description: "A web frontend for creating dashboards",
	}
	score := ScoreD1(d)
	if score != 5 {
		t.Errorf("D1 low: got %d, want 5", score)
	}
}

func TestScoreD1_Default(t *testing.T) {
	d := Discovery{
		Title:       "Novel Research Approach",
		Description: "A new method for solving math problems",
	}
	score := ScoreD1(d)
	if score != 12 {
		t.Errorf("D1 default: got %d, want 12", score)
	}
}

func TestScoreD2_BaseWithMaturity(t *testing.T) {
	d := Discovery{
		Title:       "Production Stable Release v1.0",
		Description: "Enterprise-grade tested solution with documentation and examples",
	}
	// maturity: stable(+3), production(+3), enterprise(+3), v1.0(+3) = +12
	// quality: tested(+2), documentation(+2), examples(+2) = +6
	// base 12 + 12 + 6 = 30, clamped to 25
	score := ScoreD2(d, nil)
	if score != 25 {
		t.Errorf("D2 mature: got %d, want 25", score)
	}
}

func TestScoreD2_WithRisk(t *testing.T) {
	d := Discovery{
		Title:       "Experimental Alpha Prototype",
		Description: "A research poc for beta testing",
	}
	// risk: experimental(-2), alpha(-2), prototype(-2), research(-2), poc(-2), beta(-2) = -12
	// base 12 - 12 = 0
	score := ScoreD2(d, nil)
	if score != 0 {
		t.Errorf("D2 risky: got %d, want 0", score)
	}
}

func TestScoreD2_WithGitHubStars(t *testing.T) {
	d := Discovery{Title: "Some Tool", Description: "A tool"}
	gh := &GitHubMetrics{Stars: 15000}
	score := ScoreD2(d, gh)
	// base 12 + 5 (stars>=10k) = 17
	if score != 17 {
		t.Errorf("D2 with stars: got %d, want 17", score)
	}
}

func TestScoreD3_MajorGain(t *testing.T) {
	d := Discovery{
		Title:       "50% Cost Reduction",
		Description: "Achieves 50% cost savings on token usage",
	}
	score := ScoreD3(d)
	if score != 19 {
		t.Errorf("D3 major: got %d, want 19", score)
	}
}

func TestScoreD3_QualityFocus(t *testing.T) {
	d := Discovery{
		Title:       "Accuracy and Correctness Improvement",
		Description: "Reduces hallucination and improves factual reliability",
	}
	score := ScoreD3(d)
	// quality hits: accuracy, correctness, hallucination, factual, reliable = 5 >= 2
	if score != 17 {
		t.Errorf("D3 quality: got %d, want 17", score)
	}
}

func TestScoreD3_CostFocus(t *testing.T) {
	d := Discovery{
		Title:       "Efficient Token Pricing",
		Description: "Cost-effective and cheap inference",
	}
	score := ScoreD3(d)
	// cost: cost, efficient, token, pricing, cheap = 5 >= 2
	if score != 15 {
		t.Errorf("D3 cost: got %d, want 15", score)
	}
}

func TestScoreD3_NoPerformance(t *testing.T) {
	d := Discovery{
		Title:       "New UI Design Pattern",
		Description: "A novel approach to user interfaces",
	}
	score := ScoreD3(d)
	if score != 3 {
		t.Errorf("D3 none: got %d, want 3", score)
	}
}

func TestScoreD4_Viral(t *testing.T) {
	gh := &GitHubMetrics{Stars: 60000}
	score := ScoreD4(gh, 0)
	if score != 15 {
		t.Errorf("D4 viral stars: got %d, want 15", score)
	}

	score = ScoreD4(nil, 150)
	if score != 15 {
		t.Errorf("D4 viral citations: got %d, want 15", score)
	}
}

func TestScoreD4_Strong(t *testing.T) {
	gh := &GitHubMetrics{Stars: 12000}
	score := ScoreD4(gh, 0)
	if score != 13 {
		t.Errorf("D4 strong: got %d, want 13", score)
	}
}

func TestScoreD4_Growing(t *testing.T) {
	gh := &GitHubMetrics{Stars: 2000}
	score := ScoreD4(gh, 0)
	if score != 9 {
		t.Errorf("D4 growing: got %d, want 9", score)
	}
}

func TestScoreD4_Emerging(t *testing.T) {
	gh := &GitHubMetrics{Stars: 200}
	score := ScoreD4(gh, 0)
	if score != 5 {
		t.Errorf("D4 emerging: got %d, want 5", score)
	}
}

func TestScoreD4_None(t *testing.T) {
	score := ScoreD4(nil, 0)
	if score != 2 {
		t.Errorf("D4 none: got %d, want 2", score)
	}
}

func TestScoreD5_LowEffort(t *testing.T) {
	d := Discovery{
		Title:       "Drop-in Plugin Extension",
		Description: "A compatible wrapper for existing tools",
	}
	// drop-in, plugin, extension, compatible, wrapper = 5 >= 2
	score := ScoreD5(d)
	if score != 10 {
		t.Errorf("D5 low effort: got %d, want 10", score)
	}
}

func TestScoreD5_SingleLow(t *testing.T) {
	d := Discovery{
		Title:       "Compatible Adapter",
		Description: "Works with existing systems",
	}
	score := ScoreD5(d)
	if score != 8 {
		t.Errorf("D5 single low: got %d, want 8", score)
	}
}

func TestScoreD5_MediumEffort(t *testing.T) {
	d := Discovery{
		Title:       "Migration Tool",
		Description: "Requires refactoring existing code",
	}
	score := ScoreD5(d)
	// migration + refactor => medium >= 1 but also low_effort=0
	if score != 5 {
		t.Errorf("D5 medium: got %d, want 5", score)
	}
}

func TestScoreD5_HighEffort(t *testing.T) {
	d := Discovery{
		Title:       "Complete Rewrite Required",
		Description: "Build from-scratch with custom implementation",
	}
	score := ScoreD5(d)
	// rewrite, from-scratch, custom = high >= 1, but also check medium: no migration/refactor/adaptation
	if score != 2 {
		t.Errorf("D5 high: got %d, want 2", score)
	}
}

func TestScoreD5_Default(t *testing.T) {
	d := Discovery{
		Title:       "Novel Algorithm",
		Description: "A new approach to sorting",
	}
	score := ScoreD5(d)
	if score != 6 {
		t.Errorf("D5 default: got %d, want 6", score)
	}
}

func TestCalculateTotal(t *testing.T) {
	scores := DimensionScores{
		D1CLIApplicability:  28,
		D2ProductionReady:   20,
		D3PerformanceImpact: 19,
		D4AdoptionVelocity:  15,
		D5IntegrationEffort: 10,
	}
	total := CalculateTotal(scores)
	// 28*0.30 + 20*0.25 + 19*0.20 + 15*0.15 + 10*0.10
	// 8.4 + 5.0 + 3.8 + 2.25 + 1.0 = 20.45
	expected := 20.45
	if total != expected {
		t.Errorf("total: got %.2f, want %.2f", total, expected)
	}
}

func TestDeterminePriority(t *testing.T) {
	tests := []struct {
		score float64
		want  string
	}{
		{95, "P1_CRITICAL"},
		{80, "P1_CRITICAL"},
		{79, "P2_HIGH"},
		{60, "P2_HIGH"},
		{59, "P3_MEDIUM"},
		{40, "P3_MEDIUM"},
		{39, "ARCHIVE"},
		{0, "ARCHIVE"},
	}
	for _, tt := range tests {
		got := DeterminePriority(tt.score)
		if got != tt.want {
			t.Errorf("priority(%.0f): got %s, want %s", tt.score, got, tt.want)
		}
	}
}

func TestScoreDiscoveryWithMetrics(t *testing.T) {
	d := Discovery{
		Title:       "CLI Agent Automation Framework",
		Description: "A stable production terminal tool for agent automation with tool-use. Achieves 40% cost reduction. Drop-in plugin compatible.",
	}
	gh := &GitHubMetrics{Stars: 55000}
	citations := 120

	result := ScoreDiscoveryWithMetrics(d, gh, citations)

	if result.Scores.D1CLIApplicability != 28 {
		t.Errorf("D1: got %d, want 28", result.Scores.D1CLIApplicability)
	}
	if result.Scores.D4AdoptionVelocity != 15 {
		t.Errorf("D4: got %d, want 15", result.Scores.D4AdoptionVelocity)
	}
	if result.TotalScore <= 0 {
		t.Errorf("total should be > 0, got %.2f", result.TotalScore)
	}
	if result.Priority == "" {
		t.Error("priority should not be empty")
	}
	if result.RecommendedAction == "" {
		t.Error("action should not be empty")
	}
	if result.ScoredAt == "" {
		t.Error("scored_at should not be empty")
	}
}

func TestFormatDimensions(t *testing.T) {
	scores := DimensionScores{
		D1CLIApplicability:  22,
		D2ProductionReady:   15,
		D3PerformanceImpact: 10,
		D4AdoptionVelocity:  9,
		D5IntegrationEffort: 6,
	}
	formatted := FormatDimensions(scores)
	if formatted == "" {
		t.Error("formatted should not be empty")
	}
	if len(formatted) < 50 {
		t.Errorf("formatted too short: %q", formatted)
	}
}
