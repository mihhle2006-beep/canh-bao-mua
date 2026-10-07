# -*- coding: utf-8 -*-
"""
VÙNG MUA ĐIỀU CHỈNH (cho mã CHƯA nắm giữ) + BACKTEST POINT-IN-TIME CỦA CHÍNH QUY TẮC NÀY.

Ý tưởng: không mua đuổi ở giá hiện tại mà đặt lệnh CHỜ ở nơi nhiều hỗ trợ trùng nhau, và chỉ mua khi giá
về vùng VÀ có nến xác nhận bật lên. Không dự báo chắc chắn giá sẽ bật – xác suất bật được đo trên lịch sử mã.

  1. Mức hỗ trợ (chỉ dùng dữ liệu ĐẾN phiên đang xét, không nhìn trước):
       EMA20 ngày · EMA50 ngày · MA20 tuần · Fibonacci 38.2 / 50 / 61.8% của nhịp tăng gần nhất
       (đáy → đỉnh trong VM_SO_PHIEN_NHIP phiên) · đáy ngày đã xác nhận gần nhất · POC volume profile.
  2. Vùng mua = cửa sổ rộng VM_DO_RONG_ATR×ATR chứa NHIỀU mức nhất (≥ VM_SO_MUC_TOI_THIEU mức khác loại);
     hoà → vùng gần giá hơn.
  3. Kích hoạt: giá chạm vùng (low ≤ cận trên) rồi có nến XÁC NHẬN (đóng cửa > đỉnh phiên trước, nến tăng,
     đóng cửa ≥ cận dưới) trong VM_CHO_PHIEN phiên → mua giá mở cửa phiên sau (không mua nếu khoá trần
     hoặc mở cửa đã vượt cận trên + 1×ATR – không đuổi giá).
  4. Vô hiệu: đóng cửa < cận dưới − 0.5×ATR trước khi có xác nhận. Cắt lỗ = cận dưới − VM_STOP_ATR×ATR.
     Chốt lời / thoát: dùng ĐÚNG bộ mô phỏng thoát của Phần I (T+2, trần/sàn, phí, trượt giá).
  5. Bối cảnh: chỉ thiết lập khi MACD tuần > Signal (giống quyền phủ quyết của công cụ).
"""
import numpy as np
import pandas as pd

from . import cau_hinh as cfg
from .cau_hinh import BO_QUA_DAU, LO_CUNG_PCT, RR_NGUONG, STOP_ATR_MAX, STOP_ATR_MIN
from .thong_ke import _chi_phi, _co_khoa
from .bo_sung import mo_phong_thoat, tong_hop_lenh

VM_SO_PHIEN_NHIP = getattr(cfg, "VM_SO_PHIEN_NHIP", 120)       # cửa sổ tìm nhịp tăng & volume profile
VM_DO_RONG_ATR = getattr(cfg, "VM_DO_RONG_ATR", 1.0)           # độ rộng tối đa của vùng (×ATR)
VM_SO_MUC_TOI_THIEU = getattr(cfg, "VM_SO_MUC_TOI_THIEU", 2)   # số mức hỗ trợ trùng nhau tối thiểu
VM_CHO_PHIEN = getattr(cfg, "VM_CHO_PHIEN", 20)                # chờ tối đa bao nhiêu phiên để giá về vùng + xác nhận
VM_STOP_ATR = getattr(cfg, "VM_STOP_ATR", 1.0)                 # cắt lỗ dưới cận dưới vùng
VM_SAU_TOI_DA_PCT = getattr(cfg, "VM_SAU_TOI_DA_PCT", 15.0)    # chỉ xét hỗ trợ trong −15% so với giá
_PIVOT = 5                                                    # đáy xác nhận: thấp nhất ±5 phiên


def _chuan_bi(d_ngay, d_tuan):
    """Các chuỗi dùng chung (đều nhân quả: giá trị tại phiên i chỉ dùng dữ liệu ≤ i)."""
    c = d_ngay.close
    ema20 = c.ewm(span=20, adjust=False).mean().values
    ema50 = c.ewm(span=50, adjust=False).mean().values
    ma20w = d_tuan.close.rolling(20, min_periods=10).mean().reindex(d_ngay.index, method="ffill").values
    tuan_ok = (d_tuan.MACD > d_tuan.SIGNAL).astype(float).reindex(d_ngay.index, method="ffill").fillna(0).values > 0
    lo = d_ngay.low.values
    w = 2 * _PIVOT + 1
    la_day = (pd.Series(lo).rolling(w, center=True).min().values == lo)   # đáy tại k, xác nhận ở k + _PIVOT
    return {"o": d_ngay.open.values, "h": d_ngay.high.values, "l": lo, "c": c.values, "v": d_ngay.volume.values,
            "atr": d_ngay.ATR.values, "ema20": ema20, "ema50": ema50, "ma20w": ma20w, "tuan_ok": tuan_ok,
            "la_day": np.nan_to_num(la_day).astype(bool)}


