# -*- coding: utf-8 -*-
"""
VỊ THẾ ĐANG GIỮ & CẢNH BÁO BÁN – theo HỆ THOÁT MỚI (ptcp/he_thoat.py, gốc T2-3R-ma10).

Nguồn vị thế: đọc danh_muc.csv từ repo RIÊNG TƯ `danh-muc` qua GitHub API bằng token CHỈ ĐỌC.
  Biến môi trường (GitHub Actions): DANH_MUC_TOKEN (secret), DANH_MUC_REPO (variable, VD "ten-ban/danh-muc"),
  DANH_MUC_PATH (tuỳ chọn, mặc định "danh_muc.csv"), DANH_MUC_NHANH (tuỳ chọn, mặc định nhánh mặc định của repo).
  Chạy trên máy: đặt file danh_muc.csv cạnh chay.py (đã có trong .gitignore – KHÔNG đẩy lên repo công khai).

Repo bot là CÔNG KHAI → log Actions ai cũng xem được: KHÔNG in số CP, giá vốn, cắt lỗ ra log;
trạng thái chống báo trùng của lệnh bán lưu trong actions/cache (cache_ptcp/), không commit lên repo.

HỆ THOÁT (tính lại mỗi lần chạy từ ngày mua – chỉ dùng phiên ĐÃ ĐÓNG CỬA; cắt lỗ chỉ dời LÊN):
  lãi < 1R  cắt lỗ ban đầu (cat_lo_goc; thiếu thì cắt lỗ chuẩn theo ATR)          1R = giá vốn − cắt lỗ ban đầu
  lãi ≥ 1R  cắt lỗ động = đóng cửa cao nhất − 3×ATR, không dưới hoà vốn (+ phí)
  lãi ≥ 3R  KHUNG TUẦN: bán khi đóng cửa tuần < MA10 tuần; sàn khoá lãi 2R
  63 phiên mà lãi < 1R → lệnh không chạy. KHÔNG chốt lời ở mục tiêu cố định.
  Cắt lỗ hiệu lực = mức CAO HƠN giữa hệ thống và cat_lo_dat đã đặt trong danh mục.

Mức cảnh báo (ưu tiên từ trên xuống):
  CAT_LO     giá ≤ cắt lỗ hiệu lực
  BAN_TUAN   đang ở khung tuần và tuần đã đóng có giá đóng cửa < MA10 tuần → bán đầu phiên tới
  HET_HAN    giữ ≥ 63 phiên mà lãi < 1R (lệnh không chạy) → bán
  DOI_CAT_LO cắt lỗ hệ thống cao hơn cat_lo_dat ≥ DOI_CAT_LO_TOI_THIEU_PCT % → cập nhật danh mục (tầng mới)
  GIU        không có gì
  (DUNG_HE_THOAT = False hoặc ptcp cũ không có theo_doi_vi_the → cách cũ: CAT_LO / CHOT_LOI / CAN_NHAC_BAN /
   DOI_CAT_LO theo mức đặt tay, MACD tuần, SuperTrend, ptcp.)
"""
import io
import json
import os

import numpy as np
import pandas as pd
import requests

from . import cau_hinh as C
from .chi_bao import supertrend

MUC = ["CAT_LO", "BAN_TUAN", "HET_HAN", "CHOT_LOI", "CAN_NHAC_BAN", "GAN_CAT_LO", "DOI_CAT_LO", "GIU"]
NHAN = {"CAT_LO": "🔴 CẮT LỖ", "BAN_TUAN": "🔴 BÁN – GÃY XU HƯỚNG TUẦN", "HET_HAN": "🟠 BÁN – LỆNH KHÔNG CHẠY",
        "CHOT_LOI": "🟢 CHỐT LỜI", "CAN_NHAC_BAN": "🟠 CÂN NHẮC BÁN", "GAN_CAT_LO": "🟠 SÁT CẮT LỖ",
        "DOI_CAT_LO": "🟡 DỜI CẮT LỖ", "GIU": "⚪ GIỮ"}
