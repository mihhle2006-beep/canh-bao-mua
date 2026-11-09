# -*- coding: utf-8 -*-
"""
DỰNG DỮ LIỆU bảng thị trường.
  chuan_bi(): chạy SAU PHIÊN (≈ 19h, khi nguồn đã có số cuối ngày) – danh sách mã & ngành, lịch sử ngày 260 phiên (lọc kỹ
    thuật, khối ngoại 5 / 20 phiên, KL TB20), tự doanh từng mã HOSE, khối ngoại / tự doanh cả sàn, hồ sơ thanh khoản 1'
    20 phiên, VN-Index ngày 1 năm → cache_thi_truong/chuan_bi.json (giữ qua actions/cache).
  chup(): mỗi 5' trong phiên – chỉ số, nến 1', bảng giá mọi mã, tác động, mua / bán chủ động top GTGD → du_lieu.json
    cho trang docs/thi_truong/index.html.
"""
import json
import os

import numpy as np
import pandas as pd

from . import nguon
from . import tinh

THU_MUC_CACHE = "cache_thi_truong"
FILE_CB = os.path.join(THU_MUC_CACHE, "chuan_bi.json")
FILE_RA = os.path.join("docs", "thi_truong", "du_lieu.json")
TEN_CHI_SO = {"VNINDEX": "VN-Index", "VN30": "VN30", "HNXIndex": "HNX-Index", "HNX30": "HNX30",
              "HNXUpcomIndex": "UPCoM-Index", "VN30F1M": "VN30F1M"}
SAN = ("HSX", "HNX", "UPCOM")
GT_UPCOM_TOI_THIEU = 0.3          # tỷ – mã UPCoM đưa vào lọc nếu GTGD phiên chuẩn bị ≥ mức này (còn lại quá kém thanh khoản)
GT_DU_THANH_KHOAN = 2.0           # tỷ / phiên TB 20 phiên → "đủ thanh khoản"
SO_MA_CHU_DONG = 150              # số mã GTGD lớn nhất được tính mua / bán chủ động mỗi lần chụp
RUT_GON_NGANH = {"Hàng & Dịch vụ Công nghiệp": "Hàng & DV công nghiệp", "Dịch vụ tài chính": "DV tài chính",
                 "Điện, nước & xăng dầu khí đốt": "Điện, nước & khí đốt", "Thực phẩm và đồ uống": "Thực phẩm & đồ uống",
                 "Xây dựng và Vật liệu": "Xây dựng & VLXD", "Hàng cá nhân & Gia dụng": "Hàng cá nhân & gia dụng",
                 "Ô tô và phụ tùng": "Ô tô & phụ tùng", "Du lịch và Giải trí": "Du lịch & giải trí",
                 "Công nghệ Thông tin": "Công nghệ", "Tài nguyên Cơ bản": "Tài nguyên cơ bản"}
BIT = {"vuot_dinh52": 1, "thung_day52": 2, "len20": 4, "len50": 8, "xuong20": 16, "xuong50": 32}


def _ghi(obj, duong):
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False, default=_mac_dinh)
    os.replace(tam, duong)


def _mac_dinh(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x) if np.isfinite(x) else None
    if isinstance(x, np.bool_):
        return bool(x)
    raise TypeError(type(x))


def _r(x, n=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, n) if np.isfinite(v) else None


