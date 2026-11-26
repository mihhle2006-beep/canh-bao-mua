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


def tv_tho(sym, khung="1D", n=5000):
    """TradingView (không đăng nhập) → Series giá đóng cửa, chỉ mục = mốc UTC THÔ của nến (chưa gộp ngày)."""
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


def ngay(s, bu=0):
    """Mốc UTC thô → ngày: (UTC + bu giờ).normalize(); bu=0 là cách cũ (lai_suat.doc_nen)."""
    s = s.copy()
    s.index = (pd.DatetimeIndex(s.index) + pd.Timedelta(hours=bu)).normalize()
    return s[~s.index.duplicated(keep="last")]


def tv(sym, khung="1D", n=5000):
    """Khung ngày / tháng: ngày theo lai_suat.TV_BU_GIO (đã sửa lệch 1 ngày – kiem_ngay); khung phút: giữ giờ."""
    from thi_truong.lai_suat import TV_BU_GIO
    s = tv_tho(sym, khung, n)
    return ngay(s, TV_BU_GIO) if khung in ("1D", "1W", "1M") else s


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
                   if x["period"].startswith("M") and x["period"] != "M13"
                   and re.fullmatch(r"-?[\d.]+", str(x["value"]))}).sort_index()
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


# KIỂM NGÀY NẾN (25/11/2026): TV ↔ Yahoo cùng hàng hoá tương quan lợi suất ngày chỉ ~0,2 dù mức lệch < 1 % → nghi nến TV
# bị gán lùi 1 ngày (nến ngày TV đánh dấu bằng GIỜ MỞ phiên – vàng/dầu/FX mở 22–23 h UTC hôm TRƯỚC). Đo: giờ UTC của nến,
# tương quan theo độ trễ −1/0/+1 với nguồn gắn nhãn ngày chuẩn (Yahoo theo ngày giao dịch sàn, Bộ Tài chính Mỹ, HNX).
# KẾT QUẢ (máy GitHub): cách cũ lệch 1 ngày (cùng ngày ≈ 0, trễ +1: vàng 0,89 · đồng 0,99 · Mỹ 10N 0,61); +12/14 h: cùng ngày
# vàng 0,90 · DXY 0,97 · Mỹ 10N 0,95 · đồng 0,99 · VIX/BTC 1,00 → lai_suat.TV_BU_GIO = 14 (SGX phiên T+1 mở 10:15 UTC cần ≥ 14).
KIEM_NGAY = [
    ("OANDA:XAUUSD", "yf:GC=F"), ("TVC:GOLD", "yf:GC=F"), ("OANDA:XAGUSD", "yf:SI=F"), ("TVC:PLATINUM", "yf:PL=F"),
    ("TVC:UKOIL", "yf:BZ=F"), ("TVC:USOIL", "yf:CL=F"), ("NYMEX:NG1!", "yf:NG=F"), ("COMEX:HG1!", "yf:HG=F"),
    ("CAPITALCOM:COPPER", "yf:HG=F"), ("COMEX:HRC1!", "yf:HRC=F"), ("SGX:FEF1!", "yf:TIO=F"), ("ICEEUR:NCF1!", "yf:MTF=F"),
    ("TVC:DXY", "yf:DX-Y.NYB"), ("FX_IDC:USDVND", "yf:VND=X"), ("TVC:VIX", "yf:^VIX"), ("BITSTAMP:BTCUSD", "yf:BTC-USD"),
    ("TVC:US10Y", "bt:US_10Y"), ("TVC:US02Y", "bt:US_2Y"), ("TVC:VN10Y", "hnx:10"), ("TVC:VN01Y", "hnx:1"),
    ("ICEEUR:RC1!", None), ("SGX:TF1!", None), ("CBOT:UFV1!", None), ("CAPITALCOM:ALUMINUM", None),
]


def _thay_doi(s, la_ls):
    return s.diff() if la_ls else s.pct_change()


def kiem_ngay():
    print("=== KIỂM NGÀY NẾN TradingView (giờ UTC của nến · tương quan thay đổi ngày theo độ trễ, 2 cách gán ngày) ===")
    bt, hnx = None, None
    for sym, ref in KIEM_NGAY:
        try:
            r = tv_tho(sym, "1D", 1500)
        except Exception as e:                                        # noqa: BLE001
            print(f"  ✘ {sym}: {type(e).__name__} {str(e)[:80]}")
            continue
        gio = pd.Series(pd.DatetimeIndex(r.index).strftime("%H:%M")).value_counts().head(3).to_dict()
        cuoi = ", ".join(f"{d:%Y-%m-%d %H:%M}" for d in r.index[-3:])
        dong = f"  {sym}: giờ UTC {gio} · 3 nến cuối {cuoi}"
        if ref is None:
            print(dong)
            continue
        try:
            loai, ma = ref.split(":", 1)
            if loai == "yf":
                b = yf(ma, "2020-01-01")
            elif loai == "bt":
                if bt is None:
                    from thi_truong import lai_suat as LS
                    bt = LS.tai_bo_tai_chinh_my(2020)
                b = bt[ma]
            else:
                if hnx is None:
                    from thi_truong import lai_suat as LS
                    hnx = LS.tai_hnx("cache_du_lieu/vi_mo/lai_suat", tu="2020-01-01")
                b = hnx[int(ma)].dropna()
        except Exception as e:                                        # noqa: BLE001
            print(dong + f" · ✘ đối chiếu {ref}: {type(e).__name__} {str(e)[:60]}")
            continue
        la_ls = loai in ("bt", "hnx") or sym.startswith("TVC:US") or sym.startswith("TVC:VN")
        kq = []
        for bu in (0, 14):                                            # cách cũ · lai_suat.TV_BU_GIO
            a = ngay(r, bu)
            a = a[a.index >= "2021-01-01"]
            bb = b[b.index >= "2021-01-01"]
            for tre in (-1, 0, 1):
                x = pd.concat([_thay_doi(a, la_ls).shift(tre), _thay_doi(bb, la_ls)], axis=1, join="inner").dropna()
                c = x.iloc[:, 0].corr(x.iloc[:, 1]) if len(x) > 30 else np.nan
                kq.append(f"bu{bu:+d}h trễ{tre:+d}={c:.2f}")
            m = pd.concat([a, bb], axis=1, join="inner").dropna()
            khop = (m.iloc[:, 0] - m.iloc[:, 1]).abs().le((m.iloc[:, 1].abs() * 0.002) + (0.01 if la_ls else 0)).mean()
            kq.append(f"bu{bu:+d}h khớp mức {khop:.0%}")
        print(dong + " · " + " | ".join(kq), flush=True)


# VÒNG 2 (25/11/2026, chủ quỹ: "trình bày như FireAnt – Kinh tế vĩ mô"): dò thêm chỉ tiêu VN theo chủ đề (tăng trưởng, sản
# xuất, giá, tiền tệ, thương mại, tiêu dùng, lao động) + thế giới, nguồn năm (World Bank, IMF), giá xăng dầu, báo cáo vĩ mô.
TV_VN = ["VNGDP", "VNGDPPC", "VNGDPPCP", "VNGDPCP", "VNGDPQQ", "VNGDPA", "VNGDPCONS", "VNGDPMAN", "VNGDPMIN", "VNGDPSERV",
         "VNGDPUTIL", "VNGFCF", "VNGDPDEF", "VNGNP", "VNIRMM", "VNCPI", "VNCPIT", "VNCPIH", "VNFOODINF", "VNPPIYY", "VNPPI",
         "VNEXPP", "VNIMPP", "VNIPMM", "VNMPMI", "VNSPMI", "VNRSMM", "VNCCI", "VNBCI", "VNUR", "VNPOP", "VNEMP", "VNLF", "VNWAG",
         "VNMW", "VNEP", "VNCOP", "VNSTP", "VNCARR", "VNCP", "VNTA", "VNTR", "VNIMP", "VNCA", "VNCAG", "VNGD", "VNGDG",
         "VNGBV", "VNGB", "VNM0", "VNM1", "VNM3", "VNLTPS", "VNPSC", "VNCBBS", "VNGASP", "VNCORP", "VNLR", "VNDIR", "VNM2",
         "VNEXPYY", "VNIMPYY", "VNRR", "VNCAPUT", "VNHPI", "VNDGC", "VNFE", "VNCI", "VNTOT", "VNBC", "VNIRYY", "VNCIR",
         "VNINTR", "VNINBR", "VNIPYY", "VNRSYY", "VNGDPYY", "VNEXP", "VNBOT", "VNFDI", "VNFER"]
TV_TG = ["USGDPQQ", "USGDPYY", "USUR", "USNFP", "USCIR", "USMPMI", "USRSYY", "CNGDPYY", "CNIRYY", "CNMPMI", "CNBOT", "CNIPYY",
         "CNRSYY", "CNINTR", "EUGDPYY", "EUIRYY", "EUINTR", "EUUR", "JPGDPYY", "JPIRYY", "JPINTR", "KRGDPYY", "KRIRYY",
         "KRINTR", "THGDPYY", "THIRYY", "THINTR"]
WB = {"NY.GDP.MKTP.KD.ZG": "GDP tăng trưởng %", "NY.GDP.MKTP.CD": "GDP USD", "NY.GDP.PCAP.CD": "GDP/người USD",
      "NY.GDP.PCAP.PP.CD": "GDP/người PPP", "SP.POP.TOTL": "dân số", "SL.UEM.TOTL.ZS": "thất nghiệp %",
      "FP.CPI.TOTL.ZG": "lạm phát %", "NE.EXP.GNFS.ZS": "xuất khẩu % GDP", "GC.DOD.TOTL.GD.ZS": "nợ CP % GDP",
      "BN.CAB.XOKA.GD.ZS": "cán cân vãng lai % GDP"}
