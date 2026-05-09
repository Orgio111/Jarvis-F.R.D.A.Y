use std::sync::Arc;
use std::time::Duration;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::{
        sse::{Event, KeepAlive, Sse},
        IntoResponse,
    },
    Json,
};
use serde_json::json;
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;

use crate::broker::EventBroker;
use crate::events::{BrokerEvent, PublishRequest};

/// POST /events/publish
pub async fn publish_event(
    State(broker): State<Arc<EventBroker>>,
    Json(req): Json<PublishRequest>,
) -> impl IntoResponse {
    let event = BrokerEvent::new(
        &req.event_type,
        &req.topic,
        req.payload,
        req.correlation_id,
        req.request_id,
        req.session_id,
    );
    let event_id = event.id.clone();
    broker.publish(event).await;

    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "data": { "published": true, "eventId": event_id },
        })),
    )
}

/// GET /events/stream/:topic — SSE stream for a given topic
pub async fn stream_events(
    State(broker): State<Arc<EventBroker>>,
    Path(topic): Path<String>,
) -> Sse<impl futures::Stream<Item = Result<Event, axum::Error>>> {
    let receiver = broker.subscribe(&topic).await;
    let stream = BroadcastStream::new(receiver)
        .filter_map(|result| async move {
            match result {
                Ok(event) => {
                    let data = serde_json::to_string(&event).ok()?;
                    Some(Ok(Event::default()
                        .event(event.event_type.clone())
                        .data(data)
                        .id(event.id.clone())))
                }
                Err(_) => None,
            }
        });

    Sse::new(stream).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(15))
            .text("heartbeat"),
    )
}
