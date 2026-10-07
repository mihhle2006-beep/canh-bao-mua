# -*- coding: utf-8 -*-
"""
NHẬT KÝ & CHẤM ĐIỂM TÍN HIỆU CỦA BOT – phần GHI là của bot, phần CHẤM dùng CHUNG bộ máy ptcp/nhat_ky.py
(một cách chấm duy nhất cho Colab, danh-muc và bot).

Loại tín hiệu (cột `loai`):
  MUA_NGAY – tin MUA NGAY trong phiên → lệnh mua ở giá lúc báo, cắt lỗ / mục tiêu như trong tin.
  PTCP     – khuyến nghị cuối ngày của ptcp, ghi khi khuyến nghị của mã THAY ĐỔI. Nhóm MUA: mua giả định giá mở
             cửa phiên sau; nhóm CHỜ / ĐỨNG NGOÀI: ĐÚNG khi lệnh mua giả định đó lẽ ra lỗ, SAI khi lẽ ra lãi.
  BAN      – cảnh báo bán mã đang giữ (CAT_LO / BAN_TUAN / HET_HAN – hệ thoát mới; CHOT_LOI / CAN_NHAC_BAN – cách
             cũ; DOI_CAT_LO không chấm). ĐÚNG nếu sau KY_HAN_BAN phiên giá đóng cửa ≤ giá lúc báo.
Luật chấm (T+2, khoá trần/sàn, gap, phí + trượt giá) – xem ptcp/nhat_ky.py.

File:
  lich_su_danh_gia.csv                    – CÔNG KHAI (commit): chỉ mã theo dõi, chỉ MUA_NGAY / PTCP.
  cache_ptcp/lich_su_danh_gia_rieng.csv   – RIÊNG (actions/cache, không commit): cảnh báo BÁN + mã chỉ có trong
                                            danh mục. Không in chi tiết ra log Actions.
"""
import os

import numpy as np
import pandas as pd

from ptcp import nhat_ky as _nk
from ptcp.nhat_ky import (  # noqa: F401  – dùng lại & giữ tên cũ cho chay.py / test
    BO_QUA, CHO, CHUA_XONG, COT, DUNG, SAI, cham_ban, cham_dong, cham_lenh_mua, chi_phi, nhom_khuyen_nghi,
    thong_ke,
)

from . import cau_hinh as C

FILE_CONG_KHAI = "lich_su_danh_gia.csv"
FILE_RIENG = os.path.join("cache_ptcp", "lich_su_danh_gia_rieng.csv")
MUC_CHAM_BAN = ("CAT_LO", "BAN_TUAN", "HET_HAN", "CHOT_LOI", "CAN_NHAC_BAN")


def _path(rieng_tu):
    return FILE_RIENG if rieng_tu else FILE_CONG_KHAI


def doc(path):
    return _nk.doc(path)


def _so(x, n=2):
    try:
        x = float(x)
        return round(x, n) if x == x else np.nan
    except (TypeError, ValueError):
        return np.nan


def ghi_mua_ngay(kq, bay_gio, rieng_tu=False):
    t = pd.Timestamp(bay_gio)
    return _nk.them_dong({"id": f"MUA_NGAY|{kq['ma']}|{t:%Y-%m-%d %H:%M}", "thoi_diem": f"{t:%Y-%m-%d %H:%M}",
                          "ngay": f"{t:%Y-%m-%d}", "ma": kq["ma"], "loai": "MUA_NGAY", "khuyen_nghi": "MUA NGAY",
                          "nhom": "MUA", "san": "HOSE", "gia": _so(kq["gia"]), "cat_lo": _so(kq.get("cat_lo")),
                          "muc_tieu": _so(kq.get("muc_tieu")), "rr": _so(kq.get("rr")),
                          "ev": _so((kq.get("ptcp") or {}).get("ev")),
                          "ky_han": int((kq.get("ptcp") or {}).get("n_phien") or C.KY_HAN_MUA)}, _path(rieng_tu))


def ghi_ptcp(kq, bay_gio, rieng_tu=False):
    """Khuyến nghị ptcp cuối ngày (ghi khi THAY ĐỔI). Cắt lỗ / mục tiêu = mức bot đang dùng."""
    pt = kq.get("ptcp")
    if not pt or not pt.get("khuyen_nghi"):
        return False
    return _nk.ghi_khuyen_nghi(kq["ma"], pt.get("ngay_du_lieu") or pd.Timestamp(bay_gio), pt.get("gia") or kq["gia"],
                               pt["khuyen_nghi"], kq.get("cat_lo"), kq.get("muc_tieu"),
                               int(pt.get("n_phien") or C.KY_HAN_MUA), "HOSE", pt.get("ev"), kq.get("rr"),
                               loai="PTCP", path=_path(rieng_tu),
                               thoi_diem=f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}")


def ghi_ban(kq, kb, bay_gio):
    """Cảnh báo bán → luôn vào file RIÊNG."""
    if kb.get("muc") not in MUC_CHAM_BAN:
        return False
    t = pd.Timestamp(bay_gio)
    return _nk.them_dong({"id": f"BAN|{kq['ma']}|{kb['muc']}|{t:%Y-%m-%d}", "thoi_diem": f"{t:%Y-%m-%d %H:%M}",
                          "ngay": f"{t:%Y-%m-%d}", "ma": kq["ma"], "loai": "BAN", "khuyen_nghi": kb["muc"],
                          "nhom": "BÁN", "san": "HOSE", "gia": _so(kq["gia"]), "ky_han": C.KY_HAN_BAN}, FILE_RIENG)


def nhap_lich_su_cu(path_cu="lich_su_tin_hieu.csv"):
    """Lần đầu: chép các tin MUA NGAY đã gửi (lich_su_tin_hieu.csv) sang nhật ký để chấm luôn."""
    if not os.path.exists(path_cu) or os.path.exists(FILE_CONG_KHAI):
        return 0
    n = 0
    for _, r in pd.read_csv(path_cu, encoding="utf-8").iterrows():
        n += ghi_mua_ngay({"ma": r["ma"], "gia": r["gia"], "cat_lo": r["cat_lo"], "muc_tieu": r["muc_tieu"],
                           "rr": r.get("rr")}, r["thoi_diem"])
    return n


def cap_nhat(tai_gia, du_lieu_san=None, paths=(FILE_CONG_KHAI, FILE_RIENG)):
    """Chấm lại mọi dòng chưa có kết luận. Trả số dòng vừa có kết luận."""
    return _nk.cap_nhat(tai_gia, du_lieu_san, list(paths))


def dong_tong_ket(path=FILE_CONG_KHAI, tieu_de="📊 ĐỘ CHÍNH XÁC TÍN HIỆU"):
    return _nk.dong_thong_ke(doc(path), tieu_de)


def xuat_excel(path_xlsx="danh_gia_tin_hieu.xlsx", rieng=False):
    """Xuất nhật ký + thống kê (tông xanh). rieng=True: gồm cả file riêng – chỉ chạy trên máy."""
    return _nk.xuat_excel(path_xlsx, [FILE_CONG_KHAI] + ([FILE_RIENG] if rieng else []))
