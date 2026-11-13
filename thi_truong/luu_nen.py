# -*- coding: utf-8 -*-
"""
KHO NẾN 1' LÂU DÀI (người dùng 13/11/2026: lưu lâu hơn nguồn – DNSE chỉ giữ ~3 tháng nến phút; cache Actions có thể mất).
Release "nen-1p" của repo bang-thi-truong, mỗi tháng 1 file nen1_<YYYY-MM>.jsonl.gz – mỗi dòng 1 mã-ngày:
  {"ma": "FPT", "ngay": "2026-11-13", "t0": …, "dt": […], "c": […], "o": […], "h": […], "l": […], "v": […]}
  (mã hoá như phut_web.ma_hoa – giải bằng phut_web.giai_ma; 5' / 15' / 1 giờ gộp từ 1').
  • Chạy cuối job chiều của vòng bảng (bang.yml, sau 15:05): tải nến 1' hôm nay của mọi mã trong chuan_bi "vu" (HOSE + HNX +
    UPCoM đủ thanh khoản), gộp vào file tháng (cùng mã-ngày thì thay), tải lại lên Release (ghi đè).
  • Release chưa có file tháng nào → tải lùi LUI_DAU ngày (phần nguồn còn giữ) rồi chia theo tháng.
  • Nến 15' toàn sàn đã có kho bền riêng: Release nen-15p của canh-bao-mua (tai_nen_15p.yml).
"""
import argparse
import gzip
import json
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import phut_web

TAG = "nen-1p"
LUI_DAU = 100                                 # ngày tải lùi lần đầu (nguồn giữ ~3 tháng)
VN = timezone(timedelta(hours=7))


def ten_file(thang):
    return f"nen1_{thang}.jsonl.gz"


def chia_ngay(t, o, h, l_, c, v):
    """Nến 1' (t giây UTC) → {ngày giờ VN: dict gọn phut_web.ma_hoa}."""
    nhom = defaultdict(list)
    for i, ti in enumerate(t):
        if None in (o[i], h[i], l_[i], c[i]):
            continue
        nhom[datetime.fromtimestamp(int(ti), VN).strftime("%Y-%m-%d")].append(i)
    return {ng: phut_web.ma_hoa([t[i] for i in ix], [o[i] for i in ix], [h[i] for i in ix], [l_[i] for i in ix],
                                [c[i] for i in ix], [v[i] if i < len(v) else 0 for i in ix]) for ng, ix in nhom.items()}


def tai_nen(ds_ma, tu, den, luong=8, tai=None):
    """Nến 1' [tu, den] (giây UTC) mọi mã → {tháng: {(ngày, mã): dòng JSON}} – xử lý từng mã ngay khi tải xong (không giữ
    nến thô của mọi mã trong bộ nhớ). Mã lỗi / không có nến bỏ qua."""
    tai = tai or (lambda m, a, b: phut_web.tai(m, "1", a, b))
    out = defaultdict(dict)

    def mot(m):
        try:
            x = tai(m, tu, den)
        except Exception:                                               # noqa: BLE001
            return m, {}
        return m, (chia_ngay(*x) if x and x[0] else {})
    with ThreadPoolExecutor(luong) as ex:
        for m, theo_ngay in ex.map(mot, ds_ma):
            for ng, d in theo_ngay.items():
                out[ng[:7]][(ng, m)] = json.dumps({"ma": m, "ngay": ng, **d}, separators=(",", ":"))
    return out


def doc_thang(duong):
    """File tháng → {(ngày, mã): dòng JSON} (không có / hỏng → {})."""
    out = {}
    try:
        with gzip.open(duong, "rt", encoding="utf-8") as f:
            for dong in f:
                dong = dong.strip()
                if dong:
                    d = json.loads(dong)
                    out[(d["ngay"], d["ma"])] = dong
    except (OSError, ValueError, KeyError, EOFError):
        return {}
    return out


def ghi_thang(duong, dong):
    """Ghi {(ngày, mã): dòng} sắp theo ngày rồi mã."""
    with gzip.open(duong, "wt", encoding="utf-8", compresslevel=9) as f:
        for k in sorted(dong):
            f.write(dong[k] + "\n")


