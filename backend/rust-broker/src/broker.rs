use std::collections::HashMap;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use tokio::sync::{broadcast, RwLock};
use tracing::{info, trace, warn};

use crate::events::BrokerEvent;

/// Per-topic channel entry tracking its sender and last-used timestamp.
struct ChannelEntry {
    sender: broadcast::Sender<BrokerEvent>,
    /// Last publish or subscribe time, as millis since UNIX_EPOCH. Atomic so
    /// touches don't need the outer write lock.
    last_used_ms: AtomicU64,
}

impl ChannelEntry {
    fn new(sender: broadcast::Sender<BrokerEvent>) -> Self {
        ChannelEntry {
            sender,
            last_used_ms: AtomicU64::new(now_ms()),
        }
    }

    fn touch(&self) {
        self.last_used_ms.store(now_ms(), Ordering::Relaxed);
    }

    fn idle_for(&self) -> Duration {
        let last = self.last_used_ms.load(Ordering::Relaxed);
        Duration::from_millis(now_ms().saturating_sub(last))
    }
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

/// EventBroker manages per-topic broadcast channels with bounded growth.
pub struct EventBroker {
    capacity: usize,
    channels: Arc<RwLock<HashMap<String, ChannelEntry>>>,
    redis_url: Option<String>,
    idle_ttl: Duration,
    max_count: usize,
    sweep_interval: Duration,
}

impl EventBroker {
    pub fn new(
        redis_url: Option<String>,
        capacity: usize,
        idle_ttl: Duration,
        max_count: usize,
        sweep_interval: Duration,
    ) -> Self {
        EventBroker {
            capacity,
            channels: Arc::new(RwLock::new(HashMap::new())),
            redis_url,
            idle_ttl,
            max_count,
            sweep_interval,
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
                // No active receivers — normal when nobody is subscribed.
            }
        }
    }

    /// Returns a receiver for a topic.
    pub async fn subscribe(&self, topic: &str) -> broadcast::Receiver<BrokerEvent> {
        let sender = self.get_or_create_channel(topic).await;
        sender.subscribe()
    }

    /// Returns the number of active channels (for metrics/observability).
    pub async fn channel_count(&self) -> usize {
        self.channels.read().await.len()
    }

    async fn get_or_create_channel(&self, topic: &str) -> broadcast::Sender<BrokerEvent> {
        // Fast path: read lock, refresh last_used.
        {
            let channels = self.channels.read().await;
            if let Some(entry) = channels.get(topic) {
                entry.touch();
                return entry.sender.clone();
            }
        }

        // Slow path: write lock.
        let mut channels = self.channels.write().await;

        // Re-check after acquiring write lock (another writer may have inserted).
        if let Some(entry) = channels.get(topic) {
            entry.touch();
            return entry.sender.clone();
        }

        // Cap check: if at max, evict zero-subscriber channels before creating.
        if channels.len() >= self.max_count {
            let before = channels.len();
            channels.retain(|_, entry| entry.sender.receiver_count() > 0);
            let evicted = before - channels.len();
            if evicted > 0 {
                info!(
                    evicted,
                    remaining = channels.len(),
                    "emergency eviction at channel cap"
                );
            } else {
                warn!(
                    count = channels.len(),
                    max = self.max_count,
                    "channel cap reached and all channels have active subscribers; proceeding anyway"
                );
            }
        }

        info!(topic = %topic, "creating new event channel");
        let (sender, _) = broadcast::channel(self.capacity);
        let entry = ChannelEntry::new(sender.clone());
        channels.insert(topic.to_string(), entry);
        sender
    }

    /// Background task: periodically evicts channels with zero subscribers
    /// that have been idle longer than `idle_ttl`.
    pub async fn run_idle_sweeper(self: Arc<Self>) {
        info!(
            ttl_secs = self.idle_ttl.as_secs(),
            interval_secs = self.sweep_interval.as_secs(),
            "channel idle sweeper started"
        );
        let mut interval = tokio::time::interval(self.sweep_interval);
        // Skip the immediate first tick.
        interval.tick().await;
        loop {
            interval.tick().await;
            self.sweep_idle_channels().await;
        }
    }

    async fn sweep_idle_channels(&self) {
        let start = Instant::now();
        let mut channels = self.channels.write().await;
        let before = channels.len();
        channels.retain(|topic, entry| {
            let active = entry.sender.receiver_count() > 0;
            let idle = entry.idle_for();
            let keep = active || idle < self.idle_ttl;
            if !keep {
                trace!(topic = %topic, idle_secs = idle.as_secs(), "evicting idle channel");
            }
            keep
        });
        let after = channels.len();
        let removed = before - after;
        if removed > 0 {
            info!(
                removed,
                remaining = after,
                elapsed_ms = start.elapsed().as_millis() as u64,
                "channel sweep complete"
            );
        }
    }

    /// Subscribes to Redis pub/sub and rebroadcasts messages as BrokerEvents.
    /// Uses the `redis_url` stored on the broker; returns an error if not configured.
    pub async fn start_redis_subscriber(&self) -> anyhow::Result<()> {
        let redis_url = self
            .redis_url
            .as_deref()
            .ok_or_else(|| anyhow::anyhow!("redis_url not configured"))?;

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
            trace!(channel = msg.get_channel_name(), "redis message received");

            if let Ok(event) = serde_json::from_str::<BrokerEvent>(&payload) {
                self.publish(event).await;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::events::BrokerEvent;

    fn test_broker(ttl_secs: u64, max: usize) -> Arc<EventBroker> {
        Arc::new(EventBroker::new(
            None,
            16,
            Duration::from_secs(ttl_secs),
            max,
            Duration::from_secs(60),
        ))
    }

    fn test_event(topic: &str) -> BrokerEvent {
        BrokerEvent::new("test", topic, serde_json::json!({}), None, None, None)
    }

    #[tokio::test]
    async fn channel_count_grows_with_unique_topics() {
        let broker = test_broker(300, 100);
        broker.publish(test_event("a")).await;
        broker.publish(test_event("b")).await;
        broker.publish(test_event("c")).await;
        assert_eq!(broker.channel_count().await, 3);
    }

    #[tokio::test]
    async fn sweep_evicts_idle_zero_subscriber_channels() {
        let broker = test_broker(0, 100); // TTL=0: any idle channel is evictable
        broker.publish(test_event("ephemeral")).await;
        assert_eq!(broker.channel_count().await, 1);

        // Allow last_used_ms to advance past 0
        tokio::time::sleep(Duration::from_millis(5)).await;
        broker.sweep_idle_channels().await;

        assert_eq!(broker.channel_count().await, 0);
    }

    #[tokio::test]
    async fn sweep_preserves_channels_with_active_subscribers() {
        let broker = test_broker(0, 100);
        let _rx = broker.subscribe("active").await;

        tokio::time::sleep(Duration::from_millis(5)).await;
        broker.sweep_idle_channels().await;

        // Subscriber still holds receiver -> retained despite zero TTL.
        assert_eq!(broker.channel_count().await, 1);
    }

    #[tokio::test]
    async fn cap_triggers_emergency_eviction_of_idle_channels() {
        let broker = test_broker(300, 2);
        broker.publish(test_event("a")).await;
        broker.publish(test_event("b")).await;
        assert_eq!(broker.channel_count().await, 2);

        // Creating a third topic should evict the two zero-subscriber channels.
        broker.publish(test_event("c")).await;
        assert_eq!(broker.channel_count().await, 1);
    }
}
