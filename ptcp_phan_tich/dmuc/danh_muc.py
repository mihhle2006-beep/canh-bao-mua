# -*- coding: utf-8 -*-
"""
CẤP DANH MỤC: đọc danh mục / nhật ký giao dịch, cắt lỗ & mục tiêu ĐÃ ĐẶT, hành động, số lượng mua, rủi ro.
Sửa so với bản 1 file:
  • Cắt lỗ / mục tiêu của mã ĐANG GIỮ được NEO từ lúc mua (lưu file trạng thái), chỉ dời LÊN, không dời xuống.
    Bản cũ tính lại từ giá hiện tại mỗi lần chạy → luôn nằm dưới giá → "CẮT LỖ"/"CHỐT LỜI" không bao giờ xảy ra.
  • Tiền mặt nằm trong mọi chỉ tiêu (tỷ trọng, beta, upside, rủi ro, VaR) – bản cũ tính trên riêng phần cổ phiếu.
  • Cho phép lô lẻ khi vốn nhỏ (bản cũ làm tròn xuống lô 100 → với NAV ~11 triệu luôn gợi ý 0 CP).
  • Tổng rủi ro mở (mọi mã cùng chạm cắt lỗ) có trần; phân bổ tiền mặt theo thứ tự ưu tiên EV khi thiếu tiền.
  • Tương quan theo lợi suất TUẦN; cảnh báo tập trung kiểm tra độc lập với số mã.
  • Stress test theo beta & giai đoạn xấu nhất lịch sử, CVaR, số phiên cần để thoát vị thế.
"""
import json
import os
import re

import numpy as np
import pandas as pd

from .cau_hinh import (CHO_PHEP_LO_LE, CU_SOC_STRESS, HE_SO_THI_TRUONG_XAU, LO_CHAN, LO_TOI_DA_GIA_VON,
                       NGUONG_TUONG_QUAN, RUI_RO_MOI_LENH, TONG_RUI_RO_MO_TOI_DA, TY_LE_THANH_KHOAN, TY_TRONG_TOI_DA)
from ptcp.thong_ke import _chi_phi as chi_phi
from .so_sanh import so_sanh_theo_ky, so_sanh_tu_ngay_mua, nhan_xet
from .tien_ich import co, doc_so, loi_suat_tuan

COT_DANH_MUC = {
    "ma": ["ma", "mã", "mã cp", "symbol", "ticker"], "so_cp": ["so_cp", "số cp", "số lượng", "khối lượng", "sl"],
    "gia_von": ["gia_von", "giá vốn"], "gia_muc_tieu": ["gia_muc_tieu", "giá mục tiêu", "mục tiêu"],
    "cat_lo_dat": ["cat_lo_dat", "cắt lỗ", "cat_lo"], "muc_tieu_dat": ["muc_tieu_dat"],
    "ngay_mua": ["ngay_mua", "ngày mua"], "nhom_nganh": ["nhom_nganh", "nhóm ngành", "cùng ngành"],
    "kl_phat_hanh": ["kl_phat_hanh", "kl phát hành"], "kl_niem_yet": ["kl_niem_yet", "kl niêm yết"],
    "cp_quy": ["cp_quy", "cổ phiếu quỹ"], "so_huu_nn": ["so_huu_nn", "sở hữu nn", "sở hữu nước ngoài"],
    "beta": ["beta"], "san": ["san", "sàn"], "csv_ngay": ["csv_ngay", "file ngày"], "csv_gio": ["csv_gio", "file giờ"],
}


def tao_file_mau(path="danh_muc_mau.csv"):
    pd.DataFrame([["MA1", "1000", "25.5", "", "", "15/03/2026", ""], ["MA2", "", "", "", "", "", ""]],
                 columns=["ma", "so_cp", "gia_von", "gia_muc_tieu", "cat_lo_dat", "ngay_mua", "nhom_nganh"]
                 ).to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  ✔ Đã tạo file mẫu: {os.path.abspath(path)} – thay MA1, MA2 bằng mã của bạn (giá theo NGHÌN ĐỒNG; "
          f"mã chưa mua: để trống so_cp, gia_von)")


