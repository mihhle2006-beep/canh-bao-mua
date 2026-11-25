# -*- coding: utf-8 -*-
"""
VĨ MÔ CHO WEB – tab "Vĩ mô" ở Bảng thị trường (25/11/2026, chủ quỹ: "có nguồn XAUUSD thì làm bộ up giá lên web, biểu đồ,
tab vĩ mô"). Tham khảo, KHÔNG phải tín hiệu mua bán (danh-muc T2 5 vòng: vĩ mô / lãi suất không giúp canh mua bán).
Nguồn (mỗi chuỗi có dự phòng; lỗi hết → đệm cache_du_lieu/vi_mo):
  Vàng thế giới XAU/USD   Stooq xauusd (giá giao ngay, ngày) → yfinance GC=F (COMEX); nến giờ 1 tháng: yfinance GC=F 60';
                          giá ngay: Swissquote (giữa mua–bán)
  Vàng SJC / nhẫn 9999    vang.today (giá CUỐI ngày từng ngày)
  USD/VND · DXY           yfinance VND=X · DX-Y.NYB; tỷ giá Vietcombank (chuyển khoản / bán) cho thẻ
  Lãi suất VN             thi_truong/lai_suat (chép danh-muc ptcp/lai_suat_vn): TPCP 1N / 10N HNX (chính thức, từ 2014), lãi điều hành / liên ngân hàng / lạm
                          phát (TradingView ECONOMICS, gốc NHNN / TCTK – theo tháng)
  Mỹ                      NY Fed (Fed funds thực tế, trần mục tiêu), Bộ Tài chính Mỹ (lợi suất 2N / 10N, lợi suất thực 10N)
Giá trực tiếp trên trang: thử nguồn cho phép trình duyệt gọi thẳng (CORS) → ghi vào "song"; không có thì dùng số lúc dựng.
→ docs/vi_mo/du_lieu.json. Chạy: python -m thi_truong.vi_mo_web --ra docs/vi_mo
"""
import argparse
import io
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

VN = timezone(timedelta(hours=7))
DEM = os.path.join("cache_du_lieu", "vi_mo")
LUONG_OZ = 37.5 / 31.1034768                       # 1 lượng = 37,5 g; 1 oz troy = 31,1034768 g
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"}
GOC_WEB = "https://mihhle2006-beep.github.io"
SONG = [("https://api.gold-api.com/price/XAU", "gold_api"),
        ("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", "swissquote")]
NHOM = {"vang": "Vàng", "ls_vn": "Lãi suất Việt Nam", "my": "Mỹ", "ty_gia": "Tỷ giá"}


# ------------------------------------------------------------------ tải
def _get(url, **kw):
    import requests
    h = {**UA, **kw.pop("headers", {})}
    r = requests.get(url, headers=h, timeout=kw.pop("timeout", 40), **kw)
    r.raise_for_status()
    return r


def _dem(ten, s=None):
    """Ghi (s có) / đọc đệm 1 chuỗi."""
    os.makedirs(DEM, exist_ok=True)
    f = os.path.join(DEM, ten + ".csv")
    if s is not None:
        (s.to_frame("c") if isinstance(s, pd.Series) else s).to_csv(f)
        return s
    if not os.path.exists(f):
        return None
    d = pd.read_csv(f, index_col=0, parse_dates=True)
    return d["c"] if list(d.columns) == ["c"] else d


def _yf(ma, tu="2010-01-01", khung="1d", ky=None):
    import contextlib

    import yfinance as yf
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        t = yf.Ticker(ma)
        df = t.history(period=ky, interval=khung, auto_adjust=False) if ky else t.history(start=tu, interval=khung,
                                                                                            auto_adjust=False)
    if df is None or not len(df):
        return None
    df.columns = [c.lower() for c in df.columns]
    idx = pd.DatetimeIndex(df.index)
    df.index = idx.tz_convert("UTC").tz_localize(None) if idx.tz is not None else idx
    return df[["open", "high", "low", "close"]].astype(float).dropna(subset=["close"])


