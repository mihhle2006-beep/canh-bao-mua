# -*- coding: utf-8 -*-
"""
PHẦN J – PHÂN TÍCH KIỂU FIINTRADE CHO 1 MÃ (đầy đủ, không rút gọn):
  J1 Tổng quan · J2 Tài chính (chỉ số + BCTC từng năm) · J3 Kỹ thuật (MA, RSI, sức mạnh giá, mô hình nến,
  Tích lũy & Vượt theo đủ các nút ngưỡng của FiinTrade) · J4 Biến động (mã / VN-Index / cùng ngành) ·
  J5 Phân tích tài chính 10 tiêu chí FiinGroup (5 mức, giải thích từng tiêu chí, so sánh tối đa 2 mã cùng ngành).
Chỉ tính toán & trình bày – KHÔNG thay đổi khuyến nghị của ptcp (Phần C là nguồn duy nhất của khuyến nghị).
"""
import numpy as np
import pandas as pd

from .danh_gia_tai_chinh import TEN_MUC, TIEU_CHI_FA, danh_gia
from .in_an import in_ra, ve_bang

NGAN_HANG_BAO_HIEM = {"VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "STB", "VIB", "TPB", "SHB", "LPB",
                      "SSB", "MSB", "OCB", "EIB", "NAB", "BAB", "ABB", "VAB", "BVB", "KLB", "PGB", "SGB", "VBB",
                      "NVB", "BVH", "BMI", "PVI", "MIG", "PTI", "BIC", "PGI", "VNR"}
BIEN_DO_TICH_LUY = 15.0
KHUNG_BIEN_DONG = [("1 ngày", 1), ("1 tuần", 5), ("2 tuần", 10), ("1 tháng", 21), ("3 tháng", 63),
                   ("6 tháng", 126), ("9 tháng", 189), ("1 năm", 252)]


def la_tai_chinh(symbol, nganh="", ma_ctck=()):
    n = str(nganh or "")
    return symbol in NGAN_HANG_BAO_HIEM or symbol in ma_ctck or any(
        t in n for t in ("Ngân hàng", "Bảo hiểm", "Chứng khoán", "Dịch vụ tài chính"))


# ---------------------------------------------------------------- kỹ thuật
def mo_hinh_nen(df):
    """Mô hình nến của phiên CUỐI df: ↑ tín hiệu tăng, ↓ giảm, – trung tính; không có → ''."""
    if df is None or len(df) < 12:
        return ""
    o, h, l, c = (float(df[k].iloc[-1]) for k in ("open", "high", "low", "close"))
    o1, c1 = float(df.open.iloc[-2]), float(df.close.iloc[-2])
    bien = h - l
    if bien <= 0:
        return ""
    than = abs(c - o)
    tren, duoi = h - max(o, c), min(o, c) - l
    giam_truoc = c1 < df.close.iloc[-11:-1].mean()
    trang = c >= o
    if c1 < o1 and trang and o <= c1 and c >= o1 and than > abs(c1 - o1):
        return "Bullish Engulfing ↑"
    if c1 > o1 and not trang and o >= c1 and c <= o1 and than > abs(c1 - o1):
        return "Bearish Engulfing ↓"
    if than >= 0.9 * bien:
        return "White Marubozu ↑" if trang else "Black Marubozu ↓"
    if than <= 0.1 * bien:
        if duoi >= 0.6 * bien:
            return "Dragonfly Doji ↑"
        if tren >= 0.6 * bien:
            return "Gravestone Doji ↓"
        return "Doji –"
    if duoi >= 2 * than and tren <= 0.5 * than:
        return "Hammer ↑" if giam_truoc else "Hanging Man ↓"
    if tren >= 2 * than and duoi <= 0.5 * than:
        return "Inverted Hammer ↑" if giam_truoc else "Shooting Star ↓"
    if than <= 0.3 * bien and tren > than and duoi > than:
        return ("White" if trang else "Black") + " Spinning Top " + ("↑" if giam_truoc else "↓")
    return ""


def so_phien_tich_luy(df, bien_do=BIEN_DO_TICH_LUY, toi_da=250):
    if df is None or len(df) < 7:
        return 0
    cao, thap = df.high.values[:-1][::-1], df.low.values[:-1][::-1]
    max_c, min_t, n = -np.inf, np.inf, 0
    for c, t in zip(cao[:toi_da], thap[:toi_da]):
        max_c, min_t = max(max_c, c), min(min_t, t)
        if min_t <= 0 or (max_c / min_t - 1) * 100 > bien_do:
            break
        n += 1
    return n


