# -*- coding: utf-8 -*-
"""
ĐỀ XUẤT ĐIỀU CHỈNH CẮT LỖ / CHỐT LỜI HẰNG NGÀY + GHI LẠI VÀO danh_muc.csv.

Mã ĐANG GIỮ – cắt lỗ chỉ DỜI LÊN, lấy mức CAO NHẤT trong các mốc hợp lệ (cách giá ≥ 1×ATR):
  • Kỹ thuật  : cắt lỗ thống nhất của ptcp hôm nay
  • Hoà vốn   : lãi ≥ 1R (R = giá vốn − cắt lỗ lúc mua) → dời về giá vốn + phí
  • Khoá lãi  : lãi ≥ 2R → dời lên giá vốn + 1R
  • Chandelier: giá đóng cửa cao nhất kể từ ngày mua − 3×ATR(14)   (giữ ≥ 5 phiên)
Chốt lời:
  • Đã chạm mục tiêu đã đặt → chốt 1 phần, mục tiêu mới = mục tiêu kỹ thuật kế tiếp (tự áp dụng)
  • Cách mục tiêu ≤ 2%      → chuẩn bị chốt CHOT_TUNG_PHAN_PCT% (ptcp/cau_hinh.py)
  • Tuần mạnh & còn mục tiêu kỹ thuật xa hơn → có thể NÂNG mục tiêu
  • Tuần yếu & có kháng cự gần hơn          → nên HẠ mục tiêu về kháng cự đó
Mã THEO DÕI: giá mua đề xuất (để R/R ≥ 2), vùng mua, cắt lỗ & mục tiêu nếu mua.
"""
import os
import shutil

import numpy as np
import pandas as pd

from ptcp import cau_hinh as _ptcp_cfg
from .cau_hinh import AP_DUNG_CAT_LO_DE_XUAT, CHANDELIER_ATR, KHOANG_CACH_ATR_MIN
from .tien_ich import co

COT_GHI = ["ngay_mua", "gia_von", "cat_lo_dat", "muc_tieu_dat", "cat_lo_goc", "muc_tieu_luc_mua",
           "muc_tieu_luc_mua_2", "muc_tieu_tiep_theo", "lai_lo_pct", "vni_tu_ngay_mua_pct", "chenh_lech_vni",
           "gia_mua_de_xuat", "cat_lo_de_xuat", "muc_tieu_de_xuat", "de_xuat", "cap_nhat"]


def atr14(df):
    c = df.close
    tr = pd.concat([df.high - df.low, (df.high - c.shift()).abs(), (df.low - c.shift()).abs()], axis=1).max(axis=1)
    return float(tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1])


def _chi_phi_pct():
    try:
        from ptcp.thong_ke import _chi_phi
        return _chi_phi()
    except Exception:
        return 0.6


