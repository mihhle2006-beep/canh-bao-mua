# -*- coding: utf-8 -*-
"""In các phần báo cáo, tóm tắt 5 dòng, xuất HTML/CSV."""
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
from . import cau_hinh as cfg
from .cau_hinh import (
    DU_LIEU_CTCK, EV_NGUONG, LO_CUNG_PCT, MAX_CACH_DUONG_XH, PHI_GD_KHU_HOI, RR_NGUONG,
    RUI_RO_KHUYEN_NGHI, SO_MUC_TIEU, STOP_ATR_MAX, TRONG_SO_GOP_NGANH, TRONG_SO_KHUNG, TRUOT_GIA_PCT,
    T_CONG, XS_BAN_RA, XS_SAN, XS_TRAN,
)
from .in_an import (
    BAO_CAO_TEXT, fmt, in_bang, in_ra, so_vn, ve_bang,
)
from .du_lieu import (
    NGUON_DA_DUNG, NHAT_KY_NGUON,
)
from .thong_ke import (
    danh_gia_muc,
)
from .phan_tich import (
    CHU_GIAI_CP, bang_bao_cao_ctck, ctck_gan_nhat, danh_gia_dinh_gia, von_hoa_chu,
)


def in_bao_cao_ctck(symbol, ht, cc):
    d = DU_LIEU_CTCK.get(symbol)
    if not d:
        return None
    in_ra(f"\n{'#' * 84}\n THÔNG TIN TỪ BÁO CÁO CÁC CÔNG TY CHỨNG KHOÁN\n{'#' * 84}")
    b = bang_bao_cao_ctck(symbol, ht)
    in_ra(ve_bang(b, dinh_dang={c: "{:,.1f}" for c in b.columns if c not in ("Ngày", "CTCK", "Khuyến nghị", "Báo cáo")}))
    gn = ctck_gan_nhat(symbol)
    if gn:
        mts = [v[1] for v in gn.values()]
        in_ra(f"\n  Đồng thuận (MT mới nhất mỗi CTCK, 12 tháng): "
              + " | ".join(f"{k} {v[1]:,.1f} ({v[2]}, {v[0]:%d/%m/%Y})" for k, v in gn.items()))
        in_ra(f"  Trung vị {np.median(mts):,.2f} | thấp {min(mts):,.2f} | cao {max(mts):,.2f} "
              f"→ upside {(np.median(mts) / ht - 1) * 100:+.1f}% so giá hiện tại")
    in_ra("\n  Chỉ số cơ bản theo CTCK:")
    for ten, gt, ng in d["chi_so"]:
        gt_s = gt if isinstance(gt, str) else so_vn(gt, 2 if abs(gt) < 100 else 0)
        in_ra(f"    {ten:<42}: {gt_s:<28} [{ng}]")
    in_ra(f"    {'Beta':<42}: {so_vn(d['beta'], 2):<28} [{d['nguon_beta']}]")
    in_ra(f"    {'Sở hữu nước ngoài %':<42}: {so_vn(d['so_huu_nn'], 1):<28} [{d['nguon_nn']}]")
    lh, ng = d.get("kl_lh_ctck", (None, ""))
    if lh and cc.get("kl_luu_hanh"):
        lech = (lh / cc["kl_luu_hanh"] - 1) * 100
        in_ra(f"    {'KL CP lưu hành theo CTCK':<42}: {so_vn(lh):<28} [{ng}]")
        if abs(lech) > 0.5:
            in_ra(f"    ⚠ Lệch {so_vn(lech, 2)}% so với số đang dùng ({so_vn(cc['kl_luu_hanh'])}) – có thể do phát hành "
                  f"ESOP/cổ tức sau kỳ BCTC; nhập lại nếu đã có số mới.")
    return b


# ==========================================================================
# 8. IN BÁO CÁO
# ==========================================================================
def in_dinh_day(ten_khung, pv, xh):
    in_ra(f"\n  Đỉnh/đáy gần nhất ({ten_khung}):")
    for _, r in pv.tail(6).iterrows():
        tg = r.time.strftime("%d/%m/%Y %Hh" if ten_khung == "Giờ" else "%d/%m/%Y")
        in_ra(f"    {'▼' if r.loai == 'Đỉnh' else '▲'} {r.loai:<4} {tg:<14}  "
              f"giá {r.gia:>9,.2f}  MACD {r.macd_cuc_tri:+.3f}  ({r.trang_thai})")
    in_ra(f"  Cấu trúc xu hướng (chỉ đỉnh/đáy xác nhận): {xh['cau_truc']}")
    if xh.get("ghi_chu_tam"):
        in_ra(f"  Ghi chú: {xh['ghi_chu_tam']}")
    for khoa, ten in (("khang_cu", "Kháng cự"), ("ho_tro", "Hỗ trợ")):
        if khoa in xh:
            l = xh[khoa]
            tt = ("dùng được" if l["hop_le"] else f"BỎ QUA – cách giá {l['cach']:.0f}% > {MAX_CACH_DUONG_XH:.0f}%")
            in_ra(f"  Đường {ten:<8}: {l['gia_nay']:,.2f} (dốc {l['doc']:+.3f}/nến, {l['so_cham']} lần chạm"
                  f"{' – đã xác nhận' if l['xac_nhan'] else ''}, cách giá {l['cach']:.1f}%) → {tt}")


