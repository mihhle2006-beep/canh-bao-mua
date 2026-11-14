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


def test_non_ket_hop_3_khung():
    """Nón "kết hợp" (danh-muc KET_LUAN "non" / bt_non.py gopβ|λ – đã xoá, lịch sử git): TB của [phân vị lãi quá khứ / (σ lúc đó / σ nền)^β ×
    (σ hiện tại / σ nền)^β] và nón σ; λ, β theo khung như NON_CG – so hàm JS với đúng công thức phép đo."""
    c = np.array(_nen(900, 8)["c"])
    c[-15:] *= np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.05, 15)))       # 15 nến cuối biến động mạnh
    kq = _js(f"const c = {json.dumps(c.tolist())};\n" + """
      const k = (kh, H, L, Ls) => non_du_bao(c, H, "ls", L, Ls, NON_CG[kh]);
      console.log(JSON.stringify({D: [5, 20, 60].map(H => k("D", H, 750, 60)), W: [1, 4, 12].map(H => k("W", H, 260, 26)), M: [1, 3].map(H => k("M", H, 1e6, 12)),
        k0: non_du_bao(c, 20, "ls", 750), phut: non_du_bao(c, 20, "ls", 1e6, 12, NON_CG["15"]), b: [5, 10, 20, 60].map(h => non_beta(NON_CG.D.be, h))}));""")
    assert kq["b"][0] == 0.75 and abs(kq["b"][1] - 0.5) < 1e-12 and kq["b"][2] == kq["b"][3] == 0.25      # nội suy theo log
    assert kq["k0"].get("ti") is None and kq["phut"].get("ti") is None                # không có bảng khung → phân vị thuần
    ln, P = np.log(c), [0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975]
    Z = np.array([-1.959964, -1.281552, -0.67449, 0, 0.67449, 1.281552, 1.959964])
    t, r1 = len(ln) - 1, np.diff(ln, prepend=ln[0])
    for kh, L, Ls, lam, tam in (("D", 750, 60, 0.94, ((5, 0.75), (20, 0.25), (60, 0.25))),
                                ("W", 260, 26, 0.73, ((1, 0.75), (4, 0.5), (12, 0.25))), ("M", 10 ** 6, 12, 0.5, ((1, 0.5), (3, 0.25)))):
        v, var = np.var(r1[1:21]), []
        for i in range(len(ln)):
            v = lam * v + (1 - lam) * r1[i] ** 2 if i > 20 else v
            var.append(v)
        sg = np.sqrt(var)
        for (H, be), k in zip(tam, kq[kh]):
            i0 = max(0, t - L)
            w, s = (ln[H:] - ln[:-H])[i0:t - H + 1], sg[i0:t - H + 1]
            nen = np.sqrt(np.mean(s ** 2))
            st, z = float(np.clip(sg[t] / nen, 0.3, 3)), w / np.clip(s / nen, 0.3, 3) ** be
            sig = Z * r1[t - Ls + 1:t + 1].std(ddof=1) * np.sqrt(H)
            ref = np.exp(((np.quantile(z, P) - np.median(z)) * st ** be + sig) / 2)
            assert abs(k["ti"] - st) < 1e-9 and st > 1.2, (kh, H)                # đang biến động mạnh hơn nền
            assert np.allclose([k["q"][j][H] for j in range(7)], ref, atol=1e-9), (kh, H)
    rong = lambda q, h: q[5][h] - q[1][h]
    assert rong(kq["D"][1]["q"], 20) > rong(kq["k0"]["q"], 20)                     # mã đang biến động mạnh → nón rộng hơn nón cũ


