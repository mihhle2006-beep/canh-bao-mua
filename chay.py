# -*- coding: utf-8 -*-
"""
CẢNH BÁO MUA THEO CHIẾN LƯỢC THỊ TRƯỜNG – chạy:
  python chay.py                       (tu_dong: trong phiên → điểm vào 15' & cảnh báo bán; sau 15h → tổng kết)
  python chay.py --che_do tong_ket     (tin tổng kết gọn theo chiến lược + mã đang giữ + file Excel chi tiết)
  python chay.py --che_do trong_phien  (quét 15': chỉ mã trong nhóm mua của tin tổng kết, đúng vùng giá)
  python chay.py --che_do backtest     (backtest điểm vào 15' & điểm bán / mua thêm → ket_qua_backtest.json)
  python chay.py --che_do lich_su      (chấm lại mọi tín hiệu đã ghi, in bảng độ chính xác, xuất Excel)
  python chay.py --chi_ma FPT          (xem RIÊNG 1 mã / vài mã: FPT,HPG – không ghi trạng thái; + --khong_gui = chỉ in)
  python chay.py --khong_gui           (chỉ in, không gửi Telegram)
  python chay.py --khong_ban           (bỏ phần danh mục / cảnh báo bán)
  python chay.py --gio "2026-10-08 10:30"   (giả lập thời điểm, giờ VN)
Một nguồn logic: chiến lược (ptcp/chien_luoc.py), hệ thoát (ptcp/he_thoat.py), điểm vào 15' (ptcp/diem_vao_15p.py).
Danh mục: danh_muc.csv của repo riêng tư danh-muc (DANH_MUC_TOKEN, DANH_MUC_REPO) – xem vi_the.py.
Repo bot CÔNG KHAI: log chỉ có phần công khai; số CP, giá vốn, cắt lỗ chỉ gửi Telegram.
"""
import argparse
import os
import sys

import pandas as pd

from canh_bao import cau_hinh as C
from canh_bao import (chien_luoc_bot, diem_vao, du_lieu, ma_bo_loc, nhat_ky, ro_vn30, tong_ket_cl, trang_tong_hop,
                      vi_the)
from canh_bao.du_lieu import bo_nen_chua_dong, gio_viet_nam, hom_nay_co_giao_dich, tai, trong_phien
from canh_bao.thong_bao import doc_trang_thai, ghi_trang_thai, gui, gui_file


def main(argv=None):
    p = argparse.ArgumentParser(description="Cảnh báo mua theo chiến lược thị trường")
    p.add_argument("--che_do", default="tu_dong",
                   choices=["tu_dong", "trong_phien", "tong_ket", "lich_su", "chien_luoc", "backtest"])
    p.add_argument("--ma", default=None, help="thêm mã theo dõi ngoài danh sách chiến lược (VD MWG,FPT)")
    p.add_argument("--chi_ma", default=None,
                   help="CHỈ xem mã này (VD FPT hoặc FPT,HPG) theo chiến lược – không ghi trạng thái / danh sách mua")
    p.add_argument("--gio", default=None, help="giả lập thời điểm (giờ VN), VD '2026-10-08 10:30'")
    p.add_argument("--khong_gui", action="store_true")
    p.add_argument("--khong_ban", action="store_true", help="bỏ danh mục / cảnh báo bán")
    p.add_argument("--khong_chien_luoc", action="store_true", help="(giữ cho tương thích – không còn tác dụng)")
    a = p.parse_args(argv)
    bay_gio = pd.Timestamp(a.gio) if a.gio else gio_viet_nam()
    che_do = a.che_do
    if a.chi_ma:
        return xem_ma(bay_gio, [m.strip().upper() for m in a.chi_ma.split(",") if m.strip()], a.khong_gui)
    if che_do == "tu_dong":
        if trong_phien(bay_gio):
            che_do = "trong_phien"
        elif bay_gio.weekday() < 5 and bay_gio >= bay_gio.normalize() + pd.Timedelta(C.GIO_TONG_KET + ":00"):
            che_do = "tong_ket"
        else:
            print(f"{bay_gio:%H:%M %d/%m} ngoài giờ giao dịch → không làm gì.")
            return 0
    if che_do == "lich_su":
        return xem_lich_su()
    if che_do == "backtest":
        from canh_bao.backtest_bot import chay_backtest
        return chay_backtest(bay_gio, a.khong_gui)
    them = [m.strip().upper() for m in (a.ma or "").split(",") if m.strip()]
    vt, nguon_vt = ({}, "tắt (--khong_ban)") if a.khong_ban else vi_the.doc_danh_muc()
    print(f"=== {che_do.upper()} | {bay_gio:%Y-%m-%d %H:%M} ===")
    print(f"Vị thế đang giữ: {len(vt)} mã (nguồn: {nguon_vt})")
    if che_do in ("tong_ket", "chien_luoc"):
        return tong_ket(bay_gio, vt, them, a.khong_gui)
    return trong_phien_15p(bay_gio, vt, a.khong_gui)


