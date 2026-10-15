# -*- coding: utf-8 -*-
"""
LÕI PHÂN TÍCH KỸ THUẬT (cùng thuật toán với phân_tích_cổ_phiếu.py):
chỉ báo MACD/RSI/ATR/ADX/SuperTrend, đỉnh đáy theo MACD, đường xu hướng, mục tiêu giá, tín hiệu.
Hàm thuần (chỉ nhận DataFrame, không gọi mạng) → dễ kiểm thử.
"""
import numpy as np
import pandas as pd

from ..cau_hinh import (BO_QUA_DAU, MACD_CHAM, MACD_NHANH, MACD_TIN_HIEU, NGUONG_GAN_HO_TRO, SO_NEN_GAN,
                        UPSIDE_MAX, UPSIDE_MIN)


def gop_tuan(df_ngay):
    """Gộp nến ngày thành nến tuần (tuần kết thúc thứ Sáu)."""
    w = df_ngay.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min",
                                       "close": "last", "volume": "sum"}).dropna()
    return w


def tinh_chi_bao(df):
    df = df.copy()
    c = df.close
    df["MACD"] = c.ewm(span=MACD_NHANH, adjust=False).mean() - c.ewm(span=MACD_CHAM, adjust=False).mean()
    df["SIGNAL"] = df.MACD.ewm(span=MACD_TIN_HIEU, adjust=False).mean()
    df["HIST"] = df.MACD - df.SIGNAL

    delta = c.diff()
    tang = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    giam = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    df["RSI"] = 100 - 100 / (1 + tang / giam.replace(0, np.nan))

    tr = pd.concat([df.high - df.low, (df.high - c.shift()).abs(),
                    (df.low - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["VolMA20"] = df.volume.rolling(20, min_periods=5).mean()
    df["pos"] = np.arange(len(df))          # vị trí nến (dùng để vẽ & tính đường thẳng)
    return df


def tim_dinh_day(df):
    """
    Trả về DataFrame các đỉnh/đáy, mỗi dòng ứng với 1 đoạn MACD:
      time, pos, gia, loai ('Đỉnh'/'Đáy'), macd_cuc_tri, xac_nhan, tu, den
    """
    d = df.iloc[BO_QUA_DAU:]
    dau = np.sign(d.MACD).replace(0, np.nan).ffill().fillna(1)
    ma_doan = (dau != dau.shift()).cumsum()
    nhom = list(d.groupby(ma_doan))

    rows = []
    for k, (_, g) in enumerate(nhom):
        duong = dau.loc[g.index[0]] > 0
        xac_nhan = k < len(nhom) - 1           # đoạn cuối chưa kết thúc → tạm thời
        if duong:
            t = g.high.idxmax()
            rows.append([t, int(df.pos[t]), g.high.max(), "Đỉnh", g.MACD.max(),
                         xac_nhan, g.index[0], g.index[-1]])
        else:
            t = g.low.idxmin()
            rows.append([t, int(df.pos[t]), g.low.min(), "Đáy", g.MACD.min(),
                         xac_nhan, g.index[0], g.index[-1]])
    return pd.DataFrame(rows, columns=["time", "pos", "gia", "loai", "macd_cuc_tri",
                                       "xac_nhan", "tu", "den"])


def duong_xu_huong(df, pv):
    ket_qua = {}
    x_nay = len(df) - 1
    for loai, khoa in (("Đỉnh", "khang_cu"), ("Đáy", "ho_tro")):
        p = pv[pv.loai == loai].tail(2)
        if len(p) < 2:
            continue
        (x1, x2), (y1, y2) = p.pos.values, p.gia.values
        if x2 == x1:
            continue
        doc = (y2 - y1) / (x2 - x1)
        ket_qua[khoa] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "doc": doc,
                         "gia_nay": y1 + doc * (x_nay - x1),
                         "gia_truoc": y1 + doc * (x_nay - 1 - x1)}

    # Phân loại cấu trúc xu hướng
    dinh, day_ = pv[pv.loai == "Đỉnh"].tail(2), pv[pv.loai == "Đáy"].tail(2)
    if len(dinh) == 2 and len(day_) == 2:
        dinh_cao_hon = dinh.gia.iloc[1] > dinh.gia.iloc[0]
        day_cao_hon = day_.gia.iloc[1] > day_.gia.iloc[0]
        if dinh_cao_hon and day_cao_hon:
            cau_truc = "TĂNG"
        elif not dinh_cao_hon and not day_cao_hon:
            cau_truc = "GIẢM"
        elif dinh_cao_hon and not day_cao_hon:
            cau_truc = "biên độ dao động nới rộng"
        else:
            cau_truc = "biên độ dao động thu hẹp"
    else:
        cau_truc = "chưa xác định"
    ket_qua["cau_truc"] = cau_truc
    return ket_qua


def tinh_muc_tieu(df, pv, xh, ten_khung):
    ht = df.close.iloc[-1]
    ung_vien = []

    # (a) Đỉnh cũ phía trên giá hiện tại: lấy tối đa 4 đỉnh gần giá nhất,
    #     bỏ các đỉnh sát nhau (< 2%) để tránh trùng lặp
    dinh_tren = pv[(pv.loai == "Đỉnh") & (pv.gia > ht * 1.005)].sort_values("gia")
    da_lay = []
    for _, r in dinh_tren.iterrows():
        if da_lay and r.gia < da_lay[-1] * 1.02:
            continue
        da_lay.append(r.gia)
        ung_vien.append([f"Đỉnh cũ {r.time:%d/%m/%Y}", r.gia])
        if len(da_lay) == 4:
            break

    # (b) Đường kháng cự xu hướng
    kc = xh.get("khang_cu")
    if kc and kc["gia_nay"] > ht * 1.005:
        ung_vien.append(["Đường kháng cự xu hướng (hiện tại)", kc["gia_nay"]])

    # (c) Sóng tương đương & Fibonacci mở rộng: cần chuỗi Đáy(T0) – Đỉnh(P0) – Đáy(T1)
    co_song = None
    loai = pv.loai.tolist()
    for i in range(len(pv) - 1, 1, -1):
        if loai[i] == "Đáy" and loai[i - 1] == "Đỉnh" and loai[i - 2] == "Đáy":
            T0, P0, T1 = pv.gia.iloc[i - 2], pv.gia.iloc[i - 1], pv.gia.iloc[i]
            if P0 > T0:
                co_song = (T0, P0, T1)
                for k, ten in ((1.0, "Sóng tương đương AB=CD"), (1.272, "Fibo mở rộng 1.272"),
                               (1.618, "Fibo mở rộng 1.618")):
                    g = T1 + k * (P0 - T0)
                    if g > ht * 1.005:
                        ung_vien.append([ten, g])
            break

    bang = pd.DataFrame(ung_vien, columns=["Phương pháp", "Giá mục tiêu"])
    if len(bang):
        bang = bang.sort_values("Giá mục tiêu").reset_index(drop=True)
        bang["Upside %"] = (bang["Giá mục tiêu"] / ht - 1) * 100
        bang["Vùng 15–20%"] = np.where(bang["Upside %"].between(UPSIDE_MIN, UPSIDE_MAX), "✔", "")
        bang.insert(0, "Khung", ten_khung)

    # Mục tiêu chính: ưu tiên mục tiêu trong vùng 15–20% (gần 17.5% nhất), nếu không có lấy mục tiêu gần nhất
    chinh = None
    if len(bang):
        trong_vung = bang[bang["Vùng 15–20%"] == "✔"]
        if len(trong_vung):
            chinh = trong_vung.iloc[(trong_vung["Upside %"] - (UPSIDE_MIN + UPSIDE_MAX) / 2).abs().argmin()]
        else:
            chinh = bang.iloc[0]

    # Cắt lỗ: dưới đáy gần nhất nằm dưới giá hiện tại 2%; nếu không có → giá − 2×ATR
    day_duoi = pv[(pv.loai == "Đáy") & (pv.gia < ht)]
    if len(day_duoi):
        cat_lo = day_duoi.gia.iloc[-1] * 0.98
    else:
        cat_lo = ht - 2 * df.ATR.iloc[-1]
    return {"bang": bang, "chinh": chinh, "cat_lo": cat_lo, "song": co_song,
            "rr": ((chinh["Giá mục tiêu"] - ht) / (ht - cat_lo)) if chinh is not None and ht > cat_lo else np.nan}


def _cat_len(a, b, n):
    """a vừa cắt lên b trong n nến gần nhất? Trả về số nến trước (0 = nến hiện tại) hoặc None."""
    tren = (a > b).values
    for k in range(n):
        i = len(tren) - 1 - k
        if i >= 1 and tren[i] and not tren[i - 1]:
            return k
    return None


def phan_tich_tin_hieu(df, pv, xh, ten_khung):
    """
    Trả về: danh sách (ký hiệu, nội dung, điểm), tổng điểm, các cờ quan trọng.
    Điểm dương = ủng hộ mua ; điểm âm = bất lợi.
    """
    n = SO_NEN_GAN[ten_khung]
    L = df.iloc[-1]
    ds, co = [], {}

    def them(diem, nd):
        ds.append(("▲" if diem > 0 else "▼" if diem < 0 else "•", nd, diem))

    # Trạng thái MACD
    them(1 if L.MACD > 0 else -1, f"MACD {'trên' if L.MACD > 0 else 'dưới'} mốc 0 "
         f"({'xu hướng tăng' if L.MACD > 0 else 'xu hướng giảm'})")
    them(1 if L.MACD > L.SIGNAL else -1,
         f"MACD {'trên' if L.MACD > L.SIGNAL else 'dưới'} đường tín hiệu")

    k = _cat_len(df.MACD, df.SIGNAL, n)
    co["cat_len_signal"] = k is not None
    if k is not None:
        vi_tri = "DƯỚI mốc 0 → tín hiệu mua sớm" if df.MACD.iloc[-1 - k] < 0 else "trên mốc 0 → tiếp diễn tăng"
        them(2, f"MACD vừa cắt lên đường tín hiệu {k} nến trước ({vi_tri})")
    k0 = _cat_len(df.MACD, pd.Series(0, index=df.index), n)
    co["cat_len_0"] = k0 is not None
    if k0 is not None:
        them(2, f"MACD vừa cắt lên mốc 0 {k0} nến trước → xác nhận xu hướng tăng")
    kx = _cat_len(df.SIGNAL, df.MACD, n)
    if kx is not None:
        them(-2, f"MACD vừa cắt xuống đường tín hiệu {kx} nến trước")

    # Cấu trúc đáy & phân kỳ
    day_ = pv[pv.loai == "Đáy"].tail(2)
    if len(day_) == 2:
        if day_.gia.iloc[1] > day_.gia.iloc[0]:
            them(1, f"Đáy sau ({day_.gia.iloc[1]:.2f}) cao hơn đáy trước ({day_.gia.iloc[0]:.2f})")
        else:
            them(-1, f"Đáy sau ({day_.gia.iloc[1]:.2f}) thấp hơn đáy trước ({day_.gia.iloc[0]:.2f})")
        if day_.gia.iloc[1] < day_.gia.iloc[0] and day_.macd_cuc_tri.iloc[1] > day_.macd_cuc_tri.iloc[0]:
            them(2, "PHÂN KỲ DƯƠNG: giá tạo đáy thấp hơn nhưng MACD tạo đáy cao hơn → lực bán suy yếu")
            co["phan_ky_duong"] = True
    dinh = pv[pv.loai == "Đỉnh"].tail(2)
    if len(dinh) == 2 and dinh.gia.iloc[1] > dinh.gia.iloc[0] and \
            dinh.macd_cuc_tri.iloc[1] < dinh.macd_cuc_tri.iloc[0]:
        them(-2, "PHÂN KỲ ÂM: giá tạo đỉnh cao hơn nhưng MACD tạo đỉnh thấp hơn → lực mua suy yếu")

    # Vị trí giá so với đường xu hướng
    ht = L.close
    ht_line, kc_line = xh.get("ho_tro"), xh.get("khang_cu")
    co["gan_ho_tro"] = co["thung_ho_tro"] = co["pha_khang_cu"] = False
    if ht_line:
        lech = (ht / ht_line["gia_nay"] - 1) * 100
        if lech < -1:
            them(-2, f"Giá đã THỦNG đường hỗ trợ ({ht_line['gia_nay']:.2f})")
            co["thung_ho_tro"] = True
        elif lech <= NGUONG_GAN_HO_TRO:
            them(1, f"Giá đang gần đường hỗ trợ ({ht_line['gia_nay']:.2f}, cách {lech:.1f}%) → vùng mua")
            co["gan_ho_tro"] = True
    if kc_line:
        if ht > kc_line["gia_nay"] and df.close.iloc[-2] <= kc_line["gia_truoc"]:
            vol_ok = L.volume > 1.5 * L.VolMA20 if L.VolMA20 > 0 else False
            them(2 if vol_ok else 1, f"Giá PHÁ đường kháng cự ({kc_line['gia_nay']:.2f})"
                 + (" kèm khối lượng lớn" if vol_ok else " – khối lượng chưa xác nhận"))
            co["pha_khang_cu"] = True
        elif ht > kc_line["gia_nay"]:
            them(1, f"Giá đang nằm trên đường kháng cự cũ ({kc_line['gia_nay']:.2f})")

    # RSI
    if L.RSI > 70:
        them(-1, f"RSI = {L.RSI:.0f}: quá mua, tránh mua đuổi")
    elif L.RSI < 30:
        them(1, f"RSI = {L.RSI:.0f}: quá bán, có thể hồi phục")

    tong = sum(d for _, _, d in ds)
    return ds, tong, co


def xep_loai_khuyen_nghi(upside):
    """Thang khuyến nghị theo tỷ suất sinh lời kỳ vọng."""
    if upside is None or np.isnan(upside):
        return "N/A", "gray"
    if upside >= 15:
        return "MUA", "#2e7d32"
    if upside >= 5:
        return "KHẢ QUAN", "#7cb342"
    if upside >= -5:
        return "NẮM GIỮ", "#f9a825"
    if upside >= -15:
        return "KÉM KHẢ QUAN", "#ef6c00"
    return "BÁN", "#c62828"


def tinh_adx(df, n=14):
    """ADX(n) của Wilder: đo SỨC MẠNH xu hướng (≥ 20–25 là có xu hướng); +DI > −DI → xu hướng tăng."""
    h, l, c = df.high, df.low, df.close
    len_ = h.diff()
    xuong = -l.diff()
    pdm = np.where((len_ > xuong) & (len_ > 0), len_, 0.0)
    mdm = np.where((xuong > len_) & (xuong > 0), xuong, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * pd.Series(mdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi


def supertrend(df, n=10, k=3.5):
    """
    SuperTrend(n, k):
      ATR(n) theo Wilder; dải trên = (H+L)/2 + k×ATR, dải dưới = (H+L)/2 − k×ATR
      Dải cuối cùng chỉ được "kéo" theo hướng xu hướng; giá đóng cửa vượt dải → đổi xu hướng.
    Trả về (đường SuperTrend, hướng: +1 tăng / −1 giảm).
    """
    h, l, c = df.high.values, df.low.values, df.close.values
    tr = np.maximum(h - l, np.maximum(abs(h - np.roll(c, 1)), abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values
    hl2 = (h + l) / 2
    tren, duoi = hl2 + k * atr, hl2 - k * atr
    tren_f, duoi_f = tren.copy(), duoi.copy()
    huong = np.ones(len(c))
    st = np.zeros(len(c))
    for i in range(1, len(c)):
        tren_f[i] = tren[i] if (tren[i] < tren_f[i - 1] or c[i - 1] > tren_f[i - 1]) else tren_f[i - 1]
        duoi_f[i] = duoi[i] if (duoi[i] > duoi_f[i - 1] or c[i - 1] < duoi_f[i - 1]) else duoi_f[i - 1]
        if huong[i - 1] == 1:
            huong[i] = -1 if c[i] < duoi_f[i] else 1
        else:
            huong[i] = 1 if c[i] > tren_f[i] else -1
        st[i] = duoi_f[i] if huong[i] == 1 else tren_f[i]
    st[0] = duoi_f[0]
    return pd.Series(st, index=df.index), pd.Series(huong, index=df.index)



def mo_hinh_nen(df):
    """
    Mô hình nến phiên cuối: ↑ tín hiệu tăng, ↓ tín hiệu giảm, – trung tính. Không có → "".
    Xu hướng trước nến = giá đóng cửa phiên trước so với MA10.
    """
    if df is None or len(df) < 12:
        return ""
    o, h, l, c = (float(df[k].iloc[-1]) for k in ("open", "high", "low", "close"))
    o1, c1 = float(df.open.iloc[-2]), float(df.close.iloc[-2])
    bien = h - l
    if bien <= 0:
        return ""
    than = abs(c - o)
    tren, duoi = h - max(o, c), min(o, c) - l
    giam_truoc = c1 < df.close.iloc[-11:-1].mean()
    trang = c >= o
    if c1 < o1 and trang and o <= c1 and c >= o1 and than > abs(c1 - o1):
        return "Bullish Engulfing ↑"
    if c1 > o1 and not trang and o >= c1 and c <= o1 and than > abs(c1 - o1):
        return "Bearish Engulfing ↓"
    if than >= 0.9 * bien:
        return "White Marubozu ↑" if trang else "Black Marubozu ↓"
    if than <= 0.1 * bien:
        if duoi >= 0.6 * bien:
            return "Dragonfly Doji ↑"
        if tren >= 0.6 * bien:
            return "Gravestone Doji ↓"
        return "Doji –"
    if duoi >= 2 * than and tren <= 0.5 * than:
        return "Hammer ↑" if giam_truoc else "Hanging Man ↓"
    if tren >= 2 * than and duoi <= 0.5 * than:
        return "Inverted Hammer ↑" if giam_truoc else "Shooting Star ↓"
    if than <= 0.3 * bien and tren > than and duoi > than:
        return ("White" if trang else "Black") + " Spinning Top " + ("↑" if giam_truoc else "↓")
    return ""


BIEN_DO_TICH_LUY = 15.0      # % – vùng tích lũy: (cao nhất / thấp nhất − 1) của các phiên trước ≤ ngưỡng này


def so_phien_tich_luy(df, bien_do=BIEN_DO_TICH_LUY, toi_da=250):
    """Số phiên LIỀN TRƯỚC phiên cuối mà giá đi ngang trong biên độ ≤ bien_do % (0 nếu không tích lũy)."""
    if df is None or len(df) < 7:
        return 0
    cao, thap = df.high.values[:-1][::-1], df.low.values[:-1][::-1]      # lùi dần từ phiên trước
    max_c, min_t, n = -np.inf, np.inf, 0
    for c, t in zip(cao[:toi_da], thap[:toi_da]):
        max_c, min_t = max(max_c, c), min(min_t, t)
        if min_t <= 0 or (max_c / min_t - 1) * 100 > bien_do:
            break
        n += 1
    return n


def tich_luy_va_vuot(df, so_ngay=20, ty_le_kl=5.0, gia_tang=5.0, bien_do=BIEN_DO_TICH_LUY):
    """
    Tín hiệu 'Tích lũy và Vượt': giá đi ngang > so_ngay phiên (biên độ ≤ bien_do %), phiên cuối
    tăng > gia_tang % và KL ≥ ty_le_kl × KL TB vùng tích lũy, đóng cửa VƯỢT đỉnh vùng tích lũy.
    → dict {dat, so_phien, ty_le_kl, tang_pct, dinh_nen} (dat=None nếu thiếu dữ liệu).
    """
    if df is None or len(df) < so_ngay + 2:
        return {"dat": None, "so_phien": 0, "ty_le_kl": np.nan, "tang_pct": np.nan, "dinh_nen": np.nan}
    n = so_phien_tich_luy(df, bien_do)
    nen = df.iloc[-1 - max(n, so_ngay):-1]
    L, truoc = df.iloc[-1], df.close.iloc[-2]
    kl_tb = nen.volume.mean()
    ty_le = float(L.volume / kl_tb) if kl_tb > 0 else np.nan
    tang = (float(L.close) / float(truoc) - 1) * 100 if truoc > 0 else np.nan
    dinh = float(nen.high.max())
    dat = bool(n > so_ngay and ty_le > ty_le_kl and tang > gia_tang and L.close > dinh)
    return {"dat": dat, "so_phien": n, "ty_le_kl": ty_le, "tang_pct": tang, "dinh_nen": dinh}
