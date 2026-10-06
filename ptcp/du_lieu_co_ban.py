# -*- coding: utf-8 -*-
"""
THÔNG TIN DOANH NGHIỆP & CHỈ SỐ CƠ BẢN (tách từ du_lieu.py): sàn/ngành/số CP, P/E – P/B – ROE – EPS,
LNST theo quý (4 quý gần nhất + 4 quý trước để tính tăng trưởng), BCTC năm cho Phần J.
Gọi API qua du_lieu (_dl._goi_api) để cache / thử lại / kiểm thử dùng chung một chỗ.
"""
# flake8: noqa: F401
import sys
import os
import io
import re
import json
import time
import base64
import shutil
import zipfile
import builtins
import textwrap
import subprocess
import html as _html
from datetime import datetime, date

import requests
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
from numpy.lib.stride_tricks import sliding_window_view as _cua_so_truot
from . import cau_hinh as cfg
from .cau_hinh import (
    HEADERS, THOI_GIAN_CHO, THU_MUC_CACHE,
)
from .in_an import (
    _print_goc, in_ra, so_vn,
)

from . import du_lieu as _dl


def _tim_so(d, *khoa):
    for k in khoa:
        v = d.get(k)
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v > 0:
            return v
    return None


def lay_thong_tin_dn(symbol):
    """
    Thông tin DN & SỐ CỔ PHIẾU từ NHIỀU nguồn (không dùng Vietstock) để đối chiếu chéo:
      • TCBS overview  : CP lưu hành, sở hữu NN, sàn, ngành
      • VNDirect finfo : KL niêm yết, sàn
      • Yahoo (yfinance): CP lưu hành, vốn hoá (dùng kiểm tra chéo vốn hoá tự tính)
    Trả về: san, nganh, so_huu_nn, so_cp (lưu hành – nguồn ưu tiên), ung_vien_cp = {"luu_hanh": {nguồn: số},
    "niem_yet": {nguồn: số}}, von_hoa_yahoo (tỷ đồng).
    """
    kq = {"ung_vien_cp": {"luu_hanh": {}, "niem_yet": {}}}
    uv = kq["ung_vien_cp"]
    # 1. TCBS
    try:
        j = _dl._goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{symbol}/overview",
                     headers={"Origin": "https://tcinvest.tcbs.com.vn"}, so_lan=1)
        cp = _tim_so(j, "outstandingShare")
        if cp:
            uv["luu_hanh"]["TCBS"] = cp * 1e6 if cp < 1e5 else cp           # API thường trả theo triệu CP
        ph = _tim_so(j, "issueShare")
        if ph:
            uv.setdefault("phat_hanh", {})["TCBS"] = ph * 1e6 if ph < 1e5 else ph
        nn = j.get("foreignPercent")
        if nn is not None:
            kq["so_huu_nn"] = nn * 100 if nn <= 1 else nn
        if j.get("exchange"):
            kq["san"] = j["exchange"]
        if j.get("industry"):
            kq["nganh"] = j["industry"]
        _dl.ghi_nguon("Thông tin DN (CP lưu hành, sở hữu NN, sàn, ngành)", "TCBS", "OK")
    except Exception as e:
        _dl.ghi_nguon("Thông tin DN", "—", f"TCBS lỗi: {str(e)[:60]}")
    # 2. VNDirect finfo
    try:
        j = _dl._goi_finfo("/v4/stocks", {"q": f"code:{symbol}"}, so_lan=1)
        d = next((x for x in (j.get("data") or []) if str(x.get("code", "")).upper() == symbol), {})
        if d.get("floor"):
            kq.setdefault("san", d["floor"])
        ny = _tim_so(d, "listedShare", "listedQuantity", "listedVolume")
        if ny:
            uv["niem_yet"]["VNDirect"] = ny
        lh = _tim_so(d, "outstandingShare", "outstandingShares")
        if lh:
            uv["luu_hanh"]["VNDirect"] = lh
        _dl.ghi_nguon("Thông tin DN (sàn, KL niêm yết)", "VND finfo", "OK" if (ny or lh) else "không có trường số CP")
    except Exception as e:
        _dl.ghi_nguon("Thông tin DN", "—", f"VND finfo lỗi: {str(e)[:60]}")
    # 3. vnstock (KBS/VCI) – số CP lưu hành trong bảng chỉ số
    if cfg.DUNG_VNSTOCK:
        try:
            from . import vnstock_nguon
            d = vnstock_nguon.co_ban(symbol)
            _VNSTOCK_CB[symbol] = d                       # dùng lại cho chỉ số cơ bản → đỡ tốn lượt gọi
            if d.get("so_cp"):
                uv["luu_hanh"]["vnstock"] = d["so_cp"]
            _dl.ghi_nguon("Thông tin DN (CP lưu hành)", "vnstock", "OK" if d.get("so_cp") else "không có số CP")
        except (Exception, SystemExit) as e:
            _dl.ghi_nguon("Thông tin DN", "—", f"vnstock lỗi: {str(e)[:60]}")
    # 4. Yahoo
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.VN").info or {}
        cp = _tim_so(info, "sharesOutstanding", "impliedSharesOutstanding")
        if cp:
            uv["luu_hanh"]["Yahoo"] = cp
        if _tim_so(info, "marketCap") and info.get("currency") in (None, "VND"):
            kq["von_hoa_yahoo"] = info["marketCap"] / 1e9
        _dl.ghi_nguon("Thông tin DN (CP lưu hành, vốn hoá)", "Yahoo", "OK" if cp else "không có số CP")
    except Exception as e:
        _dl.ghi_nguon("Thông tin DN", "—", f"Yahoo lỗi: {str(e)[:60]}")
    for ten in cfg.THU_TU_NGUON_SO_CP:                    # nguồn ưu tiên cho CP lưu hành
        if ten in uv["luu_hanh"]:
            kq["so_cp"], kq["nguon_so_cp"] = uv["luu_hanh"][ten], ten
            break
    tom = ", ".join(f"{n} {so_vn(v)}" for n, v in uv["luu_hanh"].items()) or "không nguồn nào có"
    in_ra(f"  Số CP lưu hành theo các nguồn: {tom}")
    return kq


