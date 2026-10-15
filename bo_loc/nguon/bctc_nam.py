# -*- coding: utf-8 -*-
"""
BCTC THEO NĂM (≥ 4 năm gần nhất) – dữ liệu cho bộ 10 tiêu chí phân tích tài chính.
Nguồn: TCBS (tỷ số + BCKQKD + LCTT + CĐKT theo năm) → Yahoo (yfinance: income_stmt, balance_sheet, cashflow).
Chuẩn hoá về dict, mỗi chỉ tiêu là list MỚI NHẤT TRƯỚC (None = thiếu):
  nam, doanh_thu, ln_gop, lnst, cfo (tỷ đồng) | cr (thanh toán hiện thời), icr (EBIT/lãi vay), de (Nợ/VCSH, lần),
  roe (%), von_gop (tỷ đồng), vay_no (vay nợ tài chính, tỷ đồng)
Lưu đệm 24 giờ: du_lieu_co_ban/<MÃ>_nam.json
Đọc từng nguồn = ptcp.du_lieu_co_ban (_bctc_tcbs / _bctc_vnstock / _bctc_yahoo – một nguồn logic, đã thêm phải thu,
tồn kho, tổng tài sản cho soi chất lượng lợi nhuận). Ở đây chỉ giữ thứ tự nguồn, cầu dao nguồn lỗi và lưu đệm.
"""
import json
import os
import time

from .. import cau_hinh as ch
from .._ptcp import nap_ptcp
from .http import CAU_DAO_CO_BAN, NHAT_KY

nap_ptcp()
from ptcp import du_lieu_co_ban as _cb  # noqa: E402

KHOA = _cb.KHOA_BCTC


def tu_tcbs(ma):
    return _cb._bctc_tcbs(ma)


def tu_yahoo(ma):
    return _cb._bctc_yahoo(ma)


def tu_vnstock(ma):
    return _cb._bctc_vnstock(ma)


NGUON_BCTC_NAM = {"TCBS": tu_tcbs, "vnstock": tu_vnstock, "Yahoo": tu_yahoo}


def lay_bctc_nam(ma, dung_cache=True, thu_muc_cache=None, thu_tu=None):
    """→ dict BCTC năm (kèm 'nguon') hoặc None. Nguồn có nhiều chỉ tiêu nhất được dùng."""
    thu_muc_cache = thu_muc_cache or ch.THU_MUC_CACHE_CO_BAN
    f = os.path.join(thu_muc_cache, f"{ma}_nam.json")
    if dung_cache and os.path.exists(f) and time.time() - os.path.getmtime(f) < ch.HAN_CACHE_CO_BAN_GIO * 3600:
        try:
            with open(f, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    tot, diem_tot, da_lay = None, 0, []
    for ten in thu_tu or [t for t in ("vnstock", "Yahoo", "TCBS") if t in ch.THU_TU_NGUON_CO_BAN]:
        ham = NGUON_BCTC_NAM.get(ten)
        if ten == "vnstock" and "vnstock" not in ch.THU_TU_NGUON_CO_BAN:      # đã tắt bằng --khong_vnstock
            continue
        khoa_cd = f"BCTC năm {ten}"
        if not ham or CAU_DAO_CO_BAN.bo_qua(khoa_cd):
            continue
        try:
            kq = ham(ma)
            da_lay.append(kq)
            diem = sum(v is not None for k in KHOA for v in kq.get(k, [])[:4])
            NHAT_KY.ghi(f"BCTC năm {ma}", ten, "OK", f"{len(kq['nam'])} năm, {diem} ô dữ liệu")
            CAU_DAO_CO_BAN.ghi(khoa_cd, True)
            if diem > diem_tot:
                tot, diem_tot = dict(kq, nguon=ten), diem
            if diem >= 30:                                    # đủ tốt → khỏi thử nguồn sau
                break
        except (Exception, SystemExit) as e:
            NHAT_KY.ghi(f"BCTC năm {ma}", ten, "Lỗi", str(e)[:80])
            if "hạn mức" not in str(e) and "lượt" not in str(e):
                CAU_DAO_CO_BAN.ghi(khoa_cd, False)
    bu = getattr(_cb, "_bu_dong_tai_chinh", None)          # dòng riêng NH/CK/BH (chỉ VCI có) – cùng cách ptcp
    if tot and bu:
        try:
            bu(tot, da_lay, ma)                              # ptcp mới: kèm nợ xấu / CASA (Vietcap IQ)
        except TypeError:
            bu(tot, da_lay)
    if tot and dung_cache:
        os.makedirs(thu_muc_cache, exist_ok=True)
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(tot, fh, ensure_ascii=False)
    return tot
