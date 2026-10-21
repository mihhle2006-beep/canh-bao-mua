# -*- coding: utf-8 -*-
"""
TỔNG KẾT 15:20 THEO CHIẾN LƯỢC THỊ TRƯỜNG – tin Telegram GỌN, chi tiết nằm trong file Excel.

  📊 thị trường & CL đang áp dụng
  🟢 MUA MỚI / ✅ VÀO NHƯ LỆNH MỚI / 🟡 VÀO ½   mã | vùng mua | mục tiêu 1R → 3R | cắt lỗ | đạt điểm mua
                    (Quỹ B 10/2026: ✅ = vào trễ ở giá ≤ giá vào hệ thống + ½R; không còn nhóm 🟡 · 20/10/2026:
                     vào trễ chỉ đặt lệnh ATC, huỷ nếu chạm cắt lỗ trong phiên – canh_bao/diem_vao.vao_tre_atc)
  ⏳ CHỜ ĐIỀU CHỈNH   mã + vùng chờ           ⛔ KHÔNG VÀO   hệ thống đang lỗ / sắp bán
  💼 ĐANG GIỮ (danh mục thật – tin riêng tư)  lãi/lỗ theo giá vốn · cắt lỗ hệ thoát · hành động · mốc tiếp ·
                                              ➕ mua thêm khi đủ điều kiện (luật nhồi lệnh đã backtest)
Danh sách mua (công khai) được lưu vào trang_thai_chien_luoc.json → cảnh báo 15 phút phiên tới chỉ quét đúng các mã
này, đúng vùng giá này (canh_bao/diem_vao.py).
"""
import json
import math
import re

import numpy as np
import pandas as pd

from . import cau_hinh as C

NHOM_MUA = ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA")
TIEU_DE = {"MUA_MOI": "🟢 MUA MỚI", "VAO_NHU_MOI": "✅ VÀO NHƯ LỆNH MỚI", "VAO_NUA": "🟡 VÀO ½ KHỐI LƯỢNG",
           "CHO": "⏳ CHỜ ĐIỀU CHỈNH", "DUOI_VON": "⛔ KHÔNG VÀO – hệ thống đang lỗ", "BAN": "⛔ KHÔNG VÀO – hệ thống sắp bán",
           "NGOAI_TOP": "⛔ KHÔNG VÀO – ngoài top GTGD / RS 3T quá nóng / biến động mạnh"}
KHUYEN_NGHI = {"MUA_MOI": "MUA – TÍN HIỆU MỚI", "VAO_NHU_MOI": "MUA – VÀO NHƯ LỆNH MỚI", "VAO_NUA": "MUA TỪNG PHẦN",
               "CHO": "CHỜ ĐIỀU CHỈNH", "DUOI_VON": "CHỜ – HỆ THỐNG ĐANG LỖ", "BAN": "KHÔNG MUA – HỆ THỐNG ĐANG BÁN",
               "NGOAI_TOP": "KHÔNG MUA – NGOÀI TOP GTGD / RS 3T QUÁ NÓNG / BIẾN ĐỘNG MẠNH"}


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
        if lq:                  # Quỹ B: top 100 GTGD · RS 3T nóng · biến động top 30% · ĐẮT ½ · nhiệt dài hạn ½
            k_["he_so_quy"], k_["loc_quy"] = lq["he_so"], "; ".join(lq["ly_do"])
            k_["manh_b"] = bool(lq.get("manh_b"))            # tín hiệu MẠNH B → được dùng suất dự phòng (mã thứ 9)
            k_["dau_hieu_manh"] = ", ".join(lq.get("dau_hieu_manh") or [])
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


def _quy(ten, mac_dinh):
    """Tham số Quỹ B của ptcp/cau_hinh.py (ptcp cũ → mặc định)."""
    try:
        from ptcp import cau_hinh as P
        return getattr(P, ten, mac_dinh)
    except ImportError:
        return mac_dinh


