# -*- coding: utf-8 -*-
"""
BẢN TIN CHIẾN LƯỢC CL1 / CL2 cho bot (dùng ptcp/chien_luoc.py + ptcp/he_thoat.py – MỘT nguồn logic với Colab).

  Mỗi ngày (sau tổng kết 15:20, hoặc python chay.py --che_do chien_luoc):
    1. Điểm thị trường 8 chỉ báo của VN-Index (phiên đã đóng) → CL đang áp dụng theo vùng đệm
       (đổi ở phiên cuối tháng: điểm ≥ 5 → CL2, ≤ 2 → CL1, 3–4 giữ nguyên).
    2. Mô phỏng 2 thành phần trên MA_CHIEN_LUOC (41 mã đã backtest):
         A0 = vào MACD ngày KHÔNG lọc tuần · B = vào MACD ngày lọc tuần + nhồi lệnh; cả hai thoát theo hệ thoát mới.
       → mã MUA phiên tới (giá mở cửa), mã hệ thống đang giữ (cắt lỗ phiên tới, tầng), mã BÁN phiên tới.
    3. Tỷ trọng mục tiêu từng mã (% tổng vốn) theo CL đang áp dụng; phần VN-Index (ETF) & tiền mặt.
  Tin CÔNG KHAI: chỉ có danh sách mô phỏng của hệ thống, không dùng danh mục thật.
  Đổi CL so với lần chạy trước (trang_thai_chien_luoc.json) → gửi thêm tin 🔔 ĐỔI CHIẾN LƯỢC.
"""
import json
import os

import numpy as np
import pandas as pd

from . import cau_hinh as C


def _phien_da_dong(df, bay_gio):
    from .vi_the import _phien_da_dong as f
    return f(df, bay_gio)


def _dung_duoc(df, tu):
    """Dữ liệu có sẵn dùng lại được nếu bắt đầu không muộn hơn ngày cần ~15 ngày."""
    return df is not None and len(df) >= 260 and df.index[0] <= pd.Timestamp(tu) + pd.Timedelta(days=15)


def _bang_diem_mua(cuoi, x, kl_mac_dinh):
    """Trạng thái cuối của bộ mô phỏng (he_thoat.mo_phong) → 1 dòng: MUA phiên tới / ĐANG GIỮ / CHỜ."""
    from ptcp.he_thoat import stop_chuan
    c, atr, n = x["c"], x["atr"], len(x["c"])
    r = {"Giá đóng cửa": float(c[-1])}
    vt = cuoi["vi_the"]
    if vt is not None:
        ban = bool(vt.get("Bán phiên tới (MA10 tuần)"))
        r.update({"Trạng thái": "ĐANG GIỮ" + (" → BÁN phiên tới (đóng cửa tuần < MA10 tuần)" if ban else ""),
                  "Cắt lỗ phiên tới": float(vt["Cắt lỗ phiên tới"]), "Tầng": int(vt["Tầng"]),
                  "Ngày mua": vt["Ngày mua"], "Giá mua": float(vt["Giá mua"]),
                  "Lãi hiện tại %": float(vt["Lãi hiện tại %"]), "Lãi (R)": float(vt.get("Lãi (R)", np.nan)), "KL (phần vốn)": float(vt.get("KL (phần vốn)", 1.0)),
                  "Số lần nhồi": int(vt.get("Số lần nhồi", 0))})
    elif cuoi["cho_vao"] is not None and cuoi["cho_vao"]["j_mua"] == n:
        cv = cuoi["cho_vao"]
        r.update({"Trạng thái": f"MUA phiên tới (giá mở cửa) – {cv['kind']}",
                  "Khối lượng (phần vốn)": float(cv.get("kl", kl_mac_dinh)),
                  "Cắt lỗ dự kiến": float(stop_chuan(c[-1], atr[-1]))})
    else:
        r["Trạng thái"] = "CHỜ tín hiệu"
    return r


def _hanh_dong(dm, ty, ngay=None):
    try:
        from ptcp.chien_luoc import hanh_dong
    except ImportError:                                     # ptcp cũ chưa có bảng hành động
        return None
    try:
        return hanh_dong(dm, ty, ngay)
    except TypeError:                                       # ptcp cũ: chưa có vùng mua
        return hanh_dong(dm, ty)


