# .claude/skills — プロジェクトスキル一覧

このディレクトリはプロジェクト固有のスキル定義を蓄積する場所。
Claude は CLAUDE.md を通じてこれらのスキルを毎セッション参照する。

## 利用可能なスキル

| ファイル | name | 概要 |
|---------|------|------|
| `daily-setup.md` | daily-setup | 当日の作業フォルダ（docs/plans/YYYY-MM-DD/）を作成・初期化 |

## 新しいスキルの追加手順

1. このディレクトリに `skill-name.md` を作成（ケバブケース）
2. 以下の frontmatter を必ず含める:
   ```
   ---
   name: skill-name
   description: スキルの一行説明
   trigger: いつ/どのように使うか
   ---
   ```
3. 上の表にエントリを追加
4. `CLAUDE.md` の Skills セクションも更新する
