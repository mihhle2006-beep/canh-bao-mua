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
import unicodedata

import pandas as pd

DS = "https://www.nso.gov.vn/bao-cao-tinh-hinh-kinh-te-xa-hoi-hang-thang/"
_SO = r"([\d.]+(?:,\d+)?)"
_TG = r"(tăng|giảm)"
_THANG = r"tháng [^\s,]+(?: (?:[Mm]ột|[Hh]ai))?(?: năm \d{4})?"   # "tháng Mười", "tháng Mười Một", "tháng Chín năm 2026"


def so(x):
    """ "1.010,55" → 1010.55."""
    return float(x.replace(".", "").replace(",", "."))


def dau(tg, x):
    return so(x) * (-1 if tg == "giảm" else 1)


def chu(html):
    """HTML → chữ một dòng: dựng sẵn dấu (NFC – trang có chỗ gõ dấu tổ hợp), bỏ ký tự vô hình, gộp khoảng trắng."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = unicodedata.normalize("NFC", _html.unescape(t))
    return re.sub(r"\s+", " ", re.sub(r"[\u200b-\u200d\u2060\ufeff\u00ad]", "", t))


_TU = {"mot": 1, "hai": 2, "ba": 3, "tu": 4, "nam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9, "muoi": 10, "muoi-mot": 11,
       "muoi-hai": 12}


def ky_tu_url(url):
    """URL báo cáo → (tháng số liệu – Timestamp ngày 1, quý?). Tháng: "-va-N-thang" / "-quy-ii-" / "thang-mot-nam-…" (chữ);
    năm theo thư mục đăng (báo cáo tháng M đăng đầu tháng M+1 – slug có khi ghi sai năm, vd "…-nam-2025-2" đăng 06/2026)."""
    f = re.search(r"/(\d{4})/(\d{2})/([^/?#]+)/?$", url)
    if not f or "kinh-te-xa-hoi" not in f.group(3):
        return None, False
    nam_dang, thang_dang, slug = int(f.group(1)), int(f.group(2)), f.group(3)
    m = re.search(r"(?:-va-|-)(\d{1,2})-thang(?:-dau)?-nam", slug)
    q = re.search(r"-quy-(iv|iii|ii|i)-", slug)
    w = re.search(r"kinh-te-xa-hoi-thang-(muoi-hai|muoi-mot|muoi|mot|hai|ba|tu|nam|sau|bay|tam|chin)-", slug)
    if m:
        th = int(m.group(1))
    elif q:
        th = {"i": 3, "ii": 6, "iii": 9, "iv": 12}[q.group(1)]
    elif w:
        th = _TU[w.group(1)]
    else:
        return None, False
    if not 1 <= th <= 12:
        return None, False
    nam = nam_dang if thang_dang >= th else nam_dang - 1
    return pd.Timestamp(year=nam, month=th, day=1), bool(q)


def danh_sach(lay, trang=3):
    """lay(url) → html. → [(url, tháng, quý?)] mới nhất trước (không trùng)."""
    out, thay = [], set()
    for p in range(1, trang + 1):
        u = DS if p == 1 else f"{DS}?paged={p}"                      # phân trang "?paged=N" ("/page/N/" trả lại trang 1)
        try:
            t = lay(u)
        except Exception:                                            # noqa: BLE001 – hết trang / lỗi → dừng
            break
        moi = 0
        for x in re.findall(r'href="(https://www\.nso\.gov\.vn/[^"]*kinh-te-xa-hoi-(?:thang|quy)[^"]*)"', t):
            if x in thay:
                continue
            thay.add(x)
            ky, quy = ky_tu_url(x)
            if ky is not None:
                out.append((x, ky, quy))
                moi += 1
        if not moi:
            break                                                     # trang không thêm báo cáo nào → hết
    out.sort(key=lambda r: r[1], reverse=True)
    return out


MAU = {
    # khoá: (mẫu, hàm → giá trị)  – mỗi mẫu bắt MỘT câu đặc trưng của báo cáo
    # chỉ số giá CPI / vàng / USD: đọc theo ĐOẠN (_gia) – câu đổi thứ tự / tách câu theo từng tháng
    "cpi_bq": (rf"(?:[Bb]ình quân|Tính chung) [^,]{{0,40}}, CPI {_TG} {_SO}% so với cùng kỳ", lambda g: dau(g[0], g[1])),
    "lp_cb_bq": (rf"lạm phát cơ bản {_TG} {_SO}%", lambda g: dau(g[0], g[1])),
    "iip_yoy": (rf"Chỉ số sản xuất (?:toàn ngành )?công nghiệp \(IIP\) {_THANG} (?:ước tính |ước )?{_TG} {_SO}% so với tháng trước "
                rf"và {_TG} {_SO}% so với cùng kỳ", lambda g: dau(g[2], g[3])),
    "ban_le": (rf"Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành {_THANG} (?:ước tính |ước )?đạt "
               rf"{_SO} nghìn tỷ đồng", lambda g: so(g[0])),
    "ban_le_yoy": (rf"Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành {_THANG} (?:ước tính |ước )?đạt "
                   rf"{_SO} nghìn tỷ đồng, {_TG} {_SO}% so với tháng trước và {_TG} {_SO}% so với cùng kỳ",
                   lambda g: dau(g[3], g[4])),
    "xk": (rf"(?:[Kk]im ngạch )?[Xx]uất khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD", lambda g: so(g[0])),
    "xk_yoy": (rf"(?:[Kk]im ngạch )?[Xx]uất khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD, {_TG} {_SO}% so với tháng trước và {_TG} "
               rf"{_SO}% so với cùng kỳ", lambda g: dau(g[3], g[4])),
    "nk": (rf"[Nn]hập khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD", lambda g: so(g[0])),
    "nk_yoy": (rf"[Nn]hập khẩu hàng hóa {_THANG} (?:ước tính |ước )?đạt {_SO} tỷ USD, {_TG} {_SO}% so với tháng trước và {_TG} "
               rf"{_SO}% so với cùng kỳ", lambda g: dau(g[3], g[4])),
    "can_can": (rf"[Cc]án cân thương mại hàng hóa {_THANG} (?:ước tính |ước )?(xuất siêu|nhập siêu) {_SO} tỷ USD",
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
    "khach": (rf"[Kk]hách quốc tế đến nước ta (?:{_THANG} )?(?:ước tính |ước )?đạt (?:gần |hơn )?{_SO} (triệu |nghìn )?lượt",
              lambda g: so(g[0]) * (1e6 if g[1] == "triệu " else 1e3 if g[1] == "nghìn " else 1)),
    "fdi_th": (rf"[Vv]ốn đầu tư trực tiếp nước ngoài thực hiện tại Việt Nam [^.]{{0,80}}?(?:ước tính |ước )?đạt {_SO} tỷ USD",
               lambda g: so(g[0])),
    "fdi_dk": (rf"[Tt]ổng vốn đầu tư nước ngoài đăng ký vào Việt Nam [^.]{{0,160}}?đạt {_SO} tỷ USD", lambda g: so(g[0])),
    # thu / chi NSNN lũy kế từ đầu năm (câu "…đạt X nghìn tỷ đồng, bằng Y% dự toán năm" – span không qua dấu chấm câu, không
    # vắt sang câu bên kia: tiêu đề "Thu, chi ngân sách Nhà nước Tổng thu …" từng làm chi bắt số của thu – báo cáo 10/2025)
    "thu_lk": (rf"[Tt]ổng thu ngân sách [Nn]hà nước (?:(?!chi ngân sách)[^.])*?đạt {_SO} nghìn tỷ đồng, bằng {_SO}% dự toán",
               lambda g: so(g[0])),
    "thu_dt": (rf"[Tt]ổng thu ngân sách [Nn]hà nước (?:(?!chi ngân sách)[^.])*?đạt {_SO} nghìn tỷ đồng, bằng {_SO}% dự toán",
               lambda g: so(g[1])),
    "chi_lk": (rf"chi ngân sách [Nn]hà nước (?:(?!thu ngân sách)[^.])*?đạt {_SO} nghìn tỷ đồng, bằng {_SO}% dự toán",
               lambda g: so(g[0])),
    "chi_dt": (rf"chi ngân sách [Nn]hà nước (?:(?!thu ngân sách)[^.])*?đạt {_SO} nghìn tỷ đồng, bằng {_SO}% dự toán",
               lambda g: so(g[1])),
    "dn_rut_lui": (rf"[Ss]ố doanh nghiệp rút lui khỏi thị trường là (?:gần |hơn |khoảng )?{_SO} nghìn doanh nghiệp",
                   lambda g: so(g[0]) * 1000),
    # báo cáo quý
    "gdp_nn": (rf"khu vực nông, lâm nghiệp và thủy sản tăng {_SO}%", lambda g: so(g[0])),
    "gdp_cn": (rf"khu vực công nghiệp và xây dựng tăng {_SO}%", lambda g: so(g[0])),
    "gdp_dv": (rf"khu vực dịch vụ tăng {_SO}%", lambda g: so(g[0])),
    "that_nghiep": (rf"[Tt]ỷ lệ thất nghiệp (?:của )?lực lượng lao động trong độ tuổi quý [IVX]+(?:/| năm )\d{{4}} "
                    rf"(?:là |ước tính là |khoảng )?{_SO}%", lambda g: so(g[0])),
}
MAU["gdp_yoy"] = (rf"(?:Tổng sản phẩm trong nước \(GDP\)|GDP) quý [IVX]+(?:/| năm )\d{{4}} (?:ước tính |ước )?tăng {_SO}% "
                  rf"so với cùng kỳ", lambda g: so(g[0]))


_HET_GIA = ("Bình quân", "bình quân", "Tính chung", "lạm phát cơ bản", "Lạm phát cơ bản", " d) ", " b) ")
GIA = {  # tiền tố: (mẫu mở đoạn, chữ kết đoạn thêm)
    "cpi": (r"(?:Chỉ số giá tiêu dùng \(CPI\)|\bCPI) tháng (?=[^.]{0,60}so với tháng trước)", ("Chỉ số giá vàng",)),
    "vang": (r"Chỉ số giá vàng tháng ", ("Chỉ số giá đô la Mỹ",)),
    "usd": (r"Chỉ số giá đô la Mỹ tháng ", ()),
}


def _gia(text):
    """Đoạn chỉ số giá (từ câu mở tới "Bình quân / Tính chung / chỉ số kế tiếp") → {x_mom, x_ytd, x_yoy}: số đầu tiên đứng trước
    "so với tháng trước|tháng <tên tháng>" / "so với tháng 12" / "so với cùng kỳ" trong đoạn."""
    out = {}
    for x, (mo, het) in GIA.items():
        m = re.search(mo, text)
        if not m:
            continue
        d = text[m.start():m.start() + 700]
        for h in _HET_GIA + het:
            j = d.find(h, 20)
            if j > 0:
                d = d[:j]
        for k, sau in (("mom", r"tháng (?!12)[^\s;,.]+"), ("ytd", r"tháng 12"), ("yoy", r"cùng kỳ")):
            g = re.search(rf"{_TG} {_SO}% so với {sau}", d)
            if g:
                out[f"{x}_{k}"] = round(dau(g.group(1), g.group(2)), 4)
    return out


def doc(text):
    """Chữ báo cáo → {khoá: giá trị} (chỉ khoá khớp mẫu)."""
    out = _gia(text)
    for k, (mau, f) in MAU.items():
        m = re.search(mau, text)
        if m:
            try:
                out[k] = round(float(f(m.groups())), 4)
            except (ValueError, IndexError):
                pass
    return out


QUY = ("gdp_yoy", "gdp_nn", "gdp_cn", "gdp_dv", "that_nghiep")


def kiem(df):
    """Bỏ số tự mâu thuẫn: số quý ở tháng không phải cuối quý; doanh nghiệp > 60 nghìn / tháng; xuất khẩu − nhập khẩu phải = cán cân (± 0,1 tỷ USD) – lệch thì bỏ cả 3 của tháng đó; xuất / nhập khẩu
    ngoài 5–150 tỷ USD (bắt nhầm số quý / lũy kế) thì bỏ."""
    df = df.copy()
    quy = [c for c in QUY if c in df]
    if quy:
        df.loc[~df.index.month.isin([3, 6, 9, 12]), quy] = float("nan")   # số quý chỉ ở báo cáo tháng 3 / 6 / 9 / 12
    for c in ("dn_moi", "dn_quay_lai", "dn_tam_ngung"):
        if c in df:
            df.loc[df[c] > 60000, c] = float("nan")                  # bắt nhầm số cộng dồn nhiều tháng
    for c in ("thu_dt", "chi_dt"):
        if c in df:
            df.loc[(df[c] <= 0) | (df[c] > 150), c] = float("nan")     # % dự toán năm ngoài 0–150 → bắt nhầm câu
    for c in ("xk", "nk"):
        if c in df:
            df.loc[(df[c] < 5) | (df[c] > 150), c] = float("nan")
    if {"xk", "nk", "can_can"} <= set(df):
        sai = (df.xk - df.nk - df.can_can).abs() > 0.1
        df.loc[sai, ["xk", "nk", "can_can", "xk_yoy", "nk_yoy"] if "xk_yoy" in df else ["xk", "nk", "can_can"]] = float("nan")
    if "nk" not in df and {"xk", "can_can"} <= set(df):
        df["nk"] = df.xk - df.can_can                               # nhập khẩu = xuất khẩu − cán cân (cùng báo cáo)
    elif {"xk", "can_can"} <= set(df):
        thieu = df.nk.isna() & df.xk.notna() & df.can_can.notna()
        df.loc[thieu, "nk"] = (df.xk - df.can_can)[thieu]
    return df


PHIEN = 4                                                             # tăng khi sửa MAU / _gia → đệm cũ đọc lại


def tai_dem(lay, dem=None, trang=3):
    """Như tai() nhưng nhớ kết quả từng báo cáo (dict url → {khoá: giá trị, "_ky": "YYYY-MM"}) – chỉ tải báo cáo mới. → (df, dem)."""
    dem = dict(dem or {})
    for url, ky, _ in danh_sach(lay, trang):
        if dem.get(url, {}).get("_v") == PHIEN:
            continue                                                 # bộ đọc đổi (PHIEN) → đọc lại
        try:
            d = doc(chu(lay(url)))
        except Exception:                                            # noqa: BLE001 – lượt sau thử lại; giữ bản đọc cũ
            continue                                                 # (26/11: đọc lại cả 40 báo cáo → trang chặn → mất hết)
        dem[url] = {**d, "_ky": f"{ky:%Y-%m}", "_v": PHIEN}
    hang = {}
    for v in dem.values():
        ky = pd.Timestamp(v["_ky"] + "-01")
        for k, x in v.items():
            if k not in ("_ky", "_v") and k not in hang.setdefault(ky, {}):
                hang[ky][k] = x
    df = pd.DataFrame.from_dict(hang, orient="index").sort_index()
    return kiem(df), dem


# ------------------------------------------------------------------ NHNN – dư nợ tín dụng đối với nền kinh tế
NHNN_TD = "https://sbv.gov.vn/du-no-tin-dung-doi-voi-nen-kt-dttktt"


def tin_dung(html):
    """Trang NHNN → [(tháng, tổng dư nợ tỷ đồng, tăng so cuối năm trước %)] (mọi bảng có số thật + dòng TỔNG CỘNG; kỳ là
    "Tháng M năm YYYY" gần nhất phía trước bảng)."""
    out = []
    for m in re.finditer(r"<table.*?</table>", html, re.S):
        b = m.group(0)
        hang = [[chu(c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)] for r in re.findall(r"<tr.*?</tr>", b, re.S)]
        tong = next((h for h in hang if any(x.upper() == "TỔNG CỘNG" for x in h)), None)
        if not tong:
            continue
        so_ = [x for x in tong if re.fullmatch(r"-?[\d.]+(?:,\d+)?", x)]
        if len(so_) < 2:
            continue                                                  # bảng mẫu (chưa điền số)
        truoc = chu(html[max(0, m.start() - 3000):m.start()]) + " " + chu(b[:600])
        ky = re.findall(r"[Tt]háng (\d{1,2}) [Nn]ăm (\d{4})", truoc)
        if not ky:
            continue
        th, nam = ky[-1]
        out.append((pd.Timestamp(year=int(nam), month=int(th), day=1), so(so_[0]), so(so_[1])))
    return out


# ------------------------------------------------------------------ NHNN – tổng phương tiện thanh toán (M2), tiền gửi dân cư
NHNN_M2 = "https://sbv.gov.vn/vi/tong-phuong-tien-thanh-toan"     # dò 26/11/2026 (vi_mo_nguon.do_vn9): chỉ tháng mới nhất


def m2(html):
    """Trang NHNN → [(tháng, M2 tỷ đồng, M2 tăng so cuối năm trước %, tiền gửi dân cư tăng %)]; kỳ = "Tháng M năm YYYY" gần nhất phía trước."""
    t, out = chu(html), []
    for m in re.finditer(rf"Tổng phương tiện thanh toán\W{{0,6}}{_SO} (-?[\d,]+).{{0,160}}?Tiền gửi của dân cư {_SO} (-?[\d,]+)", t):
        ky = re.findall(r"[Tt]háng (\d{1,2}) năm (\d{4})", t[max(0, m.start() - 400):m.start()])
        if ky:
            out.append((pd.Timestamp(year=int(ky[-1][1]), month=int(ky[-1][0]), day=1), so(m[1]), so(m[2]), so(m[4])))
    return out


# ------------------------------------------------------------------ CafeF – tin vĩ mô (RSS)
CAFEF_RSS = "https://cafef.vn/vi-mo-dau-tu.rss"


def tin_rss(xml, so_tin=10):
    """RSS → [{"t": tiêu đề, "u": đường dẫn, "d": "YYYY-MM-DD HH:MM"}] (chỉ đường dẫn https)."""
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S):
        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
        u = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", it, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
        if not (t and u) or not u.group(1).strip().startswith("https://"):
            continue
        try:
            ngay = pd.Timestamp(d.group(1).strip()).tz_convert("Asia/Ho_Chi_Minh").strftime("%Y-%m-%d %H:%M") if d else ""
        except (ValueError, TypeError):
            ngay = ""
        out.append({"t": _html.unescape(t.group(1)).strip(), "u": u.group(1).strip(), "d": ngay})
        if len(out) >= so_tin:
            break
    return out