def nen_va_tich_luy(df, ten_khung, so_nen=3):
    """
    Cho Phần B (mỗi khung tuần/ngày/giờ): số nến tích lũy (đi ngang, biên độ ≤ 15%) liền trước nến cuối, vùng nền,
    và mô hình nến của 'so_nen' nến gần nhất. → dict (dùng in & xuất Excel).
    """
    n = so_phien_tich_luy(df)
    nen = df.iloc[-1 - n:-1] if n else df.iloc[0:0]
    fmt = "%d/%m %H:%M" if ten_khung == "Giờ" else ("tuần %d/%m" if ten_khung == "Tuần" else "%d/%m")
    mh = []
    for k in range(so_nen, 0, -1):
        con = df.iloc[: len(df) - k + 1]
        m = mo_hinh_nen(con)
        mh.append((con.index[-1].strftime(fmt), m or "không có mô hình rõ"))
    return {"so_nen_tich_luy": n, "nen_thap": float(nen.low.min()) if n else None,
            "nen_cao": float(nen.high.max()) if n else None, "mo_hinh": mh}


def in_nen_khung(ten_khung, x):
    don_vi = {"Tuần": "tuần", "Ngày": "phiên", "Giờ": "nến giờ"}.get(ten_khung, "nến")
    in_ra(f"\n  ▸ Tích lũy & mô hình nến ({ten_khung.lower()})")
    if x["so_nen_tich_luy"]:
        in_ra(f"     Tích lũy : {x['so_nen_tich_luy']} {don_vi} đi ngang (biên độ ≤ {BIEN_DO_TICH_LUY:g}%), "
              f"vùng nền {x['nen_thap']:,.2f} – {x['nen_cao']:,.2f}")
    else:
        in_ra(f"     Tích lũy : không – biên độ > {BIEN_DO_TICH_LUY:g}% ngay từ {don_vi} trước")
    rong = max(len(t) for t, _ in x["mo_hinh"])
    for i, (t, m) in enumerate(x["mo_hinh"]):
        in_ra(f"     {'Nến      :' if i == 0 else ' ' * 10} {t.ljust(rong)}  {m}")


def _bien_dong(df, n):
    return (df.close.iloc[-1] / df.close.iloc[-1 - n] - 1) * 100 if df is not None and len(df) > n else np.nan


def _ytd(df):
    if df is None or not len(df):
        return np.nan
    truoc = df.close[df.index.year < df.index[-1].year]
    return (df.close.iloc[-1] / truoc.iloc[-1] - 1) * 100 if len(truoc) else np.nan


