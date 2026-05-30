#!/usr/bin/env python3
"""Markdownファイル内のアフィリエイトリンクプレースホルダーを実リンクに置換する。

Usage:
    python3 pipeline/insert_affiliate_links.py --input pipeline/articles/20260530_foo.md
    python3 pipeline/insert_affiliate_links.py --input pipeline/articles/ --in-place

プレースホルダー形式: {{AFFILIATE:製品キー}}
リンク辞書: pipeline/affiliate_links.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

LINKS_FILE = Path(__file__).parent / "affiliate_links.json"


def load_links() -> dict[str, str]:
    if not LINKS_FILE.exists():
        print(f"Error: {LINKS_FILE} が見つかりません。affiliate_links.json を作成してください。", file=sys.stderr)
        sys.exit(1)
    return json.loads(LINKS_FILE.read_text(encoding="utf-8"))


def replace_placeholders(text: str, links: dict[str, str]) -> tuple[str, int]:
    count = 0

    def replacer(m: re.Match) -> str:
        nonlocal count
        key = m.group(1)
        url = links.get(key)
        if url:
            count += 1
            return f"[アフィリエイトリンク]({url})"
        return m.group(0)  # キーが辞書にない場合はそのまま残す

    result = re.sub(r"\{\{AFFILIATE:([^}]+)\}\}", replacer, text)
    return result, count


def process_file(path: Path, links: dict[str, str], in_place: bool) -> None:
    text = path.read_text(encoding="utf-8")
    replaced, count = replace_placeholders(text, links)
    if in_place:
        path.write_text(replaced, encoding="utf-8")
        print(f"[insert_affiliate_links] {path.name}: {count}件置換（上書き）")
    else:
        print(replaced)
        print(f"[insert_affiliate_links] {path.name}: {count}件置換", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="アフィリエイトリンクプレースホルダーを置換")
    parser.add_argument("--input", required=True, help="Markdownファイルまたはディレクトリ")
    parser.add_argument("--in-place", action="store_true", help="元ファイルを上書き")
    args = parser.parse_args()

    links = load_links()
    target = Path(args.input)

    if target.is_dir():
        for md_file in sorted(target.glob("*.md")):
            process_file(md_file, links, in_place=True)
    elif target.is_file():
        process_file(target, links, in_place=args.in_place)
    else:
        print(f"Error: {target} が見つかりません。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
