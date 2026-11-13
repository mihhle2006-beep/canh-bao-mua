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
INPUT_RIENG = {"canh_bao.yml": {"vong", "che_do"}, "bang_thi_truong.yml": {"chuan_bi"}, "ke_hoach_dhcd.yml": {"con_lai"}}


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
    return {"id": id_, "created_at": luc_vn.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "event": event,
            "status": "completed"}


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
        if "/" in wf:                                                   # repo kín danh-muc – test riêng
            continue
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
    for ten in sorted({x[0] for x in dong_ho.LICH if "/" not in x[0]}):
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


def test_dong_ho_viec_repo_kin_danh_muc():
    """Vòng đồng bộ DNSE / xin OTP ở danh-muc (máy Mac): gọi bằng token repo kín; đang chạy / chờ Mac → không gọi; token
    thiếu quyền (403) → bỏ mốc, cảnh báo; chưa có token → bỏ, cảnh báo 1 lần."""
    import urllib.error
    lich = [("danh-muc/dnse_dong_bo.yml", "35 8 * * 1-5", {"vong": "true"}, 360)]
    luc = datetime(2026, 11, 6, 9, 10, tzinfo=VN)
    dm = GiaGH({"dnse_dong_bo.yml": [_run(1, datetime(2026, 11, 6, 5, 35, tzinfo=VN))]})
    cb = GiaGH()
    da = dong_ho.DongHo(cb, lich=lich, in_ra=lambda *_: None, gh_khac={"danh-muc": dm}).buoc(luc)
    assert len(da) == 1 and dm.goi_ds == [("dnse_dong_bo.yml", {"vong": "true"})] and cb.goi_ds == []
    dang = GiaGH({"dnse_dong_bo.yml": [{**_run(2, datetime(2026, 11, 6, 6, 0, tzinfo=VN)), "status": "queued"}]})
    assert dong_ho.DongHo(cb, lich=lich, in_ra=lambda *_: None, gh_khac={"danh-muc": dang}).buoc(luc) == []
    assert dang.goi_ds == []

    class Cam(GiaGH):
        def goi(self, wf, inputs=None, ref="main"):
            raise urllib.error.HTTPError("u", 403, "Resource not accessible", {}, None)

    log = []
    dh = dong_ho.DongHo(cb, lich=lich, in_ra=log.append, gh_khac={"danh-muc": Cam()})
    dh.buoc(luc)
    assert "Actions: Read and write" in log[-1] and len(dh.xong) == 1
    log = []
    dh = dong_ho.DongHo(cb, lich=lich, in_ra=log.append)
    dh.buoc(luc)
    dh.buoc(luc + timedelta(minutes=1))
    assert len(log) == 1 and "DANH_MUC_TOKEN_GHI" in log[0]
    assert all(x[0] in ("danh-muc/dnse_dong_bo.yml", "danh-muc/dat_lenh.yml", "bang-thi-truong/bang.yml")
               for x in dong_ho.LICH if "/" in x[0])
    otp = [x[1] for x in dong_ho.LICH if x[0] == "danh-muc/dat_lenh.yml"]
    assert otp == ["40 8 * * 1-5", "5 9 * * 1-5"]                      # 09:05 xin lại OTP (lịch GitHub hay trễ / bỏ)


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
    can = {x[0] for x in dong_ho.LICH if "/" not in x[0]} - KHONG_GAC
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


