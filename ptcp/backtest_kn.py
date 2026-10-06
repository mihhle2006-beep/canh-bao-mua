# -*- coding: utf-8 -*-
"""
BACKTEST TOÀN BỘ KHUYẾN NGHỊ (POINT-IN-TIME) + PHÂN TÍCH ĐỘ NHẠY NGƯỠNG.

Khác Phần I (chỉ thử quy tắc MACD tuần + ngày): ở đây chạy lại ĐÚNG lõi quyết định của ptcp (loi.tinh_khuyen_nghi:
mục tiêu, cắt lỗ thống nhất, EV có điều kiện + walk-forward, R/R, VN-Index/RS, lịch KQKD) tại TỪNG ngày quá khứ,
chỉ với dữ liệu có đến ngày đó (không nhìn trước), rồi chấm khuyến nghị bằng giá thực tế (cùng bộ chấm nhat_ky.py).

Giới hạn (ghi rõ trong kết quả):
  • Không có dữ liệu GIỜ quá khứ → bước "Giờ" bỏ qua (khuyến nghị đủ điều kiện ra MUA TỪNG PHẦN thay vì MUA).
  • Không có chỉ số CƠ BẢN theo thời điểm → bộ lọc cơ bản không áp dụng; không gộp nhóm ngành.
  • Ngày phân tích cách nhau `buoc` phiên, kỳ hạn chấm `n_phien` → các tín hiệu CHỒNG nhau; phần "Chiến lược"
    chỉ lấy lệnh không chồng (đang giữ thì bỏ qua tín hiệu mới) để có số liệu sát thực tế hơn.

Dùng (Colab):
  from ptcp import backtest_khuyen_nghi, backtest_nhieu_ma
  kq = backtest_khuyen_nghi("GMD")                       # ~2–4 phút/mã với 5–6 năm dữ liệu, buoc=5
  kq = backtest_nhieu_ma(["GMD", "MWG", "DHC", "VPB"])   # gộp nhiều mã → đủ mẫu hơn
"""
import contextlib
import io
import time
from datetime import date

import numpy as np
import pandas as pd

from . import cau_hinh as cfg
from . import nhat_ky
from .in_an import BAO_CAO_TEXT, _CHAY
from .du_lieu import _tai_ngay, chuan_hoa, tai_vnindex, tu_csv
from .loi import tinh_khuyen_nghi
from .thong_tin import co_cau_co_phieu, thong_tin_giao_dich

NGUONG_EV = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
NGUONG_RR = [1.5, 2.0, 2.5, 3.0]
KY_HAN_THU = [21, 42, 63, 126]


def _so(x):
    try:
        x = float(x)
        return x if x == x else np.nan
    except (TypeError, ValueError):
        return np.nan


def _mot_ngay(d, v, symbol, n_phien, ky_han, cc):
    tt = thong_tin_giao_dich(d, v, cc, None)
    r = tinh_khuyen_nghi(d, None, v, tt, symbol=symbol, n_phien=n_phien, ky_han=ky_han, co_ban=None)
    qd, kb, qr, tg, ttr, dx, stop = (r[k] for k in ("qd", "kb", "qr", "tg", "ttr", "dx", "stop"))
    mt = r["mt_chinh"]["Ngày"] or dx.get("chon")
    return {"ngay": d.index[-1], "gia": float(d.close.iloc[-1]), "khuyen_nghi": qd["khuyen_nghi"],
            "nhom": nhat_ky.nhom_khuyen_nghi(qd["khuyen_nghi"]), "cat_lo": _so(stop["gia"]), "muc_tieu": _so(mt),
            "ev_qd": _so(kb["ev_qd"]), "ev_tron": _so(kb.get("ev_tron")), "ev_dk": _so(kb.get("ev_dk")),
            "loi_the_tin_hieu": _so(kb.get("loi_the_tin_hieu")), "co_tin_hieu": kb.get("co_tin_hieu"),
            "rr": _so(qr["rr"]), "tuan_ok": bool(tg["tuan_ok"]), "ngay_ok": bool(tg["ngay_ok"]),
            "phong_thu": bool(qr["phong_thu"]), "chan_su_kien": bool(ttr["chan"]), "vni_xau": bool(ttr["vni_xau"]),
            "rs_yeu": bool(ttr["rs_yeu"])}


