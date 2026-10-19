# -*- coding: utf-8 -*-
"""TRANG HTML DẠNG DASHBOARD cho kết quả lọc – tông xanh lá, xem tốt trên điện thoại, 1 file tự chứa (ảnh nhúng)."""
import base64
import html as _h
import os
from datetime import datetime

import numpy as np
import pandas as pd

from .so import vn_hoa

CSS = """
:root{--chu:#17211b;--phu:#5c6b62;--vien:#C8E6C9;--nen:#ffffff;--the:#ffffff;--xanh:#2E7D32;--xanh-nhat:#E8F5E9;
  --vang:#9a6a00;--vang-nhat:#fbf3df;--xam:#8a8a85;--do:#a3261f}
*{box-sizing:border-box}
html{font-size:17px}
body{font-family:"Times New Roman",Times,"Liberation Serif",serif;margin:0;color:var(--chu);background:var(--nen);
  line-height:1.5;-webkit-text-size-adjust:100%}
header{background:var(--xanh-nhat);border-bottom:3px solid var(--xanh);padding:28px 20px 18px}
.khung{max-width:960px;margin:0 auto}
header .nho{font-size:.82rem;letter-spacing:.08em;text-transform:uppercase;color:var(--phu);margin:0 0 6px}
header h1{margin:0;font-size:1.75rem;line-height:1.2;font-weight:700;color:var(--xanh)}
header p.mo-ta{margin:8px 0 0;color:var(--phu);font-size:1rem}
.thi-truong{margin:14px 0 0;padding:10px 14px;border-left:3px solid var(--xanh);background:var(--xanh-nhat);font-size:.98rem}
.thi-truong.ngang{border-left-color:var(--vang);background:var(--vang-nhat)}
nav{position:sticky;top:0;background:var(--the);border-bottom:1px solid var(--vien);z-index:5;overflow-x:auto;white-space:nowrap}
nav .khung{padding:10px 20px}
nav a{color:var(--xanh);text-decoration:none;margin-right:22px;font-size:.98rem}
nav a:hover{text-decoration:underline}
main{max-width:960px;margin:0 auto;padding:8px 20px 20px}
h2{font-size:1.35rem;color:var(--xanh);margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--vien);font-weight:700}
h3{font-size:1.1rem;margin:22px 0 8px}
p{margin:6px 0}
.the{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:20px}
.o{background:var(--the);border:1px solid var(--vien);padding:12px 14px}
.o .so{font-size:1.6rem;font-weight:700;color:var(--xanh);line-height:1.1}
.o .nhan{font-size:.88rem;color:var(--phu);margin-top:4px}
.tom-tat{font-size:1rem;margin:4px 0 14px}
.ma{background:var(--the);border:1px solid var(--vien);border-left:4px solid var(--xanh);padding:16px 18px;margin:14px 0}
.ma.dk{border-left-color:var(--vang)}
.ma .dau{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 12px;margin-bottom:4px}
.ma .ten{font-size:1.4rem;font-weight:700}
.ma .diem{margin-left:auto;color:var(--phu);font-size:.92rem}
.ma .nhom-cl{font-style:italic;color:var(--phu);margin:2px 0 10px}
.nhan-nhom{display:inline-block;padding:1px 10px;border:1px solid var(--xanh);color:var(--xanh);font-size:.85rem;
  font-weight:700;letter-spacing:.02em}
.nhan-nhom.dk{border-color:var(--vang);color:var(--vang)}
table.kh{border-collapse:collapse;width:100%;font-size:1rem}
table.kh th{text-align:left;font-weight:700;color:var(--phu);vertical-align:top;padding:5px 14px 5px 0;width:118px;
  white-space:nowrap;background:none;position:static}
table.kh td{text-align:left;padding:5px 0;border-bottom:1px dotted var(--vien);white-space:normal;background:none!important}
table.kh tr:last-child td,table.kh tr:last-child th{border-bottom:0}
.so-lieu{font-variant-numeric:tabular-nums}
.chu-phu{color:var(--phu);font-size:.92rem}
.cuon{overflow-x:auto;background:var(--the);border:1px solid var(--vien);margin:10px 0 18px}
table{border-collapse:collapse;font-size:.92rem;width:100%;font-variant-numeric:tabular-nums}
th{background:var(--xanh-nhat);color:var(--chu);padding:8px 10px;font-weight:700;border-bottom:1px solid var(--vien);
  position:sticky;top:0;text-align:right}
td{padding:7px 10px;border-bottom:1px solid #ecefe9;text-align:right;white-space:nowrap}
td:first-child,th:first-child{text-align:left;font-weight:700}
td.tang{color:var(--xanh);font-weight:700} td.giam{color:var(--do)}
td.f5{background:#dbe8f6!important} td.f4{background:#e1efdc!important} td.f3{background:#f8f1d2!important}
td.f2{background:#f8e2cc!important} td.f1{background:#f4d3d0!important}
.thanh{display:inline-block;height:7px;background:var(--xanh);opacity:.55;vertical-align:middle;margin-right:6px}
img{max-width:100%;background:#fff;border:1px solid var(--vien);margin:8px 0}
ul.tc{padding-left:20px} ul.tc li{margin:4px 0}
footer{color:var(--phu);font-size:.88rem;text-align:center;padding:28px 20px;border-top:1px solid var(--vien);margin-top:30px}
@media (max-width:600px){html{font-size:16px} header h1{font-size:1.45rem} .ma{padding:14px}
  .the{grid-template-columns:repeat(3,1fr);gap:8px} .o{padding:9px 10px} .o .so{font-size:1.3rem} .o .nhan{font-size:.8rem}
  table.kh th{width:92px;padding-right:10px} .ma .diem{margin-left:0;width:100%}}
@media print{nav{display:none} body{background:#fff} .ma,.o,.cuon{break-inside:avoid}}
"""
_MUC_FA = {"Rất tốt": "f5", "Tốt": "f4", "Trung bình": "f3", "Cảnh báo": "f2", "Nguy hiểm": "f1"}