def test_giam_sat_loi_tu_chay_lai_hoac_bao_ngay():
    tu = datetime(2026, 11, 6, 8, 0, tzinfo=UTC)

    def r(id_, wf, phut, kq="failure", lan=1, nhanh="main", tt="completed"):
        luc = (tu + timedelta(minutes=phut)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"id": id_, "path": f".github/workflows/{wf}", "name": wf.split(".")[0], "conclusion": kq, "run_attempt": lan,
                "head_branch": nhanh, "updated_at": luc, "created_at": luc, "status": tt, "html_url": f"https://x/{id_}"}

    class GH:
        def __init__(self):
            self.runs, self.post = [], []

        def _goi(self, duong, du_lieu=None, phuong=None):
            if phuong == "POST":
                self.post.append(duong)
                return {}
            return {"workflow_runs": self.runs}

    gh, gui, log = GH(), [], []
    gs = dong_ho.GiamSat(gh, tu, gui=gui.append, in_ra=log.append)
    gh.runs = [r(1, "tra_cuu_web.yml", 5),                     # dữ liệu → tự chạy lại, không nhắn
               r(2, "danh_muc.yml", 6),                        # → nhắn ngay
               r(3, "quet_dinh_ky.yml", 7, "success"),
               r(4, "canh_bao.yml", 8, "cancelled"),           # hủy (concurrency – có lần mới hơn) → bỏ qua
               r(8, "canh_bao.yml", 12, None, tt="queued"),     # lần mới hơn đang chờ
               r(5, "kiem_thu.yml", 9),                        # tự nhắn
               r(6, "canh_bao.yml", 9, nhanh="claude/x"),      # nhánh thử
               r(7, "gia_lap.yml", -30)]                       # trước lúc đồng hồ chạy
    tin = gs.buoc()
    assert gh.post == ["actions/runs/1/rerun-failed-jobs"]
    assert len(tin) == 1 and "danh_muc lỗi lúc 15:06" in tin[0] and len(gui) == 1
    assert all("tra_cuu_web" not in x for x in gui)
    assert gs.buoc() == [] and len(gui) == 1                  # đã xét → không nhắn / chạy lại lặp
    gh.runs = [r(1, "tra_cuu_web.yml", 30, lan=2)]            # chạy lại vẫn lỗi → nhắn
    tin = gs.buoc()
    assert len(tin) == 1 and "đã tự chạy lại 1 lần, vẫn lỗi" in tin[0] and gh.post == ["actions/runs/1/rerun-failed-jobs"]
    assert not any("http" in x for x in log)                  # log công khai: chỉ tên workflow
    # bị huỷ KHÔNG có lần mới hơn (deploy Pages quá 10' – 05/11/2026) → coi là lỗi: CHAY_LAI chạy lại cả lần chạy
    gh.runs = [r(20, "bang_thi_truong.yml", 40, "cancelled")]
    assert gs.buoc() == [] and gh.post[-1] == "actions/runs/20/rerun"
    gh.runs = [r(21, "danh_muc.yml", 41, "cancelled")]
    tin = gs.buoc()
    assert len(tin) == 1 and "bị huỷ" in tin[0]


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


def test_kiem_quyen_token():
    """Thử quyền token repo kín bằng mã HTTP: đọc commit, đọc lần chạy Actions, PUT enable (ghi Actions, không đổi gì)."""
    goi_ds = []

    def gia(ma_ghi):
        def goi(ph, d):
            goi_ds.append((ph, d))
            return ma_ghi if ph == "PUT" else 200
        return goi
    assert dong_ho.kiem_quyen("x", "o/r", gia(204)) == {"doc_code": True, "doc_actions": True, "ghi_actions": True}
    assert goi_ds[-1] == ("PUT", "repos/o/r/actions/workflows/dnse_dong_bo.yml/enable")
    assert dong_ho.kiem_quyen("x", "o/r", gia(403))["ghi_actions"] is False
    assert dong_ho.kiem_quyen("x", "o/r", lambda ph, d: None) == {"doc_code": None, "doc_actions": None, "ghi_actions": None}


def test_kiem_token_canh_bao(monkeypatch):
    het = datetime(2026, 11, 15, tzinfo=UTC)
    monkeypatch.setattr(dong_ho, "han_token", lambda tk: het if tk == "a" else None)
    gui = []
    monkeypatch.setattr(dong_ho, "nhan_tele", gui.append)
    monkeypatch.setenv("DANH_MUC_TOKEN_GHI", "a")
    monkeypatch.setattr(dong_ho, "kiem_quyen", lambda tk: {"doc_code": True, "doc_actions": True, "ghi_actions": True})
    monkeypatch.delenv("DANH_MUC_TOKEN_DOC", raising=False)
    log = []
    canh = dong_ho.kiem_token(datetime(2026, 11, 6, 20, 5, tzinfo=VN), in_ra=log.append)
    assert len(canh) == 1 and "còn 8 ngày" in canh[0] and len(gui) == 1 and "DANH_MUC_TOKEN_GHI" in gui[0]
    assert all("a" != x for x in log)
    gui.clear()
    assert dong_ho.kiem_token(datetime(2026, 10, 1, tzinfo=VN), in_ra=log.append) == [] and gui == []


