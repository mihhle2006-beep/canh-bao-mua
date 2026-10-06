# -*- coding: utf-8 -*-
"""
CẢNH BÁO MUA ĐA KHUNG – chạy:
  python chay.py                       (tu_dong: trong phiên → quét & báo MUA NGAY; sau 15h → tổng kết)
  python chay.py --che_do tong_ket     (gửi bảng tổng kết 4 khung cho mọi mã)
  python chay.py --che_do trong_phien  (quét ngay, chỉ báo mã vừa đạt MUA NGAY)
  python chay.py --ma MWG,FPT          (đổi danh sách mã; mặc định trong canh_bao/cau_hinh.py)
  python chay.py --khong_gui           (chỉ in, không gửi Telegram)
  python chay.py --khong_ban           (bỏ cảnh báo BÁN cho mã đang giữ)
  python chay.py --che_do lich_su      (chấm lại mọi tín hiệu đã ghi, in bảng độ chính xác, xuất Excel)
CẢNH BÁO BÁN: vị thế đọc từ danh_muc.csv của repo riêng tư danh-muc (DANH_MUC_TOKEN, DANH_MUC_REPO) – xem vi_the.py.
Phân tích NGÀY bằng bộ ptcp (khuyến nghị, EV, cắt lỗ/mục tiêu, sự kiện) chạy 1 lần/ngày/mã (cache_ptcp/),
lần tổng kết 15:20 chạy lại để cập nhật cho phiên sau.
Biến môi trường: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, DANH_MUC_TOKEN, DANH_MUC_REPO.
"""
import argparse
import sys

import pandas as pd

from canh_bao import cau_hinh as C
from canh_bao import du_lieu
from canh_bao.danh_gia import phan_tich_ma
from canh_bao.ptcp_ngay import phan_tich_ngay
from canh_bao.du_lieu import gio_viet_nam, hom_nay_co_giao_dich, tai, trong_phien
from canh_bao.thong_bao import (can_bao, doc_trang_thai, dong_khung, ghi_lich_su, ghi_trang_thai, gui,
                                tin_mua_ngay, tin_tong_ket)
from canh_bao.tieu_chi import thi_truong
from canh_bao import nhat_ky, vi_the
from canh_bao import trinh_bay


def main(argv=None):
    p = argparse.ArgumentParser(description="Cảnh báo mua đa khung")
    p.add_argument("--che_do", default="tu_dong", choices=["tu_dong", "trong_phien", "tong_ket", "lich_su"])
    p.add_argument("--ma", default=",".join(C.MA_THEO_DOI))
    p.add_argument("--gio", default=None, help="giả lập thời điểm (giờ VN), VD '2026-10-02 10:30'")
    p.add_argument("--khong_gui", action="store_true")
    p.add_argument("--khong_ban", action="store_true", help="bỏ cảnh báo BÁN cho mã đang giữ")
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
    if che_do == "lich_su":
        return xem_lich_su()
    ds_ma = [m.strip().upper() for m in a.ma.split(",") if m.strip()]
    vt, nguon_vt = ({}, "tắt (--khong_ban)") if a.khong_ban else vi_the.doc_danh_muc()
    an = [m for m in vt if m not in ds_ma]                  # mã chỉ có trong danh mục: không in chi tiết ra log
    ds_ma += an
    print(f"=== {che_do.upper()} | {bay_gio:%Y-%m-%d %H:%M} | {', '.join(m for m in ds_ma if m not in an)}"
          f"{f' + {len(an)} mã trong danh mục' if an else ''} ===")
    print(f"Vị thế đang giữ: {len(vt)} mã (nguồn: {nguon_vt})")

    vni = tai("VNINDEX", "D", C.NGAY_BAT_DAU, chi_so=True)
    tt = thi_truong(vni, bay_gio)
    print(tt["nhan"])
    ds, du_lieu_ngay = [], {}
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
        du_lieu_ngay[ma] = dn
        if ma in vt:
            kq["ban"] = vi_the.danh_gia_ban(vt[ma], kq, dn)
        ds.append(kq)
        if ma in an:
            continue
        print(f"  {ma:<5} {kq['gia']:>9,.2f}  {kq['trang_thai']:<26} {dong_khung(kq)}")
        print(f"        {kq['ly_do']}")
    if not ds:
        print("Không có mã nào để đánh giá.")
        return 0

    if che_do == "tong_ket":
        cong_khai = [k for k in ds if k["ma"] not in an]
        noi_dung = tin_tong_ket(cong_khai, tt, bay_gio)
        giu = [k for k in ds if "ban" in k]
        if giu:
            noi_dung += "\n\n💼 VỊ THẾ ĐANG GIỮ\n" + "\n".join(vi_the.dong_tong_ket(vt[k["ma"]], k["ban"]) for k in giu)
        if C.GHI_NHAT_KY:
            noi_dung += _nhat_ky_tong_ket(ds, an, du_lieu_ngay, bay_gio, kem_rieng=bool(giu))
        anh = trinh_bay.ve_bang_tong_ket([trinh_bay.dong_bang_tong_ket(k) for k in cong_khai],
                                         f"TỔNG KẾT {pd.Timestamp(bay_gio):%d/%m/%Y} – {tt['nhan']}") \
            if C.GUI_ANH else None
        gui(noi_dung, rieng_tu=bool(giu), anh=anh) if not a.khong_gui else print(noi_dung)
        return 0

    trang_thai = doc_trang_thai()
    so_bao = 0
    tt_an = vi_the.doc_trang_thai_ban(vi_the.FILE_TRANG_THAI_MUA_AN)      # mã chỉ có trong danh mục: lưu riêng
    for kq in ds:
        if can_bao(kq["ma"], kq["mua_ngay"], bay_gio, tt_an if kq["ma"] in an else trang_thai):
            noi_dung = tin_mua_ngay(kq, bay_gio)
            if kq["ma"] in vt:
                noi_dung += f"\n💼 Đang giữ {vt[kq['ma']]['so_cp']:,.0f} CP – đây là tín hiệu MUA THÊM"
            anh = trinh_bay.ve_bieu_do_ma(kq["ma"], du_lieu_ngay[kq["ma"]], kq["gia"], kq.get("muc_tieu"),
                                          kq.get("cat_lo"), tieu_de=f"{kq['ma']} – MUA NGAY") if C.GUI_ANH else None
            gui(noi_dung, rieng_tu=kq["ma"] in vt, anh=anh) if not a.khong_gui else print(noi_dung)
            if kq["ma"] not in an:                       # lịch sử commit lên repo công khai → bỏ mã ẩn
                ghi_lich_su(kq, bay_gio)
            if C.GHI_NHAT_KY:
                nhat_ky.ghi_mua_ngay(kq, bay_gio, rieng_tu=kq["ma"] in an)
            so_bao += 1
    ghi_trang_thai(trang_thai)
    if an:
        vi_the.ghi_trang_thai_ban(tt_an, vi_the.FILE_TRANG_THAI_MUA_AN)
    print(f"Đã báo {so_bao} tín hiệu MUA NGAY.")

    tt_ban, so_ban = vi_the.doc_trang_thai_ban(), 0
    for kq in ds:
        kb = kq.get("ban")
        if kb and vi_the.can_bao_ban(kq["ma"], kb["muc"], bay_gio, tt_ban):
            noi_dung = vi_the.tin_ban(vt[kq["ma"]], kb, kq, bay_gio)
            v = vt[kq["ma"]]
            anh = trinh_bay.ve_bieu_do_ma(kq["ma"], du_lieu_ngay[kq["ma"]], kq["gia"], v.get("muc_tieu"), v.get("cat_lo"),
                                          v.get("gia_von"), tieu_de=f"{kq['ma']} – {vi_the.NHAN[kb['muc']]}") \
                if C.GUI_ANH else None
            gui(noi_dung, rieng_tu=True, anh=anh) if not a.khong_gui else print(noi_dung)
            if C.GHI_NHAT_KY:
                nhat_ky.ghi_ban(kq, kb, bay_gio)
            so_ban += 1
    if vt:
        vi_the.ghi_trang_thai_ban(tt_ban)
        print(f"Đã gửi {so_ban} cảnh báo cho vị thế đang giữ.")
    if du_lieu.NGUON_DA_DUNG:
        dem = {}
        for n in du_lieu.NGUON_DA_DUNG.values():
            dem[n] = dem.get(n, 0) + 1
        print("Nguồn giá đã dùng: " + ", ".join(f"{n} ({k} lần)" for n, k in dem.items()))
    return 0