def chay_chien_luoc(tai, bay_gio, du_lieu_san=None, vni=None, ds_ma=None):
    """
    tai(ma, tu_ngay, chi_so=False) → giá ngày. du_lieu_san: {mã: giá ngày} đã tải (dùng lại nếu đủ dài).
    Trả (ra, None) hoặc (None, lý do lỗi).
    """
    try:
        from ptcp.chi_bao import tinh_chi_bao
        from ptcp.chien_luoc import (NGUONG_LEN, NGUONG_XUONG, TEN_CL, TY_TRONG, bang_chi_bao, doc_thi_truong,
                                     lich_chien_luoc, phan_bo_muc_tieu)
        from ptcp.du_lieu import gop_tuan
        from ptcp.he_thoat import chuan_bi, danh_sach_bien_the, mo_phong, tin_hieu_macd
    except ImportError as e:
        return None, f"ptcp chưa có module chiến lược (cập nhật ptcp trong repo danh-muc): {e}"
    tu = C.NGAY_BAT_DAU_CL
    ds_ma = list(dict.fromkeys(m.strip().upper() for m in (ds_ma or C.MA_CHIEN_LUOC) if m.strip()))
    vni = vni if _dung_duoc(vni, tu) else tai("VNINDEX", tu, chi_so=True)
    if vni is None or len(vni) < 260:
        return None, "không có dữ liệu VN-Index"
    vni = _phien_da_dong(vni, bay_gio)
    bts = {b.ma: b for b in danh_sach_bien_the(co_vni=False, vao_phu=False)}
    thanh_phan = {"A0": (bts["A0"], False), "B": (bts["B"], True)}
    gia, diem_mua, thieu, gia_ngay, atr = {}, {k: [] for k in thanh_phan}, [], {}, {}
    for ma in ds_ma:
        df = (du_lieu_san or {}).get(ma)
        if not _dung_duoc(df, tu):
            df = tai(ma, tu)
        df = _phien_da_dong(df, bay_gio) if df is not None else None
        if df is None or len(df) < 260:
            thieu.append(ma)
            continue
        df = df[["open", "high", "low", "close", "volume"]]
        d, w = tinh_chi_bao(df), tinh_chi_bao(gop_tuan(df))
        x = chuan_bi(d)
        gia[ma] = d.close
        gia_ngay[ma], atr[ma] = df, float(d.ATR.iloc[-1])
        for ten, (bt, loc) in thanh_phan.items():
            try:                                           # A0: lọc thị trường đi ngang (ptcp mới)
                sig = tin_hieu_macd(d, w, loc_tuan=loc, vni=vni)
            except TypeError:
                sig = tin_hieu_macd(d, w, loc_tuan=loc)
            r = mo_phong(x, sig, bt)
            diem_mua[ten].append({"Mã": ma, **_bang_diem_mua(r["cuoi"], x, 0.5 if bt.nhoi else 1.0)})
    if len(gia) < 5:
        return None, f"quá ít mã có dữ liệu ({len(gia)}/{len(ds_ma)})"
    F, diem, muc = bang_chi_bao(vni, pd.DataFrame(gia))
    lich, _, cl_hien = lich_chien_luoc(diem)
    doc = doc_thi_truong(F, diem, muc, cl_hien)
    dm = {k: pd.DataFrame(v) for k, v in diem_mua.items()}
    ngang = None
    try:
        from ptcp import cau_hinh as pcfg
        from ptcp.he_thoat import di_ngang_vni
        if getattr(pcfg, "HT_LOC_DI_NGANG", True):
            ng, bien = di_ngang_vni(vni)
            ngang = {"dang": bool(ng.iloc[-1]), "bien": float(bien.iloc[-1]), "nguong": getattr(pcfg, "HT_NGANG_BIEN_PCT", 12.0),
                     "phien": getattr(pcfg, "HT_NGANG_PHIEN", 60)}
    except ImportError:
        pass
    ty = TY_TRONG[cl_hien]
    return {"doc": doc, "cl": cl_hien, "ten_cl": TEN_CL, "ty_trong": ty, "ty_trong_cl": TY_TRONG,
            "nguong": (NGUONG_LEN, NGUONG_XUONG), "lich": lich, "diem_mua": dm,
            "phan_bo": phan_bo_muc_tieu(dm, ty, len(gia)), "hanh_dong": _hanh_dong(dm, ty, doc["ngay"]),
            "so_ma": len(gia), "thieu": thieu, "gia_ngay": gia_ngay, "di_ngang": ngang, "atr": atr, "vni_df": vni,
            "vni": float(vni.close.iloc[-1])}, None