def test_may_mac_khong_nhan_viec_bao_ngay_1_lan_va_bao_khi_nhan_lai():
    """Job self-hosted chờ máy ≥ 10' trong phiên → 1 tin / đợt; máy nhận → 1 tin "đã nhận lại"; ngoài phiên / chờ hàng
    concurrency / job GitHub-hosted → im."""
    T = datetime(2026, 11, 13, 9, 30, tzinfo=VN)                       # thứ Sáu

    def iso(t):
        return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    class GH:
        def __init__(self):
            self.runs, self.jobs, self.job1 = [], {}, {}

        def _goi(self, duong, du_lieu=None, phuong=None):
            if duong.startswith("actions/runs?"):
                assert "status=queued" in duong
                return {"workflow_runs": self.runs}
            if duong.startswith("actions/runs/"):
                return {"jobs": self.jobs.get(int(duong.split("/")[2]), [])}
            return self.job1[int(duong.split("/")[2])]

    gh, gui, log = GH(), [], []
    mac = dong_ho.MayMac(gh, gui=gui.append, in_ra=log.append)
    gh.runs = [{"id": 1, "name": "DNSE dong bo", "created_at": iso(T - timedelta(minutes=12))},
               {"id": 2, "name": "Kiem thu", "created_at": iso(T - timedelta(minutes=30))}]
    gh.jobs = {1: [{"id": 11, "status": "queued", "labels": ["self-hosted", "vn"], "created_at": iso(T - timedelta(minutes=12))}],
               2: [{"id": 21, "status": "queued", "labels": ["ubuntu-24.04"], "created_at": iso(T - timedelta(minutes=30))}]}
    assert mac.buoc(T - timedelta(minutes=5)) is None                  # mới chờ 7' → chưa báo
    tin = mac.buoc(T)
    assert tin and "Máy Mac CHƯA NHẬN VIỆC" in tin and "DNSE dong bo – chờ 12'" in tin and "09:18" in tin
    assert "Kiem thu" not in tin and len(gui) == 1                     # job GitHub-hosted chờ lâu: không phải lỗi Mac
    assert mac.buoc(T + timedelta(minutes=5)) is None and len(gui) == 1   # cùng đợt → không nhắn lặp
    gh.runs, gh.job1 = [], {11: {"id": 11, "status": "in_progress", "started_at": iso(T + timedelta(minutes=7))}}
    tin = mac.buoc(T + timedelta(minutes=10))
    assert tin and "đã nhận việc lại lúc 09:37" in tin and "19 phút" in tin and len(gui) == 2
    assert mac.buoc(T + timedelta(minutes=15)) is None and len(gui) == 2
    # đợt mới: job bị huỷ (không phải máy nhận) → chỉ ghi log
    gh.runs = [{"id": 3, "name": "Dat lenh", "created_at": iso(T)}]
    gh.jobs = {3: [{"id": 31, "status": "queued", "labels": ["self-hosted", "vn"], "created_at": iso(T)}]}
    assert mac.buoc(T + timedelta(minutes=20)) and len(gui) == 3
    gh.runs, gh.job1 = [], {31: {"id": 31, "status": "completed", "conclusion": "cancelled", "started_at": None}}
    assert mac.buoc(T + timedelta(minutes=25)) is None and len(gui) == 3 and "bị huỷ" in log[-1]
    # ngoài phiên / cuối tuần → không đọc API, không nhắn
    gh.runs = [{"id": 4, "name": "DNSE dong bo", "created_at": iso(T - timedelta(hours=3))}]
    gh.jobs = {4: [{"id": 41, "status": "queued", "labels": ["self-hosted", "vn"], "created_at": iso(T - timedelta(hours=3))}]}
    assert mac.buoc(T.replace(hour=16)) is None and mac.buoc(T + timedelta(days=1)) is None and len(gui) == 3
    assert mac.buoc(T.replace(hour=8, minute=29)) is None and mac.buoc(T.replace(hour=8, minute=30)) and len(gui) == 4
    assert not any("http" in x or "DNSE" in x or "Dat lenh" in x for x in log)   # log công khai: không tên việc / link


