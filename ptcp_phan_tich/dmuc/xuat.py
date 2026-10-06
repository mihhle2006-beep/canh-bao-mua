# -*- coding: utf-8 -*-
"""IN BÁO CÁO, XUẤT EXCEL (ghi rõ đơn vị trong tên cột), LỊCH SỬ MỖI LẦN CHẠY."""
import os

import pandas as pd

from .tien_ich import co, so_vn, in_bang

FF = lambda x: f"{x:,.2f}"


def in_danh_muc(dm):
    b, t = dm["bang"], dm["tong"]
    print(f"\n{'#' * 100}\n TỔNG HỢP DANH MỤC\n{'#' * 100}")
    giu, td = b[b["Trạng thái"] == "Đang giữ"], b[b["Trạng thái"] == "Theo dõi"]
    if len(giu):
        in_bang(f"MÃ ĐANG GIỮ ({len(giu)}) – cắt lỗ/mục tiêu là mức ĐÃ ĐẶT (chỉ dời lên)",
                giu[["Mã", "SL", "Giá vốn", "Giá HT", "% L/L", "Tỷ trọng TS %", "Cắt lỗ", "% tới cắt lỗ", "Mục tiêu",
                     "Quyết định KT", "Số phiên để bán hết"]])
    if len(td):
        in_bang(f"MÃ THEO DÕI ({len(td)})", td[["Mã", "Giá HT", "Quyết định KT", "EV %", "R/R", "Mục tiêu", "Cắt lỗ",
                                                 "SL gợi ý mua", "Tương quan tuần với DM"]])
    tt = dm.get("thi_truong") or {}
    if len(tt.get("bang", [])):
        in_bang(f"THỊ TRƯỜNG CHUNG – {tt['nhan']}", tt["bang"])
    print(f"\n{'-' * 100}\n CHỈ TIÊU DANH MỤC (trên TỔNG TÀI SẢN, gồm tiền mặt)\n{'-' * 100}")
    for k, v in t.items():
        if isinstance(v, str):
            print(f"  {k:<36}: {v}")
        elif co(v):
            print(f"  {k:<36}: {so_vn(v) + ' đ' if '(đ)' in k else so_vn(v, 0 if k.startswith('Số') else 2)}")
    if len(dm["so_sanh_mua"]):
        in_bang("SO VỚI VN-INDEX TỪ NGÀY MUA (cùng dòng tiền: mua/bán VN-Index đúng ngày, đúng số tiền)",
                dm["so_sanh_mua"], ff=lambda x: f"{x:,.1f}")
    if len(dm["so_sanh_ky"]):
        in_bang("SO VỚI VN-INDEX THEO KỲ (nếu giữ đúng số CP hiện tại từ đầu kỳ)", dm["so_sanh_ky"])
    print(f"\n{'-' * 100}\n NHẬN XÉT DANH MỤC\n{'-' * 100}")
    for c in dm["nhan_xet"]:
        print(f"  • {c}")
    in_bang("HIỆU QUẢ 52 TUẦN (danh mục: giả định giữ tỷ trọng hiện tại)",
            dm["chi_so"].reset_index().rename(columns={"index": ""}))
    in_bang("KIỂM TRA SỨC CHỊU ĐỰNG", dm["stress"])
    print(f"\n{'-' * 100}\n HÀNH ĐỘNG ĐỀ XUẤT\n{'-' * 100}")
    for _, r in b.iterrows():
        sl = f"  → mua {so_vn(r['SL gợi ý mua'])} CP (~{r['Tiền cần (đ)'] / 1e6:,.2f} tr; {r['Ghi chú SL']})" \
            if r["SL gợi ý mua"] > 0 else (f"  ({r['Ghi chú SL']})" if r["Ghi chú SL"] else "")
        print(f"   [{r['Trạng thái']}] {r['Mã']:<5} {r['Hành động']}{sl}")
    if dm["canh_bao"]:
        print("\n  CẢNH BÁO:")
        for c in dm["canh_bao"]:
            print(f"   ⚠ {c}")


