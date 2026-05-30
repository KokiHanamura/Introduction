#!/usr/bin/env python3
"""記事MarkdownからX(Twitter)投稿文を生成する。

Usage:
    python3 pipeline/generate_x_post.py --input pipeline/articles/20260530_foo.md
    python3 pipeline/generate_x_post.py --input pipeline/articles/ --output pipeline/x_posts/
"""
import argparse
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """\
あなたはX(Twitter)バイラルコンテンツの専門家です。
ブログ記事の内容からX投稿文を3パターン作成してください。

【ルール】
- 各ツイート: 140字以内（日本語）
- 形式: 箇条書きや改行で読みやすく
- フック: 最初の1行で興味を引く（「〜を知ってますか？」「〜が変わった理由」など）
- CTA: 「詳しくはプロフィールのリンクから」「記事URL」などの誘導を末尾に
- ハッシュタグ: #ClaudeCode #AI開発 など関連タグ2〜3個

出力形式:
【パターン1】
（ツイート本文）

【パターン2】
（ツイート本文）

【パターン3】
（ツイート本文）\
"""


def generate_x_posts(article_text: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # 記事が長い場合は冒頭2000字に絞る（コスト削減）
    excerpt = article_text[:2000]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"以下の記事からX投稿文を3パターン作成してください。\n\n---\n{excerpt}",
            }
        ],
    )

    return response.content[0].text


def main():
    parser = argparse.ArgumentParser(description="記事からX投稿文を生成")
    parser.add_argument("--input", required=True, help="Markdownファイルまたはディレクトリ")
    parser.add_argument(
        "--output",
        default="pipeline/x_posts",
        help="出力ディレクトリ（デフォルト: pipeline/x_posts/）",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    target = Path(args.input)
    files = sorted(target.glob("*.md")) if target.is_dir() else [target]

    for md_file in files:
        article = md_file.read_text(encoding="utf-8")
        print(f"[generate_x_post] 処理中: {md_file.name}", file=sys.stderr)
        posts = generate_x_posts(article)
        out_path = output_dir / md_file.name.replace(".md", "_x.txt")
        out_path.write_text(posts, encoding="utf-8")
        print(f"[generate_x_post] 保存: {out_path}")


if __name__ == "__main__":
    main()
