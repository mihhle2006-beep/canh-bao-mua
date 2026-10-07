# -*- coding: utf-8 -*-
"""
TRANG TỔNG HỢP – 1 file HTML tự chứa (không thư viện ngoài) gom những thứ đang rải rác qua Telegram & Excel:
  ① Sức khoẻ thị trường: điểm 8 chỉ báo, CL đang áp dụng, VN-Index đi ngang hay có xu hướng
  ② Tín hiệu hôm nay: danh sách mua phiên tới (tin tổng kết) + trạng thái điểm vào 15' trong phiên
  ③ Danh mục giả lập: NAV so với VN-Index, vị thế, lệnh gần đây (canh_bao/giao_dich_ao.py)
  ④ Độ chính xác của bot: ĐÚNG/SAI theo từng loại tín hiệu (lich_su_danh_gia.csv)
  ⑤ (chỉ bản RIÊNG) danh mục thật: lãi/lỗ, cắt lỗ, hành động – KHÔNG bao giờ ghi vào docs/

Chỉ đọc file trạng thái (không cần ptcp, không tải giá) → dựng lại được sau mỗi lần chạy, kể cả trong phiên.
Bản công khai: docs/index.html → bật GitHub Pages (Settings → Pages → Branch main, thư mục /docs).
"""
import html
import json
import os

import numpy as np
import pandas as pd

from . import cau_hinh as C
from . import giao_dich_ao as GA

FILE_RIENG = "trang_tong_hop_rieng.html"


def _f(x, le=2, dau=False):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "–"
    if x != x:
        return "–"
    s = f"{x:+,.{le}f}" if dau else f"{x:,.{le}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")          # kiểu Việt Nam: 78.700,5


def _e(x):
    return html.escape("" if x is None or (isinstance(x, float) and x != x) else str(x))


def _doc_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _doc_csv(path):
    try:
        return pd.read_csv(path, encoding="utf-8")
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _sach(v):
    if isinstance(v, (pd.Timestamp, np.datetime64)):
        return f"{pd.Timestamp(v):%Y-%m-%d}"
    if isinstance(v, (np.floating, float)):
        return None if v != v else float(v)
    if isinstance(v, (np.integer, np.bool_)):
        return v.item()
    return v


# ------------------------------------------------------------------ lưu dữ liệu thị trường (gọi lúc tổng kết)
def luu_thi_truong(ra, bay_gio, ds=None, path=None):
    """Ghi điểm thị trường & toàn bộ khuyến nghị (đều CÔNG KHAI – đã có trong tin) vào trang_thai_chien_luoc.json."""
    path = path or C.FILE_TRANG_THAI_CL
    cu = _doc_json(path)
    d = ra["doc"]
    bang = d.get("bang")
    cu["thi_truong"] = {
        "ngay": f"{pd.Timestamp(d['ngay']):%Y-%m-%d}", "diem": int(d["diem"]), "so_chi_bao": int(d["so_chi_bao"]),
        "vni": _sach(ra.get("vni")), "cl": int(ra["cl"]), "ten_cl": str(ra["ten_cl"][ra["cl"]]),
        "ty_trong": {k: _sach(v) for k, v in ra["ty_trong"].items()}, "dieu_kien_doi": d.get("dieu_kien_doi", ""),
        "di_ngang": {k: _sach(v) for k, v in (ra.get("di_ngang") or {}).items()} or None,
        "chi_bao": [{"ten": str(r["Chỉ báo"]), "dat": bool(r["Đạt"]), "chi_tiet": str(r.get("Chi tiết") or "")}
                    for _, r in bang.iterrows()] if bang is not None else [],
        "cap_nhat": f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}"}
    if ds is not None:
        cu["khuyen_nghi"] = [{k: _sach(k_[k]) for k in ("ma", "nhom", "tp", "gia", "tu", "den", "cl", "mt1", "mt3",
                                                         "rui_ro", "lai_ht", "ly_do", "hieu_luc") if k in k_}
                             for k_ in ds]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cu, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ độ chính xác