TEN_TANG = {0: "tầng 0 (< 1R)", 1: "tầng 1 (≥ 1R – cắt lỗ động)", 2: "tầng tuần (≥ 3R – MA10 tuần)"}
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
                   "ngay_mua": str(r.get("ngay_mua", "")).strip(),
                   "ngay_mua_them": str(r.get("ngay_mua_them", "")).strip(),          # tuỳ chọn
                   "so_lan_mua_them": _so(r.get("so_lan_mua_them")) or 0}
    return out


def _ngay(s):
    """'25/08/2026' | '2026-08-25' → Timestamp | None."""
    s = str(s or "").strip()
    if not s:
        return None
    try:
        return pd.Timestamp(s) if s[:4].isdigit() else pd.to_datetime(s, dayfirst=True)
    except (ValueError, TypeError):
        return None


def _phien_da_dong(dn, bay_gio):
    """Bỏ nến ngày ĐANG CHẠY (trong phiên hôm nay) – hệ thoát chỉ tính trên phiên đã đóng cửa."""
    if dn is None or not len(dn) or bay_gio is None:
        return dn
    t = pd.Timestamp(bay_gio)
    het_phien = t.normalize() + pd.Timedelta(C.PHIEN[-1][1] + ":00")
    if dn.index[-1].normalize() == t.normalize() and t < het_phien:
        return dn.iloc[:-1]
    return dn


def _he_thoat(vt, dn, bay_gio):
    """Trạng thái hệ thoát của vị thế (dict) hoặc None nếu không tính được (thiếu giá vốn / dữ liệu / ptcp cũ)."""
    if not C.DUNG_HE_THOAT or dn is None or not vt.get("gia_von"):
        return None
    try:
        from ptcp.chi_bao import tinh_chi_bao
        from ptcp.he_thoat import theo_doi_vi_the
    except ImportError:
        return None
    d = _phien_da_dong(dn, bay_gio)
    if d is None or len(d) < 60:
        return None
    try:
        return theo_doi_vi_the(tinh_chi_bao(d[["open", "high", "low", "close", "volume"]]), vt["gia_von"],
                               _ngay(vt.get("ngay_mua")), vt.get("cat_lo_goc"), C.NGUONG_KHUNG_TUAN_R)
    except Exception as e:                                       # lỗi tính toán không được làm hỏng cảnh báo
        print(f"  ⚠ hệ thoát: {type(e).__name__}")
        return None