def _loc_quy(ma, vni):
    """ptcp.loc_quy_b.he_so (ptcp cũ / lỗi → None: không lọc)."""
    try:
        from ptcp.loc_quy_b import he_so
        return he_so(ma, vni)
    except Exception:                               # noqa: BLE001
        return None


def dong_nhiet(nh, rr=None):
    """Dòng 🌡 NHIỆT THỊ TRƯỜNG (công khai – chỉ dữ liệu thị trường), 2 phần nhân với nhau: DÀI HẠN (VN-Index Tăng nóng ½ /
    Tăng nhẹ ×1 / Giảm ×1,5; MA50 dốc mạnh ½) · NGẮN HẠN (6 chỉ báo) → rủi ro/lệnh mới sau cả hai hệ số."""
    if not nh:
        return None
    rr = getattr(C, "RUI_RO_MOI_LENH_PCT", 0.75) if rr is None else rr
    bat = [c["ten"] for c in nh.get("chi_bao", []) if c.get("dat")]
    hs = float(nh.get("he_so", 1.0))
    dai = nh.get("dai_han") or {}
    hd = float(dai.get("he_so", 1.0)) if dai else 1.0
    muc = "NÓNG" if nh["diem"] >= 5 else "ấm" if nh["diem"] >= 3 else "nguội"
    dong = [f"🌡 Rủi ro/lệnh mới {rr:g}% × {hd:g} × {hs:g} = {rr * hd * hs:.2f}% vốn"]
    if dai:
        tt = dai.get("trang_thai") or ("Tăng" if dai.get("tang") else "Ngang")
        htt = float(dai.get("he_so_tt", hd))
        so = (f" (MA200 {dai['cach_ma200']:+.1f}%, 3T {dai['lai_3t']:+.1f}%)"
              if dai.get("cach_ma200") is not None and dai.get("lai_3t") is not None else "")
        mo_ta = {"Tăng": ("Tăng nóng" if dai.get("nong") else "Tăng nhẹ") + so, "Giảm": "Giảm"}.get(tt, "đi ngang")
        dong.append(f"   • Dài hạn: VNI {mo_ta} ×{htt:g}")
        if dai.get("doc_manh"):
            dong.append(f"   • MA50 VNI dốc {dai.get('doc_ma50', 0):+.1f}%/10 phiên ×{float(dai.get('he_so_doc', 1.0)):g}")
    dong.append(f"   • Ngắn hạn: {nh['diem']}/{nh.get('so_chi_bao', 6)} ({muc}) ×{hs:g}"
                + (f" – {', '.join(bat)}" if bat else ""))
    dong.append("   • Danh mục sụt từ đỉnh: 3–6% ×¾ · 6–10% ×½ · >10% ×⅓ (tự nhân)")
    return "\n".join(dong)


def gia_lo(tu, den):
    """Giá đặt lệnh LO cho phiên tới = ⅓ dưới vùng (như ptcp.diem_vao_15p), làm tròn XUỐNG theo bước giá."""
    from ptcp.chien_luoc import lam_tron_buoc
    return lam_tron_buoc(tu + (den - tu) / 3, False)


def _tran_ma_pct():
    """% NAV tối đa / mã (ptcp QUY_TRAN_MA_PCT, mặc định 20)."""
    try:
        from ptcp import cau_hinh as P
        return float(getattr(P, "QUY_TRAN_MA_PCT", 20.0))
    except ImportError:
        return 20.0


def _hs(x):
    return float(x) if x is not None and x == x else 1.0


