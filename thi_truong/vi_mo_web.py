# -*- coding: utf-8 -*-
"""
VĨ MÔ CHO WEB – tab "Vĩ mô" ở Bảng thị trường (25/11/2026, chủ quỹ: "có nguồn XAUUSD thì làm bộ up giá lên web, biểu đồ,
tab vĩ mô"). Tham khảo, KHÔNG phải tín hiệu mua bán (danh-muc T2 5 vòng: vĩ mô / lãi suất không giúp canh mua bán).
Nguồn (mỗi chuỗi có dự phòng; lỗi hết → đệm cache_du_lieu/vi_mo):
  Vàng thế giới XAU/USD   TradingView OANDA:XAUUSD (giao ngay; so chéo TVC:GOLD tương quan 0,977, lệch 0,03 %) → yfinance GC=F
                          (COMEX); nến giờ 1 tháng: TradingView OANDA 60' → GC=F 60'; giá ngay: Swissquote (giữa mua–bán)
  Vàng SJC / nhẫn 9999    vang.today (giá CUỐI ngày từng ngày)
  USD/VND · DXY           yfinance VND=X · DX-Y.NYB; tỷ giá Vietcombank (chuyển khoản / bán) cho thẻ
  Lãi suất VN             thi_truong/lai_suat (chép danh-muc ptcp/lai_suat_vn): TPCP 1N / 10N HNX (chính thức, từ 2014), lãi điều hành / liên ngân hàng / lạm
                          phát (TradingView ECONOMICS, gốc NHNN / TCTK – theo tháng)
  Mỹ                      NY Fed (Fed funds thực tế, trần mục tiêu, SOFR), Bộ Tài chính Mỹ (lợi suất 2N / 10N, lợi suất thực 10N),
                          CPI so cùng kỳ (BLS chính thức + TradingView ECONOMICS:USIRYY cho lịch sử), VIX (TradingView → Yahoo)
  Kinh tế VN              TradingView ECONOMICS (gốc TCTK / NHNN): GDP, SXCN, bán lẻ, lạm phát lõi, xuất khẩu, cán cân TM, FDI,
                          dự trữ ngoại hối
  Hàng hoá (22 loại)      HANG_HOA: Yahoo hợp đồng tương lai gần nhất / TradingView – mỗi loại có dự phòng thì SO CHÉO 2 nguồn
                          (in log). Dò nguồn 25/11/2026: thi_truong/vi_mo_nguon. Ngày nến TradingView: lai_suat.TV_BU_GIO (đã sửa
                          lệch 1 ngày).
Giá trực tiếp trên trang: thử nguồn cho phép trình duyệt gọi thẳng (CORS) → ghi vào "song"; không có thì dùng số lúc dựng.
→ docs/vi_mo/du_lieu.json (+ hang_hoa.json: chuỗi giá hàng hoá, trang tải khi vẽ biểu đồ). Chạy: python -m thi_truong.vi_mo_web --ra docs/vi_mo
"""
import argparse
import io
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

VN = timezone(timedelta(hours=7))
DEM = os.path.join("cache_du_lieu", "vi_mo")
LUONG_OZ = 37.5 / 31.1034768                       # 1 lượng = 37,5 g; 1 oz troy = 31,1034768 g
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"}
GOC_WEB = "https://mihhle2006-beep.github.io"
SONG = [("https://api.gold-api.com/price/XAU", "gold_api"),
        ("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", "swissquote")]
NHOM = {"vang": "Vàng", "hh": "Bạc · dầu", "ls_vn": "Lãi suất Việt Nam", "vn": "Kinh tế Việt Nam", "my": "Mỹ",
        "ty_gia": "Tỷ giá"}
