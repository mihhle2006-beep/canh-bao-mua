# Bộ lọc cổ phiếu (bo_loc/) – bản beta 1.1

> Từ 10/2026 bộ lọc nằm trong repo canh-bao-mua (công khai). Repo riêng tư **Bo_Loc** chỉ còn quét & báo riêng
> các mã PTĐTTC.

Quét một nhóm mã, tính chỉ tiêu kỹ thuật và cơ bản, lọc theo chiến lược, xếp hạng, đánh giá sau lọc rồi xuất Excel và biểu đồ.
Đơn vị giá: **nghìn đồng**. Đây là công cụ tham khảo, không phải khuyến nghị đầu tư.


## Quét định kỳ cho bot canh-bao-mua (mỗi phiên)

Workflow `.github/workflows/quet_dinh_ky.yml` chạy lúc **15:05 mỗi phiên T2–T6** (giờ VN):
`python -m bo_loc.quet_dinh_ky --nhom hose` quét **toàn sàn HOSE**, chạy lần lượt chiến lược **quy_b** và **xu_huong**, lấy các mã có *Hành động* = **MUA**
rồi ghi vào `ma_mua_bo_loc.json` (commit vào repo canh-bao-mua). Bot đọc file đó ở lần tổng kết 15:20,
theo dõi mỗi mã **4 phiên kế tiếp**: Bo_Loc lọc lại vẫn đạt hoặc vào nhóm mua 🟢/✅/🟡 thì tính lại 4 phiên, hết hạn thì tự xoá.

- Chạy tay: Actions → *Quet dinh ky* → *Run workflow* (chọn chiến lược / tham số thêm, VD `--nhom vn30`).
- Phạm vi mặc định: toàn sàn HOSE. Đổi bằng biến repo `BO_LOC_THAM_SO` (VD `--nhom vn30`).
- Trên máy: `python -m bo_loc.quet_dinh_ky --chien_luoc quy_b,xu_huong --nhom vn30`.
- Settings → Actions → General → Workflow permissions: **Read and write** (để commit file kết quả).
- Mỗi chiến lược lấy mã **MUA** + **2 mã đầu** (điểm cao nhất) nhóm **MUA THĂM DÒ (½)** – ghi là `<chiến lược> ½`.
- Quét xong sau 15:20 (lịch GitHub trễ) → tự kích hoạt lại tổng kết (Canh bao mua) bằng token sẵn có của workflow.

## Mới ở beta 1.1 – đồng bộ chiến lược thị trường (cùng bot canh-bao-mua & ptcp)

- **Chiến lược mặc định `quy_b`** – chiến lược đang áp dụng (Quỹ B, giống danh-muc / canh-bao-mua): hệ B (MACD ngày + tuần),
  nhóm MUA (mới / vào trễ ≤ giá vào hệ thống + ½R), chỉ mã top 100 GTGD và hạng RS 3 tháng < 90 (không quá nóng),
  GTGD ≥ 3 tỷ, mã ĐẮT ½ KL, tối đa 4 mã mới/tuần, thoát 2R – MA10 tuần.
- Nhóm MUA gồm: tín hiệu hệ B hôm nay (MACD ngày cắt lên + MACD tuần > Signal), hoặc hệ thống đang giữ và giá ≤ giá
  vào + ½R (vào trễ, đủ KL) với cắt lỗ cách ≤ 7%.
- **Dòng thị trường** ở đầu KẾT LUẬN: điểm X/8, CL1/CL2, trạng thái đi ngang.
  Độ rộng: ≥ 10 mã quét thì tính trên các mã quét. Ít hơn thì dùng `thi_truong_cl.json` cùng phiên của ptcp (nếu có),
  không có thì ước tính bằng VNI > MA200.
