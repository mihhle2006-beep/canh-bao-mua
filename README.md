# 📈 Cảnh báo mua cổ phiếu

Bot Telegram chạy trên GitHub Actions. Mỗi ngày bot chọn mã nên mua, báo lúc nào mua trong phiên,
nhắc bán mã đang giữ và gửi tổng kết cuối ngày.

> Công cụ tham khảo, không phải khuyến nghị đầu tư.

## Bot gửi gì, khi nào (giờ Việt Nam, UTC+7)

| Giờ | Tin gửi |
|---|---|
| 9:00 – 14:45, mỗi 15 phút (T2–T6) | 🟢 MUA NGAY · ⏰ MUA ATC · 🚫 BỎ cho mã trong danh sách mua hôm trước; cảnh báo bán mã đang giữ |
| 15:20 (T2–T6) | Tổng kết: thị trường, danh sách mua phiên tới, file Excel và file HTML "Bảng tổng hợp" |
| 16:20 ngày 1 hằng tháng | 🚀 File HTML "Siêu CP tiềm năng": mã vốn hoá ≤ 10.000 tỷ, thanh khoản tăng ≥ 1,3× (danh sách theo dõi, chưa phải lệnh mua) |
| 9:07 thứ Bảy | Không gửi tin: chấm lại đúng/sai mọi tín hiệu cũ, kết quả xem trong log |

- Ngày nghỉ lễ bot tự bỏ qua.
- Backtest (chạy hằng tháng hoặc chạy tay) **không gửi Telegram**, kết quả xem trong log.
  Riêng phần `chuan` (ngày 1 hằng tháng) gửi 1 tin: backtest luật hiện tại và đối chiếu với giả lập.
- File HTML "Bảng tổng hợp" có đủ chi tiết: theo dõi các khuyến nghị đã gửi, danh sách mã từ bộ lọc.
  Tin Telegram chỉ ghi những việc cần làm.

## Cách đọc một dòng mua

Ví dụ (giá tính bằng nghìn đồng):
`★ ABC | 20.00–21.00 | MT 22.00 → 26.00 | CL 19.50 | đặt LO 20.30 | 💰 ≤7.0% NAV`

- **★**: mã ưu tiên trong tuần (tối đa 5 mã).
- **20.00–21.00**: vùng mua. Chỉ mua khi giá nằm trong vùng. Mở cửa cao hơn vùng thì không đuổi.
- **MT**: mục tiêu 1R → 3R. Đây là mốc để dời cắt lỗ lên, không phải lệnh bán.
- **CL**: giá cắt lỗ. Giá chạm mức này thì bán.
- **đặt LO**: giá đặt lệnh LO trước giờ mở cửa (ở ⅓ dưới của vùng mua).
  Không khớp: mã ★ mua ATC nếu giá còn trong vùng; mã không ★ thì bỏ.
- **💰 ≤ X% NAV**: mua tối đa X% tài sản cho mã này (đã nhân sẵn mọi hệ số).
  Số cổ = NAV × X% ÷ (giá × 1.000). VD NAV 10 tr, ≤5.4%, giá 11.15 → 540.000 ÷ 11.150 ≈ 48 cổ.

## Dòng 🌡 nhiệt thị trường

- Cho biết mức rủi ro mỗi lệnh mới: 0,75% × hệ số dài hạn (xu hướng VN-Index, độ rộng) × hệ số ngắn hạn (6 chỉ báo).
- Thị trường càng nóng, hệ số càng nhỏ → mua ít đi. Danh mục sụt từ đỉnh cũng tự giảm thêm.
- **Độ rộng** (từ 29/10/2026): xét 100 mã thanh khoản nhất (chốt thứ Sáu tuần trước). Nếu VN-Index không giảm nhưng
  phần lớn mã đang giảm (**tăng giả**), hoặc VN-Index lãi 60 phiên hơn trung vị các mã trên 10 điểm trong khi trung vị
  đang âm (**hẹp**), thì rủi ro lệnh mới và trần tổng rủi ro mở cùng nhân ½. Trong dòng 💰, phần này ghi là "độ rộng ×0.5".

## Mục 🎣 Hệ bắt đáy (từ 29/10/2026)

- Hệ chỉ dùng **tiền B đang để không**: tổng tối đa 30% NAV, chia 6 mã, mỗi mã tối đa 5% NAV. B luôn được ưu tiên tiền.
  Thiếu tiền cho lệnh B thì bán bớt mã bắt đáy.
- Hệ chỉ mua khi thị trường rơi sâu. Cần một trong hai điều kiện:
  - VN-Index cách đỉnh 1 năm ≥ 15% và Stochastic VN-Index vừa cắt lên;
  - RSI tuần của VN-Index < 35 và VN-Index trên MA20.
- Mã được chọn: trong top 100 thanh khoản, đã giảm ≥ 20% từ đỉnh 60 phiên, và vừa đóng cửa vượt lên MA10.
  Mã giảm sâu hơn được ưu tiên.
- 🟢 **MUA ATO** và 🔻 **BÁN ATO**: đặt lệnh ATO phiên tới. Hệ bán khi có một trong ba điều kiện:
  - đóng cửa ≤ giá mua −10%;
  - đã giữ đủ 30 phiên;
  - Stochastic đã lên ≥ 80 rồi %K cắt xuống %D.
- Bot tự theo dõi danh mục của hệ (mục "Đang giữ"). Bạn chỉ cần làm theo lệnh ATO. Mã nào không mua được vì thiếu tiền
  thì bỏ qua.
- Backtest 2013–2026 (B + Trứng vàng, khớp như bot): thêm độ rộng ×½ và hệ bắt đáy nâng Calmar từ 1,18 lên 1,29,
  MDD từ −16,1% còn −15,1%.

## Cài đặt

Vào **Settings → Secrets and variables → Actions**:

| Loại | Tên | Dùng để |
|---|---|---|
| Secret | `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | Gửi tin Telegram |
| Secret | `DANH_MUC_TOKEN_GHI` | Token đọc/ghi các repo riêng tư (lấy thư viện `ptcp/`, đọc danh mục để cảnh báo bán) |
| Variable | `DANH_MUC_REPO` | Tên repo danh mục, ví dụ `ten-ban/danh-muc` |

Tuỳ chọn: `PTCP_REPO`, `PTCP_PATH` (nếu `ptcp/` nằm ở repo khác), `VNSTOCK_API_KEY`,
và các bot/chat Telegram riêng cho tin danh mục, giả lập.

Thêm: **Settings → Actions → General → Workflow permissions** chọn *Read and write*.

## Chạy thử bằng tay

Actions → **Canh bao mua** → **Run workflow**:

- **che_do**: `tong_ket` (tổng kết), `trong_phien` (quét 15 phút), `lich_su` (chấm lại tín hiệu), `tu_dong`.
- **ma**: nhập `FPT` hoặc `FPT,HPG` để xem riêng vài mã.
- **chi_thu**: tích vào để chạy thử. Không gửi Telegram, không lưu trạng thái, kết quả chỉ xem trong log.

Chạy trên máy: `pip install -r requirements.txt` rồi `python chay.py --che_do tong_ket --khong_gui`.
Cấu hình nằm trong `canh_bao/cau_hinh.py`.

## Bảo mật

Repo này công khai. Danh mục thật không được commit và không in ra log; tin riêng chỉ gửi qua Telegram.
Các workflow riêng tư (danh mục, giả lập, sức khoẻ, tổng kết tuần) chạy kín, log chỉ in mã thoát.