def von_lenh(k):
    """VỐN CHO LỆNH đã nhân sẵn mọi hệ số (người đọc không phải tự tính): rủi ro % NAV = RUI_RO_MOI_LENH_PCT × nhiệt ngắn
    hạn × lọc Quỹ B (nhiệt dài hạn VN-Index · ĐẮT …) × khối lượng (nhóm 🟡 ½ / ATR) → tỷ trọng mua = rủi ro % ÷ khoảng
    cách cắt lỗ %, ≤ trần %/mã. → {"rr", "ty_trong", "he_so": [(nhãn, hệ số)]} (ty_trong NaN khi thiếu cắt lỗ)."""
    rr0 = float(getattr(C, "RUI_RO_MOI_LENH_PCT", 0.75))
    hn, hq, hk = _hs(k.get("he_so_nhiet")), _hs(k.get("he_so_quy")), _hs(k.get("he_so_kl"))
    hv = _hs(k.get("he_so_vni")) if "he_so_quy_ma" in k else 1.0
    hm = _hs(k.get("he_so_quy_ma")) if "he_so_quy_ma" in k else hq
    ds = []
    if hn != 1:
        ds.append(("nhiệt", hn))
    if hv != 1:
        ds.append(("VNI", hv))
    if hm != 1:                                      # nhãn ngắn: "ĐẮT (định giá −32%) ×0.5" → "ĐẮT"
        ly = [re.sub(r"\s*(\(.*|×\s*[\d.,]+)$", "", x).strip() for x in
              str(k.get("loc_quy_ma", k.get("loc_quy", "")) or "lọc").split(";")]
        ds.append((", ".join(x for x in ly if x) or "lọc", hm))
    if hk != 1:
        ds.append(("🟡" if k.get("nhom") == "VAO_NUA" else "khối lượng", hk))
    rr = rr0 * hn * hq * hk
    R = _so(k.get("rui_ro"))
    if not (R == R and R > 0):
        den, cl = _so(k.get("den")), _so(k.get("cl"))
        R = (den - cl) / den * 100 if den == den and cl == cl and den > cl > 0 else np.nan
    tt = min(rr / R * 100, _tran_ma_pct()) if R == R and R > 0 else np.nan
    return {"rr": rr, "ty_trong": tt, "he_so": ds, "rr0": rr0}


def chu_von_lenh(k):
    """'💰 ≤5.4% NAV (VNI ×0.5 · ĐẮT ×0.5)' – tỷ trọng mua tối đa, đã nhân mọi hệ số (rủi ro % ÷ khoảng cắt lỗ)."""
    v = von_lenh(k)
    if v["ty_trong"] != v["ty_trong"]:
        return ""
    ct = " · ".join(f"{t} ×{h:g}" for t, h in v["he_so"])
    return f"💰 ≤{v['ty_trong']:.1f}% NAV" + (f" ({ct})" if ct else "")


DK_ATC = {"_VWAP": " và giá ≥ VWAP phiên", "_XANH": " và giá ≥ giá mở cửa", "_TREN": " và giá ở nửa trên biên độ phiên"}
MO_TA_15P = "MACD 15' cắt lên hoặc phá đỉnh 20 nến + khối lượng ≥ 1,5× · giá ≥ VWAP · RSI 15' ≤ 75"


def mo_ta_cach_vao(bien_the):
    """Dòng giải thích cách vào chung cho tin tổng kết (tiêu chí 15' in 1 lần, từng mã chỉ ghi giá)."""
    if not bien_the:
        return None
    goc, atc, dk = bien_the.partition("+ATC")
    if goc.startswith("15P"):
        tc = MO_TA_15P + (" · MACD giờ > Signal" if "GIO" in goc else "")
        mo = f"chờ tin 🟢 MUA NGAY 15' (đủ: {tc}) rồi mua giá thị trường"
    elif goc == "LO":
        mo = "đặt LO ở ⅓ dưới vùng mua từ đầu phiên"
    elif goc == "VWAP":
        mo = "mua khi nến 15' (từ 9:30) đóng cửa ≥ VWAP, trong vùng"
    else:
        mo = "mua ATO nếu giá mở cửa trong vùng"
    if atc:
        mo += f"; {C.GIO_ATC} chưa mua được → ATC nếu giá còn trong vùng{DK_ATC.get(dk, '')}"
    return f"🎯 Cách vào ({bien_the}): {mo}. Mở cửa > vùng → bỏ (không đuổi); giá thủng vùng trước khi mua → bỏ."


