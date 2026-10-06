# -*- coding: utf-8 -*-
"""
NGUỒN vnstock (bản Cộng đồng, vnstock ≥ 4.0.9) – giá, chỉ số cơ bản, BCTC quý/năm, danh sách HOSE.

Cài (theo hướng dẫn chính thức vnstocks.com – gói KHÔNG có trên PyPI, phải thêm --extra-index-url):
    pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.9" "vnai>=2.6.2"
Trên Google Colab ptcp tự cài lệnh này (dam_bao_cai). Bản Cộng đồng KHÔNG cần khoá API; bộ lọc không
bao giờ đọc / in / hỏi khoá. Lưu ý: gói vnai gửi số lượt dùng & mã thiết bị về vnstocks.com (giới hạn tần suất).

Tên cột của vnstock khác nhau giữa nguồn (KBS/VCI) và phiên bản → dò theo TỪ KHOÁ, mọi lỗi đều bỏ qua êm
(nguồn khác bù). Thứ tự nguồn bên trong vnstock: NGUON_VNSTOCK.
"""
import importlib.util
import os
import re
import subprocess
import sys
import threading
import time
from collections import deque

import pandas as pd



def doc_so(x):
    """Đọc số kiểu Việt Nam/quốc tế ('78,700' / '15,5' / '1.234,5'); không đọc được → None."""
    try:
        if x is None:
            return None
        if not isinstance(x, str):
            v = float(x)
            return None if v != v else v
        s = x.strip().replace(" ", "").replace("%", "")
        if not s or s.lower() in ("nan", "none", "-", "--"):
            return None
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
        return float(s)
    except (TypeError, ValueError):
        return None

NGUON_VNSTOCK = ("KBS", "VCI")
LENH_CAI = [sys.executable, "-m", "pip", "install", "-q", "-U", "--extra-index-url",
            "https://vnstocks.com/api/simple", "vnstock>=4.0.9", "vnai>=2.6.2"]
_TRANG_THAI = {"da_thu_cai": False, "nghi_den": 0.0, "da_bao": False}
KHOA = ("doanh_thu", "ln_gop", "lnst", "cfo", "cr", "icr", "de", "roe", "von_gop", "vay_no")

# ---------------------------------------------------------------- HẠN MỨC LƯỢT GỌI
# Bản Cộng đồng có khoá: 60 lượt/phút; chưa đăng ký: thấp hơn. Bộ lọc tự giữ dưới hạn mức; hết lượt thì
# KHÔNG chờ mà báo lỗi để chuyển sang nguồn khác (VNDirect/TCBS/Yahoo…). vnstock gặp giới hạn sẽ gọi
# SystemExit (dừng cả chương trình) → bắt lại, tạm nghỉ vnstock 65 giây rồi dùng lại.
LUOT_MOI_PHUT = 55 if os.environ.get("VNSTOCK_API_KEY") else 18
_MOC_GOI = deque()
_KHOA_LUOT = threading.Lock()


class HetLuot(ValueError):
    pass


CHO_KHI_HET_LUOT = False      # True (--cho_vnstock): hết lượt thì CHỜ cho đủ điều kiện vnstock thay vì đổi nguồn


def _cho(giay, ly_do):
    if time.time() - _TRANG_THAI.get("lan_bao_cho", 0) > 30:
        _TRANG_THAI["lan_bao_cho"] = time.time()
        print(f"  ⏳ {ly_do} – chờ {giay:.0f} giây cho đúng hạn mức vnstock ...")
    time.sleep(max(giay, 0))


