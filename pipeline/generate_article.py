#!/usr/bin/env python3
"""キーワードから日本語SEO記事を生成する。

Usage:
    python3 pipeline/generate_article.py --keyword "Claude Code 使い方" [--niche "AI開発ツール"]
    python3 pipeline/generate_article.py --keyword "Cursor IDE 比較" --output articles/

Output: Markdownファイル（アフィリエイトリンクプレースホルダー付き）
"""
import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

NICHE_DEFAULT = "Claude Code / AI開発ツール活用"

# キャッシュ対象: 変わらないシステムプロンプト
SYSTEM_PROMPT = """\
あなたは日本語SEOコンテンツの専門家です。以下の条件でブログ記事を作成してください。

【ライティングルール】
- 読者: 個人開発者・副業エンジニア・AI活用に興味を持つビジネスマン（日本語話者）
- 文体: 丁寧語（ですます調）、親しみやすいが専門的
- 構成: H2見出し4〜6個、各H2に200〜400字、H3も適宜使用
- 文字数: 2,000〜3,000字
- E-E-A-T: 実体験ベースの表現（「私が実際に使ってみた」「〜してみると」）
- SEO: キーワードをタイトル・冒頭・H2に自然に含める
- CTA: 末尾に「まとめ」セクションと行動喚起を入れる

【アフィリエイトリンクプレースホルダー規則】
記事中で紹介した製品名の後に {{AFFILIATE:製品キー}} を挿入すること。
例: Cursor IDE {{AFFILIATE:cursor}} を使うと〜
製品キー一覧: cursor, perplexity, claude_pro, amazon, a8

出力はMarkdown形式のみ（コードブロック不要）。\
"""


def generate_article(keyword: str, niche: str = NICHE_DEFAULT) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_prompt = f"""\
ニッチ: {niche}
メインキーワード: {keyword}

上記のキーワードで、そのニッチの読者に刺さるSEO記事を書いてください。
タイトルはキーワードを含む魅力的な日本語タイトルにしてください。
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    usage = response.usage
    print(
        f"[generate_article] tokens: input={usage.input_tokens} "
        f"(cache_read={getattr(usage, 'cache_read_input_tokens', 0)}, "
        f"cache_write={getattr(usage, 'cache_creation_input_tokens', 0)}) "
        f"output={usage.output_tokens}",
        file=sys.stderr,
    )

    return response.content[0].text


def keyword_to_filename(keyword: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", keyword).strip().replace(" ", "_")
    date_prefix = datetime.now().strftime("%Y%m%d")
    return f"{date_prefix}_{slug}.md"


def main():
    parser = argparse.ArgumentParser(description="キーワードからSEO記事を生成")
    parser.add_argument("--keyword", required=True, help="メインキーワード")
    parser.add_argument("--niche", default=NICHE_DEFAULT, help="記事のニッチ")
    parser.add_argument(
        "--output",
        default="pipeline/articles",
        help="出力ディレクトリ（デフォルト: pipeline/articles/）",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。", file=sys.stderr)
        sys.exit(1)

    print(f"[generate_article] 記事生成中: {args.keyword}", file=sys.stderr)
    article = generate_article(args.keyword, args.niche)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = keyword_to_filename(args.keyword)
    output_path = output_dir / filename

    output_path.write_text(article, encoding="utf-8")
    print(f"[generate_article] 保存完了: {output_path}")


if __name__ == "__main__":
    main()
