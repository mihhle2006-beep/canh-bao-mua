# -*- coding: utf-8 -*-
"""
HIỆU QUẢ BỘ LỌC (27/10/2026) – mã MUA của quét định kỳ (ma_mua_bo_loc.json) sau 20 / 60 phiên có hơn VN-Index không.
  • Mỗi lần quét định kỳ: ghi_lich_su → lich_su_ma_mua_bo_loc.csv (phiên, mã, chiến lược · "quy_b" / "xu_huong ½" …),
    chạy lại cùng phiên thì ghi đè. Danh sách này vốn đã công khai (ma_mua_bo_loc.json) – không có mã PTĐTTC.
  • Đo: mua giá đóng cửa phiên lọc (lọc sau giờ đóng cửa → thực tế khớp phiên sau, sai lệch nhỏ), lãi sau N phiên so với
    VN-Index cùng khoảng (vượt = lãi mã − lãi VN-Index). Mã chưa đủ N phiên → chưa tính.
  • Báo cáo Telegram mỗi tháng 1 lần (phiên quét đầu tiên của tháng – trạng thái hieu_qua_bo_loc.json).
  python -m bo_loc.hieu_qua                  (in báo cáo)
  python -m bo_loc.hieu_qua --gui            (gửi Telegram nếu tháng này chưa gửi · --luon = gửi luôn)
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

FILE_LICH_SU = "lich_su_ma_mua_bo_loc.csv"
FILE_TRANG_THAI = "hieu_qua_bo_loc.json"
SO_PHIEN = (5, 20, 60)                 # 5 phiên: sớm, nhiễu – xem 20 & 60 là chính


def ghi_lich_su(du_lieu, file=FILE_LICH_SU):
    """du_lieu: nội dung ma_mua_bo_loc.json (phien, ma: {mã: [chiến lược…]}) → nối vào lịch sử, → số dòng phiên này."""
    phien = du_lieu.get("phien") or du_lieu.get("ngay_quet")
    if not phien:
        return 0
    moi = pd.DataFrame([{"phien": phien, "ma": m, "chien_luoc": cl} for m, ds in (du_lieu.get("ma") or {}).items()
                        for cl in (ds if isinstance(ds, list) else [ds])], columns=["phien", "ma", "chien_luoc"])
    cu = pd.read_csv(file, dtype=str) if os.path.exists(file) else pd.DataFrame(columns=moi.columns, dtype=str)
    out = pd.concat([cu[cu["phien"] != phien], moi]).sort_values(["phien", "chien_luoc", "ma"])
    out.to_csv(file, index=False, encoding="utf-8")
    return len(moi)


def _tai(ma, tu, chi_so=False):
    from canh_bao.du_lieu import tai
    df = tai(ma, "D", tu, chi_so=chi_so)
    return None if df is None or not len(df) else df["close"].astype(float)


def danh_gia(ls, tai_gia=_tai, so_phien=SO_PHIEN):
    """ls: DataFrame lịch sử (phien, ma, chien_luoc) → mỗi dòng thêm lãi % & vượt VN-Index % sau từng N phiên."""
    if ls is None or not len(ls):
        return pd.DataFrame()
    tu = (pd.to_datetime(ls["phien"]).min() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    vni = tai_gia("VNINDEX", tu, True)
    gia = {m: tai_gia(m, tu) for m in ls["ma"].unique()}
    out = ls.copy()
    for n in so_phien:
        lai, vuot = [], []
        for p, m in zip(out["phien"], out["ma"]):
            c = gia.get(m)
            if c is None or vni is None:
                lai.append(np.nan), vuot.append(np.nan)
                continue
            i = c.index.searchsorted(pd.Timestamp(p), side="right") - 1     # đóng cửa phiên lọc (hoặc trước đó)
            j = vni.index.searchsorted(pd.Timestamp(p), side="right") - 1
            if i < 0 or j < 0 or i + n >= len(c) or j + n >= len(vni):
                lai.append(np.nan), vuot.append(np.nan)
                continue
            a = (c.iloc[i + n] / c.iloc[i] - 1) * 100
            lai.append(a)
            vuot.append(a - (vni.iloc[j + n] / vni.iloc[j] - 1) * 100)
        out[f"lãi {n}p %"], out[f"vượt {n}p %"] = lai, vuot
    return out


def bao_cao(kq, so_phien=SO_PHIEN):
    """→ chữ báo cáo theo chiến lược: số lượt, lãi TB, vượt VN-Index TB, % lượt hơn VN-Index."""
    if kq is None or not len(kq):
        return "📏 HIỆU QUẢ BỘ LỌC: chưa có lịch sử mã MUA."
    d = [f"📏 HIỆU QUẢ BỘ LỌC – mã MUA của quét định kỳ ({kq['phien'].min()} → {kq['phien'].max()}, "
         f"{kq['phien'].nunique()} phiên lọc)", "Mua giá đóng cửa phiên lọc · so VN-Index cùng khoảng"]
    for cl, g in kq.groupby("chien_luoc"):
        d.append(f"\n• {cl} ({len(g)} lượt mã)")
        for n in so_phien:
            v = g[f"vượt {n}p %"].dropna()
            if not len(v):
                d.append(f"   {n} phiên: chưa đủ dữ liệu")
                continue
            d.append(f"   {n} phiên ({len(v)} lượt): lãi TB {g[f'lãi {n}p %'].dropna().mean():+.1f}% · vượt VN-Index "
                     f"{v.mean():+.1f}% (trung vị {v.median():+.1f}%) · {(v > 0).mean():.0%} lượt hơn VN-Index")
    d.append("\nÍt lượt (< 30) → chỉ tham khảo. Vượt VN-Index TB > 0 và > 50% lượt hơn ở cả 20 & 60 phiên = bộ lọc có ích.")
    return "\n".join(d)


def can_gui(hom_nay, file=FILE_TRANG_THAI):
    """Tháng của hom_nay chưa gửi báo cáo → True (ghi lại tháng đã gửi khi gửi xong: da_gui)."""
    try:
        with open(file, encoding="utf-8") as f:
            return json.load(f).get("thang") != f"{pd.Timestamp(hom_nay):%Y-%m}"
    except (OSError, ValueError):
        return True


def da_gui(hom_nay, file=FILE_TRANG_THAI):
    with open(file, "w", encoding="utf-8") as f:
        json.dump({"thang": f"{pd.Timestamp(hom_nay):%Y-%m}", "ngay": f"{pd.Timestamp(hom_nay):%Y-%m-%d}"}, f)


def main(argv=None):
    p = argparse.ArgumentParser(description="Hiệu quả mã MUA của bộ lọc so VN-Index")
    p.add_argument("--gui", action="store_true", help="gửi Telegram nếu tháng này chưa gửi")
    p.add_argument("--luon", action="store_true", help="gửi Telegram dù tháng này đã gửi")
    a = p.parse_args(argv)
    hom_nay = pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").tz_localize(None)
    if a.gui and not a.luon and not can_gui(hom_nay):
        print("Tháng này đã gửi báo cáo hiệu quả bộ lọc – bỏ qua")
        return 0
    ls = pd.read_csv(FILE_LICH_SU, dtype=str) if os.path.exists(FILE_LICH_SU) else None
    tin = bao_cao(danh_gia(ls))
    print(tin)
    if a.gui or a.luon:
        from canh_bao.thong_bao import gui
        gui(tin)
        da_gui(hom_nay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