def do_chinh_xac(nk):
    """Nhật ký (lich_su_danh_gia.csv) → bảng theo loại + nhóm: số tín hiệu, đúng, sai, chờ, % đúng, TB lãi/lỗ."""
    if nk is None or not len(nk) or "ket_qua" not in nk:
        return pd.DataFrame(columns=["Loại", "Nhóm", "Tổng", "Đúng", "Sai", "Đang chờ", "Đúng %", "TB lãi/lỗ %"])
    nk = nk.copy()
    nk["nhom"] = nk.get("nhom", "").fillna("")
    out = []
    for (loai, nhom), g in nk.groupby(["loai", "nhom"], sort=True):
        kq = g.ket_qua.astype(str)
        dung, sai = int((kq == "ĐÚNG").sum()), int((kq == "SAI").sum())
        p = pd.to_numeric(g.loc[kq.isin(["ĐÚNG", "SAI"]), "ket_qua_pct"], errors="coerce").dropna()
        out.append({"Loại": loai, "Nhóm": nhom, "Tổng": len(g), "Đúng": dung, "Sai": sai,
                    "Đang chờ": int((kq == "ĐANG CHỜ").sum()),
                    "Đúng %": dung / (dung + sai) * 100 if dung + sai else np.nan,
                    "TB lãi/lỗ %": float(p.mean()) if len(p) else np.nan})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ biểu đồ đường vốn (SVG inline)
