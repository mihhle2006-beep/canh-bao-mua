# -*- coding: utf-8 -*-
"""GỬI THỬ 1 tin MUA có nút (canh_bao.yml ô thu_nut, rồi nghe bấm 15'): xem nút chọn số CP → tin xác nhận → ✅ → máy Mac →
kết quả sửa tại chỗ. Chỉ gửi NGOÀI giờ nhận lệnh (T2–T6 08:45–14:45): máy Mac trả "ngoài giờ – không đặt" → thử trọn đường
đi mà không có lệnh thật (nút trên tin > 3 giờ không nhận → sáng hôm sau bấm cũng không đặt)."""
import sys
from datetime import datetime

from .diem_vao import nut_chon
from .lenh_tele import VN
from .thong_bao import gui


def gui_thu(bay_gio=None):
    bg = bay_gio or datetime.now(VN)
    if bg.weekday() < 5 and 845 <= bg.hour * 100 + bg.minute <= 1445:
        print("Đang trong giờ nhận lệnh – không gửi tin thử (bấm ✅ sẽ đặt lệnh THẬT)")
        return 1
    nd = (f"🧪 TIN THỬ {bg:%H:%M %d/%m} – không phải tín hiệu; ngoài giờ nên máy Mac KHÔNG đặt lệnh\n"
          "MUA NGAY – VND 23,5 · ưu tiên ★1\n"
          "Đặt lệnh 23,5. Không đặt cao hơn 23,8\n"
          "Chứng khoán · Vùng mua 23,0 – 23,8 · Cắt lỗ 22,0 (−6,4%)\n"
          "Mục tiêu 1R 25,0 → 3R 28,0 · ≤5% NAV → 237 CP ≈ 5,6 tr")
    return 0 if gui(nd, rieng_tu=True, nut=nut_chon("VND", 237, 23_800)) else 1


if __name__ == "__main__":
    sys.exit(gui_thu())