# ------------------------------------------------------------------ TỔNG KẾT 15:20
def tong_ket(bay_gio, vt, them=(), khong_gui=False):
    vn30, nguon_vn30 = ro_vn30.lay_vn30()
    print(f"Rổ VN30: {len(vn30)} mã (nguồn: {nguon_vn30})")
    co_dinh = list(dict.fromkeys(m.upper() for m in vn30 + list(C.MA_THEM)))   # VN30 + MA_THEM (cau_hinh.py)
    tt_bl, moi_bl = {}, []
    if getattr(C, "DUNG_BO_LOC", False):
        tt_bl = ma_bo_loc.doc()
        moi_bl = ma_bo_loc.nhan_nguon(tt_bl, ma_bo_loc.lay_nguon(), co_dinh)
        print(f"Mã từ bộ lọc: {len(ma_bo_loc.danh_sach(tt_bl))} đang theo dõi (mới: {', '.join(moi_bl) or '–'})")
    ds_ma = list(dict.fromkeys(co_dinh + ma_bo_loc.danh_sach(tt_bl) + list(them)))
    ra, loi = chien_luoc_bot.chay_chien_luoc(
        lambda ma, tu, chi_so=False: tai(ma, "D", tu, chi_so=chi_so), bay_gio, ds_ma=ds_ma,
        ds_do_rong=C.MA_CHIEN_LUOC if getattr(C, "DO_RONG_THEO_MA_CHIEN_LUOC", True) else None)
    if ra is None:
        print(f"⚠ Chiến lược: {loi}")
        if tt_bl:
            ma_bo_loc.ghi(tt_bl)                               # giữ mã mới nhận; hạn xét ở lần tổng kết sau
        return 1
    tin_bl = ""
    if getattr(C, "DUNG_BO_LOC", False):
        mua = [k["ma"] for k in tong_ket_cl.ds_khuyen_nghi(ra) if k["nhom"] in tong_ket_cl.NHOM_MUA]
        dat_bl = ma_bo_loc.danh_dau_dat(tt_bl, mua, bay_gio)
        xoa_bl = ma_bo_loc.xoa_het_han(tt_bl, bay_gio)            # mã đang giữ: chăm sóc ở phần danh mục riêng tư
        ma_bo_loc.ghi(tt_bl)
        tin_bl = ma_bo_loc.dong_tin(moi_bl, dat_bl, xoa_bl, tt_bl)
        if tin_bl:
            print(tin_bl)
    doi, cl_cu = chien_luoc_bot.kiem_tra_doi(ra, bay_gio)
    n = tong_ket_cl.luu_ds_mua(ra, bay_gio)
    print(f"Danh sách mua phiên tới: {n} mã (lưu {C.FILE_TRANG_THAI_CL} cho cảnh báo 15')")
    ds_kn = tong_ket_cl.ds_khuyen_nghi(ra)
    _an_toan("Lưu thị trường", trang_tong_hop.luu_thi_truong, ra, bay_gio, ds_kn)
    giu = []
    for ma, v in vt.items():                                   # danh mục thật: KHÔNG in chi tiết ra log
        dn = ra["gia_ngay"].get(ma)
        if dn is None:
            dn = tai(ma, "D", C.NGAY_BAT_DAU)
        if dn is None or not len(dn):
            continue
        dn = chien_luoc_bot._phien_da_dong(dn, bay_gio)
        kb = vi_the.danh_gia_ban(v, {"ma": ma, "gia": float(dn.close.iloc[-1])}, dn, bay_gio)
        giu.append((v, kb, tong_ket_cl.mua_them(v, dn, kb, bay_gio)))
    if C.GHI_NHAT_KY:
        _nhat_ky(ra, bay_gio)
    kq_bt = tong_ket_cl.doc_ket_qua_backtest()
    tin, cong_khai = tong_ket_cl.tin_tong_ket(ra, bay_gio, giu, kq_bt)
    if tin_bl:
        tin, cong_khai = f"{tin}\n\n{tin_bl}", f"{cong_khai}\n\n{tin_bl}"
    if doi:
        nd = chien_luoc_bot.tin_doi(ra, cl_cu)
        gui(nd) if not khong_gui else print(nd)
    if giu and os.environ.get("GITHUB_ACTIONS"):
        print(cong_khai)                                       # log công khai: bỏ phần 💼
    if khong_gui:
        print(tin)
    else:
        gui(tin, rieng_tu=bool(giu))
    if C.GUI_EXCEL:
        try:
            from canh_bao.bao_cao_excel import xuat
            path = xuat(ra, giu=giu, kq_bt=kq_bt, rieng=bool(giu))
            if not khong_gui:
                gui_file(path, f"Chi tiết chiến lược {pd.Timestamp(bay_gio):%d/%m/%Y}", rieng_tu=bool(giu))
            else:
                print(f"Đã xuất {path}")
            if giu and os.environ.get("GITHUB_ACTIONS"):
                os.remove(path)                                # file có danh mục: không để lại trên máy chạy
        except Exception as e:
            print(f"⚠ Excel lỗi: {type(e).__name__}: {str(e)[:150]}")
    _trang(bay_gio, giu, kq_bt, khong_gui)
    return 0


