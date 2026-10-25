# -*- coding: utf-8 -*-
"""
BACKTEST cho bot (python chay.py --che_do backtest – chạy tay trên Actions, ~10–20 phút lần đầu):
  1. ĐIỂM BÁN & MUA THÊM: chốt ⅓ / ½ ở 3R, siết cắt lỗ khi thị trường giảm, hạn ngắn hơn, mua thêm kiểu B / khi có
     tín hiệu mới – so với hệ thoát gốc, 2 giai đoạn 2019–22 & 2023–26 (giá ngày).
  2. ĐIỂM VÀO 15 PHÚT: mọi khuyến nghị mua quá khứ của chiến lược (41 mã / toàn sàn HOSE + HNX, cùng
     cách phân nhóm như tin hằng ngày; bảng tách theo sàn)
     × các cách vào (ATO / 15P / 15P+ATC / 15P+GIO / VWAP / LO …) trên nến 15' thật → lãi/lỗ theo hệ thoát.
     Cách vào được chọn (khớp ≥ 50%, lãi TB / lệnh cao nhất) dùng cho cảnh báo trong phiên (CACH_VAO_15P = "tu_dong").
Kết quả (chỉ thống kê, không có danh mục) → ket_qua_backtest.json (commit) + file Excel gửi Telegram.
"""
import json

import numpy as np
import pandas as pd

from . import cau_hinh as C


def _ban_ghi(df):
    if df is None or not len(df):
        return []
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return json.loads(df.replace({np.nan: None}).to_json(orient="records", force_ascii=False))


def _ket_luan_15p(b, tot):
    from ptcp.diem_vao_15p import BIEN_THE
    if not tot:
        return "chưa đủ tín hiệu"
    bb = b.set_index("Biến thể")
    r = bb.loc[tot]
    kl = (f"Chọn {tot} ({BIEN_THE.get(tot, '')}): lãi TB {r['TB/lệnh khớp %']:+.2f}%/lệnh, khớp {r['Khớp %']:.0f}%")
    if "ATO" in bb.index and tot != "ATO":
        kl += f" – mua ATO: {bb.loc['ATO', 'TB/lệnh khớp %']:+.2f}%/lệnh"
    return kl


def ro_rong():
    """Rổ dự phòng cho backtest cách vào (ptcp cũ chưa có danh sách sàn): ptcp.loc_quy_b.ro_ma + mã đã xếp hạng GTGD
    + 41 mã chiến lược."""
    from ptcp import loc_quy_b
    loc = loc_quy_b.doc(han_ngay=None) or {}
    return list(dict.fromkeys(loc_quy_b.ro_ma() + list(loc.get("hang_gtgd", {})) + C.MA_CHIEN_LUOC))


def ro_hose_hnx():
    """Rổ HOSE + HNX (toàn sàn, ptcp/san_niem_yet.json) + mã đã huỷ niêm yết – rổ mặc định của backtest (10/2026).
    ptcp cũ chưa có danh sách sàn → ro_rong."""
    try:
        from ptcp.nganh import HUY_NIEM_YET
        from ptcp.san import doc_san
    except ImportError:
        return ro_rong()
    d = doc_san()
    return list(dict.fromkeys(d["HOSE"] + d["HNX"] + list(HUY_NIEM_YET))) or ro_rong()


def _bang_san(ct):
    """Bảng cách vào tách theo sàn (HOSE / HNX / khác – UPCoM, đã huỷ niêm yết) – để so, không dùng chọn."""
    try:
        from ptcp.san import doc_san, san_cua
    except ImportError:
        return None
    from ptcp.diem_vao_15p import tong_hop_15p
    if not len(ct):
        return None
    d = doc_san()
    san = ct["Mã"].map(lambda m: san_cua(m, d) or "khác")
    out = {}
    for ten in ("HOSE", "HNX", "khác"):
        g = ct[san == ten]
        if len(g):
            k = tong_hop_15p(g, list(dict.fromkeys(g["Biến thể"])))
            out[ten] = {"bang": _ban_ghi(k["bang"]), "tot_nhat": k["tot_nhat"], "so_tin_hieu": k["so_tin_hieu"],
                        "so_ma": int(g["Mã"].nunique()), "ket_luan": _ket_luan_15p(k["bang"], k["tot_nhat"])}
    return out or None


