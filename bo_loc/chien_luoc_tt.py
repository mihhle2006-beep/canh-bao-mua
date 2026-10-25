# -*- coding: utf-8 -*-
"""
CHIẾN LƯỢC THEO THỊ TRƯỜNG – cùng logic với ptcp (theo_chien_luoc / chien_luoc) và bot canh-bao-mua. Đang áp dụng
QUỸ BỨT PHÁ (ptcp CHIEN_LUOC_AP_DUNG = "quy_b"): chỉ hệ B ở mọi trạng thái thị trường (tỷ trọng ptcp.chien_luoc.TY_TRONG).

  Thị trường : 8 chỉ báo VN-Index → điểm X/8 → CL1 / CL2 (chỉ để theo dõi khi Quỹ Bứt Phá), đổi ở phiên cuối tháng.
               Độ rộng tính trên các mã quét, hoặc thi_truong_cl.json của ptcp (rổ top 100 GTGD chốt thứ Sáu tuần trước).
  Từng mã    : mô phỏng A0 (MACD ngày cắt lên) & B (lọc tuần + nhồi) với hệ thoát T2-2R-ma10 (ptcp QUY_NGUONG_TUAN) → nhóm hành động
               🟢 MUA MỚI · ✅ VÀO NHƯ LỆNH MỚI · 🟡 VÀO ½ · ⏳ CHỜ ĐIỀU CHỈNH · ⛔ hệ thống lỗ / sắp bán · chưa có tín hiệu,
               vùng mua (1 phiên hiệu lực), cắt lỗ (chuẩn hệ thoát), mục tiêu tạm thời 1R → 3R (mốc dời cắt lỗ,
               KHÔNG phải lệnh bán), lý do đạt điểm mua, điều kiện vô hiệu.
Lõi bo_loc/loi trỏ thẳng tới ptcp. Nhóm mua lọc thêm theo ptcp.loc_quy_b (top 100 GTGD · ĐẮT ½ · nhiệt dài hạn – VN-Index Tăng ½).
"""
import numpy as np
import pandas as pd

from .loi import cau_hinh as lcfg
from .loi.chi_bao import tinh_chi_bao
from .loi.chien_luoc import (NGUONG_LEN, NGUONG_XUONG, NHOM_HANH_DONG, TEN_CL, TY_TRONG, bang_chi_bao,
                             doc_thi_truong, hanh_dong, lich_chien_luoc)
from .loi.he_thoat import chuan_bi, danh_sach_bien_the, di_ngang_vni, mo_phong, stop_chuan, tin_hieu_macd

NHOM_MUA = ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA")
TEN_NHOM = {"MUA_MOI": "🟢 MUA MỚI", "VAO_NHU_MOI": "✅ VÀO NHƯ LỆNH MỚI", "VAO_NUA": "🟡 VÀO ½ KHỐI LƯỢNG",
            "CHO": "⏳ CHỜ ĐIỀU CHỈNH", "DUOI_VON": "⛔ HỆ THỐNG ĐANG LỖ", "BAN": "⛔ HỆ THỐNG SẮP BÁN",
            "CHO_TIN_HIEU": "CHƯA CÓ TÍN HIỆU", "NGOAI_TOP": "⛔ NGOÀI TOP GTGD / RS 3T QUÁ NÓNG – KHÔNG MUA MỚI"}
SO_MA_DO_RONG = 10                 # ít hơn số mã này → chỉ báo "độ rộng" không tính (như ptcp: ước tính)


def gop_tuan(df):
    return df.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                     "volume": "sum"}).dropna()


def _f(x, le=2):
    return "–" if x is None or x != x else f"{x:,.{le}f}"


TEN_DO_RONG = "Độ rộng: > 50% mã trên MA200"
FILE_THI_TRUONG = ("thi_truong_cl.json", "/content/drive/MyDrive/ptcp/thi_truong_cl.json")   # ptcp chien_luoc_thang


def _doc_cache(path=None):
    """Điểm & CL của rổ thị trường do ptcp (chien_luoc_thang / danh mục) lưu – dùng nếu CÙNG phiên dữ liệu."""
    import json
    import os
    for p in ([path] if path else []) + list(FILE_THI_TRUONG):
        if p and os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f), p
            except (OSError, ValueError):
                pass
    return None, None


