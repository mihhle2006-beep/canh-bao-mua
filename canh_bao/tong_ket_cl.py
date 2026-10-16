# -*- coding: utf-8 -*-
"""
TỔNG KẾT 15:20 THEO CHIẾN LƯỢC THỊ TRƯỜNG – tin Telegram GỌN, chi tiết nằm trong file Excel.

  📊 thị trường & CL đang áp dụng
  🟢 MUA MỚI / ✅ VÀO NHƯ LỆNH MỚI / 🟡 VÀO ½   mã | vùng mua | mục tiêu 1R → 3R | cắt lỗ | đạt điểm mua
                    (Quỹ B 10/2026: ✅ = vào trễ ở giá ≤ giá vào hệ thống + ½R; không còn nhóm 🟡)
  ⏳ CHỜ ĐIỀU CHỈNH   mã + vùng chờ           ⛔ KHÔNG VÀO   hệ thống đang lỗ / sắp bán
  💼 ĐANG GIỮ (danh mục thật – tin riêng tư)  lãi/lỗ theo giá vốn · cắt lỗ hệ thoát · hành động · mốc tiếp ·
                                              ➕ mua thêm khi đủ điều kiện (luật nhồi lệnh đã backtest)
Danh sách mua (công khai) được lưu vào trang_thai_chien_luoc.json → cảnh báo 15 phút phiên tới chỉ quét đúng các mã
này, đúng vùng giá này (canh_bao/diem_vao.py).
"""
import json
import math

import numpy as np
import pandas as pd

from . import cau_hinh as C

NHOM_MUA = ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA")
TIEU_DE = {"MUA_MOI": "🟢 MUA MỚI", "VAO_NHU_MOI": "✅ VÀO NHƯ LỆNH MỚI", "VAO_NUA": "🟡 VÀO ½ KHỐI LƯỢNG",
           "CHO": "⏳ CHỜ ĐIỀU CHỈNH", "DUOI_VON": "⛔ KHÔNG VÀO – hệ thống đang lỗ", "BAN": "⛔ KHÔNG VÀO – hệ thống sắp bán",
           "NGOAI_TOP": "⛔ KHÔNG VÀO – ngoài top GTGD / RS 3T quá nóng"}
KHUYEN_NGHI = {"MUA_MOI": "MUA – TÍN HIỆU MỚI", "VAO_NHU_MOI": "MUA – VÀO NHƯ LỆNH MỚI", "VAO_NUA": "MUA TỪNG PHẦN",
               "CHO": "CHỜ ĐIỀU CHỈNH", "DUOI_VON": "CHỜ – HỆ THỐNG ĐANG LỖ", "BAN": "KHÔNG MUA – HỆ THỐNG ĐANG BÁN",
               "NGOAI_TOP": "KHÔNG MUA – NGOÀI TOP GTGD / RS 3T QUÁ NÓNG"}


def _f(x, le=2):
    return "–" if x is None or x != x else f"{x:,.{le}f}"


def _so(x):
    try:
        x = float(x)
        return x if x == x else np.nan
    except (TypeError, ValueError):
        return np.nan


def _ngay(x):
    try:
        return pd.Timestamp(x) if x is not None and x == x and str(x) else None
    except (ValueError, TypeError):
        return None


# ------------------------------------------------------------------ 1 dòng khuyến nghị
def muc_gia(r, atr=None):
    """Cắt lỗ, R, mục tiêu tạm thời 1R / 3R theo giá khuyến nghị (= giá đóng cửa). MUA MỚI: cắt lỗ chuẩn theo ATR."""
    g, cl = _so(r.get("Giá đóng cửa")), _so(r.get("Cắt lỗ"))
    if not (g == g and cl == cl and cl < g):
        return {"cl": cl, "R": np.nan, "mt1": np.nan, "mt3": np.nan}
    R = g - cl
    return {"cl": cl, "R": R, "mt1": g + R, "mt3": g + 3 * R}


def dat_diem_mua(r, ngay_du_lieu=None, di_ngang=False):
    """Lý do mua ngắn gọn (khớp tiêu chí chiến lược A0 / B; thị trường đi ngang: A0 cũng đòi MACD tuần)."""
    nhom, tp = r.get("Nhóm"), str(r.get("Thành phần", ""))
    loc = " + MACD tuần > Signal" if (tp.startswith("B") or (di_ngang and nhom == "MUA_MOI")) else ""
    if nhom == "MUA_MOI":
        ng = _ngay(ngay_du_lieu)
        return f"MACD ngày cắt lên{loc}" + (f" {ng:%d/%m}" if ng is not None else "")
    vao = _ngay(r.get("HT mua ngày"))
    lai = _so(r.get("Lãi HT (R)"))
    return (f"tín hiệu MACD{loc}, HT vào {vao:%d/%m}" if vao is not None else f"tín hiệu MACD{loc}") + \
        (f" · đang {lai:+.1f}R" if lai == lai else "")


