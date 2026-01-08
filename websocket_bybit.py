import websocket
import ssl
import json
import time

orderbook = {'bid': 0.0, 'ask': 0.0}

def on_open(ws):
    print("Connected to Bybit")
    sub_msg = {"op": "subscribe", "args": ["orderbook.1.BTCUSDT"]}
    ws.send(json.dumps(sub_msg))

def on_message(ws, message):
    global orderbook
    data = json.loads(message)
    if data.get('topic') == 'orderbook.1.BTCUSDT':
        ob = data['data']
        orderbook['bid'] = float(ob['b'][0][0])
        orderbook['ask'] = float(ob['a'][0][0])
        print(f"BTCUSDT: Bid {orderbook['bid']:.2f} | Ask {orderbook['ask']:.2f} | Time: {time.time():.0f}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

if __name__ == "__main__":
    ws_url = "wss://stream.bybit.com/v5/public/spot"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
