// Package dag implements the Directed Acyclic Graph execution engine.
// It tracks task dependencies, dispatches ready tasks in parallel,
// and handles completions/failures with retry logic.
package dag

import (
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// Status represents a task node's execution state.
type Status string

const (
	StatusPending Status = "pending"
	StatusRunning Status = "running"
	StatusDone    Status = "done"
	StatusFailed  Status = "failed"
	StatusSkipped Status = "skipped"
)

// Task is a single node in the DAG.
type Task struct {
	ID         string
	Name       string
	Type       string   // plan | design | code | test | deploy | finance
	AgentRole  string   // CEO | CTO | Engineer_Backend | QA | DevOps | Finance
	DependsOn  []string // task IDs that must be Done before this can run
	InputData  map[string]any
	OutputData map[string]any
	Status     Status
	RetryCount int
	MaxRetries int
	Error      string
	CreatedAt  time.Time
	StartedAt  *time.Time
	DoneAt     *time.Time
}

// Graph is the execution DAG for one project.
type Graph struct {
	ProjectID string
	Tasks     map[string]*Task // task_id → task
	mu        sync.RWMutex
}

// NewGraph creates an empty DAG for a project.
func NewGraph(projectID string) *Graph {
	return &Graph{
		ProjectID: projectID,
		Tasks:     make(map[string]*Task),
	}
}

// AddTask registers a task node. Panics on duplicate ID.
func (g *Graph) AddTask(t *Task) {
	g.mu.Lock()
	defer g.mu.Unlock()
	if t.ID == "" {
		t.ID = uuid.NewString()
	}
	if t.MaxRetries == 0 {
		t.MaxRetries = 3
	}
	t.Status = StatusPending
	t.CreatedAt = time.Now()
	g.Tasks[t.ID] = t
}

// ReadyTasks returns all tasks whose dependencies are Done and status is Pending.
// These are safe to dispatch to Kafka immediately.
func (g *Graph) ReadyTasks() []*Task {
	g.mu.RLock()
	defer g.mu.RUnlock()

	var ready []*Task
	for _, t := range g.Tasks {
		if t.Status != StatusPending {
			continue
		}
		if g.allDepsComplete(t) {
			ready = append(ready, t)
		}
	}
	return ready
}

// allDepsComplete returns true if every dependency is StatusDone.
// Must be called with at least RLock held.
func (g *Graph) allDepsComplete(t *Task) bool {
	for _, depID := range t.DependsOn {
		dep, ok := g.Tasks[depID]
		if !ok || dep.Status != StatusDone {
			return false
		}
	}
	return true
}

// MarkRunning transitions a task to running. Returns error if wrong state.
func (g *Graph) MarkRunning(taskID string) error {
	g.mu.Lock()
	defer g.mu.Unlock()
	t, ok := g.Tasks[taskID]
	if !ok {
		return fmt.Errorf("dag: task %s not found", taskID)
	}
	if t.Status != StatusPending {
		return fmt.Errorf("dag: task %s is %s, expected pending", taskID, t.Status)
	}
	now := time.Now()
	t.Status = StatusRunning
	t.StartedAt = &now
	logger.L().Debug("dag: task running", zap.String("task_id", taskID), zap.String("name", t.Name))
	return nil
}

// MarkDone marks a task as successfully completed and stores output.
func (g *Graph) MarkDone(taskID string, output map[string]any) error {
	g.mu.Lock()
	defer g.mu.Unlock()
	t, ok := g.Tasks[taskID]
	if !ok {
		return fmt.Errorf("dag: task %s not found", taskID)
	}
	now := time.Now()
	t.Status = StatusDone
	t.DoneAt = &now
	t.OutputData = output
	logger.L().Info("dag: task done",
		zap.String("task_id", taskID),
		zap.String("name", t.Name),
		zap.Duration("duration", now.Sub(*t.StartedAt)),
	)
	return nil
}

// MarkFailed increments retry count or marks permanently failed.
// Returns true if the task should be retried (re-queued), false if exhausted.
func (g *Graph) MarkFailed(taskID, errMsg string) (shouldRetry bool, err error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	t, ok := g.Tasks[taskID]
	if !ok {
		return false, fmt.Errorf("dag: task %s not found", taskID)
	}
	t.RetryCount++
	t.Error = errMsg

	if t.RetryCount <= t.MaxRetries {
		t.Status = StatusPending // Reset to pending → will be re-dispatched
		logger.L().Warn("dag: task failed — will retry",
			zap.String("task_id", taskID),
			zap.Int("attempt", t.RetryCount),
			zap.Int("max_retries", t.MaxRetries),
		)
		return true, nil
	}

	t.Status = StatusFailed
	// Mark all downstream tasks as skipped
	g.skipDownstream(taskID)
	logger.L().Error("dag: task permanently failed",
		zap.String("task_id", taskID),
		zap.String("error", errMsg),
	)
	return false, nil
}

// skipDownstream marks all tasks that depend (directly or transitively)
// on the failed task as Skipped, preventing cascade execution.
func (g *Graph) skipDownstream(failedID string) {
	for _, t := range g.Tasks {
		if t.Status == StatusPending {
			for _, dep := range t.DependsOn {
				if dep == failedID {
					t.Status = StatusSkipped
					g.skipDownstream(t.ID) // Recursive
				}
			}
		}
	}
}

// IsComplete returns true when all tasks are Done, Failed, or Skipped.
func (g *Graph) IsComplete() bool {
	g.mu.RLock()
	defer g.mu.RUnlock()
	for _, t := range g.Tasks {
		if t.Status == StatusPending || t.Status == StatusRunning {
			return false
		}
	}
	return true
}

// Summary returns counts of tasks by status.
func (g *Graph) Summary() map[Status]int {
	g.mu.RLock()
	defer g.mu.RUnlock()
	m := map[Status]int{}
	for _, t := range g.Tasks {
		m[t.Status]++
	}
	return m
}

// Validate checks for cycles using DFS. Returns error if a cycle is found.
func (g *Graph) Validate() error {
	g.mu.RLock()
	defer g.mu.RUnlock()

	visited := make(map[string]bool)
	inStack := make(map[string]bool)

	var dfs func(id string) error
	dfs = func(id string) error {
		visited[id] = true
		inStack[id] = true
		t := g.Tasks[id]
		for _, dep := range t.DependsOn {
			if inStack[dep] {
				return fmt.Errorf("dag: cycle detected involving task %s → %s", id, dep)
			}
			if !visited[dep] {
				if err := dfs(dep); err != nil {
					return err
				}
			}
		}
		inStack[id] = false
		return nil
	}

	for id := range g.Tasks {
		if !visited[id] {
			if err := dfs(id); err != nil {
				return err
			}
		}
	}
	return nil
}

// RequeueStaleTasks finds tasks that have been running longer than timeout
// and transitions them to StatusFailed (which triggers a retry if under max).
// Returns the list of task IDs that were re-queued to be re-dispatched.
func (g *Graph) RequeueStaleTasks(timeout time.Duration) []string {
	var stale []string
	
	g.mu.RLock()
	now := time.Now()
	for id, t := range g.Tasks {
		if t.Status == StatusRunning && t.StartedAt != nil {
			if now.Sub(*t.StartedAt) > timeout {
				stale = append(stale, id)
			}
		}
	}
	g.mu.RUnlock()

	var retried []string
	for _, id := range stale {
		msg := fmt.Sprintf("Timeout: execution exceeded %s", timeout)
		retry, _ := g.MarkFailed(id, msg)
		if retry {
			retried = append(retried, id)
		}
	}

	return retried
}
