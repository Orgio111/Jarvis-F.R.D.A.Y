use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BrokerEvent {
    pub id: String,
    #[serde(rename = "type")]
    pub event_type: String,
    pub version: String,
    pub timestamp: String,
    pub correlation_id: String,
    pub request_id: Option<String>,
    pub session_id: Option<String>,
    pub source: String,
    pub topic: String,
    pub payload: serde_json::Value,
}

impl BrokerEvent {
    pub fn new(
        event_type: impl Into<String>,
        topic: impl Into<String>,
        payload: serde_json::Value,
        correlation_id: Option<String>,
        request_id: Option<String>,
        session_id: Option<String>,
    ) -> Self {
        BrokerEvent {
            id: format!("evt_{}", Uuid::new_v4()),
            event_type: event_type.into(),
            version: "1.0".to_string(),
            timestamp: Utc::now().to_rfc3339(),
            correlation_id: correlation_id.unwrap_or_else(|| Uuid::new_v4().to_string()),
            request_id,
            session_id,
            source: "broker".to_string(),
            topic: topic.into(),
            payload,
        }
    }
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PublishRequest {
    pub event_type: String,
    pub topic: String,
    pub payload: serde_json::Value,
    pub correlation_id: Option<String>,
    pub request_id: Option<String>,
    pub session_id: Option<String>,
}
