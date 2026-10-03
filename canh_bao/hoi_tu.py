# -*- coding: utf-8 -*-
"""
HỘI TỤ MỤC TIÊU GIÁ CÁC KỲ HẠN.
Ứng viên: mọi mốc của ptcp ở khung NGÀY (~3 tháng), khung TUẦN (~12 tháng), mục tiêu đề xuất của ptcp,
mục tiêu tự định giá (cấu hình) và mục tiêu tính nhanh của bộ cảnh báo.
Vùng hội tụ = cụm mốc lệch nhau ≤ NGUONG_HOI_TU % VÀ đến từ ≥ 2 KỲ HẠN khác nhau (mốc dự phòng "giá + k×ATR"
không được tính – chỉ mức giá kỹ thuật thật).
Mục tiêu chính = CẠNH DƯỚI của vùng hội tụ gần nhất phía trên giá (≥ +UPSIDE_TOI_THIEU %) – thận trọng.
Không có vùng hội tụ → giữ mục tiêu ngắn hạn.
"""
from . import cau_hinh as C


def vung_hoi_tu(ung_vien, gia):
    """ung_vien: [{"ky_han", "gia", "pp", ...}]. Trả danh sách vùng (thấp → cao) có ≥ 2 kỳ hạn."""
    # Mốc "dự phòng" (giá + k×ATR khi không có mốc kỹ thuật) không phải mức giá thật → không tính hội tụ
    tren = sorted([u for u in ung_vien if u.get("gia") and u["gia"] >= gia * (1 + C.UPSIDE_TOI_THIEU / 100)
                   and not str(u.get("pp", "")).startswith(("Biến động", "giá +"))], key=lambda u: u["gia"])
    vung, cum = [], []
    for u in tren:
        if cum and u["gia"] > cum[0]["gia"] * (1 + C.NGUONG_HOI_TU / 100):
            vung.append(cum)
            cum = []
        cum.append(u)
    if cum:
        vung.append(cum)
    out = []
    for c in vung:
        ky_han = sorted({u["ky_han"] for u in c})
        if len(ky_han) >= 2:
            out.append({"thap": c[0]["gia"], "cao": c[-1]["gia"], "giua": sum(u["gia"] for u in c) / len(c),
                        "ky_han": ky_han, "so_moc": len(c), "moc": c})
    return out


def muc_tieu_ky_han(ung_vien, gia):
    """Mốc GẦN NHẤT phía trên giá của từng kỳ hạn (để hiển thị)."""
    gan = {}
    for u in ung_vien:
        if u.get("gia") and u["gia"] >= gia * (1 + C.UPSIDE_TOI_THIEU / 100):
            if u["ky_han"] not in gan or u["gia"] < gan[u["ky_han"]]["gia"]:
                gan[u["ky_han"]] = u
    return list(gan.values())


def chon_muc_tieu(ung_vien, gia):
    """→ (giá mục tiêu, nguồn, vùng hội tụ hoặc None)."""
    v = vung_hoi_tu(ung_vien, gia)
    if v:
        z = v[0]
        return z["thap"], f"vùng hội tụ {len(z['ky_han'])} kỳ hạn {z['thap']:,.2f}–{z['cao']:,.2f}", z
    return None, "", None
