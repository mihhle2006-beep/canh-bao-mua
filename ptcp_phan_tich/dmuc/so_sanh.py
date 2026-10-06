# -*- coding: utf-8 -*-
"""
SO SÁNH DANH MỤC VỚI VN-INDEX + NHẬN XÉT.
  1. Theo kỳ (1 tuần … 1 năm, từ đầu năm): nếu GIỮ ĐÚNG số CP hiện tại từ đầu kỳ – phần cổ phiếu & gồm tiền mặt.
  2. Từ ngày mua (cần nhật ký giao dịch hoặc cột ngay_mua): lợi suất THỰC so với việc đem ĐÚNG các khoản tiền đó
     mua VN-Index vào cùng ngày (bán ra cùng ngày, cùng tỷ lệ). VN-Index là chỉ số GIÁ – không gồm cổ tức.
"""
import numpy as np
import pandas as pd

from .tien_ich import co

KY = {"1 tuần": 5, "1 tháng": 21, "3 tháng": 63, "6 tháng": 126, "1 năm": 252}


def _gia_tai(s, ngay):
    """Giá đóng cửa gần nhất tại hoặc trước 'ngay' (NaN nếu trước ngày đầu tiên có dữ liệu)."""
    ngay = pd.Timestamp(ngay)
    return float(s.asof(ngay)) if len(s) and ngay >= s.index[0] else np.nan


def so_sanh_theo_ky(ds_kq, tien_mat, vni):
    giu = [r for r in ds_kq if r["so_cp"] > 0]
    if not giu or vni is None:
        return pd.DataFrame()
    gia = pd.concat({r["symbol"]: r["df"].close for r in giu}, axis=1).sort_index().ffill()
    n = pd.Series({r["symbol"]: r["so_cp"] for r in giu})
    gt = (gia * n * 1000).sum(axis=1, min_count=len(n))         # NaN nếu có mã chưa niêm yết
    hom_nay = gia.index[-1]
    moc = {ten: gia.index[-k - 1] for ten, k in KY.items() if len(gia) > k}
    dau_nam = gia.index[gia.index.year < hom_nay.year]
    if len(dau_nam):
        moc["Từ đầu năm"] = dau_nam[-1]
    rows = []
    for ten, t0 in moc.items():
        v0, v1 = gt.loc[t0], gt.iloc[-1]
        r_cp = (v1 / v0 - 1) * 100 if co(v0) and v0 > 0 else np.nan
        r_ts = ((v1 + tien_mat) / (v0 + tien_mat) - 1) * 100 if co(v0) else np.nan
        r_vni = (_gia_tai(vni.close, hom_nay) / _gia_tai(vni.close, t0) - 1) * 100
        rows.append([ten, f"{t0:%d/%m/%Y}", r_cp, r_ts, r_vni, r_cp - r_vni])
    return pd.DataFrame(rows, columns=["Kỳ", "Từ ngày", "Danh mục CP %", "Danh mục gồm tiền mặt %", "VN-Index %",
                                       "Chênh lệch CP − VNI (điểm %)"])


def _dong_tien(r, vao):
    """Danh sách giao dịch (ngày, loại, SL, giá, phí) của 1 mã: từ nhật ký, hoặc 1 lệnh mua tại ngay_mua/giá vốn."""
    if vao.get("dong_tien"):
        return vao["dong_tien"]
    if vao.get("ngay_mua") is not None and not pd.isna(vao["ngay_mua"]) and r["gia_von"]:
        return [(vao["ngay_mua"], "mua", r["so_cp"], r["gia_von"], 0.0)]
    return None


def so_sanh_tu_ngay_mua(ds_kq, ds_vao, vni):
    """Mỗi mã đang giữ (hoặc đã từng giao dịch trong nhật ký): lợi suất thực vs VN-Index cùng dòng tiền."""
    if vni is None:
        return pd.DataFrame(), []
    vao = {d["ma"]: d for d in ds_vao}
    v_nay = float(vni.close.iloc[-1])
    rows, thieu = [], []
    for r in ds_kq:
        dt = _dong_tien(r, vao.get(r["symbol"], {}))
        if dt is None:
            if r["so_cp"] > 0:
                thieu.append(r["symbol"])
            continue
        tong_mua = tien_ban = co_tuc = 0.0
        sl = don_vi = tien_ban_vni = 0.0
        loi = False
        for ngay, loai, so, gia, phi in sorted(dt, key=lambda x: x[0]):
            v = _gia_tai(vni.close, ngay)
            if loai == "mua":
                tien = so * gia * 1000 + phi
                tong_mua += tien
                sl += so
                if co(v):
                    don_vi += tien / v
                else:
                    loi = True
            elif loai == "ban" and sl > 0:
                f = so / sl
                tien_ban += so * gia * 1000 - phi
                tien_ban_vni += f * don_vi * (v if co(v) else 0)
                don_vi *= 1 - f
                sl -= so
            elif loai == "co_tuc_tien":
                co_tuc += sl * gia * 1000
            elif loai == "co_tuc_cp":
                sl += so
        if tong_mua <= 0 or loi:
            continue
        gt_nay = r["so_cp"] * r["ht"] * 1000
        lai_cp = gt_nay + tien_ban + co_tuc - tong_mua
        lai_vni = don_vi * v_nay + tien_ban_vni - tong_mua
        ngay_dau = min(x[0] for x in dt)
        rows.append([r["symbol"], f"{pd.Timestamp(ngay_dau):%d/%m/%Y}", (pd.Timestamp.today() - pd.Timestamp(ngay_dau)).days,
                     tong_mua, gt_nay + tien_ban + co_tuc, lai_cp, lai_cp / tong_mua * 100, lai_vni,
                     lai_vni / tong_mua * 100, (lai_cp - lai_vni) / tong_mua * 100])
    cot = ["Mã", "Mua lần đầu", "Số ngày", "Tổng tiền mua (đ)", "Giá trị + đã nhận (đ)", "Lãi/lỗ (đ)",
           "Lợi suất %", "Lãi/lỗ nếu mua VNI (đ)", "VN-Index cùng dòng tiền %", "Chênh lệch (điểm %)"]
    b = pd.DataFrame(rows, columns=cot)
    if len(b) > 1:
        t = b[["Tổng tiền mua (đ)", "Giá trị + đã nhận (đ)", "Lãi/lỗ (đ)", "Lãi/lỗ nếu mua VNI (đ)"]].sum()
        b.loc[len(b)] = ["TỔNG", "", np.nan, t.iloc[0], t.iloc[1], t.iloc[2], t.iloc[2] / t.iloc[0] * 100, t.iloc[3],
                         t.iloc[3] / t.iloc[0] * 100, (t.iloc[2] - t.iloc[3]) / t.iloc[0] * 100]
    return b, thieu


