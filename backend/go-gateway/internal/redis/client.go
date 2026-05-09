package redis

import (
	"context"
	"fmt"
	"time"

	goredis "github.com/redis/go-redis/v9"
)

// Client wraps go-redis.
type Client struct {
	rdb *goredis.Client
}

// New creates a Redis client from the given URL (redis://host:port/db).
// Returns nil and an error if the URL is invalid. Connection is lazy.
func New(redisURL string) (*Client, error) {
	opts, err := goredis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parse redis url: %w", err)
	}
	rdb := goredis.NewClient(opts)
	return &Client{rdb: rdb}, nil
}

// Ping checks connectivity. Returns nil on success.
func (c *Client) Ping(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	return c.rdb.Ping(ctx).Err()
}

// Set stores a key with an optional TTL (0 = no expiry).
func (c *Client) Set(ctx context.Context, key string, value any, ttl time.Duration) error {
	return c.rdb.Set(ctx, key, value, ttl).Err()
}

// Get retrieves a string value by key.
func (c *Client) Get(ctx context.Context, key string) (string, error) {
	return c.rdb.Get(ctx, key).Result()
}

// Del deletes a key.
func (c *Client) Del(ctx context.Context, key string) error {
	return c.rdb.Del(ctx, key).Err()
}

// Close terminates the Redis connection.
func (c *Client) Close() error {
	return c.rdb.Close()
}

// IsAvailable returns true when the client can ping Redis.
func (c *Client) IsAvailable(ctx context.Context) bool {
	return c.Ping(ctx) == nil
}