# ------------------------------------------------------------------ đánh giá bán
def danh_gia_ban(vt, kq, dn=None, bay_gio=None):
    """vt: vị thế; kq: kết quả phan_tich_ma của mã (giá, khung, ptcp); dn: giá ngày. → dict mức, lý do, số liệu."""
    gia = kq.get("gia")
    if gia is None or gia != gia:
        return {"muc": "GIU", "ly_do": ["không có giá"], "gia": np.nan, "lai_lo_pct": np.nan, "cat_lo": None,
                "muc_tieu": None, "cach_cat_lo_pct": np.nan, "cach_muc_tieu_pct": np.nan, "ghi_chu": []}
    ht = _he_thoat(vt, dn, bay_gio)
    if ht is None:
        return _danh_gia_ban_cu(vt, kq, dn)
    gv, lo_dat = vt["gia_von"], vt.get("cat_lo")
    cl_he = ht["cat_lo"]
    lo = max(cl_he, lo_dat) if lo_dat else cl_he
    theo = ht["nguon_cat_lo"] if not lo_dat or cl_he >= lo_dat else "cắt lỗ đã đặt"
    lai = (gia / gv - 1) * 100
    ly_do, ghi_chu, muc = [], [], "GIU"
    if gia <= lo:
        muc = "CAT_LO"
        ly_do.append(f"giá {gia:,.2f} ≤ cắt lỗ {lo:,.2f} ({theo})")
    elif ht["ban_tuan"]:
        muc = "BAN_TUAN"
        ly_do.append(f"đóng cửa tuần {ht['ngay_ban_tuan']:%d/%m} < MA10 tuần ({ht['ma10_tuan']:,.2f}) khi đã lãi "
                     f"≥ {C.NGUONG_KHUNG_TUAN_R:g}R → xu hướng tuần gãy")
    elif ht["het_han"]:
        muc = "HET_HAN"
        ly_do.append(f"giữ {ht['so_phien']} phiên mà lãi chưa đạt 1R → lệnh không chạy")
    elif 0 < (gia / lo - 1) * 100 <= getattr(C, "GAN_CAT_LO_PCT", 0):
        muc = "GAN_CAT_LO"
        ly_do.append(f"giá {gia:,.2f} chỉ còn cách cắt lỗ {lo:,.2f} {(gia / lo - 1) * 100:.1f}% → chạm là bán")
    elif not lo_dat or cl_he > lo_dat * (1 + C.DOI_CAT_LO_TOI_THIEU_PCT / 100):
        muc = "DOI_CAT_LO"
        ly_do.append(f"{TEN_TANG[ht['tang']]}: nâng cắt lỗ lên {cl_he:,.2f} ({ht['nguon_cat_lo']})"
                     + (f" – đang đặt {lo_dat:,.2f}" if lo_dat else " – chưa đặt cắt lỗ"))
    if not ht["ban_duoc"] and _ngay(vt.get("ngay_mua")) is not None:      # không có ngày mua → không biết T+2
        ghi_chu.append("CP chưa về tài khoản (T+2) – chưa bán được")
    if ht["moc_tiep_R"] and ht["gia_moc_tiep"]:
        ghi_chu.append(f"mốc kế tiếp {ht['moc_tiep_R']:g}R = {ht['gia_moc_tiep']:,.2f} "
                       + ("(dời cắt lỗ lên hoà vốn)" if ht["tang"] == 0 else "(chuyển sang bán theo MA10 tuần)"))
    elif ht["tang"] >= 2 and ht["ma10_tuan"]:
        ghi_chu.append(f"khung tuần: giữ tới khi đóng cửa tuần < MA10 tuần ({ht['ma10_tuan']:,.2f})")
    nguong = None
    if ht["tang"] >= 2:
        try:
            from ptcp.theo_chien_luoc import nguong_ma10_tuan
            nguong = nguong_ma10_tuan(_phien_da_dong(dn, bay_gio))[0]
        except Exception:
            nguong = None
    return {"muc": muc, "ly_do": ly_do, "ghi_chu": ghi_chu, "gia": gia, "lai_lo_pct": lai, "cat_lo": lo,
            "ma10_tuan": ht.get("ma10_tuan"), "nguong_ma10": nguong, "so_phien": ht.get("so_phien"),
            "cat_lo_he_thong": cl_he, "cat_lo_dat": lo_dat, "muc_tieu": ht["gia_moc_tiep"], "tang": ht["tang"],
            "lai_R": (gia - gv) / ht["R"], "R": ht["R"], "he_thoat": True,
            "cach_cat_lo_pct": (lo / gia - 1) * 100,
            "cach_muc_tieu_pct": (ht["gia_moc_tiep"] / gia - 1) * 100 if ht["gia_moc_tiep"] else np.nan}