def _de_xuat_giu(r, md):
    ht, gv = r["ht"], r["gia_von"] or r["ht"]
    df = r["df"]
    atr = atr14(df)
    cl_hien, mt_hien = md["cat_lo_moi"], md["muc_tieu_moi"]
    cl0 = md.get("cat_lo_ban_dau") or cl_hien
    R = gv - cl0 if gv > cl0 else gv * 0.07
    ung = [("kỹ thuật (ptcp)", r["cat_lo"])]
    if ht >= gv + _ptcp_cfg.HOA_VON_KHI_R * R:
        ung.append((f"lãi ≥ {_ptcp_cfg.HOA_VON_KHI_R:g}R → hoà vốn", gv * (1 + _chi_phi_pct() / 100)))
    if ht >= gv + 2 * R:
        ung.append(("lãi ≥ 2R → khoá 1R", gv + R))
    nm = md.get("ngay_mua")
    if nm:
        sau = df[df.index >= pd.Timestamp(nm)]
        if len(sau) >= 5:
            ung.append((f"Chandelier (đỉnh {sau.close.max():,.2f} − {CHANDELIER_ATR:g}×ATR)",
                        sau.close.max() - CHANDELIER_ATR * atr))
    # cắt lỗ phải cách giá ≥ KHOANG_CACH_ATR_MIN × ATR – sát hơn dễ bị nhiễu trong phiên quét mất
    hop_le = [(t, g) for t, g in ung if co(g) and g <= ht - KHOANG_CACH_ATR_MIN * atr]
    ly_do_cl, cl_dx = "giữ nguyên", cl_hien
    if hop_le:
        t, g = max(hop_le, key=lambda x: x[1])
        if g > cl_hien + 1e-9:
            ly_do_cl, cl_dx = f"DỜI LÊN theo {t}", g
    if md["cham_cl"]:
        ly_do_cl, cl_dx = f"ĐÃ THỦNG cắt lỗ {md['cat_lo_dat']:,.2f} → CẮT LỖ NGAY", md["cat_lo_dat"]

    nxt = r["mt_ngay"]
    tg = r["tg"]
    mt_dx, ly_do_mt = mt_hien, "giữ nguyên"
    if md["cham_mt"]:
        ly_do_mt = (f"ĐÃ CHẠM mục tiêu {md['muc_tieu_dat']:,.2f} → chốt {_ptcp_cfg.CHOT_TUNG_PHAN_PCT:g}%, phần còn lại "
                    f"theo cắt lỗ động; mục tiêu mới {mt_hien:,.2f}")
    elif ht >= mt_hien * 0.98:
        ly_do_mt = f"sát mục tiêu (còn {(mt_hien / ht - 1) * 100:.1f}%) → chuẩn bị chốt {_ptcp_cfg.CHOT_TUNG_PHAN_PCT:g}%"
    elif tg.get("tuan_rat_tot") and co(nxt) and nxt > mt_hien * 1.02:
        mt_dx, ly_do_mt = nxt, f"tuần mạnh → có thể NÂNG lên {nxt:,.2f}"
    elif not tg.get("tuan_ok") and co(nxt) and ht * 1.01 < nxt < mt_hien:
        mt_dx, ly_do_mt = nxt, f"tuần yếu → nên HẠ về kháng cự gần {nxt:,.2f}"
    lai = (ht / gv - 1) * 100
    kh = r.get("kh") or {}
    v = kh.get("so_vni") or {}
    mt2 = kh.get("muc_tieu_2")
    return {"Cắt lỗ gốc (từ giá mua)": kh.get("cat_lo_goc", np.nan),
            "Mục tiêu lúc mua": kh.get("muc_tieu_de_xuat", np.nan),
            "Phương pháp MT lúc mua": kh.get("nguon_muc_tieu", ""),
            "Mốc kế tiếp lúc mua": mt2[0] if mt2 else np.nan,
            "Mục tiêu tiếp theo": kh.get("muc_tieu_tiep_theo", np.nan) if kh.get("da_vuot_muc_tieu") else np.nan,
            "Nguồn MT tiếp theo": kh.get("nguon_muc_tieu_tiep", "") if kh.get("da_vuot_muc_tieu") else "",
            "R/R từ giá mua": kh.get("rr_tu_gia_mua", np.nan), "VN-Index từ ngày mua %": v.get("vni_pct", np.nan),
            "Chênh lệch vs VNI (điểm %)": v.get("chenh_lech", np.nan),
            "Mã": r["symbol"], "Trạng thái": "Đang giữ", "Ngày mua": nm or "", "Nguồn ngày mua": md.get("nguon_ngay_mua", ""),
            "Giá vốn": gv, "Giá HT": ht, "Lãi/lỗ %": lai, "R (1R)": R, "Lãi theo R": (ht - gv) / R if R else np.nan,
            "Cắt lỗ hiện tại": cl_hien, "Cắt lỗ đề xuất": cl_dx, "Lý do cắt lỗ": ly_do_cl,
            "Chốt lời hiện tại": mt_hien, "Chốt lời đề xuất": mt_dx, "Lý do chốt lời": ly_do_mt,
            "R/R còn lại": (mt_dx - ht) / (ht - cl_dx) if ht > cl_dx else np.nan,
            "Giá mua đề xuất": np.nan}


def _de_xuat_theo_doi(r):
    ht = r["ht"]
    gmax = r["qd"].get("gia_mua_max")
    gia_mua = min(ht, gmax) if co(gmax) and gmax > 0 else ht
    vung = r.get("vung_mua")
    ghi = f"{r['quyet_dinh']}"
    if vung:
        ghi += f"; vùng hỗ trợ {vung[0]:,.2f}–{vung[1]:,.2f}"
    return {"Mã": r["symbol"], "Trạng thái": "Theo dõi", "Ngày mua": "", "Nguồn ngày mua": "", "Giá vốn": np.nan,
            "Giá HT": ht, "Lãi/lỗ %": np.nan, "R (1R)": np.nan, "Lãi theo R": np.nan,
            "Cắt lỗ hiện tại": np.nan, "Cắt lỗ đề xuất": r["cat_lo"], "Lý do cắt lỗ": "nếu mua hôm nay",
            "Chốt lời hiện tại": np.nan, "Chốt lời đề xuất": r["mt_ngay"], "Lý do chốt lời": "mục tiêu kỹ thuật (ptcp)",
            "R/R còn lại": (r["mt_ngay"] - gia_mua) / (gia_mua - r["cat_lo"]) if gia_mua > r["cat_lo"] else np.nan,
            "Giá mua đề xuất": gia_mua, "Ghi chú": ghi + (" – chỉ mua ≤ giá này để R/R ≥ 2" if gia_mua < ht else "")}


