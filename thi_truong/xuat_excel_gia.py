# -*- coding: utf-8 -*-
"""
XUẤT GIÁ RA EXCEL (27/11/2026, chủ quỹ: "dùng file excel, đừng dùng csv nữa – làm đẹp lại"): bảng giá dọc (mã, ngày, mở, cao,
thấp, đóng, KL) → MỘT file .xlsx:
  · Tổng quan          – mỗi mã một dòng: phiên đầu / cuối, giá cuối, % 1 tuần · 1 tháng · 3 tháng · 1 năm, đỉnh / đáy 52 tuần,
                         KL TB 20 phiên, liên kết tới sheet của mã
  · Thông tin giá      – giá đóng cửa THEO TUẦN, mã thành cột, tuần mới nhất ở trên (cấu trúc file Markowitz của chủ quỹ)
  · % thay đổi (Tuần)  – công thức từ sheet trên (sửa giá → tự tính lại)
  · <MÃ>               – mỗi mã một sheet: giá ngày mới nhất ở trên, thay đổi / % thay đổi (công thức), KL
Công thức ghi kèm giá trị đã tính (XlsxWriter) → xem trên điện thoại / Telegram không bị ô trống. Dùng: workflow xuat_csv.yml
(Xuat gia Excel) hoặc `python thi_truong/xuat_excel_gia.py <file.csv> [ra.xlsx]`. Chỉ cần pandas + xlsxwriter.
"""
import sys

import pandas as pd

XANH, XANH_DAM, NEN = "#2E7D32", "#1B5E20", "#E8F5E9"
CHI_SO = ("VNINDEX", "VN30", "VN100", "HNX", "UPCOM")
F_GIA, F_PT, F_KL = "#,##0.00#", "+0.00%;-0.00%;0.00%", "#,##0"
F_DOI = "+#,##0.00#;-#,##0.00#;0.00"


def _o(ws, r, c, gt, fmt=None):
    """Ghi 1 ô, NaN → trống."""
    if gt is None or (isinstance(gt, float) and gt != gt):
        ws.write_blank(r, c, None, fmt)
    else:
        ws.write(r, c, gt, fmt)


def _so_ngay(ts):
    """Ngày → số ngày kiểu Excel (giá trị kèm công thức phải là số, không phải chữ)."""
    return (pd.Timestamp(ts).normalize() - pd.Timestamp("1899-12-30")).days


def tuan(gop):
    """Bảng dọc → giá đóng cửa cuối mỗi tuần (nhãn: thứ Sáu; tuần đang dở: ngày giao dịch cuối), mã thành cột, mới nhất trên."""
    w = gop.pivot_table(index="ngay", columns="ma", values="close", aggfunc="last").sort_index()
    w = w[list(dict.fromkeys(gop["ma"]))]
    t = w.resample("W-FRI").last().dropna(how="all")
    if len(t) and t.index[-1] > w.index[-1]:
        t = t.rename(index={t.index[-1]: w.index[-1]})
    return t.iloc[::-1]


