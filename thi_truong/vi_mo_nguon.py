# -*- coding: utf-8 -*-
"""
DÒ NGUỒN cho tab Vĩ mô (25/11/2026, chủ quỹ: "kiếm thêm nguồn"): thử từng nguồn ứng viên trên máy GitHub → in số điểm,
khoảng ngày, giá trị cuối, và SO CHÉO các nguồn cùng một chuỗi (tương quan lợi suất ngày, lệch trung vị %). Không ghi gì.
Chạy: python -m thi_truong.vi_mo_nguon   (workflow Vi mo, ô "thu_nguon")
"""
import io
import json
import re
import time

import numpy as np
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"}


def _get(url, **kw):
    import requests
    r = requests.get(url, headers={**UA, **kw.pop("headers", {})}, timeout=kw.pop("timeout", 40), **kw)
    r.raise_for_status()
    return r


def tv(sym, khung="1D", n=5000):
    """TradingView (không đăng nhập) → Series giá đóng cửa; khung phút giữ giờ (không gộp ngày)."""
    from thi_truong import lai_suat as LS
    if khung == "1D" or khung == "1M" or khung == "1W":
        df, loi = LS.tv_lich_su(sym, khung, n)
        if df is None:
            raise ValueError(loi[:120])
        return df["c"]
    # khung giờ / phút: đọc thô, giữ mốc thời gian
    import random
    import string

    from websocket import create_connection
    ws = create_connection("wss://data.tradingview.com/socket.io/websocket",
                           header=["Origin: https://data.tradingview.com"], timeout=30)

    def goi(m, p):
        t = json.dumps({"m": m, "p": p}, separators=(",", ":"))
        ws.send(f"~m~{len(t)}~m~{t}")
    cs = "cs_" + "".join(random.choice(string.ascii_lowercase) for _ in range(12))
    goi("set_auth_token", ["unauthorized_user_token"])
    goi("chart_create_session", [cs, ""])
    goi("resolve_symbol", [cs, "symbol_1", '={"symbol":"%s","adjustment":"splits"}' % sym])
    goi("create_series", [cs, "s1", "s1", "symbol_1", khung, n])
    tho, t0 = "", time.time()
    while time.time() - t0 < 30:
        try:
            m = ws.recv()
        except Exception:                                            # noqa: BLE001
            break
        if re.fullmatch(r"~m~\d+~m~~h~\d+", m):
            ws.send(m)
            continue
        tho += m
        if any(k in m for k in ("series_completed", "symbol_error", "critical_error", "series_error")):
            break
    ws.close()
    so = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"
    v = re.findall(r'"v":\[' + ",".join([so] * 5), tho)
    if not v:
        raise ValueError(tho[-120:])
    s = pd.Series([float(r[4]) for r in v], index=pd.to_datetime([float(r[0]) for r in v], unit="s"))
    return s[~s.index.duplicated(keep="last")].sort_index()


def lbma(kim="gold_pm"):
    """LBMA (giá chuẩn chính thức London) – JSON công khai prices.lbma.org.uk → Series USD/oz theo ngày."""
    j = _get(f"https://prices.lbma.org.uk/json/{kim}.json", headers={"Referer": "https://www.lbma.org.uk/"}).json()
    return pd.Series({pd.Timestamp(x["d"]): float(x["v"][0]) for x in j if x.get("v") and x["v"][0]}).sort_index()


def yf(ma, tu="2015-01-01"):
    import contextlib

    import yfinance as y
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        df = y.Ticker(ma).history(start=tu, auto_adjust=False)
    if df is None or not len(df):
        raise ValueError("rỗng")
    s = df["Close"]
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    return s


def stooq(ma):
    txt = _get(f"https://stooq.com/q/d/l/?s={ma}&i=d").text
    if not txt[:40].lower().startswith("date"):
        raise ValueError("không phải CSV: " + txt[:50])
    d = pd.read_csv(io.StringIO(txt))
    return pd.Series(d["Close"].values, index=pd.to_datetime(d["Date"]))


