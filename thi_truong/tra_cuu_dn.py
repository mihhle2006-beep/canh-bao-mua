# -*- coding: utf-8 -*-
"""
DỮ LIỆU DOANH NGHIỆP CHO TRANG TRA CỨU MÃ (docs/ma/ – công khai; dò nguồn 05/11/2026 "Chan doan nguon" --trang_ma):
  gia/<MÃ>.json  lịch sử ngày ~2 năm (Vietcap IQ price-history): OHLC điều chỉnh, giá đóng cửa gốc, KL / GT khớp, thoả
                 thuận, khối ngoại mua / bán / ròng + % sở hữu, cung cầu (KL đặt mua / bán), tự doanh ròng (HOSE)
  gia_dai/<MÃ>.json  nến ngày TỪ KHI CÓ DỮ LIỆU (gap-chart trading.vietcap – API biểu đồ của Vietcap, giá điều chỉnh, máy
                 chủ khác IQ): gọn {d0, g (cách ngày), o, h, l, c, v}; tải lại sau HAN_GIA_DAI ngày (trang nối với gia/ và
                 quy đổi theo tỷ lệ ở ngày nối nếu nguồn điều chỉnh khác nhau)
  dn/<MÃ>.json   hồ sơ + khuyến nghị Vietcap, cơ cấu sở hữu, cổ đông lớn, sự kiện (cổ tức, phát hành, ĐHCĐ…), giao dịch
                 nội bộ, chỉ số tài chính theo quý (P/E, P/B, ROE, NIM, nợ xấu…), tin CafeF, báo cáo CTCK (Simplize / CafeF),
                 hồ sơ KBS (thành lập, niêm yết, vốn điều lệ, giá chào sàn, công ty con – liên kết, lãnh đạo), tóm tắt Simplize
  cau_truc_bctc.json  cây chỉ tiêu BCTC Vietcap (cấp, tên) cho 4 loại DN – trang dựng bảng BCTC đầy đủ có thụt cấp
Vietcap hay làm chậm / chặn máy chủ GitHub → XOAY VÒNG: mã cũ nhất trước, dừng nhận mã mới khi hết giờ (--phut); mã chưa
tới lượt / lỗi GIỮ file cũ (cache). Chỉ số liệu công bố công khai, không đụng danh mục.
  python -m thi_truong.tra_cuu_dn --ra docs/ma/du_lieu [--ma HPG,FPT] [--phut 25]
"""
import argparse
import html
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from . import nguon

IQ = nguon.IQ
SIMPLIZE_BC = "https://api.simplize.vn/api/company/analysis-report/list?ticker={ma}&page=0&size=30"
CAFEF_BC = "https://cafef.vn/du-lieu/Ajax/PageNew/BaoCaoPhanTich.ashx?Symbol={ma}&PageIndex=1&PageSize=30"
KBS_HO_SO = "https://kbbuddywts.kbsec.com.vn/iis-server/investment/stockinfo/profile/{ma}?l=1"
SIMPLIZE_TOM_TAT = "https://api.simplize.vn/api/company/summary/{ma}"
CAFEF_TIN = ("https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx?symbol={ma}&floorID=0&configID=0&PageIndex=1"
             "&PageSize={so}&Type=2")
MAU_CAU_TRUC = {"CT": "HPG", "NH": "TCB", "CK": "SSI", "BH": "BVH"}         # loại DN (comTypeCode Vietcap) → mã mẫu
SO_PHIEN = 500
SO_PHIEN_DAI = 7000                                               # ~28 năm phiên – gap-chart trả từ ngày niêm yết
HAN_GIA_DAI = 30                                                  # ngày – tải lại lịch sử dài
SO_TIN = 60
SO_PHAN_DN = 12                                                    # ct cc cd sk nb cs tin bc kbs sz nn_nam tl
# chỉ số Vietcap statistics-financial giữ lại (đủ bộ – trang tự đặt tên / nhóm); giá trị tiền → tỷ đồng
CHI_SO_KHOA = ("pe", "pb", "ps", "priceToCashFlow", "evToEbitda", "dividendYield", "marketCap", "roe", "roa", "roic",
               "grossMargin", "ebitMargin", "preTaxProfitMargin", "afterTaxProfitMargin", "assetTurnover",
               "fixedAssetTurnover", "daySaleOutstanding", "daysInventoryOutstanding", "daysPayableOutstanding", "cashCycle",
               "currentRatio", "quickRatio", "cashRatio", "debtToEquity", "debtPerEquity", "financialLeverage",
               "ownersEquity", "ebit", "ebitda", "netInterestMargin", "averageYieldOnEarningAssets",
               "averageCostOfFinancing", "nonAndInterestIncome", "cir", "costToIncome", "ldrLoanDepositRatio", "casaRatio",
               "npl", "loansLossReservesToNPLs", "loansLossReserveToLoans", "provisionToOutstandingLoans", "loansGrowth",
               "depositGrowth", "equityToLoans", "totalEquityTotalAsset", "equityToLiabilities", "car")
CHI_SO_TIEN = {"marketCap", "ebit", "ebitda"}


_TK, _KHOA = {}, threading.Lock()


