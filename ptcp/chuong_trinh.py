# -*- coding: utf-8 -*-
"""Chương trình chính: main(), quet_nhieu_ma(), hỏi tham số."""
# flake8: noqa: F401
import sys
import os
import io
import re
import json
import time
import base64
import shutil
import zipfile
import builtins
import textwrap
import subprocess
import html as _html
from datetime import datetime, date

import requests
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
from numpy.lib.stride_tricks import sliding_window_view as _cua_so_truot
from .ke_hoach import ke_hoach_tu_gia_mua, dong_ke_hoach, bang_ke_hoach
from . import cau_hinh as cfg
from .cau_hinh import (
    BIEN_DO_SAN, DU_LIEU_CTCK, EV_NGUONG, MA_CTCK, NHOM_NGANH, RR_NGUONG,
    RUI_RO_KHUYEN_NGHI, SO_MUC_TIEU,
)
from .in_an import (
    BAO_CAO_TEXT, _CHAY, _print_goc, fmt, in_bang, in_ra, so_vn,
    ve_bang,
)
from .du_lieu import (
    CANH_BAO_DU_LIEU, DIA_CHI_NGUON, NGUON_DA_DUNG, NHAT_KY_NGUON, _tai_ngay, cac_nguon_gio,
    chuan_bi_vnstock, chuan_hoa, doi_chieu_nguon, ghi_nguon, gop_tuan, lay_bctc_nam, lay_chi_so_co_ban,
    lay_thong_tin_dn, tai_nhom_nganh, tai_vnindex, thu_cac_nguon, tu_csv,
)
from . import fiintrade
from .chi_bao import (
    _duong, duong_xu_huong, phan_tich_tin_hieu, tim_dinh_day, tinh_chi_bao,
)
from .thong_ke import (
    kiem_dinh_walk_forward,
)
from .phan_tich import (
    CHU_GIAI_CP, bien_dong_theo_khung, chuoi_tang_giam, co_cau_co_phieu, ctck_gan_nhat, danh_gia_dinh_gia,
    de_xuat_muc_tieu, ket_luan_mua, kich_ban_chinh, kiem_tra_du_lieu, phan_loai_phien, phan_tich_kich_ban,
    quan_tri_rui_ro, quyet_dinh_cuoi, thong_tin_giao_dich, tinh_cat_lo, tinh_muc_tieu, trang_thai_tuong_tu,
    vung_hoi_tu,
)
from .bo_sung import (
    backtest_quy_tac, boi_canh_thi_truong, danh_gia_thi_truong, lich_cong_bo_kqkd, phan_tich_khoi_luong,
)
from .bieu_do import (
    ve_bieu_do_tang_giam, ve_boi_canh, ve_khoi_luong, ve_khung, ve_kich_ban, ve_quan_tri_rui_ro,
)
from .bao_cao import (
    in_backtest, in_bao_cao_ctck, in_boi_canh, in_co_ban, in_dinh_day, in_khoi_luong,
    in_kich_ban_chinh, in_muc_tieu, in_nguon_du_lieu, in_phan_E, in_thong_tin_giao_dich, in_tin_hieu,
    in_tom_tat, in_walk_forward, lap_tom_tat, xuat_csv, xuat_html,
)


# ==========================================================================
# 11. CHƯƠNG TRÌNH CHÍNH
# ==========================================================================


_THAM_SO = {}


KHOA_THAM_SO = {
    "symbol": "Mã cổ phiếu", "start": "ngày bắt đầu dữ liệu YYYY-MM-DD", "san": "HOSE/HNX/UPCOM",
    "csv_ngay": "file CSV ngày", "csv_gio": "file CSV giờ", "csv_vni": "file CSV VNINDEX",
    "so_cp": "số CP đang giữ", "gia_von": "giá vốn", "mt_nhap": "giá mục tiêu tự định giá",
    "ngay_mua": "ngày mua dd/mm/yyyy (so với VN-Index, cắt lỗ gốc tại ngày mua)",
    "ky_han": "kỳ hạn mục tiêu (phiên)", "mt_ctck": "MT các CTCK (list hoặc 'a;b')",
    "n_phien": "số phiên kịch bản", "von_trieu": "tổng vốn (triệu đồng)", "rui_ro_pct": "% rủi ro/lệnh",
    "kl_ph": "KL CP đã phát hành", "kl_ny": "KL CP niêm yết", "cp_quy": "CP quỹ",
    "so_huu_nn": "sở hữu NN %", "beta": "Beta", "nhom": "mã cùng ngành (list hoặc 'A,B', '-' = bỏ)",
    "pb": "P/B", "roe": "ROE %", "margin": "dư nợ margin (tỷ đồng)",
    "lnst_4q": "LNST 4 quý gần nhất (tỷ đồng, từ BCTC) – để tính EPS",
    "ngay_kqkd": "ngày công bố KQKD dd/mm/yyyy", "ngay_gdkhq": "ngày GDKHQ dd/mm/yyyy",
}


def hoi(cau, mac_dinh=None, kieu=str, khoa=None, chi_tham_so=False):
    """
    Hỏi người dùng; nhấn Enter = dùng giá trị mặc định.
    chi_tham_so=True: KHÔNG hỏi – chỉ dùng giá trị truyền vào main(...) nếu có, không thì lấy tự động từ nguồn.
    [MỚI] Nếu tham số đã truyền vào main(...) theo 'khoa' → dùng luôn, không hỏi.
          Chế độ không tương tác (main(tuong_tac=False)) → dùng mặc định cho mọi câu chưa truyền.
    """
    if khoa and khoa in _THAM_SO:
        v = _THAM_SO[khoa]
        if isinstance(v, (list, tuple)):
            v = (";" if khoa == "mt_ctck" else ",").join(str(x) for x in v)
        if v is None or (isinstance(v, str) and not v.strip()):
            return mac_dinh
        if isinstance(v, str) and kieu is not str:
            try:
                return kieu(v.replace(",", ".") if kieu is float else v)
            except ValueError:
                return mac_dinh
        return v
    if chi_tham_so or not _CHAY["tuong_tac"]:
        return mac_dinh
    goi_y = f" [{mac_dinh}]" if mac_dinh is not None else ""
    s = input(f"{cau}{goi_y}: ").strip()
    if not s:
        return mac_dinh
    try:
        return kieu(s.replace(",", ".") if kieu is float else s)
    except ValueError:
        in_ra("  Giá trị không hợp lệ → dùng mặc định.")
        return mac_dinh


def tai_du_lieu(symbol, start, csv_ngay, csv_gio):
    end = str(date.today())
    in_ra("\nĐang tải dữ liệu ...")
    if csv_ngay:
        df_ngay = chuan_hoa(tu_csv(csv_ngay))
        df_ngay = df_ngay[df_ngay.index >= pd.Timestamp(start)]
        NGUON_DA_DUNG["NGÀY"] = "CSV"
        ghi_nguon("NGÀY", "CSV", f"{csv_ngay}: {len(df_ngay)} nến")
    else:
        df_ngay = _tai_ngay(symbol, start, "NGÀY")
    if df_ngay is None or len(df_ngay) < 120:
        raise SystemExit("Không đủ dữ liệu ngày (cần ≥ 120 phiên). Hãy dùng file CSV "
                         "hoặc chọn ngày bắt đầu sớm hơn.")

    if csv_gio:
        df_gio = chuan_hoa(tu_csv(csv_gio))
        ghi_nguon("GIỜ", "CSV", f"{csv_gio}: {len(df_gio)} nến")
    else:
        start_gio = str((pd.Timestamp(end) - pd.Timedelta(days=150)).date())
        df_gio = thu_cac_nguon("GIỜ", cac_nguon_gio(symbol, start_gio, end), khoa_cache=f"{symbol}_gio")
    if df_gio is not None and len(df_gio) < 60:
        df_gio = None
    if df_gio is None:
        in_ra("  ⚠ Không có dữ liệu giờ → bỏ qua phân tích khung giờ.")
    return df_ngay, df_gio


