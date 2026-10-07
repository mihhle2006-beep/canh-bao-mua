# -*- coding: utf-8 -*-
"""
Backtest toàn bộ khuyến nghị canh_bao_mua bằng bộ máy ptcp (point-in-time).

Giống hoàn toàn backtest của ptcp (walk-forward, luật T+2, trần/sàn, phí + trượt giá):
  • Mỗi `buoc` phiên: chạy lại lõi quyết định tại ngày đó chỉ với dữ liệu có đến ngày đó
  • Chấm kết quả bằng giá thực tế theo kỳ hạn C.KY_HAN_MUA
  • Ngưỡng EV / R/R dùng C.EV_NGUONG / C.RR_TOI_THIEU (đánh dấu ◄ trong bảng độ nhạy)
  • Bảng độ nhạy EV × R/R + độ nhạy kỳ hạn giống ptcp

Giới hạn (như ptcp ghi rõ – ghi trung thực vào kết quả):
  • Không có dữ liệu GIỜ quá khứ → bỏ qua khung Giờ; tín hiệu ra "MUA TỪNG PHẦN" thay vì "MUA"
    (cùng kết luận chiến lược, chỉ thiếu xác nhận giờ/phút trong phiên – lịch sử cho thấy ảnh hưởng giá
    vào khoảng ±0.3–0.5%, không thay đổi kết luận thống kê)
  • Không có chỉ số cơ bản (P/E, nợ…) theo thời điểm → bộ lọc đó bỏ qua
  • Tín hiệu có thể chồng nhau; mục "chiến lược" chỉ lấy lệnh không chồng (đang giữ → bỏ qua tín hiệu mới)

Chạy:
    python backtest.py                         # tất cả mã trong MA_THEO_DOI (cau_hinh.py)
    python backtest.py VCB ACB TCB DHC GMD     # chỉ các mã này
    python backtest.py --xuat                  # kèm xuất Excel (backtest_khuyen_nghi_*.xlsx)
    python backtest.py --buoc 3 --ky_han 42   # kiểm tra dày hơn, chấm ngắn hơn
    python backtest.py VCB --tu 2022-01-01     # từ ngày cụ thể
"""
import argparse
import sys

from canh_bao import cau_hinh as C


def main():
    p = argparse.ArgumentParser(
        description="Backtest canh_bao_mua bằng bộ máy ptcp (point-in-time, walk-forward)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ví dụ:\n  python backtest.py\n  python backtest.py VCB ACB DHC --xuat\n  python backtest.py --buoc 3",
    )
    p.add_argument("ma", nargs="*",
                   help="mã cổ phiếu (mặc định: MA_THEO_DOI trong cau_hinh.py)")
    p.add_argument("--tu", default=None,
                   help=f"ngày bắt đầu dữ liệu (mặc định: C.NGAY_BAT_DAU = {C.NGAY_BAT_DAU})")
    p.add_argument("--buoc", type=int, default=5,
                   help="kiểm tra mỗi N phiên một lần (mặc định: 5; nhỏ hơn → nhiều mẫu hơn, chậm hơn)")
    p.add_argument("--ky_han", type=int, default=C.KY_HAN_MUA,
                   help=f"phiên chấm kết quả (mặc định: C.KY_HAN_MUA = {C.KY_HAN_MUA})")
    p.add_argument("--xuat", action="store_true",
                   help="xuất kết quả ra file Excel (backtest_khuyen_nghi_*.xlsx)")
    a = p.parse_args()

    ds_ma = a.ma or list(C.MA_THEO_DOI)
    if not ds_ma:
        sys.exit(
            "✘ Chưa có mã nào.\n"
            "  Thêm vào MA_THEO_DOI trong canh_bao/cau_hinh.py, hoặc truyền trực tiếp:\n"
            "  python backtest.py VCB ACB DHC GMD"
        )

    try:
        import ptcp
        import ptcp.cau_hinh as pcfg
    except ImportError:
        sys.exit(
            "✘ Chưa có gói ptcp – chạy trước:\n"
            "   python lay_ptcp.py --tu ../ptcp_phan_tich/ptcp\n"
            "  (hoặc trỏ đến thư mục ptcp đúng của bạn)"
        )

    # Đặt ngưỡng của canh_bao_mua vào ptcp để bảng độ nhạy đánh dấu ◄ đúng hàng đang dùng
    pcfg.EV_NGUONG = C.EV_NGUONG
    pcfg.RR_NGUONG = C.RR_TOI_THIEU

    start = a.tu or C.NGAY_BAT_DAU
    print(f"\n{'=' * 72}")
    print(f" BACKTEST CANH_BAO_MUA – bộ máy ptcp (point-in-time, walk-forward)")
    print(f"{'=' * 72}")
    print(f" Mã : {', '.join(ds_ma)}")
    print(f" Từ : {start}  |  Mỗi {a.buoc} phiên  |  Kỳ hạn chấm: {a.ky_han} phiên")
    print(f" Ngưỡng đang dùng: EV ≥ {C.EV_NGUONG}%, R/R ≥ {C.RR_TOI_THIEU}  (◄ trong bảng độ nhạy)")
    print(f" Giới hạn: bỏ qua khung Giờ (không có dữ liệu intraday lịch sử)")
    print(f"{'─' * 72}\n")

    if len(ds_ma) == 1:
        kq = ptcp.backtest_khuyen_nghi(
            ds_ma[0],
            start=start,
            n_phien=a.ky_han,
            buoc=a.buoc,
            xuat_excel=a.xuat,
            in_ket_qua=True,
        )
    else:
        kq = ptcp.backtest_nhieu_ma(
            ds_ma,
            start=start,
            n_phien=a.ky_han,
            buoc=a.buoc,
            xuat_excel=a.xuat,
        )

    if kq is None:
        sys.exit("\n✘ Không có kết quả – kiểm tra kết nối dữ liệu và gói ptcp.")

    return kq


if __name__ == "__main__":
    main()
