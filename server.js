// Test latency to Polymarket
const testLatency = async () => {
  const start = Date.now();
  await fetch('https://clob.polymarket.com/markets');
  const latency = Date.now() - start;
  console.log(`🚀 Latency to Polymarket: ${latency}ms`);
  return latency;
};

// Run on startup
testLatency();
import express from 'express';
import { WebSocketServer } from 'ws';
import { WebSocket } from 'ws';

const app = express();
const PORT = process.env.PORT || 8080;
app.use(express.static('public'));

const server = app.listen(PORT, () => console.log(`Server on port ${PORT}`));

const wss = new WebSocketServer({ server });

const clients = new Set();

wss.on('connection', (ws) => {
  console.log('👤 Client connected (total:', clients.size, ')');
  clients.add(ws);
  ws.send(JSON.stringify({ type: 'connected', prices: {} }));
  
  ws.on('close', () => {
    console.log('👤 Client disconnected');
    clients.delete(ws);
  });
  
  // Ping clients every 30s (Railway WS keepalive)
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.ping();
  }, 30000);
  
  ws.on('pong', () => console.log('🏓 Client pong'));
});

let prices = { coinbase: null, kraken: null };

let reconnectCB = 0, reconnectKR = 0;
const MAX_RECONNECT = 10;

function broadcastPrices() {
  const safe = {};
  if (prices.coinbase?.price) safe.coinbase = prices.coinbase;
  if (prices.kraken?.price) safe.kraken = prices.kraken;
  const payload = { prices: safe, ts: Date.now() };
  console.log('📡 Broadcasting:', JSON.stringify(payload).slice(0, 80) + '...');
  
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(payload));
    }
  }
}

// Heartbeat
setInterval(broadcastPrices, 30000);

function connectCoinbase() {
  console.log('🔵 Connecting Coinbase...');
  const ws = new WebSocket('wss://advanced-trade-ws.coinbase.com');
  
  ws.on('open', () => {
    console.log('🔵 Coinbase CONNECTED');
    reconnectCB = 0;
    ws.send(JSON.stringify({
      type: 'subscribe',
      product_ids: ['BTC-USD'],
      channel: 'ticker'
    }));
  });
  
  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      console.log('🔵 Coinbase RAW:', JSON.stringify(msg).slice(0, 100));
      if (msg.type === 'ticker' && msg.price) {
        const price = parseFloat(msg.price);
        console.log('💰 Coinbase TICK:', price);
        prices.coinbase = { price, ts: Date.now() };
        broadcastPrices();
      }
    } catch (e) {
      console.error('🔵 Coinbase ERROR:', e);
    }
  });
  
  ws.on('close', () => {
    console.log('🔵 Coinbase DISCONNECTED');
    if (reconnectCB++ < MAX_RECONNECT) setTimeout(connectCoinbase, 2000 * reconnectCB);
  });
  
  ws.on('error', (err) => console.error('🔵 Coinbase WS ERROR:', err.message));
}

function connectKraken() {
  console.log('🔴 Connecting Kraken...');
  const ws = new WebSocket('wss://ws.kraken.com');
  
  ws.on('open', () => {
    console.log('🔴 Kraken CONNECTED');
    reconnectKR = 0;
    ws.send(JSON.stringify({
      event: 'subscribe',
      pair: ['XBT/USD'],
      subscription: { name: 'ticker' }
    }));
  });
  
  ws.on('message', (data) => {
    try {
      const msgs = JSON.parse(data.toString());
      if (Array.isArray(msgs) && msgs[1]?.c) {
        const price = parseFloat(msgs[1].c[0]);
        console.log('💰 Kraken TICK:', price);
        prices.kraken = { price, ts: Date.now() };
        broadcastPrices();
      }
    } catch (e) {
      console.error('🔴 Kraken ERROR:', e);
    }
  });
  
  ws.on('close', () => {
    console.log('🔴 Kraken DISCONNECTED');
    if (reconnectKR++ < MAX_RECONNECT) setTimeout(connectKraken, 2000 * reconnectKR);
  });
  
  ws.on('error', (err) => console.error('🔴 Kraken WS ERROR:', err.message));
}

// START
connectCoinbase();
connectKraken();
