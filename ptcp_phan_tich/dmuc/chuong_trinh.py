# -*- coding: utf-8 -*-
"""ĐIỀU PHỐI: đọc tham số → danh mục/nhật ký → phân tích từng mã (ptcp) → danh mục → Markowitz → xuất kết quả."""
import argparse
import os
import shutil
import sys
from datetime import date

import matplotlib
import pandas as pd
import matplotlib.pyplot as plt

from . import cau_hinh as C
from .bieu_do import ve_dashboard_danh_muc, ve_markowitz, ve_hiep_phuong_sai
from ptcp.du_lieu import tai_vnindex
from .danh_muc import (doc_danh_muc, doc_nhat_ky, gop_nhat_ky, tao_file_mau, doc_trang_thai, ghi_trang_thai,
                       phan_tich_danh_muc)
from .markowitz import toi_uu_markowitz
from .cau_noi import phan_tich_ma
from .dieu_chinh import de_xuat, cap_nhat_csv
from .thi_truong import danh_gia_thi_truong
from .tien_ich import so_vn
from .xuat import in_dieu_chinh, in_danh_muc, in_markowitz, xuat_excel, ghi_lich_su


def doc_tham_so(argv=None):
    p = argparse.ArgumentParser(description="Phân tích danh mục cổ phiếu")
    p.add_argument("--file", default=C.FILE_DANH_MUC, help="File danh mục CSV/Excel")
    p.add_argument("--nhat_ky", default=C.FILE_NHAT_KY, help="File nhật ký giao dịch CSV")
    p.add_argument("--start", default=C.NGAY_BAT_DAU)
    p.add_argument("--vnindex", default=C.FILE_VNINDEX)
    p.add_argument("--tien_mat", type=float, default=C.TIEN_MAT_TRIEU, help="Tiền mặt (triệu đồng)")
    p.add_argument("--rf", type=float, default=C.LAI_SUAT_PHI_RUI_RO, help="Lãi suất phi rủi ro %%/năm")
    p.add_argument("--n_phien", type=int, default=C.SO_PHIEN_KICH_BAN)
    p.add_argument("--chi_tiet", action="store_true", default=C.IN_CHI_TIET)
    p.add_argument("--khong_ve", action="store_true",
                   help="Không lưu báo cáo/biểu đồ ptcp của từng mã (chạy nhanh hơn)")
    p.add_argument("--gop_nganh", action="store_true", default=C.GOP_NGANH,
                   help="ptcp tải thêm mã cùng ngành cho từng mã (chính xác hơn, chậm hơn)")
    p.add_argument("--ky_vong", default=C.MKW_KY_VONG, choices=["lich_su", "muc_tieu", "ket_hop"])
    p.add_argument("--toi_da", type=float, default=C.MKW_TY_TRONG_TOI_DA, help="Markowitz: %% tối đa/mã")
    p.add_argument("--chon", default=C.MKW_DANH_MUC_CHON, choices=["gmv", "max_sharpe"])
    p.add_argument("--giu_tien_mat", type=float, default=None,
                   help="%% tổng tài sản giữ tiền mặt; bỏ trống = TỰ ĐỘNG theo VN-Index (GIU_TIEN_MAT_TU_DONG)")
    if argv is None:
        argv = sys.argv[1:]
        if "ipykernel" in sys.modules and sys.argv and "ipykernel" in os.path.basename(sys.argv[0]):
            argv = []                             # gọi main() trực tiếp trong ô notebook → dùng cấu hình
    a = p.parse_args(argv)                        # gõ sai tên tham số → BÁO LỖI (bản cũ bỏ qua âm thầm)
    a.da_nhap = {x.split("=")[0] for x in argv if x.startswith("--")}
    return a


def _nhap(cau_hoi, mac_dinh, kieu=float, hop_le=lambda v: True, hien=None):
    while True:
        try:
            s = input(f"  {cau_hoi} [Enter = {hien or mac_dinh}]: ").strip().replace(",", ".")
        except EOFError:
            return mac_dinh
        if not s:
            return mac_dinh
        try:
            v = kieu(s)
            if hop_le(v):
                return v
        except ValueError:
            pass
        print("    Giá trị không hợp lệ, nhập lại.")