def in_tin_hieu(ten_khung, ds, tong):
    in_ra(f"\n  Tín hiệu khung {ten_khung} (tổng điểm {tong:+d}, trọng số khung ×{TRONG_SO_KHUNG[ten_khung]}):")
    for kh, nd, _ in ds:
        in_ra(f"    {kh} {nd}")


def in_muc_tieu(ten_khung, mt, ht, stop):
    H = mt["H"]
    in_ra(f"\n  Giá mục tiêu khung {ten_khung} – {SO_MUC_TIEU} mốc tốt nhất (khả thi trước, rồi EV; mô phỏng {H} phiên, "
          f"cắt lỗ thống nhất {stop['gia']:,.2f}):")
    t = mt["top"]
    if not len(t):
        in_ra("    Không có mục tiêu phía trên.")
        return
    in_ra(f"    {'Giá':>9}  {'Upside':>7}  {'XS chạm trước CL':>16}  {'~phiên':>6}  {'EV sau phí':>10}  "
          f"{'R/R':>5}  Phương pháp")
    for _, r in t.iterrows():
        xs = r[f"XS chạm trước cắt lỗ ({H} phiên) %"]
        in_ra(f"    {r['Giá mục tiêu']:>9,.2f}  {r['Upside %']:>+6.1f}%  {fmt(xs, 0):>15}%  "
              f"{fmt(r['Số phiên trung vị'], 0):>6}  {fmt(r['EV %'], 2, True):>9}%  {fmt(r['R/R']):>5}  "
              f"{r['Phương pháp']}")
    c = mt["chinh"]
    if c is not None:
        in_ra(f"    ★ Mục tiêu chính ({mt['cach_chon']}): "
              f"{c['Giá mục tiêu']:,.2f} "
              f"({c['Upside %']:+.1f}%) – {c['Phương pháp']}")
    an = len(mt["bang"]) - len(t)
    if an > 0:
        in_ra(f"    ({an} mốc khác EV thấp hơn – xem sheet Excel 'Muc tieu')")


def in_walk_forward(wf):
    """[MỚI] D4 – kiểm định ngoài mẫu bước chọn mục tiêu."""
    in_ra(f"\n{'-' * 84}\n D4. KIỂM ĐỊNH WALK-FORWARD BƯỚC CHỌN MỤC TIÊU (khung ngày)\n{'-' * 84}")
    if wf is None:
        in_ra("  Không đủ dữ liệu để kiểm định (cần ≥ 2 khối thời gian có đủ mẫu).")
        return
    in_ra(ve_bang(wf["bang"], doi_ten={"Mốc được chọn (dữ liệu trước đó)": "Mốc chọn (dữ liệu trước)",
                                       "Mốc tốt nhất (nhìn lại)": "Mốc tốt nhất nhìn lại",
                                       "EV tốt nhất nhìn lại %": "EV tốt nhất nhìn lại %"},
                  dinh_dang={"EV trong mẫu %": "{:+.2f}", "EV ngoài mẫu %": "{:+.2f}", "EV tốt nhất nhìn lại %": "{:+.2f}"}))
    in_ra(f"  EV trong mẫu của mốc công cụ chọn ({wf['muc_is']:,.2f}): {wf['ev_is']:+.2f}% | EV ngoài mẫu "
          f"(walk-forward): {wf['ev_wf']:+.2f}% → THIÊN LỆCH CHỌN {wf['lech']:.2f}% (đã trừ vào EV quyết định)")
    in_ra("  → Mỗi khối chỉ được 'thấy' dữ liệu TRƯỚC nó (đệm thêm H phiên để các giai đoạn chồng lấn không rò rỉ). "
          "Chênh lệch lớn giữa trong mẫu và ngoài mẫu nghĩa là con số EV hiển thị đang lạc quan quá mức.")


