# -*- coding: utf-8 -*-
"""
VỊ THẾ ĐANG GIỮ & CẢNH BÁO BÁN.

Nguồn vị thế (cách 2): đọc danh_muc.csv từ repo RIÊNG TƯ `danh-muc` qua GitHub API bằng token CHỈ ĐỌC.
  Biến môi trường (GitHub Actions): DANH_MUC_TOKEN (secret), DANH_MUC_REPO (variable, VD "ten-ban/danh-muc"),
  DANH_MUC_PATH (tuỳ chọn, mặc định "danh_muc.csv"), DANH_MUC_NHANH (tuỳ chọn, mặc định nhánh mặc định của repo).
  Chạy trên máy: đặt file danh_muc.csv cạnh chay.py (đã có trong .gitignore – KHÔNG đẩy lên repo công khai).

Repo bot là CÔNG KHAI → log Actions ai cũng xem được: KHÔNG in số CP, giá vốn, cắt lỗ ra log;
trạng thái chống báo trùng của lệnh bán lưu trong actions/cache (cache_ptcp/), không commit lên repo.

Mức cảnh báo (ưu tiên từ trên xuống):
  CAT_LO       giá ≤ cắt lỗ đã đặt (cat_lo_dat; thiếu thì cat_lo_goc)
  CHOT_LOI     giá ≥ mục tiêu đã đặt (muc_tieu_dat; thiếu thì gia_muc_tieu)
  CAN_NHAC_BAN tuần mất xu hướng (MACD tuần < Signal) / giá dưới SuperTrend ngày / ptcp khuyến nghị BÁN
  DOI_CAT_LO   lãi ≥ 1R mà cắt lỗ còn dưới giá vốn → gợi ý nâng cắt lỗ lên hoà vốn
  GIU          không có gì
"""
import io
import json
import os

import numpy as np
import pandas as pd
import requests

from . import cau_hinh as C
from .chi_bao import supertrend

MUC = ["CAT_LO", "CHOT_LOI", "CAN_NHAC_BAN", "DOI_CAT_LO", "GIU"]
NHAN = {"CAT_LO": "🔴 CẮT LỖ", "CHOT_LOI": "🟢 CHỐT LỜI", "CAN_NHAC_BAN": "🟠 CÂN NHẮC BÁN",
        "DOI_CAT_LO": "🟡 DỜI CẮT LỖ", "GIU": "⚪ GIỮ"}
FILE_TRANG_THAI_BAN = os.path.join("cache_ptcp", "trang_thai_ban.json")
FILE_TRANG_THAI_MUA_AN = os.path.join("cache_ptcp", "trang_thai_mua_ma_an.json")


def _so(x):
    try:
        s = str(x).strip().replace(" ", "")
        if not s or s.lower() in ("nan", "none"):
            return None
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        v = float(s)
        return None if np.isnan(v) else v
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ đọc danh mục
def _tai_tu_github():
    token = os.environ.get("DANH_MUC_TOKEN", "").strip()
    repo = os.environ.get("DANH_MUC_REPO", "").strip()
    if not (token and repo):
        return None, "chưa đặt DANH_MUC_TOKEN / DANH_MUC_REPO"
    duong_dan = os.environ.get("DANH_MUC_PATH", "").strip() or "danh_muc.csv"
    p = {"ref": os.environ["DANH_MUC_NHANH"]} if os.environ.get("DANH_MUC_NHANH") else None
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/contents/{duong_dan}", params=p, timeout=20,
                         headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                                  "X-GitHub-Api-Version": "2022-11-28"})
    except requests.RequestException as e:
        return None, f"lỗi kết nối GitHub ({type(e).__name__})"
    if r.status_code != 200:                      # không in nội dung phản hồi (tránh lộ thông tin)
        goi_y = {401: "token sai/hết hạn", 403: "token thiếu quyền Contents: Read",
                 404: "sai tên repo/đường dẫn hoặc token không được cấp quyền repo này"}.get(r.status_code, "")
        return None, f"GitHub HTTP {r.status_code} {goi_y}".strip()
    return r.content.decode("utf-8-sig"), "repo danh-muc"


