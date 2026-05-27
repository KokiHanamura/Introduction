---
name: daily-setup
description: 当日の作業フォルダ（docs/plans/YYYY-MM-DD/）を作成し、co_plan と ai_todo を初期化する
trigger: セッション開始時に自動確認、または「今日のフォルダ作成して」で手動起動
---

# daily-setup スキル

## 目的

毎作業セッションの開始時に当日フォルダを作成し、協働計画（co_plan）とAI専用TODO（ai_todo）を準備する。

## 実行手順

1. `python3 scripts/create_daily_plan.py` を実行
2. 作成された `docs/plans/YYYY-MM-DD/co_plan.md` に今日の目標を記載（Human が担当）
3. `docs/plans/YYYY-MM-DD/ai_todo.md` は Claude がセッション中に自動更新

## 出力ファイル

- `docs/plans/YYYY-MM-DD/co_plan.md` — Human + AI 協働計画
- `docs/plans/YYYY-MM-DD/ai_todo.md` — AI 専用 TODO（Humans: read-only）

## 注意

- スクリプトは冪等（既にフォルダが存在する場合はスキップ）
- `_template/` のテンプレートをコピーして `{{DATE}}` を今日の日付に置換する
