use std::env;
use std::time::Duration;

pub struct Config {
    pub host: String,
    pub port: u16,
    pub redis_url: Option<String>,
    pub channel_capacity: usize,
    /// Idle TTL after which a channel with zero subscribers is evicted.
    pub channel_idle_ttl: Duration,
    /// Soft cap on the number of channels held in memory. When exceeded, the
    /// next create call triggers an emergency eviction of zero-subscriber
    /// channels regardless of TTL.
    pub channel_max_count: usize,
    /// How often the background sweeper scans for idle channels.
    pub sweep_interval: Duration,
}

impl Config {
    pub fn from_env() -> Self {
        let redis_url = env::var("REDIS_URL").ok().filter(|u| !u.is_empty());
        Config {
            host: env::var("RUST_BROKER_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            port: env::var("RUST_BROKER_PORT")
                .ok()
                .and_then(|p| p.parse().ok())
                .unwrap_or(8200),
            redis_url,
            channel_capacity: env::var("CHANNEL_CAPACITY")
                .ok()
                .and_then(|c| c.parse().ok())
                .unwrap_or(1024),
            channel_idle_ttl: Duration::from_secs(
                env::var("CHANNEL_IDLE_TTL_SECS")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(300),
            ),
            channel_max_count: env::var("CHANNEL_MAX_COUNT")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(10_000),
            sweep_interval: Duration::from_secs(
                env::var("CHANNEL_SWEEP_INTERVAL_SECS")
                    .ok()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(60),
            ),
        }
    }
}
