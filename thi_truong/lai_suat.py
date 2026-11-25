# -*- coding: utf-8 -*-
"""
BẢN CHÉP từ danh-muc ptcp/lai_suat_vn.py (25/11/2026) cho tab Vĩ mô – repo công khai bỏ qua ptcp/; sửa ở danh-muc thì chép lại.
LỊCH SỬ LÃI SUẤT VIỆT NAM (25/11/2026 – chan_doan LAI_SUAT lượt 2 tìm được): TradingView, websocket KHÔNG đăng nhập (giao thức
như thư viện tvdatafeed). Có trên runner GitHub (máy sandbox chặn):
  TVC:VN10Y / VN05Y / VN03Y / VN02Y / VN01Y   lợi suất TPCP theo NGÀY từ 07/2007
  ECONOMICS:VNINTR  lãi điều hành (tái cấp vốn) theo THÁNG từ 2000
  ECONOMICS:VNINBR  lãi liên ngân hàng theo THÁNG từ 1998
  ECONOMICS:VNIRYY  lạm phát CPI so cùng kỳ theo THÁNG từ 1996
(IMF IFS qua DBnomics có tiền gửi / cho vay / điều hành theo tháng nhưng chỉ tới 12/2023; FRED chặn runner; Trading Economics
bỏ tài khoản khách; Investing chặn Cloudflare.) Đệm cache_du_lieu/lai_suat/<mã>.csv – lỗi mạng thì dùng đệm cũ.
"""
import json
import os
import random
import re
import string
import time

import numpy as np
import pandas as pd

MA_LS = {"TVC:VN10Y": ("TPCP 10N", "1D"), "TVC:VN01Y": ("TPCP 1N", "1D"),
         "ECONOMICS:VNINBR": ("Liên ngân hàng", "1M"), "ECONOMICS:VNINTR": ("Lãi điều hành", "1M"),
         "ECONOMICS:VNIRYY": ("Lạm phát", "1M")}
# Vĩ mô VN theo tháng (TradingView ECONOMICS, gốc Tổng cục Thống kê / NHNN)
MA_VM_VN = {"ECONOMICS:VNIPYY": "SXCN so cùng kỳ %", "ECONOMICS:VNRSYY": "Bán lẻ so cùng kỳ %",
            "ECONOMICS:VNCIR": "Lạm phát lõi %", "ECONOMICS:VNEXP": "Xuất khẩu (USD)",
            "ECONOMICS:VNFER": "Dự trữ ngoại hối (USD)"}
# Mỹ: nguồn CHÍNH THỨC trước (NY Fed, Bộ Tài chính Mỹ), TradingView dự phòng
MA_MY = {"US_EFFR": ("Fed funds thực tế (EFFR)", "FRED:DFF"), "US_TRAN": ("Trần mục tiêu Fed", "FRED:DFEDTARU"),
         "US_3M": ("Lợi suất Mỹ 3T", "TVC:US03MY"), "US_2Y": ("Lợi suất Mỹ 2N", "TVC:US02Y"),
         "US_10Y": ("Lợi suất Mỹ 10N", "TVC:US10Y")}
THU_MUC = os.path.join("cache_du_lieu", "lai_suat")


def tv_lich_su(sym, khung="1D", n=5000, cho=30):
    """1 mã TradingView → (DataFrame [o, h, l, c] chỉ mục ngày, thông điệp lỗi | "")."""
    try:
        from websocket import create_connection
    except ImportError:
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "websocket-client"], check=False)
        from websocket import create_connection

    def goi(ws, m, p):
        t = json.dumps({"m": m, "p": p}, separators=(",", ":"))
        ws.send(f"~m~{len(t)}~m~{t}")

    ws = create_connection("wss://data.tradingview.com/socket.io/websocket",
                           header=["Origin: https://data.tradingview.com"], timeout=cho)
    cs = "cs_" + "".join(random.choice(string.ascii_lowercase) for _ in range(12))
    goi(ws, "set_auth_token", ["unauthorized_user_token"])
    goi(ws, "chart_create_session", [cs, ""])
    goi(ws, "resolve_symbol", [cs, "symbol_1", '={"symbol":"%s","adjustment":"splits"}' % sym])
    goi(ws, "create_series", [cs, "s1", "s1", "symbol_1", khung, n])
    tho, t0 = "", time.time()
    while time.time() - t0 < cho:
        try:
            m = ws.recv()
        except Exception:                                            # noqa: BLE001 – hết giờ / đóng
            break
        if re.fullmatch(r"~m~\d+~m~~h~\d+", m):
            ws.send(m)
            continue
        tho += m
        if any(k in m for k in ("series_completed", "symbol_error", "critical_error", "series_error")):
            break
    ws.close()
    return doc_nen(tho)