def thi_truong(vni, gia=None, file_cache=None):
    """
    Điểm 8 chỉ báo, CL đang áp dụng, trạng thái đi ngang. gia: {mã: giá ngày}.
    Độ rộng: ≥ 10 mã → tính trên các mã quét; ít hơn → dùng thi_truong_cl.json cùng phiên của ptcp nếu có,
    không thì ƯỚC TÍNH bằng VNI > MA200 (như ptcp/theo_chien_luoc.thi_truong).
    """
    if vni is None or len(vni) < 260:
        return None
    g = pd.DataFrame({m: d.close for m, d in (gia or {}).items() if d is not None and len(d)})
    that = len(g.columns) >= SO_MA_DO_RONG
    F, diem, muc = bang_chi_bao(vni, g if that else None)
    if not that:
        cot = list(F.columns)
        F.insert(cot.index("Biến động 20 phiên < trung vị 1 năm"), TEN_DO_RONG, F["VNI > MA200"])
        diem = F.sum(axis=1).rename("Điểm")
    lich, _, cl = lich_chien_luoc(diem)
    doc = doc_thi_truong(F, diem, muc, cl)
    nguon = f"độ rộng trên {len(g.columns)} mã quét" if that else "độ rộng ước tính = VNI > MA200"
    c, p = _doc_cache(file_cache)
    if not that and c and c.get("ngay") == f"{pd.Timestamp(doc['ngay']):%Y-%m-%d}":
        doc.update({"diem": c["diem"], "so_chi_bao": c["so_chi_bao"], "dieu_kien_doi": c.get("dieu_kien_doi", "")})
        cl, nguon = int(c["cl"]), f"rổ {c.get('so_ma', '?')} mã ({p})"
    ng, bien = di_ngang_vni(vni)
    return {"doc": doc, "cl": int(cl), "ten_cl": TEN_CL[int(cl)], "ty_trong": TY_TRONG[int(cl)],
            "diem": int(doc["diem"]), "so_chi_bao": int(doc["so_chi_bao"]), "dieu_kien_doi": doc.get("dieu_kien_doi", ""),
            "di_ngang": bool(ng.iloc[-1]), "bien": float(bien.iloc[-1]),
            "nguong_bien": getattr(lcfg, "HT_NGANG_BIEN_PCT", 12.0), "phien_bien": getattr(lcfg, "HT_NGANG_PHIEN", 60),
            "do_rong": that, "nguon": nguon, "ngay": doc["ngay"]}


def dong_thi_truong(tt):
    if not tt:
        return "Thị trường: không có VN-Index – bỏ phần chiến lược"
    s = f"Thị trường: {tt['diem']}/{tt['so_chi_bao']} điểm ({tt['nguon']}) · {tt['ten_cl']}"
    s += (f" · VN-Index ĐI NGANG (biên {tt['phien_bien']} phiên {tt['bien']:.1f}% < {tt['nguong_bien']:g}%) → tín hiệu "
          f"mới chỉ lấy khi MACD tuần > Signal" if tt["di_ngang"] else
          f" · có xu hướng (biên {tt['phien_bien']} phiên {tt['bien']:.1f}%)")
    return s


def _dong_diem_mua(cuoi, x):
    """Trạng thái cuối của mo_phong → 1 dòng như bot (MUA phiên tới / ĐANG GIỮ / CHỜ tín hiệu)."""
    c, atr, n = x["c"], x["atr"], len(x["c"])
    r = {"Giá đóng cửa": float(c[-1])}
    vt = cuoi["vi_the"]
    if vt is not None:
        # chờ bán = đóng cửa tuần < MA10 tuần HOẶC đã thủng cắt lỗ / hết hạn chưa bán được – khớp ptcp & backtest
        ly = ("đóng cửa tuần < MA10 tuần" if vt.get("Bán phiên tới (MA10 tuần)") else
              (vt.get("Lý do chờ bán") or "chạm cắt lỗ") if vt.get("Đang chờ bán") else "")
        r.update({"Trạng thái": "ĐANG GIỮ" + (f" → BÁN phiên tới ({ly})" if ly else ""),
                  "Cắt lỗ phiên tới": float(vt["Cắt lỗ phiên tới"]), "Tầng": int(vt["Tầng"]),
                  "Ngày mua": vt["Ngày mua"], "Giá mua": float(vt["Giá mua"]), "Lãi (R)": float(vt.get("Lãi (R)", np.nan))})
    elif cuoi["cho_vao"] is not None and cuoi["cho_vao"]["j_mua"] == n:
        r.update({"Trạng thái": "MUA phiên tới (giá mở cửa) – Tín hiệu",
                  "Cắt lỗ dự kiến": float(stop_chuan(c[-1], atr[-1]))})
    else:
        r["Trạng thái"] = "CHỜ tín hiệu"
    return r