NHOM_HH = {"kl": "Kim loại", "nl": "Năng lượng", "ns": "Nông sản · phân bón"}
# Hàng hoá: (khoá, nhóm, tên, đơn vị, nguồn theo thứ tự ưu tiên – "tv:MÃ" TradingView / "yf:MÃ" Yahoo, ngành / mã VN liên quan).
# Kim loại quý: giá giao ngay (như XAU); còn lại hợp đồng tương lai gần nhất (nối liên tục – có bước nhảy nhỏ khi đổi kỳ hạn).
# Dò 25/11/2026 (vi_mo_nguon): bỏ LBMA (403), Stooq (trả HTML), Yahoo RC=F (rỗng), MTF=F (than Rotterdam, ngừng 12/2025).
HANG_HOA = [
    ("bac", "kl", "Bạc XAG/USD", "USD/oz", ["tv:OANDA:XAGUSD", "yf:SI=F"], ""),
    ("bach_kim", "kl", "Bạch kim", "USD/oz", ["tv:TVC:PLATINUM", "yf:PL=F"], ""),
    ("dong", "kl", "Đồng (COMEX)", "USD/lb", ["yf:HG=F", "tv:COMEX:HG1!"], "dây cáp điện"),
    ("nhom", "kl", "Nhôm", "USD/tấn", ["tv:CAPITALCOM:ALUMINUM"], "nhôm định hình"),
    ("quang_sat", "kl", "Quặng sắt 62 % (SGX)", "USD/tấn", ["tv:SGX:FEF1!", "yf:TIO=F"], "thép: HPG, HSG, NKG"),
    ("hrc", "kl", "Thép cuộn HRC (Mỹ)", "USD/tấn ngắn", ["tv:COMEX:HRC1!", "yf:HRC=F"], "thép: HPG, HSG, NKG"),
    ("brent", "nl", "Dầu Brent", "USD/thùng", ["yf:BZ=F", "tv:TVC:UKOIL"], "dầu khí: GAS, PLX, PVS, PVD, BSR"),
    ("wti", "nl", "Dầu WTI", "USD/thùng", ["yf:CL=F", "tv:TVC:USOIL"], ""),
    ("khi", "nl", "Khí tự nhiên (Henry Hub)", "USD/MMBtu", ["yf:NG=F", "tv:NYMEX:NG1!"], "GAS"),
    ("xang", "nl", "Xăng RBOB (Mỹ)", "USD/gallon", ["yf:RB=F"], "PLX, OIL"),
    ("than", "nl", "Than Newcastle", "USD/tấn", ["tv:ICEEUR:NCF1!"], "than: TVD, NBC · điện than: PPC, QTP"),
    ("robusta", "ns", "Cà phê Robusta (London)", "USD/tấn", ["tv:ICEEUR:RC1!"], "cà phê xuất khẩu"),
    ("arabica", "ns", "Cà phê Arabica (New York)", "US cent/lb", ["yf:KC=F"], ""),
    ("cao_su", "ns", "Cao su TSR20 (SGX)", "US cent/kg", ["tv:SGX:TF1!"], "GVR, PHR, DPR, DRI"),
    ("gao", "ns", "Gạo thô (CBOT)", "USD/cwt", ["yf:ZR=F"], "LTG, TAR"),
    ("duong", "ns", "Đường thô", "US cent/lb", ["yf:SB=F"], "SBT, LSS, QNS"),
    ("bong", "ns", "Bông", "US cent/lb", ["yf:CT=F"], "dệt may: TCM, STK, MSH"),
    ("ngo", "ns", "Ngô", "US cent/giạ", ["yf:ZC=F"], "thức ăn chăn nuôi: DBC, BAF"),
    ("dau_tuong", "ns", "Đậu tương", "US cent/giạ", ["yf:ZS=F"], "thức ăn chăn nuôi: DBC, BAF"),
    ("lua_mi", "ns", "Lúa mì", "US cent/giạ", ["yf:ZW=F"], ""),
    ("heo", "ns", "Heo nạc (Mỹ)", "US cent/lb", ["yf:HE=F"], "DBC, BAF"),
    ("ure", "ns", "Urê (vịnh Mỹ)", "USD/tấn ngắn", ["tv:CBOT:UFV1!"], "phân bón: DPM, DCM"),
]
THE_HH = ("bac", "brent", "wti")              # thẻ đầu trang (nhóm "Bạc · dầu"); đủ 22 loại ở bảng Hàng hoá
# Kinh tế VN (TradingView ECONOMICS, theo tháng / quý): (khoá, mã, tên, đơn vị, chia, kiểu đổi, kỳ so). Đã kiểm 15 kỳ cuối
# 25/11/2026: xuất khẩu, cán cân TM là số TỪNG THÁNG (không tụt về tháng 1); GDP theo quý; dự trữ là số dư.
VM_VN = [("vn_gdp", "ECONOMICS:VNGDPYY", "GDP (so cùng kỳ)", "%", 1, "đ", "quý trước"),
         ("vn_sxcn", "ECONOMICS:VNIPYY", "Sản xuất công nghiệp (so cùng kỳ)", "%", 1, "đ", "tháng trước"),
         ("vn_banle", "ECONOMICS:VNRSYY", "Bán lẻ (so cùng kỳ)", "%", 1, "đ", "tháng trước"),
         ("vn_cpi_loi", "ECONOMICS:VNCIR", "Lạm phát lõi", "%", 1, "đ", "tháng trước"),
         ("vn_xk", "ECONOMICS:VNEXP", "Xuất khẩu (tháng)", "tỷ USD", 1e9, "%", "tháng trước"),
         ("vn_bot", "ECONOMICS:VNBOT", "Cán cân thương mại (tháng)", "tỷ USD", 1e9, "đ", "tháng trước"),
         # FDI: CỘNG DỒN từ đầu năm (kiểm 25/11/2026: 12/2025 27,62 tỷ = giải ngân cả năm 2025, 01/2026 tụt về 1,68) → so cùng kỳ
         ("vn_fdi", "ECONOMICS:VNFDI", "FDI giải ngân (cộng dồn năm)", "tỷ USD", 1e9, "%", "cùng kỳ năm trước"),
         ("vn_dtnh", "ECONOMICS:VNFER", "Dự trữ ngoại hối", "tỷ USD", 1e9, "%", "tháng trước")]


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
    if khung == "1d":     # ngày THEO GIỜ SÀN (VND=X múi London: nửa đêm giờ hè = 23 h UTC hôm trước – đổi UTC sẽ lùi 1 ngày)
        df.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
    else:
        df.index = idx.tz_convert("UTC").tz_localize(None) if idx.tz is not None else idx
    return df[["open", "high", "low", "close"]].astype(float).dropna(subset=["close"])


