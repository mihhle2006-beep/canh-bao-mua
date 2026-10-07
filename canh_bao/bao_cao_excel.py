# -*- coding: utf-8 -*-
"""
FILE EXCEL CHI TIẾT gửi kèm tin tổng kết (tông xanh của ptcp).

  Tong ket      mọi mã của chiến lược: nhóm, vùng mua, cắt lỗ, mục tiêu 1R/3R, đạt điểm mua, vô hiệu khi
  Thi truong    8 chỉ báo VN-Index, CL đang áp dụng, chia vốn, điều kiện đổi, lịch đổi CL
  Dang giu      (riêng tư) danh mục thật: lãi/lỗ, R, tầng, cắt lỗ hệ thoát, mốc tiếp, MA10 tuần, mua thêm
  15p hom nay   kết quả cảnh báo 15' phiên hôm nay (mã nào kích hoạt lúc nào, mã nào bị bỏ, vì sao)
  Lich su KN    nhật ký khuyến nghị chiến lược ĐÃ GỬI + kết quả chấm theo hệ thoát (ĐÚNG/SAI/ĐANG CHỜ)
  Thong ke      độ chính xác theo nhóm khuyến nghị (nhật ký thật)
  Lich su 12T   khuyến nghị MÔ PHỎNG 12 tháng qua (phân nhóm lại từng phiên, chấm cùng cách) + Thong ke 12T
  Lich su 15p   các tin MUA NGAY / ATC đã gửi
  Ban (rieng)   (riêng tư) cảnh báo bán đã gửi + chấm
  BT 15 phut / BT diem ban   kết quả backtest gần nhất (ket_qua_backtest.json)
File có danh mục thật → chỉ gửi Telegram, không commit.
"""
import json
import os

import numpy as np
import pandas as pd

from . import cau_hinh as C
from .tong_ket_cl import KHUYEN_NGHI, ds_khuyen_nghi

TEN_COT_NK = {"ngay": "Ngày", "ma": "Mã", "khuyen_nghi": "Khuyến nghị", "chien_luoc": "CL", "gia": "Giá",
              "vung_tu": "Vùng từ", "vung_den": "Vùng đến", "cat_lo": "Cắt lỗ", "muc_tieu": "MT 1R",
              "muc_tieu_2": "MT 3R", "ket_qua": "Kết quả", "ket_qua_pct": "Lãi/lỗ %", "giai_thich": "Giải thích",
              "ngay_vao": "Ngày vào", "gia_vao": "Giá vào", "cl_hien_tai": "Cắt lỗ hiện tại", "tang": "Tầng",
              "ngay_ket_thuc": "Ngày kết thúc", "gia_ket_thuc": "Giá kết thúc", "so_phien": "Số phiên",
              "thoi_diem": "Thời điểm", "rr": "R/R"}


def _bang_tong_ket(ra):
    rows = []
    for k in ds_khuyen_nghi(ra):
        rows.append({"Nhóm": KHUYEN_NGHI.get(k["nhom"], k["nhom"]), "Mã": k["ma"], "Thành phần": k["tp"],
                     "Giá đóng cửa": k["gia"], "Vùng từ": k["tu"], "Vùng đến": k["den"], "Cắt lỗ": k["cl"],
                     "Rủi ro %": k["rui_ro"], "MT 1R": k["mt1"], "MT 3R": k["mt3"], "Lãi HT (R)": k["lai_ht"],
                     "Khối lượng": k["khoi_luong"], "ATR %/ngày": k.get("atr_pct"), "Hệ số KL": k.get("he_so_kl"),
                     "Đạt điểm mua": k["ly_do"], "Vô hiệu khi": k["vo_hieu"],
                     "Hiệu lực": k["hieu_luc"]})
    return pd.DataFrame(rows)


def _bang_thi_truong(ra):
    d = ra["doc"]
    w = ra["ty_trong"]
    dau = pd.DataFrame([
        {"Mục": "Ngày dữ liệu", "Giá trị": f"{pd.Timestamp(d['ngay']):%d/%m/%Y}"},
        {"Mục": "VN-Index", "Giá trị": f"{ra['vni']:,.2f}"},
        {"Mục": "Điểm thị trường", "Giá trị": f"{d['diem']}/{d['so_chi_bao']}"},
        {"Mục": "Đang áp dụng", "Giá trị": ra["ten_cl"][ra["cl"]]},
        {"Mục": "Chia vốn", "Giá trị": " · ".join(f"{k} {v * 100:.0f}%" for k, v in w.items() if v > 0)},
        {"Mục": "Điều kiện đổi", "Giá trị": d.get("dieu_kien_doi", "")}])
    bang = d["bang"].copy() if d.get("bang") is not None else pd.DataFrame()
    if len(bang) and "Đạt" in bang:
        bang["Đạt"] = bang["Đạt"].map({True: "✔", False: "✘"})
    return dau, bang


