# -*- coding: utf-8 -*-
"""
BACKTEST HỆ THOÁT NHIỀU TẦNG trên nhiều mã. Gốc = T2-3R-ma10 (lãi ≥ 3R → bán theo đóng cửa tuần < MA10 tuần).
  Mỗi lớp được đo RIÊNG so với gốc: cao trào, mua lại, nhồi lệnh (B), bậc thang R, vào MACD không lọc tuần (A0),
  A0 + nghỉ sau lỗ, lọc VN-Index (chặn / ½ KL), nến trần (½ KL / chờ vượt đỉnh / bỏ qua); kèm T0 (cách cũ), T1,
  4 tổ hợp 3R/2R × MA10 tuần/đáy 2 tuần, cách vào "mua ngay khi đủ ĐK".
  Cùng 5 phép thử độ mạnh với backtest_phuong_phap (cham_diem), đo trên % VỐN CỦA MÃ. Bảng xếp theo hạng → KTC 90%
  thấp → Sharpe rổ.

  Đo thêm: giữ được lãi % (lãi thực ÷ MFE, cùng gốc giá mua đầu), bán rồi mua lại cao hơn %, % mua & giữ đạt được ở
  mã ×5, CAGR / MDD / Sharpe rổ chia đều, % thời gian có vị thế (TB mỗi mã); có VN-Index: vượt VNI mỗi lệnh, theo
  trạng thái thị trường, up/down capture; THỬ (< moc_chia) / KIỂM TRA (≥ moc_chia).
  Có A0, B & VN-Index → sheet "Ro gop": CL1 (A0 50% + B 50%) / CL2 (A0 70% + VNI 30%) / đổi theo điểm thị trường
  (chien_luoc.py). Điểm mua hiện tại theo A0 và B.

  from ptcp import backtest_he_thoat
  kq = backtest_he_thoat(["HAH", "DGW", "LPB", ...], start="2019-01-01")          # tự tải giá + VN-Index
  kq = backtest_he_thoat(ds, csv={"HAH": "HAH.csv", ...}, vni_csv="VNINDEX.csv")  # không cần mạng
"""
import os
from dataclasses import asdict
from datetime import date

import numpy as np
import pandas as pd

from . import cau_hinh as cfg
from .backtest_pp import _lam_tron, _tai, bang_ly_do, bang_theo_nam, cham_diem, chuan_ds_ma, TEN_PHEP
from .cau_hinh import BO_QUA_DAU
from .chi_bao import tinh_chi_bao
from .du_lieu import gop_tuan
from .he_thoat import (chuan_bi, danh_sach_bien_the, mo_phong, stop_chuan, tin_hieu_macd, tin_hieu_mua_ngay,
                       trang_thai_tt, HT_MUA_LAI_PHIEN)
from .in_an import fmt, in_ra, ve_bang

COT = "Lãi/lỗ % vốn (sau phí)"
TEN_VAO_HT = {"macd": "MACD ngày (lọc tuần)", "macd0": "MACD ngày (không lọc)", "mua_ngay": "Mua ngay khi đủ ĐK"}
HANG = {"MẠNH": 0, "KHÁ": 1, "YẾU": 2, "KHÔNG CÓ LỢI THẾ": 3, "KHÔNG CÓ LỆNH": 4}


def khoa_vao(bt):
    """Khoá tín hiệu vào của biến thể: 'macd' (lọc tuần), 'macd0' (không lọc), 'mua_ngay'."""
    return "macd0" if bt.vao == "macd" and not bt.loc_tuan else bt.vao
MA_TANG_MANH_PCT = 400.0          # mã mua & giữ > +400% (tăng > 5 lần) → đo % mua & giữ đạt được


def _tai_vni(start, vni_csv, tai_vni):
    try:
        from .du_lieu import tai_vnindex
        if vni_csv or tai_vni:
            v = tai_vnindex(start, vni_csv)
            return v if v is not None and len(v) > 250 else None
    except Exception:
        return None
    return None


def _cagr_mdd(r):
    """r: lợi suất ngày → (CAGR %, MDD %, Sharpe năm)."""
    r = pd.Series(r).fillna(0)
    if not len(r):
        return np.nan, np.nan, np.nan
    v = (1 + r).cumprod()
    nam = max(len(r) / 252, 1e-9)
    cagr = (v.iloc[-1] ** (1 / nam) - 1) * 100
    mdd = ((v / v.cummax()) - 1).min() * 100
    sh = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    return cagr, mdd, sh


