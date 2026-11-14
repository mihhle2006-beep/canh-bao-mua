# -*- coding: utf-8 -*-
"""Bảng thị trường (thi_truong): chuẩn hoá bảng giá, hồ sơ thanh khoản, chuỗi khối ngoại, cờ kỹ thuật, dựng du_lieu.json
từ dữ liệu mẫu (không gọi mạng)."""
import json

import numpy as np
import pytest
import pandas as pd

from thi_truong import dung, nguon, tinh

MAU_VIC = {"listingInfo": {"symbol": "VIC", "ceiling": 250300, "floor": 217700, "refPrice": 234000, "board": "HSX",
                           "type": "STOCK", "listedShare": 7762186429},
           "matchPrice": {"accumulatedValue": 174310.42, "accumulatedVolume": 733000, "foreignBuyValue": 68079410000,
                          "foreignSellValue": 45810832800, "highest": 239500, "lowest": 236000, "matchPrice": 237600}}


def _unix(s):
    return str(int((pd.Timestamp(s) - pd.Timedelta(hours=7)).timestamp()))


def _nen_phut(ngay, gt_cuoi):
    """Nến 1' giả: 9:15–11:30 & 13:00–14:45, GT luỹ kế tăng đều tới gt_cuoi (triệu đồng)."""
    t, gt = [], []
    for d, cuoi in zip(ngay, gt_cuoi):
        phut = list(pd.date_range(f"{d} 09:15", f"{d} 11:30", freq="1min")) + \
            list(pd.date_range(f"{d} 13:00", f"{d} 14:45", freq="1min"))
        t += [_unix(x) for x in phut]
        gt += list(np.linspace(cuoi / len(phut), cuoi, len(phut)))
    return {"t": t, "c": [1700.0] * len(t), "o": [1700.0] * len(t), "h": [1701.0] * len(t), "l": [1699.0] * len(t),
            "v": [1] * len(t), "accumulatedValue": gt}


def test_chuan_bang_don_vi_va_trang_thai():
    B = tinh.chuan_bang([MAU_VIC, {"listingInfo": {"symbol": "AAA", "refPrice": 10000, "ceiling": 10700, "floor": 9300,
                                                   "board": "HNX", "type": "STOCK"},
                                   "matchPrice": {"matchPrice": 10700, "highest": 10700, "lowest": 10000}},
                         {"listingInfo": {"symbol": "BBB", "refPrice": 5000, "board": "UPCOM"}, "matchPrice": {}}])
    v = B.loc["VIC"]
    assert v["san"] == "HSX" and abs(v["gt"] - 174.31042) < 1e-6 and abs(v["nn"] - 22.2685772) < 1e-6
    assert abs(v["pt"] - (237600 / 234000 - 1) * 100) < 1e-9 and v["tt"] == "" and v["co_gd"]
    assert B.loc["AAA", "tt"] == "tran" and abs(B.loc["AAA", "pt"] - 7.0) < 1e-9
    assert not B.loc["BBB", "co_gd"] and B.loc["BBB", "gia"] == 5000 and B.loc["BBB", "pt"] == 0


def test_ho_so_thanh_khoan_va_ty_le():
    n1 = _nen_phut(["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"], [12e6, 18e6, 15e6, 6e6])
    hs = tinh.ho_so_thanh_khoan(n1, truoc_ngay="2026-11-05")
    assert [d for d, _ in hs["ngay"]] == ["2026-11-02", "2026-11-03", "2026-11-04"]   # bỏ phiên đang chạy
    assert abs(hs["tb"] - 15000) < 1e-6
    r = np.array(hs["ty_le"])
    assert (np.diff(r) >= -1e-9).all() and r[-1] == 1.0 and r[0] == 0.0
    nua = tinh.ty_le_luc(hs, pd.Timestamp("2026-11-05 11:30"))
    assert 0.5 < nua < 0.6                                       # 136 / 241 phút khớp xong buổi sáng
    assert tinh.ty_le_luc(hs, pd.Timestamp("2026-11-05 12:10")) == nua                 # nghỉ trưa: giữ nguyên
    assert tinh.ty_le_luc(hs, pd.Timestamp("2026-11-05 15:10")) == 1.0
    assert tinh.ty_le_luc(hs, pd.Timestamp("2026-11-05 08:50")) is None


def test_chuoi_khoi_ngoai():
    assert tinh.chuoi([0, 5, 3, -1]) == 2                         # hôm nay chưa có → bỏ qua
    assert tinh.chuoi([-1, -2, -3, 4]) == -3
    assert tinh.chuoi([2, 0, 3]) == 1                             # phiên cũ = 0 → dừng
    assert tinh.chuoi([]) == 0 and tinh.chuoi([0]) == 0


def test_ky_thuat_cat_ma_va_dinh_52_tuan():
    c = list(np.linspace(100, 90, 60))
    k = tinh.ky_thuat({"c": c, "cao250": 120, "thap250": 89}, 99)
    assert k["len20"] and not k["xuong20"] and not k["vuot_dinh52"] and not k["thung_day52"]
    k = tinh.ky_thuat({"c": c, "cao250": 120, "thap250": 89.5}, 88)
    assert k["thung_day52"] and not k["len20"]
    k = tinh.ky_thuat({"c": [100] * 59 + [119], "cao250": 120, "thap250": 80}, 121)
    assert k["vuot_dinh52"] and k["rsi"] > 70
    assert tinh.ky_thuat(None, 10)["rsi"] is None


def test_tom_lich_su_bo_phien_dang_chay():
    ds = [{"tradingDate": f"2026-{m:02d}-{d:02d}T00:00:00", "closePriceAdjusted": 1000 + i, "highestPriceAdjusted": 1010 + i,
           "lowestPriceAdjusted": 990 + i, "totalMatchVolume": 100, "totalMatchValue": 2e9, "foreignNetValueTotal": 1e9 * (-1) ** i}
          for i, (m, d) in enumerate([(m, d) for m in range(1, 12) for d in (3, 10, 17, 24, 28)][:55])]
    a = tinh.tom_lich_su(ds)
    b = tinh.tom_lich_su(ds, truoc_ngay=a["ngay"])
    assert a["ngay"] == "2026-11-28" and b["ngay"] == "2026-11-24"
    assert a["c"][-1] == 1054 and b["c"][-1] == 1053 and abs(a["gt20"] - 2.0) < 1e-9
    assert a["nn"][0] == 1.0 and b["nn"][0] == -1.0 and a["cao250"] is None    # < 120 phiên → không tính đỉnh 52 tuần


def test_mua_chu_dong_va_cafef():
    assert tinh.mua_chu_dong([{"accumulatedBuyVolume": "300", "accumulatedSellVolume": "100"},
                              {"accumulatedBuyVolume": "0", "accumulatedSellVolume": "100"}]) == 60.0
    assert tinh.mua_chu_dong([]) is None
    x = tinh.theo_ngay_cafef([{"Ngay": "03/11/2026", "GtMua": 2e9, "GtBan": 5e9}, {"Ngay": "04/11/2026", "GtMua": 3e9, "GtBan": 1e9}],
                             "GtMua", "GtBan", "Ngay")
    assert x == [("2026-11-04", 2.0), ("2026-11-03", -3.0)]