# ------------------------------------------------------------------ đổi chiến lược
def kiem_tra_doi(ra, bay_gio, path=None):
    """So CL hiện tại với lần chạy trước (file trạng thái, công khai được). → (đổi?, CL cũ | None)."""
    path = path or C.FILE_TRANG_THAI_CL
    try:
        with open(path, encoding="utf-8") as f:
            cu = json.load(f)
    except (OSError, ValueError):
        cu = {}
    cl_cu = cu.get("cl")
    cu.update({"cl": int(ra["cl"]), "diem": int(ra["doc"]["diem"]), "ngay_du_lieu": f"{ra['doc']['ngay']:%Y-%m-%d}",
               "cap_nhat": f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}"})          # giữ các khoá khác (danh sách mua)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cu, f, ensure_ascii=False, indent=1)
    if cl_cu is None:                    # chưa có trạng thái (lần đầu / mất file): đổi đúng ở phiên cuối tháng vừa đóng?
        lich = ra.get("lich")
        if lich is not None and len(lich):
            r = lich.iloc[-1]
            if bool(r["Đổi"]) and pd.Timestamp(r["Phiên quyết định"]) == pd.Timestamp(ra["doc"]["ngay"]):
                return True, int(r["CL trước"])
        return False, None
    return int(cl_cu) != int(ra["cl"]), int(cl_cu)


def _f(x, le=2):
    return "–" if x is None or x != x else f"{x:,.{le}f}"


def _ty_trong(w):
    return f"A0 {w['A0'] * 100:.0f}% · B {w['B'] * 100:.0f}% · VN-Index {w['VNI'] * 100:.0f}%"


def tin_doi(ra, cl_cu):
    d, ten = ra["doc"], ra["ten_cl"]
    w_cu = ra["ty_trong_cl"].get(int(cl_cu)) if cl_cu is not None else None
    return "\n".join([
        f"🔔 ĐỔI CHIẾN LƯỢC: CL{cl_cu} → CL{ra['cl']} (dữ liệu {d['ngay']:%d/%m/%Y})",
        f"Điểm thị trường hiện tại: {d['diem']}/{d['so_chi_bao']} "
        f"(≥ {ra['nguong'][0]} → CL2, ≤ {ra['nguong'][1]} → CL1)",
        f"Đang áp dụng: {ten[ra['cl']]}",
        f"Tỷ trọng mới: {_ty_trong(ra['ty_trong'])}" + (f" (trước: {_ty_trong(w_cu)})" if w_cu else ""),
        "➜ Tái cân bằng đầu phiên tới: " + (
            "bán phần ETF VN-Index, dồn vốn cho A0 & B (an toàn)" if ra["cl"] == 1 else
            "giảm B, mua ETF VN-Index 30%, tăng A0 (lãi)"),
        "(Tham khảo – tự kiểm tra trước khi đặt lệnh)"])


def _r(x):
    return "–" if x is None or x != x else f"{x:+.1f}R".replace(".", ",")


def _dong_nhom(nhom, r):
    """2 dòng / mã: vùng mua + cắt lỗ, rồi điều kiện vô hiệu."""
    tp = f" [{r['Thành phần']}]" if r["Thành phần"] != "A0" else ""
    g, cl, rr = r["Giá đóng cửa"], r["Cắt lỗ"], r["Rủi ro %"]
    tu, den = r.get("Vùng mua từ", np.nan), r.get("Vùng mua đến", np.nan)
    if tu != tu:                                           # ptcp cũ: chỉ có Mua tối đa / Chờ giá
        tu, den = (np.nan, r.get("Mua tối đa")) if nhom != "CHO" else (np.nan, r.get("Chờ giá"))
    vung = f"{_f(tu)}–{_f(den)}" if tu == tu else f"≤ {_f(den)}"
    lai = f" · HT {_r(r['Lãi HT (R)'])}" if nhom != "MUA_MOI" else ""
    if nhom in ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA"):
        return [f"  • {r['Mã']}{tp} {_f(g)} → MUA {vung} | CL {_f(cl)} (−{_f(rr, 1)}%){lai}",
                f"     ✘ bỏ nếu mở cửa > {_f(den)} hoặc giá rơi < {_f(tu)} trước khi mua" if tu == tu else
                f"     ✘ bỏ nếu mở cửa > {_f(den)}"]
    if nhom == "CHO":
        return [f"  • {r['Mã']}{tp} {_f(g)} → chờ về {vung} | CL {_f(cl)}{lai}",
                f"     ✘ bỏ nếu đóng cửa < {_f(cl)}"]
    return [f"  • {r['Mã']}{tp} {_f(g)}{lai}"]


def ban_tin(ra, bay_gio):
    """Tin chữ bản tin chiến lược (công khai): thị trường → CL đang áp dụng → hành động phiên tới theo nhóm."""
    d, w, n_max = ra["doc"], ra["ty_trong"], C.SO_MA_TRONG_TIN
    n = d["so_chi_bao"]
    phan = " · ".join(f"{ten} {w[k] * 100:.0f}%" for k, ten in (("A0", "A0"), ("B", "B"), ("VNI", "VN-Index (ETF)"))
                      if w.get(k, 0) > 0)
    dong = [f"📈 CHIẾN LƯỢC THEO THỊ TRƯỜNG – {pd.Timestamp(bay_gio):%d/%m/%Y}",
            f"Dữ liệu phiên {d['ngay']:%d/%m} · VN-Index {_f(ra['vni'])}", "",
            f"① Thị trường: {d['diem']}/{n} điểm {'█' * d['diem']}{'░' * (n - d['diem'])}"]
    for _, r in d["bang"].iterrows():
        dong.append(f"  {'✔' if r['Đạt'] else '✘'} {r['Chỉ báo']}" + (f" – {r['Chi tiết']}" if r["Chi tiết"] else ""))
    dong += ["", f"② Đang áp dụng: {ra['ten_cl'][ra['cl']]}", f"Chia vốn: {phan}",
             f"Điều kiện đổi: {d['dieu_kien_doi']}", ""]
    hd = ra.get("hanh_dong")
    if hd is None:                                         # ptcp cũ: dùng danh sách thô
        return _ban_tin_tho(ra, bay_gio, dong)
    from ptcp.chien_luoc import NHOM_HANH_DONG
    hl = (pd.Timestamp(d["ngay"]) + pd.offsets.BDay(1)) if d.get("ngay") is not None else None
    dong.append(f"③ Hành động phiên {hl:%d/%m} (cho người CHƯA mua):" if hl is not None else
                "③ Hành động phiên tới (cho người CHƯA mua):")
    if not len(hd):
        dong.append("  Không có mã nào để mua / theo dõi.")
    for nhom, (bieu, mo_ta) in NHOM_HANH_DONG.items():
        x = hd[hd["Nhóm"] == nhom] if len(hd) else hd
        if not len(x):
            continue
        dong.append(f"{bieu} {mo_ta.split(' – ')[0]} ({len(x)}) – {mo_ta.split(' – ', 1)[1]}"
                    if " – " in mo_ta else f"{bieu} {mo_ta} ({len(x)})")
        if nhom in ("MUA_MOI", "VAO_NHU_MOI", "VAO_NUA") and hl is not None:
            dong.append(f"  (chỉ áp dụng phiên {hl:%d/%m} – sau đó xem bản tin mới)")
        for _, r in x.head(n_max).iterrows():
            dong += _dong_nhom(nhom, r)
        if len(x) > n_max:
            dong.append(f"  … và {len(x) - n_max} mã khác")
    dong += ["", "Khối lượng = 1% vốn ÷ (giá mua − cắt lỗ); nhóm 🟡 mua ½. Đặt lệnh trong vùng MUA, ngoài vùng thì bỏ.",
             "Đã mua → ghi gia_von, cat_lo_goc (= CL), ngay_mua vào danh mục để bot báo dời cắt lỗ / bán."]
    for k in ("A0", "B"):
        b = ra["diem_mua"].get(k)
        if w.get(k, 0) <= 0 and b is not None and len(b):
            mua = b[b["Trạng thái"].astype(str).str.startswith("MUA")]["Mã"].tolist()
            if mua:
                dong.append(f"({k} có tỷ trọng 0% ở CL hiện tại – tín hiệu {k} chỉ tham khảo: {', '.join(mua)})")
    if ra["thieu"]:
        dong.append(f"Thiếu dữ liệu: {', '.join(ra['thieu'][:10])}")
    dong.append(f"(HT = hệ thống mô phỏng trên {ra['so_ma']} mã, không phải danh mục thật. Tham khảo.)")
    return "\n".join(dong)


def _ban_tin_tho(ra, bay_gio, dong):
    """Dự phòng khi ptcp chưa có hanh_dong(): mua / bán / đang giữ của hệ thống."""
    n_max = C.SO_MA_TRONG_TIN
    mua, giu, ban = [], [], []
    for tp, b in ra["diem_mua"].items():
        if not ra["ty_trong"].get(tp) or b is None or not len(b):
            continue
        for _, r in b.iterrows():
            tt = str(r["Trạng thái"])
            if tt.startswith("MUA"):
                mua.append(f"  • {r['Mã']} {_f(r['Giá đóng cửa'])} [{tp}] | CL {_f(r.get('Cắt lỗ dự kiến'))}")
            elif "BÁN phiên tới" in tt:
                ban.append(f"  • {r['Mã']} {_f(r['Giá đóng cửa'])} [{tp}]")
            elif tt.startswith("ĐANG GIỮ"):
                giu.append(f"  • {r['Mã']} {_f(r['Giá đóng cửa'])} [{tp}] tầng {int(r.get('Tầng', 0))} | "
                           f"CL {_f(r.get('Cắt lỗ phiên tới'))}")
    for tieu_de, ds in (("🟢 MUA PHIÊN TỚI:", mua), ("🔻 BÁN PHIÊN TỚI:", ban), ("💼 HỆ THỐNG ĐANG GIỮ:", giu)):
        if ds:
            dong += [tieu_de] + sorted(ds)[:n_max]
    dong.append(f"(Mô phỏng hệ thống trên {ra['so_ma']} mã – KHÔNG phải danh mục thật. Tham khảo.)")
    return "\n".join(dong)
