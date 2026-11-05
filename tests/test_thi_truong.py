# -*- coding: utf-8 -*-
"""Bảng thị trường (thi_truong): chuẩn hoá bảng giá, hồ sơ thanh khoản, chuỗi khối ngoại, cờ kỹ thuật, dựng du_lieu.json
từ dữ liệu mẫu (không gọi mạng)."""
import json

import numpy as np
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
            if "DANH_MUC" in t or "danh-muc" in t:
                cham.append(st)
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
    (job,) = d["jobs"].values()
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
    ngoai = set(re.findall(r'\.src = "(https://[^"/]+)', h))                 # script tải động: chỉ TradingView + SheetJS
    assert ngoai == {"https://s3.tradingview.com", "https://cdnjs.cloudflare.com"}, ngoai
    assert 'const DL = "du_lieu/", TT = "../thi_truong/du_lieu.json"' in h
    for tab in ("tong-quan", "tin", "ho-so", "lanh-dao", "co-dong", "co-tuc", "tai-chinh", "chi-so", "dinh-gia", "lich-su",
                "bao-cao", "tai-lieu", "he-thong"):
        assert f'["{tab}",' in h, tab
    assert not re.search(r"fetch\(\s*['\"]https?:", h)
    assert not re.search("[\U0001F300-\U0001FAFF\u2605\u2B50]", h)                     # không emoji / sticker
    assert "const esc = " in h and "const url = u => /^https?:" in h
    t = open("docs/thi_truong/index.html", encoding="utf-8").read()
    assert 'href="../ma/#${esc(r.ma)}"' in t and 'href="../ma/"' in t



def test_tra_cuu_dn_gon(tmp_path):
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
    kb = T.ho_so_kbs("TCB")
    assert kb["thanh_lap"] == "06/08/1993" and kb["gia_chao_san"] == 128000 and kb["nganh_nghe"] == "- A"
    assert kb["cong_ty"][0] == {"ten": "Con", "so_huu": 79.8, "von": None, "ngay": "2025-12-31", "ghi_chu": ""}
    assert kb["lanh_dao"][0]["cv"] == "TGĐ" and kb["khac"] == {"Khac": [{"a": 1}]}
    assert T.tom_tat_simplize("TCB")["linh_vuc"] == "L"
    bc = T.bao_cao_ctck("TCB")
    assert bc[0]["ctck"] == "SSI" and bc[0]["mt"] == 37.5 and bc[0]["link"] == "https://x/a.pdf"     # gộp trùng SSI cùng ngày
    assert len(bc) == 2 and bc[1]["ctck"] == "VCBS"
    dn, loi = T.lay_dn("TCB", {"ct": {"cu": 1}})
    assert set(loi) == {"ct", "cc", "cd", "sk", "nb", "cs", "tin", "nn_nam", "tl"} and dn["ct"] == {"cu": 1} and "kbs" in dn


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
    assert T.thu_tu(["BBB"], ra, "2026-02-01", lam_moi=True) == ["BBB"]
    monkeypatch.setattr(T, "lay_gia", lambda m, san="": {"d": ["2026-11-05"], "c": [1.0]})
    monkeypatch.setattr(T, "lay_dn", lambda m, cu=None, *a: ({"ct": {"m": m}}, []) if m != "BBB" else ({}, ["ct"] * T.SO_PHAN_DN))
    xong, loi, con = T.chay(["AAA", "BBB", "CCC"], ra, phut=5, luong=2, in_ra=lambda *_: None)
    assert (xong, loi, con) == (3, 0, 0)
    assert T._doc(f"{ra}/dn/AAA.json")["ct"] == {"m": "AAA"} and T._doc(f"{ra}/dn/BBB.json") == {"cap_nhat": "2026-02-01"}
    assert T._doc(f"{ra}/gia/CCC.json")["c"] == [1.0]
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
    phan = ("ct", "cc", "cd", "sk", "nb", "cs", "tin", "bc", "kbs", "sz", "nn_nam", "tl")

    def gia_lap(*a, **k):
        goi.append(1)
        raise ValueError("HTTP 404")
    monkeypatch.setattr(T, "iq", gia_lap)
    monkeypatch.setattr(T, "tin_cafef", gia_lap)
    monkeypatch.setattr(T, "bao_cao_ctck", gia_lap)
    monkeypatch.setattr(T, "ho_so_kbs", gia_lap)
    monkeypatch.setattr(T, "tom_tat_simplize", gia_lap)
    monkeypatch.setattr(T, "tai_lieu", gia_lap)
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
