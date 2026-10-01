# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Introduction

Claude Code ハーネスエンジニアリングの実験・学習リポジトリ。
共通ハーネスは `~/claude-harness` から配布されている（共通ワークフローは `.claude/rules/harness.md`）。

## Purpose

1. 個人の開発パターン・ワークフローの実験場（全体に効くものは `~/claude-harness` に昇格させる）
2. アフィリエイト記事の自動生成パイプライン（`pipeline/`）

## Commands

| Command | Description |
|---------|-------------|
| `python3 .claude/scripts/daily_plan.py "<作業内容>"` | 当日フォルダ作成 |
| `git log --oneline -10` | 最近のコミット確認 |

## Architecture

```
Introduction/
  .claude/                  # claude-harness 管理（settings.json は生成物。固有設定は settings.repo.json）
  pipeline/                 # 記事生成 → アフィリエイトリンク挿入 → WordPress 投稿 / X 投稿生成
  docs/plans/               # 日次作業フォルダ
  .github/workflows/        # daily_article.yml（日次の記事生成）
```

## Gotchas

- `.claude/settings.local.json` は個人設定（gitignore 対象）
- `gh` CLI が未インストールの場合: `brew install gh`
- API キーは `pipeline/.env`（`.env.example` を参照）。コミットしない
