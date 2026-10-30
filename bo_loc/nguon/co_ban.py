# -*- coding: utf-8 -*-
"""
NGUỒN DỮ LIỆU CƠ BẢN (P/E, P/B, ROE, EPS, nợ, cổ tức...) – NHIỀU NGUỒN, GỘP THEO TỪNG CHỈ TIÊU.

  • Mỗi nguồn là 1 hàm f(ma) -> dict {chỉ tiêu: giá trị}, đăng ký trong NGUON_CO_BAN.
  • Gộp: file người dùng > các nguồn online theo cau_hinh.THU_TU_NGUON_CO_BAN (lấy từng chỉ tiêu
    từ nguồn ưu tiên nhất CÓ dữ liệu → nguồn này thiếu thì nguồn sau bù).
  • Đối chiếu chéo: 2 nguồn lệch nhau > LECH_CANH_BAO_PCT % ở EPS, BVPS (số CP > 1%; ROE > 5 điểm %) → ghi cảnh báo.
    KHÔNG so P/E, P/B: mỗi nguồn tính theo giá của một ngày khác nhau (VNDirect: ngày báo cáo; Yahoo: giá hiện tại)
    → giá đi 20% là "lệch" dù số liệu đúng. Lệch thật ở EPS/BVPS vẫn bị bắt qua chính EPS/BVPS.
  • Ghi rõ nguồn của TỪNG chỉ tiêu (cột nguon_chi_tieu) → dẫn nguồn được khi đưa vào báo cáo.
  • Lưu đệm JSON 24 giờ (du_lieu_co_ban/<MÃ>.json) → chạy lại không phải tải lại.

Các API dưới đây là API công khai KHÔNG chính thức, chưa kiểm chứng lâu dài → luôn xem sheet "Nguon du lieu".
Muốn chắc chắn (VD số liệu đưa vào báo cáo): tạo file mẫu (--tao_mau_co_ban), điền từ BCTC/CafeF/Vietstock.
"""
import importlib.util
import json
import os
import time
from datetime import date

import numpy as np
import pandas as pd

from .. import cau_hinh as ch
from ..tien_ich import doc_so
from .http import CAU_DAO_CO_BAN, NHAT_KY, lay_json

# Cột file co_ban.csv (đơn vị ghi rõ) – bỏ trống ô nào thì chương trình lấy online/tự tính nếu có
COT_CO_BAN = {
    "ma": "Mã cổ phiếu",
    "so_cp": "Số CP lưu hành (cổ phiếu)",
    "von_hoa": "Vốn hoá (tỷ đồng) – bỏ trống để tự tính = giá × số CP",
    "ln_4q_ty": "LNST (cổ đông công ty mẹ) 4 quý gần nhất (tỷ đồng) – EPS = số này ÷ số CP lưu hành",
    "dt_4q_ty": "Doanh thu thuần 4 quý gần nhất (tỷ đồng)",
    "eps_ttm": "EPS 4 quý gần nhất do nguồn công bố (đồng/CP) – chỉ dùng khi không tự tính được EPS",
    "eps_cot_loi": "EPS cốt lõi 4 quý, đã loại lãi/lỗ bất thường (đồng/CP) – nếu điền, P/E tính theo số này",
    "eps_nam": "EPS năm gần nhất (đồng/CP)",
    "eps_nam_truoc": "EPS năm trước đó (đồng/CP)",
    "eps_quy": "EPS quý gần nhất (đồng/CP)",
    "eps_quy_cung_ky": "EPS cùng quý năm trước (đồng/CP)",
    "pe": "P/E – bỏ trống để tự tính = giá / EPS",
    "bvps": "Giá trị sổ sách/CP (đồng)",
    "pb": "P/B – bỏ trống để tự tính = giá / BVPS",
    "roe": "ROE (%)",
    "roa": "ROA (%)",
    "no_vay_tts": "Nợ vay / Tổng tài sản (%)",
    "no_phai_tra_tts": "Nợ phải trả / Tổng tài sản (%)",
    "fcf": "Dòng tiền tự do = CFO − Capex, năm gần nhất (tỷ đồng)",
    "tt_hien_thoi": "Hệ số thanh toán hiện thời",
    "tt_nhanh": "Hệ số thanh toán nhanh",
    "kiem_toan_5nam": "1 = BCTC 5 năm đều chấp nhận toàn phần; 0 = không",
    "so_nam_co_tuc": "Số năm liên tục trả cổ tức tiền mặt",
    "co_tuc_tien_mat_cp": "Cổ tức tiền mặt 12 tháng gần nhất (đồng/CP)",
    "dt_g_quy": "Tăng trưởng doanh thu quý gần nhất so cùng kỳ (%)",
    "ln_g_quy": "Tăng trưởng LNST cổ đông mẹ quý gần nhất so cùng kỳ (%)",
    "bien_gop": "Biên gộp quý gần nhất (%)",
    "bien_gop_ck": "Biên gộp cùng quý năm trước (%)",
    "so_huu_nn": "Sở hữu nước ngoài (%)",
    "free_float": "Free float (%)",
    "kiem_toan_ngoai_tru": "1 = BCTC/soát xét gần nhất có ngoại trừ; 0 = không",
}
COT_CHU = {"san", "nganh", "ghi_chu", "ky_eps", "ky_lnst"}
SO_SANH_CHEO = ("roe", "eps_nam", "eps_ttm", "bvps", "so_cp")
# Ưu tiên RIÊNG từng chỉ tiêu (đè thứ tự nguồn chung): số CP & BVPS lấy Yahoo (VCSH mẹ ÷ BVPS, đã trừ CP quỹ) để P/E,
# P/B cùng cơ sở với CTCK ở MỌI mã – giống ptcp (cau_hinh.THU_TU_NGUON_SO_CP).
UU_TIEN_RIENG = {"so_cp": ["Yahoo"], "bvps": ["Yahoo"]}   # P/E, P/B phụ thuộc ngày lấy giá → không so
NGUONG_LECH_RIENG = {"so_cp": 1.0}      # số CP lưu hành: lệch > 1% giữa các nguồn đã đáng kiểm tra (vốn hoá sai theo)
NGUONG_LECH_DIEM = {"roe": 5.0}         # ROE: so theo ĐIỂM % (nguồn dùng VCSH bình quân 5 quý / cuối kỳ khác nhau)
TEN_CHI_TIEU = {"roe": "ROE", "eps_nam": "EPS năm", "eps_ttm": "EPS 4 quý", "bvps": "BVPS", "so_cp": "số CP",
                "pe": "P/E", "pb": "P/B"}