def test_menu_chi_bao_va_thu_vien_v5():
    h = open(TRANG, encoding="utf-8").read()
    assert h.count("${menu_khoi()}") == 2                           # trang thường + toàn màn hình dùng chung menu
    for k in ("rsi", "macd", "stoch", "adx", "atr", "obv", "mfi"):
        assert f'["{k}", ' in h
    for k in ('["bb", "Dải Bollinger"', "data-cbh", "data-cbk", "data-cbmd", "localStorage.setItem(KHOA_CB"):
        assert k in h, k
    assert "addLineSeries" not in h and ".setMarkers(" not in h and "addHistogramSeries" not in h   # API v4 cũ
    assert "LW.createSeriesMarkers(" in h and "ch.addSeries(LW[loai]" in h and "attachPrimitive(new NonPrim(" in h
    lib = open("docs/ma/lib/lightweight-charts.standalone.production.js", encoding="utf-8").read(300)
    assert "Lightweight Charts™ v5." in lib


def test_ma10_tuan_va_rs():
    import datetime as dt
    x = _nen(400, 7)
    d, t = [], dt.date(2024, 1, 3)
    while len(d) < 400:
        if t.weekday() < 5:
            d.append(t.isoformat())
        t += dt.timedelta(days=1)
    v = list(1000 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, 400))))
    kq = _js(f"const d = {json.dumps(d)}, c = {json.dumps(x['c'])}, v = {json.dumps(v)};\n"
             "console.log(JSON.stringify({m: cb_ma10_tuan(d, c), r: cb_rs(c, v, 250)}));")
    # tham chiếu: 9 tuần đã đóng gần nhất (giá đóng cửa phiên cuối tuần) + giá đóng cửa hôm nay
    c, tuan = x["c"], [dt.date.fromisoformat(z).isocalendar()[:2] for z in d]
    for i in (60, 61, 199, 399):
        dong = [c[j] for j in range(i) if j + 1 < len(c) and tuan[j + 1] != tuan[j] and tuan[j] != tuan[i]]
        assert abs(kq["m"][i] - (sum(dong[-9:]) + c[i]) / 10) < 1e-9
    assert kq["m"][0] is None and kq["m"][30] is None                       # chưa đủ 9 tuần đã đóng
    rs = [ci / vi for ci, vi in zip(c, v)]
    g = rs[400 - 1 - 250]
    assert abs(kq["r"]["rs"][-1] - rs[-1] / g * 100) < 1e-9 and abs(kq["r"]["rs"][149] - 100) < 1e-9
    for i in range(250, 400):
        moi = rs[i] > max(rs[i - 250:i])
        assert kq["r"]["dinh"][i] == moi and kq["r"]["som"][i] == (moi and not c[i] > max(c[i - 250:i]))


def test_squeeze_momentum_va_vix_fix():
    x = _nen(300, 11)
    kq = _js(f"const x = {json.dumps(x)};\n"
             "console.log(JSON.stringify({q: cb_squeeze(x.h, x.l, x.c, 20, 2, 20, 1.5), w: cb_wvf(x.c, x.l, 22, 20, 2, 50, 0.85)}));")
    h, l_, c = (np.array(x[k]) for k in ("h", "l", "c"))
    tr = np.r_[h[0] - l_[0], np.maximum.reduce([h[1:] - l_[1:], abs(h[1:] - c[:-1]), abs(l_[1:] - c[:-1])])]
    for i in (60, 150, 299):
        w = c[i - 19:i + 1]
        bb_tr, bb_du = w.mean() + 2 * w.std(), w.mean() - 2 * w.std()
        uk, lk = w.mean() + 1.5 * tr[i - 19:i + 1].mean(), w.mean() - 1.5 * tr[i - 19:i + 1].mean()
        nen = 1 if bb_du > lk and bb_tr < uk else 0 if bb_du < lk and bb_tr > uk else -1
        assert kq["q"]["nen"][i] == nen
        src = [c[j] - ((h[j - 19:j + 1].max() + l_[j - 19:j + 1].min()) / 2 + c[j - 19:j + 1].mean()) / 2 for j in range(i - 19, i + 1)]
        b, a = np.polyfit(np.arange(20), src, 1)
        assert abs(kq["q"]["val"][i] - (a + b * 19)) < 1e-9
    assert kq["q"]["val"][37] is None and kq["q"]["val"][38] is not None
    wv = [None] * 21 + [(c[i - 21:i + 1].max() - l_[i]) / c[i - 21:i + 1].max() * 100 for i in range(21, 300)]
    for i in (40, 120, 299):
        assert abs(kq["w"]["w"][i] - wv[i]) < 1e-9
        seg = np.array(wv[i - 19:i + 1])
        tren = seg.mean() + 2 * seg.std()
        mx = max(wv[i - 49:i + 1]) if i >= 21 + 49 else None
        assert kq["w"]["dinh"][i] == bool(wv[i] >= tren or (mx is not None and wv[i] >= mx * 0.85))