def ds_khuyen_nghi(ra):
    """Bảng hành động của ra → list dict đã chuẩn hoá (cả nhóm chờ / không vào)."""
    hd = ra.get("hanh_dong")
    if hd is None or not len(hd):
        return []
    ngay = ra["doc"].get("ngay")
    out = []
    for _, r in hd.iterrows():
        m = muc_gia(r)
        out.append({"ma": r["Mã"], "nhom": r["Nhóm"], "tp": str(r.get("Thành phần", "")),
                    "gia": _so(r.get("Giá đóng cửa")), "tu": _so(r.get("Vùng mua từ")),
                    "den": _so(r.get("Vùng mua đến")), "cl": m["cl"], "R": m["R"], "mt1": m["mt1"], "mt3": m["mt3"],
                    "rui_ro": _so(r.get("Rủi ro %")), "lai_ht": _so(r.get("Lãi HT (R)")),
                    "ly_do": dat_diem_mua(r, ngay, bool((ra.get("di_ngang") or {}).get("dang"))),
                    "khoi_luong": r.get("Khối lượng", ""),
                    "hieu_luc": _ngay(r.get("Hiệu lực")), "vo_hieu": r.get("Vô hiệu khi", ""),
                    "atr": _so((ra.get("atr") or {}).get(r["Mã"])),
                    "uu_tien": _so(r.get("Ưu tiên")), "diem_ut": _so(r.get("Điểm ưu tiên"))})
        k_ = out[-1]
        k_["he_so_kl"], k_["atr_pct"] = he_so_kl(k_["gia"], k_["atr"], k_["nhom"] == "VAO_NUA")
        nh = ra.get("nhiet") or {}
        k_["nhiet"], k_["he_so_nhiet"] = nh.get("diem"), float(nh.get("he_so", 1.0))
        lq = _loc_quy(k_["ma"], ra.get("vni_df")) if k_["nhom"] in NHOM_MUA else None
        if lq:                                      # Quỹ B 10/2026: top 100 GTGD · RS 3T nóng · ĐẮT ½ · nhiệt dài hạn ½
            k_["he_so_quy"], k_["loc_quy"] = lq["he_so"], "; ".join(lq["ly_do"])
            k_["he_so_vni"] = lq.get("he_so_vni", 1.0)        # gia_lap: × trần tổng rủi ro mở
            if "he_so_ma" in lq:                              # in tin: phần riêng của mã (nhiệt dài hạn ở dòng 🌡)
                k_["he_so_quy_ma"], k_["loc_quy_ma"] = lq["he_so_ma"], "; ".join(lq["ly_do_ma"])
            if lq["bo"]:
                k_["nhom"] = "NGOAI_TOP"
    # xếp hạng ưu tiên lại CHỈ trong các mã còn mua (mã ngoài top GTGD bị loại không giữ chỗ ★)
    mua = sorted((k for k in out if k["nhom"] in NHOM_MUA and k["uu_tien"] == k["uu_tien"]), key=lambda k: k["uu_tien"])
    for i, k in enumerate(xep_sao_theo_nganh(mua), 1):
        k["uu_tien"] = float(i)
    return out


def xep_sao_theo_nganh(mua, so_sao=None, toi_da=None):
    """★ tối đa QUY_TOI_DA_MOI_NGANH mã cùng ngành (ptcp/nganh.py): mã thứ 3 trở đi của 1 ngành nhường chỗ ★ cho mã
    ngành khác, xuống sau các mã ★ (vẫn giữ thứ tự ưu tiên). → list đã xếp lại."""
    so_sao = getattr(C, "SO_MA_MOI_TUAN", 4) if so_sao is None else so_sao
    try:
        from ptcp import cau_hinh as P
        from ptcp.loc_quy_b import nganh_cua
        toi_da = getattr(P, "QUY_TOI_DA_MOI_NGANH", None) if toi_da is None else toi_da
    except ImportError:                             # ptcp cũ
        return list(mua)
    if not toi_da:
        return list(mua)
    sao, dem = [], {}
    for k in mua:
        ng = nganh_cua(k["ma"])
        if len(sao) < so_sao and (ng is None or dem.get(ng, 0) < toi_da):
            sao.append(k)
            if ng:
                dem[ng] = dem.get(ng, 0) + 1
    return sao + [k for k in mua if k not in sao]


