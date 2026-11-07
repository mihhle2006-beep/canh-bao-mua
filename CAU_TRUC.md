# Cái gì ở đâu – chạy thế nào

Nguyên tắc (11/2026): **thứ gì KÍN để ở repo riêng tư, việc CHẠY (tốn phút / thời gian) để ở repo công khai này**
(phút GitHub Actions miễn phí). Mọi workflow nằm ở đây; repo kín không còn workflow nào.

| Repo | Công khai? | Chứa gì |
|---|---|---|
| **canh-bao-mua** (repo này) | công khai | 30 workflow · bot cảnh báo (`canh_bao/`, `chay.py`) · bộ lọc (`bo_loc/`) · công cụ sở hữu (`cong_cu/so_huu`) · kết quả công khai (tín hiệu, lịch sử ★, backtest điểm vào) |
| **danh-muc** | kín | thư viện chung `ptcp/` (luật Quỹ Bứt Phá, chỉ báo, backtest, định giá, BCTC…) · danh mục thật `dmuc/` + file danh mục / tiền / lệnh / Trứng vàng · script nghiên cứu (backtest quỹ, báo cáo mã, siêu cổ phiếu) · kho dữ liệu `du_lieu/` (BCTC, BCTN, bất thường) – xem `CAU_TRUC.md` trong danh-muc |
| **gia_lap** | kín | giao dịch giả lập (tài khoản ảo theo đúng luật), sức khoẻ hệ thống, tổng kết tuần |
| Bo_Loc | kín | phần bộ lọc riêng (PTĐTTC) – không chạy từ đây |

Workflow ở đây **lấy code kín lúc chạy** (token duy nhất `DANH_MUC_TOKEN_GHI` – 11/2026 gộp, bỏ `DANH_MUC_TOKEN_DOC`), XOÁ file danh mục thật trước
khi chạy (`tests/test_workflow_bao_mat.py` kiểm), log không in danh mục (`CONG_KHAI=1`), kết quả kín gửi Telegram /
commit về repo kín. Riêng **Danh muc hang ngay** cần file thật nên chạy KÍN (không bước nào in nội dung).

## Chạy tay

GitHub → repo **canh-bao-mua** → tab **Actions** → chọn workflow bên trái → **Run workflow** → điền ô (nếu có) → **Run**.
Kết quả: tin / file Telegram, hoặc mục **Artifacts** cuối trang lần chạy.

## Danh sách workflow (giờ Việt Nam)

### Chạy tự động hằng ngày / tuần

| Workflow | Lịch | Làm gì | Code ở |
|---|---|---|---|
| Loc quy But Pha | 06:07 T2–T6 | lọc mã đủ luật Quỹ Bứt Phá (top GTGD, RS, biến động) → `loc_quy_b.json` | danh-muc `ptcp` |
| Canh bao mua | 06:43 (dự phòng 07:15) T2–T6 → vòng sáng xong tự gọi vòng chiều (lịch 10:53 / 12:15 chỉ dự phòng) → 15:02 gọi danh mục, 15:20 tổng kết · 09:07 thứ Bảy | bot: vòng sáng / chiều mỗi 15', tin MUA / BÁN, tổng kết 15:20, chấm lại tín hiệu thứ Bảy. Tin MUA có nút chọn số CP (lô chẵn + lẻ) → ✅ xác nhận mới đặt; chạm cắt lỗ tự bán hết (máy Mac phải mở); nghe tin nhắn bot (`canh_bao/lenh_tele.py`) | repo này + `ptcp` |
| Kiem thu | 07:41 T2–T6 + mỗi lần push | test canh-bao-mua + gia_lap + danh-muc; hỏng → Telegram | cả 3 repo |
| Quet dinh ky | 14:20 T2–T6 | bộ lọc quét toàn sàn → `ma_mua_bo_loc.json` cho bot | repo này (`bo_loc`) |
| Danh muc hang ngay | 15:02 T2–T6 (vòng chiều gọi; lịch 14:50 dự phòng) · 08:30 / trong phiên khi có `nhap.txt` mới | danh mục THẬT: nhập lệnh, tóm tắt, dashboard, Excel, tiền nhàn rỗi; đầu tháng + phân rã hiệu suất tháng trước (thật so giả lập) → Telegram (chạy kín) | danh-muc `dmuc` |
| Gia lap | 16:30 (kiểm lại 17:30, 18:53) T2–T6 | tài khoản giả lập theo luật | gia_lap |
| Suc khoe he thong | 19:55 T2–T6 | các workflow có chạy / lỗi không, NAV giả lập | gia_lap |
| Tong ket tuan (gia lap) | 20:17 thứ Sáu | tổng kết tuần giả lập | gia_lap |
| BCTC moi hang dem | 22:13 hằng ngày | tải BCTC kỳ mới vào kho → kéo theo Bat thuong BCTC | danh-muc `ptcp.kho_bctc` |
| Doc bao cao thuong nien | 22:17 hằng ngày | đọc BCTN mới (chiến lược DN, OCR) | danh-muc `ptcp.chien_luoc_dn` |
| Kho BCTC | 00:47 thứ Bảy | làm mới kho BCTC toàn bộ | danh-muc |
| Du lieu tra cuu | 06:41 T2–T7 | dữ liệu trang Tra cứu mã + trang **Biểu đồ** (giá, BCTC, doanh nghiệp, nến 1' / 5' ~3 tháng của MỌI mã – `thi_truong/phut_web.py`; mã thêm ngoài HOSE + HNX: `thi_truong/ma_them.txt`; dữ liệu mục **Đọc biểu đồ**: điều kiện chọn mã Quỹ Bứt Phá + lịch sử tín hiệu bot – `thi_truong/he_thong_web.py` → `docs/ma/doc_bd.js`) → triển khai web; trong giờ giao dịch Bảng thị trường nối thêm nến phút hôm nay (`phut_web --trong_phien`) | repo này `thi_truong` |
| Tai nen 15p | 01:43 thứ Bảy | tải nến 15' (giữ cache backtest) | repo này |
| Boi so nganh | 03:13 thứ Bảy | bội số định giá theo ngành | danh-muc |
| Tra cuu ma | 07:53 thứ Bảy (+ chạy tay) | tra cứu mã đang giữ / theo dõi | danh-muc `ptcp.tra_cuu` |
| Backtest quy But Pha | 09:13 ngày 1 hằng tháng (+ chạy tay) | mốc luật đang chạy (`chuan`); kết luận các phần cũ đã xoá ở danh-muc `KET_LUAN_BACKTEST_CU.md` | danh-muc `chay_backtest_quy_b.py` |
| Backtest | 02:17 ngày 2 hằng tháng | backtest điểm vào 15' → `ket_qua_backtest.json` (bot tự chọn cách vào) | repo này |

