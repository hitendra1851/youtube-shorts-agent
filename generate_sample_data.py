"""Generate synthetic 5-min NIFTY-like OHLC data for backtesting (no real data bundled)."""
import numpy as np
import pandas as pd

np.random.seed(42)

start_price = 22000.0
n_days = 90
bars_per_day = 75  # 9:15 to 15:30 in 5-min bars = 75 bars

dates = pd.bdate_range("2024-01-01", periods=n_days)

rows = []
price = start_price
daily_vol = 120  # approx daily range in points

for day in dates:
    day_open = price
    # random daily drift/trend regime
    drift = np.random.choice([-1, 0, 1], p=[0.35, 0.3, 0.35]) * np.random.uniform(0.3, 1.2)
    session_start = pd.Timestamp(day.date()) + pd.Timedelta(hours=9, minutes=15)
    p = day_open
    for b in range(bars_per_day):
        t = session_start + pd.Timedelta(minutes=5 * b)
        # mean-reverting + trend + noise random walk for 5-min close
        step = drift * (daily_vol / bars_per_day) + np.random.normal(0, daily_vol / 12)
        o = p
        c = o + step
        h = max(o, c) + abs(np.random.normal(0, daily_vol / 30))
        l = min(o, c) - abs(np.random.normal(0, daily_vol / 30))
        rows.append([t, o, h, l, c])
        p = c
    price = p

df = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close"])
df.to_csv("sample_nifty_5min.csv", index=False)
print(df.head())
print(len(df), "bars across", n_days, "sessions")