def _do(ten, ok, giay):
    """Thống kê theo nguồn: [số lần được, số lần lỗi, tổng giây, giây lâu nhất]."""
    with _KHOA:
        x = _TK.setdefault(ten, [0, 0, 0.0, 0.0])
        x[0 if ok else 1] += 1
        x[2] += giay
        x[3] = max(x[3], giay)


def bang_thong_ke():
    return " · ".join(f"{k} {v[0]}/{v[0] + v[1]} TB {v[2] / max(v[0] + v[1], 1):.1f}s max {v[3]:.0f}s"
                      for k, v in sorted(_TK.items(), key=lambda kv: -kv[1][2]))


def _r(x, le=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, le) if v == v and abs(v) != float("inf") else None


def _ngay(x):
    return str(x or "")[:10] or None


def _noi_dung(j):
    d = j.get("data", j) if isinstance(j, dict) else j
    if isinstance(d, dict) and "content" in d:
        return d["content"] or []
    return d


class CauDao:
    """Nhịp + cầu dao cho 1 nguồn hay chặn (Vietcap IQ chặn IP khi gọi dồn – 05/11/2026: ~250 lượt rồi mọi lượt treo tới
    hết thời gian chờ): ≤ moi_giay lượt / giây cho mọi luồng; nguong lỗi liên tiếp → nghỉ `nghi` giây; nghỉ quá toi_da lần
    → tắt nguồn tới hết lượt chạy (phần đó giữ bản cũ / nguồn dự phòng)."""

    def __init__(self, moi_giay=2.0, nguong=6, nghi=90, toi_da=3):
        self.cach, self.nguong, self.nghi, self.toi_da = 1.0 / moi_giay, nguong, nghi, toi_da
        self.khoa, self.ke_tiep, self.lien, self.so_nghi, self.nghi_toi, self.tat = threading.Lock(), 0.0, 0, 0, 0.0, False

    def cho(self):
        if self.tat:
            raise ValueError("nguồn đã tắt (bị chặn)")
        while time.time() < self.nghi_toi:
            time.sleep(1)
            if self.tat:
                raise ValueError("nguồn đã tắt (bị chặn)")
        with self.khoa:
            t = max(time.time(), self.ke_tiep)
            self.ke_tiep = t + self.cach
        time.sleep(max(0.0, t - time.time()))

    def ok(self):
        with self.khoa:
            self.lien = 0

    def loi(self):
        with self.khoa:
            self.lien += 1
            if self.lien >= self.nguong and time.time() >= self.nghi_toi:
                self.lien, self.so_nghi = 0, self.so_nghi + 1
                if self.so_nghi > self.toi_da:
                    self.tat = True
                else:
                    self.nghi_toi = time.time() + self.nghi


VAN_IQ = CauDao()


def iq(duong, so_lan=1):
    VAN_IQ.cho()
    try:
        kq = _noi_dung(nguon.goi(f"{IQ}/{duong}", so_lan=so_lan, timeout=15))
    except Exception:
        VAN_IQ.loi()
        raise
    VAN_IQ.ok()
    return kq


# ---------------------------------------------------------------- giá
def gon_gia(ds, td=None):
    """price-history (mới → cũ) + tự doanh {ngày: ròng tỷ} → cột (cũ → mới). Giá NGHÌN đồng, giá trị TỶ đồng."""
    dong = sorted((x for x in ds or [] if x.get("tradingDate")), key=lambda x: x["tradingDate"])
    k = lambda x, a, b=None: x.get(a) if x.get(a) is not None else (x.get(b) if b else None)   # noqa: E731
    out = {"d": [], "o": [], "h": [], "l": [], "c": [], "c0": [], "v": [], "gt": [], "tt": [], "nn_m": [], "nn_b": [],
           "nn": [], "nn_pt": [], "dat_m": [], "dat_b": [], "td": []}
    for x in dong:
        c = k(x, "closePriceAdjusted", "closePrice")
        if not c:
            continue
        out["d"].append(_ngay(x["tradingDate"]))
        for ten, a, b in (("o", "openPriceAdjusted", "openPrice"), ("h", "highestPriceAdjusted", "highestPrice"),
                          ("l", "lowestPriceAdjusted", "lowestPrice")):
            out[ten].append(_r((k(x, a, b) or c) / 1000))
        out["c"].append(_r(c / 1000))
        out["c0"].append(_r((x.get("closePrice") or c) / 1000))
        out["v"].append(int(x.get("totalMatchVolume") or 0))
        out["gt"].append(_r((x.get("totalValue") or x.get("totalMatchValue") or 0) / 1e9))
        out["tt"].append(_r((x.get("totalDealValue") or 0) / 1e9))
        out["nn_m"].append(_r((x.get("foreignBuyValueTotal") or 0) / 1e9))
        out["nn_b"].append(_r((x.get("foreignSellValueTotal") or 0) / 1e9))
        nn = x.get("foreignNetValueTotal")
        if nn is None:
            nn = (x.get("foreignBuyValueTotal") or 0) - (x.get("foreignSellValueTotal") or 0)
        out["nn"].append(_r(nn / 1e9))
        out["nn_pt"].append(_r((x.get("foreignOwnedPercentage") or 0) * 100))
        out["dat_m"].append(int(x.get("totalBuyTradeVolume") or 0))
        out["dat_b"].append(int(x.get("totalSellTradeVolume") or 0))
        out["td"].append((td or {}).get(out["d"][-1]))
    if not any(v is not None for v in out["td"]):
        del out["td"]
    return out


