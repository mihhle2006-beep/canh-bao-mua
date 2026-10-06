# ptcp – Phân tích kỹ thuật cổ phiếu Việt Nam (1 mã) + Danh mục

Hai lối vào, **một lõi phân tích chung** (`ptcp/`):

| Lối vào | Việc |
|---|---|
| `chay.py` | Phân tích sâu 1 mã |
| `danh_muc.py` | Phân tích danh mục: mỗi mã chạy qua `ptcp.main`, rồi tổng hợp tỷ trọng (gồm tiền mặt), cắt lỗ đã đặt, số lượng mua, stress test, Markowitz – xem đầu file `danh_muc.py` |

Tham số kỹ thuật sửa ở `ptcp/cau_hinh.py` (dùng cho cả hai); tham số danh mục ở `dmuc/cau_hinh.py`.

## Nguồn dữ liệu

**vnstock (bản Cộng đồng)** là nguồn dự phòng cho giá (sau VNDirect/TCBS/SSI/CafeF/DNSE/VCI), số CP lưu hành,
P/E–P/B–ROE, LNST 4 quý và BCTC năm. Trên Colab tự cài; GitHub Actions cài qua `requirements.txt`
(có `--extra-index-url https://vnstocks.com/api/simple`). Khoá API: Colab Secrets / GitHub Secret `VNSTOCK_API_KEY`
(không bắt buộc). Hết hạn mức lượt gọi → tự chuyển nguồn khác (không dừng); muốn chờ cho đủ hạn mức:
`cfg.CHO_VNSTOCK = True`. Tắt hẳn: `cfg.DUNG_VNSTOCK = False`.

Khi chạy kiểu hỏi từng câu, công cụ **không còn hỏi** số CP phát hành/niêm yết/quỹ, sở hữu NN, beta, P/E, P/B, ROE, dư nợ margin – tất cả lấy tự động (số CP: TCBS → VNDirect → Yahoo, đối chiếu chéo & cảnh báo khi lệch > 0,5%; beta tự tính so VNINDEX; vốn hoá = số CP lưu hành × giá, kiểm tra chéo với vốn hoá Yahoo). Không dùng Vietstock. Muốn ghi đè số nào thì truyền vào `main(...)`, VD `main(tuong_tac=False, symbol="GMD", kl_ph=414_064_000, roe=14.2)`.

- **Giá ngày/giờ & VNINDEX:** VNDirect → VND finfo → TCBS → SSI → CafeF → DNSE → VCI (tự chuyển nguồn khi lỗi), cache, CSV.
- **Chỉ số cơ bản (Phần H):** VNDirect `api-finfo` → vnstock → TCBS → Yahoo (yfinance, nếu đã cài). Chỉ tiêu nào nguồn trước thiếu thì nguồn sau bù.
- **P/E = Thị giá ÷ EPS**, **EPS = LNST (cổ đông công ty mẹ) 4 quý gần nhất ÷ số CP lưu hành** (số CP lưu hành lấy từ mục cơ cấu cổ phiếu của báo cáo). LNST 4 quý: tham số `lnst_4q` (tỷ đồng, từ BCTC) → TCBS → Yahoo, phải đủ 4 quý liên tiếp. Không tự tính được mới dùng EPS nguồn công bố. Phần H in rõ 4 quý đã cộng, LNST, số CP và EPS. Doanh nghiệp lỗ → P/E âm.
- VNDirect finfo: host đúng là `api-finfo.vndirect.com.vn` (host cũ `finfo-api` giữ làm dự phòng).

## Phần J – phân tích chuyên sâu 1 mã (chỉ ở báo cáo 1 mã)

