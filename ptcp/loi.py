# -*- coding: utf-8 -*-
"""
LÕI TÍNH KHUYẾN NGHỊ – phần "GIAI ĐOẠN 2" của main(), tách ra để DÙNG CHUNG:
  • main()                     : phân tích hôm nay (đủ dữ liệu giờ, cơ bản, nhóm ngành)
  • backtest_khuyen_nghi()     : chạy lại ĐÚNG hàm này tại từng ngày quá khứ chỉ với dữ liệu có đến ngày đó
Không tải dữ liệu, không in báo cáo – chỉ tính.
"""
from .chi_bao import duong_xu_huong, phan_tich_tin_hieu, tim_dinh_day, tinh_chi_bao
from .du_lieu import gop_tuan
from .thong_ke import kiem_dinh_walk_forward
from .muc_tieu import de_xuat_muc_tieu, tinh_cat_lo, tinh_muc_tieu, vung_hoi_tu
from .kich_ban import kich_ban_chinh, trang_thai_tuong_tu
from .quyet_dinh import danh_gia_co_ban, ket_luan_mua, quan_tri_rui_ro, quyet_dinh_cuoi
from .bo_sung import boi_canh_thi_truong, danh_gia_thi_truong, lich_cong_bo_kqkd
from .in_an import in_ra


def tinh_khuyen_nghi(df_ngay, df_gio, vni, tt, symbol="", nhom=None, so_cp=0, gia_von=None, mt_nhap=None,
                     mt_ctck=None, ky_han=252, n_phien=63, von_trieu=None, rui_ro_pct=2.0, ngay_kqkd=None,
                     ngay_gdkhq=None, co_ban=None):
    """
    df_ngay / df_gio / vni: dữ liệu ĐÃ CẮT tới ngày phân tích. tt: thong_tin_giao_dich(...) (KL TB20, beta).
    co_ban: chỉ số cơ bản (lay_chi_so_co_ban) cho bộ lọc cơ bản; None = không xét (VD backtest – không có
            số liệu cơ bản theo thời điểm).
    Trả dict: ht, kq (3 khung), stop, hoi_tu, mt_chinh, dx, dk, wf, kb, bc, lich, ttr, qr, tg, cbl, qd.
    """
    nhom = nhom or {}
    ht = df_ngay.close.iloc[-1]
    cac_khung = {"Tuần": gop_tuan(df_ngay), "Ngày": df_ngay}
    if df_gio is not None:
        cac_khung["Giờ"] = df_gio
    kq = {}
    for ten, d in cac_khung.items():
        d = tinh_chi_bao(d)
        pv = tim_dinh_day(d, ten)
        xh = duong_xu_huong(d, pv)
        ds, tong, co = phan_tich_tin_hieu(d, pv, xh, ten)
        kq[ten] = {"df": d, "pv": pv, "xh": xh, "ds": ds, "diem": tong, "co": co, "mt": None}
    d_ngay = kq["Ngày"]["df"]
    stop = tinh_cat_lo(d_ngay, kq["Ngày"]["pv"], ht)
    in_ra("\nĐang mô phỏng lịch sử cho các mục tiêu ...")
    kq["Ngày"]["mt"] = tinh_muc_tieu(d_ngay, kq["Ngày"]["pv"], kq["Ngày"]["xh"], "Ngày", df_ngay, stop, n_phien)
    kq["Tuần"]["mt"] = tinh_muc_tieu(kq["Tuần"]["df"], kq["Tuần"]["pv"], kq["Tuần"]["xh"], "Tuần", df_ngay, stop,
                                     ky_han)
    hoi_tu = vung_hoi_tu(kq["Ngày"]["mt"]["bang"], kq["Tuần"]["mt"]["bang"])
    mt_chinh = {t: (kq[t]["mt"]["chinh"]["Giá mục tiêu"] if kq[t]["mt"]["chinh"] is not None else None)
                for t in ("Ngày", "Tuần")}
    dx = de_xuat_muc_tieu(df_ngay, kq, ht, mt_nhap, hoi_tu, ky_han, mt_ctck or None)
    dk = trang_thai_tuong_tu(d_ngay, kq["Tuần"]["df"])
    wf = kiem_dinh_walk_forward(df_ngay, ht, list(kq["Ngày"]["mt"]["bang"]["Giá mục tiêu"]), stop["gia"], n_phien)
    kb = kich_ban_chinh(df_ngay, kq, ht, stop, mt_chinh, dx["chon"], so_cp, gia_von, n_phien, dk, wf=wf, nhom=nhom)
    bc = boi_canh_thi_truong(symbol, df_ngay, vni, nhom)
    lich = lich_cong_bo_kqkd(df_ngay.index[-1])
    ttr = danh_gia_thi_truong(bc, lich, df_ngay.index[-1], ngay_kqkd, ngay_gdkhq)
    qr = quan_tri_rui_ro(df_ngay, kq, ht, dx, stop, tt, kb, gia_von, so_cp, von_trieu, rui_ro_pct, ttr["he_so"])
    tg = ket_luan_mua(kq)
    cbl = danh_gia_co_ban(co_ban) if co_ban is not None else None
    qd = quyet_dinh_cuoi(tg, kb, qr, dx, ht, stop, ttr, cbl)     # ← NGUỒN DUY NHẤT của khuyến nghị
    return {"ht": ht, "kq": kq, "stop": stop, "hoi_tu": hoi_tu, "mt_chinh": mt_chinh, "dx": dx, "dk": dk, "wf": wf,
            "kb": kb, "bc": bc, "lich": lich, "ttr": ttr, "qr": qr, "tg": tg, "cbl": cbl, "qd": qd}