def gia_du_phong(ma):
    """Nến ngày gap-chart (trading.vietcap – máy chủ khác IQ) → cùng dạng gon_gia, thiếu khối ngoại / cung cầu."""
    from datetime import datetime as _dt, timezone as _tz
    n = nguon.nen(ma, "ONE_DAY", SO_PHIEN) or {}
    out = {"d": [], "o": [], "h": [], "l": [], "c": [], "c0": [], "v": [], "gt": [], "du_phong": True}
    for i, t in enumerate(n.get("t") or []):
        c = _r(n["c"][i])
        if not c:
            continue
        out["d"].append(_dt.fromtimestamp(int(float(t)) + 7 * 3600, _tz.utc).strftime("%Y-%m-%d"))
        for k in ("o", "h", "l"):
            out[k].append(_r(n[k][i]) or c)
        out["c"].append(c)
        out["c0"].append(c)
        out["v"].append(int(float(n["v"][i] or 0)))
        out["gt"].append(None)
    if not out["d"]:
        raise ValueError("gap-chart rỗng")
    if max(out["c"]) > 1000:                                       # đồng → nghìn đồng
        for k in ("o", "h", "l", "c", "c0"):
            out[k] = [_r(x / 1000) for x in out[k]]
    return out


def _4so(x):
    """4 chữ số có nghĩa (giá điều chỉnh cũ có thể < 1 nghìn đồng)."""
    return float(f"{x:.4g}") if x else x


def lay_gia_dai(ma):
    """Nến ngày gap-chart từ khi có dữ liệu → {"d0": ngày đầu, "g": [cách ngày phiên trước…], "o", "h", "l", "c" (nghìn đồng,
    4 chữ số có nghĩa), "v"} (cũ → mới)."""
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    n = nguon.nen(ma, "ONE_DAY", SO_PHIEN_DAI) or {}
    dong = []
    for i, t in enumerate(n.get("t") or []):
        c = n["c"][i]
        if not c:
            continue
        d = (_dt.fromtimestamp(int(float(t)), _tz.utc) + _td(hours=7)).date()
        dong.append((d, n["o"][i] or c, n["h"][i] or c, n["l"][i] or c, c, int(float(n["v"][i] or 0))))
    dong.sort(key=lambda x: x[0])                                   # ổn định: trùng ngày giữ bản đến trước
    dong = [x for i, x in enumerate(dong) if i == 0 or x[0] != dong[i - 1][0]]          # trùng ngày → giữ bản đầu
    if len(dong) < 2:
        raise ValueError("gap-chart rỗng")
    k = 1e-3 if max(x[4] for x in dong) > 1000 else 1.0           # đồng → nghìn đồng
    return {"d0": dong[0][0].isoformat(), "g": [0] + [(b[0] - a[0]).days for a, b in zip(dong, dong[1:])],
            **{ten: [_4so(x[j] * k) for x in dong] for j, ten in ((1, "o"), (2, "h"), (3, "l"), (4, "c"))},
            "v": [x[5] for x in dong]}


def _lay_gia_iq(ma, san, so):
    ds = iq(f"company/{ma}/price-history?timeFrame=ONE_DAY&page=0&size={so}")
    td = {}
    if san in ("HOSE", "HSX"):
        try:
            for x in iq(f"company/{ma}/proprietary-history?timeFrame=ONE_DAY&page=0&size={min(so, 250)}", so_lan=1) or []:
                if x.get("tradingDate") is not None:
                    td[_ngay(x["tradingDate"])] = _r((x.get("totalTradeNetValue") or 0) / 1e9)
        except Exception:                                           # noqa: BLE001 – tự doanh là phần phụ
            td = {}
    return gon_gia(ds, td)


def noi_gia(cu, moi, so=SO_PHIEN):
    """Ghép lịch sử cũ + các phiên mới tải (moi đè ngày trùng) → giữ so phiên gần nhất; None khi giá cũ đã bị điều chỉnh
    lại (cổ tức / chia tách – giá đóng cửa điều chỉnh ngày trùng lệch > 0,2 %) hoặc không có ngày trùng → phải tải đủ."""
    chung = [d for d in moi["d"] if d in set(cu["d"])]
    if not chung:
        return None
    d0 = chung[0]
    a, b = cu["c"][cu["d"].index(d0)], moi["c"][moi["d"].index(d0)]
    if not a or not b or abs(a / b - 1) > 0.002:
        return None
    giu = [i for i, d in enumerate(cu["d"]) if d < moi["d"][0]]
    khoa = [k for k in dict.fromkeys(list(moi) + list(cu)) if isinstance(moi.get(k, cu.get(k)), list)]
    out = {k: [(cu.get(k) or [None] * len(cu["d"]))[i] for i in giu] + (moi.get(k) or [None] * len(moi["d"])) for k in khoa}
    if all(v is None for v in out.get("td", [None])):
        out.pop("td", None)
    return {k: v[-so:] for k, v in out.items()}


