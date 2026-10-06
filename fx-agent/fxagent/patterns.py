"""② 負けパターンの抽出と ③ 期待値を下げている条件の特定・改善案。

方針: 「感覚」ではなく、条件ごとの期待値をデータで比較し、
改善案は必ずインサンプル（前半）で見つけてアウトオブサンプル（後半）で確かめる。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .metrics import summarize

FEATURES = ["session", "hour", "weekday", "direction", "atr_pct", "trend_up", "with_trend",
            "dist_ma50_atr", "bar_range_atr", "after_loss"]
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def enrich(trades: pd.DataFrame) -> pd.DataFrame:
    """トレード一覧に派生特徴量を足す（順張りか、直前トレードが負けか）。"""
    t = trades.sort_values("entry_time").reset_index(drop=True).copy()
    if "trend_up" in t:
        trend_dir = np.where(t["trend_up"] == 1, 1, np.where(t["trend_up"] == 0, -1, 0))
        t["with_trend"] = np.where(trend_dir == 0, np.nan, (t["direction"] == trend_dir).astype(float))
    t["after_loss"] = (t["r"].shift(1) <= 0).astype(float).where(t.index > 0)
    return t


def _p_value(a: np.ndarray, b: np.ndarray) -> float:
    """Welch の t 検定（正規近似の両側 p 値）。"""
    if len(a) < 2 or len(b) < 2:
        return 1.0
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    if se == 0:
        return 1.0
    return math.erfc(abs(a.mean() - b.mean()) / se / math.sqrt(2))


def _edges(s: pd.Series, q: int = 4) -> np.ndarray | None:
    """数値列の分位境界（両端は ±inf）。カテゴリ扱いにすべき列なら None。"""
    s = s.dropna()
    if s.empty or s.dtype == object or s.nunique() <= 8:
        return None
    inner = np.unique(np.quantile(s, np.linspace(0, 1, q + 1)[1:-1]))
    return np.concatenate([[-np.inf], inner, [np.inf]])


def bucket(s: pd.Series, edges: np.ndarray | None) -> pd.Series:
    if edges is None:
        return s.astype(object).where(s.notna())
    return pd.cut(s, edges).astype(str).where(s.notna())


def label(feature: str, value) -> str:
    if feature == "weekday" and isinstance(value, (int, float)) and not pd.isna(value):
        return WEEKDAYS[int(value)]
    if feature == "direction":
        return "買い" if value == 1 else "売り"
    if feature in ("trend_up", "with_trend", "after_loss") and not isinstance(value, str):
        return {"trend_up": ["下降トレンド", "上昇トレンド"], "with_trend": ["逆張り", "順張り"],
                "after_loss": ["直前が勝ち", "直前が負け"]}[feature][int(value)]
    return str(value)


def loss_patterns(trades: pd.DataFrame, min_n: int = 20, edges: dict | None = None) -> pd.DataFrame:
    """条件（特徴量のバケット）ごとの成績。期待値が悪い順。"""
    t = enrich(trades)
    edges = edges if edges is not None else {f: _edges(t[f]) for f in FEATURES if f in t}
    overall = t["r"].mean()
    total_loss = -t.loc[t["r"] <= 0, "r"].sum() or 1.0
    rows = []
    for f, e in edges.items():
        b = bucket(t[f], e)
        for val, grp in t.groupby(b):
            if len(grp) < min_n:
                continue
            rest = t.loc[b != val, "r"].to_numpy()
            r = grp["r"].to_numpy()
            rows.append({
                "feature": f, "bucket": val, "label": f"{f}={label(f, val)}", "n": len(r),
                "win_rate": float((r > 0).mean()), "expectancy": float(r.mean()),
                "diff_vs_rest": float(r.mean() - rest.mean()) if len(rest) else 0.0,
                "loss_share": float(-r[r <= 0].sum() / total_loss),
                "total_r": float(r.sum()), "p_value": _p_value(r, rest),
                "below_overall": r.mean() < overall,
            })
    return pd.DataFrame(rows).sort_values("expectancy").reset_index(drop=True) if rows else pd.DataFrame()


def stop_target_diagnostics(trades: pd.DataFrame) -> dict:
    """MFE/MAE から損切り・利確の置き方を診断する。"""
    losers, winners = trades[trades["r"] <= 0], trades[trades["r"] > 0]
    return {
        # 一度 +1R まで伸びてから負けた割合 → 建値移動・部分利確の候補
        "losers_reached_1r": float((losers["mfe_r"] >= 1).mean()) if len(losers) else 0.0,
        # 勝ちトレードのうち -0.8R 以上逆行していた割合 → 損切りがギリギリ（狭すぎ/ノイズ内）
        "winners_near_stop": float((winners["mae_r"] >= 0.8).mean()) if len(winners) else 0.0,
        # 勝ちトレードの MFE 中央値 → 利確目標が近すぎ/遠すぎの目安
        "winners_mfe_median": float(winners["mfe_r"].median()) if len(winners) else 0.0,
        "exit_reasons": trades["exit_reason"].value_counts(normalize=True).round(3).to_dict(),
    }


def improve(trades: pd.DataFrame, split: float = 0.7, min_n: int = 20, alpha: float = 0.05) -> dict:
    """期待値を下げている条件を前半で見つけ、除外した場合の効果を後半で検証する。"""
    t = enrich(trades)
    cut = int(len(t) * split)
    ins, oos = t.iloc[:cut], t.iloc[cut:]
    edges = {f: _edges(ins[f]) for f in FEATURES if f in ins}
    pats = loss_patterns(ins, min_n=min_n, edges=edges)
    n_tests = len(pats)
    cands = pats[(pats["diff_vs_rest"] < 0) & (pats["p_value"] < alpha)] if n_tests else pats
    base_is, base_oos = summarize(ins), summarize(oos)
    results = []
    for _, p in cands.iterrows():
        keep_is = bucket(ins[p["feature"]], edges[p["feature"]]) != p["bucket"]
        keep_oos = bucket(oos[p["feature"]], edges[p["feature"]]) != p["bucket"]
        s_is, s_oos = summarize(ins[keep_is]), summarize(oos[keep_oos])
        oos_gain = s_oos.get("expectancy", 0) - base_oos.get("expectancy", 0)
        results.append({
            "rule": f"見送り: {p['label']}", "feature": p["feature"], "bucket": p["bucket"],
            "is_n_removed": int((~keep_is).sum()), "is_p_value": p["p_value"],
            "is_expectancy_after": s_is.get("expectancy"), "oos_expectancy_after": s_oos.get("expectancy"),
            "oos_gain": oos_gain, "oos_trades_after": s_oos.get("trades", 0),
            # 多重検定を考慮（Bonferroni）してもなお有意で、後半でも改善したものだけ採用
            "adopt": bool(oos_gain > 0 and p["p_value"] < alpha / max(n_tests, 1)),
            "survives_oos": bool(oos_gain > 0),
        })
    return {
        "in_sample": base_is, "out_of_sample": base_oos, "n_tests": n_tests,
        "candidates": pd.DataFrame(results), "diagnostics": stop_target_diagnostics(t),
    }
