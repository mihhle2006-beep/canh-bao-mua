# -*- coding: utf-8 -*-
"""
ĐÁNH GIÁ SAU LỌC: B2 điểm 5 trụ cột → B3 cờ đỏ → B4 kế hoạch giao dịch → B5 hành động → B6 so sánh trong nhóm.
"""
import numpy as np
import pandas as pd

from . import cau_hinh as ch
from .tien_ich import bac, co, diem_tang_truong, dung, trung_binh

THU_TU_HANH_DONG = ["MUA", "MUA KHI CHỈNH VỀ VÙNG MUA", "MUA THĂM DÒ (½ vị thế)", "CHỜ NHỊP CHỈNH",
                    "THEO DÕI", "THEO DÕI – có cờ đỏ", "LOẠI"]


def cham_tru_cot(m):
    """B2 – điểm 0–100 từng trụ cột (bỏ qua chỉ tiêu thiếu dữ liệu)."""
    has = lambda k: co(m.get(k))
    xu_huong = trung_binh([
        dung(m["gia"] > m["ma20"]) if has("ma20") else np.nan,
        dung(m["gia"] > m["ma50"]) if has("ma50") else np.nan,
        dung(m["gia"] > m["ma200"]) if has("ma200") else np.nan,
        dung(m["ma20"] > m["ma50"]) if has("ma50") and has("ma20") else np.nan,
        dung(m["ma50"] > m["ma200"]) if has("ma200") and has("ma50") else np.nan,
        dung(m["st_dir"] > 0),
        dung(m["macd_w"] > m["sig_w"]), dung(m["macd_w"] > 0),
        dung(m["adx"] >= 20 and m["pdi"] > m["mdi"]),
        dung(str(m["cau_truc_d"]).startswith("TĂNG")),
    ])
    rsi = m.get("rsi")
    diem_rsi = (100 if 50 <= rsi <= 70 else 60 if 45 <= rsi <= 75 else 30 if 40 <= rsi <= 80 else 0) \
        if co(rsi) else np.nan
    dong_luong = trung_binh([
        diem_rsi,
        float(np.clip(50 + m["rs3t"] * 2.5, 0, 100)) if has("rs3t") else np.nan,
        dung(m["macd_d"] > m["sig_d"]),
        m["vi_tri52"] if has("vi_tri52") else np.nan,
        dung(m["ret1t"] > 0) if has("ret1t") else np.nan,
    ])
    pe = m.get("pe")
    dinh_gia = trung_binh([
        (0.0 if pe <= 0 else bac(pe, [(10, 100), (15, 80), (20, 55), (25, 30)], 0)) if co(pe) else np.nan,
        bac(m.get("pb"), [(1, 100), (2, 75), (3, 50), (4, 25)], 0) if has("pb") and m["pb"] > 0 else np.nan,
        bac(-m["ty_suat_co_tuc"], [(-5, 100), (-3, 60), (-0.01, 30)], 0) if has("ty_suat_co_tuc") else np.nan,
    ])
    chat_luong = trung_binh([
        bac(-m["roe"], [(-20, 100), (-15, 80), (-12, 60), (-8, 30)], 0) if has("roe") else np.nan,
        bac(-m["roa"], [(-10, 100), (-7, 75), (-5, 50), (-2, 25)], 0) if has("roa") else np.nan,
        diem_tang_truong(m.get("eps_g_nam")), diem_tang_truong(m.get("eps_g_quy")),
        diem_tang_truong(m.get("dt_g_quy")), diem_tang_truong(m.get("ln_g_quy")),
        dung(m["bien_gop"] >= m["bien_gop_ck"]) if has("bien_gop") and has("bien_gop_ck") else np.nan,
        bac(m.get("no_phai_tra_tts"), [(40, 100), (60, 60), (75, 30)], 0) if has("no_phai_tra_tts") else np.nan,
        dung(m["fcf"] >= 0) if has("fcf") else np.nan,
        m["fa_diem"] if has("fa_diem") else np.nan,           # điểm 10 tiêu chí tài chính (3 năm)
    ])
    rui_ro = trung_binh([
        bac(m.get("beta"), [(0.8, 100), (1.0, 80), (1.2, 60), (1.5, 30)], 0) if has("beta") else np.nan,
        bac(m.get("bien_dong"), [(25, 100), (35, 70), (50, 40)], 10) if has("bien_dong") else np.nan,
        bac(-m["mdd52"], [(15, 100), (25, 70), (40, 40)], 10) if has("mdd52") else np.nan,
        bac(m.get("kc_cat_lo"), [(8, 100), (12, 70), (18, 40)], 10) if has("kc_cat_lo") else np.nan,
        bac(-m["gtgd20"], [(-20, 100), (-5, 70), (-1, 40)], 10) if has("gtgd20") else np.nan,
    ])
    return {"Xu hướng": xu_huong, "Động lượng": dong_luong, "Định giá": dinh_gia,
            "Chất lượng": chat_luong, "Rủi ro": rui_ro}


