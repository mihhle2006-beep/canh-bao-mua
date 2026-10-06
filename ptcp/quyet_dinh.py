# -*- coding: utf-8 -*-
"""Trạng thái 3 khung, quản trị rủi ro (E2) và HÀM QUYẾT ĐỊNH DUY NHẤT quyet_dinh_cuoi()."""
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
    BUFFER_ATR, DINH_DAY_THEO, DU_LIEU_CTCK, EV_NGUONG, EWMA_LAMBDA, KHUNG_TG,
    KICH_BAN, LO_CUNG_PCT, NGUONG_HOI_TU, NHOM_PHIEN, RR_NGUONG, SO_MAU_DK_MIN,
    SO_MUC_TIEU, SO_PHIEN_SU_KIEN, STOP_ATR_MAX, STOP_ATR_MIN, TRONG_SO_GOP_NGANH, TRONG_SO_KHUNG,
    TY_LE_THANH_KHOAN, TY_TRONG_MAX, UPSIDE_TOI_THIEU, XS_BAN_RA, XS_CUA_SO, XS_SAN,
    XS_TOI_THIEU_MT, XS_TRAN,
)
from .in_an import (
    fmt, so_vn,
)
from .chi_bao import (
    _duong, sigma_ewma,
)
from .thong_ke import (
    _mo_phong, _phan_vi_trong_so, _tb_trong_so, _tong_hop, _trong_so_gan_day, _upside_toi_da,
    _xs_cham_mot_phia, danh_gia_muc, mo_phong_gop_nganh,
)



def danh_gia_co_ban(cb):
    """
    [MỚI] Bộ lọc cơ bản cho hàm quyết định. cb = kết quả lay_chi_so_co_ban (có thể rỗng).
    Trả {"ha": None | "THEO DÕI" | "MUA TỪNG PHẦN", "ly_do": [...], "kiem_tra": [(mô tả, True/False/None)]}.
    Thiếu số liệu → None (không chặn) – chỉ hạ khuyến nghị khi CÓ dữ liệu xấu.
    """
    cb = cb or {}
    out = {"ha": None, "ly_do": [], "kiem_tra": []}
    if not cfg.LOC_CO_BAN:
        return out
    ln, tg, roe, pe = (cb.get(k) for k in ("LNST 4 quý (tỷ đồng)", "Tăng trưởng LNST 4Q %", "ROE %", "P/E"))
    ok_ln = None if ln is None else ln > 0
    ok_tg = None if tg is None else tg >= cfg.CO_BAN_TANG_TRUONG_MIN
    ok_roe = None if roe is None else roe >= cfg.CO_BAN_ROE_MIN
    ok_pe = None if (pe is None or cfg.CO_BAN_PE_MAX is None) else 0 < pe <= cfg.CO_BAN_PE_MAX
    out["kiem_tra"] = [("Cơ bản: LNST 4 quý dương" + (f" ({fmt(ln, 1)} tỷ)" if ln is not None else ""), ok_ln),
                       (f"Cơ bản: LNST 4 quý không giảm quá {abs(cfg.CO_BAN_TANG_TRUONG_MIN):g}%"
                        + (f" (hiện {fmt(tg, 1, True)}%)" if tg is not None else ""), ok_tg),
                       (f"Cơ bản: ROE ≥ {cfg.CO_BAN_ROE_MIN:g}%" + (f" (hiện {fmt(roe, 1)}%)" if roe is not None else ""),
                        ok_roe)]
    if cfg.CO_BAN_PE_MAX is not None:
        out["kiem_tra"].append((f"Cơ bản: 0 < P/E ≤ {cfg.CO_BAN_PE_MAX:g}", ok_pe))
    if ok_ln is False:
        out["ha"] = "THEO DÕI"
        out["ly_do"].append("doanh nghiệp LỖ 4 quý gần nhất")
    if ok_tg is False:
        out["ha"] = "THEO DÕI"
        out["ly_do"].append(f"LNST 4 quý giảm {abs(tg):.0f}% so với cùng kỳ")
    if out["ha"] is None and (ok_roe is False or ok_pe is False):
        out["ha"] = "MUA TỪNG PHẦN"
        out["ly_do"].append("ROE thấp" if ok_roe is False else "P/E cao")
    return out