def in_kich_ban_chinh(kb, ht):
    n = kb["n"]
    in_ra(f"\n{'-' * 84}\n D2. BA KỊCH BẢN CHÍNH trong {n} phiên tới (giá nghìn đồng)\n{'-' * 84}")
    in_ra(f"  Các mốc: cắt lỗ {kb['cat_lo']:,.2f} | hỗ trợ {kb['hotro']:,.2f}"
          f"{'' if kb['hotro_that'] else ' (chưa có hỗ trợ xác nhận – tạm = cắt lỗ + 0.5×ATR)'} | giá {ht:,.2f} | "
          f"breakout {kb['kc']:,.2f} | MT cơ sở {kb['mt_cs']:,.2f} | MT tích cực {kb['mt_tc']:,.2f}")
    v = lambda x, d=0: f"{x:.{d}f}%" if x == x else "N/A"
    for _, r in kb["bang"].iterrows():
        tg = f"~{r['Số phiên trung vị']:.0f} phiên" if r["Số phiên trung vị"] == r["Số phiên trung vị"] else "–"
        in_ra(f"\n  ▶ {r['Kịch bản']:<22} giá {r['Giá mục tiêu']:,.2f} ({r['% so giá hiện tại']:+.1f}%) | {tg}")
        in_ra(f"     Xác suất    : toàn bộ {v(r['XS toàn bộ %'])} | 1 năm {v(r['XS 1 năm %'])} | "
              f"TRỘN {v(r['XS trộn %'])} (KTC 90% {r['KTC 90% (trộn)']}) | có điều kiện {v(r['XS có điều kiện %'])}")
        in_ra(f"     Kích hoạt   : {r['Điều kiện kích hoạt']}")
        in_ra(f"     Xác nhận    : {r['Tín hiệu xác nhận']}")
        in_ra(f"     Đang giữ    : {r['Đang nắm giữ']}")
        in_ra(f"     Chưa có CP  : {r['Chưa có cổ phiếu']}")
        in_ra(f"     Mốc giá     : {r['Ghi chú mốc']}")
    in_ra(f"\n  Trạng thái hiện tại nghiêng về : {kb['hien_tai']}")
    ms = kb["ms"]
    in_ra(f"\n  LỢI SUẤT KỲ VỌNG nếu mua & tuân thủ kế hoạch – theo LUẬT GIAO DỊCH VN (mua giá mở cửa phiên sau, "
          f"bán từ T+{T_CONG}, khoá sàn, gap; trừ phí {PHI_GD_KHU_HOI:g}% + trượt giá 2×{TRUOT_GIA_PCT:g}%):")
    for k, ten in (("all", "Toàn bộ lịch sử"), ("1y", "1 năm gần nhất"), ("tron", "TRỘN (ưu tiên gần đây)"),
                   ("dk", f"Có điều kiện [{kb['dk_mo_ta']}]")):
        m = ms[k]
        if not m.get("so_mau"):
            in_ra(f"    {ten:<34}: không đủ mẫu")
            continue
        ci = m.get("ci_ev")
        nhan = "⚠ độ tin cậy THẤP" if m["tin_cay_thap"] else "độ tin cậy chấp nhận được"
        in_ra(f"    {ten:<34}: EV {m['ev']:+.2f}%" + (f" (KTC 90% {ci[0]:+.1f} … {ci[1]:+.1f}%)" if ci else "")
              + f" | {m['so_mau']} mẫu, ~{m['n_hieu_dung']:.0f} mẫu hiệu dụng → {nhan}")
    g = kb.get("gop")
    if g:
        ci = g.get("ci_ev")
        ds = ", ".join(f"{m} ({n_} mẫu, σ×{k_:.2f})" for m, n_, k_ in kb["gop_ct"])
        in_ra(f"    {'GỘP NGÀNH (chuẩn hoá biến động)':<34}: EV {g['ev']:+.2f}%"
              + (f" (KTC 90% {ci[0]:+.1f} … {ci[1]:+.1f}%)" if ci else "")
              + f" | {g['so_mau']} mẫu, ~{g['n_hieu_dung']:.0f} mẫu hiệu dụng [{ds}]")
    else:
        in_ra(f"    {'GỘP NGÀNH':<34}: chưa có dữ liệu mã cùng ngành")
    in_ra(f"  Cách ra EV quyết định:")
    in_ra(f"    (1) EV cơ sở = {'trộn của mã' if not g else f'{1 - TRONG_SO_GOP_NGANH:g}×trộn + {TRONG_SO_GOP_NGANH:g}×gộp ngành'}"
          f" = {kb['ev_co_so']:+.2f}%")
    in_ra(f"    (2) {'min với có điều kiện' if kb['dk_du'] else 'không đủ mẫu có điều kiện'} → {kb['ev_truoc_wf']:+.2f}%")
    in_ra(f"    (3) trừ thiên lệch chọn mục tiêu (walk-forward, phần D4) {kb['lech_wf']:.2f}% → {kb['ev_qd']:+.2f}%")
    in_ra(f"  >>> EV DÙNG ĐỂ QUYẾT ĐỊNH: {kb['ev_qd']:+.2f}% → "
          f"{'ĐẠT' if kb['ev_qd'] >= EV_NGUONG else 'KHÔNG ĐẠT'} ngưỡng {EV_NGUONG:g}%")
    in_ra(f"  R/R (MT tích cực / cắt lỗ): {kb['rr']:.2f} | XS chạm cắt lỗ trong {n} phiên (bất kể mục tiêu, trộn): "
          f"{kb['xs_cham_stop']:.0f}%")
    if kb["xs_cham_stop"] >= 70:
        in_ra(f"  ⚠ Cắt lỗ {(kb['cat_lo'] / ht - 1) * 100:+.1f}% quá sát so với biến động TB ngày "
              f"±{kb['do_lech_ngay']:.2f}%: {kb['xs_cham_stop']:.0f}% khả năng bị quét trong {n} phiên → "
              f"giảm khối lượng hoặc chờ biến động hạ nhiệt.")
    in_ra(f"  Cách tính: mỗi phiên quá khứ là 1 lần 'mua giả định', theo dõi {n} phiên kế tiếp bằng giá cao/thấp; "
          f"chạm cắt lỗ và mục tiêu cùng phiên → tính là cắt lỗ. Các giai đoạn CHỒNG LẤN nên số mẫu hiệu dụng "
          f"= số mẫu (Kish) ÷ độ dài TB giai đoạn; KTC 90% bằng block bootstrap. TRỘN = trọng số giảm 1/2 sau "
          f"mỗi {XS_BAN_RA} phiên; CÓ ĐIỀU KIỆN = chỉ các phiên có trạng thái giống hiện tại.")

    in_ra(f"\n{'-' * 84}\n D3. BIÊN ĐỘ DAO ĐỘNG THỐNG KÊ sau {n} phiên\n{'-' * 84}")
    in_ra(ve_bang(kb["bien_do"], dinh_dang={"Cận dưới %": "{:+.1f}", "Cận trên %": "{:+.1f}"}))
    in_ra("  → σ EWMA phản ánh biến động hiện tại; phân vị thực nghiệm phản ánh 'đuôi dày' (biến động cực đoan "
          "thường xuyên hơn phân phối chuẩn). Mục tiêu ngoài vùng 68% cần chất xúc tác mới đạt.")
    in_ra("  Lưu ý: xác suất là tần suất trong quá khứ của chính cổ phiếu này, không phải dự báo.")


