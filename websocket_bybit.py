import websocket
import ssl
import json
import time
import requests

top_bid = 0.0
top_ask = 0.0

def get_orderbook_snapshot():
    """Get current best bid/ask from public REST API"""
    global top_bid, top_ask
    try:
        url = "https://api.coinbase.com/api/v3/brokerage/product_book?product_id=BTC-USD&limit=1"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if 'pricebooks' in data and data['pricebooks']:
            book = data['pricebooks'][0]
            if book['bids']:
                top_bid = float(book['bids'][0][0])
            if book['asks']:
                top_ask = float(book['asks'][0][0])
            print(f"SNAPSHOT: Bid {top_bid:.2f} | Ask {top_ask:.2f}")
    except Exception as e:
        print(f"Snapshot error: {e}")

def on_open(ws):
    print("Connected to Coinbase Advanced Trade")
    get_orderbook_snapshot()
    
    sub_msg = [{
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channels": ["level2"]
    }, {
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channels": ["heartbeats"]
    }]
    for msg in sub_msg:
        ws.send(json.dumps(msg))

def on_message(ws, message):
    global top_bid, top_ask
    try:
        data = json.loads(message)
        
        if data.get('type') == 'heartbeat':
            print(f"Heartbeat: {data.get('sequence', 'N/A')}")
            return
        
        if data.get('channel') == 'level2':
            changes = data.get('changes', [])
            for change in changes:
                side, price, size = change
                price = float(price)
                size = float(size)
                
                if size > 0:  # Update top levels only
                    if side == 'bid' and price > top_bid:
                        top_bid = price
                    elif side == 'ask' and (top_ask == 0 or price < top_ask):
                        top_ask = price
            
            print(f"BTC-USD: Bid {top_bid:.2f} | Ask {top_ask:.2f} | Time: {time.time():.0f}")
            
    except json.JSONDecodeError:
        print("JSON decode error:", message[:100])

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