| Mục | Nội dung (đầy đủ, không rút gọn) |
|---|---|
| J1 Tổng quan | Giá, ngành, KL TB 3 tháng, GTGD, Beta, RSI, EPS 4 quý, P/E, P/B, ROE, vốn hoá, sở hữu NN (kèm nguồn) |
| J2 Tài chính | BCTC 4–5 năm: doanh thu, LN gộp & biên gộp, LNST & tăng trưởng, CFO & CFO/LNST, thanh toán, EBIT/lãi vay, Nợ/VCSH, ROE, vốn góp, vay nợ |
| J3 Kỹ thuật | MA20/50/100/200 (giá trị, hướng, giá trên/dưới), RSI, RS6M/RS52W so VN-Index & xếp hạng trong nhóm ngành, mô hình nến 5 phiên, Tích lũy & Vượt đối chiếu đủ 12 nút ngưỡng |
| J4 Biến động | % 1 ngày → 1 năm & từ đầu năm: mã / VN-Index / từng mã cùng ngành |
| J5 10 tiêu chí tài chính | 5 mức + giải thích từng tiêu chí, so sánh tối đa 2 mã cùng ngành (`cfg.SO_MA_SO_SANH_FA`) |

Excel: thêm 5 sheet `J1 … J5` (J5 tô màu theo 5 mức). Không đổi khuyến nghị (Phần C vẫn là nguồn duy nhất);
≥ 2 tiêu chí Nguy hiểm → thêm cảnh báo ở tóm tắt. Danh mục (`dmuc`) và quét nhiều mã không chạy Phần J.

## Cấu trúc

| File | Nội dung |
|---|---|
| `chay.py` | Chạy kiểu hỏi từng câu (`%run chay.py`) |
| `ptcp/cau_hinh.py` | **Mọi tham số** (ngưỡng EV, R/R, T+2, phí, trọng số…) và dữ liệu CTCK nạp sẵn |
| `ptcp/in_an.py` | In ra màn hình, bảng gọn `ve_bang`, định dạng số |
| `ptcp/du_lieu.py` | Lấy dữ liệu GIÁ: API VNDirect/TCBS/SSI/CafeF/DNSE/VCI/vnstock, CSV, cache |
| `ptcp/du_lieu_co_ban.py` | Thông tin DN, chỉ số cơ bản (VNDirect → vnstock → TCBS → Yahoo), LNST 8 quý, BCTC năm |
| `ptcp/chi_bao.py` | MACD, RSI, ATR, OBV, đỉnh/đáy, đường xu hướng, chấm điểm tín hiệu |
| `ptcp/thong_ke.py` | Mô phỏng theo luật giao dịch VN, EV, bootstrap, walk-forward, gộp ngành |
| `ptcp/loi.py` | **Lõi tính khuyến nghị** (giai đoạn 2 của `main`) – dùng chung cho `main()` và backtest |
| `ptcp/muc_tieu.py` | Cắt lỗ thống nhất, mục tiêu theo khung, vùng hội tụ, đề xuất mục tiêu |
| `ptcp/kich_ban.py` | Phần D: kịch bản, xác suất, EV có điều kiện theo trạng thái tín hiệu |
| `ptcp/quyet_dinh.py` | Trạng thái 3 khung, quản trị rủi ro, lọc cơ bản, **hàm quyết định duy nhất** |
| `ptcp/thong_tin.py` | Phần A, kiểm tra dữ liệu, beta, cơ cấu CP, thông tin giao dịch, báo cáo CTCK |
| `ptcp/phan_tich.py` | Chỉ để tương thích – import lại từ 4 module trên |
| `ptcp/nhat_ky.py` | **Nhật ký khuyến nghị & bộ chấm ĐÚNG/SAI** (dùng chung với bot canh-bao-mua) |
| `ptcp/backtest_kn.py` | **Backtest point-in-time toàn bộ khuyến nghị** + độ nhạy ngưỡng / kỳ hạn |
| `ptcp/ke_hoach.py` | Kế hoạch vị thế từ giá mua: cắt lỗ gốc, cắt lỗ động, kế hoạch bán |
| `ptcp/bo_sung.py` | Khối lượng, bối cảnh thị trường, sự kiện, backtest (bộ mô phỏng thoát lệnh dùng chung) |
| `ptcp/backtest_pp.py` | **Backtest phương pháp trên nhiều mã** – độ mạnh các cách vào/thoát Phần I |
| `ptcp/vung_mua.py` | **Vùng mua điều chỉnh** cho mã chưa nắm giữ + backtest point-in-time của quy tắc chờ vùng |
| `ptcp/chuyen_sau.py` | Phần J – phân tích chuyên sâu 1 mã (J1–J5) |
| `ptcp/bieu_do.py` | Biểu đồ |
| `ptcp/bao_cao.py` | In báo cáo, tóm tắt 5 dòng, xuất HTML/CSV |
| `ptcp/chuong_trinh.py` | `main()`, `quet_nhieu_ma()` |
| `dmuc/` | Phần cấp danh mục (cầu nối ptcp, danh mục, Markowitz, xuất) |
| `tests/` | ~100 test tự động cho cả gói (không cần mạng) – `!python -m pytest -q` |

