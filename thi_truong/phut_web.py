# -*- coding: utf-8 -*-
"""
NẾN 1' VÀ 5' CHO TRANG BIỂU ĐỒ (docs/ma, khung 1 phút / 5 phút / 15 phút / 1 giờ) – chạy SAU tra_cuu_dn (cần gia/<MÃ>.json để
chọn mã thanh khoản). Nguồn DNSE chart-api (giữ ~3 tháng nến phút); file cũ trong cache được nối thêm phần mới nên lịch sử 5'
dài dần (giữ tối đa GIU_NGAY), 1' giữ ~3 tháng.
  • Mã: SO_MA mã GTGD TB 20 phiên cao nhất (gia/<MÃ>.json "gt") + mã trong --them.
  • File phut/<1|5>/<MÃ>.json gọn: {"t0": giây UTC nến đầu, "dt": [phút cách nến trước], "c": [giá ×100, chênh nến trước],
    "o" / "h" / "l": [giá đóng ×100 − giá ×100], "v": [KL]} ; phut/ds.json {"cap_nhat", "1": [mã], "5": [mã]}.
  python -m thi_truong.phut_web --ra docs/ma/du_lieu [--so_ma 400] [--them HPG,FPT]
  • --trong_phien (Bảng thị trường, mỗi lần chạy trong giờ giao dịch): chỉ nối nến mới cho SO_MA_PHIEN mã thanh khoản cao nhất
    + mã đang giữ (--them_file) + mã bot đang khuyến nghị / bộ lọc (--tin_hieu), không xoá file mã khác, ds.json cộng dồn.
"""
import argparse
import glob
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
GIU_NGAY = {"1": 95, "5": 370}
SO_MA = 400
SO_MA_PHIEN = 60
VN = timezone(timedelta(hours=7))


def ma_thanh_khoan(thu_muc, so_ma=SO_MA, them=()):
    """Mã GTGD TB 20 phiên cao nhất từ gia/<MÃ>.json (+ them)."""
    ds = []
    for f in glob.glob(os.path.join(thu_muc, "gia", "*.json")):
        try:
            g = json.load(open(f, encoding="utf-8"))
            gt = [x for x in (g.get("gt") or [])[-20:] if x is not None]
            if gt and len(g.get("c") or []) >= 20:
                ds.append((sum(gt) / len(gt), os.path.basename(f)[:-5].upper()))
        except (OSError, ValueError):
            continue
    ds.sort(reverse=True)
    out = [m for _, m in ds[:so_ma]]
    return out + [m for m in them if m and m not in out]


