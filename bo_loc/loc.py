# -*- coding: utf-8 -*-
"""B1 – LỌC: chấm từng tiêu chí của chiến lược cho 1 mã, ghép bảng kết quả & xếp hạng."""
import pandas as pd

from . import cau_hinh as ch
from .tieu_chi import kiem_tra, ten_tieu_chi


def _ky_hieu(v):
    return "✔" if v else ("–" if v is None else "✘")


def danh_gia(m, cl, cl_ten=None, nghiem_ngat=None):
    """
    cl: ngưỡng áp cho mã này; cl_ten: chiến lược gốc để đặt tên cột (mọi mã chung cột).
    Trả về (kq từng tiêu chí, điểm, điểm tối đa, đạt bắt buộc?, danh sách thiếu, danh sách thiếu dữ liệu).
    """
    cl_ten = cl_ten or cl
    nghiem_ngat = ch.NGHIEM_NGAT if nghiem_ngat is None else nghiem_ngat
    kq, diem, toi_da, dat, thieu, thieu_dl = {}, 0, 0, True, [], []
    for nhom in ("bat_buoc", "cong_diem"):
        for k, t in cl.get(nhom, {}).items():
            v = kiem_tra(k, m, t)
            ten = ten_tieu_chi(k, cl_ten.get(nhom, {}).get(k, t))
            kq[ten] = _ky_hieu(v)
            if nhom == "bat_buoc":
                if v is None and not nghiem_ngat:
                    thieu_dl.append(ten)
                    continue
                toi_da += 2
                diem += 2 if v else 0
                if not v:
                    dat = False
                    thieu.append(ten + (" (thiếu dữ liệu)" if v is None else ""))
            else:
                toi_da += 1
                diem += 1 if v else 0

    tt = cl.get("toi_thieu")
    if tt:
        can, so_dat, so_thieu = tt["can_dat"], 0, 0
        for k, t in tt["tieu_chi"].items():
            v = kiem_tra(k, m, t)
            kq[ten_tieu_chi(k, t)] = _ky_hieu(v)
            so_dat += 1 if v else 0
            so_thieu += 1 if v is None else 0
            toi_da += 1
            diem += 1 if v else 0
        n_tc = len(tt["tieu_chi"])
        kq[f"Cơ bản đạt (cần {can}/{n_tc})"] = f"{so_dat}/{n_tc}"
        if so_dat < can:
            if so_dat + so_thieu >= can and not nghiem_ngat:
                thieu_dl.append(f"Cơ bản mới đạt {so_dat}/{can} (thiếu dữ liệu {so_thieu} tiêu chí)")
            else:
                dat = False
                thieu.append(f"Cơ bản chỉ đạt {so_dat}/{can} tiêu chí")
    return kq, diem, max(toi_da, 1), dat, thieu, thieu_dl


def nhan_dat(dat, thieu_dl, max_thieu=None):
    """✔ đạt đủ dữ liệu | ◐ đạt nhưng thiếu dữ liệu | ? thiếu quá nhiều | '' không đạt."""
    max_thieu = ch.MAX_TC_THIEU_DL if max_thieu is None else max_thieu
    if dat and len(thieu_dl) > max_thieu:
        return "?"
    if dat:
        return "✔" if not thieu_dl else "◐"
    return ""


def bang_ket_qua(ds_m, ds_dg, max_thieu=None):
    rows = []
    for m, (kq, diem, toi_da, dat, thieu, thieu_dl) in zip(ds_m, ds_dg):
        r = {k: v for k, v in m.items() if not k.startswith("_")}
        r.update({"Đạt lọc": nhan_dat(dat, thieu_dl, max_thieu), "Điểm": diem, "Điểm %": diem / toi_da * 100,
                  "Thiếu": "; ".join(thieu), "Thiếu dữ liệu": "; ".join(thieu_dl), "Số TC thiếu DL": len(thieu_dl)})
        r.update(kq)
        rows.append(r)
    b = pd.DataFrame(rows)
    b["_hang"] = b["Đạt lọc"].map({"✔": 0, "◐": 1, "?": 3}).fillna(2)
    b = b.sort_values(["_hang", "Số TC thiếu DL", "Điểm %", "upside"], ascending=[True, True, False, False])
    return b.drop(columns="_hang").reset_index(drop=True)


def gan_dat(b):
    """Mã chỉ thiếu đúng 1 tiêu chí bắt buộc."""
    return b[(~b["Đạt lọc"].isin(["✔", "◐"])) & (b["Thiếu"] != "") & (b["Thiếu"].str.count(";") == 0)]
