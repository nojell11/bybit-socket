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
current_question = ""

def get_current_15min_window():
    """Get current 15-minute window timestamp (aligned to clock)"""
    now = int(time.time())
    window_seconds = 15 * 60
    return (now // window_seconds) * window_seconds

def build_market_slug(timestamp):
    """Build slug: btc-updown-15m-{timestamp}"""
    return f"btc-updown-15m-{timestamp}"

def format_window_time(timestamp):
    """Format timestamp to readable time"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%I:%M %p ET")

def get_active_poly_market():
    """Get current 15-min BTC market using correct slug format"""
    try:
        timestamp = get_current_15min_window()
        slug = build_market_slug(timestamp)
        tid = int(time.time() * 1000)
        url = f"https://gamma-api.polymarket.com/events/slug/{slug}?tid={tid}"
        
        print(f"📡 Fetching: {slug}")
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Failed: {response.text[:150]}")
            return None, None, None
        
        data = response.json()
        
        if not data.get('markets') or len(data['markets']) == 0:
            print("   No markets in response")
            return None, None, None
        
        market = data['markets'][0]
        clob_token_ids = market.get('clobTokenIds')
        
        if not clob_token_ids:
            print("   No clobTokenIds field")
            return None, None, None
        
        # Parse JSON string to get token IDs
        token_ids = json.loads(clob_token_ids)
        question = market.get('question', 'BTC 15-min')
        accepting_orders = market.get('acceptingOrders', False)
        
        print(f"✅ Market: {question}")
        print(f"   Token UP: {token_ids[0]}")
        print(f"   Token DOWN: {token_ids[1]}")
        print(f"   Accepting orders: {accepting_orders}")
        
        return token_ids[0], token_ids[1], question
        
    except Exception as e:
        print(f"❌ Poly API error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def format_output():
    """Print side-by-side comparison"""
    spread = abs(poly_down_price - poly_up_price) if poly_down_price > 0 else 0
    
    print("\n" + "="*70)
    print(f"🔵 COINBASE BTC = ${coinbase_price:.2f}")
    print(f"🟣 POLYMARKET {current_question[:45]}")
    print(f"   UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢ | Spread: {spread:.2f}¢")
    print("="*70)

def coinbase_ws():
    global coinbase_price
    
    def on_message(ws, message):
        global coinbase_price
        try:
            data = json.loads(message)
            if data.get('channel') == 'l2_data':
                for event in data.get('events', []):
                    for update in event.get('updates', []):
                        if update['side'] == 'bid' and float(update['new_quantity']) > 0:
                            price = float(update['price_level'])
                            if price > coinbase_price * 0.99:
                                coinbase_price = price
                                if poly_up_price > 0:
                                    format_output()
                            break
        except:
            pass
    
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

def polymarket_ws():
    global poly_up_price, poly_down_price, current_question
    
    token_id_up, token_id_down, question = get_active_poly_market()
    if not token_id_up:
        print("❌ No Polymarket market - waiting for next window")
        return
    
    current_question = question
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price
        try:
            data = json.loads(message)
            asset_id = data.get('asset_id', '')
            
            # Parse orderbook
            if data.get('bids'):
                best_bid = float(data['bids'][0].get('price', 0)) * 100
                
                if asset_id == token_id_up:
                    poly_up_price = best_bid
                elif asset_id == token_id_down:
                    poly_down_price = best_bid
                
                if coinbase_price > 0 and poly_up_price > 0 and poly_down_price > 0:
                    format_output()
        except:
            pass
    
    def on_open(ws):
        print("✅ Polymarket connected")
        # Subscribe using correct format
        ws.send(json.dumps({
            "assets_ids": [token_id_up, token_id_down],
            "type": "market"
        }))
    
    def keep_alive(ws):
        """Send PING every 10 seconds"""
        while True:
            time.sleep(10)
            try:
                ws.send("PING")
            except:
                break
    
    def on_open_with_keepalive(ws):
        on_open(ws)
        ping_thread = threading.Thread(target=keep_alive, args=(ws,), daemon=True)
        ping_thread.start()
    
    ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com",
                                on_open=on_open_with_keepalive,
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == "__main__":
    from datetime import datetime
    print("🚀 Coinbase vs Polymarket Arb Monitor\n")
    
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    t2.start()
    time.sleep(3)
    t1.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