def ghi_excel(gop, ra, ngay_xuat=None, nguon="VNDirect / TCBS / Vietcap (giá điều chỉnh)"):
    """gop: DataFrame cột ma, ngay, open, high, low, close, volume (nhiều mã nối dọc). → ghi file .xlsx `ra`."""
    import xlsxwriter
    gop = gop.copy()
    gop["ngay"] = pd.to_datetime(gop["ngay"])
    ds = list(dict.fromkeys(gop["ma"]))                                # giữ thứ tự mã người dùng nhập
    gop = gop.sort_values(["ma", "ngay"], kind="stable")
    ngay_xuat = pd.Timestamp(ngay_xuat or pd.Timestamp.today()).normalize()
    wb = xlsxwriter.Workbook(ra, {"default_format_properties": {"font_name": "Arial", "font_size": 10},
                                  "strings_to_numbers": False})
    F = lambda **k: wb.add_format({"font_name": "Arial", "font_size": 10, **k})   # noqa: E731
    tieu_de = F(bold=True, font_size=15, font_color=XANH_DAM)
    phu = F(italic=True, font_color="#666666")
    dau = F(bold=True, font_color="#FFFFFF", bg_color=XANH, align="center", valign="vcenter", border=1, border_color=XANH_DAM,
            text_wrap=True)
    f_ngay = F(num_format="dd/mm/yyyy", align="center")
    f_gia, f_pt, f_kl, f_doi = F(num_format=F_GIA), F(num_format=F_PT), F(num_format=F_KL), F(num_format=F_DOI)
    f_ma = F(bold=True, font_color=XANH_DAM)
    f_ghi = F(font_color="#666666", font_size=9, text_wrap=True, valign="top")

    f_tang, f_giam = wb.add_format({"font_color": "#1B7F2A"}), wb.add_format({"font_color": "#C62828"})

    def mau(ws, r1, c1, r2, c2):
        """Tăng xanh / giảm đỏ (định dạng điều kiện – màu trong mã số mỗi phần mềm hiểu một kiểu)."""
        if r2 >= r1:
            ws.conditional_format(r1, c1, r2, c2, {"type": "cell", "criteria": ">", "value": 0, "format": f_tang})
            ws.conditional_format(r1, c1, r2, c2, {"type": "cell", "criteria": "<", "value": 0, "format": f_giam})

    def khung(ws, ten, mo, cot):
        ws.write(0, 0, ten, tieu_de)
        ws.write(1, 0, mo, phu)
        ws.set_row(0, 24)
        ws.set_row(3, 30)
        for i, (h, rong) in enumerate(cot):
            ws.write(3, i, h, dau)
            ws.set_column(i, i, rong)
        ws.freeze_panes(4, 1)
        ws.hide_gridlines(2)
        ws.repeat_rows(3)                                              # in: dòng tiêu đề cột lặp mỗi trang

    # ---------------- sheet từng mã (dữ liệu gốc) – ghi trước để biết hàng, nhưng xếp sau trong file
    ws_tq = wb.add_worksheet("Tổng quan")
    ws_t = wb.add_worksheet("Thông tin giá")
    ws_p = wb.add_worksheet("% thay đổi (Tuần)")
    tom = []
    for ma in ds:
        d = gop[gop["ma"] == ma].set_index("ngay").iloc[::-1]          # mới nhất trên
        ws = wb.add_worksheet(ma[:31])
        n = len(d)
        khung(ws, f"{ma} – giá ngày", f"{n:,} phiên · {d.index[-1]:%d/%m/%Y} → {d.index[0]:%d/%m/%Y} · giá: "
              f"{'điểm' if ma.startswith(CHI_SO) else 'nghìn đồng'} · nguồn: {nguon}".replace(",", "."),
              [("Ngày", 12), ("Mở", 11), ("Cao", 11), ("Thấp", 11), ("Đóng cửa", 11), ("Thay đổi", 11), ("% thay đổi", 11),
               ("Khối lượng", 15)])
        c = d["close"].to_numpy(dtype=float)
        so = d[["open", "high", "low", "close"]].to_numpy(dtype=float).tolist()   # mảng thuần → nhanh hơn iterrows ~5×
        kl = d["volume"].to_numpy(dtype=float).tolist()
        ngay = [_so_ngay(x) for x in d.index]
        wn, wf, wb_ = ws.write_number, ws.write_formula, ws.write_blank
        for i in range(n):
            r = 4 + i
            wn(r, 0, ngay[i], f_ngay)
            for j, x in enumerate(so[i], start=1):
                wn(r, j, x, f_gia) if x == x else wb_(r, j, None, f_gia)
            if i + 1 < n and c[i + 1] and c[i] == c[i] and c[i + 1] == c[i + 1]:
                wf(r, 5, f"=E{r + 1}-E{r + 2}", f_doi, float(c[i] - c[i + 1]))
                wf(r, 6, f"=IFERROR(E{r + 1}/E{r + 2}-1,\"\")", f_pt, float(c[i] / c[i + 1] - 1))
            else:
                wb_(r, 5, None, f_doi)
                wb_(r, 6, None, f_pt)
            wn(r, 7, kl[i], f_kl) if kl[i] == kl[i] else wb_(r, 7, None, f_kl)
        ws.autofilter(3, 0, 3 + n, 7)
        mau(ws, 4, 5, 3 + n, 6)
        tom.append((ma, d, n))

    # ---------------- Tổng quan
    khung(ws_tq, "Giá cổ phiếu – tổng quan",
          f"Xuất ngày {ngay_xuat:%d/%m/%Y} · {len(ds)} mã · nguồn: {nguon} · chạm tên mã để mở sheet giá ngày",
          [("Mã", 10), ("Phiên đầu", 12), ("Phiên cuối", 12), ("Số phiên", 10), ("Giá cuối", 11), ("% 1 tuần", 10),
           ("% 1 tháng", 10), ("% 3 tháng", 10), ("% 1 năm", 10), ("Cao nhất 52 tuần", 12), ("Thấp nhất 52 tuần", 12),
           ("Cách đỉnh 52 tuần", 12), ("KL TB 20 phiên", 14)])
    for i, (ma, d, n) in enumerate(tom):
        r, s = 4 + i, f"'{ma[:31]}'"
        c = d["close"].to_numpy()
        ws_tq.write_url(r, 0, f"internal:{s}!A1", f_ma, string=ma)
        ws_tq.write_formula(r, 1, f"={s}!A{3 + n + 1}", f_ngay, _so_ngay(d.index[-1]))
        ws_tq.write_formula(r, 2, f"={s}!A5", f_ngay, _so_ngay(d.index[0]))
        ws_tq.write_formula(r, 3, f"=COUNT({s}!E5:E{4 + n})", f_kl, int(pd.notna(c).sum()))
        ws_tq.write_formula(r, 4, f"={s}!E5", f_gia, float(c[0]))
        for j, lui in enumerate((5, 21, 63, 250), start=5):
            if n > lui and c[lui]:
                ws_tq.write_formula(r, j, f"=IFERROR({s}!E5/{s}!E{5 + lui}-1,\"\")", f_pt, float(c[0] / c[lui] - 1))
            else:
                ws_tq.write_blank(r, j, None, f_pt)
        m = min(n, 250)
        cao, thap = float(d["high"].iloc[:m].max()), float(d["low"].iloc[:m].min())
        ws_tq.write_formula(r, 9, f"=MAX({s}!C5:C{4 + m})", f_gia, cao)
        ws_tq.write_formula(r, 10, f"=MIN({s}!D5:D{4 + m})", f_gia, thap)
        ws_tq.write_formula(r, 11, f"=IFERROR(E{r + 1}/J{r + 1}-1,\"\")", f_pt, float(c[0] / cao - 1) if cao else 0.0)
        k = min(n, 20)
        ws_tq.write_formula(r, 12, f"=AVERAGE({s}!H5:H{4 + k})", f_kl, float(d["volume"].iloc[:k].mean()))
    mau(ws_tq, 4, 5, 3 + len(tom), 8)
    mau(ws_tq, 4, 11, 3 + len(tom), 11)
    hg = 4 + len(tom) + 1
    ws_tq.merge_range(hg, 0, hg + 2, 12, "Ghi chú: % 1 tuần / 1 tháng / 3 tháng / 1 năm = so với 5 / 21 / 63 / 250 phiên trước. "
                      "Giá đã điều chỉnh cổ tức, chia tách (nghìn đồng; chỉ số: điểm). Mọi cột ngoài Mã là công thức lấy từ sheet "
                      "của từng mã. Sheet 'Thông tin giá' + '% thay đổi (Tuần)' cùng cấu trúc bảng Markowitz (giá đóng cửa tuần, "
                      "mã thành cột, tuần mới nhất ở trên).", f_ghi)

    # ---------------- Thông tin giá (tuần) + % thay đổi (Tuần)
    t = tuan(gop)[ds]
    tu_t, den_t = (t.index[-1], t.index[0]) if len(t) else (ngay_xuat, ngay_xuat)
    cot = [("Ngày (cuối tuần)", 14)] + [(m, 10) for m in t.columns]
    khung(ws_t, "Giá đóng cửa theo tuần", f"Giá đóng cửa phiên cuối mỗi tuần · {len(t)} tuần · {tu_t:%d/%m/%Y} → {den_t:%d/%m/%Y}"
          " · nghìn đồng (chỉ số: điểm)", cot)
    khung(ws_p, "% thay đổi theo tuần", "Công thức = giá tuần này / giá tuần trước − 1 (từ sheet 'Thông tin giá'); ô trống = "
          "chưa có giá", cot)
    v = t.to_numpy(dtype=float)
    for i, ng in enumerate(t.index):
        r = 4 + i
        ws_t.write_datetime(r, 0, ng.to_pydatetime(), f_ngay)
        ws_p.write_datetime(r, 0, ng.to_pydatetime(), f_ngay)
        for j in range(v.shape[1]):
            x = v[i, j]
            _o(ws_t, r, j + 1, None if x != x else float(x), f_gia)
            col = xlsxwriter.utility.xl_col_to_name(j + 1)
            if i + 1 < len(t):
                y = v[i + 1, j]
                gt = float(x / y - 1) if x == x and y == y and y else ""
                ws_p.write_formula(r, j + 1, f"=IF(OR('Thông tin giá'!{col}{r + 1}=\"\",'Thông tin giá'!{col}{r + 2}=\"\"),\"\","
                                   f"'Thông tin giá'!{col}{r + 1}/'Thông tin giá'!{col}{r + 2}-1)", f_pt, gt)
    mau(ws_p, 4, 1, 2 + len(t), len(t.columns))                         # chỉ tô chữ tăng xanh / giảm đỏ
    for ws in (ws_tq, ws_t, ws_p):
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
    ws_tq.activate()
    wb.close()
    return ra


if __name__ == "__main__":
    vao = sys.argv[1]
    ra = sys.argv[2] if len(sys.argv) > 2 else vao.rsplit(".", 1)[0] + ".xlsx"
    print(ghi_excel(pd.read_csv(vao), ra))
