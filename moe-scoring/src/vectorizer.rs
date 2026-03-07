use crate::models::Expert;
use aws_sdk_bedrockruntime::Client as BedrockClient;
use serde_json::json;
use std::collections::HashMap;
use tracing::{error, warn};

pub const VECTOR_DIM: usize = 1024; // Nova Embeddings are 1024 dims

/// Fetches a 1024-D embedding from Amazon Bedrock Nova Multimodal text embeddings.
pub async fn get_nova_embedding(text: &str, client: &BedrockClient) -> Vec<f64> {
    if text.trim().is_empty() {
        return vec![0.0; VECTOR_DIM];
    }

    let payload = json!({
        "inputText": text,
    });

    let result = client
        .invoke_model()
        .model_id("amazon.nova-embed-text-v1:0") // Text equivalent, or amazon.titan-embed-text-v2:0 if nova text doesn't exist
        .content_type("application/json")
        .accept("application/json")
        .body(aws_sdk_bedrockruntime::primitives::Blob::new(
            serde_json::to_vec(&payload).unwrap(),
        ))
        .send()
        .await;

    match result {
        Ok(output) => {
            let body_bytes = output.body.into_inner();
            let parsed: serde_json::Value = serde_json::from_slice(&body_bytes).unwrap_or_default();
            // Nova embedding response format typically contains "embedding"
            if let Some(emb) = parsed["embedding"].as_array() {
                return emb.iter().filter_map(|v| v.as_f64()).collect();
            }
            warn!("Unexpected nova-embed response: {:?}", parsed);
            vec![0.0; VECTOR_DIM]
        }
        Err(e) => {
            error!("Failed to fetch nova embedding: {:?}", e);
            vec![0.0; VECTOR_DIM]
        }
    }
}

pub async fn task_type_to_vector(
    task_type: &str,
    context: &str,
    client: &BedrockClient,
) -> Vec<f64> {
    let combined = format!("Task: {}\nContext: {}", task_type, context);
    get_nova_embedding(&combined, client).await
}

#[inline]
fn contains_any(haystack: &str, needles: &[&str]) -> bool {
    needles.iter().any(|n| haystack.contains(n))
}

// ── Built-in Expert Capability Vectors ───────────────────────────────────────

pub async fn init_experts_with_nova(client: &BedrockClient) -> HashMap<String, Expert> {
    let raw_experts = vec![
        (
            "CEO",
            vec!["strategy", "vision", "decision_making", "risk_assessment"],
        ),
        (
            "CTO",
            vec!["architecture", "tech_stack", "system_design", "api_design"],
        ),
        (
            "Engineer_Backend",
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
            vec!["frontend", "react", "nextjs", "typescript", "ui", "css"],
        ),
        (
            "QA",
            vec!["testing", "qa", "coverage", "security_scan", "validation"],
        ),
        (
            "DevOps",
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
            vec!["cost", "budget", "finance", "optimization", "pricing"],
        ),
    ];

    let mut experts = HashMap::new();
    for (role, skills) in raw_experts {
        let skills_str = skills.join(", ");
        let prompt = format!("Expert Role: {}\nSkills: {}", role, skills_str);
        
        // Fetch 1024D embedding
        let vector = get_nova_embedding(&prompt, client).await;

        experts.insert(
            role.to_string(),
            Expert {
                role: role.to_string(),
                vector,
                skills: skills.iter().map(|s| s.to_string()).collect(),
            },
        );
    }
    
    experts
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