def doc_nen(tho):
    so = r"(-?[\d.]+(?:[eE][+-]?\d+)?)"
    v = re.findall(r'"v":\[' + ",".join([so] * 5), tho)
    if not v:
        loi = re.search(r'"m":"(symbol_error|critical_error|series_error)".{0,160}', tho)
        return None, (loi.group(0) if loi else tho[-200:])
    df = pd.DataFrame([[float(x) for x in r] for r in v], columns=["t", "o", "h", "l", "c"])
    df.index = pd.to_datetime(df.pop("t"), unit="s").dt.normalize()
    df.index.name = None
    return df[~df.index.duplicated(keep="last")].sort_index(), ""


def tai_lai_suat_vn(thu_muc=THU_MUC, tai=tv_lich_su):
    """{mã: Series giá đóng cửa (%)} cho MA_LS – tải mới, lỗi thì dùng đệm; không có gì → bỏ mã."""
    os.makedirs(thu_muc, exist_ok=True)
    out = {}
    for sym, (_, khung) in MA_LS.items():
        f = os.path.join(thu_muc, sym.replace(":", "_") + ".csv")
        s = None
        try:
            df, _ = tai(sym, khung)
            if df is not None and len(df) > 20:
                s = df["c"].astype(float)
                s.to_frame("c").to_csv(f)
        except Exception:                                            # noqa: BLE001 – mạng lỗi → đệm
            s = None
        if s is None and os.path.exists(f):
            try:
                d = pd.read_csv(f, index_col=0)
                s = pd.Series(d["c"].astype(float).values, index=pd.to_datetime(d.index))
            except (OSError, ValueError, KeyError):
                s = None
        if s is not None and len(s):
            out[sym] = s.sort_index()
    return out


