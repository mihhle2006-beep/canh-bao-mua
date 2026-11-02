# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

from canh_bao import nhip_mac as N

ENV = {"DANH_MUC_TOKEN": "t", "TELEGRAM_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"}


def _gio(h, m, ngay=3):                                                   # 03/11/2026 = thứ Ba
    return datetime(2026, 11, ngay, h, m, tzinfo=N.VN).astimezone(timezone.utc)


def test_can_bao_trong_phien_khi_im_lau():
    bg = _gio(10, 30)
    assert N.can_bao(bg, bg - timedelta(minutes=20)) is None              # còn nhịp
    assert N.can_bao(bg, bg - timedelta(minutes=50)) == 50
    assert N.can_bao(_gio(9, 0), bg - timedelta(hours=20)) is None        # trước 09:15
    assert N.can_bao(_gio(10, 30, ngay=7), bg - timedelta(days=2)) is None  # thứ Bảy
    assert N.can_bao(bg, None) is None                                    # không đọc được nhịp → không báo nhầm


def test_chay_bao_mot_lan(monkeypatch, tmp_path):
    monkeypatch.setattr(N, "CO", str(tmp_path / "co"))
    bg = _gio(13, 40)
    cu = (bg - timedelta(minutes=95)).strftime("%Y-%m-%dT%H:%M:%SZ")
    get = lambda url, tk: {"commit": {"committer": {"date": cu}}}        # noqa: E731
    tin = []
    assert N.chay(ENV, bg, get, lambda env, t: tin.append(t)) == 1
    assert "1 giờ 35 phút" in tin[0] and "12:05" in tin[0]
    assert N.chay(ENV, bg, get, lambda env, t: tin.append(t)) == 0 and len(tin) == 1   # cờ: không báo lặp
    def loi(url, tk):
        raise OSError
    assert N.nhip_cuoi(ENV, loi) is None
