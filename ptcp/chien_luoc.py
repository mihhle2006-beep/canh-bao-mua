# -*- coding: utf-8 -*-
"""
CHIẾN LƯỢC CL1 / CL2 THEO THỊ TRƯỜNG – đọc VN-Index cuối mỗi tháng, chọn cách chia vốn cho tháng sau.

  Thành phần (bộ mô phỏng he_thoat.py, mỗi mã 1 phần vốn bằng nhau):
    A0  = vào MACD ngày (KHÔNG lọc tuần), thoát khung tuần ở 3R (MA10 tuần)
    B   = vào MACD ngày (lọc tuần), thoát như A0 + nhồi lệnh (lô đầu 50%)
    VNI = VN-Index (thực tế: ETF chỉ số)
  CL1 an toàn = A0 50% + B 50%        CL2 lãi = A0 70% + VNI 30%

  ĐIỂM THỊ TRƯỜNG (0–8, mỗi chỉ báo đạt = 1 điểm, tính ở phiên CUỐI THÁNG):
    1 VNI > MA200 · 2 MA50 > MA200 · 3 MA200 dốc lên (20 phiên) · 4 động lượng 6 tháng > 0 · 5 động lượng 3 tháng > 0
    6 cách đỉnh 1 năm < 10% · 7 độ rộng: > 50% số mã trên MA200 của mã · 8 biến động 20 phiên < trung vị 1 năm
  ĐỔI CÓ VÙNG ĐỆM: điểm ≥ 5 → CL2; điểm ≤ 2 → CL1; 3–4 → GIỮ NGUYÊN (tránh đổi qua lại – chi phí cơ hội).
  Quyết định dùng giá đóng cửa phiên cuối tháng, áp dụng từ phiên kế tiếp; tái cân bằng tỷ trọng hằng tháng.

  Kiểm định trên 41 mã 2019–2026 (giá thật): đổi theo điểm CAGR ≈ 10%, MDD ≈ −19% (CL1 cố định 8% / −16%,
  CL2 cố định 10% / −31%, VN-Index 8% / −40%), 9 lần đổi trong 7,5 năm. Bền với: trễ thực thi 1–3 phiên, phí đổi
  1%, tỷ trọng ±20%, bỏ bất kỳ 1 chỉ báo. Điểm yếu: A0 rất nhạy phí giao dịch (phí khứ hồi 1% → CAGR A0 còn ~8%);
  ngưỡng 5/2 chọn sau khi xem dữ liệu – giai đoạn 2023–2026 kết quả dao động theo ngưỡng.

  from ptcp import chien_luoc_thang
  kq = chien_luoc_thang(["GMD", "HAH", ...])      # bản tin: điểm, CL tháng này, mức VNI cần theo dõi, điểm mua A0 & B
"""
import os
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from . import cau_hinh as cfg
from .in_an import fmt, in_ra, ve_bang

TY_TRONG = getattr(cfg, "CL_TY_TRONG", {1: {"A0": 0.5, "B": 0.5, "VNI": 0.0}, 2: {"A0": 0.7, "B": 0.0, "VNI": 0.3}})
NGUONG_LEN = getattr(cfg, "CL_NGUONG_LEN", 5)          # điểm ≥ → CL2
NGUONG_XUONG = getattr(cfg, "CL_NGUONG_XUONG", 2)      # điểm ≤ → CL1
PHI_DOI = getattr(cfg, "CL_PHI_DOI", 0.003)            # phí + trượt giá trên phần vốn phải chuyển khi tái cân bằng
TEN_CL = {1: "CL1 – AN TOÀN (A0 50% + B 50%)", 2: "CL2 – LÃI (A0 70% + VN-Index 30%)"}


