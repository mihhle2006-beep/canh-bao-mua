# -*- coding: utf-8 -*-
"""
GIAO DỊCH GIẢ LẬP (paper trading) – bot tự mua bán bằng VỐN ẢO theo đúng tín hiệu thật, trên giá THẬT của các phiên
SAU ngày phát tín hiệu. Backtest chỉ chạy trên quá khứ; phần này kiểm tra chiến lược "tiến về phía trước" 2–3 tháng
trước khi bỏ tiền thật.

Mỗi lần tổng kết 15:20 (phiên đã đóng cửa), với từng phiên mới kể từ lần chạy trước:
  1. Lệnh BÁN chờ (tín hiệu bán lúc đóng cửa phiên trước: gãy MA10 tuần, lệnh không chạy, đóng cửa ≤ cắt lỗ)
     → bán giá MỞ CỬA (phải đủ T+2, phiên khoá sàn không bán được → chờ phiên sau).
  2. Lệnh MUA chờ (nhóm 🟢 / ✅ / 🟡 của tin tổng kết phiên trước, đúng phiên hiệu lực)
     → mua giá MỞ CỬA nếu mở cửa nằm trong vùng mua; ngoài vùng hoặc khoá trần → bỏ (giống luật "không đuổi").
     Khối lượng = RUI_RO_MOI_LENH_PCT % NAV ÷ (giá mua − cắt lỗ), nhóm 🟡 × ½, tối đa TY_TRONG_TOI_DA_AO % NAV,
     không vượt tiền mặt, làm tròn lô 100.
  3. Cắt lỗ trong phiên: giá thấp nhất ≤ cắt lỗ → bán ở min(mở cửa, cắt lỗ) (gap xuống thì ăn gap).
  4. Cuối phiên: chạy HỆ THOÁT (vi_the.danh_gia_ban – cùng hàm với danh mục thật) → dời cắt lỗ lên / xếp lệnh bán.
  5. Định giá NAV theo giá đóng cửa, ghi đường vốn kèm VN-Index để so sánh.
Rồi đặt lệnh mua chờ cho phiên tới từ danh sách mua vừa lập.

File (CÔNG KHAI – chỉ là vốn ảo, không dính danh mục thật):
  giao_dich_ao.json       trạng thái: tiền mặt, vị thế, lệnh chờ, phiên đã xử lý
  giao_dich_ao_lenh.csv   nhật ký lệnh đã đóng (mua – bán, lãi/lỗ sau phí)
  giao_dich_ao_von.csv    đường vốn mỗi phiên (NAV, tiền mặt, số mã, VN-Index)
Giá theo NGHÌN ĐỒNG như toàn bộ bot → tiền cũng tính theo nghìn đồng, hiển thị theo triệu.
"""
import json
import math
import os

import numpy as np
import pandas as pd

from . import cau_hinh as C

FILE_TRANG_THAI = "giao_dich_ao.json"
FILE_LENH = "giao_dich_ao_lenh.csv"
FILE_VON = "giao_dich_ao_von.csv"
NHOM_MUA = ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA")
MUC_BAN = {"CAT_LO": "cắt lỗ (đóng cửa)", "BAN_TUAN": "gãy MA10 tuần", "HET_HAN": "lệnh không chạy",
           "CHOT_LOI": "chốt lời"}
LO = 100
BIEN_DO_HOSE = 0.07
COT_LENH = ["ma", "nhom", "ngay_mua", "gia_mua", "ngay_ban", "gia_ban", "so_cp", "so_phien", "lai_pct", "lai_trieu",
            "ly_do"]
COT_VON = ["ngay", "nav", "tien", "so_ma", "vni"]