## Ptcp có đúng không? – Nhật ký (Phần K) & backtest khuyến nghị

**Nhật ký (tự động mỗi lần chạy `main`)**: ghi khuyến nghị khi nó THAY ĐỔI và chấm lại các khuyến nghị cũ bằng giá
thực tế (luật T+2, trần/sàn, gap, phí 0,6%). Báo cáo có **Phần K** (console, sheet Excel `K Lich su khuyen nghi`, HTML).

| Nhóm khuyến nghị | ĐÚNG khi |
|---|---|
| MUA / MUA TỪNG PHẦN | lệnh mua giả định (giá mở cửa phiên sau, cắt lỗ & mục tiêu ngắn hạn của khuyến nghị) chạm mục tiêu trước, hoặc hết hạn mà lãi |
| THEO DÕI, CHỜ… / CHƯA MUA, KHÔNG MUA MỚI | lệnh mua giả định đó **lẽ ra bị lỗ** (đứng ngoài là đúng); lẽ ra lãi → SAI (bỏ lỡ) |

```python
from google.colab import drive; drive.mount('/content/drive')   # ← để nhật ký KHÔNG mất khi tắt Colab
from ptcp import main, nhat_ky
kq = main(tuong_tac=False, symbol="GMD")          # Phần K in lịch sử đúng/sai của GMD
nhat_ky.xem()        # tải giá mới nhất, chấm lại, GHI file Drive, hiện bảng: mỗi mã tăng/giảm bao nhiêu từ lúc
                     # khuyến nghị tới nay + độ chính xác + chi tiết; xuất danh_gia_khuyen_nghi.xlsx cạnh nhật ký
nhat_ky.xem(chi_tiet=False)                        # chỉ bảng theo mã + độ chính xác
nhat_ky.thong_ke(nhat_ky.doc())                    # (cũ) chỉ bảng độ chính xác
```
File: Drive `MyDrive/ptcp/nhat_ky_ptcp.csv` (chưa mount → `./nhat_ky_ptcp.csv`, mất khi tắt Colab). Repo danh-muc:
`nhat_ky_ptcp.csv` ở gốc repo, workflow tự commit. Tắt: `cfg.GHI_NHAT_KY = False`.

**Backtest toàn bộ khuyến nghị (không phải chờ nhật ký tích luỹ)** – chạy lại lõi quyết định tại từng ngày quá khứ,
chỉ với dữ liệu có đến ngày đó:
```python
from ptcp import backtest_khuyen_nghi, backtest_nhieu_ma
kq = backtest_khuyen_nghi("GMD", buoc=5)                    # ~2–4 phút; xuất backtest_khuyen_nghi_GMD_*.xlsx
kq = backtest_nhieu_ma(["GMD", "MWG", "DHC", "VPB"])        # gộp để đủ mẫu
```
Kết quả: độ chính xác theo nhóm; **"khi ptcp nói MUA" so với "mua bất kỳ ngày nào"** (có lợi thế thật không);
chiến lược lệnh không chồng; **bảng độ nhạy 24 cặp ngưỡng EV × R/R** tách nửa đầu / nửa sau (chọn vùng ổn định ở
cả 2 nửa, không chọn ô đẹp nhất – tránh overfit); độ nhạy kỳ hạn chấm 21/42/63/126 phiên.
Giới hạn: không có dữ liệu giờ & cơ bản theo thời điểm (bỏ 2 bước đó), không gộp ngành.

