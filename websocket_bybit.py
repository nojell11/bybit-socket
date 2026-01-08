def on_message(ws, message):
    global poly_up_price, poly_down_price
    try:
        data = json.loads(message)
        asset_id = data.get('asset_id', '')
        
        # Handle orderbook snapshot (bids/asks)
        if data.get('bids') and len(data['bids']) > 0:
            best_bid = float(data['bids'][0].get('price', 0)) * 100
            
            if asset_id == token_id_up:
                poly_up_price = best_bid
                print(f"   📊 UP: {poly_up_price:.2f}¢", flush=True)
            elif asset_id == token_id_down:
                poly_down_price = best_bid
                print(f"   📊 DOWN: {poly_down_price:.2f}¢", flush=True)
        
        # Handle price_changes (incremental updates) - FIX HERE!
        elif 'price_changes' in data:
            changes = data['price_changes']
            
            # price_changes is an ARRAY, not an object
            if isinstance(changes, list) and len(changes) > 0:
                for change in changes:
                    price = float(change.get('price', 0)) * 100
                    side = change.get('side', '')
                    
                    if asset_id == token_id_up:
                        poly_up_price = price
                        print(f"   ⬆️ UP: {poly_up_price:.2f}¢ ({side})", flush=True)
                    elif asset_id == token_id_down:
                        poly_down_price = price
                        print(f"   ⬇️ DOWN: {poly_down_price:.2f}¢ ({side})", flush=True)
        
        # Print comparison when both exist
        if coinbase_price > 0 and poly_up_price > 0 and poly_down_price > 0:
            format_output()
            
    except Exception as e:
        print(f"❌ Poly parse: {e}", flush=True)
        import traceback
        traceback.print_exc()
