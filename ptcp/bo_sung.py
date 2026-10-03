# -*- coding: utf-8 -*-
"""Khối lượng, bối cảnh thị trường, sự kiện, lịch KQKD, backtest."""
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
    BO_QUA_DAU, HE_SO_THI_TRUONG_XAU, KHUNG_TG, LO_CUNG_PCT, MA_DAI, MA_NGAN,
    RR_NGUONG, SO_PHIEN_SU_KIEN, STOP_ATR_MAX, STOP_ATR_MIN, T_CONG,
)
from .du_lieu import (
    gop_tuan,
)
from .chi_bao import (
    tinh_chi_bao,
)
from .thong_ke import (
    _chi_phi, _co_khoa,
)


# ==========================================================================
# 10D. [MỚI] PHẦN F – KHỐI LƯỢNG & THANH KHOẢN (KL/TB20, OBV, volume profile)
# ==========================================================================
def phan_tich_khoi_luong(d, so_phien=120, so_bin=24):
    """d: dữ liệu ngày đã có chỉ báo. Volume profile tính trên giá điển hình (H+L+C)/3 của 'so_phien' phiên."""
    L = d.iloc[-1]
    g = d.tail(20)
    tang = g.close.diff() > 0
    kl_tang, kl_giam = g.volume[tang].sum(), g.volume[~tang].sum()
    so_bung_no = int((g.volume > 1.5 * g.VolMA20).sum())
    d_gia = d.close.iloc[-1] / d.close.iloc[-21] - 1 if len(d) > 21 else np.nan
    d_obv = d.OBV.iloc[-1] - d.OBV.iloc[-21] if len(d) > 21 else np.nan
    if d_gia == d_gia and d_obv == d_obv:
        if d_gia >= 0 and d_obv >= 0:
            obv = "OBV cùng chiều tăng → dòng tiền xác nhận"
        elif d_gia < 0 and d_obv < 0:
            obv = "OBV cùng chiều giảm → dòng tiền rút ra, xác nhận xu hướng giảm"
        elif d_gia < 0 < d_obv:
            obv = "OBV tăng dù giá giảm → có dấu hiệu gom hàng"
        else:
            obv = "OBV giảm dù giá tăng → phân kỳ, nhịp tăng thiếu dòng tiền"
    else:
        obv = "N/A"
    p = d.tail(so_phien)
    gia_dh = (p.high + p.low + p.close) / 3
    bins = np.linspace(p.low.min(), p.high.max(), so_bin + 1)
    kl_bin, _ = np.histogram(gia_dh, bins=bins, weights=p.volume)
    tam = (bins[:-1] + bins[1:]) / 2
    i_poc = int(np.argmax(kl_bin))
    # Vùng giá trị 70% mở rộng dần quanh POC
    lo_i = hi_i = i_poc
    tong, can = kl_bin[i_poc], 0.7 * kl_bin.sum()
    while tong < can and (lo_i > 0 or hi_i < len(kl_bin) - 1):
        trai = kl_bin[lo_i - 1] if lo_i > 0 else -1
        phai = kl_bin[hi_i + 1] if hi_i < len(kl_bin) - 1 else -1
        if phai >= trai:
            hi_i += 1; tong += phai
        else:
            lo_i -= 1; tong += trai
    poc, val, vah = tam[i_poc], bins[lo_i], bins[hi_i + 1]
    ht = L.close
    vi_tri = ("TRÊN vùng giá trị → bên mua kiểm soát" if ht > vah else
              "DƯỚI vùng giá trị → bên bán kiểm soát, vùng " f"{val:,.2f}–{vah:,.2f} thành kháng cự" if ht < val
              else "TRONG vùng giá trị → cân bằng")
    return {"kl_nay": L.volume, "kl_tb20": L.VolMA20, "ty_le_kl": L.volume / L.VolMA20 if L.VolMA20 else np.nan,
            "kl_tang_giam": kl_tang / kl_giam if kl_giam else np.nan, "so_bung_no": so_bung_no, "obv": obv,
            "poc": poc, "val": val, "vah": vah, "vi_tri": vi_tri, "so_phien": so_phien,
            "profile": pd.DataFrame({"Giá giữa": tam, "Khối lượng": kl_bin}),
            "gt_tb20": float((d.volume * d.close * 1000).tail(20).mean() / 1e9)}