def test_macd_tuan_tren_khung_ngay_khop_bot():
    """cb_macd_tuan = MACD tuần của bot (gộp tuần W-FRI, EMA adjust=False) – lọc tuần: tuần ĐÃ ĐÓNG (ffill nhãn thứ Sáu),
    giá trị tạm tính trong tuần = MACD tuần nếu tuần chốt ở giá hôm nay. Có tuần nghỉ thứ Sáu."""
    import pandas as pd
    x = _nen(700, 5)
    idx = pd.bdate_range("2023-01-02", periods=700)
    nghi = {idx[k] for k in (54, 159, 304, 509) if idx[k].day_of_week == 4} | {idx[k] for k in (99, 400)}
    giu = [i for i, t in enumerate(idx) if t not in nghi]
    idx, c = idx[giu], [x["c"][i] for i in giu]
    d = [t.strftime("%Y-%m-%d") for t in idx]
    kq = _js(f"const d = {json.dumps(d)}, c = {json.dumps(c)};\nconsole.log(JSON.stringify(cb_macd_tuan(d, c)));")
    s = pd.Series(c, index=idx)

    def macd_tuan(cs):
        w = cs.resample("W-FRI").last().dropna()
        m = w.ewm(span=12, adjust=False).mean() - w.ewm(span=26, adjust=False).mean()
        return m, m.ewm(span=9, adjust=False).mean()
    m, sg = macd_tuan(s)
    ok = (m > sg).reindex(idx, method="ffill").fillna(False).to_numpy()
    tu = 40 * 5                                                                     # sau 34 tuần khởi động
    assert all(v is None for v in kq["m"][:100])
    for i in range(tu, len(c)):
        assert kq["dat"][i] == bool(ok[i]), i
    for i in (tu, tu + 3, 450, len(c) - 1):                                         # tạm tính: tuần chốt ở giá phiên i
        m2, s2 = macd_tuan(s.iloc[:i + 1])
        assert abs(kq["m"][i] - m2.iloc[-1]) < 1e-9 and abs(kq["s"][i] - s2.iloc[-1]) < 1e-9
        assert abs(kq["h"][i] - (m2.iloc[-1] - s2.iloc[-1])) < 1e-9
    assert sum(kq["dat"][i] != kq["dat"][i - 1] for i in range(tu + 1, len(c))) >= 2   # có đổi trạng thái để kiểm


