import websocket
import ssl
import json
import time
import requests
from collections import defaultdict

# Order book storage
bids = {}
asks = {}

def get_rest_snapshot():
    """Get initial order book snapshot from REST API"""
    global bids, asks
    url = "https://api.coinbase.com/api/v3/brokerage/products/BTC-USD/book?level=2"
    response = requests.get(url, timeout=10)
    data = response.json()
    
    bids.clear()
    asks.clear()
    
    for bid in data['pricebooks'][0]['bids']:
        price = float(bid[0])
        size = float(bid[1])
        bids[price] = size
    
    for ask in data['pricebooks'][0]['asks']:
        price = float(ask[0])
        size = float(ask[1])
        asks[price] = size
    
    top_bid = max(bids.keys()) if bids else 0
    top_ask = min(asks.keys()) if asks else 0
    print(f"REST Snapshot: Bid {top_bid:.2f} | Ask {top_ask:.2f}")

def on_open(ws):
    print("Connected to Coinbase Advanced Trade")
    # Get REST snapshot FIRST
    get_rest_snapshot()
    
    # Then subscribe
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
    
    if data.get('channel') == 'level2' and data.get('product_id') == 'BTC-USD':
        changes = data.get('changes', [])
        for change in changes:
            side, price_str, size_str = change
            price = float(price_str)
            size = float(size_str)
            
            if size == 0:
                if side == 'bid':
                    bids.pop(price, None)
                elif side == 'ask':
                    asks.pop(price, None)
            else:
                if side == 'bid':
                    bids[price] = size
                elif side == 'ask':
                    asks[price] = size
        
        # Print top bid/ask every update
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
