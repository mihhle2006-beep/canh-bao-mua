# -*- coding: utf-8 -*-
"""Nhóm mã, ngưỡng riêng theo nhóm/mã, danh sách toàn sàn HOSE (+ HNX: nhóm hose_hnx)."""
import os
import time

from . import cau_hinh as ch
from .nguon.http import lay_json

# Danh sách tham khảo – thành phần rổ/ngành thay đổi theo thời gian, hãy cập nhật khi cần
NHOM_MA = {
    "vn30": "ACB BCM BID BVH CTG FPT GAS GVR HDB HPG LPB MBB MSN MWG PLX SAB SHB SSB SSI STB "
            "TCB TPB VCB VHM VIB VIC VJC VNM VPB VRE",
    "ngan_hang": "VCB BID CTG TCB MBB ACB VPB HDB STB VIB TPB SHB LPB SSB MSB OCB EIB",
    "chung_khoan": "SSI VND HCM VCI SHS MBS FTS BSI CTS VIX",
    "bat_dong_san": "VHM VIC VRE NVL PDR KDH NLG DXG DIG KBC",
    # Tách CẢNG (khai thác cảng, logistics cảng) khỏi VẬN TẢI BIỂN (chủ tàu) để so sánh P/E đúng bản chất
    "cang_bien": "GMD VSC SCS DVP PHP SGP TCL CDN",
    "van_tai_bien": "HAH VOS PVT VTO",
    "ban_le": "MWG FRT PNJ DGW MSN",
    "thep": "HPG HSG NKG",
    "hoa_chat": "DGC DCM DPM CSV DHC",
    "viettel": "CTR VTP VGI VTK",
    "vien_thong_cntt": "CTR VGI VTK FPT FOX CMG ELC",
}
# Nhóm gộp cảng + vận tải (giữ tương thích cách dùng cũ)
NHOM_MA["cang_va_van_tai"] = NHOM_MA["cang_bien"] + " " + NHOM_MA["van_tai_bien"]

NHOM_GOP = ["vn30", "ngan_hang", "chung_khoan", "bat_dong_san", "cang_bien", "van_tai_bien", "ban_le", "thep",
            "hoa_chat", "viettel"]
NHOM_MA["tat_ca"] = " ".join(dict.fromkeys(m for n in NHOM_GOP for m in NHOM_MA[n].split()))

# Ngưỡng thanh khoản RIÊNG cho từng mã (áp cả khi quét chung); --gtgd_min / --klgd_min ghi đè
NGUONG_RIENG_MA = {m: {"gtgd_min": 1, "klgd_min": 10_000} for m in NHOM_MA["viettel"].split()}
# Cấu hình riêng theo nhóm (ghi đè ngưỡng chiến lược nếu KHÔNG truyền --gtgd_min/--klgd_min)
CAU_HINH_NHOM = {
    "viettel": {"gtgd_min": 1, "klgd_min": 10_000},
    "vien_thong_cntt": {"gtgd_min": 1, "klgd_min": 10_000},
}


def nhom_cua_ma(ma):
    """Ngành/nhóm đầu tiên chứa mã (ưu tiên nhóm ngành hơn vn30)."""
    for n in [x for x in NHOM_GOP if x != "vn30"] + ["vn30", "vien_thong_cntt"]:
        if ma in NHOM_MA[n].split():
            return n
    return ""


def _ds_hose_vndirect():
    loi = None
    for host in ("api-finfo", "finfo-api"):                 # host mới trước, host cũ dự phòng
        try:
            j = lay_json(f"https://{host}.vndirect.com.vn/v4/stocks",
                         params={"q": "type:STOCK~status:LISTED~floor:HOSE", "size": 2000})
            ds = [d.get("code", "") for d in (j.get("data") or [])]
            if ds:
                return ds
        except Exception as e:
            loi = e
    raise ValueError(f"không có dữ liệu ({loi})")


def _ds_hose_ssi():
    j = lay_json("https://iboard-query.ssi.com.vn/v2/stock/exchange/hose")
    return [d.get("stockSymbol") or d.get("ss") or "" for d in (j.get("data") or [])]