- **Mọi chiến lược** đều kèm cột *Nhóm chiến lược*:
  🟢 MUA MỚI · ✅ VÀO NHƯ LỆNH MỚI · 🟡 VÀO ½ · ⏳ CHỜ ĐIỀU CHỈNH · ⛔ hệ thống lỗ / sắp bán · chưa có tín hiệu.
  Kèm *Đạt điểm mua* và *Vô hiệu khi*.
- **Hành động** theo nhóm (đã đạt lọc của chiến lược đang chạy):

  | Nhóm | Hành động |
  |---|---|
  | 🟢 / ✅ | MUA |
  | 🟡 | MUA THĂM DÒ (½ vị thế) |
  | ⏳ | CHỜ NHỊP CHỈNH |
  | còn lại | THEO DÕI |

  Cờ đỏ nặng (tài chính, thanh khoản, kiểm toán…) hạ xuống THEO DÕI. Dưới SuperTrend / thủng hỗ trợ chỉ còn là lưu ý,
  vì chiến lược đã xét thời điểm.
- **Kế hoạch giao dịch**:
  - vùng mua của hệ thống (chỉ 1 phiên hiệu lực);
  - cắt lỗ chuẩn hệ thoát (2×ATR, ≤ 7%, ≥ 1,5×ATR; lệnh vào trễ dùng cắt lỗ hệ thống);
  - **mục tiêu tạm thời 1R → 3R** (mốc dời cắt lỗ, KHÔNG chốt cứng – bán theo hệ thoát T2-3R-ma10);
  - bỏ điều kiện R/R ≥ 2 theo mục tiêu kỹ thuật.
- **Cắt lỗ & mục tiêu ở MỌI chỗ** (bảng, Excel, biểu đồ, kế hoạch, mọi chiến lược) = giá trị chiến lược thị trường:
  - cắt lỗ của hệ thống, hoặc chuẩn hệ thoát (2×ATR, ≤ 7%, ≥ 1,5×ATR) nếu mã chưa có tín hiệu;
  - mục tiêu = mốc 1R / 3R; "Upside 3R %" = % tới mốc 3R.

  Không còn dùng cắt lỗ thống nhất cũ hay mục tiêu kỹ thuật (đỉnh cũ, Fibo…). Các tiêu chí `upside_min`, `rr_min`
  đã bỏ khỏi mọi chiến lược (vẫn dùng được qua `--them` nếu muốn).
- Muốn cách đánh giá cũ: `THEO_CHIEN_LUOC_TT = False` trong `bo_loc/cau_hinh.py`. Chiến lược cũ vẫn chạy được, VD
  `--chien_luoc ky_thuat`.
- Lõi `bo_loc/loi` **dùng thẳng ptcp** (không còn bản sao) – xem *Đồng bộ với ptcp*.

## Chạy nhanh trên Colab

Bộ lọc cần gói **ptcp** (lõi dùng chung, ở repo danh-muc). Trên Colab chọn 1 cách:
- upload thư mục `ptcp/` (hoặc zip) vào `/content` cạnh `bo_loc.zip` – bộ lọc tự tìm ở thư mục làm việc; hoặc
- `os.environ["DANH_MUC_TOKEN"] = "github_pat_..."` (token chỉ đọc repo danh-muc) trước khi `import bo_loc` → tự tải.

Upload `bo_loc.zip` vào `/content`, rồi chạy:

```python
import sys, os, importlib, zipimport
ZIP = "/content/bo_loc.zip"
sys.path[:] = [p for p in sys.path if "bo_loc" not in p]
sys.path.insert(0, ZIP)
for m in [m for m in list(sys.modules) if m.split(".")[0] == "bo_loc"]:
    del sys.modules[m]
zipimport._zip_directory_cache.clear(); sys.path_importer_cache.clear(); importlib.invalidate_caches()
import bo_loc
from bo_loc.cli import chay
print("Đã nạp", ZIP, "| phiên bản", bo_loc.__version__)
```

```python
kq = chay(["--nhom", "hose", "--chien_luoc", "diem_mua"])
display(kq["ket_luan"])
```