def test_chup_dung_du_lieu_mau(tmp_path, monkeypatch):
    n1 = _nen_phut(["2026-11-03", "2026-11-04", "2026-11-05"], [12e6, 15e6, 6e6])
    cb = {"tao_luc": "2026-11-04 19:07", "nganh": {"VIC": "Bất động sản", "AAA": "Ngân hàng"}, "ten": {"VIC": "VinGroup"},
          "vu": ["VIC", "AAA"], "td": {"VIC": ["2026-11-04", 1.6]},
          "ls": {"VIC": {"day_du": {"ngay": "2026-11-04", "c": [230000.0] * 60, "cao250": 260000.0, "thap250": 150000.0,
                                    "kl20": 1.5e6, "gt20": 350.0, "nn": [-0.1, -0.5, 0.2]}, "bo_cuoi": None}},
          "nn_san": [("2026-11-04", -65.5), ("2026-11-03", -502.2)], "td_san": [("2026-11-04", 286.8), ("2026-11-03", -118.5)],
          "ho_so": tinh.ho_so_thanh_khoan(n1, truoc_ngay="2026-11-05"), "vni_ngay": [["2026-11-04", 1733.02]],
          "nhom": {"VN30": ["VIC"], "HNX30": []}}
    aaa = {"listingInfo": {"symbol": "AAA", "refPrice": 10000, "ceiling": 10700, "floor": 9300, "board": "HNX", "type": "STOCK",
                           "listedShare": 1e8}, "matchPrice": {"matchPrice": 9900, "accumulatedValue": 5000, "accumulatedVolume": 5e5}}
    monkeypatch.setattr(nguon, "nen", lambda ma, khung="ONE_MINUTE", so_nen=400: n1)
    monkeypatch.setattr(nguon, "chi_so", lambda ds=nguon.CHI_SO: [
        {"symbol": "VNINDEX", "price": 1740.36, "refPrice": 1733.02, "change": 7.34, "changePercent": 0.42, "totalValue": 9915511.4,
         "totalStockIncrease": 147, "totalStockDecline": 161, "totalStockNoChange": 54, "totalStockCeiling": 4, "totalStockFloor": 2},
        {"symbol": "VN30", "price": 1866.08, "refPrice": 1862.07, "change": 4.01, "changePercent": 0.22, "totalValue": 4776040.1}])
    monkeypatch.setattr(nguon, "tat_ca_ma", lambda: [{"symbol": "VIC", "board": "HSX", "type": "STOCK"},
                                                     {"symbol": "AAA", "board": "HNX", "type": "STOCK"}])
    monkeypatch.setattr(nguon, "bang_gia", lambda ds, lo=400: [x for x in (MAU_VIC, aaa) if x["listingInfo"]["symbol"] in ds])
    monkeypatch.setattr(nguon, "tac_dong", lambda *a: {"topUp": [{"symbol": "VIC", "impact": 5.77}], "topDown": []})
    monkeypatch.setattr(nguon, "buoc_gia", lambda ma: [{"accumulatedBuyVolume": 3, "accumulatedSellVolume": 1}])
    cl = tmp_path / "trang_thai_chien_luoc.json"
    cl.write_text(json.dumps({"ds_mua": {"hieu_luc": "2026-11-05", "ma": [
        {"ma": "AAA", "nhom": "MUA_MOI", "tu": 9.8, "den": 10.3, "cl": 9.38, "mt1": 10.62, "mt3": 11.85, "ly_do": "MACD"}]}}),
        encoding="utf-8")
    monkeypatch.setattr(dung, "FILE_CHIEN_LUOC", str(cl))
    monkeypatch.delenv("MA_GIU_FILE", raising=False)
    ra = tmp_path / "du_lieu.json"
    out = dung.chup(cb, str(ra), luc=pd.Timestamp("2026-11-05 11:30"), in_tien_do=lambda *a: None)
    d = json.loads(ra.read_text(encoding="utf-8"))
    assert d["phien"] == "2026-11-05" and d["dang_gd"] and out["phien"] == d["phien"]
    assert [x["ma"] for x in d["chi_so"]] == ["VNINDEX", "VN30", "VN30F1M"]
    assert d["thanh_khoan"]["khop"] == 174 and d["thanh_khoan"]["tb20"] == 13500
    assert d["khoi_ngoai"]["chuoi"] == 1 and d["khoi_ngoai"]["ls"][-1] == 22.3       # hôm nay mua ròng VIC +22,3 tỷ
    assert d["tu_doanh"]["phien"] == "2026-11-04" and d["tac_dong"]["len"][0][:2] == ["VIC", 5.77]
    assert [r[0] for r in d["ban_do"]["dong"]] == ["VIC"] and d["ban_do"]["dong"][0][6] == 1.6
    loc = {r[0]: dict(zip(d["loc"]["cot"], r)) for r in d["loc"]["dong"]}
    assert set(loc) == {"VIC", "AAA"} and loc["VIC"]["mcd"] == 75.0 and loc["VIC"]["gia"] == 237.6
    assert loc["VIC"]["chuoi"] == 1 and loc["VIC"]["nn5"] == round(22.2685772 - 0.4, 2)
    assert loc["AAA"]["gt20"] is None and loc["AAA"]["kl_x"] is None and loc["AAA"]["san"] == "HNX"
    # nhiều phiên (FiinTrade 5 · 10 · 20): % so đóng cửa n phiên trước, khối ngoại 10 phiên; tác động VN-Index n phiên
    assert loc["VIC"]["p5"] == loc["VIC"]["p20"] == round((237600 / 230000 - 1) * 100, 2) and loc["AAA"]["p5"] is None
    assert loc["VIC"]["nn10"] == loc["VIC"]["nn5"]
    t5 = d["tac_dong"]["n"]["5"]
    assert t5["len"][0][0] == "VIC" and t5["len"][0][1] == round(7600 / 237600 * 1740.36, 2) and t5["xuong"] == []
    assert t5["rong"] is None                                          # chưa đủ 5 phiên VN-Index trong mẫu
    assert round(dung.doi_n_phien([10.0, 11.0], 12.0, 2), 6) == 20.0 and dung.doi_n_phien([10.0], 12.0, 5) is None
    assert d["tin_hieu"] == {"hieu_luc": "2026-11-05", "ma": [["AAA", "Mua mới", 9.8, 10.3, 9.38, 10.62, 11.85, "MACD"]]}
    assert dung.tin_hieu_bot(str(tmp_path / "khong_co.json")) is None
    assert d["danh_muc"] == []                                         # không có MA_GIU_FILE → không có mã đang giữ


def test_workflow_bang_thi_truong_chi_lay_ma_dang_giu():
    """Không checkout repo kín; bước duy nhất chạm danh-muc chỉ đọc cột mã danh_muc.csv ra file tạm, chỉ trên main, log
    chỉ in số mã."""
    import yaml
    d = yaml.safe_load(open(".github/workflows/bang_thi_truong.yml", encoding="utf-8"))
    cham = []
    for job in d["jobs"].values():
        for st in job.get("steps") or []:
            t = json.dumps(st, ensure_ascii=False)
            assert "danh-muc" not in str((st.get("with") or {}).get("repository", ""))
            if ("DANH_MUC" in t or "danh-muc" in t) and "bang-thi-truong" not in t:
                cham.append(st)
            elif "DANH_MUC" in t:                                    # trang riêng: token chung chỉ để đẩy sang repo bang-thi-truong
                assert "danh_muc" not in t and "contents/" not in t and "RUNNER_TEMP" not in t
    assert len(cham) == 1
    st = cham[0]
    assert st["if"] == "github.ref == 'refs/heads/main'" and "contents/danh_muc.csv" in st["run"]
    assert "x.get('ma')" in st["run"] and "RUNNER_TEMP" in st["run"] and 'cat "$F"' not in st["run"]


def test_ma_dang_giu(tmp_path, monkeypatch):
    f = tmp_path / "ma.txt"
    f.write_text("bbb,AAA,\nAAA, x, CCC1\n", encoding="utf-8")
    assert dung.ma_dang_giu(str(f)) == ["AAA", "BBB", "CCC1"]
    monkeypatch.delenv("MA_GIU_FILE", raising=False)
    assert dung.ma_dang_giu() == [] and dung.ma_dang_giu(str(tmp_path / "khong.txt")) == []
    monkeypatch.setenv("MA_GIU_FILE", str(f))
    assert dung.ma_dang_giu() == ["AAA", "BBB", "CCC1"]


def test_workflow_nhip_goi_bang_thi_truong():
    """Lịch "*/5" của GitHub không tin được → máy nhịp gọi bang_thi_truong.yml (main); không checkout, không chạm repo kín,
    chỉ quyền actions; mỗi buổi có ≥ 2 mốc lịch dự phòng."""
    import yaml
    d = yaml.safe_load(open(".github/workflows/nhip_thi_truong.yml", encoding="utf-8"))
    tren = d.get("on") or d.get(True)
    assert d["permissions"] == {"actions": "write"} and "workflow_dispatch" in tren
    lich = [int(x["cron"].split()[1]) for x in tren["schedule"]]
    assert sum(h < 4 for h in lich) >= 2 and sum(5 <= h < 8 for h in lich) >= 2
    (job,) = d["jobs"].values()
    t = json.dumps(job, ensure_ascii=False)
    assert "checkout" not in t and "danh-muc" not in t and "DANH_MUC" not in t
    assert "workflows/bang_thi_truong.yml/dispatches" in t and '{\\"ref\\":\\"main\\"}' in t
    assert job["timeout-minutes"] <= 360


def test_workflow_tra_cuu_web():
    """Trang Tra cứu mã: workflow dựng dữ liệu xoá file danh mục thật, chỉ ghi cache docs/ma/du_lieu (không commit, không
    artifact); Bang thi truong lấy cache đó khi gói trang (chỉ main)."""
    import yaml
    d = yaml.safe_load(open(".github/workflows/tra_cuu_web.yml", encoding="utf-8"))
    assert d["permissions"] == {"contents": "read", "actions": "write"}
    assert set(d["jobs"]) == {"gac", "dung"}                     # gac: lịch tới trễ mà đồng hồ đã gọi → bỏ (test_dong_ho)
    job = d["jobs"]["dung"]
    assert job["env"]["CONG_KHAI"] == "1"
    t = json.dumps(job, ensure_ascii=False)
    assert "rm -f danh_muc*.csv" in t and "upload-artifact" not in t and "git push" not in t and "git commit" not in t
    luu = [s for s in job["steps"] if "cache/save" in str(s.get("uses", ""))]
    assert len(luu) == 1 and luu[0]["with"]["path"] == "docs/ma/du_lieu" and luu[0]["with"]["key"].startswith("tra-cuu-")
    assert "ptcp.web_tra_cuu" in t and "bang_thi_truong.yml/dispatches" in t and "thi_truong.tra_cuu_dn" in t
    lay_cu = [s for s in job["steps"] if "cache/restore" in str(s.get("uses", ""))]
    assert lay_cu and lay_cu[0]["with"]["restore-keys"] == "tra-cuu-"            # mã chưa tới lượt giữ file cũ
    b = yaml.safe_load(open(".github/workflows/bang_thi_truong.yml", encoding="utf-8"))
    lay = [s for s in b["jobs"]["dung"]["steps"] if s.get("with", {}).get("path") == "docs/ma/du_lieu"]
    assert len(lay) == 1 and "cache/restore" in lay[0]["uses"] and lay[0]["with"]["restore-keys"] == "tra-cuu-"
    assert "refs/heads/main" in lay[0]["if"]
    assert "docs/ma/du_lieu/" in open(".gitignore", encoding="utf-8").read()


