"""
Backtest: 9-EMA + Pivot Point confluence intraday strategy (as shown in the reel)

STRATEGY RULES IMPLEMENTED
--------------------------
Long entry candle:
    - close crosses ABOVE the 9-EMA, AND
    - close also crosses ABOVE a pivot level (S2/S1/P/R1/R2/R3, whichever is
      nearest), within `confluence_window` candles of each other.
Short entry: mirror image (close crosses below EMA and below a pivot level).

Exit (choose one via --exit-mode):
    ema_reverse : exit when close crosses back through the 9-EMA (this is
                  what the video actually visualises - the EMA is the trail).
    fixed_rr    : fixed stop-loss (points) and target = stop * --rr, whichever
                  hits first intrabar.
Forced square-off at --eod-time (default 15:20 IST) - no overnight positions,
since this is an intraday strategy.

Pivots are STANDARD daily pivots computed from the PREVIOUS session's
High/Low/Close and held constant through the current session - this is
exactly what "Pivot Points Standard" on TradingView does.

INPUT
-----
A CSV with columns: datetime,open,high,low,close  (5-min NIFTY candles).
This is the format Kite Connect's historical_data() API returns (rename
`date`->`datetime` if needed). No data is bundled with this script -
point --csv at your own export.

USAGE
-----
    python backtest_ema_pivot.py --csv nifty_5min.csv --exit-mode ema_reverse
    python backtest_ema_pivot.py --csv nifty_5min.csv --exit-mode fixed_rr --sl 15 --rr 1.5

OUTPUT
------
Prints a trade log summary + win rate, profit factor, expectancy.
Writes the full trade list to trades_output.csv next to the input file.
"""

import argparse
import numpy as np
import pandas as pd


def compute_daily_pivots(df: pd.DataFrame) -> pd.DataFrame:
    """Standard pivots per session, using the PREVIOUS session's H/L/C."""
    df = df.copy()
    df["session_date"] = df["datetime"].dt.date
    daily = df.groupby("session_date").agg(
        day_high=("high", "max"), day_low=("low", "min"), day_close=("close", "last")
    )
    daily["P"] = (daily["day_high"] + daily["day_low"] + daily["day_close"]) / 3
    daily["R1"] = 2 * daily["P"] - daily["day_low"]
    daily["S1"] = 2 * daily["P"] - daily["day_high"]
    daily["R2"] = daily["P"] + (daily["day_high"] - daily["day_low"])
    daily["S2"] = daily["P"] - (daily["day_high"] - daily["day_low"])
    daily["R3"] = daily["day_high"] + 2 * (daily["P"] - daily["day_low"])
    daily["S3"] = daily["day_low"] - 2 * (daily["day_high"] - daily["P"])
    # shift by one session: today trades on YESTERDAY's pivots
    pivots_for_next_day = daily[["P", "R1", "R2", "R3", "S1", "S2", "S3"]].shift(1)
    pivots_for_next_day.index = daily.index
    df = df.merge(
        pivots_for_next_day, left_on="session_date", right_index=True, how="left"
    )
    return df


def add_signals(df: pd.DataFrame, ema_period: int, confluence_window: int) -> pd.DataFrame:
    df = df.copy()
    df["ema"] = df["close"].ewm(span=ema_period, adjust=False).mean()

    df["ema_cross_up"] = (df["close"] > df["ema"]) & (df["close"].shift(1) <= df["ema"].shift(1))
    df["ema_cross_dn"] = (df["close"] < df["ema"]) & (df["close"].shift(1) >= df["ema"].shift(1))

    pivot_cols = ["P", "R1", "R2", "R3", "S1", "S2", "S3"]
    prev_close = df["close"].shift(1)
    pivot_break_up = pd.Series(False, index=df.index)
    pivot_break_dn = pd.Series(False, index=df.index)
    for col in pivot_cols:
        level = df[col]
        pivot_break_up |= (prev_close <= level) & (df["close"] > level)
        pivot_break_dn |= (prev_close >= level) & (df["close"] < level)
    df["pivot_break_up"] = pivot_break_up
    df["pivot_break_dn"] = pivot_break_dn

    # confluence: either event happened within the last `confluence_window` bars
    df["long_signal"] = df["ema_cross_up"] & (
        df["pivot_break_up"].rolling(confluence_window, min_periods=1).max().astype(bool)
    )
    df["short_signal"] = df["ema_cross_dn"] & (
        df["pivot_break_dn"].rolling(confluence_window, min_periods=1).max().astype(bool)
    )
    return df


