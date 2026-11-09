# -*- coding: utf-8 -*-
"""
BỘ LỌC KỸ THUẬT cho trang Tra cứu mã (chế độ "Kỹ thuật" của Lọc) – chạy SAU tra_cuu_dn (cần gia/<MÃ>.json) trong workflow
Du lieu tra cuu. Ghi thêm vào từng dòng ds.json (giá đóng cửa phiên gần nhất, giá điều chỉnh):
  p1t p3t p6t p1n   lãi 1 / 3 / 6 tháng, 1 năm (21 / 63 / 126 / 250 phiên)
  tr20 tr50 tr200   % giá trên (> 0) / dưới MA20 / MA50 / MA200
  rsi               RSI 14 (Wilder)          kl_d   KL phiên cuối ÷ TB 20 phiên trước
  atr               ATR 14 ÷ giá (biến động ngày)
  d52               1 = đóng cửa cao nhất 52 tuần trong 5 phiên gần nhất
  nen vcp vuot      nền tích lũy (≥ 15 phiên, biên độ ≤ 18%) như "Nền tích lũy / VCP" của trang Biểu đồ: số phiên nền đang có
                    (0 = không) · 1 = co hẹp dần (VCP) · 1 = vừa vượt đỉnh nền trong 5 phiên
  python -m thi_truong.ky_thuat_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os


def _tb(x):
    x = [v for v in x if v is not None]
    return sum(x) / len(x) if x else None


def nen_tai(h, lo, i, lmin=15, lmax=60, rong=0.18):
    """Nền dài nhất kết thúc ở phiên i: (cao nhất − thấp nhất) / cao nhất ≤ rong (giống nen_tai của docs/ma/index.html)."""
    cao, thap, tot = float("-inf"), float("inf"), None
    for L in range(1, min(lmax, i + 1) + 1):
        j = i - L + 1
        if not (h[j] or 0) > 0 or not (lo[j] or 0) > 0:
            break
        cao, thap = max(cao, h[j]), min(thap, lo[j])
        if (cao - thap) / cao > rong:
            break
        if L >= lmin:
            tot = {"i0": j, "i1": i, "cao": cao, "thap": thap, "L": L}
    if not tot:
        return None
    i0, ba = tot["i0"], tot["L"] // 3

    def sau(k):
        a, b = i0 + k * ba, (i + 1 if k == 2 else i0 + (k + 1) * ba)
        hh, ll = max(h[a:b]), min(lo[a:b])
        return (hh - ll) / hh
    d = [sau(k) for k in range(3)]
    return {**tot, "vcp": d[0] > d[1] > d[2]}


def chi_so(g):
    """gia/<MÃ>.json → dict chỉ số kỹ thuật (thiếu phiên → {})."""
    c, h, lo, v = (list((g or {}).get(k) or []) for k in ("c", "h", "l", "v"))
    n = len(c)
    if n < 60 or not c[-1]:
        return {}
    h = [x if x else c[i] for i, x in enumerate(h)] if len(h) == n else c[:]
    lo = [x if x else c[i] for i, x in enumerate(lo)] if len(lo) == n else c[:]
    out = {}
    for ten, k in (("p1t", 21), ("p3t", 63), ("p6t", 126), ("p1n", 250)):
        out[ten] = round(c[-1] / c[-1 - k] - 1, 4) if n > k and c[-1 - k] else None
    for k in (20, 50, 200):
        m = _tb(c[-k:]) if n >= k else None
        out[f"tr{k}"] = round(c[-1] / m - 1, 4) if m else None
    tang = giam = 0.0                                                      # RSI 14 Wilder
    for i in range(1, n):
        d = c[i] - c[i - 1]
        if i <= 14:
            tang, giam = tang + max(d, 0) / 14, giam + max(-d, 0) / 14
        else:
            tang, giam = (tang * 13 + max(d, 0)) / 14, (giam * 13 + max(-d, 0)) / 14
    out["rsi"] = round(100 - 100 / (1 + tang / giam), 1) if giam else 100.0
    tb20 = _tb([x for x in v[-21:-1] if x]) if len(v) == n else None
    out["kl_d"] = round(v[-1] / tb20, 2) if tb20 and v[-1] is not None else None
    tr = [max(h[i] - lo[i], abs(h[i] - c[i - 1]), abs(lo[i] - c[i - 1])) for i in range(n - 14, n)]
    out["atr"] = round(sum(tr) / 14 / c[-1], 4)
    out["d52"] = int(max(c[-5:]) >= max(c[-250:]))
    b, vuot = None, 0
    for k in range(1, 6):                       # vượt nền trước: nến vượt (< +18%) vẫn lọt vào "nền" tính tới nến cuối
        z = nen_tai(h, lo, n - 1 - k)
        if z and c[-1] > z["cao"]:
            b, vuot = z, 1
            break
    b = b or nen_tai(h, lo, n - 1)
    out["nen"], out["vcp"], out["vuot"] = (b["L"] if b and not vuot else 0), int(bool(b and b["vcp"])), vuot
    return out


COT = ("p1t", "p3t", "p6t", "p1n", "tr20", "tr50", "tr200", "rsi", "kl_d", "atr", "d52", "nen", "vcp", "vuot")


def main(argv=None):
    p = argparse.ArgumentParser(description="Bộ lọc kỹ thuật cho trang Tra cứu mã")
    p.add_argument("--ra", default=os.path.join("docs", "ma", "du_lieu"))
    a = p.parse_args(argv)
    f = os.path.join(a.ra, "ds.json")
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    co = 0
    for r in d.get("ds") or []:
        try:
            with open(os.path.join(a.ra, "gia", f"{r['ma']}.json"), encoding="utf-8") as fh:
                x = chi_so(json.load(fh))
        except (OSError, ValueError, KeyError):
            x = {}
        co += bool(x)
        for k in COT:
            r[k] = x.get(k)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
    ds = d.get("ds") or []
    print(f"Kỹ thuật: {co}/{len(ds)} mã · trong nền {sum(bool(r.get('nen')) for r in ds)} · VCP {sum(bool(r.get('vcp')) for r in ds)}"
          f" · vừa vượt nền {sum(bool(r.get('vuot')) for r in ds)} · đỉnh 52 tuần {sum(bool(r.get('d52')) for r in ds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
