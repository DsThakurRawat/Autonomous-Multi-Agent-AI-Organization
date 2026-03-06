mod metrics;
mod models;
mod scorer;
mod vectorizer;

use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

use axum::{
    extract::{Json, State},
    http::StatusCode,
    response::{IntoResponse, Json as JsonResponse},
    routing::{get, post},
    Router,
};
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use tracing::info;

use models::{
    BatchRouteRequest, BatchRouteResponse, Expert, ExpertStats, HealthResponse, RouteRequest,
    RouteResponse,
};
use scorer::{rank_experts, should_use_ensemble, ENSEMBLE_THRESHOLD};
use vectorizer::{default_experts, direct_expert_for_task_type, task_type_to_vector};

// ── Application State ─────────────────────────────────────────────────────────

#[derive(Clone)]
struct AppState {
    start_time: Instant,
    /// Built-in expert definitions (can be overridden per-request)
    default_experts: Arc<HashMap<String, Expert>>,
}

// ── Router ────────────────────────────────────────────────────────────────────

/// Core routing logic — used by both single and batch handlers
fn do_route(
    req: RouteRequest,
    default_experts_map: &HashMap<String, Expert>,
) -> RouteResponse {
    let started = std::time::Instant::now();

    // Merge request-provided experts with defaults
    let experts_map: HashMap<String, Expert> = {
        let mut m = default_experts_map.clone();
        if let Some(extra) = req.experts {
            m.extend(extra);
        }
        m
    };

    // Merge request-provided stats (or empty defaults)
    let stats_map: HashMap<String, ExpertStats> = req.stats.unwrap_or_default();

    let task_type = &req.task_type;
    let is_critical = req.priority == "critical";

    // ── Step 1: Direct mapping check ──────────────────────────────────────
    if !req.force_ensemble {
        if let Some(direct_expert) = direct_expert_for_task_type(task_type) {
            let stat = stats_map.get(direct_expert).cloned().unwrap_or_default();
            if stat.load_factor < 1.0 {
                let latency_ms = started.elapsed().as_secs_f64() * 1000.0;
                metrics::record_routing("direct", direct_expert, latency_ms, false);

                return RouteResponse {
                    task_id:         req.task_id,
                    selected_expert: direct_expert.to_string(),
                    fallback_experts: vec![],
                    routing_score:   1.0,
                    confidence:      0.99,
                    ensemble_mode:   false,
                    routing_type:    "direct".to_string(),
                    routing_reason:  format!(
                        "Direct routing: task_type '{}' maps to {}",
                        task_type, direct_expert
                    ),
                    all_scores:      vec![],
                    routing_ms:      round2(latency_ms),
                    trace_id:        req.trace_id,
                };
            }
        }
    }

    // ── Step 2: Compute task vector ──────────────────────────────────────
    let task_vector = task_type_to_vector(task_type, &req.input_context);

    // Filter by required skills
    let experts_filtered: Vec<(String, Expert)> = if req.required_skills.is_empty() {
        experts_map.into_iter().collect()
    } else {
        experts_map.into_iter()
            .filter(|(_, exp)| req.required_skills.iter().any(|sk| exp.skills.contains(sk)))
            .collect()
    };

    let experts_to_rank: Vec<(String, Expert)> = if experts_filtered.is_empty() {
        default_experts_map.clone().into_iter().collect()
    } else {
        experts_filtered
    };

    // ── Step 3: Score & rank ─────────────────────────────────────────────
    let rankings = rank_experts(
        &task_vector,
        &experts_to_rank,
        &stats_map,
        !is_critical,   // skip overloaded unless critical
    );

    if rankings.is_empty() {
        // All overloaded — last-resort fallback
        let fallback = experts_to_rank.first().map(|(r, _)| r.clone())
            .unwrap_or_else(|| "CEO".to_string());
        let latency_ms = started.elapsed().as_secs_f64() * 1000.0;
        return RouteResponse {
            task_id:         req.task_id,
            selected_expert: fallback.clone(),
            fallback_experts: vec![],
            routing_score:   0.0,
            confidence:      0.1,
            ensemble_mode:   false,
            routing_type:    "fallback".to_string(),
            routing_reason:  "All experts overloaded — last-resort fallback".to_string(),
            all_scores:      vec![],
            routing_ms:      round2(latency_ms),
            trace_id:        req.trace_id,
        };
    }

    let top     = &rankings[0];
    let second  = rankings.get(1);

    // ── Step 4: Ensemble decision ─────────────────────────────────────────
    let use_ensemble = req.force_ensemble || second.map(|s| {
        should_use_ensemble(top.composite, s.composite)
    }).unwrap_or(false);

    let fallback_experts: Vec<String> = if use_ensemble {
        second.map(|s| vec![s.role.clone()]).unwrap_or_default()
    } else {
        vec![]
    };

    let confidence = (top.composite / ENSEMBLE_THRESHOLD).min(1.0);
    let routing_reason = format!(
        "Scored routing: {} selected (score={:.3}, sim={:.3}, load={:.3}, success={:.3}){}",
        top.role, top.composite, top.similarity, top.load, top.success,
        if use_ensemble {
            format!(" | Ensemble with {} (gap {:.3})",
                second.map(|s| s.role.as_str()).unwrap_or("—"),
                top.composite - second.map(|s| s.composite).unwrap_or(0.0))
        } else { String::new() }
    );

    let latency_ms = started.elapsed().as_secs_f64() * 1000.0;
    metrics::record_routing("scored", &top.role, latency_ms, use_ensemble);

    RouteResponse {
        task_id:         req.task_id,
        selected_expert: top.role.clone(),
        fallback_experts,
        routing_score:   top.composite,
        confidence:      round4(confidence),
        ensemble_mode:   use_ensemble,
        routing_type:    "scored".to_string(),
        routing_reason,
        all_scores:      rankings,
        routing_ms:      round2(latency_ms),
        trace_id:        req.trace_id,
    }
}

