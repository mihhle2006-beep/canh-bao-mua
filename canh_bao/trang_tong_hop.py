# -*- coding: utf-8 -*-
"""
TRANG TỔNG HỢP – 1 file HTML tự chứa (không thư viện ngoài) gom những thứ đang rải rác qua Telegram & Excel:
  ① Sức khoẻ thị trường: điểm 8 chỉ báo, CL đang áp dụng, VN-Index đi ngang hay có xu hướng
  ② Tín hiệu hôm nay: danh sách mua phiên tới (tin tổng kết) + trạng thái điểm vào 15' trong phiên
  ③ Độ chính xác của bot: ĐÚNG/SAI theo từng loại tín hiệu (lich_su_danh_gia.csv)
  (chỉ bản RIÊNG) danh mục thật: lãi/lỗ, cắt lỗ, hành động – KHÔNG bao giờ ghi vào docs/

Chỉ đọc file trạng thái (không cần ptcp, không tải giá) → dựng lại được sau mỗi lần chạy, kể cả trong phiên.
Bản công khai: docs/index.html → bật GitHub Pages (Settings → Pages → Branch main, thư mục /docs).
"""
import html
import json
import os

import numpy as np
import pandas as pd

from . import cau_hinh as C

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


NHOM_MUA = ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA")
TEN_NHOM = {"MUA_MOI": "🟢 Mua mới", "VAO_NHU_MOI": "✅ Vào như lệnh mới", "VAO_NUA": "🟡 Vào ½",
            "CHO": "⏳ Chờ điều chỉnh", "DUOI_VON": "⛔ HT đang lỗ", "BAN": "⛔ HT sắp bán"}


def _khoi_tin_hieu(cl, cb):
    kn = cl.get("khuyen_nghi")
    if kn is None:                                                   # file cũ: chỉ có danh sách mua
        kn = (cl.get("ds_mua") or {}).get("ma") or []
    hl = (cl.get("ds_mua") or {}).get("hieu_luc")
    mua = [k for k in kn if k.get("nhom") in NHOM_MUA]
    khac = [k for k in kn if k.get("nhom") not in NHOM_MUA]
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
:root{--nen:#f3f7f4;--the:#fff;--chu:#17211b;--mo:#5c6b62;--vien:#dfe7e1;--nhan:#15803d;--tang:#0f8a4b;
--giam:#c8352b;--vang:#9a6700;--vni:#8a94a3;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--nen:#0d1310;--the:#151d18;--chu:#e4ece6;
--mo:#93a59a;--vien:#26332b;--nhan:#4ade80;--tang:#3ccf86;--giam:#ff7b72;--vang:#e3b341;--vni:#6e7781;color-scheme:dark}}
:root[data-theme="dark"]{--nen:#0d1310;--the:#151d18;--chu:#e4ece6;--mo:#93a59a;--vien:#26332b;--nhan:#4ade80;
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
    luc = pd.Timestamp(bay_gio) if bay_gio is not None else None
    muc = [("thi-truong", "① Sức khoẻ thị trường", _khoi_thi_truong(cl.get("thi_truong"))),
           ("tin-hieu", "② Tín hiệu hôm nay", _khoi_tin_hieu(cl, cb)),
           ("chinh-xac", "③ Độ chính xác của bot", _khoi_chinh_xac(_doc_csv("lich_su_danh_gia.csv")))]
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