def _capture(r_ngay, vni):
    """Up/down capture (%) & beta tháng tăng / tháng giảm của rổ so với VN-Index (lợi suất THÁNG)."""
    if vni is None:
        return {}
    rm = (1 + r_ngay).resample("ME").prod() - 1
    vm = vni.close.resample("ME").last().pct_change()
    x = pd.concat([rm, vm], axis=1, join="inner").dropna()
    x.columns = ["pp", "vni"]
    up, dn = x[x.vni > 0], x[x.vni < 0]
    kq = {}
    if len(up) >= 6 and len(dn) >= 6:
        kq["Up capture %"] = up.pp.mean() / up.vni.mean() * 100
        kq["Down capture %"] = dn.pp.mean() / dn.vni.mean() * 100
        kq["Up/Down"] = kq["Up capture %"] / kq["Down capture %"] if kq["Down capture %"] > 0 else np.nan
        b = lambda s: np.cov(s.pp, s.vni)[0, 1] / s.vni.var() if s.vni.var() > 0 else np.nan
        kq["Beta tháng tăng"], kq["Beta tháng giảm"] = b(up), b(dn)
    return kq


def _ban_roi_mua_lai(g):
    """% lần bán ở tầng ≥ 1 mà lệnh kế tiếp cùng mã mua giá CAO hơn giá vừa bán (trên các cặp lệnh liên tiếp)."""
    dem = cao = 0
    for _, x in g.sort_values("Ngày mua").groupby("Mã"):
        a = x.iloc[:-1]
        b = x.iloc[1:]
        m = (a["Tầng cao nhất"].values >= 1) & ~a["Đang mở"].values.astype(bool)
        dem += m.sum()
        cao += (m & (b["Giá mua"].values > a["Giá bán"].values)).sum()
    return cao / dem * 100 if dem else np.nan


def _them_vni(lenh, vni):
    if vni is None or not len(lenh):
        return lenh
    c = vni.close
    gia = lambda d: c.asof(pd.Timestamp(d))
    lenh["VNI cùng kỳ %"] = [(gia(b) / gia(m) - 1) * 100 for m, b in zip(lenh["Ngày mua"], lenh["Ngày bán"])]
    lenh["Vượt VNI %"] = lenh["Lãi/lỗ % (sau phí)"] - lenh["VNI cùng kỳ %"]
    return lenh


def danh_gia_bien_the(lenh, ret, mua_giu, bts, vni, moc_chia, co_vt=None):
    """Một dòng / biến thể: 5 phép thử + chỉ số bán sớm + đường vốn + VN-Index + chia giai đoạn."""
    moc_chia = pd.Timestamp(moc_chia)
    moc = pd.to_datetime(lenh["Ngày mua"]).quantile(0.5)
    tang_manh = [m for m, v in mua_giu.items() if v == v and v >= MA_TANG_MANH_PCT]
    dong, theo_ma = [], {}
    for bt in bts:
        kv = khoa_vao(bt)
        g = lenh[(lenh["Biến thể"] == bt.ma) & (lenh["Vào"] == kv)]
        if not len(g):
            continue
        k = cham_diem(g, COT, moc=moc)
        tong_ma = g.groupby("Mã")[COT].apply(lambda x: ((1 + x / 100).prod() - 1) * 100)
        theo_ma[f"{bt.ma} | {TEN_VAO_HT[kv]}"] = tong_ma
        vuot_bh = np.mean([tong_ma[m] > mua_giu.get(m, np.inf) for m in tong_ma.index]) * 100
        dat_bh = [tong_ma.get(m, 0) / mua_giu[m] * 100 for m in tang_manh]
        lon = g[g["MFE (R)"] >= 3]
        lai_gia = (lon["Giá bán"] / lon["Giá mua"] - 1) * 100            # cùng gốc giá mua đầu với MFE (kể cả khi nhồi)
        giu = (lai_gia / lon["MFE %"] * 100).median() if len(lon) else np.nan
        tra = (lon["MFE %"] - lai_gia).mean() if len(lon) else np.nan
        thu, kt = g[pd.to_datetime(g["Ngày mua"]) < moc_chia][COT], g[pd.to_datetime(g["Ngày mua"]) >= moc_chia][COT]
        pf = lambda r: r[r > 0].sum() / -r[r <= 0].sum() if (r <= 0).any() and -r[r <= 0].sum() > 0 else np.nan
        r_ro = ret[(kv, bt.ma)]
        cagr, mdd, sh = _cagr_mdd(r_ro)
        dong.append({"Biến thể": bt.ma, "Vào": TEN_VAO_HT[kv], "Mô tả": bt.mo_ta, "Số lệnh": k["n"],
                     "TB/lệnh % vốn": k["tb"], "Trung vị %": k["trung_vi"], "Thắng %": k["thang"], "PF": k["pf"],
                     "KTC90 thấp %": k["ktc_lo"], "KTC90 cao %": k["ktc_hi"], "Mã dương %": k["phu"],
                     "Năm dương %": k["nam_duong"], "Nửa sau TB %": k["sau"], "Bỏ top 2% TB %": k["tb_bo_top"],
                     "Đạt (5 phép)": k["so_dat"], "Xếp hạng": k["hang"],
                     f"Thử (<{moc_chia:%Y}) TB %": thu.mean() if len(thu) else np.nan, f"Thử PF": pf(thu),
                     f"Kiểm tra (≥{moc_chia:%Y}) TB %": kt.mean() if len(kt) else np.nan, "Kiểm tra PF": pf(kt),
                     "Số lệnh thử": len(thu), "Số lệnh kiểm tra": len(kt),
                     "Tổng TB/mã %": tong_ma.mean(), "Vượt mua&giữ % mã": vuot_bh,
                     "% mua&giữ đạt được (mã ×5)": np.median(dat_bh) if dat_bh else np.nan,
                     "Giữ được lãi % (lệnh ≥3R)": giu, "Trả lại TB % (lệnh ≥3R)": tra,
                     "Bán rồi mua lại cao hơn %": _ban_roi_mua_lai(g),
                     "Lệnh trễ T+2 %": g["Lý do thoát"].str.contains("trễ").mean() * 100,
                     "Giữ TB phiên": g["Số phiên giữ"].mean(), "Có vị thế % thời gian (TB mã)": (co_vt or {}).get((kv, bt.ma), np.nan),
                     "CAGR rổ %": cagr, "MDD rổ %": mdd, "Sharpe rổ": sh,
                     "Vượt VNI/lệnh %": g["Vượt VNI %"].mean() if "Vượt VNI %" in g else np.nan,
                     **_capture(r_ro, vni), "_dat": k["dat"], "_vao": kv, "_cach": k["cach"]})
    bang = pd.DataFrame(dong)
    # xếp: hạng (MẠNH → YẾU), rồi KTC 90% thấp (độ chắc chắn của lợi thế), rồi Sharpe rổ
    bang = bang.assign(_h=bang["Xếp hạng"].map(HANG)).sort_values(["_h", "KTC90 thấp %", "Sharpe rổ"],
                                                                 ascending=[True, False, False])
    bang = bang.drop(columns="_h").reset_index(drop=True)
    bm = pd.DataFrame(theo_ma)
    bm["Mua & giữ %"] = pd.Series(mua_giu)
    return bang, bm


