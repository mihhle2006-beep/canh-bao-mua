# -*- coding: utf-8 -*-
"""
GỬI FILE HTML KẾT QUẢ LỌC QUA TELEGRAM (tuỳ chọn "Gửi file HTML" khi bấm Run workflow "Quet dinh ky").
Mỗi chiến lược: thư mục mới nhất ket_qua_loc_<cl>_YYYYMMDD/chien_luoc_<cl>.html → gửi file (tên
'Bộ lọc <cl> dd-mm-yyyy.html').
  --chi_html : CHỈ gửi file, không kèm gì khác
  mặc định   : gửi tin danh sách mã MUA của chiến lược (ma_mua_bo_loc.json, mã ½ ghi '(½)') rồi gửi file
  --che_do   : ngoai (mặc định – bản gửi người ngoài, *_ngoai.html) | noi_bo (đủ chi tiết)
  python -m bo_loc.gui_html [--chien_luoc quy_b,xu_huong] [--chi_html] [--che_do ngoai|noi_bo] [--khong_gui]
"""
import argparse
import glob
import json
import os
import re
import sys

import requests


def tim_file(cl, goc=".", che_do="noi_bo"):
    """→ (đường dẫn HTML mới nhất của chiến lược, 'YYYYMMDD') hoặc (None, None)."""
    ds = []
    for tm in glob.glob(os.path.join(goc, f"ket_qua_loc_{cl}_*")):
        m = re.search(r"_(\d{8})$", tm)
        f = os.path.join(tm, f"chien_luoc_{cl}{'_ngoai' if che_do == 'ngoai' else ''}.html")
        if m and os.path.exists(f):
            ds.append((m.group(1), f))
    if not ds:
        return None, None
    ngay, f = max(ds)
    return f, ngay


TEN_CL = {"sieu_cp": "Siêu CP tiềm năng", "quy_b": "Quỹ B", "xu_huong": "Xu hướng", "ky_thuat": "Kỹ thuật", "diem_mua": "Điểm mua", "bat_day": "Bắt đáy",
          "gia_tri": "Giá trị", "tich_luy_vuot": "Tích lũy vượt", "tuy_chinh": "Tùy chỉnh"}


def ten_cl(cl):
    """Tên chiến lược hiển thị (không dấu "_")."""
    return TEN_CL.get(cl, cl.replace("_", " "))


def tin_ma_mua(cl, ngay, ds_ma):
    """Tin danh sách mã MUA của chiến lược (mã thăm dò ½ ghi '(½)')."""
    ma = [m for m, v in ds_ma.items() if any(x.split(" ")[0] == cl for x in v)]
    nua = [m for m in ma if f"{cl} ½" in ds_ma[m]]
    return (f"🔎 Bộ lọc {ten_cl(cl)} – phiên {ngay[6:]}/{ngay[4:6]}/{ngay[:4]}\n"
            + (f"MUA ({len(ma)}): " + ", ".join(f"{m}{' (½)' if m in nua else ''}" for m in ma) if ma
               else "Không có mã MUA"))


def tin_ptdttc(path="ptdttc_bo_loc.json"):
    """Tin mã PTĐTTC theo dõi riêng (quet_dinh_ky --chi_ptdttc ghi) – None nếu không có."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    ma = d.get("ma") or {}
    if not ma:
        return None
    return ("📌 PTĐTTC – theo dõi riêng (không vào danh sách MUA)\n"
            + "\n".join("\n".join([m] + [f"   {ten_cl(cl)}: {v['hanh_dong']}" for cl, v in kq.items()])
                        for m, kq in ma.items()))


def _tg():
    token, chat = os.environ.get("TELEGRAM_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat):
        print("⚠ Chưa đặt secret TELEGRAM_TOKEN / TELEGRAM_CHAT_ID → không gửi")
    return token, chat


def gui_tin(noi_dung):
    token, chat = _tg()
    if not (token and chat):
        return False
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat, "text": noi_dung},
                      timeout=60)
    if r.status_code != 200:
        print("Telegram lỗi:", r.status_code, r.text[:150])
    return r.status_code == 200


def gui_file(path, ten):
    token, chat = _tg()
    if not (token and chat):
        return False
    with open(path, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                          data={"chat_id": chat}, files={"document": (ten, f)}, timeout=120)
    if r.status_code != 200:
        print("Telegram lỗi:", r.status_code, r.text[:150])
    return r.status_code == 200


def main(argv=None):
    p = argparse.ArgumentParser(description="Gửi file HTML kết quả lọc qua Telegram")
    p.add_argument("--chien_luoc", default="quy_b,xu_huong")
    p.add_argument("--file_ma", default="ma_mua_bo_loc.json")
    p.add_argument("--chi_html", action="store_true", help="chỉ gửi file HTML, không kèm danh sách mã")
    p.add_argument("--che_do", default="ngoai", choices=["ngoai", "noi_bo"],
                   help="ngoai: bản gửi người ngoài (không khối lượng/NAV, điểm, tiêu chí) · noi_bo: đủ chi tiết")
    p.add_argument("--khong_gui", action="store_true")
    p.add_argument("--chi_ptdttc", action="store_true", help="chỉ gửi tin 📌 PTĐTTC (workflow kín ptdttc.yml)")
    a = p.parse_args(argv)
    if a.chi_ptdttc:
        t = tin_ptdttc()
        if t and not a.khong_gui:
            gui_tin(t)
        return 0
    try:
        with open(a.file_ma, encoding="utf-8") as f:
            ds_ma = json.load(f).get("ma") or {}
    except (OSError, ValueError):
        ds_ma = {}
    gui = 0
    for cl in [x.strip() for x in a.chien_luoc.split(",") if x.strip()]:
        f, ngay = tim_file(cl, che_do=a.che_do)
        if not f:
            print(f"⚠ {cl}: không có file HTML ({a.che_do})")
            continue
        ten = (f"Cổ phiếu đáng chú ý {ten_cl(cl)} {ngay[6:]}-{ngay[4:6]}-{ngay[:4]}.html" if a.che_do == "ngoai" else
               f"Bộ lọc {ten_cl(cl)} {ngay[6:]}-{ngay[4:6]}-{ngay[:4]}.html")
        print(f"{cl}: {f} → {ten}")
        if a.khong_gui:
            continue
        if not a.chi_html:
            gui_tin(tin_ma_mua(cl, ngay, ds_ma))
        if gui_file(f, ten):
            gui += 1
    return 0 if gui or a.khong_gui else 1


if __name__ == "__main__":
    sys.exit(main())
