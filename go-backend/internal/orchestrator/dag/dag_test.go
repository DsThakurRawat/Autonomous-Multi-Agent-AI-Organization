package dag

import (
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// =========================================================================
// DAG Construction
// =========================================================================

func TestNewGraph(t *testing.T) {
	g := NewGraph("proj-1")
	assert.Equal(t, "proj-1", g.ProjectID)
	assert.Empty(t, g.Tasks)
}

func TestAddTask_GeneratesID(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{Name: "Setup Repo", AgentRole: "DevOps"}
	g.AddTask(task)
	assert.NotEmpty(t, task.ID)
	assert.Equal(t, StatusPending, task.Status)
	assert.Equal(t, 3, task.MaxRetries) // default
}

func TestAddTask_PreservesCustomID(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "custom-id", Name: "Task", AgentRole: "CEO"}
	g.AddTask(task)
	assert.Equal(t, "custom-id", task.ID)
}

func TestAddTask_SetsCreatedAt(t *testing.T) {
	g := NewGraph("proj-1")
	before := time.Now()
	task := &Task{Name: "Task", AgentRole: "CEO"}
	g.AddTask(task)
	assert.False(t, task.CreatedAt.Before(before))
}

// =========================================================================
// Diamond Dependency DAG
//
//     repo_setup
//        /    \
//   backend  frontend
//        \    /
//       deploy
// =========================================================================

func buildDiamondDAG() (*Graph, string, string, string, string) {
	g := NewGraph("diamond")
	repo := &Task{ID: "repo", Name: "Setup Repo", AgentRole: "DevOps"}
	g.AddTask(repo)

	backend := &Task{ID: "backend", Name: "Build Backend", AgentRole: "Engineer_Backend", DependsOn: []string{"repo"}}
	g.AddTask(backend)

	frontend := &Task{ID: "frontend", Name: "Build Frontend", AgentRole: "Engineer_Frontend", DependsOn: []string{"repo"}}
	g.AddTask(frontend)

	deploy := &Task{ID: "deploy", Name: "Deploy", AgentRole: "DevOps", DependsOn: []string{"backend", "frontend"}}
	g.AddTask(deploy)

	return g, "repo", "backend", "frontend", "deploy"
}

func TestDiamond_OnlyRepoInitiallyReady(t *testing.T) {
	g, _, _, _, _ := buildDiamondDAG()
	ready := g.ReadyTasks()
	assert.Len(t, ready, 1)
	assert.Equal(t, "Setup Repo", ready[0].Name)
}

func TestDiamond_BackendAndFrontendParallelAfterRepo(t *testing.T) {
	g, repoID, _, _, _ := buildDiamondDAG()
	require.NoError(t, g.MarkRunning(repoID))
	require.NoError(t, g.MarkDone(repoID, map[string]any{"dir": "/repo"}))

	ready := g.ReadyTasks()
	names := map[string]bool{}
	for _, r := range ready {
		names[r.Name] = true
	}
	assert.True(t, names["Build Backend"])
	assert.True(t, names["Build Frontend"])
	assert.False(t, names["Deploy"])
}

func TestDiamond_DeployOnlyAfterBothComplete(t *testing.T) {
	g, repoID, backendID, frontendID, _ := buildDiamondDAG()
	_ = g.MarkRunning(repoID)
	_ = g.MarkDone(repoID, nil)
	_ = g.MarkRunning(backendID)
	_ = g.MarkDone(backendID, map[string]any{"api": "done"})

	// Frontend still pending
	ready := g.ReadyTasks()
	for _, task := range ready {
		assert.NotEqual(t, "Deploy", task.Name)
	}

	_ = g.MarkRunning(frontendID)
	_ = g.MarkDone(frontendID, map[string]any{"ui": "done"})

	ready = g.ReadyTasks()
	assert.Len(t, ready, 1)
	assert.Equal(t, "Deploy", ready[0].Name)
}

// =========================================================================
// State Machine Transitions
// =========================================================================

func TestMarkRunning_NotFound(t *testing.T) {
	g := NewGraph("proj-1")
	err := g.MarkRunning("nonexistent")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not found")
}

func TestMarkRunning_InvalidState(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "t1", Name: "Task", AgentRole: "CEO"}
	g.AddTask(task)
	_ = g.MarkRunning("t1")
	// Try to mark running again
	err := g.MarkRunning("t1")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "expected pending")
}