def diem_mua_hien_tai(cuoi):
    """Bảng điểm mua / vị thế tại phiên cuối theo trạng thái cuối của bộ mô phỏng."""
    rows = []
    for ma, (cu, x) in cuoi.items():
        c, atr, n = x["c"], x["atr"], len(x["c"])
        r = {"Mã": ma, "Giá đóng cửa": c[-1], "Ngày": x["idx"][-1], "TT thị trường": x["tt"][-1]}
        vt = cu["vi_the"]
        if vt is not None:
            r.update({"Trạng thái": "ĐANG GIỮ" + (" → BÁN phiên tới (đóng cửa tuần < MA10 tuần)"
                                                   if vt["Bán phiên tới (MA10 tuần)"] else ""),
                      "Cắt lỗ phiên tới": vt["Cắt lỗ phiên tới"], "Tầng": vt["Tầng"], "Ngày mua": vt["Ngày mua"],
                      "Giá mua": vt["Giá mua"], "Lãi hiện tại %": vt["Lãi hiện tại %"], "Lãi (R)": vt["Lãi (R)"],
                      "Số lần nhồi": vt["Số lần nhồi"], "Tín hiệu": vt["Tín hiệu"], "KL (phần vốn)": vt.get("KL (phần vốn)"),
                      "Khoá lãi bậc thang (R)": vt.get("Khoá lãi bậc thang (R)"),
                      "Mốc R kế tiếp": vt.get("Mốc R kế tiếp"), "Giá mốc kế tiếp": vt.get("Giá mốc kế tiếp")})
        elif cu["cho_vao"] is not None and cu["cho_vao"]["j_mua"] == n:
            cv = cu["cho_vao"]
            if cv["kind"] == "Mua lại":
                stop = max(cv["day_tu"], c[-1] * (1 - cfg.LO_CUNG_PCT / 100))
                stop = min(stop, c[-1] - cfg.STOP_ATR_MIN * atr[-1])
            else:
                stop = stop_chuan(c[-1], atr[-1])
            r.update({"Trạng thái": f"MUA phiên tới (giá mở cửa) – {cv['kind']}", "Tín hiệu": cv["kind"],
                      "Khối lượng (phần vốn)": cv["kl"], "Cắt lỗ dự kiến": stop,
                      "Rủi ro % (theo giá đóng cửa)": (1 - stop / c[-1]) * 100,
                      "Nến trần": cv["tran"]})
        elif cu["cho_tran"] is not None:
            r.update({"Trạng thái": f"CHỜ đóng cửa vượt đỉnh phiên trần {cu['cho_tran']['h']:.2f} "
                                    f"(còn {cu['cho_tran']['het'] - (n - 1)} phiên)"})
        else:
            tr = cu["truoc"]
            if cu.get("mua_lai") and tr is not None and tr["tang"] >= 1 and (n - 1) - tr["j_ban"] <= HT_MUA_LAI_PHIEN:
                r.update({"Trạng thái": f"CHỜ – mua lại nếu đóng cửa > {tr['dinh']:.2f} (đỉnh lệnh cũ, còn "
                                        f"{HT_MUA_LAI_PHIEN - ((n - 1) - tr['j_ban'])} phiên)"})
            else:
                r.update({"Trạng thái": "CHỜ tín hiệu"})
        rows.append(r)
    b = pd.DataFrame(rows)
    thu_tu = b["Trạng thái"].str.startswith("MUA").map({True: 0, False: 2}) - b["Trạng thái"].str.startswith(
        "ĐANG").astype(int)
    return b.assign(_k=thu_tu).sort_values(["_k", "Mã"]).drop(columns="_k").reset_index(drop=True)


