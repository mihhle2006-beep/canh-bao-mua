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
    in_ra(f"\n  Đà kỹ thuật hiện tại : {kb['hien_tai']}")
    if kb.get("thong_ke"):
        in_ra(f"  Thống kê {kb.get('n_phien', '')} phiên tới : {kb['thong_ke']}")
    for c in kb.get("canh_bao_kb", []):
        in_ra(f"    ⚠ {c}")
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
    if not kb["dk_du"]:
        in_ra(f"    (2) không đủ mẫu có điều kiện → giữ EV cơ sở {kb['ev_truoc_wf']:+.2f}%")
    elif cfg.CACH_TINH_EV == "than_trong":
        in_ra(f"    (2) min với có điều kiện (thận trọng) → {kb['ev_truoc_wf']:+.2f}%")
    else:
        in_ra(f"    (2) {kb['w_dk']:.2f}×có điều kiện + {1 - kb['w_dk']:.2f}×cơ sở (trọng số theo mẫu hiệu dụng) "
              f"→ {kb['ev_truoc_wf']:+.2f}%")
    lt = kb.get("loi_the_tin_hieu")
    if lt == lt and lt is not None:
        if kb.get("co_tin_hieu"):
            in_ra(f"    → LỢI THẾ CỦA TÍN HIỆU = EV có điều kiện − EV trộn = {lt:+.2f}% "
                  + ("(tín hiệu có giá trị cộng thêm)" if lt > 0 else "(⚠ tín hiệu KHÔNG tốt hơn mua bất kỳ lúc nào)"))
        else:
            in_ra(f"    → Hôm nay KHÔNG có tín hiệu vào lệnh: mua ở trạng thái này lịch sử {lt:+.2f}% so với mua bất kỳ "
                  f"lúc nào")
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
    for ten in ("P/E", "EPS 4 quý (đồng)", "LNST 4 quý (tỷ đồng)", "Tăng trưởng LNST 4 quý so cùng kỳ %", "P/B", "ROE %",
                "Dư nợ margin (tỷ đồng)",
                "Dư nợ margin / VCSH (lần)"):
        if ten in cb:
            v, ng = cb[ten]
            in_ra(f"  {ten:<28}: {fmt(v) if not isinstance(v, str) else v:<12} [{ng}]")
    if cfg.LOC_CO_BAN:
        in_ra("  → Bộ lọc cơ bản ĐANG BẬT: lỗ / LNST giảm sâu → THEO DÕI; ROE thấp / P/E cao → MUA TỪNG PHẦN "
              "(xem mục kiểm tra điều kiện ở Phần C; tắt: LOC_CO_BAN = False).")
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


_TEN_VAO = {"macd": "Tín hiệu MACD ngày", "mua_ngay": "Mua ngay khi đủ điều kiện", "vung": "Chờ về vùng mua + xác nhận"}


def _ten_thoat():
    gh = (f" + gia hạn (≥ {cfg.GIA_HAN_KHI_R:g}R → siết {cfg.SIET_ATR:g}×ATR)" if cfg.GIA_HAN_LENH else "")
    return {"co_dinh": f"Cố định (cắt lỗ / chốt R/R {RR_NGUONG:g})",
            "dong": f"Cắt lỗ động ({cfg.TRAILING_ATR:g}×ATR, hoà vốn ≥ {cfg.HOA_VON_KHI_R:g}R){gh}",
            "tung_phan": f"Chốt {cfg.CHOT_TUNG_PHAN_PCT:g}% ở R/R {RR_NGUONG:g} + cắt lỗ động{gh}",
            "dong_63": f"Cắt lỗ động {cfg.TRAILING_ATR:g}×ATR, hết hạn cứng (cách cũ)"}


def _loi_the(b):
    return bool(b.get("so_lenh")) and b["tb"] > 0 and b["pf"] == b["pf"] and b["pf"] > 1.2


def _dong_so(b):
    return (f"{b['so_lenh']} lệnh | TB/lệnh {b['tb']:+.2f}% | thắng {b['ty_le_thang']:.0f}% | PF {fmt(b['pf'])} | "
            f"tổng {b['tong']:+.1f}% | MDD {b['mdd']:.1f}%")