def _loc_quy(ma, vni):
    """ptcp.loc_quy_b.he_so (ptcp cũ / lỗi → None: không lọc)."""
    try:
        from ptcp.loc_quy_b import he_so
        return he_so(ma, vni)
    except Exception:                               # noqa: BLE001
        return None


def dong_nhiet(nh, rr=None):
    """Dòng 🌡 NHIỆT THỊ TRƯỜNG (công khai – chỉ dữ liệu thị trường), 2 phần nhân với nhau: DÀI HẠN (VN-Index Tăng ½ /
    Giảm ×1,5) · NGẮN HẠN (6 chỉ báo) → rủi ro/lệnh mới sau cả hai hệ số."""
    if not nh:
        return None
    rr = getattr(C, "RUI_RO_MOI_LENH_PCT", 0.75) if rr is None else rr
    bat = [c["ten"] for c in nh.get("chi_bao", []) if c.get("dat")]
    hs = float(nh.get("he_so", 1.0))
    dai = nh.get("dai_han") or {}
    hd = float(dai.get("he_so", 1.0)) if dai else 1.0
    muc = "NÓNG" if nh["diem"] >= 5 else "ấm" if nh["diem"] >= 3 else "nguội"
    dong = [f"🌡 Nhiệt thị trường → rủi ro/lệnh mới {rr:g}% × {hd:g} × {hs:g} = {rr * hd * hs:.2f}% vốn"]
    if dai:
        tt = dai.get("trang_thai") or ("Tăng" if dai.get("tang") else "Ngang")
        mo_ta = {"Tăng": "Tăng (trên MA200 & MA200 dốc lên)", "Giảm": "Giảm (dưới MA200 & MA200 dốc xuống)"}.get(
            tt, "đi ngang (chưa Tăng / chưa Giảm so với MA200)")
        dong.append(f"   • Dài hạn: VN-Index {mo_ta} → ×{hd:g}"
                    + (" – cả trần rủi ro mở (tín hiệu muộn trong sóng tăng dài lãi kém)" if hd < 1 else
                       " – cả trần rủi ro mở (tín hiệu lúc VN-Index Giảm lãi tốt nhất)" if hd > 1 else ""))
    dong.append(f"   • Ngắn hạn: {nh['diem']}/{nh.get('so_chi_bao', 6)} ({muc}) → ×{hs:g}"
                + (" – mua nhỏ lại (tín hiệu lúc thị trường nóng lãi kém hơn)" if hs < 1 else "")
                + (f"\n     đang bật: {', '.join(bat)}" if bat else ""))
    dong.append("   Danh mục của bạn đang sụt so với đỉnh → giảm thêm: 3–6% ×¾ · 6–10% ×½ · > 10% ×⅓")
    return "\n".join(dong)


def gia_lo(tu, den):
    """Giá đặt lệnh LO cho phiên tới = ⅓ dưới vùng (như ptcp.diem_vao_15p), làm tròn XUỐNG theo bước giá."""
    from ptcp.chien_luoc import lam_tron_buoc
    return lam_tron_buoc(tu + (den - tu) / 3, False)


def dong_mua(k, dang_giu=(), bien_the=None):
    ut = k.get("uu_tien")
    sao = "★ " if ut == ut and ut is not None and ut <= getattr(C, "SO_MA_MOI_TUAN", 2) else ""
    hs = k.get("he_so_kl")
    kl = f" | KL ×{hs:.2f}" if (getattr(C, "KL_THEO_BIEN_DONG", False) and hs is not None and hs == hs
                                and hs < 0.999) else ""
    hq = k.get("he_so_quy_ma", k.get("he_so_quy"))    # chỉ phần riêng của mã (ĐẮT…) – nhiệt in ở dòng 🌡
    if hq is not None and hq < 0.999:
        kl += f" | KL ×{hq:g} ({k.get('loc_quy_ma', k.get('loc_quy', ''))})"
    if bien_the and bien_the.startswith("LO") and k.get("tu") and k.get("den"):
        kl = f" | đặt LO {_f(gia_lo(k['tu'], k['den']))}" + kl
    return (f"{sao}{k['ma']} | {_f(k['tu'])}–{_f(k['den'])} | MT {_f(k['mt1'])} → {_f(k['mt3'])} | CL {_f(k['cl'])}{kl} "
            f"| {k['ly_do']}" + (" · 💼 đang giữ → xem mua thêm" if k["ma"] in dang_giu else ""))