def doc_danh_muc(path=None, text=None):
    """Đọc danh mục từ file CSV/Excel hoặc chuỗi DANH_MUC. Số kiểu Việt Nam ('1.234,5') được hỗ trợ."""
    import io
    if text is not None:
        dong = [d.strip() for d in text.strip().splitlines() if d.strip() and not d.strip().startswith("#")]
        df, goc = pd.read_csv(io.StringIO("\n".join(dong)), dtype=str), os.getcwd()
    else:
        df = pd.read_excel(path, dtype=str) if path.lower().endswith((".xlsx", ".xls")) else pd.read_csv(path, dtype=str)
        goc = os.path.dirname(os.path.abspath(path))
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={c: k for k, ten in COT_DANH_MUC.items() for c in df.columns if c in ten})
    if "ma" not in df:
        raise SystemExit("Danh mục phải có cột 'ma'.")
    ds = []
    for _, r in df.iterrows():
        ma = str(r["ma"]).strip().upper()
        if not ma or ma == "NAN":
            continue
        g = lambda k: r[k] if k in r and str(r[k]).strip() not in ("", "nan", "None") else None
        ds.append({"ma": ma, "so_cp": doc_so(g("so_cp"), True) or 0, "gia_von": doc_so(g("gia_von")),
                   "mt_nhap": doc_so(g("gia_muc_tieu")), "cat_lo_dat": doc_so(g("cat_lo_dat")),
                   "muc_tieu_dat": doc_so(g("muc_tieu_dat")), "kl_ph": doc_so(g("kl_phat_hanh"), True),
                   "ngay_mua": pd.to_datetime(g("ngay_mua"), dayfirst=True, errors="coerce") if g("ngay_mua") else None,
                   "nhom_nganh": ",".join(x.strip().upper() for x in re.split(r"[;,\s]+", g("nhom_nganh")) if x.strip())
                   if g("nhom_nganh") else None,
                   "kl_ny": doc_so(g("kl_niem_yet"), True), "cp_quy": doc_so(g("cp_quy"), True) or 0,
                   "so_huu_nn": doc_so(g("so_huu_nn")), "beta_nhap": doc_so(g("beta")), "san": g("san"),
                   "csv_ngay": os.path.join(goc, g("csv_ngay")) if g("csv_ngay") else None,
                   "csv_gio": os.path.join(goc, g("csv_gio")) if g("csv_gio") else None})
    return ds


# ==========================================================================
# NHẬT KÝ GIAO DỊCH
# ==========================================================================
def doc_nhat_ky(path):
    """
    CSV cột: ngay,ma,loai,so_cp,gia,phi   (giá NGHÌN ĐỒNG, phí ĐỒNG)
      loai = mua | ban | co_tuc_tien (gia = cổ tức tiền mặt/CP, nghìn đ) | co_tuc_cp (so_cp = số CP nhận thêm)
    Giá vốn bình quân gia quyền (đã gồm phí mua); cổ tức cổ phiếu tăng số CP → giảm giá vốn/CP.
    Trả {mã: {so_cp, gia_von, lai_da_thuc_hien (đ), co_tuc (đ), phi (đ)}}.
    """
    nk = pd.read_csv(path, dtype=str)
    nk.columns = [c.strip().lower() for c in nk.columns]
    nk["ngay"] = pd.to_datetime(nk["ngay"], dayfirst=True)
    nk = nk.sort_values("ngay", kind="stable")
    vt = {}
    for _, r in nk.iterrows():
        ma, loai = str(r["ma"]).strip().upper(), str(r["loai"]).strip().lower()
        sl, gia, phi = doc_so(r.get("so_cp"), True) or 0, doc_so(r.get("gia")) or 0, doc_so(r.get("phi"), True) or 0
        v = vt.setdefault(ma, {"so_cp": 0.0, "von": 0.0, "lai_da_thuc_hien": 0.0, "co_tuc": 0.0, "phi": 0.0,
                               "dong_tien": []})
        v["phi"] += phi
        v["dong_tien"].append((r["ngay"], loai, sl, gia, phi))      # để so sánh với VN-Index cùng dòng tiền
        if loai == "mua":
            if v["so_cp"] <= 1e-9:
                v["ngay_mua_dau"] = r["ngay"]                       # ngày mua đầu tiên của vị thế hiện tại
            v["von"] += sl * gia * 1000 + phi
            v["so_cp"] += sl
        elif loai == "ban":
            if sl > v["so_cp"] + 1e-9:
                raise SystemExit(f"Nhật ký: bán {sl:g} {ma} ngày {r['ngay']:%d/%m/%Y} nhiều hơn số đang có "
                                 f"({v['so_cp']:g})")
            gv = v["von"] / v["so_cp"] if v["so_cp"] else 0
            v["lai_da_thuc_hien"] += sl * gia * 1000 - phi - sl * gv
            v["von"] -= sl * gv
            v["so_cp"] -= sl
            if v["so_cp"] <= 1e-9:
                v["ngay_mua_dau"] = None                            # bán hết → vị thế sau tính lại từ đầu
        elif loai == "co_tuc_tien":
            v["co_tuc"] += v["so_cp"] * gia * 1000
        elif loai == "co_tuc_cp":
            v["so_cp"] += sl
        else:
            raise SystemExit(f"Nhật ký: loại giao dịch không hợp lệ '{loai}' (mua/ban/co_tuc_tien/co_tuc_cp)")
    for v in vt.values():
        v["gia_von"] = v["von"] / v["so_cp"] / 1000 if v["so_cp"] > 0 else None
    return vt


