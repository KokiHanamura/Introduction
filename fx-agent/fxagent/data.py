"""OHLC データの読み込み・検証・合成データ生成。

CSV 形式: time,open,high,low,close[,volume]（time は UTC 推奨。ISO8601 か "YYYY-MM-DD HH:MM"）。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ["open", "high", "low", "close"]


def load_ohlc(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    time_col = next((c for c in ("time", "datetime", "date", "timestamp") if c in df.columns), None)
    if time_col is None:
        raise ValueError("time 列（time/datetime/date/timestamp）が見つからない")
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"必須列が無い: {missing}")
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    df = df.set_index(time_col).sort_index()
    df.index.name = "time"
    return validate(df)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """重複・欠損・OHLC 矛盾を検出する。黙って直さず、明らかに壊れた行は例外にする。"""
    if df.index.has_duplicates:
        raise ValueError(f"重複タイムスタンプ {int(df.index.duplicated().sum())} 件")
    if df[REQUIRED].isna().any().any():
        raise ValueError("OHLC に欠損値がある")
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    if bad.any():
        raise ValueError(f"high/low が open/close と矛盾する行が {int(bad.sum())} 件（例: {df.index[bad][0]}）")
    return df


def synthetic_ohlc(n: int = 5000, seed: int = 0, start: str = "2020-01-01", freq: str = "1h",
                   price: float = 110.0, vol: float = 0.0012) -> pd.DataFrame:
    """デモ・テスト用の合成データ（トレンド/レンジのレジームが切り替わるランダムウォーク）。

    実在の相場ではない。手法の優位性の検証には絶対に使わないこと。
    """
    rng = np.random.default_rng(seed)
    regime_len = 300
    drift = np.repeat(rng.normal(0, vol * 0.08, n // regime_len + 1), regime_len)[:n]
    # 時間帯でボラを変える（東京 < ロンドン/NY）
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    hour_vol = np.where((idx.hour >= 7) & (idx.hour < 17), 1.4, 0.8)
    rets = drift + rng.standard_normal(n) * vol * hour_vol
    close = price * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[price], close[:-1]])
    wick = np.abs(rng.standard_normal((2, n))) * vol * hour_vol * close * 0.6
    high = np.maximum(open_, close) + wick[0]
    low = np.minimum(open_, close) - wick[1]
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx).rename_axis("time")
