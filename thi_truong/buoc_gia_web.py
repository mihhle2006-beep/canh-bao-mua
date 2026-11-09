# -*- coding: utf-8 -*-
"""
KHỚP THEO BƯỚC GIÁ TRONG PHIÊN cho trang Biểu đồ (Tự vẽ → "Khớp theo bước giá hôm nay") – chạy trong phiên ở workflow
Bang thi truong: SO_MA mã GTGD TB20 cao nhất + mã bot / bộ lọc. KHÔNG nhận mã đang giữ (trang công khai: danh sách file sẽ
lộ danh mục) – quỹ chỉ mua top 100 GTGD nên phần lớn mã giữ đã nằm trong rổ.
Nguồn Vietcap AccumulatedPriceStepVol (thi_truong/nguon.buoc_gia): mỗi mức giá → KL khớp, KL mua chủ động, KL bán chủ động.
  buoc_gia/<MÃ>.json {"phien", "cap_nhat", "b": [[giá nghìn đồng, KL, KL mua chủ động, KL bán chủ động], …] (giá tăng dần)}
  buoc_gia/ds.json {"phien", "cap_nhat", "ma": [...]}
  python -m thi_truong.buoc_gia_web --ra docs/ma/du_lieu [--them_file …] [--tin_hieu …] [--bo_loc …]
"""
import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import phut_web

VN = timezone(timedelta(hours=7))
SO_MA = 120


def gon(ds):
    """[{priceStep, accumulatedVolume, accumulatedBuyVolume, accumulatedSellVolume}] → [[giá nghìn đ, KL, mua, bán]] tăng dần."""
    out = []
    for x in ds or []:
        g = x.get("priceStep")
        if not g:
            continue
        g = float(g) / 1000 if float(g) > 1000 else float(g)
        out.append([round(g, 2), int(x.get("accumulatedVolume") or 0), int(x.get("accumulatedBuyVolume") or 0),
                    int(x.get("accumulatedSellVolume") or 0)])
    return sorted(out)


def tai(ma):
    from . import nguon
    try:
        return gon(nguon.buoc_gia(ma))
    except Exception:                                   # noqa: BLE001 – 1 mã lỗi không làm hỏng lượt
        return None


def main(argv=None, tai_=tai):
    ap = argparse.ArgumentParser(description="Khớp theo bước giá trong phiên cho trang Biểu đồ")
    ap.add_argument("--ra", default="docs/ma/du_lieu")
    ap.add_argument("--so_ma", type=int, default=SO_MA)
    ap.add_argument("--them_file", default=None)
    ap.add_argument("--tin_hieu", default=None)
    ap.add_argument("--bo_loc", default=None)
    ap.add_argument("--luong", type=int, default=8)
    a = ap.parse_args(argv)
    ds = phut_web.ma_thanh_khoan(a.ra, a.so_ma, phut_web.ma_them("", a.them_file, a.tin_hieu, a.bo_loc))
    with ThreadPoolExecutor(a.luong) as ex:
        kq = list(ex.map(tai_, ds))
    bay_gio = datetime.now(VN)
    tm = os.path.join(a.ra, "buoc_gia")
    os.makedirs(tm, exist_ok=True)
    co = []
    for ma, b in zip(ds, kq):
        if b:
            with open(os.path.join(tm, f"{ma}.json"), "w", encoding="utf-8") as f:
                json.dump({"phien": bay_gio.date().isoformat(), "cap_nhat": f"{bay_gio:%H:%M}", "b": b}, f, separators=(",", ":"))
            co.append(ma)
    with open(os.path.join(tm, "ds.json"), "w", encoding="utf-8") as f:
        json.dump({"phien": bay_gio.date().isoformat(), "cap_nhat": f"{bay_gio:%H:%M}", "ma": co}, f)
    print(f"Bước giá: {len(co)}/{len(ds)} mã")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