def _so(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _d(t):
    return f"{pd.Timestamp(t):%Y-%m-%d}"


# ------------------------------------------------------------------ trạng thái
def moi(ngay_bat_dau, von_trieu=None):
    """Tài khoản ảo mới. ngay_bat_dau = phiên dữ liệu cuối đã có → chỉ giao dịch từ phiên SAU (giá tương lai)."""
    von = float(von_trieu or C.VON_AO_TRIEU) * 1000                     # triệu → nghìn đồng
    return {"bat_dau": _d(ngay_bat_dau), "von_dau": von, "tien": von, "nav": von, "dinh_nav": von,
            "vi_the": {}, "lenh_cho": [], "ban_cho": {}, "da_xu_ly_den": _d(ngay_bat_dau)}


def doc(path=FILE_TRANG_THAI):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def ghi(tt, path=FILE_TRANG_THAI):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tt, f, ensure_ascii=False, indent=1)


def doc_csv(path, cot):
    try:
        return pd.read_csv(path, encoding="utf-8")
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=cot)


def _noi_csv(dong, path, cot):
    if dong:
        pd.DataFrame(dong, columns=cot).to_csv(path, mode="a", header=not os.path.exists(path), index=False,
                                               encoding="utf-8")


# ------------------------------------------------------------------ luật khớp lệnh trên nến ngày
def _vi_tri(df, s):
    try:
        return df.index.get_loc(pd.Timestamp(s))
    except KeyError:
        return None


def _khoa(df, i, chieu):
    """Phiên khoá trần (chieu=+1, không mua được) / khoá sàn (−1, không bán được): cả phiên một giá ở biên độ."""
    if i is None or i == 0:
        return False
    r, truoc = df.iloc[i], float(df.close.iloc[i - 1])
    if r.high > r.low:
        return False
    return (r.open >= truoc * (1 + BIEN_DO_HOSE * 0.93)) if chieu > 0 else (r.open <= truoc * (1 - BIEN_DO_HOSE * 0.93))


def _so_phien_giu(df, ngay_mua, i):
    j = _vi_tri(df, ngay_mua)
    return None if j is None else i - j


def _ban(tt, ma, gia, s, ly_do, so_phien):
    v = tt["vi_the"].pop(ma)
    tt["ban_cho"].pop(ma, None)
    thu = v["so_cp"] * gia * (1 - C.PHI_BAN_AO_PCT / 100)
    von = v["so_cp"] * v["gia_mua"] * (1 + C.PHI_MUA_AO_PCT / 100)
    tt["tien"] += thu
    return {"ma": ma, "nhom": v.get("nhom", ""), "ngay_mua": v["ngay_mua"], "gia_mua": round(v["gia_mua"], 2),
            "ngay_ban": _d(s), "gia_ban": round(gia, 2), "so_cp": int(v["so_cp"]), "so_phien": so_phien,
            "lai_pct": round((thu / von - 1) * 100, 2), "lai_trieu": round((thu - von) / 1000, 3), "ly_do": ly_do}


