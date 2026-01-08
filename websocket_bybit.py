#!/usr/bin/env python3
import sys
import os

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

import websocket
import ssl
import json
import time
import threading
import requests
from datetime import datetime

# Price storage
coinbase_price = 0.0
poly_up_price = 0.0
poly_down_price = 0.0

def get_current_15min_window():
    """Get current 15-minute window timestamp"""
    now = int(time.time())
    window_seconds = 15 * 60
    return (now // window_seconds) * window_seconds

def build_market_slug(timestamp):
    """Build slug: btc-updown-15m-{timestamp}"""
    return f"btc-updown-15m-{timestamp}"

def get_active_poly_market():
    """Get current 15-min BTC market"""
    try:
        timestamp = get_current_15min_window()
        slug = build_market_slug(timestamp)
        tid = int(time.time() * 1000)
        url = f"https://gamma-api.polymarket.com/events/slug/{slug}?tid={tid}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return None, None, None
        
        data = response.json()
        
        if not data.get('markets') or len(data['markets']) == 0:
            return None, None, None
        
        market = data['markets'][0]
        clob_token_ids = market.get('clobTokenIds')
        
        if not clob_token_ids:
            return None, None, None
        
        token_ids = json.loads(clob_token_ids)
        question = market.get('question', 'BTC 15-min')
        
        return token_ids[0], token_ids[1], question
        
    except Exception as e:
        return None, None, None

def format_output():
    """Print prices - simple format"""
    # Calculate Polymarket mid price
    poly_mid = (poly_up_price + poly_down_price) / 2 if poly_down_price > 0 else 0
    
    # Clear previous lines (optional, comment out if you want scrolling)
    print("\033[2J\033[H", end='', flush=True)  # Clear screen
    
    print(f"COINBASE BTC PRICE   = ${coinbase_price:,.2f}", flush=True)
    print(f"POLYMARKET BTC PRICE = {poly_mid:.2f}¢ (UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢)", flush=True)
    print(f"Updated: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", flush=True)

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
    except:
        pass

def polymarket_ws():
    global poly_up_price, poly_down_price
    
    token_id_up, token_id_down, question = get_active_poly_market()
    if not token_id_up:
        print("❌ No Polymarket market available")
        return
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price
        try:
            data = json.loads(message)
            asset_id = data.get('asset_id', '')
            
            # Handle orderbook snapshot
            if data.get('bids') and len(data['bids']) > 0:
                best_bid = float(data['bids'][0].get('price', 0)) * 100
                
                if asset_id == token_id_up:
                    poly_up_price = best_bid
                elif asset_id == token_id_down:
                    poly_down_price = best_bid
            
            # Handle price_changes (real-time updates)
            elif 'price_changes' in data:
                changes = data['price_changes']
                
                if isinstance(changes, list) and len(changes) > 0:
                    for change in changes:
                        price = float(change.get('price', 0)) * 100
                        
                        if asset_id == token_id_up:
                            poly_up_price = price
                        elif asset_id == token_id_down:
                            poly_down_price = price
            
            # Print when both prices exist
            if coinbase_price > 0 and poly_up_price > 0 and poly_down_price > 0:
                format_output()
                
        except:
            pass
    
    def on_open(ws):
        try:
            sub_msg = {
                "assets_ids": [token_id_up, token_id_down],
                "type": "market"
            }
            ws.send(json.dumps(sub_msg))
        except:
            pass
    
    def keep_alive(ws):
        time.sleep(15)
        while True:
            try:
                ws.send("PING")
                time.sleep(10)
            except:
                break
    
    def on_open_with_keepalive(ws):
        on_open(ws)
        ping_thread = threading.Thread(target=keep_alive, args=(ws,), daemon=True)
        ping_thread.start()
    
    try:
        ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com/ws/market",
                                    on_open=on_open_with_keepalive,
                                    on_message=on_message)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except:
        pass

if __name__ == "__main__":
    print("🚀 Starting BTC Price Monitor...\n", flush=True)
    
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    
    t2.start()
    time.sleep(3)
    t1.start()
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped", flush=True)