# ------------------------------------------------------------------ danh sách mua cho cảnh báo 15 phút
def luu_ds_mua(ra, bay_gio, path=None):
    """Ghi danh sách nhóm mua (công khai) + phiên hiệu lực vào file trạng thái chiến lược."""
    path = path or C.FILE_TRANG_THAI_CL
    try:
        with open(path, encoding="utf-8") as f:
            cu = json.load(f)
    except (OSError, ValueError):
        cu = {}
    ds = [k for k in ds_khuyen_nghi(ra) if k["nhom"] in NHOM_MUA]
    hl = next((k["hieu_luc"] for k in ds if k["hieu_luc"] is not None), None)
    cu["ds_mua"] = {"hieu_luc": f"{hl:%Y-%m-%d}" if hl is not None else None,
                    "ngay_du_lieu": f"{pd.Timestamp(ra['doc']['ngay']):%Y-%m-%d}",
                    "cl": int(ra["cl"]), "tao_luc": f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}",
                    "ma": [{k_: (None if isinstance(v, float) and v != v else
                                 (f"{v:%Y-%m-%d}" if isinstance(v, pd.Timestamp) else v))
                            for k_, v in k.items()} for k in ds]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cu, f, ensure_ascii=False, indent=1)
    return len(ds)


# ------------------------------------------------------------------ mua thêm (luật nhồi lệnh kiểu B đã backtest)
def mua_them(vt, dn, kb, bay_gio=None):
    """
    → {"du": bool, "ly_do", "tu", "den", "so_cp", "cl", "gia_von_moi"} cho 1 vị thế thật.
    Đủ khi: lãi ≥ NGUONG_KHUNG_TUAN_R (tầng tuần, Quỹ B 2R) · đóng cửa hôm nay lập đỉnh đóng cửa mới kể từ ngày mua · cách lần mua gần nhất
    ≥ MUA_THEM_GIAN_CACH phiên · số lần mua thêm < MUA_THEM_TOI_DA · cắt lỗ hiện tại ≥ giá vốn BQ mới + phí.
    """
    from .vi_the import _ngay as ngay_vt, _phien_da_dong
    out = {"du": False, "ly_do": ""}
    if not kb or not kb.get("he_thoat") or dn is None or not vt.get("gia_von"):
        return out
    d = _phien_da_dong(dn, bay_gio)
    c = d.close
    gv, so_cp, lo = vt["gia_von"], vt["so_cp"], kb["cat_lo"]
    R = kb.get("R") or np.nan
    moc3 = gv + C.NGUONG_KHUNG_TUAN_R * R if R == R else np.nan
    if kb.get("tang", 0) < 2:
        out["ly_do"] = f"chưa – cần lãi ≥ {C.NGUONG_KHUNG_TUAN_R:g}R ({_f(moc3)}) rồi đóng cửa lập đỉnh mới"
        return out
    if int(vt.get("so_lan_mua_them") or 0) >= C.MUA_THEM_TOI_DA:
        out["ly_do"] = f"đã mua thêm {C.MUA_THEM_TOI_DA} lần – đủ"
        return out
    moc = ngay_vt(vt.get("ngay_mua_them")) or ngay_vt(vt.get("ngay_mua"))
    sau = c[c.index >= moc] if moc is not None else c
    if len(sau) < 2:
        return out
    dinh_truoc = float(sau.iloc[:-1].max())
    so_phien = len(sau) - 1
    if not c.iloc[-1] > dinh_truoc:
        out["ly_do"] = f"chờ đóng cửa > {_f(dinh_truoc)} (đỉnh từ lúc mua)"
        return out
    if so_phien < C.MUA_THEM_GIAN_CACH:
        out["ly_do"] = f"chờ đủ {C.MUA_THEM_GIAN_CACH} phiên từ lần mua gần nhất (mới {so_phien})"
        return out
    try:
        from ptcp.thong_ke import _chi_phi
        phi = _chi_phi() / 100
    except ImportError:
        phi = 0.003
    them = max(1, math.floor(so_cp * C.MUA_THEM_TY_LE))
    gia = float(c.iloc[-1])
    von_moi = (so_cp * gv + them * gia) / (so_cp + them)
    if lo < von_moi * (1 + phi):
        out["ly_do"] = f"chưa – cắt lỗ {_f(lo)} < giá vốn mới {_f(von_moi)} (+ phí): mua thêm sẽ có rủi ro lỗ"
        return out
    try:
        from ptcp.chien_luoc import lam_tron_buoc
        den = lam_tron_buoc(gia * 1.03, False)
    except ImportError:
        den = gia * 1.03
    return {"du": True, "ly_do": f"lãi ≥ {C.NGUONG_KHUNG_TUAN_R:g}R + đóng cửa lập đỉnh mới", "tu": gia, "den": den, "so_cp": them,
            "cl": lo, "gia_von_moi": von_moi}