# --------------------------------------------------------------------------
# CHỈ SỐ CƠ BẢN: VNDirect (api-finfo) → TCBS → Yahoo. P/E TÍNH LẠI = giá hiện tại ÷ EPS 4 quý gần nhất.
# VNDirect /v4/ratios: tham số q + sort=reportDate:desc, MỖI chỉ số gọi riêng 1 lần (gộp nhiều mã → bị trộn).
# --------------------------------------------------------------------------
_MA_VND = {"PRICE_TO_EARNINGS": "P/E", "PRICE_TO_BOOK": "P/B", "EPS_TR": "EPS 4Q", "ROAE_TR_AVG5Q": "ROE %"}


def _ty_le(v):
    return v * 100 if v is not None and abs(v) < 2 else v


def _co_ban_vndirect(symbol):
    kq, ky = {}, ""
    for ma_cs, khoa in _MA_VND.items():
        try:
            j = _dl._goi_finfo("/v4/ratios", {"q": f"code:{symbol}~ratioCode:{ma_cs}", "sort": "reportDate:desc",
                                          "size": 1}, so_lan=1)
            d = (j.get("data") or [None])[0]
            if d and str(d.get("ratioCode", ma_cs)) == ma_cs and str(d.get("code", symbol)).upper() == symbol:
                v = d.get("value")
                if v is not None:
                    kq[khoa] = float(v)
                    if khoa == "EPS 4Q" and d.get("reportDate"):
                        ky = str(d["reportDate"])[:10]
        except Exception:
            continue
    if "ROE %" in kq:
        kq["ROE %"] = _ty_le(kq["ROE %"])
    if kq:
        kq["ky"] = f"EPS kỳ {ky}" if ky else "mới nhất"
    return kq


