# -*- coding: utf-8 -*-
"""
CỤC THỐNG KÊ (nso.gov.vn) – báo cáo tình hình kinh tế – xã hội hằng tháng / quý: đọc SỐ từ chữ của báo cáo (26/11/2026, chủ quỹ:
"tìm thêm nguồn"). Nguồn gốc của phần lớn số vĩ mô VN (FireAnt / TradingView ECONOMICS cũng lấy từ đây) nhưng MỚI HƠN
TradingView (xuất nhập khẩu TradingView mới tới T7 khi báo cáo đã có T10). Máy GitHub vào được (dò 26/11/2026).

Đọc: CPI (so tháng trước / tháng 12 / cùng kỳ, bình quân), lạm phát cơ bản bình quân, chỉ số giá vàng / USD, IIP, bán lẻ, xuất
khẩu / nhập khẩu / cán cân, vốn đầu tư ngân sách (tháng, lũy kế, % kế hoạch), doanh nghiệp thành lập mới / quay lại / tạm ngừng,
khách quốc tế, FDI (đăng ký, thực hiện); báo cáo quý thêm GDP và 3 khu vực, tỷ lệ thất nghiệp. Mẫu câu có thể đổi theo năm → mỗi
chỉ tiêu là một mẫu riêng, không khớp thì bỏ (không đoán). Kiểm chéo với TradingView ở vi_mo_web (in log).
"""
import html as _html
import re

import pandas as pd

DS = "https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/"
_SO = r"([\d.]+(?:,\d+)?)"
_TG = r"(tăng|giảm)"
_THANG = r"tháng [^\s,]+(?: (?:một|hai))?"                        # "tháng Mười", "tháng Mười một", "tháng 10"


def so(x):
    """ "1.010,55" → 1010.55."""
    return float(x.replace(".", "").replace(",", "."))


def dau(tg, x):
    return so(x) * (-1 if tg == "giảm" else 1)


def chu(html):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t))


def ky_tu_url(url):
    """URL báo cáo → (tháng số liệu – Timestamp ngày 1, quý?). Năm theo thư mục đăng (báo cáo tháng M đăng đầu tháng M+1)."""
    m = re.search(r"/(\d{4})/(\d{2})/[^/]*?(?:-va-|-)(\d{1,2})-thang(?:-dau)?-nam", url)
    if not m:                                                         # thông cáo quý: "...-quy-iii-nam-2026"
        q = re.search(r"-quy-(iv|iii|ii|i)-nam-(\d{4})", url)
        if not q:
            return None, False
        return pd.Timestamp(year=int(q.group(2)), month={"i": 3, "ii": 6, "iii": 9, "iv": 12}[q.group(1)], day=1), True
    nam_dang, thang_dang, th = int(m.group(1)), int(m.group(2)), int(m.group(3))
    nam = nam_dang if thang_dang > th else nam_dang - 1
    return pd.Timestamp(year=nam, month=th, day=1), "-quy-" in url


def danh_sach(lay, trang=3):
    """lay(url) → html. → [(url, tháng, quý?)] mới nhất trước (không trùng)."""
    out, thay = [], set()
    for p in range(1, trang + 1):
        u = DS if p == 1 else f"{DS}page/{p}/"
        try:
            t = lay(u)
        except Exception:                                            # noqa: BLE001 – hết trang / lỗi → dừng
            break
        for x in re.findall(r'href="(https://www\.nso\.gov\.vn/[^"]*kinh-te-xa-hoi-(?:thang|quy)[^"]*)"', t):
            if x in thay:
                continue
            thay.add(x)
            ky, quy = ky_tu_url(x)
            if ky is not None:
                out.append((x, ky, quy))
    out.sort(key=lambda r: r[1], reverse=True)
    return out


