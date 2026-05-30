#!/usr/bin/env python3
"""PreToolUse(EnterPlanMode): 当日フォルダが未作成なら「作業」で自動生成する。"""
import glob
import json
import os
import sys
from datetime import date

today = date.today().strftime("%Y%m%d")
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
plans_dir = os.path.join(root, "docs", "plans")

if glob.glob(os.path.join(plans_dir, f"{today}_*")):
    sys.exit(0)  # 既に存在 → 何もしない

template_dir = os.path.join(plans_dir, "_template")
folder_name = f"{today}_作業"
folder = os.path.join(plans_dir, folder_name)
os.makedirs(folder)

date_label = date.today().strftime("%Y-%m-%d")
for fname in ["co_plan.md", "ai_todo.md"]:
    src = os.path.join(template_dir, fname)
    dst = os.path.join(folder, fname)
    if os.path.exists(src):
        with open(src) as f:
            content = f.read().replace("{{DATE}}", date_label)
        with open(dst, "w") as f:
            f.write(content)

print(json.dumps({
    "message": f"[ensure_daily_plan] 当日フォルダを自動作成しました: docs/plans/{folder_name}/"
}))