def run_backtest(df: pd.DataFrame, exit_mode: str, sl_points: float, rr: float, eod_time: str):
    trades = []
    position = None  # dict while open

    eod_h, eod_m = map(int, eod_time.split(":"))

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_session = df.iloc[i - 1]["session_date"]
        cur_session = row["session_date"]
        new_day = cur_session != prev_session

        # forced square-off at end of day or on session change
        if position is not None and (new_day or (row["datetime"].hour, row["datetime"].minute) >= (eod_h, eod_m)):
            exit_price = row["open"] if new_day else row["close"]
            trades.append(_close_trade(position, row["datetime"], exit_price, "EOD"))
            position = None

        if position is None:
            if row["long_signal"]:
                position = {"dir": 1, "entry_time": row["datetime"], "entry_price": row["close"],
                            "ema_at_entry": row["ema"]}
            elif row["short_signal"]:
                position = {"dir": -1, "entry_time": row["datetime"], "entry_price": row["close"],
                            "ema_at_entry": row["ema"]}
            continue

        # manage open position
        if exit_mode == "ema_reverse":
            if position["dir"] == 1 and row["ema_cross_dn"]:
                trades.append(_close_trade(position, row["datetime"], row["close"], "EMA_REVERSE"))
                position = None
            elif position["dir"] == -1 and row["ema_cross_up"]:
                trades.append(_close_trade(position, row["datetime"], row["close"], "EMA_REVERSE"))
                position = None
        else:  # fixed_rr
            target_pts = sl_points * rr
            if position["dir"] == 1:
                stop = position["entry_price"] - sl_points
                target = position["entry_price"] + target_pts
                if row["low"] <= stop:
                    trades.append(_close_trade(position, row["datetime"], stop, "SL"))
                    position = None
                elif row["high"] >= target:
                    trades.append(_close_trade(position, row["datetime"], target, "TARGET"))
                    position = None
            else:
                stop = position["entry_price"] + sl_points
                target = position["entry_price"] - target_pts
                if row["high"] >= stop:
                    trades.append(_close_trade(position, row["datetime"], stop, "SL"))
                    position = None
                elif row["low"] <= target:
                    trades.append(_close_trade(position, row["datetime"], target, "TARGET"))
                    position = None

    return pd.DataFrame(trades)


def _close_trade(position, exit_time, exit_price, reason):
    pnl = (exit_price - position["entry_price"]) * position["dir"]
    return {
        "direction": "LONG" if position["dir"] == 1 else "SHORT",
        "entry_time": position["entry_time"],
        "entry_price": position["entry_price"],
        "exit_time": exit_time,
        "exit_price": exit_price,
        "pnl_points": pnl,
        "exit_reason": reason,
    }


def summarize(trades: pd.DataFrame):
    if trades.empty:
        print("No trades generated - check your data / confluence window.")
        return
    wins = trades[trades["pnl_points"] > 0]
    losses = trades[trades["pnl_points"] <= 0]
    win_rate = len(wins) / len(trades) * 100
    avg_win = wins["pnl_points"].mean() if len(wins) else 0
    avg_loss = losses["pnl_points"].mean() if len(losses) else 0
    gross_win = wins["pnl_points"].sum()
    gross_loss = abs(losses["pnl_points"].sum())
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
    expectancy = trades["pnl_points"].mean()

    print(f"Total trades   : {len(trades)}")
    print(f"Win rate       : {win_rate:.1f}%  ({len(wins)}W / {len(losses)}L)")
    print(f"Avg win        : {avg_win:.1f} pts")
    print(f"Avg loss       : {avg_loss:.1f} pts")
    print(f"Profit factor  : {profit_factor:.2f}")
    print(f"Expectancy/trd : {expectancy:.1f} pts")
    print(f"Net points     : {trades['pnl_points'].sum():.1f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="5-min OHLC CSV: datetime,open,high,low,close")
    ap.add_argument("--ema", type=int, default=9)
    ap.add_argument("--confluence-window", type=int, default=3)
    ap.add_argument("--exit-mode", choices=["ema_reverse", "fixed_rr"], default="ema_reverse")
    ap.add_argument("--sl", type=float, default=15.0, help="stop in points (fixed_rr mode)")
    ap.add_argument("--rr", type=float, default=1.5, help="reward:risk multiple (fixed_rr mode)")
    ap.add_argument("--eod-time", default="15:20")
    args = ap.parse_args()

    raw = pd.read_csv(args.csv, parse_dates=["datetime"])
    raw = raw.sort_values("datetime").reset_index(drop=True)
    with_pivots = compute_daily_pivots(raw)
    with_signals = add_signals(with_pivots, args.ema, args.confluence_window)
    trades = run_backtest(with_signals, args.exit_mode, args.sl, args.rr, args.eod_time)

    summarize(trades)
    if not trades.empty:
        out_path = args.csv.rsplit(".", 1)[0] + "_trades_output.csv"
        trades.to_csv(out_path, index=False)
        print(f"\nFull trade log written to {out_path}")
