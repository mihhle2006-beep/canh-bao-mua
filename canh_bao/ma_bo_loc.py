# -*- coding: utf-8 -*-
"""
MÃ TỪ BỘ LỌC (repo Bo_Loc) – theo dõi có thời hạn.

  Bo_Loc chạy cuối MỖI PHIÊN (chiến lược rieng + xu_huong) → ma_mua_bo_loc.json (mã có Hành động MUA).
  Tổng kết 15:20 ở đây:
    1) đọc file đó (lần quét MỚI mới xử lý) → thêm mã vào danh sách theo dõi, hạn BO_LOC_SO_PHIEN phiên
       kế tiếp (lọc lại vẫn đạt → hạn tính lại từ lần quét đó);
    2) quét chiến lược cùng các mã cố định → mã vào nhóm mua 🟢 / ✅ / 🟡 = ĐẠT yêu cầu mua
       → hạn mới = ngày đạt + BO_LOC_SO_PHIEN phiên (mỗi lần đạt lại được thêm hạn);
    3) hết hạn → tự xoá – kể cả mã đang giữ: file này CÔNG KHAI nên không được để lộ danh mục; mã đang giữ vẫn được
       chăm sóc đủ ở phần danh mục RIÊNG TƯ (cảnh báo bán, dời cắt lỗ, mua thêm – vi_the.py, mục 💼).
       Bo_Loc lọc ra lại sau khi xoá → thêm lại, hạn mới.
  Trạng thái lưu ở FILE_MA_BO_LOC (công khai – chỉ có mã & ngày).
"""
import json
import os
import urllib.error
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
    url = f"https://api.github.com/repos/{repo}/contents/{duong_dan}"
    token = os.environ.get("BO_LOC_TOKEN")
    loi = []
    for tk in ([token] if token else []) + [None]:            # token lỗi → thử không token (repo công khai)
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.raw+json",
                                                   "User-Agent": "canh-bao-mua"})
        if tk:
            req.add_header("Authorization", f"Bearer {tk}")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                ly_do = json.loads(e.read().decode("utf-8")).get("message", "")
            except Exception:
                ly_do = ""
            loi.append(f"{'có token' if tk else 'không token'}: HTTP {e.code} {ly_do}".strip())
        except Exception as e:
            loi.append(f"{'có token' if tk else 'không token'}: {type(e).__name__}: {str(e)[:100]}")
    print(f"⚠ Không lấy được {duong_dan} từ {repo} – " + " | ".join(loi)
          + (" → kiểm tra BO_LOC_TOKEN: chọn repo Bo_Loc, quyền Contents: Read-only" if token else ""))
    return None


def nhan_nguon(tt, nguon, co_dinh=()):
    """Thêm mã từ lần quét MỚI của Bo_Loc. → danh sách mã vừa thêm (mới hoàn toàn)."""
    if not nguon or not nguon.get("ngay_quet"):
        return []
    ma_tt = tt.setdefault("ma", {})
    lan_quet = nguon.get("luc") or nguon["ngay_quet"]          # "YYYY-MM-DD HH:MM" – 1 ngày quét nhiều lần vẫn nhận
    if lan_quet <= (tt.get("ngay_quet_da_nhan") or ""):
        return []
    tt["ngay_quet_da_nhan"] = lan_quet
    co_dinh = {m.upper() for m in co_dinh}
    moi = []
    ngay_quet = _ngay(nguon["ngay_quet"])
    het_han = han_tu(ngay_quet)
    for ma, cl in (nguon.get("ma") or {}).items():
        ma = ma.upper()
        if ma in co_dinh:                                       # đã có trong danh sách cố định → không cần hạn
            continue
        cu = ma_tt.get(ma)
        if cu is None:
            ma_tt[ma] = {"ngay_them": f"{ngay_quet:%Y-%m-%d}", "het_han": het_han, "chien_luoc": list(cl),
                         "dat_mua": None}
            moi.append(ma)
        else:                                                   # lọc lại vẫn đạt → hạn tính lại từ lần quét này
            cu["chien_luoc"] = sorted(set(cu.get("chien_luoc") or []) | set(cl))
            cu["loc_gan_nhat"] = f"{ngay_quet:%Y-%m-%d}"
            cu["het_han"] = max(cu.get("het_han") or "", het_han)
    return moi


def danh_sach(tt):
    return list((tt.get("ma") or {}).keys())


def danh_dau_dat(tt, ma_mua, bay_gio):
    """Mã nằm trong nhóm mua của tin tổng kết → ĐẠT, hạn = BO_LOC_SO_PHIEN phiên từ hôm nay. → mã lần đầu đạt."""
    vua = []
    hom_nay = _ngay(bay_gio)
    het_han = han_tu(hom_nay)
    for ma in ma_mua:
        v = (tt.get("ma") or {}).get(str(ma).upper())
        if v is None:
            continue
        if not v.get("dat_mua"):
            v["dat_mua"] = f"{hom_nay:%Y-%m-%d}"
            vua.append(str(ma).upper())
        v["dat_gan_nhat"] = f"{hom_nay:%Y-%m-%d}"
        v["het_han"] = max(v.get("het_han") or "", het_han)
    return vua


