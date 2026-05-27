#!/usr/bin/env python3
"""当日の作業フォルダを docs/plans/YYYY-MM-DD/ に作成する。"""
import os
from datetime import date


def main():
    today = date.today().strftime("%Y-%m-%d")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    today_dir = os.path.join(root, "docs", "plans", today)
    template_dir = os.path.join(root, "docs", "plans", "_template")

    if os.path.exists(today_dir):
        print(f"既に存在: docs/plans/{today}/")
        return

    os.makedirs(today_dir)

    for fname in ["co_plan.md", "ai_todo.md"]:
        src = os.path.join(template_dir, fname)
        dst = os.path.join(today_dir, fname)
        if os.path.exists(src):
            with open(src) as f:
                content = f.read().replace("{{DATE}}", today)
            with open(dst, "w") as f:
                f.write(content)

    print(f"作成完了: docs/plans/{today}/")
    print(f"  co_plan.md  <- 今日の目標を記載してください")
    print(f"  ai_todo.md  <- Claude が自動更新します")


if __name__ == "__main__":
    main()
