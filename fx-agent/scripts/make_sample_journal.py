"""journal/sample.csv（架空のトレード記録）を再生成する。テスト・デモ用で、実在のトレードではない。

意図的に混ぜたミス: リベンジトレード / 負け後のロット増 / 損切りの後退 / 早すぎる利確 / 深夜帯のトレード
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
rows, t, last_loss = [], pd.Timestamp("2026-07-01 08:00"), False
while len(rows) < 60:
    revenge = last_loss and rng.random() < 0.5
    o = t + (pd.Timedelta(minutes=int(rng.integers(5, 25))) if revenge else pd.Timedelta(hours=int(rng.integers(3, 20))))
    late = o.hour >= 21 or o.hour < 1
    win = rng.random() < (0.25 if revenge or late else 0.55)
    d = rng.choice(["buy", "sell"])
    s = 1 if d == "buy" else -1
    entry = round(148 + rng.normal(0, 1), 3)
    size = 2.0 if revenge and rng.random() < 0.6 else 1.0
    if win:
        r = 2.0 if rng.random() < 0.6 else round(rng.uniform(0.3, 0.9), 2)
    else:
        r = -1.0 if rng.random() < 0.75 else round(rng.uniform(-2.5, -1.5), 2)
    c = o + pd.Timedelta(minutes=int(rng.integers(15, 180)))
    rows.append(dict(
        trade_id=len(rows) + 1, open_time=f"{o:%Y-%m-%d %H:%M}", close_time=f"{c:%Y-%m-%d %H:%M}", pair="USDJPY",
        direction=d, entry=entry, exit=round(entry + s * 0.25 * r, 3), stop=round(entry - s * 0.25, 3),
        target=round(entry + s * 0.5, 3), size=size, pnl=round(r * 2500 * size),
        setup=rng.choice(["押し目買い", "ブレイク", "逆張り"]),
        followed_plan="no" if (revenge and rng.random() < 0.7) or rng.random() < 0.05 else "yes",
        emotion="焦り" if (revenge and rng.random() < 0.6) or rng.random() < 0.1 else rng.choice(["平常", "自信"]),
        notes=""))
    t, last_loss = c, not win
pd.DataFrame(rows).to_csv("journal/sample.csv", index=False)
