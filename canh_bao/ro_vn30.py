# -*- coding: utf-8 -*-
"""
RỔ VN30 – lấy online lúc tổng kết (rổ đổi kỳ tháng 1 & 7), thử lần lượt nhiều nguồn; kết quả phải hợp lệ
(25–35 mã, mỗi mã 3 chữ cái) mới dùng, không thì dùng danh sách gõ sẵn C.MA_VN30.
"""
import json
import re
import urllib.request

from . import cau_hinh as C

NGUON = [
    ("VPS", "https://bgapidatafeed.vps.com.vn/getlistckindex/VN30"),
    ("SSI", "https://iboard-query.ssi.com.vn/v2/stock/group/VN30"),
    ("VNDirect", "https://api-finfo.vndirect.com.vn/v4/stocks?q=indexCode:VN30~type:STOCK&size=100"),
]
KHOA_MA = ("stockSymbol", "symbol", "code", "ss", "sym", "ticker")


def _tach_ma(j):
    """JSON bất kỳ (list mã / list dict / {"data": ...}) → list mã."""
    if isinstance(j, dict):
        for k in ("data", "items", "result", "stocks"):
            if k in j:
                return _tach_ma(j[k])
        return []
    out = []
    for x in j or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            out += [x[k] for k in KHOA_MA if isinstance(x.get(k), str)][:1]
    return out


def hop_le(ds):
    ds = list(dict.fromkeys(str(m).strip().upper() for m in ds))
    return ds if 25 <= len(ds) <= 35 and all(re.fullmatch(r"[A-Z]{3}", m) for m in ds) else None


def _lay(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def lay_vn30(lay=_lay):
    """→ (danh sách mã VN30, nguồn). Mọi nguồn lỗi / không hợp lệ → C.MA_VN30."""
    if getattr(C, "TU_LAY_VN30", True):
        for ten, url in NGUON:
            try:
                ds = hop_le(_tach_ma(lay(url)))
                if ds:
                    return sorted(ds), ten
            except Exception:
                continue
    return list(C.MA_VN30), "danh sách gõ sẵn (cau_hinh.MA_VN30)"
