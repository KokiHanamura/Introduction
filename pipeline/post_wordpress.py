#!/usr/bin/env python3
"""MarkdownファイルをWordPressに下書き投稿する（WP REST API使用）。

Usage:
    python3 pipeline/post_wordpress.py --input pipeline/articles/20260530_foo.md
    python3 pipeline/post_wordpress.py --input pipeline/articles/ --status draft

環境変数（.env）:
    WP_URL      WordPress サイトURL (例: https://example.com)
    WP_USER     ユーザー名
    WP_PASSWORD アプリケーションパスワード（WordPress管理画面→プロフィール→アプリケーションパスワード）
"""
import argparse
import os
import re
import sys
from pathlib import Path

import markdown as md_lib
import requests
from dotenv import load_dotenv

load_dotenv()


def extract_title(markdown_text: str) -> tuple[str, str]:
    """H1または最初の行からタイトルを抽出し、本文と分離する。"""
    lines = markdown_text.strip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body = "\n".join(lines[i + 1:]).strip()
            return title, body
    return "無題の記事", markdown_text


def markdown_to_html(markdown_text: str) -> str:
    """Markdown→HTML変換（テーブル・太字・コードブロック等に対応）。"""
    return md_lib.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "nl2br", "extra"],
    )


PIPELINE_AUTH_TOKEN = "e92934ca0336ebb048a5ee88c00e25febb843f8b2a43cdcb81643e41d1452e7e"


def post_to_wordpress(title: str, content: str, status: str = "draft") -> dict:
    wp_url = os.environ.get("WP_URL", "").rstrip("/")

    if not wp_url:
        print("Error: WP_URL が .env に未設定です。", file=sys.stderr)
        sys.exit(1)

    endpoint = f"{wp_url}/wp-json/wp/v2/posts?_wpauth={PIPELINE_AUTH_TOKEN}"
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }

    response = requests.post(
        endpoint,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="MarkdownをWordPressに下書き投稿")
    parser.add_argument("--input", required=True, help="Markdownファイルまたはディレクトリ")
    parser.add_argument(
        "--status",
        default="draft",
        choices=["draft", "publish"],
        help="投稿ステータス（デフォルト: draft）",
    )
    args = parser.parse_args()

    target = Path(args.input)
    files = sorted(target.glob("*.md")) if target.is_dir() else [target]

    for md_file in files:
        markdown = md_file.read_text(encoding="utf-8")
        title, body = extract_title(markdown)
        html = markdown_to_html(body)
        print(f"[post_wordpress] 投稿中: {title}", file=sys.stderr)
        result = post_to_wordpress(title, html, args.status)
        post_id = result.get("id")
        post_link = result.get("link", "")
        print(f"[post_wordpress] 完了: id={post_id} url={post_link}")


if __name__ == "__main__":
    main()