def _tv(sym, khung="1D", n=5000, giu_gio=False):
    """TradingView (thi_truong/lai_suat – ngày nến đã sửa, TV_BU_GIO) → DataFrame open/high/low/close."""
    from thi_truong import lai_suat as LS
    df, loi = LS.tv_lich_su(sym, khung, n, giu_gio=giu_gio)
    if df is None or not len(df):
        raise ValueError(f"TradingView {sym}: {loi[:80]}")
    return df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close"})[["open", "high", "low", "close"]]


def _lay(nguon, tu="2010-01-01"):
    """ "tv:MÃ" | "yf:MÃ" → Series giá đóng cửa theo ngày."""
    loai, ma = nguon.split(":", 1)
    if loai == "tv":
        s = _tv(ma)["close"]
        return s[s.index >= pd.Timestamp(tu)]
    df = _yf(ma, tu)
    if df is None:
        raise ValueError(f"Yahoo {ma} rỗng")
    return df["close"]


def ten_nguon(nguon):
    loai, ma = nguon.split(":", 1)
    return ("TradingView " if loai == "tv" else "Yahoo ") + ma


def so_cheo(a, b, nam=3):
    """2 nguồn cùng một chuỗi (3 năm gần nhất) → (số ngày trùng, tương quan thay đổi ngày, lệch mức trung vị %) – kiểm nguồn."""
    x = pd.concat([pd.Series(a, dtype=float), pd.Series(b, dtype=float)], axis=1, join="inner").dropna()
    if len(x):
        x = x[x.index >= x.index.max() - pd.DateOffset(years=nam)]
    if len(x) < 30:
        return len(x), None, None
    r = x.pct_change().dropna()
    return (len(x), round(float(r.iloc[:, 0].corr(r.iloc[:, 1])), 3),
            round(float((x.iloc[:, 0] / x.iloc[:, 1] - 1).abs().median() * 100), 2))


def xau_ngay(tu="2010-01-01"):
    """XAU/USD theo ngày → (DataFrame open/high/low/close, nguồn): TradingView OANDA (giao ngay) → yfinance GC=F (COMEX)."""
    try:
        df = _tv("OANDA:XAUUSD")
        df = df[df.index >= pd.Timestamp(tu)]
        if len(df) > 500:
            return df, "TradingView OANDA:XAUUSD (giao ngay)"
    except Exception as e:                                            # noqa: BLE001 – nguồn sau
        print(f"  ⚠ TradingView XAU: {type(e).__name__} {str(e)[:60]}")
    df = _yf("GC=F", tu)
    if df is None:
        raise ValueError("không lấy được XAU/USD")
    return df, "COMEX GC=F (hợp đồng tương lai, yfinance)"


