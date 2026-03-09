import yfinance as yf
import pandas as pd

# Monkeypatch to disable TkrTzCache which causes sqlite issues
try:
    from yfinance import Ticker
    # It seems the cache is used inside Ticker and base modules.
    # The cache class is usually in yfinance.cache or yfinance.utils
    
    # Let's try to mock the TkrTzCache
    class DummyCache:
        def __init__(self, *args, **kwargs): pass
        def lookup(self, *args, **kwargs): return None
        def store(self, *args, **kwargs): pass
        def dummy(self): pass
    
    # yfinance.data.TkrTzCache is where it lives usually
    import yfinance.data
    yfinance.data.TkrTzCache = DummyCache
    print("Patched TkrTzCache")
except Exception as e:
    print(f"Patch failed: {e}")

print("Testing download...")
try:
    # We also need to patch the session cache if possible, but that's requests_cache
    # yfinance uses requests_cache.CachedSession if installed?
    # No, yfinance 0.2.x uses its own logic.
    
    data = yf.download("AAPL", period="1d", progress=False)
    print(data)
except Exception as e:
    print(f"Error: {e}")