def lay_gia(ma, san="", cu=None):
    """Lịch sử giá: đã có file (không phải nguồn dự phòng) → CHỈ tải các phiên mới rồi nối (nhanh, ít lượt gọi IQ); giá
    cũ bị điều chỉnh / thiếu ngày trùng → tải đủ SO_PHIEN; IQ lỗi → nến gap-chart (dự phòng) khi chưa có file."""
    cu = cu if cu and cu.get("d") and not cu.get("du_phong") else None
    try:
        if cu:
            ngay = (date.today() - date.fromisoformat(cu["d"][-1])).days
            moi = _lay_gia_iq(ma, san, min(SO_PHIEN, max(5, ngay * 5 // 7 + 5)))
            ghep = noi_gia(cu, moi) if moi["d"] else cu
            if ghep is not None:
                return ghep
        g = _lay_gia_iq(ma, san, SO_PHIEN)
    except Exception:                                               # noqa: BLE001 – IQ chặn
        if cu:
            raise                                                   # giữ file cũ (đủ khối ngoại) – lượt sau làm lại
        return gia_du_phong(ma)
    if not g["d"]:
        raise ValueError("không có lịch sử giá")
    return g


# ---------------------------------------------------------------- doanh nghiệp
def chu_html(x, toi_da=4000):
    """HTML hồ sơ Vietcap → chữ thường (bỏ thẻ, giải mã &…;)."""
    t = re.sub(r"<(br|/p|/div|/li)[^>]*>", "\n", str(x or ""), flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t).strip()
    return t[:toi_da]


def gon_chi_tiet(d):
    if not d:
        return None
    k = ("viOrganName", "viOrganShortName", "sectorVn", "comTypeCode", "rating", "ratingAsOf", "analyst")
    out = {x: d.get(x) for x in k if d.get(x) not in (None, "")}
    for a, b, h in (("targetPrice", "muc_tieu", 1e-3), ("currentPrice", "gia", 1e-3), ("marketCap", "von_hoa", 1e-9),
                    ("numberOfSharesMktCap", "so_cp", 1), ("issueShare", "cp_niem_yet", 1),
                    ("highestPrice1Year", "cao_1n", 1e-3), ("lowestPrice1Year", "thap_1n", 1e-3),
                    ("foreignerPercentage", "nn_pt", 100), ("maximumForeignPercentage", "room_pt", 100),
                    ("averageMatchValue1Month", "gt_tb_1t", 1e-9), ("averageMatchVolume1Month", "kl_tb_1t", 1),
                    ("upsideToTargetPercent", "upside_pt", 100), ("dividendPerShareTsr", "co_tuc_tsr", 1),
                    ("projectedTSRPercentage", "tsr_pt", 100), ("statePercentage", "nha_nuoc_pt", 100)):
        if d.get(a) is not None:
            out[b] = _r(float(d[a]) * h, 4)
    out["ho_so"] = chu_html(d.get("profile"))
    return out


def gon_co_cau(d):
    if not d:
        return None
    return {k: _r((d.get(a) or 0) * 100, 3) for k, a in (("nha_nuoc", "statePercentage"), ("nuoc_ngoai", "foreignPercentage"),
                                                           ("hdqt", "bodPercentage"), ("to_chuc", "institutionPercentage"),
                                                           ("khac", "otherPercentage"))} | {"tong_cp": d.get("totalShares")}


def gon_co_dong(ds, so=40):
    out = []
    for x in sorted(ds or [], key=lambda x: -(x.get("percentage") or 0))[:so]:
        out.append({"ten": x.get("ownerName") or "", "ma": x.get("ownerCode") or "", "cv": x.get("positionName") or "",
                    "sl": x.get("quantity"), "pt": _r((x.get("percentage") or 0) * 100, 3),
                    "loai": {"CORPORATE": "Tổ chức", "INDIVIDUAL": "Cá nhân"}.get(x.get("ownerType"), x.get("ownerType") or ""),
                    "ngay": _ngay(x.get("publicDate") or x.get("updateDate"))})
    return out


def gon_su_kien(ds, so=80):
    out = []
    for x in ds or []:
        ngay = _ngay(x.get("exrightDate") or x.get("issueDate") or x.get("publicDate") or x.get("displayDate1"))
        if not ngay:
            continue
        out.append({"ngay": ngay, "cong_bo": _ngay(x.get("publicDate")), "chot": _ngay(x.get("recordDate")),
                    "thuc_hien": _ngay(x.get("issueDate") or x.get("payoutDate")), "ma_sk": x.get("eventCode") or "",
                    "loai": x.get("eventNameVi") or "", "ten": x.get("eventTitleVi") or "", "nhom": x.get("category") or "",
                    "ty_le": _r(x.get("exerciseRatio"), 4), "gia_tri": _r(x.get("valuePerShare"), 2)})
    out.sort(key=lambda r: r["ngay"], reverse=True)
    return out[:so]


def gon_noi_bo(ds, so=40):
    out = []
    for x in (ds or [])[:so]:
        out.append({"ngay": _ngay(x.get("publicDate") or x.get("displayDate2")), "tu": _ngay(x.get("startDate")),
                    "den": _ngay(x.get("endDate")), "ten": x.get("traderNameVi") or "", "cv": x.get("traderPositionVi") or "",
                    "lien_quan": x.get("relativeNameVi") if x.get("relativeNameVi") != x.get("traderNameVi") else "",
                    "hd": x.get("actionTypeVi") or "", "dk": x.get("shareRegister"), "kq": x.get("shareAcquire"),
                    "truoc": x.get("shareBeforeTrade"), "sau": x.get("shareAfterTrade"),
                    "sau_pt": _r((x.get("ownershipAfterTrade") or 0) * 100, 3), "tt": x.get("tradeStatusVi") or ""})
    return out


def gon_chi_so(ds):
    """statistics-financial (quý, cũ → mới) → {"ky": ["Q2.18", …], khoá Vietcap: [...]}; chỉ giữ chỉ số có số ≠ 0; tiền →
    tỷ đồng."""
    dong = sorted((x for x in ds or [] if x.get("year") and x.get("quarter")), key=lambda x: (int(x["year"]), int(x["quarter"])))
    out = {"ky": [f"Q{int(x['quarter'])}.{int(x['year']) % 100:02d}" for x in dong]}
    for a in CHI_SO_KHOA:
        v = [_r(x.get(a), 5) for x in dong]
        if any(x not in (None, 0) for x in v):
            out[a] = [_r(x / 1e9, 1) if (a in CHI_SO_TIEN and x is not None) else x for x in v]
    return out


def nn_cuoi_nam(ma):
    """% sở hữu nước ngoài cuối mỗi năm (IQ price-history ONE_YEAR) → [[năm, %]] cũ → mới."""
    out = {}
    for x in iq(f"company/{ma}/price-history?timeFrame=ONE_YEAR&page=0&size=30") or []:
        if x.get("foreignOwnedPercentage") is not None and x.get("tradingDate"):
            out[str(x["tradingDate"])[:4]] = _r(x["foreignOwnedPercentage"] * 100, 3)
    return [[k, out[k]] for k in sorted(out)]


CAFEF_TL = "https://cafef.vn/du-lieu/Ajax/PageNew/FileBCTC.ashx?Symbol={ma}&Type={loai}&Year=0"
LOAI_TL = ((1, "BCTC", 48), (3, "Báo cáo thường niên", 12), (4, "Nghị quyết HĐQT", 12), (5, "Báo cáo quản trị", 6))


def tai_lieu(ma):
    """File gốc trên CafeF: BCTC (quý / năm, hợp nhất / mẹ, kiểm toán), BCTN, nghị quyết HĐQT, báo cáo quản trị →
    [{loai, ten, nam, ky, link}] (link PDF / trang gốc – không tải về)."""
    out = []
    for loai, ten, so in LOAI_TL:
        j = nguon.goi(CAFEF_TL.format(ma=ma, loai=loai), so_lan=2, timeout=20,
                      headers={"Referer": "https://cafef.vn/", "Origin": "https://cafef.vn"})
        n = 0
        for x in (j or {}).get("Data") or []:
            if not str(x.get("Link") or "").startswith("http"):
                continue
            out.append({"loai": ten, "ten": re.sub(r"\s+", " ", str(x.get("Name") or "")).strip()[:200],
                        "nam": str(x.get("Year") or ""), "ky": str(x.get("Time") or ""), "link": x["Link"]})
            n += 1
            if n >= so:
                break
    return out


def tin_cafef(ma, so=SO_TIN):
    """Tin liên quan CafeF (HTML) → [{ngay, tieu_de, link}]."""
    r = nguon._phien().get(CAFEF_TIN.format(ma=ma, so=so), timeout=15,
                           headers={**nguon.H, "Referer": "https://cafef.vn/", "Origin": "https://cafef.vn",
                                    "Accept": "text/html,*/*"})
    if r.status_code != 200:
        raise ValueError(f"CafeF HTTP {r.status_code}")
    return tach_tin(r.text, so)


def tach_tin(t, so=SO_TIN):
    """HTML tin CafeF → [{ngay, tieu_de, link}]: mỗi mốc "dd/mm/yyyy [HH:MM]" lấy liên kết đầu tiên ngay sau nó."""
    out, da = [], set()
    for m in re.finditer(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}:\d{2}))?", t):
        a = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t[m.end():m.end() + 2000], re.S)
        if not a:
            continue
        tieu = html.unescape(re.sub(r"<[^>]+>|\s+", " ", a.group(2))).strip()
        link = a.group(1)
        link = "https://cafef.vn" + link if link.startswith("/") else link
        if not tieu or not link.startswith("http") or link in da:
            continue
        da.add(link)
        out.append({"ngay": f"{m.group(3)}-{m.group(2)}-{m.group(1)}" + (f" {m.group(4)}" if m.group(4) else ""),
                    "tieu_de": tieu[:300], "link": link})
        if len(out) >= so:
            break
    return out


