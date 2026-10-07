# Cảnh báo MUA đa khung (+ cảnh báo BÁN mã đang giữ + bản tin chiến lược CL1/CL2) – MWG, DHC, GMD

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
- **ptcp – MỘT nguồn duy nhất:** bot KHÔNG giữ bản sao ptcp nữa. Mỗi lần chạy, bước *"Lấy ptcp"* của workflow clone
  repo **danh-muc** (token chỉ đọc `DANH_MUC_TOKEN` đã có) và chép `ptcp_phan_tich/ptcp` vào cạnh `chay.py` → sửa ptcp
  một lần trong danh-muc là bot, danh mục và Colab cùng dùng bản mới. Đổi repo/thư mục: Variables `PTCP_REPO`,
  `PTCP_PATH`. Chạy trên máy: `python lay_ptcp.py --tu ../ptcp_phan_tich/ptcp`.

### Phần lấy từ bộ phân tích cổ phiếu (ptcp – thư mục `ptcp/`)
Mỗi mã được chạy **phân tích ngày đầy đủ của ptcp 1 lần/ngày** (lưu `cache_ptcp/`, lần tổng kết 15:20 chạy lại):
- **Cắt lỗ thống nhất & mục tiêu đề xuất** của ptcp (đỉnh cũ, kháng cự, AB=CD, Fibo, nền giá, MA, vùng KL, đỉnh 52T;
  chấm bằng XS chạm trước cắt lỗ) → dùng làm cắt lỗ / mục tiêu / R/R của tin MUA NGAY.
- **EV sau phí ≥ 1%** (mô phỏng lịch sử theo luật T+2, trần/sàn, walk-forward) – điều kiện bắt buộc.
- **Sự kiện** KQKD / GDKHQ trong 5 phiên tới (khai báo `SU_KIEN` trong cấu hình) → `CHỜ SAU SỰ KIỆN`.
- VN-Index xấu / RS ở đáy 1 năm → ghi hệ số khối lượng; khuyến nghị cuối của ptcp hiện trong mọi tin.
- `YEU_CAU_PTCP_MUA = True` → chỉ báo khi chính ptcp cũng khuyến nghị MUA (chặt nhất).
- **Vùng mua điều chỉnh** của ptcp (mã chưa mua): vùng hỗ trợ trùng nhau, trạng thái (chờ về vùng / trong vùng /
  đã xác nhận), cắt lỗ dưới vùng và phễu lịch sử (% lần giá về vùng, % lệnh đạt +1R) – hiện trong tin khi ptcp chưa MUA.
- **Kết luận backtest** Phần I của ptcp (câu hành động: ÁP DỤNG / KHÔNG giao dịch ngắn hạn / ĐỨNG NGOÀI) – 1 dòng
  trong tin MUA NGAY và tổng kết.

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

Mức bán theo **HỆ THOÁT MỚI** của ptcp (`ptcp/he_thoat.py`, gốc T2-3R-ma10 – cùng logic với backtest), tính lại
mỗi lần chạy từ `ngay_mua` trên các **phiên đã đóng cửa**; cắt lỗ **chỉ dời lên**, **không chốt lời ở mục tiêu cố định**:

| Tầng | Lãi hiện tại | Cắt lỗ |
|---|---|---|
| 0 | < 1R | cắt lỗ ban đầu `cat_lo_goc` (thiếu → giá − 2×ATR, tối đa −7%, tối thiểu 1,5×ATR). 1R = giá vốn − cắt lỗ ban đầu |
| 1 | ≥ 1R | đóng cửa cao nhất − 3×ATR, không dưới hoà vốn + phí |
| 2 (tuần) | ≥ 3R | bán khi **đóng cửa tuần < MA10 tuần**; sàn khoá lãi 2R |
| – | 63 phiên mà < 1R | lệnh không chạy → bán |

Cắt lỗ hiệu lực = mức **cao hơn** giữa hệ thống và `cat_lo_dat` trong danh mục (không bao giờ hạ cắt lỗ bạn đã đặt).

| Mức | Khi nào |
|---|---|
| 🔴 CẮT LỖ | giá ≤ cắt lỗ hiệu lực |
| 🔴 BÁN – GÃY XU HƯỚNG TUẦN | đang ở tầng tuần và tuần đã đóng có đóng cửa < MA10 tuần → bán đầu phiên tới |
| 🟠 BÁN – LỆNH KHÔNG CHẠY | giữ ≥ 63 phiên mà lãi chưa đạt 1R |
| 🟡 DỜI CẮT LỖ | cắt lỗ hệ thống cao hơn `cat_lo_dat` ≥ 0,5% (lên tầng / cắt lỗ động đi lên) → sửa danh mục |

