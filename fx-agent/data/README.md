# data/

相場データ（OHLC）を置く場所。中身は git 管理しない（サイズとデータのライセンスのため）。

- 形式: `time,open,high,low,close[,volume]`、time は **UTC**
- 推奨ファイル名: `<通貨ペア>_<時間足>.csv`（例: `usdjpy_h1.csv`）
- `data/raw/` は取得したままの原本。ハーネスで編集禁止（加工版は `data/` 直下に別名で作る）
- 入手先の候補と注意点は `docs/research/03_data-sources.md`