func TestMarkDone_SetsTimestampAndOutput(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "t1", Name: "Task", AgentRole: "CEO"}
	g.AddTask(task)
	_ = g.MarkRunning("t1")

	output := map[string]any{"plan": "SaaS product", "budget": 50000}
	err := g.MarkDone("t1", output)
	require.NoError(t, err)
	assert.Equal(t, StatusDone, g.Tasks["t1"].Status)
	assert.NotNil(t, g.Tasks["t1"].DoneAt)
	assert.Equal(t, "SaaS product", g.Tasks["t1"].OutputData["plan"])
}

func TestMarkDone_NotFound(t *testing.T) {
	g := NewGraph("proj-1")
	err := g.MarkDone("nonexistent", nil)
	assert.Error(t, err)
}

// =========================================================================
// Retry Logic & Failure Cascading
// =========================================================================

func TestMarkFailed_Retry(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "t1", Name: "Flaky LLM", AgentRole: "CTO", MaxRetries: 3}
	g.AddTask(task)
	_ = g.MarkRunning("t1")

	shouldRetry, err := g.MarkFailed("t1", "rate limit exceeded")
	require.NoError(t, err)
	assert.True(t, shouldRetry)
	assert.Equal(t, StatusPending, g.Tasks["t1"].Status) // Reset to pending
	assert.Equal(t, 1, g.Tasks["t1"].RetryCount)
}

func TestMarkFailed_ExhaustedRetries(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "t1", Name: "Permanent Failure", AgentRole: "DevOps", MaxRetries: 2}
	g.AddTask(task)

	for i := 0; i < 2; i++ {
		g.Tasks["t1"].Status = StatusRunning
		retry, _ := g.MarkFailed("t1", "permission denied")
		assert.True(t, retry)
	}

	// Third failure → permanently failed
	g.Tasks["t1"].Status = StatusRunning
	retry, err := g.MarkFailed("t1", "permission denied (final)")
	require.NoError(t, err)
	assert.False(t, retry)
	assert.Equal(t, StatusFailed, g.Tasks["t1"].Status)
}

func TestMarkFailed_CascadesDownstream(t *testing.T) {
	g := NewGraph("proj-1")
	t1 := &Task{ID: "build", Name: "Build", AgentRole: "Engineer_Backend"}
	g.AddTask(t1)
	t2 := &Task{ID: "test", Name: "Test", AgentRole: "QA", DependsOn: []string{"build"}}
	g.AddTask(t2)
	t3 := &Task{ID: "deploy", Name: "Deploy", AgentRole: "DevOps", DependsOn: []string{"test"}}
	g.AddTask(t3)

	// Override MaxRetries to 0 AFTER AddTask (AddTask defaults 0→3)
	g.Tasks["build"].MaxRetries = 0

	require.NoError(t, g.MarkRunning("build"))
	retry, err := g.MarkFailed("build", "compile error")
	require.NoError(t, err)
	assert.False(t, retry) // MaxRetries=0, first failure is permanent
	assert.Equal(t, StatusFailed, g.Tasks["build"].Status)
	assert.Equal(t, StatusSkipped, g.Tasks["test"].Status)
	assert.Equal(t, StatusSkipped, g.Tasks["deploy"].Status)
}

func TestMarkFailed_NotFound(t *testing.T) {
	g := NewGraph("proj-1")
	_, err := g.MarkFailed("nonexistent", "error")
	assert.Error(t, err)
}

// =========================================================================
// Completion & Summary
// =========================================================================

func TestIsComplete_AllDone(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "t1", Name: "Task", AgentRole: "CEO"}
	g.AddTask(task)
	_ = g.MarkRunning("t1")
	_ = g.MarkDone("t1", nil)
	assert.True(t, g.IsComplete())
}

func TestIsComplete_MixedDoneAndSkipped(t *testing.T) {
	g := NewGraph("proj-1")
	t1 := &Task{ID: "t1", Name: "Ok", AgentRole: "CEO"}
	g.AddTask(t1)
	t2 := &Task{ID: "t2", Name: "Skipped", AgentRole: "QA"}
	g.AddTask(t2)

	_ = g.MarkRunning("t1")
	_ = g.MarkDone("t1", nil)
	g.Tasks["t2"].Status = StatusSkipped

	assert.True(t, g.IsComplete())
}

func TestIsComplete_StillPending(t *testing.T) {
	g := NewGraph("proj-1")
	task := &Task{ID: "t1", Name: "Pending", AgentRole: "CEO"}
	g.AddTask(task)
	assert.False(t, g.IsComplete())
}

