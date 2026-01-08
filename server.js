// server.js
const WebSocket = require('ws');
const express = require('express');
const http = require('http');

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
    console.error('❌ Coinbase WebSocket error:', error);
  });

  coinbaseWs.on('close', () => {
    console.log('⚠️  Coinbase connection closed. Reconnecting...');
    setTimeout(connectCoinbase, 5000);
  });
}

// Connect to Polymarket (using their API)
async function fetchPolymarketPrice() {
  try {
    // Using Polymarket's gamma API for active BTC markets
    const response = await fetch('https://gamma-api.polymarket.com/markets?closed=false&active=true&limit=200');
    const data = await response.json();
    
    // Find the most recent "Bitcoin Up or Down" market
    const btcMarket = data.find(m => 
      m.question && 
      m.question.includes('Bitcoin') && 
      m.question.includes('Up or Down')
    );
    
    if (btcMarket) {
      console.log(`📊 Found Polymarket Market: "${btcMarket.question}"`);
      
      // Try to extract the target price from description or market data
      if (btcMarket.description) {
        const priceMatch = btcMarket.description.match(/\$([0-9,]+(?:\.[0-9]{2})?)/);
        if (priceMatch) {
          polymarketPrice = priceMatch[1].replace(/,/g, '');
          console.log(`✅ Polymarket target price: ${polymarketPrice}`);
          return;
        }
      }
      
      // If no price in description, try to get it from the market metadata
      if (btcMarket.markets && btcMarket.markets[0]) {
        const market = btcMarket.markets[0];
        if (market.groupItemTitle) {
          const priceMatch = market.groupItemTitle.match(/\$([0-9,]+(?:\.[0-9]{2})?)/);
          if (priceMatch) {
            polymarketPrice = priceMatch[1].replace(/,/g, '');
            console.log(`✅ Polymarket target price: ${polymarketPrice}`);
            return;
          }
        }
      }
      
      console.log('⚠️  Could not extract price from Polymarket market data');
    } else {
      console.log('⚠️  No active Bitcoin Up or Down markets found');
    }
  } catch (error) {
    console.error('❌ Error fetching Polymarket price:', error.message);
  }
}

// Poll Polymarket every 10 seconds (they don't have public WebSocket)
setInterval(fetchPolymarketPrice, 10000);
fetchPolymarketPrice();

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
      </style>
    </head>
    <body>
      <h1>🚀 BTC Price WebSocket Server</h1>
      <div class="status">✅ Server is running</div>
      <div class="price">💰 Coinbase BTC: $${coinbasePrice || 'Loading...'}</div>
      <div class="price">📊 Polymarket BTC: $${polymarketPrice || 'Loading...'}</div>
      <p>Connect to WebSocket: <code>wss://${req.headers.host}</code></p>
      <p>Active connections: ${wss.clients.size}</p>
    </body>
    </html>
  `);
});

app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    coinbase: coinbasePrice, 
    polymarket: polymarketPrice,
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
});
