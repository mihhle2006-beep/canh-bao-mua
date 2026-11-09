# -*- coding: utf-8 -*-
"""QUỸ ĐẦU TƯ (tab "Quỹ đầu tư" của Bảng thị trường – chủ quỹ 09/11/2026): quỹ mở cổ phiếu / cân bằng từ API công khai
Fmarket – tổng tài sản, % NAV từ đầu năm / 1 / 3 năm, top 10 mã đang nắm (số CP), tỷ trọng ngành / loại tài sản.

Fmarket chỉ cho danh mục THÁNG MỚI NHẤT (không có API lịch sử – đã dò 09/11/2026) → mỗi lần dựng lưu ảnh danh mục theo tháng
báo cáo (`ls`), giữ qua các lần dựng (cache chuẩn bị, mất cache thì lấy lại từ bản đang triển khai). Quỹ mua / bán ròng = chênh
số CP của cùng mã giữa tháng mới nhất và tháng cũ nhất trong 3 tháng trước, × giá báo cáo – CHỈ mã nằm trong top 10 cả hai kỳ
(mã vào / rời top 10 chỉ đếm, không đoán khối lượng)."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import requests

API = "https://api.fmarket.vn/res"
LOAI = {"STOCK": "Cổ phiếu", "BALANCED": "Cân bằng"}
THANG_SO = 3
VN = timezone(timedelta(hours=7))


def _goi(duong, body=None):
    u = f"{API}/{duong}"
    r = requests.post(u, json=body, timeout=40) if body is not None else requests.get(u, timeout=40)
    r.raise_for_status()
    return r.json().get("data")


def _thang(ms):
    return _thang_ngay(ms)[:7] if ms else None


def _mot(q):
    d = _goi(f"products/{q['id']}") or {}
    pf, bc, nc = d.get("productFund") or {}, d.get("fundReport") or {}, q.get("productNavChange") or {}
    ky = pf.get("updateAssetHoldingTime") or ""                      # "09/2026"
    ky = f"{ky[3:]}-{ky[:2]}" if len(ky) == 7 and ky[2] == "/" else _thang(bc.get("reportTime"))
    top = [[h.get("stockCode"), h.get("netAssetPercent"), h.get("volume"), round((h.get("assetValue") or 0) / 1e9, 2),
            h.get("industry") or ""]
           for h in d.get("productTopHoldingList") or [] if h.get("stockCode") and h.get("type", "STOCK") == "STOCK"]
    return {"m": q.get("shortName") or q.get("code"), "ten": q.get("name") or "",
            "cty": ((q.get("owner") or {}).get("shortName") or "").upper(),
            "loai": (q.get("dataFundAssetType") or {}).get("code"),
            "ts": round(bc["totalAssetValue"] / 1e9, 1) if bc.get("totalAssetValue") else None,
            "nav": q.get("nav"), "nav_ngay": _thang_ngay((d.get("extra") or {}).get("lastNAVDate")),
            "lai": {k: nc.get(f) for k, f in (("1t", "navTo1Months"), ("3t", "navTo3Months"), ("ytd", "navToLastYear"),
                                                ("1n", "navTo12Months"), ("3n", "navTo36Months"), ("5n", "navTo60Months"))},
            "ky": ky, "top": top,
            "nganh": [[x.get("industry"), x.get("assetPercent")] for x in d.get("productIndustriesHoldingList") or []],
            "tai_san": [[(x.get("assetType") or {}).get("name"), x.get("assetPercent")]
                        for x in d.get("productAssetHoldingList") or []]}


def _thang_ngay(ms):
    return f"{datetime.fromtimestamp(ms / 1000, VN):%Y-%m-%d}" if ms else None


def _truoc(ky, n):
    y, m = map(int, ky.split("-"))
    m -= n
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def mua_ban(ls, quy):
    """[[mã, giá trị ròng tỷ, số quỹ tăng, số quỹ giảm]] (giảm dần) · số quỹ có kỳ so sánh · {mã: [vào top 10, rời top 10]}."""
    gia = {}
    for q in quy:
        for ma, _, kl, gt, _ in q["top"]:
            if kl:
                gia.setdefault(ma, gt * 1e9 / kl)
    tong, tang, giam, vao_roi, so_quy, ky_cu = {}, {}, {}, {}, 0, set()
    for q in quy:
        moi = q.get("ky")
        cu = [k for k in sorted(ls) if moi and _truoc(moi, THANG_SO) <= k < moi and q["m"] in ls[k]]
        if not cu or q["m"] not in ls.get(moi, {}):
            continue
        a, b = ls[cu[0]][q["m"]], ls[moi][q["m"]]
        so_quy += 1
        ky_cu.add(cu[0])
        for ma in set(a) | set(b):
            if ma in a and ma in b:
                d = (b[ma] - a[ma]) * gia.get(ma, 0) / 1e9
                if abs(d) < 1e-9:
                    continue
                tong[ma] = tong.get(ma, 0) + d
                (tang if d > 0 else giam)[ma] = (tang if d > 0 else giam).get(ma, 0) + 1
            else:
                vao_roi.setdefault(ma, [0, 0])[0 if ma in b else 1] += 1
    ds = sorted(([m, round(v, 1), tang.get(m, 0), giam.get(m, 0)] for m, v in tong.items()), key=lambda x: -x[1])
    return ds, so_quy, (min(ky_cu) if ky_cu else None), vao_roi


def lay(cu=None, in_tien_do=print):
    """Dựng dữ liệu tab Quỹ; `cu` = bản lần trước (giữ lịch sử ảnh danh mục; Fmarket lỗi → trả lại bản cũ)."""
    cu = cu or {}
    try:
        ds = _goi("products/filter", {"types": ["NEW_FUND", "TRADING_FUND"], "issuerIds": [], "sortOrder": "DESC",
                                      "sortField": "navTo12Months", "page": 1, "pageSize": 300, "isIpo": False,
                                      "fundAssetTypes": [], "bondRemainPeriods": [], "searchField": "",
                                      "isBuyByReward": False, "thirdAppIds": []})["rows"]
        ds = [q for q in ds if (q.get("dataFundAssetType") or {}).get("code") in LOAI]
        from .nguon import song_song
        theo_id = {q["id"]: q for q in ds}
        ct = song_song(lambda i: _mot(theo_id[i]), theo_id, 6)        # quỹ lỗi bị bỏ
        quy = [ct[i] for i in theo_id if i in ct]
    except Exception as e:                                             # noqa: BLE001 – nguồn ngoài lỗi: giữ bản cũ
        in_tien_do(f"  quỹ: lỗi Fmarket ({str(e)[:80]}) – giữ bản cũ")
        return cu or None
    if len(quy) < max(5, len(cu.get("quy") or []) // 2):              # trả về thiếu bất thường → giữ bản cũ
        in_tien_do(f"  quỹ: chỉ lấy được {len(quy)} quỹ – giữ bản cũ")
        return cu or None
    ls = {k: dict(v) for k, v in (cu.get("ls") or {}).items()}
    for q in quy:
        if q["ky"] and q["top"]:
            ls.setdefault(q["ky"], {})[q["m"]] = {ma: kl for ma, _, kl, _, _ in q["top"] if kl}
    ls = {k: ls[k] for k in sorted(ls)[-24:]}                          # giữ 2 năm
    nam = {}
    for q in quy:
        for ma, _, _, gt, _ in q["top"]:
            n = nam.setdefault(ma, [0.0, 0])
            n[0] += gt
            n[1] += 1
    mb, so_quy, tu, vao_roi = mua_ban(ls, quy)
    quy.sort(key=lambda q: -(q["ts"] or 0))
    out = {"cap_nhat": f"{datetime.now(VN):%Y-%m-%d %H:%M}",
           "quy": quy, "loai": LOAI,
           "nam": sorted(([m, round(v[0], 1), v[1]] for m, v in nam.items()), key=lambda x: -x[1])[:20],
           "mb": mb, "mb_so_quy": so_quy, "mb_tu": tu, "vao_roi": vao_roi, "ls": ls}
    in_tien_do(f"  quỹ: {len(quy)} quỹ · {len(ls)} tháng danh mục · mua/bán ròng so được {so_quy} quỹ")
    return out


def tu_trang_trien_khai():
    """Bản 'quy' đang trên GitHub Pages (khi cache chuẩn bị mất) – để không mất lịch sử ảnh danh mục."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return None
    chu, ten = repo.split("/", 1)
    goc = f"https://{chu}.github.io/{ten}/thi_truong/"
    try:
        with urllib.request.urlopen(goc + "du_lieu.json", timeout=30) as r:
            q = json.load(r).get("quy") or {}
        with urllib.request.urlopen(goc + "quy_ls.json", timeout=30) as r:
            q["ls"] = json.load(r)
        return q
    except Exception:                                                  # noqa: BLE001 – chưa có bản nào: bắt đầu lại
        return None
