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
let updateCount = 0;

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

// Connect to Kraken WebSocket (Alternative to Polymarket)
function connectKraken() {
  const krakenWs = new WebSocket('wss://ws.kraken.com/');
  
  krakenWs.on('open', () => {
    console.log('✅ Connected to Kraken WebSocket');
    krakenWs.send(JSON.stringify({
      event: 'subscribe',
      pair: ['XBT/USD'],
      subscription: { name: 'ticker' }
    }));
  });

  krakenWs.on('message', (data) => {
    try {
      const msg = JSON.parse(data);
      if (Array.isArray(msg) && msg[2] === 'ticker') {
        const tickerData = msg[1];
        if (tickerData.c && tickerData.c[0]) {
          polymarketPrice = parseFloat(tickerData.c[0]).toFixed(2);
          broadcastPrices();
        }
      }
    } catch (error) {
      // Ignore parse errors
    }
  });

  krakenWs.on('error', (error) => {
    console.error('❌ Kraken WebSocket error:', error.message);
  });

  krakenWs.on('close', () => {
    console.log('⚠️  Kraken connection closed. Reconnecting...');
    setTimeout(connectKraken, 5000);
  });
}

// Broadcast prices to all connected clients
function broadcastPrices() {
  const cbPrice = coinbasePrice ? parseFloat(coinbasePrice) : null;
  const pmPrice = polymarketPrice ? parseFloat(polymarketPrice) : null;
  
  const message = {
    coinbase: coinbasePrice,
    kraken: polymarketPrice,
    difference: cbPrice && pmPrice ? Math.abs(cbPrice - pmPrice).toFixed(2) : null,
    percentDiff: cbPrice && pmPrice ? 
      ((Math.abs(cbPrice - pmPrice) / cbPrice) * 100).toFixed(4) : null,
    timestamp: new Date().toISOString(),
    updateCount: updateCount
  };

  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  });
}