### Chạy trên máy Mac ở Việt Nam (repo danh-muc, runner `vn` – API DNSE chỉ gọi được từ VN)

| Workflow | Lịch | Làm gì | Code ở |
|---|---|---|---|
| Dong bo DNSE | 08:35 T2–T6 vòng mỗi 10' tới 15:05 (dự phòng mỗi 30' 09:05–14:35) · ngoài phiên mỗi 3 giờ | lệnh khớp, tiền, vị thế DNSE → danh mục thật; giữ Mac không tự ngủ trong vòng | danh-muc `dmuc/dnse_dong_bo.py` |
| Dat lenh tu Telegram | nút ✅ trên tin (repository_dispatch từ `lenh_tele.py`) · 08:40 / 09:05 xin sẵn Smart OTP | đặt lệnh LO (tách lô chẵn + lẻ, chặn ngoài giờ / nút cũ / trần giá trị / trùng); bán: 5' sau còn chưa khớp → ⚠ + nút bán lại; kết quả → `lenh_dat/ket_qua.jsonl` → bot gửi Telegram | danh-muc `dmuc/dnse_lenh.py` |
| Dat lenh thu | chạy tay: số lệnh, mã, số CP (< 100 = lô lẻ) | đặt N lệnh MUA giá sàn rồi huỷ ngay, đo thời gian | danh-muc `dmuc/dnse_lenh.py --thu` |

### Chỉ chạy tay

| Workflow | Ô nhập | Làm gì | Code ở |
|---|---|---|---|
| Canh bao mua | vong (sang / chieu) · gio + ghi_bu · thu_nut · ma · chi_thu | chạy vòng tay khi lịch bỏ · chạy lại lượt bị mất và lưu trạng thái · gửi thử 1 tin nút (ngoài giờ) · xem 1 mã · chỉ thử | repo này |
| Bao cao ma | mã, nội dung | báo cáo đầy đủ 1 mã (định giá, BCTC, bất thường, chiến lược, bản ghi nhớ) | danh-muc |
| Bao cao CTCK | mã, số báo cáo | báo cáo phân tích của CTCK + giá → Excel | danh-muc |
| Tra cứu BCTC | mã / ngành / sàn | xuất BCTC Excel | danh-muc `ptcp.xuat_bctc` |
| Tra cứu sở hữu | mã, từ, đến | cơ cấu cổ đông / sở hữu nước ngoài | repo này `cong_cu/so_huu` |
| Bat thuong BCTC | mã, làm mới | dò bất thường BCTC + đọc thuyết minh giải thích (cũng tự chạy sau BCTC mới) | danh-muc |
| To chuc phat hanh trai phieu | mã | DN phát hành trái phiếu tin cậy / sự cố | danh-muc |
| Sieu co phieu | mã, từ | đặc điểm các siêu cổ phiếu | danh-muc `phan_tich_sieu_cp.py` |
| Kiem dinh dinh gia | số mã, từ | kiểm định độ chính xác định giá | danh-muc |
| Kiem du lieu thi truong moi noi | thị trường, … | đủ dữ liệu để thử luật ở thị trường khác không | danh-muc |
| Chan doan nguon | nhiều ô | in mẫu dữ liệu các nguồn giá / BCTC khi nghi lỗi nguồn | danh-muc |
| Xuat CSV gia | mã, từ ngày | 1 file CSV giá ngày → Telegram | danh-muc |
| Kiem tra DNSE API | – | gọi thử API DNSE (chỉ đọc) – log chỉ in mã phản hồi / số lượng / tên trường | danh-muc `dmuc/dnse_api.py` |
| Doc trang | URL | in nội dung trang công khai (VD hướng dẫn DNSE) | – |

Thêm / đổi workflow: sửa ở repo này; nếu workflow lấy repo kín thì phải có bước xoá file danh mục thật (test sẽ báo).
