import pandas as pd
from stockpro.data.ingest import fetch_prices_yahoo
import yfinance as yf

print("--- Testing fetch_prices_yahoo for GEVO ---")
try:
    df = fetch_prices_yahoo("GEVO", period="1mo", interval="1d")
    print("DataFrame empty:", df.empty)
    print("Columns:", df.columns)
    print("Head:\n", df.head())
except Exception as e:
    print("Error:", e)

print("\n--- Direct yf.download test ---")
try:
    df_yf = yf.download("GEVO", period="1mo", interval="1d", auto_adjust=False, progress=False)
    print("Direct download empty:", df_yf.empty)
    print("Direct download columns:", df_yf.columns)
    print("Direct download head:\n", df_yf.head())
except Exception as e:
    print("Direct Error:", e)