def gop_nhat_ky(ds, vt):
    """Số CP & giá vốn lấy từ nhật ký; mã có trong nhật ký mà chưa có trong danh mục được thêm vào."""
    co_san = {d["ma"]: d for d in ds}
    for ma, v in vt.items():
        d = co_san.get(ma)
        if d is None:
            if v["so_cp"] <= 0:
                continue
            d = {"ma": ma, "cp_quy": 0}
            ds.append(d)
        d.update(so_cp=v["so_cp"], gia_von=v["gia_von"], lai_da_thuc_hien=v["lai_da_thuc_hien"], co_tuc=v["co_tuc"],
                 dong_tien=v["dong_tien"])
        if v.get("ngay_mua_dau") is not None:
            d.update(ngay_mua=v["ngay_mua_dau"], nguon_ngay_mua="nhật ký")
    return ds


# ==========================================================================
# CẮT LỖ & MỤC TIÊU ĐÃ ĐẶT (neo từ lúc mua, chỉ dời lên)
# ==========================================================================
def doc_trang_thai(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ghi_trang_thai(path, tt):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tt, f, ensure_ascii=False, indent=1)


def cap_nhat_muc_dat(r, ts, cu):
    """
    r: kết quả phân tích mã ĐANG GIỮ; ts: dòng danh mục (cat_lo_dat / muc_tieu_dat tự nhập ưu tiên);
    cu: trạng thái đã lưu của mã (hoặc None). Trả (thông tin dùng để đánh giá, trạng thái mới).
      • Vị thế mới / đổi số CP hoặc giá vốn → đặt cắt lỗ & mục tiêu theo phân tích hiện tại
      • Ngược lại: so giá với mức ĐÃ ĐẶT TRƯỚC ĐÓ (phát hiện chạm), rồi dời cắt lỗ LÊN nếu mức mới cao hơn
    """
    ht, so_cp, gv = r["ht"], r["so_cp"], r["gia_von"] or r["ht"]
    moi = cu is None or abs(cu.get("so_cp", 0) - so_cp) > 1e-9 or abs(cu.get("gia_von", 0) / gv - 1) > 0.005
    cl_cu = ts.get("cat_lo_dat") or (None if moi else cu.get("cat_lo"))
    mt_cu = ts.get("muc_tieu_dat") or (None if moi else cu.get("muc_tieu"))
    kh = r.get("kh") or {}
    # Vị thế mới: cắt lỗ/mục tiêu đặt TỪ GIÁ MUA (cắt lỗ gốc tại ngày mua, mục tiêu ≥ 2R) nếu có kế hoạch ptcp
    cl_cu = cl_cu if cl_cu else (kh.get("cat_lo_hien_tai") or kh.get("cat_lo_goc") or r["cat_lo"])
    mt_cu = mt_cu if mt_cu else (r["mt_nhap"] or kh.get("muc_tieu_hieu_luc") or r["mt_ngay"])
    cham_cl = ht <= cl_cu
    cham_mt = ht >= mt_cu
    cl_moi = cl_cu if cham_cl else max(cl_cu, r["cat_lo"])
    mt_moi = (r["mt_ngay"] if r["mt_ngay"] > ht else mt_cu) if cham_mt else mt_cu
    hom_nay = pd.Timestamp.today().strftime("%Y-%m-%d")
    nm = ts.get("ngay_mua")
    nm = pd.Timestamp(nm).strftime("%Y-%m-%d") if nm is not None and not pd.isna(nm) else None
    ngay_mua = nm or (hom_nay if moi else cu.get("ngay_mua") or cu.get("ngay_dat"))
    cl0 = kh.get("cat_lo_goc") or (cl_cu if moi else (cu.get("cat_lo_ban_dau") or cl_cu))   # cắt lỗ LÚC MUA → 1R
    info = {"cat_lo_dat": cl_cu, "muc_tieu_dat": mt_cu, "cham_cl": cham_cl, "cham_mt": cham_mt,
            "cat_lo_moi": cl_moi, "muc_tieu_moi": mt_moi, "doi_len": cl_moi > cl_cu + 1e-9, "vi_the_moi": moi,
            "cat_lo_ban_dau": cl0, "ngay_mua": ngay_mua,
            "nguon_ngay_mua": ts.get("nguon_ngay_mua") or ("danh mục" if nm else "ngày đầu thấy vị thế")}
    trang_thai = {"so_cp": so_cp, "gia_von": gv, "cat_lo": cl_moi, "muc_tieu": mt_moi, "cat_lo_ban_dau": cl0,
                  "ngay_mua": ngay_mua, "ngay_dat": hom_nay if moi else cu.get("ngay_dat")}
    return info, trang_thai