def _hd():
    return {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36"}


def tai_ny_fed(tu="2010-01-01"):
    """NY Fed (chính thức) → {"US_EFFR": Series %, "US_TRAN": Series trần mục tiêu %} theo ngày."""
    import requests
    r = requests.get("https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json",
                     params={"startDate": tu, "endDate": pd.Timestamp.today().strftime("%Y-%m-%d")}, headers=_hd(),
                     timeout=60)
    d = pd.DataFrame(r.json().get("refRates", []))
    d.index = pd.to_datetime(d["effectiveDate"])
    d = d.sort_index()
    return {"US_EFFR": pd.to_numeric(d["percentRate"], errors="coerce").dropna(),
            "US_TRAN": pd.to_numeric(d["targetRateTo"], errors="coerce").dropna()}


def tai_bo_tai_chinh_my(tu=2010):
    """Bộ Tài chính Mỹ – đường cong lợi suất (chính thức) → {"US_3M", "US_2Y", "US_10Y": Series %} theo ngày."""
    import io

    import requests
    ds = []
    for y in range(tu, pd.Timestamp.today().year + 1):
        u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
             f"{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
        d = pd.read_csv(io.StringIO(requests.get(u, headers=_hd(), timeout=60).text))
        d.index = pd.to_datetime(d["Date"])
        ds.append(d)
    d = pd.concat(ds).sort_index()
    d = d[~d.index.duplicated(keep="last")]
    return {k: pd.to_numeric(d[c], errors="coerce").dropna() for k, c in (("US_3M", "3 Mo"), ("US_2Y", "2 Yr"),
                                                                          ("US_10Y", "10 Yr"))}


def _ghi(f, s):
    s.to_frame("c").to_csv(f)


def _doc(f):
    try:
        d = pd.read_csv(f, index_col=0)
        return pd.Series(d["c"].astype(float).values, index=pd.to_datetime(d.index)).sort_index()
    except (OSError, ValueError, KeyError):
        return None


def tai_tat_ca(thu_muc=THU_MUC, tai=tv_lich_su, ny_fed=tai_ny_fed, bo_tc=tai_bo_tai_chinh_my):
    """Mọi chuỗi cho nhóm Lãi suất / Fed – Mỹ / Vĩ mô VN → ({khoá: Series}, {khoá: nguồn}). Khoá: mã TradingView cho chuỗi
    VN, "US_*" cho Mỹ. Mỹ: nguồn chính thức, lỗi → TradingView (FRED:DFF …), lỗi nữa → đệm."""
    os.makedirs(thu_muc, exist_ok=True)
    out, nguon = {}, {}
    for sym, khung in [(k, v[1]) for k, v in MA_LS.items()] + [(k, "1M") for k in MA_VM_VN]:
        f = os.path.join(thu_muc, sym.replace(":", "_") + ".csv")
        s = None
        try:
            df, _ = tai(sym, khung)
            if df is not None and len(df) > 20:
                s = df["c"].astype(float)
                _ghi(f, s)
                nguon[sym] = "TradingView"
        except Exception:                                            # noqa: BLE001 – mạng lỗi → đệm
            s = None
        if s is None:
            s = _doc(f) if os.path.exists(f) else None
            if s is not None:
                nguon[sym] = "đệm"
        if s is not None and len(s):
            out[sym] = s.sort_index()
    chinh = {}
    for ham in (ny_fed, bo_tc):
        try:
            chinh.update(ham())
        except Exception:                                            # noqa: BLE001 – nguồn chính thức lỗi → dự phòng
            pass
    for k, (_, sym_tv) in MA_MY.items():
        f = os.path.join(thu_muc, k + ".csv")
        s = chinh.get(k)
        if s is not None and len(s) > 20:
            nguon[k] = "chính thức"
        else:
            try:
                df, _ = tai(sym_tv, "1D")
                s = df["c"].astype(float) if df is not None and len(df) > 20 else None
                nguon[k] = f"TradingView {sym_tv}" if s is not None else None
            except Exception:                                        # noqa: BLE001
                s = None
        if s is not None:
            _ghi(f, s)
        elif os.path.exists(f):
            s = _doc(f)
            nguon[k] = "đệm"
        if s is not None and len(s):
            out[k] = s.sort_index()
    # TPCP VN: HNX (Sở GDCK Hà Nội, chính thức) trước; lỗi / thiếu → TradingView
    try:
        h = tai_hnx(thu_muc)
    except Exception:                                                # noqa: BLE001 – HNX lỗi → TradingView
        h = None
    for k, ky, tv in (("VN10Y", 10, "TVC:VN10Y"), ("VN01Y", 1, "TVC:VN01Y")):
        if h is not None and ky in h and h[ky].notna().sum() > 500:
            # HNX 2013 nhiễu (10N nhảy ±1,6–2 điểm/ngày 08–09/2013 – kiểm LAI_SUAT_KT2 25/11/2026) → HNX từ HNX_TU, trước đó
            # nối TradingView (nếu có)
            hn = h[ky].dropna().loc[HNX_TU:]
            truoc = out[tv].loc[:pd.Timestamp(HNX_TU) - pd.Timedelta(days=1)] if tv in out else hn.iloc[:0]
            out[k], nguon[k] = pd.concat([truoc, hn]).sort_index(), f"HNX từ {HNX_TU[:4]}" + (" + TradingView trước đó"
                                                                                                if len(truoc) else "")
        elif tv in out:
            out[k], nguon[k] = out[tv], "TradingView"
    return out, {k: v for k, v in nguon.items() if k in out}


# ------------------------------------------------------------------ HNX (Sở GDCK Hà Nội) – đường cong lợi suất TPCP chính thức
HNX_TRANG = "https://www.hnx.vn/trai-phieu/duong-cong-loi-suat.html"
HNX_API = "https://www.hnx.vn/ModuleReportBonds/Bond_YieldCurve/SearchAndNextPageYieldCurveData"
HNX_KY = (1, 2, 3, 5, 7, 10, 15, 20)
HNX_TU = "2014-01-01"                # HNX 2013 nhiễu → dùng HNX từ ngày này


def hnx_bundle():
    """Máy chủ HNX không gửi chứng chỉ trung gian → tải theo AIA của chứng chỉ máy chủ (openssl), ghép vào certifi → vẫn
    KIỂM chứng chỉ (không tắt verify). → đường dẫn bundle | None."""
    import re
    import subprocess
    import tempfile

    import certifi
    import requests
    out = subprocess.run(["openssl", "s_client", "-connect", "www.hnx.vn:443", "-servername", "www.hnx.vn", "-showcerts"],
                         input=b"", capture_output=True, timeout=30).stdout.decode("utf-8", "ignore")
    leaf = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", out, re.S)
    if not leaf:
        return None
    info = subprocess.run(["openssl", "x509", "-noout", "-text"], input=leaf.group(0).encode(), capture_output=True,
                          timeout=20).stdout.decode()
    pem = ""
    for u in re.findall(r"CA Issuers - URI:(\S+)", info):
        der = requests.get(u, timeout=30).content
        pem += subprocess.run(["openssl", "x509", "-inform", "PEM" if der.startswith(b"-----") else "DER", "-outform",
                               "PEM"], input=der, capture_output=True, timeout=20).stdout.decode()
    if not pem:
        return None
    f = os.path.join(tempfile.gettempdir(), "hnx_bundle.pem")
    with open(f, "w") as g:
        g.write(open(certifi.where()).read() + "\n" + pem)
    return f


def doc_bang_hnx(html):
    """Bảng đường cong HNX → {kỳ hạn năm (chỉ HNX_KY): par yield %}."""
    import re
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        c = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        m = re.match(r"(\d+)\s*năm", c[0]) if len(c) >= 3 else None
        if not m or int(m.group(1)) not in HNX_KY:
            continue
        try:
            out[int(m.group(1))] = float(c[2].replace(".", "").replace(",", "."))
        except ValueError:
            continue
    return out


def _phien_hnx(bundle):
    import requests
    ss = requests.Session()
    ss.verify = bundle
    ss.headers.update({"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest", "Referer": HNX_TRANG})
    ss.get(HNX_TRANG, timeout=40)
    return ss


def tai_hnx(thu_muc=THU_MUC, tu="2013-01-01", luong=4, hom_nay=None, lay=None):
    """Par yield TPCP HNX theo NGÀY (đệm thu_muc/HNX.csv; ngày không có số = trống; 10 ngày gần nhất luôn tải lại; lỗi mạng
    → không ghi, lần sau tải lại) → DataFrame cột HNX_KY | None. lay(ngày) → dict (thay mạng khi test)."""
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(thu_muc, exist_ok=True)
    f = os.path.join(thu_muc, "HNX.csv")
    cu = None
    if os.path.exists(f):
        try:
            cu = pd.read_csv(f, index_col=0, parse_dates=True)
            cu.columns = [int(float(c)) for c in cu.columns]
        except (OSError, ValueError):
            cu = None
    hom = pd.Timestamp(hom_nay or pd.Timestamp.today()).normalize()
    if cu is not None and len(cu):
        cu = cu[cu.index < hom - pd.Timedelta(days=10)]
    can = [d for d in pd.bdate_range(tu, hom) if cu is None or d not in cu.index]
    if can and lay is None:
        b = hnx_bundle()
        if not b:
            return cu.dropna(how="all") if cu is not None and len(cu) else None
        import threading
        rieng = threading.local()

        def lay(d):                                                  # mỗi luồng 1 phiên
            for _ in range(2):
                try:
                    if not hasattr(rieng, "ss"):
                        rieng.ss = _phien_hnx(b)
                    return doc_bang_hnx(rieng.ss.post(HNX_API, data={"pDate": f"{d:%d/%m/%Y}"}, timeout=40).text)
                except Exception:                                    # noqa: BLE001 – thử lại 1 lần
                    continue
            return None
    if can:
        with ThreadPoolExecutor(max_workers=luong) as ex:
            kq = list(ex.map(lay, can))
        ok = [r is not None for r in kq]
        moi = pd.DataFrame([{k: (r or {}).get(k, np.nan) for k in HNX_KY} for r in kq], index=pd.DatetimeIndex(can))[ok]
        cu = moi if cu is None else pd.concat([cu, moi])
    if cu is None or not len(cu):
        return None
    cu = cu[~cu.index.duplicated(keep="last")].sort_index()
    cu.to_csv(f)
    return cu.dropna(how="all")