def _e(x):
    return _h.escape(vn_hoa(str(x)))


def _bang_html(df, dinh_dang=None):
    if df is None or df.empty:
        return "<p><i>Chưa có dữ liệu.</i></p>"
    if dinh_dang:                                   # bỏ cột trống hoàn toàn (VD chưa có dữ liệu cơ bản)
        giu = [c for k_, c in enumerate(df.columns)
               if k_ == 0 or any(dinh_dang(c, v) not in ("–", "") for v in df[c])]
        if len(giu) <= 2:
            return "<p><i>Chưa có dữ liệu – cần dữ liệu cơ bản (chạy kèm --luon_lay_co_ban).</i></p>"
        df = df[giu]
    # cột chữ (không phải số) → căn trái cả tiêu đề lẫn ô
    cot_chu = {c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and
               not df[c].map(lambda v: isinstance(v, (int, float)) or (isinstance(v, str) and v[:1] in "+-0123456789"
                                                                       and any(ch.isdigit() for ch in v))).mean() > 0.6}
    trai = ' style="text-align:left"'
    tieu_de = "".join(f'<th{trai if c in cot_chu else ""}>{_e(c)}</th>' for c in df.columns)
    dong = []
    for _, r in df.iterrows():
        o = []
        for c in df.columns:
            v = r[c]
            lop = ""
            if isinstance(v, str) and v in _MUC_FA:
                lop = _MUC_FA[v]
            chu = dinh_dang(c, v) if dinh_dang else ("–" if v is None or (isinstance(v, float) and np.isnan(v)) else v)
            if c in ("Điểm %",) and isinstance(v, (int, float)) and v == v:
                chu = f'<span class="thanh" style="width:{max(0, min(v, 100)) * 0.6:.0f}px"></span>{v:.0f}'
                o.append(f"<td>{chu}</td>")
                continue
            if isinstance(chu, str) and chu.startswith("+") and "%" in chu:
                lop = lop or "tang"
            elif isinstance(chu, str) and chu.startswith("-") and "%" in chu:
                lop = lop or "giam"
            can = ' style="text-align:left"' if c in cot_chu else ""
            o.append(f'<td class="{lop}"{can}>{_e(chu)}</td>')
        dong.append("<tr>" + "".join(o) + "</tr>")
    return f'<div class="cuon"><table><tr>{tieu_de}</tr>{"".join(dong)}</table></div>'


