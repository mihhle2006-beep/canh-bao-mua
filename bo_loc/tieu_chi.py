# -*- coding: utf-8 -*-
"""
DANH MỤC TIÊU CHÍ: khoá → (tên hiển thị, hàm kiểm tra(m, ngưỡng) → True/False/None=thiếu dữ liệu).
Chiến lược (thư mục chien_luoc/) chỉ tham chiếu các KHOÁ ở đây → thêm tiêu chí mới: thêm 1 dòng vào TIEU_CHI.
"""
from .tien_ich import co as _co


def _tlv(m, t):
    """t = (số ngày, tỷ lệ KL, % giá tăng[, biên độ %]) – mặc định (20, 5, 5)."""
    from .phan_tich.ky_thuat import BIEN_DO_TICH_LUY, tich_luy_va_vuot
    t = tuple(t) if isinstance(t, (tuple, list)) else (20, 5, 5)
    n, k, p_ = (list(t) + [20, 5, 5])[:3]
    bd = t[3] if len(t) > 3 else BIEN_DO_TICH_LUY
    if "_d" not in m:
        x = m.get("tlv") or {}
        return x.get("dat")
    return tich_luy_va_vuot(m["_d"], n, k, p_, bd)["dat"]

TIEU_CHI = {
    # --- chiến lược theo thị trường (bo_loc/chien_luoc_tt.py – cùng logic bot canh-bao-mua / ptcp)
    "cl_tt_mua": ("Chiến lược thị trường: nhóm MUA (mới / như lệnh mới / ½)",
                  lambda m, t: (m["cl_tt"]["nhom"] in ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA")) if m.get("cl_tt") else None),
    "cl_tt_khong_ban": ("Chiến lược thị trường: hệ thống không lỗ / không sắp bán",
                        lambda m, t: (m["cl_tt"]["nhom"] not in ("DUOI_VON", "BAN")) if m.get("cl_tt") else None),
    "gtgd_min": ("GTGD TB20 ≥ {} tỷ", lambda m, t: m["gtgd20"] >= t),
    "gia_min": ("Giá ≥ {} nghìn", lambda m, t: m["gia"] >= t),
    "tren_ma50": ("Giá > MA50", lambda m, t: m["gia"] > m["ma50"] if _co(m["ma50"]) else None),
    "tren_ma200": ("Giá > MA200", lambda m, t: m["gia"] > m["ma200"] if _co(m["ma200"]) else None),
    "ma50_tren_ma200": ("MA50 > MA200", lambda m, t: m["ma50"] > m["ma200"] if _co(m["ma200"]) else None),
    "macd_ngay_tren_sig": ("MACD ngày > Signal", lambda m, t: m["macd_d"] > m["sig_d"]),
    "macd_ngay_cat_len": ("MACD ngày vừa cắt lên Signal/0", lambda m, t: m["cat_len_d"]),
    "macd_tuan_tren_sig": ("MACD tuần > Signal", lambda m, t: m["macd_w"] > m["sig_w"]),
    "macd_tuan_tren_0": ("MACD tuần > 0", lambda m, t: m["macd_w"] > 0),
    "rsi_trong": ("RSI trong {}–{}", lambda m, t: t[0] <= m["rsi"] <= t[1]),
    "rsi_duoi": ("RSI < {}", lambda m, t: m["rsi"] < t),
    "cau_truc_tang": ("Cấu trúc đỉnh/đáy ngày TĂNG", lambda m, t: m["cau_truc_d"].startswith("TĂNG")),
    "day_cao_hon": ("Đáy sau cao hơn đáy trước", lambda m, t: m["day_cao_hon"]),
    "phan_ky_duong": ("Phân kỳ dương MACD", lambda m, t: m["phan_ky_duong"]),
    "khong_thung_ho_tro": ("Chưa thủng hỗ trợ ngày", lambda m, t: not m["thung_ho_tro"]),
    "gan_dinh52": ("Cách đỉnh 52T ≤ {}%", lambda m, t: -m["cach_dinh52"] <= t),
    "xa_dinh52": ("Thấp hơn đỉnh 52T ≥ {}%", lambda m, t: -m["cach_dinh52"] >= t),
    "gan_day52": ("Cao hơn đáy 52T ≤ {}%", lambda m, t: m["tren_day52"] <= t),
    "cach_xa_day52": ("Cao hơn đáy 52T ≥ {}%", lambda m, t: m["tren_day52"] >= t),
    "vi_tri_52t": ("Giá ở ≥ {}% biên độ 52T", lambda m, t: m["vi_tri52"] >= t),
    "rs_3t": ("Mạnh hơn VNINDEX 3T > {} điểm %", lambda m, t: m["rs3t"] > t if _co(m["rs3t"]) else None),
    "vol_dot_bien": ("KL phiên cuối ≥ {}× TB20", lambda m, t: m["vol_ratio"] >= t),
    "upside_min": ("Upside mục tiêu ≥ {}%", lambda m, t: m["upside"] >= t if _co(m["upside"]) else None),
    "rr_min": ("R/R ≥ {}", lambda m, t: m["rr"] >= t if _co(m["rr"]) else None),
    "tich_luy_vuot": ("Tích lũy > {} phiên & vượt: KL > {}× TB nền, giá tăng > {}%", _tlv),
    "dang_tich_luy": ("Đang tích lũy ≥ {} phiên (biên độ ≤ 15%)", lambda m, t: m["tich_luy_phien"] >= t),
    "beta_min": ("Beta ≥ {}", lambda m, t: m["beta"] >= t if _co(m["beta"]) else None),
    "gia_trong": ("Giá trong {}–{} nghìn", lambda m, t: t[0] <= m["gia"] <= t[1]),
    "fa_khong_nguy_hiem": ("Không tiêu chí tài chính nào ở mức Nguy hiểm",
                           lambda m, t: m["fa_nguy_hiem"] == 0 if _co(m.get("fa_diem")) else None),
    "fa_diem_min": ("Điểm phân tích tài chính 10 tiêu chí ≥ {}",
                    lambda m, t: m["fa_diem"] >= t if _co(m.get("fa_diem")) else None),
    "eps_min": ("EPS 4 quý ≥ {:,} đ", lambda m, t: m["eps_dung"] >= t if _co(m.get("eps_dung")) else None),
    "pe_duoi_tv_nganh": ("P/E < trung vị nhóm ngành", lambda m, t: m["pe"] < m["pe_tv_nhom"]
                         if _co(m.get("pe")) and _co(m.get("pe_tv_nhom")) and m["pe"] > 0 else None),
    "eps_duong": ("EPS 4 quý > 0", lambda m, t: m["eps_dung"] > 0 if _co(m.get("eps_dung")) else None),
    "klgd3t_min": ("KL TB 3 tháng ≥ {:,} CP", lambda m, t: m["klgd3t"] >= t),
    "rsi_vuot_30": ("RSI vừa vượt lên 30 (thoát quá bán)", lambda m, t: m["rsi_vuot_30"]),
    "tin_hieu_dao_chieu": ("Có tín hiệu đảo chiều (RSI vượt 30 / MACD cắt lên / phân kỳ dương / nến đảo chiều tăng)",
                           lambda m, t: bool(m["rsi_vuot_30"] or m["cat_len_d"] or m["phan_ky_duong"]
                                             or str(m.get("mo_hinh_nen", "")).endswith("↑"))),
    "beta_max": ("Beta ≤ {}", lambda m, t: m["beta"] <= t if _co(m["beta"]) else None),
    "pe_max": ("P/E ≤ {}", lambda m, t: 0 < m["pe"] <= t if _co(m["pe"]) else None),
    "pb_max": ("P/B ≤ {}", lambda m, t: 0 < m["pb"] <= t if _co(m["pb"]) else None),
    "roe_min": ("ROE ≥ {}%", lambda m, t: m["roe"] >= t if _co(m["roe"]) else None),
    # --- Kỹ thuật bổ sung ---
    "ma20_tren_ma50": ("MA20 > MA50", lambda m, t: m["ma20"] > m["ma50"] if _co(m["ma50"]) else None),
    "ma20_doc_len": ("MA20 dốc lên (so 5 phiên trước)", lambda m, t: m["ma20_doc"] > 0),
    "adx_min": ("ADX ≥ {} và +DI > −DI", lambda m, t: m["adx"] >= t and m["pdi"] > m["mdi"]),
    "breakout_20": ("Đóng cửa vượt đỉnh 20 phiên trước", lambda m, t: m["gia"] > m["dinh20"]),
    # --- Bổ sung bộ tiêu chuẩn ---
    "von_hoa_min": ("Vốn hoá ≥ {:,} tỷ", lambda m, t: m["von_hoa"] >= t if _co(m["von_hoa"]) else None),
    "klgd_min": ("KLGD TB20 ≥ {:,} CP", lambda m, t: m["klgd20"] >= t),
    "klgd_cao": ("KLGD TB20 ≥ {:,} CP (thanh khoản cao)", lambda m, t: m["klgd20"] >= t),
    "tren_supertrend": ("Giá trên SuperTrend ({}, ×{})", lambda m, t: m["st_dir"] > 0),
    "eps_tang_nam": ("EPS năm tăng trưởng", lambda m, t: m["eps_g_nam"] > 0 if _co(m["eps_g_nam"]) else None),
    "eps_tang_quy": ("EPS quý tăng so cùng kỳ", lambda m, t: m["eps_g_quy"] > 0 if _co(m["eps_g_quy"]) else None),
    "kiem_toan_5nam": ("Kiểm toán chấp nhận toàn phần 5 năm",
                       lambda m, t: bool(m["kiem_toan_5nam"]) if _co(m["kiem_toan_5nam"]) else None),
    "no_vay_tts_max": ("Nợ vay/Tổng tài sản ≤ {}%",
                       lambda m, t: m["no_vay_tts"] <= t if _co(m["no_vay_tts"]) else None),
    "no_phai_tra_tts_max": ("Nợ phải trả/Tổng tài sản ≤ {}%",
                            lambda m, t: m["no_phai_tra_tts"] <= t if _co(m["no_phai_tra_tts"]) else None),
    "roa_min": ("ROA ≥ {}%", lambda m, t: m["roa"] >= t if _co(m["roa"]) else None),
    "fcf_duong": ("Dòng tiền tự do ≥ 0", lambda m, t: m["fcf"] >= 0 if _co(m["fcf"]) else None),
    "tt_hien_thoi_min": ("Thanh toán hiện thời ≥ {}",
                         lambda m, t: m["tt_hien_thoi"] >= t if _co(m["tt_hien_thoi"]) else None),
    "tt_nhanh_min": ("Thanh toán nhanh ≥ {}", lambda m, t: m["tt_nhanh"] >= t if _co(m["tt_nhanh"]) else None),
    "co_tuc_lien_tuc": ("Trả cổ tức liên tục ≥ {} năm",
                        lambda m, t: m["so_nam_co_tuc"] >= t if _co(m["so_nam_co_tuc"]) else None),
    "ty_suat_co_tuc_min": ("Tỷ suất cổ tức ≥ {}%",
                           lambda m, t: m["ty_suat_co_tuc"] >= t if _co(m["ty_suat_co_tuc"]) else None),
}


# Các tiêu chí cần dữ liệu cơ bản (để biết khi nào phải tải dữ liệu cơ bản)
KHOA_CO_BAN = {"pe_max", "pb_max", "roe_min", "roa_min", "von_hoa_min", "eps_tang_nam", "eps_tang_quy",
               "kiem_toan_5nam", "no_vay_tts_max", "no_phai_tra_tts_max", "fcf_duong",
               "tt_hien_thoi_min", "tt_nhanh_min", "co_tuc_lien_tuc", "ty_suat_co_tuc_min", "eps_duong", "eps_min",
               "pe_duoi_tv_nganh", "fa_khong_nguy_hiem", "fa_diem_min"}


def ten_tieu_chi(k, t):
    mau = TIEU_CHI[k][0]
    if t is None:
        return mau
    return mau.format(*t) if isinstance(t, (tuple, list)) else mau.format(t)


def kiem_tra(k, m, t):
    """True / False / None (thiếu dữ liệu hoặc lỗi tính)."""
    try:
        v = TIEU_CHI[k][1](m, t)
    except Exception:
        return None
    return None if v is None else bool(v)
