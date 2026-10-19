# -*- coding: utf-8 -*-
"""
TRÌNH BÀY KẾT QUẢ LỌC THEO 4 BẢNG: TỔNG QUAN | TÀI CHÍNH | KỸ THUẬT | BIẾN ĐỘNG.
  • Giá theo VND, biến động theo %, RS6M/RS52W = xếp hạng 1–99 sức mạnh giá 6 tháng/52 tuần
    so với các mã trong lần quét (99 = mạnh nhất).
  • MA20/MA50/MA100 "Tăng/Giảm" = hướng đường MA so với 5 phiên trước.
  • Xuất file chien_luoc_<tên>.xlsx (4 sheet + sheet CHỈ TIÊU ĐÃ CHỌN).
"""
from datetime import datetime

import numpy as np
import pandas as pd

from .danh_gia_tai_chinh import TEN_MUC, TIEU_CHI_FA


TEN_NHOM = {"vn30": "VN30", "ngan_hang": "Ngân hàng", "chung_khoan": "Dịch vụ tài chính", "bat_dong_san": "Bất động sản",
            "cang_bien": "Cảng biển", "van_tai_bien": "Vận tải biển", "ban_le": "Bán lẻ", "thep": "Thép",
            "hoa_chat": "Hoá chất", "viettel": "Viễn thông", "vien_thong_cntt": "Viễn thông – CNTT"}

TEN_LOAI_TC = {"bat_buoc": "Bắt buộc", "cong_diem": "Cộng điểm", "toi_thieu": "Đạt tối thiểu"}


def _xep_hang(s):
    """Xếp hạng phần trăm 1–99 (kiểu chỉ số RS của IBD)."""
    s = pd.to_numeric(s, errors="coerce")
    if s.notna().sum() < 2:
        return pd.Series(np.nan, index=s.index)
    return (s.rank(pct=True) * 98 + 1).round(0)


def _mo_ta_tlv(x):
    if not isinstance(x, dict) or x.get("dat") is None:
        return ""
    return (f"✔ nền {x['so_phien']} phiên, KL ×{x['ty_le_kl']:.1f}, {x['tang_pct']:+.1f}%" if x["dat"] else "")


