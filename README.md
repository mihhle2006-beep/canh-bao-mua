# Cảnh báo theo CHIẾN LƯỢC THỊ TRƯỜNG (điểm vào 15' + cảnh báo BÁN mã đang giữ + tổng kết & Excel)

Một nguồn logic duy nhất với Colab / danh-muc (thư mục `ptcp/`, lấy từ repo danh-muc):
**chiến lược** (`ptcp/chien_luoc.py` – điểm thị trường 8 chỉ báo → CL1/CL2, nhóm hành động A0/B) quyết định
**có mua không & mua trong vùng nào**; **khung 15 phút** (`ptcp/diem_vao_15p.py`) chỉ quyết định **mua lúc nào**;
**hệ thoát** (`ptcp/he_thoat.py`) quyết định **bán**.

### Lịch
| Lúc | Việc |
|---|---|
| 15:20 (tổng kết) | Tin gọn: thị trường & CL · 🟢 MUA MỚI / ✅ VÀO NHƯ LỆNH MỚI / 🟡 VÀO ½: `mã \| vùng mua \| MT 1R → 3R \| CL \| đạt điểm mua` · ⏳ chờ điều chỉnh · ⛔ không vào · 💼 đang giữ (lãi/lỗ theo giá vốn, cắt lỗ hệ thoát, mốc tiếp, **mua thêm** khi đủ điều kiện) + **file Excel** chi tiết & lịch sử. Lưu danh sách mua vào `trang_thai_chien_luoc.json`. |
| 9:00–14:45 mỗi 15' | Chỉ quét mã trong danh sách mua của tối qua, đúng phiên hiệu lực & vùng giá → 🟢 MUA NGAY / ⏰ MUA ATC / 🚫 BỎ (mở cửa vượt vùng, thủng vùng). Mã đang giữ: 🔴 cắt lỗ · 🟠 sát cắt lỗ (≤ 1%) · gãy MA10 tuần · hết hạn · 🟡 dời cắt lỗ (tin riêng tư). |
| Chạy tay `backtest` | Backtest điểm vào 15' (nến 15' thật) & điểm bán / mua thêm → `ket_qua_backtest.json` + Excel. Cách vào tốt nhất tự được dùng (`CACH_VAO_15P = "tu_dong"`). |

### Tiêu chí điểm vào 15' (đồng bộ chiến lược – cùng hàm cho cảnh báo và backtest)
| Khung | Tiêu chí |
|---|---|
| **Ngày (chiến lược)** | nhóm mua của tin tổng kết: MACD ngày cắt lên (A0, không lọc tuần) / hệ thống đang lãi 0–3R & cắt lỗ cách ≤ 7%. **VN-Index đi ngang** (biên dao động 60 phiên < 12%) → A0 chỉ lấy tín hiệu khi MACD tuần > Signal (backtest 41 mã: CAGR 10,8% → 13,0%, Sharpe 0,83 → 1,05, tốt hơn cả 2019–22 và 2023–26) |
| **Vùng** | giá trong vùng mua · mở cửa ≤ cận trên (không đuổi) · chưa rơi < cận dưới trước khi mua · chỉ phiên hiệu lực |
| **15 phút** | MACD 15' cắt lên Signal (≤ 3 nến) HOẶC phá đỉnh 20 nến kèm KL ≥ 1,5× TB20 · giá ≥ VWAP phiên · RSI 15' ≤ 75 |
| **Giờ** (chỉ cách vào `15P+GIO`) | MACD giờ (giờ đã đóng) > Signal |
Cách vào: `ATO` · `15P` · `15P+ATC` (mặc định trước khi backtest) · `15P+GIO` · `VWAP` · `LO` (lệnh LO ở ⅓ dưới vùng) –
`+ATC`: hết phiên chưa có điểm vào mà giá còn trong vùng → mua ATC. **Không còn phủ quyết MACD tuần** (backtest chiến
lược đã chọn A0 = không lọc tuần). Cắt lỗ sau khi mua: MUA MỚI tính lại theo giá mua thật (2×ATR, ≤ 7%); nhóm vào
trễ giữ cắt lỗ hệ thống. MT = mục tiêu tạm thời 1R / 3R (mốc dời cắt lỗ, không phải lệnh bán).