def _khoi_luong(tt, gia, cl, nhom, nav):
    rui_ro = gia - cl
    if rui_ro <= 0:
        return 0
    cp = nav * C.RUI_RO_MOI_LENH_PCT / 100 / rui_ro * (0.5 if nhom == "VAO_NUA" else 1.0)
    cp = min(cp, nav * C.TY_TRONG_TOI_DA_AO / 100 / gia, tt["tien"] / (gia * (1 + C.PHI_MUA_AO_PCT / 100)))
    return int(cp // LO) * LO


# ------------------------------------------------------------------ xử lý 1 phiên
def xu_ly_phien(tt, s, gia_ngay, danh_gia, vni=None):
    """
    tt: trạng thái (sửa tại chỗ) · s: phiên (Timestamp) · gia_ngay {mã: giá ngày đã đóng cửa} ·
    danh_gia(vt, kq, dn, bay_gio) → dict hệ thoát (vi_the.danh_gia_ban) · vni: giá đóng cửa VN-Index phiên s.
    → (sự kiện [str], lệnh đã đóng [dict], dòng vốn dict)
    """
    s = pd.Timestamp(s).normalize()
    su_kien, dong = [], []
    nav_truoc = tt.get("nav") or tt["von_dau"]

    # 1. bán giá mở cửa theo tín hiệu cuối phiên trước
    for ma, ly_do in list(tt["ban_cho"].items()):
        df = gia_ngay.get(ma)
        i = _vi_tri(df, s) if df is not None else None
        if ma not in tt["vi_the"]:
            tt["ban_cho"].pop(ma, None)
            continue
        if i is None:
            continue
        n = _so_phien_giu(df, tt["vi_the"][ma]["ngay_mua"], i)
        if (n is not None and n < 3) or _khoa(df, i, -1):            # T+2: CP về chiều T+2 → bán mở cửa từ T+3
            continue
        dong.append(_ban(tt, ma, float(df.open.iloc[i]), s, ly_do, n))
        su_kien.append(f"BÁN {ma} {dong[-1]['gia_ban']:,.2f} ({dong[-1]['lai_pct']:+.1f}%, {ly_do})")

    # 2. mua giá mở cửa – đúng phiên hiệu lực, mở cửa trong vùng
    con_cho = []
    for o in tt["lenh_cho"]:
        hl = pd.Timestamp(o["hieu_luc"])
        if hl > s:
            con_cho.append(o)
            continue
        if hl < s:
            su_kien.append(f"HUỶ {o['ma']} (không có giá phiên {hl:%d/%m})")
            continue
        df = gia_ngay.get(o["ma"])
        i = _vi_tri(df, s) if df is not None else None
        if i is None or o["ma"] in tt["vi_the"]:
            continue
        mo = float(df.open.iloc[i])
        tu, den, cl = _so(o.get("tu")), _so(o.get("den")), _so(o.get("cl"))
        if den is not None and mo > den:
            su_kien.append(f"BỎ {o['ma']}: mở cửa {mo:,.2f} > vùng {den:,.2f}")
            continue
        if tu is not None and mo < tu:
            su_kien.append(f"BỎ {o['ma']}: mở cửa {mo:,.2f} < vùng {tu:,.2f}")
            continue
        if _khoa(df, i, +1):
            su_kien.append(f"BỎ {o['ma']}: khoá trần")
            continue
        if cl is None or cl >= mo:
            su_kien.append(f"BỎ {o['ma']}: cắt lỗ không hợp lệ")
            continue
        cp = _khoi_luong(tt, mo, cl, o.get("nhom"), nav_truoc)
        if cp < LO:
            su_kien.append(f"BỎ {o['ma']}: không đủ tiền mặt")
            continue
        tt["tien"] -= cp * mo * (1 + C.PHI_MUA_AO_PCT / 100)
        tt["vi_the"][o["ma"]] = {"ngay_mua": _d(s), "gia_mua": mo, "so_cp": cp, "cat_lo_goc": cl, "cat_lo": cl,
                                 "nhom": o.get("nhom", "")}
        su_kien.append(f"MUA {o['ma']} {mo:,.2f} × {cp:,} CP (CL {cl:,.2f})")
    tt["lenh_cho"] = con_cho

    # 3. chạm cắt lỗ trong phiên · 4. hệ thoát cuối phiên
    for ma in list(tt["vi_the"]):
        v, df = tt["vi_the"][ma], gia_ngay.get(ma)
        i = _vi_tri(df, s) if df is not None else None
        if i is None:
            continue
        n = _so_phien_giu(df, v["ngay_mua"], i) or 0
        r = df.iloc[i]
        if n >= 2 and r.low <= v["cat_lo"] and not _khoa(df, i, -1):
            gia = min(float(r.open), v["cat_lo"])
            dong.append(_ban(tt, ma, gia, s, "chạm cắt lỗ", n))
            su_kien.append(f"BÁN {ma} {gia:,.2f} ({dong[-1]['lai_pct']:+.1f}%, chạm cắt lỗ)")
            continue
        try:
            kb = danh_gia({"gia_von": v["gia_mua"], "ngay_mua": v["ngay_mua"], "cat_lo_goc": v["cat_lo_goc"],
                           "cat_lo": v["cat_lo"]}, {"ma": ma, "gia": float(r.close)}, df.iloc[:i + 1],
                          s + pd.Timedelta(hours=15))
        except Exception as e:                                       # hệ thoát lỗi → giữ nguyên cắt lỗ
            print(f"  ⚠ giả lập – hệ thoát {ma}: {type(e).__name__}")
            kb = {}
        moi_cl = _so(kb.get("cat_lo"))
        if moi_cl is not None and moi_cl > v["cat_lo"]:
            v["cat_lo"] = moi_cl
        v["tang"] = kb.get("tang", v.get("tang", 0))
        if kb.get("muc") in MUC_BAN:
            tt["ban_cho"][ma] = MUC_BAN[kb["muc"]]

    # 5. định giá
    gia_tri = 0.0
    for ma, v in tt["vi_the"].items():
        df = gia_ngay.get(ma)
        d = df.close[df.index <= s] if df is not None else None
        gia_tri += v["so_cp"] * (float(d.iloc[-1]) if d is not None and len(d) else v["gia_mua"])
    nav = tt["tien"] + gia_tri
    tt["nav"], tt["dinh_nav"] = nav, max(tt.get("dinh_nav") or nav, nav)
    tt["da_xu_ly_den"] = _d(s)
    return su_kien, dong, {"ngay": _d(s), "nav": round(nav, 1), "tien": round(tt["tien"], 1),
                           "so_ma": len(tt["vi_the"]), "vni": _so(vni)}


def dat_lenh_cho(tt, ds_mua, hieu_luc):
    """Danh sách nhóm mua của tin tổng kết → lệnh mua chờ phiên hiệu lực (bỏ mã đang giữ / đã có lệnh)."""
    co = {(o["ma"], o["hieu_luc"]) for o in tt["lenh_cho"]}
    n = 0
    for k in ds_mua or []:
        hl = k.get("hieu_luc") or hieu_luc
        if k.get("nhom") not in NHOM_MUA or hl is None:
            continue
        hl = _d(hl)
        if k["ma"] in tt["vi_the"] or (k["ma"], hl) in co:
            continue
        tt["lenh_cho"].append({"ma": k["ma"], "nhom": k["nhom"], "hieu_luc": hl, "tu": _so(k.get("tu")),
                               "den": _so(k.get("den")), "cl": _so(k.get("cl"))})
        co.add((k["ma"], hl))
        n += 1
    return n


# ------------------------------------------------------------------ chạy mỗi tổng kết
def chay(ra, ds_mua, bay_gio, danh_gia=None, path=FILE_TRANG_THAI, path_lenh=FILE_LENH, path_von=FILE_VON):
    """
    ra: kết quả chien_luoc_bot.chay_chien_luoc (gia_ngay, vni_df, doc) · ds_mua: list dict nhóm mua (tong_ket_cl).
    → (trạng thái, sự kiện phiên vừa xử lý).
    """
    if danh_gia is None:
        from .vi_the import danh_gia_ban as danh_gia
    vni = ra["vni_df"]
    ngay_dl = pd.Timestamp(ra["doc"]["ngay"]).normalize()
    tt = doc(path) or moi(ngay_dl)
    phien = [s for s in vni.index if pd.Timestamp(tt["da_xu_ly_den"]) < s.normalize() <= ngay_dl]
    su_kien, dong, von = [], [], []
    if not os.path.exists(path_von):                                 # mốc 0 của đường vốn
        von.append({"ngay": tt["bat_dau"], "nav": tt["von_dau"], "tien": tt["von_dau"], "so_ma": 0,
                    "vni": _so(vni.close[vni.index <= pd.Timestamp(tt["bat_dau"])].iloc[-1])
                    if (vni.index <= pd.Timestamp(tt["bat_dau"])).any() else None})
    for s in phien:
        sk, dg, v = xu_ly_phien(tt, s, ra["gia_ngay"], danh_gia, float(vni.close.loc[s]))
        su_kien += [f"{s:%d/%m} {x}" for x in sk] if len(phien) > 1 else sk
        dong += dg
        von.append(v)
    hl = ngay_dl + pd.offsets.BDay(1)
    dat_lenh_cho(tt, ds_mua, hl)
    tt["cap_nhat"] = f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}"
    ghi(tt, path)
    _noi_csv(dong, path_lenh, COT_LENH)
    _noi_csv(von, path_von, COT_VON)
    return tt, su_kien