def test_trang_tra_cuu_khong_tai_ngoai():
    """docs/ma/index.html: không script / font ngoài, chỉ tải JSON cùng site; chuỗi từ dữ liệu luôn qua esc()."""
    import re
    h = open("docs/ma/index.html", encoding="utf-8").read()
    assert "<script src" not in h and "@import" not in h and "fonts.googleapis" not in h
    ngoai = set(re.findall(r'\.src = "(https://[^"/]+)', h))                 # script tải động ngoài: chỉ SheetJS
    assert ngoai == {"https://cdnjs.cloudflare.com"}, ngoai
    assert 'sc.src = "lib/lightweight-charts.standalone.production.js?v=' in h       # biểu đồ: thư viện kèm trang (?v= đổi bản)
    lib = open("docs/ma/lib/lightweight-charts.standalone.production.js", encoding="utf-8").read(400)
    assert "TradingView Lightweight Charts" in lib and "Apache License 2.0" in lib
    assert "Apache License" in open("docs/ma/lib/LICENSE-lightweight-charts.txt", encoding="utf-8").read()
    assert 'const DL = "du_lieu/", TT = "../thi_truong/du_lieu.json"' in h
    assert '<a href="#rrg">RRG</a>' in h and 'lay(DL + "rrg.json", false)' in h               # đồ thị RRG đọc rrg.json cùng site
    for tab in ("tong-quan", "tin", "ho-so", "lanh-dao", "co-dong", "co-tuc", "tai-chinh", "phan-tich", "chi-so", "dinh-gia", "lich-su",
                "bao-cao", "tai-lieu", "he-thong"):
        assert f'["{tab}",' in h, tab
    assert not re.search(r"fetch\(\s*['\"]https?:", h)
    assert not re.search("[\U0001F300-\U0001FAFF\u2605\u2B50]", h)                     # không emoji / sticker
    assert "const esc = " in h and "const url = u => /^https?:" in h
    t = open("trang_bang/index.html", encoding="utf-8").read()
    cu = open("docs/thi_truong/index.html", encoding="utf-8").read()          # địa chỉ cũ: chỉ chuyển hướng sang trang riêng
    assert 'location.replace("/bang-thi-truong/" + location.hash)' in cu and "du_lieu.json" not in cu
    assert 'href="${GOC}ma/#${esc(r.ma)}"' in t and 'href="../ma/"' in t       # GOC: "../" (canh-bao-mua) | "/canh-bao-mua/" (trang riêng)
    assert re.search(r'<div class="tab" role="tablist">.*?<a href="\.\./ma/#bieu-do"[^>]*>Biểu đồ</a>\s*</div>', t, re.S)   # mục Biểu đồ riêng cạnh Tổng quan / Lọc mã



def _chay_js_phan_tich(ma_js):
    """Chạy các hàm thuần của tab Phân tích (docs/ma/index.html) trong node với BCTC giả → kết quả JSON."""
    import re
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("không có node")
    h = open("docs/ma/index.html", encoding="utf-8").read()
    tro = "\n".join(re.search(rf"^const {t} = .*$", h, re.M).group(0) for t in ("esc", "so", "pt", "mau", "tb", "trung_vi"))
    i = h.index("// ---------------------------------------------------------------- PHÂN TÍCH TÀI CHÍNH")
    j = h.index("async function phan_tich(")
    js = "let DS = [], LIVE = {}; const gia_h = r => r.gia;\n" + tro + "\n" + h[i:j] + "\n" + ma_js
    kq = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr
    return json.loads(kq.stdout)


BCTC_GIA = {"q": [], "y": ["2021", "2022", "2023", "2024", "2025"], "loai": "CT",
            "kd": {"isa3": [800, 900, 1000, 1100, 1300], "isa4": [-600, -680, -750, -800, -950], "isa5": [200, 220, 250, 300, 350],
                   "isa8": [-20, -25, -30, -30, -40], "isa9": [-30, -35, -40, -45, -50], "isa10": [-20, -22, -25, -28, -30],
                   "isa16": [100, 110, 130, 160, 200], "isa20": [80, 88, 104, 128, 160], "isa22": [76, 84, 100, 120, 150]},
            "cd": {"bsa1": [500, 550, 600, 700, 800], "bsa9": [100, 110, 120, 130, 200], "bsa15": [150, 160, 170, 180, 200],
                   "bsa29": [400, 420, 450, 480, 500], "bsa43": [10, 10, 10, 10, 10], "bsa53": [1000, 1100, 1200, 1350, 1500],
                   "bsa54": [500, 540, 580, 650, 700], "bsa57": [80, 85, 90, 95, 120], "bsa78": [500, 560, 620, 700, 800],
                   "bsa80": [300, 300, 300, 300, 360], "bsa210": [20, 22, 24, 26, 30]},
            "lc": {"cfa2": [-40, -42, -45, -48, -50], "cfa18": [90, 100, 110, 120, 100], "cfa19": [-50, -60, -60, -70, -80],
                   "cfa32": [-20, -25, -30, -40, -45]}}


def test_phan_tich_dupont_6_nhan_to_va_m_score():
    """DuPont: tích 6 nhân tố = LNST mẹ / VCSH mẹ bq, tích 5 nhân tố = LNST / VCSH bq; gánh nặng lãi vay = LNTT / (LNTT + lãi vay);
    M-Score đúng công thức Beneish; SGR = ROE × (1 − tỷ lệ chi trả)."""
    kq = _chay_js_phan_tich(f"const S = bctc_nam({json.dumps(BCTC_GIA)}); const dp = pt_dupont(S);"
                            "const tt = pt_tt(S, dp, {ke_hoach: []});"
                            "console.log(JSON.stringify({dp, m: pt_m(S), cl: pt_cl(S, false), tt}));")
    dp = kq["dp"]
    assert [x["nam"] for x in dp] == ["2022", "2023", "2024", "2025"]
    c = dp[-1]
    tich6 = c["me"] * c["thue"] * c["lai"] * c["ebit"] * c["vq"] * c["db"]
    vcm = ((800 - 30) + (700 - 26)) / 2
    assert c["roe"] == pytest.approx(150 / vcm) and tich6 == pytest.approx(c["roe"])
    assert c["thue"] * c["lai"] * c["ebit"] * c["vq"] * c["db5"] == pytest.approx(c["roe5"]) == pytest.approx(160 / 750)
    assert c["lai"] == pytest.approx(200 / 240) and c["ebit"] == pytest.approx(240 / 1300)
    m = kq["m"]
    v = m["v"]
    assert v["DSRI"] == pytest.approx((200 / 1300) / (130 / 1100)) and v["SGI"] == pytest.approx(1300 / 1100)
    assert v["TATA"] == pytest.approx((160 - 100) / 1500)
    he = {"DSRI": .92, "GMI": .528, "AQI": .404, "SGI": .892, "DEPI": .115, "SGAI": -.172, "TATA": 4.679, "LVGI": -.327}
    assert m["m"] == pytest.approx(-4.84 + sum(he[k] * v[k] for k in he))
    assert m["muc"] in ("t", "d", "g") and not m["thieu"]
    ten = {x[0]: x[2] for x in kq["cl"]["c"]}
    assert ten["Phải thu tăng − doanh thu tăng"] == "g"                  # phải thu +54% vs doanh thu +18%
    tt = kq["tt"]
    tra = [45 / 120, 40 / 100, 30 / 84]
    assert tt["tl_tra"] == pytest.approx(sum(tra) / 3) and tt["sgr"] == pytest.approx(c["roe"] * (1 - tt["tl_tra"]))
    assert tt["cg"]["ln"] == pytest.approx((150 / 84) ** (1 / 3) - 1)
    assert any("pha loãng" in x[1] for x in tt["co"])                     # vốn góp +20%


