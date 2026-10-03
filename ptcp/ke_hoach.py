# -*- coding: utf-8 -*-
"""
KẾ HOẠCH VỊ THẾ TỪ GIÁ MUA – dùng chung cho chay.py (1 mã) và Danh_mục (dmuc).

  • Cắt lỗ GỐC: áp đúng quy tắc cắt lỗ thống nhất của công cụ nhưng tính TẠI NGÀY MUA, với GIÁ MUA
      max(đáy ngày xác nhận dưới giá mua − 0.5×ATR ; giá mua − 2×ATR ; giá mua −7%), tối thiểu 1.5×ATR
    (chỉ dùng dữ liệu ĐẾN ngày mua – như khi bạn đặt lệnh hôm đó). Không có ngày mua → tính với dữ liệu hiện tại.
  • Mục tiêu LÚC MUA: dùng ĐÚNG hàm tạo mục tiêu của công cụ (tinh_muc_tieu – đỉnh cũ, đường kháng cự, AB=CD,
    Fibo mở rộng/hồi phục, nền giá, MA, vùng KL, đỉnh 52T; chấm bằng XS chạm trước cắt lỗ & EV) trên dữ liệu ĐẾN
    ngày mua, với cắt lỗ gốc → mục tiêu chính + các mốc kế tiếp. R/R tính từ giá mua.
  • Giá đã vượt mục tiêu lúc mua → dùng mục tiêu HIỆN TẠI của công cụ (phân tích hôm nay) làm mục tiêu tiếp theo.
  • R (= giá mua − cắt lỗ gốc) chỉ dùng để QUẢN LÝ CẮT LỖ (hoà vốn / khoá lãi), không dùng tạo mục tiêu.
  • Cắt lỗ HIỆN TẠI đề xuất (chỉ cao hơn cắt lỗ gốc): hoà vốn khi lãi ≥ 1R, khoá 1R khi lãi ≥ 2R,
    Chandelier (đóng cửa cao nhất từ ngày mua − 3×ATR), cắt lỗ kỹ thuật hôm nay – đều phải cách giá ≥ 1×ATR.
  • So với VN-Index từ ngày mua: % VN-Index cùng kỳ, % cổ phiếu (giá thị trường) cùng kỳ, lãi/lỗ thực theo giá vốn.
"""
import numpy as np
import pandas as pd

from .cau_hinh import PHI_GD_KHU_HOI, TRUOT_GIA_PCT
from .chi_bao import tinh_chi_bao, tim_dinh_day
from .phan_tich import tinh_cat_lo, tinh_muc_tieu
from .chi_bao import duong_xu_huong

CHANDELIER_ATR = 3.0
SO_PHIEN_KHANG_CU = 504            # kháng cự lấy từ đỉnh xác nhận trong ~2 năm gần nhất
KHOANG_CACH_ATR_MIN = 1.0


def _ngay(x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and not x.strip()):
        return None
    try:
        t = pd.to_datetime(x, dayfirst=True) if isinstance(x, str) else pd.Timestamp(x)
        return None if pd.isna(t) else t.normalize()
    except (ValueError, TypeError):
        return None


def _gia_tai(s, ngay):
    """Giá đóng cửa tại phiên gần nhất ≤ ngày (NaN nếu trước dữ liệu)."""
    return float(s.asof(ngay)) if len(s) and ngay >= s.index[0] else np.nan