def lap_4_bang(ds_m, chon=None):
    """
    ds_m: list dict chỉ tiêu của MỌI mã đã quét (để xếp hạng RS); chon: danh sách mã đưa vào bảng (giữ thứ tự).
    → {"TỔNG QUAN": df, "TÀI CHÍNH": df, "KỸ THUẬT": df, "BIẾN ĐỘNG": df}
    """
    tat_ca = pd.DataFrame([{k: v for k, v in m.items() if not k.startswith("_")} for m in ds_m])
    if tat_ca.empty:
        return {k: pd.DataFrame() for k in ("TỔNG QUAN", "TÀI CHÍNH", "KỸ THUẬT", "BIẾN ĐỘNG")}
    tat_ca["RS6M"] = _xep_hang(tat_ca["bd_6th"]) if "bd_6th" in tat_ca else np.nan
    tat_ca["RS52W"] = _xep_hang(tat_ca["bd_1nam"]) if "bd_1nam" in tat_ca else np.nan
    t = tat_ca.set_index("Mã")
    if chon is not None:
        t = t.loc[[m for m in chon if m in t.index]]
    t = t.reset_index()
    g = lambda c: t[c] if c in t else pd.Series(np.nan, index=t.index)
    gia_vnd = g("gia") * 1000
    nganh = [str(n) if str(n) not in ("", "nan", "None") else TEN_NHOM.get(str(nh), "")
             for n, nh in zip(g("nganh"), g("nhom"))]

    tong_quan = pd.DataFrame({
        "MÃ": t["Mã"], "NGÀNH": nganh, "Giá": gia_vnd, "Kl T.bình 3 tháng": g("klgd3t"),
        "GTGD TB20 (tỷ)": g("gtgd20"), "Beta": g("beta"), "RSI": g("rsi"), "EPS (TTM)": g("eps_dung"),
        "P/E": g("pe"), "Vốn hoá (tỷ)": g("von_hoa"), "Đạt lọc": g("Đạt lọc"), "Điểm %": g("Điểm %")})
    tai_chinh = pd.DataFrame({
        "MÃ": t["Mã"], "GIÁ": gia_vnd, "DOANH THU (TTM)": g("dt_4q_ty") * 1e9, "LỢI NHUẬN (TTM)": g("ln_4q_ty") * 1e9,
        "TĂNG TRƯỞNG LN QUÝ (YoY)": g("ln_g_quy") / 100, "BIÊN GỘP QUÝ": g("bien_gop") / 100,
        "EPS (TTM)": g("eps_dung"), "BVPS (VND)": g("bvps"), "P/E": g("pe"), "P/B": g("pb"),
        "ROE": g("roe") / 100})
    ky_thuat = pd.DataFrame({
        "MÃ": t["Mã"], "KHỐI LƯỢNG": g("kl_phien"), "GIÁ": gia_vnd, "MA20": g("ma20_huong"),
        "MA50": g("ma50_huong"), "MA100": g("ma100_huong"), "RSI": g("rsi"), "RS6M": g("RS6M"),
        "RS52W": g("RS52W"), "MÔ HÌNH NẾN": g("mo_hinh_nen"), "TÍCH LŨY (phiên)": g("tich_luy_phien"),
        "TÍCH LŨY & VƯỢT": [_mo_ta_tlv(x) for x in g("tlv")]})
    bien_dong = pd.DataFrame({
        "MÃ": t["Mã"], "GIÁ": gia_vnd, "1 NGÀY": g("bd_1n"), "1 TUẦN": g("bd_1t"), "2 TUẦN": g("bd_2t"),
        "1 THÁNG": g("bd_1th"), "3 THÁNG": g("bd_3th"), "6 THÁNG": g("bd_6th"), "9 THÁNG": g("bd_9th"),
        "1 NĂM": g("bd_1nam"), "TÍNH ĐẾN HIỆN TẠI": g("bd_ytd")})
    return {"TỔNG QUAN": tong_quan, "TÀI CHÍNH": tai_chinh, "KỸ THUẬT": ky_thuat, "BIẾN ĐỘNG": bien_dong,
            "PHÂN TÍCH TÀI CHÍNH": bang_phan_tich_tai_chinh(t)}


def bang_phan_tich_tai_chinh(t):
    """10 tiêu chí tài chính: dòng = tiêu chí, cột = mã."""
    if "fa_chi_tiet" not in t:
        return pd.DataFrame()
    du_lieu, giai_thich = {}, {}
    for _, r in t.iterrows():
        ct = r.get("fa_chi_tiet")
        if not isinstance(ct, dict):
            continue
        cot = []
        for ten in TIEU_CHI_FA:
            muc, gt = ct.get(ten, (None, ""))
            cot.append(TEN_MUC.get(muc, "–"))
            giai_thich[(ten, r["Mã"])] = gt
        d = r.get("fa_diem")
        cot += [round(d) if d == d else "–", r.get("fa_nguon", "")]
        du_lieu[r["Mã"]] = cot
    if not du_lieu:
        return pd.DataFrame()
    df = pd.DataFrame(du_lieu, index=TIEU_CHI_FA + ["Điểm (0–100)", "Nguồn dữ liệu"])
    df.index.name = "CHỈ TIÊU"
    df = df.reset_index()
    df.attrs["giai_thich"] = giai_thich
    return df


# ---------------------------------------------------------------- in màn hình
_PHAN_TRAM = {"TĂNG TRƯỞNG LN QUÝ (YoY)", "BIÊN GỘP QUÝ", "ROE", "1 NGÀY", "1 TUẦN", "2 TUẦN", "1 THÁNG",
              "3 THÁNG", "6 THÁNG", "9 THÁNG", "1 NĂM", "TÍNH ĐẾN HIỆN TẠI"}
_TY_DONG = {"DOANH THU (TTM)", "LỢI NHUẬN (TTM)"}


