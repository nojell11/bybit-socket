import websocket
import ssl
import json
import time
import threading
import requests
import traceback

# Price storage
coinbase_price = 0.0
poly_up_price = 0.0
poly_down_price = 0.0
last_update = time.time()

def get_active_poly_market():
    """Get current active BTC 15-min market token IDs"""
    try:
        # Use Gamma API for active markets
        url = "https://gamma-api.polymarket.com/markets?active=true&closed=false"
        response = requests.get(url, timeout=10)
        print(f"📡 Polymarket API status: {response.status_code}")
        
        data = response.json()
        print(f"📊 Response type: {type(data)}, length: {len(data) if isinstance(data, list) else 'N/A'}")
        
        # Handle if data is a list
        markets = data if isinstance(data, list) else data.get('data', [])
        
        for market in markets:
            if not isinstance(market, dict):
                continue
                
            question = market.get('question', '').lower()
            print(f"🔍 Market: {question[:60]}")
            
            if ('btc' in question or 'bitcoin' in question) and ('15' in question or 'minute' in question):
                tokens = market.get('tokens', [])
                if len(tokens) >= 2:
                    print(f"✅ Found BTC market: {market['question']}")
                    return tokens[0].get('token_id'), tokens[1].get('token_id')
        
        print("⚠️ No BTC 15-min market found")
        return None, None
        
    except Exception as e:
        print(f"❌ Poly API error: {e}")
        traceback.print_exc()
        return None, None

def format_output():
    """Print side-by-side comparison"""
    spread = poly_down_price - poly_up_price if poly_down_price > 0 else 0
    
    print("\n" + "="*60)
    print(f"🔵 COINBASE BTC = ${coinbase_price:.2f}")
    print(f"🟣 POLYMARKET UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢")
    print(f"📊 Spread: {spread:.2f}¢")
    print("="*60)

# Coinbase WebSocket
def coinbase_ws():
    global coinbase_price, last_update
    
    def on_message(ws, message):
        global coinbase_price, last_update
        try:
            data = json.loads(message)
            
            if data.get('channel') == 'l2_data':
                events = data.get('events', [])
                for event in events:
                    updates = event.get('updates', [])
                    for update in updates:
                        if update['side'] == 'bid' and float(update['new_quantity']) > 0:
                            price = float(update['price_level'])
                            if price > coinbase_price * 0.99:
                                coinbase_price = price
                                last_update = time.time()
                                if poly_up_price > 0:
                                    format_output()
                            break
        except Exception as e:
            print(f"❌ Coinbase error: {e}")
    
    def on_open(ws):
        print("✅ Coinbase connected")
        ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": ["BTC-USD"],
            "channel": "level2"
        }))
    
    try:
        ws = websocket.WebSocketApp("wss://advanced-trade-ws.coinbase.com",
                                    on_open=on_open,
                                    on_message=on_message)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"❌ Coinbase crashed: {e}")

# Polymarket WebSocket
def polymarket_ws():
    global poly_up_price, poly_down_price
    
    try:
        token_id_1, token_id_2 = get_active_poly_market()
        if not token_id_1:
            print("❌ No Polymarket data - Coinbase-only mode")
            return
        
        def on_message(ws, message):
            global poly_up_price, poly_down_price
            try:
                data = json.loads(message)
                print(f"🟣 Poly message: {json.dumps(data)[:150]}...")
                
                # Parse based on actual Polymarket CLOB format
                if data.get('type') == 'book':
                    price = float(data.get('price', 0))
                    asset_id = data.get('asset_id', '')
                    
                    if asset_id == token_id_1:
                        poly_up_price = price * 100
                    elif asset_id == token_id_2:
                        poly_down_price = price * 100
                    
                    format_output()
                    
            except Exception as e:
                print(f"❌ Poly parse: {e}")
        
        def on_open(ws):
            print(f"✅ Polymarket connected")
            # Subscribe to both token order books
            for token_id in [token_id_1, token_id_2]:
                ws.send(json.dumps({
                    "auth": {},
                    "markets": [token_id],
                    "assets_ids": [token_id],
                    "type": "market"
                }))
        
        ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com",
                                    on_open=on_open,
                                    on_message=on_message)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
    except Exception as e:
        print(f"❌ Polymarket crashed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Arbitrage Monitor...\n")
    
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    t1.start()
    t2.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