def _poc(h, l, c, v, so_bin=24):
    gia = (h + l + c) / 3
    if not len(gia) or l.min() >= h.max():
        return np.nan
    bins = np.linspace(l.min(), h.max(), so_bin + 1)
    kl, _ = np.histogram(gia, bins=bins, weights=v)
    i = int(np.argmax(kl))
    return (bins[i] + bins[i + 1]) / 2


def tinh_vung(x, i):
    """Vùng mua tại phiên i (chỉ dùng dữ liệu ≤ i). Trả None nếu không có cụm hỗ trợ đủ dày."""
    atr, ht = x["atr"][i], x["c"][i]
    if not (atr == atr and atr > 0) or i < VM_SO_PHIEN_NHIP:
        return None
    a = i - VM_SO_PHIEN_NHIP + 1
    muc = [("EMA20 ngày", x["ema20"][i]), ("EMA50 ngày", x["ema50"][i]), ("MA20 tuần", x["ma20w"][i])]
    h, l = x["h"][a:i + 1], x["l"][a:i + 1]
    k_dinh = int(np.argmax(h))
    dinh = h[k_dinh]
    day = l[:k_dinh + 1].min() if k_dinh > 0 else np.nan
    if day == day and dinh - day >= 2 * atr:
        for f in (0.382, 0.5, 0.618):
            muc.append((f"Fibo {f * 100:.1f}%", dinh - f * (dinh - day)))
    xn = np.where(x["la_day"][a:max(a, i - _PIVOT + 1)])[0]
    if len(xn):
        muc.append(("Đáy ngày xác nhận", x["l"][a + xn[-1]]))
    muc.append(("POC khối lượng", _poc(h, l, x["c"][a:i + 1], x["v"][a:i + 1])))
    can_duoi = max(ht * (1 - VM_SAU_TOI_DA_PCT / 100), ht - 5 * atr)
    can_tren = ht + 0.3 * atr
    muc = sorted([(t, float(p)) for t, p in muc if p == p and can_duoi <= p <= can_tren], key=lambda m: m[1])
    tot = None
    for k in range(len(muc)):
        cum = [m for m in muc[k:] if m[1] <= muc[k][1] + VM_DO_RONG_ATR * atr]
        loai = {t.split(" ")[0] for t, _ in cum}          # Fibo 38.2/50/61.8 tính là MỘT loại
        diem = (len(loai), len(cum), cum[-1][1])
        if tot is None or diem >= tot[0]:
            tot = (diem, cum)
    if tot is None or tot[0][0] < VM_SO_MUC_TOI_THIEU:
        return None
    cum = tot[1]
    lo_v, hi_v = cum[0][1], cum[-1][1]
    if hi_v - lo_v < 0.4 * atr:                             # vùng quá hẹp → nới đều 2 phía
        g = (lo_v + hi_v) / 2
        lo_v, hi_v = g - 0.2 * atr, g + 0.2 * atr
    return {"lo": lo_v, "hi": hi_v, "muc": cum, "so_loai": tot[0][0], "dinh_nhip": dinh, "atr": atr,
            "stop": lo_v - VM_STOP_ATR * atr}


def _xac_nhan(x, j):
    return x["c"][j] > x["h"][j - 1] and x["c"][j] > x["o"][j]


def _stop_chuan(vao, atr_i):
    stop = max(vao - STOP_ATR_MAX * atr_i, vao * (1 - LO_CUNG_PCT / 100))
    return vao - STOP_ATR_MIN * atr_i if vao - stop < STOP_ATR_MIN * atr_i else stop


