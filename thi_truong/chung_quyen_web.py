# -*- coding: utf-8 -*-
"""
CHỨNG QUYỀN cho trang Biểu đồ (menu ⋯ → Lớp phân tích → "Chứng quyền (hoà vốn, đáo hạn)", như FireAnt) – chạy mỗi lượt
workflow Bang thi truong (dữ liệu thị trường công khai, ~400 mã CW, 1–2 lệnh gọi Vietcap).
Nguồn Vietcap: nhóm CW (price/symbols/getByGroup) + bảng giá (price/symbols/getList → listingInfo + matchPrice).
  cw.json {"phien", "cap_nhat", "ma": {MÃ CƠ SỞ: [[mã CW, tổ chức phát hành, giá thực hiện (nghìn đ), tỷ lệ N (N CW : 1 cp),
           ngày đáo hạn, ngày GD cuối, giá CW (đồng), giá hoà vốn (nghìn đ), KL khớp], …] (đáo hạn gần trước)}}
  Hoà vốn (CW mua – call, kiểu châu Âu, thanh toán tiền) = giá thực hiện + giá CW × N. CW đã đáo hạn bỏ.
  python -m thi_truong.chung_quyen_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))


def _so(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v else None                        # NaN → None


def _ngay(s):
    """'20270308' | '2027-03-08' → '2027-03-08' (sai → None)."""
    s = str(s or "").replace("-", "")[:8]
    try:
        return datetime.strptime(s, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def ty_le(s):
    """'1.7245:1' → 1.7245 (số CW đổi 1 cổ phiếu); '2' → 2.0; sai → None."""
    a = str(s or "").split(":")
    n, m = _so(a[0]), _so(a[1]) if len(a) > 1 else 1.0
    return n / m if n and m else None


def gon(ds, hom_nay):
    """Bảng giá Vietcap các mã CW → {mã cơ sở: [[cw, tổ chức, giá TH nghìn, N, đáo hạn, GD cuối, giá CW đồng, hoà vốn nghìn, KL]]}."""
    out = {}
    for x in ds or []:
        li, mp = x.get("listingInfo") or {}, x.get("matchPrice") or {}
        ma, cs = li.get("symbol"), str(li.get("underlyingSymbol") or "").upper()
        th, n, dh = _so(li.get("exercisePrice")), ty_le(li.get("exerciseRatio")), _ngay(li.get("maturityDate"))
        if not ma or not cs or not th or not n or not dh or dh < hom_nay:
            continue
        gia = _so(mp.get("matchPrice")) or _so(mp.get("referencePrice")) or _so(li.get("refPrice")) or 0.0
        th_k = th / 1000 if th > 1000 else th                                                 # đồng → nghìn đồng
        hv = (th + gia * n) / 1000 if th > 1000 else th + gia * n / 1000
        out.setdefault(cs, []).append([ma, li.get("issuerName") or "", round(th_k, 3), round(n, 4), dh,
                                       _ngay(li.get("lastTradingDate")), round(gia), round(hv, 2),
                                       int(_so(mp.get("accumulatedVolume")) or 0)])
    for v in out.values():
        v.sort(key=lambda z: (z[4], z[0]))
    return out


def tai():
    from . import nguon
    ds = nguon.nhom("CW")
    return nguon.bang_gia(ds) if ds else []


def main(argv=None, tai_=tai):
    ap = argparse.ArgumentParser(description="Chứng quyền (hoà vốn, đáo hạn) cho trang Biểu đồ")
    ap.add_argument("--ra", default="docs/ma/du_lieu")
    a = ap.parse_args(argv)
    bay_gio = datetime.now(VN)
    ma = gon(tai_(), bay_gio.date().isoformat())
    if not ma:
        print("Chứng quyền: không có dữ liệu – giữ file cũ")
        return 0
    os.makedirs(a.ra, exist_ok=True)
    with open(os.path.join(a.ra, "cw.json"), "w", encoding="utf-8") as f:
        json.dump({"phien": bay_gio.date().isoformat(), "cap_nhat": f"{bay_gio:%H:%M}", "ma": ma}, f, ensure_ascii=False,
                  separators=(",", ":"))
    print(f"Chứng quyền: {sum(map(len, ma.values()))} mã CW trên {len(ma)} mã cơ sở")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
