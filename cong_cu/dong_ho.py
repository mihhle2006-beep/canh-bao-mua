# -*- coding: utf-8 -*-
"""
ĐỒNG HỒ – gọi các workflow ĐÚNG GIỜ Việt Nam thay cho lịch cron của GitHub (05/11/2026: cron trễ 4–8 GIỜ – Lọc quỹ 06:07
chạy 10:24, Danh mục 08:30 chạy 15:18, Kiểm thử 07:41 chạy 14:22, Quét bộ lọc 14:20 chạy 22:37).
  • Mỗi phút xét bảng LICH (giờ VN): mốc vừa tới (≤ "trễ tối đa" phút) mà workflow CHƯA có lần chạy nào từ mốc đó (lịch
    GitHub tự chạy đúng giờ / bot tự gọi / bấm tay đều tính) → gọi workflow_dispatch (kèm inputs).
  • Lịch cron cũ GIỮ làm dự phòng; workflow có job "gac" (gac.yml → `dong_ho.py --gac`) tự bỏ qua khi cron tới trễ mà
    đồng hồ / bấm tay đã chạy từ mốc lịch đó. Workflow phân biệt lịch / bấm tay (github.event.schedule) có input "lich":
    đồng hồ truyền đúng chuỗi cron (UTC) → chạy y như lịch.
  • Chạy liên tục: mỗi lượt ≈ 5 giờ 40 phút rồi tự gọi lượt sau (GITHUB_TOKEN gọi workflow_dispatch vẫn tạo lần chạy mới);
    đứt chuỗi → lịch dự phòng của dong_ho.yml (2 giờ / lần) khởi động lại; lượt đến sau thấy lượt cũ còn chạy → thoát.
  • Việc ở repo KÍN danh-muc (máy Mac: vòng đồng bộ DNSE, xin mã OTP đặt lệnh) – dòng "danh-muc/<file>": gọi bằng token
    DANH_MUC_TOKEN_GHI (cần quyền Actions: Read and write ở danh-muc); việc đó đang chạy / đang chờ máy Mac → không gọi.
  • 20:05 hằng ngày: kiểm hạn token repo kín (DANH_MUC_TOKEN_GHI) – còn < 14 ngày → nhắn Telegram.
  • Giám sát 5 phút / lần: workflow trên main vừa LỖI → workflow dữ liệu / trang (CHAY_LAI – chạy lại không gửi tin
    trùng) tự chạy lại job lỗi 1 lần; còn lại, hoặc chạy lại vẫn lỗi → nhắn Telegram NGAY (không đợi tin 🩺 19:55).
  • Máy Mac (cùng nhịp 5 phút, T2–T6 08:30–15:10): job của repo kín chờ máy self-hosted > 10 phút (Mac ngủ / tắt / mất
    mạng → vòng đồng bộ DNSE, lệnh đứng) → nhắn Telegram NGAY 1 tin / đợt; máy nhận việc lại → 1 tin báo đã ổn.
Chỉ dùng thư viện chuẩn (không cần pip). Log chỉ in tên workflow / giờ.
  python cong_cu/dong_ho.py --phut 340            # trên Actions (GH_TOKEN, GITHUB_REPOSITORY, GITHUB_RUN_ID)
  python cong_cu/dong_ho.py --thu "2026-11-06 06:43"   # in workflow sẽ gọi ở thời điểm đó (không gọi thật)
  python cong_cu/dong_ho.py --gac loc_quy_b.yml --lich "7 23 * * 0-4"   # job gac: in "chay=true|false"
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
API = "https://api.github.com"

# (workflow, "phút giờ ngày tháng thứ" giờ VN – thứ 1 = T2 … 7 = CN, inputs, trễ tối đa (phút) vẫn gọi bù).
# Mỗi dòng ứng đúng 1 lịch cron (UTC) trong file workflow – tests/test_dong_ho.py đối chiếu.
LICH = [
    ("loc_quy_b.yml", "7 6 * * 1-5", {}, 180),
    ("tra_cuu_web.yml", "41 6 * * 1-6", {}, 300),
    ("canh_bao.yml", "43 6 * * 1-5", {"vong": "sang"}, 240),          # vòng sáng tự gọi vòng chiều → danh mục → tổng kết
    ("canh_bao.yml", "53 10 * * 1-5", {"vong": "chieu"}, 200),        # dự phòng: xếp hàng sau vòng sáng
    ("canh_bao.yml", "20 15 * * 1-5", {"che_do": "tong_ket"}, 120),   # dự phòng: đã gửi thì không gửi lặp
    ("canh_bao.yml", "7 9 * * 6", {"che_do": "lich_su"}, 600),
    ("kiem_thu.yml", "41 7 * * 1-5", {}, 600),
    ("danh_muc.yml", "30 8 * * 1-5", {"lich": "30 1 * * 1-5"}, 120),        # chỉ chạy khi nhap.txt có lệnh
    ("danh_muc.yml", "50 14 * * 1-5", {"lich": "50 7 * * 1-5"}, 120),       # dự phòng lượt vòng chiều gọi 15:02
    ("nhip_thi_truong.yml", "45 8 * * 1-5", {}, 150),
    ("nhip_thi_truong.yml", "43 12 * * 1-5", {}, 120),
    ("quet_dinh_ky.yml", "20 14 * * 1-5", {"lich": "20 7 * * 1-5"}, 420),   # tự chờ 15:02
    ("bang_thi_truong.yml", "10 15 * * 1-5", {}, 60),
    ("bang_thi_truong.yml", "7 19 * * 1-5", {"chuan_bi": "true"}, 240),
    ("gia_lap.yml", "30 16 * * 1-5", {}, 50),
    ("gia_lap.yml", "30 17 * * 1-5", {}, 50),
    ("gia_lap.yml", "53 18 * * 1-5", {}, 60),
    ("suc_khoe.yml", "55 19 * * 1-5", {}, 240),
    ("tong_ket_tuan.yml", "17 20 * * 5", {}, 240),
    ("bctc_moi_dem.yml", "13 22 * * *", {}, 300),
    ("doc_bctn.yml", "17 22 * * *", {}, 300),
    ("lenh_tele.yml", "37 * * * *", {}, 40),
    ("tra_cuu.yml", "53 7 * * 6", {"lich": "53 0 * * 6"}, 600),
    ("kho_bctc.yml", "47 0 * * 7", {"lich": "47 17 * * 6"}, 600),
    ("kho_bctc.yml", "37 1 * * *", {"lich": "37 18 * * *"}, 240),         # bổ sung đêm: UPCoM + BCTC dài VNDirect
    ("ke_hoach_dhcd.yml", "23 0 * * *", {"con_lai": "HOSE,HNX,UPCOM"}, 240),  # kế hoạch ĐHCĐ mã còn lại
    ("tai_nen_15p.yml", "43 1 * * 7", {}, 600),
    ("boi_so_nganh.yml", "13 3 * * 7", {}, 600),
    ("backtest_quy_b.yml", "13 9 1 * *", {}, 1440),
    ("backtest.yml", "17 2 2 * *", {}, 1440),
    # repo kín danh-muc – chạy trên máy Mac (như may_mac/bat_vong.sh): Mac ngủ thì lần chạy chờ, Mac thức là chạy
    ("danh-muc/dnse_dong_bo.yml", "35 8 * * 1-5", {"vong": "true"}, 360),     # vòng đồng bộ DNSE 10' / lần tới 15:05
    ("danh-muc/dat_lenh.yml", "40 8 * * 1-5", {}, 20),                       # xin mã giao dịch (Smart OTP)
    ("danh-muc/dnse_dong_bo.yml", "47 12 * * 1-5", {"vong": "true"}, 120),    # vòng chết buổi trưa → bật lại
]
BO_NEU_DANG_CHAY = {"danh-muc/dnse_dong_bo.yml", "danh-muc/dat_lenh.yml"}   # đang chạy / chờ máy Mac → không gọi thêm
# lỗi lần đầu → tự chạy lại job lỗi 1 lần (dựng dữ liệu / trang: lỗi hay do nguồn chập chờn, chạy lại không gửi tin trùng)
CHAY_LAI = {"bang_thi_truong.yml", "tra_cuu_web.yml", "bctc_moi_dem.yml", "doc_bctn.yml", "loc_quy_b.yml",
            "kho_bctc.yml", "boi_so_nganh.yml", "ke_hoach_dhcd.yml", "tra_tai_lieu.yml", "tai_nen_15p.yml"}
KHONG_BAO = {"dong_ho.yml", "kiem_thu.yml",                       # kiem_thu tự nhắn khi lỗi
             "doc_trang.yml", "chan_doan.yml", "dnse_kiem.yml"}     # công cụ bấm tay – người bấm tự xem
LOI = ("failure", "timed_out", "startup_failure")
GIAM_SAT_GIAY = 300
MAC_CHO_PHUT = 10                                                   # job chờ máy Mac quá ngần này → nhắn
MAC_GIO = ("08:30", "15:10")                                        # T2–T6 giờ VN: vòng DNSE 08:35, lệnh, đo trong phiên
KIEM_TOKEN = "5 20 * * *"                                           # giờ VN kiểm hạn token
TOKEN_CON_NGAY = 14


# ---------------------------------------------------------------- lịch kiểu cron (giờ VN)
def _truong(f, gia_tri, nho, lon):
    if f == "*":
        return True
    for phan in f.split(","):
        buoc = 1
        if "/" in phan:
            phan, b = phan.split("/")
            buoc = int(b)
        if phan == "*":
            a, z = nho, lon
        elif "-" in phan:
            a, z = (int(x) for x in phan.split("-"))
        else:
            a = z = int(phan)
        if a <= gia_tri <= z and (gia_tri - a) % buoc == 0:
            return True
    return False


def _hop_ngay(n, th, thu, t, cron_gh):
    if cron_gh:                                                     # cron GitHub: thứ 0 = CN … 6 = T7 (7 cũng là CN)
        d = t.isoweekday() % 7
        hop_thu = _truong(thu, d, 0, 6) or (d == 0 and _truong(thu, 7, 0, 7))
    else:
        hop_thu = _truong(thu, t.isoweekday(), 1, 7)
    return _truong(n, t.day, 1, 31) and _truong(th, t.month, 1, 12) and hop_thu


def khop(lich, t, cron_gh=False):
    """t khớp lịch 'phút giờ ngày tháng thứ'? Mặc định bảng LICH (giờ VN, thứ 1 = T2 … 7 = CN); cron_gh=True: chuỗi cron
    của GitHub (so với t theo UTC, thứ 0 = CN)."""
    p, g, n, th, thu = lich.split()
    return _truong(p, t.minute, 0, 59) and _truong(g, t.hour, 0, 23) and _hop_ngay(n, th, thu, t, cron_gh)


def moc_gan_nhat(lich, bay_gio, tre, cron_gh=False):
    """Mốc khớp lịch gần nhất trong [bay_gio − tre phút, bay_gio] (làm tròn phút) → datetime hoặc None."""
    t = bay_gio.replace(second=0, microsecond=0)
    for k in range(int(tre) + 1):
        x = t - timedelta(minutes=k)
        if khop(lich, x, cron_gh):
            return x
    return None


def cac_moc(lich, tu, den, cron_gh=False):
    """Mọi mốc khớp lịch trong [tu, den) (tu tròn phút) – lọc theo ngày rồi giờ cho nhanh (kiểm bảng LICH ↔ cron)."""
    p, g, n, th, thu = lich.split()
    ngay = tu.replace(hour=0, minute=0, second=0, microsecond=0)
    while ngay < den:
        if _hop_ngay(n, th, thu, ngay, cron_gh):
            for h in range(24):
                if _truong(g, h, 0, 23):
                    for m in range(60):
                        x = ngay.replace(hour=h, minute=m)
                        if _truong(p, m, 0, 59) and tu <= x < den:
                            yield x
        ngay += timedelta(days=1)


# ---------------------------------------------------------------- GitHub API (thư viện chuẩn)
class GitHub:
    def __init__(self, repo, token):
        self.repo, self.token, self._nho = repo, token, {}

    def _goi(self, duong, du_lieu=None, phuong=None):
        req = urllib.request.Request(f"{API}/repos/{self.repo}/{duong}", method=phuong or ("POST" if du_lieu else "GET"),
                                     data=json.dumps(du_lieu).encode() if du_lieu is not None else None,
                                     headers={**({"Authorization": f"Bearer {self.token}"} if self.token else {}),
                                              "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "dong-ho"})
        with urllib.request.urlopen(req, timeout=30) as r:
            nd = r.read()
        return json.loads(nd) if nd else {}

    def lan_chay(self, wf, ttl=55):
        """Lần chạy gần nhất của workflow (đệm ttl giây – mỗi phút 1 lượt gọi / workflow)."""
        x = self._nho.get(wf)
        if x and time.time() - x[0] < ttl:
            return x[1]
        ds = self._goi(f"actions/workflows/{wf}/runs?per_page=30").get("workflow_runs") or []
        self._nho[wf] = (time.time(), ds)
        return ds

    def goi(self, wf, inputs=None, ref="main"):
        self._goi(f"actions/workflows/{wf}/dispatches", {"ref": ref, **({"inputs": inputs} if inputs else {})})
        self._nho.pop(wf, None)


def _thoi_diem(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def _tren_main(r):
    """Lần chạy trên nhánh main (lần chạy thử ở nhánh PR không tính là "đã chạy")."""
    return r.get("head_branch") in (None, "", "main")


def da_chay_tu(ds, moc, bo_id=None):
    """Có lần chạy nào trên main (mọi sự kiện, mọi trạng thái) tạo từ moc − 2 phút?"""
    nguong = moc - timedelta(minutes=2)
    return any(_thoi_diem(r["created_at"]) >= nguong for r in ds
               if r.get("id") != bo_id and r.get("created_at") and _tren_main(r))


def gac(gh, wf, lich_gh, bay_gio, run_id=None):
    """Job gac của lần chạy do LỊCH GitHub: mốc của cron lich_gh (UTC) gần nhất ≤ bay_gio (lùi ≤ 26 giờ – lịch trễ tới 8
    giờ); đã có lần chạy KHÁC (đồng hồ / bấm tay / lịch trùng) tạo từ mốc đó → (False, lý do): bỏ lượt trễ này. Không tìm
    thấy mốc / lỗi API → (True, lý do): thà chạy trùng còn hơn bỏ lượt."""
    try:
        moc = moc_gan_nhat(lich_gh, bay_gio.astimezone(timezone.utc), 26 * 60, cron_gh=True)
    except (ValueError, TypeError) as e:
        return True, f"lịch '{lich_gh}' lỗi ({e}) → chạy"
    if moc is None:
        return True, f"không thấy mốc lịch '{lich_gh}' → chạy"
    tre = int((bay_gio - moc).total_seconds() // 60)
    try:
        ds = gh.lan_chay(wf)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return True, f"không đọc được lần chạy ({str(e)[:60]}) → chạy"
    nguong = moc - timedelta(minutes=2)
    khac = [r for r in ds if str(r.get("id")) != str(run_id) and r.get("created_at") and _tren_main(r)
            and _thoi_diem(r["created_at"]) >= nguong]
    moc_vn = moc.astimezone(VN)
    if khac:
        r = min(khac, key=lambda r: r["created_at"])
        luc = _thoi_diem(r["created_at"]).astimezone(VN)
        return False, (f"lịch {moc_vn:%d/%m %H:%M} giờ VN tới trễ {tre}' – đã chạy lúc {luc:%H:%M} ({r.get('event')})"
                       " → bỏ lượt này")
    return True, f"lịch {moc_vn:%d/%m %H:%M} giờ VN (trễ {tre}') – chưa có lần chạy nào từ mốc → chạy"


# ---------------------------------------------------------------- đồng hồ
class DongHo:
    def __init__(self, gh, lich=None, in_ra=print, thu=False, gh_khac=None):
        self.gh, self.lich, self.in_ra, self.thu = gh, lich or LICH, in_ra, thu
        self.gh_khac = gh_khac or {}                                # "danh-muc" → GitHub(repo kín, token)
        self.xong = set()                                           # (wf, lịch, mốc) đã xét trong lượt chạy này
        self.da_bao = set()

    def _may(self, wf):
        """'danh-muc/x.yml' → (client repo kín | None, 'x.yml'); 'x.yml' → (client repo này, 'x.yml')."""
        if "/" not in wf:
            return self.gh, wf
        repo, ten = wf.split("/", 1)
        return self.gh_khac.get(repo), ten

    def buoc(self, bay_gio):
        """Xét mọi dòng lịch tại bay_gio → [(wf, inputs, mốc)] đã gọi."""
        da_goi = []
        for wf, lich, inputs, tre in self.lich:
            moc = moc_gan_nhat(lich, bay_gio, tre)
            if moc is None or (wf, lich, moc) in self.xong:
                continue
            gh, ten = self._may(wf)
            if gh is None:                                          # chưa có token repo kín → bỏ (báo 1 lần)
                self.xong.add((wf, lich, moc))
                if wf not in self.da_bao:
                    self.da_bao.add(wf)
                    self.in_ra(f"::warning::{wf}: thiếu secret DANH_MUC_TOKEN_GHI – không gọi được việc ở repo kín")
                continue
            try:
                ds = gh.lan_chay(ten)
                if wf in BO_NEU_DANG_CHAY and any(r.get("status") != "completed" for r in ds):
                    self.xong.add((wf, lich, moc))                  # đang chạy / đang chờ máy Mac → để yên
                    continue
                if not da_chay_tu(ds, moc):
                    if not self.thu:
                        gh.goi(ten, {k: str(v) for k, v in inputs.items()})
                    da_goi.append((wf, inputs, moc))
                    tre_phut = int((bay_gio - moc).total_seconds() // 60)
                    self.in_ra(f"{bay_gio:%d/%m %H:%M} gọi {wf} {inputs or ''} (mốc {moc:%H:%M}"
                               + (f", bù trễ {tre_phut}'" if tre_phut > 1 else "") + ")")
                self.xong.add((wf, lich, moc))
            except urllib.error.HTTPError as e:
                if "/" in wf and e.code in (401, 403, 404):           # token repo kín thiếu quyền Actions / hết hạn
                    self.xong.add((wf, lich, moc))
                    self.in_ra(f"::warning::{bay_gio:%H:%M} {wf}: GitHub {e.code} – token DANH_MUC_TOKEN_GHI cần quyền "
                               "Actions: Read and write ở repo danh-muc (hoặc đã hết hạn)")
                elif 400 <= e.code < 500 and e.code not in (403, 408, 429):   # 404 / 422 (input sai…): thử lại cũng vậy
                    self.xong.add((wf, lich, moc))
                    self.in_ra(f"::warning::{bay_gio:%H:%M} {wf}: GitHub {e.code} – bỏ mốc {moc:%H:%M}")
                else:
                    self.in_ra(f"{bay_gio:%H:%M} ⚠ {wf}: GitHub {e.code} – phút sau thử lại")
            except Exception as e:                                  # mạng chập chờn… – đồng hồ không được dừng
                self.in_ra(f"{bay_gio:%H:%M} ⚠ {wf}: {type(e).__name__} {str(e)[:80]} – phút sau thử lại")
        return da_goi


class GiamSat:
    """Lần chạy trên main vừa lỗi (cập nhật từ `tu`) → CHAY_LAI lần đầu: chạy lại job lỗi; còn lại → 1 tin Telegram gộp.
    Mỗi (lần chạy, lượt) xét 1 lần. Log chỉ in tên workflow (repo công khai)."""

    def __init__(self, gh, tu, gui=None, in_ra=print):
        self.gh, self.tu, self.gui, self.in_ra = gh, tu, gui or nhan_tele, in_ra
        self.da = set()

    def buoc(self):
        ds = [r for r in self.gh._goi("actions/runs?branch=main&per_page=60").get("workflow_runs") or [] if _tren_main(r)]
        tin = []
        for r in sorted(ds, key=lambda r: r.get("updated_at") or ""):
            wf = (r.get("path") or "").split("/")[-1]
            if r.get("status") != "completed" or wf in KHONG_BAO or not r.get("updated_at"):
                continue
            huy = r.get("conclusion") == "cancelled"
            # bị huỷ mà KHÔNG có lần chạy mới hơn thay thế (huỷ vì concurrency luôn có) → quá giờ (timeout) / huỷ tay → coi là lỗi
            if huy and any(x.get("path") == r.get("path") and (x.get("created_at") or "") > (r.get("created_at") or "")
                           for x in ds):
                continue
            if not huy and r.get("conclusion") not in LOI:
                continue
            luc = _thoi_diem(r["updated_at"])
            lan = int(r.get("run_attempt") or 1)
            if luc < self.tu or (r.get("id"), lan) in self.da:
                continue
            self.da.add((r.get("id"), lan))
            luc = luc.astimezone(VN)
            them = (" (bị huỷ – quá giờ?)" if huy else "") + (" – đã tự chạy lại 1 lần, vẫn lỗi" if lan > 1 else "")
            if wf in CHAY_LAI and lan == 1:
                try:
                    self.gh._goi(f"actions/runs/{r['id']}/{'rerun' if huy else 'rerun-failed-jobs'}", {}, "POST")
                    self.in_ra(f"giám sát: {wf} {'bị huỷ' if huy else 'lỗi'} {luc:%H:%M} → tự chạy lại")
                    continue
                except Exception as e:
                    them = f" – không tự chạy lại được ({type(e).__name__})"
            self.in_ra(f"giám sát: {wf} lỗi {luc:%H:%M}{them} → nhắn Telegram")
            tin.append(f"❌ {r.get('name') or wf} lỗi lúc {luc:%H:%M}{them}\n{r.get('html_url', '')}")
        if tin:
            self.gui("🚨 Workflow lỗi (đồng hồ báo ngay):\n" + "\n".join(tin)
                     + "\n→ bấm link xem log · chạy lại: nút Re-run jobs trên trang đó")
        return tin


class MayMac:
    """Trong phiên (T2–T6 MAC_GIO): job ở repo kín chạy trên máy Mac (nhãn self-hosted) đang CHỜ MÁY ≥ MAC_CHO_PHUT phút
    → Mac ngủ / tắt / mất mạng / runner dừng: vòng đồng bộ DNSE, xin mã OTP, lệnh đứng → 1 tin Telegram / đợt (không đợi tin
    🩺 tối). Hết job chờ: có job của đợt đã được máy nhận → 1 tin "đã nhận lại"; job bị huỷ hết → chỉ ghi log. Chờ hàng
    concurrency (lần chạy "pending") không tính – đó không phải lỗi máy. Log công khai: chỉ số job / phút, không tên việc."""

    def __init__(self, gh, gui=None, in_ra=print, cho=MAC_CHO_PHUT):
        self.gh, self.gui, self.in_ra, self.cho = gh, gui or nhan_tele, in_ra, cho
        self.dot = None                                             # đợt đang báo: {"tu": datetime, "job": {id: tên}}

    @staticmethod
    def trong_gio(bay_gio):
        t = bay_gio.astimezone(VN)
        return t.isoweekday() <= 5 and MAC_GIO[0] <= f"{t:%H:%M}" < MAC_GIO[1]

    def _dang_cho(self, bay_gio):
        """[(job, tên việc, phút chờ)] – mọi job self-hosted đang chờ máy (mọi độ dài)."""
        out = []
        for r in self.gh._goi("actions/runs?status=queued&per_page=30").get("workflow_runs") or []:
            for j in self.gh._goi(f"actions/runs/{r['id']}/jobs?per_page=30").get("jobs") or []:
                if j.get("status") != "queued" or "self-hosted" not in (j.get("labels") or []):
                    continue
                tu = _thoi_diem(j.get("created_at") or r.get("created_at"))
                out.append((j, r.get("name") or j.get("name") or "?", (bay_gio - tu).total_seconds() / 60))
        return out

    def buoc(self, bay_gio):
        """→ tin đã gửi (chuỗi) | None."""
        if not self.trong_gio(bay_gio):
            return None
        cho = self._dang_cho(bay_gio)
        lau = [x for x in cho if x[2] >= self.cho]
        if self.dot is not None:
            self.dot["job"].update({j["id"]: ten for j, ten, _ in lau})
            if cho:                                                 # còn job chờ máy → đợt chưa xong, không nhắn lặp
                return None
            dot, self.dot = self.dot, None
            nhan = []
            for jid in dot["job"]:
                j = self.gh._goi(f"actions/jobs/{jid}")
                if j.get("started_at") and j.get("status") != "queued" and j.get("conclusion") != "cancelled":
                    nhan.append(_thoi_diem(j["started_at"]))
            if not nhan:
                self.in_ra(f"máy Mac: việc chờ đã bị huỷ ({len(dot['job'])} job) – chưa thấy máy nhận lại")
                return None
            luc = min(nhan).astimezone(VN)
            tin = (f"✅ Máy Mac đã nhận việc lại lúc {luc:%H:%M} (chờ máy từ {dot['tu']:%H:%M}, "
                   f"{int((luc - dot['tu']).total_seconds() // 60)} phút)")
            self.in_ra(f"máy Mac: đã nhận việc lại {luc:%H:%M} → nhắn Telegram")
            self.gui(tin)
            return tin
        if not lau:
            return None
        tu = min(bay_gio - timedelta(minutes=p) for _, _, p in lau).astimezone(VN)
        self.dot = {"tu": tu, "job": {j["id"]: ten for j, ten, _ in lau}}
        dong = sorted({f"• {ten} – chờ {int(p)}'" for _, ten, p in lau})
        tin = (f"🖥 Máy Mac CHƯA NHẬN VIỆC – {len(lau)} việc chờ máy từ {tu:%H:%M}:\n" + "\n".join(dong)
               + "\n→ Vòng đồng bộ DNSE / lệnh đang đứng: Mac ngủ / tắt / mất mạng? Đánh thức Mac, cắm điện, kiểm Wi-Fi – "
                 "máy thức là runner tự nhận việc (bot báo lại khi đã nhận).")
        self.in_ra(f"máy Mac: {len(lau)} job chờ máy ≥ {self.cho}' → nhắn Telegram")
        self.gui(tin)
        return tin


def han_token(token):
    """Ngày hết hạn token (header github-authentication-token-expiration) → datetime | None (không hạn / lỗi)."""
    if not token:
        return None
    req = urllib.request.Request(f"{API}/rate_limit", headers={"Authorization": f"Bearer {token}", "User-Agent": "dong-ho"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            h = r.headers.get("github-authentication-token-expiration")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return datetime.now(timezone.utc)                      # đã hết hạn / bị thu hồi
        return None
    except (urllib.error.URLError, OSError):
        return None
    if not h:
        return None
    return doc_han(h)


def doc_han(h):
    """'2026-12-01 00:00:00 UTC' / '2026-12-01 00:00:00 -0800' → datetime (UTC) | None."""
    h = h.strip().replace(" UTC", " +0000")
    for dd in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            t = datetime.strptime(h, dd)
            return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def nhan_tele(noi_dung):
    tk, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tk or not chat:
        return False
    du_lieu = urllib.parse.urlencode({"chat_id": chat, "text": noi_dung}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{tk}/sendMessage", data=du_lieu, timeout=30).read()
        return True
    except (urllib.error.URLError, OSError):
        return False


REPO_KIN = "mihhle2006-beep/danh-muc"
WF_THU_QUYEN = "dnse_dong_bo.yml"


def _ma_http(token, phuong, duong):
    """Mã trạng thái HTTP của 1 lời gọi API GitHub bằng token (không đọc / in nội dung)."""
    req = urllib.request.Request(f"{API}/{duong}", method=phuong, data=b"" if phuong in ("PUT", "POST") else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "dong-ho"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError):
        return None


def kiem_quyen(token, repo=None, goi=None):
    """Token repo kín đủ quyền chưa? → {"doc_code", "doc_actions", "ghi_actions": True / False / None (lỗi mạng)}.
    Ghi Actions thử bằng PUT …/enable workflow vòng đồng bộ DNSE ĐANG bật (không đổi gì, cần Actions: Read and write)."""
    repo = repo or os.environ.get("DANH_MUC_REPO") or REPO_KIN
    goi = goi or (lambda ph, d: _ma_http(token, ph, d))
    thu = {"doc_code": ("GET", f"repos/{repo}/commits?per_page=1"),
           "doc_actions": ("GET", f"repos/{repo}/actions/workflows/{WF_THU_QUYEN}/runs?per_page=1"),
           "ghi_actions": ("PUT", f"repos/{repo}/actions/workflows/{WF_THU_QUYEN}/enable")}
    out = {}
    for k, (ph, d) in thu.items():
        m = goi(ph, d)
        out[k] = None if m is None else 200 <= m < 300
    return out


TEN_QUYEN = {"doc_code": "Contents (đọc / ghi danh mục)", "doc_actions": "Actions – đọc (tin 🩺 máy Mac)",
             "ghi_actions": "Actions – ghi (đồng hồ bật vòng DNSE 08:35)"}


def kiem_token(bay_gio, in_ra=print):
    """Token repo kín sắp / đã hết hạn hoặc thiếu quyền → Telegram (tên secret + ngày / quyền; không in token)."""
    canh = []
    tk = os.environ.get("DANH_MUC_TOKEN_GHI", "").strip()
    if tk:
        q = kiem_quyen(tk)
        thieu = [TEN_QUYEN[k] for k, v in q.items() if v is False]
        in_ra("Quyền DANH_MUC_TOKEN_GHI: " + " · ".join(f"{TEN_QUYEN[k]} {'OK' if v else 'THIẾU' if v is False else '?'}"
                                                         for k, v in q.items()))
        if thieu:
            canh.append("• DANH_MUC_TOKEN_GHI thiếu quyền: " + ", ".join(thieu)
                        + " → GitHub → Settings → Developer settings → Fine-grained tokens → token này → Edit → Add permissions")
    for ten in ("DANH_MUC_TOKEN_GHI",):
        h = han_token(os.environ.get(ten))
        if h is None:
            continue
        con = (h - bay_gio.astimezone(timezone.utc)).days
        in_ra(f"Token {ten}: hết hạn {h:%d/%m/%Y} (còn {con} ngày)")
        if con < TOKEN_CON_NGAY:
            canh.append(f"• {ten}: {'ĐÃ HẾT HẠN' if con < 0 else f'hết hạn {h:%d/%m/%Y} (còn {con} ngày)'}")
    if canh:
        nhan_tele("⚠ Token GitHub sắp / đã hết hạn – bot, bộ lọc, web sẽ ngừng khi hết:\n" + "\n".join(canh)
                  + "\n→ GitHub → Settings → Developer settings → Personal access tokens: tạo token mới (quyền như cũ), dán vào "
                    "canh-bao-mua → Settings → Secrets and variables → Actions (cùng tên).")
    return canh


def luot_khac_dang_chay(gh, run_id, cho=180, in_ra=print):
    """Lượt dong_ho CŨ HƠN còn chạy? Chờ ≤ cho giây (lượt cũ vừa gọi lượt này thì sắp xong) → True nếu vẫn còn."""
    het = time.time() + cho
    while True:
        try:
            ds = gh._goi("actions/workflows/dong_ho.yml/runs?status=in_progress&per_page=20").get("workflow_runs") or []
        except Exception as e:                                      # không đọc được → coi như không có (chạy trùng vô hại)
            in_ra(f"Không kiểm được đồng hồ khác ({type(e).__name__}) → chạy")
            return False
        cu = [r for r in ds if r.get("id") and run_id and int(r["id"]) < int(run_id)]
        if not cu:
            return False
        if time.time() >= het:
            in_ra(f"Đã có đồng hồ khác đang chạy (#{cu[0]['id']}) → thoát")
            return True
        time.sleep(15)


def main(argv=None):
    p = argparse.ArgumentParser(description="Đồng hồ gọi workflow đúng giờ VN")
    p.add_argument("--phut", type=float, default=340, help="chạy bao nhiêu phút rồi tự gọi lượt sau")
    p.add_argument("--thu", default="", help="'YYYY-MM-DD HH:MM' giờ VN: chỉ in workflow sẽ gọi (không gọi)")
    p.add_argument("--gac", default="", help="tên file workflow: job gac – in 'chay=true|false' (ghi vào GITHUB_OUTPUT)")
    p.add_argument("--lich", default="", help="với --gac: chuỗi cron GitHub của lần chạy (github.event.schedule)")
    p.add_argument("--kiem_quyen", action="store_true", help="thử quyền + hạn token DANH_MUC_TOKEN_GHI (chỉ in mã / kết quả)")
    a = p.parse_args(argv)
    if a.kiem_quyen:
        tk = os.environ.get("DANH_MUC_TOKEN_GHI", "").strip()
        if not tk:
            print("Thiếu secret DANH_MUC_TOKEN_GHI")
            return 1
        q = kiem_quyen(tk)
        for k, v in q.items():
            print(f"{'✔' if v else '✘' if v is False else '?'} {TEN_QUYEN[k]}: {'OK' if v else 'THIẾU QUYỀN' if v is False else 'lỗi mạng'}")
        h = han_token(tk)
        print(f"Hạn token: {f'{h:%d/%m/%Y}' if h else 'không hạn / không đọc được'}")
        return 0 if all(q.values()) else 1
    if a.gac:
        chay, ly_do = True, "không phải lịch → chạy"
        if a.lich:
            try:
                gh = GitHub(os.environ["GITHUB_REPOSITORY"], os.environ.get("GH_TOKEN", ""))
                chay, ly_do = gac(gh, a.gac, a.lich, datetime.now(timezone.utc), os.environ.get("GITHUB_RUN_ID"))
            except Exception as e:                                  # job gac không bao giờ chặn nhầm
                chay, ly_do = True, f"lỗi {type(e).__name__} → chạy"
        print(ly_do, file=sys.stderr)
        print(f"chay={'true' if chay else 'false'}")
        return 0
    if a.thu:
        t = datetime.strptime(a.thu, "%Y-%m-%d %H:%M").replace(tzinfo=VN)
        for wf, lich, inputs, tre in LICH:
            m = moc_gan_nhat(lich, t, tre)
            if m:
                print(f"{wf} {inputs or ''} – mốc {m:%H:%M}")
        return 0
    repo, run_id = os.environ["GITHUB_REPOSITORY"], os.environ.get("GITHUB_RUN_ID")
    gh = GitHub(repo, os.environ["GH_TOKEN"])
    if luot_khac_dang_chay(gh, run_id):
        return 0
    tk_dm = os.environ.get("DANH_MUC_TOKEN_GHI", "").strip()
    gh_khac = {"danh-muc": GitHub(os.environ.get("DANH_MUC_REPO") or "mihhle2006-beep/danh-muc", tk_dm)} if tk_dm else {}
    dh = DongHo(gh, gh_khac=gh_khac)
    gs = GiamSat(gh, datetime.now(timezone.utc) - timedelta(minutes=10))   # phủ khoảng nối giữa 2 lượt đồng hồ
    mac = MayMac(gh_khac["danh-muc"]) if gh_khac else None
    bat_dau, da_kiem, lan_gs = time.time(), None, 0.0
    print(f"Đồng hồ chạy {a.phut:.0f} phút, {len(LICH)} dòng lịch", flush=True)
    while time.time() - bat_dau < a.phut * 60:
        bay_gio = datetime.now(VN)
        try:
            dh.buoc(bay_gio)
            m = moc_gan_nhat(KIEM_TOKEN, bay_gio, 30)
            if m and m != da_kiem:
                da_kiem = m
                kiem_token(bay_gio)
            if time.time() - lan_gs >= GIAM_SAT_GIAY:
                lan_gs = time.time()
                gs.buoc()
                if mac:
                    try:
                        mac.buoc(bay_gio)
                    except urllib.error.HTTPError as e:            # token thiếu quyền Actions: Read → kiem_token báo 20:05
                        print(f"máy Mac: GitHub {e.code} – bỏ lượt")
        except Exception as e:                                      # lỗi lạ: in rồi chạy tiếp phút sau
            print(f"⚠ {type(e).__name__}: {str(e)[:100]}")
        sys.stdout.flush()
        time.sleep(max(5, 60 - datetime.now(VN).second + 3))
    for lan in range(4):                                            # gọi lượt sau: thử 4 lần (chuỗi đứt → lịch dự phòng)
        try:
            gh.goi("dong_ho.yml")
            print("Hết lượt → đã gọi lượt đồng hồ tiếp theo")
            break
        except Exception as e:
            print(f"::warning::Không gọi được lượt sau ({type(e).__name__} {str(e)[:80]})"
                  + (" – thử lại" if lan < 3 else " – lịch dự phòng 2 giờ / lần sẽ khởi động lại"))
            time.sleep(20 * (lan + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
