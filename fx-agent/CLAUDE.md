# CLAUDE.md

# fx-agent

FX トレードの「検証 → 負けパターン分析 → 改善 → 記録分析 → ルールブック」を回すための Claude Code エージェント。
共通ハーネスは `~/claude-harness` から配布（共通ワークフローは `.claude/rules/harness.md`、FX 固有の約束は `.claude/rules/fx-research.md`）。

**目標の定義**: 「必ず勝つ」手法は存在しない。目標は「正の期待値を検証で確かめ、破産しない資金管理で、ルール通りに実行し続ける」こと。
成績の数字は必ず `python3 -m fxagent` の出力から引用し、推測で書かない。

## Commands

| Command | Description |
|---------|-------------|
| `pip install -r requirements.txt` | 依存のインストール |
| `python3 -m pytest -q` | テスト |
| `python3 -m fxagent demo` | 合成データで①〜⑤を一通り実行（動作確認用。成績に意味はない） |
| `python3 -m fxagent backtest --data <csv> --strategy <name> --param k=v` | ① バックテスト |
| `python3 -m fxagent analyze --trades <trades.csv>` | ② 負けパターン + ③ 改善案（IS/OOS 検証つき） |
| `python3 -m fxagent journal --journal <csv>` | ④ 実トレード記録のミス Top5 |
| `python3 -m fxagent rulebook --trades <csv> [--journal <csv>]` | ⑤ ルールブック下書き |
| `python3 .claude/scripts/daily_plan.py "<作業内容>"` | 当日フォルダ作成 |

## Skills（ユーザーの依頼 → スキル）

| 依頼 | スキル |
|---|---|
| 「この手法を検証して」 | `/fx-backtest` |
| 「負けパターンを探して」 | `/fx-loss-patterns` |
| 「手法を改善して」 | `/fx-improve` |
| 「トレード記録を分析して」 | `/fx-journal-review` |
| 「ルールブックを作って」 | `/fx-rulebook` |

成績が良すぎる結果・ルール採用前には `quant-skeptic` エージェントでレビューする。

## Architecture

```
fx-agent/
  .claude/              # claude-harness 管理 + FX 固有（rules/fx-research.md, skills/fx-*, agents/quant-skeptic.md）
  fxagent/              # 検証エンジン（data / indicators / strategies / backtest / metrics / montecarlo / patterns / journal / rulebook）
  tests/                # pytest
  docs/research/        # 要素の洗い出し・検証の落とし穴・ロードマップ・データ入手先
  docs/plans/           # 日次作業フォルダ
  data/                 # 相場データ（git 管理外。data/raw は編集禁止）
  journal/              # トレード記録（template / sample 以外は git 管理外）
  reports/              # 分析結果の出力先（git 管理外）
```

## Gotchas

- 戦略関数は「バー i の終値で確定したシグナル」を返す。エントリーはエンジンが i+1 の始値で行う。戦略側で shift しない
- JPY クロスは `--pip-size 0.01`、それ以外は `--pip-size 0.0001`
- `journal/` の実トレード記録・`data/`・`reports/` はコミットしない