### Mua thêm (mã đang giữ) – đúng luật nhồi lệnh đã backtest (kiểu B)
Đủ cả: lãi ≥ 3R · đóng cửa lập đỉnh mới từ ngày mua · cách lần mua trước ≥ 10 phiên · cắt lỗ hiện tại ≥ giá vốn bình
quân MỚI + phí (chạm cắt lỗ cả vị thế vẫn hoà vốn) · tối đa 2 lần, mỗi lần 25% số CP. Đã mua thêm → cập nhật
`so_cp`, `gia_von` (bình quân), `so_lan_mua_them`, `ngay_mua_them` trong danh_muc.csv.

### Backtest điểm bán (41 mã, 2019–2026, tín hiệu A0)
Chốt ⅓ / ½ ở 3R, siết cắt lỗ 2–2,5×ATR khi VN-Index giảm, hạn 30 phiên/0,5R hoặc 40 phiên/1R đều **kém hơn** hệ thoát
gốc ở cả 2 giai đoạn → giữ nguyên. Mua thêm kiểu B: lô mua thêm lãi TB +5,3% (thắng 39%), lãi TB/lệnh 2,50% → 2,88%.

### Nguồn dữ liệu
VNDirect → DNSE → SSI iBoard → VCI → Yahoo, tự chuyển nguồn, lỗi thì dùng cache. Nến 15' dài cho backtest:
`du_lieu.tai_lich_su_phut` (tải lùi từng 30 ngày, cache `cache_gia/<MÃ>_15_lich_su.csv`).
ptcp KHÔNG nằm trong repo này: bước *"Lấy ptcp"* của workflow chép từ repo danh-muc (Variables `PTCP_REPO`, `PTCP_PATH`).


## Mã tự thêm từ bộ lọc Bo_Loc (2 tuần)

Bo_Loc quét cuối phiên **thứ 2 & thứ 5** (chiến lược `rieng` + `xu_huong`) và ghi mã đạt **MUA** vào `ma_mua_bo_loc.json`.
Tổng kết 15:20 ở đây (`canh_bao/ma_bo_loc.py`):

1. đọc file đó (chỉ khi là lần quét mới) → thêm mã vào danh sách quét, hạn **14 ngày** từ ngày quét
   (mã đã có trong `MA_THEO_DOI` – VN30 + DHC, GMD, MWG – thì bỏ qua; được lọc lại khi đang theo dõi → KHÔNG gia hạn);
2. mã vào nhóm mua 🟢 / ✅ / 🟡 → **đạt yêu cầu mua** → **thêm hạn 14 ngày** từ ngày đạt (mỗi lần đạt lại được thêm),
   đi tiếp cảnh báo 15' như mã khác;
3. hết hạn → **tự xoá**, kể cả mã đang giữ – file này công khai nên không để lộ danh mục. Mã đang giữ vẫn được chăm sóc
   đủ ở phần danh mục **riêng tư** (cảnh báo bán, dời cắt lỗ, 💼 mua thêm). Bo_Loc lọc ra lại sau khi xoá → thêm lại, hạn mới.
   Tin tổng kết có thêm dòng 🔎 (thêm / đạt / xoá).

Trạng thái lưu ở `ma_bo_loc.json` (công khai – chỉ mã & ngày; muốn bỏ sớm 1 mã thì xoá dòng của mã đó).
Cấu hình: `DUNG_BO_LOC`, `BO_LOC_SO_NGAY`, `BO_LOC_REPO` trong `cau_hinh.py`.

**Danh sách cảnh báo** = rổ VN30 (tự lấy online lúc tổng kết – `TU_LAY_VN30`, lỗi thì dùng `MA_VN30` gõ sẵn; log ghi nguồn)
+ `MA_THEM` (DHC, GMD, MWG) + mã từ Bo_Loc. **Độ rộng thị trường** (1 trong 8 chỉ báo) vẫn tính trên 41 mã đã backtest
(`MA_CHIEN_LUOC`, `DO_RONG_THEO_MA_CHIEN_LUOC`) để điểm thị trường / CL1–CL2 không đổi theo danh sách cảnh báo.
Bo_Loc là repo riêng tư → tạo token CHỈ ĐỌC (Contents: Read) cho Bo_Loc, lưu secret **`BO_LOC_TOKEN`**.

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