# ------------------------------------------------------------------ vị thế đang giữ (riêng tư)
def dong_giu(vt, kb, mt):
    """2–3 dòng cho 1 mã đang giữ."""
    from .vi_the import NHAN
    hanh = {"CAT_LO": "BÁN – chạm cắt lỗ", "BAN_TUAN": "BÁN ATO phiên tới – gãy MA10 tuần",
            "HET_HAN": "BÁN – lệnh không chạy", "DOI_CAT_LO": f"GIỮ – dời cắt lỗ lên {_f(kb.get('cat_lo_he_thong'))}",
            "GAN_CAT_LO": "GIỮ – sát cắt lỗ, chuẩn bị bán", "GIU": "GIỮ"}.get(kb["muc"], NHAN.get(kb["muc"], ""))
    r = f" ({kb['lai_R']:+.1f}R)" if kb.get("lai_R") == kb.get("lai_R") and kb.get("lai_R") is not None else ""
    d = [f"{vt['ma']} {_f(kb['gia'])} | vốn {_f(vt.get('gia_von'))} | {kb['lai_lo_pct']:+.1f}%{r} | "
         f"CL {_f(kb['cat_lo'])} | {hanh}"]
    them = []
    if kb.get("he_thoat"):
        if kb.get("tang", 0) >= 2 and (kb.get("nguong_ma10") or kb.get("ma10_tuan")):
            them.append(f"bán ATO thứ Hai nếu đóng cửa thứ Sáu < {_f(kb.get('nguong_ma10') or kb['ma10_tuan'])} "
                        f"(MA10 tuần)")
        elif kb.get("muc_tieu"):
            them.append(f"mốc tiếp {_f(kb['muc_tieu'])}" + (" → CL lên hoà vốn" if kb.get("tang", 0) == 0
                                                            else " → chuyển sang bán theo tuần"))
    if any("T+2" in g for g in kb.get("ghi_chu", [])):
        them.append("CP chưa về (T+2)")
    if them:
        d.append("   " + " · ".join(them))
    if mt and mt.get("du"):
        d.append(f"   ➕ MUA THÊM {mt['so_cp']:,.0f} CP | {_f(mt['tu'])}–{_f(mt['den'])} | CL cả vị thế {_f(mt['cl'])} | "
                 f"{mt['ly_do']}")
    elif mt and mt.get("ly_do"):
        d.append(f"   Mua thêm: {mt['ly_do']}")
    return d


# ------------------------------------------------------------------ tin tổng kết
def dong_su_kien(gia_ma, bay_gio):
    """
    gia_ma {mã: giá đóng cửa} → dòng báo trước GDKHQ trong SO_NGAY_BAO_QUYEN ngày tới (lịch VNDirect).
    Vùng / CL trong tin là giá TRƯỚC GDKHQ – bot 15' tự quy đổi theo tỷ lệ khi tới ngày.
    """
    if not getattr(C, "BAO_SU_KIEN_QUYEN", False) or not gia_ma:
        return []
    try:
        from ptcp.su_kien_quyen import he_so_gia, sap_toi
    except ImportError:
        return []
    out = []
    for ma in sorted(gia_ma):
        try:
            sk = sap_toi(ma, getattr(C, "SO_NGAY_BAO_QUYEN", 10), bay_gio)
        except Exception:                                        # noqa: BLE001 – lịch lỗi không chặn tin
            continue
        for d, x in sk.items():
            f = he_so_gia(x, gia_ma[ma])
            out.append(f"• {ma} GDKHQ {d:%d/%m}: {x['mo_ta']} → giá × {f:.3f}"
                       + (f" (≈ {_f(gia_ma[ma] * f)})" if gia_ma[ma] == gia_ma[ma] and gia_ma[ma] else "")
                       + (f", số CP × {x['he_so_cp']:.2f}" if x["he_so_cp"] != 1 else ""))
    return (["", "📅 SẮP GDKHQ – vùng / CL tự quy đổi theo tỷ lệ khi tới ngày"] + out) if out else []


