# -*- coding: utf-8 -*-
"""
==========================================================================
 PHÂN TÍCH DANH MỤC CỔ PHIẾU – dùng chung lõi ptcp
==========================================================================
Cùng thư mục với chay.py (phân tích 1 mã). Mỗi mã trong danh mục được phân tích bằng ĐÚNG ptcp.main
→ kết luận cho 1 mã giống hệt khi chạy chay.py. Phần dmuc/ chỉ làm việc cấp danh mục:
  dmuc/cau_hinh.py   DANH_MUC, tiền mặt, % giữ tiền mặt, ngưỡng rủi ro danh mục, Markowitz  ← SỬA Ở ĐÂY
  dmuc/cau_noi.py    gọi ptcp.main cho từng mã, rút gọn kết quả
  dmuc/danh_muc.py   nhật ký giao dịch, cắt lỗ/mục tiêu ĐÃ ĐẶT, hành động, số lượng, stress test
  dmuc/markowitz.py  tối ưu (lợi suất tuần, Ledoit–Wolf, có tiền mặt), dmuc/bieu_do.py, dmuc/xuat.py
Tham số KỸ THUẬT (MACD, đỉnh/đáy, cắt lỗ, EV, R/R, phí, T+2…) sửa ở ptcp/cau_hinh.py – áp dụng cho CẢ HAI.

CÁCH CHẠY (Colab, trong thư mục ptcp_phan_tich):
  %run Danh_mục.py                              (hỏi tiền mặt, % giữ tiền mặt, chiến lược)
  !python Danh_mục.py --file danh_muc.csv --tien_mat 8 --giu_tien_mat 50
  !python Danh_mục.py --nhat_ky nhat_ky.csv     (số CP, giá vốn, cổ tức tính từ nhật ký)
  !python Danh_mục.py --gop_nganh               (ptcp tải thêm mã cùng ngành – chính xác hơn, chậm hơn)
  !python Danh_mục.py --khong_ve                (không lưu báo cáo ptcp từng mã – nhanh hơn)
  Kiểm thử cả gói: !python -m pytest -q

FILE NHẬT KÝ (tuỳ chọn) – ngay,ma,loai,so_cp,gia,phi  (giá nghìn đồng, phí đồng)
  loai: mua | ban | co_tuc_tien (gia = cổ tức/CP) | co_tuc_cp (so_cp = số CP nhận thêm)
Lưu giữa các lần chạy: trang_thai_vi_the.json, lich_su_danh_muc.csv, cache_du_lieu/ (dùng chung với chay.py).
Công cụ tham khảo – KHÔNG phải khuyến nghị đầu tư.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())

import importlib.util  # noqa: E402
_thieu = [m for m in ("requests", "pandas", "numpy", "matplotlib", "openpyxl", "scipy") if not importlib.util.find_spec(m)]
if _thieu:
    raise SystemExit(f"Thiếu thư viện: {', '.join(_thieu)} → pip install {' '.join(_thieu)}")

from dmuc.chuong_trinh import main  # noqa: E402

if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Lỗi: {e}")