def _danh_gia_ban_cu(vt, kq, dn=None):
    """Cách cũ (DUNG_HE_THOAT = False / thiếu giá vốn / ptcp cũ): mức đặt tay + MACD tuần / SuperTrend / ptcp."""
    gia = kq.get("gia")
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
    return {"muc": muc, "ly_do": ly_do, "ghi_chu": [], "gia": gia, "lai_lo_pct": lai, "cat_lo": lo, "muc_tieu": mt,
            "he_thoat": False, "cach_cat_lo_pct": (lo / gia - 1) * 100 if lo else np.nan,
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


def _dong_he_thoat(kb):
    if not kb.get("he_thoat"):
        return [f"Cắt lỗ đã đặt {_f(kb['cat_lo'])} ({_f(kb['cach_cat_lo_pct'], 1)}%) | "
                f"Mục tiêu đã đặt {_f(kb['muc_tieu'])} ({_f(kb['cach_muc_tieu_pct'], 1)}%)"]
    d = [f"Hệ thoát: {TEN_TANG[kb['tang']]} | lãi {_f(kb['lai_R'], 1)}R (1R = {_f(kb['R'])}) | cắt lỗ hiệu lực "
         f"{_f(kb['cat_lo'])} ({_f(kb['cach_cat_lo_pct'], 1)}%)"]
    if kb.get("cat_lo_dat") is not None and abs(kb["cat_lo_he_thong"] - kb["cat_lo_dat"]) > 1e-9:
        d.append(f"  hệ thống {_f(kb['cat_lo_he_thong'])} · đã đặt {_f(kb['cat_lo_dat'])}")
    return d


def tin_ban(vt, kb, kq, bay_gio):
    g = kb["gia"]
    hanh_dong = {"CAT_LO": f"Bán toàn bộ {vt['so_cp']:,.0f} CP theo kỷ luật cắt lỗ",
                 "BAN_TUAN": f"Bán {vt['so_cp']:,.0f} CP đầu phiên tới – hệ thoát khung tuần (không chờ mục tiêu)",
                 "HET_HAN": f"Bán {vt['so_cp']:,.0f} CP – lệnh không chạy, giải phóng vốn cho tín hiệu mới",
                 "CHOT_LOI": f"Chốt lời (toàn bộ hoặc ½ = {vt['so_cp'] / 2:,.0f} CP), phần còn lại dời cắt lỗ lên",
                 "CAN_NHAC_BAN": "Xem xét giảm tỷ trọng / siết cắt lỗ – xu hướng đang yếu đi",
                 "GAN_CAT_LO": f"Chuẩn bị lệnh bán: giá chạm {_f(kb['cat_lo'])} thì bán toàn bộ (hệ thoát)",
                 "DOI_CAT_LO": f"Đặt lệnh cắt lỗ mới {_f(kb.get('cat_lo_he_thong'))} & cập nhật cat_lo_dat trong "
                               f"danh_muc.csv (repo danh-muc)"}.get(kb["muc"], "")
    d = [f"{NHAN[kb['muc']]} – {vt['ma']} @ {_f(g)} ({pd.Timestamp(bay_gio):%H:%M %d/%m})",
         f"Đang giữ {vt['so_cp']:,.0f} CP | giá vốn {_f(vt.get('gia_von'))} | lãi/lỗ {_f(kb['lai_lo_pct'], 1)}%",
         *_dong_he_thoat(kb),
         "Lý do: " + "; ".join(kb["ly_do"])]
    d += [f"  • {x}" for x in kb.get("ghi_chu", [])]
    if hanh_dong:
        d.append(f"➜ {hanh_dong}")
    pt = kq.get("ptcp") or {}
    if pt:
        d.append(f"ptcp ({pt.get('ngay_du_lieu', '')}): {pt.get('khuyen_nghi', '')} (tham khảo – hệ thoát quyết định)")
    d.append("(Tham khảo – tự kiểm tra trước khi đặt lệnh; lưu ý T+2 với CP mới mua)")
    return "\n".join(d)


def dong_tong_ket(vt, kb):
    if not kb.get("he_thoat"):
        return (f"■ {vt['ma']} {_f(kb['gia'])} – {NHAN[kb['muc']]} | {vt['so_cp']:,.0f} CP, vốn {_f(vt.get('gia_von'))}, "
                f"lãi/lỗ {_f(kb['lai_lo_pct'], 1)}% | CL {_f(kb['cat_lo'])} ({_f(kb['cach_cat_lo_pct'], 1)}%) | "
                f"MT {_f(kb['muc_tieu'])} ({_f(kb['cach_muc_tieu_pct'], 1)}%)"
                + (f"\n  {'; '.join(kb['ly_do'])}" if kb["ly_do"] else ""))
    moc = (f" | mốc {_f(kb['muc_tieu'])} ({_f(kb['cach_muc_tieu_pct'], 1)}%)" if kb.get("muc_tieu") else "")
    return (f"■ {vt['ma']} {_f(kb['gia'])} – {NHAN[kb['muc']]} | {vt['so_cp']:,.0f} CP, vốn {_f(vt.get('gia_von'))}, "
            f"lãi/lỗ {_f(kb['lai_lo_pct'], 1)}% ({_f(kb['lai_R'], 1)}R) | {TEN_TANG[kb['tang']]} | CL "
            f"{_f(kb['cat_lo'])} ({_f(kb['cach_cat_lo_pct'], 1)}%){moc}"
            + (f"\n  {'; '.join(kb['ly_do'] + kb.get('ghi_chu', []))}" if kb["ly_do"] or kb.get("ghi_chu") else ""))
