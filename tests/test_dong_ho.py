# -*- coding: utf-8 -*-
"""Đồng hồ (cong_cu/dong_ho.py + dong_ho.yml) và job gác lịch trễ (gac.yml) – không gọi mạng."""
import glob
import io
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

import yaml

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "cong_cu"))
import dong_ho  # noqa: E402

VN = dong_ho.VN
UTC = timezone.utc
WF = os.path.join(GOC, ".github", "workflows")
KHONG_GAC = {"canh_bao.yml",        # vòng lặp: lượt trùng xếp hàng rồi tự thoát (hết giờ), tổng kết có cờ đã gửi
             "danh_muc.yml",        # job kiem tự chặn chạy trùng (lịch 14:50 chờ 15:03 xem đã chạy chưa)
             "nhip_thi_truong.yml",  # tự chặn khi có máy nhịp khác đang chạy
             "bang_thi_truong.yml",  # dựng lại trang – chạy thêm vô hại
             "lenh_tele.yml"}       # đọc tin bot – chạy thêm vô hại
# workflow phân biệt lịch / bấm tay bằng input riêng (đồng hồ truyền input đó) thay vì input "lich"
INPUT_RIENG = {"canh_bao.yml": {"vong", "che_do"}, "bang_thi_truong.yml": {"chuan_bi"}}


