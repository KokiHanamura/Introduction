"""モンテカルロ（トレード順序のリサンプリング）。

バックテストの最大 DD・最大連敗は「たまたまの 1 本の並び」に過ぎない。
同じ損益分布から並びを入れ替えて、将来起こり得る DD・連敗の分布を見る。
"""
from __future__ import annotations

import numpy as np

from .metrics import drawdown, max_streak


def simulate(r: np.ndarray, n_sims: int = 2000, n_trades: int | None = None, risk_pct: float = 1.0,
             ruin_dd_pct: float = 30.0, seed: int = 0) -> dict:
    """R 倍数列からブートストラップ。risk_pct は 1 トレードの許容損失（口座比 %、固定額近似）。"""
    rng = np.random.default_rng(seed)
    r = np.asarray(r, float)
    n_trades = n_trades or len(r)
    mdd = np.empty(n_sims)
    streak = np.empty(n_sims)
    final = np.empty(n_sims)
    for k in range(n_sims):
        sample = rng.choice(r, size=n_trades, replace=True)
        mdd[k], _ = drawdown(sample)
        streak[k] = max_streak(sample <= 0)
        final[k] = sample.sum()
    mdd_pct = mdd * risk_pct
    pct = lambda a, q: float(np.percentile(a, q))  # noqa: E731
    return {
        "n_sims": n_sims, "n_trades": n_trades, "risk_pct": risk_pct,
        "max_dd_r_median": pct(mdd, 50), "max_dd_r_p95": pct(mdd, 95),
        "max_dd_pct_p95": pct(mdd_pct, 95),
        "max_losing_streak_median": pct(streak, 50), "max_losing_streak_p95": pct(streak, 95),
        "final_r_p5": pct(final, 5), "final_r_median": pct(final, 50),
        "prob_loss": float((final <= 0).mean()),
        "prob_dd_over_limit": float((mdd_pct >= ruin_dd_pct).mean()),
        "ruin_dd_pct": ruin_dd_pct,
    }


def risk_for_max_dd(r: np.ndarray, target_dd_pct: float = 20.0, **kw) -> float:
    """95% タイルの最大 DD が target_dd_pct に収まる 1 トレードのリスク %。"""
    res = simulate(r, risk_pct=1.0, **kw)
    return target_dd_pct / res["max_dd_r_p95"] if res["max_dd_r_p95"] > 0 else float("inf")


def format_mc(m: dict) -> str:
    return (
        f"- {m['n_sims']} 回 × {m['n_trades']} トレードをリサンプリング（1 トレードのリスク {m['risk_pct']}%）\n"
        f"- 最大 DD: 中央値 {m['max_dd_r_median']:.1f}R / 95%タイル {m['max_dd_r_p95']:.1f}R"
        f"（口座 {m['max_dd_pct_p95']:.1f}%）\n"
        f"- 最大連敗: 中央値 {m['max_losing_streak_median']:.0f} / 95%タイル {m['max_losing_streak_p95']:.0f}\n"
        f"- 最終損益: 5%タイル {m['final_r_p5']:+.1f}R / 中央値 {m['final_r_median']:+.1f}R、"
        f"トータルでマイナスになる確率 {m['prob_loss']:.1%}\n"
        f"- DD が {m['ruin_dd_pct']:.0f}% を超える確率 {m['prob_dd_over_limit']:.1%}"
    )
