# -*- coding: utf-8 -*-
"""GHÉP 4 KHUNG → TRẠNG THÁI của từng mã (thứ tự phủ quyết: Tuần → Ngày → Giờ → Phút → R/R → thị trường)."""
import numpy as np
import pandas as pd

from . import cau_hinh as C
from .du_lieu import bo_nen_chua_dong, gop_tuan, trong_phien
from .tieu_chi import khung_gio, khung_ngay, khung_phut, khung_tuan, muc_gia

MUA_NGAY = "MUA NGAY"


def xac_suat(dn, gia, mt, lo, H):
    """
    XS lịch sử (mô phỏng của ptcp: mua giá mở cửa phiên sau, bán từ T+2, trần/sàn, phí) tại GIÁ HIỆN TẠI với ĐÚNG
    mục tiêu & cắt lỗ của tin: chạm MỤC TIÊU trước / chạm CẮT LỖ trước / không chạm (H phiên), EV sau phí.
    """
    if dn is None or not all(x == x and x is not None for x in (gia, mt, lo)) or not (lo < gia < mt):
        return None
    try:
        from ptcp.thong_ke import danh_gia_muc
        xs_mt, t_mt, ev, xs_cl = danh_gia_muc(dn, gia, mt, lo, int(H))
    except Exception:
        return None
    if xs_mt != xs_mt:
        return None
    return {"muc_tieu": xs_mt, "phien_muc_tieu": t_mt, "cat_lo": xs_cl, "ngang": max(0.0, 100 - xs_mt - xs_cl),
            "ev": ev, "H": int(H)}


def _muc_ptcp(pt, gia, atr):
    """Cắt lỗ & mục tiêu của ptcp, chỉnh theo giá phút hiện tại. Trả (cắt lỗ, mục tiêu, nguồn) hoặc None."""
    if not pt or not pt.get("cat_lo"):
        return None
    lo = pt["cat_lo"]
    if gia - lo < C.STOP_ATR_MIN * (pt.get("atr") or atr):         # giá đã chạy lên → giữ khoảng cách tối thiểu
        lo = gia - C.STOP_ATR_MIN * (pt.get("atr") or atr)
    # Ưu tiên mục tiêu KHUNG NGÀY của ptcp (cùng kỳ hạn ~63 phiên với xác suất); mục tiêu 12 tháng chỉ để dự phòng
    for g, nguon in ((pt.get("muc_tieu_ngay"), f"ptcp: {pt.get('pp_muc_tieu_ngay', '')}"),
                     (pt.get("muc_tieu"), f"ptcp 12 tháng: {pt.get('moc_muc_tieu', '')}")):
        if g and g >= gia * (1 + C.UPSIDE_TOI_THIEU / 100):
            return lo, g, nguon
    return lo, None, ""


