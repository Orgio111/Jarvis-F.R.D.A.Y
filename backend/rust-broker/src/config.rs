use std::env;

pub struct Config {
    pub host: String,
    pub port: u16,
    pub redis_url: Option<String>,
    pub channel_capacity: usize,
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
        }
    }
}
