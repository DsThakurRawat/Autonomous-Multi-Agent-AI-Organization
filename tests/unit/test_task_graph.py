"""
Unit Tests - Task Graph Engine
Tests DAG construction, dependency resolution, cycle detection,
parallel task readiness, and status tracking.
"""

import pytest
from orchestrator.task_graph import (
    Task,
    TaskGraph,
    TaskStatus,
    build_standard_task_graph,
)


class TestTask:
    def test_task_defaults(self):
        task = Task(name="Test", description="Test task", agent_role="CEO")
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.id is not None

    def test_can_retry_when_under_limit(self):
        task = Task(
            name="T", description="", agent_role="CEO", retry_count=2, max_retries=3
        )
        assert task.can_retry() is True

    def test_cannot_retry_at_limit(self):
        task = Task(
            name="T", description="", agent_role="CEO", retry_count=3, max_retries=3
        )
        assert task.can_retry() is False

    def test_mark_completed(self):
        task = Task(name="T", description="", agent_role="CEO")
        task.mark_completed({"result": "done"})
        assert task.status == TaskStatus.COMPLETED
        assert task.output_data == {"result": "done"}
        assert task.completed_at is not None

    def test_mark_failed(self):
        task = Task(name="T", description="", agent_role="CEO")
        task.mark_failed("Connection refused")
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Connection refused"

    def test_duration_seconds(self):
        task = Task(name="T", description="", agent_role="CEO")
        task.mark_started()
        task.mark_completed({})
        assert task.duration_seconds is not None
        assert task.duration_seconds >= 0


class TestTaskGraph:
    def _make_graph(self) -> TaskGraph:
        return TaskGraph(project_id="test-project")

    def test_add_single_task(self):
        graph = self._make_graph()
        task = Task(name="Task1", description="", agent_role="CEO")
        tid = graph.add_task(task)
        assert tid == task.id
        assert tid in graph.tasks

    def test_dependency_edge_created(self):
        graph = self._make_graph()
        t1 = Task(name="T1", description="", agent_role="CEO")
        t1_id = graph.add_task(t1)
        t2 = Task(name="T2", description="", agent_role="CTO", dependencies=[t1_id])
        graph.add_task(t2)
        assert graph.graph.has_edge(t1_id, t2.id)

    def test_cycle_detection(self):
        """Manually introduced cycles are detectable via networkx DAG check."""
        import networkx as nx

        graph = self._make_graph()
        t1 = Task(name="T1", description="", agent_role="CEO")
        t1_id = graph.add_task(t1)
        t2 = Task(name="T2", description="", agent_role="CTO", dependencies=[t1_id])
        t2_id = graph.add_task(t2)
        # Valid DAG at this point
        assert nx.is_directed_acyclic_graph(graph.graph) is True
        # Manually add a back-edge to create a cycle
        graph.graph.add_edge(t2_id, t1_id)
        # Now the DAG check should detect the cycle
        assert nx.is_directed_acyclic_graph(graph.graph) is False

    def test_missing_dependency_raises(self):
        """Adding a task with a non-existent dependency ID should raise ValueError."""
        graph = self._make_graph()
        t = Task(
            name="T", description="", agent_role="CEO", dependencies=["nonexistent-id"]
        )
        with pytest.raises(ValueError, match="not found"):
            graph.add_task(t)

    def test_get_ready_tasks_no_deps(self):
        """Tasks with no dependencies should be immediately ready."""
        graph = self._make_graph()
        t1 = Task(name="T1", description="", agent_role="CEO")
        t2 = Task(name="T2", description="", agent_role="CTO")
        graph.add_task(t1)
        graph.add_task(t2)
        ready = graph.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_tasks_with_deps(self):
        """Task with pending dependency should NOT be ready."""
        graph = self._make_graph()
        t1 = Task(name="T1", description="", agent_role="CEO")
        t1_id = graph.add_task(t1)
        t2 = Task(name="T2", description="", agent_role="CTO", dependencies=[t1_id])
        graph.add_task(t2)

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "T1"

    def test_get_ready_after_dep_complete(self):
        """After dependency completes, dependent task should become ready."""
        graph = self._make_graph()
        t1 = Task(name="T1", description="", agent_role="CEO")
        t1_id = graph.add_task(t1)
        t2 = Task(name="T2", description="", agent_role="CTO", dependencies=[t1_id])
        graph.add_task(t2)

        t1.mark_completed({})
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "T2"

    def test_parallel_tasks(self):
        """Two tasks with same dependency should both be ready when dep completes."""
        graph = self._make_graph()
        t1 = Task(name="Root", description="", agent_role="CEO")
        t1_id = graph.add_task(t1)
        t2 = Task(
            name="Branch1",
            description="",
            agent_role="Engineer_Backend",
            dependencies=[t1_id],
        )
        t3 = Task(
            name="Branch2",
            description="",
            agent_role="Engineer_Frontend",
            dependencies=[t1_id],
        )
        graph.add_task(t2)
        graph.add_task(t3)

        t1.mark_completed({})
        ready = graph.get_ready_tasks()
        assert len(ready) == 2

    def test_is_complete_all_done(self):
        graph = self._make_graph()
        t = Task(name="T", description="", agent_role="CEO")
        graph.add_task(t)
        t.mark_completed({})
        assert graph.is_complete() is True

    def test_is_complete_some_pending(self):
        graph = self._make_graph()
        t = Task(name="T", description="", agent_role="CEO")
        graph.add_task(t)
        assert graph.is_complete() is False

    def test_status_summary(self):
        graph = self._make_graph()
        t1 = Task(name="T1", description="", agent_role="CEO")
        t2 = Task(name="T2", description="", agent_role="CTO")
        graph.add_task(t1)
        graph.add_task(t2)
        t1.mark_completed({})
        summary = graph.get_status_summary()
        assert summary["total"] == 2
        assert summary["completed"] == 1
        assert summary["pending"] == 1
        assert summary["progress_pct"] == 50.0

    def test_to_dict_structure(self):
        graph = self._make_graph()
        t = Task(name="T", description="Test", agent_role="CEO")
        graph.add_task(t)
        d = graph.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "summary" in d
        assert len(d["nodes"]) == 1


class TestBuildStandardTaskGraph:
    def test_standard_graph_has_expected_tasks(self):
        graph = build_standard_task_graph(
            "proj-123", {"estimated_monthly_cost_usd": 95}
        )
        assert len(graph.tasks) >= 5  # At least setup, backend, frontend, qa, deploy

    def test_standard_graph_is_dag(self):
        """The standard task graph must be acyclic."""
        import networkx as nx

        graph = build_standard_task_graph("proj-123", {})
        assert nx.is_directed_acyclic_graph(graph.graph)

    def test_first_tasks_have_no_deps(self):
        graph = build_standard_task_graph("proj-123", {})
        ready = graph.get_ready_tasks()
        assert len(ready) >= 1  # At least repo setup should be immediately ready