def xau_gio():
    """Nến giờ ~1 tháng (mốc UTC): TradingView OANDA 60' → yfinance GC=F 60'."""
    try:
        df = _tv("OANDA:XAUUSD", "60", 800, giu_gio=True)
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=31)]
        if len(df) > 100:
            return df, "TradingView OANDA:XAUUSD 60'"
    except Exception as e:                                            # noqa: BLE001 – nguồn sau
        print(f"  ⚠ TradingView XAU 60': {type(e).__name__} {str(e)[:60]}")
    return _yf("GC=F", khung="60m", ky="1mo"), "COMEX GC=F 60' (yfinance)"


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


def sofr(tu="2018-04-02"):
    """NY Fed (chính thức) – SOFR theo ngày, %."""
    j = _get("https://markets.newyorkfed.org/api/rates/secured/sofr/search.json",
             params={"startDate": tu, "endDate": f"{pd.Timestamp.today():%Y-%m-%d}"}, timeout=60).json()
    d = pd.DataFrame(j.get("refRates", []))
    return pd.Series(pd.to_numeric(d["percentRate"], errors="coerce").values,
                     index=pd.to_datetime(d["effectiveDate"])).dropna().sort_index()


def cpi_my():
    """Lạm phát Mỹ so cùng kỳ % theo tháng: BLS (chính thức, ~3 năm gần nhất, CPI-U chưa điều chỉnh mùa vụ) nối lịch sử TradingView
    ECONOMICS:USIRYY (gốc BLS) trước đó. In độ lệch các tháng trùng – kiểm 2 nguồn."""
    import re
    bls = None
    try:
        j = _get("https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0").json()
        ds = j["Results"]["series"][0]["data"]
        cs = pd.Series({pd.Timestamp(f"{x['year']}-{x['period'][1:]}-01"): float(x["value"]) for x in ds
                        if x["period"].startswith("M") and x["period"] != "M13"
                        and re.fullmatch(r"-?[\d.]+", str(x["value"]))}).sort_index()
        bls = ((cs / cs.reindex(cs.index - pd.DateOffset(years=1)).values - 1) * 100).dropna().round(2)
    except Exception as e:                                            # noqa: BLE001 – còn TradingView
        print(f"  ⚠ BLS: {type(e).__name__} {str(e)[:60]}")
    tv = None
    try:
        tv = _tv("ECONOMICS:USIRYY", "1M")["close"]
    except Exception as e:                                            # noqa: BLE001
        print(f"  ⚠ TradingView USIRYY: {type(e).__name__} {str(e)[:60]}")
    if bls is not None and len(bls) and tv is not None:
        x = pd.concat([bls, tv], axis=1, join="inner").dropna()
        if len(x):
            print(f"  kiểm CPI Mỹ: BLS ↔ TradingView {len(x)} tháng trùng · lệch lớn nhất {(x.iloc[:, 0] - x.iloc[:, 1]).abs().max():.2f}"
                  " điểm")
        return pd.concat([tv[tv.index < bls.index[0]], bls]).sort_index(), "BLS (chính thức) + TradingView USIRYY trước đó"
    if bls is not None and len(bls):
        return bls, "BLS (chính thức)"
    if tv is not None:
        return tv, "TradingView ECONOMICS:USIRYY"
    raise ValueError("không có CPI Mỹ")


def vix():
    for ng in ("tv:TVC:VIX", "yf:^VIX"):                             # kiểm 25/11: TVC:VIX ↔ ^VIX tương quan 1,00 cùng ngày
        try:
            return _lay(ng, "2015-01-01"), ten_nguon(ng)
        except Exception as e:                                        # noqa: BLE001 – nguồn sau
            print(f"  ⚠ VIX {ten_nguon(ng)}: {type(e).__name__} {str(e)[:60]}")
    raise ValueError("không có VIX")