def tin_tong_ket(ra, bay_gio, giu=None, kq_bt=None):
    """
    ra: chien_luoc_bot.chay_chien_luoc · giu: [(vt, kb, mt)] (None/[] → tin công khai) · kq_bt: ket_qua_backtest.json.
    → (tin đầy đủ, tin công khai) – tin công khai không có gì về danh mục (in ra log được).
    """
    dang_giu = {vt["ma"] for vt, _, _ in (giu or [])}
    day_du = _tin(ra, bay_gio, kq_bt, dang_giu)
    if giu:
        day_du += ["", f"💼 ĐANG GIỮ ({len(giu)})"]
        for vt, kb, mt in giu:
            day_du += dong_giu(vt, kb, mt)
        sk = dong_su_kien({vt["ma"]: (kb or {}).get("gia", np.nan) for vt, kb, _ in giu}, bay_gio)
        day_du += [x.replace("vùng / CL tự quy đổi theo tỷ lệ khi tới ngày", "mã đang giữ: cắt lỗ / giá vốn đổi theo "
                             "tỷ lệ – danh_muc tự quy đổi") for x in sk]
    if C.GUI_EXCEL:
        day_du.append("📎 Chi tiết, lịch sử & backtest: file Excel đính kèm")
    return "\n".join(day_du).rstrip(), "\n".join(_tin(ra, bay_gio, kq_bt, set())).rstrip()


def _tin(ra, bay_gio, kq_bt, dang_giu):
    d = ra["doc"]
    try:
        bt = cach_vao(kq_bt)[0]
    except ImportError:
        bt = None
    ks = ds_khuyen_nghi(ra)
    n = d["so_chi_bao"]
    w = ra["ty_trong"]
    chia = " + ".join(f"{ {'VNI': 'VN-Index', 'TIEN': 'tiền nhàn rỗi'}.get(k, k)} {w[k] * 100:.0f}%"
                      for k in ("A0", "B", "TIEN", "VNI")
                      if w.get(k, 0) > 0)
    hl = next((k["hieu_luc"] for k in ks if k["hieu_luc"] is not None), None)
    dong = [f"📊 TỔNG KẾT {pd.Timestamp(bay_gio):%d/%m} · VN-Index {_f(ra['vni'])} · {d['diem']}/{n} điểm · "
            f"CL{ra['cl']} ({chia})"]
    if d.get("dieu_kien_doi"):
        dong.append(f"↪ {d['dieu_kien_doi']}")
    ng = ra.get("di_ngang")
    if ng:
        dong.append(f"↔ VN-Index ĐI NGANG (biên {ng['phien']} phiên {ng['bien']:.1f}% < {ng['nguong']:g}%): tín hiệu mới "
                    f"chỉ lấy khi MACD tuần > Signal" if ng["dang"] else
                    f"↗ VN-Index có xu hướng (biên {ng['phien']} phiên {ng['bien']:.1f}% ≥ {ng['nguong']:g}%): "
                    f"lấy mọi tín hiệu MACD ngày")
    dn = dong_nhiet(ra.get("nhiet"))
    if dn:
        dong.append(dn)
    n_max = C.SO_MA_MOI_NHOM
    for nhom in NHOM_MUA:
        x = [k for k in ks if k["nhom"] == nhom]
        if not x:
            continue
        dong += ["", f"{TIEU_DE[nhom]} ({len(x)}) – đặt lệnh phiên {hl:%d/%m}" if hl is not None else
                 f"{TIEU_DE[nhom]} ({len(x)})"]
        x = sorted(x, key=lambda k: (k["uu_tien"] if k.get("uu_tien") == k.get("uu_tien") and k.get("uu_tien")
                                     is not None else 999, k["rui_ro"] if k["rui_ro"] == k["rui_ro"] else 99))
        dong += [dong_mua(k, dang_giu, bt) for k in x[:n_max]]
        if len(x) > n_max:
            dong.append(f"… +{len(x) - n_max} mã (xem Excel)")
    cho = [k for k in ks if k["nhom"] == "CHO"]
    if cho:
        dong += ["", f"{TIEU_DE['CHO']} ({len(cho)}): " + " · ".join(
            (f"{k['ma']} {_f(k['tu'])}–{_f(k['den'])}" if k.get("den") == k.get("den") and k.get("den") is not None
             else f"{k['ma']} chờ tín hiệu mới") for k in cho[:n_max]) + (" …" if len(cho) > n_max else "")]
    ko = [k for k in ks if k["nhom"] in ("DUOI_VON", "BAN")]
    if ko:
        dong.append(f"⛔ KHÔNG VÀO ({len(ko)}): " + ", ".join(k["ma"] for k in ko))
    ngoai = [k for k in ks if k["nhom"] == "NGOAI_TOP"]
    if ngoai:
        dong.append(f"⛔ CÓ TÍN HIỆU NHƯNG BỊ LỌC (ngoài top GTGD / RS 3T quá nóng) – không mua mới ({len(ngoai)}): "
                    + ", ".join(k["ma"] + (" (RS nóng)" if "RS 3T" in str(k.get("loc_quy", "")) else "")
                                for k in ngoai))
    if sum(k["nhom"] in NHOM_MUA for k in ks) > getattr(C, "SO_MA_MOI_TUAN", 2):
        dong += ["", f"★ = {getattr(C, 'SO_MA_MOI_TUAN', 2)} mã nên mua trước (điểm ưu tiên: cắt lỗ sát · lịch sử mã · "
                     f"lập đỉnh 52T; ≤ 2 mã/ngành) – quỹ B chỉ mua tối đa {getattr(C, 'SO_MA_MOI_TUAN', 2)} mã mới/tuần"]
    if not any(k["nhom"] in NHOM_MUA for k in ks):
        dong += ["", "Không có mã nào để mua phiên tới."]
    dong += dong_su_kien({k["ma"]: k["gia"] for k in ks if k["nhom"] in NHOM_MUA + ("CHO",)}, bay_gio)
    dong += ["", "Mua trong vùng; mở cửa > vùng thì bỏ (không đuổi), rơi < vùng trước khi mua thì bỏ. "
                 + (f"KL = {getattr(C, 'RUI_RO_MOI_LENH_PCT', 1.0):g}% vốn ÷ (giá − CL) × hệ số (ATR mục tiêu "
                    f"{C.ATR_MUC_TIEU_PCT:g}%/ngày). " if getattr(C, "KL_THEO_BIEN_DONG", False) else "")
                 + (f"{C.LUAT_QUY}. " if getattr(C, "LUAT_QUY", "") else "")
                 + "MT = mục tiêu tạm thời 1R → 3R (mốc dời cắt lỗ, không phải lệnh bán).",
             _dong_cach_vao(kq_bt)]
    return dong