def _so(x):
    return doc_so(x)


def bon_quy_lien_tiep(ds):
    """[('Q2/2026', v), ('Q1/2026', v), ('Q4/2025', v), ('Q3/2025', v)] – đúng 4 quý liên tiếp, mới nhất trước."""
    try:
        so = [int(k.split("/")[1]) * 4 + int(k[1]) for k, _ in ds[:4]]
    except (ValueError, IndexError):
        return False
    return len(so) == 4 and all(a - b == 1 for a, b in zip(so, so[1:]))


def _pct(v):
    """Tỷ lệ dạng 0.15 → 15 (%)."""
    return v * 100 if v is not None and abs(v) <= 1.5 else v


# ================================================================ NGUỒN 1: TCBS
def tu_tcbs(ma):
    kq = {}
    goc = "https://apipubaws.tcbs.com.vn/tcanalysis/v1"
    try:
        j = lay_json(f"{goc}/ticker/{ma}/overview")
        cp = _so(j.get("outstandingShare"))
        if cp:
            kq["so_cp"] = cp * 1e6 if cp < 1e5 else cp
        kq["san"], kq["nganh"] = j.get("exchange"), j.get("industry")
        fp = _so(j.get("foreignPercent"))
        if fp is not None:
            kq["so_huu_nn"] = _pct(fp)
    except Exception:
        pass
    try:
        q = lay_json(f"{goc}/finance/{ma}/financialratio", params={"yearly": 0, "isAll": "true"})
        if isinstance(q, list) and q:
            r = q[0]
            kq.update({"pe": _so(r.get("priceToEarning")), "pb": _so(r.get("priceToBook")),
                       "roe": _pct(_so(r.get("roe"))), "roa": _pct(_so(r.get("roa"))),
                       "tt_hien_thoi": _so(r.get("currentPayment")), "tt_nhanh": _so(r.get("quickPayment")),
                       "eps_quy": _so(r.get("earningPerShare")), "bvps": _so(r.get("bookValuePerShare"))})
            if r.get("equityOnTotalAsset") is not None:
                kq["no_phai_tra_tts"] = (1 - _so(r["equityOnTotalAsset"])) * 100
            if r.get("debtOnAsset") is not None:
                kq["no_vay_tts"] = _pct(_so(r["debtOnAsset"]))
            if len(q) > 4:
                kq["eps_quy_cung_ky"] = _so(q[4].get("earningPerShare"))
    except Exception:
        pass
    try:
        y = lay_json(f"{goc}/finance/{ma}/financialratio", params={"yearly": 1, "isAll": "true"})
        if isinstance(y, list) and len(y) > 1:
            kq["eps_nam"], kq["eps_nam_truoc"] = _so(y[0].get("earningPerShare")), _so(y[1].get("earningPerShare"))
    except Exception:
        pass
    try:
        dv = lay_json(f"{goc}/company/{ma}/dividend-payment-histories",
                      params={"page": 0, "size": 40}).get("listDividendPaymentHis") or []
        tien = [x for x in dv if str(x.get("issueMethod", "")).lower() == "cash"]
        nam = sorted({int(x["cashYear"]) for x in tien if x.get("cashYear")}, reverse=True)
        if nam:
            dem = 1
            for a_, b_ in zip(nam, nam[1:]):
                if a_ - b_ != 1:
                    break
                dem += 1
            kq["so_nam_co_tuc"] = dem if nam[0] >= date.today().year - 2 else 0
            kq["co_tuc_tien_mat_cp"] = sum((x.get("cashDividendPercentage") or 0) * 10_000
                                           for x in tien if int(x.get("cashYear", 0)) == nam[0])
    except Exception:
        pass
    try:
        q = lay_json(f"{goc}/finance/{ma}/incomestatement", params={"yearly": 0, "isAll": "true"})
        if isinstance(q, list) and len(q) > 4:
            q = sorted(q, key=lambda r: (r.get("year") or 0, r.get("quarter") or 0), reverse=True)
            a0, a4 = q[0], q[4]
            g = lambda x, y: (x / y - 1) * 100 if x is not None and y not in (None, 0) and y > 0 else None
            ln = lambda r: _so(r.get("shareHolderIncome", r.get("postTaxProfit")))
            kq["dt_g_quy"] = g(_so(a0.get("revenue")), _so(a4.get("revenue")))
            kq["ln_g_quy"] = g(ln(a0), ln(a4))
            if a0.get("revenue") and a0.get("grossProfit") is not None:
                kq["bien_gop"] = a0["grossProfit"] / a0["revenue"] * 100
            if a4.get("revenue") and a4.get("grossProfit") is not None:
                kq["bien_gop_ck"] = a4["grossProfit"] / a4["revenue"] * 100
            ds4 = [(f"Q{r.get('quarter')}/{r.get('year')}", ln(r)) for r in q[:4]]
            if all(v is not None for _, v in ds4) and bon_quy_lien_tiep(ds4):
                kq["ln_4q_ty"] = sum(v for _, v in ds4)            # tỷ đồng
                kq["ky_lnst"] = "+".join(k for k, _ in ds4)
            dt4 = [_so(r.get("revenue")) for r in q[:4]]
            if all(v is not None for v in dt4) and bon_quy_lien_tiep(ds4):
                kq["dt_4q_ty"] = sum(dt4)
    except Exception:
        pass
    try:
        cf = lay_json(f"{goc}/finance/{ma}/cashflow", params={"yearly": 1, "isAll": "true"})
        if isinstance(cf, list) and cf:
            r = sorted(cf, key=lambda r: r.get("year") or 0, reverse=True)[0]
            if r.get("freeCashFlow") is not None:
                kq["fcf"] = _so(r["freeCashFlow"])
            elif r.get("fromSale") is not None and r.get("investCost") is not None:
                kq["fcf"] = _so(r["fromSale"]) + _so(r["investCost"])
    except Exception:
        pass
    return {k: v for k, v in kq.items() if v is not None}