def _bang_giu(giu):
    rows = []
    for vt, kb, mt in giu or []:
        rows.append({"Mã": vt["ma"], "Số CP": vt["so_cp"], "Giá vốn": vt.get("gia_von"), "Ngày mua": vt.get("ngay_mua"),
                     "Giá": kb.get("gia"), "Lãi/lỗ %": kb.get("lai_lo_pct"), "Lãi (R)": kb.get("lai_R"),
                     "1R (đ/CP)": kb.get("R"), "Tầng": kb.get("tang"), "Cắt lỗ hiệu lực": kb.get("cat_lo"),
                     "Cắt lỗ hệ thống": kb.get("cat_lo_he_thong"), "Cắt lỗ đã đặt": kb.get("cat_lo_dat"),
                     "Mốc tiếp": kb.get("muc_tieu"), "Ngưỡng MA10 tuần": kb.get("nguong_ma10"),
                     "Mức": kb.get("muc"), "Lý do": "; ".join(kb.get("ly_do", []) + kb.get("ghi_chu", [])),
                     "Mua thêm": "ĐỦ ĐIỀU KIỆN" if (mt or {}).get("du") else (mt or {}).get("ly_do", ""),
                     "Mua thêm – vùng": (f"{mt['tu']:,.2f}–{mt['den']:,.2f}" if (mt or {}).get("du") else ""),
                     "Mua thêm – số CP": (mt or {}).get("so_cp"), "Giá vốn sau mua thêm": (mt or {}).get("gia_von_moi")})
    return pd.DataFrame(rows)


def _bang_15p(path=None):
    try:
        with open(path or C.FILE_TRANG_THAI, encoding="utf-8") as f:
            x = json.load(f).get("_15p_hom_nay") or {}
    except (OSError, ValueError):
        return pd.DataFrame()
    return pd.DataFrame(x.get("ds") or [])


def _nhat_ky(path, loai=None):
    try:
        from ptcp import nhat_ky as nk
        df = nk.doc(path)
    except Exception:
        return pd.DataFrame(), pd.DataFrame()
    if not len(df):
        return pd.DataFrame(), pd.DataFrame()
    if loai:
        df = df[df["loai"].isin(loai)]
    tk = nk.thong_ke(df) if len(df) else pd.DataFrame()
    cot = [c for c in TEN_COT_NK if c in df.columns and df[c].notna().any()]
    return df.sort_values("ngay", ascending=False)[cot].rename(columns=TEN_COT_NK), tk


def _lich_su_mo_phong(ra, so_phien=252):
    """
    Lịch sử khuyến nghị MÔ PHỎNG 12 tháng: phân nhóm lại TỪNG phiên quá khứ đúng như tin hằng ngày (chỉ dùng dữ liệu
    tới phiên đó), ghi khi nhóm của mã đổi, chấm như nhật ký (vào trong vùng giá mở cửa phiên sau, thoát bằng hệ thoát).
    → (bảng từng khuyến nghị, thống kê theo nhóm).
    """
    from ptcp.theo_chien_luoc import backtest_khuyen_nghi_cl, mo_phong_ma, thi_truong
    gia, vni = ra.get("gia_ngay") or {}, ra.get("vni_df")
    if not gia or vni is None:
        return pd.DataFrame(), pd.DataFrame()
    tt = thi_truong(vni, pd.DataFrame({m: d.close for m, d in gia.items()}), dung_cache=False)
    ds = []
    for ma, df in gia.items():
        b = backtest_khuyen_nghi_cl(mo_phong_ma(df, vni=vni), tt["cl_ngay"], tt["cl"])["bang"]
        if not len(b):
            continue
        b = b.tail(so_phien)
        b = b[(b["Nhóm"] != b["Nhóm"].shift()) & b["Nhóm"].isin(["MUA_MOI", "VAO_NHU_MOI", "VAO_NUA", "CHO"])]
        ds.append(b.assign(**{"Mã": ma}))
    if not ds:
        return pd.DataFrame(), pd.DataFrame()
    b = pd.concat(ds, ignore_index=True).sort_values("Ngày", ascending=False)
    mua = b["Nhóm"] != "CHO"
    kq = np.where(~b["Khớp"], "BỎ QUA", np.where(~b["Đóng"].astype(bool), "ĐANG CHỜ",
                  np.where((b["Lãi/lỗ %"] > 0) == mua, "ĐÚNG", "SAI")))
    out = pd.DataFrame({"Ngày": pd.to_datetime(b["Ngày"]).dt.strftime("%Y-%m-%d"), "Mã": b["Mã"],
                        "Khuyến nghị": b["Nhóm"].map(KHUYEN_NGHI), "CL": "CL" + b["CL"].astype(str),
                        "Giá": b["Giá đóng cửa"], "Vùng từ": b["Vùng từ"], "Vùng đến": b["Vùng đến"],
                        "Cắt lỗ": b["Cắt lỗ HT"], "Kết quả": kq, "Lãi/lỗ % (nếu mua)": b["Lãi/lỗ %"],
                        "Giải thích": b["Lý do"]})
    tk = []
    for ten, g in out.groupby("Khuyến nghị", sort=False):
        xong = g[g["Kết quả"].isin(["ĐÚNG", "SAI"])]
        p = g.loc[g["Kết quả"].isin(["ĐÚNG", "SAI"]), "Lãi/lỗ % (nếu mua)"]
        tk.append({"Khuyến nghị": ten, "Số KN": len(g), "Đã chấm": len(xong),
                   "Đúng %": (xong["Kết quả"] == "ĐÚNG").mean() * 100 if len(xong) else np.nan,
                   "TB lãi/lỗ % (nếu mua)": p.mean() if len(p) else np.nan,
                   "Bỏ qua (ngoài vùng)": int((g["Kết quả"] == "BỎ QUA").sum()),
                   "Đang chờ": int((g["Kết quả"] == "ĐANG CHỜ").sum())})
    return out, pd.DataFrame(tk)


