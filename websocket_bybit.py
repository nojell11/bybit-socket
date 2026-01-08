import websocket
import ssl
import json
import time

# Full order book (top 10 levels)
bids = {}
asks = {}

def on_open(ws):
    print("Connected to Coinbase Advanced Trade")
    # Subscribe to level2 + heartbeats
    sub_msg = [{
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channel": "level2"
    }, {
        "type": "subscribe", 
        "product_ids": ["BTC-USD"],
        "channel": "heartbeats"
    }]
    for msg in sub_msg:
        ws.send(json.dumps(msg))

def on_message(ws, message):
    global bids, asks
    data = json.loads(message)
    
    if data.get('channel') == 'heartbeats':
        print(f"Heartbeat: {data['events'][0]['heartbeat_counter']}")
        return
    
    if data.get('channel') == 'level2':
        if data.get('type') == 'snapshot':
            # Load initial snapshot
            for bid in data['bids']:
                price = float(bid[0])
                bids[price] = float(bid[1])
            for ask in data['asks']:
                price = float(ask[0])
                asks[price] = float(ask[1])
        elif data.get('type') == 'l2update':
            # Apply deltas
            for change in data['changes']:
                side, price_str, size_str = change
                price = float(price_str)
                size = float(size_str)
                if size == 0:
                    if side == 'buy':
                        bids.pop(price, None)
                    else:
                        asks.pop(price, None)
                else:
                    if side == 'buy':
                        bids[price] = size
                    else:
                        asks[price] = size
        
        # Get top bid/ask
        top_bid = max(bids.keys()) if bids else 0.0
        top_ask = min(asks.keys()) if asks else 0.0
        print(f"BTC-USD: Bid {top_bid:.2f} | Ask {top_ask:.2f} | Time: {time.time():.0f}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

if __name__ == "__main__":
    ws_url = "wss://advanced-trade-ws.coinbase.com"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
