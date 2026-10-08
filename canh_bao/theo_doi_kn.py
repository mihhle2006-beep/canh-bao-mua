# -*- coding: utf-8 -*-
"""
THEO DÕI KHUYẾN NGHỊ ĐÃ GỬI – "nếu đã mua theo khuyến nghị ngày X thì giờ làm gì", KHÔNG cần nhập danh mục.

Nguồn: nhật ký công khai lich_su_danh_gia.csv (nhat_ky.py) – mỗi khuyến nghị MUA của chiến lược (loai CHIEN_LUOC,
nhóm MUA) đã được chấm như 1 lệnh giả định: vào giá MỞ CỬA phiên sau nếu trong vùng mua (ngay_vao, gia_vao).
Với mỗi lệnh giả định CÒN MỞ, bot chấm lại bằng ĐÚNG hệ thoát của danh mục thật (vi_the.danh_gia_ban):
  🔴 BÁN       chạm cắt lỗ / đóng cửa tuần < MA10 tuần khi đã ≥ 3R / 63 phiên chưa đạt 1R
  ⬆ DỜI CẮT LỖ hệ thống nâng cắt lỗ cao hơn mức đã báo (≥ DOI_CAT_LO_TOI_THIEU_PCT %) – mỗi mức báo 1 lần
  ⚠ SÁT CẮT LỖ giá cách cắt lỗ ≤ GAN_CAT_LO_PCT %
  🟢 GIỮ       còn lại (kèm cắt lỗ hiện tại)
Mỗi mã 1 dòng (lấy lần vào ĐẦU TIÊN còn mở; các khuyến nghị MUA sau đó của cùng mã ghi kèm).
Lệnh giả định vừa ĐÓNG (nhật ký chấm xong) → báo 1 lần "đã bán … lãi/lỗ".
Trạng thái báo (mức cắt lỗ đã báo, lệnh đóng đã báo) lưu theo_doi_kn.json – chỉ chứa khuyến nghị công khai.
"""
import json

import numpy as np
import pandas as pd

from . import cau_hinh as C
from . import nhat_ky, vi_the

FILE = "theo_doi_kn.json"
SO_NGAY = getattr(C, "THEO_DOI_KN_NGAY", 150)          # chỉ xét khuyến nghị trong N ngày gần nhất
TOI_DA = getattr(C, "THEO_DOI_KN_TOI_DA", 15)          # tối đa số dòng trong tin
DONG = ("ĐÚNG", "SAI")
THU_TU = {"CAT_LO": 0, "BAN_TUAN": 0, "HET_HAN": 0, "DOI": 1, "GAN_CAT_LO": 2, "GIU": 3}


def doc_tt(path=FILE):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ghi_tt(tt, path=FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tt, f, ensure_ascii=False, indent=1)


def _f(x, n=2):
    return "–" if x is None or x != x else f"{x:,.{n}f}"


def _ngay(x):
    try:
        t = pd.Timestamp(x)
        return None if pd.isna(t) else t
    except (TypeError, ValueError):
        return None


def lenh_gia_dinh(nk, bay_gio):
    """→ (mở: {ma: dòng vào đầu tiên + 'them': [ngày khuyến nghị sau]}, đóng: [dòng]) – chỉ khuyến nghị MUA của chiến lược."""
    if nk is None or not len(nk):
        return {}, []
    x = nk[(nk["loai"] == "CHIEN_LUOC") & (nk["nhom"] == "MUA")].copy()
    x = x[x["ngay_vao"].map(_ngay).notna() & (pd.to_numeric(x["gia_vao"], errors="coerce") > 0)]
    x = x[pd.to_datetime(x["ngay"], errors="coerce") >= pd.Timestamp(bay_gio).normalize() - pd.Timedelta(days=SO_NGAY)]
    x = x.sort_values(["ngay_vao", "thoi_diem"])
    mo = {}
    for _, r in x[~x["ket_qua"].isin(DONG + ("BỎ QUA",))].iterrows():
        if r["ma"] in mo:
            mo[r["ma"]]["them"].append(str(r["ngay"]))
        else:
            mo[r["ma"]] = {**r.to_dict(), "them": []}
    return mo, [r.to_dict() for _, r in x[x["ket_qua"].isin(DONG)].iterrows()]