# ---------------------------------------------------------------- tổng hợp
def phan_tich(symbol, d_ngay, vni, nhom, tt, cb, online, bctc, bctc_nganh, nganh="", ma_ctck=(), khuyen_nghi=None):
    """
    d_ngay: DataFrame ngày đã có chỉ báo (RSI...). nhom: {mã cùng ngành: df}. tt: thong_tin_giao_dich.
    cb: chỉ số cơ bản Phần H; online: kết quả lay_chi_so_co_ban; bctc: BCTC năm của mã;
    bctc_nganh: {mã cùng ngành: BCTC năm} (tối đa 2). → dict các bảng + chỉ tiêu tóm tắt.
    """
    ht = float(d_ngay.close.iloc[-1])
    gia_tri = lambda k: cb[k][0] if k in cb and isinstance(cb[k], tuple) else np.nan
    so_le = lambda x, le=2: round(x, le) if x is not None and x == x else np.nan

    # ---- J1 Tổng quan
    rsi = float(d_ngay["RSI"].iloc[-1]) if "RSI" in d_ngay else np.nan
    j1 = pd.DataFrame([
        ["Giá (đồng)", round(ht * 1000), f"phiên {d_ngay.index[-1]:%d/%m/%Y}"],
        ["KL trung bình 3 tháng (CP)", round(d_ngay.volume.tail(63).mean()), "63 phiên"],
        ["GTGD trung bình 20 phiên (tỷ đồng)", so_le(tt.get("gt_tb20")), ""],
        ["Beta", so_le(tt.get("beta")), tt.get("nguon_beta", "")],
        ["RSI (14)", so_le(rsi, 1), "< 30 quá bán · > 70 quá mua"],
        ["EPS 4 quý (đồng)", so_le(gia_tri("EPS 4 quý (đồng)"), 0), cb.get("EPS 4 quý (đồng)", ("", ""))[1]
         if "EPS 4 quý (đồng)" in cb else ""],
        ["P/E (lần)", so_le(gia_tri("P/E")), cb["P/E"][1] if "P/E" in cb else "chưa có"],
        ["P/B (lần)", so_le(gia_tri("P/B")), cb["P/B"][1] if "P/B" in cb else "chưa có"],
        ["ROE (%)", so_le(gia_tri("ROE %"), 1), cb["ROE %"][1] if "ROE %" in cb else "chưa có"],
        ["Vốn hoá (tỷ đồng)", so_le(tt.get("von_hoa"), 0), "số CP lưu hành × giá"],
        ["Sở hữu nước ngoài (%)", so_le(tt.get("so_huu_nn"), 1), tt.get("nguon_nn", "")],
    ], columns=["Chỉ tiêu", "Giá trị", "Ghi chú / nguồn"])

    # ---- J2 Tài chính: bảng BCTC từng năm (đầy đủ)
    j2 = None
    if bctc:
        nam = bctc["nam"][:5]
        g = lambda k: (bctc.get(k) or [None] * len(nam))[:len(nam)]
        dt, lg, ln, cfo = g("doanh_thu"), g("ln_gop"), g("lnst"), g("cfo")
        tang = lambda v: [(a / b - 1) * 100 if a is not None and b else None for a, b in zip(v, v[1:] + [None])]
        dong = [("Doanh thu", dt), ("Tăng trưởng doanh thu %", tang(dt)), ("Lợi nhuận gộp", lg),
                ("Biên lãi gộp %", [a / b * 100 if a is not None and b else None for a, b in zip(lg, dt)]),
                ("LNST (cổ đông mẹ)", ln), ("Tăng trưởng LNST %", tang(ln)), ("Dòng tiền kinh doanh (CFO)", cfo),
                ("CFO / LNST (lần)", [a / b if a is not None and b else None for a, b in zip(cfo, ln)]),
                ("Thanh toán hiện thời (lần)", g("cr")), ("EBIT / lãi vay (lần)", g("icr")),
                ("Nợ / VCSH (lần)", g("de")), ("ROE %", g("roe")), ("Vốn góp", g("von_gop")),
                ("Vay nợ tài chính", g("vay_no"))]
        j2 = pd.DataFrame({"Chỉ tiêu (giá trị tiền: tỷ đồng)": [d[0] for d in dong],
                           **{str(y): [so_le(v[i]) if i < len(v) else np.nan for _, v in dong]
                              for i, y in enumerate(nam)}})
        j2.attrs["nguon"] = bctc.get("nguon", "")

    # ---- J3 Kỹ thuật
    d = d_ngay
    ma = {n_: d.close.rolling(n_).mean() for n_ in (20, 50, 100, 200)}
    dong3 = [["Khối lượng phiên gần nhất", f"{float(d.volume.iloc[-1]):,.0f}", "cổ phiếu"],
             ["Giá đóng cửa (nghìn)", round(ht, 2), ""]]
    for n_, s in ma.items():
        if len(s.dropna()) > 6:
            huong = "Tăng" if s.iloc[-1] > s.iloc[-6] else "Giảm"
            dong3.append([f"MA{n_}", round(float(s.iloc[-1]), 2),
                          f"hướng {huong} (so 5 phiên trước) · giá {'TRÊN' if ht > s.iloc[-1] else 'DƯỚI'} "
                          f"({(ht / s.iloc[-1] - 1) * 100:+.1f}%)"])
    dong3.append(["RSI (14)", so_le(rsi, 1), "quá bán" if rsi < 30 else ("quá mua" if rsi > 70 else "trung tính")])
    for nhan, n_ in (("Sức mạnh giá 6 tháng (RS6M)", 126), ("Sức mạnh giá 52 tuần (RS52W)", 252)):
        bd = _bien_dong(d, n_)
        vn = _bien_dong(vni, n_)
        hang = ""
        if nhom:
            ds = [bd] + [_bien_dong(x, n_) for x in nhom.values()]
            ds = [x for x in ds if x == x]
            if len(ds) >= 2:
                hang = f" · hạng {1 + sum(x > bd for x in ds)}/{len(ds)} trong ngành"
        dong3.append([nhan.replace(")", ") %"), so_le(bd, 1), f"VN-Index {vn:+.1f}% → chênh {bd - vn:+.1f} điểm{hang}"
                      if vn == vn and bd == bd else hang])
    j3 = pd.DataFrame(dong3, columns=["Chỉ tiêu", "Giá trị", "Ghi chú"])

    # ---- J4 Biến động
    cot = {symbol: d, "VN-Index": vni, **(nhom or {})}
    j4 = pd.DataFrame({"Khung": [k for k, _ in KHUNG_BIEN_DONG] + ["Từ đầu năm"],
                       **{ten: [so_le(_bien_dong(x, n_)) for _, n_ in KHUNG_BIEN_DONG] + [so_le(_ytd(x))]
                          for ten, x in cot.items() if x is not None}})

    # ---- J5 Phân tích tài chính 10 tiêu chí
    fa = danh_gia(bctc, ht, la_tai_chinh(symbol, nganh, ma_ctck)) if bctc else None
    j5 = None
    if fa:
        rows = []
        so_sanh = {m: danh_gia(b, (nhom.get(m).close.iloc[-1] if nhom and m in nhom else None),
                               la_tai_chinh(m, "", ma_ctck)) for m, b in (bctc_nganh or {}).items() if b}
        for ten in TIEU_CHI_FA:
            muc, gt = fa["chi_tiet"][ten]
            r = {"Tiêu chí": ten, symbol: TEN_MUC.get(muc, "–"), "Giải thích": gt}
            for m, f in so_sanh.items():
                r[m] = TEN_MUC.get(f["chi_tiet"][ten][0], "–")
            rows.append(r)
        rows.append({"Tiêu chí": "ĐIỂM (0–100)", symbol: so_le(fa["diem"], 0),
                     "Giải thích": f"{fa['so_nguy_hiem']} Nguy hiểm · {fa['so_canh_bao']} Cảnh báo · "
                                   f"BCTC đến năm {fa['nam']} ({fa['nguon']})",
                     **{m: so_le(f["diem"], 0) for m, f in so_sanh.items()}})
        j5 = pd.DataFrame(rows)
    kl4 = ket_luan_j4(symbol, j4)
    ket_luan = ket_luan_chung(symbol, ht=ht, pe=gia_tri("P/E"), pb=gia_tri("P/B"), roe=gia_tri("ROE %"), fa=fa,
                              bctc=bctc, ma={n_: (float(s.iloc[-1]) if len(s.dropna()) else np.nan,
                                                   float(s.iloc[-6]) if len(s.dropna()) > 6 else np.nan)
                                              for n_, s in ma.items()},
                              rsi=rsi, rs52=(_bien_dong(d, 252), _bien_dong(vni, 252)), kl_bien_dong=kl4,
                              khuyen_nghi=khuyen_nghi)
    return {"nganh": nganh, "J1": j1, "J2": j2, "J3": j3, "J4": j4, "J4_ket_luan": kl4, "J5": j5, "fa": fa,
            "ket_luan": ket_luan}