def cach_vao(kq_bt=None):
    """Cách vào 15' đang dùng: cấu hình cố định, hoặc tốt nhất theo backtest, hoặc mặc định."""
    from ptcp.diem_vao_15p import BIEN_THE, MAC_DINH
    if C.CACH_VAO_15P != "tu_dong" and C.CACH_VAO_15P in BIEN_THE:
        return C.CACH_VAO_15P, "cấu hình"
    b15 = (kq_bt or {}).get("15p") or {}
    top = b15.get("top_gtgd") or {}
    if top.get("tot_nhat") in BIEN_THE:                       # Quỹ B chỉ mua top GTGD → chọn theo đúng rổ đó
        return top["tot_nhat"], f"tốt nhất theo backtest top {top.get('top', 100)} GTGD"
    tot = b15.get("tot_nhat")
    if tot in BIEN_THE:
        return tot, "tốt nhất theo backtest"
    return MAC_DINH, "mặc định – chưa backtest 15'"


def _dong_cach_vao(kq_bt):
    try:
        bt, nguon = cach_vao(kq_bt)
    except ImportError:
        return ""
    s = f"Điểm vào 15' phiên tới: {bt} – {nguon}"
    b15 = (kq_bt or {}).get("15p") or {}
    bang = (b15.get("top_gtgd") or {}).get("bang") if "top" in nguon else b15.get("bang")
    hang = next((h for h in bang or [] if h.get("Biến thể") == bt), None)
    if hang:
        s += f" (backtest {hang['TB/lệnh khớp %']:+.2f}%/lệnh, khớp {hang['Khớp %']:.0f}%)"
    if bt.startswith("LO"):
        s += (". Đặt LO trước giờ mở cửa ở giá 'đặt LO' từng mã (⅓ dưới vùng); không chạm → "
              + ({"": "ATC (chỉ mã ★) nếu đóng cửa còn trong vùng; mã không ★ chỉ mua khi khớp LO", "_VWAP": "ATC chỉ khi giá ≥ VWAP phiên",
                  "_XANH": "ATC chỉ khi giá ≥ giá mở cửa", "_TREN": "ATC chỉ khi giá ở nửa trên biên độ phiên"}
                 .get(bt.partition("+ATC")[2], "ATC") if "+ATC" in bt else "không mua"))
    return s


