// server.js
import WebSocket from 'ws';
import express from 'express';
import http from 'http';
import { RealTimeDataClient } from '@polymarket/real-time-data-client';

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

let coinbasePrice = null;
let polymarketPrice = null;

// Connect to Coinbase WebSocket
function connectCoinbase() {
  const coinbaseWs = new WebSocket('wss://ws-feed.exchange.coinbase.com');
  
  coinbaseWs.on('open', () => {
    console.log('✅ Connected to Coinbase WebSocket');
    coinbaseWs.send(JSON.stringify({
      type: 'subscribe',
      product_ids: ['BTC-USD'],
      channels: ['ticker']
    }));
  });

  coinbaseWs.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'ticker' && msg.price) {
      coinbasePrice = parseFloat(msg.price).toFixed(2);
      broadcastPrices();
    }
  });

  coinbaseWs.on('error', (error) => {
    console.error('❌ Coinbase WebSocket error:', error.message);
  });

  coinbaseWs.on('close', () => {
    console.log('⚠️  Coinbase connection closed. Reconnecting...');
    setTimeout(connectCoinbase, 5000);
  });
}

// Connect to Polymarket WebSocket using official client
function connectPolymarket() {
  console.log('🔌 Connecting to Polymarket WebSocket...');
  
  const client = new RealTimeDataClient({
    onConnect: (c) => {
      console.log('✅ Connected to Polymarket WebSocket');
      
      // Subscribe to BTC crypto price
      c.subscribe({
        subscriptions: [{
          topic: 'crypto_prices',
          type: 'update',
          filters: '["BTCUSDT"]'
        }]
      });
      
      console.log('✅ Subscribed to Polymarket BTC prices');
    },
    onMessage: (c, message) => {
      try {
        if (message.topic === 'crypto_prices' && message.type === 'update') {
          const payload = message.payload;
          if (payload && payload.symbol === 'BTCUSDT') {
            polymarketPrice = parseFloat(payload.price).toFixed(2);
            console.log(`📊 Polymarket BTC Update: $${polymarketPrice}`);
            broadcastPrices();
          }
        }
      } catch (error) {
        console.error('❌ Error processing Polymarket message:', error.message);
      }
    },
    onStatusChange: (status) => {
      console.log(`📡 Polymarket status: ${status}`);
      if (status === 'disconnected') {
        console.log('⚠️  Polymarket disconnected. Reconnecting...');
      }
    },
    autoReconnect: true,
    pingInterval: 5000
  });

  client.connect();
}

// Log prices every second
setInterval(() => {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`COINBASE BTC PRICE  : $${coinbasePrice || 'Loading...'}`);
  console.log(`POLYMARKET BTC PRICE: $${polymarketPrice || 'Loading...'}`);
  console.log(`TIME: ${new Date().toISOString()}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
}, 1000);

// Broadcast prices to all connected clients
function broadcastPrices() {
  const message = {
    coinbase: coinbasePrice,
    polymarket: polymarketPrice,
    timestamp: new Date().toISOString()
  };

  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  });
}

// Handle client connections
wss.on('connection', (ws) => {
  console.log('🔌 New client connected. Total clients:', wss.clients.size);
  
  // Send current prices immediately
  ws.send(JSON.stringify({
    coinbase: coinbasePrice,
    polymarket: polymarketPrice,
    timestamp: new Date().toISOString()
  }));

  ws.on('close', () => {
    console.log('🔌 Client disconnected. Total clients:', wss.clients.size);
  });
});

// Health check endpoint
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>BTC Price WebSocket Server</title>
      <style>
        body {
          font-family: monospace;
          background: #1a1a1a;
          color: #00ff00;
          padding: 20px;
          max-width: 800px;
          margin: 0 auto;
        }
        h1 { color: #00ff00; }
        .price { font-size: 24px; margin: 10px 0; }
        .status { color: #ffff00; }
        .diff { 
          font-size: 14px; 
          color: ${coinbasePrice && polymarketPrice ? 
            (Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice)) > 10 ? '#ff0000' : '#00ff00') 
            : '#ffff00'
          };
        }
      </style>
    </head>
    <body>
      <h1>🚀 BTC Price WebSocket Server</h1>
      <div class="status">✅ Server is running</div>
      <div class="price">💰 Coinbase BTC: $${coinbasePrice || 'Loading...'}</div>
      <div class="price">📊 Polymarket BTC: $${polymarketPrice || 'Loading...'}</div>
      ${coinbasePrice && polymarketPrice ? 
        `<div class="diff">📈 Difference: $${Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice)).toFixed(2)}</div>` 
        : ''
      }
      <p>Connect to WebSocket: <code>wss://${req.headers.host}</code></p>
      <p>Active connections: ${wss.clients.size}</p>
      <p style="color: #888; font-size: 12px;">Using official Polymarket WebSocket (crypto_prices)</p>
    </body>
    </html>
  `);
});

app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    coinbase: coinbasePrice, 
    polymarket: polymarketPrice,
    difference: coinbasePrice && polymarketPrice ? 
      Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice)).toFixed(2) : null,
    clients: wss.clients.size,
    timestamp: new Date().toISOString()
  });
});

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📡 WebSocket endpoint: ws://localhost:${PORT}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  connectCoinbase();
  connectPolymarket();
});