def _co_ban_tcbs(symbol):
    j = _dl._goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/financialratio",
                 params={"yearly": 0, "isAll": "false"}, so_lan=1,
                 headers={"Origin": "https://tcinvest.tcbs.com.vn"})
    rows = j if isinstance(j, list) else (j.get("data") or [])
    if not rows:
        return {}
    r = rows[0]
    kq = {"P/E": r.get("priceToEarning"), "P/B": r.get("priceToBook"), "ROE %": _ty_le(r.get("roe")),
          "EPS 4Q": r.get("earningPerShare"), "ky": f"Q{r.get('quarter')}/{r.get('year')}"}
    return {k: v for k, v in kq.items() if v is not None}


def _co_ban_yahoo(symbol):
    try:
        import yfinance as yf
    except ImportError:
        raise ValueError("chưa cài yfinance")
    info = yf.Ticker(f"{symbol}.VN").info or {}
    kq = {"P/E": info.get("trailingPE"), "P/B": info.get("priceToBook"),
          "ROE %": _ty_le(info.get("returnOnEquity")),
          "EPS 4Q": info.get("trailingEps") if info.get("financialCurrency") in (None, "VND") else None,
          "ky": "TTM"}
    return {k: v for k, v in kq.items() if v is not None}


_VNSTOCK_CB = {}             # kết quả vnstock đã lấy trong phiên (dùng chung giữa các bước)


def _co_ban_vnstock(symbol):
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt")
    from . import vnstock_nguon
    d = _VNSTOCK_CB.get(symbol) or vnstock_nguon.co_ban(symbol)
    _VNSTOCK_CB[symbol] = d
    kq = {"P/E": d.get("pe"), "P/B": d.get("pb"), "ROE %": d.get("roe"), "EPS 4Q": d.get("eps_ttm"),
          "ky": d.get("ky_lnst", "mới nhất")}
    return {k: v for k, v in kq.items() if v is not None}


NGUON_CO_BAN = [("VNDirect", _co_ban_vndirect), ("vnstock", _co_ban_vnstock), ("TCBS", _co_ban_tcbs),
                ("Yahoo", _co_ban_yahoo)]


# --------------------------------------------------------------------------
# LNST 4 QUÝ GẦN NHẤT (tỷ đồng) – để tự tính EPS = LNST 4 quý ÷ số CP lưu hành
# Ưu tiên LNST thuộc cổ đông công ty mẹ (đúng cách tính EPS theo VAS); không có thì LNST hợp nhất.
# --------------------------------------------------------------------------
def _lnst_tcbs(symbol):
    j = _dl._goi_api(f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance/{symbol}/incomestatement",
                 params={"yearly": 0, "isAll": "true"}, so_lan=1, headers={"Origin": "https://tcinvest.tcbs.com.vn"})
    rows = j if isinstance(j, list) else (j.get("data") or [])
    rows = sorted([r for r in rows if r.get("year") and r.get("quarter")],
                  key=lambda r: (r["year"], r["quarter"]), reverse=True)[:8]   # 8 quý: tính tăng trưởng
    ds = []
    for r in rows:
        v = r.get("shareHolderIncome", r.get("postTaxProfit"))
        if v is None:
            if len(ds) >= 4:                     # quý cũ (5–8) thiếu → vẫn đủ 4 quý gần nhất
                break
            return None
        ds.append((f"Q{r['quarter']}/{r['year']}", float(v)))           # TCBS: tỷ đồng
    return ds


def _lnst_yahoo(symbol):
    import yfinance as yf
    t = yf.Ticker(f"{symbol}.VN")
    if (t.info or {}).get("financialCurrency") not in (None, "VND"):
        raise ValueError("đơn vị tiền không phải VND")
    df = t.quarterly_income_stmt
    hang = next((h for h in ("Net Income Common Stockholders", "Net Income",
                             "Net Income From Continuing Operation Net Minority Interest") if h in df.index), None)
    if hang is None:
        return None
    s = df.loc[hang].dropna().sort_index(ascending=False)[:8]
    return [(f"Q{(c.month - 1) // 3 + 1}/{c.year}", float(v) / 1e9) for c, v in s.items()]   # đồng → tỷ


