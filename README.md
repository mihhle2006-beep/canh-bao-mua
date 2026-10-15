# 📈 Cảnh báo mua – bán cổ phiếu theo chiến lược thị trường

> Bot Telegram chạy trên GitHub Actions: **chọn mã mua** theo chiến lược thị trường, **báo điểm vào** trong phiên
> bằng nến 15', **báo bán** mã đang giữ theo hệ thoát, rồi **tổng kết** cuối ngày kèm Excel và trang web.
>
> *Công cụ tham khảo, không phải khuyến nghị đầu tư.*

Mọi logic dùng chung thư viện `ptcp/` (lấy từ repo **danh-muc**), nên Colab, danh-muc, gia_lap, Bo_Loc và bot này
luôn tính giống nhau:

| Câu hỏi | Ai trả lời |
|---|---|
| **Có mua không, mua trong vùng nào?** | Chiến lược: `ptcp/chien_luoc.py` (điểm thị trường 8 chỉ báo → CL1/CL2, nhóm A0/B) |
| **Mua lúc nào, giá nào?** | Điểm vào: `ptcp/diem_vao_15p.py` (lệnh LO + ATC) |
| **Bán khi nào?** | Hệ thoát: `ptcp/he_thoat.py` (2R – MA10 tuần) |
| **Mua bao nhiêu?** | Quỹ B: `ptcp/quy_von.py` |

---