def xau_ngay(tu="2010-01-01"):
    """XAU/USD theo ngày → (DataFrame open/high/low/close, nguồn)."""
    try:
        txt = _get(f"https://stooq.com/q/d/l/?s=xauusd&d1={pd.Timestamp(tu):%Y%m%d}&i=d").text
        if not txt[:40].lower().startswith("date"):
            print(f"  ⚠ Stooq không trả CSV: {txt[:60]!r}")
        else:
            df = pd.read_csv(io.StringIO(txt))
            df.columns = [c.strip().lower() for c in df.columns]
            df = df.set_index(pd.to_datetime(df["date"]))[["open", "high", "low", "close"]].astype(float)
            if len(df) > 500:
                return df, "Stooq XAU/USD (giao ngay)"
    except Exception as e:                                            # noqa: BLE001 – nguồn sau
        print(f"  ⚠ Stooq: {type(e).__name__} {str(e)[:60]}")
    df = _yf("GC=F", tu)
    if df is None:
        raise ValueError("không lấy được XAU/USD")
    return df.set_index(df.index.normalize()), "COMEX GC=F (hợp đồng tương lai, yfinance)"


def xau_gio():
    df = _yf("GC=F", khung="60m", ky="1mo")
    return df, "COMEX GC=F 60' (yfinance)"


def xau_giao_ngay():
    j = _get(SONG[1][0]).json()
    p = j[0]["spreadProfilePrices"][0]
    return (float(p["bid"]) + float(p["ask"])) / 2, datetime.fromtimestamp(j[0]["ts"] / 1000, VN)


def vang_today(ma, days=1500):
    """vang.today → DataFrame mua / ban (triệu đồng / lượng) theo ngày."""
    j = _get(f"https://www.vang.today/api/prices?type={ma}&days={days}").json()
    hang = []
    for h in j.get("history") or []:
        g = (h.get("prices") or {}).get(ma) or {}
        if g.get("buy") and g.get("sell"):
            hang.append((pd.Timestamp(h["date"]), float(g["buy"]) / 1e6, float(g["sell"]) / 1e6))
    return pd.DataFrame(hang, columns=["ngay", "mua", "ban"]).set_index("ngay").sort_index()


def vcb_usd():
    import re
    txt = _get("https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx").text
    m = re.search(r'CurrencyCode="USD"[^>]*Buy="([\d,.]+)"[^>]*Transfer="([\d,.]+)"[^>]*Sell="([\d,.]+)"', txt)
    if not m:
        raise ValueError("VCB không có USD")
    return {k: float(v.replace(",", "")) for k, v in zip(("mua", "ck", "ban"), m.groups())}


def thuc_my_10n(tu=2015):
    """Lợi suất thực TIPS 10 năm – Bộ Tài chính Mỹ (CSV từng năm)."""
    ds = []
    for y in range(tu, pd.Timestamp.today().year + 1):
        d = pd.read_csv(io.StringIO(_get(
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
            f"{y}/all?type=daily_treasury_real_yield_curve&field_tdr_date_value={y}&page&_format=csv", timeout=60).text))
        c = next((c for c in d.columns if c.strip().upper() in ("10 YR", "10 YEAR")), None)
        if c is not None:
            ds.append(pd.Series(pd.to_numeric(d[c], errors="coerce").values, index=pd.to_datetime(d.iloc[:, 0])))
    s = pd.concat(ds).dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def kiem_song(lay=None):
    """Nguồn giá XAU trực tiếp cho TRÌNH DUYỆT (phải cho phép gọi từ github.io – CORS) → {"url", "kieu", "gia"} | None."""
    for url, kieu in SONG:
        try:
            r = (lay or _get)(url, headers={"Origin": GOC_WEB}, timeout=15)
            acao = r.headers.get("Access-Control-Allow-Origin", "")
            if acao not in ("*", GOC_WEB):
                print(f"  giá trực tiếp {kieu}: không cho trình duyệt gọi (CORS '{acao}')")
                continue
            j = r.json()
            gia = float(j["price"]) if kieu == "gold_api" else \
                (float(j[0]["spreadProfilePrices"][0]["bid"]) + float(j[0]["spreadProfilePrices"][0]["ask"])) / 2
            if 500 < gia < 20000:
                return {"url": url, "kieu": kieu, "gia": round(gia, 2)}
        except Exception as e:                                        # noqa: BLE001 – thử nguồn sau
            print(f"  giá trực tiếp {kieu}: {type(e).__name__} {str(e)[:60]}")
    return None