def _an_toan(ten, f, *a, **k):
    """Phần phụ (trang tổng hợp) lỗi không được làm hỏng tin cảnh báo."""
    try:
        return f(*a, **k)
    except Exception as e:
        print(f"⚠ {ten} lỗi: {type(e).__name__}: {str(e)[:150]}")
        return None


def _trang(bay_gio, giu=None, kq_bt=None, khong_gui=False):
    """Trang tổng hợp: bản công khai (docs/) mọi lần chạy; bản riêng có danh mục thật → chỉ gửi Telegram."""
    if not C.DUNG_TRANG_TONG_HOP:
        return
    p = _an_toan("Trang tổng hợp", trang_tong_hop.tao, None, None, bay_gio, kq_bt)
    if p:
        print(f"Trang tổng hợp: {p}")
    if giu and C.GUI_TRANG_RIENG:
        p = _an_toan("Trang riêng", trang_tong_hop.tao, None, giu, bay_gio, kq_bt)
        if p and not khong_gui:
            gui_file(p, f"Bảng tổng hợp {pd.Timestamp(bay_gio):%d/%m/%Y} (mở bằng trình duyệt)", rieng_tu=True)
        if p and os.environ.get("GITHUB_ACTIONS"):
            os.remove(p)                                       # có danh mục thật: không để lại trên máy chạy


