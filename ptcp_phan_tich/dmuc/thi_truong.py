# -*- coding: utf-8 -*-
"""
TRẠNG THÁI THỊ TRƯỜNG (VN-Index) → TỶ LỆ TIỀN MẶT TỰ ĐỘNG.
Mỗi tiêu chí XẤU được 1 điểm (chỉ dùng nến tuần ĐÃ ĐÓNG, đỉnh/đáy ĐÃ XÁC NHẬN – không đổi giữa tuần/phiên):
  1. Giá đóng cửa dưới MA200 ngày
  2. MA50 dưới MA200 (xu hướng trung hạn giảm)
  3. Giá dưới SuperTrend(10, 3) ngày
  4. MACD tuần ≤ Signal
  5. Giá đã THỦNG đáy xác nhận gần nhất, hoặc đáy sau THẤP hơn đáy trước (đáy ngày xác nhận, ≤ 120 phiên)
  6. Đỉnh sau THẤP hơn đỉnh trước (đỉnh ngày xác nhận, ≤ 120 phiên)
  Tiêu chí 5–6 không có dữ liệu còn hiệu lực → bỏ qua (không tính tốt, không tính xấu).
Số tiêu chí xấu ≥ NGUONG_GIAM → GIẢM; ≤ NGUONG_TANG → TĂNG; còn lại → TRUNG TÍNH.
Tỷ lệ tiền mặt giữ lại theo TIEN_MAT_THEO_THI_TRUONG (mặc định GIẢM 50% / TRUNG TÍNH 25% / TĂNG 0%).
"""
import numpy as np
import pandas as pd

from ptcp.chi_bao import tinh_chi_bao, tim_dinh_day
from ptcp.du_lieu import gop_tuan

from .cau_hinh import NGUONG_GIAM, NGUONG_TANG, SUPERTREND_ATR, SUPERTREND_HE_SO, TIEN_MAT_THEO_THI_TRUONG
from .tien_ich import gio_viet_nam


def supertrend(df, n=SUPERTREND_ATR, k=SUPERTREND_HE_SO):
    """SuperTrend chuẩn (ATR Wilder n kỳ, hệ số k). Trả (đường SuperTrend, hướng: +1 tăng / −1 giảm)."""
    h, l, c = df.high.values, df.low.values, df.close.values
    tr = np.maximum(h - l, np.maximum(abs(h - np.r_[c[0], c[:-1]]), abs(l - np.r_[c[0], c[:-1]])))
    atr = pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values
    giua = (h + l) / 2
    tren, duoi = giua + k * atr, giua - k * atr
    ft, fd = tren.copy(), duoi.copy()
    huong = np.ones(len(c), int)
    for i in range(1, len(c)):
        ft[i] = tren[i] if (tren[i] < ft[i - 1] or c[i - 1] > ft[i - 1]) else ft[i - 1]
        fd[i] = duoi[i] if (duoi[i] > fd[i - 1] or c[i - 1] < fd[i - 1]) else fd[i - 1]
        if huong[i - 1] == 1:
            huong[i] = -1 if c[i] < fd[i] else 1
        else:
            huong[i] = 1 if c[i] > ft[i] else -1
    st = np.where(huong == 1, fd, ft)
    return pd.Series(st, index=df.index), pd.Series(huong, index=df.index)


SO_PHIEN_HIEU_LUC = 120      # đỉnh/đáy xác nhận cũ hơn ~6 tháng không còn phản ánh xu hướng hiện tại


def _tieu_chi_day(gia, day_, con_hieu_luc):
    """XẤU nếu giá đã THỦNG đáy xác nhận gần nhất, hoặc đáy (còn hiệu lực) sau thấp hơn đáy trước."""
    ten = "Đáy sau thấp hơn đáy trước / thủng đáy"
    if len(day_) and gia < day_.gia.iloc[-1]:
        return ten, True, f"giá {gia:,.2f} đã thủng đáy xác nhận {day_.gia.iloc[-1]:,.2f} ({day_.time.iloc[-1]:%d/%m/%Y})"
    if len(day_) == 2 and con_hieu_luc(day_.time.iloc[1]):
        return ten, bool(day_.gia.iloc[1] < day_.gia.iloc[0]), (
            f"{day_.gia.iloc[0]:,.2f} ({day_.time.iloc[0]:%d/%m/%Y}) → {day_.gia.iloc[1]:,.2f} "
            f"({day_.time.iloc[1]:%d/%m/%Y})")
    return ten, None, "chưa có 2 đáy xác nhận trong 120 phiên gần nhất"


