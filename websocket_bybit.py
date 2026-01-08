def polymarket_ws():
    global poly_up_price, poly_down_price, current_question
    
    token_id_up, token_id_down, question = get_active_poly_market()
    if not token_id_up:
        print("❌ No Polymarket market")
        return
    
    current_question = question
    print(f"🔄 Connecting to Polymarket WebSocket...")
    
    def on_message(ws, message):
        global poly_up_price, poly_down_price
        try:
            print(f"📥 Poly message: {message[:200]}")
            data = json.loads(message)
            asset_id = data.get('asset_id', '')
            
            if data.get('bids'):
                best_bid = float(data['bids'][0].get('price', 0)) * 100
                
                if asset_id == token_id_up:
                    poly_up_price = best_bid
                    print(f"   UP price: {poly_up_price:.2f}¢")
                elif asset_id == token_id_down:
                    poly_down_price = best_bid
                    print(f"   DOWN price: {poly_down_price:.2f}¢")
                
                if coinbase_price > 0 and poly_up_price > 0 and poly_down_price > 0:
                    format_output()
        except Exception as e:
            print(f"❌ Poly parse: {e}")
    
    def on_open(ws):
        print("✅ Polymarket WebSocket opened")
        try:
            sub_msg = {
                "assets_ids": [token_id_up, token_id_down],
                "type": "market"
            }
            print(f"📤 Subscribing to tokens")
            ws.send(json.dumps(sub_msg))
            print("✅ Polymarket subscribed")
        except Exception as e:
            print(f"❌ Subscription failed: {e}")
    
    def on_error(ws, error):
        print(f"❌ Polymarket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 Polymarket closed: {close_status_code}")
    
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
        # FIXED URL - added /ws/market path
        ws = websocket.WebSocketApp("wss://ws-subscriptions-clob.polymarket.com/ws/market",
                                    on_open=on_open_with_keepalive,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    except Exception as e:
        print(f"❌ Polymarket crashed: {e}")