**Máy tính:** `python -m bo_loc --nhom cang_bien --chien_luoc xu_huong`

Lệnh cũ vẫn chạy được: `python bo_loc_co_phieu.py ...`. Các tham số giữ nguyên như bản cũ, có thêm:

| Tham số mới | Tác dụng |
|---|---|
| `--luon_lay_co_ban` | Lấy P/E, P/B, ROE cả khi chiến lược không cần, để có bảng so sánh ngành |
| `--nguon_gia VCI,TCBS,Yahoo` | Đổi thứ tự thử nguồn giá |
| `--khong_bieu_do` | Bỏ vẽ biểu đồ để chạy nhanh hơn |
| `--thu_muc_ket_qua DIR` | Nơi tạo thư mục kết quả |

## Đọc kết quả

Màn hình in theo 4 phần:

1. **BƯỚC 1 – LỌC**: mã có khớp mẫu hình của chiến lược đang chạy không (✔ đạt, ◐ đạt nhưng thiếu dữ liệu). Kèm danh sách mã gần đạt và các mã mới vào/rời khỏi so với lần lọc trước.
2. **BƯỚC 2–5 – ĐÁNH GIÁ**: chấm điểm 5 trụ cột theo cùng một cách cho mọi chiến lược. Cột cuối là hành động gợi ý.
3. **DỮ LIỆU**: nguồn nào đã chạy được, các mã có số liệu lệch giữa các nguồn.
4. **KẾT LUẬN** (in cuối cùng):
   - **[NÊN MUA]**: có kế hoạch đầy đủ (vùng mua, cắt lỗ, mục tiêu, khối lượng, lý do).
   - **[MUA CÓ ĐIỀU KIỆN]**: mua thăm dò ½ vị thế, hoặc chờ giá chỉnh về vùng mua.
   - **[THEO DÕI]**: ghi rõ cần chờ điều kiện gì.
   - **[LOẠI]**: chỉ đếm số lượng theo lý do.

Trong Excel, sheet **Ket luan** nằm đầu tiên. Trong notebook, xem bằng `display(kq["ket_luan"])`.

## 5 bảng kết quả

Sau BƯỚC 1, kết quả được trình bày thêm theo 4 bảng (in màn hình + file
`chien_luoc_<tên chiến lược>.xlsx`, kèm sheet *CHỈ TIÊU ĐÃ CHỌN*; trong notebook: `kq["bang_ket_qua"]["TỔNG QUAN"]`):

| Bảng | Cột |
|---|---|
| TỔNG QUAN | Mã, ngành, giá (VND), KL TB 3 tháng, GTGD TB20, Beta, RSI, EPS (TTM), P/E, vốn hoá, đạt lọc, điểm |
| TÀI CHÍNH | Giá, doanh thu & LNST 4 quý, tăng trưởng LN quý, biên gộp, EPS, BVPS, P/E, P/B, ROE |
| KỸ THUẬT | KL phiên, giá, hướng MA20/50/100, RSI, RS6M/RS52W (xếp hạng 1–99 trong lần quét), mô hình nến |
| BIẾN ĐỘNG | % thay đổi 1 ngày → 1 năm, từ đầu năm |

## Nguồn vnstock (bản Cộng đồng) – tự cài trên Google Colab

Bộ lọc dùng thư viện **vnstock ≥ 4.0.9** (nguồn KBS → VCI bên trong) làm thêm một nguồn cho **giá, P/E/P/B/ROE,
LNST 4 quý, BCTC năm (10 tiêu chí) và danh sách HOSE**. Thứ tự: giá `… SSI → vnstock → Yahoo`;
cơ bản `VNDirect → vnstock → TCBS → Yahoo`; BCTC năm `TCBS → vnstock → Yahoo`.

