use axum::Json;
use serde_json::{json, Value};

pub async fn health_handler() -> Json<Value> {
    Json(json!({
        "ok": true,
        "data": {
            "status": "pass",
            "service": "rust-broker",
            "version": "0.1.0"
        }
    }))
}