def test_do_trung_toan_lich_su_khop_non_du_bao_va_ket_tran_san():
    """non_do_trung (lùi TOÀN lịch sử, chỉ tính tầm H cho nhanh) cho ĐÚNG nón như dựng lại non_du_bao trên c[:t+1] ở từng mốc
    (kết hợp / phân vị / σ, có kẹp biên độ); số quãng độc lập = đoạn H nến không chồng; non_kep: không vượt (1 ± biên độ)^phiên."""
    r = np.random.default_rng(8)
    sig = 0.02 * np.exp(np.cumsum(r.normal(0, 0.04, 900)) * 0.3)
    c = list(np.round(20 * np.exp(np.cumsum(r.standard_t(4, 900) * sig / np.sqrt(2))), 4))
    kq = _js(f"const c = {json.dumps(c)};\n" + r"""
      const out = {};
      for (const [ten, kieu, cg, H, L, Ls, kep] of [["kh5", "ls", NON_CG.D, 5, 750, 60, {lim: 0.07, phien: 1}], ["kh20", "ls", NON_CG.D, 20, 750, 60, null],
          ["tuan", "ls", NON_CG.W, 4, 260, 26, {lim: 0.1, phien: 5}], ["ls", "ls", null, 20, 750, 60, null], ["sg", "sigma", null, 5, 750, 60, {lim: 0.07, phien: 1}]]) {
        const nh = non_do_trung(c, H, kieu, L, Ls, cg, kep, 250);
        let n = 0; const trong = [0, 0, 0];                         // dựng lại non_du_bao từng mốc (cách chậm)
        for (let t = 250; t + H < c.length; t += Math.max(1, Math.ceil(H / 4), Math.ceil((c.length - H - 250) / 600))) {
          let k = non_du_bao(c.slice(0, t + 1), H, kieu, L, Ls, cg); if (!k) continue;
          if (kep) k = {...k, q: non_kep(k.q, kep.lim, kep.phien)};
          const x = c[t + H] / c[t]; n++;
          [[2, 4], [1, 5], [0, 6]].forEach(([a, b], j) => { if (x >= k.q[a][H] * (1 - 1e-12) && x <= k.q[b][H] * (1 + 1e-12)) trong[j]++; });
        }
        out[ten] = {nh, cham: {n, p: trong.map(v => v / n)}};
      }
      const q = non_du_bao(c, 5, "ls", 750, 60, NON_CG.D).q, kq_ = non_kep(q.map(a => a.map(v => v * 1.5)), 0.07, 1);
      out.kep = kq_.every(a => a.every((v, h) => v <= Math.pow(1.07, h) + 1e-12 && v >= Math.pow(0.93, h) - 1e-12));
      out.bd = [NON_BD("HSX"), NON_BD("HNX"), NON_BD("UPCOM"), NON_BD("")];
      console.log(JSON.stringify(out));""")
    for ten in ("kh5", "kh20", "tuan", "ls", "sg"):
        nh, cham = kq[ten]["nh"], kq[ten]["cham"]
        assert nh["n"] == cham["n"], ten
        assert all(abs(a - b) < 1e-9 for a, b in zip(nh["p"], cham["p"])), (ten, nh["p"], cham["p"])
    H = {"kh5": 5, "kh20": 20, "tuan": 4, "ls": 20, "sg": 5}
    for ten, z in kq.items():
        if ten in H:
            nh = z["nh"]
            assert 0 < nh["doc_lap"] <= nh["n"]
            assert all(abs(s - 1.96 * np.sqrt(p * (1 - p) / nh["doc_lap"])) < 1e-9 for p, s in zip(nh["p"], nh["sai"]))
    assert kq["kep"] is True and kq["bd"] == [0.07, 0.10, 0.15, 0.07]


def test_chuan_do_trung_du_khung_tam():
    """NON_CHUAN (đo trên mọi mã HOSE / HNX / UPCoM) có đủ tầm mà trang dùng: ngày 5/20/60 · tuần round(h/5) · tháng round(h/21)."""
    kq = _js("console.log(JSON.stringify(NON_CHUAN));")
    for kh, tam in (("D", (5, 20, 60)), ("W", (1, 4, 12)), ("M", (1, 3))):
        for H in tam:
            for z in kq[kh][str(H)]:
                assert len(z) == 4 and 0.4 < z[0] < z[1] < z[2] < 1 and z[3] > 300


def _ham(*ten):
    h = open(TRANG, encoding="utf-8").read()
    return "\n".join(re.search(rf"^function {t}\(.*?^\}}", h, re.M | re.S).group(0) for t in ten)


