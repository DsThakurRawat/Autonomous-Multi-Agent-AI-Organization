/// Task-type → 8-dimensional capability vector.
/// Direct port of moe/scoring.py::task_type_to_vector()
///
/// Dimensions:
///   0 = strategy         1 = architecture
///   2 = backend_code     3 = frontend_code
///   4 = testing          5 = devops
///   6 = cost_optimization 7 = security

pub const VECTOR_DIM: usize = 8;

pub fn task_type_to_vector(task_type: &str, context: &str) -> Vec<f64> {
    let t = task_type.to_lowercase();
    let c = context.to_lowercase();

    let mut v = vec![0.0f64; VECTOR_DIM];

    // ── [0] Strategy ─────────────────────────────────────────────────────────
    if contains_any(&t, &["strategy", "plan", "vision", "market", "mvp", "business"]) {
        v[0] = 0.9;
    }
    if contains_any(&c, &["strategy", "market", "business"]) {
        v[0] = v[0].max(0.5);
    }

    // ── [1] Architecture ─────────────────────────────────────────────────────
    if contains_any(&t, &["architect", "design", "schema", "tech_stack", "system"]) {
        v[1] = 0.9;
    }
    if contains_any(&c, &["architect", "api", "database"]) {
        v[1] = v[1].max(0.5);
    }

    // ── [2] Backend Code ─────────────────────────────────────────────────────
    if contains_any(&t, &["backend", "api", "fastapi", "database", "orm", "auth"]) {
        v[2] = 0.9;
    }
    if contains_any(&c, &["python", "fastapi", "sqlalchemy", "postgres"]) {
        v[2] = v[2].max(0.6);
    }

    // ── [3] Frontend Code ─────────────────────────────────────────────────────
    if contains_any(&t, &["frontend", "ui", "react", "nextjs", "component", "page"]) {
        v[3] = 0.9;
    }
    if contains_any(&c, &["typescript", "next.js", "tailwind", "css"]) {
        v[3] = v[3].max(0.6);
    }

    // ── [4] Testing ───────────────────────────────────────────────────────────
    if contains_any(&t, &["test", "qa", "security_scan", "coverage", "validation"]) {
        v[4] = 0.9;
    }
    if contains_any(&c, &["pytest", "unittest", "bandit", "security"]) {
        v[4] = v[4].max(0.6);
    }

    // ── [5] DevOps ────────────────────────────────────────────────────────────
    if contains_any(&t, &["devops", "deploy", "terraform", "docker", "kubernetes", "ci_cd"]) {
        v[5] = 0.9;
    }
    if contains_any(&c, &["aws", "ecs", "k8s", "helm", "infra"]) {
        v[5] = v[5].max(0.6);
    }

    // ── [6] Cost Optimization ─────────────────────────────────────────────────
    if contains_any(&t, &["cost", "finance", "budget", "price", "optimization"]) {
        v[6] = 0.9;
    }
    if contains_any(&c, &["cost", "budget", "spend", "usd", "savings"]) {
        v[6] = v[6].max(0.5);
    }

    // ── [7] Security ──────────────────────────────────────────────────────────
    if contains_any(&t, &["security", "iam", "auth", "permission", "audit"]) {
        v[7] = 0.9;
    }
    if contains_any(&c, &["vulnerability", "injection", "xss", "csrf", "secret"]) {
        v[7] = v[7].max(0.5);
    }

    // If all zeros (unknown task) → uniform distribution
    if v.iter().all(|&x| x == 0.0) {
        v = vec![0.125; VECTOR_DIM];
    }

    v
}

#[inline]
fn contains_any(haystack: &str, needles: &[&str]) -> bool {
    needles.iter().any(|n| haystack.contains(n))
}

// ── Built-in Expert Capability Vectors ───────────────────────────────────────
// Mirrors moe/expert_registry.py

use crate::models::Expert;
use std::collections::HashMap;

