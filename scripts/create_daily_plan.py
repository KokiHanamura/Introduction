#!/usr/bin/env python3
"""当日の作業フォルダを docs/plans/YYYYMMDD_<description>/ に作成する。

使い方:
  python3 scripts/create_daily_plan.py "ビジネスプランの策定"
  → docs/plans/20260528_ビジネスプランの策定/ を作成
"""
import os
import sys
from datetime import date


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 scripts/create_daily_plan.py \"<作業内容>\"")
        print("例:     python3 scripts/create_daily_plan.py \"ビジネスプランの策定\"")
        sys.exit(1)

    description = sys.argv[1]
    today = date.today().strftime("%Y%m%d")
    folder_name = f"{today}_{description}"

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    today_dir = os.path.join(root, "docs", "plans", folder_name)
    template_dir = os.path.join(root, "docs", "plans", "_template")

    if os.path.exists(today_dir):
        print(f"既に存在: docs/plans/{folder_name}/")
        return

    os.makedirs(today_dir)

    date_label = date.today().strftime("%Y-%m-%d")
    for fname in ["co_plan.md", "ai_todo.md"]:
        src = os.path.join(template_dir, fname)
        dst = os.path.join(today_dir, fname)
        if os.path.exists(src):
            with open(src) as f:
                content = f.read().replace("{{DATE}}", date_label)
            with open(dst, "w") as f:
                f.write(content)

    print(f"作成完了: docs/plans/{folder_name}/")
    print(f"  co_plan.md  <- 今日の目標を記載してください")
    print(f"  ai_todo.md  <- Claude が自動更新します")


if __name__ == "__main__":
    main()