def in_nguon_du_lieu(bang_doi_chieu):
    in_ra(f"\n{'#' * 84}\n NGUỒN DỮ LIỆU\n{'#' * 84}")
    for r in NHAT_KY_NGUON:
        in_ra(f"  • {r['Dữ liệu']:<26}: {r['Nguồn']:<9} {('(' + r['Địa chỉ'] + ')') if r['Địa chỉ'] else ''}"
              f" – {r['Chi tiết']} [{r['Thời điểm lấy']}]")
    if bang_doi_chieu is not None and len(bang_doi_chieu):
        in_ra(f"\n  Đối chiếu giá đóng cửa với nguồn khác (nguồn chính: {NGUON_DA_DUNG.get('NGÀY', '?')}):")
        in_ra(ve_bang(bang_doi_chieu))
    in_ra("\n  Nguồn kiểm chứng thủ công: hsx.vn / hnx.vn (KL niêm yết, CP quỹ), BCTC & báo cáo thường niên "
          "của doanh nghiệp, VSDC (vsd.vn – số CP đăng ký), cafef.vn (cổ tức, sở hữu nước ngoài).")
    in_ra("  Các API VNDirect/TCBS/DNSE/VCI là API công khai không chính thức – có thể thay đổi bất cứ lúc nào.")


def in_thong_tin_giao_dich(symbol, tt, gia_mt, nguon_mt, qd):
    in_ra(f"\n{'#' * 84}\n THÔNG TIN GIAO DỊCH & KHUYẾN NGHỊ\n{'#' * 84}")
    in_ra(f"  Khuyến nghị (hành động)     : {qd['khuyen_nghi']}   ← kết quả DUY NHẤT của hàm quyết định")
    in_ra(f"  Giá hiện tại ({tt['ngay']:%d/%m/%Y})   : {so_vn(tt['gia'] * 1000)} đồng")
    if gia_mt:
        up = (gia_mt / tt["gia"] - 1) * 100
        in_ra(f"  Giá mục tiêu đề xuất        : {so_vn(gia_mt * 1000)} đồng   ({nguon_mt})")
        in_ra(f"  Tỷ suất sinh lời / định giá : {so_vn(up, 1)}% – {danh_gia_dinh_gia(up)}")
    in_ra(f"  {'─' * 60}")
    if not tt["kl_luu_hanh"]:
        in_ra("  ⚠ THIẾU SỐ CP LƯU HÀNH → không tính được vốn hoá / EPS. Nhập tay 'KL CP ĐÃ PHÁT HÀNH' và "
              "'Số CỔ PHIẾU QUỸ' (BCTC mục Vốn góp chủ sở hữu) khi chạy lại.")
    in_ra(f"  Vốn hoá                     : {von_hoa_chu(tt['von_hoa'])}")

    def _cp(x):
        return f"{so_vn(x)} cổ phiếu" if x else "N/A"
    in_ra(f"  KL CP đã phát hành          : {_cp(tt['kl_phat_hanh'])}")
    in_ra(f"  KL CP đang niêm yết         : {_cp(tt['kl_niem_yet'])}")
    in_ra(f"  Cổ phiếu quỹ                : {so_vn(tt['cp_quy'])} cổ phiếu")
    in_ra(f"  Số lượng CP lưu hành        : {_cp(tt['kl_luu_hanh'])}   (= phát hành − CP quỹ)")
    for cb in tt["canh_bao_cp"]:
        in_ra(f"    ⚠ {cb}")
    in_ra("  Chú giải:")
    for cg in CHU_GIAI_CP:
        in_ra(f"    • {cg}")
    bdc = tt.get("doi_chieu_cp")
    if bdc is not None:
        in_ra("  Đối chiếu số CP giữa các nguồn (ưu tiên: nhập tay > TCBS > VNDirect > Yahoo):")
        cot_so = [c for c in bdc.columns if c not in ("Chỉ tiêu", "Nguồn", "Lệch tối đa %")]
        in_ra(ve_bang(bdc, dinh_dang={**{c: (lambda x: so_vn(x)) for c in cot_so}, "Lệch tối đa %": "{:.2f}"}))
    in_ra(f"  Giá cao nhất 52 tuần        : {so_vn(tt['cao52'] * 1000)} đồng  "
          f"(ngày {tt['ngay_cao52']:%d/%m/%Y}, giá hiện tại thấp hơn đỉnh {so_vn(-tt['cach_dinh52'], 1)}%)")
    in_ra(f"  Giá thấp nhất 52 tuần       : {so_vn(tt['thap52'] * 1000)} đồng  "
          f"(ngày {tt['ngay_thap52']:%d/%m/%Y}, giá hiện tại cao hơn {so_vn(tt['cach_day52'], 1)}%)")
    in_ra(f"  Beta                        : {so_vn(tt['beta'], 2)}   [{tt.get('nguon_beta', '')}]")
    in_ra(f"  Sở hữu cổ đông nước ngoài   : {so_vn(tt['so_huu_nn'], 2) + '%' if tt['so_huu_nn'] is not None else 'N/A'}"
          f"   [{tt.get('nguon_nn', '')}]")
    in_ra(f"  KLGD bình quân 20 phiên     : {so_vn(tt['kl_tb20'])} cổ phiếu")
    in_ra(f"  KLGD bình quân 52 tuần      : {so_vn(tt['kl_tb52t'])} cổ phiếu")
    in_ra(f"  GTGD bình quân 20 phiên     : {so_vn(tt['gt_tb20'], 1)} tỷ đồng")
    in_bang("Hiệu suất so với VNINDEX", tt["hieu_suat"], dinh_dang={c: "{:+.2f}" for c in tt["hieu_suat"].columns[1:]})


