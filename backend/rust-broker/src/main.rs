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
    let broker = Arc::new(EventBroker::new(cfg.redis_url.clone(), cfg.channel_capacity));

    // Start Redis subscriber if configured
    if let Some(ref redis_url) = cfg.redis_url {
        let broker_clone = broker.clone();
        let redis_url = redis_url.clone();
        tokio::spawn(async move {
            if let Err(e) = broker_clone.start_redis_subscriber(&redis_url).await {
                tracing::warn!("redis subscriber stopped: {}", e);
            }
        });
    }

    // Router
    let app = Router::new()
        .route("/health", get(health::health_handler))
        .route("/metrics", get(metrics::metrics_handler))
        .route("/events/publish", post(handlers::publish_event))
        .route("/events/stream/:topic", get(handlers::stream_events))
        .layer(
            CorsLayer::new()
                .allow_origin(Any)
                .allow_methods(Any)
                .allow_headers(Any),
        )
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