TEN_ANH = {"tong_quan_loc.png": "Tổng quan bộ lọc", "danh_gia_sau_loc.png": "Đánh giá sau lọc",
           "bieu_do_cac_ma.png": "Biểu đồ các mã"}


def _anh(p):
    if not p or not os.path.exists(p):
        return ""
    ten = os.path.basename(p)
    ten = TEN_ANH.get(ten, os.path.splitext(ten)[0].replace("_", " "))       # tên file trên đĩa không hiện ra
    with open(p, "rb") as f:
        return f'<img alt="{_h.escape(ten)}" src="data:image/png;base64,{base64.b64encode(f.read()).decode()}">'


NHOM_TC = (("bat_buoc", "Bắt buộc", "mã phải đạt tất cả mới qua lọc"),
           ("cong_diem", "Cộng điểm", "đạt tiêu chí nào thì cộng điểm xếp hạng tiêu chí đó, không đạt không bị loại"),
           ("toi_thieu", "Cơ bản tối thiểu", "phải đạt đủ số tiêu chí tối thiểu trong nhóm này"))

QUY_TAC_CL = (
    ("Nhóm hành động", "Mua mới · Vào như mua mới · Vào nửa vị thế · Chờ · Dưới vốn · Bán · Chờ tín hiệu – "
     "tính theo điểm thị trường (8 chỉ báo, CL1/CL2) và tín hiệu MACD ngày/tuần, giống bot cảnh báo."),
    ("Đạt điểm mua", "giá nằm trong vùng mua của chiến lược; ngoài vùng thì chờ, không đuổi giá."),
    ("Cắt lỗ", "max(giá − 2·ATR, giá − 7%), cách giá tối thiểu 1,5·ATR."),
    ("Mục tiêu", "1R = giá + (giá − cắt lỗ); 3R = giá + 3·(giá − cắt lỗ). Tới 3R thì chuyển sang thoát theo MA10."),
    ("Thị trường đi ngang", "VN-Index biên 60 phiên < 12% → chỉ mua khi MACD tuần > Signal."),
    ("Điểm xếp hạng", "điểm 5 trụ cột chỉ để sắp thứ tự; quyết định mua/chờ theo nhóm chiến lược."),
)


def _tieu_chi_html(tieu_chi):
    if tieu_chi is None or not len(tieu_chi):
        return ""
    ds = list(tieu_chi.itertuples(index=False))
    phan = []
    for khoa, ten, giai_thich in NHOM_TC:
        muc = [t for n, t in ds if n == khoa]
        if muc:
            phan.append(f'<h3>{_e(ten)} <span class="nho">– {_e(giai_thich)}</span></h3>'
                        '<ul class="tc">' + "".join(f"<li>{_e(t)}</li>" for t in muc) + "</ul>")
    khac = [(n, t) for n, t in ds if n not in {k for k, _, _ in NHOM_TC}]
    if khac:
        phan.append('<ul class="tc">' + "".join(f"<li><b>{_e(n)}</b>: {_e(t)}</li>" for n, t in khac) + "</ul>")
    phan.append("<h3>Quy tắc chiến lược thị trường <span class=\"nho\">– áp cho mọi mã sau lọc</span></h3>"
                '<ul class="tc">' + "".join(f"<li><b>{_e(a)}:</b> {_e(b)}</li>" for a, b in QUY_TAC_CL) + "</ul>")
    return "".join(phan)


