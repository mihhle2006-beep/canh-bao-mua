# -*- coding: utf-8 -*-
"""
MÃ TỪ BỘ LỌC (repo Bo_Loc) – theo dõi có thời hạn.

  Bo_Loc chạy cuối phiên thứ 2 & thứ 5 (chiến lược rieng + xu_huong) → ma_mua_bo_loc.json (mã có Hành động MUA).
  Tổng kết 15:20 ở đây:
    1) đọc file đó (lần quét MỚI mới xử lý) → thêm mã vào danh sách theo dõi, hạn BO_LOC_SO_NGAY ngày
       (mã được lọc lại khi đang theo dõi → gia hạn từ ngày quét mới);
    2) quét chiến lược cùng các mã cố định → mã vào nhóm mua 🟢 / ✅ / 🟡 = ĐẠT yêu cầu mua → giữ lại;
    3) hết hạn mà chưa đạt → tự xoá.
  Trạng thái lưu ở FILE_MA_BO_LOC (công khai – chỉ có mã & ngày).
"""
import json
import os
import urllib.request

import pandas as pd

from . import cau_hinh as C


def _ngay(x):
    return pd.Timestamp(x).normalize()


def doc(path=None):
    try:
        with open(path or C.FILE_MA_BO_LOC, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi(tt, path=None):
    with open(path or C.FILE_MA_BO_LOC, "w", encoding="utf-8") as f:
        json.dump(tt, f, ensure_ascii=False, indent=1)


def lay_nguon():
    """
    File kết quả quét của Bo_Loc → dict | None.
    Thứ tự: biến BO_LOC_FILE (đường dẫn trên máy) → GitHub API repo BO_LOC_REPO (token BO_LOC_TOKEN nếu repo riêng tư).
    """
    tep = os.environ.get("BO_LOC_FILE") or C.BO_LOC_FILE
    if tep:
        try:
            with open(tep, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"⚠ Không đọc được {tep}: {e}")
            return None
    repo = os.environ.get("BO_LOC_REPO") or C.BO_LOC_REPO
    duong_dan = os.environ.get("BO_LOC_PATH") or C.BO_LOC_PATH
    if not repo:
        return None
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/contents/{duong_dan}",
                                 headers={"Accept": "application/vnd.github.raw+json", "User-Agent": "canh-bao-mua"})
    token = os.environ.get("BO_LOC_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:                                     # chưa có file / repo riêng tư thiếu token
        print(f"⚠ Không lấy được {duong_dan} từ {repo}: {type(e).__name__}: {str(e)[:120]}")
        return None


def nhan_nguon(tt, nguon, co_dinh=()):
    """Thêm mã từ lần quét MỚI của Bo_Loc. → danh sách mã vừa thêm (mới hoàn toàn)."""
    if not nguon or not nguon.get("ngay_quet"):
        return []
    ma_tt = tt.setdefault("ma", {})
    if nguon["ngay_quet"] <= (tt.get("ngay_quet_da_nhan") or ""):
        return []
    tt["ngay_quet_da_nhan"] = nguon["ngay_quet"]
    co_dinh = {m.upper() for m in co_dinh}
    moi = []
    ngay_quet = _ngay(nguon["ngay_quet"])
    het_han = f"{ngay_quet + pd.Timedelta(days=C.BO_LOC_SO_NGAY):%Y-%m-%d}"
    for ma, cl in (nguon.get("ma") or {}).items():
        ma = ma.upper()
        if ma in co_dinh:                                       # đã có trong danh sách cố định → không cần hạn
            continue
        cu = ma_tt.get(ma)
        if cu is None:
            ma_tt[ma] = {"ngay_them": f"{ngay_quet:%Y-%m-%d}", "het_han": het_han, "chien_luoc": list(cl),
                         "dat_mua": None}
            moi.append(ma)
        elif not cu.get("dat_mua"):                             # lọc lại khi đang chờ → gia hạn
            cu["het_han"] = max(cu.get("het_han") or "", het_han)
            cu["chien_luoc"] = sorted(set(cu.get("chien_luoc") or []) | set(cl))
    return moi


def danh_sach(tt):
    return list((tt.get("ma") or {}).keys())


def danh_dau_dat(tt, ma_mua, bay_gio):
    """Mã nằm trong nhóm mua của tin tổng kết → ĐẠT (giữ lại, không xoá theo hạn). → mã vừa đạt."""
    vua = []
    for ma in ma_mua:
        v = (tt.get("ma") or {}).get(str(ma).upper())
        if v is not None and not v.get("dat_mua"):
            v["dat_mua"] = f"{pd.Timestamp(bay_gio):%Y-%m-%d}"
            vua.append(str(ma).upper())
    return vua


def xoa_het_han(tt, bay_gio):
    """Hết hạn mà chưa đạt điểm mua → xoá. → mã đã xoá."""
    hom_nay = _ngay(bay_gio)
    xoa = [ma for ma, v in (tt.get("ma") or {}).items()
           if not v.get("dat_mua") and v.get("het_han") and hom_nay > _ngay(v["het_han"])]
    for ma in xoa:
        del tt["ma"][ma]
    return xoa


def dong_tin(moi, dat, xoa, tt):
    """1–3 dòng tóm tắt cho tin tổng kết (rỗng nếu không có gì đổi)."""
    if not (moi or dat or xoa):
        return ""
    dong = [f"🔎 Mã từ bộ lọc ({len(tt.get('ma') or {})} đang theo dõi, hạn {C.BO_LOC_SO_NGAY} ngày):"]
    if moi:
        dong.append(f"  ➕ thêm: {', '.join(moi)}")
    if dat:
        dong.append(f"  ✅ đạt điểm mua: {', '.join(dat)}")
    if xoa:
        dong.append(f"  🗑 xoá (quá {C.BO_LOC_SO_NGAY} ngày chưa đạt): {', '.join(xoa)}")
    return "\n".join(dong)