def _ds_hose_vci():
    h = {"Referer": "https://trading.vietcap.com.vn/", "Origin": "https://trading.vietcap.com.vn"}
    j = lay_json("https://trading.vietcap.com.vn/api/price/symbols/getAll", headers=h)
    ds = j if isinstance(j, list) else (j.get("data") or [])
    return [d.get("symbol", "") for d in ds
            if str(d.get("board", d.get("exchange", ""))).upper() in ("HSX", "HOSE")
            and str(d.get("type", "STOCK")).upper() == "STOCK"]


def _ds_hose_vnstock():
    from .nguon import vnstock_nguon
    return vnstock_nguon.ds_hose()


NGUON_DS_HOSE = [("VNDirect", _ds_hose_vndirect), ("SSI", _ds_hose_ssi), ("VCI", _ds_hose_vci),
                 ("vnstock", _ds_hose_vnstock)]


def lay_danh_sach_hose():
    """File lưu sẵn (< 7 ngày) → VNDirect → SSI → VCI → file cũ. Chỉ giữ mã 3 chữ cái."""
    f = ch.FILE_DS_HOSE
    if os.path.exists(f) and time.time() - os.path.getmtime(f) < 7 * 86400:
        ds = _doc(f).split()
        if ds:
            return ds, f"file {f}"
    loi = []
    for ten, ham in NGUON_DS_HOSE:
        try:
            ds = sorted({str(x).strip().upper() for x in ham()
                         if len(str(x).strip()) == 3 and str(x).strip().isalpha()})
            if len(ds) > 100:
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(ds))
                return ds, f"online {ten}"
            loi.append(f"{ten}: chỉ có {len(ds)} mã")
        except (Exception, SystemExit) as e:
            loi.append(f"{ten}: {str(e)[:60]}")
    if os.path.exists(f):
        return _doc(f).split(), f"file cũ {f}"
    raise ValueError("không lấy được online (" + "; ".join(loi) + f") và chưa có file {f}")


def lay_danh_sach_hnx():
    """Mã HNX đang niêm yết: ptcp/san_niem_yet.json (cập nhật python -m ptcp.san); thiếu → VNDirect; lỗi → []."""
    try:
        from ptcp.san import doc_san
        ds = doc_san()["HNX"]
        if ds:
            return ds
    except ImportError:
        pass
    try:
        j = lay_json("https://api-finfo.vndirect.com.vn/v4/stocks",
                     params={"q": "type:STOCK~status:LISTED~floor:HNX", "size": 2000})
        return sorted({str(d.get("code", "")).upper() for d in (j.get("data") or []) if len(str(d.get("code", ""))) == 3})
    except Exception:                                   # noqa: BLE001
        return []


def _doc(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def tach_ma(chuoi):
    return [x.strip().upper() for x in chuoi.replace(";", ",").replace("\n", ",").replace(" ", ",").split(",")
            if x.strip()]


def lay_danh_sach_ma(ma=None, file_ma=None, nhom="tat_ca"):
    if ma:
        return list(dict.fromkeys(tach_ma(ma)))
    if file_ma:
        return list(dict.fromkeys(tach_ma(_doc(file_ma))))
    if nhom == "hose":
        try:
            ds, nguon = lay_danh_sach_hose()
            print(f"  Danh sách HOSE ({nguon}): {len(ds)} mã")
            return ds
        except Exception as e:
            raise SystemExit(f"Không lấy được danh sách HOSE ({e}). Dùng --nhom khác, --ma, "
                             f"hoặc tạo file {ch.FILE_DS_HOSE} (mỗi dòng 1 mã).")
    if nhom == "hose_hnx":                  # 17/10/2026: Quỹ Bứt Phá mua cả HNX (rổ HOSE + HNX – ptcp QUY_RO)
        ds = lay_danh_sach_ma(nhom="hose")
        hnx = lay_danh_sach_hnx()
        print(f"  Danh sách HNX (ptcp/san_niem_yet.json): {len(hnx)} mã")
        return list(dict.fromkeys(ds + hnx))
    if nhom not in NHOM_MA:
        raise SystemExit(f"Không có nhóm '{nhom}'. Chọn một trong: {', '.join(NHOM_MA)}, hose, hose_hnx")
    return NHOM_MA[nhom].split()