def ket_luan_chung(symbol, ht, pe, pb, roe, fa, bctc, ma, rsi, rs52, kl_bien_dong=(), khuyen_nghi=None):
    """
    KẾT LUẬN CHUNG PHẦN J: chấm 4 nhóm (định giá · sức khỏe tài chính · kỹ thuật · sức mạnh giá), mỗi ý +1/0/−1
    → TÍCH CỰC (≥ +3) / TIÊU CỰC (≤ −2) / TRUNG TÍNH; liệt kê điểm mạnh – điểm yếu và đối chiếu khuyến nghị Phần C.
    """
    co = lambda x: x is not None and x == x
    y = []                                               # (nhóm, diễn giải, điểm)

    # 1. Định giá & hiệu quả
    if co(pe):
        if pe <= 0:
            y.append(("Định giá", f"P/E {pe:.1f} – doanh nghiệp đang lỗ", -1))
        elif pe < 10:
            y.append(("Định giá", f"P/E {pe:.1f} – rẻ", 1))
        elif pe <= 20:
            y.append(("Định giá", f"P/E {pe:.1f} – hợp lý", 0))
        else:
            y.append(("Định giá", f"P/E {pe:.1f} – cao", -1))
    if co(pb):
        y.append(("Định giá", f"P/B {pb:.2f}" + (" – dưới giá trị sổ sách" if pb < 1 else
                                                  " – cao" if pb > 3 else ""), 1 if pb < 1 else (-1 if pb > 3 else 0)))
    if co(roe):
        y.append(("Hiệu quả", f"ROE {roe:.1f}%" + (" – cao" if roe >= 15 else " – thấp" if roe < 10 else ""),
                  1 if roe >= 15 else (-1 if roe < 10 else 0)))

    # 2. Sức khỏe tài chính (10 tiêu chí) & tăng trưởng lợi nhuận
    if fa and co(fa.get("diem")):
        d_ = fa["diem"]
        y.append(("Tài chính", f"điểm 10 tiêu chí {d_:.0f}/100" + (" – khỏe" if d_ >= 70 else " – yếu" if d_ < 50 else
                                                                   " – trung bình"), 1 if d_ >= 70 else (-1 if d_ < 50 else 0)))
        if fa["so_nguy_hiem"]:
            y.append(("Tài chính", f"{fa['so_nguy_hiem']} tiêu chí NGUY HIỂM ({fa['tom_tat']})",
                      -1 if fa["so_nguy_hiem"] >= 2 else 0))
    ln = (bctc or {}).get("lnst") or []
    if len(ln) >= 2 and co(ln[0]) and co(ln[1]) and ln[1]:
        g = (ln[0] - ln[1]) / abs(ln[1]) * 100
        y.append(("Tài chính", f"LNST năm {bctc['nam'][0]} {g:+.1f}% so năm trước",
                  1 if g > 10 else (-1 if g < -10 else 0)))

    # 3. Kỹ thuật
    m50, m200 = ma.get(50, (np.nan, np.nan)), ma.get(200, (np.nan, np.nan))
    if co(m50[0]) and co(m200[0]):
        tren = (ht > m50[0]) + (ht > m200[0])
        y.append(("Kỹ thuật", "giá trên cả MA50 & MA200 – xu hướng tăng" if tren == 2 else
                  "giá dưới cả MA50 & MA200 – xu hướng giảm" if tren == 0 else
                  f"giá {'trên MA50, dưới MA200' if ht > m50[0] else 'dưới MA50, trên MA200'} – chưa rõ xu hướng",
                  1 if tren == 2 else (-1 if tren == 0 else 0)))
    if co(m50[0]) and co(m50[1]):
        y.append(("Kỹ thuật", f"MA50 đang {'đi lên' if m50[0] > m50[1] else 'đi xuống'}", 1 if m50[0] > m50[1] else -1))
    if co(rsi):
        if rsi > 70:
            y.append(("Kỹ thuật", f"RSI {rsi:.0f} – quá mua, dễ điều chỉnh", -1))
        elif rsi < 30:
            y.append(("Kỹ thuật", f"RSI {rsi:.0f} – quá bán", 0))

    # 4. Sức mạnh giá so thị trường
    bd, vn = rs52
    if co(bd) and co(vn):
        c = bd - vn
        y.append(("Sức mạnh giá", f"1 năm {bd:+.1f}% vs VN-Index {vn:+.1f}% ({c:+.1f} điểm)",
                  1 if c > 10 else (-1 if c < -10 else 0)))

    tong = sum(x[2] for x in y)
    nhan = "TÍCH CỰC" if tong >= 3 else ("TIÊU CỰC" if tong <= -2 else "TRUNG TÍNH")
    manh = [f"{n}: {t}" for n, t, s in y if s > 0]
    yeu = [f"{n}: {t}" for n, t, s in y if s < 0]
    goi_y = ""
    kn = str(khuyen_nghi or "")
    if kn:
        if nhan == "TÍCH CỰC" and "MUA" in kn and "CHƯA" not in kn and "KHÔNG" not in kn:
            goi_y = f"Nền tảng & kỹ thuật cùng ủng hộ khuyến nghị {kn} ở Phần C."
        elif nhan == "TÍCH CỰC":
            goi_y = (f"Doanh nghiệp/cổ phiếu đang tốt nhưng Phần C khuyến nghị {kn} – chưa có điểm mua có lợi thế "
                     "thống kê; đưa vào danh sách theo dõi, chờ điều kiện ở Phần C.")
        elif nhan == "TIÊU CỰC":
            goi_y = f"Nhiều điểm yếu – thận trọng; Phần C: {kn}."
        else:
            goi_y = f"Chưa nổi bật mặt nào; quyết định theo Phần C: {kn}."
    return {"nhan": nhan, "diem": tong, "y": y, "manh": manh, "yeu": yeu, "bien_dong": list(kl_bien_dong),
            "goi_y": goi_y}


