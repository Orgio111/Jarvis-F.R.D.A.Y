mod config;
mod broker;
mod events;
mod handlers;
mod health;
mod metrics;

use std::net::SocketAddr;
use std::sync::Arc;

use axum::{
    Router,
    routing::{get, post},
};
use axum::http::HeaderValue;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing::info;
use tracing_subscriber::{EnvFilter, fmt};

use crate::broker::EventBroker;
use crate::config::Config;

#[tokio::main]
async fn main() {
    // Load environment
    let _ = dotenvy::dotenv();

    // Tracing
    fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("jarvis_broker=info".parse().unwrap()))
        .init();

    let cfg = Config::from_env();
    info!(
        version = "0.1.0",
        host = %cfg.host,
        port = cfg.port,
        "starting JARVIS Rust broker"
    );

    // Event broker (in-memory broadcast bus + optional Redis pub/sub)
    let broker = Arc::new(EventBroker::new(
        cfg.redis_url.clone(),
        cfg.channel_capacity,
        cfg.channel_idle_ttl,
        cfg.channel_max_count,
        cfg.sweep_interval,
    ));

    // Start Redis subscriber if configured (the broker reads its own redis_url)
    if cfg.redis_url.is_some() {
        let broker_clone = broker.clone();
        tokio::spawn(async move {
            if let Err(e) = broker_clone.start_redis_subscriber().await {
                tracing::warn!("redis subscriber stopped: {}", e);
            }
        });
    }

    // Idle channel sweeper — bounds memory growth from one-shot topics.
    {
        let broker_clone = broker.clone();
        tokio::spawn(async move {
            broker_clone.run_idle_sweeper().await;
        });
    }

    // Router
    // Internal service — only allow calls from the Go gateway and Python AI service.
    // Origins are configurable via CORS_ALLOWED_ORIGINS env var (comma-separated).
    let allowed_origins: Vec<HeaderValue> = std::env::var("CORS_ALLOWED_ORIGINS")
        .unwrap_or_else(|_| {
            "http://localhost:8000,http://go-gateway:8000,http://localhost:8100,http://python-ai-service:8100".to_string()
        })
        .split(',')
        .filter_map(|o| o.trim().parse::<HeaderValue>().ok())
        .collect();

    let cors = CorsLayer::new()
        .allow_origin(allowed_origins)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(health::health_handler))
        .route("/metrics", get(metrics::metrics_handler))
        .route("/events/publish", post(handlers::publish_event))
        .route("/events/stream/:topic", get(handlers::stream_events))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(broker);

    let addr: SocketAddr = format!("{}:{}", cfg.host, cfg.port)
        .parse()
        .expect("invalid bind address");

    info!("broker listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .unwrap();

    info!("broker stopped");
}

async fn shutdown_signal() {
    tokio::signal::ctrl_c().await.expect("ctrl-c install failed");
    info!("shutdown signal received");
}