def ket_luan_backtest(bt, bt0, bt_thoat=None, bt_vm=None, so_lenh_toi_thieu=5):
    """
    KẾT LUẬN Phần I (dùng cho in báo cáo & Excel/HTML): chọn tổ hợp VÀO × THOÁT tốt nhất (TB/lệnh, tối thiểu
    'so_lenh_toi_thieu' lệnh), đánh giá bộ lọc tuần, cách thoát, so với mua & giữ, và câu hành động cụ thể.
    """
    bt_thoat = bt_thoat or {}
    bt_vm = bt_vm or {}
    ten_t = _ten_thoat()
    to_hop = {("macd", "co_dinh"): bt}
    to_hop.update({("macd", k): b for k, b in bt_thoat.items()})
    for k, r in bt_vm.items():
        to_hop[("vung", k)] = r["vung"]
        to_hop[("mua_ngay", k)] = r["mua_ngay"]
    hop_le = {k: b for k, b in to_hop.items() if b.get("so_lenh", 0) >= so_lenh_toi_thieu}
    tot = max(hop_le.items(), key=lambda kv: kv[1]["tb"]) if hop_le else None
    bh = bt["buy_hold"]
    dong = []
    # 1. quy tắc hiện tại
    dong.append(f"Quy tắc MACD hiện tại {'CÓ' if _loi_the(bt) else 'KHÔNG có'} lợi thế: TB/lệnh {bt['tb']:+.2f}%, "
                f"PF {fmt(bt['pf'])}, thắng {bt['ty_le_thang']:.0f}% trên {bt['so_lenh']} lệnh; tổng {bt['tong']:+.1f}% "
                f"so với mua & giữ {bh:+.1f}% → {'tốt hơn' if bt['tong'] > bh else 'kém hơn'} mua & giữ.")
    # 2. bộ lọc tuần
    if bt0.get("so_lenh"):
        chenh = round(bt["tb"] - bt0["tb"], 2)
        tot_hon = chenh > 0
        it_sut = bt["mdd"] > bt0["mdd"]
        danh_gia = ("giữ bộ lọc" if (tot_hon or it_sut) else "bộ lọc không giúp ích trên mã này")
        xu_huong = "tốt lên" if chenh > 0 else ("xấu đi" if chenh < 0 else "không đổi")
        dong.append(f"Bộ lọc MACD tuần: {bt0['so_lenh']} → {bt['so_lenh']} lệnh, TB/lệnh {bt0['tb']:+.2f}% → "
                    f"{bt['tb']:+.2f}% ({xu_huong}), MDD {bt0['mdd']:.1f}% → {bt['mdd']:.1f}% "
                    f"({'giảm sụt giảm' if it_sut else 'sụt giảm sâu hơn'}) → {danh_gia}.")
    # 3. cách thoát (cùng điểm vào MACD)
    thoat = {k: b for (v, k), b in to_hop.items() if v == "macd" and k != "dong_63" and b.get("so_lenh")}
    if len(thoat) > 1:
        kt = max(thoat, key=lambda k: thoat[k]["tb"])
        cai_thien = thoat[kt]["tb"] - bt["tb"]
        if kt == "co_dinh":
            dong.append("Cách thoát: chốt cố định đang tốt nhất – cắt lỗ động không cải thiện kết quả.")
        else:
            dong.append(f"Cách thoát: {ten_t[kt]} tốt nhất – TB/lệnh {bt['tb']:+.2f}% → {thoat[kt]['tb']:+.2f}% "
                        f"({cai_thien:+.2f} điểm %), MDD {thoat[kt]['mdd']:.1f}%"
                        + ("; đủ để quy tắc có lãi." if thoat[kt]["tb"] > 0 else
                           "; giảm lỗ nhưng KHÔNG biến quy tắc thành có lãi → vấn đề nằm ở điểm VÀO."))
    # 3b. gia hạn lệnh (cắt lỗ động: hết hạn cứng → gia hạn khi lãi ≥ xR & siết)
    if cfg.GIA_HAN_LENH and bt_thoat.get("dong", {}).get("so_lenh") and bt_thoat.get("dong_63", {}).get("so_lenh"):
        moi, cu = bt_thoat["dong"], bt_thoat["dong_63"]
        so_gh = int(moi["bang"]["Lý do thoát"].str.contains("gia hạn|tối đa", regex=True).sum())
        dong.append(f"Gia hạn lệnh (lãi ≥ {cfg.GIA_HAN_KHI_R:g}R tới hạn → giữ, siết {cfg.SIET_ATR:g}×ATR): "
                    f"{so_gh} lệnh được giữ quá hạn; TB/lệnh {cu['tb']:+.2f}% → {moi['tb']:+.2f}%, tổng "
                    f"{cu['tong']:+.1f}% → {moi['tong']:+.1f}% → "
                    + ("gia hạn CÓ ÍCH trên mã này." if moi["tong"] > cu["tong"] + 0.05 else
                       "không khác biệt." if abs(moi["tong"] - cu["tong"]) <= 0.05 else
                       "gia hạn KÉM hơn hết hạn cứng trên mã này."))
    # 4. cách vào (cùng cách thoát cố định)
    if bt_vm.get("co_dinh"):
        v, m = bt_vm["co_dinh"]["vung"], bt_vm["co_dinh"]["mua_ngay"]
        ung = [(n, b) for n, b in (("macd", bt), ("mua_ngay", m), ("vung", v)) if b.get("so_lenh")]
        if ung:
            nv = max(ung, key=lambda x: x[1]["tb"])
            dong.append("Cách vào (cùng thoát cố định): " + "; ".join(f"{_TEN_VAO[n]} {b['tb']:+.2f}%/lệnh"
                                                                      for n, b in ung)
                        + f" → tốt nhất: {_TEN_VAO[nv[0]]}."
                        + (f" Chờ điều chỉnh: giá về vùng {fmt(v.get('xs_ve_vung'), 0)}% số lần, "
                           f"đạt +1R trước cắt lỗ {fmt(v.get('xs_1R'), 0)}% số lệnh." if v.get("so_lenh") else ""))
    # 5. hành động
    if tot and _loi_the(tot[1]):
        (vao, th), b = tot
        hd = (f"ÁP DỤNG: {_TEN_VAO[vao]} + {ten_t[th]} ({b['so_lenh']} lệnh, TB/lệnh {b['tb']:+.2f}%, "
              f"PF {fmt(b['pf'])}, thắng {b['ty_le_thang']:.0f}%)"
              + (" – đặt lệnh chờ ở VÙNG MUA (Phần C), chỉ khớp khi có nến xác nhận." if vao == "vung" else ".")
              + (f" Tuy vậy mua & giữ cả giai đoạn ({bh:+.1f}%) vẫn lãi hơn tổng các lệnh ({b['tong']:+.1f}%) – "
                 f"với vị thế dài hạn nên nắm giữ thay vì lướt sóng." if bh > b["tong"] else ""))
    elif tot:
        (vao, th), b = tot
        if bh > 0 and bh > max(x["tong"] for x in hop_le.values()):
            hd = (f"KHÔNG giao dịch ngắn hạn theo tín hiệu kỹ thuật trên mã này: mọi tổ hợp vào/thoát đều thua "
                  f"mua & giữ ({bh:+.1f}%). Nếu muốn sở hữu, quyết định theo định giá cơ bản và giải ngân dần ở vùng "
                  f"mua, thoát bằng cắt lỗ động.")
        else:
            hd = (f"ĐỨNG NGOÀI giao dịch ngắn hạn: chưa tổ hợp vào/thoát nào có lợi thế; ít lỗ nhất là "
                  f"{_TEN_VAO[vao]} + {ten_t[th]} (TB/lệnh {b['tb']:+.2f}%, PF {fmt(b['pf'])}). Chỉ xét mua khi "
                  f"quy tắc này dương trở lại hoặc có lý do cơ bản rõ ràng.")
    else:
        hd = "Chưa có tổ hợp vào/thoát nào đủ số lệnh để so sánh – dựa vào Phần C & định giá cơ bản."
    dong.append(hd)
    return {"dong": dong, "tot": tot, "co_loi_the": bool(tot and _loi_the(tot[1]))}