def _svg_von(von):
    v = von.dropna(subset=["nav"]) if len(von) else von
    if len(v) < 2:
        return '<p class="mo">Chưa đủ phiên để vẽ đường vốn – bot giao dịch giả lập từ phiên sau ngày bắt đầu.</p>'
    W, H, L, R, T, B = 640, 220, 44, 12, 12, 26
    nav = (v.nav.astype(float) / float(v.nav.iloc[0]) - 1) * 100
    vn = v.vni.astype(float)
    vn = (vn / vn.dropna().iloc[0] - 1) * 100 if vn.notna().any() else vn
    gt = pd.concat([nav, vn.dropna(), pd.Series([0.0])])
    lo, hi = float(gt.min()), float(gt.max())
    if hi - lo < 2:
        lo, hi = lo - 1, hi + 1
    n = len(v)
    x = lambda i: L + (W - L - R) * i / (n - 1)                     # noqa: E731
    y = lambda p: T + (H - T - B) * (hi - p) / (hi - lo)            # noqa: E731

    def duong(s):
        return " ".join(f"{x(i):.1f},{y(p):.1f}" for i, p in enumerate(s) if p == p)

    vach = []
    for k in range(5):
        p = lo + (hi - lo) * k / 4
        vach.append(f'<line x1="{L}" x2="{W - R}" y1="{y(p):.1f}" y2="{y(p):.1f}" class="luoi"/>'
                    f'<text x="{L - 6}" y="{y(p) + 4:.1f}" text-anchor="end">{_f(p, 1)}%</text>')
    ngay = list(v.ngay.astype(str))
    neo = {0: "start", n - 1: "end"}
    nhan = "".join(f'<text x="{x(i):.1f}" y="{H - 6}" text-anchor="{neo.get(i, "middle")}">'
                   f'{pd.Timestamp(ngay[i]):%d/%m}</text>' for i in sorted({0, n // 2, n - 1}))
    return (f'<div class="bieu-do"><svg viewBox="0 0 {W} {H}" role="img" aria-label="NAV giả lập so với VN-Index (%)">'
            f'{"".join(vach)}<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" class="truc"/>{nhan}'
            f'<polyline points="{duong(vn)}" class="dg-vni"/><polyline points="{duong(nav)}" class="dg-nav"/></svg></div>'
            '<div class="chu-giai"><span class="k-nav"></span>NAV giả lập <span class="k-vni"></span>VN-Index</div>')


# ------------------------------------------------------------------ các khối HTML
def _bang(cot, dong, lop=""):
    if not dong:
        return '<p class="mo">Không có.</p>'
    th = "".join(f"<th>{_e(c)}</th>" for c in cot)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in d) + "</tr>" for d in dong)
    return f'<div class="cuon"><table class="{lop}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def _the(nhan, gia, phu="", lop=""):
    return (f'<div class="the {lop}"><div class="nhan">{_e(nhan)}</div><div class="gia">{gia}</div>'
            f'<div class="phu">{phu}</div></div>')


def _mau(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return ""
    return "" if x != x or x == 0 else ("tang" if x > 0 else "giam")


def _khoi_thi_truong(tt):
    if not tt:
        return '<p class="mo">Chưa có dữ liệu – chờ lần tổng kết 15:20 đầu tiên.</p>'
    w = tt.get("ty_trong") or {}
    chia = " · ".join(f"{'VN-Index' if k == 'VNI' else k} {float(w[k]) * 100:.0f}%" for k in ("A0", "B", "VNI")
                      if float(w.get(k) or 0) > 0)
    n, d = tt["so_chi_bao"], tt["diem"]
    vach = "".join(f'<span class="{"bat" if i < d else ""}"></span>' for i in range(n))
    ng = tt.get("di_ngang")
    xu = ("↔ Đi ngang" if ng["dang"] else "↗ Có xu hướng") + f" (biên {_f(ng['bien'], 1)}%)" if ng else "–"
    the = (_the("VN-Index", _f(tt.get("vni")), f"phiên {pd.Timestamp(tt['ngay']):%d/%m/%Y}")
           + _the("Điểm thị trường", f"{d}/{n}", f'<span class="vach">{vach}</span>')
           + _the("Chiến lược", f"CL{tt['cl']}", _e(chia))
           + _the("Trạng thái VN-Index", _e(xu.split(" (")[0]), _e(xu[len(xu.split(" (")[0]):].strip(" ()"))))
    ds = "".join(f'<li class="{"dat" if c["dat"] else "truot"}"><b>{"✔" if c["dat"] else "✘"}</b> {_e(c["ten"])}'
                 + (f' <span class="mo">– {_e(c["chi_tiet"])}</span>' if c.get("chi_tiet") else "") + "</li>"
                 for c in tt.get("chi_bao", []))
    return (f'<div class="luoi-the">{the}</div><p><b>{_e(tt.get("ten_cl"))}</b>'
            + (f' · <span class="mo">{_e(tt["dieu_kien_doi"])}</span>' if tt.get("dieu_kien_doi") else "")
            + f'</p><ul class="chi-bao">{ds}</ul>')


TEN_NHOM = {"MUA_MOI": "🟢 Mua mới", "VAO_NHU_MOI": "✅ Vào như lệnh mới", "VAO_NUA": "🟡 Vào ½",
            "CHO": "⏳ Chờ điều chỉnh", "DUOI_VON": "⛔ HT đang lỗ", "BAN": "⛔ HT sắp bán"}


def _khoi_tin_hieu(cl, cb):
    kn = cl.get("khuyen_nghi")
    if kn is None:                                                   # file cũ: chỉ có danh sách mua
        kn = (cl.get("ds_mua") or {}).get("ma") or []
    hl = (cl.get("ds_mua") or {}).get("hieu_luc")
    mua = [k for k in kn if k.get("nhom") in GA.NHOM_MUA]
    khac = [k for k in kn if k.get("nhom") not in GA.NHOM_MUA]
    out = [f"<h3>Danh sách mua phiên {pd.Timestamp(hl):%d/%m}</h3>" if hl else "<h3>Danh sách mua phiên tới</h3>",
           _bang(["Mã", "Nhóm", "Giá", "Vùng mua", "Cắt lỗ", "MT 1R → 3R", "Lý do"],
                 [[f"<b>{_e(k['ma'])}</b>", TEN_NHOM.get(k.get("nhom"), _e(k.get("nhom"))), _f(k.get("gia")),
                   f"{_f(k.get('tu'))}–{_f(k.get('den'))}", _f(k.get("cl")),
                   f"{_f(k.get('mt1'))} → {_f(k.get('mt3'))}", f'<span class="mo">{_e(k.get("ly_do"))}</span>']
                  for k in mua])]
    if khac:
        out.append('<p class="mo">' + " · ".join(f"{TEN_NHOM.get(k.get('nhom'), _e(k.get('nhom')))} "
                                                 f"<b>{_e(k['ma'])}</b>" for k in khac) + "</p>")
    p = cb.get("_15p_hom_nay")
    if p and p.get("ds"):
        out += [f"<h3>Điểm vào 15' phiên {pd.Timestamp(p['ngay']):%d/%m} · cách vào {_e(p.get('cach_vao'))}</h3>",
                _bang(["Mã", "Nhóm", "Vùng", "Giá", "Trạng thái", "Giờ", "Giá mua", "Lý do"],
                      [[f"<b>{_e(r.get('Mã'))}</b>", _e(r.get("Nhóm")), _e(r.get("Vùng")), _f(r.get("Giá")),
                        f'<span class="nhan-tt {"tang" if r.get("Trạng thái") == "MUA" else ""}">'
                        f'{_e(r.get("Trạng thái"))}</span>', _e(r.get("Giờ")), _f(r.get("Giá mua")),
                        f'<span class="mo">{_e(r.get("Lý do"))}</span>'] for r in p["ds"]])]
    return "".join(out)


def _khoi_gia_lap(tt, lenh, von, kq_bt):
    if not tt:
        return '<p class="mo">Chưa bắt đầu – tài khoản ảo được mở ở lần tổng kết 15:20 kế tiếp.</p>'
    x = GA.thong_ke(tt, lenh, von)
    bt = GA._bt_goc(kq_bt)
    con = C.SO_PHIEN_GIA_LAP_TOI_THIEU - x["so_phien"]
    the = (_the("NAV", f"{_f(x['nav'] / 1000, 0)} tr", f'<span class="{_mau(x["lai_pct"])}">'
                f'{_f(x["lai_pct"], 1, True)}%</span> từ {pd.Timestamp(tt["bat_dau"]):%d/%m/%Y}')
           + _the("VN-Index cùng kỳ", f'<span class="{_mau(x["vni_pct"])}">{_f(x["vni_pct"], 1, True)}%</span>',
                  f"{x['so_phien']} phiên")
           + _the("Sụt giảm lớn nhất", f"{_f(x['mdd'], 1)}%", f"backtest {_f(bt['MDD %'], 1)}%" if bt else "")
           + _the("Lệnh đã đóng", f"{x['so_lenh']}",
                  f"thắng {_f(x['thang_pct'], 0)}% · TB {_f(x['tb_lenh_pct'], 2, True)}%"
                  + (f"<br>backtest: {_f(bt['Thắng %'], 0)}% · {_f(bt['TB/lệnh %'], 2, True)}%" if bt else "")))
    tien = ('<p class="canh-bao">Còn <b>%d phiên</b> nữa mới đủ %d phiên (~3 tháng) để đánh giá – chưa nên dùng tiền '
            'thật.</p>' % (con, C.SO_PHIEN_GIA_LAP_TOI_THIEU) if con > 0 else
            '<p class="tot">Đã đủ %d phiên – so kết quả với backtest trước khi dùng tiền thật.</p>'
            % C.SO_PHIEN_GIA_LAP_TOI_THIEU)
    vt = [[f"<b>{_e(m)}</b>", _e(TEN_NHOM.get(v.get("nhom"), v.get("nhom"))), f"{pd.Timestamp(v['ngay_mua']):%d/%m}",
           _f(v["gia_mua"]), f"{int(v['so_cp']):,}".replace(",", "."), _f(v["cat_lo"]),
           f"tầng {v.get('tang', 0)}" + (f" · <b>bán: {_e(tt['ban_cho'][m])}</b>" if m in tt["ban_cho"] else "")]
          for m, v in sorted(tt["vi_the"].items())]
    ln = lenh.tail(15).iloc[::-1] if len(lenh) else lenh
    lg = [[f"<b>{_e(r.ma)}</b>", f"{pd.Timestamp(r.ngay_mua):%d/%m} → {pd.Timestamp(r.ngay_ban):%d/%m}",
           f"{_f(r.gia_mua)} → {_f(r.gia_ban)}", f'<span class="{_mau(r.lai_pct)}">{_f(r.lai_pct, 1, True)}%</span>',
           _e(r.ly_do)] for r in ln.itertuples()]
    cho = ", ".join(f"{o['ma']} ({_f(o.get('tu'))}–{_f(o.get('den'))})" for o in tt["lenh_cho"])
    return (f'<div class="luoi-the">{the}</div>{tien}{_svg_von(von)}'
            f'<h3>Đang giữ ({len(vt)}) · tiền mặt {_f(x["tien_pct"], 0)}%</h3>'
            + _bang(["Mã", "Nhóm", "Ngày mua", "Giá mua", "Số CP", "Cắt lỗ", "Hệ thoát"], vt)
            + (f'<p class="mo">Lệnh mua chờ phiên tới: {_e(cho)}</p>' if cho else "")
            + "<h3>Lệnh gần đây</h3>" + _bang(["Mã", "Ngày", "Giá", "Lãi/lỗ sau phí", "Lý do bán"], lg))


def _khoi_chinh_xac(nk):
    b = do_chinh_xac(nk)
    if not len(b):
        return '<p class="mo">Chưa có tín hiệu nào được chấm.</p>'
    dong = [[_e(r["Loại"]), _e(r["Nhóm"]), r["Tổng"], r["Đúng"], r["Sai"], r["Đang chờ"],
             (f'<span class="thanh"><i style="width:{r["Đúng %"]:.0f}%"></i></span> {_f(r["Đúng %"], 0)}%'
              if r["Đúng %"] == r["Đúng %"] else "–")
             + (' <span class="mo">(ít mẫu)</span>' if 0 < r["Đúng"] + r["Sai"] < 30 else ""),
             f'<span class="{_mau(r["TB lãi/lỗ %"])}">{_f(r["TB lãi/lỗ %"], 2, True)}%</span>'
             if r["TB lãi/lỗ %"] == r["TB lãi/lỗ %"] else "–"]
            for _, r in b.iterrows()]
    return _bang(["Loại", "Nhóm", "Tổng", "Đúng", "Sai", "Đang chờ", "Đúng %", "TB lãi/lỗ"], dong)


def _khoi_rieng(giu):
    from .vi_the import NHAN
    dong = []
    for vt, kb, mt in giu:
        dong.append([f"<b>{_e(vt['ma'])}</b>", f"{vt['so_cp']:,.0f}".replace(",", "."), _f(vt.get("gia_von")),
                     _f(kb.get("gia")),
                     f'<span class="{_mau(kb.get("lai_lo_pct"))}">{_f(kb.get("lai_lo_pct"), 1, True)}%</span>',
                     _f(kb.get("cat_lo")), _e(NHAN.get(kb.get("muc"), kb.get("muc")))
                     + (" · ➕ đủ điều kiện mua thêm" if (mt or {}).get("du") else "")])
    return _bang(["Mã", "Số CP", "Giá vốn", "Giá", "Lãi/lỗ", "Cắt lỗ", "Hành động"], dong)


CSS = """
:root{--nen:#f6f7f9;--the:#fff;--chu:#1b1f24;--mo:#5f6b7a;--vien:#e3e6ea;--nhan:#2457c5;--tang:#0f8a4b;
--giam:#c8352b;--vang:#9a6700;--vni:#8a94a3;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--nen:#0f1216;--the:#181c22;--chu:#e6e9ee;
--mo:#97a1ae;--vien:#2a3038;--nhan:#7aa7ff;--tang:#3ccf86;--giam:#ff7b72;--vang:#e3b341;--vni:#6e7781;color-scheme:dark}}
:root[data-theme="dark"]{--nen:#0f1216;--the:#181c22;--chu:#e6e9ee;--mo:#97a1ae;--vien:#2a3038;--nhan:#7aa7ff;
--tang:#3ccf86;--giam:#ff7b72;--vang:#e3b341;--vni:#6e7781;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--nen);color:var(--chu);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:20px 16px 48px}
header h1{font-size:22px;margin:0}header p{margin:4px 0 0;color:var(--mo)}
nav{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0}nav a{color:var(--nhan);text-decoration:none;
padding:4px 10px;border:1px solid var(--vien);border-radius:999px;font-size:13px;background:var(--the)}
section{background:var(--the);border:1px solid var(--vien);border-radius:12px;padding:16px;margin:16px 0}
section h2{font-size:17px;margin:0 0 12px}h3{font-size:14px;margin:18px 0 8px;color:var(--mo)}
.luoi-the{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.the{border:1px solid var(--vien);border-radius:10px;padding:10px 12px}.the .nhan{font-size:12px;color:var(--mo)}
.the .gia{font-size:22px;font-weight:650;font-variant-numeric:tabular-nums}.the .phu{font-size:12px;color:var(--mo)}
.vach{display:inline-flex;gap:3px;margin-top:4px}.vach span{width:14px;height:8px;border-radius:2px;
background:var(--vien)}.vach span.bat{background:var(--nhan)}
.chi-bao{list-style:none;padding:0;margin:8px 0 0;columns:2 280px}.chi-bao li{margin:2px 0;break-inside:avoid}
.chi-bao .dat b{color:var(--tang)}.chi-bao .truot b{color:var(--giam)}
.cuon{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:6px 8px;border-bottom:1px solid var(--vien);text-align:left;white-space:nowrap}
th{font-weight:600;color:var(--mo);font-size:12px}td{font-variant-numeric:tabular-nums}
.mo{color:var(--mo)}.tang{color:var(--tang)}.giam{color:var(--giam)}
.nhan-tt{padding:1px 6px;border-radius:4px;border:1px solid var(--vien)}
.canh-bao{color:var(--vang)}.tot{color:var(--tang)}
.thanh{display:inline-block;width:60px;height:6px;background:var(--vien);border-radius:3px;vertical-align:middle}
.thanh i{display:block;height:100%;background:var(--tang);border-radius:3px}
.bieu-do{overflow-x:auto}svg{width:100%;min-width:520px;height:auto;margin-top:8px}svg text{fill:var(--mo);font-size:11px}
.luoi{stroke:var(--vien)}.truc{stroke:var(--mo);stroke-dasharray:3 3}
.dg-nav{fill:none;stroke:var(--nhan);stroke-width:2.2}.dg-vni{fill:none;stroke:var(--vni);stroke-width:1.6}
.chu-giai{font-size:12px;color:var(--mo)}.chu-giai span{display:inline-block;width:14px;height:3px;
margin:0 4px 3px 10px;vertical-align:middle}.k-nav{background:var(--nhan)}.k-vni{background:var(--vni)}
section.rieng{border-color:var(--vang)}footer{color:var(--mo);font-size:12px;text-align:center}
@media (max-width:560px){.the .gia{font-size:19px}th,td{padding:5px 6px}}
"""


def tao(path=None, giu=None, bay_gio=None, kq_bt=None):
    """Dựng trang. giu = [(vt, kb, mt)] → thêm mục danh mục thật (chỉ dùng cho bản RIÊNG, không ghi vào docs/)."""
    path = path or (FILE_RIENG if giu else C.FILE_TRANG)
    cl, cb = _doc_json(C.FILE_TRANG_THAI_CL), _doc_json(C.FILE_TRANG_THAI)
    tt = GA.doc()
    lenh, von = GA.doc_csv(GA.FILE_LENH, GA.COT_LENH), GA.doc_csv(GA.FILE_VON, GA.COT_VON)
    if kq_bt is None:
        kq_bt = _doc_json(C.FILE_BACKTEST)
    luc = pd.Timestamp(bay_gio) if bay_gio is not None else None
    muc = [("thi-truong", "① Sức khoẻ thị trường", _khoi_thi_truong(cl.get("thi_truong"))),
           ("tin-hieu", "② Tín hiệu hôm nay", _khoi_tin_hieu(cl, cb)),
           ("gia-lap", "③ Danh mục giả lập (vốn ảo)", _khoi_gia_lap(tt, lenh, von, kq_bt)),
           ("chinh-xac", "④ Độ chính xác của bot", _khoi_chinh_xac(_doc_csv("lich_su_danh_gia.csv")))]
    if giu:
        muc.insert(0, ("danh-muc", "💼 Danh mục thật (riêng tư)", _khoi_rieng(giu)))
    nav = "".join(f'<a href="#{i}">{_e(t)}</a>' for i, t, _ in muc)
    lop = {"danh-muc": ' class="rieng"'}
    than = "".join(f'<section id="{i}"{lop.get(i, "")}><h2>{_e(t)}</h2>{k}</section>' for i, t, k in muc)
    trang = (f'<!doctype html><html lang="vi"><head><meta charset="utf-8">'
             f'<meta name="viewport" content="width=device-width,initial-scale=1">'
             f'<title>Bảng tổng hợp{" (riêng)" if giu else ""}</title><style>{CSS}</style></head><body><main>'
             f'<header><h1>Bảng tổng hợp cảnh báo</h1><p>Cập nhật '
             f'{f"{luc:%H:%M %d/%m/%Y}" if luc is not None else "–"} (giờ VN)'
             f'{" · bản RIÊNG – không chia sẻ" if giu else ""}</p></header><nav>{nav}</nav>{than}'
             f'<footer>Công cụ tham khảo – không phải khuyến nghị đầu tư.</footer></main></body></html>')
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(trang)
    return path
