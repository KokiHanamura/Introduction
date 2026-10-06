"""成績指標。トレード一覧の `r`（R 倍数）または任意の損益列から計算する。"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def max_streak(mask: np.ndarray) -> int:
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def drawdown(pnl: np.ndarray) -> tuple[float, int]:
    """累積損益の最大ドローダウン（値）と最長ドローダウン期間（トレード数）。"""
    if len(pnl) == 0:
        return 0.0, 0
    equity = np.concatenate([[0.0], np.cumsum(pnl)])
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    longest = cur = 0
    for v in dd[1:]:
        cur = cur + 1 if v > 0 else 0
        longest = max(longest, cur)
    return float(dd.max()), longest


def summarize(trades: pd.DataFrame, col: str = "r") -> dict:
    """勝率・PF・期待値・最大連敗・最大 DD など。`col` は "r" か "pnl_pips"。"""
    x = trades[col].to_numpy(float) if len(trades) else np.array([])
    n = len(x)
    if n == 0:
        return {"trades": 0}
    wins, losses = x[x > 0], x[x <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = -losses.mean() if len(losses) else 0.0
    payoff = avg_win / avg_loss if avg_loss > 0 else math.inf
    mdd, dd_len = drawdown(x)
    std = x.std(ddof=1) if n > 1 else 0.0
    total = float(x.sum())
    return {
        "trades": n,
        "win_rate": len(wins) / n,
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else math.inf,
        "expectancy": float(x.mean()),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "payoff_ratio": float(payoff),
        # この損益比で損益分岐になる勝率。実際の勝率がこれを上回っているかが本質
        "breakeven_win_rate": 1 / (1 + payoff) if math.isfinite(payoff) else 0.0,
        "max_consecutive_losses": max_streak(x <= 0),
        "max_consecutive_wins": max_streak(x > 0),
        "max_drawdown": mdd,
        "longest_drawdown_trades": dd_len,
        "total": total,
        "recovery_factor": total / mdd if mdd > 0 else math.inf,
        # 期待値が 0 と区別できるか（t 値 2 未満なら運の可能性を否定できない）
        "t_stat": float(x.mean() / (std / math.sqrt(n))) if std > 0 else 0.0,
        "unit": col,
    }


def format_summary(s: dict) -> str:
    if not s.get("trades"):
        return "トレードなし"
    u = "R" if s["unit"] == "r" else "pips"
    pf = "∞" if math.isinf(s["profit_factor"]) else f"{s['profit_factor']:.2f}"
    rows = [
        ("トレード数", f"{s['trades']}"),
        ("勝率", f"{s['win_rate']:.1%}（損益分岐勝率 {s['breakeven_win_rate']:.1%}）"),
        ("プロフィットファクター", pf),
        ("期待値 / トレード", f"{s['expectancy']:+.3f} {u}（t 値 {s['t_stat']:.2f}）"),
        ("平均利益 / 平均損失", f"{s['avg_win']:.2f} / {s['avg_loss']:.2f} {u}（損益比 {s['payoff_ratio']:.2f}）"),
        ("最大連敗 / 最大連勝", f"{s['max_consecutive_losses']} / {s['max_consecutive_wins']}"),
        ("最大ドローダウン", f"{s['max_drawdown']:.2f} {u}（最長 {s['longest_drawdown_trades']} トレード）"),
        ("合計損益", f"{s['total']:+.2f} {u}"),
    ]
    return "| 指標 | 値 |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows)
