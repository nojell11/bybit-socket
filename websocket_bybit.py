import websocket
import ssl
import json
import time

orderbook = {'bid': 0.0, 'ask': 0.0}

def on_open(ws):
    print("Connected to Coinbase")
    sub_msg = {
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channel": "level2"
    }
    ws.send(json.dumps(sub_msg))

def on_message(ws, message):
    global orderbook
    data = json.loads(message)
    if data.get('type') == 'snapshot':
        # Use snapshot for initial book
        bids = data['bids']
        asks = data['asks']
        if bids:
            orderbook['bid'] = float(bids[0][0])
        if asks:
            orderbook['ask'] = float(asks[0][0])
    elif data.get('type') == 'l2update':
        # Apply updates
        changes = data['changes']
        for change in changes:
            side, price_str, size_str = change
            price = float(price_str)
            if price == 0:
                continue  # Remove level
            if side[0] == 'b':
                if price > orderbook['bid']:
                    orderbook['bid'] = price
            else:
                if price < orderbook['ask']:
                    orderbook['ask'] = price
    print(f"BTC-USD: Bid {orderbook['bid']:.2f} | Ask {orderbook['ask']:.2f} | Time: {time.time():.0f}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

if __name__ == "__main__":
    ws_url = "wss://advanced-trade-ws.coinbase.com"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
