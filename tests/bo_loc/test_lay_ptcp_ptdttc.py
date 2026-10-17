# -*- coding: utf-8 -*-
import importlib.util
import os


def test_chep_ptdttc_chi_khi_bat(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("lay_ptcp", os.path.join(os.path.dirname(__file__), "..", "..",
                                                                          "lay_ptcp.py"))
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    nguon, dich = tmp_path / "danh_muc", tmp_path / "bo_loc"
    nguon.mkdir()
    dich.mkdir()
    monkeypatch.setattr(L, "DICH", str(dich / "ptcp"))
    (nguon / "danh_muc_ptdttc.csv").write_text("ma\nMWG\n", encoding="utf-8")
    monkeypatch.delenv("CHEP_PTDTTC", raising=False)
    L.chep_ptdttc(str(nguon))                                              # workflow công khai → không chép
    assert not (dich / "danh_muc_ptdttc.csv").exists()
    monkeypatch.setenv("CHEP_PTDTTC", "1")
    L.chep_ptdttc(str(nguon))
    assert (dich / "danh_muc_ptdttc.csv").read_text(encoding="utf-8") == "ma\nMWG\n"
