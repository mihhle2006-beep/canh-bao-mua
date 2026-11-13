# 📈 Cảnh báo mua cổ phiếu

> **Cái gì ở đâu, chạy thế nào:** xem [CAU_TRUC.md](CAU_TRUC.md) (30 workflow, lịch, cách bấm chạy, code nằm ở repo nào).

Bot Telegram chạy trên GitHub Actions. Mỗi ngày bot chọn mã nên mua, báo lúc nào mua trong phiên,
nhắc bán mã đang giữ và gửi tổng kết cuối ngày.

> Công cụ tham khảo, không phải khuyến nghị đầu tư.

## Bot gửi gì, khi nào (giờ Việt Nam, UTC+7)

| Giờ | Tin gửi |
|---|---|
| ~8:00 – 8:15 (T2–T6, khi có lệnh) | ⏰ LỆNH ATO HÔM NAY: mã phải bán ATO + mã hệ bắt đáy mua ATO (1 tin riêng) |
| 9:00 – 14:45, mỗi 15 phút (T2–T6) | 🟢 MUA NGAY · ⏰ MUA ATC · 🚫 BỎ cho mã trong danh sách mua hôm trước (nhiều mã cùng lúc: tin riêng chỉ mã ★, còn lại 1 dòng dự phòng trong tin 📋); cảnh báo bán mã đang giữ |
| 15:20 (T2–T6) | Tổng kết: thị trường, danh sách mua phiên tới, file Excel và file HTML "Bảng tổng hợp" |
| 16:20 ngày 1 hằng tháng | 🚀 File HTML "Siêu CP tiềm năng": mã vốn hoá ≤ 10.000 tỷ, thanh khoản tăng ≥ 1,3× (danh sách theo dõi, chưa phải lệnh mua) |
| 9:07 thứ Bảy | Không gửi tin: chấm lại đúng/sai mọi tín hiệu cũ, kết quả xem trong log |

- Ngày nghỉ lễ bot tự bỏ qua.
- Backtest (chạy hằng tháng hoặc chạy tay) **không gửi Telegram**, kết quả xem trong log.
  Riêng phần `chuan` (ngày 1 hằng tháng) gửi 1 tin: backtest luật hiện tại và đối chiếu với giả lập.
- File HTML "Bảng tổng hợp" có đủ chi tiết: theo dõi các khuyến nghị đã gửi, danh sách mã từ bộ lọc.
  Tin Telegram chỉ ghi những việc cần làm.

## Cách đọc một mã mua

Ví dụ (giá tính bằng nghìn đồng), mỗi mã 3 dòng:

```
★1 ABC 20.50 | MUA MỚI · MACD ngày cắt lên
   Vùng mua 20.00 – 21.00 · Đặt LO 20.30 · Cắt lỗ 19.50 (-4.9%)
   Mục tiêu 1R 21.50 → 3R 23.50 · 💰 ≤7.0% NAV
```