# ================================================================ NGUỒN 2: VNDirect (api-finfo)
# Đã kiểm chứng (dự án vndirect-mcp, 08/2026): host api-finfo (KHÔNG phải finfo-api), endpoint /v4/ratios,
# tham số q + sort=reportDate:desc, MỖI chỉ số gọi riêng 1 lần (gộp nhiều mã chỉ số → kết quả bị trộn).
_MA_VND = {"PRICE_TO_EARNINGS": "pe", "PRICE_TO_BOOK": "pb", "EPS_TR": "eps_ttm",
           "ROAE_TR_AVG5Q": "roe", "ROAA_TR_AVG5Q": "roa"}


def tu_vndirect(ma):
    kq, loi = {}, []
    for ma_cs, khoa in _MA_VND.items():
        try:
            j = lay_json("https://api-finfo.vndirect.com.vn/v4/ratios",
                         params={"q": f"code:{ma}~ratioCode:{ma_cs}", "sort": "reportDate:desc", "size": 1})
            d = (j.get("data") or [None])[0]
            if d and str(d.get("ratioCode", ma_cs)) == ma_cs and str(d.get("code", ma)).upper() == ma:
                v = _so(d.get("value"))
                if v is not None:
                    kq[khoa] = v
                    if khoa == "eps_ttm" and d.get("reportDate"):
                        kq["ky_eps"] = str(d["reportDate"])[:10]
        except Exception as e:
            loi.append(f"{ma_cs}: {str(e)[:30]}")
    if not kq and loi:
        raise ValueError("; ".join(loi[:2]))
    for k in ("roe", "roa"):
        if k in kq:
            kq[k] = _pct(kq[k])
    return kq