def backtest_vung_mua(d_ngay, d_tuan, n_giu, thoat="co_dinh"):
    """
    Duyệt lịch sử theo thời gian thực. Tại phiên i có THIẾT LẬP khi: MACD tuần > Signal, có vùng mua và giá đóng
    cửa NẰM TRÊN vùng (phải chờ điều chỉnh). Từ đó:
      • "vung"    : chờ tối đa VM_CHO_PHIEN phiên để giá về vùng + nến xác nhận → mua; cắt lỗ dưới vùng.
      • "mua_ngay": đối chứng – mua luôn giá mở cửa phiên i+1 với cắt lỗ chuẩn của công cụ.
    Hai nhánh dùng cùng bộ mô phỏng thoát 'thoat' và chạy độc lập (mỗi nhánh không chồng lệnh).
    """
    x = _chuan_bi(d_ngay, d_tuan)
    o, h, l, c, atr = x["o"], x["h"], x["l"], x["c"], x["atr"]
    tran_khoa, san_khoa = _co_khoa(d_ngay)
    i0 = max(BO_QUA_DAU + 30, VM_SO_PHIEN_NHIP)
    n = len(c)
    cache = {}

    def vung(i):
        if i not in cache:
            cache[i] = tinh_vung(x, i) if x["tuan_ok"][i] else None
        return cache[i]

    def thiet_lap(i):
        v = vung(i)
        return v if v is not None and c[i] > v["hi"] else None

    # ---- nhánh CHỜ VÙNG
    lenh, so_tl, so_ve, so_hong, so_1r, i = [], 0, 0, 0, 0, i0
    while i < n - 2:
        v = thiet_lap(i)
        if v is None:
            i += 1
            continue
        so_tl += 1
        cham, j_mua, ket_thuc = False, None, min(i + VM_CHO_PHIEN, n - 2)
        for j in range(i + 1, ket_thuc + 1):
            if c[j] < v["lo"] - 0.5 * v["atr"]:
                so_hong += 1 if cham else 0
                ket_thuc = j
                break
            if not cham and l[j] <= v["hi"]:
                cham = True
                so_ve += 1
            if cham and c[j] >= v["lo"] and _xac_nhan(x, j):
                if not tran_khoa[j + 1] and o[j + 1] <= v["hi"] + v["atr"]:
                    j_mua = j
                ket_thuc = j
                break
        if j_mua is None:
            i = ket_thuc + 1
            continue
        vao = o[j_mua + 1]
        stop = min(v["stop"], vao - STOP_ATR_MIN * atr[j_mua] * 0.5)
        R = vao - stop
        tp = vao + RR_NGUONG * R
        k_r = next((k for k in range(j_mua + 1, min(j_mua + 1 + n_giu, n)) if l[k] <= stop or h[k] >= vao + R),
                   None)
        so_1r += 1 if (k_r is not None and h[k_r] >= vao + R and l[k_r] > stop) else 0
        jb, ra, ly_do = mo_phong_thoat(j_mua, vao, stop, tp, o, h, l, c, atr[j_mua], san_khoa, n_giu, thoat)
        lenh.append([d_ngay.index[j_mua + 1], vao, d_ngay.index[jb], ra, (ra / vao - 1) * 100 - _chi_phi(),
                     jb - j_mua, ly_do])
        i = jb + 1
    kq_vung = tong_hop_lenh(lenh, d_ngay, c, i0)
    kq_vung.update({"so_thiet_lap": so_tl, "so_ve_vung": so_ve, "so_thung_vung": so_hong,
                    "xs_ve_vung": so_ve / so_tl * 100 if so_tl else np.nan,
                    "xs_1R": so_1r / len(lenh) * 100 if lenh else np.nan})

    # ---- nhánh MUA NGAY (đối chứng, cùng điều kiện thiết lập)
    lenh, i = [], i0
    while i < n - 2:
        if thiet_lap(i) is None or tran_khoa[i + 1]:
            i += 1
            continue
        vao = o[i + 1]
        stop = _stop_chuan(vao, atr[i])
        tp = vao + RR_NGUONG * (vao - stop)
        jb, ra, ly_do = mo_phong_thoat(i, vao, stop, tp, o, h, l, c, atr[i], san_khoa, n_giu, thoat)
        lenh.append([d_ngay.index[i + 1], vao, d_ngay.index[jb], ra, (ra / vao - 1) * 100 - _chi_phi(),
                     jb - i, ly_do])
        i = jb + 1
    return {"vung": kq_vung, "mua_ngay": tong_hop_lenh(lenh, d_ngay, c, i0)}


def vung_mua_hien_tai(d_ngay, d_tuan):
    """Vùng mua tại phiên cuối + trạng thái (chờ về vùng / trong vùng chờ xác nhận / đã xác nhận)."""
    x = _chuan_bi(d_ngay, d_tuan)
    i = len(x["c"]) - 1
    v = tinh_vung(x, i)
    if v is None:
        return None
    ht = x["c"][i]
    gan_day_cham = (x["l"][max(0, i - 4):i + 1] <= v["hi"]).any()
    if ht > v["hi"] and not gan_day_cham:
        tt = "CHỜ giá điều chỉnh về vùng"
    elif gan_day_cham and ht >= v["lo"] and _xac_nhan(x, i):
        tt = "ĐÃ XÁC NHẬN bật lên trong vùng → có thể mua phiên tới (nếu mở cửa ≤ cận trên + 1×ATR)"
    else:
        tt = "Giá đang TRONG vùng → chờ nến xác nhận (đóng cửa > đỉnh phiên trước, nến tăng)"
    g = (v["lo"] + v["hi"]) / 2
    mt = v["dinh_nhip"] if v["dinh_nhip"] > g * 1.01 else g + RR_NGUONG * (g - v["stop"])
    v.update({"gia": ht, "trang_thai": tt, "tuan_ok": bool(x["tuan_ok"][i]), "giua": g, "muc_tieu": mt,
              "rr": (mt - g) / (g - v["stop"]) if g > v["stop"] else np.nan,
              "cach_gia_pct": (v["hi"] / ht - 1) * 100})
    return v