def in_phan_E(dx, qr, ht, stop, rui_ro_pct):
    in_ra(f"\n{'#' * 84}\n PHẦN E. ĐỀ XUẤT GIÁ MỤC TIÊU & QUẢN TRỊ RỦI RO\n{'#' * 84}")
    in_ra(f"\n{'-' * 84}\n E1. ĐỀ XUẤT GIÁ MỤC TIÊU (kỳ hạn {dx['ky_han']} phiên)\n{'-' * 84}")
    in_ra(f"  Vùng mục tiêu hợp lý : {dx['san']:,.2f} – {dx['tran']:,.2f}  "
          f"({(dx['san'] / ht - 1) * 100:+.1f}% → {(dx['tran'] / ht - 1) * 100:+.1f}%)")
    in_ra(f"     (SÀN = ≥{XS_SAN:.0f}% giai đoạn đã chạm; TRẦN = ≤{XS_TRAN:.0f}% chạm & trong biên 95% σ EWMA; "
          f"theo {dx['cach']})")
    if dx["mt_nhap"]:
        in_ra(f"  Mục tiêu tự định     : {dx['mt_nhap']:,.2f} ({(dx['mt_nhap'] / ht - 1) * 100:+.1f}%) – "
              f"XS chạm (trộn) {dx['xs_nhap']:.0f}%")
    in_ra(f"  >>> {dx['hanh_dong']} → MỤC TIÊU ĐỀ XUẤT: {dx['chon']:,.2f} ({(dx['chon'] / ht - 1) * 100:+.1f}%) "
          f"– XS chạm: trộn {fmt(dx['xs_chon'], 0)}% | toàn bộ lịch sử {fmt(dx['xs_chon_deu'], 0)}%")
    in_ra(f"      {dx['ly_do']}")
    for cb in dx["canh_bao"]:
        in_ra(f"      ⚠ {cb}")
    if len(dx["bang"]):
        b = dx["bang"]
        gan = b[b["Trong vùng hợp lý"] == "✔"].head(SO_MUC_TIEU)
        if len(gan):
            in_ra(f"\n  Mốc kỹ thuật trong vùng hợp lý (tối đa {SO_MUC_TIEU}; đầy đủ ở sheet 'E1 Moc ky thuat'):")
            in_ra(ve_bang(gan, an=["Trong vùng hợp lý"],
                          doi_ten={c: c.replace(f"XS chạm {dx['ky_han']} phiên – ", "XS chạm ") for c in gan.columns},
                          dinh_dang={c: ("{:+.1f}" if c == "Upside %" else "{:.1f}") for c in gan.columns
                                     if c not in ("Mốc", "Giá", "Trong vùng hợp lý")}))

    in_ra(f"\n{'-' * 84}\n E2. CÁC MỨC QUẢN TRỊ RỦI RO (giá nghìn đồng)\n{'-' * 84}")
    in_ra(ve_bang(qr["bang"], doi_ten={"% so giá hiện tại": "% so giá"}, dinh_dang={"% so giá hiện tại": "{:+.1f}"}))
    in_ra(f"  Cắt lỗ thống nhất = {stop['quy_tac']} → {stop['gia']:,.2f} (theo {stop['theo']}). "
          f"Thành phần: đáy ngày − buffer {fmt(stop['lo_day'])} | giá − {STOP_ATR_MAX:g}×ATR {fmt(stop['lo_atr'])} | "
          f"cứng −{LO_CUNG_PCT:g}% {fmt(stop['lo_cung'])}")
    for cb in stop["canh_bao"]:
        in_ra(f"  ⚠ {cb}")
    if qr["phong_thu"]:
        in_ra(f"\n  KẾ HOẠCH PHÒNG THỦ: mục tiêu ≤ giá hiện tại → không mở vị thế mới; giảm tỷ trọng khi hồi; "
              f"mua lại ở ≤ {qr['gia_mua_rr2']:,.2f}.")
    else:
        nhan_rr = (f"(đạt ≥ {RR_NGUONG:g})" if qr["rr"] >= RR_NGUONG
                   else f"(< {RR_NGUONG:g} – chỉ mua ở giá ≤ {qr['gia_mua_rr2']:,.2f})")
        in_ra(f"\n  R/R hiện tại: {qr['rr']:.2f} {nhan_rr}")
    if rui_ro_pct > 3:
        in_ra(f"  ⚠ Rủi ro {rui_ro_pct:g}% vốn/lệnh là RẤT CAO (thông lệ {RUI_RO_KHUYEN_NGHI:g}%, tối đa 3%): "
              f"3 lệnh thua liên tiếp ≈ −{(1 - (1 - rui_ro_pct / 100) ** 3) * 100:.0f}% vốn.")
    if qr["vi_the"]:
        in_ra("\n  Quy mô vị thế:")
        for k, v in qr["vi_the"].items():
            if isinstance(v, str):
                gt = v
            elif "Số phiên" in k:
                gt = "< 1 phiên" if v < 1 else f"{so_vn(v, 1)} phiên"
            else:
                gt = so_vn(v, 1 if abs(v) < 1000 else 0)
            in_ra(f"    {k:<52}: {gt}")
    else:
        in_ra("\n  Chưa nhập 'Tổng vốn đầu tư' → chưa tính được quy mô vị thế.")
        if qr.get("vi_du"):
            in_ra(f"    {qr['vi_du']}")
    in_ra("\n  Rủi ro thống kê:")
    for k, v in qr["thong_ke"].items():
        in_ra(f"    {k:<44}: {so_vn(v, 0 if 'phiên)' in k else 2)}")
    in_ra(f"\n  Kỷ luật: (1) không mua khi EV < {EV_NGUONG:g}% hoặc R/R < {RR_NGUONG:g}; (2) đóng cửa dưới cảnh báo sớm"
          f" → giảm 1/3; (3) đóng cửa dưới cắt lỗ → bán hết; (4) đạt TP1 → dời cắt lỗ về hoà vốn; "
          f"(5) sau {qr['thong_ke']['Cắt lỗ thời gian (phiên)']} phiên chưa đạt TP1 → đánh giá lại luận điểm.")


