# -*- coding: utf-8 -*-
"""
CẢNH BÁO MUA TRONG PHIÊN (mỗi 15 phút) – ĐỒNG BỘ với chiến lược thị trường.

  Chỉ quét các mã trong nhóm 🟢 / ✅ / 🟡 của tin tổng kết gần nhất (trang_thai_chien_luoc.json → ds_mua), đúng phiên
  hiệu lực, đúng vùng mua & cắt lỗ của tin đó. Tiêu chí 15' = ptcp/diem_vao_15p.py (cùng hàm với backtest):
    [Ngày – chiến lược] nhóm mua + lý do (đã đạt từ tối qua)
    [Vùng]  giá trong vùng mua · mở cửa ≤ đến · chưa rơi < từ
    [15']   MACD 15' cắt lên Signal (≤ 3 nến) HOẶC phá đỉnh 20 nến kèm KL ≥ 1,5× · giá ≥ VWAP · RSI 15' ≤ 75
    [Giờ]   MACD giờ > Signal (chỉ khi cách vào là 15P+GIO)
  Cách vào (ATO / 15P / 15P+ATC / LO …) lấy theo backtest (tong_ket_cl.cach_vao).
Tin: 🟢 MUA NGAY (đủ tiêu chí) · ⏰ MUA ATC (hết phiên chưa có điểm vào, giá còn trong vùng) · 🚫 BỎ (vô hiệu).
"""
import json

import numpy as np
import pandas as pd

from . import cau_hinh as C

TEN_NHOM = {"MUA_MOI": "MUA MỚI", "VAO_NHU_MOI": "VÀO NHƯ LỆNH MỚI", "VAO_NUA": "VÀO ½ KHỐI LƯỢNG"}


def _f(x, le=2):
    return "–" if x is None or x != x else f"{x:,.{le}f}"


def doc_ds_mua(bay_gio, path=None):
    """Danh sách mua có hiệu lực ĐÚNG phiên của bay_gio (list dict) – phiên cũ lấy từ lich_su_ds_mua (chạy lại)."""
    try:
        with open(path or C.FILE_TRANG_THAI_CL, encoding="utf-8") as f:
            tt = json.load(f)
    except (OSError, ValueError):
        return []
    ngay = f"{pd.Timestamp(bay_gio):%Y-%m-%d}"
    ds = tt.get("ds_mua") or {}
    if ds.get("hieu_luc") != ngay:
        ds = (tt.get("lich_su_ds_mua") or {}).get(ngay) or {}
    return ds.get("ma") or []


NGUONG_THANG_GIA = 0.03                         # đóng cửa phiên trước lệch giá của tin > 3% → nguồn đã điều chỉnh quyền
_MUC_GIA = ("gia", "tu", "den", "cl", "R", "mt1", "mt3", "atr")


def _he_so_lich(ma, gia, bay_gio):
    """Lịch quyền (ptcp.su_kien_quyen): GDKHQ đúng phiên hôm nay → hệ số giá tham chiếu, ngược lại None."""
    if not ma or not getattr(C, "BAO_SU_KIEN_QUYEN", False):
        return None
    try:
        from ptcp.su_kien_quyen import gop_theo_ngay, he_so_gia, lay_su_kien
        x = gop_theo_ngay(lay_su_kien(ma)).get(pd.Timestamp(bay_gio).normalize())
    except Exception:                                            # noqa: BLE001 – không có lịch → giữ nguyên vùng
        return None
    if not x:
        return None
    f = he_so_gia(x, float(gia))
    return f if abs(f - 1) > 1e-6 else None


