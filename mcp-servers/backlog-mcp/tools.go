package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

const maxActive = 30
const maxArchive = 50

func registerTools(s *server.MCPServer) {
	// backlog_add
	s.AddTool(mcp.NewTool("backlog_add",
		mcp.WithDescription("Add a new task to the Active section of BACKLOG.md"),
		mcp.WithString("description", mcp.Required(), mcp.Description("Task description")),
		mcp.WithString("priority", mcp.Description("P1, P2, or P3 (default P2)")),
		mcp.WithString("wave", mcp.Description("Wave group, e.g. W1, W2")),
		mcp.WithString("agent_hint", mcp.Description("Suggested agent type, e.g. web-developer")),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md (default: $CWD/BACKLOG.md)")),
	), handleAdd)

	// backlog_update
	s.AddTool(mcp.NewTool("backlog_update",
		mcp.WithDescription("Update fields of an existing task (find by ID or description substring)"),
		mcp.WithString("task_id", mcp.Required(), mcp.Description("Task ID (8-char hex) or description substring")),
		mcp.WithString("description", mcp.Description("New description")),
		mcp.WithString("priority", mcp.Description("New priority: P1, P2, P3")),
		mcp.WithString("wave", mcp.Description("New wave group")),
		mcp.WithString("agent_hint", mcp.Description("New agent hint")),
		mcp.WithString("section", mcp.Description("Move to section: Active, Completed Archive, Deferred")),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleUpdate)

	// backlog_complete
	s.AddTool(mcp.NewTool("backlog_complete",
		mcp.WithDescription("Mark a task as completed and move it to Completed Archive"),
		mcp.WithString("task_id", mcp.Required(), mcp.Description("Task ID or description substring")),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleComplete)

	// backlog_delete
	s.AddTool(mcp.NewTool("backlog_delete",
		mcp.WithDescription("Remove a task from the backlog entirely"),
		mcp.WithString("task_id", mcp.Required(), mcp.Description("Task ID or description substring")),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleDelete)

	// backlog_list
	s.AddTool(mcp.NewTool("backlog_list",
		mcp.WithDescription("List backlog tasks with optional filters"),
		mcp.WithString("section", mcp.Description("Filter by section: Active, Completed Archive, Deferred")),
		mcp.WithString("priority", mcp.Description("Filter by priority: P1, P2, P3")),
		mcp.WithString("wave", mcp.Description("Filter by wave: W1, W2, etc.")),
		mcp.WithString("agent", mcp.Description("Filter by agent hint")),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleList)

	// backlog_stale
	s.AddTool(mcp.NewTool("backlog_stale",
		mcp.WithDescription("Detect stale tasks (P1 >3d, P2 >7d, P3 >14d)"),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleStale)

	// backlog_stats
	s.AddTool(mcp.NewTool("backlog_stats",
		mcp.WithDescription("Show backlog statistics: counts by priority, section, wave"),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleStats)

	// backlog_rotate
	s.AddTool(mcp.NewTool("backlog_rotate",
		mcp.WithDescription("Enforce limits: active max 30 (overflow → Deferred), archive max 50 (oldest deleted)"),
		mcp.WithString("file_path", mcp.Description("Path to BACKLOG.md")),
	), handleRotate)
}

// --- Helpers ---

func resolveFilePath(request mcp.CallToolRequest) string {
	args := request.GetArguments()
	if v, ok := args["file_path"]; ok {
		if s, ok := v.(string); ok && s != "" {
			return s
		}
	}
	cwd, _ := os.Getwd()
	return filepath.Join(cwd, "BACKLOG.md")
}

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

// --- Handlers ---

func handleAdd(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	desc, err := request.RequireString("description")
	if err != nil {
		return mcp.NewToolResultError("description is required"), nil
	}

	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	task := Task{
		Description: desc,
		Priority:    ParsePriority(optStr(request, "priority")),
		Wave:        optStr(request, "wave"),
		AgentHint:   optStr(request, "agent_hint"),
		CreatedDate: time.Now().Truncate(24 * time.Hour),
		Section:     SectionActive,
	}
	task.ID = TaskID(desc)

	b.Active = append(b.Active, task)

	if err := Save(path, b); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save: %v", err)), nil
	}

	return jsonResult(map[string]string{
		"status": "added",
		"id":     task.ID,
		"task":   FormatTask(task),
	})
}

func handleUpdate(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query, err := request.RequireString("task_id")
	if err != nil {
		return mcp.NewToolResultError("task_id is required"), nil
	}

	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	task, section, idx := FindTask(b, query)
	if task == nil {
		return mcp.NewToolResultError(fmt.Sprintf("task not found: %q", query)), nil
	}

	// Apply updates
	if v := optStr(request, "description"); v != "" {
		task.Description = v
		task.ID = TaskID(v)
	}
	if v := optStr(request, "priority"); v != "" {
		task.Priority = ParsePriority(v)
	}
	if v := optStr(request, "wave"); v != "" {
		task.Wave = v
	}
	if v := optStr(request, "agent_hint"); v != "" {
		task.AgentHint = v
	}

	// Move to different section if requested
	if v := optStr(request, "section"); v != "" {
		newSection := Section(v)
		if newSection != section {
			taskCopy := *task
			RemoveTask(b, section, idx)
			switch newSection {
			case SectionActive:
				b.Active = append(b.Active, taskCopy)
			case SectionCompleted:
				b.Completed = append(b.Completed, taskCopy)
			case SectionDeferred:
				b.Deferred = append(b.Deferred, taskCopy)
			}
		}
	}

	if err := Save(path, b); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save: %v", err)), nil
	}

	return jsonResult(map[string]string{
		"status": "updated",
		"id":     task.ID,
		"task":   FormatTask(*task),
	})
}

func handleComplete(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query, err := request.RequireString("task_id")
	if err != nil {
		return mcp.NewToolResultError("task_id is required"), nil
	}

	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	task, section, idx := FindTask(b, query)
	if task == nil {
		return mcp.NewToolResultError(fmt.Sprintf("task not found: %q", query)), nil
	}

	now := time.Now().Truncate(24 * time.Hour)
	task.Completed = true
	task.CompletedDate = &now
	task.Section = SectionCompleted

	taskCopy := *task
	RemoveTask(b, section, idx)
	b.Completed = append([]Task{taskCopy}, b.Completed...)

	if err := Save(path, b); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save: %v", err)), nil
	}

	return jsonResult(map[string]string{
		"status": "completed",
		"id":     taskCopy.ID,
		"task":   FormatTask(taskCopy),
	})
}

func handleDelete(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	query, err := request.RequireString("task_id")
	if err != nil {
		return mcp.NewToolResultError("task_id is required"), nil
	}

	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	task, section, idx := FindTask(b, query)
	if task == nil {
		return mcp.NewToolResultError(fmt.Sprintf("task not found: %q", query)), nil
	}

	desc := task.Description
	RemoveTask(b, section, idx)

	if err := Save(path, b); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save: %v", err)), nil
	}

	return jsonResult(map[string]string{
		"status":      "deleted",
		"description": desc,
	})
}

func handleList(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	filterSection := optStr(request, "section")
	filterPriority := optStr(request, "priority")
	filterWave := optStr(request, "wave")
	filterAgent := optStr(request, "agent")

	var tasks []Task

	addFiltered := func(source []Task) {
		for _, t := range source {
			if filterSection != "" && !strings.Contains(string(t.Section), filterSection) {
				continue
			}
			if filterPriority != "" && t.Priority.String() != filterPriority {
				continue
			}
			if filterWave != "" && t.Wave != filterWave {
				continue
			}
			if filterAgent != "" && !strings.Contains(t.AgentHint, filterAgent) {
				continue
			}
			tasks = append(tasks, t)
		}
	}

	if filterSection == "" || strings.Contains("Active", filterSection) {
		addFiltered(b.Active)
	}
	if filterSection == "" || strings.Contains("Completed Archive", filterSection) {
		addFiltered(b.Completed)
	}
	if filterSection == "" || strings.Contains("Deferred", filterSection) {
		addFiltered(b.Deferred)
	}

	type taskView struct {
		ID          string `json:"id"`
		Description string `json:"description"`
		Priority    string `json:"priority"`
		Wave        string `json:"wave,omitempty"`
		Agent       string `json:"agent,omitempty"`
		Section     string `json:"section"`
		Completed   bool   `json:"completed"`
		Created     string `json:"created"`
		Done        string `json:"done,omitempty"`
	}
	views := make([]taskView, 0, len(tasks))
	for _, t := range tasks {
		v := taskView{
			ID:          t.ID,
			Description: t.Description,
			Priority:    t.Priority.String(),
			Wave:        t.Wave,
			Agent:       t.AgentHint,
			Section:     string(t.Section),
			Completed:   t.Completed,
			Created:     t.CreatedDate.Format(dateFormat),
		}
		if t.CompletedDate != nil {
			v.Done = t.CompletedDate.Format(dateFormat)
		}
		views = append(views, v)
	}

	return jsonResult(map[string]any{
		"count": len(views),
		"tasks": views,
	})
}

func handleStale(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	now := time.Now()
	type staleTask struct {
		ID          string `json:"id"`
		Description string `json:"description"`
		Priority    string `json:"priority"`
		Age         string `json:"age"`
		Threshold   string `json:"threshold"`
	}
	var stale []staleTask

	// Check active and deferred only
	checkTasks := append(b.Active, b.Deferred...)
	for _, t := range checkTasks {
		age := now.Sub(t.CreatedDate)
		threshold := StaleThreshold(t.Priority)
		if age > threshold {
			stale = append(stale, staleTask{
				ID:          t.ID,
				Description: t.Description,
				Priority:    t.Priority.String(),
				Age:         fmt.Sprintf("%dd", int(age.Hours()/24)),
				Threshold:   fmt.Sprintf("%dd", int(threshold.Hours()/24)),
			})
		}
	}

	return jsonResult(map[string]any{
		"stale_count": len(stale),
		"tasks":       stale,
	})
}

func handleStats(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	byPriority := map[string]int{"P1": 0, "P2": 0, "P3": 0}
	byWave := map[string]int{}
	byAgent := map[string]int{}

	for _, t := range b.Active {
		byPriority[t.Priority.String()]++
		if t.Wave != "" {
			byWave[t.Wave]++
		}
		if t.AgentHint != "" {
			byAgent[t.AgentHint]++
		}
	}

	return jsonResult(map[string]any{
		"active":    len(b.Active),
		"completed": len(b.Completed),
		"deferred":  len(b.Deferred),
		"total":     len(b.Active) + len(b.Completed) + len(b.Deferred),
		"by_priority": byPriority,
		"by_wave":     byWave,
		"by_agent":    byAgent,
	})
}

func handleRotate(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path := resolveFilePath(request)
	b, err := Load(path)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load: %v", err)), nil
	}

	movedToDeferred := 0
	deletedFromArchive := 0

	// Active overflow → move lowest priority to Deferred
	for len(b.Active) > maxActive {
		// Find lowest priority task (P3 first, then P2)
		worstIdx := len(b.Active) - 1
		for i := len(b.Active) - 1; i >= 0; i-- {
			if b.Active[i].Priority > b.Active[worstIdx].Priority {
				worstIdx = i
			}
		}
		task := b.Active[worstIdx]
		task.Section = SectionDeferred
		b.Deferred = append(b.Deferred, task)
		b.Active = append(b.Active[:worstIdx], b.Active[worstIdx+1:]...)
		movedToDeferred++
	}

	// Archive overflow → delete oldest
	for len(b.Completed) > maxArchive {
		b.Completed = b.Completed[:len(b.Completed)-1]
		deletedFromArchive++
	}

	if movedToDeferred > 0 || deletedFromArchive > 0 {
		if err := Save(path, b); err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("save: %v", err)), nil
		}
	}

	return jsonResult(map[string]any{
		"status":               "rotated",
		"moved_to_deferred":    movedToDeferred,
		"deleted_from_archive": deletedFromArchive,
		"active_count":         len(b.Active),
		"archive_count":        len(b.Completed),
	})
}
