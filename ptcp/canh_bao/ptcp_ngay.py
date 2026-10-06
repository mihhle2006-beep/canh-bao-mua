# -*- coding: utf-8 -*-
"""
PHÂN TÍCH NGÀY BẰNG BỘ ptcp (phân tích cổ phiếu) – chạy 1 lần/ngày/mã, lưu cache, các lần quét 15 phút dùng lại.
Lấy từ ptcp:
  • Khuyến nghị cuối của ptcp (tuần phủ quyết, EV, R/R, 3 khung, bối cảnh thị trường, sự kiện)
  • EV sau phí & xác suất chạm mục tiêu trước cắt lỗ (mô phỏng lịch sử theo luật T+2, trần/sàn, walk-forward)
  • Cắt lỗ THỐNG NHẤT & mục tiêu đề xuất (đỉnh cũ, kháng cự, AB=CD, Fibo, nền giá, MA, vùng KL, đỉnh 52T…)
  • Sự kiện KQKD / GDKHQ trong 5 phiên tới → chặn mở vị thế; VN-Index xấu / RS ở đáy 1 năm → giảm khối lượng
"""
import contextlib
import io
import json
import os

import numpy as np
import pandas as pd

from . import cau_hinh as C

THU_MUC = "cache_ptcp"


def _so(x):
    try:
        x = float(x)
        return None if np.isnan(x) else x
    except (TypeError, ValueError):
        return None


def _kich_ban(kb):
    """Bảng 3 kịch bản của ptcp (TÍCH CỰC / CƠ SỞ / TIÊU CỰC); 2 dòng CƠ SỞ (đạt MT cơ sở, đi ngang) gộp làm 1."""
    b = kb.get("bang")
    if b is None or not len(b):
        return []
    cot_xs = "XS trộn %" if "XS trộn %" in b else next((c for c in b.columns if c.startswith("XS")), None)
    out = {}
    for _, r in b.iterrows():
        ten = str(r["Kịch bản"])
        nhom = "TÍCH CỰC" if ten.startswith("TÍCH") else "TIÊU CỰC" if ten.startswith("TIÊU") else "CƠ SỞ"
        xs = _so(r.get(cot_xs)) or 0.0
        if nhom == "CƠ SỞ" and nhom in out:
            out[nhom]["xs"] += xs
            out[nhom]["chi_tiet"].append(f"{ten.split('–')[-1].strip()} {xs:.0f}%")
            continue
        out[nhom] = {"ten": nhom, "gia": _so(r.get("Giá mục tiêu")), "xs": xs, "ktc": str(r.get("KTC 90% (trộn)", "")),
                     "phien": _so(r.get("Số phiên trung vị")), "dieu_kien": str(r.get("Điều kiện kích hoạt", "")),
                     "chi_tiet": [f"{ten.split('–')[-1].strip()} {xs:.0f}%"] if nhom == "CƠ SỞ" else []}
    return [out[k] for k in ("TÍCH CỰC", "CƠ SỞ", "TIÊU CỰC") if k in out]