def chuan_bi(ra=FILE_CB, luong=8, in_tien_do=print):
    """Dữ liệu ít đổi trong ngày (gọi sau phiên / khi cache thiếu)."""
    from . import quy_web
    quy = quy_web.lay((doc_chuan_bi(ra) or {}).get("quy") or quy_web.tu_trang_trien_khai(), in_tien_do)
    tat = nguon.tat_ca_ma()
    cp = [d for d in tat if d.get("type") == "STOCK" and d.get("board") in SAN]
    ten_icb = nguon.ten_nganh()
    nganh = {}
    for d in cp:
        ten = ten_icb.get(str(d.get("icbCode2") or ""), "")
        nganh[d["symbol"]] = RUT_GON_NGANH.get(ten, ten) or "Khác"
    bang = tinh.chuan_bang(nguon.bang_gia([d["symbol"] for d in cp]))
    vu = [d["symbol"] for d in cp if d["board"] in ("HSX", "HNX")]
    if len(bang):
        vu += [m for m in bang.index[(bang["san"] == "UPCOM") & (bang["gt"] >= GT_UPCOM_TOI_THIEU)]]
    in_tien_do(f"chuẩn bị: {len(cp)} cổ phiếu, lọc {len(vu)} mã; tải lịch sử ngày…")
    tho = nguon.song_song(lambda m: nguon.lich_su_ngay(m, 260), vu, luong)
    ls = {}
    for m, ds in tho.items():
        a = tinh.tom_lich_su(ds)
        if a:
            ls[m] = {"day_du": a, "bo_cuoi": tinh.tom_lich_su(ds, truoc_ngay=a["ngay"])}
    hsx = [d["symbol"] for d in cp if d["board"] == "HSX"]
    in_tien_do(f"  lịch sử {len(ls)}/{len(vu)} mã; tự doanh {len(hsx)} mã HOSE…")
    td = {}
    for m, ds in nguon.song_song(lambda m: nguon.tu_doanh_ma(m, 3), hsx, luong).items():
        x = sorted(((str(r.get("tradingDate"))[:10], (r.get("totalTradeNetValue") or 0) / 1e9) for r in ds or []),
                   reverse=True)
        if x:
            td[m] = [x[0][0], round(x[0][1], 3)]
    n1 = nguon.nen("VNINDEX", "ONE_MINUTE", 6000)
    ngay = nguon.nen("VNINDEX", "ONE_DAY", 260)
    d1 = []
    if ngay and ngay.get("t"):
        t = pd.to_datetime([int(float(x)) for x in ngay["t"]], unit="s") + tinh.LECH_GIO
        d1 = [[f"{a:%Y-%m-%d}", _r(c)] for a, c in zip(t, ngay["c"])]
    cb = {"tao_luc": f"{tinh.gio_vn():%Y-%m-%d %H:%M}", "nganh": nganh,
          "ten": {d["symbol"]: d.get("organShortName") or "" for d in cp}, "vu": vu, "ls": ls, "td": td,
          "nn_san": tinh.theo_ngay_cafef(nguon.cafef("GDKhoiNgoai", "VNINDEX", 30), "GtMua", "GtBan", "Ngay"),
          "td_san": tinh.theo_ngay_cafef(nguon.cafef("GDTuDoanh", "VNINDEX", 30), "GtMua", "GtBan", "Date"),
          "ho_so": tinh.ho_so_thanh_khoan(n1, so_phien=30), "vni_ngay": d1,
          "nhom": {g: nguon.nhom(g) for g in ("VN30", "HNX30")}, "quy": quy}
    _ghi(cb, ra)
    in_tien_do(f"  xong: {ra} ({os.path.getsize(ra) / 1e6:.1f} MB)")
    return cb


