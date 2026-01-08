import websocket
import ssl
import json
import time

def on_open(ws):
    print("✅ Connected to Coinbase Advanced Trade")
    
    # Coinbase Advanced Trade subscription format
    sub_msg = {
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channel": "level2"
    }
    print(f"📤 Sending: {json.dumps(sub_msg)}")
    ws.send(json.dumps(sub_msg))

def on_message(ws, message):
    print(f"📥 RAW MESSAGE: {message}")  # Debug: see everything
    
    try:
        data = json.loads(message)
        print(f"📊 PARSED: {data.get('type', 'unknown')} | {data.get('channel', 'N/A')}")
        
        # Handle different message types
        if data.get('channel') == 'subscriptions':
            print(f"✅ Subscribed to: {data.get('product_ids', [])}")
        
        elif data.get('channel') == 'l2_data':
            print(f"💰 L2 Data received")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON Error: {e}")

def on_error(ws, error):
    print(f"❌ WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 Closed: {close_status_code} - {close_msg}")

if __name__ == "__main__":
    websocket.enableTrace(True)  # Full debug mode
    ws_url = "wss://advanced-trade-ws.coinbase.com"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
