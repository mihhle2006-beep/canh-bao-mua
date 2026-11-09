# -*- coding: utf-8 -*-
"""
PHẢN ỨNG GIÁ SAU BCTC QUÝ cho trang Tra cứu mã (tab Lịch sử giá) + KIỂM ĐỊNH PEAD (giá trôi tiếp sau công bố) in ra log –
chạy SAU tra_cuu_dn (cần gia/ & gia_dai/) và vni_web (vni.json) trong workflow Du lieu tra cuu.

  Ngày BIẾT CHẮC = sớm hơn của (ngày công bố Vietcap trong kho, hạn công bố BCTC hợp nhất = hết quý + 30 ngày). Ngày Vietcap
  của quý 2 / quý 4 thường là bản soát xét / kiểm toán (muộn) → hạn luật là mốc chắc chắn đã có số (doanh nghiệp nộp trễ
  hạn: hiếm ở mã thanh khoản – chấp nhận). Phiên E = phiên đầu tiên SAU ngày biết chắc (công bố thường sau giờ giao dịch).
  Mỗi quý: LNST (tỷ), so cùng kỳ, SUE = (LNST − cùng kỳ) ÷ độ lệch chuẩn 8 lần chênh trước · phản ứng 2 phiên (đóng cửa
  E−2 → E) · lãi 5 / 20 / 60 phiên SAU E (đóng cửa E → E+n) · vượt VN-Index 20 phiên.
  → ma/<MÃ>.json thêm "pu": [[quý, ngày biết chắc, LNST, so cùng kỳ, SUE, phản ứng, +5, +20, +60, vượt VNI 20], …] (cũ → mới).

  --pead: mỗi quý báo cáo, xếp các mã (vốn hoá ≥ 1.000 tỷ) theo SUE / so cùng kỳ / phản ứng 2 phiên → lãi VƯỢT VN-Index 20 / 60
  phiên sau E của nhóm 20 % cao nhất − 20 % thấp nhất; tương quan hạng (IC); 2018–21 vs 2022+.
  python -m thi_truong.phan_ung_bctc --ra docs/ma/du_lieu --kho danh-muc/du_lieu/bctc [--pead]
"""
import argparse
import bisect
import json
import os
import statistics
from datetime import date, timedelta

HAN = 30                       # ngày sau hết quý: hạn công bố BCTC quý hợp nhất (TT96/2020)
TU_NAM = 2018


def _gon(gd):
    """{d0, g (cách ngày), c} → (ngày ISO, đóng cửa)."""
    if not gd or not gd.get("c"):
        return [], []
    d, t = [], date.fromisoformat(gd["d0"])
    for k in gd.get("g") or [0] * len(gd["c"]):
        t += timedelta(days=k)
        d.append(t.isoformat())
    return d, list(gd["c"])


def chuoi_gia(g, gd):
    """gia/ (~2 năm) + gia_dai/ (từ khi niêm yết, quy đổi theo tỷ lệ ở ngày nối) → (ngày, đóng cửa) – như chuoi_gia của trang."""
    D, C = _gon(gd)
    if not (g or {}).get("d"):
        return D, C
    d, c = list(g["d"]), list(g["c"])
    het = next((i for i, x in enumerate(D) if x >= d[0]), len(D))
    if het:
        j = D.index(d[0]) if d[0] in D else -1
        k = c[0] / C[j] if j >= 0 and C[j] and c[0] else 1.0
        d, c = D[:het] + d, [x * k if x else x for x in C[:het]] + c
    return d, c


def _het_quy(ky):
    y, q = int(ky[:4]), int(ky[-1])
    return date(y, *{1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}[q])


def _lui(ky, n):
    t = int(ky[:4]) * 4 + int(ky[-1]) - 1 + n
    return f"{t // 4}-Q{t % 4 + 1}"


def _r(x, le=4):
    return round(x, le) if x is not None else None


def phan_ung(kho, d, c, vni=None, tu_nam=TU_NAM):
    """kho BCTC 1 mã + chuỗi giá (ngày, đóng cửa) [+ {ngày: VN-Index}] → danh sách quý (xem docstring)."""
    kd, ncb = ((kho or {}).get("ky") or {}).get("kd") or {}, ((kho or {}).get("ngay_cb") or {}).get("kd") or {}

    def ln(k):
        v = (kd.get(k) or {}).get("isa20")
        return v / 1e9 if isinstance(v, (int, float)) else None

    def i_sau(ng):                                     # phiên đầu tiên SAU ngày ng
        i = bisect.bisect_right(d, ng)
        return i if i < len(d) else None

    def lai(a, b):
        return c[b] / c[a] - 1 if a is not None and b is not None and 0 <= a < len(c) and b < len(c) and c[a] and c[b] else None

    def vni_lai(a, b):
        if vni is None or a is None or b is None or b >= len(d):
            return None
        x, y = vni.get(d[a]), vni.get(d[b])
        return y / x - 1 if x and y else None
    out = []
    for k in sorted(x for x in kd if "-Q" in x and int(x[:4]) >= tu_nam):
        v, cu = ln(k), ln(_lui(k, -4))
        if v is None:
            continue
        han = (_het_quy(k) + timedelta(days=HAN)).isoformat()
        biet = min(ncb.get(k, han)[:10], han)
        E = i_sau(biet)
        if E is None:
            continue
        dl = [ln(_lui(k, -j)) - ln(_lui(k, -j - 4)) for j in range(1, 9)
              if ln(_lui(k, -j)) is not None and ln(_lui(k, -j - 4)) is not None]
        sd = statistics.pstdev(dl) if len(dl) >= 6 else 0
        r20, v20 = lai(E, E + 20), vni_lai(E, E + 20)
        out.append([k, biet, _r(v, 1), _r(v / cu - 1 if cu and cu > 0 else None), _r((v - cu) / sd if cu is not None and sd else None, 2),
                    _r(lai(E - 2, E) if E >= 2 else None), _r(lai(E, E + 5)), _r(r20), _r(lai(E, E + 60)),
                    _r(r20 - v20 if r20 is not None and v20 is not None else None)])
    return out


