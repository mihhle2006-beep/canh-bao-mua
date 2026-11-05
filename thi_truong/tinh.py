# -*- coding: utf-8 -*-
"""
TÍNH TOÁN bảng thị trường (hàm thuần – không gọi mạng, test bằng dữ liệu mẫu). Đơn vị ra: giá NGHÌN đồng, GTGD / khối
ngoại / tự doanh TỶ đồng, % là phần trăm.
"""
import numpy as np
import pandas as pd

LECH_GIO = pd.Timedelta(hours=7)


def gio_vn():
    return (pd.Timestamp.now(tz="UTC") + LECH_GIO).tz_localize(None)


def _so(x, mac_dinh=0.0):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return mac_dinh
    return v if np.isfinite(v) else mac_dinh


def chuan_bang(ds):
    """Bảng giá Vietcap [{listingInfo, matchPrice}] → DataFrame theo mã: sàn, loại, tham chiếu / trần / sàn, giá, cao,
    thấp, % thay đổi, KL, GT (tỷ), khối ngoại ròng hôm nay (tỷ), CP niêm yết, có giao dịch chưa."""
    dong = []
    for x in ds:
        li, mp = x.get("listingInfo") or {}, x.get("matchPrice") or {}
        ma = li.get("symbol") or mp.get("symbol")
        if not ma:
            continue
        tc = _so(li.get("refPrice")) or _so(mp.get("referencePrice"))
        gia = _so(mp.get("matchPrice"))
        co_gd = gia > 0
        gia = gia if co_gd else tc
        dong.append({"ma": ma, "san": li.get("board") or "", "loai": li.get("type") or li.get("stockType") or "",
                     "tc": tc, "tran": _so(li.get("ceiling")) or _so(mp.get("ceilingPrice")),
                     "san_gia": _so(li.get("floor")) or _so(mp.get("floorPrice")), "gia": gia,
                     "cao": _so(mp.get("highest")) or gia, "thap": _so(mp.get("lowest")) or gia,
                     "kl": _so(mp.get("accumulatedVolume")), "gt": _so(mp.get("accumulatedValue")) / 1000,
                     "nn": (_so(mp.get("foreignBuyValue")) - _so(mp.get("foreignSellValue"))) / 1e9,
                     "cp": _so(li.get("listedShare")), "co_gd": co_gd})
    B = pd.DataFrame(dong).drop_duplicates("ma").set_index("ma") if dong else pd.DataFrame()
    if len(B):
        B["pt"] = np.where(B["tc"] > 0, (B["gia"] / B["tc"].replace(0, np.nan) - 1) * 100, 0.0)
        B["pt"] = B["pt"].fillna(0.0)
        B["tt"] = np.where(B["co_gd"] & (B["tran"] > 0) & (B["gia"] >= B["tran"]), "tran",
                           np.where(B["co_gd"] & (B["san_gia"] > 0) & (B["gia"] <= B["san_gia"]), "san", ""))
    return B


def nen_phien(nen, ngay=None):
    """Nến gap-chart → DataFrame (giờ VN, o h l c v, gt_luy_ke tỷ); ngay = chỉ giữ phiên đó (mặc định phiên cuối)."""
    if not nen or not nen.get("t"):
        return pd.DataFrame()
    t = pd.to_datetime([int(float(x)) for x in nen["t"]], unit="s") + LECH_GIO
    df = pd.DataFrame({k: pd.to_numeric(pd.Series(nen.get(k)), errors="coerce").to_numpy() for k in "ohlcv"
                       if nen.get(k) is not None}, index=t)
    if nen.get("accumulatedValue") is not None:
        df["gt_luy_ke"] = pd.to_numeric(pd.Series(nen["accumulatedValue"]), errors="coerce").to_numpy() / 1000
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if ngay is None and len(df):
        ngay = df.index[-1].normalize()
    return df[df.index.normalize() == pd.Timestamp(ngay)] if ngay is not None else df


