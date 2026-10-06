# fx-agent

FX トレードを **感覚ではなくデータで** 改善するための Claude Code エージェント。

1. 過去チャートで手法を大量検証（勝率・PF・期待値・最大連敗・最大 DD・モンテカルロ）
2. 負けトレードに共通する条件を洗い出す
3. 期待値を下げている条件を特定し、アウトオブサンプルで確かめてから改善
4. 自分のトレード記録から繰り返しているミスを損失額順に特定
5. 1〜4 を根拠にした自分専用ルールブックを作る

```bash
pip install -r requirements.txt
python3 -m pytest -q
python3 -m fxagent demo          # 合成データでの動作確認
```

調査メモ: [`docs/research/00_winning-elements.md`](docs/research/00_winning-elements.md)

> 本ツールは検証・学習用。将来の利益を保証するものではなく、投資助言ではありません。