def test_phan_tich_dinh_gia_trung_vi_va_phuong_phap():
    """Định giá đa phương pháp: Graham Number đúng, trung vị các phương pháp có số, biên an toàn; mọi công cụ có Phương pháp."""
    kq = _chay_js_phan_tich(f"const S = bctc_nam({json.dumps(BCTC_GIA)}); const tt = pt_tt(S, pt_dupont(S), {{ke_hoach: []}});"
                            "const dg = pt_dinh_gia(S, {eps: 4000, bvps: 20000, gia_tri: 50000, nganh: 'X'}, {}, 40000, 36e6, tt, 'CT');"
                            "console.log(JSON.stringify({dg, pp: Object.keys(PT_PP), html: pp_html('dp')}));")
    dg = kq["dg"]
    gn = next(x for x in dg["pp"] if x["ten"] == "Graham Number")
    assert gn["v"] == pytest.approx((22.5 * 4000 * 20000) ** 0.5)
    co = sorted(x["v"] for x in dg["pp"] if x["v"])
    tv = co[len(co) // 2] if len(co) % 2 else (co[len(co) // 2 - 1] + co[len(co) // 2]) / 2
    assert dg["tv"] == pytest.approx(tv) and dg["bien"] == pytest.approx((tv - 40000) / tv)
    assert set(kq["pp"]) == {"z", "f", "dp", "m", "cl", "dg", "tt"}
    assert "Gánh nặng lãi vay" in kq["html"] and "Tham khảo" in kq["html"]


def test_tra_cuu_dn_gon(tmp_path, monkeypatch):
    from thi_truong import tra_cuu_dn as T
    ds = [{"tradingDate": f"2026-11-0{i}T00:00:00", "openPriceAdjusted": 20000 + i, "highestPriceAdjusted": 21000,
           "lowestPriceAdjusted": 19000, "closePriceAdjusted": 20500 + i * 10, "closePrice": 41000, "totalMatchVolume": 1e6,
           "totalValue": 2.05e10, "totalDealValue": 1e9, "foreignBuyValueTotal": 3e9, "foreignSellValueTotal": 1e9,
           "foreignOwnedPercentage": 0.2, "totalBuyTradeVolume": 5e5, "totalSellTradeVolume": 4e5} for i in (4, 3, 2)]
    ds.append({"tradingDate": "2026-11-01T00:00:00", "closePriceAdjusted": 0})          # không giao dịch → bỏ
    g = T.gon_gia(ds, {"2026-11-03": 1.5})
    assert g["d"] == ["2026-11-02", "2026-11-03", "2026-11-04"] and g["c"][-1] == 20.54 and g["c0"][0] == 41.0
    assert g["nn"] == [2.0, 2.0, 2.0] and g["nn_pt"][0] == 20.0 and g["td"] == [None, 1.5, None] and g["gt"][0] == 20.5
    assert "td" not in T.gon_gia(ds)
    cs = T.gon_chi_so([{"year": 2026, "quarter": 2, "pe": 8.0, "roe": 0.2, "npl": 0, "marketCap": 5e12},
                       {"year": 2025, "quarter": 4, "pe": 9.0, "roe": 0.18, "npl": 0, "marketCap": 4e12}])
    assert cs["ky"] == ["Q4.25", "Q2.26"] and cs["pe"] == [9.0, 8.0] and "npl" not in cs and cs["marketCap"] == [4000, 5000]
    sk = T.gon_su_kien([{"exrightDate": "2026-05-19T00:00:00", "eventCode": "DIV", "eventTitleVi": "Cổ tức", "valuePerShare": 700},
                        {"publicDate": "2026-10-01", "eventCode": "ISS", "exerciseRatio": 0.5}, {"eventCode": "X"}])
    assert [x["ngay"] for x in sk] == ["2026-10-01", "2026-05-19"] and sk[1]["gia_tri"] == 700
    # 14/11/2026: cổ tức / phát hành / đại hội giữ hết từ 2012, loại khác ≤ so mục mới nhất
    nhieu = [{"exrightDate": f"{2012 + i // 4}-0{1 + i % 4}-15", "eventCode": "DIV", "valuePerShare": 500} for i in range(56)] + \
        [{"publicDate": f"2026-{1 + i % 12:02d}-{1 + i // 12:02d}", "eventCode": "DDINS"} for i in range(200)] + [{"publicDate": "2013-04-20", "eventCode": "AGME"}]
    g = T.gon_su_kien(nhieu, so=50)
    assert sum(x["ma_sk"] == "DIV" for x in g) == 56 and sum(x["ma_sk"] == "DDINS" for x in g) == 50 and any(x["ma_sk"] == "AGME" for x in g)
    assert [x["ngay"] for x in g] == sorted((x["ngay"] for x in g), reverse=True)
    trang = []
    monkeypatch.setattr(T, "iq", lambda duong, so_lan=1: trang.append(duong) or ([{"eventCode": "DIV"}] * (T.SK_TRANG if len(trang) < 3 else 7)))
    assert len(T.lay_su_kien("AAA")) == 2 * T.SK_TRANG + 7 and len(trang) == 3 and "page=2&size=200" in trang[-1]
    cd = T.gon_co_dong([{"ownerName": "A", "percentage": 0.01, "ownerType": "INDIVIDUAL"}, {"ownerName": "B", "percentage": 0.2,
                                                                                          "ownerType": "CORPORATE"}])
    assert [x["ten"] for x in cd] == ["B", "A"] and cd[0]["pt"] == 20.0 and cd[0]["loai"] == "Tổ chức"
    assert T.chu_html("<div>Ng&acirc;n h&agrave;ng<br>A</div>") == "Ngân hàng\nA"
    tin = T.tach_tin('<li>05/11/2026 18:05 <a href="/x.chn">Tin &amp; 1</a></li><li>03/11/2026<a href="javascript:x">y</a></li>')
    assert tin == [{"ngay": "2026-11-05 18:05", "tieu_de": "Tin & 1", "link": "https://cafef.vn/x.chn"}]


def test_tra_cuu_dn_nguon(monkeypatch):
    from thi_truong import tra_cuu_dn as T

    def goi(url, **k):
        if "kbsec" in url:
            return {"FD": "06/08/1993", "CC": 70862, "LD": "04/06/2018", "LP": 128000, "SM": "<p>- A</p>",
                    "Subsidiaries": [{"NM": "Con", "OR": 79.8, "CC": -1, "D": "2025-12-31T00:00:00"}],
                    "Leaders": [{"NM": "Ông X", "PI": "TGĐ", "PO": "TGĐ (CEO)", "FD": "2020"}], "Khac": [{"a": 1}]}
        if "simplize.vn/api/company/summary" in url:
            return {"data": {"nameVi": "Cty", "website": "https://x.vn", "businessLine": "<div>L</div>"}}
        if "simplize" in url:
            return {"data": [{"issueDate": "28/10/2026", "source": "ssi", "recommend": "MUA", "targetPrice": 37500,
                              "title": "T", "attachedLink": "https://x/a.pdf"}]}
        if "BaoCaoPhanTich" in url:
            return {"Data": [{"DateDeploy": "/Date(1793145600000)/", "ResourceCode": "SSI", "Title": "T2", "FileName": "f.pdf"},
                             {"DateDeploy": "/Date(1792022400000)/", "ResourceCode": "VCBS", "Title": "T3"}]}
        raise ValueError("HTTP 404")
    monkeypatch.setattr(T.nguon, "goi", goi)

    def khong_mang(*a, **k):
        raise ValueError("không gọi mạng trong test")
    monkeypatch.setattr(T.nguon, "_phien", lambda: type("S", (), {"get": khong_mang})())
    monkeypatch.setattr(T, "VAN_IQ", T.CauDao(moi_giay=1e6, nghi=0))   # IQ lỗi liên tiếp → cầu dao thật nghỉ 90 giây
    kb = T.ho_so_kbs("TCB")
    assert kb["thanh_lap"] == "06/08/1993" and kb["gia_chao_san"] == 128000 and kb["nganh_nghe"] == "- A"
    assert kb["cong_ty"][0] == {"ten": "Con", "so_huu": 79.8, "von": None, "ngay": "2025-12-31", "ghi_chu": ""}
    assert kb["lanh_dao"][0]["cv"] == "TGĐ" and kb["khac"] == {"Khac": [{"a": 1}]}
    assert T.tom_tat_simplize("TCB")["linh_vuc"] == "L"
    bc = T.bao_cao_ctck("TCB")
    assert bc[0]["ctck"] == "SSI" and bc[0]["mt"] == 37.5 and bc[0]["link"] == "https://x/a.pdf"     # gộp trùng SSI cùng ngày
    assert len(bc) == 2 and bc[1]["ctck"] == "VCBS"
    dn, loi = T.lay_dn("TCB", {"ct": {"cu": 1}})
    assert set(loi) == {"ct", "cc", "cd", "sk", "nb", "cs", "tin", "nn_nam"} and dn["ct"] == {"cu": 1} and "kbs" in dn


def test_tra_cuu_dn_xoay_vong(tmp_path, monkeypatch):
    from thi_truong import tra_cuu_dn as T
    ra = str(tmp_path)
    T._ghi({"cap_nhat": "2026-01-01"}, f"{ra}/gia/AAA.json")
    T._ghi({"cap_nhat": "2026-01-01"}, f"{ra}/dn/AAA.json")
    T._ghi({"cap_nhat": "2026-02-01"}, f"{ra}/gia/BBB.json")
    T._ghi({"cap_nhat": "2026-02-01"}, f"{ra}/dn/BBB.json")
    assert T.thu_tu(["BBB", "AAA", "CCC"], ra, "2026-03-01") == ["CCC", "AAA", "BBB"]     # chưa có → cũ nhất trước
    assert T.thu_tu(["ZZZ", "CCC"], ra, "2026-03-01") == ["ZZZ", "CCC"]                     # cùng độ cũ: giữ thứ tự (vốn hoá)
    assert T.thu_tu(["BBB"], ra, "2026-02-01") == []                                      # đã cập nhật hôm nay
    assert T.thu_tu(["BBB"], ra, "2026-02-01", lam_moi=True) == ["BBB"]                  # định dạng cũ → làm lại
    T._ghi({"cap_nhat": "2026-02-01", "phien_ban": T.PHIEN_BAN_DN}, f"{ra}/dn/BBB.json")
    assert T.thu_tu(["BBB"], ra, "2026-02-01", lam_moi=True) == []                       # đã xong định dạng mới hôm nay
    T._ghi({"cap_nhat": "2026-01-01", "phien_ban": T.PHIEN_BAN_DN}, f"{ra}/dn/AAA.json")
    T._ghi({"cap_nhat": "2026-01-01"}, f"{ra}/dn/ZZZ.json")
    T._ghi({"cap_nhat": "2026-01-01"}, f"{ra}/gia/ZZZ.json")
    assert T.thu_tu(["AAA", "ZZZ"], ra, "2026-03-01") == ["ZZZ", "AAA"]                  # cùng độ cũ: định dạng cũ trước
    monkeypatch.setattr(T, "lay_gia", lambda m, san="", cu=None: {"d": ["2026-11-05"], "c": [1.0]})
    monkeypatch.setattr(T, "lay_gia_dai", lambda m: {"d0": "2010-01-04", "g": [0], "c": [2.0]} if m != "CCC" else 1 / 0)
    monkeypatch.setattr(T, "lay_dn", lambda m, cu=None, *a: ({"ct": {"m": m}}, []) if m != "BBB" else ({}, ["ct"] * T.SO_PHAN_DN))
    xong, loi, con = T.chay(["AAA", "BBB", "CCC"], ra, phut=5, luong=2, in_ra=lambda *_: None)
    assert (xong, loi, con) == (3, 0, 0)
    assert T._doc(f"{ra}/dn/AAA.json")["ct"] == {"m": "AAA"} and T._doc(f"{ra}/dn/BBB.json")["cap_nhat"] == "2026-02-01"  # lỗi hết → giữ file
    assert T._doc(f"{ra}/gia/CCC.json")["c"] == [1.0]
    assert T._doc(f"{ra}/gia_dai/AAA.json")["c"] == [2.0] and T._doc(f"{ra}/gia_dai/CCC.json") is None   # lỗi → bỏ qua
    _, _, con = T.chay(["DDD", "EEE"], ra, phut=0, in_ra=lambda *_: None)                   # hết giờ → không nhận mã mới
    assert con == 2



def test_tra_cuu_dn_cau_dao_va_han(monkeypatch):
    from thi_truong import tra_cuu_dn as T
    v = T.CauDao(moi_giay=1000, nguong=2, nghi=0.05, toi_da=1)
    v.cho(); v.loi(); v.loi()                                  # 2 lỗi liền → nghỉ lần 1
    assert v.so_nghi == 1 and not v.tat
    v.cho(); v.ok(); v.loi(); v.loi()                          # lại 2 lỗi → quá số lần nghỉ → tắt
    assert v.tat
    try:
        v.cho()
        assert False, "phải báo nguồn đã tắt"
    except ValueError:
        pass
    goi = []
    phan = ("ct", "cc", "cd", "sk", "nb", "cs", "tin", "bc", "kbs", "sz", "nn_nam")
    assert len(phan) == T.SO_PHAN_DN

    def gia_lap(*a, **k):
        goi.append(1)
        raise ValueError("HTTP 404")
    monkeypatch.setattr(T, "iq", gia_lap)
    monkeypatch.setattr(T, "tin_cafef", gia_lap)
    monkeypatch.setattr(T, "bao_cao_ctck", gia_lap)
    monkeypatch.setattr(T, "ho_so_kbs", gia_lap)
    monkeypatch.setattr(T, "tom_tat_simplize", gia_lap)
    monkeypatch.setattr(T, "tai_lieu", gia_lap)                      # tài liệu: vòng riêng (tl/<MÃ>.json), không trong dn
    cu = {k: {"cu": k} for k in phan}
    cu["ngay_phan"], cu["phien_ban"] = {k: "2026-11-04" for k in phan}, T.PHIEN_BAN_DN
    dn, loi = T.lay_dn("AAA", cu, "2026-11-05")
    assert sorted(loi) == ["tin"] and len(goi) == 1                 # chỉ tin (hạn 1 ngày) phải làm lại
    assert dn["ct"] == {"cu": "ct"} and dn["ngay_phan"]["tin"] == "2026-11-04"
    goi.clear()
    dn, loi = T.lay_dn("AAA", cu, "2026-11-20")                    # 16 ngày: quá hạn mọi phần trừ sz, nn_nam (30 ngày)
    assert len(goi) == len(phan) - 2 and dn["kbs"] == {"cu": "kbs"} and "sz" not in loi and "nn_nam" not in loi
    goi.clear()
    T.lay_dn("AAA", {**cu, "phien_ban": 1}, "2026-11-05")           # định dạng cũ → làm mới hết
    assert len(goi) == len(phan)


def test_tra_cuu_dn_gia_du_phong(monkeypatch):
    from thi_truong import tra_cuu_dn as T
    monkeypatch.setattr(T.nguon, "nen", lambda ma, k, n: {"t": ["1762300800", "1762387200"], "o": [21000, 21500],
                                                          "h": [22000, 22000], "l": [20500, 21000], "c": [21500, 0],
                                                          "v": [1e6, 2e6]})
    g = T.gia_du_phong("AAA")
    assert g["d"] == ["2025-11-05"] and g["c"] == [21.5] and g["o"] == [21.0] and g["du_phong"]

    def iq_loi(*a, **k):
        raise ValueError("chặn")
    monkeypatch.setattr(T, "iq", iq_loi)
    assert T.lay_gia("AAA")["du_phong"]



def test_tra_cuu_dn_tai_lieu_va_nganh(tmp_path, monkeypatch):
    from thi_truong import tra_cuu_dn as T

    def goi(url, **k):
        if "Type=1" in url:
            return {"Data": [{"Name": "BCTC hợp nhất  kiểm toán", "Year": 2025, "Time": "CN", "Link": "https://x/a.pdf"},
                             {"Name": "x", "Link": "javascript:alert(1)"}]}
        return {"Data": []}
    monkeypatch.setattr(T.nguon, "goi", goi)
    tl = T.tai_lieu("AAA")
    assert tl == [{"loai": "BCTC", "ten": "BCTC hợp nhất kiểm toán", "nam": "2025", "ky": "CN", "link": "https://x/a.pdf"}]
    ra = str(tmp_path)
    for m, pe in (("AAA", 8.0), ("BBB", 10.0), ("CCC", 12.0), ("DDD", 30.0)):
        T._ghi({"cs": {"ky": ["Q2.26"], "pe": [pe], "roe": [0.1]}}, f"{ra}/dn/{m}.json")
    ds = [{"ma": "AAA", "nganh": "X"}, {"ma": "BBB", "nganh": "X"}, {"ma": "CCC", "nganh": "X"}, {"ma": "DDD", "nganh": "Y"}]
    ng = T.chi_so_nganh(ra, ds)
    assert ng == {"X": {"pe": [10.0, 3], "roe": [0.1, 3]}, "Y": {}} and T._doc(f"{ra}/chi_so_nganh.json") == ng



def test_tra_cuu_dn_gia_noi(monkeypatch):
    """Giá chạy nối: chỉ tải phiên mới rồi ghép; giá cũ bị điều chỉnh → tải đủ; IQ lỗi khi đã có file → giữ file cũ."""
    from datetime import date as _d, timedelta
    from thi_truong import tra_cuu_dn as T
    hom = _d.today()
    ngay = [(hom - timedelta(days=k)).isoformat() for k in range(6, -1, -1)]          # 7 ngày, cũ → mới
    cu = {"d": ngay[:5], "o": [1] * 5, "h": [1] * 5, "l": [1] * 5, "c": [10.0, 10.1, 10.2, 10.3, 10.4], "c0": [1] * 5,
          "v": [1] * 5, "nn": [0.1] * 5}
    goi = []

    def gia(ma, san, so):
        goi.append(so)
        d = ngay[3:] if so < T.SO_PHIEN else ngay
        c = {ngay[3]: 10.3 * he, ngay[4]: 10.4 * he, ngay[5]: 10.5, ngay[6]: 10.6}
        c = [c.get(x, 9.0) for x in d]
        return {"d": d, "o": c, "h": c, "l": c, "c": c, "c0": c, "v": [2] * len(d), "nn": [0.5] * len(d)}
    monkeypatch.setattr(T, "_lay_gia_iq", gia)
    he = 1.0
    g = T.lay_gia("AAA", "HOSE", cu)
    assert goi[0] < T.SO_PHIEN and len(goi) == 1                              # chỉ tải phiên mới
    assert g["d"] == ngay and g["c"] == [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6] and g["nn"][:3] == [0.1] * 3
    goi.clear()
    he = 0.9                                                                   # cổ tức → giá cũ điều chỉnh
    g = T.lay_gia("AAA", "HOSE", cu)
    assert goi == [goi[0], T.SO_PHIEN] and g["d"] == ngay                      # tải đủ lại

    def loi(*a, **k):
        raise ValueError("chặn")
    monkeypatch.setattr(T, "_lay_gia_iq", loi)
    try:
        T.lay_gia("AAA", "HOSE", cu)
        assert False, "có file cũ → không thay bằng dự phòng"
    except ValueError:
        pass



def test_canslim_web():
    """CANSLIM trang Tra cứu mã: C·A từ ds.json (tỷ lệ), N cách đỉnh 52T, S KL 20 ÷ 120, L hạng RS kiểu IBD trong mọi mã;
    M VN-Index so MA50 / MA200 (xét riêng); thiếu giá → chữ đó không đạt. Mã giả AAA / BBB / CCC."""
    from thi_truong import canslim_web as CW

    def gia(c, v=None):
        return {"d": [str(i) for i in range(len(c))], "c": c, "v": v or [1000] * len(c)}
    tang = [10 + i * 0.05 for i in range(300)]                          # đỉnh mới, mạnh nhất
    giam = [30 - i * 0.05 for i in range(300)]                          # cách đỉnh xa
    ngang = [10.0] * 300
    kl = [1000] * 280 + [3000] * 20                                     # KL 20 phiên ×3 / TB120
    ds = [{"ma": "AAA", "ln_yoy": 0.6, "ln4_yoy": 0.3}, {"ma": "BBB", "ln_yoy": 0.1, "ln4_yoy": -0.2},
          {"ma": "CCC", "ln_yoy": None, "ln4_yoy": 0.5}, {"ma": "DDD", "ln_yoy": 0.9, "ln4_yoy": 0.9}]
    vni = {"c": [1000 + i for i in range(260)]}
    meta = CW.tinh(ds, {"AAA": gia(tang, kl), "BBB": gia(giam), "CCC": gia(ngang)}, vni)
    a, b, c, d = ds
    assert a["cs"] == 5 and a["cs_d"] == "C·A·N·S·L" and a["rs"] == 99 and a["cach52"] == 0
    assert b["cs"] == 0 and b["rs"] == 0 and b["cach52"] < -15
    assert c["cs_d"] == "A·N" and c["kl_x"] == 1.0                     # ngang: N đạt, S / L không
    assert d["cs"] == 2 and d["rs"] is None                            # không có file giá → chỉ C·A
    assert meta["m"] == "tăng" and meta["vni"] == 1259
    assert CW.thi_truong_m({"c": [1000 - i for i in range(260)]})["m"] == "giảm"
    assert CW.thi_truong_m(None) == {"m": None}
    assert CW.chi_tieu_gia(gia([10.0] * 30)) == {"cach52": None, "kl_x": None, "ibd": None}   # < 60 phiên


def test_workflow_tra_cuu_web_co_canslim():
    import yaml
    d = yaml.safe_load(open(".github/workflows/tra_cuu_web.yml", encoding="utf-8"))
    buoc = [s.get("run", "") for s in d["jobs"]["dung"]["steps"]]
    i_dn = next(i for i, r in enumerate(buoc) if "thi_truong.tra_cuu_dn" in r)
    i_cs = next(i for i, r in enumerate(buoc) if "thi_truong.canslim_web" in r)
    i_vgm = next(i for i, r in enumerate(buoc) if "thi_truong.xep_hang_web" in r)
    i_luu = next(i for i, s in enumerate(d["jobs"]["dung"]["steps"]) if "cache/save" in str(s.get("uses", "")))
    i_sk = next(i for i, r in enumerate(buoc) if "thi_truong.su_kien_web" in r)
    assert i_dn < i_sk < i_luu and "|| echo" in buoc[i_sk]           # sau dn/ (sự kiện từng mã), trước lưu cache
    i_rrg = next(i for i, r in enumerate(buoc) if "thi_truong.rrg_web" in r)
    assert i_dn < i_rrg < i_luu and "|| echo" in buoc[i_rrg]          # sau gia/ (giá từng mã), trước lưu cache
    assert i_dn < i_cs < i_vgm < i_luu and "|| echo" in buoc[i_cs] and "|| echo" in buoc[i_vgm]   # sau giá + CANSLIM (rs),
                                                                    # trước lưu cache; lỗi không làm hỏng lượt



def test_xep_hang_vgm():
    """Xếp hạng A–F kiểu VGM: hạng phần trăm (bằng nhau cùng hạng), mỗi nhóm cần ≥ 2 chỉ tiêu, tổng cần ≥ 2 nhóm; P/E ≤ 0
    xếp cuối nhóm giá trị; chữ chia đều ~⅕. Mã giả M00…M19."""
    from thi_truong import xep_hang_web as XH
    assert XH.hang_pt({"A": 1, "B": 2, "C": 2, "D": None}) == {"A": 0.0, "B": 75.0, "C": 75.0}
    assert XH.hang_pt({"A": 1, "B": 2}, cao_tot=False) == {"A": 100.0, "B": 0.0}
    assert [XH.chu(x) for x in (95, 80, 79.9, 45, 20, 3)] == ["A", "A", "B", "C", "D", "F"] and XH.chu(None) is None
    ds = [{"ma": f"M{i:02d}", "pe": 5 + i, "pb": 0.5 + i / 10, "dinh_gia": 0.5 - i / 20, "ln_yoy": i / 10, "ln4_yoy": i / 10,
           "dt_yoy": i / 20, "dt4_yoy": i / 20, "rs": 5 * i, "cach52": -i} for i in range(20)]
    ds[0]["pe"] = -3                                                     # lỗ → giá trị kém nhất dù P/B rẻ
    ds.append({"ma": "THIEU", "pe": 8})                                  # thiếu gần hết → không xếp
    gia = {r["ma"]: {"c": [10.0] * 30 + [10 + j * (i / 50) for j in range(70)]} for i, r in enumerate(ds[:20])}
    assert XH.tinh(ds, gia) == 20
    v = {r["ma"]: r.get("vgm") for r in ds}
    assert v["THIEU"] is None and all(len(x.split()) == 4 for k, x in v.items() if k != "THIEU")
    assert v["M19"].split()[1] == "A" and v["M00"].split()[1] == "F"      # tăng trưởng cao nhất / thấp nhất
    assert v["M01"].split()[0] == "A" and v["M00"].split()[0] != "A"      # rẻ nhất (P/E dương thấp) / lỗ
    tong = [x.split()[3] for k, x in v.items() if k != "THIEU"]
    assert all(tong.count(c) == 4 for c in "ABCDF")                     # 20 mã → mỗi chữ 4 mã



def test_xep_hang_chat_luong_phong_cach():
    """Chất lượng (Q) và phong cách kiểu Stockopedia từ Q · V · M (cao = điểm nhóm ≥ 50); Q không vào điểm VGM tổng; nợ /
    VCSH chỉ chấm DN thường. Mã giả M00…"""
    from thi_truong import xep_hang_web as XH
    ds = []
    for i in range(16):
        q, v, m = i & 1, (i >> 1) & 1, (i >> 2) & 1                       # 8 tổ hợp × 2 mã
        ds.append({"ma": f"M{i:02d}", "loai": "CT", "roe": .05 + .2 * q + i / 1000, "roa": .02 + .1 * q + i / 1000,
                   "bien_rong": .05 + .2 * q, "f": 3 + 5 * q, "z": 1 + 3 * q, "no_vcsh": 2 - 1.5 * q,
                   "pe": 30 - 22 * v + i / 100, "pb": 4 - 3 * v + i / 100, "dinh_gia": -.3 + .6 * v,
                   "ln_yoy": .1, "ln4_yoy": .1, "dt_yoy": .1, "dt4_yoy": .1, "rs": 10 + 80 * m + i, "cach52": -40 + 38 * m})
    truoc = {r["ma"]: r for r in [dict(x) for x in ds]}
    XH.tinh(ds)
    pc = {r["ma"]: r["pc"] for r in ds}
    for i in range(16):
        q, v, m = i & 1, (i >> 1) & 1, (i >> 2) & 1
        assert pc[f"M{i:02d}"] == XH.PHONG_CACH[(q, v, m)], i
    cao = {f"M{i:02d}" for i in range(16) if i & 1}
    assert {r["ma"] for r in ds if r["q"] in ("A", "B")} <= cao and {r["ma"] for r in ds if r["q"] in ("D", "F")}.isdisjoint(cao)
    bank = [{"ma": "NH1", "loai": "NH", "roe": .2, "roa": .015, "no_vcsh": 10.0}, {"ma": "NH2", "loai": "NH", "roe": .1, "roa": .01, "no_vcsh": 5.0}]
    XH.tinh(bank)
    assert bank[0]["q"] == "A" and "pc" not in bank[0]                    # nợ / VCSH ngân hàng không chấm; thiếu V, M → không phong cách
    assert set(XH.TEN_PC) == set(XH.PHONG_CACH.values()) and truoc


def test_rrg_web():
    """RRG: mã mạnh dần so VN-Index → RS-Ratio > 100; ngành gia quyền vốn hoá; bỏ mã kém thanh khoản; đuôi đúng số kỳ, kỳ cuối
    trùng phiên cuối của chuẩn. Mã giả M00…"""
    import numpy as np
    from thi_truong import rrg_web as R
    rng = np.random.default_rng(3)
    ngay = pd.bdate_range("2025-01-01", periods=300)
    vni = pd.Series(1000 * np.cumprod(1 + rng.normal(0, .005, 300)), index=ngay)
    d = [x.strftime("%Y-%m-%d") for x in ngay]
    manh = list(vni.values / 50 * np.linspace(1, 1.6, 300))                    # vượt chuẩn đều → RS tăng
    yeu = list(vni.values / 50 * np.linspace(1, 0.6, 300))
    gia = {"M00": {"d": d, "c": manh, "v": [1e6] * 300}, "M01": {"d": d, "c": yeu, "v": [1e6] * 300},
           "M02": {"d": d, "c": manh, "v": [1e6] * 300}, "M03": {"d": d, "c": yeu, "v": [1e6] * 300},
           "M04": {"d": d, "c": manh, "v": [10] * 300},                         # GTGD ≈ 0 → bỏ
           "M05": {"d": d[:40], "c": manh[:40], "v": [1e6] * 40}}               # quá ngắn → bỏ
    ds = [{"ma": "M00", "nganh": "A", "von": 10}, {"ma": "M01", "nganh": "A", "von": 1}, {"ma": "M02", "nganh": "A", "von": 1},
          {"ma": "M03", "nganh": "B", "von": 1}, {"ma": "M04", "nganh": "B", "von": 1}, {"ma": "M05", "nganh": "B", "von": 1}]
    rng2 = np.random.default_rng(4)
    for k in ("M00", "M01", "M02", "M03"):                                     # thêm nhiễu để z-score xác định
        gia[k]["c"] = list(np.array(gia[k]["c"]) * (1 + rng2.normal(0, .003, 300)))
    out = R.dung(ds, gia, vni)
    for k, (n, duoi, _) in R.KHUNG.items():
        b = out[k]
        assert set(b["ma"]) == {"M00", "M01", "M02", "M03"} and len(b["ky"]) == duoi
        assert all(len(v) == duoi for v in b["ma"].values())
        assert b["ky"][-1] == d[-1]
        assert b["ma"]["M00"][-1][0] > 100 > b["ma"]["M01"][-1][0]
        assert set(b["nganh"]) == {"A"}                                           # ngành B chỉ còn 1 mã thanh khoản < 3 mã
        assert b["nganh"]["A"][-1][0] > 100
    assert R.dung(ds, gia, vni.iloc[:30]) == {}
    assert R.vni_ngay({"t": ["1767225600", "1767312000"], "c": [1, 2]}).index[0].strftime("%Y-%m-%d") == "2026-01-01"


def test_lich_su_kien():
    """Lịch sự kiện toàn thị trường: phân loại cổ tức tiền / cổ phiếu / ĐHCĐ / khác, chỉ trong cửa sổ ngày, bỏ trùng."""
    from datetime import date

    from thi_truong import su_kien_web as SK
    assert SK.nhom({"ma_sk": "DIV"}) == "tien" and SK.nhom({"ma_sk": "ISS", "ten": "Phát hành"}) == "cp"
    assert SK.nhom({"ma_sk": "AGME", "loai": "Đại hội cổ đông thường niên"}) == "dh"
    assert SK.nhom({"ma_sk": "", "ten": "Trả cổ tức bằng cổ phiếu 10%"}) == "cp" and SK.nhom({"ma_sk": "XYZ"}) == "khac"
    dn = {"AAA": {"sk": [{"ngay": "2026-11-20", "ma_sk": "DIV", "ten": "Cổ tức 500 đ/CP", "chot": "2026-11-21",
                          "thuc_hien": "2026-12-05", "gia_tri": 500},
                         {"ngay": "2026-11-20", "ma_sk": "DIV", "ten": "Cổ tức 500 đ/CP"},          # trùng → bỏ
                         {"ngay": "2025-01-01", "ma_sk": "DIV", "ten": "cũ"}]},                     # ngoài cửa sổ
          "BBB": {"sk": [{"ngay": "2026-11-01", "ma_sk": "ISS", "ten": "Phát hành 10%", "ty_le": 0.1}]}, "CCC": None}
    dong, tu, den = SK.gom(["AAA", "BBB", "CCC", "DDD"], dn.get, date(2026, 11, 6))
    assert (tu, den) == ("2026-10-23", "2027-03-06")
    assert [r[:3] for r in dong] == [["2026-11-01", "BBB", "cp"], ["2026-11-20", "AAA", "tien"]]
    assert dong[1][4:7] == ["2026-11-21", "2026-12-05", 500] and dong[0][7] == 0.1


def test_tra_cuu_dn_gia_dai(monkeypatch):
    from thi_truong import tra_cuu_dn as T
    # 3 phiên (1 trùng ngày, 1 giá 0 bị bỏ) – giờ UTC 17:00 = 00:00 giờ VN ngày sau
    monkeypatch.setattr(T.nguon, "nen", lambda ma, k, n: {"t": ["1262624400", "1262710800", "1262710800", "1263142800", "1263229200"],
                                                          "o": [20000, 21000, 1, 22000, 0], "h": [21000, 22000, 1, 23456, 0],
                                                          "l": [19000, 20000, 1, 21000, 0], "c": [20500, 21500, 1, 23456.7, 0],
                                                          "v": [1e6, 2e6, 3, 3e6, 0]})
    g = T.lay_gia_dai("AAA")
    assert g["d0"] == "2010-01-05" and g["g"] == [0, 1, 5] and g["c"] == [20.5, 21.5, 23.46] and g["v"] == [1000000, 2000000, 3000000]
    assert g["h"][-1] == 23.46 and T._4so(0.81234) == 0.8123
    monkeypatch.setattr(T.nguon, "nen", lambda ma, k, n: {"t": ["1262624400"], "o": [1], "h": [1], "l": [1], "c": [1], "v": [1]})
    try:
        T.lay_gia_dai("AAA")
        assert False
    except ValueError:
        pass


def test_tra_cuu_dn_bo_sung_gia_dai(tmp_path, monkeypatch):
    from thi_truong import tra_cuu_dn as T
    ra = str(tmp_path)
    T._ghi({"cap_nhat": "2026-11-01", "c": [1.0]}, f"{ra}/gia_dai/AAA.json")              # còn hạn → bỏ qua
    T._ghi({"cap_nhat": "2026-09-01", "c": [1.0]}, f"{ra}/gia_dai/BBB.json")              # quá hạn → tải lại
    monkeypatch.setattr(T, "lay_gia_dai", lambda m: {"d0": "2010-01-04", "g": [0], "c": [2.0]} if m != "DDD" else 1 / 0)
    xong, loi, con = T.bo_sung_gia_dai(["AAA", "BBB", "CCC", "DDD"], ra, phut=5, luong=2, in_ra=lambda *_: None,
                                       hom_nay="2026-11-07")
    assert (xong, loi, con) == (2, 1, 0)
    assert T._doc(f"{ra}/gia_dai/AAA.json")["c"] == [1.0] and T._doc(f"{ra}/gia_dai/BBB.json")["c"] == [2.0]
    assert T._doc(f"{ra}/gia_dai/CCC.json")["cap_nhat"] == "2026-11-07" and T._doc(f"{ra}/gia_dai/DDD.json") is None
    assert T.bo_sung_gia_dai(["EEE"], ra, phut=0, in_ra=lambda *_: None)[2] == 1          # hết giờ → không nhận mã


def test_bang_tt_khoi_loi_khong_lam_trong_trang():
    """09/11/2026: khung theo dõi đọc D.tin_hieu (dict {hieu_luc, ma}) như list → lỗi chặn mọi khối sau → trang trống."""
    import pathlib
    h = (pathlib.Path(__file__).parents[1] / "trang_bang" / "index.html").read_text(encoding="utf-8")
    assert "((D.tin_hieu || {}).ma || [])" in h and "(D.tin_hieu || []).map" not in h
    assert "try { f(); } catch (e)" in h                                   # mỗi khối Tổng quan vẽ riêng


def test_quy_web_lay_va_mua_ban(monkeypatch):
    from thi_truong import quy_web as Q

    def mau(ky, top):
        return {"productFund": {"updateAssetHoldingTime": ky}, "fundReport": {"totalAssetValue": 2.3e12},
                "extra": {"lastNAVDate": 1794157200000},
                "productTopHoldingList": [{"stockCode": m, "netAssetPercent": 5, "volume": kl, "assetValue": kl * 20000,
                                           "type": "STOCK"} for m, kl in top],
                "productIndustriesHoldingList": [{"industry": "Ngân hàng", "assetPercent": 40}],
                "productAssetHoldingList": [{"assetType": {"name": "Cổ phiếu"}, "assetPercent": 90}]}
    ds = {"rows": [{"id": 1, "shortName": "AAF", "name": "Quỹ A", "owner": {"shortName": "aa"},
                    "dataFundAssetType": {"code": "STOCK"}, "productNavChange": {"navToLastYear": -7.1}},
                   {"id": 2, "shortName": "BBF", "dataFundAssetType": {"code": "BOND"}}] +
                  [{"id": 10 + i, "shortName": f"X{i}", "dataFundAssetType": {"code": "BALANCED"}} for i in range(5)]}
    chi = {"09/2026": {1: [("ACB", 1000), ("HPG", 500), ("VIB", 300)]}}

    def goi(duong, body=None):
        if body is not None:
            return ds
        i = int(duong.split("/")[1])
        return mau(chi["ky"], chi[chi["ky"]].get(i, [("FPT", 10)]))
    monkeypatch.setattr(Q, "_goi", goi)
    chi["ky"] = "09/2026"
    a = Q.lay(None, in_tien_do=lambda *_: None)
    assert [q["m"] for q in a["quy"]][0] == "AAF" and "BBF" not in [q["m"] for q in a["quy"]]
    q = next(q for q in a["quy"] if q["m"] == "AAF")
    assert q["ky"] == "2026-09" and q["ts"] == 2300.0 and q["cty"] == "AA" and q["lai"]["ytd"] == -7.1
    assert a["ls"]["2026-09"]["AAF"] == {"ACB": 1000, "HPG": 500, "VIB": 300} and a["mb"] == [] and a["mb_so_quy"] == 0
    # tháng sau: ACB tăng 200 CP, HPG giảm 100, VIB rời top 10, TCB vào → chỉ ACB / HPG có giá trị
    chi["ky"], chi["10/2026"] = "10/2026", {1: [("ACB", 1200), ("HPG", 400), ("TCB", 50)]}
    b = Q.lay(a, in_tien_do=lambda *_: None)
    assert sorted(b["ls"]) == ["2026-09", "2026-10"] and b["mb_so_quy"] == 6 and b["mb_tu"] == "2026-09"
    mb = {x[0]: x for x in b["mb"]}
    assert mb["ACB"][1:] == [round(200 * 20000 / 1e9, 1), 1, 0] and mb["HPG"][1:] == [round(-100 * 20000 / 1e9, 1), 0, 1]
    assert "VIB" not in mb and b["vao_roi"]["VIB"] == [0, 1] and b["vao_roi"]["TCB"] == [1, 0]
    # quá 3 tháng thì không so
    assert Q.mua_ban({"2026-05": b["ls"]["2026-09"], "2026-10": b["ls"]["2026-10"]}, b["quy"])[1] == 0
    # Fmarket lỗi → giữ bản cũ
    monkeypatch.setattr(Q, "_goi", lambda *a, **k: (_ for _ in ()).throw(ValueError("HTTP 503")))
    assert Q.lay(b, in_tien_do=lambda *_: None) is b


def test_tai_lieu_du_moi_ban_moi_nhat_truoc(monkeypatch):
    """13/11/2026: CafeF trả BCTN cũ → mới; bản cũ lấy 12 bản đầu → web chỉ tới 2022 (GMD). Nay lấy ĐỦ, mới → cũ; Type 3
    lẫn cáo bạch / điều lệ → loại riêng; nghị quyết (Year 0) sắp theo ngày Time dd-mm-yyyy."""
    from thi_truong import tra_cuu_dn as T

    def goi(url, **k):
        if "Type=3" in url:
            return {"Data": [{"Name": f"Báo cáo thường niên năm {y}", "Year": str(y), "Quarter": "5", "Time": f"CN/{y}",
                              "Link": f"https://x/{y}.pdf"} for y in range(2009, 2026)]
                    + [{"Name": "Bản cáo bạch năm 2024", "Year": "2024", "Quarter": "5", "Link": "https://x/bcb.pdf"},
                       {"Name": "lạ", "Year": "", "Link": "https://x/la.pdf"}]}
        if "Type=4" in url:
            return {"Data": [{"Name": "Nghị quyết Hội đồng Quản trị", "Year": "0", "Quarter": "0", "Time": t,
                              "Link": f"{T.GOC_TL}download/{t}/aaa-nghi-quyet-h-qt-ve-viec-{t}-0.pdf"}
                             for t in ("16-09-2026", "01-07-2025", "22-10-2026")]}
        if "Type=1" in url:
            return {"Data": [{"Name": f"BCTC {t}", "Year": "2026", "Quarter": q, "Time": t, "Link": f"https://x/{t}.pdf"}
                             for q, t in (("2", "Q2/2026"), ("5", "CN/2026"), ("3", "Q3/2026"))]}
        return {"Data": []}
    monkeypatch.setattr(T.nguon, "goi", goi)
    tl = T.tai_lieu("AAA")
    bctn = [x["nam"] for x in tl if x["loai"] == "Báo cáo thường niên"]
    assert bctn == [str(y) for y in range(2025, 2008, -1)]                 # đủ 17 bản, 2025 → 2009
    assert [(x["ten"], x["nam"]) for x in tl if x["loai"] == T.LOAI_TL_KHAC] == [("Bản cáo bạch năm 2024", "2024"),
                                                                              ("lạ", "")]
    nq = [x for x in tl if x["loai"] == "Nghị quyết HĐQT"]
    assert [x["ky"] for x in nq] == ["22/10/2026", "16/09/2026", "01/07/2025"] and [x["nam"] for x in nq] == ["2026", "2026", "2025"]
    assert [x["ky"] for x in tl if x["loai"] == "BCTC"] == ["CN/2026", "Q3/2026", "Q2/2026"]
    g = T.gon_tai_lieu(tl)                                                  # file gọn: chỉ số loại + link "~…"
    assert g["loai"][g["ds"][0][0]] == "BCTC" and len(g["ds"]) == len(tl)
    assert g["ds"][-1][4].startswith("~download/") and g["ds"][0][4] == "https://x/CN/2026.pdf"

    def goi_loi(url, **k):                                                  # 1 loại lỗi → không ghi danh sách thiếu loại
        if "Type=4" in url:
            raise ValueError("HTTP 503")
        return goi(url)
    monkeypatch.setattr(T.nguon, "goi", goi_loi)
    try:
        T.tai_lieu("AAA")
        assert False, "phải báo lỗi"
    except ValueError:
        pass


def test_tra_cuu_dn_bo_sung_tai_lieu(tmp_path, monkeypatch):
    from thi_truong import tra_cuu_dn as T
    ra = str(tmp_path)
    T._ghi({"cap_nhat": "2026-11-12", "loai": ["BCTC"], "ds": []}, f"{ra}/tl/AAA.json")      # còn hạn (3 ngày) → bỏ qua
    T._ghi({"cap_nhat": "2026-11-01", "loai": ["BCTC"], "ds": []}, f"{ra}/tl/BBB.json")      # quá hạn → tải lại
    monkeypatch.setattr(T, "tai_lieu", lambda m: [{"loai": "BCTC", "ten": m, "nam": "2026", "ky": "Q3/2026",
                                                   "link": "https://x/a.pdf"}] if m != "DDD" else 1 / 0)
    xong, loi, con = T.bo_sung_tai_lieu(["AAA", "BBB", "CCC", "DDD"], ra, phut=5, luong=2, in_ra=lambda *_: None,
                                        hom_nay="2026-11-13")
    assert (xong, loi, con) == (2, 1, 0)
    assert T._doc(f"{ra}/tl/AAA.json")["ds"] == [] and T._doc(f"{ra}/tl/DDD.json") is None
    assert T._doc(f"{ra}/tl/CCC.json") == {"loai": ["BCTC"], "ds": [[0, "2026", "Q3/2026", "CCC", "https://x/a.pdf"]],
                                           "cap_nhat": "2026-11-13"}
    assert T.bo_sung_tai_lieu(["AAA"], ra, in_ra=lambda *_: None, hom_nay="2026-11-13", ep=True)[0] == 1   # bấm tay --ma
    # dn cũ còn "tl" (bản cắt trước 13/11/2026): giữ tới khi có tl/<MÃ>.json, có rồi thì bỏ khỏi dn
    T._ghi({"tl": [{"loai": "BCTC"}], "ct": {}}, f"{ra}/dn/EEE.json")
    T._ghi({"tl": [{"loai": "BCTC"}], "ct": {}}, f"{ra}/dn/AAA.json")
    monkeypatch.setattr(T, "lay_gia", lambda m, san="", cu=None: {"d": ["2026-11-13"], "c": [1.0]})
    monkeypatch.setattr(T, "lay_gia_dai", lambda m: {"c": [1.0]})
    monkeypatch.setattr(T, "lay_dn", lambda m, cu=None, *a: ({"ct": {"m": m}}, []))
    T.chay(["EEE", "AAA"], ra, phut=5, luong=1, in_ra=lambda *_: None)
    assert T._doc(f"{ra}/dn/EEE.json")["tl"] == [{"loai": "BCTC"}] and "tl" not in T._doc(f"{ra}/dn/AAA.json")


def test_web_tai_lieu_tai_file_rieng():
    import pathlib
    h = (pathlib.Path(__file__).parents[1] / "docs" / "ma" / "index.html").read_text(encoding="utf-8")
    assert 'lay(DL + "tl/" + ma + ".json", false)' in h and "k.tl || k.n?.tl" in h and 'const GOC_TL = "https://cafefnew.mediacdn.vn/"' in h


def test_chuan_bi_phan_phu_loi_nguon_giu_so_cu(tmp_path, monkeypatch):
    """14/11/2026: nến 1' VN-Index quá hạn lúc đêm làm hỏng cả lượt chuẩn bị → phần phụ lỗi giữ số lần trước + cảnh báo;
    phần chính (danh sách mã) lỗi vẫn dừng."""
    import json
    import pandas as pd
    from thi_truong import dung, nguon, quy_web, tinh
    ra = tmp_path / "chuan_bi.json"
    ra.write_text(json.dumps({"ho_so": {"tb": 1.0}, "vni_ngay": [["2026-11-12", 1600.0]], "nn_san": [["2026-11-12", 1.0]],
                              "nhom": {"VN30": ["AAA"]}, "quy": {"x": 1}}), encoding="utf-8")
    monkeypatch.setattr(quy_web, "lay", lambda q, _in: q)
    monkeypatch.setattr(nguon, "tat_ca_ma", lambda: [{"symbol": "AAA", "type": "STOCK", "board": "HSX", "icbCode2": "1"}])
    monkeypatch.setattr(nguon, "ten_nganh", lambda: {"1": "Ngân hàng"})
    monkeypatch.setattr(nguon, "bang_gia", lambda ds: [])
    monkeypatch.setattr(tinh, "chuan_bang", lambda x: pd.DataFrame())
    monkeypatch.setattr(nguon, "song_song", lambda f, ds, n: {})

    def het_han(*a, **k):
        raise ValueError("gap-chart: Read timed out")
    monkeypatch.setattr(nguon, "nen", het_han)
    monkeypatch.setattr(nguon, "cafef", lambda *a, **k: [{"Ngay": "13/11/2026", "GtMua": 3e9, "GtBan": 1e9}])
    monkeypatch.setattr(nguon, "nhom", het_han)
    log = []
    cb = dung.chuan_bi(str(ra), in_tien_do=log.append)
    assert cb["ho_so"] == {"tb": 1.0} and cb["vni_ngay"] == [["2026-11-12", 1600.0]] and cb["nhom"] == {"VN30": ["AAA"]}
    assert cb["nn_san"] != [["2026-11-12", 1.0]] and cb["vu"] == ["AAA"]                 # nguồn chạy được → số mới
    assert sum("::warning::" in x for x in log) == 3
    monkeypatch.setattr(nguon, "tat_ca_ma", het_han)
    with pytest.raises(ValueError):
        dung.chuan_bi(str(ra), in_tien_do=log.append)


def test_dung_lai_trang_ngoai_gio(tmp_path, monkeypatch):
    """Lượt đổi code ngoài giờ: dữ liệu thị trường lấy từ trang, chỉ làm mới tín hiệu bot + mã đang giữ; trang lỗi /
    hỏng → OSError / ValueError (main dựng từ nguồn như cũ)."""
    import io
    import urllib.request
    from thi_truong import __main__ as M
    trang = {"du_lieu.json": json.dumps({"phien": "2026-11-13", "chi_so": [1], "danh_muc": ["CU"], "tin_hieu": None}),
             "quy_ls.json": json.dumps({"a": 1})}

    def mo(url, timeout=None):
        ten = url.rsplit("/", 1)[-1]
        if ten not in trang:
            raise OSError("404")
        return io.BytesIO(trang[ten].encode())
    monkeypatch.setattr(urllib.request, "urlopen", mo)
    g = tmp_path / "giu.txt"
    g.write_text("AAA,BBB", encoding="utf-8")
    monkeypatch.setenv("MA_GIU_FILE", str(g))
    ra = tmp_path / "du_lieu.json"
    out = dung.dung_lai_trang("https://x.github.io/r/thi_truong/", str(ra), in_tien_do=lambda s: None)
    assert out["chi_so"] == [1] and out["danh_muc"] == ["AAA", "BBB"]
    assert json.loads(ra.read_text(encoding="utf-8"))["danh_muc"] == ["AAA", "BBB"]
    assert json.loads((tmp_path / "quy_ls.json").read_text(encoding="utf-8")) == {"a": 1}
    trang["du_lieu.json"] = "{}"
    with pytest.raises(ValueError):
        dung.dung_lai_trang("https://x/thi_truong", str(ra), in_tien_do=lambda s: None)
    goi = []
    monkeypatch.setattr(dung, "doc_chuan_bi", lambda *a: {"x": 1})
    monkeypatch.setattr(dung, "chup", lambda cb, ra: goi.append(cb))
    assert M.main(["--tu_trang", "https://x/thi_truong", "--ra", str(ra)]) == 0 and goi == [{"x": 1}]   # trang hỏng → nguồn