def in_backtest(bt, bt0, n_giu, bt_thoat=None, bt_vm=None, symbol=""):
    in_ra(f"\n{'#' * 84}\n PHẦN I. BACKTEST QUY TẮC VÀO LỆNH (tuần + ngày, giữ tối đa {n_giu} phiên)\n{'#' * 84}")
    if not bt["so_lenh"]:
        in_ra("  Không có lệnh nào trong lịch sử → chưa đánh giá được quy tắc.")
        return None
    for ten, b in (("Có lọc MACD tuần (quy tắc của công cụ)", bt), ("Không lọc tuần (đối chứng)", bt0)):
        if not b["so_lenh"]:
            in_ra(f"  {ten}: không có lệnh")
            continue
        in_ra(f"  {ten}:")
        in_ra(f"    {b['so_lenh']} lệnh / {b['so_nam']:.1f} năm | thắng {b['ty_le_thang']:.0f}% | "
              f"TB/lệnh {b['tb']:+.2f}% (thắng {fmt(b['tb_thang'], 2, True)}%, thua {fmt(b['tb_thua'], 2, True)}%) | "
              f"PF {fmt(b['pf'])} | tổng {b['tong']:+.1f}% | MDD {b['mdd']:.1f}% | giữ TB {b['giu_tb']:.0f} phiên")
    in_ra(f"  Mua & giữ cùng giai đoạn: {bt['buy_hold']:+.1f}%")
    ten = _ten_thoat()
    if bt_thoat:
        in_ra("  SO SÁNH CÁCH THOÁT LỆNH (cùng điểm vào MACD, có lọc tuần):")
        for k, b in [("co_dinh", bt)] + list(bt_thoat.items()):
            if b.get("so_lenh"):
                in_ra(f"    {ten[k]:<46}: TB/lệnh {b['tb']:+.2f}% | thắng {b['ty_le_thang']:.0f}% | PF {fmt(b['pf'])} | "
                      f"tổng {b['tong']:+.1f}% | MDD {b['mdd']:.1f}% | giữ TB {b['giu_tb']:.0f} phiên")
    if bt_vm:
        in_ra("  SO SÁNH CÁCH VÀO LỆNH (cùng điều kiện MACD tuần > Signal, cùng bộ mô phỏng thoát):")
        for k in ("co_dinh", "dong", "tung_phan"):
            if k not in bt_vm:
                continue
            in_ra(f"    Thoát: {ten[k]}")
            for n, b in (("macd", bt if k == "co_dinh" else (bt_thoat or {}).get(k, {})),
                         ("mua_ngay", bt_vm[k]["mua_ngay"]), ("vung", bt_vm[k]["vung"])):
                in_ra(f"      {_TEN_VAO[n]:<30}: " + (_dong_so(b) if b.get("so_lenh") else "không có lệnh"))
        v = bt_vm.get("co_dinh", {}).get("vung", {})
        if v.get("so_thiet_lap"):
            in_ra(f"    Phễu vùng mua: {v['so_thiet_lap']} lần thiết lập → giá về vùng {v['so_ve_vung']} lần "
                  f"({fmt(v['xs_ve_vung'], 0)}%) → khớp sau xác nhận {v['so_lenh']} lệnh | chạm vùng rồi thủng "
                  f"{v['so_thung_vung']} lần | đạt +1R trước cắt lỗ {fmt(v['xs_1R'], 0)}% số lệnh")
    kl = ket_luan_backtest(bt, bt0, bt_thoat, bt_vm)
    in_ra(f"  {'─' * 80}\n  KẾT LUẬN BACKTEST{(' – ' + symbol) if symbol else ''}")
    for i, d in enumerate(kl["dong"], 1):
        in_ra(f"   {i if i < len(kl['dong']) else '→'}{'.' if i < len(kl['dong']) else ''} {d}")
    in_ra("  Lưu ý: backtest trên chính mã này (đã tính T+2, trần/sàn, phí & trượt giá); chỉ để tham khảo.")
    return kl