_LICH = {}


def ngay_nghi(nam):
    """Ngày nghỉ lễ VN (thư viện `holidays` – tự tính Tết âm lịch, nghỉ bù… mọi năm) ∪ C.NGAY_NGHI_GIAO_DICH
    (ngày HOSE nghỉ thêm mà thư viện không có, vd 02/01/2026)."""
    if nam not in _LICH:
        ds = {str(x) for x in getattr(C, "NGAY_NGHI_GIAO_DICH", [])}
        try:
            import holidays
            ds |= {f"{d:%Y-%m-%d}" for d in holidays.country_holidays("VN", years=nam)}
        except Exception as e:                                  # thiếu thư viện → chỉ dùng danh sách cấu hình
            print(f"⚠ Không đọc được lịch lễ VN ({type(e).__name__}) – dùng NGAY_NGHI_GIAO_DICH")
        _LICH[nam] = sorted(d for d in ds if d.startswith(str(nam)))
    return _LICH[nam]


def _lich_phien(tu):
    nam = range(tu.year, tu.year + 2)
    return pd.offsets.CustomBusinessDay(holidays=[d for n in nam for d in ngay_nghi(n)])


def han_tu(ngay, phien_thuc=None, den=None):
    """Hạn = phiên giao dịch thứ BO_LOC_SO_PHIEN sau `ngay` (theo dõi phiên ngay+1 … ngay+N).
    phien_thuc: ngày có phiên THẬT (nến ngày VNINDEX) tới `den` → phiên đã qua đếm theo dữ liệu thật (lễ đột xuất,
    nghỉ bù khác dự kiến vẫn đúng); phần chưa tới dự kiến bằng lịch lễ (T2–T6 trừ ngày nghỉ)."""
    d, n = _ngay(ngay), C.BO_LOC_SO_PHIEN
    if phien_thuc is not None and den is not None:
        den = _ngay(den)
        that = sorted({_ngay(x) for x in phien_thuc if d < _ngay(x) <= den})[:n]
        if len(that) == n:
            return f"{that[-1]:%Y-%m-%d}"
        d, n = max(d, den), n - len(that)
    return f"{d + _lich_phien(d) * n:%Y-%m-%d}"


def xoa_het_han(tt, bay_gio, phien_thuc=None):
    """Hết hạn → xoá (không ngoại lệ cho mã đang giữ – file công khai không được để lộ danh mục). → mã đã xoá.
    Hạn tính lại mỗi lần từ mốc gần nhất (thêm / lọc lại / đạt) + BO_LOC_SO_PHIEN phiên – theo phiên thật nếu có
    phien_thuc; mã thêm theo hạn cũ (14 ngày) cũng được rút về hạn theo phiên."""
    hom_nay = _ngay(bay_gio)
    for v in (tt.get("ma") or {}).values():
        moc = [x for x in (v.get("ngay_them"), v.get("loc_gan_nhat"), v.get("dat_gan_nhat")) if x]
        if moc:
            v["het_han"] = han_tu(max(moc), phien_thuc, hom_nay)
    xoa = [ma for ma, v in (tt.get("ma") or {}).items() if v.get("het_han") and hom_nay > _ngay(v["het_han"])]
    for ma in xoa:
        del tt["ma"][ma]
    return xoa


def _nhan(ma, tt):
    """'HDB (xu_huong ½)' – mã thăm dò (nhóm MUA THĂM DÒ ½ của Bo_Loc) có chữ ½."""
    cl = ((tt.get("ma") or {}).get(ma) or {}).get("chien_luoc") or []
    return f"{ma} ({', '.join(cl)})" if cl else ma


def dong_tin(moi, dat, xoa, tt):
    """Tóm tắt cho tin tổng kết (rỗng nếu không có gì đổi). Mã thăm dò ghi '<chiến lược> ½'."""
    if not (moi or dat or xoa):
        return ""
    dong = [f"🔎 Mã từ bộ lọc ({len(tt.get('ma') or {})} đang theo dõi, hạn {C.BO_LOC_SO_PHIEN} phiên · ½ = mua thăm dò):"]
    if moi:
        dong.append(f"  ➕ thêm: {', '.join(_nhan(m, tt) for m in moi)}")
    if dat:
        dong.append(f"  ✅ đạt điểm mua (+{C.BO_LOC_SO_PHIEN} phiên): {', '.join(_nhan(m, tt) for m in dat)}")
    if xoa:
        dong.append(f"  🗑 xoá (hết hạn {C.BO_LOC_SO_PHIEN} phiên): {', '.join(xoa)}")
    return "\n".join(dong)
