"""バー単位のバックテストエンジン。

設計上の約束（検証結果を信用できるものにするため）:
- シグナルはバー i の終値で確定し、エントリーはバー i+1 の始値（未来参照しない）
- 同じバーで SL と TP の両方に触れたら SL が先とみなす（保守的）
- 窓開けで SL/TP を飛び越えたら始値で約定（有利な方向にも不利な方向にも）
- 取引コスト（スプレッド＋往復スリッページ）を毎トレード pips で差し引く
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .indicators import features


@dataclass
class CostModel:
    pip_size: float = 0.01        # JPY クロスは 0.01、それ以外は 0.0001
    spread_pips: float = 0.3
    slippage_pips: float = 0.2    # 片道

    @property
    def round_trip_pips(self) -> float:
        return self.spread_pips + 2 * self.slippage_pips


def run_backtest(df: pd.DataFrame, signals: pd.DataFrame, cost: CostModel | None = None,
                 max_hold_bars: int | None = None, exit_on_reverse: bool = True,
                 attach_features: bool = True) -> pd.DataFrame:
    """1 ポジションずつのバックテスト。トレード一覧（1 行 1 トレード）を返す。"""
    cost = cost or CostModel()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    sig = signals["signal"].reindex(df.index).fillna(0).to_numpy(int)
    sl_d = signals["sl_dist"].reindex(df.index).to_numpy(float)
    tp_d = signals["tp_dist"].reindex(df.index).to_numpy(float)
    idx = df.index
    trades: list[dict] = []
    pos: dict | None = None

    def close(i: int, price: float, reason: str) -> None:
        nonlocal pos
        d, risk_pips = pos["dir"], pos["sl_dist"] / cost.pip_size
        gross = d * (price - pos["entry"]) / cost.pip_size
        pnl = gross - cost.round_trip_pips
        trades.append({
            "signal_time": idx[pos["sig_i"]], "entry_time": idx[pos["i"]], "exit_time": idx[i],
            "direction": d, "entry": pos["entry"], "exit": price, "sl": pos["sl"], "tp": pos["tp"],
            "risk_pips": risk_pips, "pnl_pips": pnl, "r": pnl / risk_pips,
            "mfe_r": pos["mfe"] / pos["sl_dist"], "mae_r": pos["mae"] / pos["sl_dist"],
            "bars_held": i - pos["i"] + 1, "exit_reason": reason,
        })
        pos = None

    for i in range(1, len(df)):
        s = sig[i - 1]
        if pos and exit_on_reverse and s == -pos["dir"]:
            close(i, o[i], "reverse")
        if pos is None and s != 0 and np.isfinite(sl_d[i - 1]) and sl_d[i - 1] > 0:
            e = o[i]
            pos = {"dir": s, "i": i, "sig_i": i - 1, "entry": e, "sl_dist": sl_d[i - 1],
                   "sl": e - s * sl_d[i - 1],
                   "tp": e + s * tp_d[i - 1] if np.isfinite(tp_d[i - 1]) else np.nan,
                   "mfe": 0.0, "mae": 0.0}
        if pos is None:
            continue

        d, sl, tp = pos["dir"], pos["sl"], pos["tp"]
        fav, adv = (h[i] - pos["entry"], pos["entry"] - l[i]) if d == 1 else (pos["entry"] - l[i], h[i] - pos["entry"])
        pos["mfe"], pos["mae"] = max(pos["mfe"], fav), max(pos["mae"], adv)
        if d == 1:
            sl_hit, tp_hit = l[i] <= sl, np.isfinite(tp) and h[i] >= tp
            sl_px, tp_px = min(o[i], sl), max(o[i], tp) if np.isfinite(tp) else np.nan
        else:
            sl_hit, tp_hit = h[i] >= sl, np.isfinite(tp) and l[i] <= tp
            sl_px, tp_px = max(o[i], sl), min(o[i], tp) if np.isfinite(tp) else np.nan
        if sl_hit:
            close(i, sl_px, "sl")
        elif tp_hit:
            close(i, tp_px, "tp")
        elif max_hold_bars and i - pos["i"] + 1 >= max_hold_bars:
            close(i, c[i], "time")

    if pos:
        close(len(df) - 1, c[-1], "end")

    result = pd.DataFrame(trades)
    if attach_features and not result.empty:
        feats = features(df).drop(columns=["atr"])
        result = result.join(feats, on="signal_time")
    return result