def ket_luan_ht(bang, mua_giu, co_vni, moc_chia, goc):
    b = bang.set_index(["Biến thể", "Vào"])
    M, M0, MN = TEN_VAO_HT["macd"], TEN_VAO_HT["macd0"], TEN_VAO_HT["mua_ngay"]
    lay = lambda ma, vao=M: b.loc[(ma, vao)] if (ma, vao) in b.index else None
    dong = []
    tot = bang.iloc[0]
    thieu = [ten for k, ten in TEN_PHEP if not tot["_dat"][k]]
    dong.append(f"Đứng đầu (hạng → KTC thấp → Sharpe): {tot['Biến thể']} ({tot['Vào']}) – {tot['Xếp hạng']} "
                f"{tot['Đạt (5 phép)']}/5, TB/lệnh {tot['TB/lệnh % vốn']:+.2f}% vốn, KTC 90% theo quý "
                f"{tot['KTC90 thấp %']:+.2f} … {tot['KTC90 cao %']:+.2f}%, CAGR rổ {fmt(tot['CAGR rổ %'], 1)}%, "
                f"MDD {fmt(tot['MDD rổ %'], 1)}%" + (f"; trượt: {', '.join(thieu)}." if thieu else "."))
    g0 = lay(goc)
    if g0 is not None and lay("T0") is not None:
        t0 = lay("T0")
        dong.append(f"Gốc {goc} so với cách cũ T0: TB/lệnh {t0['TB/lệnh % vốn']:+.2f}% → {g0['TB/lệnh % vốn']:+.2f}%, "
                    f"tổng/mã {t0['Tổng TB/mã %']:+.0f}% → {g0['Tổng TB/mã %']:+.0f}%, CAGR {fmt(t0['CAGR rổ %'], 1)}% → "
                    f"{fmt(g0['CAGR rổ %'], 1)}%, MDD {fmt(t0['MDD rổ %'], 1)}% → {fmt(g0['MDD rổ %'], 1)}%.")
    rieng = [(ten, lay(m, v)) for ten, m, v in (
        ("cao trào", "T2+caoTrao", M), ("mua lại", "T2+muaLai", M), ("nhồi lệnh (B)", "B", M),
        ("bậc thang R", f"{goc}+bac", M), ("vào KHÔNG lọc tuần (A0)", "A0", M0), ("A0 + nghỉ 10 phiên sau lỗ", "A0+nghi10", M0),
        ("chặn khi VNI giảm", "T2-ttChan", M), ("½ KL khi VNI giảm", "T2-ttGiamKL", M),
        ("nến trần ½ KL", "T2-tranB", M), ("nến trần chờ vượt đỉnh", "T2-tranC", M), ("nến trần bỏ qua", "T2-tranD", M))
        if lay(m, v) is not None]
    if g0 is not None and rieng:
        dong.append(f"Tác dụng RIÊNG từng lớp so với gốc (CAGR {fmt(g0['CAGR rổ %'], 1)}%, MDD {fmt(g0['MDD rổ %'], 1)}%, "
                    f"Sharpe {fmt(g0['Sharpe rổ'])}): " + " | ".join(
                        f"{ten}: CAGR {r['CAGR rổ %'] - g0['CAGR rổ %']:+.1f}, MDD {r['MDD rổ %'] - g0['MDD rổ %']:+.1f}, "
                        f"Sharpe {r['Sharpe rổ'] - g0['Sharpe rổ']:+.2f}" for ten, r in rieng)
                    + " (điểm %; MDD dương = sụt giảm nhẹ hơn).")
    t2 = bang[bang["Biến thể"].str.match(r"T2-\dR-") & ~bang["Biến thể"].str.contains("bac") & (bang["Vào"] == M)]
    if len(t2):
        dong.append("Ngưỡng & kiểu khung tuần: " + " | ".join(
            f"{r['Biến thể']} CAGR {fmt(r['CAGR rổ %'], 1)}%, MDD {fmt(r['MDD rổ %'], 1)}%" for _, r in t2.iterrows()) + ".")
    cot_thu = [c for c in bang.columns if c.startswith("Thử (")][0]
    cot_kt = [c for c in bang.columns if c.startswith("Kiểm tra (")][0]
    ung = bang[bang["Số lệnh thử"] >= 30]
    if len(ung):
        chon = ung.sort_values(cot_thu, ascending=False).iloc[0]
        t0 = lay("T0")
        dong.append(f"Chọn trên giai đoạn thử (<{pd.Timestamp(moc_chia):%Y}): {chon['Biến thể']} ({chon['Vào']}, TB "
                    f"{chon[cot_thu]:+.2f}%) → giai đoạn kiểm tra {fmt(chon[cot_kt], 2, True)}%/lệnh"
                    + (f" so với T0 {fmt(t0[cot_kt], 2, True)}%" if t0 is not None else "")
                    + (" – GIỮ ĐƯỢC ngoài mẫu." if t0 is not None and chon[cot_kt] > t0[cot_kt]
                       else " – KHÔNG giữ được ngoài mẫu, thận trọng." if t0 is not None else "."))
    mn = [(m, lay(m, MN)) for m in ("T0", goc)]
    mn = [(m, r) for m, r in mn if r is not None]
    if mn:
        dong.append("Vào 'Mua ngay khi đủ ĐK': " + " → ".join(
            f"{m} CAGR {fmt(r['CAGR rổ %'], 1)}%, MDD {fmt(r['MDD rổ %'], 1)}%" for m, r in mn) + ".")
    bh = pd.Series(mua_giu).dropna()
    if len(bh):
        dong.append(f"Mua & giữ: trung vị {bh.median():+.0f}%, {(bh >= MA_TANG_MANH_PCT).sum()} mã tăng > 5 lần "
                    f"({', '.join(bh[bh >= MA_TANG_MANH_PCT].sort_values(ascending=False).index[:6])}).")
    dong.append("Lưu ý: danh sách mã chọn ở hiện tại (thiên lệch mã sống sót); tham số dùng số tròn; đơn vị % VỐN CỦA "
                "MÃ (B lô đầu chỉ 50% vốn); kết quả nhạy với phí giao dịch (mặc định 0,6% khứ hồi gồm trượt giá).")
    return dong