- **★1**: thứ tự nên mua trong tuần (có giới hạn số mã mới mỗi tuần).
- **Vùng mua**: chỉ mua khi giá nằm trong vùng. Mở cửa cao hơn vùng thì không đuổi.
- **Đặt LO**: giá đặt lệnh LO trước giờ mở cửa (ở ⅓ dưới của vùng mua), chỉ có khi cách vào là LO.
  Cách vào chung (chờ tin 🟢 15', ATC cuối phiên, khi nào bỏ) ghi 1 lần ở dòng 🎯 đầu tin.
- **Cắt lỗ**: giá chạm mức này thì bán.
- **Mục tiêu 1R → 3R**: mốc để dời cắt lỗ lên, không phải lệnh bán.
- **💰 ≤ X% NAV**: mua tối đa X% tài sản cho mã này (đã nhân sẵn mọi hệ số).
  Số cổ = NAV × X% ÷ (giá × 1.000). VD NAV 10 tr, ≤5.4%, giá 11.15 → 540.000 ÷ 11.150 ≈ 48 cổ.
- Chỉ mã ★ (mua được trong tuần) ghi đủ 3 dòng; mã #6 trở đi gộp 1 dòng **Dự phòng** (chỉ mua khi mã ★ không vào được).
- **⏰ LỆNH ATO HÔM NAY** (tin riêng, khoảng 8:00–8:15, trước giờ mở cửa): mã đang giữ phải bán ATO theo đóng cửa phiên
  trước (chạm cắt lỗ, gãy MA10 tuần, hết hạn, hệ bắt đáy báo bán, cột `ban_ato`) và mã hệ bắt đáy mua ATO. Không có lệnh
  thì không gửi; mã đã nhắc ở đây không bị báo lặp trong phiên.
- Mục 💼 **Đang giữ** (tin riêng): mỗi mã 1 dòng (giá, lãi/lỗ, việc cần làm, cắt lỗ). Ngày mua, giá vốn, mục tiêu tiếp
  nằm ở tin 📊 DANH MỤC – không lặp lại.

## Dòng 🌡 nhiệt thị trường

- Cho biết mức rủi ro mỗi lệnh mới: rủi ro gốc × hệ số dài hạn (xu hướng VN-Index, độ rộng) × hệ số ngắn hạn (6 chỉ báo).
- Thị trường càng nóng, hệ số càng nhỏ → mua ít đi. Danh mục sụt từ đỉnh cũng tự giảm thêm.
- **Độ rộng** (từ 29/10/2026): xét rổ mã thanh khoản nhất (chốt thứ Sáu tuần trước). Nếu VN-Index không giảm nhưng
  phần lớn mã đang giảm (**tăng giả**), hoặc VN-Index vượt xa trung vị các mã trong khi trung vị đang âm (**hẹp**), thì rủi ro
  lệnh mới và trần tổng rủi ro mở cùng giảm. Trong dòng 💰, phần này ghi là "độ rộng ×…".

## Mục 🎣 Hệ bắt đáy (từ 29/10/2026)

- Hệ chỉ dùng **tiền B đang để không** (có trần tổng và trần mỗi mã). B luôn được ưu tiên tiền.
  Thiếu tiền cho lệnh B thì bán bớt mã bắt đáy.
- Hệ chỉ mua khi thị trường rơi sâu (VN-Index giảm mạnh từ đỉnh / quá bán rồi bật lên).
- Mã được chọn: trong rổ thanh khoản, đã giảm sâu từ đỉnh gần và vừa đóng cửa vượt lên MA10. Mã giảm sâu hơn được ưu tiên.
- 🟢 **MUA ATO** và 🔻 **BÁN ATO**: đặt lệnh ATO phiên tới. Hệ bán khi chạm mức cắt lỗ, giữ đủ số phiên tối đa, hoặc
  Stochastic quá mua rồi cắt xuống.
- Bot tự theo dõi danh mục của hệ (mục "Đang giữ"). Bạn chỉ cần làm theo lệnh ATO. Mã nào không mua được vì thiếu tiền
  thì bỏ qua.

> Ngưỡng / hệ số cụ thể của các luật trên (và của Quỹ Bứt Phá) nằm ở repo kín danh-muc: `ptcp/cau_hinh.py`,
> mô tả đầy đủ `LUAT_CHI_TIET.md`.

## 📊 Bảng thị trường (web)

Trang `docs/thi_truong/` (GitHub Pages, cùng site với Bảng tổng hợp) – dữ liệu thị trường công khai + mục 💼 CHỈ mã đang giữ:
chỉ số + VN-Index trong phiên (1D…1Y), bản đồ nhiệt HOSE theo ngành (vốn hoá / GTGD / nước ngoài / tự doanh), thống kê
phiên (độ rộng, GTGD & dự kiến cả phiên so TB20, khối ngoại, tự doanh), 10 mã kéo / đè VN-Index, và **Lọc mã** (biến động,
dòng tiền, khối ngoại gom / xả ≥ 5 phiên, vượt đỉnh / thủng đáy 52 tuần, cắt MA20 / MA50, RSI).
Trang ở repo riêng **bang-thi-truong**: `https://<tài khoản>.github.io/bang-thi-truong/` (địa chỉ cũ `…/canh-bao-mua/thi_truong/`
chuyển hướng sang). Trong phiên repo đó tự cập nhật **~30 giây / lượt** (workflow `bang.yml` – bản gốc `bang_rieng/bang.yml`,
code `thi_truong/vong_bang.py`; đồng hồ gọi 08:50 / 12:50): mỗi lượt 1 file tên mới trên nhánh `nhanh` (trang đọc qua
raw.githubusercontent.com), 10' / lần cập nhật Pages. Ở repo này workflow `Bang thi truong` chỉ còn 15' / lần (Tra cứu mã),
15:10 chốt phiên, 19:07 chuẩn bị dữ liệu (đẩy sang nhánh `chuan-bi` của bang-thi-truong).

## 🔎 Tra cứu mã (web)

Trang `docs/ma/` (`…/canh-bao-mua/ma/#TCB`, `#TCB/tai-chinh`…) – ~750 mã HOSE / HNX, dạng app với 9 mục:
**Tổng quan** (biểu đồ nến 2 năm + MA10/20/50/200 + khối lượng, hiệu suất 1 ngày → 1 năm, thống kê giá, beta, chỉ số cơ bản,
góc hệ thống: xu hướng, RSI / MACD, khối ngoại & tự doanh, giá trị hợp lý, ★ bot) · **Tài chính** (KQKD / CĐKT / LCTT quý / năm
đầy đủ chỉ tiêu, biểu đồ, F-Score, Z-Score, DuPont, so với ngành theo phân vị, chỉ số theo quý) · **Định giá** (giá trị hợp lý,
P/E – P/B lịch sử với dải ±1σ, giá mục tiêu Vietcap + CTCK, kế hoạch ĐHCĐ) · **Cổ đông** (cơ cấu, room ngoại, cổ đông lớn, giao
dịch nội bộ) · **Cổ tức & sự kiện** · **Lịch sử giá** (giá / nước ngoài / cung cầu / tự doanh) · **Tin & báo cáo** (CafeF, báo
cáo CTCK) · **Hồ sơ** (thành lập, niêm yết, vốn điều lệ, giá chào sàn, công ty con – liên kết, ban lãnh đạo) · **Phân tích hệ
thống** (bất thường BCTC + giải thích, chiến lược DN qua BCTN). Tab **Lọc KQKD** và **Ngành** cho cả sàn.
Dữ liệu: workflow `Du lieu tra cuu` (06:41 T2–T7) – danh-muc `ptcp/web_tra_cuu.py` (BCTC, định giá, F / Z / DuPont…) +
`thi_truong/tra_cuu_dn.py` (Vietcap IQ / KBS / Simplize / CafeF – xoay vòng mã cũ nhất trước) → cache → `Bang thi truong` gói
cùng khi triển khai. Chỉ số liệu công bố công khai.

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
