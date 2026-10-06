"""テクニカル指標と、負けパターン分析用の特徴量。

全て「そのバーの終値時点で分かる情報」だけで計算する（未来参照なし）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
                   axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def session_of(hour: int) -> str:
    """UTC 時刻 → 主要セッション（夏時間は無視した概算）。"""
    if 0 <= hour < 7:
        return "tokyo"
    if 7 <= hour < 12:
        return "london"
    if 12 <= hour < 16:
        return "london_ny_overlap"
    if 16 <= hour < 21:
        return "ny"
    return "late_ny"


def features(df: pd.DataFrame) -> pd.DataFrame:
    """各バー終値時点の市場状態。トレードのシグナルバーに結合して負けパターン分析に使う。"""
    a = atr(df, 14)
    ma50, ma200 = sma(df["close"], 50), sma(df["close"], 200)
    out = pd.DataFrame(index=df.index)
    out["hour"] = df.index.hour
    out["weekday"] = df.index.dayofweek
    out["session"] = [session_of(h) for h in df.index.hour]
    # ATR の過去 500 本内での順位（0-1）。高い＝高ボラ
    out["atr_pct"] = a.rolling(500, min_periods=100).rank(pct=True)
    out["trend_up"] = (ma200.diff(20) > 0).astype(float).where(ma200.notna())
    out["dist_ma50_atr"] = ((df["close"] - ma50) / a).round(3)
    out["bar_range_atr"] = ((df["high"] - df["low"]) / a).round(3)
    out["atr"] = a
    return out.replace([np.inf, -np.inf], np.nan)
