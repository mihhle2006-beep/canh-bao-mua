# -*- coding: utf-8 -*-
import argparse
import sys

from . import dung


def main(argv=None):
    p = argparse.ArgumentParser(description="Bảng thị trường → docs/thi_truong/du_lieu.json")
    p.add_argument("--chuan_bi", action="store_true", help="dựng lại dữ liệu chuẩn bị (sau phiên) rồi chụp")
    p.add_argument("--ra", default=dung.FILE_RA)
    p.add_argument("--cache", default=dung.FILE_CB)
    p.add_argument("--tu_trang", default="", help="lượt đổi code ngoài giờ: lấy dữ liệu thị trường từ trang (địa chỉ "
                   "thư mục thi_truong/ trên Pages), không gọi nguồn; lỗi → dựng như thường")
    a = p.parse_args(argv)
    if a.tu_trang and not a.chuan_bi:
        try:
            dung.dung_lai_trang(a.tu_trang, a.ra)
            return 0
        except (OSError, ValueError) as e:
            print(f"::warning::không lấy được dữ liệu từ trang ({str(e)[:80]}) → dựng từ nguồn")
    cb = None if a.chuan_bi else dung.doc_chuan_bi(a.cache)
    if cb is None:
        cb = dung.chuan_bi(a.cache)
    dung.chup(cb, a.ra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