class Release:
    """Release TAG của repo qua gh CLI (GH_TOKEN)."""

    def __init__(self, repo, thu_muc):
        self.repo, self.d = repo, thu_muc
        os.makedirs(thu_muc, exist_ok=True)

    def _gh(self, *a, check=True):
        r = subprocess.run(["gh", *a, "-R", self.repo], capture_output=True, text=True, timeout=600)
        if check and r.returncode:
            raise RuntimeError(f"gh {a[0]} {a[1]} lỗi: {r.stderr.strip()[-200:]}")
        return r

    def ds_file(self):
        r = self._gh("release", "view", TAG, "--json", "assets", check=False)
        if r.returncode:
            return None                                                 # chưa có Release
        return [a["name"] for a in json.loads(r.stdout).get("assets") or []]

    def tai_ve(self, ten):
        p = os.path.join(self.d, ten)
        r = self._gh("release", "download", TAG, "-p", ten, "-D", self.d, "--clobber", check=False)
        return p if not r.returncode and os.path.exists(p) else None

    def dua_len(self, duong):
        if self.ds_file() is None:
            self._gh("release", "create", TAG, "--title", "Nến 1' lâu dài (mỗi tháng 1 file, tự cập nhật sau mỗi phiên)",
                     "--notes", "nen1_<YYYY-MM>.jsonl.gz – mỗi dòng 1 mã-ngày, mã hoá như canh-bao-mua thi_truong/phut_web.py "
                                "(giải: phut_web.giai_ma). Bản gốc: canh-bao-mua thi_truong/luu_nen.py.")
        self._gh("release", "upload", TAG, duong, "--clobber")


def luu(ds_ma, kho, bay_gio=None, lui=None, tai=None, in_ra=print):
    """Tải nến 1' hôm nay (lui ngày nếu kho chưa có file nào) → gộp vào file tháng trên Release. → số mã-ngày đã ghi."""
    bay_gio = bay_gio or datetime.now(VN)
    co = kho.ds_file()
    if lui is None:
        lui = LUI_DAU if not co else 0
    dau = (bay_gio - timedelta(days=lui)).replace(hour=0, minute=0, second=0, microsecond=0)
    moi = tai_nen(ds_ma, int(dau.timestamp()), int(bay_gio.timestamp()) + 60, tai=tai)
    tong = 0
    for thang, dong in sorted(moi.items()):
        ten = ten_file(thang)
        cu = doc_thang(kho.tai_ve(ten)) if co and ten in co else {}
        cu.update(dong)
        p = os.path.join(kho.d, ten)
        ghi_thang(p, cu)
        mb = os.path.getsize(p) / 1e6
        kho.dua_len(p)
        tong += len(dong)
        in_ra(f"{ten}: +{len(dong)} mã-ngày → {len(cu)} mã-ngày · {mb:.1f} MB")
    return tong


def main(argv=None):
    p = argparse.ArgumentParser(description="Kho nến 1' lâu dài (Release nen-1p)")
    p.add_argument("--repo", required=True)
    p.add_argument("--lui", type=int, default=None, help="tải lùi N ngày (mặc định: 0, kho trống → LUI_DAU)")
    p.add_argument("--sau_phien", action="store_true", help="chỉ chạy T2–T6 sau 15:05 giờ VN (cuối job chiều)")
    a = p.parse_args(argv)
    bay_gio = datetime.now(VN)
    if a.sau_phien and (bay_gio.weekday() >= 5 or bay_gio.hour * 60 + bay_gio.minute < 15 * 60 + 5):
        print(f"{bay_gio:%a %H:%M} – chưa hết phiên → không lưu kho nến 1'")
        return 0
    from . import dung
    cb = dung.doc_chuan_bi() or {}
    ds = list(cb.get("vu") or [])
    if not ds:
        print("Không có danh sách mã (chuan_bi.json) → bỏ qua")
        return 0
    kho = Release(a.repo, os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "kho_nen"))
    n = luu(ds, kho, bay_gio, a.lui)
    print(f"Kho nến 1': {n} mã-ngày ({len(ds)} mã)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
