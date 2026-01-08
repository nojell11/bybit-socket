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

def get_active_poly_market():
    """Get Bitcoin Up or Down market"""
    try:
        url = "https://gamma-api.polymarket.com/events/slug/bitcoin-up-or-down"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            event = response.json()
            markets = event.get('markets', [])
            
            for market in markets:
                if market.get('active', False) and not market.get('closed', True):
                    tokens = market.get('tokens', [])
                    if len(tokens) >= 2:
                        question = market.get('question', '')
                        # Get token IDs
                        token_up = None
                        token_down = None
                        
                        for token in tokens:
                            outcome = token.get('outcome', '').lower()
                            token_id = token.get('token_id')
                            if 'yes' in outcome or 'up' in outcome:
                                token_up = token_id
                            else:
                                token_down = token_id
                        
                        if token_up and token_down:
                            print(f"✅ Market: {question}")
                            return token_up, token_down, question
        
        return None, None, None
    except Exception as e:
        print(f"❌ API error: {e}")
        return None, None, None

def format_output():
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
        print("❌ No Polymarket market")
        return
    
    current_question = question
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price
        try:
            data = json.loads(message)
            asset_id = data.get('asset_id', '')
            
            # Get best bid price
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
        # Subscribe using official format
        ws.send(json.dumps({
            "assets_ids": [token_id_up, token_id_down],
            "type": "market"
        }))
    
    def ping(ws):
        """Keep connection alive"""
        while True:
            time.sleep(10)
            try:
                ws.send("PING")
            except:
                break
    
    def on_open_with_ping(ws):
        on_open(ws)
        ping_thread = threading.Thread(target=ping, args=(ws,), daemon=True)
        ping_thread.start()
    
    ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com",
                                on_open=on_open_with_ping,
                                on_message=on_message)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

if __name__ == "__main__":
    print("🚀 Coinbase vs Polymarket Monitor\n")
    
    t1 = threading.Thread(target=coinbase_ws, daemon=True)
    t2 = threading.Thread(target=polymarket_ws, daemon=True)
    
    t2.start()
    time.sleep(3)
    t1.start()
    
    while True:
        time.sleep(1)
