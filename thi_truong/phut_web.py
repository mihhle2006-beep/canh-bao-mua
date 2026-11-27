# -*- coding: utf-8 -*-
"""
NẾN 1' VÀ 5' CHO TRANG BIỂU ĐỒ (docs/ma, khung 1 phút / 5 phút / 15 phút / 1 giờ) – chạy SAU tra_cuu_dn (cần gia/<MÃ>.json để
chọn mã thanh khoản). Nguồn DNSE chart-api (giữ ~3 tháng nến phút); file cũ trong cache được nối thêm phần mới nên lịch sử 5'
dài dần (giữ tối đa GIU_NGAY), 1' giữ ~3 tháng.
  • Mã: MỌI mã có gia/<MÃ>.json (SO_MA = 0; > 0: chỉ SO_MA mã GTGD TB 20 phiên cao nhất) + mã thêm thi_truong/ma_them.txt
    + mã trong --them.
  • File phut/<1|5>/<MÃ>.json gọn: {"t0": giây UTC nến đầu, "dt": [phút cách nến trước], "c": [giá ×100, chênh nến trước],
    "o" / "h" / "l": [giá đóng ×100 − giá ×100], "v": [KL]} ; phut/ds.json {"cap_nhat", "1": [mã], "5": [mã]}.
  python -m thi_truong.phut_web --ra docs/ma/du_lieu [--so_ma 0] [--them HPG,FPT]
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
SO_MA = 0                                                  # 0 = mọi mã (từ 07/11/2026; trước là 400 mã thanh khoản cao nhất)
SO_MA_PHIEN = 60
VN = timezone(timedelta(hours=7))


def ma_thanh_khoan(thu_muc, so_ma=SO_MA, them=()):
    """Mã GTGD TB 20 phiên cao nhất từ gia/<MÃ>.json (so_ma ≤ 0: mọi mã) + them."""
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
    out = [m for _, m in (ds[:so_ma] if so_ma and so_ma > 0 else ds)]
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


def _ngay_vn(s):
    return datetime.fromtimestamp(s, VN).strftime("%Y-%m-%d")


def ngay_5p(thu_muc, ma):
    """Các ngày (giờ VN) mã có nến 5' – đếm ngày phiên của thị trường."""
    try:
        with open(os.path.join(thu_muc, "phut", "5", f"{ma}.json"), encoding="utf-8") as f:
            return {_ngay_vn(s) for s in giai_ma(json.load(f))[0]}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def doc_bang(duong):
    """du_lieu.json Bảng thị trường CHỐT PHIÊN (dang_gd false) → (ngày phiên, {MÃ: {nn, gt, co_gd}}) | None."""
    try:
        with open(duong, encoding="utf-8") as f:
            j = json.load(f)
        if j.get("dang_gd") or not j.get("phien"):
            return None
        c = j["loc"]["cot"]
        return j["phien"], {r[c.index("ma")]: {k: r[c.index(k)] for k in ("nn", "gt", "co_gd") if k in c} for r in j["loc"]["dong"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def va_gia_ngay(thu_muc, ma, han, phien=(), bang=None):
    """gia/<MÃ>.json thiếu các phiên gần đây (tra_cuu_dn xoay vòng – mỗi mã vài ngày mới tới lượt → biểu đồ nhảy cóc từ phiên cuối
    tới nến hôm nay) → thêm nến NGÀY cho các ngày < han (phiên chưa đóng: trang tự thêm nến tạm):
      • có nến 5': mở = nến đầu, cao / thấp, đóng = nến cuối, KL cộng, GT ≈ Σ KL × giá;
      • phiên thị trường (phien) mà mã KHÔNG có nến 5' = không khớp lệnh → nến PHẲNG như Vietcap (mở = cao = thấp = đóng = giá
        phiên trước, KL 0, khối ngoại 0) – chỉ khi mã có khớp trong 10 phiên gần nhất (mã ngừng giao dịch: không vẽ thêm);
      • bang = (ngày, {MÃ: {nn, gt}}) Bảng thị trường chốt phiên → khối ngoại ròng + GTGD đúng của ngày đó.
    Mua / bán tách của khối ngoại, cung cầu, tự doanh để trống; lượt xoay vòng sau tải Vietcap đè lên (noi_gia: ngày mới đè
    ngày trùng). → số phiên đã thêm."""
    pg = os.path.join(thu_muc, "gia", f"{ma}.json")
    try:
        with open(pg, encoding="utf-8") as f:
            g = json.load(f)
        with open(os.path.join(thu_muc, "phut", "5", f"{ma}.json"), encoding="utf-8") as f:
            t, o, h, l_, c, v = giai_ma(json.load(f))
    except (OSError, ValueError, KeyError, TypeError):
        return 0
    if not g.get("d") or not g.get("c"):
        return 0
    ngay = {}
    for i, s in enumerate(t):
        ngay.setdefault(_ngay_vn(s), []).append(i)
    ps = sorted(d for d in phien if d < han)
    phang = set(ps) if set(ps[-10:]) & set(ngay) else set()
    them = sorted(d for d in set(ngay) | phang if g["d"][-1] < d < han)
    bd, bm = bang if bang else (None, {})
    sua = 0
    if bd in g["d"] and (bm.get(ma) or {}).get("nn") is not None and "nn" in g:   # nến vá trước đó chưa có khối ngoại
        k = g["d"].index(bd)
        if k < len(g["nn"]) and g["nn"][k] is None:
            g["nn"][k], sua = bm[ma]["nn"], 1
    n = len(g["d"])
    for d in them:
        ix = ngay.get(d)
        if ix:
            moi = {"o": o[ix[0]], "h": max(h[i] for i in ix), "l": min(l_[i] for i in ix), "c": c[ix[-1]], "c0": c[ix[-1]],
                   "v": sum(v[i] for i in ix), "gt": round(sum(v[i] * c[i] for i in ix) / 1e6, 2)}
            r = bm.get(ma) if d == bd else None
            if r and r.get("gt") is not None:
                moi["gt"] = r["gt"]
            if r and r.get("nn") is not None:
                moi["nn"] = r["nn"]
        else:
            c0 = g["c"][-1]
            moi = {"o": c0, "h": c0, "l": c0, "c": c0, "c0": (g.get("c0") or g["c"])[-1], "v": 0, "gt": 0.0,
                   "tt": 0.0, "nn_m": 0.0, "nn_b": 0.0, "nn": 0.0}
        moi["d"] = d
        for k, a in g.items():
            if isinstance(a, list) and len(a) == n:
                a.append(moi.get(k, a[-1] if k == "nn_pt" else None))     # % sở hữu NN: giữ mức phiên trước
        n += 1
    if them or sua:
        tam = pg + ".tam"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(g, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tam, pg)
    return len(them)


def ma_them(them="", them_file=None, tin_hieu=None, bo_loc=None):
    """Mã thêm: chuỗi "A,B" + file một dòng "A,B" (mã đang giữ) + du_lieu.json Bảng thị trường (tin_hieu.ma) + ma_mua_bo_loc.json."""
    from . import ma_them as _them
    ds = [m for m in them.split(",")] + _them()
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
    ap.add_argument("--bang", default=None, help="du_lieu.json Bảng thị trường chốt phiên – khối ngoại ròng / GTGD cho nến vá")
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
    if not a.trong_phien:                                  # lịch sử ngày còn thiếu phiên (mã chưa tới lượt xoay vòng) → vá từ nến 5'
        bay = datetime.now(VN)                             # từ 15:00 phiên hôm nay đã đóng (ATC 14:45) → gộp cả hôm nay
        han = (bay + timedelta(days=1 if bay.hour >= 15 else 0)).strftime("%Y-%m-%d")
        dem = {}
        for m in co["5"]:
            for d in ngay_5p(a.ra, m):
                dem[d] = dem.get(d, 0) + 1
        phien = {d for d, k in dem.items() if k >= 50}            # ngày ≥ 50 mã có nến = phiên giao dịch (bỏ ngày lễ)
        bang = doc_bang(a.bang) if a.bang else None
        so = [va_gia_ngay(a.ra, m, han, phien, bang) for m in co["5"]]
        print(f"Vá nến ngày từ nến 5': {sum(1 for x in so if x)} mã · {sum(so)} phiên"
              + (f" · khối ngoại / GTGD phiên {bang[0]} từ Bảng thị trường ({len(bang[1])} mã)" if bang else " · không có bảng chốt phiên"))
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