def test_su_kien_duoi_khoi_luong_va_lenh_he_co_gia():
    """Sự kiện DN gom theo nến (dải dưới khối lượng, không còn mốc trên nến) kèm chi tiết; lệnh hệ có giá vào / ra / cắt lỗ
    → vị trí nến (lệnh còn mở kéo tới nến cuối), mốc ▲ / ▼ ghi giá; file lệnh bản cũ (5 trường) vẫn chạy."""
    if not shutil.which("node"):
        pytest.skip("không có node")
    h0 = open(TRANG, encoding="utf-8").read()
    hang = "\n".join(re.search(rf"^const {t} = .*?;$", h0, re.M | re.S).group(0) for t in ("SK_LOAI", "SK_THU_TU"))
    js = ("const so = (v, l = 0) => Number(v).toFixed(l), ngay_vn = d => d;\n" + hang + "\n"
          + _ham("vi_tri_ngay", "su_kien_nen", "lenh_nen", "moc_lenh_he") + r"""
      const x = {d: ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"], c: [10, 11, 12, 13, 14]};
      const n = {sk: [{ngay: "2026-01-06", ma_sk: "DIV", ten: "Cổ tức  tiền 1.000đ"}, {ngay: "2026-01-06", ma_sk: "AGM", ten: "ĐHCĐ"},
                      {ngay: "2027-01-01", ma_sk: "DIV", ten: "tương lai"}, {ngay: "2026-01-07", ma_sk: "AIS", ten: "Niêm yết bổ sung"}],
                 nb: [{ngay: "2026-01-08", hd: "Mua", kq: 1000, ten: "A", cv: "HĐQT"}, {ngay: "2026-01-08", hd: "Mua", kq: 500, ten: "B"},
                      {ngay: "2026-01-08", hd: "Bán", kq: 0, ten: "C"}, {ngay: "2026-01-09", hd: "Bán", kq: null, dk: 2000, ten: "D", tt: "Đang thực hiện"}]};
      const r = {cot: ["Q3.25", "Q4.25", "Q1.26", "Q2.26", "Q3.26"], dt: [100, 110, 120, 130, 150], ln: [10, 11, 12, 13, 20],
                 cb: [["Q2.26", "2025-08-01"], ["Q3.26", "2026-01-07"]]};
      const sk = su_kien_nen(x, n, r);
      const lh = [["2026-01-05", "2026-01-07", 9.5, 1.2, 0, 10, 11, 9.3, "cắt lỗ", 0], ["2026-01-08", "", 2, 0.3, 1, 13, null, 12, "", 0], ["2026-01-06", "2026-01-07", -3, -1, 0]];
      console.log(JSON.stringify({sk, L: lenh_nen(x, lh).map(L => [L.i, L.j, L.mo]), m: moc_lenh_he(x, lh).map(z => z.text)}));
    """)
    kq = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    assert kq.returncode == 0, kq.stderr
    r = json.loads(kq.stdout)
    # bong bóng kiểu FireAnt: tương lai / ngoài chuỗi / kết quả 0 cp bỏ; cùng nến xếp theo SK_THU_TU; đăng ký chưa khớp = rỗng
    assert [(z["i"], z["k"], z["so"], z["dk"]) for z in r["sk"]] == [(1, "ĐH", 1, False), (1, "CT", 1, False), (2, "BC", 1, False),
                                                                   (2, "K", 1, False), (3, "M", 2, False), (4, "B", 1, True)]
    sk = {z["k"]: z for z in r["sk"]}
    assert sk["CT"]["ct"] == ["Cổ tức tiền 1.000đ"] and sk["M"]["ct"][0] == "A (HĐQT): đã mua 1000 cp"
    assert sk["BC"]["ct"] == ["Q3.26 công bố 2026-01-07 · DT 150 tỷ (+50% cùng kỳ) · LNST 20 tỷ (+100% cùng kỳ)"]
    assert sk["B"]["ct"] == ["D: đăng ký bán 2000 cp · Đang thực hiện"] and sk["K"]["ten"] == "Sự kiện khác"
    assert r["L"] == [[0, 2, False], [3, 4, True], [1, 2, False]]
    assert r["m"] == ["Mua 10.00", "Bán 11.00 +1.2R", "Mua (đang giữ) 13.00", "Mua", "-1.0R"]
    h = open(TRANG, encoding="utf-8").read()
    assert "moc_su_kien(x, them.n)" not in h and "new SuKienPrim(ch, SK_)" in h and "new LenhPrim(ch, nen, LHI, x.c)" in h
    assert 'viet(vi.get(t_chuoi(e.time)), true)' in h and "lh_o(i)" in h and "sk_o(i)" in h
    # điện thoại: nút chú giải ẩn + không bấm được cho tới khi chạm dòng
    assert ".chu-pane:not(.cg-cham) .cg-n{opacity:0;pointer-events:none}" in h and "function cg_cham(el)" in h
    assert 'data-cbx="lh"${CB.lh ? " checked" : ""}>Điểm mua – bán của hệ (backtest)' in h