def tai_hang_hoa():
    """→ ({khoá: Series}, {khoá: nguồn}, {khoá: so chéo (ngày, tương quan, lệch %)}). Nguồn đầu lỗi → nguồn sau → đệm."""
    S, N, K = {}, {}, {}
    for k, _, ten, _, nguon, _ in HANG_HOA:
        ds = {}
        for ng in nguon:
            try:
                x = _lay(ng).dropna()
                x = x[x > 0]
                if len(x) > 200:
                    ds[ng] = x[~x.index.duplicated(keep="last")].sort_index()
                else:
                    print(f"  ⚠ {ten} – {ten_nguon(ng)}: {len(x)} điểm")
            except Exception as e:                                    # noqa: BLE001 – nguồn sau
                print(f"  ⚠ {ten} – {ten_nguon(ng)}: {type(e).__name__} {str(e)[:60]}")
        if ds:
            chon = next(iter(ds))
            S[k], N[k] = _dem("hh_" + k, ds[chon]), ten_nguon(chon)
        else:
            x = _dem("hh_" + k)
            if x is not None and len(x):
                S[k], N[k] = x, "đệm (nguồn lỗi)"
        if len(ds) == 2:
            (na, a), (nb, b) = ds.items()
            K[k] = so_cheo(a, b)
            print(f"  kiểm {ten}: {ten_nguon(na)} ↔ {ten_nguon(nb)} · {K[k][0]} ngày · tương quan thay đổi ngày {K[k][1]}"
                  f" · lệch trung vị {K[k][2]} %")
    return S, N, K


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
        if "OANDA" in (n or ""):                                     # kiểm: giao ngay ↔ COMEX (lệch cơ sở ~0,5 %)
            try:
                g = _yf("GC=F")
                m, tq, lech = so_cheo(xd["close"], g["close"]) if g is not None else (0, None, None)
                print(f"  kiểm vàng: OANDA ↔ COMEX GC=F · {m} ngày · tương quan thay đổi ngày {tq} · lệch trung vị {lech} %")
            except Exception as e:                                    # noqa: BLE001 – chỉ để kiểm
                print(f"  ⚠ kiểm vàng: {type(e).__name__} {str(e)[:60]}")
    xg, n = _thu("xau_gio", xau_gio)
    if xg is not None:
        S["xau_gio"], N["xau_gio"] = xg, n
    for k, ma in (("sjc", "SJL1L10"), ("nhan", "SJ9999")):
        x, _ = _thu("vt_" + k, vang_today, ma)
        if x is not None:
            S[k], N[k] = x, "vang.today"
    for k, ma, ten in (("usdvnd", "VND=X", "Yahoo VND=X"), ("dxy", "DX-Y.NYB", "Yahoo DX-Y.NYB"),
                       ("usdcny", "CNY=X", "Yahoo CNY=X")):
        x, _ = _thu(k, lambda m=ma: _yf(m)["close"])
        if x is not None:
            S[k], N[k] = x, ten
    for k, ham, ten in (("us_thuc10", thuc_my_10n, "Bộ Tài chính Mỹ (TIPS)"), ("us_sofr", sofr, "NY Fed (chính thức)")):
        x, _ = _thu(k, ham)
        if x is not None:
            S[k], N[k] = x, ten
    x, n = _thu("us_cpi", cpi_my)
    if x is not None:
        S["us_cpi"], N["us_cpi"] = x, n or "đệm"
    x, n = _thu("us_vix", vix)
    if x is not None:
        S["us_vix"], N["us_vix"] = x, n
    hs, hn, hk = tai_hang_hoa()
    for k, x in hs.items():
        S["hh_" + k], N["hh_" + k] = x, hn[k]
    P["so_cheo"] = hk
    try:
        from thi_truong import lai_suat as LS
        ls, nguon = LS.tai_tat_ca(os.path.join(DEM, "lai_suat"))
        for k, kk in (("vn_1n", "VN01Y"), ("vn_10n", "VN10Y"), ("vn_dh", "ECONOMICS:VNINTR"), ("vn_lnh", "ECONOMICS:VNINBR"),
                      ("vn_cpi", "ECONOMICS:VNIRYY"), ("us_ff", "US_EFFR"), ("us_tran", "US_TRAN"), ("us_2n", "US_2Y"),
                      ("us_10n", "US_10Y")):
            if kk in ls:
                S[k], N[k] = ls[kk], nguon.get(kk, "")
    except Exception as e:                                            # noqa: BLE001 – lãi suất lỗi không hỏng phần vàng
        ls = {}
        print(f"  ⚠ lãi suất: {type(e).__name__} {str(e)[:80]}")
    for k, ma, ten, *_ in VM_VN:                                     # kinh tế VN: lai_suat đã tải phần MA_VM_VN, còn lại tải ở đây
        x = ls.get(ma)
        if x is not None and len(x):
            S[k], N[k] = x, "TradingView " + ma
        else:
            x, n = _thu(k, lambda m=ma: _tv(m, "1M")["close"])
            if x is not None:
                S[k], N[k] = x, ("TradingView " + ma) if n is None else n
        if k in S:                                                    # kiểm: in 15 kỳ cuối (đơn vị; số tháng hay cộng dồn năm)
            print(f"  kiểm {ten}: " + " · ".join(f"{d:%m/%Y} {v:,.4g}" for d, v in pd.Series(S[k]).dropna().iloc[-15:].items()))
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