- **Colab:** lần chạy đầu bộ lọc tự chạy lệnh cài chính thức
  `pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.9" "vnai>=2.6.2"`
  (gói không có trên PyPI nên bắt buộc có `--extra-index-url`). Muốn tự cài trước: chạy lệnh trên với `!` ở đầu.
- **Máy cá nhân:** không tự cài – tự cài vào môi trường ảo theo https://vnstocks.com/files/vibe-onboarding.md
- **Không cần khoá API** (bản Cộng đồng); bộ lọc không đọc/in/hỏi khoá. Gói `vnai` gửi số lượt dùng & mã thiết bị
  về vnstocks.com để giới hạn tần suất – quét toàn sàn có thể chạm giới hạn, khi đó nguồn khác tự bù.
- **Hạn mức lượt gọi:** bộ lọc tự giữ dưới 55 lượt/phút (có khoá) hoặc 18 lượt/phút (không khoá). Hết lượt
  thì KHÔNG dừng – tự chuyển sang VNDirect/TCBS/Yahoo; nếu vnstock báo "Rate limit exceeded" thì tạm nghỉ vnstock
  65 giây rồi dùng lại. Muốn **chờ cho đủ hạn mức** (chậm hơn, lấy hết từ vnstock): thêm `--cho_vnstock`. Đổi mức: `from bo_loc.nguon import vnstock_nguon; vnstock_nguon.LUOT_MOI_PHUT = 50`.
- Tắt: `--khong_vnstock` (hoặc `DUNG_VNSTOCK = False` trong `cau_hinh.py`).
- Số liệu vnstock bị trống? Chạy `from bo_loc.nguon.vnstock_nguon import nhan_dien_cot; nhan_dien_cot("GMD")`
  rồi gửi kết quả để chỉnh từ khoá dò cột.

## Phân tích tài chính 10 tiêu chí

Khi có dữ liệu cơ bản, mỗi mã được chấm **10 tiêu chí trên BCTC 3–4 năm** (nguồn TCBS → Yahoo), mỗi tiêu chí 5 mức
**Rất tốt / Tốt / Trung bình / Cảnh báo / Nguy hiểm**:
phát hành tăng vốn, tăng trưởng doanh thu, biên lãi gộp, tăng trưởng lợi nhuận, chất lượng dòng tiền,
khả năng thanh toán, áp lực nợ vay, cấu trúc vốn, ROE, kế hoạch kinh doanh (*chưa có dữ liệu – để trống*).
Ngân hàng/CK/bảo hiểm bỏ 4 tiêu chí không phù hợp (biên gộp, thanh toán, nợ vay, cấu trúc vốn).

- Bảng thứ 5 **PHÂN TÍCH TÀI CHÍNH** trong `chien_luoc_<tên chiến lược>.xlsx` (tô màu theo 5 mức, rê chuột xem giải thích).
- Điểm 0–100 (`fa_diem`) đưa vào trụ cột *Chất lượng*; ≥ 2 tiêu chí Nguy hiểm → **cờ đỏ**.
- Tiêu chí lọc mới: `fa_khong_nguy_hiem` (bắt buộc trong `gia_tri`, cộng điểm ở `xu_huong`, `bat_day`), `fa_diem_min`.

## Chiến lược (đã gộp – 5 phong cách + tự đặt)