def ho_so_kbs(ma):
    """KBS: ngày thành lập / niêm yết, vốn điều lệ (tỷ), mệnh giá, giá chào sàn, ngành nghề, công ty con – liên kết (% sở
    hữu), ban lãnh đạo → dict gọn (mọi danh sách khác KBS trả về giữ nguyên ≤ 60 dòng)."""
    d = nguon.goi(KBS_HO_SO.format(ma=ma), so_lan=2, timeout=20, headers={"Referer": "https://kbbuddy.kbsec.com.vn/",
                                                              "Origin": "https://kbbuddy.kbsec.com.vn"})
    if not isinstance(d, dict) or not d:
        raise ValueError("KBS rỗng")
    out = {"thanh_lap": d.get("FD"), "niem_yet": d.get("LD"), "von_dl": d.get("CC"), "menh_gia": d.get("FV"),
           "san": d.get("EX"), "gia_chao_san": d.get("LP"), "kl_niem_yet": d.get("VL"), "nhan_vien": d.get("HM"),
           "nganh_nghe": chu_html(d.get("SM"), 3000)}
    cty = []
    for x in d.get("Subsidiaries") or []:
        cty.append({"ten": x.get("NM") or "", "so_huu": _r(x.get("OR")), "von": x.get("CC") if (x.get("CC") or 0) > 0 else None,
                    "ngay": _ngay(x.get("D")), "ghi_chu": x.get("CR") or ""})
    out["cong_ty"] = cty
    out["lanh_dao"] = [{"ten": x.get("NM") or "", "cv": x.get("PI") or x.get("PN") or "", "cv_day_du": x.get("PO") or "",
                        "tu": x.get("FD") or ""} for x in d.get("Leaders") or []]
    for k, v in d.items():                                          # danh sách khác (nếu KBS có) – giữ để trang hiện
        if isinstance(v, list) and k not in ("Subsidiaries", "Leaders") and v:
            out.setdefault("khac", {})[k] = v[:60]
    return out