def boi_canh_thi_truong(symbol, df, vni, nhom):
    """Xu hướng VN-Index, đường sức mạnh tương đối (RS), so sánh hiệu suất với nhóm ngành & nhận định."""
    kq = {"vni": None, "rs": None, "bang": None, "nhan_dinh": []}
    ht_ngay = df.index[-1]
    if vni is not None and len(vni) > 60:
        v = tinh_chi_bao(vni[vni.index <= ht_ngay])
        vt = tinh_chi_bao(gop_tuan(vni[vni.index <= ht_ngay]))
        L, Lt = v.iloc[-1], vt.iloc[-1]
        ma200 = L[f"MA{MA_DAI}"]
        xu = ("TĂNG" if L.close > L[f"MA{MA_NGAN}"] > ma200 else
              "GIẢM" if L.close < L[f"MA{MA_NGAN}"] < ma200 else "ĐI NGANG / CHUYỂN TIẾP") \
            if ma200 == ma200 else "chưa đủ dữ liệu MA200"
        kq["vni"] = {"gia": L.close, "xu": xu, "tren_ma200": bool(L.close > ma200) if ma200 == ma200 else None,
                     "macd_tuan_ok": bool(Lt.MACD > Lt.SIGNAL), "r3t": (L.close / v.close.iloc[-64] - 1) * 100
                     if len(v) > 64 else np.nan}
        rs = (df.close / vni.close.reindex(df.index).ffill()).dropna()
        if len(rs) > 60:
            rs_n = rs / rs.iloc[-min(252, len(rs))] * 100
            ma50 = rs_n.rolling(50, min_periods=20).mean()
            kq["rs"] = {"chuoi": rs_n, "ma50": ma50, "tren_ma50": bool(rs_n.iloc[-1] > ma50.iloc[-1]),
                        "doi_3t": (rs.iloc[-1] / rs.iloc[-64] - 1) * 100 if len(rs) > 64 else np.nan,
                        "day_1n": bool(rs.iloc[-1] <= rs.tail(252).min() * 1.01)}
    rows = []

    def hs(s, n):
        s = s[s.index <= ht_ngay]
        return (s.iloc[-1] / s.iloc[-n - 1] - 1) * 100 if len(s) > n else np.nan
    cac = {symbol: df.close}
    if vni is not None:
        cac["VNINDEX"] = vni.close
    for ma, d in (nhom or {}).items():
        cac[ma] = d.close
    for ten, s in cac.items():
        rows.append([ten] + [hs(s, n) for n in KHUNG_TG.values()])
    bang = pd.DataFrame(rows, columns=["Mã"] + [f"{k} %" for k in KHUNG_TG])
    if nhom:
        tv = bang[~bang["Mã"].isin([symbol, "VNINDEX"])].iloc[:, 1:].median()
        bang.loc[len(bang)] = ["TRUNG VỊ NGÀNH"] + list(tv.values)
    kq["bang"] = bang

    def lay(ma, cot):
        r = bang[bang["Mã"] == ma]
        return float(r[cot].iloc[0]) if len(r) else np.nan
    for cot in ("1 năm %", "6 tháng %", "3 tháng %"):
        cp, vn, ng = lay(symbol, cot), lay("VNINDEX", cot), lay("TRUNG VỊ NGÀNH", cot)
        if cp == cp and (vn == vn or ng == ng):
            break
    ky = cot.replace(" %", "")
    nd = []
    if cp == cp and vn == vn:
        nd.append(f"{ky}: {symbol} {cp:+.1f}% vs VN-Index {vn:+.1f}% → {'kém' if cp < vn else 'vượt'} thị trường "
                  f"{abs(cp - vn):.1f} điểm %.")
    if cp == cp and ng == ng:
        rieng, nganh = cp - ng, (ng - vn) if vn == vn else np.nan
        if rieng <= -10:
            ket = f"YẾU TỐ RIÊNG của {symbol} là chính (kém trung vị ngành {abs(rieng):.1f} điểm)"
        elif nganh == nganh and nganh <= -10 and abs(rieng) < 10:
            ket = f"Chủ yếu DO NGÀNH (cả nhóm kém VN-Index {abs(nganh):.1f} điểm, {symbol} sát trung vị ngành)"
        elif rieng >= 10:
            ket = f"{symbol} MẠNH HƠN ngành {rieng:.1f} điểm → yếu tố riêng tích cực"
        else:
            ket = f"{symbol} diễn biến tương đương ngành (chênh {rieng:+.1f} điểm)"
        nd.append(f"Nhận định: {ket}.")
    elif cp == cp:
        nd.append("Chưa có dữ liệu nhóm ngành → chưa tách được yếu tố riêng / yếu tố ngành.")
    kq["nhan_dinh"] = nd
    return kq


