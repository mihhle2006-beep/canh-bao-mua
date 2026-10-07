# -*- coding: utf-8 -*-
"""
BACKTEST cho bot (python chay.py --che_do backtest – chạy tay trên Actions, ~10–20 phút lần đầu):
  1. ĐIỂM BÁN & MUA THÊM: chốt ⅓ / ½ ở 3R, siết cắt lỗ khi thị trường giảm, hạn ngắn hơn, mua thêm kiểu B / khi có
     tín hiệu mới – so với hệ thoát gốc, 2 giai đoạn 2019–22 & 2023–26 (giá ngày).
  2. ĐIỂM VÀO 15 PHÚT: mọi khuyến nghị mua quá khứ của chiến lược (41 mã, cùng cách phân nhóm như tin hằng ngày)
     × các cách vào (ATO / 15P / 15P+ATC / 15P+GIO / VWAP / LO …) trên nến 15' thật → lãi/lỗ theo hệ thoát.
     Cách vào được chọn (khớp ≥ 50%, lãi TB / lệnh cao nhất) dùng cho cảnh báo trong phiên (CACH_VAO_15P = "tu_dong").
Kết quả (chỉ thống kê, không có danh mục) → ket_qua_backtest.json (commit) + file Excel gửi Telegram.
"""
import json

import numpy as np
import pandas as pd

from . import cau_hinh as C


def _ban_ghi(df):
    if df is None or not len(df):
        return []
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return json.loads(df.replace({np.nan: None}).to_json(orient="records", force_ascii=False))


def _ket_luan_15p(b, tot):
    from ptcp.diem_vao_15p import BIEN_THE
    if not tot:
        return "chưa đủ tín hiệu"
    bb = b.set_index("Biến thể")
    r = bb.loc[tot]
    kl = (f"Chọn {tot} ({BIEN_THE.get(tot, '')}): lãi TB {r['TB/lệnh khớp %']:+.2f}%/lệnh, khớp {r['Khớp %']:.0f}%")
    if "ATO" in bb.index and tot != "ATO":
        kl += f" – mua ATO: {bb.loc['ATO', 'TB/lệnh khớp %']:+.2f}%/lệnh"
    return kl


def chay_backtest(bay_gio, khong_gui=False, ds_ma=None):
    from ptcp.backtest_diem_ban import backtest_diem_ban
    from ptcp.diem_vao_15p import backtest_15p, tin_hieu_qua_khu
    from . import du_lieu
    from .thong_bao import gui, gui_file
    ds_ma = ds_ma or C.MA_CHIEN_LUOC
    print(f"=== BACKTEST | {pd.Timestamp(bay_gio):%Y-%m-%d %H:%M} | {len(ds_ma)} mã ===")
    vni = du_lieu.tai("VNINDEX", "D", C.BACKTEST_TU, chi_so=True)
    gia = {}
    for ma in ds_ma:
        d = du_lieu.tai(ma, "D", C.BACKTEST_TU)
        if d is not None and len(d) >= 260:
            gia[ma] = d
    if vni is None or len(gia) < 5:
        print("Thiếu dữ liệu ngày → dừng backtest.")
        return 1
    ra = {"ngay_chay": f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}", "so_ma": len(gia)}

    print("\n① Điểm bán & mua thêm (giá ngày)…")
    kb = backtest_diem_ban(gia, vni, start=C.BACKTEST_TU)
    ra["diem_ban"] = {"bang": _ban_ghi(kb["bang"]), "ket_luan": kb["ket_luan"],
                      "mo_ta": f"{len(gia)} mã, {C.BACKTEST_TU[:4]}–nay, tín hiệu A0, so với hệ thoát gốc"}
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(kb["bang"].round(2).to_string(index=False))
    print(kb["ket_luan"])

    print(f"\n② Điểm vào 15 phút – tải nến 15' từ {C.BACKTEST_15P_TU}…")
    n15 = {}
    for ma in gia:
        d = du_lieu.tai_lich_su_phut(ma, C.BACKTEST_15P_TU)
        if d is not None and len(d):
            n15[ma] = d
    if not n15:
        ra["15p"] = {"bang": [], "theo_nhom": [], "tot_nhat": None,
                     "ket_luan": "không tải được nến 15' – chưa backtest được"}
        print("Không tải được nến 15' nào.")
    else:
        tu = min(d.index[0] for d in n15.values()).normalize()
        den = max(d.index[-1] for d in n15.values())
        print(f"  nến 15': {len(n15)} mã, {tu:%d/%m/%Y} → {den:%d/%m/%Y}")
        ds, xs = tin_hieu_qua_khu(gia, vni, tu - pd.Timedelta(days=3))
        k15 = backtest_15p(ds, n15, xs)
        b = k15["bang"]
        kl = _ket_luan_15p(b, k15["tot_nhat"])
        ra["15p"] = {"bang": _ban_ghi(b), "theo_nhom": _ban_ghi(k15["theo_nhom"]), "tot_nhat": k15["tot_nhat"],
                     "ket_luan": kl, "so_tin_hieu": k15["so_tin_hieu"],
                     "mo_ta": f"{len(n15)} mã, nến 15' {tu:%d/%m/%Y}–{den:%d/%m/%Y}, {k15['so_tin_hieu']} khuyến nghị mua"}
        if len(b):
            with pd.option_context("display.width", 250, "display.max_columns", 30):
                print(b.drop(columns=["Mô tả"]).round(2).to_string(index=False))
        print(kl)
    with open(C.FILE_BACKTEST, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=1)
    print(f"Đã lưu {C.FILE_BACKTEST}")
    tin = "\n".join([f"🧪 BACKTEST CHIẾN LƯỢC – {pd.Timestamp(bay_gio):%d/%m/%Y}",
                     f"Điểm vào 15': {ra['15p']['ket_luan']}",
                     f"Điểm bán & mua thêm: {ra['diem_ban']['ket_luan']}",
                     "(Chi tiết: file Excel – các sheet BT 15 phut, BT diem ban)"])
    if khong_gui:
        print(tin)
        return 0
    gui(tin)
    path = "backtest_chien_luoc.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        pd.DataFrame(ra["diem_ban"]["bang"]).to_excel(w, sheet_name="BT diem ban", index=False)
        if ra["15p"].get("bang"):
            pd.DataFrame(ra["15p"]["bang"]).to_excel(w, sheet_name="BT 15 phut", index=False)
            pd.DataFrame(ra["15p"]["theo_nhom"]).to_excel(w, sheet_name="BT 15 phut theo nhom", index=False)
    try:
        from ptcp.excel_xanh import trang_tri_excel
        trang_tri_excel(path)
    except Exception:
        pass
    gui_file(path, "Backtest điểm vào 15' & điểm bán")
    return 0
