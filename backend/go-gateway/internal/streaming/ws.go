package streaming

import (
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

var defaultUpgrader = websocket.Upgrader{
	ReadBufferSize:  4096,
	WriteBufferSize: 4096,
	CheckOrigin: func(r *http.Request) bool {
		// Origin checking is handled by CORS middleware.
		// For WebSocket we allow the upgrade if the HTTP layer passed CORS.
		return true
	},
	HandshakeTimeout: 10 * time.Second,
}

// UpgradeWS upgrades an HTTP connection to a WebSocket connection.
func UpgradeWS(w http.ResponseWriter, r *http.Request) (*websocket.Conn, error) {
	return defaultUpgrader.Upgrade(w, r, nil)
}

// WriteJSON serialises v to JSON and sends it as a WebSocket text message.
func WriteJSON(conn *websocket.Conn, v any) error {
	return conn.WriteJSON(v)
}

// SetPingPongHandlers installs ping/pong handlers to keep the connection alive.
func SetPingPongHandlers(conn *websocket.Conn, idleTimeout time.Duration) {
	conn.SetReadDeadline(time.Now().Add(idleTimeout))
	conn.SetPongHandler(func(_ string) error {
		conn.SetReadDeadline(time.Now().Add(idleTimeout))
		return nil
	})
}