def cafef_sjc():
    """CafeF lịch sử giá SJC (từ 02/2025) → Series giá bán triệu đồng / lượng."""
    j = _get("https://cafef.vn/du-lieu/Ajax/ajaxgoldpricehistory.ashx?index=all", headers={"Referer": "https://cafef.vn/"}).json()
    ds = (j.get("Data") or {}).get("goldPriceWorldHistories") or (j.get("Data") or {}).get("data") or j.get("Data") or []
    if isinstance(ds, dict):
        ds = next((v for v in ds.values() if isinstance(v, list)), [])
    out = {}
    for x in ds:
        d = x.get("createdAt") or x.get("Date") or x.get("date") or x.get("lastUpdated")
        b = x.get("sellPrice") or x.get("Sell") or x.get("sell") or x.get("buyPrice")
        if d and b:
            out[pd.Timestamp(str(d)[:10])] = float(b) / (1e6 if float(b) > 1e5 else (1e3 if float(b) > 1e3 else 1))
    if not out:
        raise ValueError("không đọc được – khoá: " + str(list(j)[:5]) + " " + json.dumps(j)[:200])
    return pd.Series(out).sort_index()


def ny_fed(loai="secured/sofr"):
    j = _get(f"https://markets.newyorkfed.org/api/rates/{loai}/last/500.json").json()
    d = pd.DataFrame(j.get("refRates", []))
    return pd.Series(pd.to_numeric(d["percentRate"]).values, index=pd.to_datetime(d["effectiveDate"])).sort_index()


def bls(ma="CUUR0000SA0"):
    """BLS (Cục Thống kê Lao động Mỹ) API v1 không khoá → CPI theo tháng (chỉ số) → lạm phát so cùng kỳ %."""
    j = _get(f"https://api.bls.gov/publicAPI/v1/timeseries/data/{ma}").json()
    ds = j["Results"]["series"][0]["data"]
    s = pd.Series({pd.Timestamp(f"{x['year']}-{x['period'][1:]}-01"): float(x["value"]) for x in ds
                   if x["period"].startswith("M") and x["period"] != "M13"}).sort_index()
    return (s / s.shift(12) - 1).dropna() * 100 if len(s) > 13 else s


def gold_api_lich_su():
    return _get("https://api.gold-api.com/history?symbol=XAU&startTimestamp="
                f"{int(time.time()) - 30 * 86400}&endTimestamp={int(time.time())}&groupBy=day").json()


def metals_live():
    return _get("https://api.metals.live/v1/spot/gold").json()