def tom_tat_simplize(ma):
    j = nguon.goi(SIMPLIZE_TOM_TAT.format(ma=ma), so_lan=2, timeout=20, headers={"Referer": "https://simplize.vn/",
                                                                     "Origin": "https://simplize.vn"})
    d = (j or {}).get("data") or {}
    if not d:
        raise ValueError("Simplize rỗng")
    return {"ten": d.get("nameVi") or d.get("name") or "", "website": d.get("website") or "",
            "nganh": d.get("industryActivity") or "", "nhom": d.get("bcEconomicSectorName") or "",
            "loai": d.get("bcIndustryGroupType") or "", "dich_vu": chu_html(d.get("mainService"), 2500),
            "linh_vuc": chu_html(d.get("businessLine"), 3000), "chien_luoc": chu_html(d.get("businessStrategy"), 3000),
            "rui_ro": chu_html(d.get("businessRisk"), 2500)}


def bao_cao_ctck(ma, so=25):
    """Báo cáo phân tích CTCK (Simplize – có link PDF + giá mục tiêu; CafeF – tiêu đề + link) → [{ngay, ctck, kn, mt
    (nghìn đ), tieu_de, link, nguon}] mới → cũ, gộp trùng (CTCK, ngày). Chỉ tiêu đề / link – không lưu PDF."""
    out = []
    try:
        for x in nguon._ds(nguon.goi(SIMPLIZE_BC.format(ma=ma), so_lan=2, timeout=20, headers={"Referer": "https://simplize.vn/",
                                                                                   "Origin": "https://simplize.vn"})):
            d = str(x.get("issueDate") or "")
            ngay = f"{d[6:10]}-{d[3:5]}-{d[:2]}" if re.fullmatch(r"\d{2}/\d{2}/\d{4}", d) else _ngay(d)
            mt = x.get("targetPrice")
            out.append({"ngay": ngay, "ctck": str(x.get("source") or "").upper(), "kn": x.get("recommend") or "",
                        "mt": _r(float(mt) / 1000, 2) if mt else None, "tieu_de": x.get("title") or x.get("name") or "",
                        "link": x.get("attachedLink") or "", "nguon": "Simplize"})
    except Exception:                                               # noqa: BLE001
        pass
    try:
        j = nguon.goi(CAFEF_BC.format(ma=ma), so_lan=2, timeout=20, headers={"Referer": "https://cafef.vn/", "Origin": "https://cafef.vn"})
        for x in (j or {}).get("Data") or []:
            m = re.search(r"\d{10,}", str(x.get("DateDeploy") or ""))
            ngay = date.fromtimestamp(int(m.group(0)) / 1000).isoformat() if m else None
            lk = ("https://cafefnew.mediacdn.vn/Images/Uploaded/DuLieuDownload/PhanTichBaoCao/" + str(x["FileName"])
                  if x.get("FileName") else "")
            out.append({"ngay": ngay, "ctck": str(x.get("ResourceCode") or "").upper(), "kn": "", "mt": None,
                        "tieu_de": str(x.get("Title") or "").strip(), "link": lk, "nguon": "CafeF"})
    except Exception:                                               # noqa: BLE001
        pass
    gop, da = [], {}
    for x in sorted((x for x in out if x["ngay"]), key=lambda x: (x["ngay"], x["nguon"] == "Simplize"), reverse=True):
        k = (x["ctck"], x["ngay"])
        if k in da:
            g = da[k]
            for c in ("kn", "mt", "link"):
                g[c] = g[c] or x[c]
            continue
        da[k] = x
        gop.append(x)
    return gop[:so]