# LNST CÔNG TY MẸ THEO QUÝ (BCTC VNDirect finfo – cùng chỉ tiêu v23000 kho BCTC của ptcp, mọi loại DN: thường / ngân
# hàng / CTCK / bảo hiểm) → EPS = LNST 4 quý ÷ CP lưu hành cho mọi mã (10/2026: chỉ ~25% mã có LNST 4 quý – vnstock hết
# lượt, Yahoo thiếu quý). 1 lần gọi / mã; lọc itemCode không được thì đọc cả bảng KQKD 2 năm rồi tự lọc.
_VND_MODEL = "1,2,3,89,90,91,101,102,103,411,412,413"
_VND_LNST_ME = 23000


def lnst_quy_vnd(dong):
    """Dòng /v4/financial_statements (QUARTER) → {"Qn/YYYY": LNST công ty mẹ tỷ đồng}, chỉ itemCode 23000."""
    kq = {}
    for x in dong or []:
        try:
            if int(x.get("itemCode")) != _VND_LNST_ME or not x.get("fiscalDate"):
                continue
        except (TypeError, ValueError):
            continue
        v, t = _so(x.get("numericValue")), str(x["fiscalDate"])[:10]
        if v is not None:
            kq.setdefault(f"Q{(int(t[5:7]) + 2) // 3}/{t[:4]}", v / 1e9)
    return kq


def tu_vndirect_bctc(ma):
    tu = f"{date.today().year - 2}-01-01"
    goc = "https://api-finfo.vndirect.com.vn/v4/financial_statements"
    q = f"code:{ma}~reportType:QUARTER~modelType:{_VND_MODEL}~fiscalDate:gte:{tu}"
    quy = {}
    for them, co in ((f"~itemCode:{_VND_LNST_ME}", 20), ("", 9999)):
        try:
            j = lay_json(goc, params={"q": q + them, "sort": "fiscalDate:desc", "size": co})
        except Exception:
            if not them:
                raise
            continue                                   # không lọc được theo itemCode → đọc cả bảng
        quy = lnst_quy_vnd(j.get("data") if isinstance(j, dict) else None)
        if len(quy) >= 4:
            break
    ds = sorted(quy.items(), key=lambda kv: int(kv[0][3:]) * 4 + int(kv[0][1]), reverse=True)
    if not bon_quy_lien_tiep(ds):
        return {}
    kq = {"ln_4q_ty": sum(v for _, v in ds[:4]), "ky_lnst": "+".join(k for k, _ in ds[:4])}
    if len(ds) > 4 and bon_quy_lien_tiep(ds[1:5]) and ds[4][1] > 0:        # quý gần nhất so cùng kỳ
        kq["ln_g_quy"] = (ds[0][1] / ds[4][1] - 1) * 100
    return kq


# ================================================================ NGUỒN 3: Yahoo Finance (thư viện yfinance)
_MA_YAHOO = {"trailingPE": "pe", "priceToBook": "pb", "returnOnEquity": "roe", "returnOnAssets": "roa",
             "trailingEps": "eps_ttm", "bookValue": "bvps", "sharesOutstanding": "so_cp",
             "currentRatio": "tt_hien_thoi", "quickRatio": "tt_nhanh", "dividendRate": "co_tuc_tien_mat_cp",
             "earningsQuarterlyGrowth": "ln_g_quy", "revenueGrowth": "dt_g_quy"}


def doc_yahoo_info(info):
    kq = {}
    for k, khoa in _MA_YAHOO.items():
        v = _so(info.get(k))
        if v is not None:
            kq[khoa] = v
    for k in ("roe", "roa", "ln_g_quy", "dt_g_quy"):
        if k in kq:
            kq[k] *= 100                         # Yahoo luôn trả dạng thập phân
    if info.get("financialCurrency") not in (None, "VND"):
        for k in ("eps_ttm", "bvps", "co_tuc_tien_mat_cp"):
            kq.pop(k, None)                      # khác đơn vị tiền → bỏ số tuyệt đối, giữ tỷ số
    return kq


def cp_luu_hanh_yahoo(ticker, info):
    """CP lưu hành đã trừ CP quỹ = VCSH cổ đông mẹ ÷ BVPS (Yahoo) – dùng đúng hàm của ptcp (một nguồn logic)."""
    from .._ptcp import nap_ptcp
    nap_ptcp()
    from ptcp.du_lieu_co_ban import cp_luu_hanh_yahoo as f
    return f(ticker, info)