def hoi_nguoi_dung(a):
    """Hỏi các lựa chọn quan trọng (bỏ qua mục đã truyền bằng tham số dòng lệnh)."""
    co_the_hoi = "ipykernel" in sys.modules or (sys.stdin is not None and sys.stdin.isatty())
    if not (C.HOI_KHI_CHAY and co_the_hoi):
        return a
    print("\n  ▶ THIẾT LẬP (Enter để giữ mặc định)")
    if "--tien_mat" not in a.da_nhap:
        a.tien_mat = _nhap("Tiền mặt hiện có (triệu đồng)", a.tien_mat, float, lambda v: v >= 0)
    if "--giu_tien_mat" not in a.da_nhap:
        tu_dong = C.GIU_TIEN_MAT_TU_DONG and a.giu_tien_mat is None
        a.giu_tien_mat = _nhap("Giữ bao nhiêu % tổng tài sản bằng tiền mặt (0–100)", a.giu_tien_mat,
                               float, lambda v: 0 <= v <= 100,
                               hien=("tự động theo VN-Index: " + ", ".join(
                                   f"{k} {v:g}%" for k, v in C.TIEN_MAT_THEO_THI_TRUONG.items())) if tu_dong else None)
    if "--chon" not in a.da_nhap:
        print("    Chiến lược phân bổ: 1 = Phương sai nhỏ nhất (ổn định, khuyên dùng) | "
              "2 = Sharpe lớn nhất (cần kỳ vọng lợi suất đáng tin)")
        a.chon = {1: "gmv", 2: "max_sharpe"}[_nhap("Chọn 1 hoặc 2", 1 if a.chon == "gmv" else 2, int,
                                                     lambda v: v in (1, 2))]
    return a