def in_khoi_luong(kl):
    in_ra(f"\n{'#' * 84}\n PHẦN F. KHỐI LƯỢNG & THANH KHOẢN\n{'#' * 84}")
    in_ra(f"  KL phiên gần nhất / TB20         : {so_vn(kl['kl_nay'])} / {so_vn(kl['kl_tb20'])} "
          f"(= {fmt(kl['ty_le_kl'])} lần)")
    in_ra(f"  KL phiên tăng / KL phiên giảm (20): {fmt(kl['kl_tang_giam'])} "
          f"({'bên mua chủ động hơn' if kl['kl_tang_giam'] > 1 else 'bên bán chủ động hơn'})")
    in_ra(f"  Số phiên KL ≥ 1.5× TB20 (20 phiên): {kl['so_bung_no']}")
    in_ra(f"  OBV (20 phiên)                   : {kl['obv']}")
    in_ra(f"  Volume profile {kl['so_phien']} phiên        : POC {kl['poc']:,.2f} | vùng giá trị 70% "
          f"{kl['val']:,.2f} – {kl['vah']:,.2f} → giá đang {kl['vi_tri']}")
    in_ra(f"  GTGD TB20                        : {kl['gt_tb20']:,.1f} tỷ đồng")
    in_ra("  → Breakout chỉ được tính điểm khi KL ≥ 1.5× TB20 (xem tín hiệu khung ngày/giờ).")


def in_boi_canh(symbol, bc, nhom_ma, ttr=None):
    in_ra(f"\n{'#' * 84}\n PHẦN G. BỐI CẢNH THỊ TRƯỜNG & SỨC MẠNH TƯƠNG ĐỐI\n{'#' * 84}")
    v = bc["vni"]
    if v:
        in_ra(f"  VN-Index {v['gia']:,.2f}: xu hướng {v['xu']} | "
              f"{'trên' if v['tren_ma200'] else 'dưới'} MA200 | MACD tuần {'>' if v['macd_tuan_ok'] else '≤'} Signal"
              f" | 3 tháng {fmt(v['r3t'], 1, True)}%")
    else:
        in_ra("  Không có dữ liệu VN-Index.")
    r = bc["rs"]
    if r:
        in_ra(f"  Đường RS ({symbol}/VN-Index): {'TRÊN' if r['tren_ma50'] else 'DƯỚI'} MA50 | thay đổi 3 tháng "
              f"{fmt(r['doi_3t'], 1, True)}%" + (" | ⚠ RS ở ĐÁY 1 năm (yếu nhất so với thị trường)" if r["day_1n"] else ""))
    in_ra(f"  Nhóm so sánh: {', '.join(nhom_ma) if nhom_ma else '(không có)'}")
    if bc["bang"] is not None:
        in_ra(ve_bang(bc["bang"], dinh_dang={c: "{:+.1f}" for c in bc["bang"].columns if c != "Mã"}))
    for s in bc["nhan_dinh"]:
        in_ra(f"  → {s}")
    if ttr:
        in_ra(f"  ẢNH HƯỞNG TỚI QUYẾT ĐỊNH: VN-Index {'XẤU' if ttr['vni_xau'] else 'ổn'} | RS "
              f"{'ở ĐÁY 1 năm' if ttr['rs_yeu'] else 'bình thường'} → hệ số khối lượng ×{ttr['he_so']:g}"
              + (" | KHÔNG mở vị thế mới (cả hai yếu tố xấu)" if ttr["vni_xau"] and ttr["rs_yeu"] else ""))
        for sk in ttr["su_kien"]:
            in_ra(f"  ⚠ Sự kiện sắp tới: {sk} → không mở vị thế mới trước sự kiện")
        for c_ in ttr["canh_bao"]:
            in_ra(f"  ⚠ {c_}")
        if not ttr["co_vni"]:
            in_ra("  (Không có dữ liệu VN-Index → bỏ qua điều chỉnh theo thị trường)")