def phan_tich_ma(ma, dn, dh, dp, vni, tt, bay_gio, pt=None):
    """pt: kết quả ptcp_ngay.phan_tich_ngay (có thể None)."""
    bay_gio = pd.Timestamp(bay_gio)
    dang_phien = trong_phien(bay_gio)
    nen_chay = bool(dang_phien and dn is not None and len(dn) and dn.index[-1].normalize() == bay_gio.normalize())
    kt = khung_tuan(gop_tuan(dn, bay_gio) if dn is not None else None)
    kn = khung_ngay(dn, vni, nen_chay)
    kg = khung_gio(bo_nen_chua_dong(dh, "60", bay_gio))
    kp = khung_phut(bo_nen_chua_dong(dp, C.KHUNG_PHUT, bay_gio))
    gia = kp.get("gia") or kn.get("gia") or np.nan
    lo = mt = rr = np.nan
    nguon_mt = ""
    mp = None
    if "gia" in kn:
        lo, mt, nguon_mt, rr = muc_gia(kn)
        mp = _muc_ptcp(pt, gia if gia == gia else kn["gia"], kn["atr"]) if C.DUNG_PTCP else None
        if mp:                                                   # ưu tiên cắt lỗ / mục tiêu của ptcp
            lo = mp[0]
            if mp[1]:
                mt, nguon_mt = mp[1], mp[2]
            rr = (mt - gia) / (gia - lo) if gia == gia and gia > lo else rr
        if gia == gia and gia != kn["gia"] and not mp:           # giá phút mới nhất khác giá ngày
            if gia - lo < C.STOP_ATR_MIN * kn["atr"]:              # giữ khoảng cách cắt lỗ tối thiểu 1.5×ATR
                lo = gia - C.STOP_ATR_MIN * kn["atr"]
            rr = (mt - gia) / (gia - lo) if gia > lo else np.nan
    xs = xac_suat(dn, gia, mt, lo, (pt or {}).get("n_phien", C.SO_PHIEN_XAC_SUAT))
    phut_hom_nay = "nen" in kp and pd.Timestamp(kp["nen"]).normalize() == bay_gio.normalize()

    if not kt["dat"]:
        tt_ma, ly_do = "ĐỨNG NGOÀI", "khung TUẦN phủ quyết: " + ", ".join(kt["truot"])
    elif not kn["dat"]:
        thieu = kn["truot"] + ([f"điểm cộng {kn['diem']}/{kn['tong_diem']} < {kn['diem_can']}"]
                               if kn["diem"] < kn["diem_can"] else [])
        tt_ma, ly_do = "THEO DÕI", "khung NGÀY chưa đạt: " + ", ".join(thieu)
    elif not kg["dat"]:
        tt_ma, ly_do = "CHỜ XÁC NHẬN GIỜ", "khung GIỜ chưa đạt: " + ", ".join(kg["truot"])
    elif not kp["dat"]:
        tt_ma, ly_do = "CHỜ ĐIỂM VÀO", f"khung {C.KHUNG_PHUT} PHÚT chưa có điểm vào: " + ", ".join(kp["truot"])
    elif not (rr == rr and rr >= C.RR_TOI_THIEU):
        tt_ma, ly_do = "ĐỦ TÍN HIỆU – R/R THẤP", f"R/R {rr:.2f} < {C.RR_TOI_THIEU:g} (mục tiêu gần)"
    elif C.DUNG_PTCP and pt and pt.get("chan_su_kien"):
        tt_ma, ly_do = "CHỜ SAU SỰ KIỆN", "ptcp: " + ", ".join(pt.get("su_kien", []))
    elif C.DUNG_PTCP and pt and not (pt.get("ev") is not None and pt["ev"] >= C.EV_NGUONG):
        tt_ma, ly_do = "ĐỦ TÍN HIỆU – EV THẤP", (f"ptcp: EV sau phí {pt['ev']:+.2f}% < {C.EV_NGUONG:g}% – "
                                                 f"chưa có lợi thế thống kê" if pt.get("ev") is not None
                                                 else "ptcp: thiếu EV")
    elif C.DUNG_PTCP and C.YEU_CAU_PTCP_MUA and pt and not str(pt.get("khuyen_nghi", "")).startswith("MUA"):
        tt_ma, ly_do = "ĐỦ TÍN HIỆU – ptcp CHƯA MUA", f"ptcp: {pt['khuyen_nghi']} – {pt.get('hanh_dong', '')}"
    elif tt.get("tot") is False and C.CHAN_KHI_THI_TRUONG_XAU:
        tt_ma, ly_do = "ĐỦ TÍN HIỆU – THỊ TRƯỜNG XẤU", tt["nhan"]
    elif not (dang_phien and phut_hom_nay):
        tt_ma, ly_do = "ĐẠT CUỐI PHIÊN", "đủ 4 khung khi đóng cửa → xem xét mua đầu phiên sau nếu tín hiệu còn"
    else:
        tt_ma, ly_do = MUA_NGAY, "đủ 4 khung: " + (kp.get("kich_hoat") or "")
    return {"ma": ma, "gia": gia, "trang_thai": tt_ma, "ly_do": ly_do, "mua_ngay": tt_ma == MUA_NGAY,
            "khung": [kt, kn, kg, kp], "cat_lo": lo, "muc_tieu": mt, "nguon_mt": nguon_mt, "rr": rr,
            "nen_phut": kp.get("nen"), "thi_truong": tt, "ptcp": pt, "xac_suat": xs}
