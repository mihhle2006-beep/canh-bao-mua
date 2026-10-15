# -*- coding: utf-8 -*-
"""
QUÉT ĐỊNH KỲ cho bot canh-bao-mua – chạy cuối MỖI PHIÊN T2–T6 (workflow quet_dinh_ky.yml):
  chạy lần lượt các chiến lược (mặc định quy_b, xu_huong) → lấy mã có Hành động = "MUA"
  + 2 mã đầu (điểm cao nhất) của nhóm "MUA THĂM DÒ (½ vị thế)" mỗi chiến lược
  → ghi ma_mua_bo_loc.json. Bot canh-bao-mua đọc file này, theo dõi mỗi mã 4 phiên kế tiếp (lọc lại / đạt điểm mua thì tính lại) rồi tự xoá.

  python -m bo_loc.quet_dinh_ky                              (quy_b + xu_huong, nhóm mặc định)
  python -m bo_loc.quet_dinh_ky --chien_luoc quy_b --nhom vn30 --file ma_mua_bo_loc.json
"""
import argparse
import json
import os
import sys

import pandas as pd

CHIEN_LUOC_QUET = ("quy_b", "xu_huong")
FILE_KET_QUA = "ma_mua_bo_loc.json"
HANH_DONG_LAY = ("MUA",)
THAM_DO = "MUA THĂM DÒ (½ vị thế)"
SO_MA_THAM_DO = 2                  # mỗi chiến lược lấy thêm 2 mã đầu (điểm tổng cao nhất) của nhóm MUA THĂM DÒ


def ma_mua_nhom(kq, so_tham_do=SO_MA_THAM_DO):
    """
    Kết quả chay() → {mã: "MUA" | "½"}: mã có Hành động MUA + `so_tham_do` mã đầu nhóm MUA THĂM DÒ (½) – bảng đánh giá
    đã xếp theo hành động rồi điểm tổng giảm dần, nên "mã đầu" = điểm cao nhất.
    """
    e = (kq or {}).get("danh_gia")
    if e is None or not len(e) or "Hành động" not in e.columns:
        return {}
    out = {str(m).upper(): "MUA" for m in e.loc[e["Hành động"].isin(HANH_DONG_LAY), "Mã"]}
    for m in list(e.loc[e["Hành động"] == THAM_DO, "Mã"])[:max(0, so_tham_do)]:
        out.setdefault(str(m).upper(), "½")
    return out


def ma_mua(kq, so_tham_do=SO_MA_THAM_DO):
    return list(ma_mua_nhom(kq, so_tham_do))


def quet(ds_cl=CHIEN_LUOC_QUET, them_argv=(), chay=None):
    """→ ({mã: [chiến lược...]}, {chiến lược: lỗi}, phiên dữ liệu mới nhất | None)."""
    if chay is None:
        from .cli import chay
    gop, loi, phien = {}, {}, None
    for cl in ds_cl:
        try:
            kq = chay(["--chien_luoc", cl, "--khong_bieu_do", *them_argv])
        except (Exception, SystemExit) as e:                # 1 chiến lược lỗi không bỏ cả lần quét
            loi[cl] = f"{type(e).__name__}: {str(e)[:200]}"
            continue
        if kq is None:
            loi[cl] = "không có kết quả"
            continue
        b = kq.get("bang")
        ngay = _phien(kq)
        if ngay and (phien is None or ngay > phien):
            phien = ngay
        for m, nhom in ma_mua_nhom(kq).items():               # mã thăm dò ghi "<chiến lược> ½"
            gop.setdefault(m, []).append(cl if nhom == "MUA" else f"{cl} ½")
        print(f"  → {cl}: {sum(cl in v for v in gop.values())} mã MUA, {sum(f'{cl} ½' in v for v in gop.values())} mã ½"
              + (f" / {len(b)} mã phân tích" if b is not None else ""))
    return gop, loi, phien


def _phien(kq):
    """Phiên dữ liệu: lấy từ tên thư mục kết quả (ket_qua_loc_<cl>_YYYYMMDD)."""
    tm = os.path.basename(str(kq.get("thu_muc") or ""))
    so = tm.rsplit("_", 1)[-1]
    return f"{so[:4]}-{so[4:6]}-{so[6:]}" if len(so) == 8 and so.isdigit() else None


def ghi(gop, loi, phien, path=FILE_KET_QUA, bay_gio=None, ds_cl=CHIEN_LUOC_QUET):
    from .cli import gio_viet_nam
    bay_gio = pd.Timestamp(bay_gio) if bay_gio is not None else pd.Timestamp(gio_viet_nam()).tz_localize(None)
    du_lieu = {"ngay_quet": f"{bay_gio:%Y-%m-%d}", "luc": f"{bay_gio:%Y-%m-%d %H:%M}", "phien": phien,
               "chien_luoc": list(ds_cl), "ma": {m: gop[m] for m in sorted(gop)}, "loi": loi}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=1)
    return du_lieu


def main(argv=None):
    p = argparse.ArgumentParser(description="Quét định kỳ → danh sách mã MUA cho bot canh-bao-mua")
    p.add_argument("--chien_luoc", default=",".join(CHIEN_LUOC_QUET), help="VD quy_b,xu_huong")
    p.add_argument("--file", default=FILE_KET_QUA)
    a, them = p.parse_known_args(argv)                     # tham số còn lại chuyển nguyên cho bộ lọc (VD --nhom vn30)
    ds_cl = [x.strip() for x in a.chien_luoc.split(",") if x.strip()]
    gop, loi, phien = quet(ds_cl, them)
    if len(loi) == len(ds_cl):                             # mọi chiến lược đều lỗi → giữ file cũ, báo đỏ
        for cl, l in loi.items():
            print(f"  ⚠ {cl}: {l}")
        return 1
    ghi(gop, loi, phien, a.file, ds_cl=ds_cl)
    print(f"\n✔ {len(gop)} mã MUA ({', '.join(gop) or '–'}) → {a.file}")
    for cl, l in loi.items():
        print(f"  ⚠ {cl}: {l}")
    return 0


if __name__ == "__main__":
    from ._cai_dat import dam_bao_thu_vien
    dam_bao_thu_vien()
    sys.exit(main())