// Log prices every second + broadcast
setInterval(() => {
  updateCount++;
  
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`UPDATE #${updateCount} | ${new Date().toLocaleTimeString()}`);
  console.log(`COINBASE BTC : $${coinbasePrice || 'Loading...'}`);
  console.log(`KRAKEN BTC   : $${polymarketPrice || 'Loading...'}`);
  
  if (coinbasePrice && polymarketPrice) {
    const diff = Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice));
    const pct = ((diff / parseFloat(coinbasePrice)) * 100).toFixed(4);
    console.log(`DIFFERENCE   : $${diff.toFixed(2)} (${pct}%)`);
  }
  
  console.log(`CLIENTS      : ${wss.clients.size}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  // Broadcast to all connected clients
  broadcastPrices();
}, 1000);

// Handle client connections
wss.on('connection', (ws) => {
  console.log('🔌 New client connected. Total clients:', wss.clients.size);
  
  // Send current prices immediately
  ws.send(JSON.stringify({
    coinbase: coinbasePrice,
    kraken: polymarketPrice,
    timestamp: new Date().toISOString()
  }));

  ws.on('close', () => {
    console.log('🔌 Client disconnected. Total clients:', wss.clients.size);
  });
});

// Web interface route
app.get('/', (req, res) => {
  const diff = coinbasePrice && polymarketPrice ? 
    Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice)) : 0;
  
  // Detect if Railway deployment
  const wsProtocol = req.headers.host.includes('railway.app') ? 'wss' : 'ws';
  const wsUrl = `${wsProtocol}://${req.headers.host}`;
  
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>BTC Price Monitor - Live</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
          padding: 20px;
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
          font-size: 32px;
        }
        .status {
          text-align: center;
          padding: 15px;
          border-radius: 10px;
          margin: 20px 0;
          font-weight: bold;
          transition: all 0.3s;
        }
        .status.connected {
          background: #d4edda;
          color: #155724;
        }
        .status.disconnected {
          background: #f8d7da;
          color: #721c24;
        }
        .price-card {
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
          border-radius: 15px;
          padding: 25px;
          margin: 15px 0;
          transition: transform 0.3s, box-shadow 0.3s;
        }
        .price-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        .label {
          font-size: 13px;
          color: #7f8c8d;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 8px;
        }
        .price {
          font-size: 36px;
          font-weight: bold;
          color: #2c3e50;
          font-family: 'Courier New', monospace;
        }
        .diff {
          text-align: center;
          font-size: 16px;
          font-weight: bold;
          margin: 20px 0;
          padding: 15px;
          border-radius: 10px;
          background: #fff3cd;
        }
        .info {
          text-align: center;
          color: #7f8c8d;
          font-size: 12px;
          margin-top: 25px;
          line-height: 1.8;
        }
        code {
          background: #ecf0f1;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 11px;
        }
        .pulse {
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        .update-indicator {
          display: inline-block;
          width: 10px;
          height: 10px;
          background: #27ae60;
          border-radius: 50%;
          margin-left: 8px;
          animation: blink 1s infinite;
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.2; }
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🚀 BTC Price Monitor <span class="update-indicator"></span></h1>
        <div class="status disconnected" id="status">⏳ Connecting...</div>
        
        <div class="price-card">
          <div class="label">💰 Coinbase BTC/USD</div>
          <div class="price" id="coinbase-price">$${coinbasePrice || '---'}</div>
        </div>
        
        <div class="price-card">
          <div class="label">📊 Kraken BTC/USD</div>
          <div class="price" id="kraken-price">$${polymarketPrice || '---'}</div>
        </div>
        
        <div class="diff" id="diff">
          ${diff > 0 ? `📈 Difference: $${diff.toFixed(2)}` : '⏳ Waiting for data...'}
        </div>
        
        <div class="info">
          <p><strong>WebSocket:</strong> <code>${wsUrl}</code></p>
          <p><strong>Active Connections:</strong> <span id="clients">${wss.clients.size}</span></p>
          <p><strong>Updates:</strong> <span id="updates">0</span> | <strong>Last Update:</strong> <span id="time">---</span></p>
          <p style="margin-top: 15px; font-size: 11px; color: #95a5a6;">
            Real-time BTC price comparison between Coinbase and Kraken exchanges.
            Updates every second via WebSocket. Deployed on Railway.
          </p>
        </div>
      </div>
      
      <script>
        const ws = new WebSocket('${wsUrl}'.replace('http', 'ws'));
        const statusEl = document.getElementById('status');
        const coinbasePriceEl = document.getElementById('coinbase-price');
        const krakenPriceEl = document.getElementById('kraken-price');
        const diffEl = document.getElementById('diff');
        const timeEl = document.getElementById('time');
        const updatesEl = document.getElementById('updates');
        
        ws.onopen = () => {
          console.log('✅ WebSocket connected');
          statusEl.textContent = '✅ Live - Connected';
          statusEl.className = 'status connected';
        };
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          // Update prices
          if (data.coinbase) {
            coinbasePriceEl.textContent = '$' + data.coinbase;
            coinbasePriceEl.classList.add('pulse');
            setTimeout(() => coinbasePriceEl.classList.remove('pulse'), 300);
          }
          
          if (data.kraken) {
            krakenPriceEl.textContent = '$' + data.kraken;
            krakenPriceEl.classList.add('pulse');
            setTimeout(() => krakenPriceEl.classList.remove('pulse'), 300);
          }
          
          // Update difference
          if (data.difference) {
            const diff = parseFloat(data.difference);
            const pct = data.percentDiff || 0;
            diffEl.textContent = \`📈 Difference: $\${diff.toFixed(2)} (\${pct}%)\`;
            diffEl.style.color = diff > 10 ? '#e74c3c' : '#27ae60';
          }
          
          // Update timestamp
          if (data.timestamp) {
            const time = new Date(data.timestamp);
            timeEl.textContent = time.toLocaleTimeString();
          }
          
          // Update counter
          if (data.updateCount) {
            updatesEl.textContent = data.updateCount;
          }
        };
        
        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          statusEl.textContent = '❌ Connection Error';
          statusEl.className = 'status disconnected';
        };
        
        ws.onclose = () => {
          console.log('⚠️ WebSocket disconnected');
          statusEl.textContent = '⚠️ Disconnected - Reconnecting...';
          statusEl.className = 'status disconnected';
          setTimeout(() => window.location.reload(), 3000);
        };
      </script>
    </body>
    </html>
  `);
});

// Health check endpoint for Railway
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    coinbase: coinbasePrice, 
    kraken: polymarketPrice,
    difference: coinbasePrice && polymarketPrice ? 
      Math.abs(parseFloat(coinbasePrice) - parseFloat(polymarketPrice)).toFixed(2) : null,
    clients: wss.clients.size,
    updates: updateCount,
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📡 WebSocket endpoint: ws://localhost:${PORT}`);
  console.log(`🌐 Web interface: http://localhost:${PORT}`);
  console.log(`💚 Health check: http://localhost:${PORT}/health`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  
  // Connect to data sources
  connectCoinbase();
  connectKraken();
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('⚠️  SIGTERM received, closing server...');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});
