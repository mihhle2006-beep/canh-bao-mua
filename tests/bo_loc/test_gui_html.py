# -*- coding: utf-8 -*-
from bo_loc import gui_html as G


def test_tim_file_moi_nhat(tmp_path):
    for ngay in ("20261008", "20261009"):
        d = tmp_path / f"ket_qua_loc_quy_b_{ngay}"
        d.mkdir()
        (d / "chien_luoc_quy_b.html").write_text("<html></html>", encoding="utf-8")
    f, ngay = G.tim_file("quy_b", str(tmp_path))
    assert ngay == "20261009" and f.endswith("ket_qua_loc_quy_b_20261009/chien_luoc_quy_b.html")
    assert G.tim_file("xu_huong", str(tmp_path)) == (None, None)


def test_main_gui(tmp_path, monkeypatch):
    d = tmp_path / "ket_qua_loc_quy_b_20261009"
    d.mkdir()
    (d / "chien_luoc_quy_b.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    gui = []
    monkeypatch.setattr(G, "gui_file", lambda p, ten: gui.append(ten) or True)
    assert G.main(["--chien_luoc", "quy_b,xu_huong", "--che_do", "noi_bo"]) == 0
    assert gui == ["Bộ lọc Quỹ Bứt Phá 09-10-2026.html"]


def test_hai_che_do(tmp_path, monkeypatch):
    d = tmp_path / "ket_qua_loc_quy_b_20261009"
    d.mkdir()
    (d / "chien_luoc_quy_b.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "ma_mua_bo_loc.json").write_text('{"ma": {"SBT": ["quy_b"], "MCH": ["quy_b ½"], "GMD": ["xu_huong"]}}',
                                                encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    gui, tin = [], []
    monkeypatch.setattr(G, "gui_file", lambda p, ten: gui.append(ten) or True)
    monkeypatch.setattr(G, "gui_tin", lambda t: tin.append(t) or True)
    G.main(["--chien_luoc", "quy_b", "--chi_html", "--che_do", "noi_bo"])
    assert gui == ["Bộ lọc Quỹ Bứt Phá 09-10-2026.html"] and tin == []
    G.main(["--chien_luoc", "quy_b", "--che_do", "noi_bo"])
    assert len(gui) == 2 and tin[0].startswith("🔎 Bộ lọc Quỹ Bứt Phá – phiên 09/10/2026") and "MUA (2): SBT, MCH (½)" in tin[0]


def test_mac_dinh_gui_ban_ngoai(tmp_path, monkeypatch):
    d = tmp_path / "ket_qua_loc_quy_b_20261009"
    d.mkdir()
    (d / "chien_luoc_quy_b.html").write_text("<html></html>", encoding="utf-8")
    (d / "chien_luoc_quy_b_ngoai.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    gui = []
    monkeypatch.setattr(G, "gui_file", lambda p, ten: gui.append((p, ten)) or True)
    G.main(["--chien_luoc", "quy_b", "--chi_html"])
    assert gui[0][0].endswith("chien_luoc_quy_b_ngoai.html") and gui[0][1] == "Cổ phiếu đáng chú ý Quỹ Bứt Phá 09-10-2026.html"


def test_ban_ngoai_khong_lo_noi_bo(tmp_path):
    import numpy as np
    import pandas as pd
    from bo_loc.html import xuat_html
    k = pd.DataFrame([{"Kết luận": "[NÊN MUA]", "Mã": "FPT", "Hành động": "MUA", "Điểm tổng": 81.0, "Giá": 100.0,
                       "Vùng mua": "98 – 101", "Đặt LO": 99.0, "Cắt lỗ": 93.0, "Cắt lỗ %": -7.0, "Mục tiêu": 107.0,
                       "Mục tiêu %": 7.0, "R/R": 1.0, "MT 3R": 121.0, "Nhóm chiến lược": "A0 mua mới",
                       "Đạt điểm mua": "MACD cắt lên", "Vô hiệu khi": "", "Số CP": 1200, "Giá trị (tr)": 120.0,
                       "% NAV": 12.0, "Điểm mạnh": "xu hướng tốt (80)", "Điểm yếu": "", "Rủi ro / lưu ý": "",
                       "Cần chờ": ""},
                      {"Kết luận": "[THEO DÕI]", "Mã": "HPG", "Hành động": "THEO DÕI", "Điểm tổng": 55.0,
                       "Giá": 27.0, "Cần chờ": "giá về vùng mua", "MT 3R": np.nan}])
    f = tmp_path / "ngoai.html"
    xuat_html(str(f), "Riêng", "mô tả nội bộ", "09/10/2026", None, None, k, {}, [], None,
              thi_truong="Thị trường: 6/8 điểm (VND) · CL2 · có xu hướng (biên 60 phiên 15,0%)", che_do="ngoai")
    s = f.read_text(encoding="utf-8")
    assert "FPT" in s and "HPG" in s and "99" in s and "sức khoẻ 6/8" in s
    for lo in ("NAV", "1.200", "Số CP", "81", "/100", "A0", "CL2", "mô tả nội bộ", "Riêng", "Tiêu chí", "MACD"):
        assert lo not in s, lo


def test_ten_anh_khong_gach_duoi(tmp_path):
    from bo_loc.html import _anh
    p = tmp_path / "tong_quan_loc.png"
    p.write_bytes(b"x")
    assert 'alt="Tổng quan bộ lọc"' in _anh(str(p))