def ma_hoa(t, o, h, l_, c, v):
    """Nến (giá nghìn đồng) → dict gọn (xem đầu file)."""
    if not t:
        return None
    C = [round(x * 100) for x in c]
    return {"t0": int(t[0]), "dt": [0] + [int((t[i] - t[i - 1]) // 60) for i in range(1, len(t))],
            "c": [C[0]] + [C[i] - C[i - 1] for i in range(1, len(C))],
            "o": [C[i] - round(x * 100) for i, x in enumerate(o)], "h": [C[i] - round(x * 100) for i, x in enumerate(h)],
            "l": [C[i] - round(x * 100) for i, x in enumerate(l_)], "v": [int(x or 0) for x in v]}


def giai_ma(d):
    """dict gọn → (t, o, h, l, c, v) giá nghìn đồng."""
    if not d or not d.get("dt"):
        return [], [], [], [], [], []
    t, c, s, cc = [], [], d["t0"], 0
    for i, (a, b) in enumerate(zip(d["dt"], d["c"])):
        s += a * 60 if i else 0
        cc += b
        t.append(s)
        c.append(cc)
    f = lambda k: [(c[i] - x) / 100 for i, x in enumerate(d[k])]                        # noqa: E731
    return t, f("o"), f("h"), f("l"), [x / 100 for x in c], list(d["v"])


def tai(ma, res, tu, den, so_lan=3):
    """DNSE chart-api → (t, o, h, l, c, v) | None."""
    for k in range(so_lan):
        try:
            r = requests.get(URL, params={"symbol": ma, "resolution": res, "from": int(tu), "to": int(den)}, timeout=25)
            if r.status_code == 200:
                j = r.json()
                return [j.get(x) or [] for x in ("t", "o", "h", "l", "c", "v")]
        except (requests.RequestException, ValueError):
            pass
        time.sleep(1 + k)
    return None


def cap_nhat(thu_muc, ma, res, bay_gio):
    """Nối nến mới vào file cũ, cắt theo GIU_NGAY → số nến (0 = không có)."""
    p = os.path.join(thu_muc, "phut", res, f"{ma}.json")
    try:
        cu = giai_ma(json.load(open(p, encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError):
        cu = [[], [], [], [], [], []]
    tu = (cu[0][-1] - 3 * 86400) if cu[0] else bay_gio - GIU_NGAY[res] * 86400
    moi = tai(ma, res, tu, bay_gio + 86400)
    if moi is None:
        return len(cu[0])
    gop = {t: tuple(a[i] for a in cu[1:]) for i, t in enumerate(cu[0])}
    for i, t in enumerate(moi[0]):
        if None not in (moi[1][i], moi[2][i], moi[3][i], moi[4][i]):
            gop[int(t)] = (moi[1][i], moi[2][i], moi[3][i], moi[4][i], moi[5][i] if i < len(moi[5]) else 0)
    tg = sorted(t for t in gop if t >= bay_gio - GIU_NGAY[res] * 86400)
    if not tg:
        return 0
    os.makedirs(os.path.dirname(p), exist_ok=True)
    d = ma_hoa(tg, *[[gop[t][k] for t in tg] for k in range(5)])
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, separators=(",", ":"))
    return len(tg)


def ma_them(them="", them_file=None, tin_hieu=None, bo_loc=None):
    """Mã thêm: chuỗi "A,B" + file một dòng "A,B" (mã đang giữ) + du_lieu.json Bảng thị trường (tin_hieu.ma) + ma_mua_bo_loc.json."""
    ds = [m for m in them.split(",")]
    try:
        ds += open(them_file, encoding="utf-8").read().replace("\n", ",").split(",") if them_file else []
    except OSError:
        pass
    try:
        ds += [r[0] for r in (json.load(open(tin_hieu, encoding="utf-8")).get("tin_hieu") or {}).get("ma") or []] if tin_hieu else []
    except (OSError, ValueError, TypeError, IndexError, AttributeError):
        pass
    try:
        ds += list((json.load(open(bo_loc, encoding="utf-8")).get("ma") or {})) if bo_loc else []
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    out = []
    for m in ds:
        m = str(m).strip().upper()
        if m.isalnum() and 3 <= len(m) <= 8 and m not in out:
            out.append(m)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Nến 1' / 5' cho trang Biểu đồ")
    ap.add_argument("--ra", default="docs/ma/du_lieu")
    ap.add_argument("--so_ma", type=int, default=None)
    ap.add_argument("--them", default="")
    ap.add_argument("--them_file", default=None)
    ap.add_argument("--tin_hieu", default=None)
    ap.add_argument("--bo_loc", default=None)
    ap.add_argument("--trong_phien", action="store_true")
    ap.add_argument("--luong", type=int, default=8)
    a = ap.parse_args(argv)
    so_ma = a.so_ma if a.so_ma is not None else SO_MA_PHIEN if a.trong_phien else SO_MA
    ds = ma_thanh_khoan(a.ra, so_ma, ma_them(a.them, a.them_file, a.tin_hieu, a.bo_loc))
    bay_gio = int(time.time())
    co = {"1": [], "5": []}
    for res in ("1", "5"):
        with ThreadPoolExecutor(a.luong) as ex:
            so = list(ex.map(lambda m: cap_nhat(a.ra, m, res, bay_gio), ds))
        co[res] = sorted(m for m, n in zip(ds, so) if n)
        print(f"Nến {res}': {len(co[res])}/{len(ds)} mã")
    if a.trong_phien:                                      # trong phiên: giữ file / danh sách mã khác (dựng hằng ngày)
        try:
            cu = json.load(open(os.path.join(a.ra, "phut", "ds.json"), encoding="utf-8"))
        except (OSError, ValueError):
            cu = {}
        co = {r: sorted(set(co[r]) | set(cu.get(r) or [])) for r in ("1", "5")}
    for res in ("1", "5") if not a.trong_phien else ():    # bỏ file mã đã rời danh sách
        for f in glob.glob(os.path.join(a.ra, "phut", res, "*.json")):
            if os.path.basename(f)[:-5] not in co[res]:
                os.remove(f)
    with open(os.path.join(a.ra, "phut", "ds.json"), "w", encoding="utf-8") as f:
        json.dump({"cap_nhat": datetime.now(VN).strftime("%H:%M %d/%m/%Y"), **co}, f, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
