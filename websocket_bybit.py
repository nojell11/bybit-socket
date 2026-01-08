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
    """Get current active BTC 15-min market from Polymarket"""
    try:
        url = "https://clob.polymarket.com/markets?active=true"
        response = requests.get(url, timeout=5)
        markets = response.json()
        
        for market in markets:
            question = market.get('question', '').lower()
            if 'btc' in question or 'bitcoin' in question:
                if '15' in question or 'fifteen' in question:
                    print(f"📍 Found market: {market['question'][:50]}")
                    return market['condition_id']
        print("⚠️ No active BTC 15-min market found")
        return None
    except Exception as e:
        print(f"❌ Poly market fetch error: {e}")
        traceback.print_exc()
        return None

def format_output():
    """Print side-by-side comparison"""
    spread = poly_down_price - poly_up_price if poly_down_price > 0 else 0
    lag = time.time() - last_update
    
    print("\n" + "="*60)
    print(f"🔵 COINBASE BTC = ${coinbase_price:.2f}")
    print(f"🟣 POLYMARKET UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢")
    print(f"📊 Spread: {spread:.2f}¢ | Lag: {lag:.1f}s")
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
                                if poly_up_price > 0:  # Only print if Poly data exists
                                    format_output()
                            break
        except Exception as e:
            print(f"❌ Coinbase parse error: {e}")
    
    def on_open(ws):
        print("✅ Coinbase connected")
        ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": ["BTC-USD"],
            "channel": "level2"
        }))
    
    def on_error(ws, error):
        print(f"❌ Coinbase WebSocket error: {error}")
    
    try:
        ws = websocket.WebSocketApp("wss://advanced-trade-ws.coinbase.com",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"❌ Coinbase thread crashed: {e}")
        traceback.print_exc()

# Polymarket WebSocket
def polymarket_ws():
    global poly_up_price, poly_down_price, last_update
    
    try:
        market_id = get_active_poly_market()
        if not market_id:
            print("❌ Skipping Polymarket (no active market)")
            return
        
        def on_message(ws, message):
            global poly_up_price, poly_down_price, last_update
            try:
                print(f"🟣 Poly raw: {message[:200]}")  # Debug first 200 chars
                data = json.loads(message)
                # Parse Polymarket data (adjust based on actual format)
                # This will show us what Polymarket actually sends
            except Exception as e:
                print(f"❌ Poly parse error: {e}")
        
        def on_open(ws):
            print(f"✅ Polymarket connected (market: {market_id[:8]}...)")
            ws.send(json.dumps({
                "auth": {},
                "assets_ids": [market_id],
                "type": "MARKET"
            }))
        
        def on_error(ws, error):
            print(f"❌ Polymarket error: {error}")
        
        ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
    except Exception as e:
        print(f"❌ Polymarket thread crashed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Arbitrage Monitor...\n")
    
    # Run both WebSockets
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    t1.start()
    t2.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
