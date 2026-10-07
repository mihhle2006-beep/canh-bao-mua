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
   PHẦN I. Backtest quy tắc vào lệnh (MACD tuần + ngày) + so sánh cách VÀO / THOÁT lệnh + KẾT LUẬN
   PHẦN K. Lịch sử khuyến nghị của mã – ĐÚNG / SAI theo giá thực tế (nhật ký)        [MỚI]
   Ngoài báo cáo: backtest_khuyen_nghi() – chạy lại TOÀN BỘ lõi quyết định tại từng ngày quá khứ  [MỚI]
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
    nhớ dữ liệu đã tải trong phiên.
 CẬP NHẬT LẦN 3
10. VNDirect finfo dùng host đúng api-finfo. P/E tính lại = giá hiện tại ÷ EPS 4 quý gần nhất
    (EPS = LNST 4 quý ÷ CP lưu hành; P/E của nguồn giữ để đối chiếu). (Lần 3 từng bỏ vnstock – nay đã DÙNG LẠI
    vnstock bản Cộng đồng làm nguồn dự phòng: cfg.DUNG_VNSTOCK = True, khoá API ở Colab Secrets / VNSTOCK_API_KEY.)
 CẬP NHẬT LẦN 4
11. Nhật ký khuyến nghị (nhat_ky.py, Phần K): ghi khuyến nghị khi đổi, tự chấm ĐÚNG/SAI bằng giá thực tế; Colab
    lưu ở Google Drive. Cùng bộ chấm với bot canh-bao-mua.
12. Backtest point-in-time toàn bộ khuyến nghị (backtest_kn.py) + độ nhạy ngưỡng EV × R/R (tách nửa đầu/nửa sau)
    và độ nhạy kỳ hạn chấm. Lõi quyết định tách ra loi.py để main() và backtest dùng CHUNG.
13. EV quyết định dựa trên các phiên CÙNG TRẠNG THÁI TÍN HIỆU (co về EV cơ sở theo số mẫu hiệu dụng); in "lợi thế
    của tín hiệu". Cách cũ: cfg.CACH_TINH_EV = "than_trong".
14. Bộ lọc CƠ BẢN trong hàm quyết định (LOC_CO_BAN): lỗ / LNST 4 quý giảm sâu → THEO DÕI; ROE thấp / P/E cao →
    MUA TỪNG PHẦN. LNST lấy 8 quý để tính tăng trưởng.
15. Thoát lệnh: một chỗ cấu hình (TRAILING_ATR, HOA_VON_KHI_R, CHOT_TUNG_PHAN_PCT) dùng chung ptcp & danh mục;
    Phần I so sánh chốt cứng / cắt lỗ động / chốt từng phần; kế hoạch vị thế có dòng "Kế hoạch BÁN".
16. Tách file: phan_tich.py → thong_tin / muc_tieu / kich_ban / quyet_dinh (phan_tich.py giữ tương thích);
    du_lieu.py → du_lieu_co_ban.py (thông tin DN, chỉ số cơ bản, LNST, BCTC).

 CẬP NHẬT LẦN 5
17. Vùng mua điều chỉnh cho mã CHƯA nắm giữ (vung_mua.py): cụm hỗ trợ trùng nhau + nến xác nhận, backtest
    point-in-time (phễu về vùng / khớp / +1R). Phần I so sánh cách VÀO × cách THOÁT và có mục KẾT LUẬN BACKTEST.
    Phần J đổi tên thành "Phân tích chuyên sâu" (module chuyen_sau.py, khoá kết quả "chuyen_sau"), không còn
    tên thương hiệu bên thứ ba trong code, báo cáo, Excel, HTML.
18. backtest_phuong_phap([...]) (backtest_pp.py): mọi tổ hợp vào × thoát của Phần I trên nhiều mã, 4 phép thử độ
    mạnh (TB & PF, KTC bootstrap theo mã, độ phủ số mã, ổn định 2 nửa) → MẠNH / KHÁ / YẾU; xuất Excel.
19. nhat_ky.xem(): tải giá mới nhất mọi mã trong nhật ký, chấm lại & ghi file (Drive), hiện tóm tắt THEO MÃ (giá lúc
    khuyến nghị → hiện tại, % tăng/giảm, đánh giá tạm ✔/✘) + độ chính xác + chi tiết; Excel lưu cạnh nhật ký.
20. Gia hạn lệnh (GIA_HAN_LENH): tới n_phien mà lãi < 1R → bán; lãi ≥ 1R → giữ tiếp, cắt lỗ động siết 2×ATR, tối
    đa 252 phiên. Áp cho backtest Phần I, backtest_phuong_phap (so với "hết hạn cứng") và kế hoạch vị thế.

 CẬP NHẬT LẦN 6
