# Cái gì ở đâu – chạy thế nào

Nguyên tắc (11/2026): **thứ gì KÍN để ở repo riêng tư, việc CHẠY (tốn phút / thời gian) để ở repo công khai này**
(phút GitHub Actions miễn phí). Mọi workflow nằm ở đây; repo kín không còn workflow nào.

| Repo | Công khai? | Chứa gì |
|---|---|---|
| **canh-bao-mua** (repo này) | công khai | 30 workflow · bot cảnh báo (`canh_bao/`, `chay.py`) · bộ lọc (`bo_loc/`) · công cụ sở hữu (`cong_cu/so_huu`) · kết quả công khai (tín hiệu, lịch sử ★, backtest điểm vào) |
| **danh-muc** | kín | thư viện chung `ptcp/` (luật Quỹ Bứt Phá, chỉ báo, backtest, định giá, BCTC…) · danh mục thật `dmuc/` + file danh mục / tiền / lệnh / Trứng vàng · script nghiên cứu (backtest quỹ, báo cáo mã, siêu cổ phiếu) · kho dữ liệu `du_lieu/` (BCTC, BCTN, bất thường) – xem `CAU_TRUC.md` trong danh-muc |
| **gia_lap** | kín | giao dịch giả lập (tài khoản ảo theo đúng luật), sức khoẻ hệ thống, tổng kết tuần |
| Bo_Loc | kín | phần bộ lọc riêng (PTĐTTC) – không chạy từ đây |

Workflow ở đây **lấy code kín lúc chạy** (token `DANH_MUC_TOKEN_GHI` / `DANH_MUC_TOKEN_DOC`), XOÁ file danh mục thật trước
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
| Canh bao mua | 06:43 (dự phòng 07:15), 12:15, 15:20 T2–T6 · 09:07 thứ Bảy | bot: vòng sáng / chiều mỗi 15', tin MUA / BÁN, tổng kết 15:20, chấm lại tín hiệu thứ Bảy | repo này + `ptcp` |
| Kiem thu | 07:41 T2–T6 + mỗi lần push | test canh-bao-mua + gia_lap + danh-muc; hỏng → Telegram | cả 3 repo |
| Quet dinh ky | 14:20 T2–T6 | bộ lọc quét toàn sàn → `ma_mua_bo_loc.json` cho bot | repo này (`bo_loc`) |
| Danh muc hang ngay | 14:50 T2–T6 (08:30 chỉ khi có `nhap.txt` mới) | danh mục THẬT: nhập lệnh, tóm tắt, dashboard, Excel, tiền nhàn rỗi → Telegram (chạy kín) | danh-muc `dmuc` |
| Gia lap | 16:30 (kiểm lại 17:30, 18:53) T2–T6 | tài khoản giả lập theo luật | gia_lap |
| Suc khoe he thong | 19:55 T2–T6 | các workflow có chạy / lỗi không, NAV giả lập | gia_lap |
| Tong ket tuan (gia lap) | 20:17 thứ Sáu | tổng kết tuần giả lập | gia_lap |
| BCTC moi hang dem | 22:13 hằng ngày | tải BCTC kỳ mới vào kho → kéo theo Bat thuong BCTC | danh-muc `ptcp.kho_bctc` |
| Doc bao cao thuong nien | 22:17 hằng ngày | đọc BCTN mới (chiến lược DN, OCR) | danh-muc `ptcp.chien_luoc_dn` |
| Kho BCTC | 00:47 thứ Bảy | làm mới kho BCTC toàn bộ | danh-muc |
| Tai nen 15p | 01:43 thứ Bảy | tải nến 15' (giữ cache backtest) | repo này |
| Boi so nganh | 03:13 thứ Bảy | bội số định giá theo ngành | danh-muc |
| Tra cuu ma | 07:53 thứ Bảy (+ chạy tay) | tra cứu mã đang giữ / theo dõi | danh-muc `ptcp.tra_cuu` |
| Backtest quy But Pha | 09:13 ngày 1 hằng tháng (+ chạy tay) | mốc luật đang chạy (`chuan`) · `von86` tài khoản thật · `von100/101` UPCoM | danh-muc `chay_backtest_quy_b.py` |
| Backtest | 02:17 ngày 2 hằng tháng | backtest điểm vào 15' → `ket_qua_backtest.json` (bot tự chọn cách vào) | repo này |

### Chỉ chạy tay

| Workflow | Ô nhập | Làm gì | Code ở |
|---|---|---|---|
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