| Chiến lược | Dùng khi |
|---|---|
| `quy_b` *(mặc định)* | Chiến lược đang áp dụng – Quỹ B: hệ B, top 100 GTGD, thoát 2R – MA10 tuần – **cùng tiêu chí bot `canh-bao-mua`** |
| `ky_thuat` | Lọc tổng quát: xu hướng + cơ bản tối thiểu (bộ tiêu chí cũ của bot) |
| `xu_huong` | Mua theo đà: giá > MA50 > MA200, RSI 50–72, mạnh hơn VN-Index, có lãi |
| `diem_mua` | Điểm vào: MACD ngày vừa cắt lên |
| `bat_day` | Hồi phục có xác nhận: RSI 25–45 + tín hiệu đảo chiều, có lãi, P/E ≤ 20 |
| `gia_tri` | Rẻ mà tốt: ROE ≥ 15%, P/E ≤ 10, P/B ≤ 2, LN quý ≥ cùng kỳ, giá > MA200 (+ cộng điểm cổ tức, nợ, FCF…) |
| `tich_luy_vuot` | Tín hiệu "Tích lũy và Vượt": nền > 20 phiên (biên độ ≤ 15%), KL > 5× TB nền, giá tăng > 5%, vượt đỉnh nền. Đổi ngưỡng: `--them tich_luy_vuot=40:3:3` |
| `tuy_chinh` | Tự đặt (sửa file `bo_loc/chien_luoc/tuy_chinh.py` hoặc JSON trong `chien_luoc_rieng/`) |

**Ghép tiêu chí lúc chạy** thay cho các bản biến thể:

```python
chay(["--chien_luoc", "xu_huong", "--them", "beta_min=1.2"])                # xu hướng rủi ro cao
chay(["--chien_luoc", "bat_day", "--them", "beta_min=1.2", "--rui_ro", "0.5"])  # bắt đáy rủi ro cao
chay(["--chien_luoc", "gia_tri", "--them", "von_hoa_min=300,gtgd_min=2"])   # nới điều kiện
chay(["--chien_luoc", "gia_tri", "--bo", "tren_ma200"])                     # bỏ 1 tiêu chí
```

`--them khoa=gia_tri` đưa tiêu chí vào nhóm BẮT BUỘC (khoảng dùng `a:b`, VD `rsi_trong=25:45`; tiêu chí không cần ngưỡng
để trống, VD `pe_duoi_tv_nganh=`). Tên cũ (`rui_ro_cao`, `rui_ro_cao_xu_huong`, `co_ban`, `tieu_chuan`) vẫn chạy được – tự chuyển sang chiến lược mới.

## Đồng bộ với ptcp (lõi dùng chung)

- **Một nguồn logic**: bộ lọc nạp gói **ptcp** (repo danh-muc) và dùng thẳng – `bo_loc/loi/*`, `danh_gia_tai_chinh`,
  `nguon/vnstock_nguon`, phần đọc BCTC năm đều trỏ tới ptcp (`bo_loc/_ptcp.py`). Sửa ptcp là bộ lọc, danh-muc,
  canh-bao-mua dùng ngay – không còn chép tay (trước đây bản sao lệch: vnstock của bộ lọc còn lỗi CFO / đơn vị đã sửa ở ptcp).
  Nạp ptcp: đã import được → thư mục `ptcp/` cạnh `bo_loc_co_phieu.py` hoặc `PTCP_DIR` → tự tải bằng `DANH_MUC_TOKEN`.
  GitHub Actions: bước *Lấy ptcp* (`python lay_ptcp.py`) – cần **secret `DANH_MUC_TOKEN_GHI`** (token repo danh-muc,
  dùng chung với bot).
- **Đỉnh/đáy, đường xu hướng, cắt lỗ, mục tiêu** = ptcp: đỉnh/đáy theo **giá đóng cửa**, **cắt lỗ thống nhất**
  (max(đáy ngày xác nhận − 0,5×ATR; giá − 2×ATR; giá −7%), tối thiểu 1,5×ATR), mục tiêu = **mục tiêu ngắn hạn khung
  ngày** của ptcp (63 phiên). Cùng một mã → cùng mức giá ở mọi công cụ.
- **P/E** luôn theo quy tắc EPS = LNST 4 quý ÷ CP lưu hành: dữ liệu (kể cả lưu đệm) thiếu LNST 4 quý thì tự lấy bổ sung
  từ vnstock → Yahoo; chỉ khi không nguồn nào có mới dùng EPS nguồn công bố (cột `pe_cach_tinh` ghi rõ).
  CP lưu hành đã trừ CP quỹ (VCSH cổ đông mẹ ÷ BVPS, Yahoo).
