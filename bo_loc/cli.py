# -*- coding: utf-8 -*-
"""
CHƯƠNG TRÌNH CHÍNH – ghép các bước: danh sách mã → tải giá → lọc sơ bộ → cơ bản → chỉ tiêu → lọc → đánh giá → xuất.
Gọi từ code khác (VD bot cảnh báo):  from bo_loc.cli import chay;  kq = chay(["--ma", "GMD,DHC"])
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import cau_hinh as ch
from . import chien_luoc as cl_mod
from . import danh_sach_ma as dsm
from . import xuat
from .danh_gia_sau_loc import danh_gia_sau_loc
from .ket_luan import in_ket_luan, lap_ket_luan
from . import bon_bang
from .lich_su import ghi_lich_su
from .loc import bang_ket_qua, danh_gia, gan_dat
from .nguon import bctc_nam as nguon_bctc
from .nguon import co_ban as nguon_cb
from . import danh_gia_tai_chinh as fa
from .nguon import gia as nguon_gia
from .nguon.http import CAU_DAO_CO_BAN, CAU_DAO_GIA, NHAT_KY
from .phan_tich.chi_so import tinh_chi_so
from .tieu_chi import KHOA_CO_BAN, ten_tieu_chi


def doc_tham_so(argv=None):
    ds_cl = list(cl_mod.tai_tat_ca())
    p = argparse.ArgumentParser(description="Bộ lọc cổ phiếu")
    p.add_argument("--chien_luoc", default=getattr(ch, "CHIEN_LUOC_MAC_DINH", "quy_b"), help="Chiến lược: " + ", ".join(ds_cl))
    p.add_argument("--them", default=None,
                   help="Thêm/đổi tiêu chí BẮT BUỘC lúc chạy, VD beta_min=1.2,rsi_trong=25:45")
    p.add_argument("--bo", default=None, help="Bỏ tiêu chí khỏi chiến lược, VD tren_ma200,pe_max")
    p.add_argument("--nghiem_ngat", action="store_true", default=ch.NGHIEM_NGAT,
                   help="Thiếu dữ liệu = không đạt (mặc định: bỏ qua & đánh dấu ◐)")
    p.add_argument("--khong_online_co_ban", action="store_true", help="Không lấy dữ liệu cơ bản online")
    p.add_argument("--khong_vnstock", action="store_true", help="Không dùng thư viện vnstock làm nguồn")
    p.add_argument("--cho_vnstock", action="store_true",
                   help="Hết lượt vnstock thì CHỜ (chạy chậm, đúng hạn mức) thay vì chuyển nguồn khác")
    p.add_argument("--luon_lay_co_ban", action="store_true",
                   help="Lấy dữ liệu cơ bản kể cả khi chiến lược không cần (để có P/E, P/B so sánh ngành)")
    p.add_argument("--tao_mau_co_ban", action="store_true", help="Tạo file co_ban_mau.csv rồi thoát")
    p.add_argument("--nhom", default="tat_ca", help="Nhóm mã: hose, " + ", ".join(dsm.NHOM_MA))
    p.add_argument("--khong_cache", action="store_true", help="Không dùng/lưu bộ nhớ đệm (tải lại toàn bộ)")
    p.add_argument("--bo_nen_dang_chay", action="store_true", help="Chỉ dùng nến ngày đã đóng cửa")
    p.add_argument("--ma", default=None, help="Danh sách mã, VD GMD,HAH,VSC")
    p.add_argument("--file_ma", default=None, help="File danh sách mã")
    p.add_argument("--start", default=ch.NGAY_BAT_DAU)
    p.add_argument("--vnindex", default=None, help="File CSV VNINDEX (bỏ trống = online)")
    p.add_argument("--thu_muc_csv", default=None, help="Thư mục file giá <MÃ>.csv (khi không lấy được online)")
    p.add_argument("--co_ban", default=None, help="File CSV/XLSX dữ liệu cơ bản tự nhập (ưu tiên cao nhất)")
    p.add_argument("--nguon_gia", default=None,
                   help="Thứ tự nguồn giá, VD VCI,TCBS,Yahoo. Có: " + ",".join(nguon_gia.NGUON_GIA))
    p.add_argument("--gtgd_min", type=float, default=None, help="Ghi đè ngưỡng GTGD TB20 (tỷ đồng)")
    p.add_argument("--klgd_min", type=float, default=None, help="Ghi đè ngưỡng KLGD TB20 (cổ phiếu)")
    p.add_argument("--von", type=float, default=ch.VON_DANH_MUC, help="Quy mô danh mục (triệu đồng)")
    p.add_argument("--rui_ro", type=float, default=ch.RUI_RO_MOI_LENH, help="%% NAV chấp nhận mất mỗi lệnh")
    p.add_argument("--khong_danh_gia", action="store_true", help="Bỏ bước đánh giá sau lọc")
    p.add_argument("--khong_bieu_do", action="store_true", help="Không vẽ biểu đồ (chạy nhanh hơn)")
    p.add_argument("--thu_muc_ket_qua", default=".", help="Nơi tạo thư mục kết quả")
    p.add_argument("--top", type=int, default=ch.TOP_N)
    if argv is not None:
        return p.parse_args(argv)
    if "ipykernel" in sys.modules and ch.THAM_SO_NOTEBOOK:
        return p.parse_known_args(ch.THAM_SO_NOTEBOOK)[0]
    return p.parse_known_args()[0]


def _cai_tuy_chon():
    """Tự cài yfinance (nguồn cơ bản dự phòng) nếu thiếu – im lặng, lỗi thì bỏ qua."""
    import importlib.util
    import subprocess
    thieu = [g for g in ("yfinance",) if importlib.util.find_spec(g) is None]
    if thieu:
        print(f"  Đang cài thư viện nguồn dữ liệu dự phòng: {', '.join(thieu)} ...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", *thieu], check=False, timeout=240,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            importlib.invalidate_caches()
        except Exception:
            pass


def gio_viet_nam():
    return datetime.now(timezone.utc) + timedelta(hours=7)


def _tai_song_song(ham, ds, ten, moi=25):
    kq = {}
    with ThreadPoolExecutor(max_workers=ch.SO_LUONG_TAI) as ex:
        tl = {ex.submit(ham, m): m for m in ds}
        for i, f in enumerate(as_completed(tl), 1):
            try:
                kq[tl[f]] = f.result()
            except (Exception, SystemExit):           # 1 mã lỗi (kể cả thư viện gọi SystemExit) không dừng cả lần chạy
                kq[tl[f]] = None
            if i % moi == 0 or i == len(ds):
                print(f"  {ten}: {i}/{len(ds)}")
    return kq


class _InSoVN:
    """Bọc sys.stdout: mọi chữ in ra được đổi số sang kiểu Việt Nam (1.234,56) – xem so.py."""

    def __init__(self, goc):
        self.goc = goc

    def write(self, s):
        from .so import vn_hoa
        return self.goc.write(vn_hoa(s))

    def flush(self):
        return self.goc.flush()

    def __getattr__(self, ten):
        return getattr(self.goc, ten)


def chay(argv=None):
    """Chạy bộ lọc. Trong notebook: lỗi đầu vào/dữ liệu chỉ in thông báo ngắn (không in traceback dài)."""
    goc = sys.stdout
    sys.stdout = _InSoVN(goc)
    try:
        if "ipykernel" not in sys.modules:
            return _chay(argv)
        try:
            return _chay(argv)
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"\n❌ {e}")
            return None
    finally:
        sys.stdout = goc


def _chay(argv=None):
    import bo_loc
    print(f"▶ BỘ LỌC CỔ PHIẾU {bo_loc.__version__}  ({os.path.dirname(bo_loc.__file__)})")
    a = doc_tham_so(argv)
    NHAT_KY.xoa()
    CAU_DAO_GIA.xoa()
    CAU_DAO_CO_BAN.xoa()
    if a.nguon_gia:
        ch.THU_TU_NGUON_GIA = [x.strip() for x in a.nguon_gia.split(",") if x.strip()]
    cl = cl_mod.them_bot(cl_mod.lay(a.chien_luoc), a.them, a.bo)
    from .nguon import vnstock_nguon
    vnstock_nguon.CHO_KHI_HET_LUOT = bool(a.cho_vnstock)
    if a.cho_vnstock:
        print(f"  (Chế độ chờ vnstock: tối đa {vnstock_nguon.LUOT_MOI_PHUT} lượt/phút – quét nhiều mã sẽ chậm hơn)")
    if a.khong_vnstock or not ch.DUNG_VNSTOCK:
        ch.THU_TU_NGUON_GIA = [x for x in ch.THU_TU_NGUON_GIA if x != "vnstock"]
        ch.THU_TU_NGUON_CO_BAN = [x for x in ch.THU_TU_NGUON_CO_BAN if x != "vnstock"]
    elif not a.thu_muc_csv:
        vnstock_nguon.dam_bao_cai()            # chỉ tự cài trên Colab; máy cá nhân: tự cài vào môi trường ảo

    # Ngưỡng thanh khoản: dòng lệnh > cấu hình nhóm > chiến lược
    ghi_de = {}
    if not a.ma and not a.file_ma:
        ghi_de.update(dsm.CAU_HINH_NHOM.get(a.nhom, {}))
    if a.gtgd_min is not None:
        ghi_de["gtgd_min"] = a.gtgd_min
    if a.klgd_min is not None:
        ghi_de["klgd_min"] = a.klgd_min
    cl_goc = cl
    cl = cl_mod.ap_nguong(cl, ghi_de)
    if ghi_de:
        print(f"  (Ngưỡng thanh khoản áp dụng: {ghi_de})")
    dong_lenh = a.gtgd_min is not None or a.klgd_min is not None
    cl_cho = lambda ma: cl if dong_lenh else cl_mod.ap_nguong(cl, dsm.NGUONG_RIENG_MA.get(ma))

    ds_ma = dsm.lay_danh_sach_ma(a.ma, a.file_ma, a.nhom)
    if a.tao_mau_co_ban:
        nguon_cb.tao_mau(ds_ma)
        return None

    from .mau import xanh, xanh_nhat
    print(xanh_nhat("=" * 100))
    print(" " + xanh(f"BỘ LỌC CỔ PHIẾU – CHIẾN LƯỢC {cl['ten'].upper()}") + f"  ({a.chien_luoc})")
    print(f" {cl['mo_ta']}")
    print(xanh_nhat("=" * 100))
    print(f"  Số mã: {len(ds_ma)} | Dữ liệu từ {a.start} | Nguồn giá thử lần lượt: {', '.join(ch.THU_TU_NGUON_GIA)}")
    print("  BẮT BUỘC : " + " | ".join(ten_tieu_chi(k, t) for k, t in cl["bat_buoc"].items()))
    print("  CỘNG ĐIỂM: " + " | ".join(ten_tieu_chi(k, t) for k, t in cl["cong_diem"].items()))
    if cl.get("toi_thieu"):
        tt = cl["toi_thieu"]
        print(f"  CƠ BẢN – cần {tt['can_dat']}/{len(tt['tieu_chi'])}: "
              + " | ".join(ten_tieu_chi(k, t) for k, t in tt["tieu_chi"].items()))

    vni = nguon_gia.tai_vnindex(a.start, os.path.abspath(a.vnindex) if a.vnindex else None)
    can_cb = not a.khong_online_co_ban and (a.luon_lay_co_ban or
                                            any(k in KHOA_CO_BAN for _, k, _ in cl_mod.cac_tieu_chi(cl)))
    cb_file = nguon_cb.doc_file(a.co_ban) if a.co_ban else {}

    # --- Giá ---
    print(f"\n  Đang tải giá {len(ds_ma)} mã ...")
    gia = _tai_song_song(lambda m: nguon_gia.tai_gia(m, a.start, a.thu_muc_csv, not a.khong_cache), ds_ma, "Giá")

    # --- Phiên mới nhất / nến đang chạy / mã ngừng giao dịch ---
    loi, loai_som = [], []
    ngay_cuoi = pd.Series({m: df.index[-1] for m, df in gia.items() if df is not None and len(df)})
    if not len(ngay_cuoi):
        raise SystemExit("Không tải được dữ liệu giá nào. Thử --thu_muc_csv, --nguon_gia hoặc kiểm tra kết nối.")
    phien_moi = ngay_cuoi.mode().iloc[0]
    bay_gio = gio_viet_nam()
    nen_dang_chay = phien_moi.date() == bay_gio.date() and bay_gio.weekday() < 5 and bay_gio.hour < ch.GIO_DONG_CUA
    print(f"  Phiên mới nhất: {phien_moi:%d/%m/%Y}" + (" (⚠ nến hôm nay CHƯA đóng cửa)" if nen_dang_chay else ""))
    if nen_dang_chay and a.bo_nen_dang_chay:
        gia = {m: (df[df.index < phien_moi] if df is not None else None) for m, df in gia.items()}
        phien_moi = max(df.index[-1] for df in gia.values() if df is not None and len(df))
        print(f"  → Đã bỏ nến đang chạy, dùng phiên {phien_moi:%d/%m/%Y}")
    for m, df in list(gia.items()):
        if df is not None and len(df) and df.index[-1] < phien_moi - pd.Timedelta(days=7):
            loi.append((m, f"không giao dịch từ {df.index[-1]:%d/%m/%Y} (tạm ngừng/hạn chế?)"))
            gia[m] = None

    # --- Lọc sơ bộ thanh khoản (chỉ khi > 50 mã) ---
    for m, df in (list(gia.items()) if len(ds_ma) > 50 else []):
        if m in dsm.NGUONG_RIENG_MA or df is None or len(df) < ch.SO_PHIEN_TOI_THIEU:
            continue
        bb = cl_cho(m)["bat_buoc"]
        t20 = df.tail(20)
        gt20, kl20 = (t20.volume * t20.close * 1000).mean() / 1e9, t20.volume.mean()
        ly_do = []
        if "gtgd_min" in bb and gt20 < bb["gtgd_min"]:
            ly_do.append(f"GTGD {gt20:.1f} tỷ < {bb['gtgd_min']}")
        if "klgd_min" in bb and kl20 < bb["klgd_min"]:
            ly_do.append(f"KLGD {kl20:,.0f} < {bb['klgd_min']:,}")
        if ly_do:
            loai_som.append((m, "; ".join(ly_do)))
            gia[m] = "loai_som"
    con_lai = [m for m, df in gia.items() if isinstance(df, pd.DataFrame) and len(df) >= ch.SO_PHIEN_TOI_THIEU]
    print(f"  Lọc sơ bộ thanh khoản: loại {len(loai_som)}, còn {len(con_lai)} mã phân tích chi tiết")

    # --- Cơ bản: nhiều nguồn online + file người dùng ---
    cb_online, bctc = {}, {}
    if can_cb and con_lai:
        _cai_tuy_chon()
        print(f"  Đang lấy dữ liệu cơ bản ({', '.join(ch.THU_TU_NGUON_CO_BAN)}) ...")
        cb_online = _tai_song_song(lambda m: nguon_cb.lay_online(m, not a.khong_cache), con_lai, "Cơ bản")
        so_ok = sum(1 for v in cb_online.values() if v)
        print(f"  → Có dữ liệu cơ bản online cho {so_ok}/{len(cb_online)} mã")
        bctc = _tai_song_song(lambda m: nguon_bctc.lay_bctc_nam(m, not a.khong_cache), con_lai, "BCTC năm")
        print(f"  → Có BCTC năm (phân tích tài chính 10 tiêu chí) cho {sum(1 for v in bctc.values() if v)}/{len(con_lai)} mã")
        if CAU_DAO_CO_BAN.da_ngat():
            print(f"  (Đã bỏ qua nguồn không phản hồi: {', '.join(CAU_DAO_CO_BAN.da_ngat())})")
        if so_ok == 0:
            print("  ⚠ Không nguồn cơ bản nào chạy được. Thử: !pip install -q yfinance  rồi chạy lại,\n"
                  "    hoặc tự nhập số liệu: --tao_mau_co_ban → điền co_ban.csv → --co_ban co_ban.csv")

    # --- Chỉ tiêu từng mã ---
    ds_m = {}
    da_loi = {m for m, _ in loi}
    for m in ds_ma:
        df = gia.get(m)
        if isinstance(df, str):
            continue
        if df is None or len(df) < ch.SO_PHIEN_TOI_THIEU:
            if m not in da_loi:
                loi.append((m, f"không có/thiếu dữ liệu giá (cần ≥ {ch.SO_PHIEN_TOI_THIEU} phiên)"))
            continue
        cb = nguon_cb.gop(cb_online.get(m) or {}, cb_file.get(m))
        try:
            ds_m[m] = tinh_chi_so(m, df, vni, cb, dsm.nhom_cua_ma(m), nguon_gia.NGUON_DA_DUNG.get(m, ""))
            x = ds_m[m]
            la_tc = x["nhom"] in ("ngan_hang", "chung_khoan") or any(
                t in str(x.get("nganh", "")) for t in ("Ngân hàng", "Bảo hiểm", "Chứng khoán", "tài chính"))
            kq_fa = fa.danh_gia(bctc.get(m), x["gia"], la_tc) if bctc.get(m) else None
            x.update({"fa_diem": kq_fa["diem"] if kq_fa else np.nan,
                      "fa_nguy_hiem": kq_fa["so_nguy_hiem"] if kq_fa else np.nan,
                      "fa_canh_bao": kq_fa["so_canh_bao"] if kq_fa else np.nan,
                      "fa_tom_tat": kq_fa["tom_tat"] if kq_fa else "",
                      "fa_chi_tiet": kq_fa["chi_tiet"] if kq_fa else None,
                      "fa_nguon": f"{kq_fa['nguon']} (BCTC {kq_fa['nam']})" if kq_fa else ""})
        except Exception as e:
            loi.append((m, f"lỗi tính toán: {e}"))
    if not ds_m:
        raise SystemExit("Không có mã nào vượt qua lọc sơ bộ / đủ dữ liệu.")

    # Trung vị P/E theo nhóm ngành (≥ 3 mã có P/E dương) – cho tiêu chí "P/E < trung vị ngành"
    _pe = pd.DataFrame([{"nhom": m.get("nhom") or "", "pe": m.get("pe")} for m in ds_m.values()], index=list(ds_m))
    _pe["pe"] = pd.to_numeric(_pe["pe"], errors="coerce").where(lambda x: x > 0)
    _tv = _pe.groupby("nhom")["pe"].agg(["median", "count"])
    for ma, m in ds_m.items():
        n = m.get("nhom") or ""
        m["pe_tv_nhom"] = _tv.loc[n, "median"] if n and n in _tv.index and _tv.loc[n, "count"] >= 3 else np.nan
    # --- Chiến lược theo thị trường (cùng bot canh-bao-mua / ptcp): điểm thị trường, CL, đi ngang, nhóm từng mã ---
    tt_cl, dong_tt = None, None
    if getattr(ch, "THEO_CHIEN_LUOC_TT", True):
        try:
            from . import chien_luoc_tt as cltt
            tt_cl, kq_cl = cltt.danh_gia({m: gia[m] for m in ds_m if isinstance(gia.get(m), pd.DataFrame)}, vni)
            dong_tt = cltt.dong_thi_truong(tt_cl)
            for m in ds_m:
                ds_m[m]["cl_tt"] = kq_cl.get(m)
                cltt.ap_vao_chi_so(ds_m[m], kq_cl.get(m))      # cắt lỗ / mục tiêu = giá trị chiến lược
            print(f"\n  {dong_tt}")
        except Exception as e:                     # lỗi phần chiến lược không làm hỏng bộ lọc
            print(f"  ⚠ Chiến lược thị trường lỗi ({type(e).__name__}: {str(e)[:120]}) → dùng cách đánh giá cũ")
    ds_dg = [danh_gia(ds_m[m], cl_cho(m), cl, a.nghiem_ngat) for m in ds_m]
    b = bang_ket_qua(list(ds_m.values()), ds_dg)
    dat = b[b["Đạt lọc"].isin(["✔", "◐"])]

    # ===== BƯỚC 1 =====
    xuat.tieu_de(f"BƯỚC 1 – LỌC THEO CHIẾN LƯỢC {cl['ten'].upper()}: mã nào khớp tiêu chí?")
    xuat.in_ket_qua(b, dat, a.top)
    gd = gan_dat(b)
    if len(gd):
        print(f"\n  Gần đạt – chỉ thiếu 1 tiêu chí ({len(gd)} mã):")
        for _, r in gd.head(a.top).iterrows():
            print(f"   {r['Mã']:<4} điểm lọc {r['Điểm %']:.0f}% │ thiếu: {r['Thiếu']}")
    ngay_truoc, vao, ra, giu = ghi_lich_su(phien_moi, a.chien_luoc, dat)
    if ngay_truoc:
        print(f"\n  So với lần lọc trước (phiên {ngay_truoc}): 🆕 mới vào: {', '.join(vao) or '–'} │ "
              f"❌ rời khỏi: {', '.join(ra) or '–'} │ giữ nguyên: {len(giu)} mã")
    if loi:
        print(f"\n  Bỏ qua {len(loi)} mã thiếu dữ liệu: " + ", ".join(m for m, _ in loi[:20])
              + (" ..." if len(loi) > 20 else ""))

    # ===== 4 BẢNG KẾT QUẢ (TỔNG QUAN | TÀI CHÍNH | KỸ THUẬT | BIẾN ĐỘNG) =====
    chon = dat["Mã"].tolist() if len(dat) else b["Mã"].head(a.top).tolist()
    bang4 = bon_bang.lap_4_bang(b.to_dict("records"), chon)
    ghi_chu_4 = (f"{len(dat)} mã đạt" if len(dat)
                 else f"chưa mã nào đạt – liệt kê top {len(chon)} theo điểm lọc")
    xuat.tieu_de(f"KẾT QUẢ CHIẾN LƯỢC {cl['ten'].upper()} – {ghi_chu_4}")
    bon_bang.in_4_bang(bang4, a.top)

    # ===== BƯỚC 2–5 =====
    e = k = None
    if not a.khong_danh_gia:
        e = danh_gia_sau_loc(ds_m, b, a.von, a.rui_ro)
        xuat.tieu_de("BƯỚC 2–5 – ĐÁNH GIÁ TOÀN DIỆN: chấm 5 trụ cột, cờ đỏ, kế hoạch, hành động")
        xuat.in_danh_gia(e, a.top)
        k = lap_ket_luan(e)

    tk_nguon = NHAT_KY.thong_ke()
    canh_bao = b.loc[b.get("canh_bao_du_lieu", pd.Series("", index=b.index)).fillna("") != "", "Mã"].tolist()
    if len(tk_nguon) or canh_bao:
        xuat.tieu_de("DỮ LIỆU", "─")
        if len(tk_nguon):
            print("  Nguồn: " + " │ ".join(f"{n} {r['Thành công']:.0f}/{r['Tổng lần gọi']:.0f}"
                                           for n, r in tk_nguon.iterrows()))
        if canh_bao:
            print(f"  ⚠ Nguồn cơ bản lệch nhau ở: {', '.join(canh_bao)} (sheet 'Canh bao du lieu')")

    # --- Xuất ---
    thu_muc = os.path.abspath(os.path.join(a.thu_muc_ket_qua, f"ket_qua_loc_{a.chien_luoc}_{phien_moi:%Y%m%d}"))
    os.makedirs(thu_muc, exist_ok=True)
    print(f"\n  Đã lưu kết quả → {thu_muc}")
    if not a.khong_bieu_do:
        xuat.ve_tong_quan(b, cl["ten"].upper(), os.path.join(thu_muc, "tong_quan_loc.png"), a.top)
        xuat.ve_bieu_do_nho(ds_m, dat if len(dat) else b, os.path.join(thu_muc, "bieu_do_cac_ma.png"))
        if e is not None:
            xuat.ve_danh_gia(e, os.path.join(thu_muc, "danh_gia_sau_loc.png"), a.top)
    ten_cot = {ten_tieu_chi(k, t) for _, k, t in cl_mod.cac_tieu_chi(cl_goc)}
    tieu_chi_cot = [c for c in b.columns if c in ten_cot or c.startswith("Cơ bản đạt")]
    tham_so = pd.DataFrame({
        "Tham số": ["NAV (triệu đồng)", "Rủi ro/lệnh (% NAV)", "Tỷ trọng tối đa (%)",
                    "Mua tối đa (% KLGD TB20/phiên)", "Cắt lỗ (× ATR14)"] + [f"Trọng số {k}" for k in ch.TRONG_SO],
        "Giá trị": [a.von, a.rui_ro, ch.TY_TRONG_MAX, ch.TY_LE_THANH_KHOAN, ch.SO_ATR_CAT_LO]
        + list(ch.TRONG_SO.values())})
    thay_doi = pd.DataFrame({"Mới lọt lọc": pd.Series(vao, dtype=str), "Rời khỏi": pd.Series(ra, dtype=str),
                             "Vẫn giữ": pd.Series(giu, dtype=str)})
    bang_tc = pd.DataFrame([[n, ten_tieu_chi(k, t)] for n, k, t in cl_mod.cac_tieu_chi(cl)],
                           columns=["Loại", "Tiêu chí"])
    file_xlsx = os.path.join(thu_muc, "ket_qua_loc.xlsx")
    file_cl = os.path.join(thu_muc, f"chien_luoc_{a.chien_luoc}.xlsx")
    anh = [os.path.join(thu_muc, f) for f in ("tong_quan_loc.png", "danh_gia_sau_loc.png", "bieu_do_cac_ma.png")]
    tq = {"Chiến lược": f"{cl['ten']} ({a.chien_luoc})", "Phiên dữ liệu": f"{phien_moi:%d/%m/%Y}",
          **({"Thị trường": dong_tt.replace("Thị trường: ", "")} if dong_tt else {}),
          "Số mã phân tích": len(b), "Số mã đạt lọc": len(dat)}
    if k is not None and len(k):
        from .ket_luan import THU_TU_NHOM
        for n in THU_TU_NHOM:
            ds_n = k[k["Kết luận"] == n]["Mã"].tolist()
            tq[n] = f"{len(ds_n)} mã" + (f": {', '.join(ds_n[:12])}" if ds_n and n != "[LOẠI]" else "")
    bon_bang.xuat_excel(file_cl, bang4, bang_tc, f"Chiến lược {cl['ten']} – {ghi_chu_4}", cl["ten"],
                              anh=anh, tong_quan=tq)
    print(f"  ✔ Excel kết quả chiến lược {cl['ten']}: {file_cl}")
    xuat.xuat_excel(file_xlsx, b, dat, tieu_chi_cot, bang_tc, loi, loai_som, e, tham_so, thay_doi,
                    NHAT_KY.bang(), tk_nguon, k)
    from .html import xuat_html
    file_html = os.path.join(thu_muc, f"chien_luoc_{a.chien_luoc}.html")
    for che_do, f_ in (("noi_bo", file_html), ("ngoai", file_html.replace(".html", "_ngoai.html"))):
        xuat_html(f_, cl["ten"], cl["mo_ta"], f"{phien_moi:%d/%m/%Y}", b, dat, k, bang4, anh, bang_tc,
                  thi_truong=dong_tt, che_do=che_do)
    print(f"  ✔ Trang HTML nội bộ: {file_html}  ·  bản gửi người ngoài: *_ngoai.html")

    # ===== KẾT LUẬN (in cuối cùng để dễ thấy) =====
    if k is not None:
        thieu_cb = not any(pd.notna(m.get("roe")) or pd.notna(m.get("pe")) for m in ds_m.values())
        in_ket_luan(k, a.von, thieu_co_ban=thieu_cb, dong_tt=dong_tt)
    return {"thi_truong": tt_cl, "bang": b, "dat": dat, "danh_gia": e, "ket_luan": k, "bang_ket_qua": bang4, "file_chien_luoc": file_cl, "file_html": file_html, "thu_muc": thu_muc, "file_excel": file_xlsx,
            "chi_so": ds_m, "loi": loi}


def main():
    try:
        _chay()
    except SystemExit as e:
        if e.code not in (0, None):
            print(e)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Lỗi: {e}")
    if "ipykernel" not in sys.modules and sys.stdin and sys.stdin.isatty() and os.name == "nt":
        try:
            input("\nNhấn Enter để thoát...")
        except EOFError:
            pass
