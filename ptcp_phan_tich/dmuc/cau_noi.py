# -*- coding: utf-8 -*-
"""
CẦU NỐI ptcp → danh mục: phân tích từng mã bằng ptcp.main (KHÔNG hỏi) và rút gọn kết quả về dạng phần danh mục dùng.
Mọi logic kỹ thuật (đỉnh/đáy, cắt lỗ thống nhất, mục tiêu theo EV, walk-forward, bối cảnh thị trường, sự kiện,
quyết định cuối) nằm DUY NHẤT trong ptcp → chạy chay.py hay Danh_mục.py đều cho cùng một kết luận cho 1 mã.
"""
import contextlib
import io
import os

import numpy as np
import pandas as pd

from ptcp import main as ptcp_main
from ptcp import du_lieu as _du_lieu
from ptcp.chi_bao import _duong

from .cau_hinh import GOP_NGANH, NGAY_DU_LIEU_CU
from .tien_ich import co, quy_doi_gia

# Khoá dòng danh mục → tham số ptcp.main
_KHOA = {"kl_ph": "kl_ph", "kl_ny": "kl_ny", "cp_quy": "cp_quy", "so_huu_nn": "so_huu_nn", "beta_nhap": "beta",
         "san": "san", "csv_ngay": "csv_ngay", "csv_gio": "csv_gio", "ngay_kqkd": "ngay_kqkd",
         "ngay_gdkhq": "ngay_gdkhq", "ngay_mua": "ngay_mua"}


def _chuan_nhan(kn):
    """'MUA – ĐỦ ĐIỀU KIỆN 3 KHUNG' → 'MUA'; giữ nguyên các nhãn khác của ptcp."""
    return "MUA" if str(kn).startswith("MUA –") else str(kn)


def _sua_don_vi(gia, ten):
    """Giá nhập phải theo NGHÌN đồng; > 1.000 gần như chắc chắn là nhập theo ĐỒNG (VD 73900 → 73.9)."""
    if co(gia) and gia > 1000:
        return gia / 1000, f"{ten}: {gia:,.0f} có vẻ nhập theo ĐỒNG → quy đổi thành {gia / 1000:,.2f} nghìn đồng"
    return gia, ""


def phan_tich_ma(ts, start, csv_vni=None, n_phien=63, thu_muc=".", in_man_hinh=False, xuat_file=True):
    """
    ts: 1 dòng danh mục (danh_muc.doc_danh_muc). Chạy ptcp.main trong thư mục riêng của mã.
    Trả dict dùng cho danh_muc / markowitz.
    """
    canh_bao = []
    gia_von, cb1 = _sua_don_vi(ts.get("gia_von"), f"{ts['ma']} giá vốn")
    mt_nhap, cb2 = _sua_don_vi(ts.get("mt_nhap"), f"{ts['ma']} giá mục tiêu")
    canh_bao += [c for c in (cb1, cb2) if c]
    ts_ptcp = {"symbol": ts["ma"], "start": start, "csv_vni": csv_vni, "n_phien": n_phien,
               "so_cp": int(ts.get("so_cp") or 0), "gia_von": gia_von, "mt_nhap": mt_nhap,
               # nhóm ngành: cột nhom_nganh của mã (nếu có) khi bật GOP_NGANH; không thì bỏ qua để chạy nhanh
               "nhom": (ts.get("nhom_nganh") or None) if GOP_NGANH else "-"}
    for k, kp in _KHOA.items():
        v = ts.get(k)
        if v is not None and not (isinstance(v, str) and not v.strip()) and not pd.isna(v):
            ts_ptcp[kp] = v.strftime("%d/%m/%Y") if isinstance(v, pd.Timestamp) else v
    goc = os.getcwd()
    if not os.path.isabs(_du_lieu.THU_MUC_CACHE):        # cache giá dùng chung, không tách theo thư mục từng mã
        _du_lieu.THU_MUC_CACHE = os.path.abspath(_du_lieu.THU_MUC_CACHE)
    from ptcp import cau_hinh as _cfg, nhat_ky as _nk           # nhật ký khuyến nghị dùng chung, không tách theo mã
    if not os.path.isabs(_nk.duong_dan()) and not str(_nk.duong_dan()).startswith("/content/"):
        _cfg.FILE_NHAT_KY = os.path.abspath(_nk.duong_dan())
    os.makedirs(thu_muc, exist_ok=True)
    try:
        os.chdir(thu_muc)                         # ptcp ghi file theo đường dẫn tương đối
        dau_ra = contextlib.nullcontext() if in_man_hinh else contextlib.redirect_stdout(io.StringIO())
        with dau_ra:
            k = ptcp_main(tuong_tac=False, im_lang=not in_man_hinh, xuat_file=xuat_file,
                          **{a: b for a, b in ts_ptcp.items() if b is not None})
    finally:
        os.chdir(goc)

    ht, df = k["gia"], k["df_ngay"]
    gia_von2, cb3 = quy_doi_gia(gia_von, ht, f"{ts['ma']} giá vốn")    # kiểm tra lần 2 theo giá thị trường
    if cb3:
        canh_bao.append(cb3 + " (báo cáo ptcp của mã này tính theo giá vốn chưa quy đổi)")
    tre = (pd.Timestamp.today().normalize() - df.index[-1]).days
    if tre > NGAY_DU_LIEU_CU:
        canh_bao.append(f"Phiên cuối {df.index[-1]:%d/%m/%Y} cách hôm nay {tre} ngày → dữ liệu CŨ / tạm ngừng giao dịch")
    stop, dx, qr, qd, kb = k["stop"], k["dx"], k["qr"], k["qd"], k["kb"]
    mt = dx["chon"] if co(dx.get("chon")) and dx["chon"] > ht else k["kq"]["Ngày"]["mt"]["chinh"]["Giá mục tiêu"]
    hotro = _duong(k["kq"]["Ngày"]["xh"], "ho_tro")
    return {
        "symbol": k["symbol"], "san": k["san"], "ht": ht, "df": df, "tt": k["tt"],
        "so_cp": ts.get("so_cp") or 0, "gia_von": gia_von2, "mt_nhap": mt_nhap,
        "upside_dg": (mt_nhap / ht - 1) * 100 if mt_nhap else np.nan,
        "mt_ngay": mt, "upside": (mt / ht - 1) * 100, "ev": kb["ev_qd"], "rr": qr["rr"],
        "stop": stop, "cat_lo": stop["gia"], "tg": k["tg"],
        "qd": {"nhan": _chuan_nhan(qd["khuyen_nghi"]), "ly_do": qd["hanh_dong"], "kiem_tra": qd["kiem_tra"],
               "gia_mua_max": qr["gia_mua_rr2"], "dang_giu": qd["dang_giu"]},
        "quyet_dinh": _chuan_nhan(qd["khuyen_nghi"]), "khuyen_nghi_ptcp": qd["khuyen_nghi"],
        "cau_truc_ngay": k["kq"]["Ngày"]["xh"]["cau_truc"], "cau_truc_tuan": k["kq"]["Tuần"]["xh"]["cau_truc"],
        "vung_mua": (hotro["gia_nay"], hotro["gia_nay"] * 1.03) if hotro else None,
        "canh_bao": canh_bao + [c for c in k.get("canh_bao", []) if c],
        "kh": k.get("kh"),                                 # kế hoạch từ giá mua (cắt lỗ gốc, mục tiêu R, so VNI)
        "du_lieu_cu": tre > NGAY_DU_LIEU_CU, "thu_muc_ptcp": os.path.join(thu_muc, k["thu_muc"]) if k["thu_muc"] else None,
    }
