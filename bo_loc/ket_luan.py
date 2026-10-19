# -*- coding: utf-8 -*-
"""
KẾT LUẬN – tóm tắt cuối cùng bằng lời cho dễ đọc:
  [NÊN MUA]            : đạt lọc, điểm cao, R/R tốt, không cờ đỏ → kế hoạch đầy đủ
  [MUA CÓ ĐIỀU KIỆN]   : thăm dò ½ vị thế / chờ giá chỉnh về vùng mua
  [THEO DÕI]           : cổ phiếu khá nhưng còn thiếu điều kiện → nêu rõ cần chờ gì
  [LOẠI]               : chỉ đếm số lượng
"""
import numpy as np
import pandas as pd

from . import cau_hinh as ch
from .tien_ich import co

NHOM_KET_LUAN = {
    "MUA": "[NÊN MUA]",
    "MUA KHI CHỈNH VỀ VÙNG MUA": "[MUA CÓ ĐIỀU KIỆN]",
    "MUA THĂM DÒ (½ vị thế)": "[MUA CÓ ĐIỀU KIỆN]",
    "CHỜ NHỊP CHỈNH": "[MUA CÓ ĐIỀU KIỆN]",
    "THEO DÕI": "[THEO DÕI]",
    "THEO DÕI – có cờ đỏ": "[THEO DÕI]",
    "LOẠI": "[LOẠI]",
}
THU_TU_NHOM = ["[NÊN MUA]", "[MUA CÓ ĐIỀU KIỆN]", "[THEO DÕI]", "[LOẠI]"]
TEN_TRU_COT = {"Xu hướng": "xu hướng", "Động lượng": "động lượng", "Định giá": "định giá",
               "Chất lượng": "chất lượng DN", "Rủi ro": "mức rủi ro"}


def _chu(x):
    return x if isinstance(x, str) else ""


def _so(x, le=2):
    return "–" if not co(x) else f"{x:,.{le}f}"          # đổi sang kiểu VN ở đầu ra (so.vn_hoa)


def vi_sao(r):
    """Điểm mạnh / yếu theo trụ cột (≥ 70 mạnh, < 40 yếu; trụ cột Rủi ro: điểm cao = ít rủi ro)."""
    manh, yeu = [], []
    for k, ten in TEN_TRU_COT.items():
        v = r.get(k)
        if not co(v):
            continue
        if v >= 70:
            manh.append(("rủi ro thấp" if k == "Rủi ro" else f"{ten} tốt") + f" ({v:.0f})")
        elif v < 40:
            yeu.append(("rủi ro cao" if k == "Rủi ro" else f"{ten} yếu") + f" ({v:.0f})")
    return manh, yeu


def dieu_kien_cho(r):
    """Cần thêm gì để mã chuyển lên mua."""
    dk = []
    nhom = r.get("nhom_cl")
    nhom = nhom if isinstance(nhom, str) and nhom else None
    if nhom:                                               # theo chiến lược thị trường (cùng bot)
        if nhom == "CHO":
            dk.append(f"giá về vùng chờ {r.get('vung_mua')} rồi có phiên tăng lại, hoặc tín hiệu MACD mới")
        elif nhom == "CHO_TIN_HIEU":
            dk.append(r.get("dat_diem_mua") or "chờ MACD ngày cắt lên")
        elif nhom == "DUOI_VON":
            dk.append("hệ thống đang lỗ – chờ giá vượt lại giá vào của hệ thống hoặc tín hiệu mới")
        elif nhom == "BAN":
            dk.append("hệ thống sắp bán (gãy MA10 tuần) – chờ tín hiệu mới")
        elif r.get("Hành động") == "THEO DÕI" and r.get("Đạt lọc") not in ("✔", "◐"):
            dk.append(f"có nhóm {r.get('ten_nhom_cl')} nhưng chưa đạt lọc của chiến lược đang chạy")
    if r.get("Hành động") in ("MUA KHI CHỈNH VỀ VÙNG MUA", "CHỜ NHỊP CHỈNH") and not nhom:
        dk.append(f"giá chỉnh về vùng mua {r.get('vung_mua')} (đang quá mua / xa MA20)")
    for t in [x.strip() for x in str(r.get("Thiếu tiêu chí lọc") or "").split(";") if x.strip()]:
        dk.append(f"đạt thêm tiêu chí: {t}")
    for c in [x.strip() for x in str(r.get("Cờ đỏ (nặng)") or "").split(";") if x.strip()]:
        if c.startswith("Dưới SuperTrend") and co(r.get("SuperTrend")):
            dk.append(f"giá đóng cửa vượt lại SuperTrend ({_so(r['SuperTrend'])})")
        elif c.startswith("Đã thủng hỗ trợ"):
            dk.append("giá lấy lại đường hỗ trợ đã thủng")
        else:
            dk.append(f"hết cờ đỏ: {c}")
    if not nhom and co(r.get("Điểm tổng")) and r["Điểm tổng"] < ch.NGUONG_HANH_DONG["mua"] and not dk:
        dk.append(f"điểm tổng lên ≥ {ch.NGUONG_HANH_DONG['mua']} (hiện {r['Điểm tổng']:.0f})")
    if co(r.get("rr_kh")) and r["rr_kh"] < 2:
        dk.append(f"R/R ≥ 2 (hiện {_so(r['rr_kh'], 1)}) – chờ giá về gần vùng mua hơn")
    return dk


