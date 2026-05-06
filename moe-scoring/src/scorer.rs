use crate::models::{Expert, ExpertScore, ExpertStats, Strategy};

/// Confidence threshold — below this, trigger ensemble mode
pub const ENSEMBLE_THRESHOLD: f64 = 0.70;

/// Scoring weights based on the selected strategy.
#[derive(Debug, Clone, Copy)]
struct ScoringWeights {
    similarity: f64,
    load: f64,
    success: f64,
    cost: f64,
    latency: f64,
}

impl ScoringWeights {
    fn from_strategy(strategy: Strategy) -> Self {
        match strategy {
            Strategy::Balanced => Self {
                similarity: 0.35,
                load: 0.20,
                success: 0.20,
                cost: 0.15,
                latency: 0.10,
            },
            Strategy::Performance => Self {
                similarity: 0.30,
                load: 0.10,
                success: 0.30,
                cost: 0.05,
                latency: 0.25,
            },
            Strategy::CostSaver => Self {
                similarity: 0.30,
                load: 0.20,
                success: 0.10,
                cost: 0.35,
                latency: 0.05,
            },
        }
    }
}

// ── Cosine Similarity ─────────────────────────────────────────────────────────

/// Compute cosine similarity between two f64 vectors.
/// Returns value in [0.0, 1.0]. Returns 0.0 for zero vectors.
pub fn cosine_similarity(a: &[f64], b: &[f64]) -> f64 {
    let len = a.len().min(b.len());
    let (a, b) = (&a[..len], &b[..len]);

    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let mag_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let mag_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();

    if mag_a < f64::EPSILON || mag_b < f64::EPSILON {
        return 0.0;
    }

    (dot / (mag_a * mag_b)).clamp(0.0, 1.0)
}

// ── Expert Scoring ────────────────────────────────────────────────────────────

/// Compute composite routing score for a single expert.
pub fn compute_expert_score(
    task_vector: &[f64],
    expert_vector: &[f64],
    stat: &ExpertStats,
    max_cost_usd: f64,
    max_latency_ms: f64,
    strategy: Strategy,
) -> ExpertScore {
    let weights = ScoringWeights::from_strategy(strategy);

    let sim_score = cosine_similarity(task_vector, expert_vector);
    let load_score = 1.0 - stat.load_factor; // prefer idle

    // Non-linear cost penalty (penalize expensive models more aggressively)
    let cost_ratio = (stat.avg_cost_usd / max_cost_usd.max(1e-9)).min(1.0);
    let cost_score = (1.0 - cost_ratio).powi(2);

    // Latency score (prefer faster response)
    let latency_ratio = (stat.p95_latency_ms / max_latency_ms.max(1e-9)).min(1.0);
    let latency_score = 1.0 - latency_ratio;

    let composite = weights.similarity * sim_score
        + weights.load * load_score
        + weights.success * stat.success_rate
        + weights.cost * cost_score
        + weights.latency * latency_score;

    ExpertScore {
        role: String::new(), // filled by caller
        composite: round4(composite),
        similarity: round4(sim_score),
        load: round4(load_score),
        success: round4(stat.success_rate),
        cost: round4(cost_score),
        latency: round4(latency_score),
    }
}

/// Round to 4 decimal places.
#[inline]
fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

// ── Rank All Experts ──────────────────────────────────────────────────────────

