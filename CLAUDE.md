# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Introduction

Claude Code ハーネスエンジニアリングの実験・学習リポジトリ。

## Purpose

このリポジトリの3つの役割:
1. Claude Code ハーネス設定のリファレンス実装
2. 個人の開発パターン・ワークフローの実験場
3. 新しいプロジェクト作成時のテンプレート元

## Commands

| Command | Description |
|---------|-------------|
| `python3 -m pytest` | テスト実行 |
| `git status` | 作業状態確認 |
| `git log --oneline -10` | 最近のコミット確認 |

## Architecture

```
Introduction/
  .claude/
    settings.json             # パーミッション・フック設定（バージョン管理）
    hooks/
      check_dangerous.py      # PreToolUse: 危険コマンドブロック
      check_sensitive_files.py # PostToolUse: 機密ファイル警告
      session_summary.py      # Stop: 未コミット変更サマリ
    skills/
      README.md               # スキル追加ガイド・一覧インデックス
      daily-setup.md          # 当日作業フォルダ作成スキル
  docs/
    plans/
      _template/              # co_plan/ai_todo のテンプレート
      YYYYMMDD_<説明>/         # 日次作業フォルダ（スクリプトで自動生成）
        co_plan.md            # Human + AI 協働計画
        ai_todo.md            # AI 専用 TODO（Humans: read-only）
  scripts/
    create_daily_plan.py      # 日次フォルダ作成スクリプト
  .github/
    PULL_REQUEST_TEMPLATE.md
  CLAUDE.md                   # このファイル（毎セッション読み込まれる）
  README.md                   # 公開向け説明
```

## Harness Design

### Hook Events

| Event | Matcher | Script | 役割 |
|-------|---------|--------|------|
| PreToolUse | Bash | check_dangerous.py | 破壊的コマンドをブロック |
| PreToolUse | EnterPlanMode | ensure_daily_plan.py | 当日フォルダ未作成時に自動生成 |
| PostToolUse | Edit/Write | check_sensitive_files.py | 機密ファイル編集を警告 |
| Stop | — | session_summary.py | 未コミット変更を通知 |
| Stop | — | `afplay Hero.aiff` | 作業完了を効果音で通知 |

### Permission Model

**事前承認済み（摩擦ゼロ）**: `git status/log/diff/add/commit/branch/checkout/stash`、`find`、`grep`、`ls`、`python3`、`Read`

**明示的拒否**: `git push --force`、`git reset --hard`、`sudo`

## Gotchas

- `.claude/settings.json` はチーム設定としてバージョン管理に含める
- `.claude/settings.local.json` は個人設定として gitignore 対象（`Write(.claude/settings.json)` 権限を付与済み）
- グローバル `~/.claude/settings.json` とプロジェクト設定はマージされる（プロジェクト側が優先）
- `gh` CLI が未インストールの場合: `brew install gh`

## Skills

プロジェクト固有スキルは `.claude/skills/` に定義。新スキル追加時は同ディレクトリの `README.md` を参照。

| スキル | 起動方法 | 概要 |
|--------|---------|------|
| daily-setup | 「今日のフォルダ作成して」 | `python3 scripts/create_daily_plan.py "<作業内容>"` を実行し当日フォルダを初期化（description 引数必須） |

## Workflow

- **セッション開始時**: プランを立てると `ensure_daily_plan.py` フックが自動実行され `docs/plans/YYYYMMDD_作業/` を生成する（手動で説明付きフォルダを作る場合は `python3 scripts/create_daily_plan.py "<作業内容>"`）
- `ai_todo.md` は Claude のみ編集（Humans: read-only）
- 新機能: ブランチを切って実装 → PR
- コミット: 変更の意図（why）を中心に記述
- 新スキル習得時: `.claude/skills/` にファイルを追加し、上表を更新