# ==========================================================================
# HÀNH ĐỘNG & SỐ LƯỢNG
# ==========================================================================
MUA_DUOC = ("MUA", "MUA TỪNG PHẦN")


def goi_y_hanh_dong(r, md, ty_trong, con_rui_ro):
    """Mã ĐANG GIỮ. md = kết quả cap_nhat_muc_dat."""
    ht = r["ht"]
    ll = (ht / r["gia_von"] - 1) * 100 if r["gia_von"] else 0
    if r["du_lieu_cu"]:
        return "KIỂM TRA DỮ LIỆU – phiên cuối đã cũ (tạm ngừng giao dịch?)"
    if md["cham_cl"]:
        return f"CẮT LỖ – giá {ht:,.2f} ≤ cắt lỗ đã đặt {md['cat_lo_dat']:,.2f}"
    if ll <= -LO_TOI_DA_GIA_VON and not r["tg"]["tuan_ok"]:
        return f"XEM XÉT CẮT LỖ – lỗ {abs(ll):.1f}% so giá vốn, khung tuần không ủng hộ"
    if md["cham_mt"]:
        return f"CHỐT LỜI MỘT PHẦN – đạt mục tiêu đã đặt {md['muc_tieu_dat']:,.2f}; cắt lỗ dời lên {md['cat_lo_moi']:,.2f}"
    if co(r["upside_dg"]) and r["upside_dg"] < -5:
        return "GIẢM TỶ TRỌNG – giá đã vượt giá trị định giá tự nhập"
    if not r["tg"]["tuan_ok"] and "GIẢM" in str(r["cau_truc_tuan"]):
        return "GIẢM TỶ TRỌNG – xu hướng tuần giảm"
    them = f" | cắt lỗ dời lên {md['cat_lo_moi']:,.2f}" if md["doi_len"] else ""
    if r["quyet_dinh"] in MUA_DUOC:
        if ty_trong >= TY_TRONG_TOI_DA:
            return "NẮM GIỮ – tín hiệu tốt nhưng tỷ trọng đã chạm trần" + them
        if con_rui_ro <= 0:
            return "NẮM GIỮ – tổng rủi ro mở đã chạm trần" + them
        return "MUA THÊM – đủ điều kiện kỹ thuật & EV" + them
    return "NẮM GIỮ" + them


def goi_y_ma_theo_doi(r, tt_xau):
    qd = r["quyet_dinh"]
    if r["du_lieu_cu"]:
        return "KIỂM TRA DỮ LIỆU – phiên cuối đã cũ"
    if qd == "MUA":
        return "MUA TỪNG PHẦN – tín hiệu đủ nhưng VN-Index xấu" if tt_xau else "MUA MỚI – đủ điều kiện"
    if qd == "MUA TỪNG PHẦN":
        return "MUA TỪNG PHẦN – " + r["qd"]["ly_do"]
    if qd == "CHỜ GIÁ TỐT HƠN":
        return f"CHỜ GIÁ ≤ {r['qd']['gia_mua_max']:,.2f} (để R/R ≥ 2)"
    return f"{qd} – {r['qd']['ly_do']}"