func TestSummary(t *testing.T) {
	g := NewGraph("proj-1")
	t1 := &Task{ID: "t1", Name: "Done", AgentRole: "CEO"}
	g.AddTask(t1)
	t2 := &Task{ID: "t2", Name: "Failed", AgentRole: "CTO"}
	g.AddTask(t2)
	t3 := &Task{ID: "t3", Name: "Pending", AgentRole: "QA"}
	g.AddTask(t3)

	_ = g.MarkRunning("t1")
	_ = g.MarkDone("t1", nil)
	g.Tasks["t2"].Status = StatusFailed

	s := g.Summary()
	assert.Equal(t, 1, s[StatusDone])
	assert.Equal(t, 1, s[StatusFailed])
	assert.Equal(t, 1, s[StatusPending])
}

// =========================================================================
// Cycle Detection (Validate)
// =========================================================================

func TestValidate_NoCycleInDiamond(t *testing.T) {
	g, _, _, _, _ := buildDiamondDAG()
	assert.NoError(t, g.Validate())
}

func TestValidate_DetectsCycle(t *testing.T) {
	g := NewGraph("proj-cycle")
	t1 := &Task{ID: "a", Name: "A", AgentRole: "CEO", DependsOn: []string{"c"}}
	g.AddTask(t1)
	t2 := &Task{ID: "b", Name: "B", AgentRole: "CTO", DependsOn: []string{"a"}}
	g.AddTask(t2)
	t3 := &Task{ID: "c", Name: "C", AgentRole: "QA", DependsOn: []string{"b"}}
	g.AddTask(t3)

	err := g.Validate()
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "cycle")
}

func TestValidate_LinearChainNoCycle(t *testing.T) {
	g := NewGraph("proj-linear")
	for i := 0; i < 10; i++ {
		deps := []string{}
		if i > 0 {
			deps = []string{fmt.Sprintf("t%d", i-1)}
		}
		g.AddTask(&Task{
			ID:        fmt.Sprintf("t%d", i),
			Name:      fmt.Sprintf("Task %d", i),
			AgentRole: "CEO",
			DependsOn: deps,
		})
	}
	assert.NoError(t, g.Validate())
}

// =========================================================================
// Stale Task Recovery
// =========================================================================

func TestRequeueStaleTasks_RequeuesHungTasks(t *testing.T) {
	g := NewGraph("proj-stale")
	task := &Task{ID: "hung", Name: "Hung LLM Call", AgentRole: "CTO", MaxRetries: 3}
	g.AddTask(task)
	_ = g.MarkRunning("hung")

	// Simulate the task started 10 minutes ago
	past := time.Now().Add(-10 * time.Minute)
	g.Tasks["hung"].StartedAt = &past

	retried := g.RequeueStaleTasks(5 * time.Minute)
	assert.Len(t, retried, 1)
	assert.Equal(t, "hung", retried[0])
	assert.Equal(t, StatusPending, g.Tasks["hung"].Status) // Reset for retry
}

func TestRequeueStaleTasks_IgnoresFreshRunning(t *testing.T) {
	g := NewGraph("proj-stale")
	task := &Task{ID: "fresh", Name: "Active Task", AgentRole: "CEO"}
	g.AddTask(task)
	_ = g.MarkRunning("fresh")

	retried := g.RequeueStaleTasks(5 * time.Minute)
	assert.Empty(t, retried)
}

// =========================================================================
// Concurrency Safety
// =========================================================================

func TestConcurrentReadyTasks(t *testing.T) {
	g := NewGraph("proj-concurrent")
	for i := 0; i < 50; i++ {
		g.AddTask(&Task{
			ID:        fmt.Sprintf("t%d", i),
			Name:      fmt.Sprintf("Task %d", i),
			AgentRole: "CEO",
		})
	}

	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ready := g.ReadyTasks()
			assert.Len(t, ready, 50) // All independent, all ready
		}()
	}
	wg.Wait()
}

func TestConcurrentMarkRunningAndDone(t *testing.T) {
	g := NewGraph("proj-concurrent")
	for i := 0; i < 20; i++ {
		g.AddTask(&Task{
			ID:        fmt.Sprintf("t%d", i),
			Name:      fmt.Sprintf("Task %d", i),
			AgentRole: "CEO",
		})
	}

	var wg sync.WaitGroup
	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(id string) {
			defer wg.Done()
			_ = g.MarkRunning(id)
			_ = g.MarkDone(id, map[string]any{"result": "ok"})
		}(fmt.Sprintf("t%d", i))
	}
	wg.Wait()
	assert.True(t, g.IsComplete())
}
