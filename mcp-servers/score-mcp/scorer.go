package main

import (
	"fmt"
	"math"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// Discovery represents a single discovery to score.
type Discovery struct {
	Title          string `json:"title"`
	Description    string `json:"description"`
	GitHubURL      string `json:"github_url"`
	ArxivID        string `json:"arxiv_id"`
	Category       string `json:"category"`
	DateDiscovered string `json:"date_discovered"`
}

// DimensionScores holds individual D1-D5 scores.
type DimensionScores struct {
	D1CLIApplicability  int `json:"D1_cli_applicability"`
	D2ProductionReady   int `json:"D2_production_readiness"`
	D3PerformanceImpact int `json:"D3_performance_impact"`
	D4AdoptionVelocity  int `json:"D4_adoption_velocity"`
	D5IntegrationEffort int `json:"D5_integration_effort"`
}

// ScoredDiscovery is the full scoring result.
type ScoredDiscovery struct {
	Discovery         Discovery         `json:"discovery"`
	Scores            DimensionScores   `json:"scores"`
	TotalScore        float64           `json:"total_score"`
	Priority          string            `json:"priority"`
	RecommendedAction string            `json:"recommended_action"`
	GitHubMetrics     *GitHubMetrics    `json:"github_metrics,omitempty"`
	Citations         int               `json:"citations"`
	ScoredAt          string            `json:"scored_at"`
}

// GitHubMetrics holds repository metrics from the GitHub API.
type GitHubMetrics struct {
	Stars       int    `json:"stars"`
	Forks       int    `json:"forks"`
	OpenIssues  int    `json:"open_issues"`
	LastUpdated string `json:"last_updated"`
	Language    string `json:"language"`
	Description string `json:"description"`
}

// Dimension weights
const (
	weightD1 = 0.30
	weightD2 = 0.25
	weightD3 = 0.20
	weightD4 = 0.15
	weightD5 = 0.10
)

// Decision thresholds
var decisionThresholds = map[string]struct {
	Min    float64
	Max    float64
	Action string
}{
	"P1_CRITICAL": {80, 100, "Immediate PoC (<1 week)"},
	"P2_HIGH":     {60, 79, "Planned PoC (<1 month)"},
	"P3_MEDIUM":   {40, 59, "Backlog (<1 quarter)"},
	"ARCHIVE":     {0, 39, "Monitor only"},
}

// CLI Applicability keywords (D1)
var cliKeywordsHigh = []string{
	"cli", "terminal", "shell", "bash", "command-line",
	"repl", "interactive", "agent", "automation", "tool-use", "function-calling",
}
var cliKeywordsMedium = []string{"api", "sdk", "library", "framework", "integration"}
var cliKeywordsLow = []string{"gui", "web", "frontend", "visual", "dashboard"}

// Production Readiness indicators (D2)
var maturityKeywords = []string{"stable", "production", "enterprise", "v1.0", "release"}
var riskKeywords = []string{"experimental", "alpha", "beta", "poc", "prototype", "research"}
var qualityKeywords = []string{"tested", "ci/cd", "documentation", "examples"}

// Performance keywords (D3)
var perfQualityKW = []string{"accuracy", "correctness", "hallucination", "factual", "reliable"}
var perfCostKW = []string{"cost", "efficient", "token", "pricing", "cheap"}
var perfLatencyKW = []string{"fast", "latency", "speed", "performance", "real-time", "cache"}

// Integration effort keywords (D5)
var lowEffortKW = []string{"drop-in", "compatible", "wrapper", "plugin", "extension"}
var mediumEffortKW = []string{"migration", "refactor", "adaptation"}
var highEffortKW = []string{"rewrite", "rebuild", "custom", "from-scratch"}

var percentageRe = regexp.MustCompile(`(\d+)%`)

// combinedText returns lowercase title + description for keyword matching.
func combinedText(d Discovery) string {
	return strings.ToLower(d.Title + " " + d.Description)
}

// countKeywords counts how many keywords appear in text.
func countKeywords(text string, keywords []string) int {
	count := 0
	for _, kw := range keywords {
		if strings.Contains(text, kw) {
			count++
		}
	}
	return count
}

// ScoreD1 scores CLI Applicability (0-30 points).
func ScoreD1(d Discovery) int {
	text := combinedText(d)

	highCount := countKeywords(text, cliKeywordsHigh)
	if highCount >= 3 {
		return 28
	}
	if highCount >= 1 {
		return 22
	}

	mediumCount := countKeywords(text, cliKeywordsMedium)
	if mediumCount >= 2 {
		return 15
	}

	lowCount := countKeywords(text, cliKeywordsLow)
	if lowCount >= 2 {
		return 5
	}

	return 12
}

// ScoreD2 scores Production Readiness (0-25 points).
func ScoreD2(d Discovery, gh *GitHubMetrics) int {
	text := combinedText(d)
	score := 12

	score += countKeywords(text, maturityKeywords) * 3
	score -= countKeywords(text, riskKeywords) * 2
	score += countKeywords(text, qualityKeywords) * 2

	stars := 0
	if gh != nil {
		stars = gh.Stars
	}
	if stars >= 10000 {
		score += 5
	} else if stars >= 1000 {
		score += 3
	} else if stars >= 100 {
		score += 1
	}

	if score < 0 {
		score = 0
	}
	if score > 25 {
		score = 25
	}
	return score
}

// ScoreD3 scores Performance Impact (0-20 points).
func ScoreD3(d Discovery) int {
	text := combinedText(d)

	matches := percentageRe.FindAllStringSubmatch(text, -1)
	var gains []int
	for _, m := range matches {
		if v, err := strconv.Atoi(m[1]); err == nil {
			gains = append(gains, v)
		}
	}

	qualityHits := countKeywords(text, perfQualityKW)
	costHits := countKeywords(text, perfCostKW)
	latencyHits := countKeywords(text, perfLatencyKW)

	// Major gains claimed
	for _, p := range gains {
		if p >= 30 {
			return 19
		}
	}

	if qualityHits >= 2 {
		return 17
	}
	if costHits >= 2 || latencyHits >= 2 {
		return 15
	}
	if qualityHits+costHits+latencyHits >= 1 {
		return 10
	}

	return 3
}

// ScoreD4 scores Adoption Velocity (0-15 points).
func ScoreD4(gh *GitHubMetrics, citations int) int {
	stars := 0
	if gh != nil {
		stars = gh.Stars
	}

	if stars >= 50000 || citations >= 100 {
		return 15
	}
	if stars >= 10000 || citations >= 50 {
		return 13
	}
	if stars >= 1000 || citations >= 10 {
		return 9
	}
	if stars >= 100 || citations >= 1 {
		return 5
	}
	return 2
}

// ScoreD5 scores Integration Effort (0-10 points, inverse).
func ScoreD5(d Discovery) int {
	text := combinedText(d)

	lowCount := countKeywords(text, lowEffortKW)
	if lowCount >= 2 {
		return 10
	}
	if lowCount >= 1 {
		return 8
	}

	medCount := countKeywords(text, mediumEffortKW)
	if medCount >= 1 {
		return 5
	}

	highCount := countKeywords(text, highEffortKW)
	if highCount >= 1 {
		return 2
	}

	return 6
}

// CalculateTotal computes the weighted total score (0-100).
func CalculateTotal(s DimensionScores) float64 {
	total := float64(s.D1CLIApplicability)*weightD1 +
		float64(s.D2ProductionReady)*weightD2 +
		float64(s.D3PerformanceImpact)*weightD3 +
		float64(s.D4AdoptionVelocity)*weightD4 +
		float64(s.D5IntegrationEffort)*weightD5
	return math.Round(total*100) / 100
}

// DeterminePriority returns priority level based on total score.
func DeterminePriority(totalScore float64) string {
	if totalScore >= 80 {
		return "P1_CRITICAL"
	}
	if totalScore >= 60 {
		return "P2_HIGH"
	}
	if totalScore >= 40 {
		return "P3_MEDIUM"
	}
	return "ARCHIVE"
}

// RecommendedAction returns the action string for a priority.
func RecommendedAction(priority string) string {
	if t, ok := decisionThresholds[priority]; ok {
		return t.Action
	}
	return "Monitor only"
}

// ScoreDiscovery performs full scoring of a discovery, optionally fetching external data.
func ScoreDiscovery(d Discovery, fetchExternal bool) ScoredDiscovery {
	var gh *GitHubMetrics
	var citations int

	if fetchExternal {
		if d.GitHubURL != "" {
			gh = FetchGitHubMetrics(d.GitHubURL)
		}
		if d.ArxivID != "" {
			citations = FetchArxivCitations(d.ArxivID)
		}
	}

	return ScoreDiscoveryWithMetrics(d, gh, citations)
}

// ScoreDiscoveryWithMetrics scores with pre-fetched metrics (for testing/batch).
func ScoreDiscoveryWithMetrics(d Discovery, gh *GitHubMetrics, citations int) ScoredDiscovery {
	scores := DimensionScores{
		D1CLIApplicability:  ScoreD1(d),
		D2ProductionReady:   ScoreD2(d, gh),
		D3PerformanceImpact: ScoreD3(d),
		D4AdoptionVelocity:  ScoreD4(gh, citations),
		D5IntegrationEffort: ScoreD5(d),
	}

	total := CalculateTotal(scores)
	priority := DeterminePriority(total)

	return ScoredDiscovery{
		Discovery:         d,
		Scores:            scores,
		TotalScore:        total,
		Priority:          priority,
		RecommendedAction: RecommendedAction(priority),
		GitHubMetrics:     gh,
		Citations:         citations,
		ScoredAt:          time.Now().Format(time.RFC3339),
	}
}

// FormatDimensions returns a human-readable breakdown.
func FormatDimensions(s DimensionScores) string {
	return fmt.Sprintf(
		"D1 CLI Applicability:  %d/30 (weight %.0f%%)\n"+
			"D2 Production Ready:   %d/25 (weight %.0f%%)\n"+
			"D3 Performance Impact: %d/20 (weight %.0f%%)\n"+
			"D4 Adoption Velocity:  %d/15 (weight %.0f%%)\n"+
			"D5 Integration Effort: %d/10 (weight %.0f%%)",
		s.D1CLIApplicability, weightD1*100,
		s.D2ProductionReady, weightD2*100,
		s.D3PerformanceImpact, weightD3*100,
		s.D4AdoptionVelocity, weightD4*100,
		s.D5IntegrationEffort, weightD5*100,
	)
}