def doc_danh_muc(path_cuc_bo="danh_muc.csv"):
    """→ ({MÃ: vị thế}, mô tả nguồn). Chỉ giữ mã có so_cp > 0."""
    noi_dung, nguon = _tai_tu_github()
    if noi_dung is None and os.path.exists(path_cuc_bo):
        with open(path_cuc_bo, encoding="utf-8-sig") as f:
            noi_dung, nguon = f.read(), f"file {path_cuc_bo}"
    if noi_dung is None:
        return {}, nguon
    return phan_tich_csv(noi_dung), nguon


def phan_tich_csv(noi_dung):
    df = pd.read_csv(io.StringIO(noi_dung), dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]
    out = {}
    for _, r in df.iterrows():
        ma = str(r.get("ma", "")).strip().upper()
        so_cp = _so(r.get("so_cp"))
        if not ma or not so_cp or so_cp <= 0:
            continue
        out[ma] = {"ma": ma, "so_cp": so_cp, "gia_von": _so(r.get("gia_von")),
                   "cat_lo": _so(r.get("cat_lo_dat")) or _so(r.get("cat_lo_goc")),
                   "cat_lo_goc": _so(r.get("cat_lo_goc")),
                   "muc_tieu": _so(r.get("muc_tieu_dat")) or _so(r.get("gia_muc_tieu")),
                   "ngay_mua": str(r.get("ngay_mua", "")).strip()}
    return out


# ------------------------------------------------------------------ đánh giá bán
def danh_gia_ban(vt, kq, dn=None):
    """vt: vị thế; kq: kết quả phan_tich_ma của mã (giá, khung, ptcp). → dict mức, lý do, số liệu."""
    gia = kq.get("gia")
    if gia is None or gia != gia:
        return {"muc": "GIU", "ly_do": ["không có giá"], "gia": np.nan}
    gv, lo, mt = vt.get("gia_von"), vt.get("cat_lo"), vt.get("muc_tieu")
    lai = (gia / gv - 1) * 100 if gv else np.nan
    ly_do, muc = [], "GIU"
    if lo and gia <= lo:
        muc = "CAT_LO"
        ly_do.append(f"giá {gia:,.2f} ≤ cắt lỗ đã đặt {lo:,.2f}")
    elif mt and gia >= mt:
        muc = "CHOT_LOI"
        ly_do.append(f"giá {gia:,.2f} ≥ mục tiêu đã đặt {mt:,.2f}")
    else:
        xau = []
        tuan = next((k for k in kq.get("khung", []) if k.get("khung") == "Tuần"), None)
        if tuan is not None and not tuan.get("dat"):
            xau.append("tuần mất xu hướng (MACD tuần < Signal)")
        if dn is not None and len(dn) > 30:
            _, huong = supertrend(dn, *C.SUPERTREND)
            if huong.iloc[-1] < 0:
                xau.append("giá dưới SuperTrend ngày")
        kn = str((kq.get("ptcp") or {}).get("khuyen_nghi", ""))
        if "BÁN" in kn.upper():
            xau.append(f"ptcp khuyến nghị {kn}")
        if xau:
            muc = "CAN_NHAC_BAN"
            ly_do += xau
        else:
            r = (gv - (vt.get("cat_lo_goc") or lo)) if gv and (vt.get("cat_lo_goc") or lo) else None
            if r and r > 0 and lo is not None and lo < gv and gia >= gv + r:
                muc = "DOI_CAT_LO"
                ly_do.append(f"đã lãi ≥ 1R ({gia - gv:+,.2f}/CP) mà cắt lỗ {lo:,.2f} còn dưới giá vốn "
                             f"→ nâng cắt lỗ lên hoà vốn {gv:,.2f}")
    return {"muc": muc, "ly_do": ly_do, "gia": gia, "lai_lo_pct": lai, "cat_lo": lo, "muc_tieu": mt,
            "cach_cat_lo_pct": (lo / gia - 1) * 100 if lo else np.nan,
            "cach_muc_tieu_pct": (mt / gia - 1) * 100 if mt else np.nan}