## Mục lục
1. [Luật mua hiện tại](#-luật-mua-hiện-tại)
2. [Lịch chạy](#-lịch-chạy)
3. [Điểm vào trong phiên](#-điểm-vào-trong-phiên)
4. [Bán mã đang giữ](#-bán-mã-đang-giữ)
5. [Bản tin chiến lược CL1 / CL2](#-bản-tin-chiến-lược-cl1--cl2)
6. [Mã từ bộ lọc](#-mã-từ-bộ-lọc-bo_loc)
7. [Theo dõi & chấm điểm tín hiệu](#-theo-dõi--chấm-điểm-tín-hiệu)
8. [Trang tổng hợp, biểu đồ, tin Telegram](#-trang-tổng-hợp-biểu-đồ-tin-telegram)
9. [Backtest](#-backtest)
10. [Workflow của danh-muc chạy ở đây](#-workflow-của-danh-muc-chạy-ở-đây)
11. [Cài đặt](#%EF%B8%8F-cài-đặt)
12. [Bảo mật](#-bảo-mật-repo-công-khai)
13. [Chạy tay & tuỳ chỉnh](#-chạy-tay--tuỳ-chỉnh)

---

## 🛒 Luật mua hiện tại

**Quỹ B**, áp dụng từ 10/2026, giống nhau ở dmuc, gia_lap, canh-bao-mua và Bo_Loc.

| | Luật |
|---|---|
| **Chọn mã** | Mã có tín hiệu MUA trong tin tổng kết (🟢 mua mới · ✅ vào trễ), thuộc top 100 GTGD và **không quá nóng** (hạng RS 3 tháng so VN-Index trong toàn rổ < 90). Mỗi tuần đánh dấu **★ 4 mã** ưu tiên cao nhất. |
| **Số lệnh** | Giữ tối đa **8 mã** · tối đa **4 mã MỚI/tuần** (thứ 2 – thứ 6, tính cả lệnh vào trễ) · mỗi mã mua thêm tối đa 2 lần. |
| **Vào trễ** | Mã đã bỏ vì **hết suất tuần** được mua sau khi giá **≤ giá vào của hệ thống + ½R** (cắt lỗ hệ thống cách ≤ 7%), đủ khối lượng – như đặt lệnh chờ quanh giá tín hiệu. Lãi > ½R → chờ giá hồi. |
| **Khối lượng** | **0,75% vốn** ÷ (giá mua − cắt lỗ). VN-Index đang *Tăng* → ½ mức rủi ro · mã **ĐẮT** → ½ khối lượng. |
| **Giới hạn quỹ** | ≤ 15% vốn/mã · tổng rủi ro mở ≤ 4%. |
| **Đặt lệnh** | Đặt **LO từ hôm trước** ở giá = cận dưới + ⅓ × (cận trên − cận dưới), làm tròn xuống theo bước giá. |
| **LO không khớp** | Mã **★** → mua **ATC** nếu giá còn trong vùng · mã không ★ → **bỏ**. |
| **Thoát lệnh** | Theo hệ thoát (xem [Bán mã đang giữ](#-bán-mã-đang-giữ)); cắt lỗ & mục tiêu tính lại mỗi phiên. |

> Vì sao LO + ATC chỉ cho mã ★? Backtest Quỹ B trên ~400 mã: LO + ATC ngang tốt nhất và dễ làm nhất; LO đơn thuần
> kém nhất; ATC cho mọi mã thì mua quá nhiều.

---

## 🕒 Lịch chạy

| Giờ VN | Workflow | Việc |
|---|---|---|
| 9:00 – 14:45, mỗi 15' | `canh_bao.yml` | Quét mã trong danh sách mua tối qua → 🟢 MUA NGAY · ⏰ MUA ATC · 🚫 BỎ. Quét mã đang giữ → cảnh báo bán. |
| **15:20** | `canh_bao.yml` | Tổng kết: thị trường & CL, danh sách mua phiên tới, 💼 vị thế đang giữ, Excel, trang tổng hợp. |
| 09:07 thứ Bảy | `canh_bao.yml` | Chấm lại mọi tín hiệu, xuất Excel lịch sử. |
| 01:43 Chủ nhật | `tai_nen_15p.yml` | Tải thêm nến 15' (nguồn miễn phí chỉ giữ ~1 năm → tích luỹ dần). |
| 02:17 mùng 2 | `backtest.yml` | Backtest điểm vào / điểm bán → tin 🧪 + Excel. |

Ngày nghỉ lễ tự bỏ qua: lịch lễ VN lấy từ thư viện `holidays`, đếm phiên thật theo VNINDEX.
Ngày HOSE nghỉ ngoài lịch thì thêm vào `NGAY_NGHI_GIAO_DICH`.

---

## 🎯 Điểm vào trong phiên

Chỉ quét mã trong nhóm mua của tin tổng kết gần nhất, đúng phiên hiệu lực. Cảnh báo và backtest dùng cùng một hàm.

| Khung | Tiêu chí |
|---|---|
| **Ngày (chiến lược)** | Hệ B (Quỹ B): MACD ngày cắt lên **kèm MACD tuần > Signal** (🟢 mua mới) / hệ thống đang giữ và giá ≤ giá vào + ½R (✅ vào trễ, đủ KL), cắt lỗ cách ≤ 7%; chỉ mã top 100 GTGD, hạng RS 3T < 90. |
| **Vùng giá** | Giá trong vùng mua · mở cửa ≤ cận trên (không đuổi) · chưa thủng cận dưới trước khi mua. |
| **15 phút** *(chỉ cách vào `15P…`)* | MACD 15' cắt lên Signal (≤ 3 nến) **hoặc** phá đỉnh 20 nến, KL ≥ 1,5× TB20 · giá ≥ VWAP · RSI 15' ≤ 75. |

<details>
<summary><b>Các cách vào lệnh có sẵn</b> (đổi bằng <code>CACH_VAO_15P</code>)</summary>

| Cách vào | Nghĩa |
|---|---|
| **`LO+ATC`** *(đang dùng)* | LO ở ⅓ dưới vùng; chưa khớp → ATC (chỉ mã ★) |
| `LO` | Chỉ LO |
| `ATO` | Mua giá mở cửa |
| `15P` / `15P+ATC` | Chờ tín hiệu 15'; `+ATC`: hết phiên chưa có điểm vào mà giá còn trong vùng → ATC (từ `GIO_ATC` 14:25) |
| `15P+GIO` | Như 15P, thêm MACD giờ > Signal |
| `VWAP` | Vào khi giá ≥ VWAP |
| `tu_dong` | Dùng cách tốt nhất của lần backtest gần nhất |

</details>

**Sau khi mua:** MUA MỚI tính lại cắt lỗ theo giá mua thật (2×ATR, ≤ 7%); nhóm vào trễ giữ cắt lỗ hệ thống.
MT 1R / 3R là mốc dời cắt lỗ, **không phải lệnh bán**.

**Mua thêm** (kiểu B, đã backtest): lãi ≥ 2R (khung tuần) · đóng cửa lập đỉnh mới · cách lần trước ≥ 10 phiên · cắt lỗ ≥ giá vốn
bình quân mới + phí · tối đa 2 lần, mỗi lần 25% số CP. Mua xong cập nhật `so_cp`, `gia_von`, `so_lan_mua_them`,
`ngay_mua_them` trong `danh_muc.csv`.

---

## 💼 Bán mã đang giữ

Bot đọc `danh_muc.csv` của repo riêng tư **danh-muc** (mã có `so_cp` > 0) và tính hệ thoát lại mỗi lần chạy từ
`ngay_mua`, trên các phiên đã đóng cửa. Cắt lỗ **chỉ dời lên**, không chốt lời ở mục tiêu cố định.

| Tầng | Lãi hiện tại | Cắt lỗ |
|---|---|---|
| 0 | < 1R | `cat_lo_goc` (thiếu → giá − 2×ATR, tối đa −7%, tối thiểu 1,5×ATR). 1R = giá vốn − cắt lỗ ban đầu |
| 1 | ≥ 1R | Đóng cửa cao nhất − 3×ATR, không dưới hoà vốn + phí |
| 2 (tuần) | ≥ 2R | Bán khi **đóng cửa tuần < MA10 tuần**; sàn khoá lãi 1R |
| – | 63 phiên chưa tới 1R | Lệnh không chạy → bán |

| Cảnh báo | Khi nào |
|---|---|
| 🔴 **CẮT LỖ** | Giá ≤ cắt lỗ hiệu lực (mức cao hơn giữa hệ thống và `cat_lo_dat`) |
| 🔴 **GÃY XU HƯỚNG TUẦN** | Ở tầng tuần, tuần đã đóng có đóng cửa < MA10 tuần → bán đầu phiên tới |
| 🟠 **LỆNH KHÔNG CHẠY** | Giữ ≥ 63 phiên mà chưa đạt 1R |
| 🟠 **SÁT CẮT LỖ** | Cách cắt lỗ ≤ `GAN_CAT_LO_PCT` (1%) |
| 🟡 **DỜI CẮT LỖ** | Cắt lỗ hệ thống cao hơn `cat_lo_dat` ≥ 0,5% → sửa danh mục |

- Mỗi mức báo **1 lần khi xuất hiện**, còn thì nhắc 1 lần/ngày. Tin ghi tầng, lãi theo R, mốc kế tiếp, nhắc CP chưa về (T+2).
- **Vị thế cũ** (mua ngoài vùng khuyến nghị): quản lý từ giá đóng cửa ngày mua thay cho giá vốn.
- Cắt lỗ / mục tiêu do repo danh-muc cập nhật **15:45** mỗi ngày → không phải nhập 2 nơi.
- **Danh mục cũ** `danh_muc_cu.csv`: quét thêm mỗi lượt 15', chạm / sát cắt lỗ đề xuất thì báo. Tắt: `QUET_DANH_MUC_CU = False`.
- Thiếu dữ liệu hoặc `DUNG_HE_THOAT = False` → quay về cách cũ (chốt lời ở mục tiêu đặt tay, MACD tuần / SuperTrend).

---

## 📊 Bản tin chiến lược CL1 / CL2

Gửi sau tổng kết 15:20 (`canh_bao/chien_luoc_bot.py`). Đây là **mô phỏng công khai**, không dùng danh mục thật.

**Điểm thị trường (8 chỉ báo VN-Index):** VNI > MA200 · MA50 > MA200 · MA200 dốc lên · động lượng 6T & 3T > 0 ·
cách đỉnh 1 năm < 10% · > 50% mã trên MA200 · biến động 20 phiên < trung vị 1 năm.

**Chọn CL** (chỉ đổi ở phiên cuối tháng, có vùng đệm): điểm ≥ 5 → **CL2** (A0 70% + ETF 30%) · ≤ 2 → **CL1**
(A0 50% + B 50%) · 3–4 giữ nguyên. Đổi CL → tin 🔔 riêng.

**Hành động phiên tới** (cho người chưa mua):

| Nhóm | Khi nào | Làm gì |
|---|---|---|
| 🟢 MUA MỚI | Tín hiệu MACD hôm nay | Đặt LO; không mua nếu mở cửa > cận trên |
| ✅ VÀO NHƯ LỆNH MỚI (vào trễ) | Hệ thống đang giữ, giá ≤ giá vào hệ thống + ½R, cắt lỗ cách ≤ 7% | Mua đủ, dùng cắt lỗ hệ thống (quỹ B: chỉ mã đã bỏ vì hết suất tuần) |
| ⏳ CHỜ ĐIỀU CHỈNH | Lãi > ½R hoặc cắt lỗ cách > 7% | Chờ giá về ≤ giá vào hệ thống + ½R hoặc tín hiệu mới |
| 🔻 BÁN PHIÊN TỚI | Đóng cửa tuần < MA10 tuần | Không mua; đang giữ thì bán |

**Danh sách mã:** VN30 (tự lấy online, lỗi thì dùng `MA_VN30`) + `MA_THEM` (DHC, GMD, MWG) + mã từ Bo_Loc.
Độ rộng thị trường tính trên **rổ top 100 GTGD chốt ở phiên thứ Sáu tuần liền trước** (giữ cố định cả tuần, lấy từ
`ptcp/loc_quy_b.json`) để điểm thị trường không đổi theo danh sách; chưa có rổ tuần thì dùng 41 mã `MA_CHIEN_LUOC`.

---

## 🔎 Mã từ bộ lọc (bo_loc/)

Bộ lọc (thư mục `bo_loc/`, chuyển từ repo Bo_Loc 10/2026 – hướng dẫn đầy đủ: [docs/bo_loc.md](docs/bo_loc.md)) chạy ở
workflow **Quet dinh ky** cuối mỗi phiên (15:05), ghi mã đạt MUA vào `ma_mua_bo_loc.json` của repo này. Mã PTĐTTC
không quét ở đây (repo riêng tư Bo_Loc lo phần đó). Tổng kết 15:20 (`canh_bao/ma_bo_loc.py`):

1. **Thêm** mã mới vào danh sách quét, hạn **4 phiên** (mã đã trong `MA_THEO_DOI` thì bỏ qua).
2. Mã vào nhóm mua 🟢 / ✅ / 🟡 → **đạt** → hạn tính lại 4 phiên từ ngày đạt.
3. Hết hạn → **tự xoá** (kể cả mã đang giữ; mã đó vẫn có cảnh báo bán riêng tư). Bo_Loc lọc ra lại → thêm lại.

Trạng thái ở `ma_bo_loc.json` (chỉ mã & ngày). Cấu hình: `DUNG_BO_LOC`, `BO_LOC_SO_PHIEN`, `BO_LOC_REPO`
(mặc định chính repo này – đọc qua GitHub API để luôn lấy bản mới nhất).

---

## ✅ Theo dõi & chấm điểm tín hiệu

**📌 Theo dõi khuyến nghị đã gửi** (`canh_bao/theo_doi_kn.py`): mỗi khuyến nghị MUA là 1 lệnh giả định (mua mở cửa
phiên sau nếu trong vùng), chấm mỗi ngày bằng đúng hệ thoát → 🔴 BÁN · ⬆ DỜI cắt lỗ · ⚠ sát cắt lỗ · 🟢 GIỮ · ✅/❌ đã đóng.

**Nhật ký ĐÚNG / SAI** (`canh_bao/nhat_ky.py`, chấm bằng `ptcp/nhat_ky.py`):

| Loại | Ghi khi | ĐÚNG khi |
|---|---|---|
| MUA NGAY | Gửi tin MUA NGAY | Chạm mục tiêu trước cắt lỗ, hoặc hết hạn mà lãi sau phí > 0 |
| ptcp – nhóm MUA | Khuyến nghị đổi sang MUA | Như trên, mua giá mở cửa phiên sau |
| ptcp – CHỜ / ĐỨNG NGOÀI | Khuyến nghị đổi sang chờ / không mua | Lệnh giả định đó **lỗ** (tránh được lỗ) |
| BÁN | Gửi cảnh báo bán | Sau 20 phiên giá ≤ giá lúc báo |

Chấm theo luật VN: T+2, trần/sàn, gap, cắt lỗ & mục tiêu cùng phiên → tính cắt lỗ, phí + trượt 0,6%.
Kết quả `ĐÚNG` · `SAI` · `ĐANG CHỜ` · `BỎ QUA`. Xem chi tiết: `python chay.py --che_do lich_su` → `danh_gia_tin_hieu.xlsx`.

---

## 🖼 Trang tổng hợp, biểu đồ, tin Telegram

- **Trang tổng hợp** (`docs/index.html`, GitHub Pages): sức khoẻ thị trường · tín hiệu hôm nay · mã Bo_Loc · độ chính
  xác bot. Tự sáng/tối, xem tốt trên điện thoại, không có danh mục thật. Bản **riêng** (có 💼 danh mục) chỉ gửi
  Telegram dạng file HTML. Bật Pages: Settings → Pages → Branch `main`, thư mục `/docs`.
- **Biểu đồ mốc giá** (`canh_bao/bieu_do_moc.py`): 120 phiên với vùng mua, cắt lỗ, 1R / 2R / 3R. Kèm tin MUA NGAY,
  nhóm mua của tổng kết (tối đa `ANH_MUA_TOI_DA`) và cảnh báo bán.
- **Tin Telegram:** số kiểu Việt Nam (78.700 · 5,6%), tiêu đề in đậm, ghi chú nghiêng. Tắt ảnh: `GUI_ANH = False`.
- **Giao dịch giả lập:** repo riêng **gia_lap** (16:30) đọc `ds_mua` trong `trang_thai_chien_luoc.json`.
  → Đừng đổi cấu trúc khoá `ds_mua` mà không sửa gia_lap.

---

## 🧪 Backtest

Actions → **Backtest** → Run workflow (hoặc tự chạy mùng 2). Thử mọi cách vào lệnh trên nến 15' thật, mô phỏng
**Quỹ B theo từng cách vào**, backtest điểm bán / mua thêm → tin 🧪 + Excel + `ket_qua_backtest.json`.
Kết quả tải về được cache lại (`cache_gia`, `cache_du_lieu`) nên lần sau chạy nhanh hơn.

Kết luận đã chốt:
- **Điểm bán:** chốt ⅓/½ ở 3R, siết cắt lỗ khi thị trường giảm, hạn 30–40 phiên đều **kém** hệ thoát gốc → giữ nguyên.
- **Mua thêm kiểu B:** lãi TB/lệnh 2,50% → 2,88%.
- **Cách vào:** LO + ATC (chỉ mã ★) – xem [Luật mua](#-luật-mua-hiện-tại).

---

## 🏗 Workflow của danh-muc chạy ở đây

Repo riêng tư có giới hạn phút GitHub Actions; repo công khai này thì không. Từ 10/2026 các workflow sau của danh-muc
chạy ở đây – mỗi workflow checkout repo danh-muc vào thư mục `danh-muc/` rồi chạy như cũ:

| Workflow | Lịch | Ghi về danh-muc |
|---|---|---|
| **Backtest quy B** (`backtest_quy_b.yml`, input `nhanh_danh_muc` để thử nhánh chưa gộp) | chạy tay | – |
| **Loc quy B** – hạng GTGD, RS 3T, định giá → `ptcp/loc_quy_b.json` | 07:30 T2–T6 | ✔ |
| **Kho BCTC** · **Boi so nganh** | Chủ nhật | ✔ |
| **Kiem dinh dinh gia** · **Sieu co phieu** · **Chan doan** · **Tra cuu ma** · **Bao cao ma** | chạy tay (Tra cuu: thứ Bảy) | – |

- **Log và artifact ở đây ai cũng xem được.** Các workflow đặt `CONG_KHAI=1` → ptcp **không đọc** `danh_muc.csv` /
  `danh_muc_ptdttc.csv` (Kho BCTC chỉ báo mã top GTGD, Bao cao ma không kèm vị thế đang giữ).
- **Ở lại repo riêng tư:** *Danh muc hang ngay* (danh-muc – vị thế thật) và quét mã PTĐTTC (Bo_Loc).
- Test chạy trên máy (`python -m pytest`), không chạy trên GitHub nữa.

---

## ⚙️ Cài đặt

1. Upload toàn bộ thư mục này lên GitHub (kể cả `.github/workflows/`).
2. **Settings → Actions → General → Workflow permissions:** *Read and write*.
3. **Settings → Secrets and variables → Actions:**

   | Loại | Tên | Giá trị |
   |---|---|---|
   | Secret | `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` | Bot Telegram |
   | Secret | `DANH_MUC_TOKEN` | Token **chỉ đọc** repo danh-muc (cũng dùng để lấy `ptcp/`) |
   | Secret | `DANH_MUC_TOKEN_GHI` | Token repo danh-muc quyền **Contents: Read and write** – Loc quy B / Kho BCTC / Boi so nganh commit kết quả về danh-muc |
   | Secret (tuỳ chọn) | `VNSTOCK_API_KEY` | Khoá vnstock cho các workflow của danh-muc |
   | Variable | `DANH_MUC_REPO` | `ten-ban/danh-muc` (tuỳ chọn `DANH_MUC_PATH`, `DANH_MUC_CU_PATH`) |
   | Variable | `PTCP_REPO`, `PTCP_PATH` | Chỉ khi `ptcp/` không nằm ở repo danh-muc |

   Tạo token: GitHub → Settings → Developer settings → **Fine-grained tokens** → *Only select repositories* →
   *Contents: Read-only*.
4. Chạy thử: Actions → **Canh bao mua** → Run workflow → `tong_ket`. Log phải có
   `Vị thế đang giữ: N mã (nguồn: repo danh-muc)`; báo `HTTP 404` → sai tên repo hoặc token chưa được cấp repo đó.

**Nguồn giá:** VNDirect → DNSE → SSI iBoard → VCI → Yahoo, tự chuyển nguồn, lỗi thì dùng cache.

---

## 🔒 Bảo mật (repo công khai)

- Tin có số CP / giá vốn / cắt lỗ **chỉ gửi Telegram, không in ra log Actions** (log chỉ ghi "tin riêng tư … ký tự").
- `danh_muc.csv` nằm trong `.gitignore`. Mã chỉ có trong danh mục không hiện tên trong log, không ghi vào file commit.
- Trạng thái riêng (chống báo trùng, nhật ký bán) lưu trong cache Actions `cache_ptcp/`, không commit. Cache bị xoá
  nếu repo không chạy > 7 ngày.
- Token chỉ cấp quyền **đọc**, trừ `DANH_MUC_TOKEN_GHI` (chỉ dùng trong 3 workflow ghi dữ liệu về danh-muc).
- Workflow của danh-muc chạy với `CONG_KHAI=1`: không đọc danh mục thật / mã PTĐTTC; mã PTĐTTC không quét ở repo này.

---

## 🛠 Chạy tay & tuỳ chỉnh

**Xem riêng 1 mã:** Actions → Canh bao mua → Run workflow → ô **ma** = `FPT` (hoặc `FPT,HPG`). Kết quả gửi Telegram,
kèm trạng thái tối đa 4 mã cùng ngành; không đổi trạng thái của bot.

**Chạy thử không làm phiền:** tích **chi_thu** → không gửi Telegram, không commit, khôi phục trạng thái riêng.

```bash
pip install -r requirements.txt
python chay.py --che_do tong_ket --khong_gui      # tổng kết, không gửi tin
python chay.py --che_do chien_luoc --khong_gui    # chỉ bản tin chiến lược
python chay.py --chi_ma FPT --khong_gui           # xem 1 mã
python chay.py --che_do lich_su                   # chấm lại tín hiệu, xuất Excel
python chay.py --khong_ban                        # bỏ cảnh báo bán
python -m pytest -q
```

Cấu hình chính trong `canh_bao/cau_hinh.py`:

| Nhóm | Biến |
|---|---|
| Danh sách mã | `MA_VN30`, `TU_LAY_VN30`, `MA_THEM`, `MA_CHIEN_LUOC` |
| Điểm vào | `CACH_VAO_15P`, `GIO_ATC`, `SO_MA_MOI_TUAN` |
| Khối lượng | `RUI_RO_MOI_LENH_PCT`, `VON_TRIEU`, `KL_THEO_BIEN_DONG` |
| Mua thêm | `MUA_THEM_TY_LE`, `MUA_THEM_GIAN_CACH`, `MUA_THEM_TOI_DA` |
| Bán | `DUNG_HE_THOAT`, `GAN_CAT_LO_PCT`, `QUET_DANH_MUC_CU` |
| Bật / tắt | `DUNG_CHIEN_LUOC`, `DUNG_BO_LOC`, `GHI_NHAT_KY`, `GUI_ANH`, `GUI_EXCEL`, `GUI_TRANG_RIENG`, `DUNG_TRANG_TONG_HOP` |