def ho_so_thanh_khoan(nen1, truoc_ngay=None, so_phien=20):
    """Nến 1' VN-Index nhiều phiên → hồ sơ GT luỹ kế: {"phut": [phút từ 9:00], "ty_le": [GT tới phút đó / GT cả phiên,
    TB so_phien phiên], "tb": GT cả phiên TB (tỷ), "ngay": [(ngày, GT cả phiên)]}. Chỉ phiên trước truoc_ngay."""
    if not nen1 or not nen1.get("t") or nen1.get("accumulatedValue") is None:
        return None
    t = pd.to_datetime([int(float(x)) for x in nen1["t"]], unit="s") + LECH_GIO
    g = pd.Series(pd.to_numeric(pd.Series(nen1["accumulatedValue"]), errors="coerce").to_numpy() / 1000, index=t)
    g = g[~g.index.duplicated(keep="last")].sort_index()
    ngay = sorted(set(g.index.normalize()))
    if truoc_ngay is not None:
        ngay = [d for d in ngay if d < pd.Timestamp(truoc_ngay).normalize()]
    ngay = ngay[-so_phien:]
    luoi = np.arange(0, 6 * 60 + 1)                                   # 9:00 → 15:00
    ty_le, cuoi = [], []
    for d in ngay:
        x = g[g.index.normalize() == d]
        if len(x) < 60 or not x.iloc[-1] > 0:
            continue
        phut = ((x.index - d).total_seconds() / 60 - 9 * 60).astype(int)
        s = pd.Series(x.to_numpy(), index=phut).groupby(level=0).last().reindex(luoi).ffill().fillna(0.0)
        ty_le.append((s / x.iloc[-1]).to_numpy())
        cuoi.append((d, float(x.iloc[-1])))
    if not cuoi:
        return None
    return {"phut": luoi.tolist(), "ty_le": np.round(np.mean(ty_le, axis=0), 4).tolist(),
            "tb": float(np.mean([v for _, v in cuoi])), "ngay": [(f"{d:%Y-%m-%d}", round(v, 1)) for d, v in cuoi]}