- **P/B = giá hiện tại ÷ BVPS** như ptcp; P/B của nguồn (theo giá ngày báo cáo) chỉ dùng khi không có BVPS.
- **TCBS đã tắt** (không còn trả dữ liệu) – bật lại: thêm "TCBS" vào `THU_TU_NGUON_CO_BAN`.

## Cấu trúc

```
bo_loc/
  cau_hinh.py            mọi ngưỡng, hằng số, thứ tự nguồn
  danh_sach_ma.py        nhóm mã (đã tách cang_bien / van_tai_bien), ngưỡng riêng
  tieu_chi.py            danh mục tiêu chí (khoá → hàm kiểm tra)
  chien_luoc/            MỖI CHIẾN LƯỢC 1 FILE: ky_thuat, xu_huong, diem_mua, bat_day, gia_tri, tuy_chinh
  nguon/gia.py           7 nguồn giá + chuẩn hoá đơn vị + cache
  nguon/co_ban.py        nhiều nguồn cơ bản + gộp theo chỉ tiêu + đối chiếu chéo + cache 24h
  nguon/http.py          phiên kết nối có thử lại, nhật ký nguồn
  phan_tich/ky_thuat.py  MACD/RSI/ATR/ADX/SuperTrend, đỉnh đáy, mục tiêu
  phan_tich/chi_so.py    toàn bộ chỉ tiêu của 1 mã
  loc.py                 B1 lọc & xếp hạng
  danh_gia_sau_loc.py    B2–B6
  ket_luan.py            kết luận cuối: nên mua / có điều kiện / theo dõi / loại
  bon_bang.py            4 bảng kết quả (Tổng quan | Tài chính | Kỹ thuật | Biến động) + bảng 10 tiêu chí, Excel
  loi/                   trỏ thẳng tới ptcp (chỉ báo, đỉnh/đáy, cắt lỗ, mục tiêu, chiến lược, hệ thoát)
  _ptcp.py               nạp gói ptcp (sys.path / PTCP_DIR / tự tải bằng DANH_MUC_TOKEN)
  lich_su.py, xuat.py, cli.py
tests/                   64 test offline + test nguồn thật (đánh dấu "mang")
```

## Sửa / thêm chiến lược

Mỗi chiến lược là một file riêng. Để thêm chiến lược, copy `bo_loc/chien_luoc/xu_huong.py` thành `ten_moi.py` rồi sửa ngưỡng. Sau đó chạy `--chien_luoc ten_moi`, không cần đăng ký ở đâu khác.

Nếu không muốn sửa code, đặt file `./chien_luoc_rieng/ten.json` cùng cấu trúc. Chương trình kiểm tra khoá tiêu chí ngay khi nạp, gõ sai tên sẽ báo lỗi rõ ràng.

## Nguồn dữ liệu

| Loại | Nguồn (thử lần lượt) | Ghi chú |
|---|---|---|
| Giá ngày | VNDirect → TCBS → DNSE → VCI → SSI → Yahoo (`GMD.VN`) | |
| Cơ bản | file của bạn → VNDirect (api-finfo) → TCBS → Yahoo (yfinance) | gộp theo từng chỉ tiêu |

**P/E = Thị giá ÷ EPS**, với **EPS = LNST (cổ đông công ty mẹ) 4 quý gần nhất ÷ số CP lưu hành** – tự tính (LNST 4 quý: file `ln_4q_ty` → TCBS → Yahoo; phải đủ 4 quý liên tiếp). Không đủ dữ liệu tự tính thì mới dùng EPS 4 quý nguồn công bố (VNDirect `EPS_TR`). Cột `pe_cach_tinh` ghi rõ đã tính theo cách nào, `eps_dung` là EPS đã dùng, `ky_lnst` là 4 quý đã cộng. Cột `ky_eps` ghi kỳ báo cáo của EPS; `pe_nguon` là P/E do nguồn công bố để đối chiếu. Mã có lãi/lỗ bất thường lớn (VD thoái vốn): điền cột `eps_cot_loi` trong `co_ban.csv` → P/E tính theo EPS cốt lõi.
| VNINDEX | như nguồn giá (trừ Yahoo) | |