def _lnst_vnstock(symbol):
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt")
    from . import vnstock_nguon
    d = _VNSTOCK_CB.get(symbol, {})
    return vnstock_nguon.lnst_quy(symbol, d.get("so_cp"), d.get("eps_ttm"))


NGUON_LNST = [("TCBS", _lnst_tcbs), ("vnstock", _lnst_vnstock), ("Yahoo", _lnst_yahoo)]


def _bon_quy_lien_tiep(ds, n=4):
    """Đúng n quý liên tiếp, mới nhất trước (Q2/2026, Q1/2026, Q4/2025, Q3/2025)."""
    if not ds or len(ds) < n:
        return False
    so = [int(k.split("/")[1]) * 4 + int(k[1]) for k, _ in ds[:n]]
    return all(a - b == 1 for a, b in zip(so, so[1:]))


def lay_lnst_4_quy(symbol):
    """→ (tổng LNST 4 quý tỷ đồng, [(kỳ, LNST)], nguồn) hoặc (None, [], lý do)."""
    loi = []
    for ten, ham in NGUON_LNST:
        try:
            ds = ham(symbol)
            if _bon_quy_lien_tiep(ds):
                return sum(v for _, v in ds[:4]), (ds[:8] if _bon_quy_lien_tiep(ds, 8) else ds[:4]), ten
            loi.append(f"{ten}: không đủ 4 quý liên tiếp")
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:40]}")
    return None, [], "; ".join(loi)


# --------------------------------------------------------------------------
# BCTC THEO NĂM (≥ 3–4 năm) – cho bộ 10 tiêu chí phân tích tài chính (Phần J5)
# Nguồn: TCBS → vnstock → Yahoo. Chuẩn hoá: list MỚI NHẤT TRƯỚC (None = thiếu).
# --------------------------------------------------------------------------
KHOA_BCTC = ("doanh_thu", "ln_gop", "lnst", "cfo", "cr", "icr", "de", "roe", "von_gop", "vay_no")


def _bctc_tcbs(symbol):
    goc = "https://apipubaws.tcbs.com.vn/tcanalysis/v1/finance"
    bang = {}
    for ten in ("financialratio", "incomestatement", "cashflow", "balancesheet"):
        try:
            j = _dl._goi_api(f"{goc}/{symbol}/{ten}", params={"yearly": 1, "isAll": "true"}, so_lan=1,
                         headers={"Origin": "https://tcinvest.tcbs.com.vn"})
            bang[ten] = {int(r["year"]): r for r in (j if isinstance(j, list) else []) if r.get("year")}
        except Exception:
            bang[ten] = {}
    nam = sorted(set().union(*[set(b) for b in bang.values()]), reverse=True)[:5]
    if len(nam) < 3:
        raise ValueError("TCBS: không đủ 3 năm BCTC")
    kq = {"nam": nam, **{k: [None] * len(nam) for k in KHOA_BCTC}}
    for i, y in enumerate(nam):
        r, kd, lc, cd = (bang[t].get(y, {}) for t in ("financialratio", "incomestatement", "cashflow", "balancesheet"))
        kq["doanh_thu"][i], kq["ln_gop"][i] = _so(kd.get("revenue")), _so(kd.get("grossProfit"))
        kq["lnst"][i] = _so(kd.get("shareHolderIncome", kd.get("postTaxProfit")))
        kq["cfo"][i], kq["cr"][i] = _so(lc.get("fromSale")), _so(r.get("currentPayment"))
        kq["icr"][i] = _so(r.get("ebitOnInterest"))
        kq["de"][i] = _so(r.get("payableOnEquity", r.get("debtOnEquity")))
        kq["roe"][i] = _ty_le(_so(r.get("roe")))
        kq["von_gop"][i] = _so(cd.get("capital"))
        vay = [_so(cd.get(k)) for k in ("shortDebt", "longDebt")]
        kq["vay_no"][i] = sum(v for v in vay if v is not None) if any(v is not None for v in vay) else None
    return kq


