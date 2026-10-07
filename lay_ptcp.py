# -*- coding: utf-8 -*-
"""
LẤY GÓI ptcp.
  1) Repo này đã có thư mục ptcp/ (cạnh chay.py) → dùng luôn (cách đơn giản, 1 repo).
  2) Không có → clone từ repo khác (danh-muc) bằng token CHỈ ĐỌC, tự tìm thư mục ptcp trong repo đó.

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


def _la_goi_ptcp(d):
    return os.path.isfile(os.path.join(d, "__init__.py")) and os.path.isfile(os.path.join(d, "cau_hinh.py"))


def tim_ptcp(goc, duong_dan, repo=""):
    """Ưu tiên DUONG_DAN; không có → tự tìm thư mục tên 'ptcp' (có __init__.py + cau_hinh.py) gần gốc nhất."""
    dung = os.path.join(goc, duong_dan)
    if _la_goi_ptcp(dung):
        return dung
    thay = []
    for thu_muc, con, _ in os.walk(goc):
        con[:] = [c for c in con if not c.startswith(".") and c not in ("__pycache__", "node_modules")]
        if os.path.basename(thu_muc) == "ptcp" and _la_goi_ptcp(thu_muc):
            thay.append(thu_muc)
    if not thay:
        sys.exit(f"✘ Repo {repo} không có gói ptcp (thư mục 'ptcp' chứa __init__.py).\n"
                 f"  → Upload thư mục ptcp_phan_tich/ptcp vào repo {repo}, hoặc đặt variable PTCP_REPO "
                 f"trỏ đến repo đang chứa ptcp.")
    chon = min(thay, key=lambda x: (x.count(os.sep), x))
    print(f"⚠ Không thấy ptcp ở '{duong_dan}' → dùng '{os.path.relpath(chon, goc)}' "
          f"(đặt variable PTCP_PATH = đường dẫn này để hết cảnh báo)")
    return chon


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tu", help="chép từ thư mục ptcp có sẵn trên máy")
    a = p.parse_args()
    if a.tu:
        chep(a.tu)
    elif _la_goi_ptcp(DICH):                           # ptcp đã nằm sẵn trong repo này → dùng luôn, không clone
        print("ptcp có sẵn trong repo → dùng trực tiếp")
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
            chep(tim_ptcp(tmp, duong_dan, repo))
    sys.path.insert(0, os.path.dirname(DICH))
    import ptcp
    print(f"✔ ptcp {ptcp.__version__} – {len([f for f in os.listdir(DICH) if f.endswith('.py')])} module")


if __name__ == "__main__":
    main()
