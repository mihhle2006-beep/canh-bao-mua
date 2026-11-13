# -*- coding: utf-8 -*-
"""
NGUỒN DỮ LIỆU bảng thị trường (dò 05/11/2026 – workflow "Chan doan nguon" --bang_thi_truong):
  • Vietcap trading: bảng giá theo mã (≤ 400 mã / lần), chỉ số + độ rộng, nến 1' / ngày, nhóm VN30 / HNX30, tác động
    lên chỉ số (top 10 kéo / đè), khớp theo bước giá có tách MUA / BÁN chủ động, danh sách mã (sàn, mã ngành ICB cấp 2).
  • Vietcap IQ: tên ngành ICB, lịch sử ngày (giá đã điều chỉnh, khối ngoại), tự doanh theo mã.
  • CafeF: khối ngoại & tự doanh cả sàn HOSE theo ngày.
Đơn vị gốc: giá ĐỒNG; GTGD bảng giá / chỉ số TRIỆU đồng; giá trị khối ngoại / tự doanh ĐỒNG.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

TV = "https://trading.vietcap.com.vn/api"
IQ = "https://iq.vietcap.com.vn/api/iq-insight-service/v1"
CAFEF = "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/{loai}.ashx?Symbol={ma}&StartDate=&EndDate=&PageIndex=1&PageSize={so}"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 "
                   "Safari/537.36", "Accept": "application/json, text/plain, */*",
     "Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"}
CHI_SO = ("VNINDEX", "VN30", "HNXIndex", "HNX30", "HNXUpcomIndex")
_LUONG = threading.local()


def _phien():
    s = getattr(_LUONG, "s", None)
    if s is None:
        s = _LUONG.s = requests.Session()
    return s


def goi(url, body=None, so_lan=3, timeout=30, headers=None):
    """GET (body None) / POST JSON → JSON; thử lại khi lỗi mạng / 5xx / 429."""
    loi = None
    for k in range(so_lan):
        try:
            h = {**H, **(headers or {})}
            r = (_phien().post(url, json=body, headers=h, timeout=timeout) if body is not None
                 else _phien().get(url, headers=h, timeout=timeout))
            if r.status_code != 200:
                raise ValueError(f"HTTP {r.status_code}")
            return r.json() if r.content else None
        except (requests.RequestException, ValueError) as e:
            loi = e
            if str(e).startswith("HTTP 4") and "429" not in str(e):
                break
            if k < so_lan - 1:
                time.sleep(0.8 * 2 ** k)
    raise ValueError(f"{url.split('?')[0][-60:]}: {str(loi)[:80]}")


def _ds(j):
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        return j.get("data") if isinstance(j.get("data"), list) else (j.get("Data") or [])
    return []


def song_song(ham, ds, luong=8):
    """{phần tử: ham(phần tử)} chạy song song; phần tử lỗi bị bỏ."""
    out = {}

    def _mot(x):
        try:
            return x, ham(x)
        except Exception:                                           # noqa: BLE001 – nguồn lỗi 1 mã không chặn cả bảng
            return x, None

    with ThreadPoolExecutor(luong) as ex:
        for x, v in ex.map(_mot, list(ds)):
            if v is not None:
                out[x] = v
    return out


def tat_ca_ma():
    """[{symbol, board (HSX / HNX / UPCOM / DELISTED…), type (STOCK / ETF / CW / FU…), icbCode2, organShortName…}]"""
    return _ds(goi(f"{TV}/price/symbols/getAll"))


def bang_gia(ds_ma, lo=400):
    """Bảng giá [{listingInfo, matchPrice, bidAsk}] cho mọi mã (gọi theo lô)."""
    ds_ma = list(ds_ma)
    lo_ma = [ds_ma[i:i + lo] for i in range(0, len(ds_ma), lo)]
    kq = song_song(lambda i: _ds(goi(f"{TV}/price/symbols/getList", {"symbols": lo_ma[i]}, timeout=60)),
                   range(len(lo_ma)), luong=4)
    return [x for i in sorted(kq) for x in kq[i]]


def chi_so(ds=CHI_SO):
    return _ds(goi(f"{TV}/price/marketIndex/getList", {"symbols": list(ds)}))


def nen(ma, khung="ONE_MINUTE", so_nen=400, timeout=30):
    """Nến gap-chart 1 mã / chỉ số: {t (unix, chuỗi), o, h, l, c, v, accumulatedValue (triệu), accumulatedVolume}."""
    j = goi(f"{TV}/chart/OHLCChart/gap-chart", {"timeFrame": khung, "symbols": [ma], "to": int(time.time()),
                                                 "countBack": int(so_nen)}, timeout=timeout)
    return j[0] if isinstance(j, list) and j else None


def nhom(ten):
    return [d.get("symbol") for d in _ds(goi(f"{TV}/price/symbols/getByGroup?group={ten}")) if d.get("symbol")]


def tac_dong(chi_so_="VNINDEX", nhom_="HOSE"):
    """{topUp: [{symbol, impact (điểm), matchPrice, refPrice…}], topDown: […]} – 10 mã mỗi chiều."""
    return goi(f"{TV}/market-watch/v2/IndexImpactChart/getData",
               {"symbol": chi_so_, "group": nhom_, "timeFrame": "ONE_DAY"}) or {}


def buoc_gia(ma):
    """Khớp theo bước giá cả phiên: [{priceStep, accumulatedVolume, accumulatedBuyVolume, accumulatedSellVolume}]."""
    return _ds(goi(f"{TV}/market-watch/AccumulatedPriceStepVol/getSymbolData", {"symbol": ma}))


def ten_nganh():
    """{mã ICB: tên tiếng Việt} mọi cấp (IQ sectors/icb-codes)."""
    return {str(d.get("name")): d.get("viSector") for d in _ds(goi(f"{IQ}/sectors/icb-codes")) if d.get("viSector")}


def lich_su_ngay(ma, so=260):
    """Lịch sử ngày IQ (mới → cũ): giá & giá điều chỉnh, KL / GT khớp, khối ngoại ròng (đồng)."""
    j = goi(f"{IQ}/company/{ma}/price-history?timeFrame=ONE_DAY&page=0&size={so}")
    d = j.get("data", j) if isinstance(j, dict) else j
    return d.get("content", d) if isinstance(d, dict) else d


def tu_doanh_ma(ma, so=20):
    j = goi(f"{IQ}/company/{ma}/proprietary-history?timeFrame=ONE_DAY&page=0&size={so}")
    d = j.get("data", j) if isinstance(j, dict) else j
    return d.get("content", d) if isinstance(d, dict) else d


def cafef(loai, ma="VNINDEX", so=25):
    """CafeF GDKhoiNgoai / GDTuDoanh theo ngày (mới → cũ)."""
    j = goi(CAFEF.format(loai=loai, ma=ma, so=so), headers={"Referer": "https://cafef.vn/", "Origin": "https://cafef.vn"})
    d = (j or {}).get("Data") or {}
    x = d.get("Data")
    if isinstance(x, dict):
        x = x.get("ListDataTudoanh") or []
    return x or []