# ------------------------------------------------------------------ gom
def _thu(ten, ham, *a, **k):
    """Gọi ham; lỗi → đệm (đọc) – thành công → ghi đệm. → (kết quả | None, nguồn ghi chú | lỗi)."""
    try:
        kq = ham(*a, **k)
        if isinstance(kq, tuple):
            x, nguon = kq
        else:
            x, nguon = kq, None
        if x is not None and len(x):
            _dem(ten, x)
            return x, nguon
        raise ValueError("rỗng")
    except Exception as e:                                            # noqa: BLE001 – nguồn lỗi → đệm
        print(f"  ⚠ {ten}: {type(e).__name__} {str(e)[:80]} → dùng đệm")
        x = _dem(ten)
        return x, ("đệm (nguồn lỗi)" if x is not None else None)


def tai_tat_ca():
    """→ (dict chuỗi thô, dict nguồn, dict phụ)."""
    S, N, P = {}, {}, {}
    xd, n = _thu("xau_ngay", xau_ngay)
    if xd is not None:
        S["xau_nen"], N["xau"] = xd, n
    xg, n = _thu("xau_gio", xau_gio)
    if xg is not None:
        S["xau_gio"], N["xau_gio"] = xg, n
    for k, ma in (("sjc", "SJL1L10"), ("nhan", "SJ9999")):
        x, _ = _thu("vt_" + k, vang_today, ma)
        if x is not None:
            S[k], N[k] = x, "vang.today"
    for k, ma, ten in (("usdvnd", "VND=X", "Yahoo VND=X"), ("dxy", "DX-Y.NYB", "Yahoo DX-Y.NYB")):
        x, _ = _thu(k, lambda m=ma: _yf(m)["close"])
        if x is not None:
            S[k], N[k] = x, ten
    x, _ = _thu("us_thuc10", thuc_my_10n)
    if x is not None:
        S["us_thuc10"], N["us_thuc10"] = x, "Bộ Tài chính Mỹ (TIPS)"
    try:
        from thi_truong import lai_suat as LS
        ls, nguon = LS.tai_tat_ca(os.path.join(DEM, "lai_suat"))
        for k, kk in (("vn_1n", "VN01Y"), ("vn_10n", "VN10Y"), ("vn_dh", "ECONOMICS:VNINTR"), ("vn_lnh", "ECONOMICS:VNINBR"),
                      ("vn_cpi", "ECONOMICS:VNIRYY"), ("us_ff", "US_EFFR"), ("us_tran", "US_TRAN"), ("us_2n", "US_2Y"),
                      ("us_10n", "US_10Y")):
            if kk in ls:
                S[k], N[k] = ls[kk], nguon.get(kk, "")
    except Exception as e:                                            # noqa: BLE001 – lãi suất lỗi không hỏng phần vàng
        print(f"  ⚠ lãi suất: {type(e).__name__} {str(e)[:80]}")
    try:
        P["gia_ngay"], P["gia_ngay_luc"] = xau_giao_ngay()
    except Exception as e:                                            # noqa: BLE001
        print(f"  ⚠ Swissquote: {type(e).__name__} {str(e)[:60]}")
    try:
        P["vcb"] = vcb_usd()
    except Exception as e:                                            # noqa: BLE001
        print(f"  ⚠ Vietcombank: {type(e).__name__} {str(e)[:60]}")
    P["song"] = kiem_song()
    return S, N, P


# ------------------------------------------------------------------ dựng JSON (thuần – test được không mạng)
def _gon(s, nam_ngay=3, le=3, tu="2010-01-01"):
    """Series → [[ngày, giá trị]]: theo NGÀY 3 năm gần nhất, theo TUẦN (giá cuối tuần) trước đó – trang nhẹ."""
    s = pd.Series(s).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s[s.index >= pd.Timestamp(tu)]
    if not len(s):
        return []
    moc = s.index[-1] - pd.DateOffset(years=nam_ngay)
    cu, moi = s[s.index < moc], s[s.index >= moc]
    if len(cu) > 400:
        cu = cu.groupby(cu.index.to_period("W-FRI")).last()
        cu.index = cu.index.to_timestamp(how="end").normalize()
        cu = cu[cu.index < moc]                                          # tuần cuối lấn sang phần theo ngày → bỏ
    s = pd.concat([cu, moi]).sort_index()
    s = s[~s.index.duplicated(keep="last")]                             # biểu đồ cần thời gian tăng dần, không trùng
    return [[f"{d:%Y-%m-%d}", round(float(v), le)] for d, v in s.items()]


