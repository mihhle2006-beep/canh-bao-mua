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
    """Định giá J8 theo quý (kho BCTC du_lieu/bctc của danh-muc) cho các mã có tín hiệu → mã ĐẮT giảm KL như live (hệ số ở ptcp).
    Thiếu kho / lỗi → None (backtest chạy không có ĐẮT, ghi rõ trong log)."""
    try:
        from ptcp import kiem_dinh_dinh_gia as kd
        ma = sorted(set(ct["Mã"]) & set(gia))
        dg = kd.chay(ma, gia_san={m: gia[m]["close"] for m in ma})
        dg = dg[dg.bien_the == "hiện tại"] if "bien_the" in dg else dg
        print(f"  Định giá J8: {dg['ma'].nunique()}/{len(ma)} mã có số liệu → áp ĐẮT giảm khối lượng")
        return dg
    except Exception as e:                                          # noqa: BLE001 – không có định giá vẫn backtest
        print(f"  ⚠ Không có định giá ({type(e).__name__}: {str(e)[:120]}) → backtest 15' không áp ĐẮT")
        return None


def tai_nen_5p(ma, tu=None, cua_so=20, nghi=0.2):
    """Nến 5' dài cho backtest đa khung: nến 1' Vietcap (có từ 11/09/2023) tải lùi từng cửa sổ `cua_so` ngày (mốc 0h UTC
    = 7h giờ VN – không cắt ngang phiên) rồi gộp 5' ngay → cache gọn cache_gia/<MÃ>_5tu1_lich_su.csv (lần sau chỉ tải
    phần mới). Trả DataFrame (nghìn đồng) hoặc None."""
    import os
    import time

    from ptcp.diem_vao_15p import nen_tu_phut

    from . import du_lieu
    tu = pd.Timestamp(tu or C.BACKTEST_15P_TU)
    path = du_lieu._cache(f"{ma}_5tu1_lich_su")
    cu = None
    if os.path.exists(path):
        try:
            cu = pd.read_csv(path, index_col=0, parse_dates=True).astype(float)
        except (OSError, ValueError):
            cu = None
    moc = max(tu, cu.index[-1].normalize() - pd.Timedelta(days=2)) if cu is not None and len(cu) else tu
    den = int(pd.Timestamp.now(tz="UTC").normalize().timestamp()) + 2 * 86400
    phan, rong = [], 0
    while den > int(moc.timestamp()) and rong < 3:
        t_tu = max(den - cua_so * 86400, int(moc.timestamp()) // 86400 * 86400)
        try:
            d1 = du_lieu.chuan_hoa(du_lieu.tu_vci(ma, t_tu, den, "1"))
        except Exception:                                           # noqa: BLE001 – cửa sổ không có dữ liệu
            d1 = None
        if d1 is not None and len(d1):
            phan.append(nen_tu_phut(d1, 5))
            rong = 0
        else:
            rong += 1
        den = t_tu
        time.sleep(nghi)
    if cu is not None:
        phan.append(cu)
    if not phan:
        return None
    out = pd.concat(phan).sort_index()
    out = out[~out.index.duplicated(keep="first")]                  # bản mới tải (đủ nến) trước bản cache
    try:
        out.to_csv(path)
    except OSError:
        pass
    return out[out.index >= tu]


def ro_da_khung():
    """Rổ backtest đa khung: 41 mã chiến lược + rổ top GTGD hiện tại (Quỹ Bứt Phá chỉ mua rổ này) – nến 1' nặng nên
    không chạy toàn sàn."""
    ds = list(C.MA_CHIEN_LUOC)
    try:
        from ptcp import loc_quy_b
        hang = (loc_quy_b.doc(han_ngay=None) or {}).get("hang_gtgd", {})
        ds += sorted((m for m, h in hang.items() if h <= 100), key=lambda m: hang[m])
    except ImportError:
        pass
    return list(dict.fromkeys(ds))


def chay_da_khung(bay_gio, ds_ma=None, file_ra="ket_qua_backtest_da_khung.json"):
    """ĐIỂM VÀO ĐA KHUNG 5' + 15' + 60' (05/11/2026): khuyến nghị quá khứ của chiến lược × cách vào đang dùng (15P+GIO,
    15P+GIO+ATC, ATO) và cách vào nến 5' (ptcp.diem_vao_15p.BIEN_THE_5P), nến 5' / 15' dựng từ CÙNG nến 1' Vietcap →
    lãi/lỗ theo hệ thoát + theo năm + mô phỏng Quỹ Bứt Phá. Chỉ thống kê → file riêng (KHÔNG đổi cách vào bot đang dùng)."""
    from ptcp.diem_vao_15p import backtest_da_khung, quy_b_theo_cach_vao, theo_nam, tin_hieu_qua_khu

    from . import du_lieu
    ds_ma = ds_ma or ro_da_khung()
    print(f"=== BACKTEST ĐA KHUNG 5' + 15' + 60' | {pd.Timestamp(bay_gio):%Y-%m-%d %H:%M} | {len(ds_ma)} mã ===", flush=True)
    vni = du_lieu.tai("VNINDEX", "D", C.BACKTEST_TU, chi_so=True)
    gia = {m: d for m, d in _tai_song_song(lambda m: du_lieu.tai(m, "D", C.BACKTEST_TU), ds_ma).items() if len(d) >= 260}
    print(f"  giá ngày: {len(gia)}/{len(ds_ma)} mã · tải nến 1' Vietcap → 5'…", flush=True)
    n5 = _tai_song_song(tai_nen_5p, list(gia), luong=6)
    if vni is None or not n5:
        print("Thiếu dữ liệu → dừng.")
        return 1
    tu = min(d.index[0] for d in n5.values()).normalize()
    den = max(d.index[-1] for d in n5.values())
    print(f"  nến 5': {len(n5)} mã, {tu:%d/%m/%Y} → {den:%d/%m/%Y}, {sum(len(d) for d in n5.values()):,} nến", flush=True)
    ds, xs = tin_hieu_qua_khu({m: gia[m] for m in n5}, vni, tu - pd.Timedelta(days=3))
    k = backtest_da_khung(ds, n5, xs)
    b, nam = k["bang"], theo_nam(k["chi_tiet"])
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 200):
        print(f"\nĐA KHUNG – {k['so_tin_hieu']} khuyến nghị (lãi sau phí, hệ thoát gốc):")
        print(b.drop(columns=["Mô tả"]).round(2).to_string(index=False))
        print("\nTheo năm (TB / tín hiệu tính cả lệnh không khớp = 0):")
        print(nam.round(2).unstack(0).to_string())
    q = quy_b_theo_cach_vao(k["chi_tiet"], gia, vni, dg=_dinh_gia(k["chi_tiet"], gia))
    if q is not None and len(q):
        with pd.option_context("display.width", 250, "display.max_columns", 30):
            print("\nQuỹ Bứt Phá (luật vốn thật, top GTGD) theo cách vào:")
            print(q.sort_values("Calmar", ascending=False).round(2).to_string(index=False))
    ra = {"ngay_chay": f"{pd.Timestamp(bay_gio):%Y-%m-%d %H:%M}", "so_ma": len(n5),
          "mo_ta": f"{len(n5)} mã, nến 5' {tu:%d/%m/%Y}–{den:%d/%m/%Y}, {k['so_tin_hieu']} khuyến nghị",
          "bang": _ban_ghi(b), "theo_nam": _ban_ghi(nam.reset_index()), "quy_b": _ban_ghi(q)}
    with open(file_ra, "w", encoding="utf-8") as f:
        json.dump(ra, f, ensure_ascii=False, indent=1)
    print(f"Đã lưu {file_ra}")
    return 0


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
            top = int(pc.QUY_TOP_GTGD)                               # ngưỡng ở ptcp/cau_hinh.py (repo kín) – không ghi ra
            bt = _bang_top(k15["chi_tiet"], top)
        except (ImportError, AttributeError):                       # ptcp cũ chưa có loc_quy_b
            bt = None
        if bt:
            ra["15p"]["top_gtgd"] = bt                               # không ghi số mã rổ (file kết quả công khai)
            print(f"  Riêng rổ top GTGD ({bt['so_tin_hieu']} khuyến nghị): {bt['ket_luan']}")
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
                     *([f"  riêng rổ top GTGD: {ra['15p']['top_gtgd']['ket_luan']}"]
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