pub fn default_experts() -> HashMap<String, Expert> {
    let experts = vec![
        (
            "CEO",
            vec![0.9, 0.3, 0.1, 0.1, 0.1, 0.2, 0.6, 0.3],
            vec!["strategy", "vision", "decision_making", "risk_assessment"],
        ),
        (
            "CTO",
            vec![0.3, 0.95, 0.5, 0.4, 0.3, 0.5, 0.3, 0.5],
            vec!["architecture", "tech_stack", "system_design", "api_design"],
        ),
        (
            "Engineer_Backend",
            vec![0.1, 0.4, 0.95, 0.1, 0.4, 0.3, 0.2, 0.4],
            vec![
                "backend",
                "api",
                "database",
                "orm",
                "authentication",
                "fastapi",
            ],
        ),
        (
            "Engineer_Frontend",
            vec![0.1, 0.3, 0.1, 0.95, 0.3, 0.1, 0.1, 0.2],
            vec!["frontend", "react", "nextjs", "typescript", "ui", "css"],
        ),
        (
            "QA",
            vec![0.1, 0.2, 0.3, 0.3, 0.95, 0.2, 0.1, 0.6],
            vec!["testing", "qa", "coverage", "security_scan", "validation"],
        ),
        (
            "DevOps",
            vec![0.2, 0.4, 0.3, 0.1, 0.3, 0.95, 0.4, 0.5],
            vec![
                "devops",
                "terraform",
                "docker",
                "kubernetes",
                "ci_cd",
                "deploy",
            ],
        ),
        (
            "Finance",
            vec![0.4, 0.1, 0.1, 0.1, 0.1, 0.2, 0.95, 0.3],
            vec!["cost", "budget", "finance", "optimization", "pricing"],
        ),
    ];

    experts
        .into_iter()
        .map(|(role, vector, skills)| {
            (
                role.to_string(),
                Expert {
                    role: role.to_string(),
                    vector,
                    skills: skills.iter().map(|s| s.to_string()).collect(),
                },
            )
        })
        .collect()
}

// ── Direct Task-Type → Expert Mapping (O(1) lookup) ──────────────────────────

pub fn direct_expert_for_task_type(task_type: &str) -> Option<&'static str> {
    match task_type.to_lowercase().as_str() {
        "strategy" | "business_plan" | "market_analysis" | "mvp_definition" => Some("CEO"),
        "architecture" | "tech_stack_selection" | "api_design" | "database_design" => Some("CTO"),
        "backend_development" | "api_implementation" | "database_setup" | "auth_implementation" => {
            Some("Engineer_Backend")
        }
        "frontend_development" | "ui_implementation" | "component_development" => {
            Some("Engineer_Frontend")
        }
        "qa_testing" | "security_scan" | "performance_testing" | "test_coverage" => Some("QA"),
        "infrastructure_setup" | "ci_cd_pipeline" | "deployment" | "monitoring_setup" => {
            Some("DevOps")
        }
        "cost_analysis" | "budget_optimization" | "cost_report" => Some("Finance"),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strategy_vector() {
        let v = task_type_to_vector("business_strategy", "market analysis");
        assert!(v[0] > 0.8, "strategy dim should be high");
    }

    #[test]
    fn test_unknown_task_uniform() {
        let v = task_type_to_vector("xyzzy_unknown", "");
        assert!(
            v.iter().all(|&x| (x - 0.125).abs() < 1e-9),
            "unknown -> uniform"
        );
    }

    #[test]
    fn test_default_experts_count() {
        let experts = default_experts();
        assert_eq!(experts.len(), 7);
    }

    #[test]
    fn test_direct_mapping() {
        assert_eq!(direct_expert_for_task_type("strategy"), Some("CEO"));
        assert_eq!(direct_expert_for_task_type("deployment"), Some("DevOps"));
        assert_eq!(direct_expert_for_task_type("unknown_xyz"), None);
    }
}