# ------------------------------------------------------------------ XEM RIÊNG 1 / VÀI MÃ
def xem_ma(bay_gio, ds, khong_gui=False):
    """
    Chạy chiến lược CHỈ cho mã trong ds (độ rộng thị trường vẫn theo MA_CHIEN_LUOC) → in / gửi nhóm hành động,
    vùng mua, cắt lỗ, mục tiêu. KHÔNG ghi trang_thai_chien_luoc.json, nhật ký, trang tổng hợp, mã Bo_Loc.
    """
    if not ds:
        print("Chưa nhập mã.")
        return 1
    ra, loi = chien_luoc_bot.chay_chien_luoc(
        lambda ma, tu, chi_so=False: tai(ma, "D", tu, chi_so=chi_so), bay_gio, ds_ma=ds,
        ds_do_rong=C.MA_CHIEN_LUOC if getattr(C, "DO_RONG_THEO_MA_CHIEN_LUOC", True) else None)
    if ra is None:
        print(f"⚠ Chiến lược: {loi}")
        return 1
    kn = {k["ma"]: k for k in tong_ket_cl.ds_khuyen_nghi(ra)}
    trang_thai = {}
    for tp, bang in (ra.get("diem_mua") or {}).items():
        for _, r in bang.iterrows():
            trang_thai.setdefault(r["Mã"], []).append(f"{tp}: {r.get('Trạng thái', '')}")
    d = ra["doc"]
    dong = [f"🔍 XEM MÃ {', '.join(ds)} – dữ liệu {pd.Timestamp(d['ngay']):%d/%m/%Y} · thị trường "
            f"{d.get('diem', '–')}/{d.get('so_chi_bao', 8)} điểm · CL{ra['cl']}"]
    for ma in ds:
        k = kn.get(ma)
        if ma in ra.get("thieu", []):
            dong.append(f"\n{ma}: thiếu dữ liệu giá (cần ≥ 260 phiên)")
        elif k is None:
            dong.append(f"\n{ma}: chưa có tín hiệu mua – " + " · ".join(trang_thai.get(ma, ["CHỜ tín hiệu"])))
        else:
            dong.append(f"\n{tong_ket_cl.TIEU_DE.get(k['nhom'], k['nhom'])}\n{tong_ket_cl.dong_mua(k)}")
    tin = "\n".join(dong)
    print(tin)
    if not khong_gui:
        gui(tin)
    return 0


def _nhat_ky(ra, bay_gio):
    try:
        n = tong_ket_cl.ghi_nhat_ky(ra, nhat_ky.FILE_CONG_KHAI)
        xong = nhat_ky.cap_nhat(lambda ma: tai(ma, "D", C.NGAY_BAT_DAU), ra.get("gia_ngay"))
        print(f"Nhật ký: ghi {n} khuyến nghị mới, {xong} tín hiệu vừa có kết luận ĐÚNG/SAI.")
    except Exception as e:                                     # nhật ký lỗi không được làm hỏng tin tổng kết
        print(f"⚠ Nhật ký lỗi: {type(e).__name__}: {str(e)[:150]}")


# ------------------------------------------------------------------ TRONG PHIÊN (mỗi 15 phút)
def trong_phien_15p(bay_gio, vt, khong_gui=False):
    ds = diem_vao.doc_ds_mua(bay_gio)
    bien_the, nguon = tong_ket_cl.cach_vao(tong_ket_cl.doc_ket_qua_backtest())
    print(f"Điểm vào 15': {len(ds)} mã trong danh sách mua phiên {bay_gio:%d/%m} · cách vào {bien_the} ({nguon})")
    tt = doc_trang_thai()
    luu = tt.setdefault("_15p", {})
    bang, so_bao = [], 0
    for z in ds:
        dp = bo_nen_chua_dong(tai(z["ma"], C.KHUNG_PHUT), C.KHUNG_PHUT, bay_gio)
        kq = diem_vao.danh_gia(z, dp, bay_gio, bien_the)
        print(diem_vao.dong_bang(kq))
        bang.append({"Mã": kq["ma"], "Nhóm": diem_vao.TEN_NHOM.get(kq["nhom"], kq["nhom"]),
                     "Vùng": f"{kq['tu']:,.2f}–{kq['den']:,.2f}", "Giá": kq["gia_nay"], "Trạng thái": kq["trang_thai"],
                     "Lý do": kq["ly_do"], "Giờ": f"{pd.Timestamp(kq['thoi_diem']):%H:%M}" if kq["thoi_diem"] is not None
                     else "", "Giá mua": kq["gia_mua"]})
        if diem_vao.can_bao(kq["ma"], kq["trang_thai"], bay_gio, luu, kq["ly_do"]):
            nd = diem_vao.tin_mua(kq, bay_gio, bien_the, kq["ma"] in vt) if kq["trang_thai"] == "MUA" else \
                diem_vao.tin_bo(kq, bay_gio)
            gui(nd, rieng_tu=kq["ma"] in vt) if not khong_gui else print(nd)
            if kq["trang_thai"] == "MUA" and C.GHI_NHAT_KY:
                gia, cl, mt1, _ = diem_vao.muc_sau_mua(kq)
                nhat_ky.ghi_mua_ngay({"ma": kq["ma"], "gia": gia, "cat_lo": cl, "muc_tieu": mt1}, bay_gio)
            so_bao += 1
    tt["_15p_hom_nay"] = {"ngay": f"{bay_gio:%Y-%m-%d}", "cach_vao": bien_the,
                          "ds": [{k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}
                                 for r in bang]}
    ghi_trang_thai(tt)
    print(f"Đã báo {so_bao} tin điểm vào.")
    _canh_bao_ban(bay_gio, vt, khong_gui)
    _trang(bay_gio)
    _in_nguon()
    return 0


