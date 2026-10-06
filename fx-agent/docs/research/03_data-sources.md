# 相場データの入手先と注意点

| 入手先 | 内容 | 注意 |
|---|---|---|
| ブローカーの MT4/MT5 ヒストリー | 自分が実際に取引する価格に一番近い | サーバー時間（GMT+2/+3、夏時間あり）→ UTC 変換が必要。期間が短いことがある |
| Dukascopy ヒストリカルデータ | ティック〜日足、長期間、無料 | 1 社の bid/ask。ダウンロードツールが必要 |
| HistData.com | M1 の無料 CSV（年・月単位） | 時刻は EST（夏時間なし）。出来高なし |
| 国内 FX 業者の API・CSV | 国内口座で取引するなら価格の一致度が高い | 業者ごとに提供範囲が違う。利用規約を確認 |
| OANDA API 等 | API で取得・発注まで一貫 | 口座開設が必要 |

## 取り込み手順
1. 原本を `data/raw/` に保存（編集禁止）
2. UTC に変換し、`time,open,high,low,close` の CSV にして `data/<pair>_<tf>.csv` に保存
3. `python3 -c "from fxagent.data import load_ohlc; print(load_ohlc('data/<file>.csv').describe())"` で検証（重複・欠損・OHLC 矛盾は例外になる）
4. 週末の足・祝日の薄商い・異常値（スパイク）を目視確認

## 注意
- bid 足か mid 足かを揃える（バックテストは mid 想定 + スプレッドをコストで引く）
- データは再配布できないことが多いので git に入れない（`.gitignore` 済み）
