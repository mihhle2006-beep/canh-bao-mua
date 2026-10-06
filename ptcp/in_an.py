# -*- coding: utf-8 -*-
"""In ấn: in_ra (tự xuống dòng, ghi báo cáo), ve_bang (bảng gọn), định dạng số."""
# flake8: noqa: F401
import sys
import os
import io
import re
import json
import time
import base64
import shutil
import zipfile
import builtins
import textwrap
import subprocess
import html as _html
from datetime import datetime, date

import requests
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
from numpy.lib.stride_tricks import sliding_window_view as _cua_so_truot
from . import cau_hinh as cfg


# ==========================================================================
# IN ẤN [MỚI]: tự xuống dòng theo độ rộng màn hình + ghi lại toàn bộ báo cáo (xuất TXT/HTML)
# ==========================================================================
_print_goc = builtins.print


BAO_CAO_TEXT = []


_MAU_THUT_DONG = re.compile(r"^(\s*(?:[•▶▲▼⚠✔✘★◆✎>\-–]+\s+|\d+[.)]\s+)?(?:[^:]{1,46}:\s+)?)")


def _do_rong():
    if cfg.DO_RONG_DONG:
        return cfg.DO_RONG_DONG
    if "google.colab" in sys.modules or "ipykernel" in sys.modules:
        return 110
    return max(70, shutil.get_terminal_size((110, 24)).columns - 1)


def _la_bang(dong):
    """Chuỗi nhiều dòng có cột căn thẳng (DataFrame.to_string) → không tự xuống dòng để giữ nguyên bảng."""
    return len(dong) >= 3 and sum(1 for d in dong if "   " in d.strip()) >= 2


_RE_KE = re.compile(r"^\s*([#═=─\-]{20,})\s*$")
_RE_TIEU_DE = re.compile(r"^\s*(PHẦN [A-Z]\b|[A-J]\d*\.\s|J\d\.|KHUNG |TÓM TẮT|KẾT LUẬN|NGUỒN DỮ LIỆU|BÁO CÁO|"
                         r"ĐỐI CHIẾU|DANH MỤC|PHÂN TÍCH)")


def _to_mau(s):
    """Tô xanh lá đường kẻ & tiêu đề mục khi IN (file báo cáo .txt/.html vẫn là chữ thường)."""
    from .mau import BAT_MAU, xanh, xanh_nhat
    if not BAT_MAU:
        return s
    ra = []
    for d in s.split("\n"):
        if _RE_KE.match(d):
            ra.append(xanh_nhat(d))
        elif _RE_TIEU_DE.match(d) and len(d) < 160:
            ra.append(xanh(d))
        else:
            ra.append(d)
    return "\n".join(ra)


_RE_MUC = re.compile(r"^\s*(TÓM TẮT|PHẦN ([A-K])\.|([A-J]\d)\.\s|XUẤT KẾT QUẢ|KẾT LUẬN CHUNG PHẦN J|KẾT LUẬN BACKTEST)")
_RE_GACH = re.compile(r"^\s*[#─=\-█]{10,}\s*$")
# Mục giữ lại khi in gọn (đổi trong cau_hinh.py → MUC_GON). Mã mục: "TÓM TẮT", chữ phần ("C", "G", "H"…),
# mục con ("D2", "E1"…), "I_KL" = Kết luận backtest, "J_KL" = Kết luận chung Phần J.
MUC_GON_MAC_DINH = ("TÓM TẮT", "C", "D2", "E1", "G", "H", "I_KL", "J_KL")


def _muc_gon():
    return set(getattr(cfg, "MUC_GON", MUC_GON_MAC_DINH))


def _loc_gon(s):
    """Chế độ in gọn: chỉ giữ các mục trong MUC_GON (+ dòng đã lưu file ✔ / cảnh báo ⚠). File vẫn đầy đủ."""
    ds = s.split("\n")
    muc_dong = []
    for d in ds:
        m = _RE_MUC.match(d)
        if m:
            g1 = m.group(1)
            _CHAY["muc"] = m.group(3) or m.group(2) or {"TÓM TẮT": "TÓM TẮT"}.get(g1) or \
                ("J_KL" if g1.startswith("KẾT LUẬN CHUNG") else "I_KL" if g1.startswith("KẾT LUẬN BACKTEST")
                 else "XUAT")
        muc_dong.append(_CHAY.get("muc", ""))
    # đường kẻ đứng TRƯỚC tiêu đề thuộc về mục kế tiếp (không để sót / thừa dòng kẻ)
    for k in range(len(ds) - 2, -1, -1):
        if _RE_GACH.match(ds[k]) or not ds[k].strip():
            muc_dong[k] = muc_dong[k + 1]
    giu_muc = _muc_gon()
    giu = []
    for d, muc in zip(ds, muc_dong):
        if muc in giu_muc or (len(muc) == 2 and muc[0] in giu_muc) or d.lstrip().startswith(("✔ Đã", "⚠ Không")) \
                or (muc == "XUAT" and "✔" in d):
            giu.append(d)
    return "\n".join(giu) if giu else None