def ke_hoach_tu_gia_mua(df_ngay, gia_von, ngay_mua=None, vni=None, cat_lo_ky_thuat=None, mt_tu_nhap=None,
                        mt_hien_tai=None, H=63):
    """mt_hien_tai: (giá, phương pháp) – mục tiêu chính của phân tích HÔM NAY (dùng khi giá đã vượt mục tiêu lúc mua)."""
    """df_ngay: OHLCV ngày (đến hôm nay). Trả dict kế hoạch, hoặc None nếu không có giá vốn."""
    if not gia_von or gia_von <= 0 or df_ngay is None or len(df_ngay) < 60:
        return None
    nm = _ngay(ngay_mua)
    if nm is not None and nm > df_ngay.index[-1]:
        nm = None
    ht = float(df_ngay.close.iloc[-1])

    # --- Cắt lỗ gốc tại ngày mua (point-in-time) ---
    goc = df_ngay[df_ngay.index <= nm] if nm is not None else df_ngay
    if len(goc) < 60:
        goc = df_ngay
    d0 = tinh_chi_bao(goc)
    pv0 = tim_dinh_day(d0, "Ngày")
    sl0 = tinh_cat_lo(d0, pv0, gia_von)
    cl_goc, atr0 = sl0["gia"], sl0["atr"]
    R = gia_von - cl_goc

    # --- Mục tiêu LÚC MUA: hàm tạo mục tiêu của công cụ, dữ liệu đến ngày mua, cắt lỗ gốc ---
    d = tinh_chi_bao(df_ngay)
    atr = float(d.ATR.iloc[-1])
    xh0 = duong_xu_huong(d0, pv0)
    mt0 = tinh_muc_tieu(d0, pv0, xh0, "Ngày", goc, {"gia": cl_goc}, H)
    bang_mt = mt0["bang"].copy()
    gia0 = float(goc.close.iloc[-1])
    bang_mt["R/R từ giá mua"] = (bang_mt["Giá mục tiêu"] - gia_von) / R if R > 0 else np.nan
    bang_mt = bang_mt[bang_mt["Giá mục tiêu"] > gia_von * 1.005]
    chinh = mt0["chinh"]
    if chinh is None or chinh["Giá mục tiêu"] <= gia_von * 1.005:
        chinh = bang_mt.iloc[0] if len(bang_mt) else None
    mt_dx = float(chinh["Giá mục tiêu"]) if chinh is not None else gia_von + 3 * atr0
    nguon_mt = (f"{chinh['Phương pháp']} – {mt0['cach_chon']}" if chinh is not None
                else "giá mua + 3×ATR (không có mốc kỹ thuật)")
    cac_moc = bang_mt.sort_values("Giá mục tiêu")
    sau_chinh = cac_moc[cac_moc["Giá mục tiêu"] > mt_dx * 1.01]
    mt_2 = (float(sau_chinh["Giá mục tiêu"].iloc[0]), sau_chinh["Phương pháp"].iloc[0]) if len(sau_chinh) else None

    # --- Cắt lỗ hiện tại đề xuất (chỉ dời lên từ cắt lỗ gốc) ---
    phi = PHI_GD_KHU_HOI + 2 * TRUOT_GIA_PCT
    ung = [("cắt lỗ gốc", cl_goc)]
    if ht >= gia_von + R:
        ung.append(("lãi ≥ 1R → hoà vốn", gia_von * (1 + phi / 100)))
    if ht >= gia_von + 2 * R:
        ung.append(("lãi ≥ 2R → khoá 1R", gia_von + R))
    if nm is not None:
        sau = df_ngay[df_ngay.index >= nm]
        if len(sau) >= 5:
            ung.append((f"Chandelier (đỉnh {sau.close.max():,.2f} − {CHANDELIER_ATR:g}×ATR)",
                        float(sau.close.max()) - CHANDELIER_ATR * atr))
    if cat_lo_ky_thuat is not None and cat_lo_ky_thuat == cat_lo_ky_thuat:
        ung.append(("cắt lỗ kỹ thuật hôm nay", float(cat_lo_ky_thuat)))
    hop_le = [(t, g) for t, g in ung if g <= ht - KHOANG_CACH_ATR_MIN * atr]
    ly_do, cl_hien = max(hop_le, key=lambda x: x[1]) if hop_le else ("cắt lỗ gốc", cl_goc)
    cl_hien = max(cl_hien, cl_goc)
    thung = ht <= cl_goc

    # --- Giá đã vượt mục tiêu lúc mua → mục tiêu HIỆN TẠI của công cụ ---
    da_vuot = ht >= mt_dx * 0.99
    if mt_hien_tai and mt_hien_tai[0] and mt_hien_tai[0] > ht * 1.005:
        mt_tiep, nguon_tiep = float(mt_hien_tai[0]), f"mục tiêu hiện tại của công cụ – {mt_hien_tai[1]}"
    elif mt_2 and mt_2[0] > ht * 1.005:
        mt_tiep, nguon_tiep = mt_2[0], f"mốc lúc mua kế tiếp – {mt_2[1]}"
    else:
        mt_tiep, nguon_tiep = ht + 3 * atr, "giá + 3×ATR (không còn mốc kỹ thuật phía trên)"

    # --- So với VN-Index từ ngày mua ---
    so_vni = {}
    if nm is not None:
        so_ngay = (df_ngay.index[-1] - nm).days
        cp_tu = (ht / _gia_tai(df_ngay.close, nm) - 1) * 100
        so_vni = {"so_ngay": so_ngay, "cp_thi_truong_pct": cp_tu}
        if vni is not None and len(vni):
            v0, v1 = _gia_tai(vni.close, nm), _gia_tai(vni.close, df_ngay.index[-1])
            if v0 == v0 and v0 > 0:
                so_vni["vni_pct"] = (v1 / v0 - 1) * 100
                so_vni["vni_tu"], so_vni["vni_nay"] = v0, v1
    lai = (ht / gia_von - 1) * 100
    if "vni_pct" in so_vni:
        so_vni["chenh_lech"] = lai - so_vni["vni_pct"]

    return {
        "gia_von": gia_von, "ngay_mua": nm, "gia_hien_tai": ht, "lai_lo_pct": lai, "atr_luc_mua": atr0, "atr": atr,
        "cat_lo_goc": cl_goc, "cat_lo_goc_pct": (cl_goc / gia_von - 1) * 100, "cat_lo_goc_theo": sl0["theo"],
        "R": R, "lai_theo_R": (ht - gia_von) / R if R > 0 else np.nan,
        "muc_tieu_de_xuat": mt_dx, "nguon_muc_tieu": nguon_mt, "muc_tieu_2": mt_2,
        "bang_muc_tieu_luc_mua": cac_moc, "gia_ngay_mua": gia0,
        "rr_tu_gia_mua": (mt_dx - gia_von) / R if R > 0 else np.nan,
        "mt_tu_nhap": mt_tu_nhap, "rr_mt_tu_nhap": (mt_tu_nhap - gia_von) / R if mt_tu_nhap and R > 0 else np.nan,
        "cat_lo_hien_tai": cl_hien, "ly_do_cat_lo": ly_do, "thung_cat_lo_goc": thung,
        "da_vuot_muc_tieu": da_vuot, "muc_tieu_tiep_theo": mt_tiep, "nguon_muc_tieu_tiep": nguon_tiep,
        "muc_tieu_hieu_luc": mt_tiep if da_vuot else mt_dx,
        "con_toi_muc_tieu_pct": (mt_dx / ht - 1) * 100, "so_vni": so_vni,
        "dung_ngay_mua": nm is not None,
    }