def bang_chi_bao(vni, gia_cac_ma=None):
    """8 chỉ báo (True = thuận lợi) theo NGÀY + cột 'Điểm' + các mức tham chiếu. vni: DataFrame có cột close."""
    c = vni.close
    ma200, ma50 = c.rolling(200, min_periods=200).mean(), c.rolling(50, min_periods=50).mean()
    dinh = c.rolling(252, min_periods=60).max()
    vol = c.pct_change().rolling(20).std() * np.sqrt(252)
    vol_tv = vol.rolling(252, min_periods=120).median()
    F = pd.DataFrame({
        "VNI > MA200": c > ma200,
        "MA50 > MA200": ma50 > ma200,
        "MA200 dốc lên (20 phiên)": ma200.diff(20) > 0,
        "Động lượng 6 tháng > 0": c / c.shift(126) > 1,
        "Động lượng 3 tháng > 0": c / c.shift(63) > 1,
        "Cách đỉnh 1 năm < 10%": c / dinh > 0.90,
    }, index=c.index)
    if gia_cac_ma is not None and len(gia_cac_ma.columns):
        g = gia_cac_ma.reindex(c.index).ffill()
        F["Độ rộng: > 50% mã trên MA200"] = (g > g.rolling(200, min_periods=200).mean()).mean(axis=1) > 0.5
    F["Biến động 20 phiên < trung vị 1 năm"] = vol < vol_tv
    F = F.fillna(False).astype(bool)
    muc = pd.DataFrame({"VNI": c, "MA50": ma50, "MA200": ma200, "Độ dốc MA200 (20 phiên)": ma200.diff(20),
                        "Đỉnh 1 năm": dinh, "Mốc cách đỉnh 10%": 0.9 * dinh, "VNI 63 phiên trước": c.shift(63),
                        "VNI 126 phiên trước": c.shift(126), "Biến động 20p %": vol * 100,
                        "Trung vị biến động 1 năm %": vol_tv * 100}, index=c.index)
    return F, F.sum(axis=1).rename("Điểm"), muc


def _la_cuoi_thang(idx):
    """Phiên cuối tháng ĐÃ KẾT THÚC (phiên cuối dữ liệu chỉ tính nếu là ngày làm việc cuối tháng)."""
    s = pd.Series(idx, index=idx)
    cuoi = (s.dt.month != s.shift(-1).dt.month).to_numpy(dtype=bool, copy=True)
    cuoi[-1] = idx[-1] == idx[-1] + pd.offsets.BMonthEnd(0)
    return cuoi


def lich_chien_luoc(diem, nguong_len=NGUONG_LEN, nguong_xuong=NGUONG_XUONG, cl_dau=1):
    """(lịch quyết định cuối tháng, CL áp dụng mỗi phiên). Quyết định ở phiên cuối tháng → áp từ phiên kế tiếp."""
    idx = diem.index
    cuoi = _la_cuoi_thang(idx)
    cl, rows = cl_dau, []
    cl_ngay = pd.Series(np.nan, index=idx)
    cl_ngay.iloc[0] = cl_dau
    for i in np.where(cuoi)[0]:
        d = int(diem.iloc[i])
        moi = 2 if d >= nguong_len else 1 if d <= nguong_xuong else cl
        rows.append({"Phiên quyết định": idx[i], "Điểm": d, "CL trước": cl, "CL tháng sau": moi, "Đổi": moi != cl})
        cl = moi
        if i + 1 < len(idx):
            cl_ngay.iloc[i + 1] = moi
    return pd.DataFrame(rows), cl_ngay.ffill().astype(int), cl


def ro_gop(thanh_phan, cl_ngay, ty_trong=None, phi=PHI_DOI):
    """Lợi suất ngày của rổ: tái cân bằng về tỷ trọng của CL đang áp dụng ở phiên đầu mỗi tháng / khi đổi CL."""
    ty_trong = ty_trong or TY_TRONG
    idx = cl_ngay.index
    comp = {k: v.reindex(idx).fillna(0) for k, v in thanh_phan.items()}
    w = ty_trong[int(cl_ngay.iloc[0])]
    val = {k: w.get(k, 0.0) for k in comp}
    out, truoc = [], None
    for t in idx:
        if truoc is not None and (t.month != truoc.month or cl_ngay[t] != cl_ngay[truoc]):
            moi = ty_trong[int(cl_ngay[t])]
            tong = sum(val.values())
            luan_chuyen = sum(abs(moi.get(k, 0.0) - val[k] / tong) for k in comp) / 2
            tong *= 1 - luan_chuyen * phi
            val = {k: moi.get(k, 0.0) * tong for k in comp}
        v0 = sum(val.values())
        val = {k: val[k] * (1 + comp[k][t]) for k in comp}
        out.append(sum(val.values()) / v0 - 1)
        truoc = t
    return pd.Series(out, idx)