def _canh_bao_ban(bay_gio, vt, khong_gui):
    """Mã đang giữ: chạm cắt lỗ / sát cắt lỗ / gãy MA10 tuần / hết hạn / dời cắt lỗ – theo hệ thoát (tin riêng tư)."""
    if not vt:
        return
    tt_ban, so_ban = vi_the.doc_trang_thai_ban(), 0
    for ma, v in vt.items():
        dn = tai(ma, "D", C.NGAY_BAT_DAU)
        if dn is None or not hom_nay_co_giao_dich(dn, bay_gio):
            continue
        dp = bo_nen_chua_dong(tai(ma, C.KHUNG_PHUT), C.KHUNG_PHUT, bay_gio)
        gia = float(dp.close.iloc[-1]) if dp is not None and len(dp) else float(dn.close.iloc[-1])
        kq = {"ma": ma, "gia": gia}
        kb = vi_the.danh_gia_ban(v, kq, dn, bay_gio)
        if vi_the.can_bao_ban(ma, kb["muc"], bay_gio, tt_ban):
            nd = vi_the.tin_ban(v, kb, kq, bay_gio)
            gui(nd, rieng_tu=True) if not khong_gui else print(nd)
            if C.GHI_NHAT_KY:
                nhat_ky.ghi_ban(kq, kb, bay_gio)
            so_ban += 1
    vi_the.ghi_trang_thai_ban(tt_ban)
    print(f"Đã gửi {so_ban} cảnh báo cho vị thế đang giữ.")


def _in_nguon():
    if du_lieu.NGUON_DA_DUNG:
        dem = {}
        for n in du_lieu.NGUON_DA_DUNG.values():
            dem[n] = dem.get(n, 0) + 1
        print("Nguồn giá đã dùng: " + ", ".join(f"{n} ({k} lần)" for n, k in dem.items()))


def xem_lich_su():
    """Chấm lại & in bảng độ chính xác. Trên Actions (repo công khai) chỉ in phần công khai."""
    rieng = not os.environ.get("GITHUB_ACTIONS")
    xong = nhat_ky.cap_nhat(lambda ma: tai(ma, "D", C.NGAY_BAT_DAU))
    print(f"Vừa có kết luận: {xong} tín hiệu")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        for ten, path in [("CÔNG KHAI", nhat_ky.FILE_CONG_KHAI)] + ([("RIÊNG", nhat_ky.FILE_RIENG)] if rieng else []):
            tk = nhat_ky.thong_ke(nhat_ky.doc(path))
            print(f"\n=== ĐỘ CHÍNH XÁC – {ten} ===")
            print(tk.round(1).to_string(index=False) if len(tk) else "(chưa có tín hiệu)")
    print("\nĐã xuất", nhat_ky.xuat_excel(rieng=rieng))
    return 0


if __name__ == "__main__":
    sys.exit(main())
