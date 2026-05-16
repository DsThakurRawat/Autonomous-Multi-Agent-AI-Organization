package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"

	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
)

var (
	ctx           = context.Background()
	upgrader      = websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}
	redisClient   *redis.Client
	hub           *Hub
)

// Hub maintains the set of active clients and broadcasts messages to them.
type Hub struct {
	clients    map[*Client]bool
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
}

func newHub() *Hub {
	return &Hub{
		broadcast:  make(chan []byte),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		clients:    make(map[*Client]bool),
	}
}

func (h *Hub) run() {
	for {
		select {
		case client := <-h.register:
			h.clients[client] = true
			log.Printf("Client connected. Total: %d", len(h.clients))
		case client := <-h.unregister:
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
				log.Printf("Client disconnected. Total: %d", len(h.clients))
			}
		case message := <-h.broadcast:
			for client := range h.clients {
				select {
				case client.send <- message:
				default:
					close(client.send)
					delete(h.clients, client)
				}
			}
		}
	}
}

// Client is a middleman between the websocket connection and the hub.
type Client struct {
	hub  *Hub
	conn *websocket.Conn
	send chan []byte
}

func (c *Client) readPump() {
	defer func() {
		c.hub.unregister <- c
		c.conn.Close()
	}()
	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			break
		}
		// When Go receives a message from UI, it publishes to Redis for Python Swarm
		var msg map[string]interface{}
		if err := json.Unmarshal(message, &msg); err == nil {
			log.Printf("Received message from UI: %s", msg["message"])
			payload, _ := json.Marshal(msg)
			redisClient.Publish(ctx, "sarang:tasks", payload)
		}
	}
}

func (c *Client) writePump() {
	defer func() {
		c.conn.Close()
	}()
	for {
		select {
		case message, ok := <-c.send:
			if !ok {
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}
			c.conn.WriteMessage(websocket.TextMessage, message)
		}
	}
}

func subscribeToEvents() {
	pubsub := redisClient.Subscribe(ctx, "sarang:events")
	defer pubsub.Close()

	ch := pubsub.Channel()
	log.Println("Listening for SARANG Agent Events on Redis...")

	for msg := range ch {
		// Relay events from Redis to all WebSocket clients
		hub.broadcast <- []byte(msg.Payload)
	}
}

func main() {
	redisAddr := os.Getenv("REDIS_URL")
	if redisAddr == "" {
		redisAddr = "localhost:6379"
	}
	redisClient = redis.NewClient(&redis.Options{Addr: redisAddr})

	hub = newHub()
	go hub.run()
	go subscribeToEvents()

	http.HandleFunc("/ws/chat", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Println("Upgrade error:", err)
			return
		}
		client := &Client{hub: hub, conn: conn, send: make(chan []byte, 256)}
		client.hub.register <- client
		go client.writePump()
		go client.readPump()
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("SARANG Go Gateway started on :%s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatal("ListenAndServe:", err)
	}
}
