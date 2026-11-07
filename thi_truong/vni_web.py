# -*- coding: utf-8 -*-
"""
VN-INDEX NGÀY TỪ 2010 CHO TRANG BIỂU ĐỒ (đường RS so VN-Index) – chạy trong workflow "Du lieu tra cuu".
Nguồn DNSE chart-api (index, 1D). File gọn như gia_dai: vni.json {"d0": ngày đầu, "g": [0, cách ngày phiên trước…],
"c": [đóng cửa], "cap_nhat"}. Trang nối thêm các phiên mới nhất từ Bảng thị trường (vni_ngay) khi đang giao dịch.
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


def tai(ma="VNINDEX", tu=TU, so_lan=3):
    """→ [(ngày ISO, đóng cửa)] tăng dần | None."""
    a = int(datetime.fromisoformat(tu).replace(tzinfo=timezone.utc).timestamp())
    for k in range(so_lan):
        try:
            r = requests.get(URL, params={"symbol": ma, "resolution": "1D", "from": a, "to": int(time.time()) + 86400}, timeout=30)
            if r.status_code == 200:
                j = r.json()
                ds = {}
                for t, c in zip(j.get("t") or [], j.get("c") or []):
                    if c:
                        ds[(datetime.fromtimestamp(int(t), timezone.utc) + timedelta(hours=7)).date().isoformat()] = round(float(c), 2)
                return sorted(ds.items())
        except (requests.RequestException, ValueError, TypeError):
            pass
        time.sleep(1 + k)
    return None


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
