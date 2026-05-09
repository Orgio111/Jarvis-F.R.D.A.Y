use axum::{
    http::StatusCode,
    response::IntoResponse,
};
use prometheus::{Encoder, TextEncoder};

pub async fn metrics_handler() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let families = prometheus::gather();
    let mut buffer = Vec::new();
    if encoder.encode(&families, &mut buffer).is_err() {
        return (StatusCode::INTERNAL_SERVER_ERROR, "metrics encode error".to_string());
    }
    (StatusCode::OK, String::from_utf8(buffer).unwrap_or_default())
}