def _yml(ten):
    with open(os.path.join(WF, ten), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _on(d):
    return d.get(True) or d.get("on") or {}


def _cron(d):
    return [x["cron"] for x in (_on(d).get("schedule") or [])]


def _inputs(d):
    wd = _on(d).get("workflow_dispatch") or {}
    return set((wd.get("inputs") or {}).keys())


class GiaGH:
    """GitHub giả: lần chạy theo workflow (created_at ISO UTC) + ghi lại các lần gọi."""

    def __init__(self, runs=None, loi=None):
        self.runs, self.loi, self.goi_ds = runs or {}, loi, []

    def lan_chay(self, wf):
        if self.loi:
            raise self.loi
        return self.runs.get(wf, [])

    def goi(self, wf, inputs=None, ref="main"):
        self.goi_ds.append((wf, inputs))
        self.runs.setdefault(wf, []).append({"id": 999, "created_at": datetime.now(UTC).isoformat(), "event": "workflow_dispatch"})


def _run(id_, luc_vn, event="workflow_dispatch"):
    return {"id": id_, "created_at": luc_vn.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "event": event}


# ---------------------------------------------------------------- lịch
def test_khop_gio_vn_va_cron_github():
    thu5 = datetime(2026, 11, 5, 6, 50, tzinfo=VN)                      # thứ Năm
    assert dong_ho.moc_gan_nhat("43 6 * * 1-5", thu5, 240) == datetime(2026, 11, 5, 6, 43, tzinfo=VN)
    assert dong_ho.moc_gan_nhat("43 6 * * 1-5", thu5, 5) is None        # quá hạn gọi bù
    assert dong_ho.moc_gan_nhat("43 6 * * 1-5", datetime(2026, 11, 7, 6, 50, tzinfo=VN), 240) is None   # thứ Bảy
    assert dong_ho.khop("7 9 * * 6", datetime(2026, 11, 7, 9, 7, tzinfo=VN))
    assert dong_ho.khop("47 0 * * 7", datetime(2026, 11, 8, 0, 47, tzinfo=VN))                          # CN = 7
    # cron GitHub: thứ 0 = CN (UTC) – "43 23 * * 0-4" = 06:43 giờ VN T2–T6
    assert dong_ho.khop("43 23 * * 0-4", datetime(2026, 11, 8, 23, 43, tzinfo=UTC), cron_gh=True)       # CN UTC
    assert not dong_ho.khop("43 23 * * 0-4", datetime(2026, 11, 6, 23, 43, tzinfo=UTC), cron_gh=True)   # T6 UTC
    assert dong_ho.khop("11 */2 * * *", datetime(2026, 11, 6, 4, 11, tzinfo=UTC), cron_gh=True)
    assert not dong_ho.khop("11 */2 * * *", datetime(2026, 11, 6, 5, 11, tzinfo=UTC), cron_gh=True)
    assert dong_ho.khop("5,35 2-7 * * 1-5", datetime(2026, 11, 6, 7, 35, tzinfo=UTC), cron_gh=True)


def test_lich_dong_ho_khop_dung_cron_trong_workflow():
    """Mỗi dòng LICH (giờ VN) = đúng 1 lịch cron (UTC) của workflow; input gửi đi workflow phải nhận; workflow phân biệt
    lịch / bấm tay thì đồng hồ truyền "lich" = đúng chuỗi cron đó (hoặc input riêng)."""
    tu, den = datetime(2026, 10, 26, tzinfo=VN), datetime(2026, 12, 8, tzinfo=VN)    # qua 2 lần đầu tháng (lịch tháng)
    sai = []
    for wf, lich, inputs, tre in dong_ho.LICH:
        d = _yml(wf)
        assert "workflow_dispatch" in _on(d), wf
        assert set(inputs) <= _inputs(d), f"{wf}: input {set(inputs) - _inputs(d)} không có trong workflow_dispatch"
        assert 0 < tre <= 1440, wf
        vn = {x.astimezone(UTC) for x in dong_ho.cac_moc(lich, tu, den)}
        assert vn, f"{wf} {lich}: không mốc nào"
        hop = [c for c in _cron(d) if set(dong_ho.cac_moc(c, tu.astimezone(UTC), den.astimezone(UTC), cron_gh=True)) == vn]
        if not hop:
            sai.append(f"{wf} '{lich}' không trùng lịch nào {_cron(d)}")
        elif "lich" in inputs:
            assert inputs["lich"] in hop, f"{wf}: lich={inputs['lich']} phải là {hop}"
    assert not sai, sai


def test_workflow_phan_biet_lich_thi_dong_ho_truyen_input():
    for ten in sorted({x[0] for x in dong_ho.LICH}):
        d = _yml(ten)
        jobs = {k: v for k, v in (d.get("jobs") or {}).items() if k != "gac"}
        nd = yaml.safe_dump(jobs, allow_unicode=True)
        if "github.event.schedule" not in nd and "event_name == 'schedule'" not in nd and 'event_name }}" = "schedule"' not in nd:
            continue
        can = INPUT_RIENG.get(ten, {"lich"})
        assert can & _inputs(d), f"{ten} xử lý lịch khác bấm tay nhưng không có input {can}"
        dong = [x for x in dong_ho.LICH if x[0] == ten]
        dat = [bool(can & set(x[2])) for x in dong]
        assert (any(dat) if ten in INPUT_RIENG else all(dat)), f"{ten}: đồng hồ phải truyền {can} ({dong})"


# ---------------------------------------------------------------- đồng hồ
def test_dong_ho_goi_dung_luc_va_khong_goi_lap():
    luc = datetime(2026, 11, 6, 6, 45, tzinfo=VN)                      # thứ Sáu 06:45
    gh = GiaGH({"loc_quy_b.yml": [_run(1, datetime(2026, 11, 6, 6, 7, 40, tzinfo=VN), "schedule")],
                "lenh_tele.yml": [_run(2, datetime(2026, 11, 6, 6, 36, tzinfo=VN))]})
    dh = dong_ho.DongHo(gh, in_ra=lambda *_: None)
    da = dh.buoc(luc)
    assert sorted(w for w, _ in gh.goi_ds) == ["canh_bao.yml", "tra_cuu_web.yml"]     # Lọc quỹ đã chạy đúng giờ → không gọi
    assert ("canh_bao.yml", {"vong": "sang"}) in gh.goi_ds
    assert all(isinstance(v, str) for _, i in gh.goi_ds for v in (i or {}).values())
    assert len(da) == 2
    assert dh.buoc(luc + timedelta(minutes=1)) == []                  # mốc đã xét → không gọi lặp
    # mốc mới (lenh_tele :37 mỗi giờ) – lần chạy cũ trước mốc không tính
    assert [w for w, _, _ in dh.buoc(datetime(2026, 11, 6, 7, 37, tzinfo=VN))] == ["lenh_tele.yml"]


def test_dong_ho_bu_tre_va_loi_api_thu_lai():
    log = []
    gh = GiaGH(loi=OSError("mạng"))
    dh = dong_ho.DongHo(gh, lich=[("kiem_thu.yml", "41 7 * * 1-5", {}, 600)], in_ra=log.append)
    assert dh.buoc(datetime(2026, 11, 6, 12, 0, tzinfo=VN)) == []
    assert "thử lại" in log[-1]
    gh.loi = None
    da = dh.buoc(datetime(2026, 11, 6, 12, 1, tzinfo=VN))            # phút sau: gọi bù (trễ 260')
    assert [w for w, _, _ in da] == ["kiem_thu.yml"] and "bù trễ 260'" in log[-1]
    thu = dong_ho.DongHo(GiaGH(), lich=[("kiem_thu.yml", "41 7 * * 1-5", {}, 600)], in_ra=lambda *_: None, thu=True)
    assert len(thu.buoc(datetime(2026, 11, 6, 7, 41, tzinfo=VN))) == 1 and thu.gh.goi_ds == []   # chạy thử: không gọi thật


def test_dong_ho_loi_4xx_bo_moc_loi_khac_thu_lai():
    import urllib.error

    class Loi(GiaGH):
        def goi(self, wf, inputs=None, ref="main"):
            raise urllib.error.HTTPError("u", self.ma, "x", {}, None)

    log = []
    gh = Loi()
    gh.ma = 422
    dh = dong_ho.DongHo(gh, lich=[("kiem_thu.yml", "41 7 * * 1-5", {}, 600)], in_ra=log.append)
    dh.buoc(datetime(2026, 11, 6, 7, 41, tzinfo=VN))
    assert "bỏ mốc" in log[-1] and len(dh.xong) == 1
    gh2 = Loi()
    gh2.ma = 502
    dh2 = dong_ho.DongHo(gh2, lich=[("kiem_thu.yml", "41 7 * * 1-5", {}, 600)], in_ra=log.append)
    dh2.buoc(datetime(2026, 11, 6, 7, 41, tzinfo=VN))
    assert "thử lại" in log[-1] and not dh2.xong
    # lần chạy ở nhánh PR không tính là đã chạy
    gh3 = GiaGH({"kiem_thu.yml": [{**_run(3, datetime(2026, 11, 6, 7, 42, tzinfo=VN)), "head_branch": "claude/x"}]})
    assert len(dong_ho.DongHo(gh3, lich=[("kiem_thu.yml", "41 7 * * 1-5", {}, 600)], in_ra=log.append)
               .buoc(datetime(2026, 11, 6, 7, 45, tzinfo=VN))) == 1


def test_doc_han_token():
    assert dong_ho.doc_han("2026-12-01 00:00:00 UTC") == datetime(2026, 12, 1, tzinfo=UTC)
    assert dong_ho.doc_han("2026-12-01 00:00:00 -0800") == datetime(2026, 12, 1, 8, tzinfo=UTC)
    assert dong_ho.doc_han("xx") is None


def test_dong_ho_thu_in_ra():
    out = io.StringIO()
    with redirect_stdout(out):
        assert dong_ho.main(["--thu", "2026-11-06 14:52"]) == 0
    s = out.getvalue()
    assert "quet_dinh_ky.yml" in s and "danh_muc.yml" in s and "mốc 14:50" in s


# ---------------------------------------------------------------- gác lịch trễ
def test_gac_bo_lich_tre_khi_da_chay_tu_moc():
    lich = "7 23 * * 0-4"                                             # 06:07 giờ VN T2–T6
    tre = datetime(2026, 11, 6, 10, 24, tzinfo=VN)                    # GitHub chạy trễ 4 giờ
    dong_ho_goi = _run(5, datetime(2026, 11, 6, 6, 7, 20, tzinfo=VN))
    hom_qua = _run(4, datetime(2026, 11, 5, 6, 8, tzinfo=VN))
    chay, ly_do = dong_ho.gac(GiaGH({"loc_quy_b.yml": [hom_qua, dong_ho_goi, _run(9, tre, "schedule")]}),
                              "loc_quy_b.yml", lich, tre, run_id=9)
    assert chay is False and "06:07" in ly_do and "trễ 257'" in ly_do
    # chỉ có lần chạy hôm qua + chính nó → chạy
    chay, _ = dong_ho.gac(GiaGH({"loc_quy_b.yml": [hom_qua, _run(9, tre, "schedule")]}), "loc_quy_b.yml", lich, tre, 9)
    assert chay is True
    # lần chạy thử ở nhánh PR không tính
    nhanh = {**dong_ho_goi, "head_branch": "claude/thu"}
    assert dong_ho.gac(GiaGH({"loc_quy_b.yml": [nhanh]}), "loc_quy_b.yml", lich, tre, 9)[0] is True
    assert dong_ho.gac(GiaGH({"loc_quy_b.yml": [{**dong_ho_goi, "head_branch": "main"}]}), "loc_quy_b.yml", lich, tre, 9)[0] is False
    # lỗi API / lịch lạ → vẫn chạy (không bỏ lượt nhầm)
    assert dong_ho.gac(GiaGH(loi=OSError("x")), "loc_quy_b.yml", lich, tre, 9)[0] is True
    assert dong_ho.gac(GiaGH(), "loc_quy_b.yml", "61 99 * * *", tre, 9)[0] is True
    # lịch tháng (mùng 1 19:17 UTC) chạy trễ sang mùng 2
    t = datetime(2026, 12, 2, 4, 0, tzinfo=VN)
    assert dong_ho.gac(GiaGH({"backtest.yml": [_run(7, datetime(2026, 12, 2, 2, 18, tzinfo=VN))]}),
                       "backtest.yml", "17 19 1 * *", t, 9)[0] is False


def test_gac_main_khong_phai_lich_thi_chay():
    out = io.StringIO()
    with redirect_stdout(out):
        dong_ho.main(["--gac", "loc_quy_b.yml", "--lich", ""])
    assert out.getvalue().strip().splitlines()[-1] == "chay=true"


def test_workflow_co_gac_dung_cach():
    """Workflow có lịch mà đồng hồ gọi (trừ KHONG_GAC): job gac (chỉ khi lịch) + mọi job gốc needs gac, vẫn chạy khi gac
    bỏ qua / lỗi; job sau không bị bỏ theo vì gac bị bỏ qua."""
    can = {x[0] for x in dong_ho.LICH} - KHONG_GAC
    co = set()
    for f in sorted(glob.glob(os.path.join(WF, "*.yml"))):
        ten = os.path.basename(f)
        d = _yml(ten)
        jobs = d.get("jobs") or {}
        if "gac" not in jobs or ten == "gac.yml":
            continue
        co.add(ten)
        g = jobs["gac"]
        assert g["uses"] == "./.github/workflows/gac.yml" and g["with"]["wf"] == ten, ten
        assert g["if"] == "github.event_name == 'schedule'", ten
        assert g["permissions"].get("actions") in ("read", "write"), ten
        for k, j in jobs.items():
            if k == "gac":
                continue
            needs = j.get("needs") or []
            needs = [needs] if isinstance(needs, str) else needs
            assert needs, f"{ten}:{k} phải needs gac"
            dk = str(j.get("if", ""))
            assert "!cancelled()" in dk or "always()" in dk, f"{ten}:{k} bị bỏ theo khi gac bỏ qua: if={dk!r}"
            if "gac" in needs:
                assert "needs.gac.outputs.chay != 'false'" in dk, ten
    assert can <= co, f"thiếu job gac: {can - co}"
    gac = _yml("gac.yml")
    assert "workflow_call" in _on(gac)
    run = " ".join(s.get("run", "") for s in gac["jobs"]["gac"]["steps"])
    assert "dong_ho.py --gac" in run and "chay=true" in run                 # lỗi → chạy


def test_dong_ho_yml():
    d = _yml("dong_ho.yml")
    assert d["permissions"]["actions"] == "write"
    assert _cron(d), "cần lịch dự phòng khởi động lại chuỗi"
    j = d["jobs"]["dong_ho"]
    assert "refs/heads/main" in j["if"]
    run = " ".join(s.get("run", "") for s in j["steps"])
    phut = float(run.split("--phut")[1].split()[0])
    assert phut + 10 <= j["timeout-minutes"] <= 360
    env = {k for s in j["steps"] for k in (s.get("env") or {})}
    assert {"GH_TOKEN", "TELEGRAM_TOKEN", "DANH_MUC_TOKEN_GHI"} <= env
    assert "print(os.environ" not in open(os.path.join(GOC, "cong_cu", "dong_ho.py"), encoding="utf-8").read()


def test_kiem_token_canh_bao(monkeypatch):
    het = datetime(2026, 11, 15, tzinfo=UTC)
    monkeypatch.setattr(dong_ho, "han_token", lambda tk: het if tk == "a" else None)
    gui = []
    monkeypatch.setattr(dong_ho, "nhan_tele", gui.append)
    monkeypatch.setenv("DANH_MUC_TOKEN_GHI", "a")
    monkeypatch.delenv("DANH_MUC_TOKEN_DOC", raising=False)
    log = []
    canh = dong_ho.kiem_token(datetime(2026, 11, 6, 20, 5, tzinfo=VN), in_ra=log.append)
    assert len(canh) == 1 and "còn 8 ngày" in canh[0] and len(gui) == 1 and "DANH_MUC_TOKEN_GHI" in gui[0]
    assert all("a" != x for x in log)
    gui.clear()
    assert dong_ho.kiem_token(datetime(2026, 10, 1, tzinfo=VN), in_ra=log.append) == [] and gui == []
