# -*- coding: utf-8 -*-
"""
LẤY GÓI ptcp TỪ MỘT NGUỒN DUY NHẤT (repo danh-muc) – bot không giữ bản sao riêng nữa.

GitHub Actions (bước "Lấy ptcp"): clone nông repo bằng token CHỈ ĐỌC rồi chép thư mục ptcp vào cạnh chay.py.
  Biến môi trường: TOKEN (secret DANH_MUC_TOKEN), REPO (vars.PTCP_REPO hoặc vars.DANH_MUC_REPO),
                   DUONG_DAN (vars.PTCP_PATH, mặc định ptcp_phan_tich/ptcp).
Chạy trên máy: python lay_ptcp.py --tu ../ptcp_phan_tich/ptcp   (chép từ thư mục có sẵn)
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

DICH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ptcp")


def chep(nguon):
    if not os.path.isfile(os.path.join(nguon, "__init__.py")):
        sys.exit(f"✘ {nguon} không phải thư mục gói ptcp (thiếu __init__.py)")
    shutil.rmtree(DICH, ignore_errors=True)
    shutil.copytree(nguon, DICH, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tu", help="chép từ thư mục ptcp có sẵn trên máy")
    a = p.parse_args()
    if a.tu:
        chep(a.tu)
    else:
        token, repo = os.environ.get("TOKEN", "").strip(), os.environ.get("REPO", "").strip()
        duong_dan = os.environ.get("DUONG_DAN", "").strip() or "ptcp_phan_tich/ptcp"
        if not (token and repo):
            sys.exit("✘ Thiếu secret DANH_MUC_TOKEN hoặc variable DANH_MUC_REPO / PTCP_REPO – xem README (Cài đặt).")
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(["git", "clone", "--depth", "1", "--quiet",
                                f"https://x-access-token:{token}@github.com/{repo}.git", tmp],
                               capture_output=True, text=True)
            if r.returncode != 0:                      # không in thông báo lỗi gốc (có thể chứa URL kèm token)
                sys.exit(f"✘ Không clone được {repo}: token sai/hết hạn hoặc chưa được cấp quyền đọc repo này.")
            chep(os.path.join(tmp, duong_dan))
    sys.path.insert(0, os.path.dirname(DICH))
    import ptcp
    print(f"✔ ptcp {ptcp.__version__} – {len([f for f in os.listdir(DICH) if f.endswith('.py')])} module")


if __name__ == "__main__":
    main()
