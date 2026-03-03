/// Scoring engine — direct port of moe/scoring.py with f64 SIMD-friendly ops.
use crate::models::{Expert, ExpertScore, ExpertStats};

// ── Scoring Weights (must sum to 1.0) ─────────────────────────────────────────
const WEIGHT_SIMILARITY: f64 = 0.40;
const WEIGHT_LOAD:       f64 = 0.25;
const WEIGHT_SUCCESS:    f64 = 0.20;
const WEIGHT_COST:       f64 = 0.15;

/// Confidence threshold — below this, trigger ensemble mode
pub const ENSEMBLE_THRESHOLD: f64 = 0.70;

// ── Cosine Similarity ─────────────────────────────────────────────────────────

/// Compute cosine similarity between two f64 vectors.
/// Returns value in [0.0, 1.0]. Returns 0.0 for zero vectors.
pub fn cosine_similarity(a: &[f64], b: &[f64]) -> f64 {
    let len = a.len().min(b.len());
    let (a, b) = (&a[..len], &b[..len]);

    let dot: f64   = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
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
    task_vector:   &[f64],
    expert_vector: &[f64],
    load_factor:    f64,
    success_rate:   f64,
    avg_cost_usd:   f64,
    max_cost_usd:   f64,
) -> ExpertScore {
    let sim_score  = cosine_similarity(task_vector, expert_vector);
    let load_score = 1.0 - load_factor;                                  // prefer idle
    let cost_factor = (avg_cost_usd / max_cost_usd.max(1e-9)).min(1.0);
    let cost_score  = 1.0 - cost_factor;                                 // prefer cheap

    let composite =
        WEIGHT_SIMILARITY * sim_score    +
        WEIGHT_LOAD       * load_score   +
        WEIGHT_SUCCESS    * success_rate +
        WEIGHT_COST       * cost_score;

    ExpertScore {
        role:       String::new(), // filled by caller
        composite:  round4(composite),
        similarity: round4(sim_score),
        load:       round4(load_score),
        success:    round4(success_rate),
        cost:       round4(cost_score),
    }
}

/// Round to 4 decimal places.
#[inline]
fn round4(v: f64) -> f64 { (v * 10_000.0).round() / 10_000.0 }

// ── Rank All Experts ──────────────────────────────────────────────────────────

/// Score and sort all experts for the given task vector.
/// Returns list sorted by composite score descending.
pub fn rank_experts(
    task_vector:        &[f64],
    experts:            &[(String, Expert)],
    stats:              &std::collections::HashMap<String, ExpertStats>,
    exclude_overloaded:  bool,
) -> Vec<ExpertScore> {
    let max_cost_usd: f64 = stats.values()
        .map(|s| s.avg_cost_usd)
        .fold(0.10_f64, f64::max);

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
                stat.load_factor,
                stat.success_rate,
                stat.avg_cost_usd,
                max_cost_usd,
            );
            score.role = role.clone();
            Some(score)
        })
        .collect();

    // Sort descending by composite score
    scores.sort_by(|a, b| b.composite.partial_cmp(&a.composite).unwrap_or(std::cmp::Ordering::Equal));
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

    #[test]
    fn test_cosine_identical() {
        let v = vec![1.0, 0.0, 0.5, 0.0];
        assert!((cosine_similarity(&v, &v) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_cosine_orthogonal() {
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
    fn test_expert_score_weights_sum() {
        assert!((WEIGHT_SIMILARITY + WEIGHT_LOAD + WEIGHT_SUCCESS + WEIGHT_COST - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_ensemble_trigger() {
        assert!(should_use_ensemble(0.65, 0.60));   // below threshold
        assert!(should_use_ensemble(0.80, 0.75));   // gap < 0.10
        assert!(!should_use_ensemble(0.90, 0.75));  // high confidence, big gap
    }
}