def cach_vao_ma(k, bien_the):
    """Cách vào CỦA TỪNG MÃ (giá cụ thể) – các dòng "Đặt LO: …" / "Cách vào: …" (+ ATC, Bỏ nếu) dưới mã trong tin
    tổng kết (đã xuống dòng + thụt lề như các dòng khác của mã)."""
    tu, den = k.get("tu"), k.get("den")
    if not bien_the or not (tu == tu and den == den) or tu is None or den is None:
        return ""
    goc, atc, dk = bien_the.partition("+ATC")
    if goc.startswith("15P"):
        x = f"Cách vào: chờ 🟢 15' khi giá {_f(tu)}–{_f(den)}"
    elif goc == "LO":
        x = f"Đặt LO: {_f(gia_lo(tu, den))}"
    elif goc == "VWAP":
        x = f"Cách vào: nến 15' đóng ≥ VWAP, giá {_f(tu)}–{_f(den)}"
    else:
        x = f"Cách vào: ATO nếu mở cửa {_f(tu)}–{_f(den)}"
    if atc:
        x += f"\n   ATC: {C.GIO_ATC} chưa mua → ATC nếu {_f(tu)}–{_f(den)}{DK_ATC.get(dk, '')}"
    return x + f"\n   Bỏ nếu: mở cửa > {_f(den)}"


def canh_bao_nganh(ma, dang_giu):
    """'⚠ đã giữ 2 mã ngành X (…) – không mua thêm mã ngành này' khi danh mục đang giữ đủ QUY_TOI_DA_MOI_NGANH mã cùng
    ngành với mã tín hiệu (ptcp/nganh.py); không có / ptcp cũ → ''. Chỉ dùng ở bản tin RIÊNG (có danh mục)."""
    if not dang_giu or ma in dang_giu:
        return ""
    try:
        from ptcp.loc_quy_b import nganh_cua
    except ImportError:
        return ""
    toi_da, ng = _quy("QUY_TOI_DA_MOI_NGANH", 2), nganh_cua(ma)
    cung = sorted(m for m in dang_giu if ng and nganh_cua(m) == ng)
    if not toi_da or len(cung) < toi_da:
        return ""
    return f"⚠ đã giữ {len(cung)} mã ngành {ng} ({', '.join(cung)}) – không mua thêm (tối đa {toi_da}/ngành)"


