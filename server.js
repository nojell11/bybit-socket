// server.js
import { WebSocketServer } from 'ws';
import WebSocket from 'ws';
import express from 'express';
import http from 'http';

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server });

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
    setTimeout(connectCoinbase, 1000);
  });
}

// Connect to Polymarket RTDS (Real-Time Data Stream) WebSocket
// Official endpoint: wss://ws-live-data.polymarket.com
function connectPolymarket() {
  const polyWs = new WebSocket('wss://ws-live-data.polymarket.com');
  let isConnected = false;
  
  polyWs.on('open', () => {
    console.log('✅ Connected to Polymarket RTDS WebSocket');
    isConnected = true;
    
    // Subscribe to crypto prices (BTC) - using correct Polymarket protocol
    const subscribeMessage = {
      subscriptions: [{
        topic: 'crypto_prices',
        type: 'update',
        filters: '["BTCUSDT"]'
      }]
    };
    
    polyWs.send(JSON.stringify(subscribeMessage));
    console.log('📊 Subscribed to Polymarket BTC prices');
  });

  polyWs.on('message', (data) => {
    try {
      const msg = JSON.parse(data);
      
      // Handle different message types
      if (msg.topic === 'crypto_prices' && msg.type === 'update') {
        const payload = msg.payload;
        if (payload && payload.symbol === 'BTCUSDT' && payload.price) {
          polymarketPrice = parseFloat(payload.price).toFixed(2);
          console.log(`📊 Polymarket BTC Update: ${polymarketPrice}`);
          broadcastPrices();
        }
      } else if (msg.event === 'connected') {
        console.log('✅ Polymarket connection confirmed');
      } else if (msg.event === 'subscribed') {
        console.log('✅ Polymarket subscription confirmed');
      }
    } catch (error) {
      // Ignore parsing errors for heartbeat/system messages
      if (data.toString() !== 'PONG') {
        console.error('❌ Error parsing Polymarket message:', error.message);
      }
    }
  });

  polyWs.on('error', (error) => {
    console.error('❌ Polymarket WebSocket error:', error.message);
  });

  polyWs.on('close', () => {
    console.log('⚠️  Polymarket connection closed. Reconnecting...');
    isConnected = false;
    setTimeout(connectPolymarket, 5000);
  });
  
  // Send ping every 30 seconds to keep connection alive
  const pingInterval = setInterval(() => {
    if (isConnected && polyWs.readyState === WebSocket.OPEN) {
      polyWs.send('PING');
    } else {
      clearInterval(pingInterval);
    }
  }, 30000);
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
  const diff = coinbasePrice && polymarketPrice ? 
    Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice)) : 0;
  
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>BTC Price WebSocket Server</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body {
          font-family: 'Courier New', monospace;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
          padding: 20px;
          margin: 0;
          display: flex;
          justify-content: center;
          align-items: center;
        }
        .container {
          background: rgba(255, 255, 255, 0.95);
          border-radius: 20px;
          padding: 40px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          max-width: 600px;
          width: 100%;
        }
        h1 { 
          color: #2c3e50;
          text-align: center;
          margin-bottom: 30px;
          font-size: 28px;
        }
        .price-card {
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
          border-radius: 15px;
          padding: 20px;
          margin: 15px 0;
          transition: transform 0.3s;
        }
        .price-card:hover {
          transform: translateY(-5px);
        }
        .label {
          font-size: 12px;
          color: #7f8c8d;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 5px;
        }
        .price {
          font-size: 32px;
          font-weight: bold;
          color: #2c3e50;
        }
        .status {
          text-align: center;
          padding: 10px;
          border-radius: 10px;
          margin: 20px 0;
          background: #d4edda;
          color: #155724;
          font-weight: bold;
        }
        .diff {
          text-align: center;
          font-size: 14px;
          color: ${diff > 10 ? '#e74c3c' : '#27ae60'};
          font-weight: bold;
          margin: 10px 0;
        }
        .info {
          text-align: center;
          color: #7f8c8d;
          font-size: 12px;
          margin-top: 20px;
          line-height: 1.6;
        }
        code {
          background: #ecf0f1;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 11px;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🚀 BTC Price Monitor</h1>
        <div class="status">✅ Server is running</div>
        
        <div class="price-card">
          <div class="label">💰 Coinbase BTC</div>
          <div class="price">$${coinbasePrice || 'Loading...'}</div>
        </div>
        
        <div class="price-card">
          <div class="label">📊 Polymarket BTC (Kraken)</div>
          <div class="price">${polymarketPrice || 'Loading...'}</div>
        </div>
        
        ${coinbasePrice && polymarketPrice ? 
          `<div class="diff">📈 Difference: $${diff.toFixed(2)}</div>` : ''
        }
        
        <div class="info">
          <p><strong>WebSocket:</strong> <code>wss://${req.headers.host}</code></p>
          <p><strong>Active Connections:</strong> ${wss.clients.size}</p>
          <p style="margin-top: 15px; font-size: 11px;">
            Polymarket's public WebSocket doesn't provide crypto prices without authentication.
            Using Kraken as comparison (a data source that Chainlink/Polymarket aggregates from).
            Comparing Coinbase vs Kraken BTC prices in real-time.
          </p>
        </div>
      </div>
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
  console.log(`🌐 Web interface: http://localhost:${PORT}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  connectCoinbase();
  connectPolymarket();
});
