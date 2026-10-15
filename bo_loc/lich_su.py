# -*- coding: utf-8 -*-
"""Lưu kết quả lọc theo ngày → báo mã MỚI LỌT / RỜI KHỎI so với lần lọc trước (cùng chiến lược)."""
import os

import pandas as pd

from . import cau_hinh as ch


def ghi_lich_su(ngay_du_lieu, chien_luoc, dat, file=None):
    file = file or ch.FILE_LICH_SU
    ngay = str(pd.Timestamp(ngay_du_lieu).date())
    moi = pd.DataFrame({"ngay": ngay, "chien_luoc": chien_luoc, "ma": dat["Mã"].values,
                        "diem": dat["Điểm %"].round(1).values, "trang_thai": dat["Đạt lọc"].values}).astype(str)
    cu = pd.read_csv(file, dtype=str) if os.path.exists(file) else pd.DataFrame(columns=moi.columns, dtype=str)
    cu = cu[~((cu["ngay"] == ngay) & (cu["chien_luoc"] == chien_luoc))]      # chạy lại cùng ngày → ghi đè
    truoc = cu[(cu["chien_luoc"] == chien_luoc) & (cu["ngay"] < ngay)]
    ngay_truoc = truoc["ngay"].max() if len(truoc) else None
    ma_truoc = set(truoc.loc[truoc["ngay"] == ngay_truoc, "ma"]) if ngay_truoc else set()
    pd.concat([cu, moi]).to_csv(file, index=False, encoding="utf-8-sig")
    ma_nay = set(moi["ma"])
    return ngay_truoc, sorted(ma_nay - ma_truoc), sorted(ma_truoc - ma_nay), sorted(ma_nay & ma_truoc)
