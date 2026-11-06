# -*- coding: utf-8 -*-
"""
ĐỒ THỊ XOAY VÒNG TƯƠNG ĐỐI (RRG, xấp xỉ JdK) cho trang Tra cứu mã (#rrg) – chạy SAU tra_cuu_dn (cần gia/<MÃ>.json):
  RS          = 100 × giá / VN-Index, làm mượt EMA (3 tuần / 5 phiên) cho đuôi bớt răng cưa
  RS-Ratio    = 100 + z-score của RS trong N kỳ            (> 100: mạnh hơn thị trường so với chính nó gần đây)
  RS-Momentum = 100 + z-score của ROC 1 kỳ của RS-Ratio trong N kỳ   (> 100: sức mạnh tương đối đang tăng tốc)
  Góc phần tư: Dẫn dắt (ratio > 100, mom > 100) · Suy yếu (> 100, < 100) · Tụt hậu (< 100, < 100) · Cải thiện (< 100, > 100).
  Khung tuần (đóng cửa cuối tuần, N = 10, đuôi 8) và ngày (N = 14, đuôi 10). Ngành = chỉ số gia quyền vốn hoá (ds.json "von")
  lợi suất ngày các mã trong ngành. Chỉ mã thanh khoản: GTGD TB 20 phiên ≥ 1 tỷ.
→ rrg.json {"cap_nhat", "W" | "D": {"ky": [nhãn kỳ đuôi], "ma": {MÃ: [[ratio, mom]…]}, "nganh": {ngành: […]}}}
  python -m thi_truong.rrg_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

KHUNG = {"W": (10, 8, 3), "D": (14, 10, 5)}           # N kỳ chuẩn hoá, số điểm đuôi, EMA làm mượt RS
GTGD_MIN = 1.0                                        # tỷ đồng / phiên
VN = timezone(timedelta(hours=7))


def rrg(gia, chuan, n, duoi, muot=1):
    """2 Series giá cùng chỉ mục → DataFrame [ratio, mom] đuôi `duoi` kỳ (bỏ kỳ thiếu)."""
    rs = (100 * gia / chuan).ewm(span=muot, adjust=False, ignore_na=True).mean().where((gia / chuan).notna())
    ratio = 100 + (rs - rs.rolling(n).mean()) / rs.rolling(n).std()
    roc = ratio.pct_change(fill_method=None) * 100
    mom = 100 + (roc - roc.rolling(n).mean()) / roc.rolling(n).std()
    return pd.DataFrame({"ratio": ratio, "mom": mom}).replace([float("inf"), float("-inf")], float("nan")).dropna().tail(duoi)


def theo_tuan(s):
    """Series ngày → giá đóng cửa phiên cuối mỗi tuần (nhãn = ngày phiên đó)."""
    tuan = s.index.to_period("W-FRI")
    return s.groupby(tuan).tail(1)


def chi_so_nganh(gia, ds):
    """gia: DataFrame ngày × mã · ds: dòng ds.json → DataFrame ngày × ngành (gia quyền vốn hoá, xích lợi suất ngày)."""
    loi = gia.pct_change(fill_method=None)
    out = {}
    for ng in sorted({r.get("nganh") for r in ds if r.get("nganh")}):
        ma = [r["ma"] for r in ds if r.get("nganh") == ng and r["ma"] in gia.columns and (r.get("von") or 0) > 0]
        if len(ma) < 3:
            continue
        w = pd.Series({r["ma"]: r["von"] for r in ds if r["ma"] in ma})
        x = loi[ma]
        co = x.notna()
        tb = (x.fillna(0) * w).sum(axis=1) / (co * w).sum(axis=1).replace(0, float("nan"))
        out[ng] = (1 + tb.fillna(0)).cumprod() * 100
    return pd.DataFrame(out)


def dung(ds, gia_ma, vni):
    """ds: dòng ds.json · gia_ma: {mã: json giá {d, c, v}} · vni: Series VN-Index theo ngày → dict rrg.json (chưa có cap_nhat)."""
    if vni is None or len(vni) < 60:
        return {}
    cot = {}
    for m, g in gia_ma.items():
        d, c, v = g.get("d") or [], g.get("c") or [], g.get("v") or []
        if len(c) < 60 or len(d) != len(c):
            continue
        gt = [(c[i] or 0) * (v[i] or 0) * 1000 / 1e9 for i in range(max(0, len(c) - 20), len(c))] if len(v) == len(c) else []
        if not gt or sum(gt) / len(gt) < GTGD_MIN:
            continue
        cot[m] = pd.Series([x if x else float("nan") for x in c], index=pd.to_datetime(d))
    if not cot:
        return {}
    gia = pd.DataFrame(cot).reindex(vni.index).ffill(limit=5)
    nganh = chi_so_nganh(gia, ds)
    out = {}
    for k, (n, duoi, muot) in KHUNG.items():
        b = theo_tuan(vni) if k == "W" else vni
        ky = [x.strftime("%Y-%m-%d") for x in b.index[-duoi:]]
        blk = {"ky": ky, "ma": {}, "nganh": {}}
        for ten, bang in (("ma", gia), ("nganh", nganh)):
            for m in bang.columns:
                s = bang[m].reindex(vni.index)
                s = theo_tuan(s) if k == "W" else s
                x = rrg(s, b.reindex(s.index), n, duoi, muot)
                if len(x) >= 2 and x.index[-1] == b.index[-1]:
                    blk[ten][m] = [[round(a, 2), round(c_, 2)] for a, c_ in zip(x["ratio"], x["mom"])]
        out[k] = blk
    return out


def vni_ngay(nen):
    """Nến ngày VN-Index ({t: [unix], c: [...]}) → Series theo ngày VN."""
    t, c = (nen or {}).get("t") or [], (nen or {}).get("c") or []
    if not t or len(t) != len(c):
        return None
    ngay = [datetime.fromtimestamp(int(x), VN).date() for x in t]
    s = pd.Series(c, index=pd.to_datetime(ngay))
    return s[~s.index.duplicated(keep="last")].dropna()


def main(argv=None):
    p = argparse.ArgumentParser(description="Đồ thị RRG cho trang Tra cứu mã")
    p.add_argument("--ra", default=os.path.join("docs", "ma", "du_lieu"))
    a = p.parse_args(argv)
    with open(os.path.join(a.ra, "ds.json"), encoding="utf-8") as fh:
        ds = json.load(fh).get("ds") or []
    gia_ma = {}
    for r in ds:
        try:
            with open(os.path.join(a.ra, "gia", f"{r['ma']}.json"), encoding="utf-8") as fh:
                gia_ma[r["ma"]] = json.load(fh)
        except (OSError, ValueError, KeyError):
            pass
    from . import nguon
    vni = vni_ngay(nguon.nen("VNINDEX", "ONE_DAY", 520))
    d = dung(ds, gia_ma, vni)
    if not d:
        print("RRG: thiếu VN-Index / giá – giữ file cũ")
        return 0
    d["cap_nhat"] = f"{datetime.now(VN):%Y-%m-%d %H:%M}"
    with open(os.path.join(a.ra, "rrg.json"), "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
    w = d.get("W") or {}
    print(f"RRG: {len(w.get('ma') or {})} mã · {len(w.get('nganh') or {})} ngành (tuần) · {len((d.get('D') or {}).get('ma') or {})} mã (ngày)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