# hạn làm mới (ngày) từng phần dn – ít đổi thì làm thưa để bớt lượt gọi (IQ chặn khi gọi dồn)
PHIEN_BAN_DN = 2                                                   # đổi định dạng phần nào → tăng để làm mới hết
HAN_PHAN = {"ct": 7, "cc": 7, "cd": 7, "cs": 7, "kbs": 14, "sz": 30, "sk": 2, "nb": 2, "tin": 1, "bc": 3, "nn_nam": 30,
            "tl": 3}


def lay_dn(ma, cu=None, hom_nay=None):
    """Mọi phần doanh nghiệp; phần còn hạn giữ nguyên, phần lỗi giữ bản cũ (cu). → (dn, phần lỗi) – dn["ngay_phan"]
    ghi ngày làm mới từng phần."""
    cu = cu or {}
    hom_nay = hom_nay or date.today().isoformat()
    ngay_phan = dict(cu.get("ngay_phan") or {}) if cu.get("phien_ban") == PHIEN_BAN_DN else {}
    phan = {
        "ct": lambda: gon_chi_tiet(iq(f"company/{ma}")),
        "cc": lambda: gon_co_cau(iq(f"company/{ma}/shareholder-structure")),
        "cd": lambda: gon_co_dong(iq(f"company/{ma}/shareholder")),
        "sk": lambda: gon_su_kien(iq(f"events?ticker={ma}&fromDate=20120101&toDate={date.today().year + 1}1231"
                                     f"&page=0&size=300")),
        "nb": lambda: gon_noi_bo(iq(f"company/{ma}/insider-transaction?page=0&size=40")),
        "cs": lambda: gon_chi_so(iq(f"company/{ma}/statistics-financial")),
        "tin": lambda: tin_cafef(ma),
        "bc": lambda: bao_cao_ctck(ma),
        "kbs": lambda: ho_so_kbs(ma),
        "sz": lambda: tom_tat_simplize(ma),
        "nn_nam": lambda: nn_cuoi_nam(ma),
        "tl": lambda: tai_lieu(ma),
    }
    out, loi = {}, []
    for k, f in phan.items():
        n = ngay_phan.get(k)
        if k in cu and n and (date.fromisoformat(hom_nay) - date.fromisoformat(n)).days < HAN_PHAN.get(k, 1):
            out[k] = cu[k]
            continue
        t0 = time.time()
        try:
            out[k] = f()
            ngay_phan[k] = hom_nay
            _do(k, True, time.time() - t0)
        except Exception as e:                                      # noqa: BLE001 – 1 phần lỗi không bỏ cả mã
            _do(k, False, time.time() - t0)
            loi.append(k)
            if k in cu:
                out[k] = cu[k]
            if "HTTP 403" in str(e) or "HTTP 429" in str(e):
                time.sleep(3)
    out["ngay_phan"], out["phien_ban"] = ngay_phan, PHIEN_BAN_DN
    return out, loi


def cau_truc_bctc():
    """{loại DN: {"cd" | "kd" | "lc": [[field, level, tên], …]}} từ financial-statement/metrics của mã mẫu."""
    ten = {"BALANCE_SHEET": "cd", "INCOME_STATEMENT": "kd", "CASH_FLOW": "lc"}
    out = {}
    for loai, ma in MAU_CAU_TRUC.items():
        try:
            d = iq(f"company/{ma}/financial-statement/metrics")
        except Exception:                                           # noqa: BLE001
            continue
        out[loai] = {ten[k]: [[x.get("field"), x.get("level") or 1, x.get("titleVi") or x.get("fullTitleVi") or ""]
                              for x in v or [] if x.get("field")] for k, v in (d or {}).items() if k in ten}
    return out


# ---------------------------------------------------------------- chạy
def _doc(duong):
    try:
        with open(duong, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _ghi(obj, duong):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tam, duong)


def thu_tu(ds_ma, ra, hom_nay=None, lam_moi=False):
    """Mã cần làm, cũ nhất trước: chưa có file → trước hết; rồi theo ngày cập nhật gia / dn; cùng độ cũ: file định dạng cũ
    (phien_ban) trước, rồi thứ tự ds_ma (ds.json xếp vốn hoá lớn trước). lam_moi: thêm cả mã đã cập nhật hôm nay nhưng
    file còn định dạng cũ (chạy nối sau khi đổi định dạng – không làm lại mã đã xong)."""
    hom_nay = hom_nay or date.today().isoformat()

    def tuoi(m):
        g = (_doc(os.path.join(ra, "gia", f"{m}.json")) or {}).get("cap_nhat") or ""
        dn = _doc(os.path.join(ra, "dn", f"{m}.json")) or {}
        return min(g, dn.get("cap_nhat") or ""), dn.get("phien_ban") == PHIEN_BAN_DN
    ds = [(*tuoi(m), i, m) for i, m in enumerate(ds_ma)]
    return [m for t, moi, i, m in sorted(ds) if t < hom_nay or (lam_moi and not moi)]


