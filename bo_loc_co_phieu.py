# -*- coding: utf-8 -*-
"""
Lối chạy tương thích bản cũ:  python bo_loc_co_phieu.py --nhom cang_bien
(tương đương  python -m bo_loc --nhom cang_bien). Mã nguồn thật nằm trong thư mục bo_loc/.

Code khác (VD bot canh_bao_mua) từng `import bo_loc_co_phieu` vẫn dùng được các tên cũ bên dưới.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bo_loc._cai_dat import dam_bao_thu_vien  # noqa: E402

dam_bao_thu_vien()
from bo_loc import chien_luoc as _cl  # noqa: E402
from bo_loc.cli import chay, main  # noqa: E402,F401
from bo_loc.danh_sach_ma import NHOM_MA, nhom_cua_ma  # noqa: E402,F401
from bo_loc.loc import bang_ket_qua, danh_gia  # noqa: E402,F401
from bo_loc.nguon import co_ban as _cb  # noqa: E402
from bo_loc.nguon.gia import tai_gia, tai_vnindex, tinh_beta  # noqa: E402,F401
from bo_loc.phan_tich.chi_so import tinh_chi_so  # noqa: E402,F401
from bo_loc.tieu_chi import TIEU_CHI, ten_tieu_chi  # noqa: E402,F401

CHIEN_LUOC = _cl.tai_tat_ca()
cac_tieu_chi = _cl.cac_tieu_chi


def lay_co_ban_online(ma):
    """Tên cũ: dữ liệu cơ bản online đã gộp nhiều nguồn."""
    return _cb.gop(_cb.lay_online(ma))


if __name__ == "__main__":
    main()