def _the(k, nhom, ten, s, dv, nguon, ky=1, kieu="%", le=2, ten_ky="phiên trước"):
    s = pd.Series(s).dropna()
    if not len(s):
        return None
    v = float(s.iloc[-1])
    q = float(s.iloc[-1 - ky]) if len(s) > ky else None
    doi = None if q is None else (round((v / q - 1) * 100, 2) if kieu == "%" else round(v - q, 3))
    return {"k": k, "nhom": nhom, "ten": ten, "gia": round(v, le), "dv": dv, "doi": doi, "kieu_doi": kieu,
            "ky": ten_ky, "ngay": f"{s.index[-1]:%Y-%m-%d}", "nguon": nguon}


def dung(S, N, P, bay_gio=None):
    """Chuỗi thô → JSON cho trang."""
    bay_gio = bay_gio or datetime.now(VN)
    C, T = {}, []

    def them(k, nhom, ten, s, dv, le=3, **kt):
        if s is None or not len(pd.Series(s).dropna()):
            return
        C[k] = {"ten": ten, "dv": dv, "nhom": nhom, "nguon": N.get(k, ""), "d": _gon(s, le=le)}
        t = _the(k, nhom, ten, s, dv, N.get(k, ""), **kt)
        if t:
            T.append(t)
    xd = S.get("xau_nen")
    xau = xd["close"] if xd is not None else None
    usd = S.get("usdvnd")
    if xau is not None:
        # % thay đổi: theo CHÍNH chuỗi ngày (cùng nguồn – COMEX GC=F khi Stooq chặn); giá trên thẻ: giá giao ngay lúc dựng
        # (Swissquote) – không lấy giao ngay chia cho đóng cửa hợp đồng tương lai (lệch cơ sở ~0,5–1 %)
        them("xau", "vang", "Vàng thế giới XAU/USD", xau, "USD/oz", le=2)
        if P.get("gia_ngay"):
            T[-1].update(gia=round(float(P["gia_ngay"]), 2), luc=P["gia_ngay_luc"].strftime("%H:%M %d/%m"),
                         ky="phiên trước (" + ("COMEX" if "GC=F" in N.get("xau", "") else "giao ngay") + ")")
    for k, ten in (("sjc", "Vàng miếng SJC – bán"), ("nhan", "Nhẫn 9999 – bán")):
        x = S.get(k)
        if x is not None and len(x):
            them(k + "_ban", "vang", ten, x["ban"], "tr.đ/lượng", le=2)
            if k == "sjc":
                C["sjc_mua"] = {"ten": "Vàng miếng SJC – mua", "dv": "tr.đ/lượng", "nhom": "vang", "nguon": "vang.today",
                                "d": _gon(x["mua"], le=2)}
    if xau is not None and usd is not None:
        u = pd.Series(usd)
        u = u[(u > 15000) & (u < 60000)]
        tg = (xau * u.reindex(xau.index.union(u.index)).ffill().reindex(xau.index) * LUONG_OZ / 1e6).dropna()
        N["tg_vnd"] = "XAU/USD × USD/VND × 37,5 / 31,1035"
        them("tg_vnd", "vang", "Thế giới quy đổi", tg, "tr.đ/lượng", le=2)
        sjc = S.get("sjc")
        if sjc is not None and len(sjc):
            b = sjc["ban"]
            ch = (b - tg.reindex(b.index.union(tg.index)).ffill().reindex(b.index)).dropna()
            N["chenh"] = "SJC bán − thế giới quy đổi"
            them("chenh", "vang", "Chênh SJC – thế giới", ch, "tr.đ/lượng", le=2, kieu="đ")
    for k, nhom, ten, dv in (("usdvnd", "ty_gia", "USD/VND (thị trường)", "đồng"), ("dxy", "ty_gia", "Chỉ số USD (DXY)", "điểm")):
        them(k, nhom, ten, S.get(k), dv, le=2)
    for k, ten in (("vn_dh", "Lãi điều hành NHNN"), ("vn_lnh", "Liên ngân hàng"), ("vn_1n", "TPCP 1 năm"),
                   ("vn_10n", "TPCP 10 năm"), ("vn_cpi", "Lạm phát CPI (so cùng kỳ)")):
        thang = k in ("vn_dh", "vn_lnh", "vn_cpi")
        them(k, "ls_vn", ten, S.get(k), "%/năm" if k != "vn_cpi" else "%", kieu="đ",
             ten_ky="tháng trước" if thang else "phiên trước")
    for k, ten in (("us_ff", "Fed funds thực tế"), ("us_tran", "Trần mục tiêu Fed"), ("us_2n", "Lợi suất Mỹ 2 năm"),
                   ("us_10n", "Lợi suất Mỹ 10 năm"), ("us_thuc10", "Lợi suất thực Mỹ 10 năm (TIPS)")):
        them(k, "my", ten, S.get(k), "%/năm", kieu="đ")
    nen = []
    if xd is not None:
        x = xd[xd.index >= xd.index[-1] - pd.DateOffset(years=5)]
        nen = [[f"{d:%Y-%m-%d}", *[round(float(v), 2) for v in r]] for d, r in x[["open", "high", "low", "close"]].iterrows()]
    gio = []
    xg = S.get("xau_gio")
    if xg is not None and len(xg):
        gio = [[int(pd.Timestamp(d).timestamp()), *[round(float(v), 2) for v in r]]
               for d, r in xg[["open", "high", "low", "close"]].iterrows()]
    vcb = P.get("vcb")
    if vcb:
        T.append({"k": "vcb", "nhom": "ty_gia", "ten": "USD/VND Vietcombank (bán)", "gia": vcb["ban"], "dv": "đồng",
                  "doi": None, "kieu_doi": "%", "ky": "", "ngay": f"{bay_gio:%Y-%m-%d}",
                  "nguon": f"Vietcombank – mua {vcb['mua']:,.0f} · chuyển khoản {vcb['ck']:,.0f}".replace(",", ".")})
    return {"cap_nhat": f"{bay_gio:%Y-%m-%d %H:%M}", "nhom": NHOM, "the": T, "chuoi": C, "xau_nen": nen, "xau_gio": gio,
            "nguon_gio": N.get("xau_gio", ""), "song": P.get("song"),
            "ghi_chu": "Tham khảo – không phải tín hiệu mua bán. Lãi suất / vĩ mô đã kiểm (backtest): không giúp canh mua bán "
                       "cổ phiếu. Số liệu tháng (lãi điều hành, liên ngân hàng, lạm phát) công bố trễ 1–2 tháng."}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--ra", default=os.path.join("docs", "vi_mo"))
    a = p.parse_args(argv)
    S, N, P = tai_tat_ca()
    kq = dung(S, N, P)
    os.makedirs(a.ra, exist_ok=True)
    with open(os.path.join(a.ra, "du_lieu.json"), "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Vĩ mô: {len(kq['the'])} thẻ, {len(kq['chuoi'])} chuỗi, nến ngày {len(kq['xau_nen'])}, nến giờ {len(kq['xau_gio'])},"
          f" giá trực tiếp: {(kq['song'] or {}).get('kieu') or 'không'} · "
          + " · ".join(f"{k}: {v}" for k, v in N.items()))
    for t in kq["the"]:                                              # số công khai – soát nhanh trong log
        print(f"  {t['ten']}: {t['gia']} {t['dv']}" + (f" ({t['doi']:+}{'%' if t['kieu_doi'] == '%' else ''})"
                                                       if t.get("doi") is not None else "") + f" · {t['ngay']}")
    thieu = [k for k in ("xau", "sjc_ban", "vn_10n", "us_10n") if k not in kq["chuoi"]]
    if len(thieu) >= 3:
        print(f"::error::Vĩ mô thiếu gần hết chuỗi chính: {thieu}")
        return 1
    if thieu:
        print(f"::warning::Vĩ mô thiếu: {thieu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