def _tai_ngay(ma):
    return tai(ma, "D", C.NGAY_BAT_DAU)


def _nhat_ky_tong_ket(ds, an, du_lieu_ngay, bay_gio, kem_rieng=False):
    """Ghi khuyến nghị ptcp hôm nay, chấm lại tín hiệu cũ, trả các dòng độ chính xác để gắn vào tin tổng kết."""
    try:
        nhat_ky.nhap_lich_su_cu()
        for kq in ds:
            nhat_ky.ghi_ptcp(kq, bay_gio, rieng_tu=kq["ma"] in an)
        xong = nhat_ky.cap_nhat(_tai_ngay, du_lieu_ngay)
        print(f"Nhật ký tín hiệu: {xong} tín hiệu vừa có kết luận ĐÚNG/SAI.")
        d = nhat_ky.dong_tong_ket()
        if kem_rieng:                                  # tin này là tin riêng tư → được kèm thống kê lệnh bán
            d += nhat_ky.dong_tong_ket(nhat_ky.FILE_RIENG, "📊 ĐỘ CHÍNH XÁC (riêng: cảnh báo bán, mã trong danh mục)")
        return ("\n\n" + "\n".join(d)) if d else ""
    except Exception as e:                             # nhật ký lỗi không được làm hỏng tin tổng kết
        print(f"⚠ Nhật ký tín hiệu lỗi: {str(e)[:150]}")
        return ""


def xem_lich_su():
    """Chấm lại & in bảng độ chính xác. Trên Actions (repo công khai) chỉ in phần công khai."""
    import os
    rieng = not os.environ.get("GITHUB_ACTIONS")
    xong = nhat_ky.cap_nhat(_tai_ngay)
    print(f"Vừa có kết luận: {xong} tín hiệu")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        for ten, path in [("CÔNG KHAI", nhat_ky.FILE_CONG_KHAI)] + ([("RIÊNG", nhat_ky.FILE_RIENG)] if rieng else []):
            tk = nhat_ky.thong_ke(nhat_ky.doc(path))
            print(f"\n=== ĐỘ CHÍNH XÁC – {ten} ===")
            print(tk.round(1).to_string(index=False) if len(tk) else "(chưa có tín hiệu)")
    print("\nĐã xuất", nhat_ky.xuat_excel(rieng=rieng))
    return 0


if __name__ == "__main__":
    sys.exit(main())