def main(argv=None):
    a = doc_tham_so(argv)
    print("=" * 100 + "\n PHÂN TÍCH DANH MỤC CỔ PHIẾU\n" + "=" * 100)
    dung_chuoi = bool(str(C.DANH_MUC).strip()) and "--file" not in a.da_nhap   # DANH_MUC gõ trong cau_hinh.py
    if not dung_chuoi:
        if not a.file:
            raise SystemExit("Chưa có danh mục: dùng --file danh_muc.csv hoặc điền DANH_MUC trong dmuc/cau_hinh.py.")
        if not os.path.exists(a.file):
            tao_file_mau(a.file)
            raise SystemExit(f"Hãy điền {a.file} rồi chạy lại.")
    ds = doc_danh_muc(text=C.DANH_MUC) if dung_chuoi else doc_danh_muc(a.file)
    if a.nhat_ky:
        ds = gop_nhat_ky(ds, doc_nhat_ky(a.nhat_ky))
        print(f"  Số CP & giá vốn lấy từ nhật ký: {a.nhat_ky}")
    if not ds:
        raise SystemExit("Danh mục trống.")
    a = hoi_nguoi_dung(a)
    C.GOP_NGANH = a.gop_nganh
    from . import cau_noi as _cn
    _cn.GOP_NGANH = a.gop_nganh
    tien_mat = a.tien_mat * 1e6
    print(f"  {len(ds)} mã: " + ", ".join(f"{d['ma']}{'' if d['so_cp'] else ' (theo dõi)'}" for d in ds)
          + f" | Tiền mặt {so_vn(a.tien_mat, 1)} tr | Rf {a.rf:g}%")

    can = (pd.Timestamp.today() - pd.DateOffset(years=C.MKW_SO_NAM, days=60)).strftime("%Y-%m-%d")
    if pd.Timestamp(a.start) > pd.Timestamp(can):
        print(f"  ⚠ --start {a.start} chưa đủ {C.MKW_SO_NAM} năm cho Markowitz → tự lùi về {can}")
        a.start = can
    vni = tai_vnindex(a.start, os.path.abspath(a.vnindex) if a.vnindex else None)
    thi_truong = danh_gia_thi_truong(vni)
    if len(thi_truong["bang"]):
        print("\n  THỊ TRƯỜNG CHUNG (VN-Index):")
        for _, r in thi_truong["bang"].iterrows():
            print(f"    {r['Kết quả']:<7} {r['Tiêu chí VN-Index']:<36} {r['Chi tiết']}")
    print(f"  → {thi_truong['nhan']}")
    if a.giu_tien_mat is None:                        # không nhập tay → tự động theo VN-Index
        a.giu_tien_mat = (thi_truong["giu_tien_mat"] if C.GIU_TIEN_MAT_TU_DONG and thi_truong["giu_tien_mat"]
                          is not None else C.GIU_TIEN_MAT_PCT)
        nguon_tm = (f"TỰ ĐỘNG – thị trường {thi_truong['trang_thai']}" if C.GIU_TIEN_MAT_TU_DONG
                    and thi_truong["giu_tien_mat"] is not None else "mặc định cau_hinh.py")
    else:
        nguon_tm = "nhập tay"
    if not 0 <= a.giu_tien_mat <= 100:
        raise SystemExit("--giu_tien_mat phải trong 0–100")
    thi_truong["nguon_tien_mat"] = nguon_tm
    print(f"  ★ Giữ tiền mặt: {a.giu_tien_mat:g}% tổng tài sản ({nguon_tm}) → cổ phiếu tối đa "
          f"{100 - a.giu_tien_mat:g}% | Kế hoạch chính: "
          f"{'Sharpe lớn nhất' if a.chon == 'max_sharpe' else 'Phương sai nhỏ nhất'}")

    thu_muc = os.path.abspath(f"ket_qua_danh_muc_{date.today():%Y%m%d}")
    os.makedirs(thu_muc, exist_ok=True)
    ds_kq, ds_ok, loi = [], [], []
    for i, ts in enumerate(ds, 1):
        ma = ts["ma"]
        tm = os.path.join(thu_muc, ma)
        os.makedirs(tm, exist_ok=True)
        print(f"\n[{i}/{len(ds)}] {ma} ...")
        try:
            kq = phan_tich_ma(ts, a.start, os.path.abspath(a.vnindex) if a.vnindex else None, a.n_phien, tm,
                              in_man_hinh=a.chi_tiet, xuat_file=C.XUAT_FILE_TUNG_MA and not a.khong_ve)
            ds_kq.append(kq)
            ds_ok.append(ts)
            print(f"   ✔ {ma}: {kq['ht']:,.2f} | ptcp: {kq['khuyen_nghi_ptcp']} | EV {kq['ev']:+.2f}% | "
                  f"R/R {kq['rr']:.2f}")
        except (SystemExit, Exception) as e:
            loi.append((ma, str(e)))
            print(f"   ✘ {ma}: {e}")
            shutil.rmtree(tm, ignore_errors=True)
        finally:
            plt.close("all")
    if not ds_kq:
        raise SystemExit("Không phân tích được mã nào.")

    trang_thai = doc_trang_thai(C.FILE_TRANG_THAI)
    dm, tt_moi = phan_tich_danh_muc(ds_kq, ds_ok, vni, a.rf / 100, tien_mat, trang_thai, thi_truong,
                                     a.giu_tien_mat)
    in_danh_muc(dm)
    mk = toi_uu_markowitz(ds_kq, dm, a.rf / 100, tien_mat, a.ky_vong, a.toi_da, a.chon, a.giu_tien_mat)
    if mk:
        in_markowitz(mk)
    dm["dieu_chinh"] = de_xuat(ds_kq, dm, tt_moi)            # có thể dời cắt lỗ lên trong tt_moi
    in_dieu_chinh(dm["dieu_chinh"])
    if C.CAP_NHAT_FILE_DANH_MUC and not dung_chuoi and cap_nhat_csv(a.file, dm["dieu_chinh"]):
        print(f"\n  ✔ Đã cập nhật {a.file}: ngày mua, cắt lỗ/chốt lời đã đặt, đề xuất (bản cũ: {a.file}.bak)")
    thay_doi = ghi_lich_su(dm, C.FILE_LICH_SU)
    if thay_doi:
        print("\n ▶ THAY ĐỔI HÀNH ĐỘNG " + thay_doi[0] + (":" if len(thay_doi) > 1 else ": không có"))
        for t in thay_doi[1:]:
            print(f"   • {t}")
    ma_loi = {m for m, _ in loi}                   # mã lỗi: giữ nguyên trạng thái cũ
    ghi_trang_thai(C.FILE_TRANG_THAI, {**{m: v for m, v in trang_thai.items() if m in ma_loi}, **tt_moi})
    if loi:
        print("\n  Mã không phân tích được: " + ", ".join(ma_loi))

    print(f"\n{'=' * 100}\n XUẤT KẾT QUẢ → {thu_muc}\n{'=' * 100}")
    ve_dashboard_danh_muc(dm, os.path.join(thu_muc, "dashboard_danh_muc.png"))
    if mk:
        ve_markowitz(mk, os.path.join(thu_muc, "markowitz.png"))
        ve_hiep_phuong_sai(mk, os.path.join(thu_muc, "hiep_phuong_sai.png"))
    xuat_excel(dm, mk, loi, os.path.join(thu_muc, "danh_muc_tong_hop.xlsx"))
    print("\n(Công cụ tham khảo dựa trên dữ liệu quá khứ – không phải khuyến nghị đầu tư)")
    if matplotlib.get_backend().lower() != "agg":
        plt.show()
    return dm, mk


if __name__ == "__main__":
    main()