def in_lich_su_khuyen_nghi(symbol, nk):
    """[MỚI] PHẦN K – các khuyến nghị ptcp đã đưa ra cho mã này và kết quả thực tế."""
    in_ra(f"\n{'#' * 84}\n PHẦN K. LỊCH SỬ KHUYẾN NGHỊ CỦA {symbol} – ĐÚNG / SAI THEO GIÁ THỰC TẾ\n{'#' * 84}")
    if nk is None:
        in_ra("  Nhật ký đang tắt (GHI_NHAT_KY = False) hoặc lỗi – xem cảnh báo dữ liệu.")
        return
    in_ra(f"  File nhật ký: {nk['path']}" + (" | ✔ đã ghi khuyến nghị hôm nay" if nk["moi"]
                                              else " | khuyến nghị không đổi so với lần ghi trước → không ghi thêm"))
    if "/content/" in nk["path"] and "/drive/" not in nk["path"]:
        in_ra("  ⚠ Đang lưu trong Colab (mất khi tắt máy) – mount Google Drive để giữ lịch sử: "
              "from google.colab import drive; drive.mount('/content/drive')")
    b = nk["bang"]
    if len(b) <= 1 and not (b["ket_qua"].isin(["ĐÚNG", "SAI"])).any():
        in_ra("  Chưa có khuyến nghị nào có kết luận ĐÚNG/SAI – lịch sử tích luỹ qua các lần chạy sau "
              "(khuyến nghị MUA cần tới khi chạm mục tiêu / cắt lỗ hoặc hết hạn).")
    for _, r in b.tail(12).iterrows():
        pct = f"{r['ket_qua_pct']:+.1f}%" if r["ket_qua_pct"] == r["ket_qua_pct"] else ""
        in_ra(f"  {r['ngay']}  {str(r['khuyen_nghi'])[:24]:<24} giá {r['gia']:>8,.2f} → {r['ket_qua'] or 'ĐANG CHỜ':<9}"
              f" {pct:>7}  {r['giai_thich']}")
    for _, r in nk["tk"].iterrows():
        if r["Đã chấm"]:
            nhan = "TB lệnh" if r["Nhóm"].endswith("MUA") else "TB nếu đã mua"
            in_ra(f"  ► {r['Nhóm']}: đúng {r['Đúng']}/{r['Đã chấm']} ({r['Tỷ lệ đúng %']:.0f}%), {nhan} {r['TB kết quả %']:+.2f}%"
                  + (" ⚠ ít mẫu" if r["Đã chấm"] < cfg.SO_MAU_TIN_CAY else ""))
    tk = nk["tk_tat_ca"]
    if len(tk) and tk["Đã chấm"].sum():
        mua = tk[tk["Nhóm"] == "ptcp MUA"]
        if len(mua) and mua["Đã chấm"].iloc[0]:
            r = mua.iloc[0]
            in_ra(f"  ► Toàn bộ nhật ký (mọi mã) – ptcp MUA: đúng {r['Đúng']}/{r['Đã chấm']} ({r['Tỷ lệ đúng %']:.0f}%), "
                  f"TB {r['TB kết quả %']:+.2f}%")
    in_ra("  Cách chấm: MUA = lệnh mua giả định giá mở cửa phiên sau với cắt lỗ / mục tiêu ngắn hạn của khuyến nghị "
          "(T+2, trần/sàn, phí); CHỜ / ĐỨNG NGOÀI đúng khi lệnh mua đó lẽ ra bị lỗ.")