def dong_mua(k, dang_giu=(), bien_the=None):
    """Mã trong nhóm mua – mỗi mục 1 dòng (người dùng 19/10/2026: đọc trên điện thoại):
    ★ FPT 100.00 | MUA MỚI / Vùng mua / Đặt LO (cách vào) / Mục tiêu 1R → 3R / Cắt lỗ (% so giá) / Khối lượng / Lý do."""
    ut = k.get("uu_tien")
    sao = "★ " if ut == ut and ut is not None and ut <= getattr(C, "SO_MA_MOI_TUAN", 2) else ""
    manh = "💪" if k.get("manh_b") else ""
    g, cl = _so(k.get("gia")), _so(k.get("cl"))
    nhom = TIEU_DE.get(k.get("nhom"), str(k.get("nhom") or "")).split(" ", 1)[-1]     # "🟢 MUA MỚI" → "MUA MỚI"
    vao = cach_vao_ma(k, bien_the)                      # giá LO / ATC / chờ 15' của riêng mã này
    von, nganh = chu_von_lenh(k), canh_bao_nganh(k["ma"], dang_giu)
    d = [f"{sao}{k['ma']}{manh}" + (f" {_f(g)}" if g == g else "") + (f" | {nhom}" if nhom else ""),
         f"   Vùng mua: {_f(k['tu'])} – {_f(k['den'])}"]
    d += [f"   {vao}"] if vao else []
    d += [f"   Mục tiêu: 1R {_f(k['mt1'])} → 3R {_f(k['mt3'])}",
          f"   Cắt lỗ: {_f(cl)}" + (f" ({(cl / g - 1) * 100:+.1f}%)" if g == g and cl == cl and g else "")]
    d += [f"   Khối lượng: {von}"] if von else []
    d.append(f"   Lý do: {k['ly_do']}")
    d += ["   💼 đang giữ → xem mua thêm"] if k["ma"] in dang_giu else []
    d += [f"   {nganh}"] if nganh else []
    return "\n".join(d)


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
    if cu["ds_mua"]["hieu_luc"]:                  # lưu theo phiên để chạy lại phiên cũ (python chay.py --gio …)
        ls = {**(cu.get("lich_su_ds_mua") or {}), cu["ds_mua"]["hieu_luc"]: cu["ds_mua"]}
        cu["lich_su_ds_mua"] = dict(sorted(ls.items())[-30:])
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
    """Mã đang giữ – mỗi mục 1 dòng: tiêu đề + hành động / Đã vào lệnh / Cắt lỗ / Mục tiêu tiếp / ➕ mua thêm."""
    from .vi_the import NHAN, dong_da_vao
    hanh = {"CAT_LO": "BÁN – chạm cắt lỗ", "BAN_TUAN": "BÁN ATO phiên tới – gãy MA10 tuần",
            "HET_HAN": "BÁN – lệnh không chạy", "DOI_CAT_LO": f"GIỮ – dời cắt lỗ lên {_f(kb.get('cat_lo_he_thong'))}",
            "GAN_CAT_LO": "GIỮ – sát cắt lỗ, chuẩn bị bán", "GIU": "GIỮ"}.get(kb["muc"], NHAN.get(kb["muc"], ""))
    g, lo = _so(kb.get("gia")), _so(kb.get("cat_lo"))
    d = [f"{vt['ma']} {_f(g)} | {hanh}",
         "   " + dong_da_vao(vt.get("ngay_mua"), vt.get("gia_von"), kb.get("lai_lo_pct"), kb.get("lai_R")),
         f"   Cắt lỗ: {_f(lo)}" + (f" ({(lo / g - 1) * 100:+.1f}%)" if g == g and lo == lo and g else "")]
    if kb.get("he_thoat"):
        if kb.get("tang", 0) >= 2 and (kb.get("nguong_ma10") or kb.get("ma10_tuan")):
            d.append(f"   Thoát: bán ATO thứ Hai nếu đóng cửa thứ Sáu < "
                     f"{_f(kb.get('nguong_ma10') or kb['ma10_tuan'])} (MA10 tuần)")
        elif kb.get("muc_tieu"):
            d.append(f"   Mục tiêu tiếp: {_f(kb['muc_tieu'])}" + (" → dời cắt lỗ lên hoà vốn" if kb.get("tang", 0) == 0
                                                                 else " → chuyển sang bán theo tuần"))
    if any("T+2" in x for x in kb.get("ghi_chu", [])):
        d.append("   CP chưa về (T+2)")
    if mt and mt.get("du"):
        d += [f"   ➕ MUA THÊM {mt['so_cp']:,.0f} CP",
              f"      Vùng mua: {_f(mt['tu'])} – {_f(mt['den'])}",
              f"      Cắt lỗ cả vị thế: {_f(mt['cl'])}",
              f"      Lý do: {mt['ly_do']}"]
    elif mt and mt.get("ly_do"):
        d.append(f"   Mua thêm: {mt['ly_do']}")
    return d