def danh_gia(gia, vni, tt=None):
    """
    gia: {mã: giá ngày (open/high/low/close/volume)}. → (tt, {mã: dict chiến lược}).
    Mỗi mã: nhom, ten_nhom, tu, den, cl, R, mt1, mt3, ly_do, vo_hieu, hieu_luc, khoi_luong, lai_ht.
    """
    tt = tt or thi_truong(vni, gia)
    if tt is None:
        return None, {}
    bts = {b.ma: b for b in danh_sach_bien_the(co_vni=False, vao_phu=False)}
    dm = {"A0": [], "B": []}
    for ma, df in gia.items():
        if df is None or len(df) < 260:
            continue
        df = df[["open", "high", "low", "close", "volume"]]
        d, w = tinh_chi_bao(df), tinh_chi_bao(gop_tuan(df))
        x = chuan_bi(d)
        for k, loc in (("A0", False), ("B", True)):
            r = mo_phong(x, tin_hieu_macd(d, w, loc_tuan=loc, vni=vni), bts[k])
            dm[k].append({"Mã": ma, **_dong_diem_mua(r["cuoi"], x)})
    hd = hanh_dong({k: pd.DataFrame(v) for k, v in dm.items()}, tt["ty_trong"], tt["ngay"])
    out = {}
    for _, r in (hd.iterrows() if len(hd) else []):
        g, cl, nhom = float(r["Giá đóng cửa"]), float(r["Cắt lỗ"]), r["Nhóm"]
        R = g - cl if cl == cl and cl < g else np.nan
        tp = str(r.get("Thành phần", ""))
        loc_tuan = tp.startswith("B") or (tt["di_ngang"] and nhom == "MUA_MOI")
        if nhom == "MUA_MOI":
            ly_do = f"MACD ngày cắt lên {pd.Timestamp(tt['ngay']):%d/%m}" + (" + MACD tuần > Signal" if loc_tuan else "")
        else:
            vao = r.get("HT mua ngày")
            lai = r.get("Lãi HT (R)")
            ly_do = ("tín hiệu MACD" + (" + MACD tuần" if tp.startswith("B") else "")
                     + (f", HT vào {pd.Timestamp(vao):%d/%m}" if vao is not None and vao == vao else "")
                     + (f" · đang {lai:+.1f}R" if lai is not None and lai == lai else ""))
        out[r["Mã"]] = {"nhom": nhom, "ten_nhom": TEN_NHOM.get(nhom, nhom), "tp": tp, "gia": g, "cl": cl, "R": R,
                        "tu": r.get("Vùng mua từ"), "den": r.get("Vùng mua đến"),
                        "mt1": g + R if R == R else np.nan, "mt3": g + 3 * R if R == R else np.nan,
                        "ly_do": ly_do, "vo_hieu": r.get("Vô hiệu khi", ""), "hieu_luc": r.get("Hiệu lực"),
                        "khoi_luong": r.get("Khối lượng", "–"), "lai_ht": r.get("Lãi HT (R)"),
                        "rui_ro_pct": r.get("Rủi ro %")}
        lq = _loc_quy(r["Mã"], vni) if nhom in NHOM_MUA else None
        if lq:                                         # Quỹ Bứt Phá 10/2026: top 100 GTGD · RS 3T nóng · ĐẮT ½ · nhiệt dài hạn ½
            k = out[r["Mã"]]
            k["he_so_quy"], k["loc_quy"] = lq["he_so"], "; ".join(lq["ly_do"])
            if lq["bo"]:
                k["nhom"], k["ten_nhom"] = "NGOAI_TOP", TEN_NHOM["NGOAI_TOP"]
            elif lq["he_so"] < 0.999:
                k["khoi_luong"] = f"{k['khoi_luong']} × {lq['he_so']:g} ({k['loc_quy']})"
    for ma in gia:                                     # không có trong bảng hành động = chưa có tín hiệu
        if ma not in out and gia[ma] is not None and len(gia[ma]) >= 260:
            g = float(gia[ma].close.iloc[-1])
            out[ma] = {"nhom": "CHO_TIN_HIEU", "ten_nhom": TEN_NHOM["CHO_TIN_HIEU"], "tp": "", "gia": g, "cl": np.nan,
                       "R": np.nan, "tu": np.nan, "den": np.nan, "mt1": np.nan, "mt3": np.nan,
                       "ly_do": "chưa có tín hiệu MACD ngày" + (" (đi ngang: cần thêm MACD tuần > Signal)"
                                                                if tt["di_ngang"] else ""),
                       "vo_hieu": "", "hieu_luc": None, "khoi_luong": "–", "lai_ht": np.nan, "rui_ro_pct": np.nan}
    return tt, out


def _loc_quy(ma, vni):
    """ptcp.loc_quy_b.he_so (ptcp cũ / lỗi → None: không lọc)."""
    try:
        from ptcp.loc_quy_b import he_so
        return he_so(ma, vni)
    except Exception:                                  # noqa: BLE001
        return None


def ap_vao_chi_so(m, k):
    """
    Ghi đè cắt lỗ / mục tiêu / upside / R/R / khuyến nghị của 1 mã bằng giá trị CHIẾN LƯỢC THỊ TRƯỜNG:
    cắt lỗ của hệ thống (vào trễ: cắt lỗ hệ thống đang chạy; tín hiệu mới: chuẩn hệ thoát), mốc 1R / 3R.
    Mã chưa có tín hiệu: giữ cắt lỗ chuẩn hệ thoát tính từ giá hiện tại (chi_so).
    """
    if not k:
        return m
    m["khuyen_nghi"] = k["ten_nhom"]
    cl, g = k.get("cl"), m["gia"]
    if cl is not None and cl == cl and cl < g:
        R = g - cl
        m.update({"cat_lo": cl, "gia_mt": g + R, "gia_mt_3r": g + 3 * R, "upside": 3 * R / g * 100, "rr": 3.0,
                  "kc_cat_lo_pct": R / g * 100,
                  "cat_lo_theo": ("cắt lỗ hệ thống đang chạy" if k["nhom"] not in ("MUA_MOI",)
                                  else "chuẩn hệ thoát (2×ATR, ≤ 7%, ≥ 1,5×ATR)")})
    return m
