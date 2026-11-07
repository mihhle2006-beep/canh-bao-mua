# -*- coding: utf-8 -*-
"""
DỮ LIỆU "HỆ THỐNG" CHO MỤC "ĐỌC BIỂU ĐỒ" CỦA TRANG BIỂU ĐỒ (docs/ma/doc_bd.js) – chạy trong workflow "Du lieu tra cuu":
  • he_thong.json : từng mã – đạt / chưa đạt các điều kiện chọn mã của Quỹ Bứt Phá (danh-muc ptcp/loc_quy_b.json, ngưỡng
                    đọc thẳng từ ptcp/cau_hinh.py): trong rổ thanh khoản tuần, RS 3 tháng không quá nóng, không thuộc nhóm
                    biến động mạnh nhất, định giá (đắt → giảm khối lượng), 4 dấu hiệu MẠNH; + chiến lược Bo_Loc hôm nay.
  • tin_hieu/<MÃ>.json : các lần bot đã báo (lich_su_danh_gia.csv – vốn công khai trong repo) kèm kết quả.
  python -m thi_truong.he_thong_web --ra docs/ma/du_lieu --loc danh-muc/ptcp/loc_quy_b.json --cau_hinh danh-muc/ptcp/cau_hinh.py
"""
import argparse
import csv
import json
import os
import re
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
NGUONG_MAC = {"QUY_TOP_GTGD": 100, "QUY_RS3T_NONG": 90.0, "QUY_BO_BIEN_DONG_PCT": 30.0, "QUY_DAT_NGUONG_PCT": -20.0,
              "QUY_MANH_DINH_PCT": -3.0, "QUY_MANH_RS3T": 70.0, "QUY_MANH_TK": 1.5, "QUY_MANH_SO_DAU_HIEU": 3}
COT_TH = ("ngay", "loai", "khuyen_nghi", "nhom", "gia", "cat_lo", "muc_tieu", "ket_qua", "ket_qua_pct", "giai_thich",
          "ngay_ket_thuc", "gia_ket_thuc", "so_phien", "vung_tu", "vung_den")


def nguong(duong):
    """Ngưỡng luật từ ptcp/cau_hinh.py (đọc chữ – không import vì file tự cài thư viện); thiếu → mặc định."""
    out = dict(NGUONG_MAC)
    try:
        txt = open(duong, encoding="utf-8").read()
    except (OSError, TypeError):
        return out
    for k in out:
        m = re.search(rf"^{k}\s*=\s*(-?[\d.]+)", txt, re.M)
        if m:
            out[k] = type(out[k])(float(m[1]))
    return out


def he_thong(loc, ng, bo_loc=None):
    """loc: loc_quy_b.json · ng: nguong() · bo_loc: ma_mua_bo_loc.json → dict he_thong.json (mỗi mã 1 mảng gọn)."""
    ro = set((loc.get("ro_tuan") or {}).get("ma") or [])
    hang = {m: i + 1 for i, m in enumerate((loc.get("ro_tuan") or {}).get("ma") or [])}
    g = lambda k, m: (loc.get(k) or {}).get(m)                                         # noqa: E731
    ma = {}
    for m in set(loc.get("hang_gtgd") or {}) | ro:
        ma[m] = [hang.get(m), g("hang_gtgd", m), g("gtgd", m), g("hang_rs3t", m), g("bien_dong_hang", m), g("dinh_gia", m),
                 g("cach_dinh_52t", m), g("tk_tang", m), g("rs_nganh", m), g("dinh_52t_3t", m)]
    return {"cap_nhat": datetime.now(VN).strftime("%H:%M %d/%m/%Y"), "ngay_gia": loc.get("ngay_gia"),
            "ro_ngay_chot": (loc.get("ro_tuan") or {}).get("ngay_chot"), "nguong": ng,
            "cot": ["hang_ro_tuan", "hang_gtgd", "gtgd", "hang_rs3t", "bien_dong_hang", "dinh_gia", "cach_dinh_52t", "tk_tang",
                    "rs_nganh", "dinh_52t_3t"],
            "ma": ma, "bo_loc": (bo_loc or {}).get("ma") or {}, "bo_loc_phien": (bo_loc or {}).get("phien")}


def lich_su_tin_hieu(duong):
    """lich_su_danh_gia.csv → {mã: [dict gọn…]} (cũ → mới)."""
    out = {}
    try:
        with open(duong, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                m = (r.get("ma") or "").strip().upper()
                if m:
                    out.setdefault(m, []).append({k: (r.get(k) or "").strip() for k in COT_TH})
    except OSError:
        return {}
    for m in out:
        out[m].sort(key=lambda x: x["ngay"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dữ liệu hệ thống cho mục Đọc biểu đồ")
    ap.add_argument("--ra", default="docs/ma/du_lieu")
    ap.add_argument("--loc", default="danh-muc/ptcp/loc_quy_b.json")
    ap.add_argument("--cau_hinh", default="danh-muc/ptcp/cau_hinh.py")
    ap.add_argument("--bo_loc", default="ma_mua_bo_loc.json")
    ap.add_argument("--lich_su", default="lich_su_danh_gia.csv")
    a = ap.parse_args(argv)
    try:
        loc = json.load(open(a.loc, encoding="utf-8"))
    except (OSError, ValueError):
        loc = {}
    try:
        bl = json.load(open(a.bo_loc, encoding="utf-8"))
    except (OSError, ValueError):
        bl = {}
    os.makedirs(a.ra, exist_ok=True)
    d = he_thong(loc, nguong(a.cau_hinh), bl)
    with open(os.path.join(a.ra, "he_thong.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    th = lich_su_tin_hieu(a.lich_su)
    os.makedirs(os.path.join(a.ra, "tin_hieu"), exist_ok=True)
    for m, ds in th.items():
        with open(os.path.join(a.ra, "tin_hieu", f"{m}.json"), "w", encoding="utf-8") as f:
            json.dump(ds, f, ensure_ascii=False, separators=(",", ":"))
    print(f"he_thong.json: {len(d['ma'])} mã · tín hiệu bot: {len(th)} mã")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
