import pandas as pd
from stockpro.scanner import scan_market, get_default_tickers
import yfinance as yf

print("--- Debugging Scanner ---")
tickers = get_default_tickers()[:5] # Test with first 5 tickers to save time
print(f"Testing tickers: {tickers}")

# Try to download data manually first to see structure
print("\nDownloading data...")
data = yf.download(tickers, period="5d", interval="1d", group_by='ticker', auto_adjust=False, progress=False)
print("Data shape:", data.shape)
print("Data columns:", data.columns)

if not data.empty:
    first_ticker = tickers[0]
    try:
        df = data[first_ticker]
        print(f"\nData for {first_ticker}:")
        print(df.tail())
    except KeyError:
        print(f"\nCould not get data for {first_ticker} from multi-index.")

# Now run the actual scan function with very loose criteria
print("\nRunning scan_market with loose criteria...")
# min_price=0, max_price=10000, min_vol=0, min_change=-100
res = scan_market(tickers, 0, 10000, 0, -100)
print(f"Result count: {len(res)}")
if not res.empty:
    print(res)
else:
    print("Result is empty!")