def _cham(bang, df, n_phien, san):
    """Chấm từng khuyến nghị (kết quả theo nhóm) + lệnh mua giả định thô (dùng cho độ nhạy)."""
    out = []
    for _, r in bang.iterrows():
        dong = {"loai": "PTCP", "nhom": r["nhom"], "ngay": r["ngay"], "gia": r["gia"], "cat_lo": r["cat_lo"],
                "muc_tieu": r["muc_tieu"], "ky_han": n_phien, "san": san}
        kq = nhat_ky.cham_dong(pd.Series(dong), df)
        tho = nhat_ky.cham_lenh_mua(df, r["ngay"], r["gia"], r["cat_lo"], r["muc_tieu"], n_phien, True, san)
        out.append({**kq, "mua_ket_qua": tho["ket_qua"], "mua_pct": tho["ket_qua_pct"],
                    "mua_ngay_ra": tho["ngay_ket_thuc"]})
    return pd.concat([bang.reset_index(drop=True), pd.DataFrame(out)], axis=1)


def _lenh_khong_chong(g, cot_mua):
    lenh, dang_giu_den = [], None
    for _, r in g.sort_values("ngay").iterrows():
        if not r[cot_mua] or r["mua_ket_qua"] not in (nhat_ky.DUNG, nhat_ky.SAI):
            continue
        if dang_giu_den is not None and pd.Timestamp(r["ngay"]) <= dang_giu_den:
            continue
        lenh.append(r["mua_pct"])
        dang_giu_den = pd.Timestamp(r["mua_ngay_ra"]) if r["mua_ngay_ra"] else pd.Timestamp(r["ngay"])
    return lenh


def _chien_luoc(bang, cot_mua="la_mua"):
    """Lệnh KHÔNG chồng (từng mã: đang giữ thì bỏ tín hiệu mới); thoát theo kết quả chấm của lệnh mua giả định.
    Nhiều mã → gộp các lệnh của mọi mã (vốn chia đều, tổng = lãi kép theo thứ tự lệnh)."""
    lenh = []
    for _, g in (bang.groupby("ma") if "ma" in bang else [(None, bang)]):
        lenh += _lenh_khong_chong(g, cot_mua)
    r = pd.Series(lenh, dtype=float)
    if not len(r):
        return {"so_lenh": 0}
    von = (1 + r / 100).cumprod()
    lai, lo = r[r > 0].sum(), -r[r <= 0].sum()
    return {"so_lenh": len(r), "ty_le_thang": (r > 0).mean() * 100, "tb": r.mean(), "pf": lai / lo if lo > 0 else np.nan,
            "tong": (von.iloc[-1] - 1) * 100, "mdd": ((von / von.cummax()) - 1).min() * 100}


def _la_mua(b, ev_min, rr_min):
    """Áp lại hàm quyết định (phần backtest được) với ngưỡng khác – thứ tự phủ quyết như quyet_dinh_cuoi."""
    return (~b["phong_thu"] & b["tuan_ok"] & (b["ev_qd"] >= ev_min) & b["ngay_ok"] & (b["rr"] >= rr_min)
            & ~b["chan_su_kien"] & ~(b["vni_xau"] & b["rs_yeu"]))


