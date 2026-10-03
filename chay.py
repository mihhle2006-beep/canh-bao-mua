# -*- coding: utf-8 -*-
"""
CẢNH BÁO MUA ĐA KHUNG – chạy:
  python chay.py                       (tu_dong: trong phiên → quét & báo MUA NGAY; sau 15h → tổng kết)
  python chay.py --che_do tong_ket     (gửi bảng tổng kết 4 khung cho mọi mã)
  python chay.py --che_do trong_phien  (quét ngay, chỉ báo mã vừa đạt MUA NGAY)
  python chay.py --ma MWG,FPT          (đổi danh sách mã; mặc định trong canh_bao/cau_hinh.py)
  python chay.py --khong_gui           (chỉ in, không gửi Telegram)
Phân tích NGÀY bằng bộ ptcp (khuyến nghị, EV, cắt lỗ/mục tiêu, sự kiện) chạy 1 lần/ngày/mã (cache_ptcp/),
lần tổng kết 15:20 chạy lại để cập nhật cho phiên sau.
Biến môi trường: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.
"""
import argparse
import sys

import pandas as pd

from canh_bao import cau_hinh as C
from canh_bao.danh_gia import phan_tich_ma
from canh_bao.ptcp_ngay import phan_tich_ngay
from canh_bao.du_lieu import gio_viet_nam, hom_nay_co_giao_dich, tai, trong_phien
from canh_bao.thong_bao import (can_bao, doc_trang_thai, dong_khung, ghi_lich_su, ghi_trang_thai, gui,
                                tin_mua_ngay, tin_tong_ket)
from canh_bao.tieu_chi import thi_truong


def main(argv=None):
    p = argparse.ArgumentParser(description="Cảnh báo mua đa khung")
    p.add_argument("--che_do", default="tu_dong", choices=["tu_dong", "trong_phien", "tong_ket"])
    p.add_argument("--ma", default=",".join(C.MA_THEO_DOI))
    p.add_argument("--gio", default=None, help="giả lập thời điểm (giờ VN), VD '2026-10-02 10:30'")
    p.add_argument("--khong_gui", action="store_true")
    a = p.parse_args(argv)
    bay_gio = pd.Timestamp(a.gio) if a.gio else gio_viet_nam()
    che_do = a.che_do
    if che_do == "tu_dong":
        if trong_phien(bay_gio):
            che_do = "trong_phien"
        elif bay_gio.weekday() < 5 and bay_gio >= bay_gio.normalize() + pd.Timedelta(C.GIO_TONG_KET + ":00"):
            che_do = "tong_ket"
        else:
            print(f"{bay_gio:%H:%M %d/%m} ngoài giờ giao dịch → không làm gì.")
            return 0
    ds_ma = [m.strip().upper() for m in a.ma.split(",") if m.strip()]
    print(f"=== {che_do.upper()} | {bay_gio:%Y-%m-%d %H:%M} | {', '.join(ds_ma)} ===")

    vni = tai("VNINDEX", "D", C.NGAY_BAT_DAU, chi_so=True)
    tt = thi_truong(vni, bay_gio)
    print(tt["nhan"])
    ds = []
    for ma in ds_ma:
        dn = tai(ma, "D", C.NGAY_BAT_DAU)
        if dn is None:
            continue
        if che_do == "trong_phien" and not hom_nay_co_giao_dich(dn, bay_gio):
            print(f"{ma}: chưa có dữ liệu phiên hôm nay (ngày nghỉ?) → bỏ qua")
            continue
        dh, dp = tai(ma, "60"), tai(ma, C.KHUNG_PHUT)
        pt = phan_tich_ngay(ma, bay_gio, lam_moi=(che_do == "tong_ket")) if C.DUNG_PTCP else None
        kq = phan_tich_ma(ma, dn, dh, dp, vni, tt, bay_gio, pt)
        ds.append(kq)
        print(f"  {ma:<5} {kq['gia']:>9,.2f}  {kq['trang_thai']:<26} {dong_khung(kq)}")
        print(f"        {kq['ly_do']}")
    if not ds:
        print("Không có mã nào để đánh giá.")
        return 0

    if che_do == "tong_ket":
        noi_dung = tin_tong_ket(ds, tt, bay_gio)
        gui(noi_dung) if not a.khong_gui else print(noi_dung)
        return 0

    trang_thai = doc_trang_thai()
    so_bao = 0
    for kq in ds:
        if can_bao(kq["ma"], kq["mua_ngay"], bay_gio, trang_thai):
            noi_dung = tin_mua_ngay(kq, bay_gio)
            gui(noi_dung) if not a.khong_gui else print(noi_dung)
            ghi_lich_su(kq, bay_gio)
            so_bao += 1
    ghi_trang_thai(trang_thai)
    print(f"Đã báo {so_bao} tín hiệu MUA NGAY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
