import websocket
import ssl
import json
import time
import threading
import requests

# Price storage
coinbase_price = 0.0
poly_up_price = 0.0
poly_down_price = 0.0
last_update = time.time()

def get_active_poly_market():
    """Get current active BTC 15-min market from Polymarket"""
    url = "https://clob.polymarket.com/markets?active=true"
    response = requests.get(url, timeout=5)
    markets = response.json()
    
    # Find BTC 15-minute market
    for market in markets:
        question = market.get('question', '').lower()
        if 'btc' in question or 'bitcoin' in question:
            if '15' in question or 'fifteen' in question:
                return market['condition_id']
    return None

def format_output():
    """Print side-by-side comparison"""
    spread = poly_down_price - poly_up_price if poly_down_price > 0 else 0
    lag = time.time() - last_update
    
    print("\n" + "="*60)
    print(f"🔵 COINBASE BTC SPOT = ${coinbase_price:.2f}")
    print(f"🟣 POLYMARKET BTC 15m = UP: {poly_up_price:.3f}¢ | DOWN: {poly_down_price:.3f}¢")
    print(f"📊 Spread: {spread:.3f}¢ | Last Update: {lag:.1f}s ago")
    print("="*60)

# Coinbase WebSocket
def coinbase_ws():
    global coinbase_price, last_update
    
    def on_message(ws, message):
        global coinbase_price, last_update
        data = json.loads(message)
        
        if data.get('channel') == 'l2_data':
            events = data.get('events', [])
            for event in events:
                updates = event.get('updates', [])
                for update in updates:
                    if update['side'] == 'bid' and float(update['new_quantity']) > 0:
                        price = float(update['price_level'])
                        if price > coinbase_price * 0.99:  # Filter noise
                            coinbase_price = price
                            last_update = time.time()
                            format_output()
                        break
    
    def on_open(ws):
        print("✅ Coinbase connected")
        ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": ["BTC-USD"],
            "channel": "level2"
        }))
    
    ws = websocket.WebSocketApp("wss://advanced-trade-ws.coinbase.com",
                                on_open=on_open,
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# Polymarket WebSocket
def polymarket_ws():
    global poly_up_price, poly_down_price, last_update
    
    market_id = get_active_poly_market()
    if not market_id:
        print("❌ No active BTC 15-min market found")
        return
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price, last_update
        data = json.loads(message)
        
        if data.get('type') == 'MARKET':
            # Parse Polymarket order book updates
            for event in data.get('events', []):
                if event.get('event_type') == 'book':
                    price = float(event.get('price', 0))
                    outcome = event.get('outcome', '')
                    
                    if 'yes' in outcome.lower() or 'up' in outcome.lower():
                        poly_up_price = price * 100  # Convert to cents
                    else:
                        poly_down_price = price * 100
                    
                    last_update = time.time()
                    format_output()
    
    def on_open(ws):
        print("✅ Polymarket connected")
        ws.send(json.dumps({
            "auth": {},
            "assets_ids": [market_id],
            "type": "MARKET"
        }))
    
    ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com",
                                on_open=on_open,
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == "__main__":
    print("🚀 Starting Arbitrage Monitor...\n")
    
    # Run both WebSockets in parallel
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