def bang_ke_hoach(kh):
    """DataFrame 2 cột (Chỉ tiêu, Giá trị) – dùng cho Excel."""
    if not kh:
        return pd.DataFrame(columns=["Chỉ tiêu", "Giá trị"])
    v = kh["so_vni"]
    rows = [("Giá vốn", kh["gia_von"]), ("Ngày mua", f"{kh['ngay_mua']:%d/%m/%Y}" if kh["ngay_mua"] is not None else "–"),
            ("Giá hiện tại", kh["gia_hien_tai"]), ("Lãi/lỗ %", kh["lai_lo_pct"]),
            ("Cắt lỗ gốc (tại ngày mua)", kh["cat_lo_goc"]), ("Cắt lỗ gốc %", kh["cat_lo_goc_pct"]),
            ("Cắt lỗ gốc theo", kh["cat_lo_goc_theo"]), ("1R (đồng/CP, nghìn)", kh["R"]),
            ("Lãi hiện tại theo R", kh["lai_theo_R"]),
            ("Mục tiêu lúc mua", kh["muc_tieu_de_xuat"]), ("Nguồn mục tiêu", kh["nguon_muc_tieu"]),
            ("Mốc kế tiếp lúc mua", kh["muc_tieu_2"][0] if kh["muc_tieu_2"] else None),
            ("R/R từ giá mua", kh["rr_tu_gia_mua"]), ("Mục tiêu tự nhập", kh["mt_tu_nhap"]),
            ("Đã vượt mục tiêu lúc mua", "Có" if kh["da_vuot_muc_tieu"] else "Chưa"),
            ("Mục tiêu tiếp theo", kh["muc_tieu_tiep_theo"]), ("Nguồn mục tiêu tiếp theo", kh["nguon_muc_tieu_tiep"]),
            ("Cắt lỗ hiện tại đề xuất", kh["cat_lo_hien_tai"]), ("Lý do", kh["ly_do_cat_lo"])]
    if v:
        rows += [("Số ngày nắm giữ", v.get("so_ngay")), ("Cổ phiếu (giá TT) từ ngày mua %", v.get("cp_thi_truong_pct")),
                 ("VN-Index từ ngày mua %", v.get("vni_pct")), ("Chênh lệch lãi/lỗ − VN-Index (điểm %)", v.get("chenh_lech"))]
    return pd.DataFrame(rows, columns=["Chỉ tiêu", "Giá trị"])