def test_hop_chi_bao_va_du_lieu():
    """ƒx mở hộp "Chỉ báo và dữ liệu" (14/11/2026, bố cục kiểu FireAnt): mọi chỉ báo ngăn dưới / lớp phân tích đều có mục."""
    import re
    h = open(TRANG, encoding="utf-8").read()
    for k in ("function cbm_mo()", "data-cbm aria-haspopup", "Chỉ báo và dữ liệu", "data-cbmq", "Thêm vào biểu đồ", "Thêm vào ngăn mới",
              "Gỡ khỏi biểu đồ", "function ts_html(k)", "ts_doc(el, k);", "↑↓ chọn · Enter thêm", "e.stopImmediatePropagation()"):
        assert k in h, k
    assert "menu_cb" not in h and "data-cbmo>ƒx" not in h                    # menu thả xuống cũ đã bỏ
    duoi = set(re.findall(r'\["(\w+)", "[^"]+", "\w*"\]', h[h.index("const CB_DUOI"):h.index("// Kiểu từng đường")]))
    cbm = h[h.index("const CBM = ["):h.index("const cbm_ta")]
    assert duoi and set(re.findall(r'\["p:(\w+)"', cbm)) == duoi
    assert '...LP_DS.map(([k, ten, , ta]) => ["lp:" + k' in cbm


def _js_moi(ma_js):
    """Chạy khối CB_MOI (chỉ báo mới) cùng hàm thuần trong node."""
    h = open(TRANG, encoding="utf-8").read()
    i, j = h.index("// CHỈ BÁO MỚI (CB_MOI"), h.index("const MOI = Object.fromEntries")
    return _js(h[i:j] + "\n" + ma_js)


def test_chi_bao_moi_tinh_duoc_moi_mau():
    x = _nen(320, 7)
    kq = _js_moi(f"const x = {json.dumps(x)};\n" + """
      const o = {};
      for (const z of CB_MOI) { const r = z.f(x, z.ts.map(t => t[1]), "D"), d = {};
        for (const [id] of z.d) { const a = r[id] || []; d[id] = [a.length, a.filter(v => v != null && isFinite(v)).length, a.slice(-1)[0]]; }
        o[z.k] = {noi: z.noi, d, so_ts: z.ts.length, gh: z.ts.every(t => t[2] <= t[1] && t[1] <= t[3])}; }
      console.log(JSON.stringify(o));""")
    assert len(kq) >= 55
    for k, z in kq.items():
        assert z["gh"], k                                                   # mặc định nằm trong [min, max]
        for id_, (n, co, cuoi) in z["d"].items():
            assert n == 320, (k, id_)
            assert co > 0, (k, id_)                                          # có giá trị
            if k not in ("khq", "magic", "ce", "zz"):                         # magic / ce: tăng hoặc giảm (dưới); zz dừng ở cực trị cuối
                assert cuoi is not None, (k, id_)
    assert all(kq[k]["d"]["xuong"][2] is not None or kq[k]["d"]["len"][2] is not None for k in ("magic", "ce"))