def lnst_4q_tu_bang_yahoo(df):
    """quarterly_income_stmt của yfinance (đồng) → (tổng 4 quý tỷ đồng, 'Q2/2026+...') hoặc (None, '')."""
    if df is None or len(df) == 0:
        return None, ""
    hang = next((h for h in ("Net Income Common Stockholders", "Net Income",
                             "Net Income From Continuing Operation Net Minority Interest") if h in df.index), None)
    if hang is None:
        return None, ""
    s = df.loc[hang].dropna()
    s = s.sort_index(ascending=False)[:4]
    ds = [(f"Q{(pd.Timestamp(c).month - 1) // 3 + 1}/{pd.Timestamp(c).year}", float(v) / 1e9) for c, v in s.items()]
    if not bon_quy_lien_tiep(ds):
        return None, ""
    return sum(v for _, v in ds), "+".join(k for k, _ in ds)


def _ma_yahoo(ma):
    """Mã Yahoo: HOSE '.VN', HNX '.HN' (ptcp.san; ptcp cũ → '.VN')."""
    try:
        from ptcp.san import ma_yahoo
        return ma_yahoo(ma)
    except ImportError:
        return f"{ma}.VN"


def tu_yahoo(ma):
    try:
        import yfinance as yf
    except ImportError:
        raise ValueError("chưa cài yfinance (pip install yfinance)")
    t = yf.Ticker(_ma_yahoo(ma))
    info = t.info or {}
    kq = doc_yahoo_info(info)
    cp = cp_luu_hanh_yahoo(t, info)
    if cp:
        kq["so_cp"] = cp
    if info.get("financialCurrency") in (None, "VND"):
        try:
            bang = t.quarterly_income_stmt
            ln, ky = lnst_4q_tu_bang_yahoo(bang)
            if ln is not None:
                kq["ln_4q_ty"], kq["ky_lnst"] = ln, ky
            if bang is not None and "Total Revenue" in bang.index:
                s = bang.loc["Total Revenue"].dropna().sort_index(ascending=False)[:4]
                if len(s) == 4:
                    kq["dt_4q_ty"] = float(s.sum()) / 1e9
        except Exception:
            pass
    return kq


# Thêm nguồn mới: viết hàm f(ma) -> dict theo khoá COT_CO_BAN rồi đăng ký vào đây + THU_TU_NGUON_CO_BAN
def tu_vnstock(ma):
    from . import vnstock_nguon
    return vnstock_nguon.co_ban(ma)


tu_vnstock.thu_vien, tu_yahoo.thu_vien = "vnstock", "yfinance"
NGUON_CO_BAN = {"VNDirect": tu_vndirect, "VNDirect BCTC": tu_vndirect_bctc, "vnstock": tu_vnstock, "TCBS": tu_tcbs,
                "Yahoo": tu_yahoo}


# ================================================================ BỘ NHỚ ĐỆM
def _doc_cache(ma, thu_muc):
    f = os.path.join(thu_muc, f"{ma}.json")
    if os.path.exists(f) and time.time() - os.path.getmtime(f) < ch.HAN_CACHE_CO_BAN_GIO * 3600:
        try:
            with open(f, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None
    return None


def _ghi_cache(ma, thu_muc, du_lieu):
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, f"{ma}.json"), "w", encoding="utf-8") as fh:
        json.dump(du_lieu, fh, ensure_ascii=False)


NGUON_LNST = ("VNDirect BCTC", "vnstock", "TCBS", "Yahoo")   # nguồn có LNST theo quý (EPS = LNST 4 quý ÷ số CP)


def _co_lnst(du_lieu):
    return any(isinstance(d, dict) and d.get("ln_4q_ty") is not None for d in (du_lieu or {}).values())


def _thieu_thu_vien(ham):
    """Nguồn cần thư viện chưa cài (bot GitHub không cài vnstock / yfinance) → bỏ qua, khỏi ghi 'Lỗi' cả trăm lần mỗi lượt."""
    tv = getattr(ham, "thu_vien", None)
    return tv is not None and importlib.util.find_spec(tv) is None