def _bctc_vnstock(symbol):
    if not cfg.DUNG_VNSTOCK:
        raise ValueError("đã tắt")
    from . import vnstock_nguon
    return vnstock_nguon.bctc_nam(symbol)


def _bctc_yahoo(symbol):
    import yfinance as yf
    t = yf.Ticker(f"{symbol}.VN")
    kd, cd, lc = t.income_stmt, t.balance_sheet, t.cashflow
    if kd is None or kd.empty:
        raise ValueError("Yahoo: không có BCTC năm")
    cot = sorted(kd.columns, reverse=True)[:5]
    kq = {"nam": [c.year for c in cot], **{k: [None] * len(cot) for k in KHOA_BCTC}}

    def h(df, *ten):
        return next((df.loc[x] for x in ten if df is not None and x in df.index), None)

    ty = lambda s_, c: (float(s_[c]) / 1e9 if s_ is not None and c in s_.index and s_[c] == s_[c] else None)
    dt, lg, ln = h(kd, "Total Revenue"), h(kd, "Gross Profit"), h(kd, "Net Income Common Stockholders", "Net Income")
    ebit, lv = h(kd, "EBIT"), h(kd, "Interest Expense")
    tsnh, nnh = h(cd, "Current Assets"), h(cd, "Current Liabilities")
    no, vcsh = h(cd, "Total Liabilities Net Minority Interest"), h(cd, "Stockholders Equity")
    vg, vay, cfo = h(cd, "Common Stock", "Capital Stock"), h(cd, "Total Debt"), h(lc, "Operating Cash Flow")
    for i, c in enumerate(cot):
        kq["doanh_thu"][i], kq["ln_gop"][i], kq["lnst"][i] = ty(dt, c), ty(lg, c), ty(ln, c)
        kq["cfo"][i], kq["von_gop"][i], kq["vay_no"][i] = ty(cfo, c), ty(vg, c), ty(vay, c)
        a, b = ty(tsnh, c), ty(nnh, c)
        kq["cr"][i] = a / b if a is not None and b else None
        e, l_ = ty(ebit, c), ty(lv, c)
        kq["icr"][i] = e / abs(l_) if e is not None and l_ else None
        n, v = ty(no, c), ty(vcsh, c)
        kq["de"][i] = n / v if n is not None and v and v > 0 else None
        kq["roe"][i] = kq["lnst"][i] / v * 100 if kq["lnst"][i] is not None and v and v > 0 else None
    return kq


NGUON_BCTC_NAM = [("TCBS", _bctc_tcbs), ("vnstock", _bctc_vnstock), ("Yahoo", _bctc_yahoo)]


def lay_bctc_nam(symbol, im_lang=False):
    """BCTC năm của 1 mã → dict (kèm 'nguon') hoặc None. Lấy nguồn có nhiều ô dữ liệu nhất."""
    tot, diem_tot, loi = None, 0, []
    for ten, ham in NGUON_BCTC_NAM:
        try:
            kq = ham(symbol)
            diem = sum(v is not None for k in KHOA_BCTC for v in kq[k][:4])
            if diem > diem_tot:
                tot, diem_tot = dict(kq, nguon=ten), diem
            if diem >= 30:
                break
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:40]}")
    if not im_lang:
        _dl.ghi_nguon(f"BCTC năm {symbol} (10 tiêu chí)", tot["nguon"] if tot else "—",
                  f"{len(tot['nam'])} năm, {diem_tot} ô dữ liệu" if tot else "; ".join(loi)[:120])
    return tot