MAU = {
    # khoá: (mẫu, hàm → giá trị)  – mỗi mẫu bắt MỘT câu đặc trưng của báo cáo
    "cpi_mom": (rf"Chỉ số giá tiêu dùng \(CPI\) {_THANG} {_TG} {_SO}% so với tháng trước", lambda g: dau(g[0], g[1])),
    "cpi_ytd": (rf"Chỉ số giá tiêu dùng \(CPI\) {_THANG} {_TG} {_SO}% so với tháng trước; {_TG} {_SO}% so với tháng 12",
                lambda g: dau(g[2], g[3])),
    "cpi_yoy": (rf"Chỉ số giá tiêu dùng \(CPI\) {_THANG} {_TG} {_SO}% so với tháng trước; {_TG} {_SO}% so với tháng 12/\d{{4}} "
                rf"và {_TG} {_SO}% so với cùng kỳ", lambda g: dau(g[4], g[5])),
    "cpi_bq": (rf"[Bb]ình quân [^,]{{0,40}}, CPI {_TG} {_SO}% so với cùng kỳ", lambda g: dau(g[0], g[1])),
    "lp_cb_bq": (rf"lạm phát cơ bản {_TG} {_SO}%", lambda g: dau(g[0], g[1])),
    "vang_mom": (rf"Chỉ số giá vàng {_THANG} {_TG} {_SO}% so với tháng trước", lambda g: dau(g[0], g[1])),
    "vang_yoy": (rf"Chỉ số giá vàng {_THANG} {_TG} {_SO}% so với tháng trước; {_TG} {_SO}% so với cùng kỳ",
                 lambda g: dau(g[2], g[3])),
    "usd_mom": (rf"Chỉ số giá đô la Mỹ {_THANG} {_TG} {_SO}% so với tháng trước", lambda g: dau(g[0], g[1])),
    "usd_yoy": (rf"Chỉ số giá đô la Mỹ {_THANG} {_TG} {_SO}% so với tháng trước; {_TG} {_SO}% so với cùng kỳ",
                lambda g: dau(g[2], g[3])),
    "iip_yoy": (rf"Chỉ số sản xuất toàn ngành công nghiệp \(IIP\) {_THANG} (?:ước tính |ước )?{_TG} {_SO}% so với tháng trước "
                rf"và {_TG} {_SO}% so với cùng kỳ", lambda g: dau(g[2], g[3])),
    "ban_le": (rf"Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành {_THANG} (?:ước tính |ước )?đạt "
               rf"{_SO} nghìn tỷ đồng", lambda g: so(g[0])),
    "ban_le_yoy": (rf"Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành {_THANG} (?:ước tính |ước )?đạt "
                   rf"{_SO} nghìn tỷ đồng, {_TG} {_SO}% so với tháng trước và {_TG} {_SO}% so với cùng kỳ",
                   lambda g: dau(g[3], g[4])),
    "xk": (rf"Xuất khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD", lambda g: so(g[0])),
    "xk_yoy": (rf"Xuất khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD, {_TG} {_SO}% so với tháng trước và {_TG} "
               rf"{_SO}% so với cùng kỳ", lambda g: dau(g[3], g[4])),
    "nk": (rf"[Nn]hập khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD", lambda g: so(g[0])),
    "nk_yoy": (rf"[Nn]hập khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD, {_TG} {_SO}% so với tháng trước và {_TG} "
               rf"{_SO}% so với cùng kỳ", lambda g: dau(g[3], g[4])),
    "can_can": (rf"cán cân thương mại hàng hóa {_THANG} (?:ước tính |ước )?(xuất siêu|nhập siêu) {_SO} tỷ USD",
                lambda g: so(g[1]) * (1 if g[0] == "xuất siêu" else -1)),
    "nsnn": (rf"Vốn đầu tư thực hiện từ nguồn ngân sách [Nn]hà nước {_THANG} (?:ước tính |ước )?đạt {_SO} nghìn tỷ đồng",
             lambda g: so(g[0])),
    "nsnn_yoy": (rf"Vốn đầu tư thực hiện từ nguồn ngân sách [Nn]hà nước {_THANG} (?:ước tính |ước )?đạt {_SO} nghìn tỷ đồng, "
                 rf"{_TG} {_SO}% so với cùng kỳ", lambda g: dau(g[1], g[2])),
    "nsnn_lk": (rf"vốn đầu tư thực hiện từ nguồn ngân sách [Nn]hà nước (?:ước tính |ước )?đạt {_SO} nghìn tỷ đồng, bằng {_SO}% "
                rf"kế hoạch năm", lambda g: so(g[0])),
    "nsnn_kh": (rf"vốn đầu tư thực hiện từ nguồn ngân sách [Nn]hà nước (?:ước tính |ước )?đạt {_SO} nghìn tỷ đồng, bằng {_SO}% "
                rf"kế hoạch năm", lambda g: so(g[1])),
    "dn_moi": (r"cả nước có (?:gần |hơn |khoảng )?([\d.,]+) (nghìn )?doanh nghiệp thành lập mới",
               lambda g: so(g[0]) * (1000 if g[1] else 1)),
    "dn_quay_lai": (r"(?:gần |hơn |khoảng )?([\d.,]+) (nghìn )?doanh nghiệp quay trở lại hoạt động",
                    lambda g: so(g[0]) * (1000 if g[1] else 1)),
    "dn_tam_ngung": (r"có (?:gần |hơn |khoảng )?([\d.,]+) (nghìn )?doanh nghiệp đăng ký tạm ngừng kinh doanh",
                     lambda g: so(g[0]) * (1000 if g[1] else 1)),
    "khach": (rf"[Kk]hách quốc tế đến nước ta {_THANG} (?:ước tính |ước )?đạt (?:gần |hơn )?{_SO} (triệu |nghìn )?lượt",
              lambda g: so(g[0]) * (1e6 if g[1] == "triệu " else 1e3 if g[1] == "nghìn " else 1)),
    "fdi_th": (rf"[Vv]ốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam [^.]{{0,80}}?(?:ước tính |ước )?đạt {_SO} tỷ USD",
               lambda g: so(g[0])),
    "fdi_dk": (rf"[Tt]ổng vốn đầu tư nước ngoài đăng ký vào Việt Nam [^.]{{0,160}}?đạt {_SO} tỷ USD", lambda g: so(g[0])),
    # báo cáo quý
    "gdp_nn": (rf"khu vực nông, lâm nghiệp và thủy sản tăng {_SO}%", lambda g: so(g[0])),
    "gdp_cn": (rf"khu vực công nghiệp và xây dựng tăng {_SO}%", lambda g: so(g[0])),
    "gdp_dv": (rf"khu vực dịch vụ tăng {_SO}%", lambda g: so(g[0])),
    "that_nghiep": (rf"[Tt]ỷ lệ thất nghiệp (?:của )?lực lượng lao động trong độ tuổi quý [IVX]+(?:/| năm )\d{{4}} "
                    rf"(?:là |ước tính là |khoảng )?{_SO}%", lambda g: so(g[0])),
}
MAU["gdp_yoy"] = (rf"(?:Tổng sản phẩm trong nước \(GDP\)|GDP) quý [IVX]+(?:/| năm )\d{{4}} (?:ước tính |ước )?tăng {_SO}% "
                  rf"so với cùng kỳ", lambda g: so(g[0]))


def doc(text):
    """Chữ báo cáo → {khoá: giá trị} (chỉ khoá khớp mẫu)."""
    out = {}
    for k, (mau, f) in MAU.items():
        m = re.search(mau, text)
        if m:
            try:
                out[k] = round(float(f(m.groups())), 4)
            except (ValueError, IndexError):
                pass
    return out


def tai(lay, trang=3, so_bc=24):
    """→ DataFrame tháng × khoá (mới nhất cuối) từ tối đa so_bc báo cáo gần nhất. lay(url) → html."""
    hang = {}
    for url, ky, quy in danh_sach(lay, trang)[:so_bc]:
        try:
            d = doc(chu(lay(url)))
        except Exception:                                            # noqa: BLE001 – một báo cáo lỗi không hỏng cả lượt
            continue
        if d:
            hang.setdefault(ky, {}).update({k: v for k, v in d.items() if k not in hang.get(ky, {})})
    return pd.DataFrame.from_dict(hang, orient="index").sort_index()