def _tai_song_song(ham, ds_ma, luong=8):
    from concurrent.futures import ThreadPoolExecutor

    def mot(ma):
        try:
            return ma, ham(ma)
        except Exception:                                           # noqa: BLE001 – thiếu 1 mã không dừng backtest
            return ma, None
    out = {}
    with ThreadPoolExecutor(max_workers=luong) as ex:
        for i, (m, d) in enumerate(ex.map(mot, ds_ma), 1):
            if d is not None and len(d):
                out[m] = d
            if i % 25 == 0 or i == len(ds_ma):
                print(f"  đã tải {i}/{len(ds_ma)} mã ({len(out)} có dữ liệu)", flush=True)
    return out


def _bang_top(ct, top):
    """Bảng cách vào chỉ trên khuyến nghị của mã top GTGD hiện tại (Quỹ Bứt Phá chỉ mua top) – để so, không dùng chọn."""
    from ptcp import loc_quy_b
    from ptcp.diem_vao_15p import tong_hop_15p
    hang = (loc_quy_b.doc(han_ngay=None) or {}).get("hang_gtgd", {})
    ma_top = {m for m, h in hang.items() if h <= top}
    if not ma_top or not len(ct):
        return None
    k = tong_hop_15p(ct[ct["Mã"].isin(ma_top)])
    return {"bang": _ban_ghi(k["bang"]), "tot_nhat": k["tot_nhat"], "so_tin_hieu": k["so_tin_hieu"],
            "ket_luan": _ket_luan_15p(k["bang"], k["tot_nhat"])}


def _dinh_gia(ct, gia):
    """Định giá J8 theo quý (kho BCTC du_lieu/bctc của danh-muc) cho các mã có tín hiệu → mã ĐẮT × ½ KL như live.
    Thiếu kho / lỗi → None (backtest chạy không có ĐẮT, ghi rõ trong log)."""
    try:
        from ptcp import kiem_dinh_dinh_gia as kd
        ma = sorted(set(ct["Mã"]) & set(gia))
        dg = kd.chay(ma, gia_san={m: gia[m]["close"] for m in ma})
        dg = dg[dg.bien_the == "hiện tại"] if "bien_the" in dg else dg
        print(f"  Định giá J8: {dg['ma'].nunique()}/{len(ma)} mã có số liệu → áp ĐẮT ½ khối lượng")
        return dg
    except Exception as e:                                          # noqa: BLE001 – không có định giá vẫn backtest
        print(f"  ⚠ Không có định giá ({type(e).__name__}: {str(e)[:120]}) → backtest 15' không áp ĐẮT ½")
        return None


def tai_nen_15p(ds_ma=None):
    """Chỉ tải phần nến 15' mới cho rổ backtest (workflow hằng tuần): giữ cache không bị GitHub xoá (7 ngày không
    dùng) và tích luỹ lịch sử dài hơn giới hạn ~1 năm của nguồn. Trả số mã có dữ liệu."""
    from . import du_lieu
    ds_ma = ds_ma or ro_hose_hnx()
    n15 = _tai_song_song(lambda m: du_lieu.tai_lich_su_phut(m, C.BACKTEST_15P_TU), ds_ma)
    if n15:
        tu = min(d.index[0] for d in n15.values())
        print(f"Nến 15': {len(n15)}/{len(ds_ma)} mã · từ {tu:%d/%m/%Y} · "
              f"{sum(len(d) for d in n15.values()):,} nến")
    return len(n15)


def chay_backtest(bay_gio, khong_gui=False, ds_ma=None, chi_diem_vao=False, file_ra=None):
    """chi_diem_vao: chỉ backtest cách vào 15' (rổ lớn) – giữ phần điểm bán / bộ lọc mua của lần chạy trước.
    file_ra: ghi kết quả ra file khác C.FILE_BACKTEST (rổ so sánh – KHÔNG đổi cách vào 15' bot đang dùng)."""
    from ptcp.backtest_diem_ban import backtest_diem_ban
    from ptcp.diem_vao_15p import backtest_15p, tin_hieu_qua_khu
    from . import du_lieu
    from .thong_bao import gui, gui_file
    ds_ma = ds_ma or C.MA_CHIEN_LUOC
    print(f"=== BACKTEST | {pd.Timestamp(bay_gio):%Y-%m-%d %H:%M} | {len(ds_ma)} mã ===", flush=True)
    vni = du_lieu.tai("VNINDEX", "D", C.BACKTEST_TU, chi_so=True)
    gia = {m: d for m, d in _tai_song_song(lambda m: du_lieu.tai(m, "D", C.BACKTEST_TU), ds_ma).items()
           if len(d) >= 260}
    print(f"  giá ngày: {len(gia)}/{len(ds_ma)} mã", flush=True)
    if vni is None or len(gia) < 5:
        print("Thiếu dữ liệu ngày → dừng backtest.")
        return 1
    cu = doc_cu() if chi_diem_vao else {}
    ra = {**cu, "ngay_chay": f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}", "so_ma": len(gia)}
    if chi_diem_vao and not cu.get("diem_ban"):
        chi_diem_vao = False                                        # chưa có kết quả cũ → chạy đủ
    if chi_diem_vao:
        print("\n(bỏ qua ① điểm bán & ①b bộ lọc mua – giữ kết quả lần trước)")
    else:
        _diem_ban_loc_mua(ra, gia, vni, backtest_diem_ban)
    _diem_vao(ra, gia, vni, du_lieu, backtest_15p, tin_hieu_qua_khu)
    return _luu_gui(ra, bay_gio, khong_gui, gui, gui_file, file_ra or C.FILE_BACKTEST)


