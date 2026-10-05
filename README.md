# Cảnh báo MUA đa khung (+ cảnh báo BÁN mã đang giữ) – MWG, DHC, GMD

Quét các mã theo dõi theo **4 khung** (tuần → ngày → giờ → phút), tiêu chí lấy từ bộ lọc cổ phiếu
(chiến lược `ky_thuat` / `diem_mua`), và **gửi Telegram ngay khi một mã đạt đủ tiêu chí mua**.

| Khung | Vai trò | Tiêu chí |
|---|---|---|
| **Tuần** | Định hướng – **phủ quyết** | MACD tuần > Signal (tuần đã đóng) |
| **Ngày** | Xu hướng & sức khoẻ | **Bắt buộc**: GTGD TB20 ≥ 5 tỷ, KLGD TB20 ≥ 100.000, giá trên SuperTrend(10; 3,5), giá > MA50, MA20 > MA50, MACD ngày > Signal, RSI 45–75, chưa thủng hỗ trợ · **Cộng điểm (cần ≥ 3/9)**: MA50 > MA200, MA20 dốc lên, ADX ≥ 20 & +DI > −DI, cấu trúc tăng, MACD vừa cắt lên, vượt đỉnh 20 phiên, KL đột biến, mạnh hơn VN-Index 3T, cách đỉnh 52T ≤ 15% |
| **Giờ** | Xác nhận động lượng | MACD giờ > Signal VÀ (vừa cắt lên HOẶC vượt đỉnh 10 nến giờ) |
| **15 phút** | Điểm vào | (MACD 15p cắt lên Signal trong 3 nến HOẶC phá đỉnh 20 nến kèm KL ≥ 1,5×) VÀ giá ≥ VWAP phiên VÀ RSI 15p ≤ 75 |
| Rủi ro | | Cắt lỗ thống nhất (đáy xác nhận − 0,5 ATR / giá − 2 ATR / −7%, tối thiểu 1,5 ATR); mục tiêu = đỉnh cũ xác nhận / đỉnh 52T / giá + 3 ATR; **R/R ≥ 2** |

### Nguồn dữ liệu
- **Giá 4 khung (tuần/ngày/giờ/phút):** VNDirect → DNSE → SSI iBoard → VCI → Yahoo, tự chuyển nguồn khi lỗi
  (nguồn không hỗ trợ khung nào thì bỏ qua: VCI chỉ ngày & giờ, Yahoo chỉ ngày). Mọi nguồn lỗi → dùng cache.
  Cuối mỗi lần chạy in dòng *"Nguồn giá đã dùng"* để biết nguồn nào đang sống.
- **ptcp** (thư mục `ptcp/`, bản 3.4): không dùng vnstock / Vietstock; số CP đối chiếu TCBS → VNDirect → Yahoo;
  P/E = giá ÷ (LNST 4 quý ÷ CP lưu hành). Khi sửa ptcp, chép nguyên thư mục `ptcp/` mới đè lên.

### Phần lấy từ bộ phân tích cổ phiếu (ptcp – thư mục `ptcp/`)
Mỗi mã được chạy **phân tích ngày đầy đủ của ptcp 1 lần/ngày** (lưu `cache_ptcp/`, lần tổng kết 15:20 chạy lại):
- **Cắt lỗ thống nhất & mục tiêu đề xuất** của ptcp (đỉnh cũ, kháng cự, AB=CD, Fibo, nền giá, MA, vùng KL, đỉnh 52T;
  chấm bằng XS chạm trước cắt lỗ) → dùng làm cắt lỗ / mục tiêu / R/R của tin MUA NGAY.
- **EV sau phí ≥ 1%** (mô phỏng lịch sử theo luật T+2, trần/sàn, walk-forward) – điều kiện bắt buộc.
- **Sự kiện** KQKD / GDKHQ trong 5 phiên tới (khai báo `SU_KIEN` trong cấu hình) → `CHỜ SAU SỰ KIỆN`.
- VN-Index xấu / RS ở đáy 1 năm → ghi hệ số khối lượng; khuyến nghị cuối của ptcp hiện trong mọi tin.
- `YEU_CAU_PTCP_MUA = True` → chỉ báo khi chính ptcp cũng khuyến nghị MUA (chặt nhất).

Chỉ dùng **nến đã đóng** (giờ, phút, tuần) → tín hiệu không nhấp nháy giữa chừng nến.

**Trạng thái:** ĐỨNG NGOÀI (tuần xấu) → THEO DÕI (ngày chưa đạt) → CHỜ XÁC NHẬN GIỜ → CHỜ ĐIỂM VÀO →
(R/R thấp / CHỜ SAU SỰ KIỆN / EV THẤP) → **MUA NGAY**.

## Trình bày tin Telegram
- Số ghi **kiểu Việt Nam** (78.700 · 5,6%); tiêu đề & nhãn **in đậm**, ghi chú *nghiêng* (HTML Telegram – lỗi định dạng
  thì tự gửi lại dạng chữ thường).