def bo_sung_lnst(ma, du_lieu, thu_tu=NGUON_LNST):
    """
    Dữ liệu chưa có LNST 4 quý (VD lưu đệm lúc vnstock hết lượt / TCBS chặn) → thử lại RIÊNG các nguồn có LNST quý
    để P/E luôn tính theo quy tắc EPS = LNST 4 quý ÷ CP lưu hành (giống ptcp). Sửa du_lieu tại chỗ; True nếu bổ sung được.
    """
    if _co_lnst(du_lieu):
        return False
    da_thu = False
    for ten in thu_tu:
        ham = NGUON_CO_BAN.get(ten)
        if ten not in ch.THU_TU_NGUON_CO_BAN or not ham or _thieu_thu_vien(ham) or CAU_DAO_CO_BAN.bo_qua(ten):
            continue
        da_thu = True
        try:
            d = ham(ma)
        except (Exception, SystemExit) as e:
            NHAT_KY.ghi(f"LNST 4 quý {ma}", ten, "Lỗi", str(e)[:80])
            CAU_DAO_CO_BAN.ghi(ten, False)                 # nguồn chết → ngắt, khỏi gọi lại cho mọi mã trong lần chạy
            continue
        CAU_DAO_CO_BAN.ghi(ten, True)
        if d and d.get("ln_4q_ty") is not None:
            du_lieu[ten] = {**(du_lieu.get(ten) or {}), **d}
            NHAT_KY.ghi(f"LNST 4 quý {ma}", ten, "OK", f"{d['ln_4q_ty']:,.1f} tỷ ({d.get('ky_lnst', '')})")
            return True
    if da_thu:
        NHAT_KY.ghi(f"LNST 4 quý {ma}", "—", "Lỗi", "không nguồn nào có LNST 4 quý → dùng EPS nguồn công bố")
    return False


def lay_online(ma, dung_cache=True, thu_muc_cache=None, thu_tu=None):
    """Tải TẤT CẢ nguồn online cho 1 mã → {tên nguồn: dict}. Có lưu đệm; thiếu LNST 4 quý thì tự bổ sung."""
    thu_muc_cache = thu_muc_cache or ch.THU_MUC_CACHE_CO_BAN
    if dung_cache:
        c = _doc_cache(ma, thu_muc_cache)
        if c is not None:
            NHAT_KY.ghi(f"Cơ bản {ma}", "cache", "OK", ", ".join(c))
            if bo_sung_lnst(ma, c):
                _ghi_cache(ma, thu_muc_cache, c)
            return c
    kq = {}
    for ten in (thu_tu or ch.THU_TU_NGUON_CO_BAN):
        ham = NGUON_CO_BAN.get(ten)
        if not ham or _thieu_thu_vien(ham) or CAU_DAO_CO_BAN.bo_qua(ten):
            continue
        try:
            d = ham(ma)
            if d:
                kq[ten] = d
                NHAT_KY.ghi(f"Cơ bản {ma}", ten, "OK", f"{len(d)} chỉ tiêu")
            else:
                NHAT_KY.ghi(f"Cơ bản {ma}", ten, "Lỗi", "rỗng")
            CAU_DAO_CO_BAN.ghi(ten, bool(d))
        except (Exception, SystemExit) as e:
            NHAT_KY.ghi(f"Cơ bản {ma}", ten, "Lỗi", str(e)[:80])
            if "hạn mức" not in str(e) and "lượt" not in str(e):     # hết lượt tạm thời → không tính là nguồn chết
                CAU_DAO_CO_BAN.ghi(ten, False)
    if kq:
        bo_sung_lnst(ma, kq, [t for t in NGUON_LNST if t not in kq])
    if kq and dung_cache:
        _ghi_cache(ma, thu_muc_cache, kq)
    return kq