def test_kenh_telegram_he_thong_va_chinh(monkeypatch):
    """Workflow lỗi / token → kênh hệ thống (bot giả lập); máy Mac chưa nhận việc → bot chính (ảnh hưởng lệnh trong phiên).
    Chưa đặt kênh hệ thống → bot chính như cũ."""
    import urllib.parse
    gui = []

    class R:
        def read(self):
            return b"{}"
    monkeypatch.setattr(dong_ho.urllib.request, "urlopen",
                        lambda url, data=None, timeout=None: gui.append((url, urllib.parse.parse_qs(data.decode()))) or R())
    for k, v in {"TELEGRAM_TOKEN": "CHINH", "TELEGRAM_CHAT_ID": "1", "TELEGRAM_TOKEN_HE_THONG": "HT",
                 "TELEGRAM_CHAT_ID_HE_THONG": "2"}.items():
        monkeypatch.setenv(k, v)
    dong_ho.nhan_tele("lỗi")
    dong_ho.nhan_tele("mac", "chinh")
    dong_ho.MayMac(None).gui("mac 2")
    assert [("botHT" in u, c["chat_id"][0]) for u, c in gui] == [(True, "2"), (False, "1"), (False, "1")]
    monkeypatch.delenv("TELEGRAM_TOKEN_HE_THONG")
    dong_ho.nhan_tele("lỗi")
    assert "botCHINH" in gui[-1][0] and gui[-1][1]["chat_id"] == ["1"]


def _bt(expr, sec):
    """Tính biểu thức ${{ … }} của GitHub (|| && ngoặc, secrets.X) bằng Python – secret thiếu = ''."""
    import re
    py = re.sub(r"!contains\((secrets\.\w+), ':'\)", r"(':' not in \1)", expr)
    py = py.replace("&&", " and ").replace("||", " or ")
    py = re.sub(r"secrets\.(\w+)", lambda m: repr(sec.get(m.group(1), "")), py)
    return eval(py)  # noqa: S307 – chỉ chuỗi hằng + and / or


def test_workflow_kenh_nghien_cuu_co_du_phong():
    """Báo cáo nghiên cứu: bot nghiên cứu riêng (TELEGRAM_TOKEN_NGHIEN_CUU → chat riêng của chủ quỹ) hoặc nhóm
    (TELEGRAM_CHAT_ID_NGHIEN_CUU, bot danh mục); chưa đặt gì → bot / chat cũ y như trước (không mất tin)."""
    import re
    goc = {"TELEGRAM_TOKEN": "CHINH", "TELEGRAM_CHAT_ID": "toi", "TELEGRAM_TOKEN_DANH_MUC": "DM",
           "TELEGRAM_CHAT_ID_DANH_MUC": "toi_dm"}
    so = 0
    for f in glob.glob(os.path.join(WF, "*.yml")):
        dong = open(f, encoding="utf-8").read().splitlines()
        for i, d in enumerate(dong):
            if "TELEGRAM_TOKEN:" not in d or "NGHIEN_CUU" not in d:
                continue
            tk = re.search(r"\$\{\{(.*?)\}\}", d).group(1)
            ch = re.search(r"\$\{\{(.*?)\}\}", dong[i + 1]).group(1)
            assert "TELEGRAM_CHAT_ID:" in dong[i + 1], (f, i)
            cu_tk = "DM" if tk.strip().startswith("secrets.TELEGRAM_TOKEN_NGHIEN_CUU || secrets.TELEGRAM_TOKEN_DANH_MUC") else "CHINH"
            cu_ch = "toi_dm" if "CHAT_ID_DANH_MUC" in ch else "toi"
            assert (_bt(tk, goc), _bt(ch, goc)) == (cu_tk, cu_ch), (f, "chưa đặt gì phải như cũ")
            assert (_bt(tk, {**goc, "TELEGRAM_TOKEN_NGHIEN_CUU": "NC"}), _bt(ch, {**goc, "TELEGRAM_TOKEN_NGHIEN_CUU": "NC"})) \
                == ("NC", "toi"), (f, "bot nghiên cứu → chat riêng chủ quỹ")
            assert (_bt(tk, {**goc, "TELEGRAM_CHAT_ID_NGHIEN_CUU": "-4"}), _bt(ch, {**goc, "TELEGRAM_CHAT_ID_NGHIEN_CUU": "-4"})) \
                == ("DM", "-4"), (f, "nhóm nghiên cứu → bot danh mục")
            sai = {**goc, "TELEGRAM_TOKEN_NGHIEN_CUU": "NC", "TELEGRAM_CHAT_ID_NGHIEN_CUU": "911:AA"}   # token để nhầm chỗ chat id
            assert (_bt(tk, sai), _bt(ch, sai)) == ("NC", "toi"), (f, "secret nhóm chứa token → bỏ qua")
            so += 1
    assert so >= 15


