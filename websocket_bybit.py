import websocket
import ssl
import json
import time

top_bid = 0.0
top_ask = 0.0

def on_open(ws):
    print("✅ Connected to Coinbase Advanced Trade")
    
    sub_msg = {
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channel": "level2"
    }
    ws.send(json.dumps(sub_msg))

def on_message(ws, message):
    global top_bid, top_ask
    data = json.loads(message)
    
    # Coinbase uses 'l2_data' channel
    if data.get('channel') == 'l2_data':
        events = data.get('events', [])
        for event in events:
            if event.get('type') == 'snapshot':
                # Initial snapshot
                updates = event.get('updates', [])
                for update in updates:
                    price = float(update['price_level'])
                    qty = float(update['new_quantity'])
                    if qty > 0:
                        if update['side'] == 'bid' and price > top_bid:
                            top_bid = price
                        elif update['side'] == 'offer' and (top_ask == 0 or price < top_ask):
                            top_ask = price
                print(f"📸 SNAPSHOT: Bid ${top_bid:.2f} | Ask ${top_ask:.2f}")
                
            elif event.get('type') == 'update':
                # Live updates
                updates = event.get('updates', [])
                for update in updates:
                    price = float(update['price_level'])
                    qty = float(update['new_quantity'])
                    
                    if update['side'] == 'bid':
                        if qty > 0 and price > top_bid:
                            top_bid = price
                    elif update['side'] == 'offer':
                        if qty > 0 and (top_ask == 0 or price < top_ask):
                            top_ask = price
                
                # Print every update
                if top_bid > 0 and top_ask > 0:
                    spread = top_ask - top_bid
                    print(f"💰 BTC-USD: Bid ${top_bid:.2f} | Ask ${top_ask:.2f} | Spread ${spread:.2f}")

def on_error(ws, error):
    print(f"❌ Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 Closed")

if __name__ == "__main__":
    ws_url = "wss://advanced-trade-ws.coinbase.com"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
