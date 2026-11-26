# -*- coding: utf-8 -*-
"""
ĐÊM QUA → PHIÊN SÁNG: tin trước phiên khi hàng hoá / chứng khoán Mỹ biến động MẠNH đêm qua (chốt sau giờ VN đóng cửa).
Số đo ở thi_truong/vi_mo_nguon vòng 14 (26/11/2026, giá ngày 2012–2026, tiêu chí đặt trước): biến động đêm qua tương quan rõ
với cổ phiếu ngành phiên sau (dầu → dầu khí +0,26, S&P 500 → VN-Index +0,23, đường → SBT/LSS/QNS +0,17, than → TVD/NBC +0,16
giai đoạn 2020–2026) nhưng phần lớn đã nằm ở giá MỞ CỬA; riêng đường còn chạy tiếp trong phiên. Thép, đồng, cao su, urê, heo:
không có tác động. CHỈ LÀ THÔNG TIN – không đổi lệnh.
"""
import pandas as pd

# (tên, nguồn vi_mo_web._lay, nhóm VN, điều thường xảy ra phiên sau – kiểm 2020–2026, ngày biến động > 2 độ lệch)
DEM = [("Dầu Brent", "yf:BZ=F", "GAS, PVS, PVD, BSR, PLX", "thường lệch VN-Index ~1% cùng chiều – chủ yếu ngay lúc mở cửa"),
       ("Đường", "yf:SB=F", "SBT, LSS, QNS", "thường đi cùng chiều, cả trong phiên (~0,4%/phiên)"),
       ("Than Newcastle", "tv:ICEEUR:NCF1!", "TVD, NBC", "thường lệch VN-Index ~1% cùng chiều"),
       ("S&P 500", "yf:^GSPC", "VN-Index", "thường mở cửa cùng chiều (~0,4%), từ 2020 hay đảo chiều trong phiên"),
       ("VIX", "yf:^VIX", "VN-Index", "đi NGƯỢC chiều VIX (~0,4%)"),
       ("Chỉ số USD", "yf:DX-Y.NYB", "VN-Index", "đi NGƯỢC chiều USD (~0,3%)")]


def bien_dong(s, hom_nay, nguong=2.0, han_ngay=5):
    """Giá đóng cửa theo ngày sàn → (lợi suất %, z, ngày) của phiên gần nhất TRƯỚC hôm nay nếu |z| > nguong, không thì None.
    z = lợi suất / độ lệch 60 phiên trước đó. Bỏ nến của chính hôm nay (sàn châu Á / Globex mở phiên mới trước 08:00 giờ VN)."""
    hom_nay = pd.Timestamp(hom_nay).normalize()
    s = pd.Series(s, dtype=float).dropna()
    s = s[s.index < hom_nay]
    if len(s) < 62 or (hom_nay - s.index[-1]).days > han_ngay:
        return None
    r = s.pct_change().dropna()
    z = r.iloc[-1] / r.iloc[-61:-1].std()
    return (round(float(r.iloc[-1]) * 100, 2), round(float(z), 1), s.index[-1]) if abs(z) > nguong else None


def tin(chuoi, hom_nay):
    """chuoi: {tên: Series giá đóng cửa} → nội dung tin (rỗng khi không có biến động mạnh)."""
    dong = []
    for ten, _, nhom, cau in DEM:
        x = bien_dong(chuoi.get(ten), hom_nay) if chuoi.get(ten) is not None else None
        if x:
            dong.append(f"• <b>{ten} {x[0]:+.1f}%</b> (mạnh, {x[1]:+.1f} độ lệch, phiên {x[2]:%d/%m}) → {nhom}: {cau}")
    return ("🌙 <b>Đêm qua biến động mạnh</b>\n" + "\n".join(dong) +
            "\n<i>Đo 2012–2026: phần lớn đã vào giá mở cửa – thông tin, không phải lệnh.</i>") if dong else ""


def lay_tat_ca(hom_nay):
    """Tải chuỗi ~1 năm cho DEM (nguồn lỗi → bỏ qua)."""
    from thi_truong.vi_mo_web import _lay
    tu = f"{pd.Timestamp(hom_nay) - pd.Timedelta(days=400):%Y-%m-%d}"
    out = {}
    for ten, ng, *_ in DEM:
        try:
            out[ten] = _lay(ng, tu)
        except Exception as e:                                       # noqa: BLE001 – thiếu 1 nguồn không chặn tin
            print(f"⚠ Đêm qua – {ten}: {type(e).__name__}")
    return out