# ================================================================ FILE NGƯỜI DÙNG
def doc_file(path):
    """co_ban.csv / .xlsx → {mã: {chỉ tiêu: giá trị}}."""
    df = pd.read_excel(path) if path.lower().endswith((".xlsx", ".xls")) else pd.read_csv(path, dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    out = {}
    for _, r in df.iterrows():
        ma = str(r.get("ma", "")).strip().upper()
        if not ma or ma == "NAN":
            continue
        d = {k: _so(r.get(k)) for k in COT_CO_BAN if k != "ma" and k in df.columns}
        d = {k: v for k, v in d.items() if v is not None}
        for k in COT_CHU:
            if k in df.columns and str(r.get(k, "")).strip() not in ("", "nan", "None"):
                d[k] = str(r[k]).strip()
        out[ma] = d
    return out


def tao_mau(ds_ma, path="co_ban_mau.csv"):
    pd.DataFrame({k: (list(ds_ma) if k == "ma" else "") for k in COT_CO_BAN}).to_csv(path, index=False,
                                                                                    encoding="utf-8-sig")
    hd = path.replace(".csv", "_huong_dan.txt")
    with open(hd, "w", encoding="utf-8") as f:
        f.write("HƯỚNG DẪN ĐIỀN co_ban.csv (bỏ trống ô không có số liệu)\n\n")
        for k, v in COT_CO_BAN.items():
            f.write(f"  {k:<20} : {v}\n")
        f.write("\nNguồn số liệu: BCTC đã kiểm toán (HOSE/HNX, website DN), CafeF, Vietstock, Simplize, Fireant.\n"
                "Ghi ngày lấy số liệu vào cột ghi_chu để dẫn nguồn trong báo cáo.\n")
    print(f"  ✔ Đã tạo {os.path.abspath(path)} ({len(ds_ma)} mã) và {hd}")
    print("    Điền số liệu, đổi tên thành co_ban.csv rồi chạy kèm: --co_ban co_ban.csv")


# ================================================================ GỘP & ĐỐI CHIẾU
def gop(online, tu_file=None, thu_tu=None):
    """
    online: {tên nguồn: dict}; tu_file: dict của mã trong file người dùng.
    Trả về dict đã gộp + 'nguon_chi_tieu' (chỉ tiêu ← nguồn) + 'canh_bao_du_lieu' (lệch giữa các nguồn).
    """
    thu_tu = ["file"] + [t for t in (thu_tu or ch.THU_TU_NGUON_CO_BAN) if t in online] + \
             [t for t in online if t not in (thu_tu or ch.THU_TU_NGUON_CO_BAN)]
    tat_ca = dict(online or {})
    if tu_file:
        tat_ca["file"] = tu_file
    kq, nguon_ct = {}, {}
    for ten in thu_tu:
        for k, v in (tat_ca.get(ten) or {}).items():
            if k not in kq and v is not None:
                kq[k], nguon_ct[k] = v, ten
    for k, ds in UU_TIEN_RIENG.items():
        if nguon_ct.get(k) == "file":
            continue
        ten = next((t for t in ds if (tat_ca.get(t) or {}).get(k) is not None), None)
        if ten:
            kq[k], nguon_ct[k] = tat_ca[ten][k], ten
    canh_bao = []
    for k in SO_SANH_CHEO:
        gt = {t: d[k] for t, d in tat_ca.items() if isinstance(d.get(k), (int, float)) and d.get(k)}
        if len(gt) >= 2:
            lo, hi = min(gt.values()), max(gt.values())
            lech = (hi - lo > NGUONG_LECH_DIEM[k]) if k in NGUONG_LECH_DIEM else \
                (lo > 0 and (hi / lo - 1) * 100 > NGUONG_LECH_RIENG.get(k, ch.LECH_CANH_BAO_PCT))
            if lech:
                canh_bao.append(f"{k}: " + ", ".join(f"{t} {v:,.2f}" for t, v in gt.items()))
    if nguon_ct:
        dem = pd.Series(nguon_ct).value_counts()
        kq["nguon_co_ban"] = " + ".join(f"{t}({n})" for t, n in dem.items())
        kq["nguon_chi_tieu"] = "; ".join(f"{k}←{t}" for k, t in nguon_ct.items()
                                         if k in ("pe", "pb", "roe", "eps_ttm", "eps_nam", "bvps", "ln_4q_ty", "so_cp"))
    kq["canh_bao_du_lieu"] = " | ".join(canh_bao)
    if "pb" in nguon_ct:
        kq["nguon_pb"] = nguon_ct["pb"]
    if "bvps" in nguon_ct:
        kq["nguon_bvps"] = nguon_ct["bvps"]
    if "so_cp" in nguon_ct:
        kq["nguon_so_cp"] = nguon_ct["so_cp"]
        so_nguon_cp = sum(1 for d in tat_ca.values() if isinstance(d.get("so_cp"), (int, float)) and d.get("so_cp"))
        kq["so_nguon_so_cp"] = so_nguon_cp
    return kq


def tinh_chi_so(cb, gia):
    """Chỉ tiêu dẫn xuất (giá: nghìn đồng). P/E, P/B tự tính theo GIÁ HIỆN TẠI nếu có EPS/BVPS."""
    g = gia * 1000
    eps_n, eps_nt = cb.get("eps_nam"), cb.get("eps_nam_truoc")
    eps_q, eps_qc = cb.get("eps_quy"), cb.get("eps_quy_cung_ky")
    pe, pe_cach = cb.get("pe"), "nguồn" if cb.get("pe") is not None else ""
    # EPS = LNST 4 quý gần nhất / số CP lưu hành (tự tính); không đủ dữ liệu → EPS nguồn công bố
    eps_tu_tinh = cb["ln_4q_ty"] * 1e9 / cb["so_cp"] if cb.get("ln_4q_ty") is not None and cb.get("so_cp") else None
    eps_dung, ten_eps = next(((v, t) for v, t in (
        (cb.get("eps_cot_loi"), "EPS cốt lõi (tự nhập)"),
        (eps_tu_tinh, f"EPS = LNST 4 quý {cb.get('ky_lnst', '')} ÷ CP lưu hành"),
        (cb.get("eps_ttm"), "EPS 4 quý (nguồn)"), (cb.get("eps_nam"), "EPS năm (nguồn)")) if v), (None, ""))
    if eps_dung and eps_dung > 0 and (ch.PE_THEO_GIA_HIEN_TAI or pe is None or ten_eps.startswith("EPS cốt")):
        pe, pe_cach = g / eps_dung, f"P/E = giá ÷ {ten_eps}"
    elif eps_dung is not None and eps_dung <= 0:
        pe, pe_cach = g / eps_dung if eps_dung else np.nan, "EPS âm – lỗ, không đạt mọi tiêu chí P/E"
    # P/B = GIÁ HIỆN TẠI ÷ BVPS (như P/E và như CTCK: MWG 76.900 ÷ 24.298 = 3,16). P/B của nguồn tính theo giá NGÀY
    # BÁO CÁO (VNDirect MWG 3,32) → chỉ dùng khi không nguồn nào có BVPS.
    pb, pb_cach = cb.get("pb"), ("P/B nguồn " + cb.get("nguon_pb", "")).strip() if cb.get("pb") is not None else ""
    if cb.get("bvps") and cb["bvps"] > 0 and (ch.PE_THEO_GIA_HIEN_TAI or pb is None):
        pb, pb_cach = g / cb["bvps"], f"P/B = giá ÷ BVPS ({cb.get('nguon_bvps', 'nguồn')})"
    von_hoa = cb.get("von_hoa")
    if cb.get("so_cp") and (ch.PE_THEO_GIA_HIEN_TAI or von_hoa is None):
        von_hoa = g * cb["so_cp"] / 1e9

    def tang(a, b):
        if a is None or b is None:
            return np.nan
        if b > 0:
            return (a / b - 1) * 100
        return 100.0 if a > 0 else -100.0

    ct = cb.get("co_tuc_tien_mat_cp")
    nan = lambda k: cb.get(k, np.nan) if cb.get(k) is not None else np.nan
    return {
        "so_cp": nan("so_cp"), "von_hoa": von_hoa if von_hoa is not None else np.nan,
        "pe": pe if pe is not None else np.nan, "pe_nguon": nan("pe"), "pe_cach_tinh": pe_cach,
        "pb": pb if pb is not None else np.nan, "pb_nguon": nan("pb"), "pb_cach_tinh": pb_cach,
        "roe": nan("roe"), "roa": nan("roa"),
        "eps_dung": eps_dung if eps_dung is not None else np.nan,
        "ln_4q_ty": nan("ln_4q_ty"), "dt_4q_ty": nan("dt_4q_ty"), "ky_lnst": cb.get("ky_lnst") or "",
        "eps_ttm": nan("eps_ttm"), "eps_cot_loi": nan("eps_cot_loi"), "ky_eps": cb.get("ky_eps") or "",
        "eps_nam": nan("eps_nam"), "eps_g_nam": tang(eps_n, eps_nt),
        "eps_quy": nan("eps_quy"), "eps_g_quy": tang(eps_q, eps_qc),
        "no_vay_tts": nan("no_vay_tts"), "no_phai_tra_tts": nan("no_phai_tra_tts"), "fcf": nan("fcf"),
        "tt_hien_thoi": nan("tt_hien_thoi"), "tt_nhanh": nan("tt_nhanh"),
        "kiem_toan_5nam": nan("kiem_toan_5nam"), "so_nam_co_tuc": nan("so_nam_co_tuc"),
        "co_tuc_tien_mat_cp": ct if ct is not None else np.nan,
        "ty_suat_co_tuc": ct / g * 100 if ct is not None and g > 0 else np.nan,
        "nguon_co_ban": cb.get("nguon_co_ban", "không có"), "nguon_chi_tieu": cb.get("nguon_chi_tieu", ""),
        "nguon_so_cp": cb.get("nguon_so_cp", ""), "so_nguon_so_cp": cb.get("so_nguon_so_cp", np.nan),
        "canh_bao_du_lieu": cb.get("canh_bao_du_lieu", ""),
        **{k: nan(k) for k in ("dt_g_quy", "ln_g_quy", "bien_gop", "bien_gop_ck", "so_huu_nn", "free_float",
                               "kiem_toan_ngoai_tru")},
        **{k: cb.get(k) or "" for k in COT_CHU},
    }