def do_nhay_nguong(b, ev_list=NGUONG_EV, rr_list=NGUONG_RR):
    """Bảng độ nhạy: mỗi cặp (EV, R/R) → số tín hiệu MUA, tỷ lệ đúng, TB lãi/lỗ, TB nửa đầu / nửa sau (ổn định?)."""
    b = b[b["mua_ket_qua"].isin([nhat_ky.DUNG, nhat_ky.SAI])].copy()
    if not len(b):
        return pd.DataFrame()
    giua = b["ngay"].sort_values().iloc[len(b) // 2]
    rows = []
    for e in ev_list:
        for rr in rr_list:
            m = _la_mua(b, e, rr)
            g = b[m]
            r = g["mua_pct"]
            dau, sau = g[g["ngay"] < giua]["mua_pct"], g[g["ngay"] >= giua]["mua_pct"]
            cl = _chien_luoc(b.assign(la_mua=m))
            rows.append({"EV tối thiểu %": e, "R/R tối thiểu": rr, "Số tín hiệu MUA": len(g),
                         "Tỷ lệ đúng %": (r > 0).mean() * 100 if len(r) else np.nan,
                         "TB lãi/lỗ %": r.mean() if len(r) else np.nan,
                         "TB nửa đầu %": dau.mean() if len(dau) else np.nan,
                         "TB nửa sau %": sau.mean() if len(sau) else np.nan,
                         "Lệnh không chồng": cl["so_lenh"], "Tổng (không chồng) %": cl.get("tong", np.nan),
                         "Đang dùng": "◄" if (e == cfg.EV_NGUONG and rr == cfg.RR_NGUONG) else ""})
    return pd.DataFrame(rows)


def do_nhay_ky_han(b, df, san, ky_han_list=KY_HAN_THU):
    """Chấm lại các khuyến nghị MUA với kỳ hạn khác nhau."""
    mua = b[b["nhom"] == "MUA"]
    rows = []
    for H in ky_han_list:
        kq = [nhat_ky.cham_lenh_mua(df, r["ngay"], r["gia"], r["cat_lo"], r["muc_tieu"], H, True, san)
              for _, r in mua.iterrows()]
        x = pd.DataFrame(kq) if kq else pd.DataFrame(columns=["ket_qua", "ket_qua_pct"])
        x = x[x["ket_qua"].isin([nhat_ky.DUNG, nhat_ky.SAI])]
        rows.append({"Kỳ hạn (phiên)": H, "Đã chấm": len(x),
                     "Tỷ lệ đúng %": (x["ket_qua"] == nhat_ky.DUNG).mean() * 100 if len(x) else np.nan,
                     "TB lãi/lỗ %": x["ket_qua_pct"].mean() if len(x) else np.nan})
    return pd.DataFrame(rows)


def _tai(symbol, start, csv_ngay, csv_vni):
    if csv_ngay:
        df = chuan_hoa(tu_csv(csv_ngay))
        df = df[df.index >= pd.Timestamp(start)]
    else:
        df = _tai_ngay(symbol, start, "NGÀY")
    return df, tai_vnindex(start, csv_vni)


def backtest_khuyen_nghi(symbol, start="2019-01-01", tu=None, den=None, buoc=5, n_phien=63, ky_han=252,
                         san="HOSE", csv_ngay=None, csv_vni=None, df_ngay=None, vni=None, xuat_excel=True,
                         in_ket_qua=True):
    """
    Chạy lõi khuyến nghị tại mỗi `buoc` phiên từ `tu` (mặc định: sau 2 năm dữ liệu đầu để đủ mẫu thống kê)
    đến `den`, chấm bằng giá thực tế. Trả dict: bang (chi tiết), theo_nhom, chien_luoc, mua_bat_ky, do_nhay,
    do_nhay_ky_han, file_excel.
    """
    symbol = str(symbol).upper()
    if df_ngay is None:
        df_ngay, vni2 = _tai(symbol, start, csv_ngay, csv_vni)
        vni = vni if vni is not None else vni2
    if df_ngay is None or len(df_ngay) < 600:
        raise ValueError("Cần ≥ 600 phiên dữ liệu ngày để backtest (2 năm khởi động + thời gian kiểm tra).")
    cu_san, cfg.NGUONG_TRAN_SAN = cfg.NGUONG_TRAN_SAN, cfg.BIEN_DO_SAN.get(san, 7.0) - 0.3
    idx = df_ngay.index
    i_tu = max(504, idx.searchsorted(pd.Timestamp(tu))) if tu else 504
    i_den = idx.searchsorted(pd.Timestamp(den), side="right") - 1 if den else len(idx) - 2
    vi_tri = list(range(i_tu, i_den + 1, buoc))
    cc = co_cau_co_phieu(None, None, None)
    cu_im, _CHAY["im_lang"] = _CHAY.get("im_lang"), True
    hang, t0 = [], time.time()
    try:
        for k, i in enumerate(vi_tri):
            d = df_ngay.iloc[:i + 1]
            v = vni[vni.index <= d.index[-1]] if vni is not None else None
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    hang.append(_mot_ngay(d, v, symbol, n_phien, ky_han, cc))
            except Exception as e:                                     # 1 ngày lỗi không dừng cả backtest
                hang.append({"ngay": d.index[-1], "gia": float(d.close.iloc[-1]), "khuyen_nghi": f"LỖI: {e}"[:60],
                             "nhom": "LỖI"})
            BAO_CAO_TEXT.clear()
            if in_ket_qua and (k + 1) % 25 == 0:
                print(f"  {symbol}: {k + 1}/{len(vi_tri)} ngày ({time.time() - t0:.0f}s)")
    finally:
        _CHAY["im_lang"] = cu_im
    bang = pd.DataFrame(hang)
    bang = bang[bang["nhom"] != "LỖI"].copy()
    for c in ("tuan_ok", "ngay_ok", "phong_thu", "chan_su_kien", "vni_xau", "rs_yeu"):
        bang[c] = bang[c].astype(bool)
    bang = _cham(bang, df_ngay, n_phien, san)
    bang.insert(0, "ma", symbol)
    cfg.NGUONG_TRAN_SAN = cu_san
    kq = tong_hop(bang, {symbol: (df_ngay, san)})
    kq["thoi_gian"] = time.time() - t0
    if in_ket_qua:
        in_tong_hop(kq, f"{symbol} – {len(bang)} ngày phân tích, mỗi {buoc} phiên, kỳ hạn chấm {n_phien} phiên")
    if xuat_excel:
        kq["file_excel"] = xuat_ket_qua(kq, f"backtest_khuyen_nghi_{symbol}_{date.today():%Y%m%d}.xlsx")
        if in_ket_qua:
            print(f"  → Đã xuất {kq['file_excel']}")
    return kq


def tong_hop(bang, du_lieu):
    """bang: chi tiết (có thể nhiều mã). du_lieu: {mã: (df_ngay, sàn)} cho độ nhạy kỳ hạn."""
    b = bang.copy()
    b["loai"], b["ket_qua"] = "PTCP", b["ket_qua"].fillna("")
    theo_nhom = nhat_ky.thong_ke(b)
    b["la_mua"] = b["nhom"] == "MUA"
    cl = pd.DataFrame([dict(ma=m, **_chien_luoc(g)) for m, g in b.groupby("ma")]
                      + ([dict(ma="TẤT CẢ", **_chien_luoc(b))] if b["ma"].nunique() > 1 else []))
    da = b[b["mua_ket_qua"].isin([nhat_ky.DUNG, nhat_ky.SAI])]
    mua_bat_ky = {"so": len(da), "tb": da["mua_pct"].mean() if len(da) else np.nan,
                  "ty_le_thang": (da["mua_pct"] > 0).mean() * 100 if len(da) else np.nan}
    mua = da[da["nhom"] == "MUA"]
    mua_bat_ky["tb_khi_mua"] = mua["mua_pct"].mean() if len(mua) else np.nan
    kh = pd.concat([do_nhay_ky_han(b[b["ma"] == m], df, s).assign(ma=m) for m, (df, s) in du_lieu.items()]) \
        if du_lieu else pd.DataFrame()
    if len(kh) and kh["ma"].nunique() > 1:                      # gộp nhiều mã: bình quân theo số lệnh
        kh = kh.assign(_d=kh["Tỷ lệ đúng %"] * kh["Đã chấm"], _t=kh["TB lãi/lỗ %"] * kh["Đã chấm"]) \
            .groupby("Kỳ hạn (phiên)", as_index=False)[["Đã chấm", "_d", "_t"]].sum()
        kh["Tỷ lệ đúng %"], kh["TB lãi/lỗ %"] = kh["_d"] / kh["Đã chấm"], kh["_t"] / kh["Đã chấm"]
        kh = kh.drop(columns=["_d", "_t"])
    elif len(kh):
        kh = kh.drop(columns=["ma"])
    return {"bang": bang, "theo_nhom": theo_nhom, "chien_luoc": cl, "mua_bat_ky": mua_bat_ky,
            "do_nhay": do_nhay_nguong(b), "do_nhay_ky_han": kh}


def in_tong_hop(kq, tieu_de):
    f = lambda x, n=2: "–" if x is None or x != x else f"{x:+.{n}f}"
    print(f"\n{'#' * 84}\n BACKTEST TOÀN BỘ KHUYẾN NGHỊ (point-in-time): {tieu_de}\n{'#' * 84}")
    print("  1. ĐỘ CHÍNH XÁC THEO NHÓM KHUYẾN NGHỊ (mỗi ngày phân tích = 1 khuyến nghị, có chồng lấn):")
    for _, r in kq["theo_nhom"].iterrows():
        if r["Đã chấm"]:
            nhan = "TB lệnh" if r["Nhóm"].endswith("MUA") else "TB nếu đã mua"
            print(f"     {r['Nhóm']:<18}: đúng {r['Đúng']}/{r['Đã chấm']} ({r['Tỷ lệ đúng %']:.0f}%) | "
                  f"{nhan} {f(r['TB kết quả %'])}%")
    m = kq["mua_bat_ky"]
    print(f"  2. MUA có chọn lọc hơn MUA BẤT KỲ LÚC NÀO không? TB lệnh khi ptcp nói MUA {f(m['tb_khi_mua'])}% "
          f"vs mọi ngày {f(m['tb'])}% → " + ("✔ có lợi thế" if m["tb_khi_mua"] == m["tb_khi_mua"]
                                            and m["tb_khi_mua"] > m["tb"] else "✘ CHƯA có lợi thế"))
    cl = kq["chien_luoc"]
    print("  3. CHIẾN LƯỢC (chỉ lệnh không chồng, sau phí):")
    for _, r in cl.iterrows():
        if r.get("so_lenh"):
            print(f"     {r.get('ma', ''):<6} {int(r['so_lenh'])} lệnh | thắng {r['ty_le_thang']:.0f}% | TB {f(r['tb'])}% | "
                  f"PF {f(r['pf']).lstrip('+')} | tổng {f(r['tong'], 1)}% | MDD {r['mdd']:.1f}%"
                  + (" ⚠ < 30 lệnh" if r["so_lenh"] < cfg.SO_MAU_TIN_CAY else ""))
        else:
            print(f"     {r.get('ma', '')} không có lệnh MUA đã chấm")
    dn = kq["do_nhay"]
    if len(dn):
        print("  4. ĐỘ NHẠY NGƯỠNG (◄ = ngưỡng đang dùng). Chọn vùng ổn định ở CẢ 2 nửa thời gian, đừng chọn ô đẹp nhất:")
        print(dn.round(2).to_string(index=False))
    if len(kq["do_nhay_ky_han"]):
        print("  5. ĐỘ NHẠY KỲ HẠN CHẤM (khuyến nghị MUA):")
        print(kq["do_nhay_ky_han"].round(2).to_string(index=False))
    print("  Giới hạn: không có dữ liệu GIỜ & CƠ BẢN theo thời điểm (bỏ qua 2 bước đó), không gộp nhóm ngành.")


def xuat_ket_qua(kq, path):
    cl = kq["chien_luoc"]
    m = kq["mua_bat_ky"]
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        kq["theo_nhom"].to_excel(w, sheet_name="Theo nhom", index=False)
        cl.to_excel(w, sheet_name="Chien luoc", index=False)
        pd.DataFrame([["TB lệnh khi ptcp MUA %", m["tb_khi_mua"]], ["TB lệnh mua mọi ngày %", m["tb"]],
                      ["Tỷ lệ thắng mua mọi ngày %", m["ty_le_thang"]]],
                     columns=["Chỉ tiêu", "Giá trị"]).to_excel(w, sheet_name="So voi mua bat ky", index=False)
        kq["do_nhay"].to_excel(w, sheet_name="Do nhay nguong", index=False)
        kq["do_nhay_ky_han"].to_excel(w, sheet_name="Do nhay ky han", index=False)
        kq["bang"].to_excel(w, sheet_name="Chi tiet", index=False)
        nhat_ky.trang_tri_excel(w, "Chi tiet")
    return path


def backtest_nhieu_ma(ds_ma, start="2019-01-01", buoc=5, n_phien=63, san=None, xuat_excel=True, **kw):
    """Backtest từng mã rồi GỘP (nhiều mẫu hơn → kết luận đáng tin hơn). san: {mã: sàn} hoặc None (= HOSE)."""
    bang, du_lieu, vni = [], {}, None
    for ma in ds_ma:
        print(f"\n=== {ma} ===")
        try:
            df, vni_ = _tai(ma, start, None, None)
            vni = vni if vni is not None else vni_
            s = (san or {}).get(ma, "HOSE")
            k = backtest_khuyen_nghi(ma, df_ngay=df, vni=vni, buoc=buoc, n_phien=n_phien, san=s, xuat_excel=False,
                                     in_ket_qua=False, **kw)
            bang.append(k["bang"])
            du_lieu[ma] = (df, s)
            print(f"  xong {len(k['bang'])} ngày ({k['thoi_gian']:.0f}s)")
        except Exception as e:
            print(f"  ⚠ bỏ qua {ma}: {str(e)[:100]}")
    if not bang:
        return None
    kq = tong_hop(pd.concat(bang, ignore_index=True), du_lieu)
    in_tong_hop(kq, f"GỘP {len(bang)} mã: {', '.join(du_lieu)}")
    if xuat_excel:
        kq["file_excel"] = xuat_ket_qua(kq, f"backtest_khuyen_nghi_gop_{date.today():%Y%m%d}.xlsx")
        print(f"  → Đã xuất {kq['file_excel']}")
    return kq