def doc_chuan_bi(duong=FILE_CB):
    try:
        with open(duong, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _the_chi_so(ci, nen1, phien):
    """Thẻ chỉ số + đường trong phiên (phút từ 9:00, giá đóng cửa 1')."""
    the = []
    for x in ci:
        ma = x.get("symbol")
        df = tinh.nen_phien(nen1.get(ma), phien)
        the.append({"ma": ma, "ten": TEN_CHI_SO.get(ma, ma), "gia": _r(x.get("price")), "tc": _r(x.get("refPrice")),
                    "td": _r(x.get("change")), "pt": _r(x.get("changePercent")),
                    "gt": _r((x.get("totalValue") or 0) / 1000, 0),
                    "tang": x.get("totalStockIncrease"), "giam": x.get("totalStockDecline"),
                    "dung": x.get("totalStockNoChange"), "tran": x.get("totalStockCeiling"),
                    "san": x.get("totalStockFloor"), **_duong(df)})
    return the


def _duong(df):
    if not len(df):
        return {"t": [], "c": []}
    phut = ((df.index - df.index.normalize()).total_seconds() / 60 - 9 * 60).astype(int)
    return {"t": phut.tolist(), "c": [_r(v) for v in df["c"]]}


def _phai_sinh(nen_f, nen_f_ngay, vn30, phien):
    """VN30F1M: giá cuối, tham chiếu = đóng cửa phiên trước (nến ngày), basis so với VN30."""
    df = tinh.nen_phien(nen_f, phien)
    if not len(df):
        df = tinh.nen_phien(nen_f)
    if not len(df):
        return None
    tc = None
    if nen_f_ngay and nen_f_ngay.get("t"):
        t = pd.to_datetime([int(float(x)) for x in nen_f_ngay["t"]], unit="s") + tinh.LECH_GIO
        truoc = [c for a, c in zip(t, nen_f_ngay["c"]) if a.normalize() < df.index[-1].normalize()]
        tc = float(truoc[-1]) if truoc else None
    gia = float(df["c"].iloc[-1])
    return {"ma": "VN30F1M", "ten": "VN30F1M", "gia": _r(gia, 1), "tc": _r(tc, 1),
            "td": _r(gia - tc, 1) if tc else None, "pt": _r((gia / tc - 1) * 100) if tc else None,
            "basis": _r(gia - vn30, 1) if vn30 else None, **_duong(df)}


FILE_CHIEN_LUOC = "trang_thai_chien_luoc.json"


def ma_dang_giu(duong=None):
    """Mã đang giữ (CHỈ mã – không số lượng / giá vốn) cho mục 💼 của trang: workflow đọc cột "ma" danh_muc.csv (repo
    danh-muc) ra file tạm ngoài repo, đường dẫn ở biến MA_GIU_FILE (chủ quỹ 05/11/2026 chọn hiện công khai). Không có → []."""
    import re
    duong = duong or os.environ.get("MA_GIU_FILE")
    if not duong:
        return []
    try:
        with open(duong, encoding="utf-8") as f:
            ma = re.split(r"[^A-Za-z0-9]+", f.read())
    except OSError:
        return []
    return sorted({m.upper() for m in ma if re.fullmatch(r"[A-Za-z0-9]{3,8}", m or "")})
TEN_NHOM_BOT = {"MUA_MOI": "Mua mới", "VAO_NHU_MOI": "Vào như lệnh mới", "VAO_NUA": "Vào ½"}


def tin_hieu_bot(duong=None):
    """Danh sách mua CÔNG KHAI của bot (canh-bao-mua lưu sau tổng kết 15:20) → [[mã, nhóm, từ, đến, cắt lỗ, mục tiêu 1R,
    3R, lý do]] + ngày hiệu lực. Không có file → None."""
    try:
        with open(duong or FILE_CHIEN_LUOC, encoding="utf-8") as f:
            ds = (json.load(f).get("ds_mua") or {})
    except (OSError, ValueError):
        return None
    ma = [[x.get("ma"), TEN_NHOM_BOT.get(x.get("nhom"), x.get("nhom") or ""), _r(x.get("tu")), _r(x.get("den")),
           _r(x.get("cl")), _r(x.get("mt1")), _r(x.get("mt3")), x.get("ly_do") or ""] for x in ds.get("ma") or [] if x.get("ma")]
    return {"hieu_luc": ds.get("hieu_luc"), "ma": ma} if ma else None


SO_PHIEN_DT = (5, 10, 20)                     # dòng tiền / tác động nhiều phiên (kiểu FiinTrade 1 · 5 · 10 · 20 ngày)


def _ls_truoc(cb, m, ps):
    """Lịch sử gọn của mã chỉ gồm phiên TRƯỚC phiên ps."""
    ls = (cb.get("ls") or {}).get(m) or {}
    return ls.get("bo_cuoi") if (ls.get("day_du") or {}).get("ngay", "") >= ps else ls.get("day_du")


def doi_n_phien(c, gia, n):
    """% đổi giá hiện tại so đóng cửa n phiên trước (c: đóng cửa các phiên TRƯỚC hôm nay, cũ → mới; c[-1] = phiên trước)."""
    if not c or len(c) < n or not c[-n] or not gia:
        return None
    return (gia / c[-n] - 1) * 100


def tac_dong_n(H, cb, ps, vni_gia, vni_ngay, so=SO_PHIEN_DT, top=10):
    """Tác động lên VN-Index n phiên – mã HOSE (cổ phiếu): Δgiá (so đóng cửa n phiên trước) × CP niêm yết ÷ hệ số chia
    (tổng vốn hoá hiện tại ÷ VN-Index hiện tại). Giá lịch sử đã điều chỉnh → xấp xỉ (lệch nhỏ ở mã có GDKHQ trong kỳ).
    → {"5": {"len": [[mã, điểm, %]…], "xuong": […], "rong": VN-Index đổi thật (điểm)}, …}."""
    st = H[H["loai"] == "STOCK"]
    von = float((st["gia"] * st["cp"]).sum()) if len(st) else 0.0
    if not vni_gia or von <= 0:
        return {}
    chia = von / float(vni_gia)
    truoc = [v for d, v in vni_ngay if d < ps and v]
    out = {}
    for n in so:
        ds = []
        for m, r in st.iterrows():
            c = (_ls_truoc(cb, m, ps) or {}).get("c") or []
            if len(c) >= n and c[-n] and r["gia"] > 0 and r["cp"] > 0:
                ds.append([m, _r((r["gia"] - c[-n]) * r["cp"] / chia), _r((r["gia"] / c[-n] - 1) * 100)])
        if not ds:
            continue
        ds.sort(key=lambda x: x[1])
        out[str(n)] = {"len": [x for x in ds[::-1][:top] if x[1] > 0], "xuong": [x for x in ds[:top] if x[1] < 0],
                       "rong": _r(float(vni_gia) - truoc[-n]) if len(truoc) >= n else None}
    return out


def chup(cb, ra=FILE_RA, luc=None, in_tien_do=print):
    luc = luc or tinh.gio_vn()
    ma_cs = list(nguon.CHI_SO) + ["VN30F1M"]
    nen1 = nguon.song_song(lambda m: nguon.nen(m, "ONE_MINUTE", 1600 if m == "VNINDEX" else 400), ma_cs, 6)
    ci = nguon.chi_so()
    dv = tinh.nen_phien(nen1.get("VNINDEX"))
    phien = dv.index[-1].normalize() if len(dv) else luc.normalize()
    ps = f"{phien:%Y-%m-%d}"
    the = _the_chi_so(ci, nen1, phien)
    vn30 = next((x["gia"] for x in the if x["ma"] == "VN30"), None)
    f = _phai_sinh(nen1.get("VN30F1M"), nguon.nen("VN30F1M", "ONE_DAY", 5), vn30, phien)
    if f:
        the.append(f)
    # bảng giá: mọi mã HOSE (cả ETF / CW – tính GTGD & khối ngoại cả sàn) + mã lọc HNX / UPCoM
    tat = nguon.tat_ca_ma()
    hsx = [d["symbol"] for d in tat if d.get("board") == "HSX"]
    B = tinh.chuan_bang(nguon.bang_gia(list(dict.fromkeys(hsx + cb["vu"]))))
    in_tien_do(f"phiên {ps}: bảng giá {len(B)} mã")
    H = B[B["san"] == "HSX"]
    vni = next((x for x in the if x["ma"] == "VNINDEX"), {})
    # thanh khoản: khớp = tổng GT khớp các mã HOSE; tổng = GTGD chỉ số; dự kiến theo hồ sơ 1' 20 phiên
    ho_so = cb.get("ho_so")
    truoc = [v for d, v in (ho_so or {}).get("ngay", []) if d < ps][-20:]
    dang_gd = phien.normalize() == luc.normalize() and luc.hour * 60 + luc.minute < 15 * 60 + 5
    ty_le = tinh.ty_le_luc(ho_so, luc) if dang_gd else 1.0
    khop, tong = float(H["gt"].sum()), float(vni.get("gt") or 0)
    tk = {"khop": _r(khop, 0), "tong": _r(tong, 0), "thoa_thuan": _r(tong - khop, 0) if tong - khop > 0.01 * tong else None,
          "du_kien": _r(tong / ty_le, 0) if ty_le else None, "tb20": _r(np.mean(truoc), 0) if truoc else None,
          "ty_le": _r(ty_le, 3)}
    # khối ngoại & tự doanh cả sàn HOSE
    nn_nay = float(H["nn"].sum())
    nn_ls = [(d, v) for d, v in cb.get("nn_san", []) if d < ps]
    gt_nn = [nn_nay] + [v for _, v in nn_ls]
    kn = {"hom_nay": _r(nn_nay, 1), "chuoi": tinh.chuoi(gt_nn), "tong20": _r(sum(gt_nn[:20]), 0),
          "ls": [_r(v, 1) for v in gt_nn[:20]][::-1]}
    td_ls = cb.get("td_san", [])
    tdo = {"phien": td_ls[0][0] if td_ls else None, "rong": _r(td_ls[0][1], 1) if td_ls else None,
           "tong20": _r(sum(v for _, v in td_ls[:20]), 0) if td_ls else None,
           "ls": [_r(v, 1) for _, v in td_ls[:20]][::-1]}
    # tác động lên VN-Index
    tac = nguon.tac_dong()
    pt = B["pt"].to_dict()

    def _tac(ds):
        return [[x.get("symbol"), _r(x.get("impact")), _r(pt.get(x.get("symbol")))] for x in ds or []]

    tac_dong = {"rong": vni.get("td"), "len": _tac(tac.get("topUp")), "xuong": _tac(tac.get("topDown")),
                "n": tac_dong_n(H, cb, ps, vni.get("gia"), cb.get("vni_ngay", []))}
    # nhóm ngành chung (bản đồ nhiệt + lọc)
    ten_nganh = sorted(set(cb["nganh"].values()))
    so_nganh = {t: i for i, t in enumerate(ten_nganh)}
    # bản đồ nhiệt HOSE (cổ phiếu)
    hm = []
    for m, r in H[H["loai"] == "STOCK"].iterrows():
        vh = r["gia"] * r["cp"] / 1e9
        if vh <= 0:
            continue
        tdm = cb.get("td", {}).get(m)
        hm.append([m, so_nganh.get(cb["nganh"].get(m, "Khác"), so_nganh.get("Khác", 0)), _r(vh, 0), _r(r["pt"]),
                   _r(r["gt"]), _r(r["nn"]), _r(tdm[1]) if tdm else None, {"tran": 1, "san": -1}.get(r["tt"], 0)])
    # mua / bán chủ động: top GTGD
    cp = B[(B["loai"] == "STOCK") & B.index.isin(cb["vu"])]
    top = cp.sort_values("gt", ascending=False).head(SO_MA_CHU_DONG).index
    mcd = {m: tinh.mua_chu_dong(v) for m, v in nguon.song_song(nguon.buoc_gia, top, 8).items()}
    # bảng lọc
    dong = []
    for m, r in cp.iterrows():
        ls = _ls_truoc(cb, m, ps)
        kt = tinh.ky_thuat(ls, r["gia"])                              # lịch sử IQ & bảng giá cùng đơn vị đồng
        bit = sum(v for k, v in BIT.items() if kt.get(k))
        nn_ls = (ls or {}).get("nn") or []
        gia_nn = [float(r["nn"])] + nn_ls
        kl_x = None
        if ls and ls.get("kl20") and ty_le:
            kl_x = _r(r["kl"] / (ls["kl20"] * ty_le), 2)
        dong.append([m, r["san"], so_nganh.get(cb["nganh"].get(m, "Khác"), 0), _r(r["gia"] / 1000, 2), _r(r["pt"]),
                     _r(r["gt"]), kl_x, mcd.get(m), _r(r["nn"]), _r(sum(gia_nn[:5])), _r(sum(gia_nn[:20])),
                     tinh.chuoi(gia_nn), _r(r["tc"] / 1000, 2), _r(r["tran"] / 1000, 2), _r(r["san_gia"] / 1000, 2),
                     _r(r["cao"] / 1000, 2), _r(r["thap"] / 1000, 2), {"tran": 1, "san": -1}.get(r["tt"], 0),
                     _r((ls or {}).get("gt20"), 1), bit, kt.get("rsi"), int(bool(r["co_gd"])),
                     *[_r(doi_n_phien((ls or {}).get("c"), r["gia"], n)) for n in SO_PHIEN_DT], _r(sum(gia_nn[:10]))])
    vni_ngay = [x for x in cb.get("vni_ngay", []) if x[0] < ps] + ([[ps, vni.get("gia")]] if vni.get("gia") else [])
    w = _tuan(nen1.get("VNINDEX"))
    out = {"cap_nhat": f"{luc:%Y-%m-%d %H:%M:%S}", "phien": ps, "dang_gd": bool(dang_gd), "chi_so": the,
           "vni_ngay": vni_ngay[-260:], "vni_tuan": w, "thanh_khoan": tk, "khoi_ngoai": kn, "tu_doanh": tdo,
           "tac_dong": tac_dong, "nganh": ten_nganh,
           "ban_do": {"cot": ["ma", "nganh", "vh", "pt", "gt", "nn", "td", "tt"], "dong": hm},
           "loc": {"cot": ["ma", "san", "nganh", "gia", "pt", "gt", "kl_x", "mcd", "nn", "nn5", "nn20", "chuoi", "tc",
                           "tran", "san_gia", "cao", "thap", "tt", "gt20", "bit", "rsi", "co_gd", "p5", "p10", "p20", "nn10"],
                   "dong": dong,
                   "bit": BIT, "du_tk": GT_DU_THANH_KHOAN},
           "ten": {m: cb.get("ten", {}).get(m, "") for m in cp.index},
           "nhom": cb.get("nhom", {}), "chuan_bi": cb.get("tao_luc"), "tin_hieu": tin_hieu_bot(), "danh_muc": ma_dang_giu(),
           "quy": {k: v for k, v in (cb.get("quy") or {}).items() if k != "ls"} or None}
    _ghi(out, ra)
    if (cb.get("quy") or {}).get("ls"):                              # lịch sử danh mục quỹ: file riêng (trang không tải)
        _ghi(cb["quy"]["ls"], os.path.join(os.path.dirname(ra), "quy_ls.json"))
    in_tien_do(f"  xong: {ra} ({os.path.getsize(ra) / 1e3:.0f} KB) · khớp {khop:,.0f} / tổng {tong:,.0f} tỷ · "
               f"NN {nn_nay:+,.0f} tỷ · {len(dong)} mã lọc · {len(hm)} ô bản đồ")
    return out


def _tuan(nen1):
    """5 phiên gần nhất, nến 5' (giờ VN dạng 'dd/mm HH:MM', đóng cửa)."""
    if not nen1 or not nen1.get("t"):
        return {"t": [], "c": []}
    t = pd.to_datetime([int(float(x)) for x in nen1["t"]], unit="s") + tinh.LECH_GIO
    s = pd.Series(pd.to_numeric(pd.Series(nen1["c"]), errors="coerce").to_numpy(), index=t)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    ngay = sorted(set(s.index.normalize()))[-5:]
    s = s[s.index.normalize().isin(ngay)]
    s = s.groupby(s.index.floor("5min")).last()
    return {"t": [f"{x:%d/%m %H:%M}" for x in s.index], "c": [_r(v) for v in s]}