def ty_le_luc(ho_so, luc):
    """Phần GT cả phiên thường đã khớp tới thời điểm luc (theo hồ sơ); ngoài giờ → 1."""
    if not ho_so:
        return None
    phut = int((luc - luc.normalize()).total_seconds() // 60) - 9 * 60
    if phut >= ho_so["phut"][-1]:
        return 1.0
    if phut < 0:
        return None
    return max(float(ho_so["ty_le"][min(phut, len(ho_so["ty_le"]) - 1)]), 0.02)


def chuoi(gia_tri):
    """Chuỗi khối ngoại: gia_tri mới → cũ (hôm nay đầu tiên). +n = mua ròng n phiên liên tiếp, −n = bán ròng. Hôm nay đúng
    bằng 0 (chưa giao dịch) → bỏ qua hôm nay; phiên cũ bằng 0 → dừng chuỗi."""
    x = [v for v in gia_tri if v is not None]
    if x and x[0] == 0:
        x = x[1:]
    if not x or x[0] == 0:
        return 0
    dau = np.sign(x[0])
    n = 0
    for v in x:
        if np.sign(v) != dau:
            break
        n += 1
    return int(dau * n)


def rsi(c, n=14):
    c = np.asarray(c, dtype=float)
    if len(c) < n + 1:
        return None
    d = np.diff(c)
    t, g = np.clip(d, 0, None), np.clip(-d, 0, None)
    at, ag = t[:n].mean(), g[:n].mean()
    for i in range(n, len(d)):
        at, ag = (at * (n - 1) + t[i]) / n, (ag * (n - 1) + g[i]) / n
    return 100.0 if ag == 0 else float(100 - 100 / (1 + at / ag))


def ky_thuat(ls, gia):
    """ls: {"c": giá đóng cửa điều chỉnh cũ → mới tới phiên trước, "cao250", "thap250"}; gia: giá hiện tại (cùng đơn vị).
    → cờ vượt đỉnh / thủng đáy 52 tuần, cắt lên / xuống MA20 & MA50 HÔM NAY, RSI 14."""
    c = [v for v in (ls or {}).get("c") or [] if v and v > 0]
    out = {"vuot_dinh52": False, "thung_day52": False, "len20": False, "len50": False, "xuong20": False,
           "xuong50": False, "rsi": None}
    if not c or not gia:
        return out
    if ls.get("cao250"):
        out["vuot_dinh52"] = bool(gia > ls["cao250"] and c[-1] <= ls["cao250"])
    if ls.get("thap250"):
        out["thung_day52"] = bool(gia < ls["thap250"] and c[-1] >= ls["thap250"])
    for n in (20, 50):
        if len(c) >= n:
            truoc, nay = np.mean(c[-n:]), np.mean(c[-(n - 1):] + [gia])
            out[f"len{n}"] = bool(c[-1] <= truoc and gia > nay)
            out[f"xuong{n}"] = bool(c[-1] >= truoc and gia < nay)
    r = rsi(c[-60:] + [gia])
    out["rsi"] = round(r, 1) if r is not None else None
    return out


def tom_lich_su(ds, truoc_ngay=None):
    """Lịch sử ngày IQ (mới → cũ) → bản gọn cho lọc mã: 60 giá đóng cửa điều chỉnh (cũ → mới), đỉnh / đáy 250 phiên, KL &
    GT khớp TB 20 phiên, khối ngoại ròng 25 phiên (tỷ, mới → cũ). Chỉ phiên TRƯỚC truoc_ngay (phiên đang chạy tính riêng)."""
    dong = []
    for x in ds or []:
        d = str(x.get("tradingDate") or "")[:10]
        if not d or (truoc_ngay and d >= truoc_ngay):
            continue
        dong.append((d, _so(x.get("closePriceAdjusted")) or _so(x.get("closePrice")),
                     _so(x.get("highestPriceAdjusted")) or _so(x.get("highestPrice")),
                     _so(x.get("lowestPriceAdjusted")) or _so(x.get("lowestPrice")),
                     _so(x.get("totalMatchVolume")), _so(x.get("totalMatchValue")) / 1e9,
                     _so(x.get("foreignNetValueTotal")) / 1e9))
    if not dong:
        return None
    dong.sort(reverse=True)                                           # mới → cũ
    cao = [r[2] for r in dong[:250] if r[2] > 0]
    thap = [r[3] for r in dong[:250] if r[3] > 0]
    return {"ngay": dong[0][0], "c": [r[1] for r in dong[:60]][::-1],
            "cao250": max(cao) if len(cao) >= 120 else None, "thap250": min(thap) if len(thap) >= 120 else None,
            "kl20": float(np.mean([r[4] for r in dong[:20]])), "gt20": float(np.mean([r[5] for r in dong[:20]])),
            "nn": [round(r[6], 3) for r in dong[:25]]}


def mua_chu_dong(ds):
    """Khớp theo bước giá → % KL mua chủ động trong (mua + bán chủ động); không có → None."""
    b = sum(_so(x.get("accumulatedBuyVolume")) for x in ds or [])
    s = sum(_so(x.get("accumulatedSellVolume")) for x in ds or [])
    return round(b / (b + s) * 100, 1) if b + s > 0 else None


def theo_ngay_cafef(ds, khoa_mua, khoa_ban, khoa_ngay):
    """CafeF (mới → cũ) → [(yyyy-mm-dd, ròng tỷ)] mới → cũ."""
    out = []
    for x in ds or []:
        try:
            d = pd.to_datetime(str(x.get(khoa_ngay)), dayfirst=True)
        except (ValueError, TypeError):
            continue
        out.append((f"{d:%Y-%m-%d}", round((_so(x.get(khoa_mua)) - _so(x.get(khoa_ban))) / 1e9, 2)))
    return sorted(out, reverse=True)