def bien_dong(s):
    """Series giá → giá cuối, ngày, % so phiên trước / 1 tuần / 1 tháng / đầu năm / 1 năm (mốc: giá cuối cùng ở hoặc trước mốc)."""
    s = pd.Series(s).dropna().sort_index()
    v, d = float(s.iloc[-1]), s.index[-1]

    def pt(moc):
        q = s[s.index <= moc]
        return None if not len(q) or float(q.iloc[-1]) == 0 else round((v / float(q.iloc[-1]) - 1) * 100, 2)
    return {"gia": round(v, 3 if abs(v) < 20 else 2), "ngay": f"{d:%Y-%m-%d}",
            "d1": round((v / float(s.iloc[-2]) - 1) * 100, 2) if len(s) > 1 and float(s.iloc[-2]) else None,
            "w1": pt(d - pd.Timedelta(days=7)), "m1": pt(d - pd.DateOffset(months=1)),
            "ytd": pt(pd.Timestamp(d.year - 1, 12, 31)), "y1": pt(d - pd.DateOffset(years=1))}


def _the(k, nhom, ten, s, dv, nguon, ky=1, kieu="%", le=2, ten_ky="phiên trước"):
    s = pd.Series(s).dropna()
    if not len(s):
        return None
    v = float(s.iloc[-1])
    if ten_ky.startswith("cùng kỳ"):
        tr = s[s.index <= s.index[-1] - pd.DateOffset(years=1)]
        q = float(tr.iloc[-1]) if len(tr) and tr.index[-1] > s.index[-1] - pd.DateOffset(years=1, days=20) else None
    else:
        q = float(s.iloc[-1 - ky]) if len(s) > ky else None
    doi = None if q is None else (round((v / q - 1) * 100, 2) if kieu == "%" else round(v - q, 3))
    d = s.index[-1]
    kn = "quý" if ten_ky.startswith("quý") else "tháng" if ten_ky.startswith(("tháng", "cùng kỳ")) else ""
    return {"k": k, "nhom": nhom, "ten": ten, "gia": round(v, le), "dv": dv, "doi": doi, "kieu_doi": kieu,
            "ky": ten_ky, "ngay": f"{d:%Y-%m-%d}", "nguon": nguon,
            **({"ky_so": f"quý {(d.month - 1) // 3 + 1}/{d.year}" if kn == "quý" else f"tháng {d.month}/{d.year}"} if kn else {})}


