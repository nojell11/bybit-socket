import express from 'express';
import { WebSocketServer } from 'ws';
import { WebSocket } from 'ws';

const app = express();
const PORT = process.env.PORT || 3000;
app.use(express.static('public')); // Serve dashboard files

const server = app.listen(PORT, () => console.log(`Server on port ${PORT}`));

const wss = new WebSocketServer({ server });

const clients = new Set(); // Track connected browsers

wss.on('connection', (ws) => {
  clients.add(ws);
  ws.send(JSON.stringify({ type: 'connected' }));
  ws.on('close', () => clients.delete(ws));
});

let prices = { coinbase: null, kraken: null };

// Coinbase Advanced Trade WebSocket
const cbWs = new WebSocket('wss://advanced-trade-ws.coinbase.com');
cbWs.on('open', () => {
  cbWs.send(JSON.stringify({
    type: 'subscribe',
    product_ids: ['BTC-USD'],
    channel: 'ticker',
    jwt: undefined // No auth for public ticker
  }));
});
cbWs.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.type === 'ticker' && msg.price) {
    prices.coinbase = { price: parseFloat(msg.price), ts: Date.now() };
    broadcastPrices();
  }
});

// Kraken Spot WebSocket (v2)
const krWs = new WebSocket('wss://ws.kraken.com/v2');
krWs.on('open', () => {
  krWs.send(JSON.stringify({
    method: 'subscribe',
    params: { channel: 'ticker', symbol: 'BTC/USD' },
    req_id: Date.now()
  }));
});
krWs.on('message', (data) => {
  const msg = JSON.parse(data);
  if (msg.method === 'ticker' && msg.result?.c?.[0]) {
    prices.kraken = { price: parseFloat(msg.result.c[0]), ts: Date.now() };
    broadcastPrices();
  }
});

function broadcastPrices() {
  const payload = { prices, ts: Date.now() };
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(payload));
    }
  }
}
