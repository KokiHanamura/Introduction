# エージェント構成とロードマップ

## 構成

```
人間 ──「この手法を検証して」──▶ Claude Code（このリポジトリのハーネス）
                                   │  スキル: /fx-backtest → /fx-loss-patterns → /fx-improve
                                   │         /fx-journal-review → /fx-rulebook
                                   │  レビュー: quant-skeptic（過剰最適化・未来参照を疑う）
                                   ▼
                        python3 -m fxagent（数値は必ずコードで計算）
                        data.py → strategies.py → backtest.py → metrics.py / montecarlo.py
                                                         → patterns.py（②③） → rulebook.py（⑤）
                        journal.py（④）
```

**役割分担の原則**: LLM は「手法をルールに翻訳する・結果を解釈する・次の検証を提案する」。
数字（勝率・PF・DD など）は LLM に計算させず、必ずテスト済みのコードで出す（LLM の暗算は間違える）。

## ①〜⑤のワークフロー

| ステップ | ユーザーの依頼例 | スキル | コマンド |
|---|---|---|---|
| ① 大量検証 | 「この手法を過去 1000 回検証して。勝率・PF・最大連敗・最大 DD を出して」 | `/fx-backtest` | `fxagent backtest` |
| ② 負けパターン | 「負けトレードに共通する条件を全部洗い出して」 | `/fx-loss-patterns` | `fxagent analyze` |
| ③ 改善 | 「期待値を下げている条件を特定して改善案を出して」 | `/fx-improve` | `fxagent analyze` + 再 backtest |
| ④ 記録分析 | 「過去 50 回のトレードから俺が繰り返しているミスを 5 つ」 | `/fx-journal-review` | `fxagent journal` |
| ⑤ ルールブック | 「俺専用のエントリー・損切り・利確・見送りルールを作って」 | `/fx-rulebook` | `fxagent rulebook` |

## ロードマップ

### Phase 0（今回）✅
- ハーネス（claude-harness v1.0.1 + FX 固有ルール・スキル・レビュアー）
- 要素の洗い出し（`00_winning-elements.md`）と検証の落とし穴（`01`）
- 検証エンジン最小版（①〜⑤が合成データで一通り動く、テスト 15 件）

### Phase 1: 実データで回す
- [ ] 実データ取得（`03_data-sources.md`）: USDJPY・EURUSD・GBPJPY の H1 / M15、最低 5 年
- [ ] ユーザーの実際の手法を 1 つルール化して①〜③
- [ ] ユーザーの実トレード記録（50 件〜）で④⑤
- [ ] パラメータ感度表・ウォークフォワード検証を `fxagent` に追加

### Phase 2: 検証の精度を上げる
- [ ] 時間帯別スプレッド、スワップ
- [ ] 経済指標カレンダー・介入警戒の特徴量
- [ ] 複数通貨ペアの同時検証と相関エクスポージャー
- [ ] Deflated Sharpe Ratio / PBO

### Phase 3: 運用支援（自動売買はまだしない）
- [ ] 実運用成績 vs バックテスト分布の監視レポート（週次、GitHub Actions）
- [ ] エントリー前チェックリスト（ルールブックから生成）
- [ ] 停止条件の自動判定と通知

自動売買（API 発注）は、Phase 3 で実運用の成績がバックテスト分布の内側に収まることを確認してから検討する。
