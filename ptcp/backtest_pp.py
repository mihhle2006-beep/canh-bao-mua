# -*- coding: utf-8 -*-
"""
BACKTEST PHƯƠNG PHÁP TRÊN NHIỀU MÃ – thử ĐỘ MẠNH của các cách vào/thoát lệnh ở Phần I.

Khác backtest_nhieu_ma() (chạy lại TOÀN BỘ lõi khuyến nghị, ~2–4 phút/mã): hàm này chỉ chạy các quy tắc của Phần I
nên rất nhanh (vài giây/mã, chủ yếu là thời gian tải dữ liệu) → thử được 20–50 mã.

  Tổ hợp thử (cùng luật VN: T+2, trần/sàn, phí, trượt giá):
    VÀO : Tín hiệu MACD ngày (có lọc tuần) · MACD không lọc tuần · Mua ngay khi đủ điều kiện · Chờ về vùng mua
    THOÁT: Cố định R/R 2 · Cắt lỗ động · Chốt từng phần + cắt lỗ động
  Độ mạnh được đo bằng 5 phép thử:
    1. TB/lệnh gộp > 0 và PF gộp > 1,2
    2. KTC 90% của TB/lệnh (bootstrap THEO MÃ khi ≥ 5 mã – các lệnh cùng mã không độc lập) nằm trên 0
    3. Độ phủ: ≥ 60% số mã (có ≥ 3 lệnh) có TB/lệnh > 0 – không chỉ nhờ 1–2 mã
    4. Ổn định thời gian: nửa đầu VÀ nửa sau giai đoạn đều có TB/lệnh > 0
    5. So với mua & giữ: % số mã mà tổng lãi theo phương pháp > mua & giữ

  from ptcp import backtest_phuong_phap
  kq = backtest_phuong_phap(["GMD", "HAH", "VSC", "PHP", "MWG", "DHC", "VPB", "FPT", "HPG", "VNM"])
"""
from datetime import date

import numpy as np
import pandas as pd

from .bo_sung import backtest_quy_tac
from .cau_hinh import RR_NGUONG
from . import cau_hinh as cfg
from .chi_bao import tinh_chi_bao
from .du_lieu import _tai_ngay, chuan_hoa, gop_tuan, tu_csv
from .in_an import fmt, in_ra, ve_bang
from .vung_mua import backtest_vung_mua

THOAT = ("co_dinh", "dong", "tung_phan", "dong_63")
TEN_VAO = {"macd": "MACD ngày (lọc tuần)", "macd_0": "MACD ngày (không lọc)", "mua_ngay": "Mua ngay khi đủ ĐK",
           "vung": "Chờ vùng mua + xác nhận"}
SO_LENH_MA_TOI_THIEU = 3


def _ten_thoat(k):
    gh = " + gia hạn" if cfg.GIA_HAN_LENH else ""
    return {"co_dinh": f"Cố định R/R {RR_NGUONG:g}", "dong": f"Cắt lỗ động {cfg.TRAILING_ATR:g}×ATR{gh}",
            "tung_phan": f"Chốt {cfg.CHOT_TUNG_PHAN_PCT:g}% + động{gh}",
            "dong_63": f"Cắt lỗ động {cfg.TRAILING_ATR:g}×ATR hết hạn cứng"}[k]


def _tai(ma, start, csv):
    if csv and ma in csv:
        df = chuan_hoa(tu_csv(csv[ma]))
        return df[df.index >= pd.Timestamp(start)]
    return _tai_ngay(ma, start, "NGÀY")