# ------------------------------------------------------------------ thống kê & tin
def thong_ke(tt, lenh, von):
    """Chỉ số tổng hợp của tài khoản ảo (dict)."""
    v = von.dropna(subset=["nav"]) if len(von) else von
    nav = float(tt.get("nav") or tt["von_dau"])
    x = {"nav": nav, "von_dau": tt["von_dau"], "lai_pct": (nav / tt["von_dau"] - 1) * 100,
         "so_phien": max(len(v) - 1, 0), "tien_pct": tt["tien"] / nav * 100 if nav else np.nan,
         "so_dang_giu": len(tt["vi_the"]), "so_lenh_cho": len(tt["lenh_cho"]), "mdd": 0.0, "vni_pct": np.nan,
         "so_lenh": len(lenh), "thang_pct": np.nan, "tb_lenh_pct": np.nan}
    if len(v):
        s = v.nav.astype(float)
        x["mdd"] = float((s / s.cummax() - 1).min() * 100)
        vn = v.vni.dropna().astype(float)
        if len(vn) >= 2:
            x["vni_pct"] = (vn.iloc[-1] / vn.iloc[0] - 1) * 100
    if len(lenh):
        p = lenh.lai_pct.astype(float)
        x["thang_pct"], x["tb_lenh_pct"] = float((p > 0).mean() * 100), float(p.mean())
    return x


