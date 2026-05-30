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

import requests
from dotenv import load_dotenv

load_dotenv()


def extract_title(markdown: str) -> tuple[str, str]:
    """H1または最初の行からタイトルを抽出し、本文と分離する。"""
    lines = markdown.strip().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body = "\n".join(lines[i + 1:]).strip()
            return title, body
    return "無題の記事", markdown


def markdown_to_html_basic(markdown: str) -> str:
    """最小限のMarkdown→HTML変換（H2/H3/段落のみ）。
    本番ではWordPressプラグイン（Markdown有効化）推奨。
    """
    lines = markdown.splitlines()
    html_lines = []
    for line in lines:
        if line.startswith("## "):
            html_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.strip() == "":
            html_lines.append("")
        else:
            html_lines.append(f"<p>{line}</p>")
    return "\n".join(html_lines)


def post_to_wordpress(title: str, content: str, status: str = "draft") -> dict:
    wp_url = os.environ.get("WP_URL", "").rstrip("/")
    wp_user = os.environ.get("WP_USER", "")
    wp_password = os.environ.get("WP_PASSWORD", "")

    if not all([wp_url, wp_user, wp_password]):
        print("Error: WP_URL / WP_USER / WP_PASSWORD が .env に未設定です。", file=sys.stderr)
        sys.exit(1)

    endpoint = f"{wp_url}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }

    response = requests.post(
        endpoint,
        json=payload,
        auth=(wp_user, wp_password),
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
        html = markdown_to_html_basic(body)
        print(f"[post_wordpress] 投稿中: {title}", file=sys.stderr)
        result = post_to_wordpress(title, html, args.status)
        post_id = result.get("id")
        post_link = result.get("link", "")
        print(f"[post_wordpress] 完了: id={post_id} url={post_link}")


if __name__ == "__main__":
    main()