def ket_luan_j4(symbol, j4):
    """Kết luận tự động cho bảng biến động: so VN-Index, xếp hạng trong nhóm, giữ giá ngắn hạn."""
    if j4 is None or symbol not in j4:
        return []
    t = j4.set_index("Khung")
    kl = []
    if "VN-Index" in t:
        chenh = {k: t.loc[k, symbol] - t.loc[k, "VN-Index"] for k in ("1 tháng", "3 tháng", "1 năm")
                 if t.loc[k, symbol] == t.loc[k, symbol] and t.loc[k, "VN-Index"] == t.loc[k, "VN-Index"]}
        if chenh:
            so_duong = sum(v > 0 for v in chenh.values())
            nhan = ("mạnh hơn rõ ở mọi khung" if so_duong == len(chenh) else
                    "yếu hơn ở mọi khung" if so_duong == 0 else "lúc mạnh lúc yếu hơn")
            kl.append(f"So VN-Index: {symbol} {nhan} – " +
                      ", ".join(f"{k} {v:+.1f} điểm %" for k, v in chenh.items()) + ".")
        t1, v1 = t.loc["1 tuần", symbol], t.loc["1 tuần", "VN-Index"]
        if t1 == t1 and v1 == v1:
            if v1 < -1 and t1 >= v1 + 2:
                kl.append(f"Ngắn hạn: tuần qua {symbol} {t1:+.1f}% khi VN-Index {v1:+.1f}% → giữ giá tốt khi thị "
                          "trường điều chỉnh.")
            elif v1 > 1 and t1 <= v1 - 2:
                kl.append(f"Ngắn hạn: tuần qua {symbol} {t1:+.1f}% trong khi VN-Index {v1:+.1f}% → đang tụt lại "
                          "so với thị trường.")
            else:
                kl.append(f"Ngắn hạn: tuần qua {symbol} {t1:+.1f}%, VN-Index {v1:+.1f}% → đi cùng thị trường.")
    nganh = [c for c in t.columns if c not in (symbol, "VN-Index")]
    if nganh:
        tong = len(nganh) + 1
        hang = {}
        for k in ("3 tháng", "1 năm", "Từ đầu năm"):
            v = t.loc[k, [symbol] + nganh].dropna()
            if symbol in v and len(v) >= 2:
                hang[k] = (int(1 + (v > v[symbol]).sum()), len(v))
        if hang:
            nhat = [c for c in nganh if t.loc["1 năm", c] == t.loc["1 năm", [symbol] + nganh].max()]
            kl.append(f"Trong nhóm {tong} mã: " + ", ".join(f"xếp {h}/{n} theo {k}" for k, (h, n) in hang.items())
                      + (f" (mạnh nhất 1 năm: {nhat[0]})" if nhat and nhat[0] != symbol else "") + ".")
    return kl


