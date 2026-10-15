# -*- coding: utf-8 -*-
"""
NẠP GÓI ptcp – MỘT nguồn logic dùng chung với ptcp (Colab), danh-muc và canh-bao-mua.
Bộ lọc KHÔNG giữ bản sao lõi nữa (trước đây bo_loc/loi chép tay từ ptcp → hay lệch, mỗi lỗi phải sửa 2 nơi).

Thứ tự tìm ptcp:
  1) đã import được (cài sẵn / có trên sys.path)
  2) thư mục ptcp/ cạnh bo_loc_co_phieu.py (gốc repo) hoặc biến môi trường PTCP_DIR (thư mục CHỨA ptcp/)
  3) tự tải từ repo danh-muc nếu có DANH_MUC_TOKEN (+ DANH_MUC_REPO, mặc định mihhle2006-beep/danh-muc) – giống
     bước "Lấy ptcp" của GitHub Actions (python lay_ptcp.py)
Không có → báo lỗi rõ cách lấy.
"""
import importlib
import os
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _co_ptcp(thu_muc):
    return os.path.isfile(os.path.join(thu_muc, "ptcp", "__init__.py"))


def nap_ptcp():
    try:
        return importlib.import_module("ptcp")
    except ImportError:
        pass
    for d in (os.environ.get("PTCP_DIR", ""), GOC, os.getcwd()):
        if d and _co_ptcp(d):
            sys.path.insert(0, d)
            return importlib.import_module("ptcp")
    token = os.environ.get("DANH_MUC_TOKEN", "").strip() or os.environ.get("TOKEN", "").strip()
    if token:
        import subprocess
        env = {**os.environ, "TOKEN": token,
               "REPO": os.environ.get("PTCP_REPO") or os.environ.get("DANH_MUC_REPO") or "mihhle2006-beep/danh-muc",
               "DUONG_DAN": os.environ.get("PTCP_PATH") or "ptcp"}
        subprocess.run([sys.executable, os.path.join(GOC, "lay_ptcp.py")], env=env, check=False)
        if _co_ptcp(GOC):
            sys.path.insert(0, GOC)
            return importlib.import_module("ptcp")
    raise ImportError(
        "Bộ lọc cần gói ptcp (lõi dùng chung, ở repo danh-muc). Cách lấy:\n"
        "  • Máy/Colab: chép thư mục ptcp/ vào cạnh bo_loc_co_phieu.py, hoặc đặt PTCP_DIR = thư mục chứa ptcp/\n"
        "  • Hoặc đặt DANH_MUC_TOKEN (token chỉ đọc repo danh-muc) → tự tải\n"
        "  • GitHub Actions: secret DANH_MUC_TOKEN_GHI (bước 'Lấy ptcp' tự chạy python lay_ptcp.py)")


def bi_danh(ten_bo_loc, ten_ptcp):
    """Cho module bo_loc.<...> trỏ thẳng tới ptcp.<...> (cùng một đối tượng – monkeypatch/test vẫn chạy)."""
    nap_ptcp()
    m = importlib.import_module(ten_ptcp)
    sys.modules[ten_bo_loc] = m
    goc, _, la = ten_bo_loc.rpartition(".")
    if goc in sys.modules:
        setattr(sys.modules[goc], la, m)
    return m
