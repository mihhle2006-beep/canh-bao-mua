# -*- coding: utf-8 -*-
"""
Chạy danh mục KHÔNG HỎI rồi gửi tóm tắt qua Telegram (dùng cho GitHub Actions hoặc lịch chạy trên máy).
Biến môi trường:
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID   – bỏ trống thì chỉ in ra màn hình
  TIEN_MAT (triệu đồng, mặc định 8), GIU_TIEN_MAT (% – bỏ trống = tự động theo VN-Index), CHON (gmv | max_sharpe),
  NHAT_KY (đường dẫn nhật ký giao dịch, tuỳ chọn)
"""
import os
import re
import subprocess
import sys

import requests


def phan(out, tieu_de):
    """Lấy nội dung 1 mục của báo cáo (từ dòng tiêu đề tới đường kẻ / mục kế tiếp)."""
    m = re.search(rf"{tieu_de}[^\n]*\n-+\n(.*?)(?=\n-{{20,}}|\n#{{20,}}|\n ▶|\Z)", out, re.S)
    return m.group(1).strip() if m else ""


def gui(noi_dung):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    print(noi_dung)
    if not (token and chat):
        print("\n(Chưa đặt TELEGRAM_TOKEN / TELEGRAM_CHAT_ID → không gửi)")
        return
    for i in range(0, len(noi_dung), 3900):                     # Telegram tối đa 4096 ký tự / tin
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat.strip(), "text": noi_dung[i:i + 3900]}, timeout=30)
        if r.status_code != 200:
            print(f"Gửi Telegram lỗi: {r.status_code} {r.text[:200]}")
            if "chat not found" in r.text:
                print("→ TELEGRAM_CHAT_ID sai, hoặc bạn CHƯA bấm Start với bot. Lấy lại id: nhắn bot 1 tin rồi mở "
                      "https://api.telegram.org/bot<TOKEN>/getUpdates, dùng số sau \"chat\":{\"id\":")
            break


def main():
    # Gọi thẳng hàm main của dmuc thay vì file "danh_muc.py": tên file có dấu bị macOS lưu dạng Unicode khác
    # (NFD) khi upload lên GitHub → Linux không tìm thấy file. Cách này không phụ thuộc tên file.
    lenh = [sys.executable, "-m", "dmuc.chuong_trinh",
            "--khong_ve",
            "--tien_mat", os.environ.get("TIEN_MAT") or "8",
            "--chon", os.environ.get("CHON") or "gmv"]
    if os.environ.get("GIU_TIEN_MAT"):                          # bỏ trống = % tiền mặt TỰ ĐỘNG theo VN-Index
        lenh += ["--giu_tien_mat", os.environ["GIU_TIEN_MAT"]]
    if os.environ.get("NHAT_KY") and os.path.exists(os.environ["NHAT_KY"]):
        lenh += ["--nhat_ky", os.environ["NHAT_KY"]]
    p = subprocess.run(lenh, capture_output=True, text=True, timeout=3300)
    out = p.stdout + ("\n" + p.stderr if p.stderr else "")
    print(out)
    if p.returncode != 0 or "❌" in out or "Traceback" in out:
        gui("❌ DANH MỤC – LỖI KHI CHẠY\n\n" + out[-3500:])
        sys.exit(1)
    thay_doi = re.search(r" ▶ THAY ĐỔI HÀNH ĐỘNG.*?(?=\n\n|\Z)", out, re.S)
    tin = ["📊 DANH MỤC – " + (re.search(r"ket_qua_danh_muc_(\d{8})", out) or [None, ""])[1],
           "", "▶ HÀNH ĐỘNG", phan(out, "HÀNH ĐỘNG ĐỀ XUẤT"),
           "", "▶ NHẬN XÉT", phan(out, "NHẬN XÉT DANH MỤC")]
    if thay_doi:
        tin += ["", thay_doi.group(0).strip()]
    gui("\n".join(tin))


if __name__ == "__main__":
    main()
