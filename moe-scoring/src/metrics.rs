/// Prometheus metrics for the MoE scoring service.
use once_cell::sync::Lazy;
use prometheus::{
    register_counter_vec, register_histogram_vec, register_int_counter, CounterVec, Encoder,
    HistogramVec, IntCounter, TextEncoder,
};

/// Total routing decisions by routing_type (direct | scored)
pub static ROUTING_DECISIONS: Lazy<CounterVec> = Lazy::new(|| {
    register_counter_vec!(
        "moe_routing_decisions_total",
        "Total MoE routing decisions made",
        &["routing_type", "selected_expert"]
    )
    .expect("Failed to register moe_routing_decisions_total")
});

/// Routing latency histogram (milliseconds)
pub static ROUTING_LATENCY: Lazy<HistogramVec> = Lazy::new(|| {
    register_histogram_vec!(
        "moe_routing_latency_ms",
        "MoE routing latency in milliseconds",
        &["routing_type"],
        vec![0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0]
    )
    .expect("Failed to register moe_routing_latency_ms")
});

/// Total ensemble decisions (when two experts are close)
pub static ENSEMBLE_DECISIONS: Lazy<IntCounter> = Lazy::new(|| {
    register_int_counter!(
        "moe_ensemble_decisions_total",
        "Total number of routing decisions that used ensemble mode"
    )
    .expect("Failed to register moe_ensemble_decisions_total")
});

/// Total HTTP requests
#[allow(dead_code)]
pub static HTTP_REQUESTS: Lazy<CounterVec> = Lazy::new(|| {
    register_counter_vec!(
        "moe_http_requests_total",
        "Total HTTP requests to the MoE service",
        &["method", "path", "status"]
    )
    .expect("Failed to register moe_http_requests_total")
});

/// Record a routing decision into metrics.
pub fn record_routing(routing_type: &str, expert: &str, latency_ms: f64, ensemble: bool) {
    ROUTING_DECISIONS
        .with_label_values(&[routing_type, expert])
        .inc();
    ROUTING_LATENCY
        .with_label_values(&[routing_type])
        .observe(latency_ms);
    if ensemble {
        ENSEMBLE_DECISIONS.inc();
    }
}

/// Render all metrics in Prometheus text format.
pub fn render_metrics() -> String {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buf = Vec::new();
    encoder.encode(&metric_families, &mut buf).unwrap_or(());
    String::from_utf8(buf).unwrap_or_default()
}