def de_xuat(ds_kq, dm, tt_moi):
    """Bảng đề xuất; nếu AP_DUNG_CAT_LO_DE_XUAT → cắt lỗ đề xuất (chỉ cao hơn) được ghi vào trạng thái đã đặt."""
    rows = []
    for r in ds_kq:
        if r["so_cp"] > 0 and r["symbol"] in dm["md"]:
            x = _de_xuat_giu(r, dm["md"][r["symbol"]])
            if AP_DUNG_CAT_LO_DE_XUAT and r["symbol"] in tt_moi and x["Cắt lỗ đề xuất"] > tt_moi[r["symbol"]]["cat_lo"]:
                tt_moi[r["symbol"]]["cat_lo"] = x["Cắt lỗ đề xuất"]
            rows.append(x)
        else:
            rows.append(_de_xuat_theo_doi(r))
    return pd.DataFrame(rows)


def _txt(x, le=2):
    return "" if x is None or not co(x) else f"{x:.{le}f}"


def cap_nhat_csv(path, bang):
    """
    Ghi lại vào file danh mục (giữ nguyên mọi cột khác; sao lưu bản cũ .bak):
      đang giữ : ngay_mua (nếu trống), cat_lo_dat, muc_tieu_dat, de_xuat, cap_nhat
      theo dõi : gia_mua_de_xuat, cat_lo_de_xuat, muc_tieu_de_xuat, de_xuat, cap_nhat
    """
    if not path or not os.path.exists(path) or not len(bang):
        return False
    shutil.copyfile(path, path + ".bak")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    goc_cot = list(df.columns)
    khoa = {c.strip().lower(): c for c in df.columns}
    cot_ma = khoa.get("ma") or khoa.get("mã") or df.columns[0]
    for c in COT_GHI:
        if c not in khoa:
            df[c] = ""
            khoa[c] = c
    hom_nay = pd.Timestamp.today().strftime("%d/%m/%Y")
    b = bang.set_index("Mã")
    for i, ma in df[cot_ma].str.strip().str.upper().items():
        if ma not in b.index:
            continue
        x = b.loc[ma]
        def set_(c, v):
            df.at[i, khoa[c]] = v
        if x["Trạng thái"] == "Đang giữ":
            if not str(df.at[i, khoa["ngay_mua"]]).strip() and x["Ngày mua"]:
                set_("ngay_mua", pd.Timestamp(x["Ngày mua"]).strftime("%d/%m/%Y"))
            set_("cat_lo_dat", _txt(x["Cắt lỗ đề xuất"] if AP_DUNG_CAT_LO_DE_XUAT else x["Cắt lỗ hiện tại"]))
            set_("muc_tieu_dat", _txt(x["Chốt lời hiện tại"]))
            set_("cat_lo_goc", _txt(x.get("Cắt lỗ gốc (từ giá mua)")))
            set_("muc_tieu_luc_mua", _txt(x.get("Mục tiêu lúc mua")))
            set_("muc_tieu_luc_mua_2", _txt(x.get("Mốc kế tiếp lúc mua")))
            set_("muc_tieu_tiep_theo", _txt(x.get("Mục tiêu tiếp theo")))
            set_("lai_lo_pct", _txt(x["Lãi/lỗ %"], 1))
            set_("vni_tu_ngay_mua_pct", _txt(x.get("VN-Index từ ngày mua %"), 1))
            set_("chenh_lech_vni", _txt(x.get("Chênh lệch vs VNI (điểm %)"), 1))
            for c in ("gia_mua_de_xuat", "cat_lo_de_xuat", "muc_tieu_de_xuat"):
                set_(c, "")
            dx = f"CL: {x['Lý do cắt lỗ']} | TP: {x['Lý do chốt lời']}"
            if x["Nguồn ngày mua"] == "ngày đầu thấy vị thế":
                dx += " | ngày mua = ngày đầu thấy vị thế, hãy sửa nếu sai"
        else:
            for c in ("ngay_mua", "cat_lo_dat", "muc_tieu_dat", "cat_lo_goc", "muc_tieu_luc_mua", "muc_tieu_luc_mua_2",
                      "muc_tieu_tiep_theo", "lai_lo_pct", "vni_tu_ngay_mua_pct", "chenh_lech_vni"):
                # mức của vị thế cũ (đã bán) không dùng lại
                set_(c, "")
            set_("gia_mua_de_xuat", _txt(x["Giá mua đề xuất"]))
            set_("cat_lo_de_xuat", _txt(x["Cắt lỗ đề xuất"]))
            set_("muc_tieu_de_xuat", _txt(x["Chốt lời đề xuất"]))
            dx = str(x.get("Ghi chú", ""))
        set_("de_xuat", dx)
        set_("cap_nhat", hom_nay)
    bo = ["muc_tieu_2r", "muc_tieu_3r", "muc_tieu_tu_gia_mua"]          # cột bản trước (mục tiêu theo R) – bỏ
    thu_tu = [c for c in goc_cot + [c for c in df.columns if c not in goc_cot] if c not in bo]
    df[thu_tu].to_csv(path, index=False, encoding="utf-8-sig")
    return True