BIEU_TUONG = {"Rất tốt": "🔵 Rất tốt", "Tốt": "🟢 Tốt", "Trung bình": "🟡 Trung bình", "Cảnh báo": "🟠 Cảnh báo",
              "Nguy hiểm": "🔴 Nguy hiểm", "–": "⚪ –"}


def _dinh_dang_theo_nhan(nhan, v):
    """Định dạng 1 giá trị theo ĐƠN VỊ ghi trong tên chỉ tiêu (đồng, CP, tỷ, %, lần)."""
    if v is None or (isinstance(v, float) and v != v):
        return "–"
    if isinstance(v, str):
        return v
    n = nhan.lower()
    if "tăng trưởng" in n and "%" in n:
        return f"{v:+.1f}%"
    if "%" in n:
        return f"{v:.1f}%"
    if "lần" in n or n.startswith("beta"):
        return f"{v:.2f}"
    if "(đồng)" in n or "(cp)" in n or "khối lượng" in n:
        return f"{v:,.0f}"
    if "tỷ" in n:
        return f"{v:,.1f}" if abs(v) < 100 else f"{v:,.0f}"
    if "rsi" in n:
        return f"{v:.1f}"
    return f"{v:,.2f}"


def _bang_hien_thi(df, cot_nhan, cot_so):
    """Bản để IN: định dạng từng ô theo đơn vị trong tên dòng (Excel vẫn giữ số gốc)."""
    d = df.copy()
    for c in cot_so:
        d[c] = [_dinh_dang_theo_nhan(n, v) for n, v in zip(d[cot_nhan], d[c])]
    return d