## Biểu đồ mốc giá kèm tín hiệu – `canh_bao/bieu_do_moc.py`
Mỗi tin **MUA NGAY**, các mã nhóm MUA của tin tổng kết (mua mới / vào như lệnh mới / vào ½, tối đa `ANH_MUA_TOI_DA` ảnh) và
cảnh báo **BÁN / dời cắt lỗ** mã đang giữ (riêng tư, xoá ảnh sau khi gửi) có kèm biểu đồ 120 phiên với các mốc:
cắt lỗ toàn bộ · ½ đường xuống cắt lỗ (**vẫn GIỮ lại**) · điểm mua – mua toàn bộ / mua 1 phần (½) + vùng mua ·
1R mua thêm ½ (khi có tín hiệu mới) & dời cắt lỗ hoà vốn · 2R chốt lời hết nếu đã qua 3R rồi rơi về ·
3R **GIỮ lại** (không chốt 1 phần – backtest chốt ⅓/½ ở 3R kém hơn), chuyển bán theo MA10 tuần. Tắt: `GUI_ANH = False`.

## Theo dõi khuyến nghị đã gửi – `canh_bao/theo_doi_kn.py`
Cuối tin tổng kết có mục **📌 THEO DÕI KHUYẾN NGHỊ ĐÃ GỬI** – "nếu đã mua theo khuyến nghị thì giờ làm gì", không cần nhập
danh mục. Mỗi khuyến nghị MUA của chiến lược (nhật ký `lich_su_danh_gia.csv`) là 1 lệnh giả định: vào giá mở cửa phiên sau
nếu trong vùng mua; chấm lại mỗi ngày bằng đúng hệ thoát của danh mục thật:
🔴 BÁN đầu phiên tới (chạm cắt lỗ / tuần < MA10 khi ≥ 3R / 63 phiên chưa đạt 1R) · ⬆ DỜI cắt lỗ (mỗi mức báo 1 lần) ·
⚠ sát cắt lỗ · 🟢 GIỮ kèm cắt lỗ. Lệnh vừa đóng báo 1 lần (✅ lãi / ❌ lỗ). Mỗi mã 1 dòng; trạng thái lưu `theo_doi_kn.json`
(chỉ khuyến nghị công khai). Mã bạn thật sự mua thì vẫn nên ghi `danh_muc.csv` (giá vốn thật, cảnh báo riêng tư).

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
- **③ Hành động phiên tới** trên mã theo dõi (`MA_THEO_DOI` = VN30 + `MA_THEM` DHC, GMD, MWG) và mã từ Bo_Loc, chỉ thành phần đang có tỷ trọng, viết cho
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
  tắt hẳn: `DUNG_CHIEN_LUOC = False`. Đổi danh sách mã: `MA_VN30` / `MA_THEM` (`MA_CHIEN_LUOC` chỉ còn cho backtest); hiển thị tối đa `SO_MA_TRONG_TIN` dòng/mục.
- CL hiện tại lưu ở `trang_thai_chien_luoc.json` (chỉ có số CL & điểm – công khai được) để biết khi nào ĐỔI; thiếu
  file thì bot vẫn báo đổi nếu đổi đúng ở phiên cuối tháng vừa đóng.
- Lần tổng kết tải thêm ~41 mã (dùng lại dữ liệu đã tải của mã theo dõi) → chạy lâu hơn khoảng 1–2 phút.

## Giao dịch giả lập (vốn ảo) → repo riêng `gia_lap`
Bot mua bán bằng vốn ảo theo đúng tín hiệu của repo này, trên giá thật các phiên sau – chạy ở repo riêng tư
**`gia_lap`** (16:30 mỗi ngày). `gia_lap` đọc danh sách mua từ `trang_thai_chien_luoc.json` mà tổng kết 15:20 commit
lên đây, dùng lại `canh_bao/du_lieu.py` (giá), `canh_bao/vi_the.py` (hệ thoát) và `canh_bao/thong_bao.py` (Telegram).
→ Đừng đổi tên / cấu trúc khoá `ds_mua` trong file này mà không sửa `gia_lap`.