def xuat_html(path, ten_cl, mo_ta, phien, b, dat, k, bang, anh, tieu_chi=None, thi_truong=None, che_do="noi_bo"):
    """che_do "noi_bo": đủ chi tiết (khối lượng/NAV, điểm, bảng lọc, tiêu chí) · "ngoai": bản gửi người ngoài."""
    if che_do == "ngoai":
        return _xuat_ngoai(path, phien, k, anh, thi_truong)
    from .bon_bang import _dinh_dang
    dem = k["Kết luận"].value_counts().to_dict() if k is not None and len(k) else {}
    the = [("Mã phân tích", len(b)), ("Đạt lọc", len(dat)), ("Nên mua", dem.get("[NÊN MUA]", 0)),
           ("Mua có điều kiện", dem.get("[MUA CÓ ĐIỀU KIỆN]", 0)), ("Theo dõi", dem.get("[THEO DÕI]", 0))]
    the_html = "".join(f'<div class="o"><div class="so">{_e(v)}</div><div class="nhan">{_e(n)}</div></div>'
                       for n, v in the)

    kl = []
    if k is not None and len(k):
        f2 = lambda v, le=2: _e(f"{v:,.{le}f}") if isinstance(v, (int, float)) and v == v else "–"
        chu = lambda v: v if isinstance(v, str) else ""
        for nhom, lop in (("[NÊN MUA]", ""), ("[MUA CÓ ĐIỀU KIỆN]", "dk")):
            for _, r in k[k["Kết luận"] == nhom].iterrows():
                luu_y = "; ".join(x for x in (chu(r.get("Điểm yếu")), chu(r.get("Rủi ro / lưu ý"))) if x)
                co_3r = isinstance(r.get("MT 3R"), (int, float)) and r.get("MT 3R") == r.get("MT 3R")
                dong = [("Vùng mua", _e(r["Vùng mua"])),
                        ("Cắt lỗ", f'{f2(r["Cắt lỗ"])} <span class="chu-phu">({f2(r["Cắt lỗ %"], 1)}%)</span>'),
                        ("Mục tiêu", (f'1R {f2(r["Mục tiêu"])} → 3R {f2(r["MT 3R"])} <span class="chu-phu">'
                                      f'(mốc dời cắt lỗ – bán theo hệ thoát, không chốt cứng)</span>') if co_3r else
                         f'{f2(r["Mục tiêu"])} (+{f2(r["Mục tiêu %"], 1)}%) · R/R {f2(r["R/R"], 1)}'),
                        ("Khối lượng", f'{f2(r["Số CP"], 0)} CP ≈ {f2(r["Giá trị (tr)"], 1)} triệu '
                                       f'<span class="chu-phu">({f2(r["% NAV"], 1)}% NAV)</span>')]
                if chu(r.get("Vô hiệu khi")):
                    dong.append(("Vô hiệu khi", _e(r["Vô hiệu khi"])))
                if chu(r.get("Điểm mạnh")):
                    dong.append(("Điểm mạnh", _e(r["Điểm mạnh"])))
                if luu_y:
                    dong.append(("Lưu ý", _e(luu_y)))
                if chu(r.get("Cần chờ")):
                    dong.append(("Cần chờ", _e(r["Cần chờ"])))
                nhom_cl = chu(r.get("Nhóm chiến lược"))
                kl.append(
                    f'<div class="ma {lop}"><div class="dau"><span class="ten">{_e(r["Mã"])}</span>'
                    f'<span class="nhan-nhom {lop}">{_e(r["Hành động"])}</span>'
                    f'<span class="diem">giá {f2(r["Giá"])} · điểm {r["Điểm tổng"]:.0f}/100</span></div>'
                    + (f'<div class="nhom-cl">{_e(nhom_cl)} — {_e(chu(r.get("Đạt điểm mua")))}</div>' if nhom_cl else "")
                    + '<table class="kh so-lieu">' + "".join(f"<tr><th>{_e(n)}</th><td>{v}</td></tr>" for n, v in dong)
                    + "</table></div>")
        td = k[k["Kết luận"] == "[THEO DÕI]"]
        if len(td):
            kl.append('<h3>Theo dõi – cần chờ thêm điều kiện</h3><div class="cuon"><table><tr><th>Mã</th><th>Điểm</th>'
                      '<th style="text-align:left">Cần chờ</th></tr>' + "".join(
                          f'<tr><td>{_e(r["Mã"])}</td><td>{r["Điểm tổng"]:.0f}</td><td style="text-align:left;'
                          f'white-space:normal">{_e(r["Cần chờ"] or "tín hiệu rõ hơn")}</td></tr>'
                          for _, r in td.iterrows()) + "</table></div>")
        if not dem.get("[NÊN MUA]"):
            kl.insert(0, '<p class="tom-tat">Hôm nay <b>không có mã đủ điều kiện mua ngay</b>. '
                         'Ưu tiên theo dõi các mã bên dưới.</p>')
    else:
        kl.append("<p><i>Chưa chạy bước đánh giá (đã dùng --khong_danh_gia).</i></p>")

    muc = [("ket-luan", "Kết luận")] + [(f"b{i}", t.title()) for i, t in enumerate(bang)] + \
        [("bieu-do", "Biểu đồ"), ("tieu-chi", "Tiêu chí")]
    phan_bang = "".join('<h2 id="b%d">%s</h2>%s' % (i, _e(t.title()), _bang_html(
        df, None if t == "PHÂN TÍCH TÀI CHÍNH" else _dinh_dang)) for i, (t, df) in enumerate(bang.items()))
    tc = _tieu_chi_html(tieu_chi)
    nav = "".join('<a href="#%s">%s</a>' % (a, _e(t)) for a, t in muc)
    tt_html = ""
    if thi_truong:
        phan = thi_truong.replace("Thị trường: ", "").split(" · VN-Index ", 1)
        tt_html = (f'<div class="thi-truong{" ngang" if "ĐI NGANG" in thi_truong else ""}"><b>Thị trường:</b> '
                   f'{_e(phan[0])}' + (f'<br>VN-Index {_e(phan[1])}' if len(phan) > 1 else "") + "</div>")
    noi_dung = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Bộ lọc – chiến lược {_e(ten_cl)}</title>
