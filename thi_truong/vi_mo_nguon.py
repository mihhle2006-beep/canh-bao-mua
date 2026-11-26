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


def main():
    do_vn4()
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
