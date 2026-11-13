# -*- coding: utf-8 -*-
"""
VÒNG BẢNG THỊ TRƯỜNG – chạy ở repo bang-thi-truong (workflow bang.yml, bản gốc bang_rieng/bang.yml), người dùng
13/11/2026: bảng cập nhật ≤ 1 phút, workflow chạy ở bang-thi-truong thay vì ~170 lượt / ngày ở canh-bao-mua.
  • 1 job / buổi (sáng 08:50–11:36, chiều 12:50–15:12 – đồng hồ canh-bao-mua gọi): nạp chuan_bi.json 1 lần (nhánh
    chuan-bi – canh-bao-mua đẩy sau lượt chuẩn bị 19:07), rồi mỗi CHU_KY giây trong giờ giao dịch: dung.chup() → nhánh
    "nhanh" p/<yyyymmdd>/<ô>.json (ô = giây trong ngày giờ VN // CHU_KY, mốc lúc chụp).
  • raw.githubusercontent.com cache 5' THEO ĐƯỜNG DẪN (bỏ qua ?t=) và cache cả 404 ~1' (đo 13/11/2026) → mỗi lượt 1 TÊN
    FILE MỚI; trang đọc ô (giờ máy − 25") – lượt đó đã đẩy xong – thiếu thì ô trước (trang_bang/index.html lay_o).
  • TRIEN_KHAI giây / lần + cuối buổi: nhánh du-lieu (trang + du_lieu.json) + gọi trien_khai.yml (Pages – bản nền khi mở
    trang, ngoài giờ giao dịch).
  • Mã đang giữ (mục 💼): đọc từ du_lieu.json nhánh du-lieu (canh-bao-mua đẩy kèm mỗi lượt của nó); tín hiệu bot: file
    trang_thai_chien_luoc.json của canh-bao-mua (lấy lại TRIEN_KHAI giây / lần). Không cần token repo kín.
Token: GITHUB_TOKEN của bang-thi-truong (contents + actions: write) – gửi qua header, không ghi vào URL / log.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

from . import dung, tinh

CHU_KY = 30                                   # giây / lượt chụp (chụp ~10–15 giây)
TRIEN_KHAI = 600                              # giây / lần cập nhật nhánh du-lieu + Pages
GIU_O = 12                                    # số file ô gần nhất giữ trên nhánh nhanh
CUA_SO = ((8 * 60 + 50, 11 * 60 + 36), (12 * 60 + 50, 15 * 60 + 12))      # phút trong ngày: job chạy trong khoảng này
GIO_GD = ((9 * 60, 11 * 60 + 31), (13 * 60, 15 * 60 + 5))                # chụp khi đang giao dịch
TRANG = ("index.html", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png")


def _phut(luc):
    return luc.hour * 60 + luc.minute


def cua_so(luc):
    """(đầu, cuối) phút của buổi chứa luc (T2–T6) | None."""
    if luc.weekday() >= 5:
        return None
    return next(((a, b) for a, b in CUA_SO if a <= _phut(luc) < b), None)


def dang_gd(luc):
    return luc.weekday() < 5 and any(a <= _phut(luc) < b for a, b in GIO_GD)


def o_cua(luc):
    """Ô CHU_KY giây trong ngày (giờ VN) của luc."""
    return (luc.hour * 3600 + luc.minute * 60 + luc.second) // CHU_KY


def ten_o(luc):
    return f"p/{luc:%Y%m%d}/{o_cua(luc):04d}.json"


def cho_toi_o_sau(luc):
    """Giây tới đầu ô kế tiếp + 1."""
    giay = luc.hour * 3600 + luc.minute * 60 + luc.second + luc.microsecond / 1e6
    return (o_cua(luc) + 1) * CHU_KY - giay + 1


class Git:
    """Đẩy 1 commit (ghi đè) lên 1 nhánh – mỗi nhánh 1 thư mục làm việc riêng; token qua http.extraheader."""

    def __init__(self, goc, repo, token, url=None):
        self.goc, self.url = goc, url or f"https://github.com/{repo}.git"
        self.hdr = "AUTHORIZATION: basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
        self.co = set()

    def _g(self, thu_muc, *a, check=True):
        r = subprocess.run(["git", "-c", f"http.extraheader={self.hdr}", "-C", thu_muc, *a], capture_output=True,
                           text=True, timeout=120)
        if check and r.returncode:
            raise RuntimeError(f"git {a[0]} lỗi {r.returncode}: {r.stderr.strip()[-200:]}")
        return r

    def thu_muc(self, nhanh):
        d = os.path.join(self.goc, nhanh)
        if not os.path.isdir(os.path.join(d, ".git")):
            os.makedirs(d, exist_ok=True)
            subprocess.run(["git", "init", "-q", "-b", nhanh, d], check=True, capture_output=True)
            for k, v in (("user.name", "github-actions[bot]"),
                         ("user.email", "41898283+github-actions[bot]@users.noreply.github.com")):
                subprocess.run(["git", "-C", d, "config", k, v], check=True, capture_output=True)
        return d

    def doc(self, nhanh, duong):
        """Nội dung 1 file trên nhánh (bản mới nhất ở GitHub) | None."""
        d = self.thu_muc("_doc")
        if self._g(d, "fetch", "-q", "--depth", "1", self.url, nhanh, check=False).returncode:
            return None
        r = self._g(d, "show", f"FETCH_HEAD:{duong}", check=False)
        return r.stdout if not r.returncode else None

    def day(self, nhanh, thong_diep):
        """Commit thư mục nhánh (ghi đè commit trước – nhánh chỉ 1 commit) + đẩy."""
        d = self.thu_muc(nhanh)
        self._g(d, "add", "-A")
        self._g(d, "commit", "-q", "--allow-empty", *(["--amend"] if nhanh in self.co else []), "-m", thong_diep)
        self.co.add(nhanh)
        self._g(d, "push", "-qf", self.url, f"HEAD:{nhanh}")


def don_o(thu_muc, giu=GIU_O):
    """Chỉ giữ giu file ô mới nhất trong <thu_muc>/p (thư mục ngày cũ xoá hẳn)."""
    goc = os.path.join(thu_muc, "p")
    if not os.path.isdir(goc):
        return
    ds = sorted((ngay, f) for ngay in os.listdir(goc) for f in os.listdir(os.path.join(goc, ngay)))
    for ngay, f in ds[:-giu] if giu else ds:
        os.remove(os.path.join(goc, ngay, f))
    for ngay in os.listdir(goc):
        if not os.listdir(os.path.join(goc, ngay)):
            os.rmdir(os.path.join(goc, ngay))


def ma_giu(du_lieu):
    """Mã đang giữ từ du_lieu.json (chuỗi JSON) nhánh du-lieu → list."""
    try:
        return [m for m in (json.loads(du_lieu or "{}").get("danh_muc") or []) if isinstance(m, str)]
    except ValueError:
        return []


def goi_trien_khai(repo, token, wf="trien_khai.yml"):
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{wf}/dispatches",
                                 data=json.dumps({"ref": "main"}).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status in (200, 204)


class XuatGit:
    """Nơi xuất của vòng (bản thật): nhánh nhanh / du-lieu của repo bang-thi-truong."""

    def __init__(self, repo, token, goc, trang="trang_bang", file_giu=None):
        self.repo, self.token, self.trang, self.file_giu = repo, token, trang, file_giu
        self.git = Git(goc, repo, token)

    def lam_moi(self):
        """Mã đang giữ (nhánh du-lieu) → file MA_GIU_FILE; trang_thai_chien_luoc.json + trang mới nhất của canh-bao-mua."""
        ds = ma_giu(self.git.doc("du-lieu", "du_lieu.json"))
        if ds and self.file_giu:
            with open(self.file_giu, "w", encoding="utf-8") as f:
                f.write(",".join(ds))
        r = subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "main"], capture_output=True, timeout=120)
        if not r.returncode:
            subprocess.run(["git", "checkout", "-q", "FETCH_HEAD", "--", dung.FILE_CHIEN_LUOC, self.trang],
                           capture_output=True, timeout=60)
        return len(ds)

    def nhanh(self, ten, du_lieu):
        d = self.git.thu_muc("nhanh")
        os.makedirs(os.path.dirname(os.path.join(d, ten)), exist_ok=True)
        with open(os.path.join(d, ten), "w", encoding="utf-8") as f:
            f.write(du_lieu)
        don_o(d)
        self.git.day("nhanh", f"Bảng {ten}")

    def nen(self, file_du_lieu):
        d = self.git.thu_muc("du-lieu")
        for t in TRANG:
            if os.path.exists(os.path.join(self.trang, t)):
                shutil.copy(os.path.join(self.trang, t), d)
        with open(os.path.join(d, "index.html"), encoding="utf-8") as f:
            h = f.read()
        with open(os.path.join(self.trang, "index.html"), "rb") as f:
            ban = hashlib.sha1(f.read()).hexdigest()[:10]
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(h.replace("__BAN__", ban))
        shutil.copy(file_du_lieu, os.path.join(d, "du_lieu.json"))
        self.git.day("du-lieu", f"Bảng thị trường {tinh.gio_vn():%Y-%m-%d %H:%M}")
        return goi_trien_khai(self.repo, self.token)


def vong(cb, xuat, file_ra, luc_fn=tinh.gio_vn, ngu=time.sleep, chup=None, so_luot=0, in_ra=print):
    """so_luot > 0: chạy thử đúng so_luot lượt bất kể giờ (rồi cập nhật nền). → (số lượt chụp được, số lượt lỗi)."""
    chup = chup or dung.chup
    luot = loi = 0
    lan_nen, chot = None, False
    in_ra(f"Mã đang giữ: {xuat.lam_moi()} mã")
    while True:
        luc = luc_fn()
        if so_luot:
            if luot + loi >= so_luot:
                break
        else:
            cs = cua_so(luc)
            if cs is None:
                break
            if not dang_gd(luc):
                if _phut(luc) >= 15 * 60 + 5 and not chot:          # chốt phiên (ATC, thoả thuận) – 1 lượt rồi thôi
                    chot = True
                else:
                    ngu(min(60.0, max(1.0, (cs[1] - _phut(luc)) * 60.0)))
                    continue
        t0 = time.monotonic()
        try:
            out = chup(cb, file_ra, luc=luc, in_tien_do=lambda *_: None)
            xuat.nhanh(ten_o(luc), json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=dung._mac_dinh))
            luot += 1
        except Exception as e:                                          # noqa: BLE001 – 1 lượt lỗi, lượt sau chạy tiếp
            loi += 1
            in_ra(f"⚠ lượt {luc:%H:%M:%S}: {type(e).__name__}: {str(e)[:150]}")
        if luot and luot % 20 == 0:
            in_ra(f"{luc:%H:%M:%S} · {luot} lượt · lỗi {loi} · lượt này {time.monotonic() - t0:.1f}s")
        if chot or (so_luot and luot + loi >= so_luot):
            break
        if lan_nen is None or (luc - lan_nen).total_seconds() >= TRIEN_KHAI:
            lan_nen = luc
            _nen(xuat, file_ra, in_ra)
        ngu(cho_toi_o_sau(luc_fn()))
    if luot:                                                            # cuối buổi / chốt phiên: bản nền mới nhất
        _nen(xuat, file_ra, in_ra)
    return luot, loi


def _nen(xuat, file_ra, in_ra):
    try:
        xuat.lam_moi()
        if os.path.exists(file_ra):
            xuat.nen(file_ra)
    except Exception as e:                                              # noqa: BLE001
        in_ra(f"⚠ cập nhật trang (Pages): {type(e).__name__}: {str(e)[:150]}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Vòng bảng thị trường (repo bang-thi-truong)")
    p.add_argument("--repo", required=True)
    p.add_argument("--so_luot", type=int, default=0, help="chạy thử N lượt bất kể giờ")
    p.add_argument("--goc", default=os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "bang_git"))
    a = p.parse_args(argv)
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        print("Thiếu GH_TOKEN")
        return 1
    luc = tinh.gio_vn()
    if not a.so_luot and cua_so(luc) is None:
        print(f"{luc:%H:%M} ngoài khung chạy (sáng 08:50–11:36, chiều 12:50–15:12, T2–T6) → thoát")
        return 0
    file_giu = os.path.join(os.path.dirname(a.goc), "ma_giu.txt")
    os.environ["MA_GIU_FILE"] = file_giu
    xuat = XuatGit(a.repo, token, a.goc, file_giu=file_giu)
    os.makedirs(dung.THU_MUC_CACHE, exist_ok=True)
    cb_json = xuat.git.doc("chuan-bi", "chuan_bi.json")
    if cb_json:
        with open(dung.FILE_CB, "w", encoding="utf-8") as f:
            f.write(cb_json)
    cb = dung.doc_chuan_bi()
    if cb is None:
        print("Chưa có chuan_bi.json (nhánh chuan-bi) → tự dựng")
        cb = dung.chuan_bi()
    print(f"Dữ liệu chuẩn bị: {cb.get('tao_luc')} · {len(cb.get('vu') or [])} mã lọc")
    ra = os.path.join(os.path.dirname(a.goc), "ra", "du_lieu.json")
    os.makedirs(os.path.dirname(ra), exist_ok=True)
    luot, loi = vong(cb, xuat, ra, so_luot=a.so_luot)
    print(f"Xong: {luot} lượt chụp · {loi} lượt lỗi")
    return 0 if luot or not loi else 1


if __name__ == "__main__":
    sys.exit(main())