21. backtest_phuong_phap: BỎ MÃ TRÙNG (mã nhập 2 lần từng bị chạy 2 lần → số lệnh của mã đó nhân đôi); 5 phép thử:
    KTC bootstrap THEO QUÝ (thay theo mã), ổn định ≥ 60% số năm có lãi & nửa sau có lãi, bỏ 2% lệnh lãi nhất vẫn
    > 0 → MẠNH 5/5, KHÁ 4/5. Excel thêm sheet "Theo nam", "Ly do thoat". Hàm cham_diem() dùng chung.
22. Hệ thoát nhiều tầng (he_thoat.py) + backtest_he_thoat([...]) (backtest_thoat.py): T0 hiện tại → T1 không siết /
    không hạn → T2 chuyển khung tuần ở 3R/2R (MA10 tuần / đáy 2 tuần) → T3 siết khi cao trào → T4 mua lại khi vượt
    đỉnh cũ → T5 nhồi lệnh; biến thể nến trần (mua / ½ KL / chờ vượt đỉnh / bỏ qua) và thị trường giảm (không lọc /
    chặn / ½ KL + siết – cần VN-Index). Đo % vốn của mã, giữ được lãi (MFE), bán rồi mua lại cao hơn, % mua & giữ
    đạt được ở mã ×5, CAGR/MDD rổ, up/down capture so VN-Index, giai đoạn thử/kiểm tra; điểm mua hiện tại; biểu đồ.
    T0 của bộ mô phỏng mới cho ĐÚNG các lệnh của backtest_quy_tac(thoat="dong") (có test).
23. Theo kết quả giá thật 41 mã: gốc = T2-3R-ma10; mỗi lớp đo RIÊNG so với gốc (bỏ thang chồng lớp T3–T5). Thêm A0
    (vào MACD KHÔNG lọc tuần) và B (nhồi lệnh). chien_luoc.py + chien_luoc_thang([...]): điểm thị trường 8 chỉ báo
    (MA200, MA50/MA200, dốc MA200, động lượng 3/6 tháng, cách đỉnh 1 năm, độ rộng, biến động), vùng đệm ≥5 → CL2
    (A0 70% + VNI 30%), ≤2 → CL1 (A0 50% + B 50%), 3–4 giữ nguyên; tỷ trọng mục tiêu từng mã; sheet "Ro gop".
    Sửa chỉ số: % thời gian có vị thế tính theo mã, "giữ được lãi" cùng gốc giá mua đầu khi nhồi lệnh.

CHẠY TRÊN GOOGLE COLAB: xem README.md (unzip → %run chay.py, hoặc from ptcp import main, quet_nhieu_ma).
KIỂM THỬ: !python -m pytest -q tests  – chạy sau mỗi lần sửa code.

NGUỒN DỮ LIỆU
  Giá ngày/giờ & VNINDEX: VNDirect → VND finfo → TCBS → SSI → CafeF → DNSE → VCI (tự chuyển nguồn khi lỗi),
  cache cục bộ, hoặc file CSV. Chỉ số cơ bản: VNDirect (api-finfo) → vnstock → TCBS → Yahoo. Báo cáo CTCK: tuỳ chọn, tự điền vào DU_LIEU_CTCK (mặc định trống – dùng cho mọi mã). Số CP & thông tin DN: TCBS → VNDirect → Yahoo (đối chiếu chéo, không dùng Vietstock).
  Cuối báo cáo in nguồn đã dùng, thời điểm lấy, đối chiếu giá đóng cửa giữa các nguồn.

Đơn vị giá: NGHÌN ĐỒNG.   Công cụ tham khảo – KHÔNG phải khuyến nghị đầu tư.
"""
__version__ = "beta 1.3"   # + hệ thoát nhiều tầng, phép thử siết lại, chiến lược CL1/CL2 theo thị trường

from . import cau_hinh
from . import cau_hinh as cfg
from .chuong_trinh import main, quet_nhieu_ma, KHOA_THAM_SO
from .backtest_kn import backtest_khuyen_nghi, backtest_nhieu_ma
from .backtest_pp import backtest_phuong_phap
from .backtest_thoat import backtest_he_thoat
from .chien_luoc import chien_luoc_thang
from . import nhat_ky

__all__ = ["main", "quet_nhieu_ma", "KHOA_THAM_SO", "cfg", "backtest_khuyen_nghi", "backtest_nhieu_ma",
           "backtest_phuong_phap", "backtest_he_thoat", "chien_luoc_thang", "nhat_ky"]