def so_luong_goi_y(r, tong_ts, tien_con, rui_ro_con, he_so=1.0, gia_tri_dang_giu=0.0):
    """
    Số CP = min( rủi ro cho phép ÷ rủi ro/CP ; trần tỷ trọng còn lại ÷ giá ; tiền mặt còn ÷ giá )
      rủi ro cho phép = min(RUI_RO_MOI_LENH% × tổng tài sản × hệ số thị trường ; rủi ro mở còn lại)
      rủi ro/CP = (giá − cắt lỗ) + chi phí khứ hồi
    ≥ 100 CP → làm tròn lô chẵn; < 100 → lô lẻ (nếu CHO_PHEP_LO_LE). Trả (số CP, ghi chú).
    """
    gia_d = r["ht"] * 1000
    if r["cat_lo"] >= r["ht"] or tong_ts <= 0:
        return 0, "cắt lỗ ≥ giá"
    rui_ro_cp = (r["ht"] - r["cat_lo"]) * 1000 + gia_d * chi_phi() / 100
    gioi_han = {"rủi ro/lệnh": min(RUI_RO_MOI_LENH / 100 * tong_ts * he_so, rui_ro_con) / rui_ro_cp,
                "trần tỷ trọng": max(0.0, TY_TRONG_TOI_DA / 100 * tong_ts - gia_tri_dang_giu) / gia_d,
                "tiền giải ngân (sau mức giữ)": tien_con / (gia_d * (1 + chi_phi() / 200))}
    rang_buoc = min(gioi_han, key=gioi_han.get)
    n = int(max(0.0, gioi_han[rang_buoc]))
    if n >= LO_CHAN:
        return n // LO_CHAN * LO_CHAN, f"lô chẵn (giới hạn bởi {rang_buoc})"
    if n > 0 and CHO_PHEP_LO_LE:
        return n, f"LÔ LẺ (giới hạn bởi {rang_buoc})"
    return 0, f"không đủ ({rang_buoc})"


# ==========================================================================
# TỔNG HỢP DANH MỤC
# ==========================================================================
def _gia_ngay(ds_kq):
    """Ma trận giá ngày: chỉ ffill SAU ngày giao dịch đầu tiên của từng mã (không bịa giá trước niêm yết)."""
    return pd.concat({r["symbol"]: r["df"].close for r in ds_kq}, axis=1).sort_index().ffill()


def chi_so_rui_ro(r, rf=0.0):
    """r: lợi suất ngày. Lợi suất năm, biến động năm, Sharpe, MDD, VaR & CVaR 95% 1 ngày."""
    r = r.dropna()
    if len(r) < 20:
        return {}
    tl = (1 + r).cumprod()
    ln = tl.iloc[-1] ** (252 / len(r)) - 1
    bd = r.std() * np.sqrt(252)
    q = np.percentile(r, 5)
    return {"Lợi suất năm %": ln * 100, "Biến động năm %": bd * 100, "Sharpe": (ln - rf) / bd if bd > 0 else np.nan,
            "Sụt giảm tối đa %": (tl / tl.cummax() - 1).min() * 100, "VaR 95% 1 ngày %": -q * 100,
            "CVaR 95% 1 ngày %": -r[r <= q].mean() * 100}