def diem_tong(tc, trong_so=None):
    trong_so = trong_so or ch.TRONG_SO
    w = {k: v for k, v in trong_so.items() if co(tc.get(k))}
    if not w:
        return np.nan
    return sum(tc[k] * v for k, v in w.items()) / sum(w.values())


def ke_hoach_giao_dich(m, von_trieu, rui_ro_pct):
    """
    B4 – vùng mua, cắt lỗ, mục tiêu, khối lượng (lô 100 CP).
    Có chiến lược thị trường (m["cl_tt"]): vùng mua / cắt lỗ của hệ thống (chuẩn hệ thoát T2-3R-ma10),
    mục tiêu tạm thời 1R → 3R (mốc dời cắt lỗ, KHÔNG chốt cứng). Không có: cắt lỗ chuẩn 2×ATR (≤ 7%), mốc 1R/3R.
    """
    gia, atr = m["gia"], m["atr"]
    k = m.get("cl_tt")
    if k is not None and getattr(ch, "THEO_CHIEN_LUOC_TT", True):
        return _ke_hoach_chien_luoc(m, k, von_trieu, rui_ro_pct)
    # Cắt lỗ = CẮT LỖ THỐNG NHẤT của lõi ptcp (đã gồm đáy xác nhận − 0,5×ATR, giá − 2×ATR, −7%, tối thiểu 1,5×ATR)
    sl_core = m.get("cat_lo")
    sl = sl_core if co(sl_core) and sl_core < gia else gia - ch.SO_ATR_CAT_LO * atr
    co_mt = co(m.get("gia_mt")) and m["gia_mt"] > gia
    mt = m["gia_mt"] if co_mt else gia + 2 * (gia - sl)
    rr = (mt - gia) / (gia - sl)
    vung_tu = max(m["ma20"], gia - atr) if co(m.get("ma20")) and m["ma20"] < gia else gia - 0.5 * atr
    von = von_trieu * 1e6
    cp_rui_ro = von * rui_ro_pct / 100 / ((gia - sl) * 1000)
    cp_ty_trong = von * ch.TY_TRONG_MAX / 100 / (gia * 1000)
    cp_mot_phien = m["klgd20"] * ch.TY_LE_THANH_KHOAN / 100
    so_cp = int(min(cp_rui_ro, cp_ty_trong) // 100 * 100)
    return {
        "vung_mua": f"{vung_tu:,.2f} – {gia:,.2f}", "cat_lo_kh": sl, "kc_cat_lo": (gia - sl) / gia * 100,
        "muc_tieu_kh": mt, "nguon_mt": "mục tiêu kỹ thuật" if co_mt else "2R (không có mục tiêu)", "rr_kh": rr,
        "so_cp_kh": so_cp, "gia_tri_kh": so_cp * gia / 1000, "ty_trong_kh": so_cp * gia * 1000 / von * 100,
        "rang_buoc_kl": "rủi ro/lệnh" if cp_rui_ro <= cp_ty_trong else f"tỷ trọng tối đa {ch.TY_TRONG_MAX}%",
        "so_phien_mua": so_cp / cp_mot_phien if cp_mot_phien > 0 else np.nan,
    }


def _ke_hoach_chien_luoc(m, k, von_trieu, rui_ro_pct):
    from .loi.he_thoat import stop_chuan
    gia, atr = m["gia"], m["atr"]
    sl = k["cl"] if k and co(k.get("cl")) and k["cl"] < gia else float(stop_chuan(gia, atr))
    R = gia - sl
    tu, den = (k.get("tu"), k.get("den")) if k else (np.nan, np.nan)
    co_vung = co(tu) and co(den)
    von = von_trieu * 1e6
    cp_rui_ro = von * rui_ro_pct / 100 / (R * 1000)
    cp_ty_trong = von * ch.TY_TRONG_MAX / 100 / (gia * 1000)
    cp_mot_phien = m["klgd20"] * ch.TY_LE_THANH_KHOAN / 100
    so_cp = int(min(cp_rui_ro, cp_ty_trong) // 100 * 100)
    nhom = (k or {}).get("nhom")
    return {
        "vung_mua": (f"{tu:,.2f} – {den:,.2f}" if co_vung else "–"),
        "vung_cho": nhom == "CHO",
        "cat_lo_kh": sl, "kc_cat_lo": R / gia * 100,
        "muc_tieu_kh": gia + R, "muc_tieu_3r": gia + 3 * R, "nguon_mt": "mốc 1R / 3R (dời cắt lỗ – không chốt cứng)",
        "rr_kh": np.nan,
        "so_cp_kh": so_cp, "gia_tri_kh": so_cp * gia / 1000, "ty_trong_kh": so_cp * gia * 1000 / von * 100,
        "rang_buoc_kl": "rủi ro/lệnh" if cp_rui_ro <= cp_ty_trong else f"tỷ trọng tối đa {ch.TY_TRONG_MAX}%",
        "so_phien_mua": so_cp / cp_mot_phien if cp_mot_phien > 0 else np.nan,
        "nhom_cl": nhom, "ten_nhom_cl": (k or {}).get("ten_nhom", ""), "dat_diem_mua": (k or {}).get("ly_do", ""),
        "vo_hieu": (k or {}).get("vo_hieu", ""),
        "gia_lo": _gia_lo(tu, den) if co_vung and nhom in ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA") else np.nan,
    }


def _gia_lo(tu, den):
    """Giá đặt LO phiên tới = ⅓ dưới vùng, làm tròn xuống bước giá (như tin tổng kết canh-bao-mua – cách vào LO+ATC★)."""
    from ptcp.chien_luoc import lam_tron_buoc
    return lam_tron_buoc(tu + (den - tu) / 3, False)


def xep_loai_theo_chien_luoc(nhom, dat_loc, gan_dat, nang):
    """
    B5 – hành động theo CHIẾN LƯỢC THỊ TRƯỜNG (cùng bot): 🟢/✅ → MUA · 🟡 → MUA THĂM DÒ (½) · ⏳ → CHỜ NHỊP CHỈNH ·
    hệ thống lỗ / sắp bán / chưa có tín hiệu → THEO DÕI. Không đạt lọc của chiến lược đang chạy → THEO DÕI / LOẠI;
    cờ đỏ nặng → THEO DÕI – có cờ đỏ.
    """
    if not (dat_loc or gan_dat):
        return "LOẠI"
    if nang:
        return "THEO DÕI – có cờ đỏ"
    if not dat_loc:
        return "THEO DÕI"
    return {"MUA_MOI": "MUA", "VAO_NHU_MOI": "MUA", "VAO_NUA": "MUA THĂM DÒ (½ vị thế)",
            "CHO": "CHỜ NHỊP CHỈNH"}.get(nhom, "THEO DÕI")


def co_do(m, kh):
    """B3 – cờ đỏ: (nặng, nhẹ)."""
    nang, nhe = [], []
    g = lambda k: m.get(k)
    if co(g("fa_nguy_hiem")) and g("fa_nguy_hiem") >= 2:
        nang.append(f"Phân tích TC: {int(g('fa_nguy_hiem'))} tiêu chí Nguy hiểm ({g('fa_tom_tat')})")
    elif co(g("fa_nguy_hiem")) and g("fa_nguy_hiem") == 1:
        nhe.append(f"Phân tích TC: {g('fa_tom_tat')}")
    elif co(g("fa_canh_bao")) and g("fa_canh_bao") >= 3:
        nhe.append(f"Phân tích TC: {g('fa_tom_tat')}")
    if g("st_dir") is not None and g("st_dir") < 0:
        nang.append("Dưới SuperTrend (xu hướng ngắn hạn giảm)")
    if g("thung_ho_tro"):
        nang.append("Đã thủng hỗ trợ ngày")
    if co(g("gtgd20")) and g("gtgd20") < 1:
        nang.append(f"Thanh khoản rất thấp ({g('gtgd20'):.2f} tỷ/phiên)")
    if co(g("free_float")) and g("free_float") < 5:
        nang.append(f"Free float chỉ ~{g('free_float'):.0f}% (dễ bị chi phối giá)")
    if co(g("kiem_toan_ngoai_tru")) and g("kiem_toan_ngoai_tru") >= 1:
        nang.append("BCTC/soát xét gần nhất có ngoại trừ hoặc chưa đủ bằng chứng")
    if co(g("eps_g_quy")) and g("eps_g_quy") < -20:
        nang.append(f"EPS quý giảm {abs(g('eps_g_quy')):.0f}% so cùng kỳ")
    elif co(g("ln_g_quy")) and g("ln_g_quy") < -20:
        nang.append(f"LNST quý giảm {abs(g('ln_g_quy')):.0f}% so cùng kỳ")
    if co(g("rsi")) and g("rsi") > 75:
        nhe.append(f"RSI {g('rsi'):.0f} – quá mua")
    if co(g("cach_ma20")) and g("cach_ma20") > 12:
        nhe.append(f"Giá cao hơn MA20 {g('cach_ma20'):.0f}% – chờ nhịp chỉnh")
    if co(g("pe")) and g("pe") > 30:
        nhe.append(f"P/E {g('pe'):.1f} cao")
    if co(g("no_phai_tra_tts")) and g("no_phai_tra_tts") > 75:
        nhe.append("Nợ phải trả/TTS > 75% (bỏ qua nếu là ngân hàng/CK)")
    if co(g("bien_gop")) and co(g("bien_gop_ck")) and g("bien_gop") < g("bien_gop_ck") - 1:
        nhe.append(f"Biên gộp thu hẹp ({g('bien_gop_ck'):.1f}% → {g('bien_gop'):.1f}%)")
    if str(g("san") or "").upper().startswith("UPCOM"):
        nhe.append("UPCoM: biên độ ±15%, yêu cầu công bố thông tin thấp hơn")
    if g("canh_bao_du_lieu"):
        from .nguon.co_ban import TEN_CHI_TIEU
        ct = [x.split(":")[0].strip() for x in str(g("canh_bao_du_lieu")).split(" | ") if x.strip()]
        nhe.append("Nguồn dữ liệu lệch nhau ở " + ", ".join(TEN_CHI_TIEU.get(k, k) for k in ct)
                   + " – kiểm tra lại số liệu")
    if co(kh.get("so_phien_mua")) and kh["so_phien_mua"] > 5:
        nhe.append(f"Cần ~{kh['so_phien_mua']:.0f} phiên để gom đủ vị thế")
    if co(kh.get("kc_cat_lo")) and kh["kc_cat_lo"] > 15:
        nhe.append(f"Cắt lỗ xa {kh['kc_cat_lo']:.0f}% – nên giảm khối lượng")
    if co(g("bien_dong")) and g("bien_dong") > 50:
        nhe.append(f"Biến động mạnh ({g('bien_dong'):.0f}%/năm)")
    return nang, nhe


def xep_loai_hanh_dong(dat_loc, gan_dat, diem, rr, nang, nhe):
    """B5 – hành động gợi ý (tham khảo)."""
    cho_chinh = any(("quá mua" in x) or ("MA20" in x) for x in nhe)
    if nang:
        return "THEO DÕI – có cờ đỏ" if dat_loc or gan_dat else "LOẠI"
    if dat_loc and co(diem) and diem >= ch.NGUONG_HANH_DONG["mua"] and co(rr) and rr >= 2:
        return "MUA KHI CHỈNH VỀ VÙNG MUA" if cho_chinh else "MUA"
    if dat_loc and co(diem) and diem >= ch.NGUONG_HANH_DONG["tham_do"]:
        return "CHỜ NHỊP CHỈNH" if cho_chinh else "MUA THĂM DÒ (½ vị thế)"
    if (dat_loc or gan_dat) and co(diem) and diem >= ch.NGUONG_HANH_DONG["tham_do"]:
        return "THEO DÕI"
    return "LOẠI"


def so_sanh_trong_nhom(e):
    """
    B6 – P/E, P/B (lần trung vị) và ROE (chênh điểm %) so với TRUNG VỊ CÙNG NHÓM NGÀNH.
    Nhóm có < SO_MA_TOI_THIEU_SO_SANH_NHOM mã có dữ liệu → so với trung vị toàn bộ mã quét (ghi rõ ở cột 'Cơ sở so sánh').
    """
    e = e.copy()
    nhom = e["Nhóm"].replace("", "khác").fillna("khác")
    for c, ten in (("pe", "P/E so TV nhóm"), ("pb", "P/B so TV nhóm"), ("roe", "ROE − TV nhóm")):
        s = pd.to_numeric(e[c], errors="coerce")
        s = s.where(s > 0) if c != "roe" else s
        tv_nhom = s.groupby(nhom).transform("median")
        dem = s.groupby(nhom).transform("count")
        tv = tv_nhom.where(dem >= ch.SO_MA_TOI_THIEU_SO_SANH_NHOM, s.median())
        e[ten] = (s / tv) if c != "roe" else (s - tv)
        e[f"TV {c.upper()} dùng so sánh"] = tv
    dem_pe = pd.to_numeric(e["pe"], errors="coerce").where(lambda x: x > 0).groupby(nhom).transform("count")
    e["Cơ sở so sánh"] = np.where(dem_pe >= ch.SO_MA_TOI_THIEU_SO_SANH_NHOM, "nhóm " + nhom, "toàn bộ mã quét")
    return e


def danh_gia_sau_loc(ds_m, b, von_trieu, rui_ro_pct):
    """Chạy B2–B6 cho mọi mã trong bảng b (đã xếp theo kết quả lọc)."""
    rows = []
    for _, r in b.iterrows():
        m = dict(ds_m[r["Mã"]])
        kh = ke_hoach_giao_dich(m, von_trieu, rui_ro_pct)
        m["kc_cat_lo"] = kh["kc_cat_lo"]
        tc = cham_tru_cot(m)
        tong = diem_tong(tc)
        nang, nhe = co_do(m, kh)
        dat_loc = r["Đạt lọc"] in ("✔", "◐")
        gan = (not dat_loc) and r["Thiếu"] != "" and r["Thiếu"].count(";") == 0
        if "nhom_cl" in kh:          # chiến lược thị trường đã xét xu hướng/thời điểm → cờ kỹ thuật chỉ là lưu ý
            ky_thuat = [x for x in nang if x.startswith(("Dưới SuperTrend", "Đã thủng hỗ trợ"))]
            nang = [x for x in nang if x not in ky_thuat]
            nhe = ky_thuat + nhe
        hd = (xep_loai_theo_chien_luoc(kh.get("nhom_cl"), dat_loc, gan, nang) if "nhom_cl" in kh
              else xep_loai_hanh_dong(dat_loc, gan, tong, kh["rr_kh"], nang, nhe))
        rows.append({"Mã": r["Mã"], "Nhóm": m.get("nhom", ""), "Sàn": m.get("san", ""), "Đạt lọc": r["Đạt lọc"],
                     "Điểm lọc %": r["Điểm %"], **tc, "Điểm tổng": tong,
                     "Hành động": hd,
                     "Giá": m["gia"], **kh,
                     "Cờ đỏ (nặng)": "; ".join(nang), "Lưu ý (nhẹ)": "; ".join(nhe),
                     "pe": m.get("pe"), "pb": m.get("pb"), "roe": m.get("roe"),
                     "Thiếu tiêu chí lọc": r["Thiếu"], "SuperTrend": m.get("st"), "RSI": m.get("rsi"),
                     "Ghi chú DN": m.get("ghi_chu", "")})
    e = so_sanh_trong_nhom(pd.DataFrame(rows))
    e["_t"] = e["Hành động"].map({k: i for i, k in enumerate(THU_TU_HANH_DONG)})
    return e.sort_values(["_t", "Điểm tổng"], ascending=[True, False]).drop(columns="_t").reset_index(drop=True)