def _dinh_dang(cot, x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    if isinstance(x, str):
        return x or "–"
    if cot in _PHAN_TRAM:
        return f"{x * 100:+.1f}%"
    if cot in _TY_DONG:
        return f"{x / 1e9:,.0f} tỷ"
    if cot in ("Giá", "GIÁ", "Kl T.bình 3 tháng", "KHỐI LƯỢNG", "EPS (TTM)", "BVPS (VND)", "Vốn hoá (tỷ)"):
        return f"{x:,.0f}"
    if cot in ("RS6M", "RS52W", "Điểm %", "TÍCH LŨY (phiên)"):
        return f"{x:.0f}"
    return f"{x:,.2f}"


BIEU_TUONG = {"Rất tốt": "🔵 Rất tốt", "Tốt": "🟢 Tốt", "Trung bình": "🟡 Trung bình", "Cảnh báo": "🟠 Cảnh báo",
              "Nguy hiểm": "🔴 Nguy hiểm", "–": "⚪ –"}
_COT_CHU = {"MÃ", "NGÀNH", "MA20", "MA50", "MA100", "MÔ HÌNH NẾN", "TÍCH LŨY & VƯỢT", "Đạt lọc", "CHỈ TIÊU"}


def in_4_bang(bang, so_dong=15):
    from .bang import ve_bang
    for ten, df in bang.items():
        if ten == "PHÂN TÍCH TÀI CHÍNH":
            print(f"\n  ▌{ten} – 10 tiêu chí (BCTC 3 năm)")
            if df.empty:
                print("    (chưa có BCTC năm – chạy kèm --luon_lay_co_ban hoặc chiến lược cần dữ liệu cơ bản)")
                continue
            print("    🔵 Rất tốt  🟢 Tốt  🟡 Trung bình  🟠 Cảnh báo  🔴 Nguy hiểm  ⚪ thiếu dữ liệu")
            t = df.iloc[:, : so_dong + 1].copy()
            for c in t.columns[1:]:
                t[c] = [BIEU_TUONG.get(v, v) if isinstance(v, str) else (f"{v:.0f}" if v == v else "–") for v in t[c]]
            print(ve_bang(t, thut=4))
            continue
        print(f"\n  ▌{ten}")
        if df.empty:
            print("    (không có mã)")
            continue
        t = df.head(so_dong).copy()
        for c in t.columns:
            t[c] = [_dinh_dang(c, x) for x in t[c]]
        so = [c for c in t.columns if c not in _COT_CHU]
        bo = [c for c in t.columns if (t[c] == "–").all()]                  # cột trống hoàn toàn → bỏ
        if len(bo) >= len(t.columns) - 2:
            print("    (chưa có dữ liệu – cần dữ liệu cơ bản: thêm --luon_lay_co_ban)")
            continue
        print(ve_bang(t.drop(columns=bo), thut=4, can_phai=so))


# ---------------------------------------------------------------- Excel kết quả
def _to_dieu_kien(ws, df, dong_dau):
    """Thanh dữ liệu (data bar) cho cột điểm; thang màu đỏ–trắng–xanh cho % thay đổi, upside, RSI."""
    from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
    from openpyxl.utils import get_column_letter
    if not len(df):
        return
    for j, cot in enumerate(df.columns, start=1):
        vung = f"{get_column_letter(j)}{dong_dau + 1}:{get_column_letter(j)}{dong_dau + len(df)}"
        if cot in ("Điểm %", "Điểm tổng", "Điểm lọc %"):
            ws.conditional_formatting.add(vung, DataBarRule(start_type="num", start_value=0, end_type="num",
                                                            end_value=100, color="FF66BB6A", showValue=True))
        elif cot in _PHAN_TRAM or cot in ("upside", "Upside %", "Mục tiêu %"):
            ws.conditional_formatting.add(vung, ColorScaleRule(
                start_type="min", start_color="FFEF9A9A", mid_type="num", mid_value=0, mid_color="FFFFFFFF",
                end_type="max", end_color="FFA5D6A7"))
        elif cot == "RSI":
            ws.conditional_formatting.add(vung, ColorScaleRule(
                start_type="num", start_value=30, start_color="FFA5D6A7", mid_type="num", mid_value=50,
                mid_color="FFFFFFFF", end_type="num", end_value=70, end_color="FFEF9A9A"))


def chen_anh(ws, anh, o_dau="A6", rong_toi_da=900):
    """Chèn ảnh PNG vào sheet (cần Pillow – Colab có sẵn); thiếu thư viện thì bỏ qua êm."""
    try:
        from openpyxl.drawing.image import Image as AnhXL
    except Exception:
        return
    dong = int("".join(ch for ch in o_dau if ch.isdigit()))
    for p in anh:
        try:
            a = AnhXL(p)
            if a.width > rong_toi_da:
                ty = rong_toi_da / a.width
                a.width, a.height = int(a.width * ty), int(a.height * ty)
            ws.add_image(a, f"A{dong}")
            dong += int(a.height / 20) + 2
        except Exception:
            continue


def xuat_excel(path, bang, tieu_chi=None, ghi_chu="", ten_chien_luoc="", anh=None, tong_quan=None):
    """
    File Excel kết quả của chiến lược – màu chủ đạo XANH LÁ: mỗi bảng 1 sheet (tiêu đề lớn, dòng thông tin,
    hàng tiêu đề xanh đậm chữ trắng, dòng xen kẽ xanh nhạt, lọc & cố định tiêu đề) + sheet TIÊU CHÍ.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    from .mau import XANH_DAM_HEX, XANH_HEX, XANH_NHAT_HEX

    nen_tieu_de = PatternFill("solid", fgColor="FF" + XANH_DAM_HEX)
    nen_xen = PatternFill("solid", fgColor="FF" + XANH_NHAT_HEX)
    chu_trang = Font(bold=True, color="FFFFFFFF")
    vien = Border(bottom=Side(style="thin", color="FFC8E6C9"))
    font_tang, font_giam = Font(color="FF2E7D32", bold=True), Font(color="FFC62828")
    from .so import la_cot_ty_le, vn_hoa
    dinh_dang = {**{c: "0.####%" for c in _PHAN_TRAM}, **{c: "#,##0" for c in _TY_DONG},
                 "Giá": "#,##0", "GIÁ": "#,##0", "Kl T.bình 3 tháng": "#,##0", "KHỐI LƯỢNG": "#,##0",
                 "EPS (TTM)": "#,##0", "BVPS (VND)": "#,##0", "Vốn hoá (tỷ)": "#,##0", "RS6M": "0",
                 "RS52W": "0", "Điểm %": "0", "TÍCH LŨY (phiên)": "0", "GTGD TB20 (tỷ)": "#,##0.0", "Beta": "0.####",
                 "RSI": "0.0", "P/E": "0.####", "P/B": "0.####"}
    mau_fa = {"Rất tốt": "FF4A90E2", "Tốt": "FF66BB6A", "Trung bình": "FFFFEE58", "Cảnh báo": "FFFFA726",
              "Nguy hiểm": "FFEF5350"}
    bay_gio = datetime.now()
    anh = [a for a in (anh or []) if a and __import__("os").path.exists(a)]
    tieu_de_lon = f"BỘ LỌC CỔ PHIẾU – CHIẾN LƯỢC {ten_chien_luoc.upper()}" if ten_chien_luoc else "BỘ LỌC CỔ PHIẾU"
    wb = Workbook()
    wb.remove(wb.active)

    def sheet(ten, df, dong_dau=4):
        ws = wb.create_sheet(ten[:31])
        ws.sheet_properties.tabColor = XANH_HEX
        ws.cell(1, 1, tieu_de_lon).font = Font(bold=True, size=14, color="FF" + XANH_DAM_HEX)
        ws.cell(2, 1, f"{ten}  ·  {ghi_chu}  ·  xuất lúc {bay_gio:%d/%m/%Y %H:%M}").font = Font(
            italic=True, color="FF616161")
        for j, cot in enumerate(df.columns, start=1):
            o = ws.cell(dong_dau, j, str(cot))
            o.fill, o.font = nen_tieu_de, chu_trang
            o.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, dong in enumerate(df.itertuples(index=False), start=dong_dau + 1):
            for j, (cot, x) in enumerate(zip(df.columns, dong), start=1):
                o = ws.cell(i, j)
                if (i - dong_dau) % 2 == 0:
                    o.fill = nen_xen
                o.border = vien
                if x is None or (isinstance(x, float) and np.isnan(x)):
                    continue
                o.value = vn_hoa(x) if isinstance(x, str) else x
                if cot in dinh_dang and not isinstance(x, str):
                    o.number_format = dinh_dang[cot]
                elif la_cot_ty_le(cot) and isinstance(x, float):
                    o.number_format = "0.####"
                if cot in _PHAN_TRAM and isinstance(x, (int, float)):
                    o.font = font_tang if x > 0 else (font_giam if x < 0 else Font())
                elif x == "Tăng":
                    o.font = font_tang
                elif x == "Giảm":
                    o.font = font_giam
                elif j == 1:
                    o.font = Font(bold=True)
        for j, cot in enumerate(df.columns, start=1):            # độ rộng theo nội dung
            dai = max([len(str(cot))] + [len(str(v)) for v in df[cot].tolist()[:200]])
            ws.column_dimensions[get_column_letter(j)].width = max(9, min(dai + 3, 50))
        ws.row_dimensions[dong_dau].height = 32
        ws.freeze_panes = ws.cell(dong_dau + 1, 2)
        _to_dieu_kien(ws, df, dong_dau)
        if len(df):
            ws.auto_filter.ref = f"A{dong_dau}:{get_column_letter(len(df.columns))}{dong_dau + len(df)}"
        return ws

    # ---- sheet đầu: TỔNG QUAN CHUNG (số liệu chính + biểu đồ)
    if tong_quan or anh:
        ws0 = wb.create_sheet("TỔNG QUAN CHUNG")
        ws0.sheet_properties.tabColor = XANH_DAM_HEX
        ws0.cell(1, 1, tieu_de_lon).font = Font(bold=True, size=16, color="FF" + XANH_DAM_HEX)
        ws0.cell(2, 1, f"{ghi_chu}  ·  xuất lúc {bay_gio:%d/%m/%Y %H:%M}").font = Font(italic=True, color="FF616161")
        dong = 4
        for nhan, gt in (tong_quan or {}).items():
            a_, b_ = ws0.cell(dong, 1, nhan), ws0.cell(dong, 2, vn_hoa(gt) if isinstance(gt, str) else gt)
            a_.font, a_.fill = Font(bold=True, color="FFFFFFFF"), nen_tieu_de
            b_.font = Font(bold=True, size=12, color="FF" + XANH_DAM_HEX)
            b_.fill = nen_xen
            dong += 1
        ws0.column_dimensions["A"].width, ws0.column_dimensions["B"].width = 30, 60
        chen_anh(ws0, anh, f"A{dong + 1}")
    for ten, df in bang.items():
        if ten == "PHÂN TÍCH TÀI CHÍNH" and df.empty:
            continue
        if ten != "PHÂN TÍCH TÀI CHÍNH":                          # bỏ cột trống hoàn toàn cho gọn
            df = df[[c for c in df.columns if c == "MÃ" or not df[c].replace("", np.nan).isna().all()]]
            if len(df.columns) <= 2:
                continue
        ws = sheet(ten, df)
        if ten == "PHÂN TÍCH TÀI CHÍNH":
            from openpyxl.comments import Comment
            gt = df.attrs.get("giai_thich", {})
            for i, dong in enumerate(df.itertuples(index=False), start=5):
                for j, (cot, x) in enumerate(zip(df.columns, dong), start=1):
                    if x in mau_fa:
                        o = ws.cell(i, j)
                        o.fill = PatternFill("solid", fgColor=mau_fa[x])
                        o.alignment = Alignment(horizontal="center")
                        if gt.get((dong[0], cot)):
                            o.comment = Comment(gt[(dong[0], cot)], "Bộ lọc")
            ws.column_dimensions["A"].width = 28
    if tieu_chi is not None and len(tieu_chi):
        ws = sheet("TIÊU CHÍ", tieu_chi.rename(columns={"Loại": "Nhóm"}).replace(TEN_LOAI_TC))
        ws.column_dimensions["B"].width = 80
    if wb.sheetnames and wb.sheetnames[0] != "TỔNG QUAN CHUNG" and "TỔNG QUAN CHUNG" in wb.sheetnames:
        wb.move_sheet("TỔNG QUAN CHUNG", offset=-wb.sheetnames.index("TỔNG QUAN CHUNG"))
    wb.save(path)
    return path
