# -*- coding: utf-8 -*-
"""
TỐI ƯU DANH MỤC MARKOWITZ.
Sửa so với bản 1 file:
  • Lợi suất TUẦN, căn theo ngày chung (bản cũ: ffill + fillna(0) → phiên không giao dịch = lợi suất 0, làm thấp
    phương sai & tương quan); co ma trận hiệp phương sai Ledoit–Wolf
  • Mặc định danh mục PHƯƠNG SAI NHỎ NHẤT (không cần μ – μ lịch sử 2 năm của vài mã rất nhiễu)
  • Có TIỀN MẶT: chỉ phân bổ (100% − GIU_TIEN_MAT_PCT) tổng tài sản cho cổ phiếu (bản cũ buộc đầu tư 100%)
  • Lập kế hoạch cho CẢ GMV và Sharpe lớn nhất để so sánh; xuất ma trận hiệp phương sai & tương quan
  • Mã đang giữ bị loại vì thiếu dữ liệu được GIỮ NGUYÊN (bản cũ ngầm bán mà không ghi trong kế hoạch)
  • Ngưỡng tái cân bằng, bỏ lệnh nhỏ, ước tính phí; lệnh mua chưa có tín hiệu kỹ thuật được đánh dấu CHỜ
  • "muc_tieu" chỉ dùng giá mục tiêu TỰ NHẬP (định giá) – không dùng upside kỹ thuật (tự đặt sẵn 15–20%)
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .cau_hinh import (LO_CHAN, CHO_PHEP_LO_LE, MKW_CO_GIAN, MKW_GIA_TRI_GD_TOI_THIEU, MKW_NGUONG_TAI_CAN_BANG,
                       MKW_SO_DANH_MUC_NGAU_NHIEN, MKW_SO_NAM, MKW_SO_TUAN, MKW_SO_TUAN_TOI_THIEU)
from ptcp.thong_ke import _chi_phi as chi_phi
from .tien_ich import co


def ledoit_wolf(X, tra_he_so=False):
    """Co ma trận hiệp phương sai mẫu về m·I (Ledoit & Wolf 2004). X: T × n lợi suất.
    Hệ số co δ ∈ [0, 1]: 0 = dùng nguyên ma trận mẫu; 1 = coi mọi mã cùng rủi ro, không tương quan
    (khi đó GMV = CHIA ĐỀU). tra_he_so=True → trả (ma trận, δ)."""
    X = np.asarray(X, float)
    T, n = X.shape
    Xc = X - X.mean(0)
    S = Xc.T @ Xc / T
    m = np.trace(S) / n
    d2 = ((S - m * np.eye(n)) ** 2).sum() / n
    b2 = min(sum(((np.outer(x, x) - S) ** 2).sum() for x in Xc) / T ** 2 / n, d2)
    delta = b2 / d2 if d2 > 0 else 1.0
    Sig = delta * m * np.eye(n) + (1 - delta) * S
    return (Sig, delta) if tra_he_so else Sig


def _hq(w, mu, cov, rf):
    r, v = float(w @ mu), float(np.sqrt(max(w @ cov @ w, 1e-12)))
    return r, v, (r - rf) / v


def _toi_uu(ham, n, cap, rb=()):
    kq = minimize(ham, np.ones(n) / n, method="SLSQP", bounds=[(0, cap)] * n,
                  constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}] + list(rb),
                  options={"maxiter": 1000, "ftol": 1e-12})
    w = np.clip(kq.x, 0, None)
    return w / w.sum(), kq.success


def _lap_ke_hoach(w, ma, kq_ma, gt, bi_loai, tong_ts, phan_bo):
    """Số CP mua/bán để phần cổ phiếu đạt tỷ trọng w (bỏ lệnh lệch nhỏ / giá trị nhỏ; mua chưa có tín hiệu → CHỜ)."""
    rows = []
    for i, m in enumerate(ma):
        r = kq_ma[m]
        gia_d = r["ht"] * 1000
        dich = w[i] * phan_bo
        lech = dich - gt[m]
        sl = int(abs(lech) // gia_d)
        sl = sl // LO_CHAN * LO_CHAN if sl >= LO_CHAN else (sl if CHO_PHEP_LO_LE else 0)
        sl = min(sl, int(r["so_cp"])) if lech < 0 else sl
        if (abs(lech) / tong_ts * 100 if tong_ts else 0) < MKW_NGUONG_TAI_CAN_BANG or sl * gia_d < MKW_GIA_TRI_GD_TOI_THIEU \
                or sl == 0:
            hd, sl = "GIỮ NGUYÊN (lệch nhỏ / lệnh quá nhỏ)", 0
        elif lech > 0:
            hd = "MUA" if r["quyet_dinh"] in ("MUA", "MUA TỪNG PHẦN") else f"CHỜ – tín hiệu KT: {r['quyet_dinh']}"
        else:
            hd = "BÁN"
        sl_ky = sl if lech > 0 else -sl
        rows.append({"Mã": m, "Tỷ trọng HT % TS": gt[m] / tong_ts * 100 if tong_ts else 0,
                     "Tỷ trọng mục tiêu % TS": dich / tong_ts * 100 if tong_ts else 0, "SL hiện tại": r["so_cp"],
                     "Mua(+)/Bán(−) CP": sl_ky, "Giá trị GD (đ)": sl_ky * gia_d,
                     "Phí ước tính (đ)": abs(sl_ky) * gia_d * chi_phi() / 200,
                     "Lô": "lô lẻ" if 0 < sl < LO_CHAN else ("lô chẵn" if sl else ""), "Hành động": hd})
    for m in bi_loai:
        if gt[m] > 0:
            rows.append({"Mã": m, "Tỷ trọng HT % TS": gt[m] / tong_ts * 100, "Tỷ trọng mục tiêu % TS": gt[m] / tong_ts * 100,
                         "SL hiện tại": kq_ma[m]["so_cp"], "Mua(+)/Bán(−) CP": 0, "Giá trị GD (đ)": 0,
                         "Phí ước tính (đ)": 0, "Lô": "", "Hành động": "GIỮ NGUYÊN – thiếu dữ liệu để tối ưu"})
    return pd.DataFrame(rows)


def toi_uu_markowitz(ds_kq, dm, rf, tien_mat, ky_vong="lich_su", cap_pct=40.0, chon="gmv", giu_tien_mat=50.0):
    kq_ma = {r["symbol"]: r for r in ds_kq}
    gia = pd.concat({r["symbol"]: r["df"].close for r in ds_kq}, axis=1).sort_index()
    ret = gia.resample("W-FRI").last().pct_change(fill_method=None).iloc[1:].tail(MKW_SO_TUAN)   # 5 năm gần nhất
    so_tuan_co = ret.notna().sum()
    du = so_tuan_co >= MKW_SO_TUAN_TOI_THIEU
    bi_loai = list(ret.columns[~du])
    ret = ret.loc[:, du].dropna()
    ma = list(ret.columns)
    n = len(ma)
    if n < 2 or len(ret) < 26:
        print(f"  ⚠ Markowitz cần ≥ 2 mã có ≥ {MKW_SO_NAM} năm dữ liệu chung"
              + (f" (không đủ: {', '.join(bi_loai)})" if bi_loai else "") + ".")
        return None
    mu_ls = ret.mean().values * 52
    mu_dg = np.array([kq_ma[m]["upside_dg"] / 100 if co(kq_ma[m]["upside_dg"]) else mu_ls[i] for i, m in enumerate(ma)])
    mu, mo_ta = {"muc_tieu": (mu_dg, "upside tới giá mục tiêu TỰ NHẬP (mã không nhập: lịch sử)"),
                 "ket_hop": (0.5 * mu_ls + 0.5 * mu_dg, "50% lịch sử + 50% định giá tự nhập")}.get(
        ky_vong, (mu_ls, f"trung bình lịch sử {len(ret)} tuần"))
    cov_mau = np.cov(ret.values.T, bias=True) * 52 + np.eye(n) * 1e-10
    if MKW_CO_GIAN:
        cov, he_so_co = ledoit_wolf(ret.values, tra_he_so=True)
        cov = cov * 52 + np.eye(n) * 1e-10
    else:
        cov, he_so_co = cov_mau, 0.0
    # Trần tỷ trọng: với n mã và trần c, mỗi mã BỊ ÉP ≥ 1 − (n−1)·c (VD 3 mã, trần 40% → mỗi mã 20–40%, kết quả
    # luôn quanh 33%). Tự nới trần lên ≥ 1/(n−1) để sàn ép buộc = 0%.
    cap_nhap = cap_pct / 100
    cap = min(1.0, max(cap_nhap, 1 / (n - 1)))
    canh_bao = []
    if cap > cap_nhap + 1e-9:
        canh_bao.append(f"Chỉ có {n} mã: trần {cap_nhap * 100:.0f}%/mã sẽ ép mọi mã vào khoảng "
                        f"{max(0, 1 - (n - 1) * cap_nhap) * 100:.0f}–{cap_nhap * 100:.0f}% (≈ chia đều) → tự nới trần lên "
                        f"{cap * 100:.0f}%. Muốn giữ trần cũ: thêm mã hoặc sửa MKW_TY_TRONG_TOI_DA.")
    if he_so_co > 0.5:
        canh_bao.append(f"Hệ số co Ledoit–Wolf {he_so_co * 100:.0f}%: dữ liệu chưa đủ phân biệt rủi ro giữa các mã → "
                        f"GMV gần chia đều. Đây là thận trọng có chủ đích, không phải lỗi (xem cột 'không co').")

    w_gmv, _ = _toi_uu(lambda w: w @ cov @ w, n, cap)
    w_ms, _ = _toi_uu(lambda w: -_hq(w, mu, cov, rf)[2], n, cap)
    # Bản "tự tính" để đối chiếu: ma trận MẪU (không co), KHÔNG trần tỷ trọng – như làm tay trên Excel/Solver
    w_gmv_tho, _ = _toi_uu(lambda w: w @ cov_mau @ w, n, 1.0)
    w_ms_tho, _ = _toi_uu(lambda w: -_hq(w, mu, cov_mau, rf)[2], n, 1.0)
    cac_dm = {"Phương sai nhỏ nhất (GMV)": w_gmv, "Sharpe lớn nhất": w_ms, "Chia đều": np.ones(n) / n,
              "GMV – không co, không trần": w_gmv_tho, "Sharpe – không co, không trần": w_ms_tho}

    # Danh mục hiện tại (phần cổ phiếu)
    gt = {m: kq_ma[m]["so_cp"] * kq_ma[m]["ht"] * 1000 for m in kq_ma}
    gt_ma = np.array([gt[m] for m in ma])
    if gt_ma.sum() > 0:
        cac_dm = {"Hiện tại": gt_ma / gt_ma.sum(), **cac_dm}

    r_min = _hq(w_gmv, mu, cov, rf)[0]
    bien = []
    for muc in np.linspace(r_min, max(r_min, np.sort(mu)[::-1][:max(1, int(np.ceil(1 / cap)))].mean()), 30):
        w, ok = _toi_uu(lambda w: w @ cov @ w, n, cap, [{"type": "eq", "fun": lambda w, m=muc: w @ mu - m}])
        if ok:
            bien.append(list(_hq(w, mu, cov, rf)))
    bien = pd.DataFrame(bien, columns=["Rủi ro", "Lợi suất", "Sharpe"])
    W = np.random.default_rng(42).dirichlet(np.ones(n), MKW_SO_DANH_MUC_NGAU_NHIEN)
    mc_r, mc_v = W @ mu, np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W))
    mc = pd.DataFrame({"Rủi ro": mc_v, "Lợi suất": mc_r, "Sharpe": (mc_r - rf) / mc_v})

    bang_w = pd.DataFrame({k: v * 100 for k, v in cac_dm.items()}, index=pd.Index(ma, name="Mã"))
    chi_tieu = pd.DataFrame({k: dict(zip(["Lợi suất kỳ vọng %", "Rủi ro (σ) %", "Sharpe"],
                                         [x * 100 if i < 2 else x for i, x in enumerate(_hq(v, mu, cov, rf))]))
                             for k, v in cac_dm.items()})

    # ---- Kế hoạch: chỉ phân bổ PHẦN CỔ PHIẾU = (100% − % tiền mặt muốn giữ); mã bị loại giữ nguyên ----
    tong_ts = dm["tong"]["Tổng tài sản (đ)"]
    pct_cp = 100.0 - giu_tien_mat
    co_dinh = sum(gt[m] for m in bi_loai)
    phan_bo = max(0.0, pct_cp / 100 * tong_ts - co_dinh)
    ke_hoach = {ten: _lap_ke_hoach(w, ma, kq_ma, gt, bi_loai, tong_ts, phan_bo)
                for ten, w in (("Phương sai nhỏ nhất (GMV)", w_gmv), ("Sharpe lớn nhất", w_ms))}
    ten_chon = "Sharpe lớn nhất" if chon == "max_sharpe" else "Phương sai nhỏ nhất (GMV)"
    for ten, w in (("Phương sai nhỏ nhất (GMV)", w_gmv), ("Sharpe lớn nhất", w_ms)):
        if _hq(w, mu, cov, rf)[0] < rf:
            canh_bao.append(f"Lợi suất kỳ vọng (lịch sử) của '{ten}' < Rf.")
    tien_sau = {}
    for ten, kh in ke_hoach.items():
        th = kh["Hành động"].isin(["MUA", "BÁN"])
        tien_sau[ten] = tien_mat - kh.loc[th, "Giá trị GD (đ)"].sum() - kh.loc[th, "Phí ước tính (đ)"].sum()
    if tien_sau[ten_chon] < 0:
        canh_bao.append(f"Kế hoạch '{ten_chon}' cần thêm {-tien_sau[ten_chon]:,.0f} đ → thực hiện lệnh BÁN trước.")
    if bi_loai:
        canh_bao.append(f"Chưa đủ {MKW_SO_NAM} năm dữ liệu → không đưa vào tối ưu, vị thế giữ nguyên: "
                        + ", ".join(f"{m} ({int(n)} tuần)" for m, n in so_tuan_co.items() if m in bi_loai))
    tq = pd.DataFrame(cov / np.sqrt(np.outer(np.diag(cov), np.diag(cov))), index=ma, columns=ma)
    return {"ma": ma, "mu": pd.Series(mu * 100, index=ma), "sigma": pd.Series(np.sqrt(np.diag(cov)) * 100, index=ma),
            "mo_ta_mu": mo_ta, "cap": cap, "so_tuan": len(ret), "bang_w": bang_w, "chi_tieu": chi_tieu, "bien": bien,
            "mc": mc, "cac_dm": cac_dm, "mu_vec": mu, "cov": cov, "rf": rf, "ke_hoach": ke_hoach,
            "ten_chon": ten_chon, "pct_cp": pct_cp, "giu_tien_mat": giu_tien_mat, "tong_ts": tong_ts,
            "tien_sau": tien_sau, "canh_bao": canh_bao, "tuong_quan": tq, "he_so_co": he_so_co,
            "cov_mau": cov_mau, "cap_nhap": cap_nhap}