def backtest_he_thoat(ds_ma, start="2019-01-01", n_phien=63, csv=None, vni_csv=None, tai_vni=True,
                      moc_chia="2023-01-01", goc_tuan=(3, "ma10"), vao_phu=True, bien_the=None, bt_diem_mua=("A0", "B"),
                      ve_ma=None, xuat_excel=True, in_ket_qua=True, thu_muc="."):
    """
    Chạy các biến thể hệ thoát trên danh sách mã. csv: {mã: file CSV}; vni_csv: file CSV VN-Index (tuỳ chọn).
    goc_tuan: (ngưỡng R, "ma10"|"day2") làm gốc. bt_diem_mua: mã biến thể (hoặc nhiều) lập bảng điểm mua hiện tại
    (vào MACD lọc tuần hoặc không lọc theo biến thể). ve_ma: danh sách mã vẽ biểu đồ đường cắt lỗ T0 vs biến thể đầu
    của bt_diem_mua (mặc định: 2 mã mua & giữ tốt nhất + 1 mã kém nhất). Trả dict: bang, lenh, theo_ma, theo_nam,
    theo_tt, ly_do, diem_mua {biến thể: bảng}, von, ro_gop (khi có A0, B & VN-Index), ret_ro, vni, gia, ket_luan, …
    """
    ds = chuan_ds_ma(ds_ma)
    if in_ket_qua and len(ds) < len(ds_ma):
        in_ra(f"  ⚠ Bỏ {len(ds_ma) - len(ds)} mã nhập trùng.")
    vni = _tai_vni(start, vni_csv, tai_vni)
    tt = trang_thai_tt(vni) if vni is not None else None
    bts = bien_the or danh_sach_bien_the(co_vni=tt is not None, goc_tuan=goc_tuan, vao_phu=vao_phu)
    goc = f"T2-{goc_tuan[0]:g}R-{goc_tuan[1]}"
    ds_diem = [bt_diem_mua] if isinstance(bt_diem_mua, str) else list(bt_diem_mua or [])
    bt_ve = ds_diem[0] if ds_diem else goc
    can = {khoa_vao(b) for b in bts}
    tat_ca, ret, expo, mua_giu, loi, cuoi, du_lieu, gia = [], {}, {}, {}, {}, {m: {} for m in ds_diem}, {}, {}
    if in_ket_qua:
        in_ra(f"  VN-Index: {'có ' + str(len(vni)) + ' phiên' if vni is not None else 'KHÔNG có → bỏ biến thể thị trường'}")
    for ma in ds:
        try:
            df = _tai(ma, start, csv)
            if df is None or len(df) < 300:
                raise ValueError("dữ liệu < 300 phiên")
            df = df[["open", "high", "low", "close", "volume"]]
            d, w = tinh_chi_bao(df), tinh_chi_bao(gop_tuan(df))
            x = chuan_bi(d, tt)
            sig = {}
            if "macd" in can:
                sig["macd"] = tin_hieu_macd(d, w)
            if "macd0" in can:
                sig["macd0"] = tin_hieu_macd(d, w, loc_tuan=False)
            if "mua_ngay" in can:
                sig["mua_ngay"] = tin_hieu_mua_ngay(d, w)
            gia[ma] = d.close
            i0 = BO_QUA_DAU + 30
            mua_giu[ma] = (x["c"][-1] / x["c"][i0] - 1) * 100
            for bt in bts:
                i0_bt = max(i0, getattr(cfg, "VM_SO_PHIEN_NHIP", 120)) if bt.vao == "mua_ngay" else i0
                kv = khoa_vao(bt)
                r = mo_phong(x, sig[kv], bt, n_phien, i0_bt, ghi_duong=True)
                if r["lenh"]:
                    t = pd.DataFrame(r["lenh"])
                    t.insert(0, "Mã", ma)
                    t.insert(1, "Vào", kv)
                    t.insert(2, "Biến thể", bt.ma)
                    tat_ca.append(t)
                ret.setdefault((kv, bt.ma), {})[ma] = pd.Series(r["ret"], index=d.index)
                expo.setdefault((kv, bt.ma), {})[ma] = float((r["expo"][i0_bt:] > 0).mean() * 100)
                if bt.vao != "mua_ngay" and bt.ma in cuoi:
                    cuoi[bt.ma][ma] = (r["cuoi"], x)
                if bt.vao != "mua_ngay" and bt.ma in ("T0", bt_ve):
                    du_lieu.setdefault(ma, {"d": d})[bt.ma] = (r["duong"], r["lenh"])
            if in_ket_qua:
                in_ra(f"  ✔ {ma}: {len(df)} phiên")
        except Exception as e:
            loi[ma] = str(e)[:100]
            if in_ket_qua:
                in_ra(f"  ⚠ bỏ qua {ma}: {loi[ma]}")
    if not tat_ca:
        return None
    lenh = _them_vni(pd.concat(tat_ca, ignore_index=True), vni)
    ret_ro = {k: pd.DataFrame(v).fillna(0).mean(axis=1) for k, v in ret.items()}
    bh_ngay = pd.DataFrame({m: v["d"].close.pct_change().iloc[BO_QUA_DAU + 31:] for m, v in du_lieu.items()}) \
        .fillna(0).mean(axis=1).sort_index() if du_lieu else None
    co_vt = {k: float(np.mean(list(v.values()))) for k, v in expo.items()}
    bang, theo_ma = danh_gia_bien_the(lenh, ret_ro, mua_giu, bts, vni, moc_chia, co_vt)
    if bh_ngay is not None and len(bh_ngay):
        cagr, mdd, sh = _cagr_mdd(bh_ngay)
        bang.attrs["mua_giu_ro"] = {"CAGR %": cagr, "MDD %": mdd, "Sharpe": sh, **_capture(bh_ngay, vni)}
    if vni is not None and bh_ngay is not None and len(bh_ngay):
        rv = vni.close.pct_change().loc[bh_ngay.index[0]:bh_ngay.index[-1]]
        bang.attrs["vni"] = dict(zip(("CAGR %", "MDD %", "Sharpe"), _cagr_mdd(rv)))
    theo_nam = bang_theo_nam(lenh, khoa=("Vào", "Biến thể"), cot=COT, doi_ten={"Vào": TEN_VAO_HT.get})
    ly_do = bang_ly_do(lenh, khoa=("Vào", "Biến thể"), cot=COT, doi_ten={"Vào": TEN_VAO_HT.get})
    theo_tt = None
    if vni is not None:
        theo_tt = lenh.groupby(["Vào", "Biến thể", "TT lúc mua"]).agg(**{
            "Số lệnh": (COT, "count"), "TB % vốn": (COT, "mean"), "Thắng %": (COT, lambda r: (r > 0).mean() * 100),
            "Vượt VNI TB %": ("Vượt VNI %", "mean")}).reset_index()
        theo_tt["Vào"] = theo_tt["Vào"].map(TEN_VAO_HT)
    von = pd.DataFrame({f"{m} | {TEN_VAO_HT[v]}": (1 + r).cumprod() for (v, m), r in ret_ro.items()})
    if bh_ngay is not None:
        von["Mua & giữ rổ"] = (1 + bh_ngay).cumprod()
    if vni is not None:
        von["VNINDEX"] = vni.close.reindex(von.index).ffill() / vni.close.reindex(von.index).ffill().dropna().iloc[0]
    von = von.resample("ME").last()
    diem = {m: diem_mua_hien_tai(c) for m, c in cuoi.items() if c}
    kl = ket_luan_ht(bang, mua_giu, vni is not None, moc_chia, goc)
    ro = None
    if vni is not None and ("macd0", "A0") in ret_ro and ("macd", "B") in ret_ro:
        from .chien_luoc import bang_chi_bao, lich_chien_luoc, so_sanh_ro
        F, diem_tt, _ = bang_chi_bao(vni, pd.DataFrame(gia))
        _, cl_ngay, _ = lich_chien_luoc(diem_tt)
        r_a0 = ret_ro[("macd0", "A0")]
        cl_ngay = cl_ngay[(cl_ngay.index >= r_a0.index[0] + pd.Timedelta(days=90)) & (cl_ngay.index <= r_a0.index[-1])]
        ro, ro_nam, _ = so_sanh_ro({"A0": r_a0, "B": ret_ro[("macd", "B")], "VNI": vni.close.pct_change()}, cl_ngay,
                                   moc_chia)
        kl.insert(1, "Rổ theo thị trường (A0/B/VN-Index, đổi CL1/CL2 theo điểm 8 chỉ báo): " + " | ".join(
            f"{r['Cách']}: CAGR {fmt(r['CAGR %'], 1)}%, MDD {fmt(r['MDD %'], 1)}%, Sharpe {fmt(r['Sharpe'])}"
            for _, r in ro.iterrows()) + ". Bản tin hằng tháng: chien_luoc_thang().")
    kq = {"bang": bang, "lenh": lenh, "theo_ma": theo_ma, "theo_nam": theo_nam, "theo_tt": theo_tt, "ly_do": ly_do,
          "diem_mua": diem, "von": von, "ket_luan": kl, "loi": loi, "ds_ma": list(mua_giu), "bien_the": bts,
          "file_excel": None, "bieu_do": [], "ro_gop": ro, "ret_ro": ret_ro, "vni": vni, "gia": pd.DataFrame(gia)}
    if ve_ma is None and mua_giu:
        s = pd.Series(mua_giu).sort_values()
        ve_ma = list(s.index[::-1][:2]) + [s.index[0]]
    kq["bieu_do"] = ve_bieu_do(du_lieu, ve_ma or [], bt_ve, thu_muc) if ve_ma else []
    if in_ket_qua:
        in_tong_hop_ht(kq)
    if xuat_excel:
        kq["file_excel"] = xuat_excel_ht(kq, os.path.join(thu_muc, f"backtest_he_thoat_{date.today():%Y%m%d}.xlsx"))
        if in_ket_qua:
            in_ra(f"  ✔ Đã xuất {kq['file_excel']}" + (f" + {len(kq['bieu_do'])} biểu đồ" if kq["bieu_do"] else ""))
    return kq


