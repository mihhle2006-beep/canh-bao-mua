# -*- coding: utf-8 -*-
"""
CANSLIM cho trang Tra cứu mã (docs/ma) – chạy SAU tra_cuu_dn (cần gia/<MÃ>.json của mọi mã) trong workflow Du lieu tra cuu.
Ghi thêm vào từng dòng ds.json (danh-muc ptcp/web_tra_cuu dựng – LNST quý / 4 quý đã có sẵn):
  cs      điểm 0–5 = số chữ đạt trong C · A · N · S · L (cùng ngưỡng ptcp/canslim.diem của backtest)
  cs_d    chuỗi chữ đạt, VD "C·A·L"
  rs      hạng sức mạnh giá kiểu IBD 0–99 trong toàn bộ mã (40% lãi 3T + 20% 6T + 20% 9T + 20% 12T)
  cach52  % cách đỉnh đóng cửa 52 tuần (≤ 0)
  kl_x    khối lượng TB 20 phiên ÷ TB 120 phiên
và ds.json["canslim"] = {"m": "tăng" | "giằng co" | "giảm" | None, "vni", "ma50", "ma200", "cap_nhat", "nguong"} (M –
VN-Index so MA50 / MA200, xét riêng, không cộng vào điểm). Thiếu giá / BCTC → chữ đó không đạt (như backtest).
  python -m thi_truong.canslim_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

NGUONG = {"C": 0.25, "A": 0.20, "N": -15.0, "S": 1.2, "L": 70}     # LNST quý / 4 quý (tỷ lệ), % cách đỉnh, ×, hạng
CHU = ("C", "A", "N", "S", "L")


def _tb(x):
    x = [v for v in x if v is not None]
    return sum(x) / len(x) if x else None


def chi_tieu_gia(g):
    """gia/<MÃ>.json ({d, c, v…}) → {"cach52", "kl_x", "ibd"} (None khi thiếu phiên)."""
    c = [v for v in (g or {}).get("c") or [] if v]
    v = list((g or {}).get("v") or [])
    out = {"cach52": None, "kl_x": None, "ibd": None}
    if len(c) < 60:
        return out
    dinh = max(c[-252:])
    out["cach52"] = round((c[-1] / dinh - 1) * 100, 2) if dinh else None
    k20, k120 = _tb(v[-20:]), _tb(v[-120:])
    out["kl_x"] = round(k20 / k120, 3) if k20 and k120 else None

    def lai(n):
        return c[-1] / c[-1 - n] if len(c) > n and c[-1 - n] else None
    phan = [(0.4, lai(63)), (0.2, lai(126)), (0.2, lai(189)), (0.2, lai(252))]
    co = [(w, x) for w, x in phan if x is not None]
    if co and phan[0][1] is not None:                              # mã mới niêm yết: chuẩn hoá theo phần có dữ liệu
        out["ibd"] = sum(w * x for w, x in co) / sum(w for w, _ in co)
    return out


def hang_rs(ibd):
    """{mã: điểm IBD} → {mã: hạng 0–99} (cao hơn = mạnh hơn)."""
    ds = sorted((v, m) for m, v in ibd.items() if v is not None)
    n = len(ds)
    return {m: int(round(i / (n - 1) * 99)) if n > 1 else 99 for i, (_, m) in enumerate(ds)}


def danh_gia(r, x, nguong=NGUONG):
    """Dòng ds.json r (ln_yoy, ln4_yoy) + chỉ tiêu giá x (cach52, kl_x, rs) → (điểm, chuỗi chữ đạt)."""
    def ge(v, k):
        return v is not None and v == v and v >= nguong[k]
    dat = {"C": ge(r.get("ln_yoy"), "C"), "A": ge(r.get("ln4_yoy"), "A"), "N": ge(x.get("cach52"), "N"),
           "S": ge(x.get("kl_x"), "S"), "L": ge(x.get("rs"), "L")}
    chu = [k for k in CHU if dat[k]]
    return len(chu), "·".join(chu)


def thi_truong_m(nen):
    """Nến ngày VN-Index ({c: [...]}) → {"m", "vni", "ma50", "ma200"}: tăng = giá > MA50 > MA200 · giảm = giá < MA200 và
    MA50 < MA200 · còn lại giằng co."""
    c = [v for v in (nen or {}).get("c") or [] if v]
    if len(c) < 200:
        return {"m": None}
    m50, m200 = sum(c[-50:]) / 50, sum(c[-200:]) / 200
    m = "tăng" if c[-1] > m50 > m200 else "giảm" if c[-1] < m200 and m50 < m200 else "giằng co"
    return {"m": m, "vni": round(c[-1], 2), "ma50": round(m50, 2), "ma200": round(m200, 2)}


def tinh(ds, gia, nen_vni=None):
    """ds: list dòng ds.json (sửa tại chỗ) · gia: {mã: json giá} → meta canslim."""
    x = {m: chi_tieu_gia(g) for m, g in gia.items()}
    rs = hang_rs({m: v["ibd"] for m, v in x.items()})
    for r in ds:
        xi = dict(x.get(r.get("ma"), {}))
        xi["rs"] = rs.get(r.get("ma"))
        r["cs"], r["cs_d"] = danh_gia(r, xi)
        r["rs"], r["cach52"], r["kl_x"] = xi.get("rs"), xi.get("cach52"), xi.get("kl_x")
    gio_vn = datetime.now(timezone(timedelta(hours=7)))
    return {**thi_truong_m(nen_vni), "cap_nhat": f"{gio_vn:%Y-%m-%d %H:%M}",
            "nguong": {"C": "LNST quý ≥ +25%", "A": "LNST 4 quý ≥ +20%", "N": "cách đỉnh 52 tuần ≤ 15%",
                       "S": "KL TB20 ÷ TB120 ≥ 1,2", "L": "hạng RS ≥ 70",
                       "M": "VN-Index trên MA50 và MA50 trên MA200"}}


def main(argv=None):
    p = argparse.ArgumentParser(description="CANSLIM cho trang Tra cứu mã")
    p.add_argument("--ra", default=os.path.join("docs", "ma", "du_lieu"))
    a = p.parse_args(argv)
    f = os.path.join(a.ra, "ds.json")
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    gia = {}
    tm = os.path.join(a.ra, "gia")
    for r in d.get("ds") or []:
        try:
            with open(os.path.join(tm, f"{r['ma']}.json"), encoding="utf-8") as fh:
                gia[r["ma"]] = json.load(fh)
        except (OSError, ValueError, KeyError):
            pass
    try:
        from . import nguon
        nen = nguon.nen("VNINDEX", "ONE_DAY", 260)
    except Exception as e:                                          # noqa: BLE001 – mạng lỗi: M để trống
        print(f"VN-Index lỗi ({type(e).__name__}) – bỏ M")
        nen = None
    d["canslim"] = tinh(d.get("ds") or [], gia, nen)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
    dem = sum((r.get("cs") or 0) >= 4 for r in d.get("ds") or [])
    print(f"CANSLIM: {len(gia)}/{len(d.get('ds') or [])} mã có giá · {dem} mã ≥ 4/5 · M {d['canslim'].get('m')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