## Thử độ mạnh phương pháp trên nhiều mã (Phần I gộp)

Chạy mọi tổ hợp VÀO (MACD lọc tuần / MACD không lọc / mua ngay / chờ vùng mua) × THOÁT (cố định / cắt lỗ động /
chốt từng phần) trên nhiều mã, gộp lệnh và chấm 4 phép thử: TB/lệnh > 0 & PF > 1,2 · KTC 90% (bootstrap theo mã)
trên 0 · ≥ 60% số mã có lãi · nửa đầu và nửa sau giai đoạn đều có lãi → MẠNH (4/4) / KHÁ (3/4) / YẾU / KHÔNG CÓ LỢI
THẾ. Nhanh (vài giây/mã), xuất Excel `backtest_phuong_phap_YYYYMMDD.xlsx`.

```python
from ptcp import backtest_phuong_phap
kq = backtest_phuong_phap(["GMD", "HAH", "VSC", "PHP", "MWG", "DHC", "VPB", "FPT", "HPG", "VNM"], start="2019-01-01")
kq["bang"]       # bảng xếp hạng tổ hợp   | kq["theo_ma"]: TB/lệnh từng mã | kq["lenh"]: chi tiết lệnh
```
Nên dùng ≥ 10 mã thuộc nhiều ngành. Khác `backtest_nhieu_ma()` (chạy lại toàn bộ lõi khuyến nghị, chậm).

## Thay đổi logic (bản beta 1.1)

- **EV theo trạng thái tín hiệu**: EV quyết định dựa trên các phiên quá khứ CÙNG trạng thái tín hiệu vào lệnh
  (tuần MACD > Signal & MACD ngày vừa cắt lên / phá đỉnh 5 phiên), co về EV cơ sở theo số mẫu hiệu dụng. Phần D in
  thêm **"lợi thế của tín hiệu"** = EV có điều kiện − EV trộn. Cách cũ (min): `cfg.CACH_TINH_EV = "than_trong"`.
- **Lọc cơ bản** (`LOC_CO_BAN = True`): LNST 4 quý âm hoặc giảm > 30% so cùng kỳ → THEO DÕI; ROE < 5% (hoặc P/E >
  `CO_BAN_PE_MAX` nếu đặt) → MUA TỪNG PHẦN. Thiếu số liệu thì không chặn. Hiện ở mục kiểm tra điều kiện Phần C.
- **Thoát lệnh**: `TRAILING_ATR`, `HOA_VON_KHI_R`, `CHOT_TUNG_PHAN_PCT` (ptcp/cau_hinh.py) dùng chung cho kế hoạch vị
  thế và danh mục. Phần I so sánh chốt cứng R/R 2 / cắt lỗ động / chốt từng phần + cắt lỗ động trên lịch sử mã.
- **Vùng mua điều chỉnh** (mã chưa nắm giữ, `ptcp/vung_mua.py`): vùng = nơi ≥ 2 loại hỗ trợ trùng nhau trong 1×ATR
  (EMA20/EMA50 ngày, MA20 tuần, Fibo 38.2–61.8% nhịp tăng gần nhất, đáy ngày xác nhận, POC khối lượng). Chỉ mua khi
  giá chạm vùng rồi có nến xác nhận (đóng cửa > đỉnh phiên trước); vô hiệu khi đóng cửa thủng vùng; cắt lỗ dưới vùng
  1×ATR. Phần C in vùng + trạng thái; tóm tắt dòng 2 dùng vùng này khi chưa mua. Tham số `VM_*` đặt được trong
  `cau_hinh.py`.
- **Gia hạn lệnh** (`GIA_HAN_LENH = True`, áp cho cắt lỗ động & chốt từng phần): tới hạn `n_phien` (63) mà lãi
  < `GIA_HAN_KHI_R` (1R) → bán (lệnh không chạy); lãi đủ → KHÔNG bán, giữ tiếp với cắt lỗ động siết về `SIET_ATR`
  (2×ATR), tối đa `HAN_TOI_DA` (252) phiên. Phần I & `backtest_phuong_phap` so sánh với hết hạn cứng (cách cũ);
  kế hoạch vị thế có dòng *Hạn lệnh*. Tắt: `cfg.GIA_HAN_LENH = False`.