def pead(ds_pu, vni_d, vni_c, von=None, von_min=1000):
    """{mã: (pu, ngày, đóng cửa)} → chuỗi in: nhóm cao − thấp & IC theo SUE / so cùng kỳ / phản ứng 2 phiên (lãi vượt VNI)."""
    vni = dict(zip(vni_d, vni_c))
    hang = {}                                          # quý → [(mã, sue, yoy, phản ứng vượt, vượt 20, vượt 60, năm)]
    for ma, (pu, d, c) in ds_pu.items():
        if von is not None and (von.get(ma) or 0) < von_min:
            continue
        for q in pu:
            ky, biet = q[0], q[1]
            E = bisect.bisect_right(d, biet)
            if E >= len(d) or E < 2:
                continue

            def vuot(a, b):
                if b >= len(d) or not c[a] or not c[b] or d[a] not in vni or d[b] not in vni:
                    return None
                return (c[b] / c[a] - 1) - (vni[d[b]] / vni[d[a]] - 1)
            hang.setdefault(ky, []).append((ma, q[4], q[3], vuot(E - 2, E), vuot(E, E + 20), vuot(E, E + 60), int(ky[:4])))

    def rank(x):
        s = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        for j, i in enumerate(s):
            r[i] = j
        return r

    def ic(a, b):
        ra, rb = rank(a), rank(b)
        ma_, mb = statistics.mean(ra), statistics.mean(rb)
        sa = sum((x - ma_) ** 2 for x in ra) ** .5
        sb = sum((y - mb) ** 2 for y in rb) ** .5
        return sum((x - ma_) * (y - mb) for x, y in zip(ra, rb)) / (sa * sb) if sa and sb else None
    dong = ["PEAD – lãi VƯỢT VN-Index sau phiên E (phiên đầu sau ngày biết chắc); mỗi quý xếp các mã, nhóm 20% cao − 20% thấp"]
    for ten, j in (("SUE", 1), ("LNST so cùng kỳ", 2), ("Phản ứng 2 phiên", 3)):
        for kq, m in (("20 phiên", 4), ("60 phiên", 5)):
            ch, ics, n, gd = [], [], 0, {"2018–21": [], "2022+": []}
            for ky, x in sorted(hang.items()):
                x = [z for z in x if z[j] is not None and z[m] is not None]
                if len(x) < 20:
                    continue
                x.sort(key=lambda z: z[j])
                k5 = max(1, len(x) // 5)
                s = statistics.mean(z[m] for z in x[-k5:]) - statistics.mean(z[m] for z in x[:k5])
                ch.append(s)
                gd["2018–21" if x[0][6] <= 2021 else "2022+"].append(s)
                v = ic([z[j] for z in x], [z[m] for z in x])
                if v is not None:
                    ics.append(v)
                n += len(x)
            if ch:
                dong.append(f"  {ten:18s} {kq}: cao − thấp TB {statistics.mean(ch) * 100:+.1f} điểm % · {sum(s > 0 for s in ch)}/{len(ch)} quý > 0"
                            f" · IC {statistics.mean(ics):+.3f} · " + " · ".join(f"{g} {statistics.mean(v) * 100:+.1f}" for g, v in gd.items() if v)
                            + f" · {n} mã-quý")
    return "\n".join(dong)


def main(argv=None):
    p = argparse.ArgumentParser(description="Phản ứng giá sau BCTC quý (trang Tra cứu mã) + kiểm định PEAD")
    p.add_argument("--ra", default=os.path.join("docs", "ma", "du_lieu"))
    p.add_argument("--kho", default=os.path.join("danh-muc", "du_lieu", "bctc"))
    p.add_argument("--pead", action="store_true")
    a = p.parse_args(argv)

    def doc(*duong):
        try:
            with open(os.path.join(*duong), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
    ds = (doc(a.ra, "ds.json") or {}).get("ds") or []
    vd, vc = _gon(doc(a.ra, "vni.json"))
    vni = dict(zip(vd, vc))
    tat_ca, co = {}, 0
    for r in ds:
        ma = r.get("ma")
        kho, chi = doc(a.kho, f"{ma}.json"), doc(a.ra, "ma", f"{ma}.json")
        d, c = chuoi_gia(doc(a.ra, "gia", f"{ma}.json"), doc(a.ra, "gia_dai", f"{ma}.json"))
        if not kho or not chi or len(d) < 100:
            continue
        pu = phan_ung(kho, d, c, vni)
        chi["pu"] = pu
        with open(os.path.join(a.ra, "ma", f"{ma}.json"), "w", encoding="utf-8") as f:
            json.dump(chi, f, ensure_ascii=False, separators=(",", ":"))
        co += bool(pu)
        tat_ca[ma] = (pu, d, c)
    print(f"Phản ứng BCTC: {co}/{len(ds)} mã")
    if a.pead and vd:
        print(pead(tat_ca, vd, vc, {r.get("ma"): r.get("von") for r in ds}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