def _goi(ham):
    """
    Gọi 1 hàm vnstock trong hạn mức. Hết lượt:
      • mặc định → báo lỗi HetLuot để bộ lọc chuyển ngay sang nguồn khác;
      • CHO_KHI_HET_LUOT → chờ tới khi đủ lượt rồi gọi tiếp (chậm hơn nhưng dữ liệu lấy hết từ vnstock).
    vnstock báo hết lượt bằng SystemExit → bắt lại (không để dừng cả chương trình).
    """
    with _KHOA_LUOT:                                 # giữ khoá khi chờ → các luồng vnstock khác xếp hàng
        bay_gio = time.time()
        if bay_gio < _TRANG_THAI["nghi_den"]:
            if not CHO_KHI_HET_LUOT:
                raise HetLuot("vnstock đang tạm nghỉ (hết hạn mức) → dùng nguồn khác")
            _cho(_TRANG_THAI["nghi_den"] - bay_gio, "vnstock báo hết hạn mức")
            bay_gio = time.time()
        while _MOC_GOI and bay_gio - _MOC_GOI[0] > 60:
            _MOC_GOI.popleft()
        if len(_MOC_GOI) >= LUOT_MOI_PHUT:
            if not CHO_KHI_HET_LUOT:
                raise HetLuot(f"vnstock đã dùng {LUOT_MOI_PHUT} lượt/phút → dùng nguồn khác")
            _cho(60 - (bay_gio - _MOC_GOI[0]) + 0.5, f"đã dùng {LUOT_MOI_PHUT} lượt/phút")
            bay_gio = time.time()
            while _MOC_GOI and bay_gio - _MOC_GOI[0] > 60:
                _MOC_GOI.popleft()
        _MOC_GOI.append(bay_gio)
    for lan in range(2 if CHO_KHI_HET_LUOT else 1):
        try:
            return ham()
        except SystemExit as e:                     # vnai báo hết hạn mức bằng SystemExit
            if CHO_KHI_HET_LUOT and lan == 0:
                with _KHOA_LUOT:
                    _cho(65, "vnstock báo hết hạn mức")
                    _MOC_GOI.clear()
                    _MOC_GOI.append(time.time())
                continue
            with _KHOA_LUOT:
                _TRANG_THAI["nghi_den"] = time.time() + 65
                if not _TRANG_THAI["da_bao"]:
                    _TRANG_THAI["da_bao"] = True
                    print("  ⚠ vnstock hết hạn mức lượt gọi → tạm nghỉ 65 giây, các mã khác dùng nguồn còn lại")
            raise HetLuot(f"vnstock hết hạn mức ({str(e)[:40]})")


def co_vnstock():
    return importlib.util.find_spec("vnstock") is not None