def _rut_gon(k):
    """Kết quả ptcp.main → dict JSON gọn (chỉ phần cảnh báo cần)."""
    kb, qr, qd, dx, ttr, tg = k["kb"], k["qr"], k["qd"], k["dx"], k["ttr"], k["tg"]
    ms = kb.get("ms", {}).get("tron", {})
    mt_ngay = k["kq"]["Ngày"]["mt"]["chinh"]
    return {
        "ngay_du_lieu": f"{pd.Timestamp(k['ngay']):%Y-%m-%d}", "gia": _so(k["gia"]),
        "khuyen_nghi": qd["khuyen_nghi"], "hanh_dong": qd["hanh_dong"], "ly_do": qd.get("ly_do", []),
        "mua": bool(qd.get("mua")), "ev": _so(kb.get("ev_qd")), "xs_muc_tieu": _so(ms.get("tren")),
        "xs_cat_lo": _so(ms.get("duoi")), "rr": _so(qr.get("rr")), "cat_lo": _so(k["stop"]["gia"]),
        "cat_lo_theo": k["stop"].get("theo", ""), "atr": _so(k["stop"].get("atr")),
        "muc_tieu": _so(dx.get("chon")), "moc_muc_tieu": str(dx.get("moc", "")),
        "muc_tieu_ngay": _so(mt_ngay["Giá mục tiêu"]) if mt_ngay is not None else None,
        "pp_muc_tieu_ngay": str(mt_ngay["Phương pháp"]) if mt_ngay is not None else "",
        "gia_mua_rr2": _so(qr.get("gia_mua_rr2")),
        "tuan_ok": bool(tg.get("tuan_ok")), "ngay_ok": bool(tg.get("ngay_ok")),
        "chan_su_kien": bool(ttr.get("chan")), "su_kien": list(ttr.get("su_kien", [])),
        "canh_bao_su_kien": list(ttr.get("canh_bao", [])), "vni_xau": bool(ttr.get("vni_xau")),
        "rs_yeu": bool(ttr.get("rs_yeu")), "he_so": _so(ttr.get("he_so")) or 1.0,
        "kich_ban": _kich_ban(kb), "n_phien": int(kb.get("n") or 63),
        "loi_the_tin_hieu": _so(kb.get("loi_the_tin_hieu")),
        "co_ban": [t for t, ok in qd.get("kiem_tra", []) if t.startswith("Cơ bản") and ok is False],
        "vung_mua": _vung_mua(k), "backtest": _backtest(k),
    }


def _vung_mua(k):
    """Vùng mua điều chỉnh của ptcp (mã chưa nắm giữ) + phễu lịch sử. ptcp cũ không có → None."""
    vm = k.get("vm")
    if not vm:
        return None
    ls = ((k.get("bt_vm") or {}).get("co_dinh") or {}).get("vung") or {}
    return {"lo": _so(vm["lo"]), "hi": _so(vm["hi"]), "cat_lo": _so(vm["stop"]), "muc_tieu": _so(vm["muc_tieu"]),
            "rr": _so(vm["rr"]), "trang_thai": str(vm["trang_thai"]), "tuan_ok": bool(vm["tuan_ok"]),
            "xs_ve_vung": _so(ls.get("xs_ve_vung")), "xs_1R": _so(ls.get("xs_1R")), "so_lenh": int(ls.get("so_lenh") or 0)}


def _backtest(k):
    """Kết luận backtest Phần I: câu hành động (dòng cuối) + có lợi thế hay không."""
    kl = k.get("ket_luan_bt")
    if not kl or not kl.get("dong"):
        return None
    return {"hanh_dong": str(kl["dong"][-1]), "co_loi_the": bool(kl.get("co_loi_the"))}


def phan_tich_ngay(ma, bay_gio, lam_moi=False, **them):
    """Trả dict ptcp đã rút gọn (cache theo ngày). Lỗi → None (cảnh báo vẫn chạy, chỉ thiếu phần ptcp)."""
    os.makedirs(THU_MUC, exist_ok=True)
    f = os.path.join(THU_MUC, f"{ma}_{pd.Timestamp(bay_gio):%Y-%m-%d}.json")
    if os.path.exists(f) and not lam_moi:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    try:
        import ptcp
        ptcp.cau_hinh.GHI_NHAT_KY = False                    # bot tự ghi nhật ký (canh_bao/nhat_ky.py) – tránh ghi trùng
        tham_so = {"symbol": ma, "nhom": "-", "start": C.NGAY_BAT_DAU, **C.SU_KIEN.get(ma, {}), **them}
        with contextlib.redirect_stdout(io.StringIO()):
            k = ptcp.main(tuong_tac=False, im_lang=True, xuat_file=False, **tham_so)
        kq = _rut_gon(k)
    except Exception as e:                                   # ptcp lỗi không được làm hỏng cảnh báo
        print(f"  ⚠ ptcp {ma}: {str(e)[:120]}")
        return None
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(kq, fh, ensure_ascii=False, indent=1)
    return kq