def quy_thang_gia(z, dp, bay_gio):
    """
    Nguồn giá điều chỉnh quyền (chia / tách cổ phiếu) SAU tin tổng kết → vùng / cắt lỗ tính trên giá cũ lệch thang
    nến 15'. Đóng cửa phiên trước trong dp lệch 'gia' (đóng cửa lúc tổng kết) > 3% → nhân mọi mức giá cùng hệ số.
    VD HDB 08/10/2026: tin ghi giá 28,00 vùng 27,45–28,70; tối đó VNDirect chia cả chuỗi 1,3 → 21,54.
    """
    g = z.get("gia")
    truoc = dp[dp.index.normalize() < pd.Timestamp(bay_gio).normalize()] if dp is not None else None
    if not g or truoc is None or not len(truoc):
        return z
    f = float(truoc.close.iloc[-1]) / float(g)
    if abs(f - 1) <= NGUONG_THANG_GIA or not 0.2 < f < 5:
        f = _he_so_lich(z.get("ma"), g, bay_gio)               # chuỗi giá thô: GDKHQ hôm nay theo lịch quyền
        if f is None:
            return z
    moi = {k: z[k] * f for k in _MUC_GIA if isinstance(z.get(k), (int, float)) and z[k] == z[k]}
    return {**z, **moi, "he_so_quyen": f}


def danh_gia(z, dp, bay_gio, bien_the):
    """z: 1 dòng ds_mua; dp: nến 15' (nhiều phiên, đã bỏ nến chưa đóng). → dict kết quả phiên hôm nay."""
    from ptcp.diem_vao_15p import chi_bao_15p, danh_gia_phien, macd_gio, tieu_chi_nen
    t = pd.Timestamp(bay_gio)
    z = quy_thang_gia(z, dp, t)
    kq = {**z, "ly_do_ngay": z.get("ly_do", ""), "trang_thai": "CHỜ", "ly_do": "chưa có dữ liệu 15' hôm nay", "gia_nay": np.nan, "tieu_chi": [],
          "gia_mua": np.nan, "thoi_diem": None}
    if dp is None or not len(dp):
        return kq
    d = chi_bao_15p(dp)
    hom_nay = d[d.index.normalize() == t.normalize()]
    if not len(hom_nay):
        return kq
    g = macd_gio(dp)[hom_nay.index]
    het = t >= t.normalize() + pd.Timedelta(C.GIO_ATC + ":00")
    if vao_tre_atc(z):                      # Quỹ Bứt Phá: vào trễ chỉ đặt lệnh ATC (huỷ nếu chạm cắt lỗ trong phiên)
        bien_the = "ATC"
    r = danh_gia_phien(hom_nay, z["tu"], z["den"], bien_the, g, het_phien=het,
                       **({"cl": z.get("cl")} if bien_the == "ATC" else {}))
    L = hom_nay.iloc[-1]
    tc = r["tieu_chi"] or tieu_chi_nen(L, z["tu"], z["den"], bool(g.iloc[-1]) if "GIO" in bien_the else None)
    kq.update({"trang_thai": r["trang_thai"], "ly_do": r["ly_do"], "gia_nay": float(L.close), "tieu_chi": tc,
               "gia_mua": r["gia"], "thoi_diem": r["thoi_diem"], "atc": "ATC" in r["ly_do"]})
    gm, gn = kq["gia_mua"], kq["gia_nay"]
    if kq["trang_thai"] == "MUA" and not kq["atc"] and gm == gm and z["tu"] - 1e-9 <= gn < gm - 1e-9:
        # lúc báo, giá đã DƯỚI giá LO nhưng vẫn trong vùng → mua theo giá hiện tại (lệnh LO cao hơn vẫn chỉ khớp ở giá
        # chào bán thấp nhất); cắt lỗ % / mục tiêu / khối lượng tính theo giá này, không theo giá LO
        kq.update({"gia_mua": gn, "ly_do": f"giá {gn:,.2f} dưới LO {gm:,.2f}, còn trong vùng → mua giá hiện tại "
                                           f"(đặt LO {gn:,.2f}, không cần đặt cao hơn)"})
    if kq["trang_thai"] == "MUA" and kq["atc"] and not la_sao(z) and bien_the != "ATC":   # ATC chỉ cho mã ★ (trừ vào trễ)
        kq.update({"trang_thai": "BỎ", "ly_do": "không khớp LO, không phải mã ★ → không mua ATC", "gia_mua": np.nan,
                   "atc": False})
    return kq


