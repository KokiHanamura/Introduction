"""⑤ 検証結果とトレード履歴から「自分専用ルールブック」の下書きを作る。

ここで出すのは数値に裏付けられた骨組み。最終的な言い回し・優先順位は
/fx-rulebook スキルで Claude と人間がすり合わせて決める。
"""
from __future__ import annotations

from datetime import date

from .metrics import format_summary


def build(strategy_desc: str, summary: dict, improvement: dict | None = None, mc: dict | None = None,
          risk_pct: float | None = None, mistakes: list[dict] | None = None) -> str:
    lines = [f"# マイ・トレードルールブック（下書き {date.today():%Y-%m-%d}）", "",
             "> このルールは過去データの検証に基づく仮説であり、将来の利益を保証しない。",
             "> 四半期ごと、または 50 トレードごとに検証し直す。", ""]

    lines += ["## 1. エントリールール", f"- 手法: {strategy_desc}",
              "- シグナルは足の確定後のみ有効。確定前の先回りエントリーはしない", ""]

    skip = []
    if improvement is not None and len(improvement.get("candidates", [])):
        c = improvement["candidates"]
        for _, row in c[c["adopt"]].iterrows():
            skip.append(f"- {row['rule']}（後半データで期待値 {row['oos_gain']:+.3f}R 改善、検証済み）")
        for _, row in c[~c["adopt"] & c["survives_oos"]].iterrows():
            skip.append(f"- （保留）{row['rule']} — 後半でも改善したが統計的に弱い。追加データで再確認")
    for m in mistakes or []:
        if m["key"] in ("bad_session", "emotion", "tilt", "revenge", "overtrade"):
            skip.append(f"- {m['fix']}（実トレードで損失寄与 {m['cost']:+,.0f}）")
    lines += ["## 2. 見送りルール"] + (skip or ["- 検証で有意な見送り条件はまだ無い（データを増やして再分析）"]) + [""]

    lines += ["## 3. 損切りルール", "- エントリーと同時に逆指値を置く。後から広げない"]
    if improvement:
        d = improvement["diagnostics"]
        if d["winners_near_stop"] > 0.3:
            lines.append(f"- 勝ちトレードの {d['winners_near_stop']:.0%} が損切り直前まで逆行 → 損切り幅が狭すぎる可能性。"
                         "ATR 倍率を広げた版を検証する")
    lines += [""]

    lines += ["## 4. 利確ルール", "- 利確は事前に決めた指値で行う。途中決済は下記の条件のみ"]
    if improvement:
        d = improvement["diagnostics"]
        if d["losers_reached_1r"] > 0.25:
            lines.append(f"- 負けトレードの {d['losers_reached_1r']:.0%} が一度 +1R に到達してから負けている → "
                         "+1R で建値ストップに移動する案を検証する")
        lines.append(f"- 勝ちトレードの最大含み益（MFE）中央値: {d['winners_mfe_median']:.2f}R")
    lines += [""]

    lines += ["## 5. 資金管理"]
    if risk_pct:
        lines.append(f"- 1 トレードの許容損失: 口座の {risk_pct:.2f}%（モンテカルロ 95%タイルの最大 DD を許容範囲に収める値）")
    else:
        lines.append("- 1 トレードの許容損失: 口座の 0.5〜1%")
    lines.append("- ロット = 口座残高 × 許容損失% ÷ 損切り幅（pips × pip 価値）")
    if mc:
        lines.append(f"- 想定すべき連敗: {mc['max_losing_streak_p95']:.0f} 連敗（95%タイル）。ここまでは手法を疑わない")
        lines.append(f"- 停止ライン: DD が想定 95%タイル（{mc['max_dd_r_p95']:.1f}R）を超えたら取引停止して再検証")
    lines += ["", "## 6. 行動ルール（自分のミス対策）"]
    lines += [f"- {m['fix']}  ← {m['title']}" for m in (mistakes or [])] or ["- トレード記録を 50 件貯めて /fx-journal-review で分析する"]
    lines += ["", "## 付録: 根拠となった検証結果", format_summary(summary)]
    return "\n".join(lines) + "\n"