def dam_bao_cai(chi_tren_colab=True):
    """Cài vnstock nếu thiếu (mặc định chỉ trên Colab – máy cá nhân nên tự cài vào môi trường ảo)."""
    if co_vnstock() or _TRANG_THAI["da_thu_cai"]:
        return co_vnstock()
    _TRANG_THAI["da_thu_cai"] = True
    if chi_tren_colab and "google.colab" not in sys.modules:
        return False
    print("  Đang cài vnstock (bản Cộng đồng) từ vnstocks.com ...")
    try:
        subprocess.run(LENH_CAI, check=False, timeout=300, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        importlib.invalidate_caches()
    except Exception:
        pass
    print("  → vnstock " + ("đã sẵn sàng" if co_vnstock() else "cài KHÔNG được – bỏ qua nguồn này"))
    return co_vnstock()


def _lop(ten):
    if not co_vnstock():
        raise ValueError("chưa cài vnstock")
    import vnstock
    return getattr(vnstock, ten)


# ---------------------------------------------------------------- chuẩn hoá bảng
def _ten(c):
    return (" ".join(str(x) for x in c) if isinstance(c, tuple) else str(c)).strip().lower()


_KY_RE = re.compile(r"((?:19|20)\d{2})(?:\D*q?([1-4]))?", re.I)
_KY_RE_QUY_TRUOC = re.compile(r"q([1-4])\D*((?:19|20)\d{2})", re.I)


def chuan_hoa_bang(df):
    """
    Bảng tài chính vnstock (kỳ theo DÒNG hoặc theo CỘT, cột 1 hay 2 tầng) → DataFrame:
    mỗi dòng 1 kỳ, MỚI NHẤT TRƯỚC, tên cột viết thường; thêm cột '_ky' = (năm, quý).
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = df.copy()
    ky_cot = [c for c in df.columns
              if re.fullmatch(r"\s*(q[1-4]\s*[-/ ]?\s*)?(19|20)\d{2}(\s*[-/ ]?\s*q?[1-4])?\s*", str(c), re.I)]
    if len(ky_cot) >= 2:                                   # kỳ theo CỘT → xoay lại
        nhan = next((c for c in df.columns if c not in ky_cot and not pd.api.types.is_numeric_dtype(df[c])), None)
        if nhan is None:
            return pd.DataFrame()
        df = df.set_index(nhan)[ky_cot].T
        df.index = [str(i) for i in df.index]
        df["_ky"] = [_ky(i) for i in df.index]
    else:
        df.columns = [_ten(c) for c in df.columns]
        nam = next((c for c in df.columns if c.endswith("yearreport") or c in ("year", "năm", "nam")), None)
        quy = next((c for c in df.columns if c.endswith("lengthreport") or c in ("quarter", "quý", "quy")), None)
        kyc = next((c for c in df.columns if c in ("period", "kỳ", "ky", "report_period", "time")), None)
        if nam is not None:
            df["_ky"] = [(int(doc_so(y) or 0), int(doc_so(q) or 0) if quy else 0)
                         for y, q in zip(df[nam], df[quy] if quy else [0] * len(df))]
        elif kyc is not None:
            df["_ky"] = [_ky(str(x)) for x in df[kyc]]
        else:
            df["_ky"] = [(0, 0)] * len(df)
    df.columns = [c if c == "_ky" else _ten(c) for c in df.columns]
    return df.sort_values("_ky", ascending=False, key=lambda s: s.map(lambda x: x[0] * 10 + x[1])).reset_index(drop=True)


def _ky(s):
    m = _KY_RE_QUY_TRUOC.search(str(s))
    if m:
        return int(m.group(2)), int(m.group(1))
    m = _KY_RE.search(str(s))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


def tim_cot(df, *tu_khoa, tru=()):
    """Cột đầu tiên có tên chứa một trong các từ khoá (không chứa từ trong 'tru')."""
    for k in tu_khoa:
        for c in df.columns:
            if c != "_ky" and k in c and not any(x in c for x in tru):
                return c
    return None


def _gia_tri(df, cot, i=0):
    if cot is None or len(df) <= i:
        return None
    return doc_so(df[cot].iloc[i])


# ---------------------------------------------------------------- GIÁ
def gia(ma, start, end, chi_so=False):
    loi = []
    Quote = _lop("Quote")
    for src in NGUON_VNSTOCK:
        for khung in ("1D", "d"):
            try:
                df = _goi(lambda: Quote(symbol=ma, source=src).history(start=start, end=end, interval=khung))
                if df is not None and len(df):
                    df = df.rename(columns={"date": "time", "tradingDate": "time", "trading_date": "time"})
                    df["time"] = pd.to_datetime(df["time"]).dt.normalize()
                    return df[["time", "open", "high", "low", "close", "volume"]]
            except HetLuot:
                raise
            except Exception as e:
                loi.append(f"{src}/{khung}: {str(e)[:30]}")
    raise ValueError("; ".join(loi[:2]) or "không có dữ liệu")


# ---------------------------------------------------------------- CHỈ SỐ & BCTC QUÝ
_TU_TY_SO = [
    ("pe", ("p/e", "pe_ratio", "price_to_earning"), ("p/e/g", "forward")),
    ("pb", ("p/b", "pb_ratio", "price_to_book"), ()),
    ("roe", ("roe",), ()), ("roa", ("roa",), ()),
    ("eps_ttm", ("eps",), ("growth", "tăng", "change")),
    ("bvps", ("bvps", "book value per share"), ()),
    ("tt_hien_thoi", ("current ratio", "current_ratio", "thanh toán hiện hành", "thanh toán hiện thời"), ()),
    ("tt_nhanh", ("quick ratio", "quick_ratio", "thanh toán nhanh"), ()),
]
_TU_DT = ("net revenue", "net sales", "doanh thu thuần", "revenue", "doanh thu")
_TU_LN_ME = ("attributable to parent", "parent company", "công ty mẹ", "cổ đông của công ty mẹ", "net_profit_parent")
_TU_LN = ("net profit after tax", "profit after tax", "lợi nhuận sau thuế", "net income", "net profit")
_TU_LG = ("gross profit", "lợi nhuận gộp", "lãi gộp")


def _ty_le(v):
    return v * 100 if v is not None and abs(v) <= 2 else v


def _don_vi_ty(tong, so_cp, eps_tham_chieu):
    """Đưa tổng LNST về TỶ đồng: chọn hệ số (đồng / triệu / tỷ) cho EPS gần EPS tham chiếu nhất."""
    if tong is None:
        return None
    if so_cp and eps_tham_chieu:
        ung_vien = [(abs(tong * h * 1e9 / so_cp - eps_tham_chieu), h) for h in (1e-9, 1e-3, 1.0)]
        return tong * min(ung_vien)[1]
    return tong / 1e9 if abs(tong) > 1e8 else (tong / 1e3 if abs(tong) > 1e5 else tong)


def co_ban(ma):
    """→ dict theo khoá của nguon/co_ban.py (pe, pb, roe, roa, eps_ttm, bvps, so_cp, ln_4q_ty, dt_4q_ty …)."""
    Finance = _lop("Finance")
    kq, loi = {}, []
    for src in NGUON_VNSTOCK:
        try:
            f = _goi(lambda: Finance(symbol=ma, source=src))
            ts = chuan_hoa_bang(_goi(lambda: f.ratio(period="quarter")))
            for khoa, tu, tru in _TU_TY_SO:
                v = _gia_tri(ts, tim_cot(ts, *tu, tru=tru))
                if v is not None and khoa not in kq:
                    kq[khoa] = _ty_le(v) if khoa in ("roe", "roa") else v
            cp = _gia_tri(ts, tim_cot(ts, "outstanding share", "số cp lưu hành", "shares outstanding"))
            if cp and "so_cp" not in kq:
                kq["so_cp"] = cp * 1e6 if cp < 1e5 else cp
            kd = chuan_hoa_bang(_goi(lambda: f.income_statement(period="quarter")))
            if len(kd) >= 4 and "ln_4q_ty" not in kq:
                ky = [k for k in kd["_ky"][:4]]
                lien_tuc = all((a[0] * 4 + a[1]) - (b[0] * 4 + b[1]) == 1 for a, b in zip(ky, ky[1:]))
                c_ln = tim_cot(kd, *_TU_LN_ME) or tim_cot(kd, *_TU_LN, tru=("before", "trước", "minority"))
                c_dt = tim_cot(kd, *_TU_DT, tru=("deduction", "giảm trừ", "growth", "tăng"))
                if lien_tuc and c_ln:
                    ln4 = [doc_so(x) for x in kd[c_ln][:4]]
                    if all(v is not None for v in ln4):
                        kq["ln_4q_ty"] = _don_vi_ty(sum(ln4), kq.get("so_cp"), kq.get("eps_ttm"))
                        kq["ky_lnst"] = "+".join(f"Q{q}/{y}" for y, q in ky)
                        he_so = kq["ln_4q_ty"] / sum(ln4) if sum(ln4) else None
                        if c_dt and he_so:
                            dt4 = [doc_so(x) for x in kd[c_dt][:4]]
                            if all(v is not None for v in dt4):
                                kq["dt_4q_ty"] = sum(dt4) * he_so
            if kq:
                break
        except HetLuot as e:
            if kq:
                break
            raise e
        except Exception as e:
            loi.append(f"{src}: {str(e)[:40]}")
    if not kq and loi:
        raise ValueError("; ".join(loi))
    return kq


# ---------------------------------------------------------------- BCTC NĂM (10 tiêu chí tài chính)
def bctc_nam(ma):
    Finance = _lop("Finance")
    loi = []
    for src in NGUON_VNSTOCK:
        try:
            f = _goi(lambda: Finance(symbol=ma, source=src))
            kd = chuan_hoa_bang(_goi(lambda: f.income_statement(period="year")))
            if len(kd) < 3:
                raise ValueError("không đủ 3 năm")
            nam = [k[0] for k in kd["_ky"][:5]]
            cd = chuan_hoa_bang(_goi(lambda: f.balance_sheet(period="year")))
            lc = chuan_hoa_bang(_goi(lambda: f.cash_flow(period="year")))
            ts = chuan_hoa_bang(_goi(lambda: f.ratio(period="year")))
            kq = {"nam": nam, **{k: [None] * len(nam) for k in KHOA}}

            def theo_nam(bang, cot, chuyen=lambda v: v):
                if bang is None or not len(bang) or cot is None:
                    return [None] * len(nam)
                m = {k[0]: doc_so(v) for k, v in zip(bang["_ky"], bang[cot])}
                return [chuyen(m.get(y)) if m.get(y) is not None else None for y in nam]

            kq["doanh_thu"] = theo_nam(kd, tim_cot(kd, *_TU_DT, tru=("deduction", "giảm trừ", "growth")))
            kq["ln_gop"] = theo_nam(kd, tim_cot(kd, *_TU_LG))
            kq["lnst"] = theo_nam(kd, tim_cot(kd, *_TU_LN_ME) or tim_cot(kd, *_TU_LN, tru=("before", "trước")))
            kq["cfo"] = theo_nam(lc, tim_cot(lc, "operating activities", "hoạt động kinh doanh", "operating cash"))
            kq["von_gop"] = theo_nam(cd, tim_cot(cd, "paid-in capital", "charter capital", "owner's capital",
                                                 "vốn góp", "vốn điều lệ", "common stock"))
            vay = [tim_cot(cd, "short-term borrowing", "vay ngắn hạn", "vay và nợ thuê tài chính ngắn hạn"),
                   tim_cot(cd, "long-term borrowing", "vay dài hạn", "vay và nợ thuê tài chính dài hạn")]
            v1, v2 = theo_nam(cd, vay[0]), theo_nam(cd, vay[1])
            kq["vay_no"] = [(a or 0) + (b or 0) if (a is not None or b is not None) else None for a, b in zip(v1, v2)]
            kq["cr"] = theo_nam(ts, tim_cot(ts, "current ratio", "current_ratio", "thanh toán hiện hành",
                                            "thanh toán hiện thời"))
            kq["icr"] = theo_nam(ts, tim_cot(ts, "interest coverage", "ebit/interest", "khả năng chi trả lãi vay",
                                             "ebit / lãi vay"))
            kq["de"] = theo_nam(ts, tim_cot(ts, "debt/equity", "liabilities/equity", "nợ/vcsh", "nợ phải trả/vốn chủ",
                                            "debt_to_equity"))
            kq["roe"] = theo_nam(ts, tim_cot(ts, "roe"), _ty_le)
            if any(v is not None for v in kq["lnst"]):
                return kq
            raise ValueError("không tìm thấy cột lợi nhuận")
        except HetLuot:
            raise
        except Exception as e:
            loi.append(f"{src}: {str(e)[:40]}")
    raise ValueError("; ".join(loi))


# ---------------------------------------------------------------- DANH SÁCH HOSE
def ds_hose():
    Listing = _lop("Listing")
    df = _goi(lambda: Listing().symbols_by_exchange())
    df.columns = [_ten(c) for c in df.columns]
    san = tim_cot(df, "exchange", "board", "comgroupcode", "sàn")
    ma = tim_cot(df, "symbol", "ticker", "mã")
    loai = tim_cot(df, "type", "loại")
    df = df[df[san].astype(str).str.upper().isin(["HSX", "HOSE"])] if san else df
    if loai:
        df = df[df[loai].astype(str).str.upper().str.contains("STOCK")]
    return df[ma].astype(str).tolist() if ma else []


def nhan_dien_cot(ma="GMD"):
    """Chẩn đoán: in tên cột thật của vnstock trên máy này (gửi kết quả nếu số liệu vnstock bị trống)."""
    Finance = _lop("Finance")
    for src in NGUON_VNSTOCK:
        print(f"===== nguồn {src}")
        for ten in ("ratio", "income_statement", "balance_sheet", "cash_flow"):
            try:
                df = getattr(Finance(symbol=ma, source=src), ten)(period="quarter" if ten != "balance_sheet" else "year")
                print(f"  {ten}: {df.shape} | {[_ten(c) for c in df.columns][:25]}")
            except Exception as e:
                print(f"  {ten}: lỗi {str(e)[:80]}")



def lnst_quy(ma, so_cp=None, eps_tham_chieu=None):
    """LNST (cổ đông công ty mẹ) các quý gần nhất → [(\"Q2/2026\", tỷ đồng), ...] mới nhất trước."""
    Finance = _lop("Finance")
    loi = []
    for src in NGUON_VNSTOCK:
        try:
            f = _goi(lambda: Finance(symbol=ma, source=src))
            kd = chuan_hoa_bang(_goi(lambda: f.income_statement(period="quarter")))
            c_ln = tim_cot(kd, *_TU_LN_ME) or tim_cot(kd, *_TU_LN, tru=("before", "trước", "minority"))
            if c_ln is None or len(kd) < 4:
                raise ValueError("không có cột LNST quý")
            gt = [doc_so(x) for x in kd[c_ln][:8]]
            tong4 = sum(v for v in gt[:4] if v is not None)
            he_so = (_don_vi_ty(tong4, so_cp, eps_tham_chieu) / tong4) if tong4 else 1e-9
            return [(f"Q{q}/{y}", v * he_so) for (y, q), v in zip(kd["_ky"][:8], gt) if v is not None]
        except HetLuot:
            raise
        except Exception as e:
            loi.append(f"{src}: {str(e)[:40]}")
    raise ValueError("; ".join(loi))