def chay_mot_ma(ma, df, n_phien=63):
    """Mọi tổ hợp vào × thoát trên 1 mã → (danh sách lệnh, mua & giữ %)."""
    d = tinh_chi_bao(df[["open", "high", "low", "close", "volume"]].copy())
    w = tinh_chi_bao(gop_tuan(df[["open", "high", "low", "close", "volume"]]))
    kq = {}
    for k in THOAT:
        kq[("macd", k)] = backtest_quy_tac(d, w, n_phien, loc_tuan=True, thoat=k)
        r = backtest_vung_mua(d, w, n_phien, thoat=k)
        kq[("vung", k)], kq[("mua_ngay", k)] = r["vung"], r["mua_ngay"]
    kq[("macd_0", "co_dinh")] = backtest_quy_tac(d, w, n_phien, loc_tuan=False, thoat="co_dinh")
    lenh, bh = [], np.nan
    for (vao, thoat), b in kq.items():
        if b.get("so_lenh"):
            bh = b["buy_hold"]
            t = b["bang"].copy()
            t.insert(0, "Mã", ma)
            t.insert(1, "Vào", vao)
            t.insert(2, "Thoát", thoat)
            lenh.append(t)
    return (pd.concat(lenh, ignore_index=True) if lenh else pd.DataFrame()), bh


def _thong_ke(r):
    r = np.asarray(r, float)
    if not len(r):
        return {"n": 0}
    lai, lo = r[r > 0].sum(), -r[r <= 0].sum()
    return {"n": len(r), "tb": r.mean(), "trung_vi": float(np.median(r)), "thang": (r > 0).mean() * 100,
            "pf": lai / lo if lo > 0 else np.nan}


def _ktc_bootstrap(g, so_lan=2000, seed=0):
    """KTC 90% của TB/lệnh: lấy mẫu lại THEO MÃ (cụm) nếu ≥ 5 mã, ngược lại theo lệnh."""
    rng = np.random.default_rng(seed)
    r = g["Lãi/lỗ % (sau phí)"].values
    ma = g["Mã"].values
    nhom = [r[ma == m] for m in pd.unique(ma)]
    tb = []
    if len(nhom) >= 5:
        for _ in range(so_lan):
            chon = rng.integers(0, len(nhom), len(nhom))
            x = np.concatenate([nhom[i] for i in chon])
            tb.append(x.mean())
        cach = "theo mã"
    else:
        for _ in range(so_lan):
            tb.append(rng.choice(r, len(r)).mean())
        cach = "theo lệnh"
    return np.percentile(tb, 5), np.percentile(tb, 95), cach


def danh_gia(lenh, mua_giu):
    """Bảng gộp mỗi tổ hợp + bảng TB/lệnh theo mã + xếp hạng độ mạnh."""
    if not len(lenh):
        return None
    moc = lenh["Ngày mua"].quantile(0.5)
    dong, theo_ma = [], {}
    for (vao, thoat), g in lenh.groupby(["Vào", "Thoát"], sort=False):
        s = _thong_ke(g["Lãi/lỗ % (sau phí)"])
        lo95, hi95, cach = _ktc_bootstrap(g)
        tm = g.groupby("Mã")["Lãi/lỗ % (sau phí)"].agg(["mean", "count"])
        du = tm[tm["count"] >= SO_LENH_MA_TOI_THIEU]
        phu = (du["mean"] > 0).mean() * 100 if len(du) else np.nan
        dau = _thong_ke(g.loc[g["Ngày mua"] < moc, "Lãi/lỗ % (sau phí)"])
        sau = _thong_ke(g.loc[g["Ngày mua"] >= moc, "Lãi/lỗ % (sau phí)"])
        tong_ma = g.groupby("Mã")["Lãi/lỗ % (sau phí)"].apply(lambda x: ((1 + x / 100).prod() - 1) * 100)
        vuot_bh = np.mean([tong_ma[m] > mua_giu.get(m, np.inf) for m in tong_ma.index]) * 100
        dat = {"tb_pf": s["tb"] > 0 and s["pf"] == s["pf"] and s["pf"] > 1.2, "ktc": lo95 > 0,
               "phu": phu == phu and phu >= 60, "on_dinh": dau.get("tb", -1) > 0 and sau.get("tb", -1) > 0}
        so_dat = sum(dat.values())
        if s["tb"] <= 0:
            hang = "KHÔNG CÓ LỢI THẾ"
        elif so_dat == 4:
            hang = "MẠNH"
        elif so_dat == 3:
            hang = "KHÁ"
        else:
            hang = "YẾU"
        dong.append({"Vào": TEN_VAO[vao], "Thoát": _ten_thoat(thoat), "Số lệnh": s["n"], "Số mã": g["Mã"].nunique(),
                     "TB/lệnh %": s["tb"], "Trung vị %": s["trung_vi"], "Thắng %": s["thang"], "PF": s["pf"],
                     "KTC90 thấp %": lo95, "KTC90 cao %": hi95, "Mã dương %": phu,
                     "Nửa đầu TB %": dau.get("tb", np.nan), "Nửa sau TB %": sau.get("tb", np.nan),
                     "Tổng TB/mã %": tong_ma.mean(), "Giữ TB phiên": g["Số phiên giữ"].mean(),
                     "Vượt mua&giữ % mã": vuot_bh, "Đạt (4 phép)": so_dat, "Xếp hạng": hang,
                     "_vao": vao, "_thoat": thoat, "_dat": dat, "_cach": cach})
        theo_ma[f"{TEN_VAO[vao]} | {_ten_thoat(thoat)}"] = tm["mean"]
    bang = pd.DataFrame(dong).sort_values(["Đạt (4 phép)", "TB/lệnh %"], ascending=False).reset_index(drop=True)
    bang_ma = pd.DataFrame(theo_ma)
    bang_ma["Mua & giữ %"] = pd.Series(mua_giu)
    return {"bang": bang, "theo_ma": bang_ma, "moc_giua": moc}