def _ly_do_loai(r):
    if r.get("Cờ đỏ (nặng)"):
        return "có cờ đỏ"
    if r.get("Đạt lọc") not in ("✔", "◐") and str(r.get("Thiếu tiêu chí lọc") or "").count(";") >= 1:
        return "không khớp chiến lược (thiếu ≥ 2 tiêu chí)"
    return "điểm tổng thấp"


def lap_ket_luan(e):
    """Bảng kết luận (1 dòng/mã) – dùng in ra & xuất sheet 'Ket luan'."""
    rows = []
    for _, r in e.iterrows():
        nhom = NHOM_KET_LUAN.get(r["Hành động"], "[LOẠI]")
        manh, yeu = vi_sao(r)
        so_cp = r["so_cp_kh"]
        if r["Hành động"] == "MUA THĂM DÒ (½ vị thế)":
            so_cp = int(so_cp / 2 // 100 * 100)
        ty_le = so_cp / r["so_cp_kh"] if r["so_cp_kh"] else 0
        lai = (r["muc_tieu_kh"] / r["Giá"] - 1) * 100 if co(r["muc_tieu_kh"]) else np.nan
        rows.append({
            "Kết luận": nhom, "Mã": r["Mã"], "Hành động": r["Hành động"], "Điểm tổng": r["Điểm tổng"],
            "Đạt lọc": r["Đạt lọc"], "Giá": r["Giá"], "Vùng mua": r["vung_mua"], "Đặt LO": r.get("gia_lo", np.nan),
            "Cắt lỗ": r["cat_lo_kh"], "Cắt lỗ %": -r["kc_cat_lo"], "Mục tiêu": r["muc_tieu_kh"],
            "Mục tiêu %": lai, "R/R": r["rr_kh"], "MT 3R": r.get("muc_tieu_3r", np.nan),
            "Nhóm chiến lược": _chu(r.get("ten_nhom_cl")), "Đạt điểm mua": _chu(r.get("dat_diem_mua")),
            "Vô hiệu khi": _chu(r.get("vo_hieu")), "Số CP": so_cp, "Giá trị (tr)": r["gia_tri_kh"] * ty_le,
            "% NAV": r["ty_trong_kh"] * ty_le,
            "Điểm mạnh": ", ".join(manh), "Điểm yếu": ", ".join(yeu),
            "Rủi ro / lưu ý": "; ".join(x for x in (r["Cờ đỏ (nặng)"], r["Lưu ý (nhẹ)"]) if x),
            "Cần chờ": "; ".join(dieu_kien_cho(r)) if nhom in ("[THEO DÕI]", "[MUA CÓ ĐIỀU KIỆN]") else "",
            "Lý do loại": _ly_do_loai(r) if nhom == "[LOẠI]" else "",
        })
    k = pd.DataFrame(rows)
    if k.empty:
        return k
    k["_t"] = k["Kết luận"].map({n: i for i, n in enumerate(THU_TU_NHOM)})
    return k.sort_values(["_t", "Điểm tổng"], ascending=[True, False]).drop(columns="_t").reset_index(drop=True)


def _ke_hoach(r):
    if co(r.get("MT 3R")):                                 # theo chiến lược thị trường
        lo = (f"đặt LO {_so(r['Đặt LO'])} (chưa khớp → ATC chỉ khi là mã ★ của tin tổng kết) · "
              if co(r.get("Đặt LO")) else "")
        return (f"mua {r['Vùng mua']} · {lo}cắt lỗ {_so(r['Cắt lỗ'])} ({_so(r['Cắt lỗ %'], 1)}%) · "
                f"Mục tiêu tạm thời 1R {_so(r['Mục tiêu'])} → 3R {_so(r['MT 3R'])} · bán theo hệ thoát (không chốt cứng)")
    return (f"mua {r['Vùng mua']} · cắt lỗ {_so(r['Cắt lỗ'])} ({_so(r['Cắt lỗ %'], 1)}%) · "
            f"mục tiêu {_so(r['Mục tiêu'])} (+{_so(r['Mục tiêu %'], 1)}%) · R/R {_so(r['R/R'], 1)}")


def _mau_nhom(nhom):
    from .mau import mo, vang, xanh
    return {"[NÊN MUA]": xanh, "[MUA CÓ ĐIỀU KIỆN]": vang, "[LOẠI]": mo}.get(nhom, lambda x: x)(nhom)


def in_ket_luan(k, von_trieu, so_theo_doi=10, thieu_co_ban=False, dong_tt=None):
    from .mau import xanh, xanh_nhat
    print("\n" + xanh_nhat("═" * 100) + "\n " + xanh("KẾT LUẬN") + "\n" + xanh_nhat("═" * 100))
    if dong_tt:
        print(f"  {dong_tt}")
    if k.empty:
        print("  Không có mã nào để kết luận.")
        return
    dem = k["Kết luận"].value_counts()
    print("  " + " | ".join(f"{_mau_nhom(n)}: {dem.get(n, 0)} mã" for n in THU_TU_NHOM))

    for nhom in ("[NÊN MUA]", "[MUA CÓ ĐIỀU KIỆN]"):
        ds = k[k["Kết luận"] == nhom]
        if ds.empty:
            continue
        print(f"\n {_mau_nhom(nhom)}")
        for _, r in ds.iterrows():
            hd = "" if nhom == "[NÊN MUA]" else f" – {r['Hành động'].lower()}"
            nhom_cl = f" · {r['Nhóm chiến lược']}" if isinstance(r.get("Nhóm chiến lược"), str) and r["Nhóm chiến lược"] else ""
            print(f"\n  ▸ {r['Mã']}{hd}{nhom_cl}  (điểm {r['Điểm tổng']:.0f}, giá {_so(r['Giá'])})")
            print(f"     Kế hoạch  : {_ke_hoach(r)}")
            if isinstance(r.get("Đạt điểm mua"), str) and r["Đạt điểm mua"]:
                print(f"     Điểm mua  : {r['Đạt điểm mua']}")
            if isinstance(r.get("Vô hiệu khi"), str) and r["Vô hiệu khi"]:
                print(f"     Vô hiệu   : {r['Vô hiệu khi']}")
            print(f"     Khối lượng: {_so(r['Số CP'], 0)} CP ≈ {_so(r['Giá trị (tr)'], 1)} triệu "
                  f"({_so(r['% NAV'], 1)}% của NAV {_so(von_trieu, 0)} triệu)")
            if r["Điểm mạnh"]:
                print(f"     Vì sao    : {r['Điểm mạnh']}")
            if r["Rủi ro / lưu ý"] or r["Điểm yếu"]:
                print(f"     Lưu ý     : {'; '.join(x for x in (r['Điểm yếu'], r['Rủi ro / lưu ý']) if x)}")
            if r["Cần chờ"]:
                print(f"     Chờ       : {r['Cần chờ']}")

    ds = k[k["Kết luận"] == "[THEO DÕI]"]
    if len(ds):
        print(f"\n [THEO DÕI] chưa mua, cần chờ thêm điều kiện (top {min(so_theo_doi, len(ds))}/{len(ds)})")
        for _, r in ds.head(so_theo_doi).iterrows():
            print(f"  ▸ {r['Mã']:<4} điểm {r['Điểm tổng']:.0f} │ chờ: {r['Cần chờ'] or 'tín hiệu rõ hơn'}")

    loai = k[k["Kết luận"] == "[LOẠI]"]
    if len(loai):
        ly_do = loai["Lý do loại"].value_counts()
        print(f"\n [LOẠI] {len(loai)} mã – " + ", ".join(f"{n} {ld}" for ld, n in ly_do.items())
              + " (chi tiết: sheet 'Ket luan')")

    if (k["Kết luận"] == "[NÊN MUA]").sum() == 0:
        print("\n  → Hôm nay KHÔNG có mã đủ điều kiện mua ngay. Ưu tiên theo dõi nhóm [MUA CÓ ĐIỀU KIỆN]/[THEO DÕI] ở trên.")
    if thieu_co_ban:
        print("  ⓘ Lần chạy này chưa có dữ liệu cơ bản nên trụ cột 'Chất lượng' chưa được chấm "
              "(thêm \"--luon_lay_co_ban\").")
    print("  ⓘ Kết quả dựa trên dữ liệu quá khứ – tham khảo, không phải khuyến nghị đầu tư.")
