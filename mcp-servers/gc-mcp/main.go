package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

const version = "0.1.0"

func main() {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "--run":
			cwd := getCwdFromArgs()
			results := runAllCleanups(cwd, false)
			printCLI(results)
			return
		case "--dry-run":
			cwd := getCwdFromArgs()
			results := runAllCleanups(cwd, true)
			printCLI(results)
			return
		case "--quick":
			cwd := getCwdFromArgs()
			results := runQuickCleanups(cwd, false)
			printCLI(results)
			return
		case "--status":
			cwd := getCwdFromArgs()
			data, _ := json.MarshalIndent(getStatus(cwd), "", "  ")
			fmt.Println(string(data))
			return
		case "--version":
			fmt.Println("gc-mcp", version)
			return
		}
	}

	s := server.NewMCPServer(
		"gc-mcp",
		version,
		server.WithToolCapabilities(false),
	)

	registerTools(s)

	if os.Getenv("GC_MCP_DEBUG") != "" {
		fmt.Fprintf(os.Stderr, "gc-mcp %s started (tools: %d)\n", version, 3)
	}

	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %v\n", err)
		os.Exit(1)
	}
}

func getCwdFromArgs() string {
	if len(os.Args) > 2 {
		return os.Args[2]
	}
	cwd, _ := os.Getwd()
	return cwd
}

func printCLI(results *GCResults) {
	data, err := json.MarshalIndent(results, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "json error: %v\n", err)
		os.Exit(1)
	}
	fmt.Println(string(data))
}

// ServerInfo returns the MCP server info for testing.
func ServerInfo() mcp.Implementation {
	return mcp.Implementation{
		Name:    "gc-mcp",
		Version: version,
	}
}
