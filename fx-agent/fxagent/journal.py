"""④ 実トレード記録から「繰り返しているミス」を損失額の大きい順に特定する。

記録フォーマットは journal/template.csv を参照。必須: open_time, close_time, direction, entry, exit, pnl。
stop / target / size / followed_plan / emotion / setup があるほど検出できるミスが増える。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import session_of

REQUIRED = ["open_time", "close_time", "direction", "entry", "exit", "pnl"]


def load_journal(path) -> pd.DataFrame:
    j = pd.read_csv(path)
    j.columns = [c.strip().lower() for c in j.columns]
    missing = [c for c in REQUIRED if c not in j.columns]
    if missing:
        raise ValueError(f"必須列が無い: {missing}")
    return prepare(j)


def prepare(j: pd.DataFrame) -> pd.DataFrame:
    j = j.copy()
    j["open_time"] = pd.to_datetime(j["open_time"], utc=True)
    j["close_time"] = pd.to_datetime(j["close_time"], utc=True)
    j = j.sort_values("open_time").reset_index(drop=True)
    d = j["direction"].astype(str).str.lower().map({"buy": 1, "long": 1, "買い": 1, "1": 1,
                                                     "sell": -1, "short": -1, "売り": -1, "-1": -1})
    if d.isna().any():
        raise ValueError("direction は buy/sell（または long/short・買い/売り）で書く")
    j["dir"] = d.astype(int)
    if "stop" in j:
        risk = (j["entry"] - j["stop"]).abs()
        j["r"] = (j["dir"] * (j["exit"] - j["entry"]) / risk).where(risk > 0)
    j["win"] = j["pnl"] > 0
    j["prev_win"] = j["win"].shift(1)
    j["mins_since_prev_close"] = (j["open_time"] - j["close_time"].shift(1)).dt.total_seconds() / 60
    j["session"] = [session_of(h) for h in j["open_time"].dt.hour]
    return j


def _finding(key, title, mask, j, why, fix, cost=None) -> dict:
    mask = mask.fillna(False).astype(bool)
    sub = j[mask]
    return {
        "key": key, "title": title, "count": int(mask.sum()), "share": float(mask.mean()),
        "pnl": float(sub["pnl"].sum()), "cost": float(cost if cost is not None else min(sub["pnl"].sum(), 0)),
        "win_rate": float(sub["win"].mean()) if len(sub) else 0.0,
        "others_win_rate": float(j.loc[~mask, "win"].mean()) if (~mask).any() else 0.0,
        "why": why, "fix": fix, "related": [], "_ids": set(sub.index),
    }


def find_mistakes(j: pd.DataFrame, revenge_minutes: float = 30, top: int = 5) -> list[dict]:
    """ミスの候補を全部検出し、損失寄与（cost）の大きい順に top 件返す。"""
    out = []
    if "stop" in j:
        out.append(_finding("no_stop", "損切りを置かずにエントリー", j["stop"].isna(), j,
                            "損失が青天井になり、1 回で数十回分の利益を失う", "注文と同時に逆指値を入れる。置けないなら入らない"))
    if "r" in j:
        over = j["r"] < -1.2
        excess = (j.loc[over, "pnl"] * (1 - 1 / j.loc[over, "r"].abs())).sum()
        out.append(_finding("stop_violation", "損切りを動かした / 守らなかった（-1.2R 超の損失）", over, j,
                            "想定した 1R を超える損失が期待値を直接削る", "逆指値は広げない。損切り後の再エントリーは条件を満たした時だけ",
                            cost=excess))
        avg_win = j.loc[j["r"] > 0, "r"].mean()
        avg_loss = -j.loc[j["r"] <= 0, "r"].mean()
        if "target" in j and pd.notna(avg_win) and pd.notna(avg_loss) and avg_win < avg_loss:
            planned = (j["target"] - j["entry"]).abs() / (j["entry"] - j["stop"]).abs()
            early = (j["r"] > 0) & (j["r"] < planned * 0.5)
            missed = ((planned - j["r"]) * j["pnl"] / j["r"]).where(early).sum()
            out.append(_finding("early_take", f"利小損大（平均利益 {avg_win:.2f}R < 平均損失 {avg_loss:.2f}R）・利確が早い",
                                early, j, "勝率が高くても損益比が崩れていれば期待値はマイナスになる（損失寄与は目標到達率 50% と仮定した機会損失）",
                                "利確は指値に任せる。途中決済するなら事前に決めた条件（建値移動・部分利確）だけ",
                                cost=-abs(missed) * 0.5))
    revenge = (j["prev_win"] == False) & (j["mins_since_prev_close"] <= revenge_minutes)  # noqa: E712
    out.append(_finding("revenge", f"負けた直後 {revenge_minutes:.0f} 分以内の再エントリー（リベンジトレード）", revenge, j,
                        "損を取り返したい焦りで、条件の揃っていないエントリーになりやすい",
                        f"損切り後は最低 {revenge_minutes:.0f} 分チャートを閉じる。2 連敗でその日は終了"))
    if "size" in j:
        med = j["size"].median()
        upsized = (j["size"] > med * 1.5) & (j["prev_win"] == False)  # noqa: E712
        out.append(_finding("size_up", "負けの後にロットを上げる（ナンピン的な取り返し）", upsized, j,
                            "負けを大きいロットで取り返そうとすると、DD が指数的に深くなる",
                            "ロットは口座残高×許容リスク%÷損切り幅で毎回計算する。感情でロットを変えない"))
    per_day = j.groupby(j["open_time"].dt.date).cumcount() + 1
    limit = max(int(j.groupby(j["open_time"].dt.date).size().median()), 1)
    out.append(_finding("overtrade", f"1 日 {limit} 回を超えるトレード（オーバートレード）", per_day > limit, j,
                        "回数を重ねるほど条件の質が落ち、コストと判断疲れが積み上がる", f"1 日の上限を {limit} 回にする"))
    if "followed_plan" in j:
        off = j["followed_plan"].astype(str).str.lower().isin(["no", "n", "false", "0", "いいえ", "×"])
        out.append(_finding("off_plan", "ルール外のエントリー（自己申告）", off, j,
                            "検証していない条件のトレードは、期待値が分からないギャンブル",
                            "エントリー前にチェックリストを声に出して確認する"))
    sess = j.groupby("session")["pnl"].sum()
    if len(sess) > 1 and sess.min() < 0:
        worst = sess.idxmin()
        out.append(_finding("bad_session", f"負けやすい時間帯（{worst}）でのトレード", j["session"] == worst, j,
                            "時間帯ごとに値動きの性質（ボラ・ダマシの多さ）が違う", f"{worst} は見送るか、検証し直す"))
    streak = j["win"].eq(False).astype(int).groupby(j["win"].cumsum()).cumsum().shift(1).fillna(0)
    out.append(_finding("tilt", "2 連敗以上の直後のトレード（ティルト）", streak >= 2, j,
                        "連敗中は判断が荒れやすい", "2 連敗で当日終了、3 連敗で翌日のロットを半分に"))
    if "emotion" in j and j["emotion"].notna().any():
        emo = j.groupby("emotion")["pnl"].sum()
        worst = emo.idxmin()
        out.append(_finding("emotion", f"感情「{worst}」の時のトレード", j["emotion"] == worst, j,
                            "感情が判断に入っているトレードは成績が悪い傾向", f"「{worst}」を感じたら見送り"))
    found = sorted([f for f in out if f["count"] > 0 and f["cost"] < 0], key=lambda f: f["cost"])
    # 同じトレード群を別の角度で言い直しているだけの検出は 1 つにまとめる（Jaccard ≥ 0.8）
    picked: list[dict] = []
    for f in found:
        dup = next((p for p in picked if len(f["_ids"] & p["_ids"]) / len(f["_ids"] | p["_ids"]) >= 0.8), None)
        if dup:
            dup["related"].append(f["title"])
        else:
            picked.append(f)
    for f in picked:
        f.pop("_ids")
    return picked[:top]


def format_mistakes(found: list[dict]) -> str:
    if not found:
        return "損失につながっている繰り返しのミスは検出されなかった（記録列を増やすと検出項目が増える）"
    lines = []
    for i, f in enumerate(found, 1):
        lines.append(
            f"### {i}. {f['title']}\n"
            f"- 発生: {f['count']} 回（全体の {f['share']:.0%}）／ 損失寄与: {f['cost']:+,.0f}\n"
            f"- 勝率: 該当 {f['win_rate']:.0%} vs それ以外 {f['others_win_rate']:.0%}\n"
            f"- なぜ問題か: {f['why']}\n- 対策ルール: {f['fix']}\n"
            + (f"- 同じトレード群に重なる兆候: {' / '.join(f['related'])}\n" if f["related"] else ""))
    return "\n".join(lines)


def summary(j: pd.DataFrame) -> dict:
    pnl = j["pnl"].to_numpy(float)
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    return {"trades": len(pnl), "win_rate": float((pnl > 0).mean()), "total": float(pnl.sum()),
            "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else np.inf,
            "avg_win": float(wins.mean()) if len(wins) else 0.0,
            "avg_loss": float(-losses.mean()) if len(losses) else 0.0}
