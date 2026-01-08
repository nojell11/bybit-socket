import websocket
import ssl
import json
import time

top_bid = 0.0
top_ask = 0.0

def on_open(ws):
    print("Connected to Coinbase Advanced Trade")
    
    # Subscribe to level2 (sends snapshot automatically)
    sub_msg = {
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channels": ["level2", "heartbeats"]
    }
    ws.send(json.dumps(sub_msg))

def on_message(ws, message):
    global top_bid, top_ask
    data = json.loads(message)
    
    # Heartbeat check
    if data.get('type') == 'heartbeat':
        print(f"♥ Heartbeat")
        return
    
    # Initial snapshot
    if data.get('type') == 'snapshot':
        if data['bids']:
            top_bid = float(data['bids'][0][0])
        if data['asks']:
            top_ask = float(data['asks'][0][0])
        print(f"📸 SNAPSHOT: Bid {top_bid:.2f} | Ask {top_ask:.2f}")
        return
    
    # Live updates
    if data.get('type') == 'l2update':
        changes = data.get('changes', [])
        for change in changes:
            side, price, size = change
            price = float(price)
            
            if side == 'buy' and price > top_bid:
                top_bid = price
            elif side == 'sell' and (top_ask == 0 or price < top_ask):
                top_ask = price
        
        print(f"💰 BTC-USD: Bid {top_bid:.2f} | Ask {top_ask:.2f}")

def on_error(ws, error):
    print(f"❌ Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("🔌 Connection closed")

if __name__ == "__main__":
    ws_url = "wss://advanced-trade-ws.coinbase.com"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