/// Score and sort all experts for the given task vector.
/// Returns list sorted by composite score descending.
pub fn rank_experts(
    task_vector: &[f64],
    experts: &[(String, Expert)],
    stats: &std::collections::HashMap<String, ExpertStats>,
    exclude_overloaded: bool,
    strategy: Strategy,
) -> Vec<ExpertScore> {
    let max_cost_usd: f64 = stats
        .values()
        .map(|s| s.avg_cost_usd)
        .fold(0.10_f64, f64::max);

    let max_latency_ms: f64 = stats
        .values()
        .map(|s| s.p95_latency_ms)
        .fold(500.0_f64, f64::max);

    let mut scores: Vec<ExpertScore> = experts
        .iter()
        .filter_map(|(role, expert)| {
            let stat = stats.get(role).cloned().unwrap_or_default();

            if exclude_overloaded && stat.load_factor >= 1.0 {
                return None;
            }

            let mut score = compute_expert_score(
                task_vector,
                &expert.vector,
                &stat,
                max_cost_usd,
                max_latency_ms,
                strategy,
            );
            score.role = role.clone();
            Some(score)
        })
        .collect();

    // Sort descending by composite score
    scores.sort_by(|a, b| {
        b.composite
            .partial_cmp(&a.composite)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    scores
}

// ── Ensemble Decision ─────────────────────────────────────────────────────────

/// Returns true if top two experts are close enough to warrant ensemble.
pub fn should_use_ensemble(top_score: f64, second_score: f64) -> bool {
    let gap = top_score - second_score;
    top_score < ENSEMBLE_THRESHOLD || gap < 0.10
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{Expert, ExpertStats, Strategy};
    use std::collections::HashMap;

    // ── Cosine Similarity ────────────────────────────────────────────────

    #[test]
    fn test_cosine_identical_vectors() {
        let v = vec![1.0, 0.0, 0.5, 0.0];
        assert!((cosine_similarity(&v, &v) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_cosine_orthogonal_vectors() {
        let a = vec![1.0, 0.0, 0.0, 0.0];
        let b = vec![0.0, 1.0, 0.0, 0.0];
        assert_eq!(cosine_similarity(&a, &b), 0.0);
    }

    #[test]
    fn test_cosine_zero_vector() {
        let a = vec![0.0, 0.0, 0.0];
        let b = vec![1.0, 0.5, 0.3];
        assert_eq!(cosine_similarity(&a, &b), 0.0);
    }

    #[test]
    fn test_cosine_opposite_vectors() {
        let a = vec![1.0, 0.0];
        let b = vec![-1.0, 0.0];
        // Clamped to [0.0, 1.0] so negative similarity becomes 0
        assert_eq!(cosine_similarity(&a, &b), 0.0);
    }

    #[test]
    fn test_cosine_partial_overlap() {
        let a = vec![1.0, 1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0, 0.0];
        let sim = cosine_similarity(&a, &b);
        // cos(45°) ≈ 0.707
        assert!((sim - 0.7071).abs() < 0.01);
    }

    #[test]
    fn test_cosine_different_lengths_truncated() {
        let a = vec![1.0, 0.0, 0.5];
        let b = vec![1.0, 0.0]; // Only 2 dims
        let sim = cosine_similarity(&a, &b);
        // Should use min(3,2)=2 dimensions → both are [1,0] → sim=1.0
        assert!((sim - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_perfect_expert_gets_max_score() {
        let stat = ExpertStats {
            load_factor: 0.0,
            success_rate: 1.0,
            avg_cost_usd: 0.01,
            p95_latency_ms: 50.0,
        };
        let score = compute_expert_score(
            &vec![1.0, 0.0, 0.0, 0.0], // task vector
            &vec![1.0, 0.0, 0.0, 0.0], // identical expert vector
            &stat,
            0.10,  // max cost range
            500.0, // max latency range
            Strategy::Balanced,
        );
        // sim=1.0, load=1.0, success=1.0, cost≈0.9, latency≈0.9 → high composite
        assert!(
            score.composite > 0.9,
            "Perfect expert should score >0.9, got {}",
            score.composite
        );
    }

    #[test]
    fn test_overloaded_expert_gets_low_score() {
        let stat_loaded = ExpertStats {
            load_factor: 1.0,
            success_rate: 1.0,
            avg_cost_usd: 0.01,
            p95_latency_ms: 100.0,
        };
        let stat_idle = ExpertStats {
            load_factor: 0.0,
            success_rate: 1.0,
            avg_cost_usd: 0.01,
            p95_latency_ms: 100.0,
        };

        let score_loaded = compute_expert_score(
            &vec![1.0, 0.0, 0.0, 0.0],
            &vec![1.0, 0.0, 0.0, 0.0],
            &stat_loaded,
            0.10,
            500.0,
            Strategy::Balanced,
        );
        let score_idle = compute_expert_score(
            &vec![1.0, 0.0, 0.0, 0.0],
            &vec![1.0, 0.0, 0.0, 0.0],
            &stat_idle,
            0.10,
            500.0,
            Strategy::Balanced,
        );
        assert!(
            score_loaded.composite < score_idle.composite,
            "Overloaded expert should score lower than idle one"
        );
    }

    // ── Expert Ranking ───────────────────────────────────────────────────

    fn build_test_experts() -> Vec<(String, Expert)> {
        vec![
            (
                "CTO".to_string(),
                Expert {
                    role: "CTO".to_string(),
                    vector: vec![0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    skills: vec!["architecture".to_string()],
                },
            ),
            (
                "Engineer_Backend".to_string(),
                Expert {
                    role: "Engineer_Backend".to_string(),
                    vector: vec![0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    skills: vec!["backend".to_string()],
                },
            ),
            (
                "DevOps".to_string(),
                Expert {
                    role: "DevOps".to_string(),
                    vector: vec![0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                    skills: vec!["devops".to_string()],
                },
            ),
        ]
    }

    fn build_test_stats() -> HashMap<String, ExpertStats> {
        let mut stats = HashMap::new();
        stats.insert(
            "CTO".to_string(),
            ExpertStats {
                load_factor: 0.3,
                success_rate: 0.95,
                avg_cost_usd: 0.08,
                p95_latency_ms: 300.0,
            },
        );
        stats.insert(
            "Engineer_Backend".to_string(),
            ExpertStats {
                load_factor: 0.5,
                success_rate: 0.90,
                avg_cost_usd: 0.05,
                p95_latency_ms: 200.0,
            },
        );
        stats.insert(
            "DevOps".to_string(),
            ExpertStats {
                load_factor: 0.1,
                success_rate: 0.98,
                avg_cost_usd: 0.03,
                p95_latency_ms: 100.0,
            },
        );
        stats
    }

    #[test]
    fn test_rank_experts_returns_sorted() {
        let experts = build_test_experts();
        let stats = build_test_stats();
        let task_vec = vec![0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; // architecture

        let rankings = rank_experts(&task_vec, &experts, &stats, false, Strategy::Balanced);
        assert!(!rankings.is_empty());
        // CTO should be ranked first (perfect vector match for architecture)
        assert_eq!(rankings[0].role, "CTO");
    }

    #[test]
    fn test_rank_experts_excludes_overloaded() {
        let experts = build_test_experts();
        let mut stats = build_test_stats();
        stats.get_mut("CTO").unwrap().load_factor = 1.0; // Saturated

        let task_vec = vec![0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];

        let rankings = rank_experts(&task_vec, &experts, &stats, true, Strategy::Balanced);
        assert!(
            rankings.iter().all(|r| r.role != "CTO"),
            "Overloaded CTO should be excluded"
        );
    }

    #[test]
    fn test_rank_experts_includes_overloaded_when_not_excluded() {
        let experts = build_test_experts();
        let mut stats = build_test_stats();
        stats.get_mut("CTO").unwrap().load_factor = 1.0;

        let task_vec = vec![0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];

        let rankings = rank_experts(&task_vec, &experts, &stats, false, Strategy::Balanced);
        assert!(
            rankings.iter().any(|r| r.role == "CTO"),
            "Overloaded CTO should still appear when exclusion is off"
        );
    }

    // ── Ensemble Decision ────────────────────────────────────────────────

    #[test]
    fn test_ensemble_trigger_below_threshold() {
        assert!(should_use_ensemble(0.65, 0.60)); // below ENSEMBLE_THRESHOLD
    }

    #[test]
    fn test_ensemble_trigger_close_gap() {
        assert!(should_use_ensemble(0.80, 0.75)); // gap < 0.10
    }

    #[test]
    fn test_no_ensemble_high_confidence_big_gap() {
        assert!(!should_use_ensemble(0.90, 0.75)); // confident, big gap
    }

    #[test]
    fn test_ensemble_boundary_exact_threshold() {
        // At exactly ENSEMBLE_THRESHOLD, top_score < threshold is false
        assert!(!should_use_ensemble(
            ENSEMBLE_THRESHOLD,
            ENSEMBLE_THRESHOLD - 0.15
        ));
    }

    #[test]
    fn test_ensemble_boundary_large_gap() {
        // Gap 0.90-0.75 = 0.15     → clearly >= 0.10 → should NOT trigger
        assert!(!should_use_ensemble(0.90, 0.75));
    }
}