def ket_luan_mua(kq):
    """
    Trạng thái 3 khung theo nguyên tắc: Tuần định hướng (QUYỀN PHỦ QUYẾT) → Ngày tìm vùng mua → Giờ điểm vào.
    [SỬA] Chỉ trả về trạng thái; khuyến nghị cuối được quyết định DUY NHẤT bởi quyet_dinh_cuoi().
    """
    L_t = kq["Tuần"]["df"].iloc[-1]
    tuan_ok = bool(L_t.MACD > L_t.SIGNAL)
    co_ngay = kq["Ngày"]["co"]
    ngay_ok = bool(kq["Ngày"]["diem"] >= 2 and not co_ngay["thung_ho_tro"]
                   and (co_ngay["xac_nhan_dao_chieu"] or not co_ngay["xu_huong_giam"]))
    co_gio = kq["Giờ"]["co"] if "Giờ" in kq else None
    gio_ok = None if co_gio is None else bool(co_gio["cat_len_signal"] or co_gio["cat_len_0"]
                                              or co_gio["pha_khang_cu"] or co_gio["pha_dinh_nho"])
    tong_ts = sum(TRONG_SO_KHUNG[k] for k in kq)
    diem_ts = sum(TRONG_SO_KHUNG[k] * kq[k]["diem"] for k in kq) / tong_ts
    return {"tuan_ok": tuan_ok, "tuan_rat_tot": tuan_ok and L_t.MACD > 0, "ngay_ok": ngay_ok,
            "gio_ok": gio_ok, "diem_trong_so": diem_ts}