def danh_gia_thi_truong(bc, lich, ngay_hien_tai, ngay_kqkd=None, ngay_gdkhq=None):
    """
    [MỚI] Đưa BỐI CẢNH THỊ TRƯỜNG & SỰ KIỆN vào quyết định (bản trước chỉ in ra để đọc):
      • VN-Index xấu  = dưới MA200 HOẶC MACD tuần ≤ Signal
      • RS yếu        = đường RS (mã/VN-Index) ở đáy 1 năm
      → một yếu tố xấu: khối lượng × HE_SO_THI_TRUONG_XAU và hạ 'MUA' xuống 'MUA TỪNG PHẦN';
        cả hai xấu: không mở vị thế mới (THEO DÕI).
      • Sự kiện trong SO_PHIEN_SU_KIEN phiên tới: ngày công bố KQKD (nhập tay) hoặc ngày GDKHQ
        → không mở vị thế mới trước sự kiện (gap giá dễ quét cắt lỗ).
        Chỉ có hạn công bố theo quy định (chưa biết ngày cụ thể) → cảnh báo, không chặn.
    """
    hn = pd.Timestamp(ngay_hien_tai).normalize()
    v, r = bc.get("vni"), bc.get("rs")
    vni_xau = bool(v and ((v["tren_ma200"] is False) or not v["macd_tuan_ok"]))
    rs_yeu = bool(r and r["day_1n"])
    he_so = 1.0
    if vni_xau:
        he_so *= HE_SO_THI_TRUONG_XAU
    if rs_yeu:
        he_so *= HE_SO_THI_TRUONG_XAU
    su_kien, chan = [], False

    def _ngay(s):
        if not s:
            return None
        try:
            return pd.to_datetime(s, dayfirst=True).normalize()
        except (ValueError, TypeError):
            return None

    for ten, nd in (("Công bố KQKD", _ngay(ngay_kqkd)), ("Ngày GDKHQ", _ngay(ngay_gdkhq))):
        if nd is not None and nd >= hn:
            so_phien = int(np.busday_count(hn.date(), nd.date()))
            if so_phien <= SO_PHIEN_SU_KIEN:
                su_kien.append(f"{ten} {nd:%d/%m/%Y} (còn {so_phien} phiên)")
                chan = True
    canh_bao = []
    if lich and not ngay_kqkd:
        q_ket_thuc = lich["han_hop_nhat"] - pd.Timedelta(days=30)
        if q_ket_thuc < hn <= lich["han_hop_nhat"] and lich["con_ngay"] <= 10:
            canh_bao.append(f"Sắp hết hạn công bố {lich['ky']} ({lich['han_hop_nhat']:%d/%m/%Y}) – KQKD có thể "
                            f"ra bất cứ lúc nào")
    return {"vni_xau": vni_xau, "rs_yeu": rs_yeu, "he_so": he_so, "su_kien": su_kien, "chan": chan,
            "canh_bao": canh_bao, "co_vni": v is not None, "co_rs": r is not None}


# ==========================================================================
# 10F. [MỚI] PHẦN H – CƠ BẢN TỐI THIỂU & LỊCH CÔNG BỐ KQKD
# ==========================================================================
def lich_cong_bo_kqkd(hom_nay=None):
    """Hạn công bố BCTC quý theo TT 96/2020: 20 ngày (BCTC riêng) / 30 ngày (công ty mẹ – hợp nhất) sau quý.
    Trả về kỳ gần nhất còn hạn (đang chờ công bố hoặc quý sắp kết thúc)."""
    hn = pd.Timestamp(hom_nay or date.today()).normalize()
    q_end = (hn - pd.offsets.QuarterEnd(1)).normalize()
    for _ in range(3):
        han_hn = q_end + pd.Timedelta(days=30)
        if han_hn >= hn:
            q = (q_end.month - 1) // 3 + 1
            return {"ky": f"KQKD Q{q}/{q_end.year}", "han_rieng": q_end + pd.Timedelta(days=20),
                    "han_hop_nhat": han_hn, "con_ngay": (han_hn - hn).days}
        q_end = (q_end + pd.offsets.QuarterEnd(1)).normalize()
    return None


