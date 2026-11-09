# -*- coding: utf-8 -*-
"""
VN-INDEX NGÀY TỪ 2010 CHO TRANG BIỂU ĐỒ (đường RS so VN-Index) – chạy trong workflow "Du lieu tra cuu".
Nguồn DNSE chart-api (index, 1D). File gọn như gia_dai: vni.json {"d0": ngày đầu, "g": [0, cách ngày phiên trước…],
"c": [đóng cửa], "cap_nhat"}. Trang nối thêm các phiên mới nhất từ Bảng thị trường (vni_ngay) khi đang giao dịch.
+ CÁC CHỈ SỐ (VN-Index, VN30, VNDiamond, HNX…) đủ nến mở / cao / thấp / đóng / KL → chi_so/<MÃ>.json (như gia_dai) +
chi_so/ds.json {mã: tên} – trang Biểu đồ mở như một mã (gõ VN30…) và so sánh được. DNSE không có (VNDiamond, VNMidcap…,
lượt 09/11/2026) → thử nến ngày Vietcap (thi_truong/nguon.nen); cả hai không có → bỏ, giữ file cũ.
  python -m thi_truong.vni_web --ra docs/ma/du_lieu
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/index"
TU = "2010-01-01"
VN = timezone(timedelta(hours=7))


CHI_SO = {"VNINDEX": "VN-Index", "VN30": "VN30", "VN100": "VN100", "VNMID": "VNMidcap", "VNSML": "VNSmallcap",
          "VNALL": "VNAllshare", "VNDIAMOND": "VNDiamond", "VNFINLEAD": "VNFin Lead", "VNFINSELECT": "VNFin Select",
          "VNX50": "VNX50", "HNX": "HNX-Index", "HNX30": "HNX30", "UPCOM": "UPCoM-Index"}
TEN_DNSE = {"HNX": ("HNX", "HNXINDEX", "HNXIndex"), "UPCOM": ("UPCOM", "UPCOMINDEX", "HNXUpcomIndex"),
            "VNALL": ("VNALL", "VNALLSHARE")}                 # mã chỉ số phía DNSE chưa chắc → thử lần lượt
TEN_VC = {"VNMID": ("VNMID", "VNMIDCAP"), "VNSML": ("VNSML", "VNSMALLCAP"), "VNALL": ("VNALL", "VNALLSHARE")}   # Vietcap


def tai_nen(ma="VNINDEX", tu=TU, so_lan=3):
    """→ [(ngày ISO, mở, cao, thấp, đóng, KL)] tăng dần | None."""
    a = int(datetime.fromisoformat(tu).replace(tzinfo=timezone.utc).timestamp())
    for k in range(so_lan):
        try:
            r = requests.get(URL, params={"symbol": ma, "resolution": "1D", "from": a, "to": int(time.time()) + 86400}, timeout=30)
            if r.status_code == 200:
                j = r.json()
                c_ = j.get("c") or []
                cot = [j.get(k_) or c_ for k_ in ("o", "h", "l")] + [c_, j.get("v") or [0] * len(c_)]
                ds = {}
                for t, o, h, lo, c, v in zip(j.get("t") or [], *cot):
                    if c:
                        ds[(datetime.fromtimestamp(int(t), timezone.utc) + timedelta(hours=7)).date().isoformat()] = (
                            round(float(o or c), 2), round(float(h or c), 2), round(float(lo or c), 2), round(float(c), 2), int(v or 0))
                return [(d, *x) for d, x in sorted(ds.items())] or None
        except (requests.RequestException, ValueError, TypeError):
            pass
        time.sleep(1 + k)
    return None


def tai_vc(ma, so_lan=1, so_nen=5000):                  # nguon.goi đã tự thử lại 3 lần
    """Nến ngày chỉ số từ Vietcap gap-chart (dự phòng DNSE) → như tai_nen | None."""
    from . import nguon
    for k in range(so_lan):
        try:
            j = nguon.nen(ma, "ONE_DAY", so_nen)
            t_ = (j or {}).get("t") or []
            if t_:
                c_ = j.get("c") or []
                cot = [j.get(k_) or c_ for k_ in ("o", "h", "l")] + [c_, j.get("v") or [0] * len(c_)]
                ds = {}
                for t, o, h, lo, c, v in zip(t_, *cot):
                    if c:
                        ds[(datetime.fromtimestamp(int(t), timezone.utc) + timedelta(hours=7)).date().isoformat()] = (
                            round(float(o or c), 2), round(float(h or c), 2), round(float(lo or c), 2), round(float(c), 2), int(v or 0))
                return [(d, *x) for d, x in sorted(ds.items())] or None
        except (ValueError, TypeError, KeyError):
            pass
        time.sleep(1 + k)
    return None


def gon_nen(dong):
    """[(ngày, o, h, l, c, v)] → {"d0", "g", "o", "h", "l", "c", "v"} (như gia_dai)."""
    if not dong:
        return None
    return {**gon([(d, c) for d, _, _, _, c, _ in dong]), "o": [x[1] for x in dong], "h": [x[2] for x in dong],
            "l": [x[3] for x in dong], "v": [x[5] for x in dong]}


def ghi_chi_so(ra, tai_=tai_nen, tai_vc_=tai_vc):
    """Mỗi chỉ số trong CHI_SO → ra/chi_so/<MÃ>.json; ra/chi_so/ds.json = các mã đang có file. → (có, thiếu)."""
    thu_muc = os.path.join(ra, "chi_so")
    os.makedirs(thu_muc, exist_ok=True)
    co, thieu = [], []
    for ma in CHI_SO:
        d = next((x for x in (tai_(t, so_lan=2) for t in TEN_DNSE.get(ma, (ma,))) if x and len(x) >= 250), None) \
            or next((x for x in (tai_vc_(t) for t in TEN_VC.get(ma, (ma,))) if x and len(x) >= 250), None)
        if d:
            with open(os.path.join(thu_muc, f"{ma}.json"), "w", encoding="utf-8") as f:
                json.dump(gon_nen(d), f, separators=(",", ":"))
            co.append(ma)
        else:
            thieu.append(ma)
    ds = {m: CHI_SO[m] for m in CHI_SO if os.path.exists(os.path.join(thu_muc, f"{m}.json"))}   # thiếu lần này: giữ file cũ
    with open(os.path.join(thu_muc, "ds.json"), "w", encoding="utf-8") as f:
        json.dump({"ds": ds, "cap_nhat": datetime.now(VN).strftime("%H:%M %d/%m/%Y")}, f, ensure_ascii=False, separators=(",", ":"))
    return co, thieu


def tai(ma="VNINDEX", tu=TU, so_lan=3):
    """→ [(ngày ISO, đóng cửa)] tăng dần | None."""
    n = tai_nen(ma, tu, so_lan)
    return [(d, c) for d, _, _, _, c, _ in n] if n else None


def gon(dong):
    """[(ngày, giá)] → {"d0", "g", "c"} (như gia_dai)."""
    if not dong:
        return None
    ng = [datetime.fromisoformat(d) for d, _ in dong]
    return {"d0": dong[0][0], "g": [0] + [(b - a).days for a, b in zip(ng, ng[1:])], "c": [c for _, c in dong]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="VN-Index ngày từ 2010 cho đường RS (trang Biểu đồ)")
    ap.add_argument("--ra", default="docs/ma/du_lieu")
    a = ap.parse_args(argv)
    d = gon(tai())
    if not d or len(d["c"]) < 250:
        print("VN-Index: không tải được – giữ file cũ")
        return 0
    os.makedirs(a.ra, exist_ok=True)
    with open(os.path.join(a.ra, "vni.json"), "w", encoding="utf-8") as f:
        json.dump({**d, "cap_nhat": datetime.now(VN).strftime("%H:%M %d/%m/%Y")}, f, separators=(",", ":"))
    print(f"VN-Index: {len(d['c'])} phiên từ {d['d0']}")
    co, thieu = ghi_chi_so(a.ra)
    print(f"Chỉ số: có {', '.join(co) or '–'} · DNSE không có {', '.join(thieu) or '–'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
