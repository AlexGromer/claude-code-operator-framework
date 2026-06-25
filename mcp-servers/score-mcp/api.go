package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"regexp"
	"time"
)

var githubRepoRe = regexp.MustCompile(`github\.com/([^/]+)/([^/\s]+)`)

const apiTimeout = 10 * time.Second

// FetchGitHubMetrics fetches repository metrics from the GitHub API.
// Returns nil on any error (graceful fallback).
func FetchGitHubMetrics(repoURL string) *GitHubMetrics {
	match := githubRepoRe.FindStringSubmatch(repoURL)
	if match == nil {
		return nil
	}
	owner := match[1]
	repo := match[2]
	// Strip .git suffix
	if len(repo) > 4 && repo[len(repo)-4:] == ".git" {
		repo = repo[:len(repo)-4]
	}

	apiURL := fmt.Sprintf("https://api.github.com/repos/%s/%s", owner, repo)

	client := &http.Client{Timeout: apiTimeout}
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")

	if token := os.Getenv("GITHUB_TOKEN"); token != "" {
		req.Header.Set("Authorization", "token "+token)
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil
	}

	var data struct {
		Stars       int    `json:"stargazers_count"`
		Forks       int    `json:"forks_count"`
		OpenIssues  int    `json:"open_issues_count"`
		LastUpdated string `json:"updated_at"`
		Language    string `json:"language"`
		Description string `json:"description"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil
	}

	return &GitHubMetrics{
		Stars:       data.Stars,
		Forks:       data.Forks,
		OpenIssues:  data.OpenIssues,
		LastUpdated: data.LastUpdated,
		Language:    data.Language,
		Description: data.Description,
	}
}

// FetchArxivCitations fetches citation count from Semantic Scholar.
// Returns 0 on any error (graceful fallback).
func FetchArxivCitations(arxivID string) int {
	apiURL := fmt.Sprintf("https://api.semanticscholar.org/graph/v1/paper/arXiv:%s?fields=citationCount", arxivID)

	client := &http.Client{Timeout: apiTimeout}
	resp, err := client.Get(apiURL)
	if err != nil {
		return 0
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0
	}

	var data struct {
		CitationCount int `json:"citationCount"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return 0
	}

	return data.CitationCount
}