def vao_tre_atc(z):
    """Nhóm vào trễ (✅ / 🟡) & ptcp.cau_hinh.QUY_VAO_TRE_KHOP = "dong" → chỉ lệnh ATC (backtest Quỹ Bứt Phá von41–42)."""
    if z.get("nhom") not in ("VAO_NHU_MOI", "VAO_NUA"):
        return False
    try:
        from ptcp import cau_hinh as P
    except ImportError:
        return False
    return getattr(P, "QUY_VAO_TRE_KHOP", "mo") == "dong"


def la_sao(z):
    """Mã ★ của tin tổng kết: ưu tiên ≤ SO_MA_MOI_TUAN (số mã mới tối đa / tuần)."""
    ut = z.get("uu_tien")
    return ut is not None and ut == ut and ut <= getattr(C, "SO_MA_MOI_TUAN", 2)


def muc_sau_mua(kq):
    """Cắt lỗ & mục tiêu theo GIÁ MUA THẬT: MUA MỚI tính lại 2×ATR (≤ 7%); vào trễ giữ cắt lỗ hệ thống."""
    gia = kq["gia_mua"] if kq["gia_mua"] == kq["gia_mua"] else kq["gia_nay"]
    cl = kq.get("cl")
    if kq.get("nhom") == "MUA_MOI" and kq.get("atr") and kq["atr"] == kq["atr"]:
        try:
            from ptcp.he_thoat import stop_chuan
            cl = stop_chuan(gia, kq["atr"])
        except ImportError:
            pass
    if not (cl and cl == cl and cl < gia):
        return gia, cl, np.nan, np.nan
    R = gia - cl
    return gia, cl, gia + R, gia + 3 * R


def dong_bang(kq):
    """1 dòng log (công khai) – bảng 15' của mã trong danh sách mua."""
    ky = {True: "✔", False: "✘"}
    tc = " | ".join(f"{t[0].split(' (')[0].replace('Kích hoạt 15', '15')} {ky[bool(t[1])]}" for t in kq["tieu_chi"])
    return (f"  {kq['ma']:<5} {_f(kq['gia_nay']):>8}  {TEN_NHOM.get(kq['nhom'], kq['nhom']):<16} vùng "
            f"{_f(kq['tu'])}–{_f(kq['den'])} | {tc or '–'} → {kq['trang_thai']}: {kq['ly_do']}")


def _gon(tc):
    """Tiêu chí 15' rút gọn cho tin: 'MACD 15' cắt lên ✔ · ≥ VWAP 13,53 ✔ · RSI 57 ✔'."""
    ky = {True: "✔", False: "✘"}
    out = []
    for ten, dat, ct in tc:
        if ten.startswith("Giá trong vùng"):
            continue
        if ten.startswith("Kích hoạt"):
            out.append(f"{ct if dat else 'chưa kích hoạt'} {ky[bool(dat)]}")
        elif "VWAP" in ten:
            out.append(f"≥ {ct} {ky[bool(dat)]}")
        elif ten.startswith("RSI"):
            out.append(f"RSI {ct} {ky[bool(dat)]}")
        else:
            out.append(f"{ten} {ky[bool(dat)]}")
    return " · ".join(out)


def tin_giu_theo_he_thong(kq, bay_gio, vt=None):
    """Mã ĐANG GIỮ trong danh mục mà hệ thống vừa có điểm mua: KHÔNG báo "MUA NGAY" (tránh vừa cắt lỗ vừa mua) –
    giữ vị thế theo đúng lệnh hệ thống (cắt lỗ / mốc của lệnh này), như dmuc._theo_he_thong của danh mục thật.
    vt: vị thế thật (dict danh_muc) → thêm dòng "Đã vào lệnh"."""
    from .vi_the import dong_da_vao
    gia, cl, mt1, mt3 = muc_sau_mua(kq)
    gv = vt.get("gia_von") if isinstance(vt, dict) else None
    return "\n".join([
        f"💼 GIỮ THEO HỆ THỐNG – {kq['ma']} {_f(gia)} ({pd.Timestamp(bay_gio):%H:%M %d/%m})",
        f"Đang giữ, hệ thống vừa có điểm mua ({TEN_NHOM.get(kq['nhom'], kq['nhom'])}) → KHÔNG mua trùng; mua thêm chỉ "
        "khi tin tổng kết ghi MUA THÊM"]
        + ([dong_da_vao(vt.get("ngay_mua"), gv, (gia / gv - 1) * 100 if gia == gia else None)] if gv else [])
        + [f"Giữ theo lệnh hệ thống: Cắt lỗ {_f(cl)}" + (f" ({(cl / gia - 1) * 100:+.1f}%)" if cl == cl and gia else "")
           + f" · Mục tiêu 1R {_f(mt1)} → 3R {_f(mt3)}"])