def _bang_backtest(kq_bt):
    out = {}
    if not kq_bt:
        return out
    for khoa, ten in (("15p", "BT 15 phut"), ("diem_ban", "BT diem ban")):
        x = kq_bt.get(khoa) or {}
        if x.get("bang"):
            b = pd.DataFrame(x["bang"])
            ghi = pd.DataFrame([{b.columns[0]: f"Kết luận: {x.get('ket_luan', '')}"},
                                {b.columns[0]: f"Dữ liệu: {x.get('mo_ta', '')} · chạy {kq_bt.get('ngay_chay', '')}"}])
            out[ten] = pd.concat([b, ghi], ignore_index=True)
        if x.get("theo_nhom"):
            out[ten + " nhom"] = pd.DataFrame(x["theo_nhom"])
    return out


def xuat(ra, path=None, giu=None, kq_bt=None, rieng=False):
    """Ghi file Excel. rieng=True: thêm sheet danh mục & cảnh báo bán (file chỉ gửi Telegram). Trả đường dẫn."""
    from .nhat_ky import FILE_CONG_KHAI, FILE_RIENG
    path = path or C.FILE_EXCEL
    sheets = {"Tong ket": _bang_tong_ket(ra)}
    dau, bang = _bang_thi_truong(ra)
    if rieng and giu:
        sheets["Dang giu"] = _bang_giu(giu)
    sheets["15p hom nay"] = _bang_15p()
    kn, tk = _nhat_ky(FILE_CONG_KHAI, [C.LOAI_NHAT_KY_CL])
    sheets["Lich su KN"], sheets["Thong ke"] = kn, tk
    try:
        ms, mtk = _lich_su_mo_phong(ra)
        sheets["Lich su 12T (mo phong)"], sheets["Thong ke 12T"] = ms, mtk
    except Exception as e:                                     # không để lịch sử mô phỏng làm hỏng file
        print(f"⚠ Lịch sử mô phỏng lỗi: {type(e).__name__}: {str(e)[:100]}")
    sheets["Lich su 15p"] = _nhat_ky(FILE_CONG_KHAI, ["MUA_NGAY"])[0]
    if rieng:
        sheets["Ban (rieng)"] = _nhat_ky(FILE_RIENG, ["BAN"])[0]
    sheets.update(_bang_backtest(kq_bt))
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        for ten, b in sheets.items():
            if ten == "Tong ket":
                b.to_excel(w, sheet_name=ten, index=False)
                dau.to_excel(w, sheet_name="Thi truong", index=False)
                if len(bang):
                    bang.to_excel(w, sheet_name="Thi truong", index=False, startrow=len(dau) + 2)
                lich = ra.get("lich")
                if lich is not None and len(lich):
                    lich.to_excel(w, sheet_name="Lich doi CL", index=False)
                continue
            (b if b is not None and len(b) else pd.DataFrame({"(trống)": ["chưa có dữ liệu"]})) \
                .to_excel(w, sheet_name=ten[:31], index=False)
    try:
        from ptcp.excel_xanh import trang_tri_excel
        trang_tri_excel(path, sheet_chinh=("Tong ket", "Dang giu"))
    except Exception:
        pass
    return path
