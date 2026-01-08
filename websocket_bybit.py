#!/usr/bin/env python3
import sys
import os
import websocket
import ssl
import json
import time
import threading
import requests
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)
os.environ['PYTHONUNBUFFERED'] = '1'

# Price storage
coinbase_price = 0.0
poly_up_price = 0.0
poly_down_price = 0.0
last_print_time = 0

def get_current_15min_window():
    now = int(time.time())
    return (now // 900) * 900

def get_active_poly_market():
    try:
        timestamp = get_current_15min_window()
        slug = f"btc-updown-15m-{timestamp}"
        url = f"https://gamma-api.polymarket.com/events/slug/{slug}?tid={int(time.time()*1000)}"
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, None
        
        data = response.json()
        if not data.get('markets'):
            return None, None
        
        market = data['markets'][0]
        token_ids = json.loads(market.get('clobTokenIds'))
        return token_ids[0], token_ids[1]
    except:
        return None, None

def format_output():
    global last_print_time
    
    # Throttle to 1 update per second
    now = time.time()
    if now - last_print_time < 1.0:
        return
    last_print_time = now
    
    poly_mid = (poly_up_price + poly_down_price) / 2 if poly_down_price > 0 else 0
    
    print(f"COINBASE BTC PRICE   = ${coinbase_price:,.2f}", flush=True)
    print(f"POLYMARKET BTC PRICE = {poly_mid:.2f}¢ (UP: {poly_up_price:.2f}¢ | DOWN: {poly_down_price:.2f}¢)", flush=True)
    print(f"Updated: {datetime.now().strftime('%H:%M:%S')}\n", flush=True)

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
    
    ws = websocket.WebSocketApp("wss://advanced-trade-ws.coinbase.com",
                                on_open=on_open,
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

def polymarket_ws():
    global poly_up_price, poly_down_price
    
    token_id_up, token_id_down = get_active_poly_market()
    if not token_id_up:
        print("❌ No Polymarket market")
        return
    
    print(f"✅ Subscribed: UP={token_id_up[:8]}... DOWN={token_id_down[:8]}...\n", flush=True)
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price
        try:
            data = json.loads(message)
            asset_id = data.get('asset_id', '')
            
            # Handle bids array (snapshot)
            if 'bids' in data:
                bids = data['bids']
                if isinstance(bids, list) and len(bids) > 0:
                    # Get first bid
                    first_bid = bids[0]
                    
                    # Could be dict or list
                    if isinstance(first_bid, dict):
                        price = float(first_bid.get('price', 0)) * 100
                    elif isinstance(first_bid, list) and len(first_bid) >= 2:
                        price = float(first_bid[0]) * 100
                    else:
                        return
                    
                    if asset_id == token_id_up:
                        poly_up_price = price
                    elif asset_id == token_id_down:
                        poly_down_price = price
            
            # Handle price_changes (real-time)
            elif 'price_changes' in data:
                changes = data.get('price_changes', [])
                
                if isinstance(changes, list):
                    for change in changes:
                        if isinstance(change, dict):
                            price = float(change.get('price', 0)) * 100
                            
                            if asset_id == token_id_up:
                                poly_up_price = price
                            elif asset_id == token_id_down:
                                poly_down_price = price
            
            if coinbase_price > 0 and poly_up_price > 0 and poly_down_price > 0:
                format_output()
        except Exception as e:
            print(f"Parse error: {e}", flush=True)
    
    def on_open(ws):
        ws.send(json.dumps({
            "assets_ids": [token_id_up, token_id_down],
            "type": "market"
        }))
    
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
        threading.Thread(target=keep_alive, args=(ws,), daemon=True).start()
    
    ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com/ws/market",
                                on_open=on_open_with_keepalive,
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == "__main__":
    print("🚀 BTC Price Monitor Starting...\n", flush=True)
    
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    
    t2.start()
    time.sleep(3)
    t1.start()
    
    while True:
        time.sleep(1)
