# -*- coding: utf-8 -*-
"""
==========================================================================
 PHÂN TÍCH TỔNG HỢP CỔ PHIẾU – BẢN GỘP (cập nhật theo "Đề xuất cập nhật bộ phân tích kỹ thuật")
   TÓM TẮT 5 DÒNG ở đầu báo cáo (khuyến nghị, vùng mua, cắt lỗ, 2 mục tiêu, EV & R/R)
   PHẦN A. % tăng/giảm giá (6 khung thời gian, phân loại phiên, tách riêng trần / sàn theo sàn niêm yết)
   PHẦN B. MACD xác định đỉnh/đáy (chỉ dùng đỉnh/đáy ĐÃ XÁC NHẬN) + đường xu hướng trên 3 khung
   PHẦN C. Thời điểm mua – MỘT hàm quyết định duy nhất (tuần phủ quyết, EV & R/R là ngưỡng cứng)
   PHẦN D. Kịch bản giá: xác suất toàn bộ / 1 năm / trộn / có điều kiện, mẫu hiệu dụng, KTC 90%
   PHẦN E. Đề xuất giá mục tiêu & quản trị rủi ro (MỘT mức cắt lỗ thống nhất, quy mô vị thế theo % rủi ro)
   PHẦN F. Khối lượng & thanh khoản (KL/TB20, OBV, volume profile)          [MỚI]
   PHẦN G. Bối cảnh thị trường: VN-Index, đường RS, so sánh nhóm ngành      [MỚI]
   PHẦN H. Cơ bản tối thiểu: P/E, P/B, ROE, dư nợ margin, lịch công bố KQKD [MỚI]
   PHẦN I. Backtest quy tắc vào lệnh (MACD tuần + ngày) của chính công cụ  [MỚI]
==========================================================================

NHẬT KÝ CẬP NHẬT (đối chiếu từng mục của đề xuất)
 1. Lỗi logic / mâu thuẫn
   • Hai kết luận trái nhau  → quyet_dinh_cuoi() là nguồn DUY NHẤT; phần C, Thông tin giao dịch, tóm tắt, Excel,
     HTML chỉ đọc kết quả của nó. Mục "Tỷ suất sinh lời" nay chỉ mô tả mức hấp dẫn định giá, không ra lệnh MUA.
     Khung tuần có quyền phủ quyết: MACD tuần ≤ Signal → không bao giờ ra "MUA".
   • Kịch bản TÍCH CỰC: mục tiêu luôn > mốc breakout (mốc kỹ thuật kế tiếp, hoặc đo độ rộng vùng).
   • Kịch bản TIÊU CỰC: giá đích = đáy xác nhận kế tiếp dưới cắt lỗ, không sâu hơn biên −1σ EWMA (bỏ đáy 2022).
   • "Hỗ trợ cách 0.0%": đỉnh/đáy tạm thời (nến hiện tại) không còn được dùng cho đường xu hướng, so sánh đáy,
     mục tiêu hay cắt lỗ; chỉ đỉnh/đáy của đoạn MACD đã kết thúc hoặc đã có ≥ n nến sau không bị phá.
   • Cắt lỗ: MỘT quy tắc – max(đáy ngày xác nhận − 0.5×ATR; giá − 2×ATR; giá −7%), tối thiểu 1.5×ATR.
     Bỏ cắt lỗ khung tuần (−67%, R/R 0.10) và các mức "tham khảo" gây nhiễu.
   • Ngưỡng cứng: EV sau phí < EV_NGUONG hoặc R/R < RR_NGUONG → không khuyến nghị mua; cảnh báo khi xác suất
     bị quét cắt lỗ trong n phiên ≥ 70%.
   • E1 dùng NHẤT QUÁN xác suất TRỘN (ưu tiên gần đây) như phần D, kèm số toàn lịch sử để so sánh.
   • Chấm điểm: trọng số tuần×3 > ngày×2 > giờ×1; gần hỗ trợ / RSI quá bán / phân kỳ chỉ được điểm khi có
     xác nhận (MACD cắt lên, phá đỉnh nhỏ); breakout chỉ được điểm khi KL ≥ 1.5× TB20.
   • Đỉnh/đáy mặc định theo high/low → tuần và ngày cùng cơ sở; thêm mục KIỂM TRA DỮ LIỆU (đỉnh tuần vs ngày,
     phiên vượt biên độ – nghi chưa điều chỉnh giá, lệch giá giờ/ngày).
 2. Thống kê: số mẫu hiệu dụng & nhãn "độ tin cậy thấp", KTC 90% bằng block bootstrap, xác suất có điều kiện
    (trạng thái giống hiện tại), chỉ giữ 3 mục tiêu theo EV, biên độ trần/sàn theo HOSE/HNX/UPCoM và tách riêng,
    σ EWMA + phân vị thực nghiệm, đường xu hướng > 25% khỏi giá bị bỏ qua & đếm số lần chạm.
 3. Dữ liệu: thử lại có backoff, kiểm tra status/content-type trước .json(), thêm nguồn VND finfo, SSI iBoard,
    CafeF, cache cục bộ; cảnh báo rõ khi thiếu số CP lưu hành; quy mô vị thế = vốn × %rủi ro ÷ (giá − cắt lỗ).
 4. Bổ sung: OBV & volume profile, bối cảnh VN-Index + RS + nhóm ngành, cơ bản tối thiểu, backtest.
 5. Trình bày: tự xuống dòng theo độ rộng màn hình, định dạng số thống nhất (1,234.56), tóm tắt 5 dòng,
    xuất Excel + CSV + HTML (kèm biểu đồ) + TXT, nén .zip.
 CẬP NHẬT LẦN 2
 6. Luật giao dịch VN trong mô phỏng & backtest: mua giá MỞ CỬA phiên sau (phiên khoá trần → không mua được),
    chỉ bán từ T+2, phiên đóng cửa giá sàn → không bán được, gap khi chạm cắt lỗ/mục tiêu, trượt giá 2 chiều.
 7. Khử thiên lệch thống kê: kiểm định WALK-FORWARD bước chọn mục tiêu (D4) – phần thiên lệch được trừ vào EV;
    GỘP mã cùng ngành vào mô phỏng (chuẩn hoá theo biến động) và co EV về trung bình ngành.
 8. Bối cảnh vào quyết định: VN-Index xấu / RS ở đáy 1 năm → giảm khối lượng hoặc chưa mua;
    KQKD / GDKHQ trong 5 phiên tới → chờ sau sự kiện.
 9. Colab: chạy không cần hỏi  main(tuong_tac=False, symbol="ABC", ...),  quét nhiều mã  quet_nhieu_ma([...]),
    nhớ dữ liệu đã tải trong phiên, nguồn vnstock (tự cài lần đầu).

CHẠY TRÊN GOOGLE COLAB: xem README.md (unzip → %run chay.py, hoặc from ptcp import main, quet_nhieu_ma).
KIỂM THỬ: !python -m pytest -q tests  – chạy sau mỗi lần sửa code.

NGUỒN DỮ LIỆU
  Giá ngày/giờ & VNINDEX: VNDirect → VND finfo → TCBS → SSI → CafeF → DNSE → VCI (tự chuyển nguồn khi lỗi),
  cache cục bộ, hoặc file CSV. Báo cáo CTCK: tuỳ chọn, tự điền vào DU_LIEU_CTCK (mặc định trống – dùng cho mọi mã). Thông tin DN: Vietstock + TCBS.
  Cuối báo cáo in nguồn đã dùng, thời điểm lấy, đối chiếu giá đóng cửa giữa các nguồn.

Đơn vị giá: NGHÌN ĐỒNG.   Công cụ tham khảo – KHÔNG phải khuyến nghị đầu tư.
"""
from . import cau_hinh
from . import cau_hinh as cfg
from .chuong_trinh import main, quet_nhieu_ma, KHOA_THAM_SO

__all__ = ["main", "quet_nhieu_ma", "KHOA_THAM_SO", "cfg"]
