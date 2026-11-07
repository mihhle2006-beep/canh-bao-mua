# -*- coding: utf-8 -*-
"""Chỉ báo kỹ thuật + nón dự báo của biểu đồ giá web (docs/ma/index.html, phần "CHỈ BÁO KỸ THUẬT (hàm thuần)"):
chạy các hàm JS trong node, so với công thức tham chiếu viết lại bằng Python."""
import json
import re
import shutil
import subprocess

import numpy as np
import pytest

TRANG = "docs/ma/index.html"


def _js(ma_js):
    if not shutil.which("node"):
        pytest.skip("không có node")
    h = open(TRANG, encoding="utf-8").read()
    i = h.index("// ---------------------------------------------------------------- CHỈ BÁO KỸ THUẬT (hàm thuần")
    j = h.index("// ---------------------------------------------------------------- hết chỉ báo kỹ thuật")
    phien_sau = re.search(r"^function phien_sau\(d\) \{.*?^\}", h, re.M | re.S).group(0)
    kq = subprocess.run(["node", "-e", phien_sau + "\n" + h[i:j] + "\n" + ma_js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr
    return json.loads(kq.stdout)


def _nen(n=300, seed=3):
    r = np.random.default_rng(seed)
    c = 20 * np.exp(np.cumsum(r.normal(0.0005, 0.02, n)))
    o = c * np.exp(r.normal(0, 0.005, n))
    h = np.maximum(o, c) * np.exp(np.abs(r.normal(0, 0.008, n)))
    l_ = np.minimum(o, c) * np.exp(-np.abs(r.normal(0, 0.008, n)))
    v = np.round(1e6 * np.exp(r.normal(0, 0.4, n)))
    return {k: [round(float(x), 6) for x in a] for k, a in (("o", o), ("h", h), ("l", l_), ("c", c), ("v", v))}


def _rma(x, n):
    o = [None] * len(x)
    vals = [(i, v) for i, v in enumerate(x) if v is not None]
    if len(vals) < n:
        return o
    e = sum(v for _, v in vals[:n]) / n
    o[vals[n - 1][0]] = e
    for i, v in vals[n:]:
        e = (e * (n - 1) + v) / n
        o[i] = e
    return o


def _ema(x, n):
    o = [None] * len(x)
    vals = [(i, v) for i, v in enumerate(x) if v is not None]
    if len(vals) < n:
        return o
    e = sum(v for _, v in vals[:n]) / n
    o[vals[n - 1][0]] = e
    a = 2 / (n + 1)
    for i, v in vals[n:]:
        e = v * a + e * (1 - a)
        o[i] = e
    return o


def _gan(a, b, tol=1e-7):
    assert len(a) == len(b)
    for i, (x, y) in enumerate(zip(a, b)):
        assert (x is None) == (y is None), (i, x, y)
        if x is not None:
            assert abs(x - y) <= tol * max(1, abs(y)), (i, x, y)


def test_chi_bao_khop_cong_thuc_tham_chieu():
    x = _nen()
    kq = _js(f"const x = {json.dumps(x)};\n" + """
      const m = cb_macd(x.c, 12, 26, 9), b = cb_bb(x.c, 20, 2), s = cb_stoch(x.h, x.l, x.c, 14, 3, 3), d = cb_dmi(x.h, x.l, x.c, 14);
      console.log(JSON.stringify({rsi: cb_rsi(x.c, 14), macd: m, bb: b, atr: cb_atr(x.h, x.l, x.c, 14), stoch: s, dmi: d,
        obv: cb_obv(x.c, x.v), mfi: cb_mfi(x.h, x.l, x.c, x.v, 14), atr_pt: cb_atr_pt(x.h, x.l, x.c, 14)}));""")
    c, h, l_, v = (np.array(x[k]) for k in ("c", "h", "l", "v"))
    n = len(c)
    # RSI Wilder
    d = np.diff(c)
    rs = [None] + list(zip(np.maximum(d, 0), np.maximum(-d, 0)))
    a, b = _rma([None] + list(np.maximum(d, 0)), 14), _rma([None] + list(np.maximum(-d, 0)), 14)
    _gan(kq["rsi"], [None if x_ is None else (100 if y == 0 else 100 - 100 / (1 + x_ / y)) for x_, y in zip(a, b)])
    assert len(rs) == n
    # MACD (EMA khởi đầu bằng SMA)
    e12, e26 = _ema(list(c), 12), _ema(list(c), 26)
    mm = [None if p is None or q is None else p - q for p, q in zip(e12, e26)]
    sg = _ema(mm, 9)
    _gan(kq["macd"]["m"], mm)
    _gan(kq["macd"]["s"], sg)
    # Bollinger 20, 2σ (độ lệch chuẩn tổng thể)
    gi = [None if i < 19 else c[i - 19:i + 1].mean() for i in range(n)]
    sd = [None if i < 19 else c[i - 19:i + 1].std() for i in range(n)]
    _gan(kq["bb"]["gi"], gi)
    _gan(kq["bb"]["tr"], [None if g is None else g + 2 * s_ for g, s_ in zip(gi, sd)])
    # ATR Wilder
    tr = [h[0] - l_[0]] + [max(h[i] - l_[i], abs(h[i] - c[i - 1]), abs(l_[i] - c[i - 1])) for i in range(1, n)]
    atr = _rma(tr, 14)
    _gan(kq["atr"], atr)
    _gan(kq["atr_pt"], [None if a_ is None else a_ / c[i] * 100 for i, a_ in enumerate(atr)])
    # Stochastic chậm 14, 3, 3
    raw = [None if i < 13 else (c[i] - l_[i - 13:i + 1].min()) / (h[i - 13:i + 1].max() - l_[i - 13:i + 1].min()) * 100 for i in range(n)]
    sk = [None if i < 15 else sum(raw[i - 2:i + 1]) / 3 for i in range(n)]
    _gan(kq["stoch"]["k"], sk)
    _gan(kq["stoch"]["d"], [None if i < 17 else sum(sk[i - 2:i + 1]) / 3 for i in range(n)])
    # OBV, MFI
    obv, s_ = [0.0], 0.0
    for i in range(1, n):
        s_ += v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0
        obv.append(s_)
    _gan(kq["obv"], obv)
    tp = (h + l_ + c) / 3
    mfi = [None] * n
    for i in range(14, n):
        a_ = sum(tp[j] * v[j] for j in range(i - 13, i + 1) if tp[j] > tp[j - 1])
        b_ = sum(tp[j] * v[j] for j in range(i - 13, i + 1) if tp[j] < tp[j - 1])
        mfi[i] = 100 if b_ == 0 else 100 - 100 / (1 + a_ / b_)
    _gan(kq["mfi"], mfi)
    # ADX / DMI: trong khoảng 0–100, +DI / −DI cùng có giá trị
    adx = [z for z in kq["dmi"]["adx"] if z is not None]
    assert adx and all(0 <= z <= 100 for z in adx) and kq["dmi"]["adx"][:27] == [None] * 27


def test_supertrend_sar_ichimoku():
    x = _nen(260, 5)
    kq = _js(f"const x = {json.dumps(x)};\n" + """
      console.log(JSON.stringify({st: cb_supertrend(x.h, x.l, x.c, 10, 3), sar: cb_psar(x.h, x.l, 0.02, 0.2), ich: cb_ichimoku(x.h, x.l, x.c, 9, 26, 52)}));""")
    c, h, l_ = (x[k] for k in ("c", "h", "l"))
    st, sar, ich = kq["st"], kq["sar"], kq["ich"]
    for i, (v, len_) in enumerate(zip(st["v"], st["len"])):           # tăng: đường dưới giá đóng cửa; giảm: trên
        if v is not None:
            assert (v <= c[i]) if len_ else (v >= c[i]), i
    assert {True, False} <= set(st["len"])
    for i, (v, len_) in enumerate(zip(sar["v"], sar["len"])):
        if v is not None and i > 1 and sar["len"][i - 1] == len_:      # không phải nến đảo chiều: SAR nằm ngoài nến
            assert (v <= l_[i]) if len_ else (v >= h[i]), i
    n = len(c)
    assert len(ich["spa"]) == n + 26 and ich["spa"][:26 + 25] == [None] * 51
    i = 100
    assert abs(ich["spa"][i + 26] - (ich["tenkan"][i] + ich["kijun"][i]) / 2) < 1e-9
    assert abs(ich["spb"][i + 26] - (max(h[i - 51:i + 1]) + min(l_[i - 51:i + 1])) / 2) < 1e-9
    assert ich["chikou"][i - 26] == c[i]


def test_non_du_bao_va_ngay_toi():
    x = _nen(900, 8)
    kq = _js(f"const c = {json.dumps(x['c'])};\n" + """
      console.log(JSON.stringify({ls: non_du_bao(c, 20, "ls", 750), sg: non_du_bao(c, 20, "sigma", 750, 60), it: non_du_bao(c.slice(0, 45), 20, "ls"),
        d: ngay_toi("2026-11-06", 3, "D"), w: ngay_toi("2026-11-06", 2, "W"), m: ngay_toi("2026-11-06", 2, "M"),
        ts: [cb_ts_dung("rsi", ["abc"]), cb_ts_dung("bb", ["0", "9,5"]), cb_ts_dung("sar", ["0,0237", 0.2])]}));""")
    ls = kq["ls"]
    assert ls["kieu"] == "ls" and ls["so_mau"] >= 700 and all(len(a) == 21 for a in ls["q"])
    for h in range(1, 21):                                          # 7 mốc tăng dần, trung vị = giá hiện tại
        col = [ls["q"][j][h] for j in range(7)]
        assert col == sorted(col) and abs(col[3] - 1) < 1e-12
    assert ls["q"][6][20] - ls["q"][0][20] > ls["q"][6][1] - ls["q"][0][1]          # loe dần theo thời gian
    # σ: e^(z·σ·√h), σ = độ lệch chuẩn mẫu của 60 lợi suất log cuối
    r = np.diff(np.log(x["c"]))[-60:]
    sd = r.std(ddof=1)
    assert abs(kq["sg"]["sd"] - sd) < 1e-12
    assert abs(kq["sg"]["q"][6][20] - np.exp(1.959964 * sd * np.sqrt(20))) < 1e-9
    assert kq["it"]["kieu"] == "sigma" and kq["it"]["thay"] is True      # lịch sử < 30 mẫu → chuyển sang σ
    assert kq["d"] == ["2026-11-09", "2026-11-10", "2026-11-11"]        # bỏ T7 / CN
    assert kq["w"] == ["2026-11-13", "2026-11-20"] and kq["m"] == ["2026-12-28", "2027-01-28"]
    assert kq["ts"] == [[14], [2, 5], [0.025, 0.2]]                    # tham số sai / ngoài khoảng → chặn


def test_menu_chi_bao_va_thu_vien_v5():
    h = open(TRANG, encoding="utf-8").read()
    assert h.count("${menu_khoi()}") == 2                           # trang thường + toàn màn hình dùng chung menu
    for k in ("rsi", "macd", "stoch", "adx", "atr", "obv", "mfi"):
        assert f'["{k}", ' in h
    for k in ('data-cbx="bb"', "data-cbh", "data-cbk", "data-cbmd", "localStorage.setItem(KHOA_CB"):
        assert k in h.replace("${khoa}", "bb") if k == 'data-cbx="bb"' else k in h, k
    assert "addLineSeries" not in h and ".setMarkers(" not in h and "addHistogramSeries" not in h   # API v4 cũ
    assert "LW.createSeriesMarkers(" in h and "ch.addSeries(LW[loai]" in h and "attachPrimitive(new NonPrim(" in h
    lib = open("docs/ma/lib/lightweight-charts.standalone.production.js", encoding="utf-8").read(300)
    assert "Lightweight Charts™ v5." in lib
