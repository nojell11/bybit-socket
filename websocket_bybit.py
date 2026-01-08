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
current_question = ""

def get_active_poly_market():
    """Get Bitcoin Up or Down market directly"""
    try:
        # Try direct slug first
        slug_url = "https://gamma-api.polymarket.com/events/slug/bitcoin-up-or-down"
        response = requests.get(slug_url, timeout=10)
        
        if response.status_code == 200:
            event = response.json()
            print(f"✅ Found event: {event.get('title', 'Bitcoin Up or Down')}")
            
            # Get markets from event
            markets = event.get('markets', [])
            for market in markets:
                # Find the current active time window
                if market.get('active', False) and not market.get('closed', True):
                    tokens = market.get('tokens', [])
                    if len(tokens) >= 2:
                        question = market.get('question', '')
                        print(f"✅ Active window: {question}")
                        print(f"   Token IDs: {tokens[0].get('token_id')[:8]}..., {tokens[1].get('token_id')[:8]}...")
                        return tokens[0].get('token_id'), tokens[1].get('token_id'), question
        
        # Fallback: Search all markets
        print("🔄 Trying search fallback...")
        search_url = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=200"
        response = requests.get(search_url, timeout=10)
        
        if response.status_code == 200:
            markets = response.json()
            for market in markets:
                if not isinstance(market, dict):
                    continue
                question = market.get('question', '').lower()
                
                if 'bitcoin' in question and ('up' in question or 'down' in question):
                    tokens = market.get('tokens', [])
                    if len(tokens) >= 2:
                        print(f"✅ Found via search: {market['question']}")
                        return tokens[0].get('token_id'), tokens[1].get('token_id'), market['question']
        
        print("❌ Bitcoin Up or Down market not found")
        return None, None, None
        
    except Exception as e:
        print(f"❌ API error: {e}")
        traceback.print_exc()
        return None, None, None

def format_output():
    """Print side-by-side comparison"""
    spread = abs(poly_down_price - poly_up_price) if poly_down_price > 0 else 0
    
    print("\n" + "="*70)
    print(f"🔵 COINBASE BTC SPOT = ${coinbase_price:.2f}")
    print(f"🟣 POLYMARKET {current_question[:40]}")
    print(f"   UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢ | Spread: {spread:.2f}¢")
    print("="*70)

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
                            if price > coinbase_price * 0.99:  # Filter noise
                                coinbase_price = price
                                last_update = time.time()
                                if poly_up_price > 0:  # Only print if Poly connected
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
    
    def on_error(ws, error):
        print(f"❌ Coinbase WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Coinbase closed")
    
    try:
        ws = websocket.WebSocketApp("wss://advanced-trade-ws.coinbase.com",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"❌ Coinbase crashed: {e}")
        traceback.print_exc()

# Polymarket WebSocket
def polymarket_ws():
    global poly_up_price, poly_down_price, current_question
    
    try:
        token_id_1, token_id_2, question = get_active_poly_market()
        if not token_id_1:
            print("❌ Polymarket skipped - no active market")
            return
        
        current_question = question
        print(f"📍 Monitoring: {question}")
        
        def on_message(ws, message):
            global poly_up_price, poly_down_price
            try:
                data = json.loads(message)
                
                # Debug first few messages
                if poly_up_price == 0:
                    print(f"🟣 Poly msg type: {data.get('type', 'unknown')}")
                
                # Handle book updates
                if data.get('type') == 'book':
                    asset_id = data.get('asset_id', '')
                    bids = data.get('bids', [])
                    asks = data.get('asks', [])
                    
                    # Get best bid price
                    if bids and len(bids) > 0:
                        best_bid = float(bids[0].get('price', 0))
                        
                        if asset_id == token_id_1:
                            poly_up_price = best_bid * 100  # Convert to cents
                        elif asset_id == token_id_2:
                            poly_down_price = best_bid * 100
                
                # Handle trade/price updates
                elif data.get('type') == 'price_change':
                    asset_id = data.get('asset_id', '')
                    price = float(data.get('price', 0))
                    
                    if asset_id == token_id_1:
                        poly_up_price = price * 100
                    elif asset_id == token_id_2:
                        poly_down_price = price * 100
                
                # Print when both prices exist
                if poly_up_price > 0 and poly_down_price > 0 and coinbase_price > 0:
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
                print(f"   Subscribed to token: {token_id[:8]}...")
        
        def on_error(ws, error):
            print(f"❌ Polymarket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print(f"🔌 Polymarket closed")
        
        ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
    except Exception as e:
        print(f"❌ Polymarket crashed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting Coinbase vs Polymarket Arbitrage Monitor...\n")
    
    # Run both WebSockets in parallel
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    t1.start()
    time.sleep(2)  # Let Polymarket fetch market first
    t2.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