def ket_luan(dg, ds_ma):
    b = dg["bang"]
    tot = b.iloc[0]
    dong = []
    co = b[b["Xếp hạng"].isin(["MẠNH", "KHÁ"])]
    if tot["Xếp hạng"] == "MẠNH":
        dong.append(f"Phương pháp MẠNH: {tot['Vào']} + {tot['Thoát']} đạt cả 4 phép thử trên {tot['Số mã']} mã "
                    f"({tot['Số lệnh']} lệnh): TB/lệnh {tot['TB/lệnh %']:+.2f}% (KTC 90% {tot['KTC90 thấp %']:+.2f} … "
                    f"{tot['KTC90 cao %']:+.2f}%), PF {fmt(tot['PF'])}, {fmt(tot['Mã dương %'], 0)}% mã có lãi.")
    elif len(co):
        t = co.iloc[0]
        thieu = [ten for k, ten in (("tb_pf", "TB/lệnh & PF"), ("ktc", "KTC trên 0"), ("phu", "độ phủ ≥ 60% mã"),
                                    ("on_dinh", "ổn định 2 nửa")) if not t["_dat"][k]]
        dong.append(f"Chưa có phương pháp MẠNH. Tốt nhất: {t['Vào']} + {t['Thoát']} (KHÁ) – TB/lệnh "
                    f"{t['TB/lệnh %']:+.2f}%, PF {fmt(t['PF'])}, {fmt(t['Mã dương %'], 0)}% mã có lãi; còn thiếu: "
                    f"{', '.join(thieu)}.")
    else:
        dong.append(f"KHÔNG phương pháp nào đủ mạnh trên {len(ds_ma)} mã: tổ hợp tốt nhất "
                    f"({tot['Vào']} + {tot['Thoát']}) chỉ đạt {tot['Đạt (4 phép)']}/4 phép thử, TB/lệnh "
                    f"{tot['TB/lệnh %']:+.2f}%.")
    # so sánh cách vào (cùng thoát cố định) & cách thoát (cùng vào MACD)
    vao = b[b["_thoat"] == "co_dinh"].sort_values("TB/lệnh %", ascending=False)
    if len(vao):
        dong.append("Cách VÀO (thoát cố định): " + " > ".join(f"{r['Vào']} {r['TB/lệnh %']:+.2f}%"
                                                            for _, r in vao.iterrows()) + ".")
    th = b[b["_vao"] == "macd"].sort_values("TB/lệnh %", ascending=False)
    if len(th):
        dong.append("Cách THOÁT (vào MACD): " + " > ".join(f"{r['Thoát']} {r['TB/lệnh %']:+.2f}%"
                                                          for _, r in th.iterrows()) + ".")
    # gia hạn lệnh: cắt lỗ động gia hạn vs hết hạn cứng (cùng điểm vào)
    if cfg.GIA_HAN_LENH:
        ss = []
        for v in ("macd", "mua_ngay", "vung"):
            moi = b[(b["_vao"] == v) & (b["_thoat"] == "dong")]
            cu = b[(b["_vao"] == v) & (b["_thoat"] == "dong_63")]
            if len(moi) and len(cu):
                m, c = moi.iloc[0], cu.iloc[0]
                ss.append(f"{TEN_VAO[v]}: TB/lệnh {c['TB/lệnh %']:+.2f}% → {m['TB/lệnh %']:+.2f}%, tổng TB/mã "
                          f"{c['Tổng TB/mã %']:+.1f}% → {m['Tổng TB/mã %']:+.1f}%, nửa sau {c['Nửa sau TB %']:+.2f}% → "
                          f"{m['Nửa sau TB %']:+.2f}%")
        if ss:
            dong.append(f"Gia hạn lệnh (lãi ≥ {cfg.GIA_HAN_KHI_R:g}R tới hạn → giữ, siết {cfg.SIET_ATR:g}×ATR, tối đa "
                        f"{cfg.HAN_TOI_DA} phiên) so với hết hạn cứng: " + " | ".join(ss) + ".")
    # mã kéo lùi / mã hợp phương pháp
    cot = f"{tot['Vào']} | {tot['Thoát']}"
    if cot in dg["theo_ma"]:
        s = dg["theo_ma"][cot].dropna().sort_values()
        if len(s) >= 2:
            dong.append(f"Với {tot['Vào']} + {tot['Thoát']}: hợp nhất {', '.join(s.index[::-1][:3])}; "
                        f"kém nhất {', '.join(s.index[:3])} (TB/lệnh {s.iloc[0]:+.2f}%).")
    bh = dg["theo_ma"]["Mua & giữ %"]
    dong.append(f"Mua & giữ: {(bh > 0).mean() * 100:.0f}% số mã có lãi, trung vị {bh.median():+.1f}%; tổ hợp tốt "
                f"nhất vượt mua & giữ ở {fmt(tot['Vượt mua&giữ % mã'], 0)}% số mã.")
    return dong