def chay(ds_ma, ra, san=None, phut=25, luong=6, in_ra=print, lam_moi=False):
    """Lấy giá + doanh nghiệp cho ds_ma (xoay vòng, giới hạn phút) → (số mã xong, số mã lỗi, số mã còn lại)."""
    san = san or {}
    bat_dau = time.time()
    viec = thu_tu(ds_ma, ra, lam_moi=lam_moi)
    hom_nay = date.today().isoformat()
    xong, loi, con = 0, 0, 0

    def mot(m):
        """True khi có ít nhất 1 phần mới (giá hoặc doanh nghiệp)."""
        ok, t0 = True, time.time()
        try:
            g_cu = _doc(os.path.join(ra, "gia", f"{m}.json"))
            _ghi({**lay_gia(m, san.get(m, ""), g_cu), "cap_nhat": hom_nay}, os.path.join(ra, "gia", f"{m}.json"))
        except Exception:                                           # noqa: BLE001
            ok = False
        _do("gia", ok, time.time() - t0)
        dai = os.path.join(ra, "gia_dai", f"{m}.json")
        cu_dai = (_doc(dai) or {}).get("cap_nhat") or ""
        if not cu_dai or (date.fromisoformat(hom_nay) - date.fromisoformat(cu_dai)).days >= HAN_GIA_DAI:
            t1 = time.time()
            try:
                _ghi({**lay_gia_dai(m), "cap_nhat": hom_nay}, dai)
                _do("gia_dai", True, time.time() - t1)
            except Exception:                                       # noqa: BLE001 – lịch sử dài là phần phụ
                _do("gia_dai", False, time.time() - t1)
        dn_cu = _doc(os.path.join(ra, "dn", f"{m}.json")) or {}
        dn, hong = lay_dn(m, dn_cu, hom_nay)
        if len(hong) < SO_PHAN_DN:
            _ghi({**dn, "cap_nhat": hom_nay if len(hong) <= 1 else dn_cu.get("cap_nhat", ""), "loi": hong},
                 os.path.join(ra, "dn", f"{m}.json"))
        return ok or len(hong) < SO_PHAN_DN

    with ThreadPoolExecutor(luong) as ex:
        tuong_lai = {}
        for m in viec:
            if time.time() - bat_dau > phut * 60:
                con += 1
                continue
            tuong_lai[ex.submit(mot, m)] = m
            while len(tuong_lai) >= luong * 2:
                for f in as_completed(list(tuong_lai)):
                    del tuong_lai[f]
                    try:
                        xong += bool(f.result())
                    except Exception:                               # noqa: BLE001
                        loi += 1
                    break
        for f in as_completed(list(tuong_lai)):
            try:
                xong += bool(f.result())
            except Exception:                                       # noqa: BLE001
                loi += 1
    in_ra(f"Doanh nghiệp: {xong}/{len(viec)} mã cập nhật · lỗi {loi} · hết giờ chưa làm {con} · "
          f"{(time.time() - bat_dau) / 60:.1f} phút · Vietcap IQ nghỉ {VAN_IQ.so_nghi} lần{' – TẮT (bị chặn)' if VAN_IQ.tat else ''}"
          f"\n  nguồn (được/lần · giây): {bang_thong_ke()}")
    return xong, loi, con


def chi_so_nganh(ra, ds):
    """Trung vị chỉ số kỳ gần nhất (statistics-financial trong dn/<MÃ>.json) theo ngành của ds.json → chi_so_nganh.json
    {ngành: {khoá: [trung vị, số mã]}} – trang so sánh mã với ngành ở mục Chỉ số."""
    import statistics
    gom = {}
    for r in ds:
        cs = (_doc(os.path.join(ra, "dn", f"{r['ma']}.json")) or {}).get("cs") or {}
        if not r.get("nganh") or not cs.get("ky"):
            continue
        g = gom.setdefault(r["nganh"], {})
        for k in CHI_SO_KHOA:
            v = cs.get(k)
            if v and v[-1] is not None:
                g.setdefault(k, []).append(v[-1])
    out = {ng: {k: [round(statistics.median(v), 5), len(v)] for k, v in g.items() if len(v) >= 3} for ng, g in gom.items()}
    _ghi(out, os.path.join(ra, "chi_so_nganh.json"))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description="Dữ liệu doanh nghiệp cho trang Tra cứu mã")
    p.add_argument("--ra", default="docs/ma/du_lieu")
    p.add_argument("--ma", default="", help="danh sách mã (trống = mọi mã trong <ra>/ds.json)")
    p.add_argument("--phut", type=float, default=25)
    p.add_argument("--luong", type=int, default=6)
    p.add_argument("--lam_moi", action="store_true", help="làm cả mã đã cập nhật hôm nay (cũ nhất trước)")
    a = p.parse_args(argv)
    ds = (_doc(os.path.join(a.ra, "ds.json")) or {}).get("ds") or []
    san = {r["ma"]: r.get("san", "") for r in ds}
    ma = [m.strip().upper() for m in a.ma.split(",") if m.strip()] or [r["ma"] for r in ds]
    ct = cau_truc_bctc()
    if ct:
        _ghi(ct, os.path.join(a.ra, "cau_truc_bctc.json"))
    print(f"Cấu trúc BCTC: {', '.join(sorted(ct)) or 'lỗi – dùng thứ tự kho'}")
    chay(ma, a.ra, san, a.phut, a.luong, lam_moi=a.lam_moi)
    ng = chi_so_nganh(a.ra, ds)
    print(f"Chỉ số ngành: {len(ng)} ngành")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
