use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── Expert Definition ─────────────────────────────────────────────────────────

/// Capability vector dimensions:
/// [strategy, architecture, backend_code, frontend_code,
///  testing, devops, cost_optimization, security]
#[allow(dead_code)]
pub const VECTOR_DIM: usize = 8;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExpertStats {
    /// 0.0 (idle) → 1.0 (saturated)
    pub load_factor: f64,
    /// 0.0 → 1.0
    pub success_rate: f64,
    /// Average USD cost per task
    pub avg_cost_usd: f64,
}

impl Default for ExpertStats {
    fn default() -> Self {
        Self {
            load_factor: 0.0,
            success_rate: 1.0,
            avg_cost_usd: 0.05,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Expert {
    pub role: String,
    pub vector: Vec<f64>,
    pub skills: Vec<String>,
}

// ── Route Request ─────────────────────────────────────────────────────────────

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct RouteRequest {
    pub task_id: String,
    pub task_type: String,
    pub task_name: String,
    pub project_id: String,
    #[serde(default)]
    pub input_context: String,
    #[serde(default)]
    pub required_skills: Vec<String>,
    #[serde(default = "default_priority")]
    pub priority: String,
    #[serde(default)]
    pub force_ensemble: bool,
    #[serde(default)]
    pub trace_id: String,
    /// If provided, use these expert definitions (dynamic); otherwise use built-ins
    pub experts: Option<HashMap<String, Expert>>,
    pub stats: Option<HashMap<String, ExpertStats>>,
}

fn default_priority() -> String {
    "medium".to_string()
}

// ── Route Response ────────────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct ExpertScore {
    pub role: String,
    pub composite: f64,
    pub similarity: f64,
    pub load: f64,
    pub success: f64,
    pub cost: f64,
}

#[derive(Debug, Serialize)]
pub struct RouteResponse {
    pub task_id: String,
    pub selected_expert: String,
    pub fallback_experts: Vec<String>,
    pub routing_score: f64,
    pub confidence: f64,
    pub ensemble_mode: bool,
    pub routing_type: String, // "direct" | "scored"
    pub routing_reason: String,
    pub all_scores: Vec<ExpertScore>,
    pub routing_ms: f64,
    pub trace_id: String,
}

// ── Batch Request / Response ──────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
pub struct BatchRouteRequest {
    pub tasks: Vec<RouteRequest>,
    pub experts: Option<HashMap<String, Expert>>,
    pub stats: Option<HashMap<String, ExpertStats>>,
}

#[derive(Debug, Serialize)]
pub struct BatchRouteResponse {
    pub decisions: Vec<RouteResponse>,
    pub total_ms: f64,
}

// ── Health ────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub version: &'static str,
    pub uptime_seconds: u64,
}

// ── Vectorize ─────────────────────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
pub struct VectorizeRequest {
    #[serde(default)]
    pub task_type: String,
    #[serde(default)]
    pub context: String,
}

// ── Error ─────────────────────────────────────────────────────────────────────

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
    pub task_id: Option<String>,
}