def _tieu_de(chu):
    in_ra(f"\n{'═' * 84}\n {chu}\n{'═' * 84}")


def in_phan_J(symbol, kq):
    in_ra(f"\n{'#' * 84}\n PHẦN J. PHÂN TÍCH KIỂU FIINTRADE – {symbol}\n{'#' * 84}")

    _tieu_de(f"J1. TỔNG QUAN – {symbol}" + (f" · {kq['nganh']}" if kq.get("nganh") else ""))
    in_ra(ve_bang(_bang_hien_thi(kq["J1"], "Chỉ tiêu", ["Giá trị"]), can_phai=["Giá trị"]))

    if kq["J2"] is not None:
        _tieu_de(f"J2. TÀI CHÍNH – BCTC THEO NĂM (tỷ đồng · nguồn {kq['J2'].attrs.get('nguon', '')})")
        j2 = kq["J2"].rename(columns={"Chỉ tiêu (giá trị tiền: tỷ đồng)": "Chỉ tiêu"})
        nam = [c for c in j2.columns if c != "Chỉ tiêu"]
        j2 = j2.assign(**{"Chỉ tiêu": [x if any(t in x for t in ("%", "lần")) else x + " (tỷ)" for x in j2["Chỉ tiêu"]]})
        in_ra(ve_bang(_bang_hien_thi(j2, "Chỉ tiêu", nam), can_phai=nam))
    else:
        _tieu_de("J2. TÀI CHÍNH – BCTC THEO NĂM")
        in_ra("  Chưa lấy được BCTC năm (TCBS / vnstock / Yahoo đều lỗi) – xem mục NGUỒN DỮ LIỆU.")

    _tieu_de("J3. KỸ THUẬT  (tích lũy & mô hình nến: xem Phần B từng khung)")
    in_ra(ve_bang(_bang_hien_thi(kq["J3"], "Chỉ tiêu", ["Giá trị"]), can_phai=["Giá trị"]))

    _tieu_de("J4. BIẾN ĐỘNG GIÁ (%) – mã · VN-Index · cùng ngành")
    in_ra(ve_bang(kq["J4"], dinh_dang={c: "{:+.1f}" for c in kq["J4"].columns if c != "Khung"}))

    if kq["J5"] is not None:
        _tieu_de("J5. PHÂN TÍCH TÀI CHÍNH 10 TIÊU CHÍ (phương pháp luận FiinGroup)")
        in_ra("  🔵 Rất tốt   🟢 Tốt   🟡 Trung bình   🟠 Cảnh báo   🔴 Nguy hiểm   ⚪ không đủ dữ liệu\n")
        j5 = kq["J5"].copy()
        ma_cot = [c for c in j5.columns if c not in ("Tiêu chí", "Giải thích")]
        for c in ma_cot:
            j5[c] = [BIEU_TUONG.get(v, v) if isinstance(v, str) else (f"   {v:.0f}" if v == v else "   –")
                     for v in j5[c]]
        j5 = j5[["Tiêu chí"] + ma_cot + ["Giải thích"]]           # giải thích để cuối → xuống dòng gọn
        in_ra(ve_bang(j5))
        fa = kq["fa"]
        if fa["so_nguy_hiem"]:
            in_ra(f"\n  ⚠ {symbol} có {fa['so_nguy_hiem']} tiêu chí NGUY HIỂM: {fa['tom_tat']}")
    in_ket_luan_J(symbol, kq.get("ket_luan"))