Tin bán ghi tầng hiện tại, lãi theo R, mốc kế tiếp (1R → hoà vốn, 3R → khung tuần) và nhắc khi CP chưa về (T+2).
Thiếu giá vốn / dữ liệu, ptcp cũ chưa có `theo_doi_vi_the`, hoặc `DUNG_HE_THOAT = False` → tự quay về cách cũ
(🟢 CHỐT LỜI ở mục tiêu đặt tay, 🟠 CÂN NHẮC BÁN theo MACD tuần / SuperTrend / ptcp).
Tin MUA NGAY có thêm dòng **Kế hoạch thoát** (giá 1R, 3R) – mục tiêu trong tin chỉ để tham khảo.

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
   - Token này cũng dùng để **lấy ptcp** từ repo danh-muc (bước "Lấy ptcp") – nếu ptcp nằm ở repo khác, đặt
     Variable `PTCP_REPO` và cấp thêm repo đó cho token.
3. Chạy thử: Actions → Canh bao mua → Run workflow → `tong_ket`. Log phải có dòng
   `Vị thế đang giữ: N mã (nguồn: repo danh-muc)`; nếu báo `GitHub HTTP 404` → sai tên repo hoặc token chưa được cấp repo đó.

Cắt lỗ / mục tiêu đã đặt do repo `danh-muc` cập nhật mỗi ngày 15:45 → bot tự dùng mức mới, không phải nhập 2 nơi.
Chạy trên máy: đặt `danh_muc.csv` cạnh `chay.py`; bỏ cảnh báo bán: `python chay.py --khong_ban`.

## Nhật ký & chấm điểm tín hiệu (ĐÚNG / SAI)
Module `canh_bao/nhat_ky.py` ghi lại mọi tín hiệu bot đã phát rồi **tự chấm bằng giá thực tế** ở mỗi lần tổng kết 15:20.
Bộ chấm là **`ptcp/nhat_ky.py`** – cùng một cách chấm với Phần K của ptcp trên Colab và repo danh-muc.

| Loại | Ghi khi | Chấm ĐÚNG khi |
|---|---|---|
| **MUA NGAY** | gửi tin MUA NGAY | lệnh mua ở giá lúc báo chạm **mục tiêu trước cắt lỗ**, hoặc hết hạn mà lãi sau phí > 0 |
| **ptcp – nhóm MUA** | khuyến nghị ptcp **đổi** sang MUA / MUA TỪNG PHẦN | như trên, mua giả định ở giá mở cửa phiên sau |
| **ptcp – CHỜ / ĐỨNG NGOÀI** | khuyến nghị đổi sang THEO DÕI, CHỜ…, CHƯA MUA, KHÔNG MUA MỚI | lệnh mua giả định đó **lỗ** (tránh được lỗ); lãi → SAI (bỏ lỡ) |
| **BÁN** (mã đang giữ) | gửi 🔴 CẮT LỖ / 🔴 GÃY XU HƯỚNG TUẦN / 🟠 LỆNH KHÔNG CHẠY (cách cũ: CHỐT LỜI / CÂN NHẮC BÁN) | sau `KY_HAN_BAN` (20) phiên giá đóng cửa ≤ giá lúc báo |

- Chấm theo luật VN như backtest của ptcp: T+2, phiên khoá trần không mua được, khoá sàn không bán được, gap,
  cắt lỗ và mục tiêu cùng phiên → tính cắt lỗ, trừ phí + trượt giá 0,6%. Hạn lệnh mua = kỳ hạn ptcp (63 phiên).
- Kết quả: `ĐÚNG` · `SAI` · `ĐANG CHỜ` (có lãi/lỗ tạm tính) · `BỎ QUA` (không vào được lệnh / thiếu mức giá).
- Tin tổng kết có thêm mục **📊 ĐỘ CHÍNH XÁC TÍN HIỆU** (tỷ lệ đúng, TB lãi/lỗ theo từng nhóm; < 30 mẫu ghi "ít mẫu").
- Xem chi tiết: `python chay.py --che_do lich_su` → in bảng + xuất `danh_gia_tin_hieu.xlsx` (sheet *Thống kê*, *Nhật ký*
  tô màu xanh/đỏ/vàng). Lần đầu tự nhập các tin MUA NGAY cũ từ `lich_su_tin_hieu.csv`.
