"""CLI。各スキル（/fx-backtest など）はこのコマンドを呼んで数値を得る。

  python3 -m fxagent backtest --data data/usdjpy_h1.csv --strategy ma_cross --param fast=20 --param slow=50
  python3 -m fxagent analyze  --trades reports/<run>/trades.csv           # ② 負けパターン + ③ 改善案
  python3 -m fxagent journal  --journal journal/my_trades.csv              # ④ 自分のミス Top5
  python3 -m fxagent rulebook --trades reports/<run>/trades.csv [--journal ...]   # ⑤ ルールブック下書き
  python3 -m fxagent demo                                                  # 合成データで一連の流れを確認

結果は reports/<日時>_<名前>/ に Markdown と CSV で保存する。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import journal as jr
from . import montecarlo, patterns, rulebook
from .backtest import CostModel, run_backtest
from .data import load_ohlc, synthetic_ohlc
from .metrics import format_summary, summarize
from .strategies import STRATEGIES

ROOT = Path(__file__).resolve().parents[1]


def _out_dir(name: str, base: str | None) -> Path:
    d = Path(base) if base else ROOT / "reports" / f"{datetime.now():%Y%m%d_%H%M%S}_{name}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _params(items: list[str]) -> dict:
    out = {}
    for kv in items or []:
        k, v = kv.split("=", 1)
        out[k] = float(v) if "." in v else int(v)
    return out


def _load_trades(path: str) -> pd.DataFrame:
    t = pd.read_csv(path, parse_dates=["signal_time", "entry_time", "exit_time"])
    return t


def backtest_report(df, strategy: str, params: dict, cost: CostModel, max_hold: int | None) -> tuple[str, pd.DataFrame]:
    trades = run_backtest(df, STRATEGIES[strategy](df, **params), cost=cost, max_hold_bars=max_hold)
    s_r, s_p = summarize(trades, "r"), summarize(trades, "pnl_pips")
    md = [f"# バックテスト: {strategy} {params}",
          f"- 期間: {df.index[0]} 〜 {df.index[-1]}（{len(df)} 本）",
          f"- コスト: スプレッド {cost.spread_pips} pips + スリッページ片道 {cost.slippage_pips} pips",
          "", "## 成績（R 倍数）", format_summary(s_r), "", "## 成績（pips）", format_summary(s_p)]
    if len(trades) >= 30:
        mc = montecarlo.simulate(trades["r"].to_numpy())
        md += ["", "## モンテカルロ（並び順の偶然を除いた見通し）", montecarlo.format_mc(mc)]
    else:
        md += ["", f"> ⚠️ トレード数 {len(trades)} は少なすぎて統計的に判断できない（最低 100、できれば 300 以上）"]
    return "\n".join(md) + "\n", trades


def analyze_report(trades: pd.DataFrame, min_n: int) -> tuple[str, dict]:
    pats = patterns.loss_patterns(trades, min_n=min_n)
    imp = patterns.improve(trades, min_n=min_n)
    md = ["# 負けパターン分析と改善案", "", "## ② 期待値が低い条件 Top10（全期間）"]
    if len(pats):
        md.append("| 条件 | 件数 | 勝率 | 期待値(R) | 他との差 | 負け全体に占める割合 | p 値 |\n|---|---|---|---|---|---|---|")
        for _, p in pats.head(10).iterrows():
            md.append(f"| {p['label']} | {p['n']} | {p['win_rate']:.0%} | {p['expectancy']:+.3f} | "
                      f"{p['diff_vs_rest']:+.3f} | {p['loss_share']:.0%} | {p['p_value']:.3f} |")
    else:
        md.append("条件ごとに十分な件数が無い")
    d = imp["diagnostics"]
    md += ["", "## 損切り・利確の診断（MFE/MAE）",
           f"- 一度 +1R に到達してから負けた割合: {d['losers_reached_1r']:.0%}",
           f"- 勝ちトレードで -0.8R 以上逆行していた割合: {d['winners_near_stop']:.0%}",
           f"- 勝ちトレードの MFE 中央値: {d['winners_mfe_median']:.2f}R",
           f"- 決済理由の内訳: {d['exit_reasons']}",
           "", "## ③ 改善案（前半 70% で発見 → 後半 30% で検証）",
           f"- 前半: 期待値 {imp['in_sample'].get('expectancy', 0):+.3f}R / 後半: {imp['out_of_sample'].get('expectancy', 0):+.3f}R",
           f"- 試した条件の数: {imp['n_tests']}（多いほど偶然の当たりが混ざる → Bonferroni 補正で判定）"]
    c = imp["candidates"]
    if len(c):
        md.append("\n| 案 | 前半 p 値 | 後半 期待値(除外後) | 後半 改善幅 | 判定 |\n|---|---|---|---|---|")
        for _, r in c.iterrows():
            verdict = "採用" if r["adopt"] else ("保留（後半では改善）" if r["survives_oos"] else "却下（後半で再現せず）")
            md.append(f"| {r['rule']} | {r['is_p_value']:.4f} | {r['oos_expectancy_after']:+.3f} | {r['oos_gain']:+.3f} | {verdict} |")
    else:
        md.append("- 前半データで有意に期待値を下げている条件は見つからなかった")
    return "\n".join(md) + "\n", imp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fxagent")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backtest")
    b.add_argument("--data", required=True)
    b.add_argument("--strategy", default="ma_cross", choices=list(STRATEGIES))
    b.add_argument("--param", action="append", default=[])
    b.add_argument("--pip-size", type=float, default=0.01)
    b.add_argument("--spread", type=float, default=0.3)
    b.add_argument("--slippage", type=float, default=0.2)
    b.add_argument("--max-hold", type=int)
    b.add_argument("--out")

    a = sub.add_parser("analyze")
    a.add_argument("--trades", required=True)
    a.add_argument("--min-n", type=int, default=20)
    a.add_argument("--out")

    j = sub.add_parser("journal")
    j.add_argument("--journal", required=True)
    j.add_argument("--revenge-minutes", type=float, default=30)
    j.add_argument("--out")

    r = sub.add_parser("rulebook")
    r.add_argument("--trades", required=True)
    r.add_argument("--strategy-desc", default="（手法の説明を書く）")
    r.add_argument("--journal")
    r.add_argument("--target-dd", type=float, default=20.0)
    r.add_argument("--out")

    d = sub.add_parser("demo")
    d.add_argument("--out")

    args = ap.parse_args(argv)

    if args.cmd in ("backtest", "demo"):
        if args.cmd == "demo":
            df, strategy, params, cost, max_hold = synthetic_ohlc(8000, seed=7), "ma_cross", {}, CostModel(), None
        else:
            df, strategy, params = load_ohlc(args.data), args.strategy, _params(args.param)
            cost, max_hold = CostModel(args.pip_size, args.spread, args.slippage), args.max_hold
        out = _out_dir(f"{args.cmd}_{strategy}", args.out)
        md, trades = backtest_report(df, strategy, params, cost, max_hold)
        trades.to_csv(out / "trades.csv", index=False)
        if args.cmd == "demo" and len(trades):
            amd, imp = analyze_report(trades, 20)
            md += "\n" + amd
            mc = montecarlo.simulate(trades["r"].to_numpy())
            risk = montecarlo.risk_for_max_dd(trades["r"].to_numpy())
            md += "\n" + rulebook.build("MA(20/50) クロス（デモ）", summarize(trades), imp, mc, risk)
            md = "> ⚠️ 合成データによるデモ。実在相場の検証結果ではない\n\n" + md
        (out / "report.md").write_text(md)
        print(md)
        print(f"\n→ {out}", file=sys.stderr)
        return 0

    if args.cmd == "analyze":
        out = _out_dir("analyze", args.out)
        md, imp = analyze_report(_load_trades(args.trades), args.min_n)
        (out / "report.md").write_text(md)
        imp["candidates"].to_csv(out / "candidates.csv", index=False)
        print(md)
        return 0

    if args.cmd == "journal":
        out = _out_dir("journal", args.out)
        jdf = jr.load_journal(args.journal)
        s = jr.summary(jdf)
        found = jr.find_mistakes(jdf, revenge_minutes=args.revenge_minutes)
        md = (f"# トレード記録分析（{s['trades']} 件）\n\n- 勝率 {s['win_rate']:.0%} / PF {s['profit_factor']:.2f} / "
              f"合計 {s['total']:+,.0f} / 平均利益 {s['avg_win']:,.0f} / 平均損失 {s['avg_loss']:,.0f}\n\n"
              f"## 繰り返しているミス（損失寄与の大きい順）\n\n{jr.format_mistakes(found)}")
        (out / "report.md").write_text(md)
        (out / "mistakes.json").write_text(json.dumps(found, ensure_ascii=False, indent=2))
        print(md)
        return 0

    if args.cmd == "rulebook":
        out = _out_dir("rulebook", args.out)
        trades = _load_trades(args.trades)
        imp = patterns.improve(trades)
        r_arr = trades["r"].to_numpy()
        mc = montecarlo.simulate(r_arr)
        risk = montecarlo.risk_for_max_dd(r_arr, target_dd_pct=args.target_dd)
        mistakes = jr.find_mistakes(jr.load_journal(args.journal)) if args.journal else None
        md = rulebook.build(args.strategy_desc, summarize(trades), imp, mc, risk, mistakes)
        (out / "rulebook.md").write_text(md)
        print(md)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
