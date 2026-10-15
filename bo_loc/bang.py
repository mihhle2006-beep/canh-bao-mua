# -*- coding: utf-8 -*-
"""
VẼ BẢNG CHỮ THẲNG HÀNG cho màn hình / Colab: tiêu đề + đường kẻ ─, số căn phải, chữ căn trái,
tự bỏ cột trống hoàn toàn, tính đúng độ rộng ký tự rộng (emoji 🔵🟢…, ký tự CJK) để cột không lệch.
"""
import unicodedata

import numpy as np
import pandas as pd


def rong_hien_thi(s):
    """Độ rộng hiển thị: emoji & ký tự rộng chiếm 2 ô, dấu kết hợp chiếm 0."""
    w = 0
    for ch in str(s):
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _can(s, rong, phai):
    thieu = max(rong - rong_hien_thi(s), 0)
    return " " * thieu + s if phai else s + " " * thieu


def _o(v, dinh_dang=None):
    if v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v.strip() in ("", "nan")):
        return "–"
    if dinh_dang and not isinstance(v, str):
        try:
            return dinh_dang(v) if callable(dinh_dang) else dinh_dang.format(v)
        except (ValueError, TypeError):
            return str(v)
    if isinstance(v, (bool, np.bool_)):
        return "✔" if v else "✘"
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    if isinstance(v, (float, np.floating)):
        return f"{v:,.2f}"
    return str(v)


def ve_bang(df, dinh_dang=None, thut=2, bo_cot_trong=True, can_phai=(), toi_da_rong_chu=48):
    """
    df → chuỗi bảng. dinh_dang: {cột: "{:.1f}" | hàm}. can_phai: cột chữ muốn căn phải.
    Cột chữ dài quá toi_da_rong_chu bị cắt '…' (giữ bảng không vỡ dòng).
    """
    if df is None or len(df) == 0:
        return " " * thut + "(không có dữ liệu)"
    d = df.copy()
    if bo_cot_trong:
        giu = [c for c in d.columns if not d[c].apply(lambda v: _o(v) == "–").all()]
        d = d[giu] if giu else d
    from .so import la_cot_ty_le, so4
    dinh_dang = dict(dinh_dang or {})
    so = {c: pd.api.types.is_numeric_dtype(d[c]) and not pd.api.types.is_bool_dtype(d[c]) for c in d.columns}
    for c in d.columns:                       # % và "lần": tối đa 4 chữ số thập phân, bỏ 0 thừa
        if so[c] and la_cot_ty_le(c):
            dau = "+" in str(dinh_dang.get(c, ""))
            dinh_dang[c] = (lambda dau_: (lambda v: so4(v, dau_)))(dau)
    o = {c: [_o(v, dinh_dang.get(c)) for v in d[c]] for c in d.columns}
    for c in d.columns:
        if not so[c] and c not in can_phai:
            o[c] = [x if rong_hien_thi(x) <= toi_da_rong_chu else x[: toi_da_rong_chu - 1] + "…" for x in o[c]]
    rong = {c: max([rong_hien_thi(c)] + [rong_hien_thi(x) for x in o[c]]) for c in d.columns}
    phai = {c: so[c] or c in can_phai for c in d.columns}
    le = " " * thut
    dong = [le + "  ".join(_can(str(c), rong[c], phai[c]) for c in d.columns),
            le + "  ".join("─" * rong[c] for c in d.columns)]
    for i in range(len(d)):
        dong.append(le + "  ".join(_can(o[c][i], rong[c], phai[c]) for c in d.columns))
    return "\n".join(x.rstrip() for x in dong)


def in_bang(df, **kw):
    print(ve_bang(df, **kw))