def ve_bieu_do(du_lieu, ds_ma, bt_so_sanh="A0", thu_muc="."):
    """Giá + đường cắt lỗ T0 và biến thể so sánh, điểm mua/bán – thấy ngay chỗ bán sớm / giữ quá lâu."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return []
    ra = []
    for ma in ds_ma:
        if ma not in du_lieu or "T0" not in du_lieu[ma] or bt_so_sanh not in du_lieu[ma]:
            continue
        d = du_lieu[ma]["d"]
        fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
        for a, k, mau in ((ax[0], "T0", "#C62828"), (ax[1], bt_so_sanh, "#1B5E20")):
            duong, lenh = du_lieu[ma][k]
            a.plot(d.index, d.close, color="#455A64", lw=0.9, label="Giá đóng cửa")
            a.plot(d.index, duong, color=mau, lw=1.0, label=f"Cắt lỗ {k}")
            if k != "T0":
                tuan = d.index.to_period("W-FRI")
                ma10 = d.close.groupby(tuan).last().rolling(10).mean().reindex(tuan).values
                a.plot(d.index, ma10, color="#F9A825", lw=0.8, ls="--", label="MA10 tuần")
            for L in lenh:
                a.scatter(L["Ngày mua"], L["Giá mua"], marker="^", color="#2E7D32", s=28, zorder=3)
                a.scatter(L["Ngày bán"], L["Giá bán"], marker="v", color="#C62828", s=28, zorder=3)
            tong = (np.prod([1 + L["Lãi/lỗ % vốn (sau phí)"] / 100 for L in lenh]) - 1) * 100
            a.set_title(f"{ma} – {k}: {len(lenh)} lệnh, tổng {tong:+.0f}% "
                        f"(mua & giữ {(d.close.iloc[-1] / d.close.iloc[BO_QUA_DAU + 30] - 1) * 100:+.0f}%)",
                        fontsize=10, color="#1B5E20")
            a.set_yscale("log")
            a.grid(alpha=0.3)
            a.legend(loc="upper left", fontsize=8)
        fig.tight_layout()
        p = os.path.join(thu_muc, f"bieu_do_thoat_{ma}.png")
        fig.savefig(p, dpi=110)
        plt.close(fig)
        ra.append(p)
    return ra


def in_tong_hop_ht(kq):
    b = kq["bang"]
    in_ra(f"\n{'#' * 84}\n BACKTEST HỆ THOÁT NHIỀU TẦNG – {len(kq['ds_ma'])} mã\n{'#' * 84}")
    cot = ["Biến thể", "Vào", "Số lệnh", "TB/lệnh % vốn", "PF", "KTC90 thấp %", "Đạt (5 phép)", "Xếp hạng",
           "Tổng TB/mã %", "% mua&giữ đạt được (mã ×5)", "Giữ được lãi % (lệnh ≥3R)", "Bán rồi mua lại cao hơn %",
           "CAGR rổ %", "MDD rổ %", "Sharpe rổ"] + [c for c in b.columns if c.startswith(("Thử (", "Kiểm tra ("))] + \
        [c for c in ("Down capture %",) if c in b.columns]
    in_ra(ve_bang(_lam_tron(b[cot])))
    if "mua_giu_ro" in b.attrs:
        m = b.attrs["mua_giu_ro"]
        in_ra(f"  Mua & giữ rổ chia đều: CAGR {fmt(m['CAGR %'], 1)}%, MDD {fmt(m['MDD %'], 1)}%"
              + (f" | VN-Index: CAGR {fmt(b.attrs['vni']['CAGR %'], 1)}%, MDD {fmt(b.attrs['vni']['MDD %'], 1)}%"
                 if "vni" in b.attrs else ""))
    if kq.get("ro_gop") is not None:
        in_ra("\n  RỔ THEO THỊ TRƯỜNG (CL1 = A0 50% + B 50% · CL2 = A0 70% + VNI 30% · đổi theo điểm 8 chỉ báo):")
        in_ra(ve_bang(kq["ro_gop"].round(2)))
    for ten, dm in kq["diem_mua"].items():
        hien = dm[[c for c in ("Mã", "Trạng thái", "Giá đóng cửa", "Cắt lỗ dự kiến", "Cắt lỗ phiên tới", "Tầng",
                                "Lãi hiện tại %") if c in dm.columns]]
        hien = hien[~hien["Trạng thái"].eq("CHỜ tín hiệu")]
        if len(hien):
            in_ra(f"\n  ĐIỂM MUA / VỊ THẾ HIỆN TẠI – {ten}:")
            in_ra(ve_bang(hien))
    in_ra(f"  {'─' * 80}\n  KẾT LUẬN")
    for i, d in enumerate(kq["ket_luan"], 1):
        in_ra(f"   {i}. {d}")
    if kq["loi"]:
        in_ra(f"  ⚠ Bỏ qua: {', '.join(f'{m} ({e})' for m, e in kq['loi'].items())}")


def xuat_excel_ht(kq, path):
    with pd.ExcelWriter(path) as w:
        pd.DataFrame({"Kết luận": kq["ket_luan"]}).to_excel(w, sheet_name="Ket luan", index=False)
        b = kq["bang"]
        b.drop(columns=[c for c in b.columns if c.startswith("_")]).to_excel(w, sheet_name="Tong hop", index=False)
        if kq.get("ro_gop") is not None:
            kq["ro_gop"].to_excel(w, sheet_name="Ro gop", index=False)
        for ten, dm in kq["diem_mua"].items():
            dm.to_excel(w, sheet_name=f"Diem mua {ten}"[:31], index=False)
        kq["theo_nam"].to_excel(w, sheet_name="Theo nam", index=False)
        if kq["theo_tt"] is not None:
            kq["theo_tt"].to_excel(w, sheet_name="Theo thi truong", index=False)
        kq["ly_do"].to_excel(w, sheet_name="Ly do thoat", index=False)
        kq["theo_ma"].to_excel(w, sheet_name="Tong theo ma")
        kq["von"].to_excel(w, sheet_name="Duong von thang")
        pd.DataFrame([{**asdict(bt), "vao": TEN_VAO_HT[khoa_vao(bt)]} for bt in kq["bien_the"]]) \
            .to_excel(w, sheet_name="Bien the", index=False)
        l = kq["lenh"].copy()
        l["Vào"] = l["Vào"].map(TEN_VAO_HT)
        l.to_excel(w, sheet_name="Chi tiet lenh", index=False)
    try:
        from .excel_xanh import trang_tri_excel
        trang_tri_excel(path)
    except Exception:
        pass
    return path