def in_ket_luan_J(symbol, kl):
    """Kết luận chung cuối Phần J (tổng hợp J1–J5)."""
    if not kl:
        return
    _tieu_de(f"KẾT LUẬN CHUNG PHẦN J – {symbol}: {kl['nhan']} (điểm {kl['diem']:+d})")
    nhom = {}
    for n, t, s in kl["y"]:
        nhom.setdefault(n, []).append(("▲" if s > 0 else "▼" if s < 0 else "•") + " " + t)
    for n, ds in nhom.items():
        in_ra(f"  {n:<13}: " + " · ".join(ds))
    for k, d in enumerate(kl["bien_dong"]):
        in_ra(f"  {'Biến động' if k == 0 else '':<13}{':' if k == 0 else ' '} {d}")
    in_ra("")
    in_ra("  Điểm mạnh : " + ("; ".join(kl["manh"]) if kl["manh"] else "không có điểm nổi bật"))
    in_ra("  Điểm yếu  : " + ("; ".join(kl["yeu"]) if kl["yeu"] else "không có điểm yếu đáng kể"))
    if kl.get("goi_y"):
        in_ra(f"  ➜ {kl['goi_y']}")
    in_ra("  ⓘ Kết luận Phần J mô tả chất lượng doanh nghiệp & trạng thái cổ phiếu; khuyến nghị giao dịch vẫn theo Phần C.")


MAU_MUC = {"Rất tốt": "FF4A90E2", "Tốt": "FF2ECC71", "Trung bình": "FFF1C40F", "Cảnh báo": "FFF39C12",
           "Nguy hiểm": "FFE74C3C"}


def _do_rong_cot(ws, df):
    """Tự đặt độ rộng cột theo nội dung + cố định dòng tiêu đề (openpyxl & xlsxwriter)."""
    for i, c in enumerate(df.columns):
        rong = min(60, max([len(str(c))] + [len(str(v)) for v in df[c].tolist()]) + 2)
        if hasattr(ws, "set_column"):
            ws.set_column(i, i, rong)
        else:
            from openpyxl.utils import get_column_letter
            ws.column_dimensions[get_column_letter(i + 1)].width = rong
    ws.freeze_panes(1, 1) if hasattr(ws, "set_column") else setattr(ws, "freeze_panes", "B2")


def ghi_excel(w, kq):
    """Ghi các sheet J vào ExcelWriter đang mở; tô màu J5 như FiinTrade (chạy được với openpyxl & xlsxwriter)."""
    for ten, sheet in (("J1", "J1 Tong quan"), ("J2", "J2 BCTC nam"), ("J3", "J3 Ky thuat"),
                       ("J4", "J4 Bien dong"), ("J5", "J5 Phan tich TC 10 tieu chi")):
        if kq.get(ten) is None:
            continue
        kq[ten].to_excel(w, sheet_name=sheet, index=False)
        _do_rong_cot(w.sheets[sheet], kq[ten])
        if ten != "J5":
            continue
        ws = w.sheets[sheet]
        if hasattr(ws, "iter_rows"):                                    # openpyxl
            from openpyxl.styles import PatternFill
            for row in ws.iter_rows(min_row=2):
                for o in row:
                    if o.value in MAU_MUC:
                        o.fill = PatternFill("solid", fgColor=MAU_MUC[o.value])
        else:                                                           # xlsxwriter
            n_dong, n_cot = kq[ten].shape
            for nhan, mau in MAU_MUC.items():
                ws.conditional_format(1, 0, n_dong, n_cot - 1, {
                    "type": "cell", "criteria": "==", "value": f'"{nhan}"',
                    "format": w.book.add_format({"bg_color": "#" + mau[2:]})})

    kl = kq.get("ket_luan")
    if kl:
        dong = [["Kết luận chung", f"{kl['nhan']} (điểm {kl['diem']:+d})", ""]]
        dong += [[n, t, "▲ tích cực" if s > 0 else ("▼ tiêu cực" if s < 0 else "• trung tính")] for n, t, s in kl["y"]]
        dong += [["Biến động", d, ""] for d in kl["bien_dong"]]
        dong += [["Điểm mạnh", "; ".join(kl["manh"]) or "–", ""], ["Điểm yếu", "; ".join(kl["yeu"]) or "–", ""],
                 ["Gợi ý", kl.get("goi_y") or "–", ""]]
        pd.DataFrame(dong, columns=["Nhóm", "Nội dung", "Đánh giá"]).to_excel(w, sheet_name="J Ket luan chung",
                                                                             index=False)