<style>{CSS}</style></head><body>
<header><div class="khung"><p class="nho">Bộ lọc cổ phiếu · phiên {_e(phien)}</p>
<h1>Chiến lược {_e(ten_cl)}</h1><p class="mo-ta">{_e(mo_ta)}</p>{tt_html}</div></header>
<nav><div class="khung">{nav}</div></nav>
<main><div class="the">{the_html}</div>
<h2 id="ket-luan">Kết luận</h2>{"".join(kl)}
{phan_bang}
<h2 id="bieu-do">Biểu đồ</h2>{"".join(_anh(p) for p in anh)}
<h2 id="tieu-chi">Tiêu chí của chiến lược</h2>{tc}
</main><footer>Xuất lúc {datetime.now():%d/%m/%Y %H:%M} · Công cụ tham khảo dựa trên dữ liệu quá khứ – không phải khuyến nghị đầu tư.</footer>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(noi_dung)
    return path


# ---------------- BẢN GỬI NGƯỜI NGOÀI ----------------
# Không có: quy mô vốn / số CP / % NAV, điểm chấm, tên & tiêu chí chiến lược, bảng lọc, quy tắc nội bộ (ATR, CL1/CL2…). Biểu đồ giữ đủ.
CACH_DOC = (
    ("Vùng mua", "khoảng giá hợp lý để mua. Giá mở cửa đã vượt vùng thì không đuổi theo."),
    ("Giá đặt", "giá đặt lệnh giới hạn (LO) gợi ý, nằm ở phần dưới của vùng mua."),
    ("Cắt lỗ", "giá đóng cửa thấp hơn mức này thì bán, chấp nhận lỗ nhỏ để bảo vệ vốn."),
    ("Mục tiêu 1R / 3R", "R = khoảng cách từ giá mua tới cắt lỗ. Tới 1R: dời cắt lỗ về hoà vốn. Tới 3R: tiếp tục "
                         "giữ, bán khi xu hướng tuần gãy. Đây là mốc quản lý lệnh, không phải giá chốt cứng."),
    ("Vô hiệu khi", "điều kiện khiến nhận định mua không còn đúng – xảy ra thì bỏ qua mã."),
    ("Khối lượng", "nên tính sao cho nếu chạm cắt lỗ chỉ mất khoảng 0,5–1% tổng vốn; không dồn vốn vào một mã."),
)
NHOM_NGOAI = (("[NÊN MUA]", "", "Có thể mua", "đủ điều kiện, mua trong vùng giá"),
              ("[MUA CÓ ĐIỀU KIỆN]", "dk", "Mua khi đủ điều kiện", "mua một phần hoặc chờ giá về vùng mua"))