def doc_cu():
    try:
        with open(C.FILE_BACKTEST, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _diem_ban_loc_mua(ra, gia, vni, backtest_diem_ban):
    print("\n① Điểm bán & mua thêm (giá ngày)…")
    kb = backtest_diem_ban(gia, vni, start=C.BACKTEST_TU)
    ra["diem_ban"] = {"bang": _ban_ghi(kb["bang"]), "ket_luan": kb["ket_luan"],
                      "mo_ta": f"{len(gia)} mã, {C.BACKTEST_TU[:4]}–nay, tín hiệu A0, so với hệ thoát gốc"}
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(kb["bang"].round(2).to_string(index=False))
    print(kb["ket_luan"])

    print("\n①b Bộ lọc mua theo thị trường (giá ngày)…")
    try:                                                    # ptcp cũ chưa có module → bỏ qua, không làm hỏng backtest
        from ptcp.backtest_loc_mua import backtest_loc_mua
        kl_ = backtest_loc_mua(gia, vni, start=C.BACKTEST_TU)
        ra["loc_mua"] = {"bang": _ban_ghi(kl_["bang"]), "ket_luan": kl_["ket_luan"], "tot": kl_["tot"],
                         "mo_ta": f"{len(gia)} mã, {C.BACKTEST_TU[:4]}–nay, tín hiệu A0, hệ thoát gốc"}
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print(kl_["bang"].round(2).to_string(index=False))
        print(kl_["ket_luan"])
    except ImportError:
        print("ptcp chưa có backtest_loc_mua – bỏ qua")


def _diem_vao(ra, gia, vni, du_lieu, backtest_15p, tin_hieu_qua_khu):
    print(f"\n② Điểm vào 15 phút – tải nến 15' từ {C.BACKTEST_15P_TU}…", flush=True)
    n15 = _tai_song_song(lambda m: du_lieu.tai_lich_su_phut(m, C.BACKTEST_15P_TU), list(gia))
    if not n15:
        ra["15p"] = {"bang": [], "theo_nhom": [], "tot_nhat": None,
                     "ket_luan": "không tải được nến 15' – chưa backtest được"}
        print("Không tải được nến 15' nào.")
    else:
        tu = min(d.index[0] for d in n15.values()).normalize()
        den = max(d.index[-1] for d in n15.values())
        print(f"  nến 15': {len(n15)} mã, {tu:%d/%m/%Y} → {den:%d/%m/%Y}")
        try:                                                        # ptcp mới: song song + lưu kết quả từng mã
            from ptcp.diem_vao_15p import backtest_15p_song_song
            k15 = backtest_15p_song_song(gia, vni, n15, tu - pd.Timedelta(days=3))
        except ImportError:
            ds, xs = tin_hieu_qua_khu(gia, vni, tu - pd.Timedelta(days=3))
            k15 = backtest_15p(ds, n15, xs)
        b = k15["bang"]
        kl = _ket_luan_15p(b, k15["tot_nhat"])
        ra["15p"] = {"bang": _ban_ghi(b), "theo_nhom": _ban_ghi(k15["theo_nhom"]), "tot_nhat": k15["tot_nhat"],
                     "ket_luan": kl, "so_tin_hieu": k15["so_tin_hieu"],
                     "mo_ta": f"{len(n15)} mã, nến 15' {tu:%d/%m/%Y}–{den:%d/%m/%Y}, {k15['so_tin_hieu']} khuyến nghị mua"}
        if len(b):
            with pd.option_context("display.width", 250, "display.max_columns", 30):
                print(b.drop(columns=["Mô tả"]).round(2).to_string(index=False))
        print(kl)
        try:
            from ptcp import cau_hinh as pc
            top = getattr(pc, "QUY_TOP_GTGD", 0) or 100
            bt = _bang_top(k15["chi_tiet"], top)
        except ImportError:                                         # ptcp cũ chưa có loc_quy_b
            bt = None
        if bt:
            ra["15p"]["top_gtgd"] = {**bt, "top": top}
            print(f"  Riêng top {top} GTGD ({bt['so_tin_hieu']} khuyến nghị): {bt['ket_luan']}")
        ts = _bang_san(k15["chi_tiet"])
        if ts:
            ra["15p"]["theo_san"] = ts
            for ten, v in ts.items():
                print(f"  Sàn {ten} ({v['so_ma']} mã, {v['so_tin_hieu']} khuyến nghị): {v['ket_luan']}")
        try:                                                        # ptcp mới: mô phỏng cả quỹ Bứt Phá theo từng cách vào
            from ptcp.diem_vao_15p import quy_b_theo_cach_vao
            q = quy_b_theo_cach_vao(k15["chi_tiet"], gia, vni, dg=_dinh_gia(k15["chi_tiet"], gia))
        except ImportError:
            q = None
        if q is not None and len(q):
            q = q.sort_values("Calmar", ascending=False)
            t = q.iloc[0]
            ra["15p"]["quy_b"] = {"bang": _ban_ghi(q), "ket_luan":
                                  f"quỹ Bứt Phá tốt nhất {t['Biến thể']}: lãi kỳ {t['Lãi kỳ %']:+.1f}%, MDD {t['MDD %']:.1f}%, "
                                  f"{int(t['Lệnh vào'])} lệnh"}
            print("\n  Quỹ Bứt Phá (luật vốn thật, top GTGD) theo cách vào:")
            with pd.option_context("display.width", 250, "display.max_columns", 30):
                print(q.round(2).to_string(index=False))


def _luu_gui(ra, bay_gio, khong_gui, gui, gui_file, file_ra=None):
    file_ra = file_ra or C.FILE_BACKTEST
    with open(file_ra, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=1)
    print(f"Đã lưu {file_ra}")
    tin = "\n".join([f"🧪 BACKTEST CHIẾN LƯỢC – {pd.Timestamp(bay_gio):%d/%m/%Y}",
                     f"Điểm vào 15' ({ra['15p'].get('mo_ta', '')}): {ra['15p']['ket_luan']}",
                     *([f"  riêng top {ra['15p']['top_gtgd']['top']} GTGD: {ra['15p']['top_gtgd']['ket_luan']}"]
                       if ra["15p"].get("top_gtgd") else []),
                     *([f"  {ra['15p']['quy_b']['ket_luan']}"] if ra["15p"].get("quy_b") else []),
                     f"Điểm bán & mua thêm: {ra['diem_ban']['ket_luan']}",
                     *([f"Bộ lọc mua: {ra['loc_mua']['ket_luan']}"] if ra.get("loc_mua") else []),
                     "(Chi tiết: file Excel – các sheet BT 15 phut, BT diem ban, BT loc mua)"])
    if khong_gui:
        print(tin)
        return 0
    gui(tin)
    path = "backtest_chien_luoc.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        pd.DataFrame(ra["diem_ban"]["bang"]).to_excel(w, sheet_name="BT diem ban", index=False)
        if ra.get("loc_mua"):
            pd.DataFrame(ra["loc_mua"]["bang"]).to_excel(w, sheet_name="BT loc mua", index=False)
        if ra["15p"].get("bang"):
            pd.DataFrame(ra["15p"]["bang"]).to_excel(w, sheet_name="BT 15 phut", index=False)
            pd.DataFrame(ra["15p"]["theo_nhom"]).to_excel(w, sheet_name="BT 15 phut theo nhom", index=False)
            if ra["15p"].get("quy_b"):
                pd.DataFrame(ra["15p"]["quy_b"]["bang"]).to_excel(w, sheet_name="BT 15 phut quy But Pha", index=False)
            if ra["15p"].get("top_gtgd"):
                pd.DataFrame(ra["15p"]["top_gtgd"]["bang"]).to_excel(w, sheet_name="BT 15 phut top GTGD", index=False)
            for ten, v in (ra["15p"].get("theo_san") or {}).items():
                pd.DataFrame(v["bang"]).to_excel(w, sheet_name=f"BT 15 phut san {ten}", index=False)
    try:
        from ptcp.excel_xanh import trang_tri_excel
        trang_tri_excel(path)
    except Exception:
        pass
    gui_file(path, "Backtest điểm vào 15' & điểm bán")
    return 0