- **MUA NGAY / cảnh báo bán gửi kèm ảnh**: giá 6 tháng, MA20/MA50, mục tiêu – cắt lỗ (– giá vốn nếu đang giữ).
- **Tổng kết 15:20 gửi kèm ảnh bảng**: mỗi mã 1 dòng (giá, trạng thái, 4 khung ✔/✘, mục tiêu, cắt lỗ, R/R, ptcp),
  tô màu theo trạng thái. Tắt ảnh: `GUI_ANH = False` trong `canh_bao/cau_hinh.py`.

## Cảnh báo BÁN cho mã đang giữ
Bot đọc **`danh_muc.csv` của repo riêng tư `danh-muc`** (mã có `so_cp` > 0 = đang giữ) và quét cùng lúc với cảnh báo mua:

| Mức | Khi nào |
|---|---|
| 🔴 CẮT LỖ | giá ≤ `cat_lo_dat` (thiếu thì `cat_lo_goc`) |
| 🟢 CHỐT LỜI | giá ≥ `muc_tieu_dat` (thiếu thì `gia_muc_tieu`) |
| 🟠 CÂN NHẮC BÁN | MACD tuần < Signal / giá dưới SuperTrend ngày / ptcp khuyến nghị BÁN |
| 🟡 DỜI CẮT LỖ | lãi ≥ 1R mà cắt lỗ còn dưới giá vốn → gợi ý nâng lên hoà vốn |

Mỗi mức báo **1 lần khi xuất hiện**, nếu vẫn còn thì nhắc lại 1 lần/ngày. Tổng kết 15:20 có thêm mục 💼 VỊ THẾ ĐANG GIỮ.
Mã đang giữ mà là tín hiệu MUA NGAY → tin ghi rõ "MUA THÊM".

**Bảo mật (repo này công khai):** tin có số CP / giá vốn chỉ gửi Telegram, **không in ra log Actions**; mã chỉ có
trong danh mục không hiện tên trong log, không ghi vào `lich_su_tin_hieu.csv`; trạng thái chống báo trùng của lệnh
bán lưu trong cache Actions (`cache_ptcp/`), không commit. `danh_muc.csv` nằm trong `.gitignore`.

**Cài đặt (1 lần):**
1. GitHub → Settings (tài khoản) → Developer settings → **Fine-grained personal access tokens** → Generate:
   *Repository access*: **Only select repositories → danh-muc**; *Permissions → Repository → Contents: Read-only*;
   thời hạn tuỳ chọn (hết hạn thì tạo lại).
2. Repo **canh-bao-mua** → Settings → Secrets and variables → Actions:
   - Secrets: `DANH_MUC_TOKEN` = token vừa tạo
   - Variables: `DANH_MUC_REPO` = `ten-ban/danh-muc` (tuỳ chọn `DANH_MUC_PATH` nếu file không ở gốc repo)
3. Chạy thử: Actions → Canh bao mua → Run workflow → `tong_ket`. Log phải có dòng
   `Vị thế đang giữ: N mã (nguồn: repo danh-muc)`; nếu báo `GitHub HTTP 404` → sai tên repo hoặc token chưa được cấp repo đó.

Cắt lỗ / mục tiêu đã đặt do repo `danh-muc` cập nhật mỗi ngày 15:45 → bot tự dùng mức mới, không phải nhập 2 nơi.
Chạy trên máy: đặt `danh_muc.csv` cạnh `chay.py`; bỏ cảnh báo bán: `python chay.py --khong_ban`.

## Lịch chạy (GitHub Actions)
- Mỗi **15 phút** trong phiên (9:00–11:30, 13:00–14:45): chỉ gửi tin khi một mã **vừa chuyển** sang MUA NGAY.
- **15:20**: gửi bảng tổng kết 4 khung của mọi mã.
- Ngày nghỉ lễ: tự bỏ qua (không có dữ liệu phiên hôm nay).

## Cài đặt
1. Tạo repo **Private**, upload toàn bộ nội dung thư mục này (kể cả `.github/workflows/canh_bao.yml`).
2. Settings → Secrets and variables → Actions → Secrets: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Settings → Actions → General → Workflow permissions: **Read and write permissions**.
4. Actions → **Canh bao mua** → Run workflow (chọn `tong_ket`) để thử.

## Tuỳ chỉnh – `canh_bao/cau_hinh.py`
`MA_THEO_DOI`, ngưỡng từng khung, `KHUNG_PHUT` ("5"/"15"/"30"), `RR_TOI_THIEU`, `CHAN_KHI_THI_TRUONG_XAU`, `BAO_LAI_TRONG_NGAY`.

## Chạy tay
```
pip install -r requirements.txt
python chay.py --che_do tong_ket --khong_gui
python -m pytest -q
```
Công cụ tham khảo – không phải khuyến nghị đầu tư.
