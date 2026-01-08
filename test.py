import sys
print("TEST: Python is running!")
sys.stdout.flush()

import websocket
print("TEST: websocket-client imported OK")
sys.stdout.flush()

import requests
print("TEST: requests imported OK")
sys.stdout.flush()

print("TEST: All imports successful!")

import time
for i in range(5):
    print(f"TEST: Counter {i}")
    sys.stdout.flush()
    time.sleep(1)

print("TEST: Script completed!")