Tất cả đều là API công khai không chính thức của các công ty chứng khoán, có thể đổi hoặc bị chặn bất cứ lúc nào.
Chương trình tự chuyển sang nguồn khác khi một nguồn lỗi; nguồn nào lỗi liên tiếp 5 lần mà chưa thành công lần nào sẽ bị bỏ qua cho phần còn lại của lần chạy (khỏi chờ timeout). Kết quả được ghi ở hai sheet Excel:
- **Nguon du lieu**: từng lần gọi.
- **Suc khoe nguon**: tỷ lệ thành công theo từng nguồn.

Muốn biết nguồn nào đang sống thì chạy `pytest -m mang -v`.

**Số liệu đưa vào báo cáo:**
- Cột `nguon_chi_tieu` ghi rõ từng chỉ tiêu lấy từ nguồn nào.
- Sheet **Canh bao du lieu** liệt kê các mã mà hai nguồn lệch nhau trên 20% ở EPS, BVPS (số CP trên 1%, ROE trên 5 điểm %). Không so P/E, P/B vì mỗi nguồn tính theo giá của một ngày khác nhau.
- Nếu cần chắc chắn, chạy `--tao_mau_co_ban`, điền số từ BCTC/CafeF/Vietstock, rồi chạy kèm `--co_ban co_ban.csv`. File của bạn luôn được ưu tiên. File chấp nhận cả số kiểu Việt Nam (`15,5`, `1.234,5`).

Thêm nguồn mới: viết 1 hàm theo mẫu trong `nguon/gia.py` hoặc `nguon/co_ban.py`, đăng ký vào dict `NGUON_GIA`/`NGUON_CO_BAN` và thêm tên vào `cau_hinh.py`.

## Thay đổi so với bản cũ

1. **Sửa lỗi dừng chương trình:** `THONG_TIN_BO_SUNG` được gọi nhưng chưa định nghĩa, nên báo NameError mỗi khi có dữ liệu cơ bản. Đã bỏ biến này. Dữ liệu bổ sung giờ nhập qua file `--co_ban`, không gắn cứng theo mã.
2. **Sửa lỗi đọc CSV với pandas ≥ 2.x/3.0:** số có dấu phẩy (`78,700`) không được đổi sang số, khiến cả file bị bỏ.
3. **P/E, P/B theo giá hiện tại:** tính bằng giá ÷ EPS 4 quý (tự tính từ LNST 4 quý) hoặc ÷ EPS năm. Số của nguồn vẫn giữ ở cột `pe_nguon` để đối chiếu.
4. **B6 so với trung vị đúng nhóm ngành:** bản cũ lấy trung vị toàn bộ mã quét. Nếu nhóm có dưới 3 mã thì mới so với toàn bộ, và ghi rõ ở cột `Cơ sở so sánh`.
5. **Tách nhóm `cang_bien` (khai thác cảng) khỏi `van_tai_bien` (chủ tàu)** để P/E so sánh đúng bản chất. Nhóm gộp cũ vẫn dùng được với tên `cang_va_van_tai`.
6. **Hạ tầng mạng và dữ liệu:**
   - Gọi HTTP có thử lại khi lỗi 429/5xx.
   - Phiên kết nối riêng cho từng luồng.
   - Tự nhận đơn vị giá (đồng hay nghìn đồng).
   - Loại dữ liệu hỏng (giá ≤ 0, high < low).
   - Lưu đệm dữ liệu cơ bản 24 giờ.
7. Biểu đồ đóng sau khi lưu (không rò bộ nhớ khi quét toàn sàn) và chạy được không cần màn hình (GitHub Actions).