def quyet_dinh_cuoi(tg, kb, qr, dx, ht, stop, ttr=None, cbl=None):
    """
    [MỚI] HÀM QUYẾT ĐỊNH DUY NHẤT – mọi phần khác (tóm tắt, phần C, thông tin giao dịch, Excel, HTML) chỉ đọc
    kết quả này. Thứ tự kiểm tra (điều kiện trước có quyền phủ quyết điều kiện sau):
      1. Mục tiêu đề xuất ≤ giá  → KHÔNG MUA MỚI
      2. Tuần MACD ≤ Signal       → CHƯA MUA (đúng quy tắc vào lệnh của chính công cụ)
      3. EV (sau phí) < EV_NGUONG → CHƯA MUA (không có lợi thế thống kê)
      4. Ngày chưa có điểm mua    → THEO DÕI
      5. R/R < RR_NGUONG          → CHỜ GIÁ TỐT HƠN (chỉ mua ≤ giá R/R 2)
      6. Giờ chưa có tín hiệu     → CHỜ ĐIỂM VÀO  (không có dữ liệu giờ → MUA TỪNG PHẦN)
      7. Đạt tất cả               → MUA
    [MỚI] Sau đó điều chỉnh theo bối cảnh (danh_gia_thi_truong):
      8. Sự kiện (KQKD/GDKHQ) trong 5 phiên → CHỜ SAU SỰ KIỆN
      9. VN-Index xấu VÀ RS ở đáy 1 năm     → THEO DÕI
     10. Một trong hai xấu                  → MUA TỪNG PHẦN (khối lượng × hệ số)
    [MỚI] 11. Cơ bản (cbl = danh_gia_co_ban): lỗ / LNST giảm sâu → THEO DÕI; ROE thấp / P/E cao → MUA TỪNG PHẦN
    """
    cbl = cbl or {"ha": None, "ly_do": [], "kiem_tra": []}
    ttr = ttr or {"vni_xau": False, "rs_yeu": False, "chan": False, "su_kien": [], "he_so": 1.0,
                  "co_vni": False, "co_rs": False}
    ev, rr = kb["ev_qd"], qr["rr"]
    ok_ev = bool(ev == ev and ev >= EV_NGUONG)
    ok_rr = bool(rr == rr and rr >= RR_NGUONG)
    kiem_tra = [
        ("Tuần: MACD > Signal (quyền phủ quyết)", tg["tuan_ok"]),
        (f"Lợi suất kỳ vọng sau phí ≥ {EV_NGUONG:g}% (hiện {fmt(ev, 2, True)}%)", ok_ev),
        ("Ngày: có điểm mua đã xác nhận", tg["ngay_ok"]),
        (f"R/R ≥ {RR_NGUONG:g} (hiện {fmt(rr)})", ok_rr),
        ("Giờ: có tín hiệu vào lệnh", tg["gio_ok"]),
        ("Mục tiêu đề xuất > giá hiện tại", not qr["phong_thu"]),
        ("Thị trường: VN-Index trên MA200 & MACD tuần > Signal", (not ttr["vni_xau"]) if ttr["co_vni"] else None),
        ("Sức mạnh tương đối: RS không ở đáy 1 năm", (not ttr["rs_yeu"]) if ttr["co_rs"] else None),
        (f"Không có KQKD / GDKHQ trong {SO_PHIEN_SU_KIEN} phiên tới", not ttr["chan"]),
    ] + list(cbl["kiem_tra"])
    if qr["phong_thu"]:
        kn, hd = "KHÔNG MUA MỚI", (f"Mục tiêu đề xuất {fmt(dx['chon'])} ≤ giá hiện tại → không mở vị thế; "
                                   f"chỉ mua lại ở ≤ {fmt(qr['gia_mua_rr2'])}.")
    elif not tg["tuan_ok"]:
        kn, hd = "CHƯA MUA", ("Khung TUẦN phủ quyết: MACD tuần dưới Signal. Đứng ngoài, chờ MACD tuần cắt lên "
                              "Signal rồi xét lại khung ngày.")
    elif not ok_ev:
        kn, hd = "CHƯA MUA", (f"Không có lợi thế thống kê: EV {fmt(ev, 2, True)}% < {EV_NGUONG:g}% với cắt lỗ "
                              f"{fmt(stop['gia'])} – xác suất chạm cắt lỗ trước mục tiêu quá cao.")
    elif not tg["ngay_ok"]:
        kn, hd = "THEO DÕI", ("Tuần ủng hộ, EV dương nhưng khung ngày chưa có điểm mua đã xác nhận. Chờ MACD ngày "
                              "cắt lên Signal / giá phá đỉnh nhỏ gần hỗ trợ.")
    elif not ok_rr:
        kn, hd = "CHỜ GIÁ TỐT HƠN", f"R/R {fmt(rr)} < {RR_NGUONG:g}: chỉ mua ở ≤ {fmt(qr['gia_mua_rr2'])}."
    elif tg["gio_ok"] is None:
        kn, hd = "MUA TỪNG PHẦN", "Đủ điều kiện tuần, ngày, EV, R/R; thiếu dữ liệu giờ → giải ngân từng phần."
    elif not tg["gio_ok"]:
        kn, hd = "CHỜ ĐIỂM VÀO", ("Đủ điều kiện tuần, ngày, EV, R/R. Chờ trên biểu đồ GIỜ: MACD giờ cắt lên Signal "
                                  "hoặc giá phá đỉnh nhỏ / kháng cự giờ.")
    else:
        kn = "MUA" + (" – ĐỦ ĐIỀU KIỆN 3 KHUNG" if tg["tuan_rat_tot"] else "")
        hd = f"Giải ngân theo khối lượng ở phần E2; cắt lỗ {fmt(stop['gia'])} ({fmt(stop['pct'], 1, True)}%)."
    if kn.startswith("MUA"):
        if ttr["chan"]:
            kn, hd = "CHỜ SAU SỰ KIỆN", (f"Đủ điều kiện kỹ thuật nhưng sắp có {', '.join(ttr['su_kien'])} → không mở "
                                         f"vị thế trước sự kiện (gap giá dễ quét cắt lỗ).")
        elif ttr["vni_xau"] and ttr["rs_yeu"]:
            kn, hd = "THEO DÕI", "Đủ điều kiện kỹ thuật nhưng VN-Index xấu VÀ RS ở đáy 1 năm → chưa mở vị thế."
        elif ttr["vni_xau"] or ttr["rs_yeu"]:
            ly = "VN-Index xấu" if ttr["vni_xau"] else "RS ở đáy 1 năm"
            kn = "MUA TỪNG PHẦN"
            hd = f"{ly} → chỉ giải ngân {ttr['he_so'] * 100:.0f}% khối lượng tính theo rủi ro. " + hd
    if kn.startswith("MUA") and cbl["ha"] == "THEO DÕI":
        kn, hd = "THEO DÕI", f"Đủ điều kiện kỹ thuật nhưng cơ bản xấu ({', '.join(cbl['ly_do'])}) → chưa mở vị thế."
    elif kn.startswith("MUA") and cbl["ha"] == "MUA TỪNG PHẦN":
        kn, hd = "MUA TỪNG PHẦN", f"Cơ bản chưa đẹp ({', '.join(cbl['ly_do'])}) → chỉ giải ngân từng phần. " + hd
    mua = kn.startswith("MUA")
    if ht <= stop["gia"]:
        dang_giu = "BÁN – giá đã ở/dưới mức cắt lỗ."
    elif qr["phong_thu"]:
        dang_giu = f"Giảm tỷ trọng khi hồi; bán hết nếu đóng cửa dưới {fmt(stop['gia'])}."
    elif mua:
        dang_giu = f"Giữ / có thể gia tăng; cắt lỗ {fmt(stop['gia'])}."
    else:
        dang_giu = f"Giữ, KHÔNG mua thêm; cắt lỗ {fmt(stop['gia'])} ({fmt(stop['pct'], 1, True)}%)."
    mau = "#2e7d32" if mua else ("#f9a825" if kn in ("THEO DÕI", "CHỜ ĐIỂM VÀO", "CHỜ GIÁ TỐT HƠN",
                                                      "CHỜ SAU SỰ KIỆN") else "#c62828")
    return {"khuyen_nghi": kn, "hanh_dong": hd, "kiem_tra": kiem_tra, "dang_giu": dang_giu, "mau": mau,
            "mua": mua, "ly_do": [t for t, ok in kiem_tra if ok is False]}


