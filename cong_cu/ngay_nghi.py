# -*- coding: utf-8 -*-
"""
LỊCH NGHỈ GIAO DỊCH (HOSE / HNX) – 1 file dùng chung: cong_cu/ngay_nghi.json (công khai – chỉ ngày + tên lễ).
  Đọc (thư viện chuẩn): doc() → {ngày: tên}; nghi(t) → bool. Dùng ở đồng hồ (cong_cu/dong_ho.py), bộ lọc
  (canh_bao/ma_bo_loc.py), máy Mac đặt lệnh (danh-muc dmuc/dnse_lenh.py đọc bản raw trên main, có cache).
CẬP NHẬT HẰNG TUẦN – job "lich_nghi" của Tong ket tuan (20:17 thứ Sáu, trước tuần mới) / bấm tay:
    python cong_cu/ngay_nghi.py --cap_nhat
  1. thư viện `holidays` BẢN MỚI NHẤT (job cài pip -U, không cache): lễ VN T2–T6 năm trước → năm sau (Tết âm lịch, nghỉ
     bù, ngày lễ mới như 24/11 Ngày Văn hoá VN khi thư viện cập nhật)
  2. ngày sở nghỉ THÊM ghi tay: canh_bao/cau_hinh.NGAY_NGHI_GIAO_DICH
  3. đối chiếu PHIÊN THẬT (nến ngày VNINDEX ~120 ngày tới hôm qua): T2–T6 không có phiên → thêm (nghỉ đột xuất); lịch ghi
     nghỉ mà CÓ phiên trong tuần vừa qua → bỏ + báo. Dữ liệu thiếu (< 60 % số phiên dự kiến) → bỏ bước này, cảnh báo.
  4. ngày nghỉ SẮP TỚI đã có trong file mà nguồn 1–2 không còn → GIỮ + cảnh báo (không bao giờ tự bỏ ngày nghỉ tương lai)
  5. quét tin (Google News RSS "nghỉ giao dịch" chứng khoán): ngày T2–T6 sắp tới được nhắc mà chưa có trong lịch → CHỈ BÁO
     (không tự thêm – tin dễ đọc nhầm, thêm nhầm là chặn cả phiên: không xin OTP, không đặt lệnh)
  Có đổi / cảnh báo / tin cần xác nhận / tuần tới có ngày nghỉ → 1 tin Telegram. Mỗi lần ghi "kiem_luc" → đồng hồ nhắn
  khi > HAN_CU ngày chưa cập nhật (job hỏng / không chạy). Lỗi nguồn 1 → mã thoát 1 (đồng hồ báo workflow lỗi) nhưng
  vẫn ghi phần còn lại.
Chỉ thư viện chuẩn ở phần đọc; phần cập nhật dùng thêm `holidays` và (bước 3) canh_bao.du_lieu (pandas, requests).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import unescape

VN = timezone(timedelta(hours=7))
FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ngay_nghi.json")
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAN_CU = 15                                                         # ngày – quá hạn chưa cập nhật → đồng hồ nhắn
SO_NGAY_DU_LIEU, SO_NGAY_TIN, BO_GAN = 120, 120, 8                   # BO_GAN: chỉ bỏ ngày "nghỉ mà có phiên" ≤ 8 ngày qua
TU_KHOA_TIN = '"nghỉ giao dịch" chứng khoán'
# Dự phòng khi file hỏng / thiếu (= file lúc tạo, 24/11/2026): lễ T2–T6 của thư viện + NGAY_NGHI_GIAO_DICH 2026–2027.
DU_PHONG = {
    "2026-01-01": "Tết Dương lịch", "2026-01-02": "Sở nghỉ thêm", "2026-02-16": "Giao thừa Tết Nguyên Đán",
    "2026-02-17": "Tết Nguyên Đán", "2026-02-18": "Mùng hai Tết Nguyên Đán", "2026-02-19": "Mùng ba Tết Nguyên Đán",
    "2026-02-20": "Mùng bốn Tết Nguyên Đán", "2026-04-27": "Ngày Giỗ Tổ Hùng Vương (nghỉ bù)",
    "2026-04-30": "Ngày Chiến thắng", "2026-05-01": "Ngày Quốc tế Lao động", "2026-08-31": "Ngày nghỉ (thay cho 22/08/2026)",
    "2026-09-01": "Quốc khánh", "2026-09-02": "Quốc khánh", "2026-11-24": "Ngày Văn hóa Việt Nam",
    "2027-01-01": "Tết Dương lịch", "2027-02-04": "Tết Nguyên Đán", "2027-02-05": "Tết Nguyên Đán",
    "2027-02-08": "Tết Nguyên Đán", "2027-02-09": "Tết Nguyên Đán", "2027-02-10": "Tết Nguyên Đán",
    "2027-04-16": "Ngày Giỗ Tổ Hùng Vương", "2027-04-30": "Ngày Chiến thắng", "2027-05-03": "Ngày Quốc tế Lao động (nghỉ bù)",
    "2027-09-02": "Quốc khánh", "2027-09-03": "Quốc khánh", "2027-11-24": "Ngày Văn hóa Việt Nam"}


# ---------------------------------------------------------------- đọc (thư viện chuẩn)
def doc_file(file=FILE):
    """→ dict JSON {"kiem_luc", "thu_vien", "ngay": {ngày: tên}} | None (thiếu / hỏng)."""
    try:
        with open(file, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d.get("ngay"), dict) and d["ngay"] else None
    except (OSError, ValueError, AttributeError):
        return None


def doc(file=FILE):
    """{ngày 'YYYY-MM-DD': tên} – file; thiếu / hỏng → DU_PHONG."""
    d = doc_file(file)
    return dict(d["ngay"]) if d else dict(DU_PHONG)


def nghi(t, lich=None):
    """t (date / datetime; có múi giờ → đổi giờ VN) là T7 / CN / ngày nghỉ trong lịch?"""
    if isinstance(t, datetime) and t.tzinfo:
        t = t.astimezone(VN)
    return t.weekday() >= 5 or f"{t:%Y-%m-%d}" in (doc() if lich is None else lich)


def tuoi(file=FILE, bay_gio=None):
    """Số ngày từ lần cập nhật cuối (kiem_luc) | None (không đọc được)."""
    d = doc_file(file)
    try:
        luc = datetime.strptime(d["kiem_luc"][:10], "%Y-%m-%d").date()
    except (TypeError, KeyError, ValueError):
        return None
    return ((bay_gio or datetime.now(VN)).date() - luc).days


# ---------------------------------------------------------------- nguồn
def tu_thu_vien(nam_ds):
    """Lễ VN T2–T6 của thư viện `holidays` → ({ngày: tên}, 'holidays x.y')."""
    import holidays
    lich = {}
    for d, ten in sorted(holidays.country_holidays("VN", years=list(nam_ds)).items()):
        if d.weekday() < 5:
            lich[f"{d:%Y-%m-%d}"] = ten
    return lich, f"holidays {getattr(holidays, '__version__', '?')}"


def tu_cau_hinh():
    """canh_bao/cau_hinh.NGAY_NGHI_GIAO_DICH (đọc chữ – không import cả gói canh_bao)."""
    with open(os.path.join(GOC, "canh_bao", "cau_hinh.py"), encoding="utf-8") as f:
        m = re.search(r"^NGAY_NGHI_GIAO_DICH\s*=\s*\[([^\]]*)\]", f.read(), re.M)
    return sorted(set(re.findall(r"\d{4}-\d{2}-\d{2}", m.group(1)))) if m else []


def phien_vnindex(hom_nay, so_ngay=SO_NGAY_DU_LIEU):
    """Ngày có phiên thật (nến ngày VNINDEX) từ hom_nay − so_ngay → [ 'YYYY-MM-DD' ] | None (lỗi)."""
    sys.path.insert(0, GOC)
    import pandas as pd
    from canh_bao.du_lieu import tai
    df = tai("VNINDEX", "D", pd.Timestamp(hom_nay) - pd.Timedelta(days=so_ngay + 10), chi_so=True)
    return sorted({f"{x:%Y-%m-%d}" for x in df.index}) if df is not None and len(df) else None


_NGAY = re.compile(r"(?<![\d/])(\d{1,2})\s*[/-]\s*(\d{1,2})(?:\s*[/-]\s*(\d{4}))?(?![\d/])")
_KHOANG = re.compile(r"từ[^\d]{0,30}(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?[^\d]{1,40}?(?:đến|tới|-|–)[^\d]{0,30}"
                     r"(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{4}))?", re.I)


def _ngay_tu(d, m, y, hom_nay):
    """(ngày, tháng, năm | None) → date gần nhất ≥ hom_nay − 7 (năm thiếu: năm nay hoặc năm sau) | None."""
    try:
        d, m = int(d), int(m)
        if y:
            return date(int(y), m, d)
        for nam in (hom_nay.year, hom_nay.year + 1):
            x = date(nam, m, d)
            if x >= hom_nay - timedelta(days=7):
                return x
    except ValueError:
        return None
    return None


def quet_tin(xml, hom_nay, so_ngay=SO_NGAY_TIN):
    """RSS (Google News) → {ngày T2–T6 trong [hom_nay, +so_ngay]: tiêu đề} – chỉ mục có chữ "nghỉ" và "giao dịch" /
    "chứng khoán"; khoảng "từ dd/mm đến dd/mm" → mọi T2–T6 ở giữa (≤ 15 ngày)."""
    ra = {}
    for muc in re.findall(r"<item>(.*?)</item>", xml or "", re.S):
        tieu = unescape(re.sub(r"<[^>]+>", " ", unescape((re.search(r"<title>(.*?)</title>", muc, re.S) or [None, ""])[1])))
        mo_ta = unescape(re.sub(r"<[^>]+>", " ", unescape((re.search(r"<description>(.*?)</description>", muc, re.S)
                                                             or [None, ""])[1])))
        chu = f"{tieu} {mo_ta}"
        thuong = chu.lower()
        if "nghỉ" not in thuong or not ("giao dịch" in thuong or "chứng khoán" in thuong):
            continue
        ds = []
        for k in _KHOANG.finditer(chu):
            a, b = _ngay_tu(k[1], k[2], k[3], hom_nay), _ngay_tu(k[4], k[5], k[6] or k[3], hom_nay)
            if a and b and 0 <= (b - a).days <= 15:
                ds += [a + timedelta(days=i) for i in range((b - a).days + 1)]
        ds += [x for x in (_ngay_tu(*g, hom_nay) for g in _NGAY.findall(chu)) if x]
        for x in ds:
            if x.weekday() < 5 and hom_nay <= x <= hom_nay + timedelta(days=so_ngay):
                ra.setdefault(f"{x:%Y-%m-%d}", tieu.strip()[:120])
    return ra


def lay_tin(tu_khoa=TU_KHOA_TIN):
    url = ("https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": tu_khoa, "hl": "vi", "gl": "VN",
                                                                            "ceid": "VN:vi"}))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (lich-nghi)"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


# ---------------------------------------------------------------- gộp
def cap_nhat(cu, hom_nay, thu_vien, tay, phien=None, tin=None, so_ngay=SO_NGAY_DU_LIEU):
    """Gộp nguồn (docstring) → (lịch mới {ngày: tên}, [dòng báo]). cu: lịch cũ; thu_vien: {ngày: tên} | None (lỗi);
    tay: [ngày]; phien: [ngày có phiên] | None; tin: {ngày: tiêu đề} | None. Hàm thuần – không đọc / ghi gì."""
    hn = f"{hom_nay:%Y-%m-%d}"
    tu_nam = f"{hom_nay.year - 1}"
    lich, bao = {}, []
    for d, ten in (thu_vien or {}).items():
        lich[d] = ten
    for d in tay:
        lich.setdefault(d, "Sở nghỉ thêm (cau_hinh)")
    for d, ten in cu.items():                                       # không tự bỏ ngày nghỉ đã biết
        if d not in lich:
            lich[d] = ten
            if d >= hn and thu_vien is not None:
                bao.append(f"⚠ {_dd(d)} ({ten}): thư viện / cấu hình không còn – vẫn giữ là ngày nghỉ, kiểm lại tay")
    if phien is not None:
        co = set(phien)
        dau, cuoi = hom_nay - timedelta(days=so_ngay), hom_nay - timedelta(days=1)
        ngay_thuong = [dau + timedelta(days=i) for i in range((cuoi - dau).days + 1)]
        ngay_thuong = [f"{x:%Y-%m-%d}" for x in ngay_thuong if x.weekday() < 5]
        du_kien = [x for x in ngay_thuong if x not in lich]
        that = [x for x in ngay_thuong if x in co]
        if not ngay_thuong or len(that) < 0.6 * max(len(du_kien), 1) or max(co, default="") < f"{dau:%Y-%m-%d}":
            bao.append(f"⚠ Dữ liệu VNINDEX thiếu ({len(that)}/{len(du_kien)} phiên) – bỏ đối chiếu phiên thật")
        else:
            dau_dl = min(x for x in co if x >= f"{dau:%Y-%m-%d}")       # chỉ xét từ phiên đầu có dữ liệu
            for x in ngay_thuong:
                if x < dau_dl:
                    continue
                if x not in co and x not in lich:
                    lich[x] = "Không có phiên (dữ liệu VNINDEX)"
                    bao.append(f"➕ {_dd(x)}: không có phiên mà lịch không ghi nghỉ – đã thêm (nghỉ ngoài lịch)")
                elif x in co and x in lich and x >= f"{hom_nay - timedelta(days=BO_GAN):%Y-%m-%d}":
                    bao.append(f"➖ {_dd(x)} ({lich.pop(x)}): lịch ghi nghỉ nhưng CÓ phiên – đã bỏ")   # chỉ tuần vừa qua
                    # (cũ hơn: thư viện vẫn ghi → tuần nào cũng thêm lại / bỏ / báo – để nguyên, đếm phiên đã theo dữ liệu)
    lich = {d: lich[d] for d in sorted(lich) if d >= tu_nam}
    for d, tieu in sorted((tin or {}).items()):
        if d not in lich:
            bao.append(f"❓ Tin nhắc nghỉ giao dịch {_dd(d)} – chưa có trong lịch: “{tieu}” → đúng thì thêm vào "
                       "canh_bao/cau_hinh.NGAY_NGHI_GIAO_DICH")
    return lich, bao


def _dd(d):
    x = datetime.strptime(d, "%Y-%m-%d")
    return f"{['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'][x.weekday()]} {x:%d/%m/%Y}"


def tin_tele(cu, moi, bao, hom_nay, so_ngay_toi=10):
    """Nội dung Telegram | None (không có gì đáng báo): đổi lịch, cảnh báo, ngày nghỉ ~10 ngày tới."""
    them = sorted(set(moi) - set(cu))
    bo = sorted(set(cu) - set(moi))
    toi = [d for d in sorted(moi) if f"{hom_nay:%Y-%m-%d}" < d <= f"{hom_nay + timedelta(days=so_ngay_toi):%Y-%m-%d}"]
    if not (them or bo or bao or toi):
        return None
    dong = ["📅 Lịch nghỉ giao dịch (HOSE/HNX)"]
    dong += [f"Sắp nghỉ: " + " · ".join(f"{_dd(d)} ({moi[d]})" for d in toi)] if toi else []
    dong += [f"+ thêm {len(them)}: " + ", ".join(_dd(d) for d in them[:12]) + (" …" if len(them) > 12 else "")] if them else []
    dong += [f"− bỏ {len(bo)}: " + ", ".join(_dd(d) for d in bo[:12])] if bo else []
    return "\n".join(dong + bao)


# ---------------------------------------------------------------- chạy
def chay_cap_nhat(hom_nay=None, file=FILE, gui=None, in_ra=print, lay_phien=phien_vnindex, lay_tin_=lay_tin):
    """→ mã thoát: 0 · 1 (thư viện `holidays` lỗi – vẫn ghi phần còn lại)."""
    hom_nay = hom_nay or datetime.now(VN).date()
    cu_file = doc_file(file)
    cu = dict(cu_file["ngay"]) if cu_file else dict(DU_PHONG)
    ma = 0
    try:
        tv, ban = tu_thu_vien(range(hom_nay.year - 1, hom_nay.year + 2))
    except Exception as e:                                          # noqa: BLE001 – nguồn chính lỗi: báo, vẫn chạy tiếp
        tv, ban, ma = None, f"lỗi {type(e).__name__}", 1
        in_ra(f"::error::Thư viện holidays lỗi ({type(e).__name__}: {str(e)[:80]})")
    try:
        tay = tu_cau_hinh()
    except OSError:
        tay = []
    try:
        phien = lay_phien(hom_nay)
    except Exception as e:                                          # noqa: BLE001 – nguồn phụ
        phien = None
        in_ra(f"⚠ Không tải được VNINDEX ({type(e).__name__}) – bỏ đối chiếu phiên thật")
    try:
        tin = quet_tin(lay_tin_(), hom_nay)
    except Exception as e:                                          # noqa: BLE001 – nguồn phụ
        tin = None
        in_ra(f"⚠ Không đọc được tin ({type(e).__name__}) – bỏ quét tin")
    moi, bao = cap_nhat(cu, hom_nay, tv, tay, phien, tin)
    if tv is None:
        bao.insert(0, "⚠ Thư viện holidays lỗi – lịch chỉ từ cấu hình + file cũ + dữ liệu")
    out = {"kiem_luc": f"{datetime.now(VN):%Y-%m-%d %H:%M}", "thu_vien": ban,
           "nguon": {"thu_vien": len(tv or {}), "cau_hinh": len(tay), "phien_vnindex": len(phien or []),
                     "tin_ung_vien": len(tin or {})},
           "ngay": moi}
    with open(file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    in_ra(f"Lịch nghỉ: {len(moi)} ngày ({ban}; cấu hình {len(tay)}; phiên VNINDEX {len(phien or [])}; "
          f"tin {len(tin or {})}) · thêm {sorted(set(moi) - set(cu))} · bỏ {sorted(set(cu) - set(moi))}")
    for b in bao:
        in_ra(b)
    noi = tin_tele(cu, moi, bao, hom_nay)
    if noi and gui:
        gui(noi)
    return ma


def main(argv=None):
    p = argparse.ArgumentParser(description="Lịch nghỉ giao dịch HOSE/HNX – đọc / cập nhật cong_cu/ngay_nghi.json")
    p.add_argument("--cap_nhat", action="store_true", help="cập nhật từ thư viện holidays + cấu hình + VNINDEX + tin")
    p.add_argument("--khong_gui", action="store_true")
    a = p.parse_args(argv)
    if a.cap_nhat:
        gui = None
        if not a.khong_gui:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from dong_ho import nhan_tele
            gui = lambda t: nhan_tele(t, "chinh")                    # noqa: E731
        return chay_cap_nhat(gui=gui)
    hn = datetime.now(VN).date()
    for d, ten in sorted(doc().items()):
        if d >= f"{hn:%Y-%m-%d}":
            print(_dd(d), ten)
    return 0


if __name__ == "__main__":
    sys.exit(main())