## Xem riêng 1 mã
- **Trên GitHub:** Actions → **Canh bao mua** → **Run workflow** → ô **ma** nhập `FPT` (hoặc `FPT,HPG`) → Run.
  Kết quả (nhóm hành động, vùng mua, cắt lỗ, mục tiêu 1R → 3R) gửi Telegram; KHÔNG đổi danh sách mua / trạng thái của bot.
  Kèm dòng `Cùng ngành: VCB ⏳ · BID ⛔ · TCB 🟡` – trạng thái tối đa 4 mã cùng ngành (bản đồ `ptcp/nganh.py`).
- **Trên máy:** `python chay.py --chi_ma FPT --khong_gui` (cần thư mục `ptcp/` – xem `lay_ptcp.py`).
- Lần chạy 15' trong phiên bỏ bước kiểm thử để tin đến nhanh hơn; tổng kết, chạy tay & backtest vẫn kiểm thử.

**Chạy thử không làm phiền:** Run workflow → tích **chi_thu** → bot chạy đủ nhưng KHÔNG gửi Telegram, KHÔNG commit
trạng thái (danh sách mua, nhật ký, trang tổng hợp) và khôi phục trạng thái riêng (`cache_ptcp`) sau khi chạy. Kết quả xem
trong log – tin có danh mục thật KHÔNG bao giờ in ra log (repo công khai), chỉ ghi "(tin riêng tư … ký tự)".

## Backtest điểm vào 15' – `.github/workflows/backtest.yml`
Chạy **đêm mùng 2 hằng tháng** (02:17 giờ VN) hoặc bấm tay: Actions → **Backtest** → Run workflow (20–60 phút).
Thử mọi cách vào lệnh (ATO, 15P, 15P+ATC, VWAP, LO…) trên nến 15' thật của các tín hiệu mua đã qua + backtest điểm bán /
mua thêm → gửi tin 🧪 kèm Excel, commit `ket_qua_backtest.json`. Cảnh báo trong phiên tự dùng **cách vào tốt nhất**
(`CACH_VAO_15P = "tu_dong"`; muốn cố định thì đặt tên cách vào).

## Trang tổng hợp – `canh_bao/trang_tong_hop.py`
Một trang web thay cho việc đọc rải rác qua Telegram & Excel: ① sức khoẻ thị trường (8 chỉ báo, CL, đi ngang/xu
hướng) · ② tín hiệu hôm nay (danh sách mua phiên tới + trạng thái điểm vào 15') · ③ mã từ bộ lọc Bo_Loc (hạn, đã đạt chưa) · ④ độ chính xác của bot (ĐÚNG/SAI
theo loại tín hiệu). Danh mục giả lập có báo cáo riêng ở repo `gia_lap` (repo riêng tư → không lên trang công khai). Tự sáng/tối, xem tốt trên
điện thoại, không dùng thư viện ngoài.
- **Bản công khai** `docs/index.html`: dựng lại sau mỗi lần chạy (cả 15' trong phiên) và commit. Bật 1 lần:
  Settings → **Pages** → Source *Deploy from a branch* → Branch `main`, thư mục `/docs` → trang ở
  `https://<tên-bạn>.github.io/canh-bao-mua/`. **Không có danh mục thật.**
- **Bản riêng** có mục 💼 danh mục thật (lãi/lỗ, cắt lỗ, hành động, mua thêm): chỉ **gửi Telegram** dạng file HTML lúc
  tổng kết (mở bằng trình duyệt), xoá khỏi máy chạy Actions, không commit. Tắt: `GUI_TRANG_RIENG = False`.
- Trang chỉ đọc file trạng thái → không tải giá, không cần ptcp. Tổng kết lưu thêm điểm thị trường & toàn bộ khuyến
  nghị vào `trang_thai_chien_luoc.json` (công khai – đã có trong tin). File này giờ **được commit** (trước đây không
  commit nên danh sách mua cho cảnh báo 15' sáng hôm sau mất theo máy chạy Actions).
- Tắt hẳn: `DUNG_TRANG_TONG_HOP = False`.

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