def _tk(r):
    r = r.dropna()
    if len(r) < 20:
        return {"CAGR %": np.nan, "MDD %": np.nan, "Sharpe": np.nan}
    v = (1 + r).cumprod()
    return {"CAGR %": (v.iloc[-1] ** (252 / len(r)) - 1) * 100, "MDD %": ((v / v.cummax()) - 1).min() * 100,
            "Sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan}


def so_sanh_ro(thanh_phan, cl_ngay, moc_chia="2023-01-01"):
    """Bảng so sánh: CL1 cố định, CL2 cố định, đổi theo điểm, VN-Index (cả kỳ, trước/sau mốc chia) + theo năm."""
    idx = cl_ngay.index
    cach = {"CL1 cố định": ro_gop(thanh_phan, pd.Series(1, idx)),
            "CL2 cố định": ro_gop(thanh_phan, pd.Series(2, idx)),
            "Đổi CL1/CL2 theo điểm": ro_gop(thanh_phan, cl_ngay),
            "VN-Index": thanh_phan["VNI"].reindex(idx).fillna(0)}
    moc = pd.Timestamp(moc_chia)
    rows = []
    for ten, r in cach.items():
        a, b, c = _tk(r), _tk(r[r.index < moc]), _tk(r[r.index >= moc])
        rows.append({"Cách": ten, **a, f"Sharpe <{moc:%Y}": b["Sharpe"], f"CAGR ≥{moc:%Y} %": c["CAGR %"],
                     f"MDD ≥{moc:%Y} %": c["MDD %"], f"Sharpe ≥{moc:%Y}": c["Sharpe"]})
    nam = pd.DataFrame({ten: (1 + r).groupby(r.index.year).prod() - 1 for ten, r in cach.items()}).T * 100
    return pd.DataFrame(rows), nam, cach


def doc_thi_truong(F, diem, muc, cl_dang_dung):
    """Diễn giải phiên cuối: từng chỉ báo, khoảng cách tới ngưỡng, điều gì làm đổi CL ở cuối tháng."""
    t = F.index[-1]
    m = muc.loc[t]
    v = m["VNI"]
    chi_tiet = {
        "VNI > MA200": f"VNI {v:,.1f} vs MA200 {m['MA200']:,.1f} ({(v / m['MA200'] - 1) * 100:+.1f}%)",
        "MA50 > MA200": f"MA50 {m['MA50']:,.1f} vs MA200 {m['MA200']:,.1f}",
        "MA200 dốc lên (20 phiên)": f"MA200 thay đổi {m['Độ dốc MA200 (20 phiên)']:+.1f} điểm / 20 phiên",
        "Động lượng 6 tháng > 0": f"{(v / m['VNI 126 phiên trước'] - 1) * 100:+.1f}% (mốc {m['VNI 126 phiên trước']:,.1f})",
        "Động lượng 3 tháng > 0": f"{(v / m['VNI 63 phiên trước'] - 1) * 100:+.1f}% (mốc {m['VNI 63 phiên trước']:,.1f})",
        "Cách đỉnh 1 năm < 10%": f"{(v / m['Đỉnh 1 năm'] - 1) * 100:+.1f}% so đỉnh {m['Đỉnh 1 năm']:,.1f} – mất điểm "
                                 f"nếu VNI < {m['Mốc cách đỉnh 10%']:,.1f}",
        "Biến động 20 phiên < trung vị 1 năm": f"{m['Biến động 20p %']:.1f}% vs {m['Trung vị biến động 1 năm %']:.1f}%",
        "Độ rộng: > 50% mã trên MA200": "theo danh sách mã đang chạy",
    }
    bang = pd.DataFrame([{"Chỉ báo": k, "Đạt": bool(F.loc[t, k]), "Chi tiết": chi_tiet.get(k, "")} for k in F.columns])
    d = int(diem.iloc[-1])
    if d >= NGUONG_LEN:
        de = 2
    elif d <= NGUONG_XUONG:
        de = 1
    else:
        de = cl_dang_dung
    if cl_dang_dung == 2:
        can = f"chuyển CL1 nếu cuối tháng điểm ≤ {NGUONG_XUONG} (cần mất thêm {max(0, d - NGUONG_XUONG)} điểm)"
    else:
        can = f"chuyển CL2 nếu cuối tháng điểm ≥ {NGUONG_LEN} (cần thêm {max(0, NGUONG_LEN - d)} điểm)"
    return {"ngay": t, "diem": d, "so_chi_bao": len(F.columns), "bang": bang, "cl_dang_dung": cl_dang_dung,
            "cl_neu_cuoi_thang": de, "dieu_kien_doi": can}


def phan_bo_muc_tieu(diem_mua, ty_trong, so_ma):
    """
    Tỷ trọng MỤC TIÊU mỗi mã (% tổng vốn) phiên tới = Σ tỷ trọng CL của thành phần × (1 / số mã) × khối lượng lệnh
    của thành phần đó (đang giữ, hoặc sẽ mua phiên tới). Phần VN-Index để riêng (ETF chỉ số).
    """
    rows = {}
    for tp in ("A0", "B"):
        b = diem_mua.get(tp)
        w = ty_trong.get(tp, 0.0)
        if b is None or not len(b) or w <= 0:
            continue
        for _, r in b.iterrows():
            tt = str(r["Trạng thái"])
            if tt.startswith("ĐANG GIỮ"):
                kl = r.get("KL (phần vốn)", 1.0)
                kl = 1.0 if kl != kl else kl
                if "BÁN phiên tới" in tt:
                    kl = 0.0
            elif tt.startswith("MUA"):
                kl = r.get("Khối lượng (phần vốn)", 1.0)
            else:
                continue
            x = rows.setdefault(r["Mã"], {"Mã": r["Mã"], "Giá đóng cửa": r["Giá đóng cửa"], "A0": "", "B": "",
                                          "Tỷ trọng mục tiêu % vốn": 0.0, "Cắt lỗ chặt nhất": np.nan})
            x[tp] = ("giữ" if tt.startswith("ĐANG") else "mua") + f" {kl:g}"
            x["Tỷ trọng mục tiêu % vốn"] += w * kl / so_ma * 100
            cl = r.get("Cắt lỗ phiên tới", np.nan)
            cl = r.get("Cắt lỗ dự kiến", np.nan) if cl != cl else cl
            if cl == cl:
                x["Cắt lỗ chặt nhất"] = cl if x["Cắt lỗ chặt nhất"] != x["Cắt lỗ chặt nhất"] else max(cl, x["Cắt lỗ chặt nhất"])
    b = pd.DataFrame(list(rows.values()))
    if len(b):
        b = b.sort_values("Tỷ trọng mục tiêu % vốn", ascending=False).reset_index(drop=True)
        b.loc[len(b)] = {"Mã": "VN-Index (ETF)", "Tỷ trọng mục tiêu % vốn": ty_trong.get("VNI", 0) * 100}
        b.loc[len(b)] = {"Mã": "TIỀN MẶT", "Tỷ trọng mục tiêu % vốn": 100 - b["Tỷ trọng mục tiêu % vốn"].sum()}
    return b


def chien_luoc_thang(ds_ma, start="2019-01-01", csv=None, vni_csv=None, moc_chia="2023-01-01", xuat_excel=True,
                     in_ket_qua=True, thu_muc="."):
    """
    Bản tin chiến lược: điểm thị trường hôm nay, CL đang áp dụng & tỷ trọng, điều kiện đổi, điểm mua / vị thế của
    A0 và B, so sánh rổ (CL1 / CL2 / đổi theo điểm / VN-Index) + lịch đổi. Cần VN-Index (tự tải hoặc vni_csv).
    """
    from .backtest_thoat import backtest_he_thoat
    from .he_thoat import danh_sach_bien_the
    bts = {b.ma: b for b in danh_sach_bien_the(co_vni=False, vao_phu=False)}
    kq = backtest_he_thoat(ds_ma, start=start, csv=csv, vni_csv=vni_csv, bien_the=[bts["A0"], bts["B"]],
                           bt_diem_mua=("A0", "B"), xuat_excel=False, in_ket_qua=False, ve_ma=[], thu_muc=thu_muc)
    if kq is None or kq.get("vni") is None:
        raise ValueError("Không có VN-Index – truyền vni_csv=... hoặc kiểm tra kết nối.")
    vni = kq["vni"]
    F, diem, muc = bang_chi_bao(vni, kq["gia"])
    lich, cl_ngay, cl_hien = lich_chien_luoc(diem)
    i0 = kq["ret_ro"][("macd0", "A0")].index[0]
    tp = {"A0": kq["ret_ro"][("macd0", "A0")], "B": kq["ret_ro"][("macd", "B")], "VNI": vni.close.pct_change()}
    idx = cl_ngay.index[cl_ngay.index >= i0 + pd.Timedelta(days=90)]
    bang, nam, cach = so_sanh_ro(tp, cl_ngay.loc[idx], moc_chia)
    doc = doc_thi_truong(F, diem, muc, cl_hien)
    ra = {"doc": doc, "ty_trong": TY_TRONG[cl_hien], "lich": lich, "so_sanh": bang, "theo_nam": nam, "chi_bao": F,
          "diem": diem, "diem_mua": kq["diem_mua"], "backtest": kq, "file_excel": None,
          "phan_bo": phan_bo_muc_tieu(kq["diem_mua"], TY_TRONG[cl_hien], len(kq["ds_ma"]))}
    if in_ket_qua:
        in_ban_tin(ra)
    if xuat_excel:
        ra["file_excel"] = xuat_excel_cl(ra, os.path.join(thu_muc, f"chien_luoc_{date.today():%Y%m%d}.xlsx"))
        if in_ket_qua:
            in_ra(f"  ✔ Đã xuất {ra['file_excel']}")
    return ra


def in_ban_tin(ra):
    d = ra["doc"]
    in_ra(f"\n{'#' * 84}\n CHIẾN LƯỢC THEO THỊ TRƯỜNG – phiên {d['ngay']:%d/%m/%Y}\n{'#' * 84}")
    in_ra(f"  ĐIỂM THỊ TRƯỜNG: {d['diem']}/{d['so_chi_bao']}  (≥ {NGUONG_LEN} → CL2, ≤ {NGUONG_XUONG} → CL1, ở giữa giữ nguyên)")
    in_ra(ve_bang(d["bang"].assign(Đạt=d["bang"]["Đạt"].map({True: "✔", False: "✘"}))))
    w = ra["ty_trong"]
    in_ra(f"\n  ĐANG ÁP DỤNG: {TEN_CL[d['cl_dang_dung']]}  → tỷ trọng A0 {w['A0'] * 100:.0f}% · B {w['B'] * 100:.0f}% · "
          f"VN-Index {w['VNI'] * 100:.0f}%")
    in_ra(f"  Nếu cuối tháng giữ nguyên điểm này: {TEN_CL[d['cl_neu_cuoi_thang']]}. Điều kiện đổi: {d['dieu_kien_doi']}.")
    for ten, b in ra["diem_mua"].items():
        if b is None or not len(b):
            continue
        hien = b[~b["Trạng thái"].eq("CHỜ tín hiệu")]
        cot = [c for c in ("Mã", "Trạng thái", "Giá đóng cửa", "Cắt lỗ dự kiến", "Cắt lỗ phiên tới", "Tầng",
                           "Lãi hiện tại %") if c in hien.columns]
        in_ra(f"\n  ĐIỂM MUA / VỊ THẾ – {ten}:")
        in_ra(ve_bang(hien[cot]) if len(hien) else "  (không có)")
    if len(ra.get("phan_bo", [])):
        in_ra("\n  TỶ TRỌNG MỤC TIÊU PHIÊN TỚI (% tổng vốn; 'giữ 1' = đủ 1 phần vốn mã của thành phần đó):")
        in_ra(ve_bang(ra["phan_bo"].round(2)))
    in_ra("\n  SO SÁNH RỔ (giá thật, đã trừ phí):")
    in_ra(ve_bang(ra["so_sanh"].round(2)))
    doi = ra["lich"][ra["lich"]["Đổi"]]
    in_ra("  Lịch đổi: " + ", ".join(f"{r['Phiên quyết định']:%m/%Y} → CL{r['CL tháng sau']}" for _, r in doi.iterrows()))
    in_ra("  Lưu ý: tỷ trọng & ngưỡng chọn sau khi xem dữ liệu 2019–2026; A0 nhạy phí giao dịch – dùng công ty phí thấp.")


def xuat_excel_cl(ra, path):
    with pd.ExcelWriter(path) as w:
        d = ra["doc"]
        pd.DataFrame({"Mục": ["Phiên", "Điểm thị trường", "Đang áp dụng", "Nếu cuối tháng giữ điểm", "Điều kiện đổi",
                              "Tỷ trọng A0 %", "Tỷ trọng B %", "Tỷ trọng VN-Index %"],
                      "Giá trị": [f"{d['ngay']:%d/%m/%Y}", f"{d['diem']}/{d['so_chi_bao']}", TEN_CL[d["cl_dang_dung"]],
                                  TEN_CL[d["cl_neu_cuoi_thang"]], d["dieu_kien_doi"],
                                  ra["ty_trong"]["A0"] * 100, ra["ty_trong"]["B"] * 100, ra["ty_trong"]["VNI"] * 100]}) \
            .to_excel(w, sheet_name="Ban tin", index=False)
        d["bang"].to_excel(w, sheet_name="Chi bao thi truong", index=False)
        if len(ra.get("phan_bo", [])):
            ra["phan_bo"].to_excel(w, sheet_name="Ty trong muc tieu", index=False)
        for ten, b in ra["diem_mua"].items():
            if b is not None and len(b):
                b.to_excel(w, sheet_name=f"Diem mua {ten}"[:31], index=False)
        ra["so_sanh"].to_excel(w, sheet_name="So sanh ro", index=False)
        ra["theo_nam"].to_excel(w, sheet_name="Ro theo nam")
        ra["lich"].to_excel(w, sheet_name="Lich doi CL", index=False)
        ra["chi_bao"].assign(Điểm=ra["diem"]).resample("ME").last().to_excel(w, sheet_name="Diem theo thang")
    try:
        from .excel_xanh import trang_tri_excel
        trang_tri_excel(path)
    except Exception:
        pass
    return path