def _chuan_san(x):
    x = str(x or "").upper().replace("HSX", "HOSE").replace("UPCOM", "UPCOM").strip()
    return x if x in BIEN_DO_SAN else None


def main(tuong_tac=True, im_lang=False, xuat_file=True, **tham_so):
    """
    Chạy toàn bộ phân tích.
      tuong_tac=True : hỏi từng câu (như bản cũ).
      tuong_tac=False: KHÔNG hỏi – dùng tham số truyền vào, câu nào không truyền thì lấy mặc định. Ví dụ:
          main(tuong_tac=False, symbol="ABC", san="HOSE", von_trieu=500, rui_ro_pct=1.5, mt_nhap=24)
      im_lang=True   : không in báo cáo ra màn hình (vẫn lưu vào file TXT/HTML nếu xuat_file).
      xuat_file=False: không vẽ biểu đồ / xuất file (dùng khi quét nhiều mã).
    Trả về dict kết quả (khuyến nghị, EV, cắt lỗ, mục tiêu, ...).
    """
    sai = set(tham_so) - set(KHOA_THAM_SO) - {"gon"}
    if sai:
        raise ValueError(f"Tham số không hợp lệ: {sorted(sai)}. Dùng được: {', '.join(KHOA_THAM_SO)}")
    _THAM_SO.clear(); _THAM_SO.update(tham_so)
    _CHAY["tuong_tac"], _CHAY["im_lang"] = tuong_tac, im_lang
    _CHAY["gon"], _CHAY["muc"] = bool(tham_so.pop("gon", cfg.IN_GON) if "gon" in tham_so else cfg.IN_GON), ""
    BAO_CAO_TEXT.clear(); NHAT_KY_NGUON.clear(); NGUON_DA_DUNG.clear(); CANH_BAO_DU_LIEU.clear()
    in_ra("=" * 84)
    in_ra(" PHÂN TÍCH TỔNG HỢP: % TĂNG/GIẢM + MACD ĐỈNH ĐÁY + ĐIỂM MUA + MỤC TIÊU + QUẢN TRỊ RỦI RO")
    in_ra(" (nhấn Enter để dùng giá trị mặc định)")
    in_ra("=" * 84)
    symbol = str(hoi("Mã cổ phiếu (VD: FPT)", None, khoa="symbol") or "").strip().upper()
    while not symbol and _CHAY["tuong_tac"]:
        symbol = str(hoi("  Chưa nhập mã – nhập mã cổ phiếu", None) or "").strip().upper()
    if not symbol:
        raise ValueError("Thiếu mã cổ phiếu: main(tuong_tac=False, symbol=\"...\")")
    pre      = DU_LIEU_CTCK.get(symbol, {})
    if pre:
        in_ra(f"  ✔ Có dữ liệu CTCK nạp sẵn cho {symbol} – nhấn Enter để dùng giá trị trong [ ].")
    start    = hoi("Dữ liệu ngày từ (YYYY-MM-DD) – nên ≥ 4 năm cho khung tuần", pre.get("ngay_bat_dau", "2019-01-01"), khoa="start")
    san_nhap = hoi("Sàn niêm yết HOSE / HNX / UPCOM (bỏ trống = tự nhận)", pre.get("san"), khoa="san")
    csv_ngay = hoi("File CSV giá NGÀY (bỏ trống)", None, khoa="csv_ngay")
    csv_gio  = hoi("File CSV giá GIỜ (bỏ trống)", None, khoa="csv_gio")
    so_cp    = hoi("Số cổ phiếu đang nắm giữ", 0, int, khoa="so_cp")
    gia_von  = hoi("Giá vốn (nghìn đồng, VD 70.5)", None, float, khoa="gia_von")
    ngay_mua = hoi("Ngày mua dd/mm/yyyy (bỏ trống nếu không nhớ)", None, khoa="ngay_mua") if gia_von else None
    mt_nhap  = hoi("Giá mục tiêu tự định giá", None, float, khoa="mt_nhap")
    ky_han   = hoi("Kỳ hạn giá mục tiêu (phiên, 252 ≈ 12 tháng)", 252, int, khoa="ky_han")
    gn = ctck_gan_nhat(symbol)
    mac_dinh_ctck = ";".join(f"{v[1]:g}" for v in gn.values()) or None
    if gn:
        in_ra("     MT CTCK mới nhất: " + ", ".join(f"{k} {v[1]:g} ({v[0]:%d/%m/%Y})" for k, v in gn.items()))
    ctck_str = hoi("Giá mục tiêu các CTCK (nghìn đồng, cách nhau ';')", mac_dinh_ctck, khoa="mt_ctck")
    mt_ctck = []
    for x in (ctck_str or "").split(";"):
        try:
            mt_ctck.append(float(x.strip().replace(",", ".")))
        except ValueError:
            pass
    n_phien  = hoi("Số phiên tính xác suất kịch bản", 63, int, khoa="n_phien")
    von_trieu = hoi("Tổng vốn đầu tư (triệu đồng) – để tính khối lượng mua theo % rủi ro", None, float, khoa="von_trieu")
    rui_ro_pct = hoi(f"% vốn chấp nhận lỗ tối đa mỗi lệnh (thông lệ {RUI_RO_KHUYEN_NGHI:g})", RUI_RO_KHUYEN_NGHI, float, khoa="rui_ro_pct")
    if rui_ro_pct > 3:
        in_ra(f"  ⚠ {rui_ro_pct:g}% vốn/lệnh là rất cao – thông lệ 1–2%, tối đa 3%.")
    so_nguyen = lambda x: float(str(x).replace(".", "").replace(",", "").replace(" ", ""))
    # Số CP (phát hành/niêm yết/quỹ), sở hữu NN, beta, P/B, ROE, P/E, vốn hoá: KHÔNG hỏi nữa – lấy tự động
    # (TCBS → VNDirect → Yahoo, đối chiếu chéo; beta tự tính so VNINDEX). Muốn ghi đè: truyền vào main(kl_ph=..., ...).
    if _CHAY["tuong_tac"]:
        in_ra("  (Số CP, vốn hoá, sở hữu NN, beta, P/E, P/B, ROE: lấy tự động từ nguồn dữ liệu – không cần nhập)")
    kl_ph    = hoi("KL CP ĐÃ PHÁT HÀNH", pre.get("kl_phat_hanh"), so_nguyen, khoa="kl_ph", chi_tham_so=True)
    kl_ny    = hoi("KL CP ĐANG NIÊM YẾT", pre.get("kl_niem_yet"), so_nguyen, khoa="kl_ny", chi_tham_so=True)
    cp_quy   = hoi("Số CỔ PHIẾU QUỸ", pre.get("cp_quy"), so_nguyen, khoa="cp_quy", chi_tham_so=True)
    so_huu_nn = hoi("Sở hữu nước ngoài %", None, float, khoa="so_huu_nn", chi_tham_so=True)
    beta_nhap = hoi("Beta", None, float, khoa="beta", chi_tham_so=True)
    dung_pre_cp = bool(pre) and (kl_ph, kl_ny, cp_quy) == (pre.get("kl_phat_hanh"), pre.get("kl_niem_yet"),
                                                         pre.get("cp_quy"))
    csv_vni  = hoi("File CSV VNINDEX (bỏ trống)", None, khoa="csv_vni")
    nhom_mac_dinh = ",".join(pre.get("nhom_nganh", NHOM_NGANH.get(symbol, [])))
    nhom_str = hoi("Mã cùng ngành để so sánh (cách nhau ',', '-' = bỏ qua)", nhom_mac_dinh or None, khoa="nhom")
    nhom_ma = [m.strip().upper() for m in (nhom_str or "").split(",") if m.strip() and m.strip() != "-"]
    pb_nhap  = hoi("P/B (lần)", None, float, khoa="pb", chi_tham_so=True)
    roe_nhap = hoi("ROE (%)", None, float, khoa="roe", chi_tham_so=True)
    lnst_nhap = hoi("LNST 4 quý (tỷ đồng)", None, float, khoa="lnst_4q", chi_tham_so=True)
    la_ctck  = symbol in MA_CTCK
    margin   = hoi("Dư nợ margin (tỷ đồng)", None, float, khoa="margin", chi_tham_so=True) if la_ctck else None
    ngay_kqkd = hoi("Ngày công bố KQKD tiếp theo (dd/mm/yyyy, bỏ trống = theo quy định)", None, khoa="ngay_kqkd")
    ngay_gdkhq = hoi("Ngày GDKHQ sắp tới (dd/mm/yyyy, bỏ trống nếu không có)", pre.get("gdkhq"), khoa="ngay_gdkhq")

    if not csv_ngay:
        chuan_bi_vnstock()                       # Colab: tự cài vnstock (bản Cộng đồng) nếu thiếu
    thu_muc = f"ket_qua_{symbol}_{date.today():%Y%m%d}"
    if xuat_file:
        os.makedirs(thu_muc, exist_ok=True)
    fp = lambda ten: os.path.join(thu_muc, ten)

    # ==================================================================
    # GIAI ĐOẠN 1 – TẢI DỮ LIỆU
    # ==================================================================
    df_ngay, df_gio = tai_du_lieu(symbol, start, csv_ngay, csv_gio)
    vni = tai_vnindex(start, csv_vni)
    if vni is None:
        in_ra("  ⚠ Không có dữ liệu VNINDEX → không tính Beta / so sánh hiệu suất.")
    info = lay_thong_tin_dn(symbol)
    san = _chuan_san(san_nhap) or _chuan_san(info.get("san"))
    if not san:
        san = "HOSE"
        CANH_BAO_DU_LIEU.append("Không xác định được sàn niêm yết → tạm dùng HOSE (±7%). Nhập lại nếu là HNX/UPCoM.")
    cfg.NGUONG_TRAN_SAN = BIEN_DO_SAN[san] - 0.3
    nguon_nn = "Nhập tay" if so_huu_nn is not None else None
    if so_huu_nn is None and info.get("so_huu_nn") is not None:
        so_huu_nn, nguon_nn = info["so_huu_nn"], "TCBS"
    if so_huu_nn is None and pre.get("so_huu_nn") is not None:
        so_huu_nn, nguon_nn = pre["so_huu_nn"], f"CTCK – {pre['nguon_nn']}"
        ghi_nguon("Sở hữu nước ngoài", "CTCK", pre["nguon_nn"])
    nhap_tay = [ten for ten, v in (("KL phát hành", kl_ph), ("KL niêm yết", kl_ny), ("CP quỹ", cp_quy is not None),
                                   ("Sở hữu NN", so_huu_nn if not info.get("so_huu_nn") else None),
                                   ("Beta", beta_nhap), ("Giá vốn", gia_von), ("Giá mục tiêu", mt_nhap),
                                   ("MT CTCK", mt_ctck), ("Tổng vốn", von_trieu), ("Sàn", san_nhap)) if v]
    if nhap_tay:
        ghi_nguon("Số liệu nhập tay", "Người dùng", ", ".join(nhap_tay))
    cc = co_cau_co_phieu(kl_ph, kl_ny, cp_quy, info.get("ung_vien_cp"),
                         nhan_nhap=f"CTCK/BCTC: {pre['nguon_cp']}" if dung_pre_cp else "Tham số main()",
                         lech_pct=cfg.LECH_SO_CP_PCT)
    if dung_pre_cp:
        ghi_nguon("Cơ cấu cổ phiếu", "CTCK", pre["nguon_cp"])
    if not cc["kl_luu_hanh"]:
        CANH_BAO_DU_LIEU.append("THIẾU số CP lưu hành → không có vốn hoá/EPS (truyền main(kl_ph=..., cp_quy=...)).")
    tt = thong_tin_giao_dich(df_ngay, vni, cc, so_huu_nn, beta_nhap)
    if info.get("von_hoa_yahoo") and tt.get("von_hoa") == tt.get("von_hoa"):        # kiểm tra chéo vốn hoá
        lech = (tt["von_hoa"] / info["von_hoa_yahoo"] - 1) * 100
        tt["von_hoa_yahoo"] = info["von_hoa_yahoo"]
        if abs(lech) > cfg.LECH_VON_HOA_PCT:
            cc["canh_bao_cp"].append(f"Vốn hoá tự tính {so_vn(tt['von_hoa'], 0)} tỷ lệch {lech:+.1f}% so với Yahoo "
                                     f"({so_vn(info['von_hoa_yahoo'], 0)} tỷ) – kiểm tra số CP lưu hành.")
    tt["nguon_beta"] = "Nhập tay" if beta_nhap is not None else "Tự tính 52 tuần so VNINDEX"
    if (tt["beta"] is None or tt["beta"] != tt["beta"]) and pre.get("beta"):
        tt["beta"], tt["nguon_beta"] = pre["beta"], f"CTCK – {pre['nguon_beta']}"
        ghi_nguon("Beta", "CTCK", pre["nguon_beta"])
    tt["nguon_nn"] = nguon_nn or "—"
    if pre:
        ghi_nguon("Giá mục tiêu & chỉ số CTCK", "CTCK",
                  f"{len(pre['bao_cao'])} báo cáo, mới nhất {pre['bao_cao'][-1][1]} {pre['bao_cao'][-1][0]}")
    nhom = {}
    if nhom_ma:
        in_ra("\nĐang tải dữ liệu nhóm ngành ...")
        nhom = tai_nhom_nganh(nhom_ma, start)
    ht = df_ngay.close.iloc[-1]

    # ==================================================================
    # GIAI ĐOẠN 2 – TÍNH TOÁN (in sau, để có TÓM TẮT ở đầu báo cáo)
    # ==================================================================
    bang_khung = bien_dong_theo_khung(df_ngay)
    bang_phien, pct = phan_loai_phien(df_ngay, cfg.NGUONG_TRAN_SAN)
    mtg, mgg, xu, dd = chuoi_tang_giam(pct)

    cac_khung = {"Tuần": gop_tuan(df_ngay), "Ngày": df_ngay}
    if df_gio is not None:
        cac_khung["Giờ"] = df_gio
    kq = {}
    for ten, d in cac_khung.items():
        d = tinh_chi_bao(d)
        pv = tim_dinh_day(d, ten)
        xh = duong_xu_huong(d, pv)
        ds, tong, co = phan_tich_tin_hieu(d, pv, xh, ten)
        kq[ten] = {"df": d, "pv": pv, "xh": xh, "ds": ds, "diem": tong, "co": co, "mt": None}
    d_ngay = kq["Ngày"]["df"]
    stop = tinh_cat_lo(d_ngay, kq["Ngày"]["pv"], ht)
    in_ra("\nĐang mô phỏng lịch sử cho các mục tiêu ...")
    kq["Ngày"]["mt"] = tinh_muc_tieu(d_ngay, kq["Ngày"]["pv"], kq["Ngày"]["xh"], "Ngày", df_ngay, stop, n_phien)
    kq["Tuần"]["mt"] = tinh_muc_tieu(kq["Tuần"]["df"], kq["Tuần"]["pv"], kq["Tuần"]["xh"], "Tuần", df_ngay, stop,
                                     ky_han)
    hoi_tu = vung_hoi_tu(kq["Ngày"]["mt"]["bang"], kq["Tuần"]["mt"]["bang"])
    mt_chinh = {t: (kq[t]["mt"]["chinh"]["Giá mục tiêu"] if kq[t]["mt"]["chinh"] is not None else None)
                for t in ("Ngày", "Tuần")}
    canh_bao_dl = kiem_tra_du_lieu(df_ngay, df_gio, kq["Ngày"]["pv"], kq["Tuần"]["pv"], BIEN_DO_SAN[san])

    dx = de_xuat_muc_tieu(df_ngay, kq, ht, mt_nhap, hoi_tu, ky_han, mt_ctck or None)
    them = {"★ MT ngắn hạn (ngày)": mt_chinh["Ngày"], "★ MT trung hạn (tuần)": mt_chinh["Tuần"],
            "✎ MT tự nhập": mt_nhap, "◆ MT đề xuất": dx["chon"] if dx["chon"] != mt_nhap else None,
            "✘ Cắt lỗ": stop["gia"] if stop["gia"] < ht else None}
    bang_kb = phan_tich_kich_ban(df_ngay, so_cp, gia_von, n_phien, them)
    dk = trang_thai_tuong_tu(d_ngay, kq["Tuần"]["df"])
    wf = kiem_dinh_walk_forward(df_ngay, ht, list(kq["Ngày"]["mt"]["bang"]["Giá mục tiêu"]), stop["gia"], n_phien)
    kb = kich_ban_chinh(df_ngay, kq, ht, stop, mt_chinh, dx["chon"], so_cp, gia_von, n_phien, dk, wf=wf, nhom=nhom)
    bc = boi_canh_thi_truong(symbol, df_ngay, vni, nhom)
    lich = lich_cong_bo_kqkd(df_ngay.index[-1])
    ttr = danh_gia_thi_truong(bc, lich, df_ngay.index[-1], ngay_kqkd, ngay_gdkhq)
    qr = quan_tri_rui_ro(df_ngay, kq, ht, dx, stop, tt, kb, gia_von, so_cp, von_trieu, rui_ro_pct, ttr["he_so"])
    tg = ket_luan_mua(kq)
    qd = quyet_dinh_cuoi(tg, kb, qr, dx, ht, stop, ttr)     # ← NGUỒN DUY NHẤT của khuyến nghị
    # [MỚI] Kế hoạch từ GIÁ MUA: cắt lỗ gốc tại ngày mua, mục tiêu theo R, so với VN-Index từ ngày mua
    _mtc = kq["Ngày"]["mt"]["chinh"]
    kh = ke_hoach_tu_gia_mua(df_ngay, gia_von, ngay_mua, vni, stop["gia"], mt_nhap,
                             (dx["chon"], dx.get("hanh_dong", "đề xuất E1")) if dx.get("chon") else
                             ((_mtc["Giá mục tiêu"], _mtc["Phương pháp"]) if _mtc is not None else None),
                             n_phien) if gia_von else None
    kl = phan_tich_khoi_luong(d_ngay)
    bt = backtest_quy_tac(d_ngay, kq["Tuần"]["df"], n_phien, loc_tuan=True)
    bt0 = backtest_quy_tac(d_ngay, kq["Tuần"]["df"], n_phien, loc_tuan=False)

    cb = {"la_ctck": la_ctck, "lich": lich, "ngay_kqkd": ngay_kqkd, "ngay_gdkhq": ngay_gdkhq, "thieu": []}
    online = lay_chi_so_co_ban(symbol, ht, cc["kl_luu_hanh"], lnst_nhap) \
        if (xuat_file or _CHAY["tuong_tac"] or lnst_nhap is not None) else {}
    chi_so_ctck = {t: (v, n) for t, v, n in pre.get("chi_so", [])}
    for ten, nhap, khoa_ctck in (("P/E", None, "P/E TTM (lần)"), ("P/B", pb_nhap, "P/B (lần)"),
                                 ("ROE %", roe_nhap, "ROE (%)")):
        if nhap is not None:
            cb[ten] = (nhap, "Tham số main()")
        elif ten in online:
            cb[ten] = (online[ten], online.get("cach_tinh_pe", online.get("nguon", "")) if ten == "P/E"
                       else online.get("nguon", ""))
        elif khoa_ctck in chi_so_ctck:
            cb[ten] = chi_so_ctck[khoa_ctck]
        elif ten != "P/E":
            cb["thieu"].append(ten)
    for ten, khoa in (("EPS 4 quý (đồng)", "EPS 4Q"), ("LNST 4 quý (tỷ đồng)", "LNST 4 quý (tỷ đồng)")):
        if online.get(khoa) is not None:
            cb[ten] = (online[khoa], online.get("cach_tinh_eps", ""))
    if margin is not None:
        cb["Dư nợ margin (tỷ đồng)"] = (margin, "Nhập tay")
    # [MỚI] PHẦN J – phân tích kiểu FiinTrade (chỉ khi xuất báo cáo / chạy hỏi đáp; không đổi khuyến nghị)
    fj = None
    if xuat_file or _CHAY["tuong_tac"]:
        in_ra("\nĐang lấy BCTC năm cho phân tích 10 tiêu chí ...")
        bctc = lay_bctc_nam(symbol)
        bctc_nganh = {m: lay_bctc_nam(m, im_lang=True) for m in list(nhom)[:cfg.SO_MA_SO_SANH_FA]}
        fj = fiintrade.phan_tich(symbol, d_ngay, vni, nhom, tt, cb, online, bctc, bctc_nganh,
                                 info.get("nganh", ""), MA_CTCK)
    tt5 = lap_tom_tat(symbol, ht, df_ngay.index[-1], qd, stop, kb, qr, dx, df_ngay, kq)
    canh_bao_tt = CANH_BAO_DU_LIEU + canh_bao_dl + stop["canh_bao"] + ttr["canh_bao"]
    if kb["ms"]["tron"].get("tin_cay_thap"):
        canh_bao_tt.append("Mẫu thống kê hiệu dụng nhỏ → xác suất/EV có độ tin cậy THẤP.")
    if fj and fj["fa"] and fj["fa"]["so_nguy_hiem"] >= 2:
        canh_bao_tt.append(f"Phân tích tài chính 10 tiêu chí: {fj['fa']['so_nguy_hiem']} tiêu chí NGUY HIỂM "
                           f"({fj['fa']['tom_tat']}) – xem Phần J5.")

    # ==================================================================
    # GIAI ĐOẠN 3 – IN BÁO CÁO
    # ==================================================================
    in_tom_tat(tt5, qd, canh_bao_tt)
    in_ra(f"\n{'=' * 84}\n {symbol} ({san}) | Giá hiện tại: {ht:,.2f} nghìn đồng | "
          f"Phiên {df_ngay.index[-1]:%d/%m/%Y} | {len(df_ngay)} phiên dữ liệu\n{'=' * 84}")

    in_ra(f"\n{'#' * 84}\n PHẦN A. PHÂN TÍCH % TĂNG / GIẢM GIÁ\n{'#' * 84}")
    in_bang("A1. BIẾN ĐỘNG THEO KHUNG THỜI GIAN", bang_khung, dinh_dang={"% thay đổi": "{:+.2f}"})
    in_bang(f"A2. PHÂN LOẠI PHIÊN (biên độ {san} ±{BIEN_DO_SAN[san]:g}%, nhận diện trần/sàn ≥ {cfg.NGUONG_TRAN_SAN:g}%)",
            bang_phien, dinh_dang={"TB % thay đổi": "{:+.2f}"})
    in_ra(f"\n Chuỗi tăng dài nhất: {mtg} phiên | Chuỗi giảm dài nhất: {mgg} phiên")
    in_ra(f" Hiện tại: {dd} phiên {xu} liên tiếp | Biến động TB mỗi ngày: ±{pct.std():.2f}% "
          f"(1 năm gần nhất ±{pct.tail(252).std():.2f}%)")

    in_ra(f"\n{'#' * 84}\n PHẦN B. MACD – ĐỈNH ĐÁY, ĐƯỜNG XU HƯỚNG, TÍN HIỆU\n{'#' * 84}")
    if canh_bao_dl:
        in_ra("  KIỂM TRA DỮ LIỆU:")
        for c in canh_bao_dl:
            in_ra(f"    ⚠ {c}")
    else:
        in_ra("  KIỂM TRA DỮ LIỆU: ✔ đỉnh/đáy tuần–ngày nhất quán, không có phiên vượt biên độ bất thường.")
    for ten in kq:
        d = kq[ten]["df"]
        in_ra(f"\n{'─' * 84}\n KHUNG {ten.upper()}  ({len(d)} nến)\n{'─' * 84}")
        in_dinh_day(ten, kq[ten]["pv"], kq[ten]["xh"])
        in_tin_hieu(ten, kq[ten]["ds"], kq[ten]["diem"])
        kq[ten]["nen"] = fiintrade.nen_va_tich_luy(d, ten)          # [MỚI] tích lũy & mô hình nến 3 nến gần nhất
        fiintrade.in_nen_khung(ten, kq[ten]["nen"])
        if kq[ten]["mt"]:
            in_muc_tieu(ten, kq[ten]["mt"], ht, stop)

    in_ra(f"\n{'#' * 84}\n PHẦN C. THỜI ĐIỂM MUA & GIÁ MỤC TIÊU\n{'#' * 84}")
    if hoi_tu:
        in_ra("  ★ VÙNG MỤC TIÊU HỘI TỤ (ngày & tuần trùng nhau):")
        for lo, hi, a, b in hoi_tu[:SO_MUC_TIEU]:
            in_ra(f"     {lo:,.2f} – {hi:,.2f}  ({(lo / ht - 1) * 100:+.1f}% → {(hi / ht - 1) * 100:+.1f}%)"
                  f"   [Ngày: {a} | Tuần: {b}]")
    else:
        in_ra("  Không có vùng hội tụ giữa mục tiêu ngày và tuần.")
    for ten, nhan in (("Ngày", "Ngắn hạn (1–3 tháng)"), ("Tuần", "Trung hạn (6–12 tháng)")):
        c = kq[ten]["mt"]["chinh"]
        if c is not None:
            in_ra(f"  Mục tiêu {nhan:<22}: {c['Giá mục tiêu']:,.2f} ({c['Upside %']:+.1f}%) – {c['Phương pháp']} "
                  f"| EV {fmt(c['EV %'], 2, True)}%")
    if mt_nhap:
        in_ra(f"  Mục tiêu tự nhập (định giá)         : {mt_nhap:,.2f} ({(mt_nhap / ht - 1) * 100:+.1f}%)")
    h = _duong(kq["Ngày"]["xh"], "ho_tro")
    if h and stop["gia"] < h["gia_nay"] < ht * 1.03:
        in_ra(f"  Vùng mua tham khảo (quanh hỗ trợ ngày): {h['gia_nay']:,.2f} – {h['gia_nay'] * 1.03:,.2f} "
              f"(chỉ khi có xác nhận đảo chiều)")
    in_ra(f"  CẮT LỖ THỐNG NHẤT                    : {stop['gia']:,.2f} ({stop['pct']:+.1f}%) – {stop['quy_tac']}")
    in_ra(f"  Điểm tín hiệu có trọng số (tuần×3, ngày×2, giờ×1): {tg['diem_trong_so']:+.2f}")
    in_ra(f"\n  >>> KHUYẾN NGHỊ: {qd['khuyen_nghi']}")
    in_ra(f"      {qd['hanh_dong']}")
    in_ra("  Kiểm tra điều kiện (theo thứ tự quyền phủ quyết):")
    for t, ok in qd["kiem_tra"]:
        in_ra(f"    {'✔' if ok else ('–' if ok is None else '✘')} {t}")
    in_ra(f"  Đang nắm giữ: {qd['dang_giu']}")
    if kh:
        in_ra(f"\n{'-' * 84}\n KẾ HOẠCH VỊ THẾ TỪ GIÁ MUA (cắt lỗ gốc, mục tiêu lúc mua, so với VN-Index)\n{'-' * 84}")
        for dong in dong_ke_hoach(kh):
            in_ra(f"  • {dong}")
    in_ra("\n  Quy tắc vào lệnh:")
    in_ra("   1. TUẦN (phủ quyết): MACD tuần > Signal (tốt nhất > 0); nếu không → không mua.")
    in_ra("   2. NGÀY: tín hiệu đảo chiều (gần hỗ trợ, RSI quá bán, phân kỳ) chỉ có giá trị khi đã có xác nhận:")
    in_ra("            MACD ngày cắt lên Signal / cắt lên 0, hoặc giá phá đỉnh nhỏ 5 phiên.")
    in_ra("   3. GIỜ : vào lệnh khi MACD giờ cắt lên Signal / phá đỉnh nhỏ / phá kháng cự giờ kèm KL.")
    in_ra(f"   4. THỐNG KÊ: EV sau phí ≥ {EV_NGUONG:g}% và R/R ≥ {RR_NGUONG:g}; cắt lỗ theo quy tắc thống nhất.")

    gia_mt = dx["chon"]
    nguon_mt = (f"{dx['hanh_dong']} từ MT tự định {mt_nhap:,.2f}" if mt_nhap else "đề xuất từ phân tích") + \
               " – xem phần E1"
    in_thong_tin_giao_dich(symbol, tt, gia_mt, nguon_mt, qd)
    bang_ctck = in_bao_cao_ctck(symbol, ht, cc)

    in_ra(f"\n{'#' * 84}\n PHẦN D. KỊCH BẢN GIÁ & LÃI/LỖ\n{'#' * 84}")
    an_d1 = ["Ý nghĩa"] + ([] if so_cp else ["Lãi/Lỗ (đồng)"]) + ([] if gia_von else ["% so giá vốn"])
    in_bang(f"D1. BẢNG MỨC GIÁ & XÁC SUẤT LỊCH SỬ ({n_phien} phiên)", bang_kb, an=an_d1,
            doi_ten={"Kịch bản": "Mức giá", "% thay đổi": "% so giá", "Giá mới": "Giá",
                     f"XS đóng cửa sau {n_phien} phiên %": "Đóng cửa – toàn bộ %",
                     "XS đóng cửa – 1 năm %": "Đóng cửa – 1 năm %",
                     f"XS chạm trong {n_phien} phiên %": "Chạm – toàn bộ %", "XS chạm – 1 năm %": "Chạm – 1 năm %",
                     "XS chạm – trộn %": "Chạm – TRỘN %", "Số phiên TB để chạm": "~Phiên chạm",
                     "Lãi/Lỗ (đồng)": "Lãi/lỗ (đ)"},
            dinh_dang={"% thay đổi": "{:+.1f}", f"XS đóng cửa sau {n_phien} phiên %": "{:.1f}",
                       "XS đóng cửa – 1 năm %": "{:.1f}", f"XS chạm trong {n_phien} phiên %": "{:.1f}",
                       "XS chạm – 1 năm %": "{:.1f}", "XS chạm – trộn %": "{:.1f}", "Số phiên TB để chạm": "{:.0f}",
                       "Lãi/Lỗ (đồng)": "{:+,.0f}", "% so giá vốn": "{:+.1f}"})
    in_ra(f"  Đóng cửa = giá ĐÓNG CỬA sau {n_phien} phiên vượt mức; Chạm = giá trong phiên chạm mức ít nhất "
          "1 lần; TRỘN = ưu tiên giai đoạn gần đây (số dùng cho quyết định)."
          + ("" if so_cp else " Nhập 'số CP đang giữ' để thêm cột lãi/lỗ vị thế."))
    in_kich_ban_chinh(kb, ht)
    in_walk_forward(wf)
    in_phan_E(dx, qr, ht, stop, rui_ro_pct)
    in_khoi_luong(kl)
    in_boi_canh(symbol, bc, list(nhom), ttr)
    in_co_ban(symbol, cb)
    in_backtest(bt, bt0, n_phien)
    if fj:
        fiintrade.in_phan_J(symbol, fj)

    bang_doi_chieu = None
    if xuat_file and NGUON_DA_DUNG.get("NGÀY") in DIA_CHI_NGUON and NGUON_DA_DUNG.get("NGÀY") not in ("CSV", "Cache"):
        in_ra("\n  Đang đối chiếu giá với các nguồn khác ...")
        bang_doi_chieu = doi_chieu_nguon(symbol, df_ngay, NGUON_DA_DUNG["NGÀY"])
    in_nguon_du_lieu(bang_doi_chieu)

    ket_qua = {"symbol": symbol, "san": san, "ngay": df_ngay.index[-1], "gia": ht, "qd": qd, "stop": stop, "kb": kb,
               "qr": qr, "dx": dx, "tg": tg, "wf": wf, "ttr": ttr, "bt": bt, "bc": bc, "kl": kl, "kq": kq,
               "tom_tat": tt5, "thu_muc": thu_muc if xuat_file else None,
               # [MỚI] dùng cho phân tích DANH MỤC (dmuc) – không đổi kết quả phân tích 1 mã
               "df_ngay": df_ngay, "tt": tt, "canh_bao": canh_bao_tt, "mt_nhap": mt_nhap,
               "gia_von": gia_von, "so_cp": so_cp, "kh": kh, "ngay_mua": ngay_mua, "fiintrade": fj}
    if not xuat_file:
        return ket_qua

    # ==================================================================
    # GIAI ĐOẠN 4 – XUẤT FILE (PNG, Excel, CSV, HTML, TXT, ZIP)
    # ==================================================================
    in_ra(f"\n{'=' * 84}\n XUẤT KẾT QUẢ → thư mục {thu_muc}/\n{'=' * 84}")
    from .bieu_do import ve_tom_tat_1_trang
    anh_tom_tat = fp(f"{symbol}_tom_tat.png")
    ve_tom_tat_1_trang(symbol, df_ngay, df_ngay.index[-1], ht, qd, stop, qr, dx, kb, fj, anh_tom_tat)
    png = [fp(f"{symbol}_quan_tri_rui_ro.png"), fp(f"{symbol}_kich_ban.png")]
    ve_quan_tri_rui_ro(symbol, df_ngay, dx, qr, png[0], kq["Ngày"]["pv"], ctck_gan_nhat(symbol))
    ve_kich_ban(symbol, df_ngay, kb, png[1], kq["Ngày"]["pv"])
    ten_file = {"Tuần": "tuan", "Ngày": "ngay", "Giờ": "gio"}
    for ten in kq:
        f = fp(f"{symbol}_{ten_file[ten]}.png")
        ve_khung(symbol, ten, kq[ten]["df"], kq[ten]["pv"], kq[ten]["xh"], kq[ten]["mt"], f, stop)
        png.append(f)
    png.append(fp(f"{symbol}_khoi_luong.png")); ve_khoi_luong(symbol, d_ngay, kl, png[-1])
    png.append(fp(f"{symbol}_boi_canh.png")); ve_boi_canh(symbol, df_ngay, vni, nhom, bc, png[-1])
    png.append(fp(f"{symbol}_tang_giam.png"))
    ve_bieu_do_tang_giam(symbol, pct, bang_phien, bang_kb, ht, png[-1])

    tom_tat_df = pd.DataFrame([["Khuyến nghị", qd["khuyen_nghi"]], ["Hành động", qd["hanh_dong"]],
                               ["Đang nắm giữ", qd["dang_giu"]]] + [[f"Dòng {i + 1}", d[3:]] for i, d in
                                                                     enumerate(tt5["dong"])] +
                              [[("✔ " if ok else "– " if ok is None else "✘ ") + t, ""] for t, ok in qd["kiem_tra"]] +
                              [["Cảnh báo", c] for c in canh_bao_tt], columns=["Chỉ tiêu", "Giá trị"])
    muc_tieu_top = pd.concat([kq["Ngày"]["mt"]["top"], kq["Tuần"]["mt"]["top"]])
    cac_bang = [("Tom tat", tom_tat_df), ("Muc tieu (3 moc moi khung)", muc_tieu_top),
                ("Kich ban chinh", kb["bang"]), ("Quan tri rui ro", qr["bang"]),
                ("Bien do thong ke", kb["bien_do"]), ("Boi canh thi truong", bc["bang"]),
                ("Phan loai phien", bang_phien), ("Bien dong theo khung", bang_khung)]
    xuat_csv(fp("csv"), cac_bang + [("Backtest lenh", bt["bang"]), ("Du lieu ngay", d_ngay.drop(columns=["pos"])
                                                                    .round(4).reset_index())])

    try:
        with pd.ExcelWriter(fp(f"{symbol}_phan_tich_tong_hop.xlsx")) as w:
            tom_tat_df.to_excel(w, sheet_name="Tom tat", index=False)
            if kh:
                bang_ke_hoach(kh).to_excel(w, sheet_name="Ke hoach tu gia mua", index=False)
                kh["bang_muc_tieu_luc_mua"].to_excel(w, sheet_name="Muc tieu luc mua", index=False)
            up = (gia_mt / ht - 1) * 100 if gia_mt else np.nan
            pd.DataFrame([
                ["Khuyến nghị (hành động)", qd["khuyen_nghi"]],
                [f"Giá hiện tại ({tt['ngay']:%d/%m/%Y}) – đồng", ht * 1000],
                ["Giá mục tiêu đề xuất – đồng", gia_mt * 1000 if gia_mt else None],
                ["Nguồn giá mục tiêu", nguon_mt], ["Tỷ suất sinh lời %", up],
                ["Đánh giá định giá", danh_gia_dinh_gia(up)], ["Sàn niêm yết", san],
                ["Vốn hoá (tỷ đồng)", tt["von_hoa"]], ["KL CP đã phát hành", tt["kl_phat_hanh"]],
                ["KL CP đang niêm yết", tt["kl_niem_yet"]], ["KL CP chưa niêm yết", tt["chua_niem_yet"]],
                ["Cổ phiếu quỹ", tt["cp_quy"]], ["Số lượng CP lưu hành (= phát hành − CP quỹ)", tt["kl_luu_hanh"]],
                ["Giá cao nhất 52 tuần – đồng", tt["cao52"] * 1000],
                ["Ngày đạt đỉnh 52 tuần", tt["ngay_cao52"].strftime("%d/%m/%Y")],
                ["Giá thấp nhất 52 tuần – đồng", tt["thap52"] * 1000],
                ["Ngày đạt đáy 52 tuần", tt["ngay_thap52"].strftime("%d/%m/%Y")],
                ["% cách đỉnh 52 tuần", tt["cach_dinh52"]], ["% cao hơn đáy 52 tuần", tt["cach_day52"]],
                ["Beta", tt["beta"]], ["Nguồn Beta", tt.get("nguon_beta")],
                ["Sở hữu nước ngoài %", tt["so_huu_nn"]], ["KLGD bình quân 20 phiên", tt["kl_tb20"]],
                ["KLGD bình quân 52 tuần", tt["kl_tb52t"]], ["GTGD bình quân 20 phiên (tỷ đồng)", tt["gt_tb20"]],
            ] + [["Lưu ý cổ phiếu", c] for c in tt["canh_bao_cp"]],
                columns=["Chỉ tiêu", "Giá trị"]).to_excel(w, sheet_name="Thong tin giao dich", index=False)
            tt["hieu_suat"].to_excel(w, sheet_name="Hieu suat vs VNINDEX", index=False)
            tt["doi_chieu_cp"].to_excel(w, sheet_name="Doi chieu so CP", index=False)
            pd.DataFrame([["Kỳ hạn (phiên)", dx["ky_han"]], ["Sàn vùng hợp lý", dx["san"]],
                          ["Trần vùng hợp lý", dx["tran"]], ["MT tự định", dx["mt_nhap"]],
                          ["XS chạm MT tự định (trộn) %", dx["xs_nhap"]], ["Hành động", dx["hanh_dong"]],
                          ["MT ĐỀ XUẤT", dx["chon"]], ["Mốc", dx["moc"]],
                          ["XS chạm MT đề xuất (trộn) %", dx["xs_chon"]],
                          ["XS chạm MT đề xuất (toàn bộ) %", dx["xs_chon_deu"]],
                          ["Lý do", dx["ly_do"]]] + [["Lưu ý", c] for c in dx["canh_bao"]],
                         columns=["Chỉ tiêu", "Giá trị"]).to_excel(w, sheet_name="E1 De xuat MT", index=False)
            dx["bang"].to_excel(w, sheet_name="E1 Moc ky thuat", index=False)
            qr["bang"].to_excel(w, sheet_name="E2 Muc rui ro", index=False)
            pd.DataFrame(list(qr["vi_the"].items()) + list(qr["thong_ke"].items()) +
                         [(f"Cắt lỗ – {k}", v) for k, v in (("quy tắc", stop["quy_tac"]), ("giá", stop["gia"]),
                                                            ("theo", stop["theo"]))],
                         columns=["Chỉ tiêu", "Giá trị"]).to_excel(w, sheet_name="E2 Vi the & thong ke", index=False)
            bang_kb.to_excel(w, sheet_name="Kich ban - muc gia", index=False)
            kb["bang"].to_excel(w, sheet_name="Kich ban chinh", index=False)
            dong_ev = []
            for k, ten in (("all", "Toàn bộ"), ("1y", "1 năm"), ("tron", "Trộn"), ("dk", "Có điều kiện")):
                m = kb["ms"][k]
                dong_ev.append([ten, m.get("ev"), m.get("so_mau"), m.get("n_hieu_dung"),
                                "THẤP" if m.get("tin_cay_thap") else "chấp nhận được",
                                str(tuple(round(x, 2) for x in m["ci_ev"])) if m.get("ci_ev") else ""])
            pd.DataFrame(dong_ev + [["EV dùng để quyết định", kb["ev_qd"], None, None, "", ""],
                                    ["Điều kiện trạng thái", kb["dk_mo_ta"], None, None, "", ""]],
                         columns=["Cách tính", "EV % (sau phí)", "Số mẫu", "Mẫu hiệu dụng", "Độ tin cậy",
                                  "KTC 90%"]).to_excel(w, sheet_name="Kich ban - EV", index=False)
            kb["bien_do"].to_excel(w, sheet_name="Bien do thong ke", index=False)
            pd.DataFrame([[k, v] for k, v in kl.items() if not isinstance(v, pd.DataFrame)],
                         columns=["Chỉ tiêu", "Giá trị"]).to_excel(w, sheet_name="F Khoi luong", index=False)
            kl["profile"].to_excel(w, sheet_name="F Volume profile", index=False)
            if bc["bang"] is not None:
                bc["bang"].to_excel(w, sheet_name="G Boi canh", index=False)
            bt["bang"].to_excel(w, sheet_name="I Backtest", index=False)
            if wf is not None:
                wf["bang"].to_excel(w, sheet_name="Walk-forward", index=False)
            if fj:
                fiintrade.ghi_excel(w, fj)
            pd.DataFrame(NHAT_KY_NGUON).to_excel(w, sheet_name="Nguon du lieu", index=False)
            if bang_ctck is not None:
                bang_ctck.to_excel(w, sheet_name="Bao cao CTCK", index=False)
                p_ = DU_LIEU_CTCK[symbol]
                pd.DataFrame(list(p_["chi_so"]) + [("Beta", p_["beta"], p_["nguon_beta"]),
                                                   ("Sở hữu nước ngoài %", p_["so_huu_nn"], p_["nguon_nn"])],
                             columns=["Chỉ tiêu", "Giá trị", "Nguồn"]).to_excel(w, sheet_name="Chi so CTCK", index=False)
            if bang_doi_chieu is not None:
                bang_doi_chieu.to_excel(w, sheet_name="Doi chieu nguon", index=False)
            pd.concat([kq["Ngày"]["mt"]["bang"], kq["Tuần"]["mt"]["bang"]]).to_excel(
                w, sheet_name="Muc tieu", index=False)
            pd.DataFrame([[t, kh, nd, dd_] for t in kq for kh, nd, dd_ in kq[t]["ds"]],
                         columns=["Khung", "", "Tín hiệu", "Điểm"]).to_excel(w, sheet_name="Tin hieu mua", index=False)
            pd.DataFrame([[t, kq[t]["nen"]["so_nen_tich_luy"], kq[t]["nen"]["nen_thap"], kq[t]["nen"]["nen_cao"],
                           " | ".join(f"{a}: {b}" for a, b in kq[t]["nen"]["mo_hinh"])] for t in kq if "nen" in kq[t]],
                         columns=["Khung", "Số nến tích lũy", "Đáy nền", "Đỉnh nền", "Mô hình nến 3 nến gần nhất"]
                         ).to_excel(w, sheet_name="B Nen & tich luy", index=False)
            for ten in kq:
                kq[ten]["pv"].drop(columns=["pos"]).to_excel(w, sheet_name=f"Dinh day {ten_file[ten]}", index=False)
            bang_khung.to_excel(w, sheet_name="Khung thoi gian", index=False)
            bang_phien.to_excel(w, sheet_name="Phan loai phien", index=False)
            d_ngay.drop(columns=["pos"]).round(4).to_excel(w, sheet_name="Du lieu ngay")
        pass                                             # trang trí Excel ở dưới (sau khi có thẻ số liệu)
        in_ra(f"  ✔ Đã xuất Excel: {fp(f'{symbol}_phan_tich_tong_hop.xlsx')}")
    except PermissionError:
        in_ra("  ⚠ Không ghi được Excel – hãy đóng file Excel cũ rồi chạy lại.")

    in_ra("\n(Công cụ tham khảo dựa trên dữ liệu quá khứ – không phải khuyến nghị đầu tư)")
    fa_ = (fj or {}).get("fa") or {}
    the = [("Khuyến nghị", qd["khuyen_nghi"], qd["mau"]), ("Giá (nghìn đồng)", f"{ht:,.2f}", "#1f2d1f"),
           ("Cắt lỗ", f"{stop['gia']:,.2f} ({stop['pct']:+.1f}%)", "#C62828"),
           ("MT đề xuất", f"{dx['chon']:,.2f} ({(dx['chon'] / ht - 1) * 100:+.1f}%)", "#1B5E20"),
           ("R/R", f"{qr['rr']:.2f}", "#1f2d1f"), ("EV sau phí", f"{kb['ev_qd']:+.2f}%", "#1f2d1f"),
           ("Tài chính 10 tiêu chí", f"{fa_['diem']:.0f}/100" if fa_ and fa_.get("diem") == fa_.get("diem") else "–",
            "#1B5E20")]
    from .excel_xanh import trang_tri_excel
    trang_tri_excel(fp(f"{symbol}_phan_tich_tong_hop.xlsx"), the=the, anh=[anh_tom_tat, png[0], png[1]],
                    tieu_de=tt5["tieu_de"])
    xuat_html(fp(f"{symbol}_bao_cao.html"), symbol, tt5, qd, cac_bang + [("Backtest", bt["bang"].tail(20))], png,
              the=the, fj=fj, anh_tom_tat=anh_tom_tat)
    with open(fp(f"{symbol}_bao_cao.txt"), "w", encoding="utf-8") as f:
        f.write("".join(BAO_CAO_TEXT))
    file_zip = f"{thu_muc}.zip"
    with zipfile.ZipFile(file_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for goc, _, files in os.walk(thu_muc):
            for f in files:
                z.write(os.path.join(goc, f))
    _print_goc(f"  ✔ Đã nén toàn bộ kết quả: {file_zip}")
    if "google.colab" in sys.modules:
        _print_goc("  (Colab: mở thanh Files bên trái để tải file, hoặc đặt cfg.TU_DONG_TAI_VE = True)")
        if cfg.TU_DONG_TAI_VE:
            try:
                from google.colab import files as _files
                _files.download(file_zip)
            except Exception as e:
                _print_goc(f"  Không tự tải được: {e}")
    if tuong_tac and not im_lang and matplotlib.get_backend().lower() != "agg":
        plt.show()
    else:
        plt.close("all")
    return ket_qua


def quet_nhieu_ma(ds_ma, file_ket_qua=None, **tham_so_chung):
    """
    [MỚI] QUÉT NHIỀU MÃ không cần trả lời câu hỏi; xếp hạng theo (có tín hiệu mua, EV quyết định).
      quet_nhieu_ma(["AAA", "BBB", "CCC"], von_trieu=500, rui_ro_pct=1.5)
    Tham số chung (vd. von_trieu, n_phien, start) áp dụng cho mọi mã; 'nhom' mặc định lấy theo NHOM_NGANH (mặc định trống).
    Kết quả: DataFrame + file Excel 'quet_<ngày>.xlsx'.
    """
    rows = []
    for i, ma in enumerate(ds_ma, 1):
        _print_goc(f"[{i}/{len(ds_ma)}] {ma} ...", end=" ", flush=True)
        try:
            k = main(tuong_tac=False, im_lang=True, xuat_file=False, symbol=ma, **tham_so_chung)
            qd, kb, qr, st, tg, ttr = k["qd"], k["kb"], k["qr"], k["stop"], k["tg"], k["ttr"]
            rows.append([ma, k["san"], f"{k['ngay']:%d/%m/%Y}", k["gia"], qd["khuyen_nghi"], qd["mua"], kb["ev_qd"],
                         kb["ms"]["tron"].get("n_hieu_dung"), qr["rr"], st["gia"], st["pct"], k["dx"]["chon"],
                         (k["dx"]["chon"] / k["gia"] - 1) * 100, kb["xs_cham_stop"], tg["tuan_ok"], tg["ngay_ok"],
                         ttr["he_so"], "; ".join(qd["ly_do"])])
            _print_goc(f"{qd['khuyen_nghi']} | EV {kb['ev_qd']:+.2f}%")
        except SystemExit as e:
            rows.append([ma] + [None] * 16 + [f"lỗi dữ liệu: {e}"])
            _print_goc("lỗi dữ liệu")
        except Exception as e:
            rows.append([ma] + [None] * 16 + [f"lỗi: {str(e)[:80]}"])
            _print_goc(f"lỗi: {str(e)[:60]}")
    bang = pd.DataFrame(rows, columns=["Mã", "Sàn", "Phiên", "Giá", "Khuyến nghị", "Có tín hiệu mua",
                                       "EV quyết định %", "Mẫu hiệu dụng", "R/R", "Cắt lỗ", "Cắt lỗ %",
                                       "MT đề xuất", "Upside %", "XS bị quét cắt lỗ %", "Tuần OK", "Ngày OK",
                                       "Hệ số KL thị trường", "Điều kiện chưa đạt"])
    bang = bang.sort_values(["Có tín hiệu mua", "EV quyết định %"], ascending=False, na_position="last") \
        .reset_index(drop=True)
    _print_goc("\n" + ve_bang(bang, an=["Điều kiện chưa đạt", "Sàn", "Phiên", "Mẫu hiệu dụng", "Cắt lỗ"],
                               doi_ten={"Có tín hiệu mua": "Mua?", "EV quyết định %": "EV %", "Cắt lỗ %": "CL %",
                                        "MT đề xuất": "MT", "XS bị quét cắt lỗ %": "XS quét CL %",
                                        "Hệ số KL thị trường": "Hệ số KL", "Tuần OK": "Tuần", "Ngày OK": "Ngày"},
                               dinh_dang={"EV quyết định %": "{:+.2f}", "Cắt lỗ %": "{:+.1f}", "Upside %": "{:+.1f}",
                                          "XS bị quét cắt lỗ %": "{:.0f}", "Hệ số KL thị trường": "{:g}"}, rong=130))
    f = file_ket_qua or f"quet_{date.today():%Y%m%d}.xlsx"
    try:
        bang.to_excel(f, index=False)
        _print_goc(f"✔ Đã lưu: {f}")
    except Exception as e:
        _print_goc(f"Không lưu được Excel: {e}")
    return bang
