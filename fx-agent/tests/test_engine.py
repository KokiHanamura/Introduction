import math

import numpy as np
import pandas as pd
import pytest

from fxagent import journal as jr
from fxagent import montecarlo, patterns
from fxagent.__main__ import main
from fxagent.backtest import CostModel, run_backtest
from fxagent.data import synthetic_ohlc, validate
from fxagent.metrics import drawdown, max_streak, summarize

NO_COST = CostModel(pip_size=0.01, spread_pips=0, slippage_pips=0)


def bars(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def signals(df, at, direction=1, sl=1.0, tp=2.0):
    s = pd.DataFrame({"signal": 0, "sl_dist": sl, "tp_dist": tp}, index=df.index)
    s.iloc[at, 0] = direction
    return s


# ---------- ① バックテスト ----------

def test_entry_is_next_bar_open_no_lookahead():
    df = bars([[100, 100.5, 99.5, 100], [101, 101.2, 100.8, 101], [101, 103.5, 100.5, 103]])
    t = run_backtest(df, signals(df, 0), NO_COST, attach_features=False)
    assert t.loc[0, "entry"] == 101  # バー 0 のシグナル → バー 1 の始値
    assert t.loc[0, "entry_time"] == df.index[1]


def test_take_profit_r_multiple_and_cost():
    df = bars([[100, 100, 100, 100], [100, 100.5, 99.5, 100], [100, 102.5, 99.8, 102]])
    t = run_backtest(df, signals(df, 0), NO_COST, attach_features=False)
    assert t.loc[0, "exit_reason"] == "tp" and t.loc[0, "exit"] == 102
    assert t.loc[0, "r"] == pytest.approx(2.0)
    costed = run_backtest(df, signals(df, 0), CostModel(0.01, 10, 5), attach_features=False)
    assert costed.loc[0, "pnl_pips"] == pytest.approx(200 - 20)


def test_same_bar_sl_and_tp_assumes_stop_first():
    df = bars([[100, 100, 100, 100], [100, 102.5, 98.5, 100]])
    t = run_backtest(df, signals(df, 0), NO_COST, attach_features=False)
    assert t.loc[0, "exit_reason"] == "sl" and t.loc[0, "r"] == pytest.approx(-1.0)


def test_gap_through_stop_fills_at_open():
    df = bars([[100, 100, 100, 100], [100, 100.2, 99.8, 100], [97, 97.5, 96.5, 97]])
    t = run_backtest(df, signals(df, 0), NO_COST, attach_features=False)
    assert t.loc[0, "exit"] == 97 and t.loc[0, "r"] == pytest.approx(-3.0)


def test_short_trade_and_reverse_exit():
    df = bars([[100, 100, 100, 100], [100, 100.3, 99.5, 99.6], [99.5, 99.6, 99.4, 99.5], [99.5, 99.6, 99.4, 99.5]])
    s = signals(df, 0, direction=-1, sl=5, tp=np.nan)
    s.iloc[1, 0] = 1
    t = run_backtest(df, s, NO_COST, attach_features=False)
    assert t.loc[0, "direction"] == -1 and t.loc[0, "exit_reason"] == "reverse"
    assert t.loc[0, "exit"] == 99.5 and t.loc[1, "direction"] == 1


def test_validate_rejects_broken_ohlc():
    with pytest.raises(ValueError):
        validate(bars([[100, 99, 98, 100]]))


# ---------- 指標 ----------

def test_summary_metrics():
    s = summarize(pd.DataFrame({"r": [2, -1, -1, -1, 2, 2, -1]}))
    assert s["trades"] == 7
    assert s["win_rate"] == pytest.approx(3 / 7)
    assert s["profit_factor"] == pytest.approx(6 / 4)
    assert s["max_consecutive_losses"] == 3
    assert s["max_drawdown"] == pytest.approx(3)
    assert s["breakeven_win_rate"] == pytest.approx(1 / 3)


def test_drawdown_and_streak_edge_cases():
    assert drawdown(np.array([])) == (0.0, 0)
    assert drawdown(np.array([-1.0, -1.0, 3.0])) == (2.0, 2)
    assert max_streak(np.array([True, True, False, True])) == 2
    assert math.isinf(summarize(pd.DataFrame({"r": [1, 1]}))["profit_factor"])


def test_montecarlo_bounds():
    m = montecarlo.simulate(np.array([1.0, 2.0]), n_sims=100)
    assert m["prob_loss"] == 0 and m["max_dd_r_p95"] == 0
    m2 = montecarlo.simulate(np.array([2.0, -1.0, -1.0]), n_sims=500, seed=1)
    assert m2["max_losing_streak_p95"] >= 2
    assert montecarlo.risk_for_max_dd(np.array([2.0, -1.0, -1.0]), 20, n_sims=500) > 0


# ---------- ② ③ 負けパターン・改善 ----------

def planted_trades(n=600, seed=0):
    """金曜だけ明確に負ける人工トレード群。"""
    rng = np.random.default_rng(seed)
    t = pd.DataFrame({
        "entry_time": pd.date_range("2022-01-03", periods=n, freq="7h", tz="UTC"),
        "direction": rng.choice([1, -1], n),
        "mfe_r": rng.uniform(0, 3, n), "mae_r": rng.uniform(0, 1, n), "exit_reason": "sl",
    })
    t["weekday"] = t["entry_time"].dt.dayofweek
    t["r"] = np.where(t["weekday"] == 4, rng.choice([2, -1], n, p=[0.1, 0.9]), rng.choice([2, -1], n, p=[0.45, 0.55]))
    return t


def test_loss_patterns_finds_planted_condition():
    p = patterns.loss_patterns(planted_trades())
    assert p.iloc[0]["label"] == "weekday=金"
    assert p.iloc[0]["p_value"] < 0.001


def test_improve_adopts_real_effect_and_validates_out_of_sample():
    res = patterns.improve(planted_trades())
    c = res["candidates"]
    fri = c[c["rule"] == "見送り: weekday=金"]
    assert len(fri) == 1 and bool(fri.iloc[0]["adopt"])
    assert res["n_tests"] > 1


def test_improve_rejects_noise():
    rng = np.random.default_rng(3)
    t = planted_trades()
    t["r"] = rng.choice([2, -1], len(t), p=[0.4, 0.6])
    c = patterns.improve(t)["candidates"]
    assert not (len(c) and c["adopt"].any())


# ---------- ④ トレード記録 ----------

def test_journal_detects_revenge_and_stop_violation():
    rows = []
    t0 = pd.Timestamp("2024-03-01 09:00", tz="UTC")
    for k in range(40):
        o = t0 + pd.Timedelta(hours=6 * k)
        win = k % 2 == 0
        # 負けの直後（10 分後）に入ったトレードは必ず -2R（損切りを動かした）
        rows.append({"open_time": o, "close_time": o + pd.Timedelta(minutes=50), "direction": "buy",
                     "entry": 150.0, "stop": 149.5, "target": 151.0,
                     "exit": 151.0 if win else 149.5, "pnl": 10000 if win else -5000, "size": 1})
        if not win:
            o2 = o + pd.Timedelta(minutes=60)
            rows.append({"open_time": o2, "close_time": o2 + pd.Timedelta(minutes=30), "direction": "buy",
                         "entry": 150.0, "stop": 149.5, "target": 151.0, "exit": 149.0, "pnl": -10000, "size": 2})
    j = jr.prepare(pd.DataFrame(rows))
    found = jr.find_mistakes(j)
    # 同じトレード群（負け直後・ロット 2 倍・-2R）の兆候は 1 件にまとめられ、残りは related に入る
    merged = found[0]
    assert merged["key"] == "revenge" and merged["count"] == 20
    assert any("ロット" in r for r in merged["related"]) and any("損切り" in r for r in merged["related"])


def test_journal_requires_direction_values():
    with pytest.raises(ValueError):
        jr.prepare(pd.DataFrame([{"open_time": "2024-01-01", "close_time": "2024-01-01", "direction": "?",
                                  "entry": 1, "exit": 1, "pnl": 0}]))


# ---------- CLI ----------

def test_cli_end_to_end(tmp_path):
    data = tmp_path / "ohlc.csv"
    synthetic_ohlc(3000, seed=1).reset_index().to_csv(data, index=False)
    assert main(["backtest", "--data", str(data), "--param", "fast=10", "--param", "slow=30",
                 "--out", str(tmp_path / "bt")]) == 0
    trades = tmp_path / "bt" / "trades.csv"
    assert trades.exists()
    assert main(["analyze", "--trades", str(trades), "--out", str(tmp_path / "an")]) == 0
    assert main(["rulebook", "--trades", str(trades), "--journal", "journal/sample.csv",
                 "--out", str(tmp_path / "rb")]) == 0
    assert "見送りルール" in (tmp_path / "rb" / "rulebook.md").read_text()
    assert main(["journal", "--journal", "journal/sample.csv", "--out", str(tmp_path / "jr")]) == 0