def _tieu_chi_dinh(dinh, con_hieu_luc):
    """XẤU nếu đỉnh (còn hiệu lực) sau thấp hơn đỉnh trước."""
    ten = "Đỉnh sau thấp hơn đỉnh trước"
    if len(dinh) == 2 and con_hieu_luc(dinh.time.iloc[1]):
        return ten, bool(dinh.gia.iloc[1] < dinh.gia.iloc[0]), (
            f"{dinh.gia.iloc[0]:,.2f} ({dinh.time.iloc[0]:%d/%m/%Y}) → {dinh.gia.iloc[1]:,.2f} "
            f"({dinh.time.iloc[1]:%d/%m/%Y})")
    return ten, None, "chưa có 2 đỉnh xác nhận trong 120 phiên gần nhất"


def _tuan_da_dong(vni):
    """Nến tuần, bỏ tuần chưa kết thúc (chưa qua 15h thứ Sáu giờ VN) → MACD tuần không đổi giữa tuần."""
    w = gop_tuan(vni)
    if len(w) > 1 and pd.Timestamp(gio_viet_nam()) < w.index[-1].normalize() + pd.Timedelta(hours=15):
        w = w.iloc[:-1]
    return w


def danh_gia_thi_truong(vni):
    """
    Trả dict: trang_thai ('TĂNG' | 'TRUNG TÍNH' | 'GIẢM' | 'KHÔNG RÕ'), xau (bool, = GIẢM), so_xau, tong,
    giu_tien_mat (% tự động), nhan (1 dòng mô tả), bang (DataFrame từng tiêu chí).
    """
    if vni is None or len(vni) < 260:
        return {"trang_thai": "KHÔNG RÕ", "xau": False, "so_xau": np.nan, "tong": 0, "giu_tien_mat": None,
                "nhan": "không có/thiếu dữ liệu VN-Index", "bang": pd.DataFrame()}
    d = tinh_chi_bao(vni)
    L = d.iloc[-1]
    ma50, ma200 = d.close.rolling(50).mean().iloc[-1], d.close.rolling(200).mean().iloc[-1]
    st, huong = supertrend(vni)
    w = tinh_chi_bao(_tuan_da_dong(vni)).iloc[-1]
    pv = tim_dinh_day(d, "Ngày")
    pvx = pv[pv.xac_nhan]
    day_, dinh = pvx[pvx.loai == "Đáy"].tail(2), pvx[pvx.loai == "Đỉnh"].tail(2)
    con_hieu_luc = lambda t: (len(d) - 1 - d.index.get_loc(t)) <= SO_PHIEN_HIEU_LUC

    tc = [
        ("Giá dưới MA200 ngày", L.close < ma200, f"{L.close:,.2f} vs MA200 {ma200:,.2f}"),
        ("MA50 dưới MA200", ma50 < ma200, f"MA50 {ma50:,.2f} vs MA200 {ma200:,.2f}"),
        ("Giá dưới SuperTrend(10,3) ngày", huong.iloc[-1] < 0, f"SuperTrend {st.iloc[-1]:,.2f}"),
        ("MACD tuần ≤ Signal (tuần đã đóng)", w.MACD <= w.SIGNAL, f"MACD {w.MACD:,.2f} vs Signal {w.SIGNAL:,.2f}"),
        _tieu_chi_day(L.close, day_, con_hieu_luc),
        _tieu_chi_dinh(dinh, con_hieu_luc),
    ]
    bang = pd.DataFrame([[ten, "XẤU ✘" if x else ("–" if x is None else "Tốt ✔"), ct] for ten, x, ct in tc],
                        columns=["Tiêu chí VN-Index", "Kết quả", "Chi tiết"])
    co_dl = [x for _, x, _ in tc if x is not None]
    so_xau = int(sum(bool(x) for x in co_dl))
    trang_thai = "GIẢM" if so_xau >= NGUONG_GIAM else ("TĂNG" if so_xau <= NGUONG_TANG else "TRUNG TÍNH")
    giu = TIEN_MAT_THEO_THI_TRUONG[trang_thai]
    return {"trang_thai": trang_thai, "xau": trang_thai == "GIẢM", "so_xau": so_xau, "tong": len(co_dl),
            "giu_tien_mat": giu, "bang": bang,
            "nhan": f"VN-Index {trang_thai} ({so_xau}/{len(co_dl)} tiêu chí xấu, phiên {vni.index[-1]:%d/%m/%Y}) "
                    f"→ giữ {giu:g}% tiền mặt"}