UNG_VIEN = {
    # (nhóm, tên): hàm
    ("XAU ngày", "LBMA PM (chính thức)"): lambda: lbma("gold_pm"),
    ("XAU ngày", "LBMA AM (chính thức)"): lambda: lbma("gold_am"),
    ("XAU ngày", "TradingView OANDA:XAUUSD"): lambda: tv("OANDA:XAUUSD"),
    ("XAU ngày", "TradingView TVC:GOLD"): lambda: tv("TVC:GOLD"),
    ("XAU ngày", "TradingView FX_IDC:XAUUSD"): lambda: tv("FX_IDC:XAUUSD"),
    ("XAU ngày", "yfinance GC=F (COMEX)"): lambda: yf("GC=F"),
    ("XAU ngày", "Stooq xauusd"): lambda: stooq("xauusd"),
    ("XAU giờ", "TradingView OANDA:XAUUSD 60'"): lambda: tv("OANDA:XAUUSD", "60", 800),
    ("XAG ngày", "LBMA bạc (chính thức)"): lambda: lbma("silver"),
    ("XAG ngày", "TradingView OANDA:XAGUSD"): lambda: tv("OANDA:XAGUSD"),
    ("XAG ngày", "yfinance SI=F"): lambda: yf("SI=F"),
    ("Dầu Brent", "TradingView TVC:UKOIL"): lambda: tv("TVC:UKOIL"),
    ("Dầu Brent", "yfinance BZ=F"): lambda: yf("BZ=F"),
    ("Dầu WTI", "TradingView TVC:USOIL"): lambda: tv("TVC:USOIL"),
    ("DXY", "TradingView TVC:DXY"): lambda: tv("TVC:DXY"),
    ("DXY", "yfinance DX-Y.NYB"): lambda: yf("DX-Y.NYB"),
    ("USD/VND", "TradingView FX_IDC:USDVND"): lambda: tv("FX_IDC:USDVND"),
    ("USD/VND", "yfinance VND=X"): lambda: yf("VND=X"),
    ("USD/CNY", "yfinance CNY=X"): lambda: yf("CNY=X"),
    ("SJC", "CafeF lịch sử SJC"): cafef_sjc,
    ("Mỹ", "NY Fed SOFR"): lambda: ny_fed("secured/sofr"),
    ("Mỹ", "BLS CPI so cùng kỳ %"): lambda: bls("CUUR0000SA0"),
    ("Mỹ", "TradingView ECONOMICS:USIRYY"): lambda: tv("ECONOMICS:USIRYY", "1M"),
    ("VN", "TradingView ECONOMICS:VNGDPYY (GDP)"): lambda: tv("ECONOMICS:VNGDPYY", "1M"),
    ("VN", "TradingView ECONOMICS:VNDIR (tiền gửi)"): lambda: tv("ECONOMICS:VNDIR", "1M"),
    ("VN", "TradingView ECONOMICS:VNLR (cho vay)"): lambda: tv("ECONOMICS:VNLR", "1M"),
    ("VN", "TradingView ECONOMICS:VNM2 (cung tiền)"): lambda: tv("ECONOMICS:VNM2", "1M"),
    ("VN", "TradingView ECONOMICS:VNBOT (cán cân TM)"): lambda: tv("ECONOMICS:VNBOT", "1M"),
    ("VN", "TradingView ECONOMICS:VNFDI (FDI)"): lambda: tv("ECONOMICS:VNFDI", "1M"),
    ("VN", "TradingView ECONOMICS:VNMPMI (PMI)"): lambda: tv("ECONOMICS:VNMPMI", "1M"),
    ("VN", "TradingView ECONOMICS:VNIPYY (SXCN)"): lambda: tv("ECONOMICS:VNIPYY", "1M"),
    ("VN", "TradingView ECONOMICS:VNFER (dự trữ NH)"): lambda: tv("ECONOMICS:VNFER", "1M"),
    # hàng hoá (25/11/2026, chủ quỹ: "kiếm thêm giá bạc, dầu các thứ") – Yahoo hợp đồng tương lai + TradingView so chéo
    ("Bạch kim", "yfinance PL=F"): lambda: yf("PL=F"),
    ("Bạch kim", "TradingView TVC:PLATINUM"): lambda: tv("TVC:PLATINUM"),
    ("Palladium", "yfinance PA=F"): lambda: yf("PA=F"),
    ("Đồng", "yfinance HG=F"): lambda: yf("HG=F"),
    ("Đồng", "TradingView COMEX:HG1!"): lambda: tv("COMEX:HG1!"),
    ("Đồng", "TradingView CAPITALCOM:COPPER"): lambda: tv("CAPITALCOM:COPPER"),
    ("Nhôm", "TradingView CAPITALCOM:ALUMINUM"): lambda: tv("CAPITALCOM:ALUMINUM"),
    ("Khí tự nhiên", "yfinance NG=F"): lambda: yf("NG=F"),
    ("Khí tự nhiên", "TradingView NYMEX:NG1!"): lambda: tv("NYMEX:NG1!"),
    ("Dầu WTI", "yfinance CL=F"): lambda: yf("CL=F"),
    ("Xăng RBOB", "yfinance RB=F"): lambda: yf("RB=F"),
    ("Than", "yfinance MTF=F"): lambda: yf("MTF=F"),
    ("Than", "TradingView ICEEUR:NCF1!"): lambda: tv("ICEEUR:NCF1!"),
    ("Quặng sắt", "yfinance TIO=F"): lambda: yf("TIO=F"),
    ("Quặng sắt", "TradingView SGX:FEF1!"): lambda: tv("SGX:FEF1!"),
    ("Thép HRC", "yfinance HRC=F"): lambda: yf("HRC=F"),
    ("Thép HRC", "TradingView COMEX:HRC1!"): lambda: tv("COMEX:HRC1!"),
    ("Cà phê Arabica", "yfinance KC=F"): lambda: yf("KC=F"),
    ("Cà phê Robusta", "yfinance RC=F"): lambda: yf("RC=F"),
    ("Cà phê Robusta", "TradingView ICEEUR:RC1!"): lambda: tv("ICEEUR:RC1!"),
    ("Cao su", "TradingView SGX:TF1!"): lambda: tv("SGX:TF1!"),
    ("Cao su", "TradingView OSE:RSS31!"): lambda: tv("OSE:RSS31!"),
    ("Gạo", "yfinance ZR=F"): lambda: yf("ZR=F"),
    ("Đường", "yfinance SB=F"): lambda: yf("SB=F"),
    ("Bông", "yfinance CT=F"): lambda: yf("CT=F"),
    ("Ngô", "yfinance ZC=F"): lambda: yf("ZC=F"),
    ("Lúa mì", "yfinance ZW=F"): lambda: yf("ZW=F"),
    ("Đậu tương", "yfinance ZS=F"): lambda: yf("ZS=F"),
    ("Heo nạc", "yfinance HE=F"): lambda: yf("HE=F"),
    ("Urê", "TradingView CBOT:UFV1!"): lambda: tv("CBOT:UFV1!"),
    ("Khác", "TradingView TVC:VIX"): lambda: tv("TVC:VIX"),
    ("Khác", "TradingView BITSTAMP:BTCUSD"): lambda: tv("BITSTAMP:BTCUSD"),
}
THO = {("XAU trực tiếp", "gold-api lịch sử 30 ngày"): gold_api_lich_su, ("XAU trực tiếp", "metals.live"): metals_live}