# ==========================================================================
# 10G. [MỚI] PHẦN I – BACKTEST QUY TẮC VÀO LỆNH CỦA CHÍNH CÔNG CỤ
# ==========================================================================
def backtest_quy_tac(d_ngay, d_tuan, n_giu, loc_tuan=True):
    """
    Quy tắc (phần tuần + ngày; khung giờ không backtest được vì dữ liệu giờ ngắn):
      VÀO  : MACD TUẦN (tuần đã hoàn tất, không nhìn trước) > Signal  VÀ  hôm nay MACD ngày cắt lên Signal
             hoặc cắt lên 0 → mua giá mở cửa phiên kế tiếp (phiên đó khoá trần cả phiên → bỏ lệnh).
      THOÁT: cắt lỗ = max(giá − 2×ATR, giá −7%), tối thiểu 1.5×ATR; chốt lời tại R/R = 2; hết n_giu phiên → bán.
      [SỬA] Theo luật VN: chỉ bán được từ T+2; cắt lỗ bị chạm trước đó → bán giá mở cửa phiên đầu tiên được bán;
            phiên đóng cửa giá sàn → không bán được; gap được tính; trừ phí + trượt giá.
    """
    # Nhãn nến tuần = thứ Sáu: các phiên T2–T5 dùng tuần ĐÃ HOÀN TẤT trước đó; thứ Sáu dùng tuần vừa đóng cửa
    tuan_ok = (d_tuan.MACD > d_tuan.SIGNAL).astype(float).reindex(d_ngay.index, method="ffill").fillna(0).values > 0
    m, s = d_ngay.MACD.values, d_ngay.SIGNAL.values
    cat_sig = np.r_[False, (m[1:] > s[1:]) & (m[:-1] <= s[:-1])]
    cat_0 = np.r_[False, (m[1:] > 0) & (m[:-1] <= 0)]
    tin_hieu = (cat_sig | cat_0) & (tuan_ok if loc_tuan else True)
    o, h, l, c, atr = (d_ngay[k].values for k in ("open", "high", "low", "close", "ATR"))
    tran_khoa, san_khoa = _co_khoa(d_ngay)
    lenh, i = [], BO_QUA_DAU + 30
    while i < len(c) - 2:
        if not tin_hieu[i] or tran_khoa[i + 1]:
            i += 1
            continue
        vao = o[i + 1]
        stop = max(vao - STOP_ATR_MAX * atr[i], vao * (1 - LO_CUNG_PCT / 100))
        if vao - stop < STOP_ATR_MIN * atr[i]:
            stop = vao - STOP_ATR_MIN * atr[i]
        tp = vao + RR_NGUONG * (vao - stop)
        ra, ly_do, ks, j = None, "hết hạn", None, i + 1
        for j in range(i + 1, min(i + 1 + n_giu, len(c))):
            ban_duoc = (j - (i + 1)) >= T_CONG and not san_khoa[j]
            if ks is None and l[j] <= stop:
                ks = j
            if ks is not None and ban_duoc:
                ra = min(stop, o[j]) if j == ks else o[j]
                ly_do = "cắt lỗ" if j == ks else "cắt lỗ (trễ do T+2/khoá sàn)"
                break
            if ks is None and ban_duoc and h[j] >= tp:
                ra, ly_do = max(tp, o[j]), "chốt lời"
                break
        if ra is None:
            ra = c[j]
        lenh.append([d_ngay.index[i + 1], vao, d_ngay.index[j], ra, (ra / vao - 1) * 100 - _chi_phi(),
                     j - i, ly_do])
        i = j + 1
    bl = pd.DataFrame(lenh, columns=["Ngày mua", "Giá mua", "Ngày bán", "Giá bán", "Lãi/lỗ % (sau phí)",
                                     "Số phiên giữ", "Lý do thoát"])
    if not len(bl):
        return {"bang": bl, "so_lenh": 0}
    r = bl["Lãi/lỗ % (sau phí)"]
    von = (1 + r / 100).cumprod()
    lai, lo = r[r > 0].sum(), -r[r <= 0].sum()
    nam = (d_ngay.index[-1] - d_ngay.index[BO_QUA_DAU + 30]).days / 365.25
    return {"bang": bl, "so_lenh": len(bl), "ty_le_thang": (r > 0).mean() * 100, "tb": r.mean(),
            "tb_thang": r[r > 0].mean() if (r > 0).any() else np.nan,
            "tb_thua": r[r <= 0].mean() if (r <= 0).any() else np.nan,
            "pf": lai / lo if lo > 0 else np.nan, "tong": (von.iloc[-1] - 1) * 100,
            "mdd": ((von / von.cummax()) - 1).min() * 100, "giu_tb": bl["Số phiên giữ"].mean(),
            "buy_hold": (c[-1] / c[BO_QUA_DAU + 30] - 1) * 100, "so_nam": nam,
            "tin_cay_thap": len(bl) < 30}
