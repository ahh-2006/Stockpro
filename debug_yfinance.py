import os
import sys

# Force env var before ANY import
import tempfile
cache_dir = os.path.join(tempfile.gettempdir(), f"yfinance_test_{os.getpid()}")
os.makedirs(cache_dir, exist_ok=True)
os.environ["YFINANCE_CACHE_DIR"] = cache_dir
print(f"Set YFINANCE_CACHE_DIR to: {os.environ['YFINANCE_CACHE_DIR']}")

import yfinance as yf
print(f"yfinance version: {yf.__version__}")

# Try to find where cache is
try:
    from yfinance import utils
    # Check if we can access internal cache path
    # Depending on version, it might be in different places
    print("Checking yfinance internals...")
except ImportError:
    pass

print("\n--- Single Ticker Test ---")
try:
    t = yf.Ticker("AAPL")
    hist = t.history(period="1d")
    print("History empty:", hist.empty)
    print(hist)
except Exception as e:
    print(f"Single ticker error: {e}")

print("\n--- Multi Ticker Test ---")
try:
    data = yf.download(["AAPL", "MSFT"], period="1d", progress=False)
    print("Multi data empty:", data.empty)
    print(data)
except Exception as e:
    print(f"Multi ticker error: {e}")