def backtest_phuong_phap(ds_ma, start="2019-01-01", n_phien=63, csv=None, xuat_excel=True, in_ket_qua=True):
    """
    Chạy mọi tổ hợp vào × thoát của Phần I trên danh sách mã, GỘP lại và chấm độ mạnh.
    csv: {mã: đường dẫn CSV} (tuỳ chọn, để chạy không cần mạng). Trả dict: bang, theo_ma, lenh, ket_luan, file_excel.
    Nên dùng ≥ 10 mã thuộc nhiều ngành; mã cùng ngành biến động cùng nhau nên ít "độc lập" hơn số lượng.
    """
    tat_ca, mua_giu, loi = [], {}, {}
    for ma in [m.strip().upper() for m in ds_ma]:
        try:
            df = _tai(ma, start, csv)
            if df is None or len(df) < 300:
                raise ValueError("dữ liệu < 300 phiên")
            lenh, bh = chay_mot_ma(ma, df, n_phien)
            mua_giu[ma] = bh
            if len(lenh):
                tat_ca.append(lenh)
            if in_ket_qua:
                in_ra(f"  ✔ {ma}: {len(df)} phiên, {len(lenh)} lệnh (mọi tổ hợp)")
        except Exception as e:                                       # 1 mã lỗi không làm hỏng cả lượt
            loi[ma] = str(e)[:100]
            if in_ket_qua:
                in_ra(f"  ⚠ bỏ qua {ma}: {loi[ma]}")
    if not tat_ca:
        return None
    lenh = pd.concat(tat_ca, ignore_index=True)
    dg = danh_gia(lenh, mua_giu)
    kl = ket_luan(dg, list(mua_giu))
    kq = {"bang": dg["bang"], "theo_ma": dg["theo_ma"], "lenh": lenh, "ket_luan": kl, "loi": loi,
          "ds_ma": list(mua_giu), "file_excel": None}
    if in_ket_qua:
        in_tong_hop(kq, n_phien, dg["moc_giua"])
    if xuat_excel:
        kq["file_excel"] = xuat_excel_pp(kq, f"backtest_phuong_phap_{date.today():%Y%m%d}.xlsx")
        if in_ket_qua:
            in_ra(f"  ✔ Đã xuất {kq['file_excel']}")
    return kq