def danh_gia(mo, gia_ngay, tai, bay_gio, tt):
    """mo: lenh_gia_dinh()[0] → [(thứ tự, dòng tin)] và cập nhật tt["cat_lo"] (mức cắt lỗ đã báo)."""
    da_bao = tt.setdefault("cat_lo", {})
    ra = []
    for ma, r in mo.items():
        dn = (gia_ngay or {}).get(ma)
        if dn is None and tai is not None:
            try:
                dn = tai(ma)
            except Exception:
                dn = None
        if dn is None or not len(dn):
            continue
        dn = vi_the._phien_da_dong(dn, bay_gio)
        if dn is None or not len(dn):
            continue
        khoa = f"{ma}|{r['ngay_vao']}"
        cl_bao = da_bao.get(khoa) or float(r["cat_lo"])
        v = {"ma": ma, "so_cp": None, "gia_von": float(r["gia_vao"]), "cat_lo": cl_bao,
             "cat_lo_goc": float(r["cat_lo"]), "muc_tieu": None, "ngay_mua": str(r["ngay_vao"]),
             "ngay_mua_them": "", "so_lan_mua_them": 0}
        kb = vi_the.danh_gia_ban(v, {"ma": ma, "gia": float(dn.close.iloc[-1])}, dn, bay_gio)
        if not kb.get("he_thoat"):
            continue
        muc, cl = kb["muc"], kb["cat_lo"]
        dau = (f"{ma} – mua {pd.Timestamp(r['ngay_vao']):%d/%m} giá {_f(r['gia_vao'])} → {_f(kb['gia'])} "
               f"({kb['lai_lo_pct']:+.1f}%, {kb['lai_R']:+.1f}R)")
        if muc in ("CAT_LO", "BAN_TUAN", "HET_HAN"):
            ly = {"CAT_LO": f"chạm cắt lỗ {_f(cl)}", "BAN_TUAN": "đóng cửa tuần < MA10 tuần",
                  "HET_HAN": f"{kb.get('so_phien')} phiên chưa đạt 1R"}[muc]
            dong = f"🔴 {dau}: BÁN đầu phiên tới – {ly}"
        elif muc == "DOI_CAT_LO" and khoa not in da_bao:           # lần đầu: cắt lỗ theo giá khớp thật, không gọi là "dời"
            cl = kb["cat_lo_he_thong"]
            da_bao[khoa] = round(float(cl), 2)
            dong, muc = f"🟢 {dau}: GIỮ · cắt lỗ {_f(cl)}", "GIU"
        elif muc == "DOI_CAT_LO":
            cl = kb["cat_lo_he_thong"]
            dong, muc = f"⬆ {dau}: GIỮ, DỜI cắt lỗ lên {_f(cl)} (từ {_f(cl_bao)})", "DOI"
            da_bao[khoa] = round(float(cl), 2)
        elif muc == "GAN_CAT_LO":
            dong = f"⚠ {dau}: GIỮ, sát cắt lỗ {_f(cl)} – thủng là bán"
        else:
            dong = f"🟢 {dau}: GIỮ · cắt lỗ {_f(cl)}"
            da_bao.setdefault(khoa, round(float(cl), 2))
        if r["them"]:
            dong += f" (báo MUA lại {', '.join(pd.Timestamp(t).strftime('%d/%m') for t in r['them'])})"
        ra.append((THU_TU.get(muc, 3), kb["lai_lo_pct"], dong))
    con = {f"{m}|{r['ngay_vao']}" for m, r in mo.items()}
    tt["cat_lo"] = {k: v for k, v in da_bao.items() if k in con}          # bỏ lệnh đã đóng
    return [d for _, _, d in sorted(ra, key=lambda x: (x[0], -x[1] if x[1] == x[1] else 0))]


def dong_moi(dong, tt):
    """Lệnh giả định vừa đóng (chưa báo) → dòng tin; đánh dấu đã báo."""
    da = set(tt.get("da_bao_dong", []))
    ra = []
    for r in dong:
        if r["id"] in da:
            continue
        da.add(r["id"])
        ra.append(f"{'✅' if r['ket_qua'] == 'ĐÚNG' else '❌'} {r['ma']} – mua {pd.Timestamp(r['ngay_vao']):%d/%m} giá "
                  f"{_f(r['gia_vao'])}, đã bán {_f(r.get('gia_ket_thuc'))}"
                  + (f" ngày {pd.Timestamp(r['ngay_ket_thuc']):%d/%m}" if _ngay(r.get("ngay_ket_thuc")) else "")
                  + f" ({float(r['ket_qua_pct']):+.1f}%)")
    tt["da_bao_dong"] = sorted(da)[-500:]
    return ra


def tom_tat(bay_gio, gia_ngay=None, tai=None, path=None, path_tt=FILE, ghi=True):
    """→ list dòng tin mục "📌 THEO DÕI KHUYẾN NGHỊ ĐÃ GỬI" ([] nếu không có gì)."""
    nk = nhat_ky.doc(path or nhat_ky.FILE_CONG_KHAI)
    mo, dong = lenh_gia_dinh(nk, bay_gio)
    tt = doc_tt(path_tt)
    lan_dau = "da_bao_dong" not in tt
    ds = danh_gia(mo, gia_ngay, tai, bay_gio, tt)
    xong = dong_moi(dong, tt)
    if lan_dau:
        xong = []                                   # lần đầu: không báo lại các lệnh đã đóng từ trước
    if ghi:
        ghi_tt(tt, path_tt)
    if not ds and not xong:
        return []
    out = ["", f"📌 THEO DÕI KHUYẾN NGHỊ ĐÃ GỬI – nếu đã mua theo khuyến nghị ({len(ds)} lệnh đang mở)"]
    out += ds[:TOI_DA] + ([f"… +{len(ds) - TOI_DA} mã (xem Excel/trang)"] if len(ds) > TOI_DA else [])
    if xong:
        out += ["Đã đóng:"] + xong
    out.append("(giá vào = mở cửa phiên sau khuyến nghị nếu trong vùng mua; thoát theo hệ thoát – như danh mục thật)")
    return out