def dong_dat_lenh(kq, bien_the, gia):
    """Dòng đặt lệnh ngắn gọn: giá đặt + giới hạn (theo cách vào đang dùng)."""
    den = kq.get("den")
    if kq.get("atc"):
        return f"👉 Đặt lệnh ATC (giá ước tính {_f(gia)}). Không mua nếu giá cao hơn {_f(den)}"
    goc = (bien_the or "").partition("+ATC")[0]
    if goc == "ATO":
        return f"👉 Đặt lệnh ATO {_f(gia)}. Không mua nếu mở cửa cao hơn {_f(den)}"
    return f"👉 Đặt lệnh {_f(gia)}. Không đặt cao hơn {_f(den)}"


def tin_mua(kq, bay_gio, bien_the, dang_giu=None):
    if dang_giu:                                       # True hoặc dict vị thế thật (chay.py)
        return tin_giu_theo_he_thong(kq, bay_gio, dang_giu)
    gia, cl, mt1, mt3 = muc_sau_mua(kq)
    dau = "⏰ MUA ATC" if kq.get("atc") else "🟢 MUA NGAY"
    # tin gọn (người dùng 17/10/2026): giá đặt + nhóm / vùng / cắt lỗ / mục tiêu – bỏ dòng tiêu chí & khối lượng;
    # 19/10/2026: ghi đủ chữ (đọc trên điện thoại) · 29/10/2026: 4 dòng (gộp nhóm · vùng · cắt lỗ, mục tiêu · khối lượng)
    from .tong_ket_cl import nhan_uu_tien
    ut = nhan_uu_tien(kq.get("uu_tien"))                 # nhiều tin cùng lúc → thấy mã nào ưu tiên (★1 cao nhất)
    von = _von_nav(kq, gia, cl)
    d = [f"{dau} – {kq['ma']} {_f(gia)} ({pd.Timestamp(bay_gio):%H:%M %d/%m})" + (f" · ưu tiên {ut}" if ut else ""),
         dong_dat_lenh(kq, bien_the, gia),
         f"{TEN_NHOM.get(kq['nhom'], kq['nhom'])} · Vùng mua {_f(kq['tu'])} – {_f(kq['den'])} · Cắt lỗ {_f(cl)}"
         + (f" ({(cl / gia - 1) * 100:+.1f}%)" if cl == cl and gia else ""),
         f"Mục tiêu 1R {_f(mt1)} → 3R {_f(mt3)}" + (f" · {von}" if von else "")]
    if kq.get("he_so_quyen"):
        d.append(f"(Giá đã điều chỉnh quyền – vùng / cắt lỗ của tin tổng kết quy đổi × {kq['he_so_quyen']:.3f}; "
                 "kiểm tra lại giá trên bảng điện)")
    return "\n".join(d)


def _von_nav(kq, gia, cl):
    """'Khối lượng: 💰 ≤5.4% NAV (…)' – cùng công thức tin tổng kết, khoảng cắt lỗ tính theo giá đặt lệnh."""
    from .tong_ket_cl import chu_von_lenh
    r = (gia - cl) / gia * 100 if gia == gia and cl == cl and gia > cl > 0 else None
    s = chu_von_lenh({**kq, "rui_ro": r} if r else kq)
    return s or ""


def _theo_uu_tien(ds):
    """Mã sắp theo ★ (★1 trước), mã không có hạng ưu tiên cuối."""
    return sorted(ds, key=lambda k: (k.get("uu_tien") if k.get("uu_tien") == k.get("uu_tien") and k.get("uu_tien")
                                     is not None else 999))


