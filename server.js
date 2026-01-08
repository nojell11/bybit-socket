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
  console.log('Client connected');
  clients.add(ws);
  ws.send(JSON.stringify({ type: 'connected', prices: {} }));
  ws.on('close', () => {
    console.log('Client disconnected');
    clients.delete(ws);
  });
});

let prices = { coinbase: null, kraken: null };

let reconnectAttemptsCB = 0, reconnectAttemptsKR = 0;
const MAX_RECONNECTS = 10;

// Safe broadcast
function broadcastPrices() {
  const safePrices = {};
  if (prices.coinbase && typeof prices.coinbase.price === 'number') safePrices.coinbase = prices.coinbase;
  if (prices.kraken && typeof prices.kraken.price === 'number') safePrices.kraken = prices.kraken;
  const payload = { prices: safePrices, ts: Date.now() };
  console.log('Broadcasting:', payload);
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(payload));
    }
  }
}

// Coinbase WS (Advanced Trade)
function connectCoinbase() {
  console.log('Connecting Coinbase...');
  const ws = new WebSocket('wss://advanced-trade-ws.coinbase.com');
  ws.on('open', () => {
    console.log('Coinbase connected');
    reconnectAttemptsCB = 0;
    ws.send(JSON.stringify({
      type: 'subscribe',
      product_ids: ['BTC-USD'],
      channel: 'ticker'
    }));
  });
  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      if (msg.type === 'ticker' && msg.price) {
        const price = parseFloat(msg.price);
        console.log('Coinbase tick:', price);
        prices.coinbase = { price, ts: Date.now() };
        broadcastPrices();
      }
    } catch (e) {
      console.error('Coinbase parse error:', e);
    }
  });
  ws.on('error', (err) => console.error('Coinbase error:', err));
  ws.on('close', () => {
    console.log('Coinbase closed');
    if (reconnectAttemptsCB++ < MAX_RECONNECTS) {
      setTimeout(connectCoinbase, 2000 * reconnectAttemptsCB);
    }
  });
}

// Kraken WS v1 (works reliably)
function connectKraken() {
  console.log('Connecting Kraken...');
  const ws = new WebSocket('wss://ws.kraken.com');
  ws.on('open', () => {
    console.log('Kraken connected');
    reconnectAttemptsKR = 0;
    ws.send(JSON.stringify({
      event: 'subscribe',
      pair: ['XBT/USD'],
      subscription: { name: 'ticker' }
    }));
  });
  ws.on('message', (data) => {
    try {
      const msgs = JSON.parse(data.toString());
      if (Array.isArray(msgs) && msgs.length > 1) {
        const tickerData = msgs[1];
        if (tickerData && tickerData.c) {
          const price = parseFloat(tickerData.c[0]);
          console.log('Kraken tick:', price);
          prices.kraken = { price, ts: Date.now() };
          broadcastPrices();
        }
      }
    } catch (e) {
      console.error('Kraken parse error:', e);
    }
  });
  ws.on('error', (err) => console.error('Kraken error:', err));
  ws.on('close', () => {
    console.log('Kraken closed');
    if (reconnectAttemptsKR++ < MAX_RECONNECTS) {
      setTimeout(connectKraken, 2000 * reconnectAttemptsKR);
    }
  });
}

// Start connections
connectCoinbase();
connectKraken();

// Heartbeat every 30s
setInterval(broadcastPrices, 30000);
