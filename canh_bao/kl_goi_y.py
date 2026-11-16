# -*- coding: utf-8 -*-
"""
SỐ CP / TỶ TRỌNG BOT GỢI Ý → danh-muc/lenh_that_goi_y.csv (RIÊNG TƯ – tên theo mẫu lenh_that*.csv nên các workflow công
khai checkout danh-muc tự xoá / bỏ khỏi sparse-checkout). dmuc/tuan_thu so lệnh thật với ĐÚNG con số bot đã báo.
Chủ quỹ 16/11/2026: "khối lượng lệch, mua đúng mà" – phần kiểm cũ so với mức cơ sở (0,75 % NAV ÷ khoảng cắt lỗ) CHƯA nhân
hệ số ĐẮT / nhiệt / VN-Index / khối lượng như tin MUA → báo "QUÁ NHỎ" sai.
  nguon MUA_NGAY : tin MUA 15' – so_cp = số CP theo NAV in trên tin (lô chẵn khi ATC), ty_trong % NAV
  nguon TONG_KET : tin tổng kết – ty_trong "≤ x % NAV" của mã nhóm mua, ngay = phiên hiệu lực
Lỗi đọc / ghi → bỏ qua (không ảnh hưởng tin). Log công khai: KHÔNG in gì khi ghi được (số dòng phụ thuộc mã đang giữ).
"""
import base64
import csv
import io
import os
import urllib.error

import pandas as pd

FILE = "lenh_that_goi_y.csv"
COT = ("ngay", "thoi_diem", "ma", "nguon", "so_cp", "ty_trong", "gia")
GIU_NGAY = 120


def _chu(v, le=None):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return f"{float(v):.{le}f}" if le is not None else str(v)


def gop(cu, dong, hom_nay=None):
    """CSV cũ (chuỗi) + dòng mới → (CSV mới, số dòng thêm / đổi). Khoá (ngay, ma, nguon): dòng mới thay dòng cũ khi so_cp
    hoặc ty_trong khác (gửi lặp cùng số → không đổi); bỏ dòng cũ hơn GIU_NGAY ngày."""
    rows = list(csv.DictReader(io.StringIO(cu))) if cu and cu.strip() else []
    vt = {(r.get("ngay"), r.get("ma"), r.get("nguon")): i for i, r in enumerate(rows)}
    doi = 0
    for d in dong:
        d = {k: "" if d.get(k) is None else str(d.get(k)) for k in COT}
        k = (d["ngay"], d["ma"], d["nguon"])
        if k in vt:
            r = rows[vt[k]]
            if (r.get("so_cp", ""), r.get("ty_trong", "")) == (d["so_cp"], d["ty_trong"]):
                continue
            rows[vt[k]] = d
        else:
            vt[k] = len(rows)
            rows.append(d)
        doi += 1
    if hom_nay is not None:
        moc = f"{pd.Timestamp(hom_nay) - pd.Timedelta(days=GIU_NGAY):%Y-%m-%d}"
        rows = [r for r in rows if str(r.get("ngay", "")) >= moc]
    rows.sort(key=lambda r: (r.get("ngay", ""), r.get("thoi_diem", ""), r.get("ma", "")))
    out = io.StringIO()
    w = csv.DictWriter(out, COT, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return out.getvalue(), doi


def dong_mua(kq, bay_gio):
    """Tin MUA 15' → dòng gợi ý (số CP đúng như tin / nút: NAV thật × tỷ trọng đã nhân mọi hệ số)."""
    from . import diem_vao
    from .tong_ket_cl import von_lenh
    gia, cl, _, _ = diem_vao.muc_sau_mua(kq)
    tt = von_lenh(diem_vao._k_rui_ro(kq, gia, cl))["ty_trong"]
    return {"ngay": f"{pd.Timestamp(bay_gio):%Y-%m-%d}", "thoi_diem": f"{pd.Timestamp(bay_gio):%H:%M}", "ma": kq["ma"],
            "nguon": "MUA_NGAY", "so_cp": diem_vao._lo_atc(kq, diem_vao.so_cp_nav(kq, gia, cl)) or "",
            "ty_trong": _chu(tt, 2), "gia": _chu(gia, 2)}


def dong_tong_ket(k, bay_gio):
    """Mã nhóm mua của tin tổng kết → dòng gợi ý (tỷ trọng ≤ x % NAV, ngày = phiên hiệu lực)."""
    from .tong_ket_cl import von_lenh
    hl = k.get("hieu_luc")
    ngay = pd.Timestamp(hl) if hl is not None and hl == hl else pd.Timestamp(bay_gio)
    return {"ngay": f"{ngay:%Y-%m-%d}", "thoi_diem": f"{pd.Timestamp(bay_gio):%H:%M}", "ma": k["ma"], "nguon": "TONG_KET",
            "so_cp": "", "ty_trong": _chu(von_lenh(k)["ty_trong"], 2), "gia": _chu(k.get("gia"), 2)}


def ghi(dong, bay_gio=None, goi=None):
    """Ghi dòng gợi ý vào danh-muc (GitHub contents API, thử lại khi sha cũ). Không token / không dòng → 0. → số dòng đổi."""
    gh = os.environ.get("DANH_MUC_TOKEN_GHI", "").strip()
    dong = [d for d in dong if d and (d.get("so_cp") not in ("", None, 0) or d.get("ty_trong") not in ("", None))]
    if not gh or not dong:
        return 0
    if goi is None:
        from .lenh_tele import _goi as goi
    repo = os.environ.get("DANH_MUC_REPO", "").strip() or "mihhle2006-beep/danh-muc"
    url = f"https://api.github.com/repos/{repo}/contents/{FILE}"
    h = {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}
    for lan in range(3):
        try:
            f = goi(url, headers=h)
            cu, sha = base64.b64decode(f["content"]).decode("utf-8"), f["sha"]
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            cu, sha = "", None
        moi, doi = gop(cu, dong, bay_gio)
        if not doi:
            return 0
        body = {"message": f"{FILE}: cập nhật gợi ý", "content": base64.b64encode(moi.encode("utf-8")).decode()}
        if sha:
            body["sha"] = sha
        try:
            goi(url, body, h, "PUT")
            return doi
        except urllib.error.HTTPError as e:
            if e.code not in (409, 422) or lan == 2:                 # sha cũ (lượt khác vừa ghi) → đọc lại
                raise
    return 0