def test_bang_tre_bao_dung_va_chay_lai():
    """Vòng bảng thị trường (repo bang-thi-truong) không có lượt mới > 4 phút trong giờ giao dịch → 1 tin / đợt, lượt mới lại →
    1 tin "chạy lại"; ngoài giờ / ngày nghỉ (commit "Nghỉ <ngày>") im."""
    class Gh:
        repo = "chu/bang-thi-truong"

        def __init__(self):
            self.c = {"commit": {"committer": {"date": "2026-11-16T03:00:00Z"}, "message": "Bảng p/20261116/1200.json"}}

        def _goi(self, duong):
            assert duong == "commits/nhanh"
            return self.c
    gh, tin = Gh(), []
    bt = dong_ho.BangTre(gh, gui=tin.append, in_ra=lambda *_: None)
    t = lambda s: datetime.fromisoformat(s).replace(tzinfo=VN)                         # noqa: E731
    assert bt.buoc(t("2026-11-16 10:02")) is None                                     # 2 phút – chưa
    assert "ĐỨNG" in bt.buoc(t("2026-11-16 10:05")) and "10:00" in tin[0]
    assert bt.buoc(t("2026-11-16 10:10")) is None and len(tin) == 1                   # 1 tin / đợt
    gh.c["commit"]["committer"]["date"] = "2026-11-16T03:11:00Z"
    assert bt.buoc(t("2026-11-16 10:12")).startswith("Bảng thị trường chạy lại") and len(tin) == 2
    assert bt.buoc(t("2026-11-16 12:00")) is None and bt.buoc(t("2026-11-14 10:30")) is None   # trưa / thứ Bảy
    gh.c["commit"] = {"committer": {"date": "2026-11-16T02:20:00Z"}, "message": "Nghỉ 2026-11-16"}
    assert bt.buoc(t("2026-11-16 10:30")) is None and len(tin) == 2


def test_giam_sat_ghi_ten_repo():
    class Gh:
        def _goi(self, duong, *a):
            return {"workflow_runs": [{"id": 5, "path": ".github/workflows/kho.yml", "name": "Bang thi truong",
                                       "status": "completed", "conclusion": "failure", "head_branch": "main",
                                       "event": "workflow_dispatch", "updated_at": "2026-11-16T03:00:00Z",
                                       "created_at": "2026-11-16T02:00:00Z", "html_url": "u"}]}
    tin = []
    gs = dong_ho.GiamSat(Gh(), datetime(2026, 11, 16, tzinfo=UTC), gui=tin.append, in_ra=lambda *_: None, nhan="[bảng] ")
    gs.buoc()
    assert "❌ [bảng] Bang thi truong lỗi" in tin[0]
    assert "bang.yml" in dong_ho.CHAY_LAI and "trien_khai.yml" in dong_ho.KHONG_BAO