# ==========================================================================
# 10H. [MỚI] TÓM TẮT 5 DÒNG & XUẤT HTML / CSV
# ==========================================================================
def lap_tom_tat(symbol, ht, ngay, qd, stop, kb, qr, dx, df_ngay, kq, vm=None, bt_vm=None):
    v_ls = (bt_vm or {}).get("vung", {})
    if not qd["mua"] and vm and vm["tuan_ok"]:
        vung = (f"{vm['lo']:,.2f} – {vm['hi']:,.2f} (vùng điều chỉnh, {vm['so_loai']} hỗ trợ trùng nhau) – "
                f"{vm['trang_thai'].split(' →')[0].lower()}; mua khi có nến xác nhận, cắt lỗ {vm['stop']:,.2f}"
                + (f" | lịch sử: về vùng {fmt(v_ls['xs_ve_vung'], 0)}%, đạt +1R {fmt(v_ls['xs_1R'], 0)}% "
                   f"({v_ls['so_lenh']} lệnh)" if v_ls.get("so_lenh") else ""))
    elif qd["mua"]:
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


def in_vung_mua(vm, bt_vm=None):
    """[MỚI] Phần C – vùng mua điều chỉnh cho mã CHƯA nắm giữ (chờ giá về vùng + nến xác nhận)."""
    in_ra(f"  ◆ VÙNG MUA ĐIỀU CHỈNH (chưa nắm giữ): {vm['lo']:,.2f} – {vm['hi']:,.2f} "
          f"({(vm['lo'] / vm['gia'] - 1) * 100:+.1f}% → {(vm['hi'] / vm['gia'] - 1) * 100:+.1f}% so với giá)")
    in_ra("     Hỗ trợ trùng nhau: " + " · ".join(f"{t} {p:,.2f}" for t, p in vm["muc"]))
    in_ra(f"     Trạng thái: {vm['trang_thai']}")
    if not vm["tuan_ok"]:
        in_ra("     ⚠ MACD tuần ≤ Signal → vùng chỉ để THEO DÕI, chưa đặt lệnh (quyền phủ quyết khung tuần).")
    in_ra(f"     Điều kiện mua: giá chạm vùng rồi có nến đóng cửa > đỉnh phiên trước (nến tăng); mua giá mở cửa phiên sau, "
          f"bỏ lệnh nếu mở cửa > {vm['hi'] + vm['atr']:,.2f} (không đuổi giá).")
    in_ra(f"     Vô hiệu khi đóng cửa < {vm['lo'] - 0.5 * vm['atr']:,.2f} | Cắt lỗ (lệnh mua ở vùng) {vm['stop']:,.2f} | Mục tiêu "
          f"{vm['muc_tieu']:,.2f} (đỉnh nhịp) → R/R giữa vùng {fmt(vm['rr'])}"
          + ("" if vm["rr"] == vm["rr"] and vm["rr"] >= RR_NGUONG else f" (< {RR_NGUONG:g}: chỉ mua ở cận dưới)"))
    v = (bt_vm or {}).get("vung", {})
    if v.get("so_thiet_lap"):
        in_ra(f"     Lịch sử mã (cùng quy tắc, thoát cố định): {v['so_thiet_lap']} lần thiết lập → về vùng "
              f"{fmt(v['xs_ve_vung'], 0)}% → {v['so_lenh']} lệnh khớp | đạt +1R trước cắt lỗ {fmt(v['xs_1R'], 0)}%"
              + (f" | TB/lệnh {v['tb']:+.2f}%, PF {fmt(v['pf'])}" if v.get("so_lenh") else "")
              + " – xem so sánh cách vào lệnh ở Phần I.")


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
    from .so import la_cot_ty_le, so4, vn_hoa
    if df is None or not len(df):
        return "<p><i>(không có dữ liệu)</i></p>"
    d = df.reset_index(drop=True)
    so = {c: pd.api.types.is_numeric_dtype(d[c]) and not pd.api.types.is_bool_dtype(d[c]) for c in d.columns}

    def o(c, v):
        if v is None or (isinstance(v, float) and v != v) or v is pd.NaT:
            return "–"
        if isinstance(v, float):
            return so4(v) if la_cot_ty_le(c) else f"{v:,.{so_le}f}"
        if isinstance(v, pd.Timestamp):
            return f"{v:%d/%m/%Y}"
        return str(v)
    dau = "".join(f"<th{' class=so' if so[c] else ''}>{_html.escape(str(c))}</th>" for c in d.columns)
    than = "".join("<tr>" + "".join(f"<td{' class=so' if so[c] else ''}>{_html.escape(o(c, v))}</td>"
                                    for c, v in r.items()) + "</tr>" for _, r in d.iterrows())
    return vn_hoa(f'<table class="bang"><tr>{dau}</tr>{than}</table>')


