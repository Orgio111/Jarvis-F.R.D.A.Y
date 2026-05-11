use std::sync::Arc;

use axum::{extract::State, Json};
use serde_json::{json, Value};

use crate::broker::EventBroker;

pub async fn health_handler(State(broker): State<Arc<EventBroker>>) -> Json<Value> {
    let channels = broker.channel_count().await;
    Json(json!({
        "ok": true,
        "data": {
            "status": "pass",
            "service": "rust-broker",
            "version": "0.1.0",
            "channels": channels,
        }
    }))
}