def quan_tri_rui_ro(df_ngay, kq, ht, dx, stop, tt, kb, gia_von, so_cp, von_trieu, rui_ro_pct, he_so_tt=1.0):
    """
    E2 – Các mức quản trị rủi ro gắn với mục tiêu đề xuất.
    [SỬA] Chỉ còn MỘT mức cắt lỗ (cắt lỗ thống nhất); các thành phần (đáy ngày, ATR, cứng) chỉ in ở dòng giải thích.
          Bỏ 'cắt lỗ trung hạn theo đáy tuần' (−60…−70%, R/R ≈ 0.1 – không có giá trị hành động).
          Khối lượng mua = vốn × % rủi ro ÷ (giá vào − cắt lỗ), giới hạn bởi trần tỷ trọng.
    """
    d = kq["Ngày"]["df"]
    atr = float(d.ATR.iloc[-1])
    mt = dx["chon"]
    lo_ap_dung = stop["gia"]
    ho_tro = _duong(kq["Ngày"]["xh"], "ho_tro")
    ung = [x for x in ((ho_tro["gia_nay"] if ho_tro else None), ht - atr) if x and lo_ap_dung * 1.01 < x < ht]
    canh_bao_som = max(ung) if ung else None

    mt_ngay = kq["Ngày"]["mt"]["chinh"]
    tp1 = mt_ngay["Giá mục tiêu"] if mt_ngay is not None else None
    if not tp1 or tp1 >= mt * 0.97 or tp1 <= ht:
        tp1 = ht + (mt - ht) / 3
    tp2 = (tp1 + mt) / 2
    chandelier = d.high.tail(22).max() - 3 * atr
    nhan_ts = ("ĐÃ BỊ XUYÊN – giá đã giảm > 3×ATR từ đỉnh 22 phiên" if chandelier >= ht else None)

    rr = (mt - ht) / (ht - lo_ap_dung) if ht > lo_ap_dung else np.nan
    gia_mua_rr2 = (mt + RR_NGUONG * lo_ap_dung) / (1 + RR_NGUONG)
    gia_mua_rr3 = (mt + 3 * lo_ap_dung) / 4

    phong_thu = mt <= ht
    if phong_thu:
        kc_ngay = _duong(kq["Ngày"]["xh"], "khang_cu")
        ban_hoi = tp1 if tp1 and tp1 > ht else (kc_ngay["gia_nay"] if kc_ngay and kc_ngay["gia_nay"] > ht else ht + atr)
        rr = np.nan
        gia_mua_rr2 = mt * 0.9
        muc = [
            ["Bán giảm tỷ trọng khi hồi (MT/kháng cự ngày)", ban_hoi, "Bán 50% vị thế nếu giá hồi lên đây"],
            ["Cảnh báo sớm", canh_bao_som, "Đóng cửa dưới → bán thêm, chỉ giữ tối đa 1/4"],
            ["CẮT LỖ (thống nhất)", lo_ap_dung, "Đóng cửa dưới → BÁN toàn bộ"],
            ["GIÁ TRỊ HỢP LÝ (mục tiêu tự định)", mt, "Mức định giá cơ bản"],
            ["Giá mua lại (biên an toàn 10%)", gia_mua_rr2, "Chỉ mở vị thế mới ở ≤ mức này"],
            ["Trailing stop (đỉnh 22 phiên − 3×ATR)", chandelier, nhan_ts or "Bảo vệ lãi phần đang giữ"],
        ]
    else:
        muc = [
            ["Chốt lời 3 – MỤC TIÊU ĐỀ XUẤT", mt, "Bán 40% còn lại (hoặc giữ nếu trailing stop chưa bị chạm)"],
            ["Chốt lời 2", tp2, "Bán 30%; dời cắt lỗ lên TP1"],
            ["Chốt lời 1", tp1, "Bán 30%; dời cắt lỗ về hoà vốn (giá mua)"],
            [f"Giá mua tối đa để R/R ≥ {RR_NGUONG:g}", gia_mua_rr2, "Không mua cao hơn mức này"],
            ["Giá mua lý tưởng (R/R ≥ 3)", gia_mua_rr3, "Vùng gom ưu tiên"],
            ["Cảnh báo sớm (không phải cắt lỗ)", canh_bao_som, "Đóng cửa dưới → giảm 1/3 tỷ trọng, không mua thêm"],
            ["CẮT LỖ (thống nhất)", lo_ap_dung, "Đóng cửa dưới → BÁN toàn bộ phần còn lại"],
            ["Trailing stop (đỉnh 22 phiên − 3×ATR)", chandelier, nhan_ts or "Dùng sau khi đạt TP1, cập nhật mỗi phiên"],
        ]
    bang = pd.DataFrame(muc, columns=["Mức", "Giá", "Hành động"]).dropna(subset=["Giá"])
    bang["% so giá hiện tại"] = (bang["Giá"] / ht - 1) * 100
    bang = bang[["Mức", "Giá", "% so giá hiện tại", "Hành động"]]

    kl_tb20 = tt["kl_tb20"]
    vt = {}
    rui_ro_1cp = (ht - lo_ap_dung) * 1000

    def _kich_thuoc(von):
        tien_rui_ro = von * rui_ro_pct / 100 * he_so_tt          # [MỚI] × hệ số theo thị trường
        cp_theo_rr = tien_rui_ro / rui_ro_1cp if rui_ro_1cp > 0 else 0
        cp_theo_tt = von * TY_TRONG_MAX / 100 / (ht * 1000)
        return tien_rui_ro, cp_theo_rr, cp_theo_tt, int(min(cp_theo_rr, cp_theo_tt) // 100 * 100)

    if von_trieu and phong_thu:
        vt["Gợi ý mở vị thế mới"] = f"KHÔNG mở mới – chờ giá ≤ {gia_mua_rr2:,.2f} (giá trị hợp lý − 10%)."
    elif von_trieu:
        von = von_trieu * 1e6
        tien_rui_ro, cp_theo_rr, cp_theo_tt, cp_max = _kich_thuoc(von)
        vt = {"Tổng vốn (đồng)": von, f"Rủi ro tối đa/lệnh ({rui_ro_pct:g}% vốn, đồng)": tien_rui_ro,
              "Rủi ro trên 1 CP đến cắt lỗ (đồng)": rui_ro_1cp,
              "KL theo giới hạn rủi ro = vốn × %RR ÷ (giá − cắt lỗ)": int(cp_theo_rr // 100 * 100),
              f"KL theo trần tỷ trọng {TY_TRONG_MAX:.0f}%": int(cp_theo_tt // 100 * 100),
              "Hệ số khối lượng theo thị trường": he_so_tt,
              "KL MUA TỐI ĐA (lô 100)": cp_max, "Giá trị mua tối đa (đồng)": cp_max * ht * 1000,
              "Tỷ trọng / vốn %": cp_max * ht * 1000 / von * 100,
              "Lỗ nếu chạm cắt lỗ (đồng)": cp_max * rui_ro_1cp,
              "Lãi nếu đạt mục tiêu (đồng)": cp_max * (mt - ht) * 1000}
        vt["Số phiên để thoát hàng"] = cp_max / (kl_tb20 * TY_LE_THANH_KHOAN / 100) if kl_tb20 else np.nan
    if so_cp:
        gv = gia_von or ht
        vt["Vị thế đang giữ (CP)"] = so_cp
        vt["Lãi/lỗ hiện tại (đồng)"] = (ht - gv) * so_cp * 1000
        vt["Lỗ thêm nếu chạm cắt lỗ (đồng)"] = (lo_ap_dung - ht) * so_cp * 1000
        vt["Lãi/lỗ so giá vốn tại cắt lỗ (đồng)"] = (lo_ap_dung - gv) * so_cp * 1000
        vt["Số phiên để thoát vị thế đang giữ"] = so_cp / (kl_tb20 * TY_LE_THANH_KHOAN / 100) if kl_tb20 else np.nan
        if gia_von and ht > gia_von * 1.05 and lo_ap_dung < gia_von:
            vt["Gợi ý"] = f"Đang lãi > 5%: có thể nâng cắt lỗ lên giá vốn {gia_von:,.2f} (hoà vốn)."
    vi_du = None
    if not von_trieu and not phong_thu and rui_ro_1cp > 0:
        _, _, _, cp100 = _kich_thuoc(100e6)
        vi_du = (f"Ví dụ vốn 100 triệu, rủi ro {rui_ro_pct:g}%/lệnh: KL = 100,000,000 × {rui_ro_pct:g}% ÷ "
                 f"{rui_ro_1cp:,.0f}đ = {100e6 * rui_ro_pct / 100 / rui_ro_1cp:,.0f} CP → tối đa {cp100:,} CP "
                 f"(sau trần tỷ trọng {TY_TRONG_MAX:.0f}%).")

    r1 = df_ngay.close.pct_change().dropna().tail(252) * 100
    r5 = (df_ngay.close.pct_change(5).dropna().tail(252)) * 100
    c52 = df_ngay.close.tail(252)
    mdd = ((c52 / c52.cummax()) - 1).min() * 100
    beta = tt.get("beta")
    tk = {"VaR 95% 1 phiên %": np.percentile(r1, 5) if len(r1) > 30 else np.nan,
          "VaR 95% 1 tuần %": np.percentile(r5, 5) if len(r5) > 30 else np.nan,
          "Sụt giảm tối đa 52 tuần (MDD) %": mdd,
          "ATR ngày (nghìn đồng)": atr, "ATR / giá %": atr / ht * 100,
          "Nếu VNINDEX −10% → cổ phiếu dự kiến %": -10 * beta if beta is not None and beta == beta else np.nan,
          "R/R (mục tiêu đề xuất / cắt lỗ)": rr}
    t_xem_lai = kb["bang"].loc[kb["bang"]["Kịch bản"] == "CƠ SỞ – đạt MT cơ sở", "Số phiên trung vị"]
    t_xem_lai = float(t_xem_lai.iloc[0]) if len(t_xem_lai) and t_xem_lai.iloc[0] == t_xem_lai.iloc[0] else 42.0
    tk["Cắt lỗ thời gian (phiên)"] = round(t_xem_lai * 1.5)
    return {"bang": bang, "vi_the": vt, "thong_ke": tk, "lo_ap_dung": lo_ap_dung, "tp": (tp1, tp2, mt),
            "canh_bao_som": canh_bao_som, "rr": rr, "gia_mua_rr2": gia_mua_rr2, "trailing": chandelier,
            "phong_thu": phong_thu, "vi_du": vi_du}