def dong_ke_hoach(kh):
    """Các dòng văn bản để in báo cáo."""
    if not kh:
        return []
    f = lambda x: "N/A" if x is None or x != x else f"{x:,.2f}"
    v = kh["so_vni"]
    d = [f"Giá vốn {f(kh['gia_von'])}"
         + (f", mua ngày {kh['ngay_mua']:%d/%m/%Y}" if kh["ngay_mua"] is not None else " (chưa có ngày mua)")
         + f" → giá hiện tại {f(kh['gia_hien_tai'])} ({kh['lai_lo_pct']:+.1f}%, {kh['lai_theo_R']:+.1f}R)",
         f"Cắt lỗ GỐC (tính tại ngày mua): {f(kh['cat_lo_goc'])} ({kh['cat_lo_goc_pct']:+.1f}%) – {kh['cat_lo_goc_theo']}"
         f" | 1R = {f(kh['R'])} (chỉ dùng để dời cắt lỗ: hoà vốn ≥ 1R, khoá lãi ≥ 2R)",
         f"Mục tiêu LÚC MUA (phương pháp kỹ thuật của công cụ, dữ liệu đến ngày mua): {f(kh['muc_tieu_de_xuat'])} "
         f"– {kh['nguon_muc_tieu']} | R/R từ giá mua {kh['rr_tu_gia_mua']:.1f}"
         + (f" | mốc kế tiếp {f(kh['muc_tieu_2'][0])} ({kh['muc_tieu_2'][1]})" if kh["muc_tieu_2"] else ""),
         (f"→ ĐÃ VƯỢT mục tiêu lúc mua: chốt lời một phần, mục tiêu TIẾP THEO {f(kh['muc_tieu_tiep_theo'])} "
          f"({kh['nguon_muc_tieu_tiep']})" if kh["da_vuot_muc_tieu"]
          else f"Còn {kh['con_toi_muc_tieu_pct']:+.1f}% tới mục tiêu lúc mua")]
    b = kh["bang_muc_tieu_luc_mua"]
    if len(b):
        d.append("Các mốc lúc mua: " + "; ".join(
            f"{r['Giá mục tiêu']:,.2f} {r['Phương pháp']} (EV {r['EV %']:+.1f}%)" for _, r in b.head(6).iterrows()))
    if kh["mt_tu_nhap"]:
        d.append(f"Mục tiêu tự nhập {f(kh['mt_tu_nhap'])} → R/R từ giá mua {kh['rr_mt_tu_nhap']:.1f}")
    d.append(f"Cắt lỗ HIỆN TẠI đề xuất: {f(kh['cat_lo_hien_tai'])} – {kh['ly_do_cat_lo']}"
             + (" | ⚠ GIÁ ĐÃ THỦNG CẮT LỖ GỐC" if kh["thung_cat_lo_goc"] else ""))
    if v.get("vni_pct") is not None:
        d.append(f"So với VN-Index từ ngày mua ({v['so_ngay']} ngày): lãi/lỗ thực {kh['lai_lo_pct']:+.1f}% vs VN-Index "
                 f"{v['vni_pct']:+.1f}% ({v['vni_tu']:,.2f} → {v['vni_nay']:,.2f}) → "
                 f"{'VƯỢT' if v['chenh_lech'] >= 0 else 'KÉM'} {abs(v['chenh_lech']):.1f} điểm %")
    elif kh["ngay_mua"] is None:
        d.append("Nhập ngày mua để so sánh với VN-Index từ ngày mua.")
    return d