def in_dieu_chinh(b):
    """Bảng đề xuất điều chỉnh cắt lỗ / chốt lời (mục riêng để Telegram trích ra)."""
    print(f"\n{'-' * 100}\n ĐIỀU CHỈNH CẮT LỖ / CHỐT LỜI\n{'-' * 100}")
    for _, x in b.iterrows():
        if x["Trạng thái"] == "Đang giữ":
            print(f"  {x['Mã']:<5} giá {x['Giá HT']:,.2f} (vốn {x['Giá vốn']:,.2f}, {x['Lãi/lỗ %']:+.1f}%, "
                  f"{x['Lãi theo R']:+.1f}R) | Cắt lỗ {x['Cắt lỗ hiện tại']:,.2f} → {x['Cắt lỗ đề xuất']:,.2f}: "
                  f"{x['Lý do cắt lỗ']} | Chốt lời {x['Chốt lời hiện tại']:,.2f} → {x['Chốt lời đề xuất']:,.2f}: "
                  f"{x['Lý do chốt lời']}")
            if x.get("Cắt lỗ gốc (từ giá mua)") == x.get("Cắt lỗ gốc (từ giá mua)") and x.get("Cắt lỗ gốc (từ giá mua)") is not None:
                vni = x.get("VN-Index từ ngày mua %")
                mt2 = x.get("Mốc kế tiếp lúc mua")
                mtt = x.get("Mục tiêu tiếp theo")
                print(f"        từ giá mua: cắt lỗ gốc {x['Cắt lỗ gốc (từ giá mua)']:,.2f} | mục tiêu lúc mua "
                      f"{x['Mục tiêu lúc mua']:,.2f} ({x['Phương pháp MT lúc mua'].split(' – ')[0]}, R/R "
                      f"{x['R/R từ giá mua']:.1f})"
                      + (f" | mốc kế tiếp {mt2:,.2f}" if mt2 == mt2 and mt2 is not None else "")
                      + (f" → ĐÃ VƯỢT, mục tiêu tiếp {mtt:,.2f} ({x['Nguồn MT tiếp theo']})"
                         if mtt == mtt and mtt is not None else "")
                      + (f" | so VN-Index từ ngày mua: {x['Lãi/lỗ %']:+.1f}% vs {vni:+.1f}% "
                         f"({x['Chênh lệch vs VNI (điểm %)']:+.1f} điểm %)" if vni == vni and vni is not None else ""))
        else:
            print(f"  {x['Mã']:<5} (theo dõi) mua ≤ {x['Giá mua đề xuất']:,.2f} | cắt lỗ {x['Cắt lỗ đề xuất']:,.2f} | "
                  f"mục tiêu {x['Chốt lời đề xuất']:,.2f} | R/R {x['R/R còn lại']:.2f} – {x.get('Ghi chú', '')}")


def in_markowitz(mk):
    print(f"\n{'#' * 100}\n TỐI ƯU MARKOWITZ – {mk['so_tuan']} tuần | kỳ vọng: {mk['mo_ta_mu']} | mỗi mã ≤ "
          f"{mk['cap'] * 100:.0f}% phần CP | Rf {mk['rf'] * 100:.1f}%\n{'#' * 100}")
    in_bang("Kỳ vọng & rủi ro từng mã (năm)", pd.DataFrame({"Mã": mk["ma"], "Lợi suất kỳ vọng %": mk["mu"].values,
                                                            "Độ lệch chuẩn %": mk["sigma"].values}))
    in_bang("Tỷ trọng trong phần cổ phiếu (%)", mk["bang_w"].reset_index())
    in_bang("Hiệu quả", mk["chi_tieu"].T.reset_index().rename(columns={"index": "Danh mục"}))
    print(f"\n  Hệ số co Ledoit–Wolf: {mk['he_so_co'] * 100:.0f}% (0% = ma trận mẫu nguyên bản; 100% = coi mọi mã như nhau "
          f"→ GMV chia đều). Hai cột 'không co, không trần' là kết quả nếu tự tính bằng ma trận mẫu, không giới hạn.")
    in_bang("Ma trận hiệp phương sai MẪU năm (%², chưa co)",
            pd.DataFrame(mk["cov_mau"] * 1e4, index=mk["ma"], columns=mk["ma"]).reset_index().rename(columns={"index": "Mã"}),
            ff=lambda x: f"{x:,.1f}")
    in_bang("Ma trận hiệp phương sai năm (%², co Ledoit–Wolf)",
            pd.DataFrame(mk["cov"] * 1e4, index=mk["ma"], columns=mk["ma"]).reset_index().rename(columns={"index": "Mã"}),
            ff=lambda x: f"{x:,.1f}")
    for ten, kh in mk["ke_hoach"].items():
        chinh = " ★ KẾ HOẠCH CHÍNH" if ten == mk["ten_chon"] else " (tham khảo)"
        in_bang(f"KẾ HOẠCH '{ten}'{chinh} – cổ phiếu {mk['pct_cp']:.0f}% / tiền mặt {mk['giu_tien_mat']:.0f}% tổng tài "
                f"sản (tiền mặt sau kế hoạch ≈ {mk['tien_sau'][ten] / 1e6:,.2f} tr)", kh)
    for c in mk["canh_bao"]:
        print(f"   ⚠ {c}")