def in_co_ban(symbol, cb):
    in_ra(f"\n{'#' * 84}\n PHẦN H. CƠ BẢN TỐI THIỂU & CHẤT XÚC TÁC\n{'#' * 84}")
    for ten in ("P/E", "EPS 4 quý (đồng)", "LNST 4 quý (tỷ đồng)", "P/B", "ROE %", "Dư nợ margin (tỷ đồng)",
                "Dư nợ margin / VCSH (lần)"):
        if ten in cb:
            v, ng = cb[ten]
            in_ra(f"  {ten:<28}: {fmt(v) if not isinstance(v, str) else v:<12} [{ng}]")
    if cb.get("la_ctck") and "Dư nợ margin (tỷ đồng)" not in cb:
        in_ra("  Dư nợ margin               : chưa nhập (quan trọng với CTCK – lấy từ BCTC quý, thuyết minh "
              "'Các khoản cho vay')")
    l = cb.get("lich")
    if cb.get("ngay_kqkd"):
        in_ra(f"  KQKD tiếp theo (nhập tay)    : {cb['ngay_kqkd']}")
    if l:
        in_ra(f"  Lịch công bố {l['ky']:<16}: hạn BCTC riêng {l['han_rieng']:%d/%m/%Y} | công ty mẹ/hợp nhất "
              f"{l['han_hop_nhat']:%d/%m/%Y} (còn {l['con_ngay']} ngày) → chất xúc tác gần nhất")
    if cb.get("thieu"):
        in_ra(f"  ⚠ Thiếu: {', '.join(cb['thieu'])} – nhập tay khi chạy hoặc bổ sung vào DU_LIEU_CTCK.")


def in_backtest(bt, bt0, n_giu):
    in_ra(f"\n{'#' * 84}\n PHẦN I. BACKTEST QUY TẮC VÀO LỆNH (tuần + ngày, giữ tối đa {n_giu} phiên)\n{'#' * 84}")
    if not bt["so_lenh"]:
        in_ra("  Không có lệnh nào trong lịch sử → chưa đánh giá được quy tắc.")
        return
    for ten, b in (("Có lọc MACD tuần (quy tắc của công cụ)", bt), ("Không lọc tuần (đối chứng)", bt0)):
        if not b["so_lenh"]:
            in_ra(f"  {ten}: không có lệnh")
            continue
        in_ra(f"  {ten}:")
        in_ra(f"    {b['so_lenh']} lệnh / {b['so_nam']:.1f} năm | thắng {b['ty_le_thang']:.0f}% | "
              f"TB/lệnh {b['tb']:+.2f}% (thắng {fmt(b['tb_thang'], 2, True)}%, thua {fmt(b['tb_thua'], 2, True)}%) | "
              f"PF {fmt(b['pf'])} | tổng {b['tong']:+.1f}% | MDD {b['mdd']:.1f}% | giữ TB {b['giu_tb']:.0f} phiên"
              + (" | ⚠ < 30 lệnh: độ tin cậy THẤP" if b["tin_cay_thap"] else ""))
    in_ra(f"  Mua & giữ cùng giai đoạn: {bt['buy_hold']:+.1f}%")
    co_loi_the = bt["tb"] > 0 and (bt["pf"] == bt["pf"] and bt["pf"] > 1.2)
    loc_co_ich = bt0["so_lenh"] and bt["tb"] > bt0["tb"]
    in_ra(f"  → Quy tắc {'CÓ' if co_loi_the else 'CHƯA có'} lợi thế (TB/lệnh > 0 và PF > 1.2); "
          f"bộ lọc tuần {'có' if loc_co_ich else 'không'} cải thiện kết quả.")
    in_ra("  Lưu ý: backtest trên chính mã này, không tính trượt giá & giới hạn biên độ; chỉ để tham khảo.")


# ==========================================================================
# 10H. [MỚI] TÓM TẮT 5 DÒNG & XUẤT HTML / CSV
# ==========================================================================
def lap_tom_tat(symbol, ht, ngay, qd, stop, kb, qr, dx, df_ngay, kq):
    if qd["mua"]:
        vung = f"{max(stop['gia'] * 1.01, min(ht, qr['gia_mua_rr2']) * 0.97):,.2f} – {min(ht, qr['gia_mua_rr2']):,.2f}"
    elif kb["hotro_that"] and not qr["phong_thu"]:
        vung = (f"{kb['hotro']:,.2f} – {min(kb['hotro'] * 1.03, qr['gia_mua_rr2']):,.2f} "
                f"(chỉ khi có xác nhận đảo chiều; tối đa {qr['gia_mua_rr2']:,.2f} để R/R ≥ {RR_NGUONG:g})")
    else:
        vung = (f"chưa có hỗ trợ xác nhận gần giá – chờ điều kiện; giá mua tối đa {qr['gia_mua_rr2']:,.2f} "
                f"(R/R ≥ {RR_NGUONG:g})")
    if qr["phong_thu"]:
        dong_mt = (f"4. Mục tiêu: không mở vị thế mới (MT đề xuất {dx['chon']:,.2f} ≤ giá); "
                   f"bán giảm khi hồi về {qr['bang']['Giá'].iloc[0]:,.2f}")
    else:
        t1, t2 = qr["tp"][0], dx["chon"]
        xs1, tt1, _, _ = danh_gia_muc(df_ngay, ht, t1, stop["gia"], kb["n"])
        xs2, tt2, _, _ = danh_gia_muc(df_ngay, ht, t2, stop["gia"], dx["ky_han"])
        dong_mt = (f"4. Mục tiêu: TP1 {t1:,.2f} ({(t1 / ht - 1) * 100:+.1f}%, XS chạm trước cắt lỗ {fmt(xs1, 0)}%/{kb['n']} phiên, "
                   f"~{fmt(tt1, 0)} phiên) | MT đề xuất {t2:,.2f} ({(t2 / ht - 1) * 100:+.1f}%, XS {fmt(xs2, 0)}%/{dx['ky_han']} phiên, "
                   f"~{fmt(tt2, 0)} phiên)")
    tc = kb["ms"]["tron"]
    tin_cay = "tin cậy THẤP" if tc.get("tin_cay_thap") else "tin cậy chấp nhận được"
    dong = [
        f"1. KHUYẾN NGHỊ: {qd['khuyen_nghi']} – {qd['hanh_dong']}",
        f"2. Vùng mua: {vung}",
        f"3. Cắt lỗ: {stop['gia']:,.2f} ({stop['pct']:+.1f}%) – {stop['quy_tac']}",
        dong_mt,
        f"5. EV {kb['ev_qd']:+.2f}% sau phí ({tin_cay}, ~{fmt(tc.get('n_hieu_dung'), 0)} mẫu hiệu dụng) | "
        f"R/R {fmt(qr['rr'])} | XS chạm cắt lỗ trong {kb['n']} phiên {fmt(kb['xs_cham_stop'], 0)}%",
    ]
    return {"tieu_de": f"TÓM TẮT – {symbol} | phiên {ngay:%d/%m/%Y} | giá {ht:,.2f} nghìn đồng", "dong": dong}


