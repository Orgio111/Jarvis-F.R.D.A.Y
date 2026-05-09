use std::collections::HashMap;
use std::sync::Arc;

use tokio::sync::{broadcast, RwLock};
use tracing::{info, warn};

use crate::events::BrokerEvent;

/// EventBroker manages per-topic broadcast channels.
pub struct EventBroker {
    capacity: usize,
    channels: Arc<RwLock<HashMap<String, broadcast::Sender<BrokerEvent>>>>,
    redis_url: Option<String>,
}

impl EventBroker {
    pub fn new(redis_url: Option<String>, capacity: usize) -> Self {
        EventBroker {
            capacity,
            channels: Arc::new(RwLock::new(HashMap::new())),
            redis_url,
        }
    }

    /// Publishes an event to a topic. Creates the channel if it doesn't exist.
    pub async fn publish(&self, event: BrokerEvent) {
        let topic = event.topic.clone();
        let sender = self.get_or_create_channel(&topic).await;
        match sender.send(event) {
            Ok(n) => {
                if n > 0 {
                    info!(topic = %topic, receivers = n, "event published");
                }
            }
            Err(_) => {
                // No active receivers — this is normal when nobody is subscribed
            }
        }
    }

    /// Returns a receiver for a topic.
    pub async fn subscribe(&self, topic: &str) -> broadcast::Receiver<BrokerEvent> {
        let sender = self.get_or_create_channel(topic).await;
        sender.subscribe()
    }

    async fn get_or_create_channel(&self, topic: &str) -> broadcast::Sender<BrokerEvent> {
        // Fast path: read lock
        {
            let channels = self.channels.read().await;
            if let Some(tx) = channels.get(topic) {
                return tx.clone();
            }
        }
        // Slow path: write lock
        let mut channels = self.channels.write().await;
        channels
            .entry(topic.to_string())
            .or_insert_with(|| {
                info!(topic = %topic, "creating new event channel");
                let (tx, _) = broadcast::channel(self.capacity);
                tx
            })
            .clone()
    }

    /// Subscribes to Redis pub/sub and rebroadcasts messages as BrokerEvents.
    pub async fn start_redis_subscriber(&self, redis_url: &str) -> Result<(), anyhow::Error> {
        use redis::AsyncCommands;

        let client = redis::Client::open(redis_url)?;
        let mut pubsub = client.get_async_pubsub().await?;
        pubsub.psubscribe("jarvis:*").await?;

        info!(url = %redis_url, "redis pubsub subscriber started");

        use futures::StreamExt;
        let mut stream = pubsub.into_on_message();
        while let Some(msg) = stream.next().await {
            let payload: String = match msg.get_payload() {
                Ok(p) => p,
                Err(e) => {
                    warn!("redis message payload error: {}", e);
                    continue;
                }
            };
            let topic = msg.get_channel_name().to_string();

            if let Ok(event) = serde_json::from_str::<BrokerEvent>(&payload) {
                self.publish(event).await;
            }
        }
        Ok(())
    }
}