- **Bảo mật:** `lich_su_danh_gia.csv` (commit, công khai) chỉ có mã theo dõi; cảnh báo BÁN & mã chỉ có trong danh mục
  nằm ở `cache_ptcp/lich_su_danh_gia_rieng.csv` (cache Actions, không commit) và chỉ hiện trong tin Telegram riêng tư.
  Cache Actions có thể bị xoá nếu repo không chạy > 7 ngày → muốn giữ lâu dài thì tải file về định kỳ.
- Tắt: `GHI_NHAT_KY = False`; chỉnh `KY_HAN_MUA`, `KY_HAN_BAN`, `CHI_PHI_KHU_HOI` trong `canh_bao/cau_hinh.py`.

## Bản tin chiến lược CL1 / CL2 (theo thị trường)
Sau tổng kết 15:20 bot gửi thêm **📈 CHIẾN LƯỢC THEO THỊ TRƯỜNG** (`canh_bao/chien_luoc_bot.py`, dùng
`ptcp/chien_luoc.py` + `ptcp/he_thoat.py` – cùng logic với `chien_luoc_thang` trên Colab):
- **Điểm thị trường 8 chỉ báo** của VN-Index (✔/✘ từng chỉ báo): VNI > MA200, MA50 > MA200, MA200 dốc lên,
  động lượng 6 tháng & 3 tháng > 0, cách đỉnh 1 năm < 10%, > 50% mã trên MA200, biến động 20 phiên < trung vị 1 năm.
- **CL đang áp dụng**: chỉ đổi ở **phiên cuối tháng**, có vùng đệm: điểm ≥ 5 → CL2, ≤ 2 → CL1, 3–4 giữ nguyên
  (tránh đổi qua lại). CL1 = A0 50% + B 50% (an toàn) · CL2 = A0 70% + ETF VN-Index 30% (lãi).
  Có dòng *Điều kiện đổi* (cần thêm/mất bao nhiêu điểm).
- **③ Hành động phiên tới** trên 41 mã đã backtest (`MA_CHIEN_LUOC`), chỉ thành phần đang có tỷ trọng, viết cho
  người CHƯA mua (dùng chung `ptcp.chien_luoc.hanh_dong`):

  | Nhóm | Khi nào | Làm gì |
  |---|---|---|
  | 🟢 MUA MỚI | tín hiệu MACD hôm nay | mua giá mở cửa, không mua nếu mở cửa > "mua ≤" |
  | ✅ VÀO ĐƯỢC NHƯ LỆNH MỚI | hệ thống đang giữ, lãi < 1R, cắt lỗ cách ≤ 7% | mua đủ khối lượng, dùng cắt lỗ của hệ thống |
  | 🟡 VÀO ½ KHỐI LƯỢNG | hệ thống lãi 1–2R, cắt lỗ cách ≤ 7% | mua một nửa |
  | ⏳ CHỜ ĐIỀU CHỈNH | lãi ≥ 2R hoặc cắt lỗ cách > 7% | chờ giá về ≤ "chờ" (cách cắt lỗ 5%) hoặc tín hiệu mới |
  | 🔻 BÁN PHIÊN TỚI | đóng cửa tuần < MA10 tuần | không mua; đang giữ thì bán |

  Khối lượng = 1% vốn ÷ (giá mua − cắt lỗ). Ngưỡng chỉnh trong ptcp (`VT_RUI_RO_TOI_DA`, `VT_R_NHU_MOI`, `VT_R_NUA`).
- Khi CL đổi so với lần chạy trước → gửi thêm tin **🔔 ĐỔI CHIẾN LƯỢC CLx → CLy** kèm tỷ trọng mới.
- Đây là **mô phỏng của hệ thống – tin công khai**, không dùng danh mục thật.
- Chỉ gửi bản tin: `python chay.py --che_do chien_luoc` · tổng kết không kèm bản tin: `--khong_chien_luoc` ·
  tắt hẳn: `DUNG_CHIEN_LUOC = False`. Đổi danh sách mã: `MA_CHIEN_LUOC`; hiển thị tối đa `SO_MA_TRONG_TIN` dòng/mục.
- CL hiện tại lưu ở `trang_thai_chien_luoc.json` (chỉ có số CL & điểm – công khai được) để biết khi nào ĐỔI; thiếu
  file thì bot vẫn báo đổi nếu đổi đúng ở phiên cuối tháng vừa đóng.
- Lần tổng kết tải thêm ~41 mã (dùng lại dữ liệu đã tải của mã theo dõi) → chạy lâu hơn khoảng 1–2 phút.

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
python chay.py --che_do chien_luoc --khong_gui
python -m pytest -q
```
Công cụ tham khảo – không phải khuyến nghị đầu tư.
