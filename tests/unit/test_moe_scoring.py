"""
Unit Tests - MoE Scoring Engine
Tests cosine similarity, expert ranking, and routing score computation.
"""

import pytest
from moe.scoring import (
    cosine_similarity,
    task_type_to_vector,
    compute_expert_score,
    rank_experts,
    should_use_ensemble,
)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.5, 0.8, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        v1 = [1.0, 0.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0, 0.0]
        assert cosine_similarity(v1, v2) == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector(self):
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 0.5, 0.8]
        assert cosine_similarity(v1, v2) == 0.0

    def test_result_range(self):
        v1 = [0.5, 0.3, 0.9, 0.1]
        v2 = [0.2, 0.8, 0.4, 0.6]
        sim = cosine_similarity(v1, v2)
        assert 0.0 <= sim <= 1.0

    def test_different_length_vectors(self):
        """Shorter vector is padded - no exception raised."""
        v1 = [1.0, 0.5]
        v2 = [1.0, 0.5, 0.8]
        # Should not raise
        result = cosine_similarity(v1, v2)
        assert 0.0 <= result <= 1.0


class TestTaskTypeToVector:
    def test_strategy_task(self):
        v = task_type_to_vector("strategy")
        # Strategy dimension [0] should be high
        assert v[0] > 0.5

    def test_backend_task(self):
        v = task_type_to_vector("backend_code")
        # Backend dimension [2] should be high
        assert v[2] > 0.5

    def test_frontend_task(self):
        v = task_type_to_vector("frontend_code")
        # Frontend dimension [3] should be high
        assert v[3] > 0.5

    def test_devops_task(self):
        v = task_type_to_vector("deployment")
        # DevOps dimension [5] should be high
        assert v[5] > 0.5

    def test_unknown_task_uniform(self):
        """Unknown task type should produce uniform vector."""
        v = task_type_to_vector("totally_unknown_xyz")
        assert all(abs(x - 0.125) < 1e-6 for x in v)

    def test_context_enrichment(self):
        """Context should boost relevant dimensions."""
        v_no_ctx = task_type_to_vector("code_review")
        v_with_ctx = task_type_to_vector(
            "code_review", context="python fastapi sqlalchemy"
        )
        # Backend dimension should be higher with context
        assert v_with_ctx[2] >= v_no_ctx[2]


class TestComputeExpertScore:
    def test_perfect_match_idle_expert(self):
        """Expert with identical vector and no load should score high."""
        task_v = [0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        expert_v = [0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        score, breakdown = compute_expert_score(
            task_vector=task_v,
            expert_vector=expert_v,
            load_factor=0.0,
            success_rate=1.0,
            avg_cost_usd=0.01,
        )
        assert score > 0.8
        assert breakdown["similarity"] == pytest.approx(1.0, abs=1e-4)
        assert breakdown["load"] == pytest.approx(1.0, abs=1e-4)

    def test_overloaded_expert_penalized(self):
        """Expert at full capacity should score lower."""
        task_v = [0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        expert_v = [0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        score_idle, _ = compute_expert_score(task_v, expert_v, 0.0, 1.0, 0.01)
        score_full, _ = compute_expert_score(task_v, expert_v, 1.0, 1.0, 0.01)
        assert score_idle > score_full

    def test_score_in_range(self):
        task_v = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        expert_v = [0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.1, 0.9]
        score, _ = compute_expert_score(task_v, expert_v, 0.5, 0.8, 0.05)
        assert 0.0 <= score <= 1.0


class TestRankExperts:
    @pytest.fixture
    def sample_experts(self):
        return {
            "CEO": {"vector": [0.9, 0.4, 0.1, 0.1, 0.1, 0.1, 0.6, 0.4]},
            "CTO": {"vector": [0.5, 0.9, 0.5, 0.3, 0.4, 0.6, 0.7, 0.8]},
            "Engineer_Backend": {"vector": [0.1, 0.4, 0.9, 0.1, 0.6, 0.4, 0.3, 0.5]},
        }

    @pytest.fixture
    def sample_stats(self):
        return {
            "CEO": {"load_factor": 0.0, "success_rate": 1.0, "avg_cost_usd": 0.03},
            "CTO": {"load_factor": 0.3, "success_rate": 0.95, "avg_cost_usd": 0.05},
            "Engineer_Backend": {
                "load_factor": 0.8,
                "success_rate": 0.90,
                "avg_cost_usd": 0.08,
            },
        }

    def test_strategy_task_selects_ceo(self, sample_experts, sample_stats):
        task_v = task_type_to_vector("strategy")
        rankings = rank_experts(task_v, sample_experts, sample_stats)
        assert len(rankings) > 0
        top_role = rankings[0][0]
        assert top_role == "CEO"

    def test_backend_task_selects_engineer(self, sample_experts, sample_stats):
        task_v = task_type_to_vector("backend_code")
        # Engineer_Backend is loaded (0.8) but should still be top for backend
        stats_low_load = {**sample_stats}
        stats_low_load["Engineer_Backend"] = {
            "load_factor": 0.1,
            "success_rate": 0.95,
            "avg_cost_usd": 0.05,
        }
        rankings = rank_experts(task_v, sample_experts, stats_low_load)
        assert rankings[0][0] == "Engineer_Backend"

    def test_overloaded_excluded(self, sample_experts, sample_stats):
        # Set all engineers to 100% load
        stats_full = {
            "CEO": {"load_factor": 0.0, "success_rate": 1.0, "avg_cost_usd": 0.03},
            "CTO": {"load_factor": 1.0, "success_rate": 0.95, "avg_cost_usd": 0.05},
            "Engineer_Backend": {
                "load_factor": 1.0,
                "success_rate": 0.90,
                "avg_cost_usd": 0.08,
            },
        }
        task_v = task_type_to_vector("backend_code")
        rankings = rank_experts(
            task_v, sample_experts, stats_full, exclude_overloaded=True
        )

        # These should be excluded
        assert "CTO" not in [r[0] for r in rankings]
        assert "Engineer_Backend" not in [r[0] for r in rankings]

    def test_sorted_descending(self, sample_experts, sample_stats):
        task_v = task_type_to_vector("architecture")
        rankings = rank_experts(task_v, sample_experts, sample_stats)
        scores = [r[1] for r in rankings]
        assert scores == sorted(scores, reverse=True)


class TestEnsemble:
    def test_ensemble_triggered_close_scores(self):
        assert should_use_ensemble(0.75, 0.72) is True  # Gap < 0.10

    def test_ensemble_triggered_low_confidence(self):
        assert should_use_ensemble(0.60, 0.40) is True  # Top < threshold

    def test_no_ensemble_clear_winner(self):
        assert should_use_ensemble(0.95, 0.60) is False  # Clear winner, high confidence