def chia_tin_mua(ds):
    """Mã MUA cùng 1 lần quét 15' → (mã gửi TIN RIÊNG kèm ảnh, mã DỰ PHÒNG chỉ ghi trong tin tổng hợp). Tin riêng: mã ★;
    không mã nào ★ → mã ưu tiên cao nhất. Người dùng 30/10/2026: lượt 14:30 29/10 gửi 10 tin (8 tin MUA ATC + tin thứ
    tự + nhắc giờ) – như tin tổng kết, chỉ mã ★ đủ dòng, còn lại 1 dòng dự phòng."""
    from .tong_ket_cl import nhan_uu_tien
    x = _theo_uu_tien(ds)
    rieng = [k for k in x if nhan_uu_tien(k.get("uu_tien")).startswith("★")] or x[:1]
    return rieng, [k for k in x if k not in rieng]


def tin_tong_hop_mua(ds, bay_gio, rieng=None):
    """≥ 2 mã báo MUA trong cùng 1 lần quét 15' (người dùng 27/10/2026: HAG + VSC cùng lúc 14:30) → 1 tin thứ tự mua
    theo ★ (★1 trước) để biết đặt mã nào trước khi thiếu tiền / suất; 0–1 mã → None. rieng: mã đã có tin riêng (mặc
    định chia_tin_mua) – 1 dòng; mã còn lại là DỰ PHÒNG, ghi đủ để đặt lệnh: giá, giới hạn, cắt lỗ."""
    if len(ds) < 2:
        return None
    from .tong_ket_cl import nhan_uu_tien
    x = _theo_uu_tien(ds)
    co_rieng = {k["ma"] for k in (chia_tin_mua(x)[0] if rieng is None else rieng)}
    co_atc = any(k.get("atc") for k in x)
    d = [f"📋 {len(x)} MÃ BÁO MUA CÙNG LÚC ({pd.Timestamp(bay_gio):%H:%M %d/%m}) – thứ tự đặt lệnh"
         + (" · ⏰ ATC đặt TRƯỚC 14:45" if co_atc else "") + ":"]
    for i, k in enumerate(x, 1):
        gia, cl = muc_sau_mua(k)[:2]
        dau = f"   {i}. {(nhan_uu_tien(k.get('uu_tien')) + ' ').lstrip()}{k['ma']} {_f(gia)} – " \
              + ("ATC" if k.get("atc") else "mua ngay")
        d.append(dau + (" (tin riêng ở trên)" if k["ma"] in co_rieng else
                        f" ≤ {_f(k['den'])} · Cắt lỗ {_f(cl)} – dự phòng"))
    d.append("Đặt lần lượt từ trên xuống tới khi hết tiền / hết suất mã mới tuần này"
             + ("; dự phòng chỉ khi còn tiền / suất sau mã có tin riêng" if len(co_rieng) < len(x) else ""))
    return "\n".join(d)


def tin_bo(kq, bay_gio):
    return (f"🚫 BỎ {kq['ma']} phiên {pd.Timestamp(bay_gio):%d/%m} – {kq['ly_do']}\n"
            f"(vùng mua {_f(kq['tu'])}–{_f(kq['den'])}; chờ bản tin tổng kết mới)")


def can_bao(ma, trang_thai_moi, bay_gio, luu, ly_do=""):
    """
    Báo 1 lần / mã / phiên: MUA, hoặc BỎ khi VÔ HIỆU thật (mở cửa vượt vùng / thủng vùng trước khi mua) – hết phiên
    mà giá ngoài vùng thì chỉ ghi vào bảng 15', không nhắn. luu: dict trạng thái (cập nhật tại chỗ).
    """
    ngay = f"{pd.Timestamp(bay_gio):%Y-%m-%d}"
    cu = luu.get(ma, {})
    da = cu.get("da_bao", []) if cu.get("ngay") == ngay else []
    luu[ma] = {"ngay": ngay, "trang_thai": trang_thai_moi, "da_bao": da}
    if trang_thai_moi == "BỎ" and not any(x in ly_do for x in ("không đuổi", "trước khi mua", "thủng vùng", "bỏ ATC")):
        return False
    if trang_thai_moi in ("MUA", "BỎ") and trang_thai_moi not in da and "MUA" not in da:
        luu[ma]["da_bao"] = da + [trang_thai_moi]
        return True
    return False