def test_chi_bao_moi_dung_cong_thuc():
    x = _nen(260, 11)
    kq = _js_moi(f"const x = {json.dumps(x)};\n" + """
      console.log(JSON.stringify({wma: cb_wma(x.c, 10), cci: cb_cci(x.h, x.l, x.c, 20), wr: cb_willr(x.h, x.l, x.c, 14),
        cmf: cb_cmf(x.h, x.l, x.c, x.v, 20), ar: cb_aroon(x.h, x.l, 25), chop: cb_chop(x.h, x.l, x.c, 14), z: cb_zscore(x.c, 20),
        hma: cb_hma(x.c, 16), psy: cb_psy(x.c, 12)}));""")
    c, h_, l_, v = (np.array(x[k]) for k in ("c", "h", "l", "v"))
    i = 200
    w = c[i - 9:i + 1]
    assert kq["wma"][i] == pytest.approx((w * np.arange(1, 11)).sum() / 55)
    tp = (h_ + l_ + c) / 3; t = tp[i - 19:i + 1]
    assert kq["cci"][i] == pytest.approx((tp[i] - t.mean()) / (0.015 * np.abs(t - t.mean()).mean()))
    hh, ll = h_[i - 13:i + 1].max(), l_[i - 13:i + 1].min()
    assert kq["wr"][i] == pytest.approx(-100 * (hh - c[i]) / (hh - ll))
    mfv = ((c - l_) - (h_ - c)) / (h_ - l_) * v
    assert kq["cmf"][i] == pytest.approx(mfv[i - 19:i + 1].sum() / v[i - 19:i + 1].sum())
    a = h_[i - 25:i + 1]
    assert kq["ar"]["up"][i] == pytest.approx(100 * (25 - (i - (i - 25 + int(np.flatnonzero(a == a.max())[-1])))) / 25)
    tr = np.maximum(h_[1:] - l_[1:], np.maximum(abs(h_[1:] - c[:-1]), abs(l_[1:] - c[:-1])))
    s = tr[i - 14:i].sum()                                                   # tr[k] ứng với nến k+1
    assert kq["chop"][i] == pytest.approx(100 * np.log10(s / (h_[i - 13:i + 1].max() - l_[i - 13:i + 1].min())) / np.log10(14))
    w = c[i - 19:i + 1]
    assert kq["z"][i] == pytest.approx((c[i] - w.mean()) / w.std())
    assert kq["psy"][i] == pytest.approx(100 * (np.diff(c[i - 12:i + 1]) > 0).sum() / 12)
    def wma(a, n):
        return [None if k < n - 1 or any(z is None for z in a[k - n + 1:k + 1]) else sum(a[k - n + 1 + j] * (j + 1) for j in range(n)) / (n * (n + 1) / 2) for k in range(len(a))]
    a8, a16 = wma(list(c), 8), wma(list(c), 16)
    raw = [None if a8[k] is None or a16[k] is None else 2 * a8[k] - a16[k] for k in range(len(c))]
    assert kq["hma"][i] == pytest.approx(wma(raw, 4)[i])


def test_magic_trend_mui_ten_o_cho_doi_chieu():
    x = _nen(320, 7)
    kq = _js_moi(f"const x = {json.dumps(x)};\n" + """
      const r = cb_magic(x.h, x.l, x.c, 20, 5, 1), n = cb_noi(r);
      console.log(JSON.stringify({len: r.len, doi: n.doi}));""")
    ln, doi = kq["len"], kq["doi"]
    mong = [0] + [(1 if ln[i] else -1) if ln[i] is not None and ln[i - 1] is not None and ln[i] != ln[i - 1] else 0 for i in range(1, len(ln))]
    assert doi == mong and 1 in doi and -1 in doi
    h = open(TRANG, encoding="utf-8").read()
    assert 'shape: h > 0 ? "arrowUp" : "arrowDown"' in h and '"▲ Mua" : "▼ Bán"' in h
