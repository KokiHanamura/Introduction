"""売買ルール。

戦略は df を受け取り、各バーについて以下の列を持つ DataFrame を返す:
  signal  : 1=買い / -1=売り / 0=なし（そのバーの終値で確定。エントリーは次バー始値）
  sl_dist : 損切り幅（価格）
  tp_dist : 利確幅（価格。NaN なら利確指値なし）
新しい戦略は同じ形で関数を足し、STRATEGIES に登録する。
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from .indicators import atr, sma


def _frame(df, signal, a, sl_atr, tp_atr) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["signal"] = signal.fillna(0).astype(int)
    out["sl_dist"] = a * sl_atr
    out["tp_dist"] = a * tp_atr if tp_atr else np.nan
    out.loc[out["sl_dist"].isna(), "signal"] = 0
    return out


def ma_cross(df: pd.DataFrame, fast: int = 20, slow: int = 50, atr_n: int = 14,
             sl_atr: float = 1.5, tp_atr: float = 3.0) -> pd.DataFrame:
    """移動平均クロス。ゴールデンクロスで買い、デッドクロスで売り。"""
    f, s = sma(df["close"], fast), sma(df["close"], slow)
    above = (f > s).astype(int)
    cross = above.diff()
    signal = pd.Series(np.where(cross > 0, 1, np.where(cross < 0, -1, 0)), index=df.index).where(s.notna(), 0)
    return _frame(df, signal, atr(df, atr_n), sl_atr, tp_atr)


def donchian_breakout(df: pd.DataFrame, n: int = 20, atr_n: int = 14,
                      sl_atr: float = 2.0, tp_atr: float = 4.0) -> pd.DataFrame:
    """直近 n 本の高値/安値ブレイク（タートル型）。"""
    hi = df["high"].rolling(n).max().shift(1)
    lo = df["low"].rolling(n).min().shift(1)
    signal = pd.Series(np.where(df["close"] > hi, 1, np.where(df["close"] < lo, -1, 0)), index=df.index)
    return _frame(df, signal, atr(df, atr_n), sl_atr, tp_atr)


STRATEGIES: dict[str, Callable[..., pd.DataFrame]] = {
    "ma_cross": ma_cross,
    "donchian_breakout": donchian_breakout,
}