# ------------------------------------------------------------------ chống báo trùng (không commit lên repo)
def doc_trang_thai_ban(path=FILE_TRANG_THAI_BAN):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ghi_trang_thai_ban(tt, path=FILE_TRANG_THAI_BAN):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tt, f, ensure_ascii=False)


def can_bao_ban(ma, muc, bay_gio, trang_thai):
    """Báo khi mức đổi sang một mức cần hành động; cùng mức thì nhắc lại 1 lần/ngày. GIU không báo."""
    hom_nay = pd.Timestamp(bay_gio).strftime("%Y-%m-%d")
    cu = trang_thai.get(ma, {})
    trang_thai[ma] = {"ngay": hom_nay, "muc": muc}
    if muc == "GIU":
        return False
    return not (cu.get("muc") == muc and cu.get("ngay") == hom_nay)


# ------------------------------------------------------------------ nội dung tin (chỉ gửi Telegram, không in log)
def _f(x, le=2):
    return "N/A" if x is None or x != x else f"{x:,.{le}f}"


def tin_ban(vt, kb, kq, bay_gio):
    g = kb["gia"]
    hanh_dong = {"CAT_LO": f"Bán toàn bộ {vt['so_cp']:,.0f} CP theo kỷ luật cắt lỗ",
                 "CHOT_LOI": f"Chốt lời (toàn bộ hoặc ½ = {vt['so_cp'] / 2:,.0f} CP), phần còn lại dời cắt lỗ lên",
                 "CAN_NHAC_BAN": "Xem xét giảm tỷ trọng / siết cắt lỗ – xu hướng đang yếu đi",
                 "DOI_CAT_LO": "Cập nhật cat_lo_dat trong danh_muc.csv (repo danh-muc)"}.get(kb["muc"], "")
    d = [f"{NHAN[kb['muc']]} – {vt['ma']} @ {_f(g)} ({pd.Timestamp(bay_gio):%H:%M %d/%m})",
         f"Đang giữ {vt['so_cp']:,.0f} CP | giá vốn {_f(vt.get('gia_von'))} | lãi/lỗ {_f(kb['lai_lo_pct'], 1)}%",
         f"Cắt lỗ đã đặt {_f(kb['cat_lo'])} ({_f(kb['cach_cat_lo_pct'], 1)}%) | "
         f"Mục tiêu đã đặt {_f(kb['muc_tieu'])} ({_f(kb['cach_muc_tieu_pct'], 1)}%)",
         "Lý do: " + "; ".join(kb["ly_do"])]
    if hanh_dong:
        d.append(f"➜ {hanh_dong}")
    pt = kq.get("ptcp") or {}
    if pt:
        d.append(f"ptcp ({pt.get('ngay_du_lieu', '')}): {pt.get('khuyen_nghi', '')}")
    d.append("(Tham khảo – tự kiểm tra trước khi đặt lệnh; lưu ý T+2 với CP mới mua)")
    return "\n".join(d)


def dong_tong_ket(vt, kb):
    return (f"■ {vt['ma']} {_f(kb['gia'])} – {NHAN[kb['muc']]} | {vt['so_cp']:,.0f} CP, vốn {_f(vt.get('gia_von'))}, "
            f"lãi/lỗ {_f(kb['lai_lo_pct'], 1)}% | CL {_f(kb['cat_lo'])} ({_f(kb['cach_cat_lo_pct'], 1)}%) | "
            f"MT {_f(kb['muc_tieu'])} ({_f(kb['cach_muc_tieu_pct'], 1)}%)"
            + (f"\n  {'; '.join(kb['ly_do'])}" if kb["ly_do"] else ""))