- **In gọn** (`main(gon=True)`): Tóm tắt · Phần C (kèm vùng mua) · D2 · E1 giá mục tiêu · G bối cảnh · H cơ bản ·
  Kết luận backtest · Kết luận Phần J. Đổi danh sách bằng `cfg.MUC_GON` (ví dụ thêm `"E2"`, `"F"`, `"K"`).
- **Phần I** thêm *so sánh cách VÀO lệnh* (tín hiệu MACD / mua ngay / chờ vùng mua) × 3 cách thoát, phễu vùng mua
  (thiết lập → về vùng → khớp, % đạt +1R trước cắt lỗ) và mục **KẾT LUẬN BACKTEST**: quy tắc có lợi thế không, bộ lọc
  tuần, cách thoát, cách vào, so với mua & giữ, và một câu hành động (ÁP DỤNG / KHÔNG giao dịch ngắn hạn / ĐỨNG NGOÀI).
  Kết luận cũng ghi vào Excel (sheet `I Ket luan`) và HTML.

## Dùng trên Google Colab

```python
# 1) Tải ptcp_phan_tich.zip lên thanh Files rồi:
!unzip -oq ptcp_phan_tich.zip
%cd /content/ptcp_phan_tich

# 2a) Hỏi từng câu
%run chay.py

# 2b) Không hỏi
from ptcp import main, quet_nhieu_ma, cfg
kq = main(tuong_tac=False, symbol="ABC", san="HOSE", von_trieu=500, rui_ro_pct=1.5)

# 2c) Quét nhiều mã
bang = quet_nhieu_ma(["AAA", "BBB", "CCC"], von_trieu=500)

# Đổi tham số lúc chạy (ví dụ nâng ngưỡng EV)
cfg.EV_NGUONG = 1.5        # với tham số khác ngoài 6 tham số "động", sửa trong cau_hinh.py rồi chạy lại kernel
```

Bốn tham số đổi được ngay lúc chạy qua `cfg.X = ...`: `NGUONG_TRAN_SAN`, `SO_LAN_THU`,
`TU_DONG_TAI_VE`, `DO_RONG_DONG`. Các tham số còn lại được đọc khi nạp module → sửa trong
`ptcp/cau_hinh.py`, sau đó *Runtime → Restart session* rồi chạy lại.

## Chạy test (nên chạy sau MỖI lần sửa code)

```python
!python -m pytest -q tests
```

Các test kiểm tra những lỗi trong đề xuất ban đầu không quay lại: một khuyến nghị duy nhất xuyên suốt báo cáo,
tuần phủ quyết, EV/R-R là ngưỡng cứng, một mức cắt lỗ, đỉnh/đáy tạm thời không được dùng, mục tiêu tích cực >
breakout, luật T+2 / khoá trần sàn / gap, bảng không tràn màn hình và không có `-0.00`.


## Chạy tự động mỗi ngày bằng GitHub Actions

1. Tạo repo **Private** trên GitHub, đưa toàn bộ thư mục này lên (gồm `.github/workflows/danh_muc.yml`, `danh_muc.csv`).
2. Telegram: nhắn @BotFather → `/newbot` → lấy TOKEN; nhắn 1 tin cho bot rồi mở
   `https://api.telegram.org/bot<TOKEN>/getUpdates` để lấy `chat.id`.
3. Repo → Settings → Secrets and variables → Actions:
   - Secrets: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
   - Variables (tuỳ chọn): `TIEN_MAT` (triệu đồng), `GIU_TIEN_MAT` (%), `CHON` (gmv/max_sharpe), `NHAT_KY` (nhat_ky.csv)
4. Tab Actions → "Danh muc hang ngay" → Run workflow để chạy thử. Sau đó tự chạy 15:45 giờ VN, thứ Hai → thứ Sáu.
   Kết quả đầy đủ tải ở mục Artifacts của mỗi lần chạy; trạng thái cắt lỗ & lịch sử được commit lại vào repo.