def dung(S, N, P, bay_gio=None):
    """Chuỗi thô → JSON cho trang."""
    bay_gio = bay_gio or datetime.now(VN)
    C, T = {}, []

    def them(k, nhom, ten, s, dv, le=3, chuoi=True, **kt):
        if s is None or not len(pd.Series(s).dropna()):
            return
        if chuoi:
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
    hh = {k: (nhom, ten, dv, lq) for k, nhom, ten, dv, _, lq in HANG_HOA}
    for k in THE_HH:                                                  # thẻ bạc / dầu – chuỗi ở hang_hoa.json
        if "hh_" + k in S:
            N[k] = N.get("hh_" + k, "")
            them(k, "hh", hh[k][1], S["hh_" + k], hh[k][2], chuoi=False)
            if T and T[-1]["k"] == k:
                T[-1]["gia"] = round(float(pd.Series(S["hh_" + k]).dropna().iloc[-1]), 3 if T[-1]["gia"] < 20 else 2)
    for k, nhom, ten, dv in (("usdvnd", "ty_gia", "USD/VND (thị trường)", "đồng"), ("dxy", "ty_gia", "Chỉ số USD (DXY)", "điểm"),
                             ("usdcny", "ty_gia", "USD/CNY (nhân dân tệ)", "tệ")):
        them(k, nhom, ten, S.get(k), dv, le=4 if k == "usdcny" else 2)
    for k, ten in (("vn_dh", "Lãi điều hành NHNN"), ("vn_lnh", "Liên ngân hàng"), ("vn_1n", "TPCP 1 năm"),
                   ("vn_10n", "TPCP 10 năm"), ("vn_cpi", "Lạm phát CPI (so cùng kỳ)")):
        thang = k in ("vn_dh", "vn_lnh", "vn_cpi")
        them(k, "ls_vn", ten, S.get(k), "%/năm" if k != "vn_cpi" else "%", kieu="đ",
             ten_ky="tháng trước" if thang else "phiên trước")
    for k, ma, ten, dv, chia, kieu, ky in VM_VN:
        x = S.get(k)
        if x is not None and len(x):
            them(k, "vn", ten, pd.Series(x).astype(float) / chia, dv, le=2, kieu=kieu, ten_ky=ky)
    for k, ten in (("us_ff", "Fed funds thực tế"), ("us_tran", "Trần mục tiêu Fed"), ("us_sofr", "SOFR (qua đêm có bảo đảm)"),
                   ("us_2n", "Lợi suất Mỹ 2 năm"), ("us_10n", "Lợi suất Mỹ 10 năm"),
                   ("us_thuc10", "Lợi suất thực Mỹ 10 năm (TIPS)")):
        them(k, "my", ten, S.get(k), "%/năm", kieu="đ")
    them("us_cpi", "my", "Lạm phát Mỹ CPI (so cùng kỳ)", S.get("us_cpi"), "%", le=2, kieu="đ", ten_ky="tháng trước")
    them("us_vix", "my", "Chỉ số biến động VIX", S.get("us_vix"), "điểm", le=2)
    bang, hh_chuoi = [], {}
    so_cheo_ = P.get("so_cheo") or {}
    for k, nhom, ten, dv, nguon, lq in HANG_HOA:
        x = S.get("hh_" + k)
        if x is None or len(pd.Series(x).dropna()) < 2:
            continue
        x = pd.Series(x).dropna().astype(float).sort_index()
        x = x[~x.index.duplicated(keep="last")]
        r = {"k": k, "nhom": nhom, "ten": ten, "dv": dv, "lq": lq, "nguon": N.get("hh_" + k, ""),
             "cheo": list(so_cheo_[k]) if k in so_cheo_ else None, **bien_dong(x)}
        r["cu"] = (pd.Timestamp(bay_gio.date()) - pd.Timestamp(r["ngay"])).days > 7      # nguồn ngừng cập nhật → trang ghi ngày
        bang.append(r)
        hh_chuoi[k] = _gon(x, le=4)
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
            "nguon_gio": N.get("xau_gio", ""), "song": P.get("song"), "nhom_hh": NHOM_HH, "hang_hoa": bang,
            "hh_chuoi": hh_chuoi,
            "ghi_chu": "Tham khảo – không phải tín hiệu mua bán. Lãi suất / vĩ mô đã kiểm (backtest): không giúp canh mua bán "
                       "cổ phiếu. Số liệu tháng (lãi điều hành, liên ngân hàng, lạm phát, kinh tế VN) công bố trễ 1–2 tháng. Hàng hoá: "
                       "hợp đồng tương lai gần nhất (nối liên tục, có bước nhảy nhỏ khi đổi kỳ hạn), giá cuối ngày / trễ."}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--ra", default=os.path.join("docs", "vi_mo"))
    a = p.parse_args(argv)
    S, N, P = tai_tat_ca()
    kq = dung(S, N, P)
    os.makedirs(a.ra, exist_ok=True)
    hh = kq.pop("hh_chuoi")
    with open(os.path.join(a.ra, "hang_hoa.json"), "w", encoding="utf-8") as f:
        json.dump(hh, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(a.ra, "du_lieu.json"), "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, separators=(",", ":"))
    for r in kq["hang_hoa"]:
        print(f"  {r['ten']}: {r['gia']:,} {r['dv']} ({r['ngay']}) · ngày {r['d1']} % · tháng {r['m1']} % · năm {r['y1']} % · "
              f"{r['nguon']}" + (" · ⚠ CŨ" if r["cu"] else ""))
    print(f"Vĩ mô: {len(kq['the'])} thẻ, {len(kq['chuoi'])} chuỗi, {len(kq['hang_hoa'])} hàng hoá, nến ngày {len(kq['xau_nen'])},"
          f" nến giờ {len(kq['xau_gio'])},"
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
