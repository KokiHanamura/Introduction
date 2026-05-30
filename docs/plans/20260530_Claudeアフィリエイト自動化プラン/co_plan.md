# 作業計画 - 2026-05-30

## 今日の目標

Claude を活用してアフィリエイト収益を自動化するプランを設計する。

## タスクブレイクダウン

### 仕組み構築（Claude が担当）
- [x] アフィリエイト自動化戦略設計（ニッチ・チャネル・パイプライン）
- [x] `.claude/hooks/ensure_daily_plan.py` 作成
- [x] `.claude/settings.json` 作成（PreToolUse + Stop 音声）
- [x] `CLAUDE.md` Hook Events テーブル更新

### Phase 0 — 土台構築（Human 担当）
- [ ] アフィリエイトプログラム申請（A8.net, Amazon アソシエイト, Cursor IDE）
- [ ] WordPress サイト立ち上げ
- [ ] Google Search Console / Analytics 設定
- [ ] コンテンツカレンダー (Google Sheets) テンプレ作成

### Phase 1 — 自動化スクリプト構築（Claude が実装）
- [x] `pipeline/generate_article.py` — Claude API でキーワード→記事生成
- [x] `pipeline/post_wordpress.py` — WP REST API で下書き自動投稿
- [x] `pipeline/generate_x_post.py` — 記事ハイライトを X 用に変換
- [x] `pipeline/insert_affiliate_links.py` — キーワード→リンク辞書置換
- [x] GitHub Actions cron 設定（毎朝自動実行）

### Phase 2 — 品質・量の両立
- [ ] SEO 最適化（見出し構造・内部リンク自動生成）
- [ ] note/Zenn への横展開（記事要約→転載）
- [ ] 成果トラッキングダッシュボード

## 進捗メモ

### Phase 1 完了（2026-05-30）

全スクリプトを `pipeline/` に実装済み:
- `generate_article.py`: Claude Sonnet API + プロンプトキャッシュ、Markdown出力、`{{AFFILIATE:key}}` プレースホルダー挿入
- `insert_affiliate_links.py`: `affiliate_links.json` 辞書で一括置換
- `generate_x_post.py`: 記事冒頭2000字から3パターンのX投稿文生成
- `post_wordpress.py`: WP REST API で下書き投稿（アプリケーションパスワード認証）
- `.github/workflows/daily_article.yml`: 毎朝7時JST自動実行、workflow_dispatch で手動キーワード指定可

**次のアクション（Phase 0 — Human担当）**:
1. `pipeline/.env.example` → `.env` にコピーして `ANTHROPIC_API_KEY` / `WP_URL` / `WP_USER` / `WP_PASSWORD` を設定
2. `pipeline/affiliate_links.json` の各URLを実際のアフィリエイトリンクに書き換え
3. GitHub Secrets に `ANTHROPIC_API_KEY` / `WP_URL` / `WP_USER` / `WP_PASSWORD` を登録
4. WordPress サイト立ち上げ後、`python3 pipeline/generate_article.py --keyword "Claude Code 使い方"` でテスト実行

## 決定・学び

### アフィリエイト自動化戦略（2026-05-30）

**ニッチ**: 「Claude Code / AI 開発ツール活用」特化（日本語、競合が薄い）

**自動化パイプライン**
```
Google Sheets（コンテンツカレンダー）
 → キーワード選定 → Claude Sonnet API で記事生成
 → WordPress 下書き投稿 / X 予約投稿 / note 転載
 → アフィリエイトリンク辞書で自動挿入
 → Analytics で週次レポート
```

**アフィリエイトプログラム候補**

| プログラム | 報酬 | 優先度 |
|-----------|------|--------|
| Cursor IDE | 20% 継続 | ★★★ |
| Perplexity AI | $10/転換 | ★★★ |
| A8.net / Amazon | 3〜10% | ★★ |
| Anthropic Claude Pro | 要確認 | ★★★（本命） |

**収益シミュレーション（3ヶ月後）**
- 記事数: 90本（1日1本、確認15分/本）
- 月間PV: 10,000
- 保守的収入: ¥30,000〜50,000 / 楽観的: ¥100,000+

**技術スタック**: Python + GitHub Actions + Claude Sonnet API + WP REST API + Buffer API