def _lam_tron(df):
    """Hiển thị gọn: % và PF 2 chữ số, tỷ lệ % số mã / thắng 0 chữ số (dạng chữ để bảng không đổi định dạng)."""
    d = df.copy()
    for c in d.columns:
        if not pd.api.types.is_float_dtype(d[c]):
            continue
        nguyen = c in ("Thắng %", "Mã dương %", "Vượt mua&giữ % mã")
        dau = not nguyen and c not in ("PF", "Giữ TB phiên")
        d[c] = d[c].map(lambda v: "–" if v != v else (f"{v:.0f}" if nguyen else f"{v:+.2f}" if dau else f"{v:.2f}"))
    return d


def in_tong_hop(kq, n_phien, moc):
    b = kq["bang"]
    in_ra(f"\n{'#' * 84}\n BACKTEST PHƯƠNG PHÁP – {len(kq['ds_ma'])} mã: {', '.join(kq['ds_ma'])}\n"
          f" (giữ tối đa {n_phien} phiên; nửa đầu / nửa sau tách tại {moc:%d/%m/%Y})\n{'#' * 84}")
    hien = b.drop(columns=[c for c in b.columns if c.startswith("_")] + ["Trung vị %", "KTC90 cao %", "Giữ TB phiên"])
    in_ra(ve_bang(_lam_tron(hien), can_phai=[c for c in hien.columns if c not in ('Vào', 'Thoát', 'Xếp hạng')]))
    in_ra(f"  Bootstrap: {b['_cach'].iloc[0]}. Phép thử: (1) TB>0 & PF>1,2 (2) KTC 90% > 0 (3) ≥ 60% mã có lãi "
          f"(mã có ≥ {SO_LENH_MA_TOI_THIEU} lệnh) (4) cả 2 nửa thời gian có lãi. 4/4 = MẠNH, 3/4 = KHÁ.")
    in_ra(f"\n  TB/lệnh % theo mã (3 tổ hợp đứng đầu):")
    top = [f"{r['Vào']} | {r['Thoát']}" for _, r in b.head(3).iterrows()]
    in_ra(ve_bang(_lam_tron(kq["theo_ma"][top + ["Mua & giữ %"]].reset_index().rename(columns={"index": "Mã"})),
                  can_phai=top + ["Mua & giữ %"]))
    in_ra(f"  {'─' * 80}\n  KẾT LUẬN ĐỘ MẠNH PHƯƠNG PHÁP")
    for i, d in enumerate(kq["ket_luan"], 1):
        in_ra(f"   {i}. {d}")
    if kq["loi"]:
        in_ra(f"  ⚠ Bỏ qua: {', '.join(f'{m} ({e})' for m, e in kq['loi'].items())}")


def xuat_excel_pp(kq, path):
    with pd.ExcelWriter(path) as w:
        pd.DataFrame({"Kết luận": kq["ket_luan"]}).to_excel(w, sheet_name="Ket luan", index=False)
        kq["bang"].drop(columns=[c for c in kq["bang"].columns if c.startswith("_")]) \
            .to_excel(w, sheet_name="Tong hop", index=False)
        kq["theo_ma"].to_excel(w, sheet_name="TB theo ma")
        l = kq["lenh"].copy()
        l["Vào"] = l["Vào"].map(TEN_VAO)
        l["Thoát"] = l["Thoát"].map(_ten_thoat)
        l.to_excel(w, sheet_name="Chi tiet lenh", index=False)
    try:
        from .excel_xanh import trang_tri_excel
        trang_tri_excel(path)
    except Exception:
        pass
    return path