def _bt_goc(kq_bt):
    """Dòng gốc (A0) của backtest điểm bán – để so kết quả thật với kỳ vọng."""
    try:
        return next(r for r in kq_bt["diem_ban"]["bang"] if r.get("Biến thể") == "A0")
    except (TypeError, KeyError, StopIteration):
        return None


def tin(tt, su_kien, lenh, von, kq_bt=None):
    """Mục 🧪 trong tin tổng kết (công khai)."""
    x = thong_ke(tt, lenh, von)
    tr = lambda v: f"{v / 1000:,.0f}"                               # noqa: E731 – nghìn đồng → triệu
    d = [f"🧪 GIAO DỊCH GIẢ LẬP – vốn ảo {tr(x['von_dau'])} tr từ {pd.Timestamp(tt['bat_dau']):%d/%m/%Y} "
         f"({x['so_phien']} phiên)",
         f"NAV {tr(x['nav'])} tr ({x['lai_pct']:+.1f}%)"
         + (f" · VN-Index {x['vni_pct']:+.1f}%" if x["vni_pct"] == x["vni_pct"] else "")
         + f" · sụt giảm lớn nhất {x['mdd']:.1f}%",
         f"Đang giữ {x['so_dang_giu']} mã · tiền mặt {x['tien_pct']:.0f}% · lệnh chờ phiên tới {x['so_lenh_cho']}"]
    if su_kien:
        d.append("Phiên vừa rồi: " + " · ".join(su_kien[:C.SO_MA_MOI_NHOM])
                 + (f" … (+{len(su_kien) - C.SO_MA_MOI_NHOM})" if len(su_kien) > C.SO_MA_MOI_NHOM else ""))
    if x["so_lenh"]:
        bt = _bt_goc(kq_bt)
        d.append(f"Đã đóng {x['so_lenh']} lệnh: thắng {x['thang_pct']:.0f}% · TB {x['tb_lenh_pct']:+.2f}%/lệnh"
                 + (f" (backtest: thắng {bt['Thắng %']:.0f}%, TB {bt['TB/lệnh %']:+.2f}%)" if bt else ""))
    con = C.SO_PHIEN_GIA_LAP_TOI_THIEU - x["so_phien"]
    d.append(f"Còn {con} phiên nữa mới đủ {C.SO_PHIEN_GIA_LAP_TOI_THIEU} phiên (~3 tháng) để đánh giá – chưa nên "
             f"dùng tiền thật." if con > 0 else
             f"Đã đủ {C.SO_PHIEN_GIA_LAP_TOI_THIEU} phiên – so kết quả với backtest trước khi dùng tiền thật.")
    if x["so_lenh"] < 30:
        d.append("(ít lệnh – tỷ lệ thắng chưa có ý nghĩa thống kê)")
    return "\n".join(d)