def in_tom_tat(tt5, qd, canh_bao):
    in_ra(f"\n{'█' * 84}\n {tt5['tieu_de']}\n{'█' * 84}")
    for d in tt5["dong"]:
        in_ra(f"  {d}")
    in_ra(f"  Đang nắm giữ: {qd['dang_giu']}")
    if qd["ly_do"]:
        in_ra(f"  Điều kiện chưa đạt: {'; '.join(qd['ly_do'])}")
    for c in canh_bao:
        in_ra(f"  ⚠ {c}")
    in_ra(f"{'█' * 84}")


def _bang_html(df, so_le=2):
    if df is None or not len(df):
        return "<p><i>(không có dữ liệu)</i></p>"
    return df.to_html(index=False, na_rep="–", border=0, classes="bang",
                      float_format=lambda x: f"{x:,.{so_le}f}")


def xuat_html(file_html, symbol, tt5, qd, cac_bang, cac_png):
    anh = ""
    for f in cac_png:
        if os.path.exists(f):
            with open(f, "rb") as fh:
                anh += (f'<figure><img src="data:image/png;base64,{base64.b64encode(fh.read()).decode()}"/>'
                        f"<figcaption>{_html.escape(os.path.basename(f))}</figcaption></figure>")
    kt = "".join(f"<li>{'✔' if ok else ('–' if ok is None else '✘')} {_html.escape(t)}</li>"
                 for t, ok in qd["kiem_tra"])
    bang = "".join(f"<h3>{_html.escape(t)}</h3>{_bang_html(b)}" for t, b in cac_bang)
    van_ban = _html.escape("".join(BAO_CAO_TEXT))
    noi_dung = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{symbol} – phân tích kỹ thuật</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0 auto;max-width:1200px;padding:16px;color:#222}}
.tt{{border:2px solid {qd['mau']};border-radius:8px;padding:12px 18px;background:#fafafa}}
.kn{{display:inline-block;background:{qd['mau']};color:#fff;padding:4px 12px;border-radius:4px;font-weight:700}}
.bang{{border-collapse:collapse;font-size:13px;margin:6px 0 18px}} .bang td,.bang th{{border-bottom:1px solid #ddd;padding:4px 8px;text-align:right}}
.bang th{{background:#f0f0f0}} .bang td:first-child,.bang th:first-child{{text-align:left}}
div.cuon{{overflow-x:auto}} img{{max-width:100%}} figure{{margin:12px 0}} figcaption{{font-size:12px;color:#777}}
pre{{background:#f6f6f6;padding:12px;overflow-x:auto;font-size:12px;line-height:1.35}}
</style></head><body>
<h1>{_html.escape(tt5['tieu_de'])}</h1>
<div class="tt"><p><span class="kn">{_html.escape(qd['khuyen_nghi'])}</span></p>
<ol>{''.join(f'<li>{_html.escape(d[3:])}</li>' for d in tt5['dong'])}</ol>
<p><b>Đang nắm giữ:</b> {_html.escape(qd['dang_giu'])}</p><p><b>Kiểm tra điều kiện:</b></p><ul>{kt}</ul></div>
<h2>Bảng chính</h2><div class="cuon">{bang}</div>
<h2>Biểu đồ</h2>{anh}
<h2>Báo cáo đầy đủ</h2><details><summary>Mở báo cáo dạng văn bản</summary><pre>{van_ban}</pre></details>
<p><i>Phân tích kỹ thuật tham khảo, không phải khuyến nghị đầu tư.</i></p></body></html>"""
    with open(file_html, "w", encoding="utf-8") as f:
        f.write(noi_dung)
    in_ra(f"  ✔ Đã xuất HTML: {file_html}")


def xuat_csv(thu_muc, cac_bang):
    os.makedirs(thu_muc, exist_ok=True)
    for ten, b in cac_bang:
        if b is not None and len(b):
            f = os.path.join(thu_muc, re.sub(r"[^\w\-]+", "_", ten).strip("_") + ".csv")
            b.to_csv(f, index=False, encoding="utf-8-sig")
    in_ra(f"  ✔ Đã xuất CSV: {thu_muc}/ ({len(cac_bang)} bảng)")