def nhan_xet(bang_ky, bang_mua, thieu, ds_kq, beta_dm, ty_trong_cp):
    """Các câu nhận xét so với VN-Index (in trong báo cáo & Excel)."""
    nx = []
    if len(bang_mua):
        t = bang_mua.iloc[-1]
        nx.append(f"Từ ngày mua ({'cả danh mục' if t['Mã'] == 'TỔNG' else t['Mã']}): lợi suất thực {t['Lợi suất %']:+.1f}% "
                  f"({t['Lãi/lỗ (đ)']:+,.0f} đ) so với {t['VN-Index cùng dòng tiền %']:+.1f}% nếu đem đúng số tiền đó mua "
                  f"VN-Index cùng ngày → {'VƯỢT' if t['Chênh lệch (điểm %)'] >= 0 else 'KÉM'} thị trường "
                  f"{abs(t['Chênh lệch (điểm %)']):.1f} điểm %.")
        ma = bang_mua[bang_mua["Mã"] != "TỔNG"]
        if len(ma) > 1:
            tot, xau = ma.loc[ma["Chênh lệch (điểm %)"].idxmax()], ma.loc[ma["Chênh lệch (điểm %)"].idxmin()]
            nx.append(f"Đóng góp: {tot['Mã']} tốt nhất ({tot['Chênh lệch (điểm %)']:+.1f} điểm % so VNI), "
                      f"{xau['Mã']} kém nhất ({xau['Chênh lệch (điểm %)']:+.1f} điểm %).")
    if thieu:
        nx.append(f"Chưa có ngày mua của {', '.join(thieu)} → chưa so được lợi suất THỰC với VN-Index; thêm cột "
                  f"'ngay_mua' (dd/mm/yyyy) vào danh mục hoặc dùng --nhat_ky.")
    if len(bang_ky):
        b = bang_ky.set_index("Kỳ")
        for ky in ("3 tháng", "1 năm", "Từ đầu năm"):
            if ky in b.index and co(b.at[ky, "Danh mục CP %"]):
                c = b.at[ky, "Chênh lệch CP − VNI (điểm %)"]
                nx.append(f"{ky} (giữ số CP hiện tại): phần cổ phiếu {b.at[ky, 'Danh mục CP %']:+.1f}% vs VN-Index "
                          f"{b.at[ky, 'VN-Index %']:+.1f}% → {'vượt' if c >= 0 else 'kém'} {abs(c):.1f} điểm %; "
                          f"tính cả tiền mặt {b.at[ky, 'Danh mục gồm tiền mặt %']:+.1f}%.")
        if "3 tháng" in b.index:
            r_vni = b.at["3 tháng", "VN-Index %"]
            hs = []
            for r in ds_kq:
                d = r["df"].close
                if len(d) > 63:
                    hs.append((r["symbol"], (d.iloc[-1] / d.iloc[-64] - 1) * 100 - r_vni))
            if hs:
                nx.append("Từng mã so VN-Index 3 tháng: " + ", ".join(f"{m} {x:+.1f}" for m, x in
                                                                    sorted(hs, key=lambda x: -x[1])) + " (điểm %).")
    if co(beta_dm):
        nx.append(f"Beta danh mục {beta_dm:.2f} (cổ phiếu {ty_trong_cp:.0f}% tài sản): VN-Index ±10% → danh mục "
                  f"dự kiến ±{abs(beta_dm) * 10:.1f}% – "
                  + ("ít biến động hơn thị trường, nên kỳ thị trường tăng mạnh thường thấp hơn VN-Index là bình thường."
                     if beta_dm < 0.8 else "biến động tương đương/ cao hơn thị trường."))
    nx.append("Lưu ý: VN-Index là chỉ số giá, không gồm cổ tức → so sánh hơi có lợi cho danh mục nhận cổ tức.")
    return nx