# ------------------------------------------------------------------ tin tổng kết
def dong_su_kien(gia_ma, bay_gio):
    """
    gia_ma {mã: giá đóng cửa} → dòng báo trước GDKHQ trong SO_NGAY_BAO_QUYEN ngày tới (lịch VNDirect).
    Vùng / cắt lỗ trong tin là giá TRƯỚC GDKHQ – bot 15' tự quy đổi theo tỷ lệ khi tới ngày.
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
    return (["", "📅 SẮP GDKHQ – vùng / cắt lỗ tự quy đổi theo tỷ lệ khi tới ngày"] + out) if out else []


def tin_tong_ket(ra, bay_gio, giu=None, kq_bt=None):
    """
    ra: chien_luoc_bot.chay_chien_luoc · giu: [(vt, kb, mt)] (None/[] → tin công khai) · kq_bt: ket_qua_backtest.json.
    → (tin đầy đủ, tin công khai) – tin công khai không có gì về danh mục (in ra log được).
    """
    dang_giu = {vt["ma"] for vt, _, _ in (giu or [])}
    day_du = _tin(ra, bay_gio, kq_bt, dang_giu)
    ds = dong_suat(ra, giu)
    if ds:                                       # bản riêng: còn bao nhiêu suất → mua lần lượt theo ★ tới hết suất
        i = next((j for j, x in enumerate(day_du) if x.startswith(tuple(TIEU_DE[n] for n in NHOM_MUA))), len(day_du))
        day_du[i:i] = [ds, ""] if i < len(day_du) else ["", ds]
    if giu:
        day_du += ["", f"💼 ĐANG GIỮ ({len(giu)})"]
        for vt, kb, mt in giu:
            day_du += dong_giu(vt, kb, mt)
        sk = dong_su_kien({vt["ma"]: (kb or {}).get("gia", np.nan) for vt, kb, _ in giu}, bay_gio)
        day_du += [x.replace("vùng / cắt lỗ tự quy đổi theo tỷ lệ khi tới ngày", "mã đang giữ: cắt lỗ / giá vốn đổi theo "
                             "tỷ lệ – danh_muc tự quy đổi") for x in sk]
    if C.GUI_EXCEL:
        day_du.append("📎 Chi tiết, lịch sử & backtest: file Excel đính kèm")
    return "\n".join(day_du).rstrip(), "\n".join(_tin(ra, bay_gio, kq_bt, set())).rstrip()


def dong_suat(ra, giu):
    """'🗓 Phiên 20/10 (tuần 43): đã mua 2/5 mã mới tuần này → còn 3 suất · đang giữ 7/8 mã (+1 cho 💪) – mua lần lượt
    theo ★ tới hết suất' – theo danh mục thật (ngày mua trong tuần của phiên hiệu lực). Không có danh mục → None."""
    if giu is None:
        return None
    from .vi_the import _ngay
    hl = next((k["hieu_luc"] for k in ds_khuyen_nghi(ra) if k.get("hieu_luc") is not None), None)
    if hl is None:
        return None
    tuan = pd.Timestamp(hl).isocalendar()[:2]
    moi = sum(1 for vt, _, _ in giu if _ngay(vt.get("ngay_mua")) is not None
              and pd.Timestamp(_ngay(vt.get("ngay_mua"))).isocalendar()[:2] == tuan)
    td, so_ma, dp = _quy("QUY_MOI_TUAN_TOI_DA", 5), _quy("QUY_SO_MA", 8), _quy("QUY_SUAT_DU_PHONG", 1)
    con, con_ma = max(td - moi, 0), max(so_ma - len(giu), 0)
    goi_y = (f"mua tối đa {min(con, con_ma)} mã theo thứ tự ★" if min(con, con_ma) else
             ("hết suất tuần – chỉ chờ ✅ vào trễ tuần sau" if not con else
              f"đủ {so_ma} mã – chỉ mã 💪 được mua (suất dự phòng)"))
    return (f"🗓 Phiên {pd.Timestamp(hl):%d/%m} (tuần {tuan[1]}): đã mua {moi}/{td} mã mới tuần này → còn {con} suất · "
            f"đang giữ {len(giu)}/{so_ma} mã" + (f" (+{dp} cho 💪)" if dp else "") + f"\n   → {goi_y}")


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
    if any(k["nhom"] in NHOM_MUA for k in ks) and mo_ta_cach_vao(bt):
        dong.append(mo_ta_cach_vao(bt))
    for nhom in NHOM_MUA:
        x = [k for k in ks if k["nhom"] == nhom]
        if not x:
            continue
        atc = (" · vào trễ: lệnh ATC, huỷ nếu chạm cắt lỗ"
               if nhom != "MUA_MOI" and _quy("QUY_VAO_TRE_KHOP", "mo") == "dong" else "")
        dong += ["", (f"{TIEU_DE[nhom]} ({len(x)}) – đặt lệnh phiên {hl:%d/%m}" if hl is not None else
                      f"{TIEU_DE[nhom]} ({len(x)})") + atc]
        x = sorted(x, key=lambda k: (k["uu_tien"] if k.get("uu_tien") == k.get("uu_tien") and k.get("uu_tien")
                                     is not None else 999, k["rui_ro"] if k["rui_ro"] == k["rui_ro"] else 99))
        dong += [dong_mua(k, dang_giu, bt) for k in x[:n_max]]
        if len(x) > n_max:
            dong.append(f"… +{len(x) - n_max} mã (xem Excel)")
    cho = [k for k in ks if k["nhom"] == "CHO"]
    if cho:
        dong += ["", f"{TIEU_DE['CHO']} ({len(cho)})"] + [
            (f"   {k['ma']}: vùng chờ {_f(k['tu'])} – {_f(k['den'])}" if k.get("den") == k.get("den")
             and k.get("den") is not None else f"   {k['ma']}: chờ tín hiệu mới") for k in cho[:n_max]] + (
            [f"   … +{len(cho) - n_max} mã"] if len(cho) > n_max else [])
    ko = [k for k in ks if k["nhom"] in ("DUOI_VON", "BAN")]
    if ko:
        dong.append(f"⛔ KHÔNG VÀO ({len(ko)}): " + ", ".join(k["ma"] for k in ko))
    ngoai = [k for k in ks if k["nhom"] == "NGOAI_TOP"]
    if ngoai:
        dong.append(f"⛔ CÓ TÍN HIỆU NHƯNG BỊ LỌC (ngoài top GTGD / RS 3T quá nóng / biến động mạnh) – không mua mới "
                    f"({len(ngoai)}): "
                    + ", ".join(k["ma"] + (" (RS nóng)" if "RS 3T" in str(k.get("loc_quy", "")) else "")
                                + (" (biến động)" if "biến động mạnh" in str(k.get("loc_quy", "")) else "")
                                for k in ngoai))
    if sum(k["nhom"] in NHOM_MUA for k in ks) > getattr(C, "SO_MA_MOI_TUAN", 2):
        dong += ["", f"★ = {getattr(C, 'SO_MA_MOI_TUAN', 2)} mã nên mua trước (điểm ưu tiên: cắt lỗ sát · lịch sử mã · "
                     f"lập đỉnh 52T; ≤ 2 mã/ngành) – quỹ B chỉ mua tối đa {getattr(C, 'SO_MA_MOI_TUAN', 2)} mã mới/tuần"]
    if any(k["nhom"] in NHOM_MUA and k.get("manh_b") for k in ks):
        dong.append(f"💪 = tín hiệu mạnh (≥ 3/4: sát đỉnh 52T · RS 3T cao · thanh khoản tăng · ngành mạnh) – đã đủ "
                    f"{_quy('QUY_SO_MA', 8)} mã vẫn được mua thêm {_quy('QUY_SUAT_DU_PHONG', 1)} mã (suất dự phòng)")
    if not any(k["nhom"] in NHOM_MUA for k in ks):
        dong += ["", "Không có mã nào để mua phiên tới."]
    dong += dong_su_kien({k["ma"]: k["gia"] for k in ks if k["nhom"] in NHOM_MUA + ("CHO",)}, bay_gio)
    # (bỏ đoạn giải thích luật cuối tin – người dùng 17/10/2026: tin ngắn; luật ở README / cau_hinh)
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
    from .nhat_ky import san_cua
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
                                     C.KY_HAN_MUA, san_cua(k["ma"]), loai=C.LOAI_NHAT_KY_CL, path=path,
                                     chien_luoc=info))
    return n