def in_ra(*args, sep=" ", end="\n", file=None, flush=False):
    """[MỚI] Thay print: tự xuống dòng theo độ rộng màn hình & ghi lại báo cáo (không ghi đè print của notebook)."""
    from .so import vn_hoa
    s = vn_hoa(sep.join(str(a) for a in args))          # số kiểu Việt Nam ở mọi đầu ra (màn hình, .txt, .html)
    if file is not None:
        return _print_goc(s, end=end, file=file, flush=flush)
    if _CHAY.get("im_lang"):
        BAO_CAO_TEXT.append(s + end)
        return
    dong = s.split("\n")
    if not _la_bang(dong):
        W, moi = _do_rong(), []
        for d in dong:
            if len(d) <= W:
                moi.append(d)
                continue
            m = _MAU_THUT_DONG.match(d)
            thut = " " * min(len(m.group(1)) if m and m.group(1).strip() else len(d) - len(d.lstrip()) + 2, 40)
            moi += textwrap.wrap(d, W, subsequent_indent=thut, break_long_words=False,
                                 break_on_hyphens=False) or [""]
        s = "\n".join(moi)
    BAO_CAO_TEXT.append(s + end)
    if _CHAY.get("gon"):
        s = _loc_gon(s)
        if s is None:
            return
    _print_goc(_to_mau(s), end=end, flush=flush)


def ve_bang(df, doi_ten=None, dinh_dang=None, an=None, rong=None, thut=2, can_phai=None):
    """
    [MỚI] Vẽ bảng dạng văn bản gọn cho màn hình hẹp (thay DataFrame.to_string):
      • cột chữ căn trái, cột số căn phải; tiêu đề tự xuống 2–3 dòng để cột số hẹp lại;
      • số định dạng thống nhất, ô trống '–', không còn '-0.00';
      • nếu vẫn tràn, cột CHỮ dài nhất tự xuống dòng trong ô → bảng không bị tách thành nhiều khối.
    doi_ten: {cột: tên hiển thị}; dinh_dang: {cột: "{:+.1f}" hoặc hàm}; an: các cột bỏ đi.
    """
    from .so import la_cot_ty_le, so4
    if df is None or not len(df):
        return " " * thut + "(không có dữ liệu)"
    d = df.drop(columns=[c for c in (an or []) if c in df.columns])
    doi_ten, dinh_dang = doi_ten or {}, dinh_dang or {}
    W = (rong or _do_rong()) - thut
    cols = list(d.columns)
    la_so = {c: (pd.api.types.is_numeric_dtype(d[c]) and not pd.api.types.is_bool_dtype(d[c]))
             or c in (can_phai or ()) for c in cols}

    def o(c, v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or (v is pd.NaT):
            return "–"
        f = dinh_dang.get(c)
        if callable(f):
            return f(v)
        if isinstance(v, (bool, np.bool_)):
            return "✔" if v else "✘"
        if isinstance(v, (int, np.integer)):
            return (f or "{:,}").format(v)
        if isinstance(v, (float, np.floating)):
            if np.isnan(v):
                return "–"
            if la_cot_ty_le(doi_ten.get(c, c)):                 # % và "lần": tối đa 4 chữ số thập phân
                return so4(v, dau="+" in str(f or ""))
            v = 0.0 if abs(v) < 5e-3 else float(v)
            return (f or "{:,.2f}").format(v)
        if isinstance(v, pd.Timestamp):
            return f"{v:%d/%m/%Y}"
        return str(v)

    o_ = {c: [o(c, v) for v in d[c]] for c in cols}
    td = {c: str(doi_ten.get(c, c)) for c in cols}
    w = {}
    for c in cols:
        w[c] = max([len(x) for x in o_[c]] + [max((len(t) for t in td[c].split()), default=0)])
        while len(textwrap.wrap(td[c], w[c])) > 2:        # tiêu đề tối đa 2 dòng
            w[c] += 1
    sep = "  "
    tong = sum(w.values()) + len(sep) * (len(cols) - 1)
    quan = None
    if tong > W:
        chu = [c for c in cols if not la_so[c] and c not in (can_phai or ())]
        if chu:
            quan = max(chu, key=lambda c: w[c])
            w[quan] = max(14, W - (tong - w[quan]))

    def dong(gt):
        n = max(len(v) for v in gt.values())
        ra = []
        for k in range(n):
            p = [(gt[c][k] if k < len(gt[c]) else "") for c in cols]
            p = [x.rjust(w[c]) if la_so[c] else x.ljust(w[c]) for x, c in zip(p, cols)]
            ra.append(" " * thut + sep.join(p).rstrip())
        return ra

    ra = dong({c: textwrap.wrap(td[c], w[c]) or [""] for c in cols})
    ra.append(" " * thut + "─" * min(W, sum(w.values()) + len(sep) * (len(cols) - 1)))
    for i in range(len(d)):
        ra += dong({c: (textwrap.wrap(o_[c][i], w[c]) or [""]) if (c == quan and len(o_[c][i]) > w[c])
                    else [o_[c][i]] for c in cols})
    return "\n".join(ra)


def fmt(x, le=2, dau=False):
    """[MỚI] Định dạng số THỐNG NHẤT toàn báo cáo: dấu phẩy ngăn nghìn, dấu chấm thập phân (34,500.25)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "N/A"
    return f"{x:+,.{le}f}" if dau else f"{x:,.{le}f}"


def in_bang(tieu_de, bang, **kw):
    in_ra(f"\n{'-' * 84}\n {tieu_de}\n{'-' * 84}")
    in_ra(ve_bang(bang, **kw))


# ==========================================================================
# 10B. THÔNG TIN GIAO DỊCH (đỉnh/đáy 52 tuần, vốn hoá, beta, sở hữu NN ...)
# ==========================================================================
def so_vn(x, le=0):
    """[SỬA] Định dạng số THỐNG NHẤT với phần còn lại của báo cáo: 34500 → '34,500' ; 1.05 → '1.05'."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "N/A"
    return f"{x:,.{le}f}"


_CHAY = {"tuong_tac": True}
