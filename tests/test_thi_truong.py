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


def test_workflow_bang_thi_truong_khong_lay_danh_muc():
    import yaml
    d = yaml.safe_load(open(".github/workflows/bang_thi_truong.yml", encoding="utf-8"))
    for job in d["jobs"].values():
        for st in job.get("steps") or []:
            assert "danh-muc" not in json.dumps(st) and "DANH_MUC" not in json.dumps(st)