def phan_tich_danh_muc(ds_kq, ds_vao, vni, rf, tien_mat, trang_thai, thi_truong, giu_tien_mat=50.0):
    """
    ds_kq: kết quả phân tích từng mã; ds_vao: dòng danh mục tương ứng (theo mã); trang_thai: dict đã lưu.
    thi_truong: {"xau": bool, "nhan": str}. giu_tien_mat: % tổng tài sản luôn giữ tiền mặt – chỉ phần tiền mặt
    VƯỢT mức này mới được dùng cho lệnh mua gợi ý. Trả dict dm + trạng thái mới.
    """
    vao = {d["ma"]: d for d in ds_vao}
    giu = [r for r in ds_kq if r["so_cp"] > 0]
    gt = {r["symbol"]: r["so_cp"] * r["ht"] * 1000 for r in ds_kq}
    gt_cp = sum(gt.values())
    tong_ts = gt_cp + tien_mat
    he_so = HE_SO_THI_TRUONG_XAU if thi_truong.get("xau") else 1.0

    # --- cắt lỗ/mục tiêu đã đặt & tổng rủi ro mở ---
    md, tt_moi = {}, {}
    for r in giu:
        md[r["symbol"]], tt_moi[r["symbol"]] = cap_nhat_muc_dat(r, vao.get(r["symbol"], {}), trang_thai.get(r["symbol"]))
    rui_ro_mo = sum(max(0.0, r["so_cp"] * (r["ht"] - md[r["symbol"]]["cat_lo_moi"]) * 1000) for r in giu)
    con_rui_ro = TONG_RUI_RO_MO_TOI_DA / 100 * tong_ts - rui_ro_mo

    rows = []
    for r in ds_kq:
        m, dang_giu = r["symbol"], r["so_cp"] > 0
        gv = r["gia_von"] or r["ht"]
        cl = md[m]["cat_lo_moi"] if dang_giu else r["cat_lo"]
        mt = md[m]["muc_tieu_moi"] if dang_giu else r["mt_ngay"]
        kl20 = r["tt"]["kl_tb20"]
        rows.append({
            "Mã": m, "Trạng thái": "Đang giữ" if dang_giu else "Theo dõi", "Sàn": r["san"], "SL": r["so_cp"],
            "Giá vốn": gv if dang_giu else np.nan, "Giá HT": r["ht"],
            "Vốn đầu tư (đ)": r["so_cp"] * gv * 1000, "Giá trị TT (đ)": gt[m],
            "Lãi/Lỗ chưa thực hiện (đ)": r["so_cp"] * (r["ht"] - gv) * 1000,
            "% L/L": (r["ht"] / gv - 1) * 100 if dang_giu else np.nan,
            "Lãi đã thực hiện (đ)": vao.get(m, {}).get("lai_da_thuc_hien", np.nan),
            "Cổ tức nhận (đ)": vao.get(m, {}).get("co_tuc", np.nan),
            "Tỷ trọng TS %": gt[m] / tong_ts * 100 if tong_ts else 0,
            "Quyết định KT": r["quyet_dinh"], "EV %": r["ev"], "R/R": r["rr"],
            "Mục tiêu": mt, "Upside %": (mt / r["ht"] - 1) * 100 if mt else np.nan,
            "Cắt lỗ": cl, "% tới cắt lỗ": (cl / r["ht"] - 1) * 100,
            "Định giá tự nhập": r["mt_nhap"], "Upside định giá %": r["upside_dg"],
            "Beta (tuần)": r["tt"]["beta"], "Đỉnh 52T": r["tt"]["cao52"], "Đáy 52T": r["tt"]["thap52"],
            "KLGD TB20": kl20, "Số phiên để bán hết": (r["so_cp"] / (TY_LE_THANH_KHOAN / 100 * kl20)
                                                        if dang_giu and kl20 > 0 else np.nan),
            "Xu hướng tuần": r["cau_truc_tuan"], "Vùng mua": (f"{r['vung_mua'][0]:,.2f} – {r['vung_mua'][1]:,.2f}"
                                                              if r["vung_mua"] else "N/A"),
        })
    bang = pd.DataFrame(rows)
    bang["Hành động"] = [goi_y_hanh_dong(r, md[r["symbol"]], w, con_rui_ro) if r["so_cp"] > 0
                         else goi_y_ma_theo_doi(r, thi_truong.get("xau"))
                         for r, w in zip(ds_kq, bang["Tỷ trọng TS %"])]

    # --- Phân bổ tiền mặt theo thứ tự ưu tiên EV (rồi R/R) ---
    bang["SL gợi ý mua"], bang["Tiền cần (đ)"], bang["Ghi chú SL"] = 0, 0.0, ""
    ung = [(i, r) for i, r in enumerate(ds_kq)
           if bang.at[i, "Hành động"].startswith(("MUA MỚI", "MUA TỪNG PHẦN", "MUA THÊM"))]
    ung.sort(key=lambda x: (-(x[1]["ev"] if co(x[1]["ev"]) else -99), -(x[1]["rr"] if co(x[1]["rr"]) else 0)))
    tien_giu = giu_tien_mat / 100 * tong_ts
    tien_giai_ngan = max(0.0, tien_mat - tien_giu)
    tien_con, rr_con = tien_giai_ngan, con_rui_ro
    for thu_tu, (i, r) in enumerate(ung, 1):
        n, ghi = so_luong_goi_y(r, tong_ts, tien_con, rr_con, he_so, gt[r["symbol"]])
        tien = n * r["ht"] * 1000
        tien_con -= tien * (1 + chi_phi() / 200)
        rr_con -= n * ((r["ht"] - r["cat_lo"]) * 1000)
        bang.at[i, "SL gợi ý mua"], bang.at[i, "Tiền cần (đ)"] = n, tien
        bang.at[i, "Ghi chú SL"] = f"ưu tiên {thu_tu} – {ghi}"

    # --- Lợi suất (tỷ trọng hiện tại, giả định) – tiền mặt lợi suất 0 ---
    gia = _gia_ngay(ds_kq)
    ret = gia.pct_change()
    w = pd.Series({m: gt[m] / tong_ts if tong_ts else 0 for m in gia.columns})
    co_w = [m for m in gia.columns if w[m] > 0]
    r_dm = (ret[co_w].dropna() @ w[co_w]) if co_w else pd.Series(dtype=float)
    chi_so = {"Danh mục (tỷ trọng HT, gồm tiền mặt)": chi_so_rui_ro(r_dm.tail(252), rf)} if len(r_dm) else {}
    r_vni = None
    if vni is not None:
        r_vni = vni.close.pct_change().reindex(ret.index).tail(252)
        chi_so["VNINDEX"] = chi_so_rui_ro(r_vni, rf)
    for m in gia.columns:
        chi_so[m] = chi_so_rui_ro(ret[m].tail(252), rf)
    ret_tuan = pd.concat({r["symbol"]: loi_suat_tuan(r["df"].close) for r in ds_kq}, axis=1).tail(104)
    tuong_quan = ret_tuan.corr(min_periods=26)
    r_dm_tuan = (ret_tuan[co_w].dropna() @ w[co_w]) if co_w else None
    bang["Tương quan tuần với DM"] = [ret_tuan[m].corr(r_dm_tuan) if r_dm_tuan is not None and len(r_dm_tuan) > 26
                                      and t == "Theo dõi" else np.nan for m, t in zip(bang["Mã"], bang["Trạng thái"])]

    # --- Stress test ---
    beta = {r["symbol"]: r["tt"]["beta"] for r in ds_kq}
    stress = [[f"VN-Index {s:+d}% (theo beta)", sum(gt[m] * (beta[m] if co(beta[m]) else 1.0) * s / 100 for m in gt)]
              for s in CU_SOC_STRESS]
    for n_p in (20, 60):
        if len(r_dm) > n_p:
            tl = (1 + r_dm).rolling(n_p).apply(np.prod, raw=True) - 1
            stress.append([f"{n_p} phiên xấu nhất lịch sử (đến {tl.idxmin():%d/%m/%Y})", tl.min() * tong_ts])
    stress = pd.DataFrame(stress, columns=["Kịch bản", "Lãi/Lỗ (đ)"])
    stress["% tổng tài sản"] = stress["Lãi/Lỗ (đ)"] / tong_ts * 100 if tong_ts else np.nan

    beta_dm = sum(gt[m] * beta[m] for m in gt if co(beta[m])) / tong_ts if tong_ts else np.nan
    tong = {
        "Số mã đang giữ": len(giu), "Số mã theo dõi": len(ds_kq) - len(giu),
        "Giá trị cổ phiếu (đ)": gt_cp, "Tiền mặt (đ)": tien_mat, "Tổng tài sản (đ)": tong_ts,
        "Tỷ trọng cổ phiếu %": gt_cp / tong_ts * 100 if tong_ts else 0,
        "Tiền mặt muốn giữ (đ)": tien_giu, "Tiền mặt muốn giữ %": giu_tien_mat,
        "Tiền có thể giải ngân (đ)": tien_giai_ngan,
        "Lãi/lỗ chưa thực hiện (đ)": bang["Lãi/Lỗ chưa thực hiện (đ)"].sum(),
        "Lãi đã thực hiện (đ)": bang["Lãi đã thực hiện (đ)"].sum(min_count=1),
        "Cổ tức đã nhận (đ)": bang["Cổ tức nhận (đ)"].sum(min_count=1),
        "Beta danh mục (gồm tiền mặt)": beta_dm,
        "Tổng rủi ro mở (đ)": rui_ro_mo, "Tổng rủi ro mở % TS": rui_ro_mo / tong_ts * 100 if tong_ts else 0,
        "Upside tới mục tiêu (% TS)": (bang["Giá trị TT (đ)"] * bang["Upside %"].fillna(0)).sum() / tong_ts
        if tong_ts else 0,
        "Lỗ nếu chạm mọi cắt lỗ (% TS)": (bang["Giá trị TT (đ)"] * bang["% tới cắt lỗ"].fillna(0)).sum() / tong_ts
        if tong_ts else 0,
        "Tiền cần cho lệnh gợi ý (đ)": bang["Tiền cần (đ)"].sum(),
        "Thị trường chung": thi_truong.get("nhan", "N/A"),
    }
    if chi_so and "VaR 95% 1 ngày %" in next(iter(chi_so.values()), {}):
        k = next(iter(chi_so))
        tong["VaR 95% 1 ngày (đ)"] = chi_so[k]["VaR 95% 1 ngày %"] / 100 * tong_ts
        tong["CVaR 95% 1 ngày (đ)"] = chi_so[k]["CVaR 95% 1 ngày %"] / 100 * tong_ts

    # --- Cảnh báo ---
    cb = []
    if 0 < len(giu) < 4:
        cb.append(f"Chỉ có {len(giu)} mã đang giữ → đa dạng hoá thấp (nên ≥ 4–5 mã khác ngành).")
    for _, r in bang[bang["Tỷ trọng TS %"] > TY_TRONG_TOI_DA].iterrows():
        cb.append(f"{r['Mã']} chiếm {r['Tỷ trọng TS %']:.1f}% tổng tài sản (> {TY_TRONG_TOI_DA:.0f}%) → tập trung.")
    ma_giu = [r["symbol"] for r in giu]
    for i, a in enumerate(ma_giu):
        for b in ma_giu[i + 1:]:
            c = tuong_quan.loc[a, b]
            if co(c) and c > NGUONG_TUONG_QUAN:
                cb.append(f"{a} & {b} tương quan tuần {c:.2f} → đa dạng hoá kém.")
    if rui_ro_mo / tong_ts * 100 > TONG_RUI_RO_MO_TOI_DA if tong_ts else False:
        cb.append(f"Tổng rủi ro mở {rui_ro_mo / tong_ts * 100:.1f}% TS > trần {TONG_RUI_RO_MO_TOI_DA:g}% → không mua thêm.")
    if co(beta_dm) and beta_dm > 1.2:
        cb.append(f"Beta danh mục {beta_dm:.2f} > 1,2.")
    if tien_mat < tien_giu:
        cb.append(f"Tiền mặt {tien_mat / tong_ts * 100:.0f}% TS < mức muốn giữ {giu_tien_mat:g}% → không mua mới; "
                  f"cân nhắc bán bớt ~{(tien_giu - tien_mat) / 1e6:,.2f} tr.")
    if thi_truong.get("xau"):
        cb.append(f"VN-Index xấu ({thi_truong['nhan']}) → rủi ro mỗi lệnh × {HE_SO_THI_TRUONG_XAU:g}.")
    for r in ds_kq:
        cb += [f"{r['symbol']}: {c}" for c in r["canh_bao"]]
    for _, r in bang.iterrows():
        if r["Số phiên để bán hết"] > 5:
            cb.append(f"{r['Mã']}: cần ~{r['Số phiên để bán hết']:.0f} phiên để bán hết (thanh khoản mỏng).")

    tl = pd.DataFrame({"Danh mục (tỷ trọng HT)": (1 + r_dm.tail(252)).cumprod() - 1}) if len(r_dm) else pd.DataFrame()
    if r_vni is not None and len(tl):
        tl["VNINDEX"] = (1 + r_vni.reindex(tl.index).fillna(0)).cumprod() - 1
    bang_ky = so_sanh_theo_ky(ds_kq, tien_mat, vni)
    bang_mua, thieu_ngay = so_sanh_tu_ngay_mua(ds_kq, ds_vao, vni)
    nx = nhan_xet(bang_ky, bang_mua, thieu_ngay, ds_kq, beta_dm, tong["Tỷ trọng cổ phiếu %"])
    if thi_truong.get("trang_thai") not in (None, "KHÔNG RÕ"):
        nx.insert(0, f"Thị trường: {thi_truong['nhan']} ({thi_truong.get('nguon_tien_mat', '')}); tiền mặt hiện "
                     f"{tien_mat / tong_ts * 100:.0f}% tổng tài sản" if tong_ts else thi_truong["nhan"])
    return {"thi_truong": thi_truong, "so_sanh_ky": bang_ky, "so_sanh_mua": bang_mua, "nhan_xet": nx, "bang": bang, "tong": tong, "chi_so": pd.DataFrame(chi_so).T, "tuong_quan": tuong_quan,
            "stress": stress, "canh_bao": cb, "tich_luy": tl, "co_vi_the": bool(giu), "md": md}, tt_moi
