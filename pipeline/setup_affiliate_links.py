#!/usr/bin/env python3
"""アフィリエイトリンクを対話形式で設定する。

Usage:
    python3 pipeline/setup_affiliate_links.py

設定済みのURLはスキップできる（Enterで保持）。
"""
import json
from pathlib import Path

LINKS_FILE = Path(__file__).parent / "affiliate_links.json"

PROGRAMS = [
    {
        "key": "cursor",
        "name": "Cursor IDE",
        "how_to_get": "https://www.cursor.com/referral → Referral link をコピー",
        "placeholder": "https://cursor.sh/?ref=YOURCODE",
    },
    {
        "key": "perplexity",
        "name": "Perplexity AI",
        "how_to_get": "https://perplexity.ai/settings/referrals → Referral link をコピー",
        "placeholder": "https://perplexity.ai/?ref=YOURCODE",
    },
    {
        "key": "claude_pro",
        "name": "Anthropic Claude Pro",
        "how_to_get": "Anthropicアフィリエイトプログラム（要申請）",
        "placeholder": "https://claude.ai/upgrade?ref=YOURCODE",
    },
    {
        "key": "amazon",
        "name": "Amazon アソシエイト",
        "how_to_get": "https://affiliate.amazon.co.jp → リンクを作成 → タグ: YOURTAG-22",
        "placeholder": "https://www.amazon.co.jp/?tag=YOURTAG-22",
    },
    {
        "key": "a8",
        "name": "A8.net",
        "how_to_get": "A8.net 管理画面 → 素材 → テキストリンク URLをコピー",
        "placeholder": "https://px.a8.net/svt/ejp?a8mat=YOURCODE",
    },
]


def main():
    current = json.loads(LINKS_FILE.read_text(encoding="utf-8")) if LINKS_FILE.exists() else {}

    print("=" * 60)
    print("アフィリエイトリンク設定ウィザード")
    print("Enter で現在の値を保持 / URLを入力で更新 / 's' でスキップ")
    print("=" * 60)

    updated = dict(current)

    for prog in PROGRAMS:
        key = prog["key"]
        current_url = current.get(key, prog["placeholder"])
        is_placeholder = "YOURCODE" in current_url or "YOURTAG" in current_url

        status = "⚠️  未設定" if is_placeholder else "✅ 設定済み"
        print(f"\n【{prog['name']}】 {status}")
        print(f"  取得方法: {prog['how_to_get']}")
        print(f"  現在値: {current_url}")

        new_url = input("  新しいURL (Enter=保持): ").strip()
        if new_url.lower() == "s":
            print("  → スキップ")
        elif new_url:
            updated[key] = new_url
            print(f"  → 更新: {new_url}")
        else:
            print("  → 保持")

    # _comment を先頭に保つ
    output = {"_comment": "アフィリエイトリンク辞書。setup_affiliate_links.py で管理。"}
    output.update({k: v for k, v in updated.items() if k != "_comment"})

    LINKS_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n✅ affiliate_links.json を保存しました。")

    # 未設定のまま残っているものを警告
    remaining = [p["name"] for p in PROGRAMS if "YOURCODE" in output.get(p["key"], "") or "YOURTAG" in output.get(p["key"], "")]
    if remaining:
        print(f"⚠️  まだ未設定: {', '.join(remaining)}")


if __name__ == "__main__":
    main()
