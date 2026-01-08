#!/usr/bin/env python3
import sys
import os

# Force unbuffered output for Railway logs
sys.stdout.reconfigure(line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

print("🔄 Script starting...", flush=True)

import websocket
import ssl
import json
import time
import threading
import requests
from datetime import datetime

print("✅ All imports successful", flush=True)

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

def get_active_poly_market():
    """Get current 15-min BTC market using correct slug format"""
    try:
        timestamp = get_current_15min_window()
        slug = build_market_slug(timestamp)
        tid = int(time.time() * 1000)
        url = f"https://gamma-api.polymarket.com/events/slug/{slug}?tid={tid}"
        
        print(f"📡 Fetching: {slug}", flush=True)
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}", flush=True)
        
        if response.status_code != 200:
            print(f"   Failed: {response.text[:150]}", flush=True)
            return None, None, None
        
        data = response.json()
        
        if not data.get('markets') or len(data['markets']) == 0:
            print("   No markets in response", flush=True)
            return None, None, None
        
        market = data['markets'][0]
        clob_token_ids = market.get('clobTokenIds')
        
        if not clob_token_ids:
            print("   No clobTokenIds field", flush=True)
            return None, None, None
        
        # Parse JSON string to get token IDs
        token_ids = json.loads(clob_token_ids)
        question = market.get('question', 'BTC 15-min')
        accepting_orders = market.get('acceptingOrders', False)
        
        print(f"✅ Market: {question}", flush=True)
        print(f"   Token UP: {token_ids[0]}", flush=True)
        print(f"   Token DOWN: {token_ids[1]}", flush=True)
        print(f"   Accepting orders: {accepting_orders}", flush=True)
        
        return token_ids[0], token_ids[1], question
        
    except Exception as e:
        print(f"❌ Poly API error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None, None, None

def format_output():
    """Print side-by-side comparison"""
    spread = abs(poly_down_price - poly_up_price) if poly_down_price > 0 else 0
    
    output = "\n" + "="*70 + "\n"
    output += f"🔵 COINBASE BTC = ${coinbase_price:.2f}\n"
    output += f"🟣 POLYMARKET {current_question[:45]}\n"
    output += f"   UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢ | Spread: {spread:.2f}¢\n"
    output += "="*70
    print(output, flush=True)

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
        except Exception as e:
            print(f"❌ Coinbase parse error: {e}", flush=True)
    
    def on_open(ws):
        print("✅ Coinbase connected", flush=True)
        ws.send(json.dumps({
            "type": "subscribe",
            "product_ids": ["BTC-USD"],
            "channel": "level2"
        }))
    
    def on_error(ws, error):
        print(f"❌ Coinbase error: {error}", flush=True)
    
    try:
        ws = websocket.WebSocketApp("wss://advanced-trade-ws.coinbase.com",
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"❌ Coinbase crashed: {e}", flush=True)

def polymarket_ws():
    global poly_up_price, poly_down_price, current_question
    
    token_id_up, token_id_down, question = get_active_poly_market()
    if not token_id_up:
        print("❌ No Polymarket market available", flush=True)
        return
    
    current_question = question
    print(f"🔄 Connecting to Polymarket WebSocket...", flush=True)
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price
        try:
            print(f"📥 Poly: {message[:150]}...", flush=True)
            data = json.loads(message)
            asset_id = data.get('asset_id', '')
            
            # Parse orderbook
            if data.get('bids') and len(data['bids']) > 0:
                best_bid = float(data['bids'][0].get('price', 0)) * 100
                
                if asset_id == token_id_up:
                    poly_up_price = best_bid
                    print(f"   UP price: {poly_up_price:.2f}¢", flush=True)
                elif asset_id == token_id_down:
                    poly_down_price = best_bid
                    print(f"   DOWN price: {poly_down_price:.2f}¢", flush=True)
                
                if coinbase_price > 0 and poly_up_price > 0 and poly_down_price > 0:
                    format_output()
        except Exception as e:
            print(f"❌ Poly parse: {e}", flush=True)
    
    def on_open(ws):
        print("✅ Polymarket WebSocket opened", flush=True)
        try:
            sub_msg = {
                "assets_ids": [token_id_up, token_id_down],
                "type": "market"
            }
            print(f"📤 Subscribing to tokens...", flush=True)
            ws.send(json.dumps(sub_msg))
            print("✅ Polymarket subscribed", flush=True)
        except Exception as e:
            print(f"❌ Subscription failed: {e}", flush=True)
    
    def on_error(ws, error):
        print(f"❌ Polymarket error: {error}", flush=True)
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Polymarket closed: {close_status_code}", flush=True)
    
    def keep_alive(ws):
        time.sleep(15)
        while True:
            try:
                print("💓 PING", flush=True)
                ws.send("PING")
                time.sleep(10)
            except Exception as e:
                print(f"❌ PING failed: {e}", flush=True)
                break
    
    def on_open_with_keepalive(ws):
        on_open(ws)
        ping_thread = threading.Thread(target=keep_alive, args=(ws,), daemon=True)
        ping_thread.start()
    
    try:
        # CORRECT URL with /ws/market path
        ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com/ws/market",
                                    on_open=on_open_with_keepalive,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        print("🔄 Starting WebSocket...", flush=True)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"❌ Polymarket crashed: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Coinbase vs Polymarket Arb Monitor\n", flush=True)
    
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    print("🔄 Starting Polymarket thread...", flush=True)
    t2.start()
    time.sleep(3)
    
    print("🔄 Starting Coinbase thread...", flush=True)
    t1.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped", flush=True)