IMF = {"NGDP_RPCH": "GDP tăng trưởng %", "PCPIPCH": "lạm phát %", "NGDPDPC": "GDP/người USD", "LUR": "thất nghiệp %",
       "GGXWDG_NGDP": "nợ CP % GDP", "BCA_NGDPD": "vãng lai % GDP", "NGDPD": "GDP tỷ USD"}


def _tom(s):
    s = pd.Series(s).dropna().sort_index()
    gap = pd.Series(s.index).diff().dt.days.median() if len(s) > 2 else float("nan")
    return (f"{len(s)} điểm {s.index[0]:%Y-%m} → {s.index[-1]:%Y-%m-%d} · ~{gap:.0f} ngày/kỳ · cuối: "
            + " · ".join(f"{d:%m/%y} {v:,.4g}" for d, v in s.iloc[-5:].items()))


def do_vn():
    print("=== TradingView ECONOMICS – Việt Nam ===")
    for m in TV_VN:
        try:
            print(f"✔ VN {m}: {_tom(tv('ECONOMICS:' + m, '1M'))}", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ VN {m}: {type(e).__name__} {str(e)[:50]}", flush=True)
    print("=== TradingView ECONOMICS – thế giới ===")
    for m in TV_TG:
        try:
            print(f"✔ TG {m}: {_tom(tv('ECONOMICS:' + m, '1M'))}", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ TG {m}: {type(e).__name__} {str(e)[:50]}", flush=True)
    print("=== World Bank (năm) ===")
    for ma, ten in WB.items():
        try:
            j = _get(f"https://api.worldbank.org/v2/country/VNM/indicator/{ma}?format=json&per_page=80").json()
            s = pd.Series({pd.Timestamp(f"{x['date']}-12-31"): x["value"] for x in j[1] if x.get("value") is not None})
            print(f"✔ WB {ma} ({ten}): {_tom(s)}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ WB {ma} ({ten}): {type(e).__name__} {str(e)[:60]}")
    print("=== IMF DataMapper (năm, có dự báo) ===")
    for ma, ten in IMF.items():
        try:
            j = _get(f"https://www.imf.org/external/datamapper/api/v1/{ma}/VNM").json()
            d = j["values"][ma]["VNM"]
            s = pd.Series({pd.Timestamp(f"{k}-12-31"): v for k, v in d.items()})
            print(f"✔ IMF {ma} ({ten}): {_tom(s)}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ IMF {ma} ({ten}): {type(e).__name__} {str(e)[:60]}")
    print("=== Giá xăng dầu ===")
    for url in ("https://www.petrolimex.com.vn/", "https://webgia.com/gia-xang-dau/petrolimex/",
                "https://vnexpress.net/chu-de/gia-xang-dau-3026", "https://xangdau.net/"):
        try:
            t = _get(url, timeout=30).text
            m = re.findall(r"(RON\s*95[^<]{0,40}|DO\s*0[,.]05S[^<]{0,40})", t)
            g = re.findall(r"\b(\d{2}[.,]\d{3})\b", t)
            print(f"✔ {url}: {len(t)} ký tự · nhãn {m[:3]} · số {g[:8]}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {url}: {type(e).__name__} {str(e)[:60]}")
    print("=== Báo cáo vĩ mô (CTCK) ===")
    for url in ("https://cafef.vn/du-lieu/Ajax/PageNew/BaoCaoPhanTich.ashx?Symbol=&PageIndex=1&PageSize=20&Type=4",
                "https://cafef.vn/du-lieu/Ajax/PageNew/BaoCaoPhanTich.ashx?Symbol=&PageIndex=1&PageSize=20",
                "https://api.simplize.vn/api/company/analysis-report/list?page=0&size=20&reportType=MACRO",
                "https://api.simplize.vn/api/company/analysis-report/list?ticker=&page=0&size=20"):
        try:
            r = _get(url, timeout=30, headers={"Referer": "https://cafef.vn/"})
            print(f"✔ {url}: {r.status_code} {r.text[:300]!r}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {url}: {type(e).__name__} {str(e)[:60]}")


def do_te():
    """Trading Economics (26/11/2026, chủ quỹ hỏi "Trading Economics có dùng được không"): API khoá khách guest:guest + trang web."""
    for url in ("https://api.tradingeconomics.com/country/vietnam?c=guest:guest&f=json",
                "https://api.tradingeconomics.com/historical/country/vietnam/indicator/inflation%20rate?c=guest:guest&f=json",
                "https://api.tradingeconomics.com/country/thailand?c=guest:guest&f=json",
                "https://tradingeconomics.com/vietnam/indicators",
                "https://tradingeconomics.com/vietnam/manufacturing-pmi",
                "https://tradingeconomics.com/vietnam/loans-to-private-sector",
                "https://tradingeconomics.com/vietnam/calendar"):
        try:
            import requests
            r = requests.get(url, headers=UA, timeout=40)
            t = r.text
            hang = re.findall(r"<td[^>]*>\s*<a[^>]*>([^<]{3,60})</a>\s*</td>\s*<td[^>]*>\s*([-\d.,]+)\s*</td>", t)
            print(f"{'✔' if r.ok else '✘'} {r.status_code} {url}: {len(t)} ký tự · {r.headers.get('server', '')} · "
                  f"{hang[:6] if hang else t[:220]!r}", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {url}: {type(e).__name__} {str(e)[:80]}", flush=True)


# VÒNG 3 (26/11/2026, chủ quỹ: "tìm thêm nguồn đi"): phần còn thiếu so FireAnt – PMI, tín dụng, thất nghiệp quý, xuất nhập khẩu
# mới, GDP theo ngành, vốn đầu tư, DN thành lập (thông cáo Cục Thống kê), xăng dầu (Petrolimex), báo cáo vĩ mô CTCK, IMF IFS
# qua DBnomics (tín dụng, M2 theo tháng).
URL_VN3 = {
    "nso_trang_chu": "https://www.nso.gov.vn/",
    "gso_trang_chu": "https://www.gso.gov.vn/",
    "nso_ktxh": "https://www.nso.gov.vn/tinh-hinh-kinh-te-xa-hoi/",
    "nso_tim": "https://www.nso.gov.vn/?s=t%C3%ACnh+h%C3%ACnh+kinh+t%E1%BA%BF+x%C3%A3+h%E1%BB%99i+th%C3%A1ng+m%C6%B0%E1%BB%9Di",
    "nso_px": "https://www.nso.gov.vn/px-web-2/",
    "hai_quan": "https://www.customs.gov.vn/",
    "spglobal_pmi": "https://www.pmi.spglobal.com/Public/Release/PressReleases?language=en",
    "petrolimex": "https://www.petrolimex.com.vn/",
    "vietstock_bc": "https://finance.vietstock.vn/bao-cao-phan-tich",
    "vndirect_vimo": "https://www.vndirect.com.vn/danh_muc_bao_cao/bao-cao-vi-mo/",
    "mbs_vimo": "https://mbs.com.vn/trung-tam-nghien-cuu/bao-cao-phan-tich/nghien-cuu-vi-mo/",
    "ssi_vimo": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-vi-mo",
    "cafef_vimo": "https://cafef.vn/vi-mo-dau-tu.chn",
    "cafef_dl_vimo": "https://s.cafef.vn/du-lieu-vi-mo.chn",
    "sbv": "https://www.sbv.gov.vn/",
}
TU_KHOA = ["PMI", "tín dụng", "tăng trưởng tín dụng", "thất nghiệp", "xuất khẩu", "RON 95", "Vĩ mô", "vĩ mô", "Manufacturing PMI",
           "Vietnam", "CPI", "tình hình kinh tế"]


def do_vn3():
    import requests
    for ten, url in URL_VN3.items():
        try:
            r = requests.get(url, headers={**UA, "Accept-Language": "vi,en;q=0.8"}, timeout=40, allow_redirects=True)
            t = r.text
            dem = {k: t.count(k) for k in TU_KHOA if t.count(k)}
            lk = re.findall(r'href="([^"]*(?:kinh-te-xa-hoi|thong-cao|bao-cao|vi-mo|pmi|PressRelease|tin-dung|xuat-nhap)[^"]*)"', t, re.I)
            print(f"{'✔' if r.ok else '✘'} {r.status_code} {ten} → {r.url[:90]} · {len(t)} ký tự · {dem} · link: {list(dict.fromkeys(lk))[:6]}",
                  flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {ten}: {type(e).__name__} {str(e)[:90]}", flush=True)
    # Petrolimex: ngữ cảnh quanh nhãn xăng RON 95 / dầu DO
    try:
        t = requests.get(URL_VN3["petrolimex"], headers=UA, timeout=40).text
        for nhan in ("RON 95-V", "RON 95-III", "E5 RON 92", "DO 0,05S"):
            i = t.find(nhan)
            if i >= 0:
                print(f"  Petrolimex [{nhan}]: {re.sub(r'<[^>]+>', ' ', t[i:i + 400])[:260]!r}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ petrolimex ngữ cảnh: {type(e).__name__}")
    # DBnomics – IMF IFS Việt Nam theo tháng: liệt kê chuỗi + kỳ cuối
    try:
        j = _get("https://api.db.nomics.world/v22/series/IMF/IFS?dimensions=%7B%22REF_AREA%22%3A%5B%22VN%22%5D%2C%22FREQ%22%3A%5B%22M%22%5D%7D"
                 "&limit=1000&observations=0", timeout=60).json()
        ds = j.get("series", {}).get("docs", [])
        print(f"✔ DBnomics IMF/IFS VN tháng: {len(ds)} chuỗi")
        for d in ds:
            ten = d.get("series_name", "")
            if re.search(r"credit|claims on private|broad money|monetary|deposit rate|lending rate|reserve", ten, re.I):
                print(f"   {d.get('series_code')}: {ten[:110]} · cuối {d.get('indexed_at', '')[:10]}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ DBnomics IFS: {type(e).__name__} {str(e)[:80]}")
    for ma in ("IMF/IFS/M.VN.FASMB_XDC", "IMF/IFS/M.VN.FOSAOP_XDC", "IMF/IFS/M.VN.FDSAOP_XDC", "IMF/IFS/M.VN.FPOLM_PA",
               "IMF/IFS/M.VN.FILR_PA", "IMF/IFS/M.VN.FIDR_PA"):
        try:
            j = _get(f"https://api.db.nomics.world/v22/series/{ma}?observations=1", timeout=40).json()
            d = j["series"]["docs"][0]
            per, val = d.get("period", []), d.get("value", [])
            print(f"✔ {ma}: {d.get('series_name', '')[:80]} · {len(per)} kỳ · cuối {per[-3:]} {val[-3:]}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {ma}: {type(e).__name__} {str(e)[:60]}")


def _chu(html):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as h
    return re.sub(r"\s+", " ", h.unescape(t))


def _quanh(t, k, n=2, rong=320):
    out = []
    for i, m in enumerate(re.finditer(re.escape(k), t)):
        if i >= n:
            break
        out.append(t[max(0, m.start() - 60):m.start() + rong])
    return out


def do_vn4():
    import requests
    g = lambda u, **k: requests.get(u, headers={**UA, "Accept-Language": "vi,en;q=0.8"}, timeout=50, **k)   # noqa: E731
    # 1) Cục Thống kê – báo cáo tháng: câu chứa số cần lấy
    try:
        ds = g("https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/").text
        lk = list(dict.fromkeys(re.findall(r'href="(https://www\.nso\.gov\.vn/[^"]*bao-cao-tinh-hinh-kinh-te-xa-hoi-thang[^"]*)"', ds)))
        print(f"✔ NSO danh sách báo cáo tháng: {len(lk)} link · {lk[:4]}")
        u = lk[0] if lk else "https://www.nso.gov.vn/bai-top/2026/11/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-muoi-va-10-thang-nam-2026/"
        t = _chu(g(u).text)
        print(f"✔ NSO báo cáo {u}: {len(t)} ký tự")
        for k in ("tổng sản phẩm trong nước", "Chỉ số giá tiêu dùng (CPI) tháng", "lạm phát cơ bản", "Chỉ số sản xuất toàn ngành công nghiệp",
                  "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ", "Tổng kim ngạch xuất, nhập khẩu", "xuất siêu", "nhập siêu",
                  "vốn đầu tư trực tiếp nước ngoài", "Vốn đầu tư thực hiện từ nguồn ngân sách", "khách quốc tế", "thành lập mới",
                  "tăng trưởng tín dụng", "tổng phương tiện thanh toán", "tỷ lệ thất nghiệp", "sản lượng điện", "xi măng", "thép"):
            for x in _quanh(t, k, 1):
                print(f"   [{k}] {x}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ NSO báo cáo: {type(e).__name__} {str(e)[:80]}")
    # 2) Cục Thống kê – cổng số liệu PX-Web
    try:
        t = g("https://www.nso.gov.vn/px-web-2/").text
        lk = list(dict.fromkeys(re.findall(r'href="([^"]*(?:pxid|px-web|pxweb)[^"]*)"', t, re.I)))
        api = re.findall(r'["\'](/?[^"\']*api[^"\']*)["\']', t)[:10]
        print(f"✔ PX-Web: {len(lk)} link {lk[:8]} · api? {api}")
        for u in ("https://www.nso.gov.vn/px-web-2/api/v1/vi/", "https://www.nso.gov.vn/px-web-2/api/v1/en/",
                  "https://pxweb.nso.gov.vn/api/v1/vi/", "https://www.nso.gov.vn/px-web-2/api/v2/tables?lang=vi"):
            try:
                r = g(u)
                print(f"   {r.status_code} {u}: {r.text[:200]!r}")
            except Exception as e:                                    # noqa: BLE001
                print(f"   ✘ {u}: {type(e).__name__}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ PX-Web: {type(e).__name__} {str(e)[:80]}")
    # 3) S&P Global – PMI Việt Nam
    try:
        t = g("https://www.pmi.spglobal.com/Public/Release/PressReleases?language=en").text
        m = re.search(r'href="(/Public/Home/PressRelease/[0-9a-f]+)"[^>]*>(?:(?!</a>).){0,200}Vietnam', t, re.S) or \
            re.search(r'Vietnam(?:(?!href).){0,400}href="(/Public/Home/PressRelease/[0-9a-f]+)"', t, re.S)
        print(f"✔ S&P danh sách: {'có' if m else 'không thấy'} Vietnam · {_quanh(_chu(t), 'Vietnam', 2, 160)}")
        if m:
            u = "https://www.pmi.spglobal.com" + m.group(1)
            tt = _chu(g(u).text)
            print(f"   {u}: {_quanh(tt, 'PMI', 3, 300)}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ S&P PMI: {type(e).__name__} {str(e)[:80]}")
    # 4) Petrolimex – thông cáo điều chỉnh giá mới nhất
    try:
        t = g("https://www.petrolimex.com.vn/ndi/thong-cao-bao-chi.html").text
        lk = list(dict.fromkeys(re.findall(r'href="(/ndi/thong-cao-bao-chi/petrolimex-dieu-chinh-gia[^"]+)"', t)))
        print(f"✔ Petrolimex thông cáo: {len(lk)} · {lk[:3]}")
        if lk:
            tt = _chu(g("https://www.petrolimex.com.vn" + lk[0]).text)
            for k in ("RON 95-III", "E5 RON 92", "DO 0,05S", "Vùng 1"):
                print(f"   [{k}] {_quanh(tt, k, 1, 220)}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ Petrolimex: {type(e).__name__} {str(e)[:80]}")
    # 5) NHNN – dư nợ tín dụng, thông cáo
    for u in ("https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt", "https://sbv.gov.vn/vi/thong-cao-bao-chi",
              "https://sbv.gov.vn/vi/ty-le-no-xau-trong-tong-du-no-tin-dung"):
        try:
            r = g(u)
            tt = _chu(r.text)
            print(f"✔ {r.status_code} {u}: {len(tt)} · {_quanh(tt, 'tín dụng', 3, 260)}")
            print(f"   bảng: {re.findall(r'<table', r.text)[:1]} · năm: {sorted(set(re.findall(r'20[12][0-9]', tt)))[-6:]}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {u}: {type(e).__name__} {str(e)[:80]}")
    # 6) Vietstock – báo cáo phân tích (vĩ mô)
    try:
        t = g("https://finance.vietstock.vn/bao-cao-phan-tich").text
        print(f"✔ Vietstock: {_quanh(_chu(t), 'Vĩ mô', 3, 200)}")
        ajax = list(dict.fromkeys(re.findall(r"""['"](/[A-Za-z]+/[A-Za-z]*[Rr]eport[A-Za-z]*)['"]""", t)))[:10]
        pdf = re.findall(r'href="([^"]+\.pdf)"', t)[:3]
        print(f"   ajax: {ajax} · pdf: {pdf}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ Vietstock: {type(e).__name__} {str(e)[:80]}")
    # 7) CafeF – RSS vĩ mô (tin, đường dẫn)
    try:
        t = g("https://cafef.vn/vi-mo-dau-tu.rss").text
        it = re.findall(r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>", t, re.S)
        print(f"✔ CafeF RSS vĩ mô: {len(it)} tin · {[(a[:70], c[:25]) for a, _, c in it[:3]]}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ CafeF RSS: {type(e).__name__} {str(e)[:80]}")


def do_vn5():
    """Vòng 5: bộ đọc thi_truong/nso trên nhiều báo cáo + so chéo TradingView; PMI S&P (link Vietnam); NHNN bảng tín dụng;
    Petrolimex thông cáo; MBS báo cáo vĩ mô."""
    import os

    import requests

    from thi_truong import nso
    g = lambda u, **k: requests.get(u, headers={**UA, "Accept-Language": "vi,en;q=0.8"}, timeout=50, **k)   # noqa: E731
    ds = nso.danh_sach(lambda u: g(u).text, trang=4)
    print(f"✔ NSO: {len(ds)} báo cáo · cũ nhất {ds[-1][1]:%m/%Y} · mới nhất {ds[0][1]:%m/%Y}" if ds else "✘ NSO: không có báo cáo")
    df, _ = nso.tai_dem(lambda u: g(u).text, {}, trang=4)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(df.to_string())
    print("số ô có giá trị theo khoá:", df.notna().sum().to_dict())
    goc = "cache_du_lieu/vi_mo"

    def doc_csv(*ten):
        for t in ten:
            f = os.path.join(goc, t)
            if os.path.exists(f):
                d = pd.read_csv(f, index_col=0, parse_dates=True)
                s = d.iloc[:, 0].astype(float)
                s.index = s.index.to_period("M").to_timestamp()
                return s
        return None
    cheo = [("xk", ("vn_xk.csv",), 1e9), ("can_can", ("vn_bot.csv",), 1e9), ("khach", ("kt_VNTA.csv",), 1),
            ("cpi_yoy", ("lai_suat/ECONOMICS_VNIRYY.csv",), 1), ("ban_le_yoy", ("lai_suat/ECONOMICS_VNRSYY.csv", "vn_banle.csv"), 1),
            ("iip_yoy", ("lai_suat/ECONOMICS_VNIPYY.csv", "vn_sxcn.csv"), 1), ("nk", ("kt_VNIMP.csv",), 1e9),
            ("lp_cb_bq", ("vn_cpi_loi.csv",), 1)]
    for k, tep, chia in cheo:
        tv = doc_csv(*tep)
        if tv is None or k not in df:
            print(f"  so chéo {k}: thiếu ({'TV' if tv is None else 'NSO'})")
            continue
        x = pd.concat([df[k], tv / chia], axis=1, join="inner").dropna()
        x.columns = ["NSO", "TV"]
        print(f"  so chéo {k}: {len(x)} tháng trùng · lệch tuyệt đối lớn nhất {(x.NSO - x.TV).abs().max():.3f} · "
              + " · ".join(f"{d:%m/%y} {a:g}/{b:.4g}" for d, (a, b) in x.tail(4).iterrows()))
    # PMI – S&P Global: link thông cáo Vietnam
    try:
        t = g("https://www.pmi.spglobal.com/Public/Release/PressReleases?language=en").text
        cap = re.findall(r'<a[^>]+href="(/Public/Home/PressRelease/[0-9a-f]+)"[^>]*>(.*?)</a>', t, re.S)
        vn = [(h, _chu(x)) for h, x in cap if "Vietnam" in x or "Viet Nam" in x]
        print(f"✔ S&P: {len(cap)} link · Vietnam: {vn[:3]}")
        if not vn:                                                    # link ở khối "View More" gần tiêu đề
            for m in re.finditer(r"Vietnam Manufacturing PMI", t):
                print("   quanh:", re.sub(r"\s+", " ", t[m.start() - 600:m.start() + 300])[:900])
                break
        for h, _ in vn[:2]:
            tt = _chu(g("https://www.pmi.spglobal.com" + h).text)
            print(f"   {h}: {_quanh(tt, 'PMI', 4, 260)}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ S&P: {type(e).__name__} {str(e)[:80]}")
    # NHNN – bảng dư nợ tín dụng
    try:
        t = g("https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt").text
        for b in re.findall(r"<table.*?</table>", t, re.S)[:2]:
            hang = [[_chu(c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)] for r in re.findall(r"<tr.*?</tr>", b, re.S)]
            print(f"✔ NHNN bảng {len(hang)} dòng: {hang[:8]}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ NHNN: {type(e).__name__} {str(e)[:80]}")
    # Petrolimex – thông cáo giá
    try:
        t = g("https://www.petrolimex.com.vn/ndi/thong-cao-bao-chi/petrolimex-dieu-chinh-gia-xang-dau-tu-15-gio-00-phut-ngay-19-11-2026.html").text
        tt = _chu(t)
        print(f"✔ Petrolimex thông cáo: {len(t)} html / {len(tt)} chữ · {_quanh(tt, 'đồng/lít', 2, 200)} · {_quanh(tt, 'RON', 2, 200)}")
        print(f"   bảng: {len(re.findall('<table', t))}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ Petrolimex: {type(e).__name__} {str(e)[:80]}")
    # MBS – báo cáo vĩ mô / trái phiếu tiền tệ (tiêu đề, ngày, PDF)
    for u in ("https://mbs.com.vn/bao-cao-thi-truong-trai-phieu-tien-te/", "https://mbs.com.vn/bao-cao-chien-luoc-thi-truong/"):
        try:
            t = g(u).text
            pdf = list(dict.fromkeys(re.findall(r'href="([^"]+\.pdf)"', t)))
            tieu = re.findall(r'<h[23][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S)
            print(f"✔ MBS {u}: pdf {len(pdf)} {pdf[:2]} · tiêu đề {[(_chu(b)[:60], a[:80]) for a, b in tieu[:4]]}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ MBS {u}: {type(e).__name__} {str(e)[:80]}")


def do_vn6():
    """Vòng 6: PMI (thông cáo S&P – câu chỉ số), NHNN (dòng tổng + kỳ của từng bảng), NSO (trang 2 danh sách, câu thất nghiệp,
    xuất khẩu các tháng)."""
    import requests
    g = lambda u, **k: requests.get(u, headers={**UA, "Accept-Language": "vi,en;q=0.8"}, timeout=50, **k)   # noqa: E731
    try:
        t = g("https://www.pmi.spglobal.com/Public/Release/PressReleases?language=en").text
        kh = re.findall(r'releaseDate">(.*?)</span>\s*<span class="releaseTitle">(.*?)</span>\s*<span class="greenListItem">'
                        r'<a href="([^"]+)"', t, re.S)
        vn = [(a.replace("&nbsp;", " "), b, c) for a, b, c in kh if "Vietnam" in b]
        print(f"✔ S&P: {len(kh)} thông cáo · Vietnam: {vn}")
        for d, ten, u in vn[:2]:
            tt = _chu(g(u).text)
            print(f"   [{ten}] {len(tt)} chữ: {_quanh(tt, 'PMI', 5, 220)}")
            so_pmi = re.findall(r'\b([4-6]\d[,.]\d)\b', tt)[:12]
            print(f"   số dạng xx,x / xx.x: {so_pmi}")
        trang2 = g("https://www.pmi.spglobal.com/Public/Release/PressReleases?language=en&page=2").text
        print(f"   trang 2: {len(re.findall('Vietnam', trang2))} lần Vietnam")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ S&P: {type(e).__name__} {str(e)[:80]}")
    try:
        t = g("https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt").text
        for i, b in enumerate(re.findall(r"<table.*?</table>", t, re.S)):
            hang = [[_chu(c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)] for r in re.findall(r"<tr.*?</tr>", b, re.S)]
            print(f"✔ NHNN bảng {i}: {hang[:3]} … {hang[-3:]}")
        tt = _chu(t)
        ky_bang = re.findall(r'[Tt]háng \d{1,2} [Nn]ăm \d{4}', tt)[:6]
        print(f"   kỳ: {ky_bang} · {_quanh(tt, 'Tổng', 3, 150)}")
        for u in re.findall(r'href="([^"]*du-no-tin-dung[^"]*)"', t)[:6]:
            print(f"   link: {u}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ NHNN: {type(e).__name__} {str(e)[:80]}")
    try:
        for u in ("https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/page/2/",
                  "https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/?paged=2"):
            r = g(u)
            print(f"   NSO {r.status_code} {u}: {len(re.findall('kinh-te-xa-hoi-(?:thang|quy)', r.text))} link")
        t9 = _chu(g("https://www.nso.gov.vn/bai-top/2026/09/bao-cao-tinh-hinh-kinh-te-xa-hoi-thang-tam-va-8-thang-nam-2026/").text)
        for k in ("thất nghiệp", "xuất khẩu hàng hóa tháng", "Xuất khẩu hàng hóa", "IIP", "khách quốc tế đến"):
            print(f"   T8 [{k}] {_quanh(t9, k, 2, 220)}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ NSO: {type(e).__name__} {str(e)[:80]}")


def do_vn7():
    """Vòng 7b: Cục Thống kê – phân trang "?paged=N" (sâu tới đâu), báo cáo năm cũ có đọc được không (khoá thiếu từng báo cáo)."""
    import requests
    from thi_truong import nso
    g = lambda u: requests.get(u, headers={**UA, "Accept-Language": "vi"}, timeout=50).text   # noqa: E731
    ds = nso.danh_sach(g, trang=5)
    print(f"✔ danh sách 5 trang: {len(ds)} báo cáo · {ds[-1][1]:%m/%Y}–{ds[0][1]:%m/%Y} · tháng thiếu: "
          f"{sorted(set(pd.date_range(ds[-1][1], ds[0][1], freq='MS').strftime('%m/%y')) - {f'{k:%m/%y}' for _, k, _ in ds})}")
    df, dem = nso.tai_dem(g, {}, trang=4)
    can = ("cpi_yoy", "cpi_ytd", "xk", "nk", "can_can", "ban_le", "dn_moi", "nsnn", "nsnn_kh", "fdi_dk", "vang_yoy", "lp_cb_bq")
    for u, v in sorted(dem.items(), key=lambda kv: kv[1]["_ky"]):
        print(f"   {v['_ky']} · {len(v) - 1} khoá · thiếu {[k for k in can if k not in v]} · {u[-60:]}")
    cot = [c for c in ("cpi_yoy", "xk", "nk", "can_can", "ban_le", "dn_moi", "nsnn", "nsnn_kh", "fdi_dk", "gdp_dv") if c in df]
    print(df[cot].to_string())


def do_vn8():
    """Vòng 8: câu CPI / giá vàng / USD / cán cân / nhập khẩu ở các báo cáo mẫu hiện tại không khớp."""
    import requests
    from thi_truong import nso
    g = lambda u: requests.get(u, headers={**UA, "Accept-Language": "vi"}, timeout=50).text   # noqa: E731
    ds = {f"{k:%Y-%m}": u for u, k, _ in nso.danh_sach(g, trang=4)}
    for ky in ("2025-10", "2025-04", "2026-05", "2026-06", "2025-11", "2026-10", "2026-07"):
        if ky not in ds:
            continue
        tt = nso.chu(g(ds[ky]))
        for k in ("Chỉ số giá tiêu dùng (CPI) tháng", "Chỉ số giá vàng", "Chỉ số giá đô la Mỹ", "cán cân thương mại hàng hóa",
                  "nhập khẩu hàng hóa tháng", "CPI bình quân", "Bình quân"):
            print(f"   {ky} [{k}] {_quanh(tt, k, 1, 300)}")

TV9_VN = ("VNGDPQQ VNGDPPC VNLF VNYUR VNFI VNCPI VNCCPI VNIMPP VNEXPP VNM0 VNM1 VNM3 VNLTPS VNPSC VNBLR VNDR VNIBR VNCBBS VNCAG "
          "VNED VNTOT VNCI VNREM VNGR VNGBV VNGREV VNGSPE VNGDGV VNIPMM VNEP VNSP VNCAR VNTVS VNBC VNCC VNCS VNRSMM VNCPIH VNHPI "
          "VNCOR VNGFCFY VNSTR VNIM VNEX").split()
TV9_TG = ("CNM2 CNEXPYY CNIMPYY CNBOT CNFER CNPPIYY USRSYY USIPYY USPCEPIYY USCCPI KREXPYY KRIMPYY TWEXPYY TWEXO JPEXPYY "
          "INGDPYY IDGDPYY MYGDPYY PHGDPYY SGGDPYY THEXPYY").split()


def do_vn9():
    """Vòng 9 (26/11/2026, chủ quỹ: "thêm nguồn cho chỉ số vĩ mô"): mã TradingView ECONOMICS chưa dùng (VN + khu vực),
    trang thống kê NHNN (M2 / tiền gửi / lãi suất), câu Cục Thống kê còn hụt (xuất khẩu T9, dầu thô, vốn NSNN, thu chi NSNN)."""
    import requests
    from thi_truong import nso
    for ma in TV9_VN + TV9_TG:
        try:
            s = tv("ECONOMICS:" + ma, "1M").dropna()
            print(f"✔ {ma}: {len(s)} kỳ {s.index[0]:%m/%Y}→{s.index[-1]:%m/%Y} · cuối {s.iloc[-1]:,.4g} · trước {s.iloc[-2]:,.4g}", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {ma}: {type(e).__name__} {str(e)[:60]}", flush=True)
    g = lambda u: requests.get(u, headers={**UA, "Accept-Language": "vi"}, timeout=50).text   # noqa: E731
    try:
        h = g(nso.NHNN_TD)
        ln = sorted(set(re.findall(r'href="(https?://(?:www\.)?sbv\.gov\.vn/[^"#?]+)"', h)))
        print(f"NHNN: {len(ln)} liên kết · " + " · ".join(u for u in ln if re.search(r"phuong-tien|tien-gui|lai-suat|thong-ke|ty-gia|"
                                                                                     r"can-can|du-tru|tin-dung|cung-tien|m2", u)))
        for u in ("https://sbv.gov.vn/tong-phuong-tien-thanh-toan", "https://sbv.gov.vn/tong-phuong-tien-thanh-toan-dttktt",
                  "https://sbv.gov.vn/tien-gui-cua-khach-hang-dttktt", "https://sbv.gov.vn/lai-suat-binh-quan-lien-ngan-hang"):
            try:
                t = _chu(g(u))
                print(f"   {u[20:]}: {len(t)} ký tự · {_quanh(t, 'Tháng', 1, 260) or t[:200]}")
            except Exception as e:                                    # noqa: BLE001
                print(f"   {u[20:]}: {type(e).__name__} {str(e)[:60]}")
    except Exception as e:                                            # noqa: BLE001
        print(f"✘ NHNN: {type(e).__name__} {str(e)[:80]}")
    ds = {f"{k:%Y-%m}": u for u, k, _ in nso.danh_sach(g, trang=2)}
    for ky in ("2026-09", "2026-10", "2026-06"):
        if ky not in ds:
            print(f"   {ky}: không có báo cáo")
            continue
        tt = nso.chu(g(ds[ky]))
        for k in ("xuất khẩu hàng hóa", "Kim ngạch xuất khẩu", "dầu thô", "ngân sách Nhà nước", "ngân sách nhà nước", "Tổng thu ngân sách",
                  "Tổng chi ngân sách", "vận chuyển hàng hóa", "Điện sản xuất", "giải thể", "rút lui khỏi thị trường"):
            for c in _quanh(tt, k, 2 if k in ("dầu thô", "ngân sách Nhà nước") else 1, 260):
                print(f"   {ky} [{k}] {c}")


def do_vn10():
    """Vòng 10: trang thống kê NHNN (nợ xấu, LDR, cán cân thanh toán, chỉ tiêu cơ bản, tiền mặt / M2) – khuôn số + có chọn kỳ cũ
    không; câu Cục Thống kê T9/2026 (nhập khẩu, cán cân, vốn NSNN) còn hụt."""
    import requests
    from thi_truong import nso
    g = lambda u: requests.get(u, headers={**UA, "Accept-Language": "vi"}, timeout=50).text   # noqa: E731
    for d in ("ty-le-no-xau-trong-tong-du-no-tin-dung", "ty-le-du-no-cho-vay-so-voi-tong-tien-gui", "can-can-thanh-toan-quoc-te",
              "thong-ke-mot-so-chi-tieu-co-ban", "tien-mat-luu-thong-tren-tong-phuong-tien-thanh-toan", "tong-phuong-tien-thanh-toan"):
        u = "https://sbv.gov.vn/vi/" + d
        try:
            h = g(u)
            t = nso.chu(h)
            i = t.find("Tháng") if "Tháng" in t[2000:] else 0
            i = max(t.find(" Tháng ", 1500), t.find(" Quý ", 1500), t.find(" Năm ", 1500), 0)
            sel = re.findall(r"<select[^>]*name=\"([^\"]+)\"", h)
            q = sorted(set(re.findall(r'href="([^"]*\?[^"]*(?:thang|nam|ky|period|date|year|month)[^"]*)"', h, re.I)))[:5]
            print(f"✔ {d}: {len(t)} ký tự · select {sel[:4]} · liên kết kỳ {q}")
            print(f"   {t[i:i + 900]}")
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {d}: {type(e).__name__} {str(e)[:80]}")
    ds = {f"{k:%Y-%m}": u for u, k, _ in nso.danh_sach(g, trang=1)}
    if "2026-09" in ds:
        tt = nso.chu(g(ds["2026-09"]))
        for k in ("nhập khẩu hàng hóa tháng", "Cán cân thương mại hàng hóa tháng", "cán cân thương mại hàng hóa tháng",
                  "Vốn đầu tư thực hiện từ nguồn ngân sách", "vốn đầu tư thực hiện từ nguồn ngân sách"):
            for c in _quanh(tt, k, 2, 280):
                print(f"   2026-09 [{k}] {c}")
        print("   2026-09 đọc được:", {k: v for k, v in nso.doc(tt).items() if k in ("xk", "nk", "can_can", "nsnn", "nsnn_kh")})


def do_vn11():
    """Vòng 11: khuôn số các bảng NHNN – cán cân thanh toán (đủ dòng), chỉ tiêu cơ bản / ROA-ROE / an toàn vốn (liên kết + bảng),
    nợ xấu, LDR (vùng quanh số %)."""
    import requests
    from thi_truong import nso
    g = lambda u: requests.get(u, headers={**UA, "Accept-Language": "vi"}, timeout=50).text   # noqa: E731
    B = "https://sbv.gov.vn/vi/"
    t = nso.chu(g(B + "can-can-thanh-toan-quoc-te"))
    i = t.find("A. Cán cân vãng lai")
    print("BoP:", t[max(0, i - 60):i + 1700])
    h = g(B + "thong-ke-mot-so-chi-tieu-co-ban")
    t = nso.chu(h)
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>\s*([^<]{0,90}(?:ROA|AN TOÀN VỐN|CHỈ TIÊU CƠ BẢN)[^<]{0,60})<', h):
        print("   liên kết:", m.group(2).strip()[:90], "→", m.group(1)[:140])
    for k in ("Tổng tài sản", "ROA", "Tỷ lệ an toàn vốn", "Tỷ lệ cấp tín dụng"):
        j = t.find(k, 2500)
        if j >= 0:
            print(f"   [{k}] {t[max(0, j - 150):j + 900]}")
    for d in ("ty-le-no-xau-trong-tong-du-no-tin-dung", "ty-le-du-no-cho-vay-so-voi-tong-tien-gui"):
        t = nso.chu(g(B + d))
        ks = [m.start() for m in re.finditer(r"\d,\d+ ?%|\d+,\d+", t)]
        j = next((x for x in ks if x > 3000), -1)
        print(f"   {d}: số đầu tiên sau đầu trang ở {j} · {t[max(0, j - 500):j + 500] if j >= 0 else t[3000:3600]}")


TQ12 = ("SHFE:RB1! SHFE:HC1! DCE:I1! DCE:J1! DCE:JM1! SHFE:RU1! ZCE:SR1! ZCE:CF1! ZCE:UR1! DCE:M1! DCE:C1! DCE:LH1! DCE:V1! "
        "DCE:L1! DCE:PP1! SHFE:AL1! SHFE:CU1! INE:SC1! ZCE:TA1! INDEX:BDI TVC:BDI").split()
# Hàng hoá → rổ mã ngành, dấu (+1: giá bán ra của ngành · −1: chi phí đầu vào). ĐẶT TRƯỚC khi chạy (26/11/2026).
CAP12 = [("hrc", "tv:COMEX:HRC1!", +1, "HPG HSG NKG"), ("thep_tq", "tv:SHFE:RB1!", +1, "HPG HSG NKG"),
         ("quang_sat", "tv:SGX:FEF1!", +1, "HPG HSG NKG"), ("brent", "yf:BZ=F", +1, "GAS PVS PVD BSR PLX"),
         ("khi", "yf:NG=F", +1, "GAS"), ("than", "tv:ICEEUR:NCF1!", +1, "TVD NBC"), ("cao_su", "tv:SGX:TF1!", +1, "GVR PHR DPR"),
         ("cao_su_tq", "tv:SHFE:RU1!", +1, "GVR PHR DPR"), ("ure", "tv:CBOT:UFV1!", +1, "DPM DCM"), ("ure_tq", "tv:ZCE:UR1!", +1, "DPM DCM"),
         ("duong", "yf:SB=F", +1, "SBT LSS QNS"), ("gao", "yf:ZR=F", +1, "LTG TAR"), ("heo", "yf:HE=F", +1, "DBC BAF"),
         ("heo_tq", "tv:DCE:LH1!", +1, "DBC BAF"), ("ngo", "yf:ZC=F", -1, "DBC BAF"), ("dau_tuong", "yf:ZS=F", -1, "DBC BAF"),
         ("bong", "yf:CT=F", -1, "TCM MSH"), ("pvc_tq", "tv:DCE:V1!", -1, "BMP NTP")]


def thang(s):
    """Chuỗi ngày → giá cuối tháng (chỉ mục ngày 1 của tháng)."""
    s = pd.Series(s).dropna()
    m = s.groupby(s.index.to_period("M")).last()
    m.index = m.index.to_timestamp()
    return m


def thu_tin_hieu(c, b, vni, dau, ky=3, chia="2020-01-01"):
    """c, b, vni: giá cuối tháng (hàng hoá, rổ ngành, VN-Index). Tín hiệu cuối tháng t: dau × lợi suất ky tháng của c > 0 → giữ rổ
    tháng t+1, ngược lại giữ VN-Index. → dict theo đoạn ("is" < chia ≤ "oos"): số tháng, tương quan cùng tháng / tháng sau,
    chênh lợi suất vượt VNI tháng có – không tín hiệu (%/tháng, t), lợi thế so luôn giữ rổ (%/năm)."""
    x = pd.concat({"c": c, "b": b, "v": vni}, axis=1).dropna()
    rc, rb, rv = x.c.pct_change(), x.b.pct_change(), x.v.pct_change()
    vuot = (rb - rv)                                                   # rổ vượt VN-Index trong tháng
    tin = (dau * x.c.pct_change(ky) > 0).astype(float)
    d = pd.DataFrame({"rc": rc, "vuot": vuot, "vuot_sau": vuot.shift(-1), "tin": tin}).dropna()
    out = {}
    for ten, k in (("is", d[d.index < chia]), ("oos", d[d.index >= chia])):
        on, off = k.vuot_sau[k.tin > 0], k.vuot_sau[k.tin == 0]
        ch = on.mean() - off.mean() if len(on) > 2 and len(off) > 2 else float("nan")
        se = (on.var(ddof=1) / len(on) + off.var(ddof=1) / len(off)) ** 0.5 if len(on) > 2 and len(off) > 2 else float("nan")
        out[ten] = {"n": len(k), "cung": k.rc.corr(k.vuot), "sau": (dau * k.rc).corr(k.vuot_sau),
                    "chenh": ch * 100, "t": ch / se if se else float("nan"),
                    "loi_the": ((k.tin * k.vuot_sau).mean() - k.vuot_sau.mean()) * 1200}
    return out


def dat12(r):
    """Tiêu chí đặt trước: chênh > 0 cả 2 đoạn, OOS t ≥ 1,5 và lợi thế OOS ≥ +3 %/năm."""
    i, o = r["is"], r["oos"]
    return bool(i["chenh"] > 0 and o["chenh"] > 0 and o["t"] >= 1.5 and o["loi_the"] >= 3)


def _gia_dai(thu, ma):
    """du_lieu/gia_dai/<MÃ>.json (bản sao lưu Tra cứu mã: d0 + g bước ngày + c đã điều chỉnh) → Series."""
    j = json.load(open(f"{thu}/du_lieu/gia_dai/{ma}.json", encoding="utf-8"))
    d = pd.Timestamp(j["d0"]) + pd.to_timedelta(np.cumsum(j["g"]), unit="D")
    return pd.Series(j["c"], index=d)


def do_vn12(cap=None, do_tq=True):
    """Vòng 12 (chủ quỹ: "kiếm thêm nguồn" + "giá hàng hoá so tương quan ngành có giúp mua bán không"): mã hàng hoá Trung Quốc /
    cước tàu trên TradingView; thử tín hiệu hàng hoá → rổ mã ngành (CAP12, tiêu chí dat12 đặt trước)."""
    import subprocess
    import tempfile
    import requests
    from thi_truong import vi_mo_web as W
    for ma in (TQ12 if do_tq else []):
        try:
            s = tv(ma, "1D").dropna()
            print(f"✔ {ma}: {len(s)} phiên {s.index[0]:%m/%Y}→{s.index[-1]:%d/%m/%Y} · cuối {s.iloc[-1]:,.6g}", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {ma}: {type(e).__name__} {str(e)[:50]}", flush=True)
    thu = tempfile.mkdtemp()
    f = f"{thu}/d.tar.zst"
    with requests.get("https://github.com/mihhle2006-beep/canh-bao-mua/releases/download/sao-luu-tra-cuu/du_lieu.tar.zst",
                      stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(f, "wb") as fp:
            for k in r.iter_content(1 << 20):
                fp.write(k)
    cap = cap or CAP12
    mas = sorted({m for x in cap for m in x[3].split()})
    subprocess.run(["tar", "--zstd", "-xf", f, "-C", thu, "du_lieu/chi_so/VNINDEX.json",
                    *[f"du_lieu/gia_dai/{m}.json" for m in mas]], check=False)
    j = json.load(open(f"{thu}/du_lieu/chi_so/VNINDEX.json", encoding="utf-8"))
    vni = thang(pd.Series(j["c"], index=pd.Timestamp(j["d0"]) + pd.to_timedelta(np.cumsum(j["g"]), unit="D")))
    gia = {}
    for m in mas:
        try:
            gia[m] = thang(_gia_dai(thu, m))
        except Exception as e:                                        # noqa: BLE001
            print(f"  ✘ {m}: {e}")
    print(f"\n=== Hàng hoá → rổ ngành (tháng, vượt VN-Index; IS < 2020 ≤ OOS) · đạt = chênh>0 cả 2 đoạn, OOS t≥1,5, lợi thế OOS ≥ +3%/năm ===")
    for k, ng, dau, ds, *ky in cap:
        try:
            c = thang(W._lay(ng, "2010-01-01"))
            r = pd.concat([gia[m].pct_change() for m in ds.split() if m in gia], axis=1).mean(axis=1, skipna=True)
            b = (1 + r.fillna(0)).cumprod()[r.notna().cumsum() > 0]
            x = thu_tin_hieu(c, b, vni, dau, ky=ky[0] if ky else 3)
            i, o = x["is"], x["oos"]
            print(f"  {'ĐẠT ' if dat12(x) else '  – '}{k:11s} {dau:+d} [{ds}] · cùng tháng {i['cung']:+.2f}/{o['cung']:+.2f} · tháng sau "
                  f"{i['sau']:+.2f}/{o['sau']:+.2f} · chênh {i['chenh']:+.2f}%/{o['chenh']:+.2f}% (t {i['t']:+.1f}/{o['t']:+.1f}) · lợi thế "
                  f"{i['loi_the']:+.1f}/{o['loi_the']:+.1f} %/năm · {i['n']}+{o['n']} tháng", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"  ✘ {k}: {type(e).__name__} {str(e)[:80]}", flush=True)


# Vòng 12 (26/11/2026) – KẾT QUẢ: 14/15 cặp KHÔNG đạt (hàng hoá đi CÙNG tháng với rổ ngành: dầu +0,39/+0,25, HRC OOS +0,30 –
# nhưng không báo trước tháng sau); chỉ đường → SBT/LSS/QNS đạt sát vạch (OOS t 1,5, lợi thế +3,5 %/năm). TradingView có ZCE
# (đường, bông, urê, PTA) + INDEX:BDI; không có SHFE / DCE / INE (resolve error).
# Vòng 13: cặp mới + ĐỘ BỀN cặp đường – đặt trước: coi là thật chỉ khi chênh > 0 cả 2 đoạn ở cả khung 1 / 3 / 6 tháng
# VÀ đường Trịnh Châu (ZCE) cùng chiều.
CAP13 = [("bdi", "tv:INDEX:BDI", +1, "HAH VOS VSC GMD PVT"), ("duong_tq", "tv:ZCE:SR1!", +1, "SBT LSS QNS"),
         ("bong_tq", "tv:ZCE:CF1!", -1, "TCM MSH"), ("pta_tq", "tv:ZCE:TA1!", -1, "TCM MSH STK"), ("ure_tq", "tv:ZCE:UR1!", +1, "DPM DCM"),
         ("duong_k1", "yf:SB=F", +1, "SBT LSS QNS", 1), ("duong_k6", "yf:SB=F", +1, "SBT LSS QNS", 6),
         ("bdi_k1", "tv:INDEX:BDI", +1, "HAH VOS VSC GMD PVT", 1)]


# Vòng 13 – KẾT QUẢ: đường → SBT/LSS/QNS BỀN (chênh > 0 cả 2 đoạn ở khung 1 / 3 / 6 tháng: IS +1,3 / +3,9 / +0,8, OOS +2,3 / +2,4 /
# +1,9 %/tháng; đường ZCE cùng chiều +3,2 / +0,9) – OOS t chỉ 1,2–1,5. BDI → HAH/VOS/VSC/GMD/PVT không đạt (OOS lợi thế −9,1 %/năm,
# khung 1 tháng âm); bông / PTA / urê ZCE không đạt. → hiển thị ghi chú ở trang, KHÔNG đưa vào lệnh (chưa hỏi chủ quỹ).


# Vòng 14 (chủ quỹ: "coi xem có dùng làm gì được không"): biến động ĐÊM QUA (phiên Mỹ/Âu chốt sau giờ VN đóng cửa) → cổ phiếu ngành
# PHIÊN SAU, tách khe mở cửa (đóng D → mở D+1) và trong phiên (mở → đóng D+1). Tiêu chí ĐẶT TRƯỚC:
#   (A) đưa vào tin sáng: OOS tương quan (biến động đêm qua, vượt VNI cả phiên sau) ≥ 0,08 và t ≥ 3
#   (B) giao dịch được: ngày |z| > 2 (z = biến động / độ lệch 60 phiên), OOS trung bình dấu×(vượt VNI TRONG PHIÊN mở→đóng) ≥ 0,3 %
#       với t ≥ 2, cùng dấu IS
CAP14 = [("brent", "yf:BZ=F", "GAS PVS PVD BSR PLX"), ("wti", "yf:CL=F", "GAS PVS PVD BSR PLX"), ("hrc", "tv:COMEX:HRC1!", "HPG HSG NKG"),
         ("duong", "yf:SB=F", "SBT LSS QNS"), ("dong", "yf:HG=F", "HPG HSG NKG"), ("cao_su", "tv:SGX:TF1!", "GVR PHR DPR"),
         ("ure", "tv:CBOT:UFV1!", "DPM DCM"), ("than", "tv:ICEEUR:NCF1!", "TVD NBC"), ("heo", "yf:HE=F", "DBC BAF"),
         ("sp500", "yf:^GSPC", ""), ("vix", "yf:^VIX", ""), ("dxy", "yf:DX-Y.NYB", "")]


def thu_dem(c, o, cl, vo, vc, chia="2020-01-01"):
    """c: giá đóng cửa hàng hoá (ngày giao dịch của nó); o, cl: giá mở / đóng rổ (ngày VN, rổ = trung bình lợi suất); vo, vc: VN-Index.
    Tín hiệu phiên VN ngày T = lợi suất hàng hoá ngày gần nhất TRƯỚC T (chốt sau giờ VN đóng cửa). Rổ rỗng (o None) → dùng VN-Index tuyệt đối.
    → {is, oos: n, tq (tương quan với vượt cả phiên), t_tq, lon_n, lon_ngay (dấu×vượt cả phiên ngày |z|>2, %), lon_trong (… mở→đóng, %), t_trong}."""
    rc = c.pct_change().dropna()
    z = (rc / rc.rolling(60).std()).dropna()
    s = pd.DataFrame({"rc": rc, "z": z}).dropna()
    s.index = s.index + pd.Timedelta(hours=12)                        # ngày hàng hoá D chốt đêm D (giờ VN) → dùng cho phiên sau D
    if o is None:
        ca, tr = vc.pct_change(), vc / vo - 1
    else:
        ca, tr = cl.pct_change() - vc.pct_change(), (cl / o - 1) - (vc / vo - 1)
    v = pd.DataFrame({"ca": ca, "tr": tr}).dropna().sort_index()
    m = pd.merge_asof(v, s.sort_index(), left_index=True, right_index=True, direction="backward",
                      tolerance=pd.Timedelta(days=4)).dropna()
    out = {}
    for ten, k in (("is", m[m.index < chia]), ("oos", m[m.index >= chia])):
        r = k.rc.corr(k.ca)
        lon = k[k.z.abs() > 2]
        x, y = np.sign(lon.rc) * lon.ca * 100, np.sign(lon.rc) * lon.tr * 100
        out[ten] = {"n": len(k), "tq": r, "t_tq": r * (len(k) - 2) ** 0.5 / max(1e-9, (1 - r * r) ** 0.5), "lon_n": len(lon),
                    "lon_ngay": x.mean(), "lon_trong": y.mean(), "t_trong": y.mean() / (y.std(ddof=1) / len(y) ** 0.5) if len(y) > 2 else float("nan")}
    return out


def dat14(r):
    i, o = r["is"], r["oos"]
    return (bool(o["tq"] >= 0.08 and o["t_tq"] >= 3), bool(o["lon_trong"] >= 0.3 and o["t_trong"] >= 2 and i["lon_trong"] > 0))


def do_vn14():
    import subprocess
    import tempfile
    import requests
    from thi_truong import vi_mo_web as W
    thu = tempfile.mkdtemp()
    f = f"{thu}/d.tar.zst"
    with requests.get("https://github.com/mihhle2006-beep/canh-bao-mua/releases/download/sao-luu-tra-cuu/du_lieu.tar.zst",
                      stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(f, "wb") as fp:
            for k in r.iter_content(1 << 20):
                fp.write(k)
    mas = sorted({m for *_, ds in CAP14 for m in ds.split()})
    subprocess.run(["tar", "--zstd", "-xf", f, "-C", thu, "du_lieu/chi_so/VNINDEX.json", *[f"du_lieu/gia_dai/{m}.json" for m in mas]],
                   check=False)

    def doc(p):
        j = json.load(open(p, encoding="utf-8"))
        d = pd.Timestamp(j["d0"]) + pd.to_timedelta(np.cumsum(j["g"]), unit="D")
        return pd.Series(j["o"], index=d, dtype=float), pd.Series(j["c"], index=d, dtype=float)
    vo, vc = doc(f"{thu}/du_lieu/chi_so/VNINDEX.json")
    print("\n=== Biến động ĐÊM QUA → phiên VN sau (IS < 2020 ≤ OOS) · A: tq OOS ≥ 0,08 & t ≥ 3 · B: ngày |z|>2 trong phiên ≥ 0,3 % & t ≥ 2 ===")
    for k, ng, ds in CAP14:
        try:
            c = W._lay(ng, "2010-01-01").dropna()
            if ds:
                oc = [doc(f"{thu}/du_lieu/gia_dai/{m}.json") for m in ds.split()]
                ro = pd.concat([x[1] / x[0] - 1 for x in oc], axis=1).mean(axis=1)     # mở → đóng trung bình rổ
                rcl = pd.concat([x[1].pct_change() for x in oc], axis=1).mean(axis=1)   # đóng → đóng
                cl = (1 + rcl.fillna(0)).cumprod()
                o = cl / (1 + ro)                                                # giá mở "rổ" sao cho cl/o − 1 = mở→đóng trung bình
                x = thu_dem(c, o, cl, vo, vc)
            else:
                x = thu_dem(c, None, None, vo, vc)
            a, b = dat14(x)
            i, oo = x["is"], x["oos"]
            print(f"  {'A' if a else '-'}{'B' if b else '-'} {k:6s} [{ds or 'VN-Index'}] · tương quan {i['tq']:+.3f}/{oo['tq']:+.3f} (t {i['t_tq']:+.1f}/"
                  f"{oo['t_tq']:+.1f}) · ngày lớn {i['lon_n']}/{oo['lon_n']}: cả phiên {i['lon_ngay']:+.2f}/{oo['lon_ngay']:+.2f}% · trong phiên "
                  f"{i['lon_trong']:+.2f}/{oo['lon_trong']:+.2f}% (t {i['t_trong']:+.1f}/{oo['t_trong']:+.1f})", flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"  ✘ {k}: {type(e).__name__} {str(e)[:80]}", flush=True)


# Vòng 14 – KẾT QUẢ (tương quan IS/OOS · ngày |z|>2: trong phiên mở→đóng IS/OOS):
#   A ĐẠT: Brent → dầu khí +0,22/+0,26 (trong phiên −0,15/+0,09 % – đã vào giá mở cửa) · WTI +0,25/+0,15 · đường → SBT/LSS/QNS
#   +0,02/+0,17 (trong phiên +0,20/+0,43 %, t 1,5/2,9 → B ĐẠT) · than → TVD/NBC 0,00/+0,16 (trong phiên +0,68 % t 1,9) · S&P 500 →
#   VN-Index +0,21/+0,23 (OOS trong phiên ĐẢO −0,61 % t −4,5, IS +0,05 – không bền) · VIX −0,20/−0,14, DXY −0,05/−0,11 (ngược dấu).
#   KHÔNG: HRC, đồng, cao su, urê, heo (|tương quan| ≤ 0,05). → canh_bao/dem_qua: tin trước phiên khi biến động mạnh (thông tin).


# Vòng 15 (chủ quỹ: "có làm được backtest chưa") – BACKTEST chiến lược đường, ĐẶT TRƯỚC khi chạy:
#   cuối tháng: đường (Yahoo SB=F) k tháng tăng → phiên đầu tháng sau MUA ATO SBT + LSS (chia đều, QNS bỏ – UPCoM), giữ cả tháng;
#   không thì tiền mặt (0 %). Phí mua 0,35 % (0,15 môi giới + 0,2 trượt), bán 0,45 % (+0,1 thuế). Giá mở cửa đã điều chỉnh.
#   C1: k=3 CAGR > giữ luôn SBT+LSS VÀ Sharpe > giữ luôn và > VN-Index; k=1, k=6 cũng CAGR > giữ luôn.
#   C2: k=3 lợi suất > giữ luôn ở 4/4 đoạn 2012–15 · 2016–19 · 2020–22 · 2023–26. Chỉ đề xuất khi đạt cả C1 + C2.
DOAN15 = [("2012", "2015"), ("2016", "2019"), ("2020", "2022"), ("2023", "2026")]


def mo_dau_thang(o):
    """Giá mở cửa ngày → giá mở cửa PHIÊN ĐẦU mỗi tháng (chỉ mục ngày 1)."""
    o = pd.Series(o).dropna()
    m = o.groupby(o.index.to_period("M")).first()
    m.index = m.index.to_timestamp()
    return m


def bt_tin_hieu(r_ro, tin, mua=0.0035, ban=0.0045):
    """r_ro: lợi suất tháng của rổ (mở cửa đầu tháng → đầu tháng sau, chỉ mục = tháng nắm giữ); tin: 1/0 cho tháng nắm giữ (đã biết
    trước khi mở cửa). → lợi suất tháng của chiến lược sau phí (vào: trừ phí mua tháng đó; ra: trừ phí bán ở tháng đầu tiên không giữ)."""
    x = pd.DataFrame({"r": r_ro, "t": tin}).dropna()
    t_truoc = x.t.shift(1).fillna(0)
    out = x.t * x.r - mua * ((x.t == 1) & (t_truoc == 0)) - ban * ((x.t == 0) & (t_truoc == 1))
    return out


def chi_so_bt(r):
    """Lợi suất tháng → (CAGR %, biến động năm %, Sharpe, sụt giảm lớn nhất %)."""
    r = pd.Series(r).dropna()
    if len(r) < 6:
        return (float("nan"),) * 4
    g = (1 + r).cumprod()
    cagr = g.iloc[-1] ** (12 / len(r)) - 1
    vol = r.std(ddof=1) * 12 ** 0.5
    return round(cagr * 100, 1), round(vol * 100, 1), round(r.mean() * 12 / vol, 2) if vol else float("nan"), round((g / g.cummax() - 1).min() * 100, 1)


def do_vn15():
    import subprocess
    import tempfile
    import requests
    from thi_truong import vi_mo_web as W
    thu = tempfile.mkdtemp()
    f = f"{thu}/d.tar.zst"
    with requests.get("https://github.com/mihhle2006-beep/canh-bao-mua/releases/download/sao-luu-tra-cuu/du_lieu.tar.zst",
                      stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(f, "wb") as fp:
            for k in r.iter_content(1 << 20):
                fp.write(k)
    mas = ["SBT", "LSS"]
    subprocess.run(["tar", "--zstd", "-xf", f, "-C", thu, "du_lieu/chi_so/VNINDEX.json", *[f"du_lieu/gia_dai/{m}.json" for m in mas],
                    *[f"du_lieu/gia/{m}.json" for m in mas]], check=False)

    def mo(p):
        j = json.load(open(p, encoding="utf-8"))
        return mo_dau_thang(pd.Series(j["o"], index=pd.Timestamp(j["d0"]) + pd.to_timedelta(np.cumsum(j["g"]), unit="D"), dtype=float))
    vni = mo(f"{thu}/du_lieu/chi_so/VNINDEX.json")
    rv = (vni.shift(-1) / vni - 1).dropna()
    ro = pd.concat([(lambda x: x.shift(-1) / x - 1)(mo(f"{thu}/du_lieu/gia_dai/{m}.json")) for m in mas], axis=1).mean(axis=1).dropna()
    ro, rv = ro[ro.index >= "2012-01-01"], rv[rv.index >= "2012-01-01"]
    for m in mas:
        try:
            j = json.load(open(f"{thu}/du_lieu/gia/{m}.json", encoding="utf-8"))
            gt = pd.Series(j["gt"][-250:], dtype=float)
            print(f"  thanh khoản {m}: GTGD trung vị 250 phiên {gt.median():.1f} tỷ/phiên (thấp nhất 10 % phiên: {gt.quantile(.1):.1f} tỷ)")
        except Exception as e:                                        # noqa: BLE001
            print(f"  thanh khoản {m}: {e}")
    c = thang(W._lay("yf:SB=F", "2010-01-01"))
    print("\n=== BACKTEST đường → SBT + LSS (tháng, mua ATO đầu tháng, phí mua 0,35 % · bán 0,45 %) ===")
    print(f"  giữ luôn SBT+LSS: CAGR/biến động/Sharpe/sụt giảm {chi_so_bt(ro)} · VN-Index {chi_so_bt(rv)} · {len(ro)} tháng")
    kq = {}
    for k in (1, 3, 6):
        tin = (c.pct_change(k) > 0).astype(float)
        tin.index = tin.index + pd.offsets.MonthBegin(1)                 # tín hiệu cuối tháng m → giữ tháng m+1
        r = bt_tin_hieu(ro, tin.reindex(ro.index))
        kq[k] = r
        n_lenh = int(((tin.reindex(ro.index).fillna(0).diff().abs()) > 0).sum())
        print(f"  k={k}: {chi_so_bt(r)} · giữ {tin.reindex(ro.index).mean() * 100:.0f} % số tháng · {n_lenh} lần vào/ra")
    bh, st = chi_so_bt(ro), {k: chi_so_bt(v) for k, v in kq.items()}
    c1 = st[3][0] > bh[0] and st[3][2] > bh[2] and st[3][2] > chi_so_bt(rv)[2] and st[1][0] > bh[0] and st[6][0] > bh[0]
    doan = []
    for a_, b_ in DOAN15:
        s3, sb, sv = (x[(x.index >= f"{a_}-01-01") & (x.index <= f"{b_}-12-31")] for x in (kq[3], ro, rv))
        doan.append(((1 + s3).prod() - 1, (1 + sb).prod() - 1, (1 + sv).prod() - 1))
        print(f"  {a_}–{b_}: chiến lược {doan[-1][0] * 100:+.0f} % · giữ luôn {doan[-1][1] * 100:+.0f} % · VN-Index {doan[-1][2] * 100:+.0f} %")
    c2 = sum(x[0] > x[1] for x in doan)
    print(f"  → C1 {'ĐẠT' if c1 else 'KHÔNG'} · C2 {c2}/4 {'ĐẠT' if c2 == 4 else 'KHÔNG'}")


# Vòng 15 – KẾT QUẢ (178 tháng 2012–2026, sau phí; CAGR / biến động / Sharpe / sụt giảm): giữ luôn SBT+LSS 7,3 / 32,4 / 0,38 / −63 % ·
#   VN-Index 11,4 / 19,9 / 0,64 / −44 % · k=1 6,2 / 25,6 / 0,36 / −63 % · k=3 9,6 / 25,4 / 0,49 / −40 % (giữ 43 % số tháng, 47 lần vào/ra)
#   · k=6 8,2 / 24,5 / 0,44 / −46 %. Đoạn k=3 vs giữ luôn: 2012–15 +71/+38 · 2016–19 +26/−4 · 2020–22 +46/+19 · 2023–26 +23/+81.
#   → C1 KHÔNG (Sharpe < VN-Index, k=1 < giữ luôn) · C2 3/4 KHÔNG (thua 2023–26) → KHÔNG đề xuất. Tín hiệu đường làm rổ đỡ tệ hơn
#   (sụt giảm −63 → −40 %) nhưng rổ đường quá yếu – vẫn kém giữ VN-Index. Ghi chú trang sửa theo kết luận này.


# Vòng 16 (chủ quỹ: "cải thiện bộ forecast… có chỉ số nào dùng được nữa không"): in GIÁ TRUNG BÌNH THÁNG 2010 → nay của các hàng
# hoá đã gắn mã ngành (CAP12/13) + lãi suất / tín dụng TradingView ECONOMICS → chép về máy, kiểm dự phóng LNST (danh-muc ptcp/
# du_phong) có / không điều chỉnh theo giá hàng hoá. Số công khai – không đọc danh mục.
HH16 = [("hrc", "tv:COMEX:HRC1!"), ("quang_sat", "tv:SGX:FEF1!"), ("brent", "yf:BZ=F"), ("khi", "yf:NG=F"), ("than", "tv:ICEEUR:NCF1!"),
        ("cao_su", "tv:SGX:TF1!"), ("ure", "tv:CBOT:UFV1!"), ("ure_tq", "tv:ZCE:UR1!"), ("duong", "yf:SB=F"), ("gao", "yf:ZR=F"),
        ("heo", "yf:HE=F"), ("ngo", "yf:ZC=F"), ("dau_tuong", "yf:ZS=F"), ("bong", "yf:CT=F"), ("pta", "tv:ZCE:TA1!"),
        ("bdi", "tv:INDEX:BDI"), ("dong", "yf:HG=F"), ("nhom", "yf:ALI=F"), ("vang", "yf:GC=F"), ("ca_phe", "yf:KC=F")]
KT16 = "VNLTPS VNIBR VNBLR VNDR VNIPMM VNRSMM VNCC VNBC VNEXPP VNIMPP VNHPI".split()


def do_vn16():
    from thi_truong import vi_mo_web as W
    for k, ng in HH16:
        try:
            s = W._lay(ng, "2010-01-01").dropna()
            m = s.groupby(s.index.to_period("M")).mean()
            print(f"HH16 {k} {m.index[0]} " + ",".join(f"{v:.5g}" for v in m.values), flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {k}: {type(e).__name__} {str(e)[:60]}", flush=True)
    for ma in KT16:
        try:
            s = tv("ECONOMICS:" + ma, "1M").dropna()
            print(f"KT16 {ma} {s.index[0]:%Y-%m} {s.index[-1]:%Y-%m} " + ",".join(f"{v:.5g}" for v in s.values[-200:]), flush=True)
        except Exception as e:                                        # noqa: BLE001
            print(f"✘ {ma}: {type(e).__name__} {str(e)[:60]}", flush=True)


# Vòng 17 (26/11/2026) – KẾT QUẢ kiểm ĐẶT TRƯỚC H2 (dự phóng LNST năm của web + điều chỉnh phần quý còn lại theo giá hàng hoá
# đã có tới ngày dự phóng, 9 nhóm mã: HRC, Brent, cao su, urê, đường, gạo, heo, bông; β học 2013–2020, kiểm 2021–2025):
# β +0,49 (t 1,95 – trượt B1), sai số trung vị 2021–25 gốc 24,6 % → điều chỉnh 25,2 % (xấu hơn), 4/5 năm, 5/8 nhóm → KHÔNG ĐẠT.
# Giá hàng hoá không làm dự phóng LNST sát hơn (thông tin đã nằm trong các quý vừa công bố). Mã thử + bảng gốc đã xoá.


def do_vn18():
    """Vòng 18: ROA / ROE NHNN theo quý (đệm roa.csv) – xem số là quy năm hay lũy kế từ đầu năm (so sánh với ROE mã trên web)."""
    import os
    from thi_truong import vi_mo_web as W
    f = os.path.join(W.DEM, "roa.csv")
    print(open(f, encoding="utf-8").read() if os.path.exists(f) else "không có " + f, flush=True)


def main():
    do_vn18()
    return 0


def do_cu():
    """Vòng 1 (đã kết luận – vi_mo_web): ngày nến + ứng viên vàng / hàng hoá / lãi suất."""
    kiem_ngay()
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
