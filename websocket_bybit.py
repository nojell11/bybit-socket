import websocket
import ssl
import json
import time
import threading
import requests
from datetime import datetime

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
    """Build market slug: btc-updown-15m-{timestamp}"""
    return f"btc-updown-15m-{timestamp}"

def get_active_poly_market():
    """Get current 15-min BTC market"""
    try:
        timestamp = get_current_15min_window()
        slug = build_market_slug(timestamp)
        url = f"https://gamma-api.polymarket.com/events/slug/{slug}?tid={int(time.time()*1000)}"
        
        print(f"📡 Fetching: {slug}")
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Error: {response.text[:200]}")
            return None, None, None
        
        data = response.json()
        
        # Get token IDs from clobTokenIds field
        if not data.get('markets') or len(data['markets']) == 0:
            print("   No markets found")
            return None, None, None
        
        market = data['markets'][0]
        clob_token_ids = market.get('clobTokenIds')
        
        if not clob_token_ids:
            print("   No clobTokenIds found")
            return None, None, None
        
        token_ids = json.loads(clob_token_ids)
        question = market.get('question', 'BTC 15-min')
        
        print(f"✅ Market: {question}")
        print(f"   Token IDs: {token_ids[0][:8]}..., {token_ids[1][:8]}...")
        
        # First token = UP, Second = DOWN (usually)
        return token_ids[0], token_ids[1], question
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

# Rest of the code stays the same (coinbase_ws, polymarket_ws, format_output)