def xuat_html(file_html, symbol, tt5, qd, cac_bang, cac_png, the=None, fj=None, anh_tom_tat=None):
    """Báo cáo HTML dạng DASHBOARD – tông xanh lá: thẻ số liệu, mục lục, ảnh tóm tắt, bảng, Phần J, biểu đồ."""
    from .so import vn_hoa
    e = lambda x: _html.escape(vn_hoa(str(x)))

    def anh_b64(f):
        if not f or not os.path.exists(f):
            return ""
        with open(f, "rb") as fh:
            return (f'<figure><img src="data:image/png;base64,{base64.b64encode(fh.read()).decode()}"/>'
                    f"<figcaption>{_html.escape(os.path.basename(f))}</figcaption></figure>")

    the_html = "".join(f'<div class="o"><div class="nhan">{e(n)}</div><div class="so" style="color:{m}">{e(v)}</div></div>'
                       for n, v, m in (the or []))
    kt = "".join(f"<li>{'✔' if ok else ('–' if ok is None else '✘')} {e(t)}</li>" for t, ok in qd["kiem_tra"])
    TEN = {"Muc tieu (3 moc moi khung)": "Mục tiêu (3 mốc mỗi khung)", "Kich ban chinh": "Kịch bản chính",
           "Quan tri rui ro": "Quản trị rủi ro", "Bien do thong ke": "Biên độ thống kê",
           "Boi canh thi truong": "Bối cảnh thị trường", "Phan loai phien": "Phân loại phiên",
           "Bien dong theo khung": "Biến động theo khung", "Backtest": "Kiểm định lịch sử (backtest)",
           "Lich su khuyen nghi": "Lịch sử khuyến nghị (đúng / sai)"}
    cac_bang = [(TEN.get(t, t), b) for t, b in cac_bang if t != "Tom tat"]      # tóm tắt đã có ở trên
    muc = [("tom-tat", "Tóm tắt")] + [(f"b{k}", t) for k, (t, _) in enumerate(cac_bang)]
    phan_j = ""
    if fj:
        for ma_, ten in (("J1", "J1. Tổng quan"), ("J2", "J2. Tài chính – BCTC theo năm"), ("J3", "J3. Kỹ thuật"),
                         ("J4", "J4. Biến động giá (%)"), ("J5", "J5. Phân tích tài chính 10 tiêu chí")):
            df = fj.get(ma_)
            if df is None:
                continue
            muc.append((ma_, ten))
            bang = _bang_html(df)
            if ma_ == "J5":
                for nhan, lop in (("Rất tốt", "f5"), ("Tốt", "f4"), ("Trung bình", "f3"), ("Cảnh báo", "f2"),
                                  ("Nguy hiểm", "f1")):
                    bang = bang.replace(f"<td>{nhan}</td>", f'<td class="{lop}">{nhan}</td>')
            if ma_ == "J4":                                           # % tăng xanh, giảm đỏ
                import re as _re
                bang = _re.sub(r"<td class=so>(-[\d.,]+)</td>", r'<td class=so style="color:#C62828">\1</td>', bang)
                bang = _re.sub(r"<td class=so>(\d[\d.,]*)</td>", r'<td class=so style="color:#2E7D32">\1</td>', bang)
            phan_j += f'<h2 id="{ma_}">{e(ten)}</h2><div class="cuon">{bang}</div>'
    if fj and fj.get("ket_luan"):
        kl = fj["ket_luan"]
        mau_kl = {"TÍCH CỰC": "#2E7D32", "TIÊU CỰC": "#C62828"}.get(kl["nhan"], "#F9A825")
        dong_y = "".join(f'<li><b>{e(n)}</b>: <span style="color:{"#2E7D32" if s_ > 0 else "#C62828" if s_ < 0 else "#555"}">'
                         f'{"▲" if s_ > 0 else "▼" if s_ < 0 else "•"} {e(t)}</span></li>' for n, t, s_ in kl["y"])
        dong_y += "".join(f"<li><b>Biến động</b>: {e(d)}</li>" for d in kl["bien_dong"])
        muc.append(("J-ket-luan", "Kết luận Phần J"))
        phan_j += (f'<h2 id="J-ket-luan">Kết luận chung Phần J</h2><div class="the-kl" style="border-left:6px solid '
                   f'{mau_kl};background:#fff;border-radius:10px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,.08)">'
                   f'<div style="font-size:22px;font-weight:700;color:{mau_kl}">{e(kl["nhan"])} '
                   f'<span style="font-size:14px;color:#555">(điểm {kl["diem"]:+d})</span></div><ul>{dong_y}</ul>'
                   f'<p><b>Điểm mạnh:</b> {e("; ".join(kl["manh"]) or "không có điểm nổi bật")}</p>'
                   f'<p><b>Điểm yếu:</b> {e("; ".join(kl["yeu"]) or "không có điểm yếu đáng kể")}</p>'
                   + (f'<p>➜ <b>{e(kl["goi_y"])}</b></p>' if kl.get("goi_y") else "")
                   + '<p style="color:#777;font-size:12px">Kết luận Phần J mô tả chất lượng doanh nghiệp &amp; '
                     'trạng thái cổ phiếu; khuyến nghị giao dịch vẫn theo Phần C.</p></div>')
    muc += [("bieu-do", "Biểu đồ"), ("day-du", "Báo cáo đầy đủ")]
    bang_html = "".join(f'<h2 id="b{k}">{e(t)}</h2><div class="cuon">{_bang_html(b)}</div>'
                        for k, (t, b) in enumerate(cac_bang))
    nav = "".join(f'<a href="#{a}">{e(t)}</a>' for a, t in muc)
    van_ban = _html.escape("".join(BAO_CAO_TEXT))
    noi_dung = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{symbol} – phân tích cổ phiếu</title>