def lay_chi_so_co_ban(symbol, gia=None, so_cp_luu_hanh=None, lnst_4q=None):
    """
    P/E, P/B, ROE, EPS. P/B & ROE: VNDirect → TCBS → Yahoo (nguồn sau bù chỗ thiếu).
    P/E = Thị giá (gia, nghìn đồng) / EPS, với EPS = LNST 4 quý gần nhất / số CP lưu hành – TỰ TÍNH:
      LNST 4 quý: tham số lnst_4q (tỷ đồng, nhập từ BCTC) → TCBS → Yahoo
      Số CP lưu hành: so_cp_luu_hanh (cơ cấu cổ phiếu của báo cáo: phát hành − CP quỹ)
    Không đủ dữ liệu tự tính → dùng EPS 4 quý của nguồn (VNDirect EPS_TR...), ghi rõ cách tính.
    """
    kq, nguon, loi = {}, [], []
    for ten, ham in NGUON_CO_BAN:
        if all(k in kq for k in ("P/E", "P/B", "ROE %", "EPS 4Q")):
            break
        try:
            d = ham(symbol)
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:40]}")
            continue
        moi = [k for k in d if k != "ky" and k not in kq]
        if moi:
            for k in moi:
                kq[k] = d[k]
            nguon.append(f"{ten} ({d.get('ky', '')})")
        else:
            loi.append(f"{ten}: không có số liệu")

    # ---- EPS tự tính = LNST 4 quý / CP lưu hành ----
    if lnst_4q is not None:
        tong, ds_quy, nguon_ln = float(lnst_4q), [], "nhập tay (BCTC)"
    elif so_cp_luu_hanh:
        tong, ds_quy, nguon_ln = lay_lnst_4_quy(symbol)
    else:
        tong, ds_quy, nguon_ln = None, [], "thiếu số CP lưu hành"
    if tong is not None and so_cp_luu_hanh:
        kq["EPS 4Q nguồn"] = kq.get("EPS 4Q")
        kq["LNST 4 quý (tỷ đồng)"] = tong
        kq["EPS 4Q"] = tong * 1e9 / so_cp_luu_hanh
        if len(ds_quy) >= 8:                                     # [MỚI] tăng trưởng LNST 4 quý so với 4 quý trước
            truoc = sum(v for _, v in ds_quy[4:8])
            kq["LNST 4 quý trước (tỷ đồng)"] = truoc
            if truoc > 0:
                kq["Tăng trưởng LNST 4Q %"] = (tong / truoc - 1) * 100
        kq["cach_tinh_eps"] = (f"LNST 4 quý {'+'.join(k for k, _ in ds_quy[:4]) or ''} = {tong:,.1f} tỷ ({nguon_ln}) "
                               f"÷ {so_cp_luu_hanh:,.0f} CP lưu hành")
        nguon.append(f"LNST {nguon_ln}")
    elif kq.get("EPS 4Q") is not None:
        kq["cach_tinh_eps"] = "EPS 4 quý do nguồn công bố (chưa tự tính được: " + str(nguon_ln)[:60] + ")"

    if not nguon:
        _dl.ghi_nguon("Chỉ số cơ bản", "—", "; ".join(loi)[:120])
        return {}
    if gia and kq.get("EPS 4Q"):
        kq["P/E nguồn"] = kq.get("P/E")
        kq["P/E"] = gia * 1000 / kq["EPS 4Q"]          # EPS âm → P/E âm (doanh nghiệp lỗ)
        kq["cach_tinh_pe"] = f"P/E = {gia:,.2f} nghìn ÷ EPS {kq['EPS 4Q']:,.0f} đ"
    kq["nguon"] = " + ".join(nguon)
    kq["ky"] = nguon[0].split("(", 1)[-1].rstrip(")")
    _dl.ghi_nguon("Chỉ số cơ bản (P/E, P/B, ROE, EPS)", nguon[0].split(" (")[0],
              kq["nguon"] + (f" | {kq['cach_tinh_eps']}" if kq.get("cach_tinh_eps") else ""))
    return kq


def _so(x):
    """'414.064.000' / '414,064,000' / 414064000 → 414064000.0 (bỏ mọi ký tự không phải số)."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if x == x and x > 0 else None
    d = re.sub(r"[^\d]", "", str(x))
    return float(d) if d else None
