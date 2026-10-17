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

import numpy as np
import pandas as pd

from . import cau_hinh as C


def ro_do_rong():
    """Rổ tính độ rộng / điểm thị trường: top 100 GTGD chốt thứ Sáu tuần liền trước (ptcp.loc_quy_b.ro_thi_truong);
    ptcp cũ / thiếu dữ liệu → MA_CHIEN_LUOC (41 mã)."""
    try:
        from ptcp.loc_quy_b import ro_thi_truong
        ro, mo_ta = ro_thi_truong()
    except (ImportError, AttributeError):
        ro, mo_ta = list(C.MA_CHIEN_LUOC), f"{len(C.MA_CHIEN_LUOC)} mã cố định"
    print(f"Độ rộng thị trường: rổ {mo_ta}")
    return ro

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
        # chờ bán = đóng cửa tuần < MA10 tuần HOẶC đã thủng cắt lỗ / hết hạn chưa bán được – khớp ptcp & backtest
        ly = ("đóng cửa tuần < MA10 tuần" if vt.get("Bán phiên tới (MA10 tuần)") else
              (vt.get("Lý do chờ bán") or "chạm cắt lỗ") if vt.get("Đang chờ bán") else "")
        r.update({"Trạng thái": "ĐANG GIỮ" + (f" → BÁN phiên tới ({ly})" if ly else ""),
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


def chay_chien_luoc(tai, bay_gio, du_lieu_san=None, vni=None, ds_ma=None, ds_do_rong=None):
    """
    tai(ma, tu_ngay, chi_so=False) → giá ngày. du_lieu_san: {mã: giá ngày} đã tải (dùng lại nếu đủ dài).
    ds_do_rong: mã CHỈ dùng tính độ rộng thị trường (điểm 8 chỉ báo) – không lên danh sách mua.
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
    chi_do_rong = [m for m in dict.fromkeys(x.strip().upper() for x in (ds_do_rong or []) if x.strip())
                   if m not in ds_ma]
    gia, diem_mua, thieu, gia_ngay, atr = {}, {k: [] for k in thanh_phan}, [], {}, {}
    from .du_lieu import tai_nhieu
    can = [m for m in ds_ma + chi_do_rong if not _dung_duoc((du_lieu_san or {}).get(m), tu)]
    da_tai = tai_nhieu(lambda m: tai(m, tu), can)                 # tải song song trước (mạng chậm, tính nhanh)
    for ma in ds_ma + chi_do_rong:
        df = (du_lieu_san or {}).get(ma)
        if not _dung_duoc(df, tu):
            df = da_tai.get(ma)
        df = _phien_da_dong(df, bay_gio) if df is not None else None
        if df is None or len(df) < 260:
            if ma in ds_ma:
                thieu.append(ma)
            continue
        df = df[["open", "high", "low", "close", "volume"]]
        if ma in chi_do_rong:                              # chỉ cần giá đóng cửa cho độ rộng
            gia[ma] = df.close
            continue
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
            diem_mua[ten].append({"Mã": ma, **_bang_diem_mua(r["cuoi"], x, 0.5 if bt.nhoi else 1.0),
                                  "GTGD TB20 (tỷ)": float((df.close * df.volume / 1e6).tail(20).mean()),
                                  "RS 3T %": _rs_3t(df.close, vni), "Số lần đỉnh 52T 3T": _dinh_52t(df.close)})
    if len(gia) < 5:
        return None, f"quá ít mã có dữ liệu ({len(gia)}/{len(ds_ma)})"
    F, diem, muc = bang_chi_bao(vni, pd.DataFrame(gia))
    nhiet = None
    try:                                                   # QUỸ B: nhiệt thị trường → hệ số khối lượng lệnh mới
        from ptcp.chien_luoc import doc_nhiet
        nhiet = doc_nhiet(vni, pd.DataFrame(gia))
    except Exception:                                      # noqa: BLE001 – ptcp cũ / thiếu dữ liệu → hệ số 1
        pass
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
            "so_ma": len(gia), "thieu": thieu, "gia_ngay": gia_ngay, "di_ngang": ngang, "atr": atr, "vni_df": vni, "nhiet": nhiet,
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


def _rs_3t(c, vni):
    """Sức mạnh giá 3 tháng so VN-Index (điểm %) – 1 trong 3 yếu tố điểm ưu tiên (RS quá nóng → ưu tiên sau)."""
    try:
        v = vni.close.reindex(c.index).ffill()
        return float((c.iloc[-1] / c.iloc[-64] - v.iloc[-1] / v.iloc[-64]) * 100) if len(c) > 64 else np.nan
    except Exception:                                           # noqa: BLE001
        return np.nan


def _dinh_52t(c):
    """Số phiên lập đỉnh 52T trong 3 tháng (điểm ★ – ptcp.chien_luoc.diem_uu_tien); ptcp cũ → NaN."""
    try:
        from ptcp.chien_luoc import so_lan_dinh_52t
    except ImportError:
        return np.nan
    return so_lan_dinh_52t(c)


def _ty_trong(w):
    return f"A0 {w['A0'] * 100:.0f}% · B {w['B'] * 100:.0f}% · tiền nhàn rỗi {w.get('TIEN', 0) * 100:.0f}%"


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
            "giảm A0, thêm B, giữ tiền nhàn rỗi theo tỷ trọng mới (an toàn)" if ra["cl"] == 1 else
            "giảm / ngừng B, tăng A0 (lãi), phần còn lại để tiền nhàn rỗi"),
        "(Tham khảo – tự kiểm tra trước khi đặt lệnh)"])