def so_cheo(a, b):
    """Hai chuỗi cùng nội dung → (số ngày trùng, tương quan lợi suất ngày, lệch trung vị %)."""
    x = pd.concat([a, b], axis=1, join="inner").dropna()
    x = x[~x.index.duplicated()]
    if len(x) < 30:
        return len(x), np.nan, np.nan
    r = x.pct_change().dropna()
    return len(x), r.iloc[:, 0].corr(r.iloc[:, 1]), ((x.iloc[:, 0] / x.iloc[:, 1] - 1).abs().median() * 100)


def main():
    kq = {}
    for (nhom, ten), ham in UNG_VIEN.items():
        try:
            s = pd.Series(ham()).dropna()
            s = s[~s.index.duplicated(keep="last")].sort_index()
            kq[(nhom, ten)] = s
            print(f"✔ [{nhom}] {ten}: {len(s)} điểm {s.index[0]:%Y-%m-%d %H:%M} → {s.index[-1]:%Y-%m-%d %H:%M} · cuối {s.iloc[-1]:,.4g}",
                  flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ [{nhom}] {ten}: {type(e).__name__} {str(e)[:120]}", flush=True)
    for (nhom, ten), ham in THO.items():
        try:
            print(f"✔ [{nhom}] {ten}: {json.dumps(ham())[:200]}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ [{nhom}] {ten}: {type(e).__name__} {str(e)[:120]}")
    print("\n=== SO CHÉO (cùng nhóm, theo ngày) ===")
    nhoms = sorted({n for n, _ in kq})
    for n in nhoms:
        ds = [(t, s) for (nn, t), s in kq.items() if nn == n]
        for i in range(len(ds)):
            for j in range(i + 1, len(ds)):
                a, b = ds[i][1], ds[j][1]
                if n == "XAU giờ":
                    continue
                a = a.groupby(a.index.normalize()).last()
                b = b.groupby(b.index.normalize()).last()
                m, c, l = so_cheo(a, b)
                print(f"  [{n}] {ds[i][0]} ↔ {ds[j][0]}: {m} ngày trùng · tương quan lợi suất ngày {c:.3f} · lệch trung vị {l:.2f} %")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