// ── HTTP Handlers ─────────────────────────────────────────────────────────────

async fn handle_route(
    State(state): State<AppState>,
    Json(req): Json<RouteRequest>,
) -> impl IntoResponse {
    info!(task_type = ?req.task_type, task_id = ?req.task_id, "routing request");
    let response = do_route(req, &state.default_experts);
    (StatusCode::OK, JsonResponse(response))
}

async fn handle_batch_route(
    State(state): State<AppState>,
    Json(batch): Json<BatchRouteRequest>,
) -> impl IntoResponse {
    let started = std::time::Instant::now();
    info!(count = batch.tasks.len(), "batch routing request");

    // Merge batch-level experts/stats into each task
    let batch_experts = batch.experts.unwrap_or_default();
    let batch_stats   = batch.stats.unwrap_or_default();

    let decisions: Vec<RouteResponse> = batch.tasks.into_iter().map(|mut t| {
        // Merge batch-level overrides
        if t.experts.is_none() && !batch_experts.is_empty() {
            t.experts = Some(batch_experts.clone());
        }
        if t.stats.is_none() && !batch_stats.is_empty() {
            t.stats = Some(batch_stats.clone());
        }
        do_route(t, &state.default_experts)
    }).collect();

    let total_ms = started.elapsed().as_secs_f64() * 1000.0;
    (
        StatusCode::OK,
        JsonResponse(BatchRouteResponse {
            decisions,
            total_ms: round2(total_ms),
        }),
    )
}

async fn handle_vectorize(
    Json(body): Json<serde_json::Value>,
) -> impl IntoResponse {
    let task_type = body["task_type"].as_str().unwrap_or("");
    let context   = body["context"].as_str().unwrap_or("");
    let vector    = task_type_to_vector(task_type, context);
    JsonResponse(serde_json::json!({
        "task_type": task_type,
        "vector": vector,
        "dim": vector.len(),
    }))
}

async fn handle_health(State(state): State<AppState>) -> impl IntoResponse {
    let uptime_seconds = state.start_time.elapsed().as_secs();
    JsonResponse(HealthResponse {
        status: "ok",
        version: env!("CARGO_PKG_VERSION"),
        uptime_seconds,
    })
}

async fn handle_metrics() -> impl IntoResponse {
    (
        StatusCode::OK,
        [(axum::http::header::CONTENT_TYPE, "text/plain; version=0.0.4")],
        metrics::render_metrics(),
    )
}

async fn handle_experts(State(state): State<AppState>) -> impl IntoResponse {
    // Clone the map out of the Arc so we return owned data, not a reference
    let experts: HashMap<String, Expert> = (*state.default_experts).clone();
    JsonResponse(experts)
}

// ── Utility ───────────────────────────────────────────────────────────────────

#[inline] fn round2(v: f64) -> f64 { (v * 100.0).round() / 100.0 }
#[inline] fn round4(v: f64) -> f64 { (v * 10_000.0).round() / 10_000.0 }

// ── Main ──────────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    // Init structured JSON logging
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(
            std::env::var("RUST_LOG")
                .unwrap_or_else(|_| "moe_scoring=info,tower_http=warn".to_string())
        )
        .init();

    let port = std::env::var("MOE_PORT")
        .unwrap_or_else(|_| "8090".to_string())
        .parse::<u16>()
        .unwrap_or(8090);

    let state = AppState {
        start_time:      Instant::now(),
        default_experts: Arc::new(default_experts()),
    };

    let app = Router::new()
        .route("/route",       post(handle_route))
        .route("/route/batch", post(handle_batch_route))
        .route("/vectorize",   post(handle_vectorize))
        .route("/experts",     get(handle_experts))
        .route("/health",      get(handle_health))
        .route("/metrics",     get(handle_metrics))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    info!("MoE scoring service starting on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .expect("Failed to bind address");

    info!(port = port, "MoE scoring service ready");
    axum::serve(listener, app).await.expect("Server error");
}