<style>
*{{box-sizing:border-box}} body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;color:#1f2d1f;background:#f6faf6}}
header{{background:linear-gradient(120deg,#1B5E20,#2E7D32);color:#fff;padding:22px 24px}} header h1{{margin:0;font-size:24px}}
nav{{position:sticky;top:0;background:#fff;border-bottom:2px solid #C8E6C9;padding:8px 16px;z-index:5;overflow-x:auto;white-space:nowrap}}
nav a{{color:#1B5E20;text-decoration:none;margin-right:16px;font-weight:600}}
main{{max-width:1250px;margin:0 auto;padding:16px}} h2{{color:#1B5E20;border-bottom:3px solid #2E7D32;padding-bottom:4px;margin-top:34px}}
.the{{display:flex;flex-wrap:wrap;gap:12px;margin-top:6px}} .o{{flex:1 1 170px;background:#fff;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.08);border-top:4px solid #2E7D32}}
.o .nhan{{font-size:12px;color:#666}} .o .so{{font-size:20px;font-weight:700;margin-top:4px}}
.tt{{background:#fff;border-left:6px solid {qd['mau']};border-radius:10px;padding:12px 18px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.kn{{display:inline-block;background:{qd['mau']};color:#fff;padding:4px 12px;border-radius:14px;font-weight:700}}
.cuon{{overflow-x:auto;background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin:8px 0 16px}}
.bang{{border-collapse:collapse;font-size:13px;width:100%}} .bang th{{background:#1B5E20;color:#fff;padding:7px 9px;text-align:left}}
.bang td{{padding:6px 9px;border-bottom:1px solid #E8F5E9;text-align:left;vertical-align:top}} .bang .so{{text-align:right;white-space:nowrap}}
.bang tr:nth-child(even) td{{background:#F1F8E9}} .bang td:first-child{{font-weight:600}}
td.f5{{background:#4A90E2!important;color:#fff}} td.f4{{background:#66BB6A!important;color:#fff}} td.f3{{background:#FFEE58!important}}
td.f2{{background:#FFA726!important}} td.f1{{background:#EF5350!important;color:#fff}}
img{{max-width:100%;border-radius:8px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.08)}} figure{{margin:12px 0}}
figcaption{{font-size:12px;color:#777}} summary{{color:#2E7D32;font-weight:600;cursor:pointer}}
pre{{background:#F1F8E9;padding:12px;overflow-x:auto;font-size:12px;line-height:1.35}}
footer{{color:#777;font-size:12px;text-align:center;padding:24px}}
</style></head><body>
<header><h1>{e(tt5['tieu_de'])}</h1></header>
<nav>{nav}</nav><main>
<div class="the">{the_html}</div>
<h2 id="tom-tat">Tóm tắt</h2>{anh_b64(anh_tom_tat)}
<div class="tt"><p><span class="kn">{e(qd['khuyen_nghi'])}</span></p>
<ol>{''.join(f'<li>{e(d[3:])}</li>' for d in tt5['dong'])}</ol>
<p><b>Đang nắm giữ:</b> {e(qd['dang_giu'])}</p><p><b>Kiểm tra điều kiện:</b></p><ul>{kt}</ul></div>
{bang_html}{phan_j}
<h2 id="bieu-do">Biểu đồ</h2>{''.join(anh_b64(f) for f in cac_png)}
<h2 id="day-du">Báo cáo đầy đủ</h2><details><summary>Mở báo cáo dạng văn bản</summary><pre>{van_ban}</pre></details>
</main><footer>Công cụ tham khảo dựa trên dữ liệu quá khứ – không phải khuyến nghị đầu tư.</footer></body></html>"""
    with open(file_html, "w", encoding="utf-8") as f:
        f.write(noi_dung)
    in_ra(f"  ✔ Đã lưu báo cáo HTML: {file_html}")


def xuat_csv(thu_muc, cac_bang):
    os.makedirs(thu_muc, exist_ok=True)
    for ten, b in cac_bang:
        if b is not None and len(b):
            f = os.path.join(thu_muc, re.sub(r"[^\w\-]+", "_", ten).strip("_") + ".csv")
            b.to_csv(f, index=False, encoding="utf-8-sig")
    in_ra(f"  ✔ Đã xuất CSV: {thu_muc}/ ({len(cac_bang)} bảng)")