def _thi_truong_ngoai(thi_truong):
    if not thi_truong or "không có VN-Index" in thi_truong:
        return ""
    import re
    m = re.search(r"(\d+)/(\d+) điểm", thi_truong)
    diem = f" · sức khoẻ {m.group(1)}/{m.group(2)}" if m else ""
    if "ĐI NGANG" in thi_truong:
        return (f'<div class="thi-truong ngang"><b>Thị trường: đi ngang{diem}.</b> Nên thận trọng, giải ngân từng '
                f'phần, ưu tiên mã có xu hướng tuần tốt.</div>')
    return f'<div class="thi-truong"><b>Thị trường: có xu hướng{diem}.</b> Có thể mua theo kế hoạch từng mã.</div>'


def _xuat_ngoai(path, phien, k, anh, thi_truong):
    f2 = lambda v, le=2: _e(f"{v:,.{le}f}") if isinstance(v, (int, float)) and v == v else "–"
    chu = lambda v: v if isinstance(v, str) else ""
    co_k = k is not None and len(k)
    dem = k["Kết luận"].value_counts().to_dict() if co_k else {}
    the = [(ten, dem.get(n, 0)) for n, _, ten, _ in NHOM_NGOAI] + [("Theo dõi", dem.get("[THEO DÕI]", 0))]
    the_html = "".join(f'<div class="o"><div class="so">{_e(v)}</div><div class="nhan">{_e(n)}</div></div>'
                       for n, v in the)
    kl = []
    if not co_k:
        kl.append("<p><i>Chưa có kết quả đánh giá cho phiên này.</i></p>")
    elif not dem.get("[NÊN MUA]") and not dem.get("[MUA CÓ ĐIỀU KIỆN]"):
        kl.append('<p class="tom-tat">Phiên này <b>chưa có mã đủ điều kiện mua</b>. Xem danh sách theo dõi bên dưới.</p>')
    for nhom, lop, ten, mo_ta in NHOM_NGOAI if co_k else ():
        ds = k[k["Kết luận"] == nhom]
        if not len(ds):
            continue
        kl.append(f'<h3>{_e(ten)} <span class="chu-phu">– {_e(mo_ta)}</span></h3>')
        for _, r in ds.iterrows():
            co_3r = isinstance(r.get("MT 3R"), (int, float)) and r.get("MT 3R") == r.get("MT 3R")
            dong = [("Vùng mua", _e(r["Vùng mua"]))]
            if isinstance(r.get("Đặt LO"), (int, float)) and r.get("Đặt LO") == r.get("Đặt LO"):
                dong.append(("Giá đặt", f'{f2(r["Đặt LO"])} <span class="chu-phu">(lệnh LO)</span>'))
            dong += [("Cắt lỗ", f'{f2(r["Cắt lỗ"])} <span class="chu-phu">({f2(r["Cắt lỗ %"], 1)}%)</span>'),
                     ("Mục tiêu", f'1R {f2(r["Mục tiêu"])} → 3R {f2(r["MT 3R"])}' if co_3r else
                      f'{f2(r["Mục tiêu"])} (+{f2(r["Mục tiêu %"], 1)}%)')]
            for n, c in (("Vô hiệu khi", "Vô hiệu khi"), ("Điểm mạnh", "Điểm mạnh"), ("Cần chờ", "Cần chờ")):
                if chu(r.get(c)):
                    dong.append((n, _e(r[c])))
            luu_y = "; ".join(x for x in (chu(r.get("Điểm yếu")), chu(r.get("Rủi ro / lưu ý"))) if x)
            if luu_y:
                dong.append(("Lưu ý", _e(luu_y)))
            kl.append(f'<div class="ma {lop}"><div class="dau"><span class="ten">{_e(r["Mã"])}</span>'
                      f'<span class="nhan-nhom {lop}">{_e(r["Hành động"])}</span>'
                      f'<span class="diem">giá {f2(r["Giá"])}</span></div>'
                      '<table class="kh so-lieu">' + "".join(f"<tr><th>{_e(n)}</th><td>{v}</td></tr>" for n, v in dong)
                      + "</table></div>")
    td = k[k["Kết luận"] == "[THEO DÕI]"] if co_k else []
    if len(td):
        kl.append('<h3>Theo dõi <span class="chu-phu">– chưa mua, chờ thêm điều kiện</span></h3><div class="cuon"><table>'
                  '<tr><th>Mã</th><th style="text-align:left">Cần chờ</th></tr>' + "".join(
                      f'<tr><td>{_e(r["Mã"])}</td><td style="text-align:left;white-space:normal">'
                      f'{_e(r["Cần chờ"] or "tín hiệu rõ hơn")}</td></tr>' for _, r in td.iterrows()) + "</table></div>")
    bd = "".join(_anh(p) for p in anh)
    cach_doc = '<table class="kh">' + "".join(f"<tr><th>{_e(a)}</th><td>{_e(b)}</td></tr>" for a, b in CACH_DOC) + "</table>"
    muc = [("ket-luan", "Danh sách"), ("cach-doc", "Cách đọc")] + ([("bieu-do", "Biểu đồ")] if bd else [])
    nav = "".join(f'<a href="#{a}">{_e(t)}</a>' for a, t in muc)
    noi_dung = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Cổ phiếu đáng chú ý – {_e(phien)}</title>
<style>{CSS}</style></head><body>
<header><div class="khung"><p class="nho">Bộ lọc cổ phiếu · phiên {_e(phien)}</p>
<h1>Cổ phiếu đáng chú ý</h1><p class="mo-ta">Các mã có xu hướng và nền tảng tốt, kèm vùng mua, cắt lỗ và mục tiêu
cho phiên giao dịch tiếp theo.</p>{_thi_truong_ngoai(thi_truong)}</div></header>
<nav><div class="khung">{nav}</div></nav>
<main><div class="the">{the_html}</div>
<h2 id="ket-luan">Danh sách</h2>{"".join(kl)}
<h2 id="cach-doc">Cách đọc</h2>{cach_doc}
{f'<h2 id="bieu-do">Biểu đồ</h2>{bd}' if bd else ""}
</main><footer>Cập nhật {datetime.now():%d/%m/%Y %H:%M} · Thông tin chỉ để tham khảo, dựa trên dữ liệu quá khứ, không
phải lời mời mua bán chứng khoán. Người đọc tự chịu trách nhiệm với quyết định đầu tư của mình.</footer>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(noi_dung)
    return path