FILE_SAO = "lich_su_sao.csv"
COT_SAO = ["thoi_diem", "ngay", "ma", "nhom", "hang", "sao", "manh_b"]


def ghi_sao(ra, path=None, bay_gio=None, giu_ngay=120):
    """Lưu thứ tự ưu tiên / ★ của nhóm mua mỗi lần tổng kết (công khai: chỉ khuyến nghị) – danh-muc so lệnh thật với ★
    (dmuc/tuan_thu.py). Cùng ngày dữ liệu ghi lại thì thay bản cũ; giữ giu_ngay ngày. Trả số dòng ghi."""
    path = path or FILE_SAO
    so_sao = getattr(C, "SO_MA_MOI_TUAN", 2)
    td = f"{pd.Timestamp(bay_gio) if bay_gio is not None else pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').tz_localize(None):%Y-%m-%d %H:%M}"
    ngay = f"{pd.Timestamp(ra['doc']['ngay']):%Y-%m-%d}"
    moi = [{"thoi_diem": td, "ngay": ngay, "ma": k["ma"], "nhom": k["nhom"], "hang": int(k["uu_tien"]),
            "sao": int(k["uu_tien"] <= so_sao), "manh_b": int(bool(k.get("manh_b")))}
           for k in ds_khuyen_nghi(ra) if k["nhom"] in NHOM_MUA and k.get("uu_tien") == k.get("uu_tien")
           and k.get("uu_tien") is not None]
    try:
        cu = pd.read_csv(path, dtype=str, keep_default_na=False)
    except (OSError, ValueError):
        cu = pd.DataFrame(columns=COT_SAO)
    han = f"{pd.Timestamp(ngay) - pd.Timedelta(days=giu_ngay):%Y-%m-%d}"
    cu = cu[cu["ngay"].ne(ngay) & cu["ngay"].ge(han)]
    pd.concat([cu, pd.DataFrame(moi, columns=COT_SAO).astype(str)], ignore_index=True)[COT_SAO].to_csv(path, index=False)
    return len(moi)


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
    if he_so_nhiet is not None and he_so_nhiet == he_so_nhiet and he_so_nhiet != 1:   # nhiệt × lọc Quỹ B (kể cả ×1,5)
        rr = round(rr * he_so_nhiet, 4)
    ly = []
    if getattr(C, "KL_THEO_BIEN_DONG", False) and atr_pct == atr_pct:
        ly.append(f"ATR {atr_pct:.1f}%/ngày" + (f" > {C.ATR_MUC_TIEU_PCT:g}% → giảm" if atr_pct > C.ATR_MUC_TIEU_PCT
                                                else f" ≤ {C.ATR_MUC_TIEU_PCT:g}% → đủ"))
    if nua:
        ly.append("nhóm 🟡 ½")
    if gia and cl == cl and 0 < cl < gia:              # tính sẵn: tỷ trọng % NAV = rủi ro % ÷ khoảng cách cắt lỗ %
        r_pct, rr_hs = (gia - cl) / gia * 100, rr * hs
        tt = min(rr_hs / r_pct * 100, _tran_ma_pct())
        s = (f"Khối lượng: mua {tt:.1f}% NAV (rủi ro {rr_hs:.2f}% ÷ cắt lỗ {r_pct:.1f}%"
             + (", chạm trần/mã" if tt >= _tran_ma_pct() - 1e-9 else "") + ")"
             + (f" – {', '.join(ly)}" if ly else ""))
    elif getattr(C, "KL_THEO_BIEN_DONG", False):
        s = f"Khối lượng: {rr:g}% vốn ÷ (giá mua − cắt lỗ) × {hs:.2f}" + (f" ({', '.join(ly)})" if ly else "")
    else:
        s = (f"Khối lượng: ½ – {rr / 2:g}% vốn ÷ (giá mua − cắt lỗ)" if nua else
             f"Khối lượng: {rr:g}% vốn ÷ (giá mua − cắt lỗ)")
    von = von_trieu if von_trieu is not None else getattr(C, "VON_TRIEU", None)
    if von and gia and cl == cl and cl < gia:
        cp = min(von * 1e6 * rr / 100 * hs / ((gia - cl) * 1000), von * 1e6 * _tran_ma_pct() / 100 / (gia * 1000))
        cp = int(cp // 100 * 100)
        if cp > 0:
            s += f" ≈ {cp:,.0f} CP (≈ {cp * gia / 1000:,.1f} triệu, mất ≈ {cp * (gia - cl) / 1000:,.1f} triệu nếu chạm cắt lỗ)"
    return s