def doc_ket_qua_backtest(path=None):
    try:
        with open(path or C.FILE_BACKTEST, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ nhật ký khuyến nghị chiến lược (công khai)
def ghi_nhat_ky(ra, path=None):
    """Ghi khuyến nghị nhóm mua & chờ (khi đổi) – chấm theo hệ thoát (ptcp/nhat_ky.cham_he_thoat). Trả số dòng ghi."""
    from ptcp import nhat_ky as nk
    path = path or "lich_su_danh_gia.csv"
    n = 0
    for k in ds_khuyen_nghi(ra):
        if k["nhom"] not in NHOM_MUA + ("CHO",):
            continue
        info = {"cach_cham": nk.HE_THOAT, "chien_luoc": f"CL{ra['cl']}", "diem_tt": ra["doc"]["diem"],
                "nhom_hd": k["nhom"], "vung_tu": k["tu"], "vung_den": k["den"],
                "gia_kn_mua": k["gia"] if k["nhom"] in NHOM_MUA else np.nan, "gia_kn_ban": k["cl"],
                "muc_tieu_2": k["mt3"]}
        n += bool(nk.ghi_khuyen_nghi(k["ma"], ra["doc"]["ngay"], k["gia"], KHUYEN_NGHI[k["nhom"]], k["cl"], k["mt1"],
                                     C.KY_HAN_MUA, "HOSE", loai=C.LOAI_NHAT_KY_CL, path=path, chien_luoc=info))
    return n


# ------------------------------------------------------------------ khối lượng theo biến động
def he_so_kl(gia, atr, nua=False):
    """→ (hệ số khối lượng, ATR % / ngày). hệ số = min(1, ATR mục tiêu ÷ ATR% của mã) × (½ nếu nhóm 🟡)."""
    atr_pct = atr / gia * 100 if gia and atr == atr and atr else np.nan
    hs = 1.0
    if getattr(C, "KL_THEO_BIEN_DONG", False) and atr_pct == atr_pct and atr_pct > 0:
        hs = min(1.0, C.ATR_MUC_TIEU_PCT / atr_pct)
    return hs * (0.5 if nua else 1.0), atr_pct


def dong_khoi_luong(gia, cl, atr, nua=False, von_trieu=None, he_so_nhiet=None):
    """Dòng 'Khối lượng: …' cho tin mua (công thức + hệ số; có VON_TRIEU → số CP làm tròn lô 100).
    he_so_nhiet: hệ số nhiệt thị trường của tin tổng kết (< 1 → rủi ro/lệnh nhân theo)."""
    hs, atr_pct = he_so_kl(gia, atr, nua)
    rr = getattr(C, "RUI_RO_MOI_LENH_PCT", 1.0)
    if he_so_nhiet is not None and he_so_nhiet == he_so_nhiet and he_so_nhiet < 1:
        rr = round(rr * he_so_nhiet, 4)
    ly = []
    if getattr(C, "KL_THEO_BIEN_DONG", False) and atr_pct == atr_pct:
        ly.append(f"ATR {atr_pct:.1f}%/ngày" + (f" > {C.ATR_MUC_TIEU_PCT:g}% → giảm" if atr_pct > C.ATR_MUC_TIEU_PCT
                                                else f" ≤ {C.ATR_MUC_TIEU_PCT:g}% → đủ"))
    if nua:
        ly.append("nhóm 🟡 ½")
    if getattr(C, "KL_THEO_BIEN_DONG", False):
        s = f"Khối lượng: {rr:g}% vốn ÷ (giá mua − cắt lỗ) × {hs:.2f}" + (f" ({', '.join(ly)})" if ly else "")
    else:
        s = (f"Khối lượng: ½ – {rr / 2:g}% vốn ÷ (giá mua − cắt lỗ)" if nua else
             f"Khối lượng: {rr:g}% vốn ÷ (giá mua − cắt lỗ)")
    von = von_trieu if von_trieu is not None else getattr(C, "VON_TRIEU", None)
    if von and gia and cl == cl and cl < gia:
        cp = von * 1e6 * rr / 100 * hs / ((gia - cl) * 1000)
        cp = int(cp // 100 * 100)
        if cp > 0:
            s += f" ≈ {cp:,.0f} CP (≈ {cp * gia / 1000:,.1f} triệu, mất ≈ {cp * (gia - cl) / 1000:,.1f} triệu nếu chạm CL)"
    return s
