# -*- coding: utf-8 -*-
"""Đọc log ket_qua_log.txt của lần chạy danh mục → gửi Telegram: tóm tắt + ảnh dashboard + file Excel."""
import glob
import os
import re
import sys

import requests

log = open("ket_qua_log.txt", encoding="utf-8", errors="replace").read()
token = os.environ.get("TELEGRAM_TOKEN", "").strip()
chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
API = f"https://api.telegram.org/bot{token}"


def phan(tieu_de):
    m = re.search(rf"{tieu_de}[^\n]*\n-+\n(.*?)(?=\n-{{20,}}|\n#{{20,}}|\n={{20,}}|\n ▶|\n\n  ✔|\Z)", log, re.S)
    return m.group(1).strip() if m else ""


def gui_tin(noi_dung):
    print(noi_dung)
    if not (token and chat):
        return
    for i in range(0, len(noi_dung), 3900):
        r = requests.post(f"{API}/sendMessage", data={"chat_id": chat, "text": noi_dung[i:i + 3900]}, timeout=30)
        if r.status_code != 200:
            print("Telegram lỗi:", r.text[:200])


def gui_file(duong_dan, kieu, chu_thich=""):
    if not (token and chat and os.path.exists(duong_dan)):
        return
    with open(duong_dan, "rb") as f:
        r = requests.post(f"{API}/send{kieu.capitalize()}", data={"chat_id": chat, "caption": chu_thich},
                          files={kieu: f}, timeout=60)
    if r.status_code != 200:
        print(f"Gửi {duong_dan} lỗi:", r.text[:200])


hanh_dong = phan("HÀNH ĐỘNG ĐỀ XUẤT")
# Coi là LỖI nếu không có mục HÀNH ĐỘNG (chương trình dừng giữa chừng, kể cả khi không có Traceback)
ok = bool(hanh_dong) and "Traceback" not in log

if not ok:
    gui_tin("❌ DANH MỤC – LỖI / KHÔNG CÓ KẾT QUẢ\n\n" + (log[-3000:] or "(log trống – chương trình không chạy)"))
    sys.exit(1)

ngay = (re.search(r"ket_qua_danh_muc_(\d{8})", log) or [None, ""])[1]
ngay = f"{ngay[6:8]}/{ngay[4:6]}/{ngay[:4]}" if ngay else ""
tt = re.search(r"→ (VN-Index [^\n]*)", log)
msg = [f"📊 DANH MỤC – {ngay}"]
if tt:
    msg += ["", "🌐 " + tt.group(1)]
msg += ["", "▶ HÀNH ĐỘNG", hanh_dong]
dc = phan("ĐIỀU CHỈNH CẮT LỖ / CHỐT LỜI")
if dc:
    msg += ["", "▶ CẮT LỖ / CHỐT LỜI", dc]
msg += ["", "▶ NHẬN XÉT", phan("NHẬN XÉT DANH MỤC")]
td = re.search(r" ▶ THAY ĐỔI HÀNH ĐỘNG.*?(?=\n\n|\Z)", log, re.S)
if td:
    msg += ["", td.group(0).strip()]
gui_tin("\n".join(msg))

thu_muc = sorted(glob.glob("ket_qua_danh_muc_*"))
if thu_muc:
    tm = thu_muc[-1]
    gui_file(os.path.join(tm, "dashboard_danh_muc.png"), "photo", "Dashboard danh mục")
    gui_file(os.path.join(tm, "markowitz.png"), "photo", "Markowitz")
    gui_file(os.path.join(tm, "danh_muc_tong_hop.xlsx"), "document", "Báo cáo Excel đầy đủ")