def xuat_excel(dm, mk, loi, path):
    try:
        with pd.ExcelWriter(path) as w:
            dm["bang"].to_excel(w, sheet_name="Danh muc", index=False)
            pd.DataFrame(list(dm["tong"].items()), columns=["Chỉ tiêu", "Giá trị"]).to_excel(w, sheet_name="Chi tieu",
                                                                                           index=False)
            dm["chi_so"].to_excel(w, sheet_name="Hieu qua 52 tuan")
            dm["stress"].to_excel(w, sheet_name="Stress test", index=False)
            pd.DataFrame({"Nhận xét": dm["nhan_xet"]}).to_excel(w, sheet_name="Nhan xet", index=False)
            if len(dm.get("dieu_chinh", [])):
                dm["dieu_chinh"].to_excel(w, sheet_name="Dieu chinh CL-TP", index=False)
            if len((dm.get("thi_truong") or {}).get("bang", [])):
                dm["thi_truong"]["bang"].to_excel(w, sheet_name="Thi truong", index=False)
            if len(dm["so_sanh_mua"]):
                dm["so_sanh_mua"].to_excel(w, sheet_name="So VNI tu ngay mua", index=False)
            if len(dm["so_sanh_ky"]):
                dm["so_sanh_ky"].to_excel(w, sheet_name="So VNI theo ky", index=False)
            dm["tuong_quan"].round(3).to_excel(w, sheet_name="Tuong quan tuan")
            pd.DataFrame({"Cảnh báo": dm["canh_bao"] or ["Không có"]}).to_excel(w, sheet_name="Canh bao", index=False)
            if mk:
                mk["bang_w"].round(2).to_excel(w, sheet_name="MKW Ty trong")
                mk["chi_tieu"].T.round(4).to_excel(w, sheet_name="MKW Hieu qua")
                pd.DataFrame(mk["cov_mau"], index=mk["ma"], columns=mk["ma"]).to_excel(w, sheet_name="MKW HPS mau")
                pd.DataFrame({"Lợi suất kỳ vọng %": mk["mu"], "Độ lệch chuẩn %": mk["sigma"]}).to_excel(
                    w, sheet_name="MKW Ky vong")
                pd.DataFrame(mk["cov"], index=mk["ma"], columns=mk["ma"]).round(6).to_excel(
                    w, sheet_name="MKW Hiep phuong sai")
                mk["tuong_quan"].round(3).to_excel(w, sheet_name="MKW Tuong quan")
                b = mk["bien"].copy()
                b[["Rủi ro", "Lợi suất"]] *= 100
                b.round(4).to_excel(w, sheet_name="MKW Duong bien", index=False)
                for ten, kh in mk["ke_hoach"].items():
                    kh.to_excel(w, sheet_name="MKW KH " + ("GMV" if "GMV" in ten else "Sharpe"), index=False)
            if loi:
                pd.DataFrame(loi, columns=["Mã", "Lỗi"]).to_excel(w, sheet_name="Ma loi", index=False)
        from ptcp.excel_xanh import trang_tri_excel
        trang_tri_excel(path)
        print(f"  ✔ Excel: {path}")
    except PermissionError:
        print("  ⚠ Không ghi được Excel – hãy đóng file cũ.")


def ghi_lich_su(dm, path):
    """Ảnh chụp mỗi lần chạy; trả danh sách thay đổi HÀNH ĐỘNG so với lần chạy trước (khác ngày)."""
    hom_nay = pd.Timestamp.today().strftime("%Y-%m-%d")
    moi = dm["bang"][["Mã", "Trạng thái", "SL", "Giá HT", "Cắt lỗ", "Mục tiêu", "Hành động"]].copy()
    moi.insert(0, "Ngày", hom_nay)
    moi["Tổng tài sản (đ)"] = dm["tong"]["Tổng tài sản (đ)"]
    cu = pd.read_csv(path, dtype={"Ngày": str}) if os.path.exists(path) else pd.DataFrame(columns=moi.columns)
    cu = cu[cu["Ngày"] != hom_nay]
    thay_doi = []
    if len(cu):
        truoc = cu[cu["Ngày"] == cu["Ngày"].max()].set_index("Mã")
        for _, r in moi.iterrows():
            hd_cu = truoc["Hành động"].get(r["Mã"]) if r["Mã"] in truoc.index else None
            if hd_cu is None:
                thay_doi.append(f"{r['Mã']}: mới vào danh mục")
            elif str(hd_cu).split(" –")[0] != str(r["Hành động"]).split(" –")[0]:
                thay_doi.append(f"{r['Mã']}: {str(hd_cu).split(' –')[0]} → {str(r['Hành động']).split(' –')[0]}")
        thay_doi.insert(0, f"(so với lần chạy {cu['Ngày'].max()})")
    pd.concat([cu, moi]).to_csv(path, index=False, encoding="utf-8-sig")
    return thay_doi
