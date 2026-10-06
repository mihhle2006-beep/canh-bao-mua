# -*- coding: utf-8 -*-
"""BIỂU ĐỒ CẤP DANH MỤC: dashboard, Markowitz, hiệp phương sai. (Biểu đồ từng mã do ptcp vẽ.)
Mọi hàm đóng figure sau khi lưu (không rò bộ nhớ khi chạy nhiều mã trên Colab)."""
import matplotlib.pyplot as plt
import numpy as np

from .tien_ich import so_vn


# ==========================================================================
# DASHBOARD DANH MỤC & MARKOWITZ
# ==========================================================================
def ve_dashboard_danh_muc(dm, file_png):
    b, t = dm["bang"], dm["tong"]
    fig, ax = plt.subplots(3, 2, figsize=(17, 16))
    a = ax[0, 0]                                      # (1) tỷ trọng TỔNG TÀI SẢN (gồm tiền mặt)
    giu = b[b["Giá trị TT (đ)"] > 0]
    gtri = list(giu["Giá trị TT (đ)"]) + [t["Tiền mặt (đ)"]]
    nhan = list(giu["Mã"]) + ["Tiền mặt"]
    if sum(gtri) > 0:
        a.pie(gtri, labels=nhan, autopct="%1.1f%%", startangle=90, wedgeprops={"width": 0.45}, textprops={"fontsize": 9})
    a.set_title("Tỷ trọng tổng tài sản (gồm tiền mặt)")
    a = ax[0, 1]                                      # (2) lãi/lỗ mã đang giữ
    if len(giu):
        v = giu["% L/L"]
        a.barh(giu["Mã"], v, color=np.where(v >= 0, "tab:green", "tab:red"))
        for i, (p, d) in enumerate(zip(v, giu["Lãi/Lỗ chưa thực hiện (đ)"])):
            a.text(p, i, f" {p:+.1f}% ({d / 1e3:,.0f} nghìn)", va="center", fontsize=8)
        a.axvline(0, color="black", lw=0.8)
        a.invert_yaxis()
    else:
        a.axis("off")
        a.text(0.5, 0.5, "Chưa có vị thế", ha="center", va="center", fontsize=14)
    a.set_title("Lãi/Lỗ chưa thực hiện so giá vốn")
    a = ax[1, 0]                                      # (3) upside vs cắt lỗ (đã đặt với mã đang giữ)
    y = np.arange(len(b))
    a.barh(y, b["Upside %"].fillna(0), color="tab:green", label="Tới mục tiêu")
    a.barh(y, b["% tới cắt lỗ"].fillna(0), color="tab:red", label="Tới cắt lỗ")
    a.set_yticks(y)
    a.set_yticklabels([f"{m}{' (TD)' if s == 'Theo dõi' else ''} – {q}" for m, s, q in
                       zip(b["Mã"], b["Trạng thái"], b["Quyết định KT"])], fontsize=8)
    a.axvline(0, color="black", lw=0.8)
    a.invert_yaxis()
    a.legend(fontsize=8)
    a.set_title("Mục tiêu vs cắt lỗ (mã đang giữ: mức ĐÃ ĐẶT; TD = theo dõi)")
    a = ax[1, 1]                                      # (4) lợi suất tích luỹ (giả định)
    tl = dm["tich_luy"] * 100
    for c, mau in zip(tl.columns, ("tab:green", "#e53935")):
        a.plot(tl.index, tl[c], color=mau, lw=2 if mau == "tab:green" else 1.4, label=c)
    a.axhline(0, color="black", lw=0.8)
    a.grid(alpha=0.3)
    if len(tl.columns):
        a.legend(fontsize=8)
    a.set_title("Lợi suất 52 tuần NẾU giữ tỷ trọng hiện tại (giả định, không phải lịch sử thật)", fontsize=10)
    a = ax[2, 0]                                      # (5) tương quan tuần
    tq = dm["tuong_quan"]
    im = a.imshow(tq.values, cmap="RdYlGn_r", vmin=-1, vmax=1)
    a.set_xticks(range(len(tq)))
    a.set_xticklabels(tq.columns, rotation=45)
    a.set_yticks(range(len(tq)))
    a.set_yticklabels(tq.index)
    for i in range(len(tq)):
        for j in range(len(tq)):
            if tq.iloc[i, j] == tq.iloc[i, j]:
                a.text(j, i, f"{tq.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=a, fraction=0.046)
    a.set_title("Tương quan lợi suất TUẦN (2 năm)")
    a = ax[2, 1]                                      # (6) stress test
    s = dm["stress"]
    a.barh(s["Kịch bản"], s["% tổng tài sản"], color="tab:red")
    for i, (p, d) in enumerate(zip(s["% tổng tài sản"], s["Lãi/Lỗ (đ)"])):
        a.text(p, i, f" {p:.1f}% ({d / 1e6:,.2f} tr)", va="center", ha="right", fontsize=8)
    a.invert_yaxis()
    a.set_title("Kiểm tra sức chịu đựng (% tổng tài sản)")
    fig.suptitle(f"DASHBOARD DANH MỤC | Tổng TS {t['Tổng tài sản (đ)'] / 1e6:,.1f} tr | CP {t['Tỷ trọng cổ phiếu %']:.0f}% | "
                 f"Beta {so_vn(t['Beta danh mục (gồm tiền mặt)'], 2)} | Rủi ro mở {t['Tổng rủi ro mở % TS']:.1f}% TS",
                 fontsize=14, fontweight="bold", color="#1B5E20")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(file_png, dpi=110)
    plt.close(fig)
    print(f"  ✔ Dashboard: {file_png}")


def ve_markowitz(mk, file_png):
    from .markowitz import _hq
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(18, 7.5), gridspec_kw={"width_ratios": [1.4, 1]})
    mc, bien = mk["mc"], mk["bien"]
    sc = a1.scatter(mc["Rủi ro"] * 100, mc["Lợi suất"] * 100, c=mc["Sharpe"], cmap="viridis", s=4, alpha=0.5)
    fig.colorbar(sc, ax=a1, label="Sharpe")
    if len(bien):
        a1.plot(bien["Rủi ro"] * 100, bien["Lợi suất"] * 100, color="black", lw=2.5, label="Đường biên hiệu quả")
    r_ms, v_ms, s_ms = _hq(mk["cac_dm"]["Sharpe lớn nhất"], mk["mu_vec"], mk["cov"], mk["rf"])
    xs = np.linspace(0, max(mc["Rủi ro"].max(), v_ms) * 100, 50)
    a1.plot(xs, mk["rf"] * 100 + s_ms * xs, color="gray", ls="--", lw=1, label="Đường thị trường vốn (CML)")
    for m in mk["ma"]:
        a1.scatter(mk["sigma"][m], mk["mu"][m], marker="D", s=60, color="black")
        a1.annotate(m, (mk["sigma"][m], mk["mu"][m]), xytext=(5, 5), textcoords="offset points", fontsize=9)
    mau = {"Hiện tại": "#00897B", "Phương sai nhỏ nhất (GMV)": "tab:green", "Sharpe lớn nhất": "tab:red",
           "Chia đều": "tab:orange", "GMV – không co, không trần": "lightgreen",
           "Sharpe – không co, không trần": "salmon"}
    for ten, w in mk["cac_dm"].items():
        r, v, s = _hq(w, mk["mu_vec"], mk["cov"], mk["rf"])
        a1.scatter(v * 100, r * 100, marker="*" if "Chia" not in ten and ten != "Hiện tại" else "o", s=300,
                   color=mau[ten], edgecolors="black", zorder=6, label=f"{ten}: LS {r * 100:.1f}%, σ {v * 100:.1f}%")
    a1.axhline(mk["rf"] * 100, color="gray", lw=0.6)
    a1.set_xlabel("Rủi ro năm (%)")
    a1.set_ylabel("Lợi suất kỳ vọng năm (%)")
    a1.legend(fontsize=8)
    a1.grid(alpha=0.3)
    bw = mk["bang_w"]
    x, rong = np.arange(len(bw)), 0.8 / bw.shape[1]
    for k, c in enumerate(bw.columns):
        a2.bar(x + k * rong - 0.4 + rong / 2, bw[c], rong, label=c, color=mau[c])
    a2.set_xticks(x)
    a2.set_xticklabels(bw.index)
    a2.set_ylabel("Tỷ trọng trong phần cổ phiếu (%)")
    a2.legend(fontsize=8)
    a2.grid(alpha=0.3, axis="y")
    fig.suptitle(f"MARKOWITZ (lợi suất tuần, Ledoit–Wolf) | Kỳ vọng: {mk['mo_ta_mu']}", fontsize=13, fontweight="bold", color="#1B5E20")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(file_png, dpi=110)
    plt.close(fig)
    print(f"  ✔ Markowitz: {file_png}")


def ve_hiep_phuong_sai(mk, file_png):
    """Ma trận HIỆP PHƯƠNG SAI năm (đã co Ledoit–Wolf, đơn vị %²) và ma trận TƯƠNG QUAN – đầu vào của Markowitz."""
    cov = mk["cov"] * 1e4
    tq = mk["tuong_quan"].values
    ma = mk["ma"]
    fig, ax = plt.subplots(1, 2, figsize=(7 + 1.6 * len(ma), 3 + 0.8 * len(ma)))
    for a, M, ten, cmap, vmin, vmax, dd in (
            (ax[0], cov, "Hiệp phương sai năm (%²) – đường chéo = phương sai = σ²", "OrRd", 0, cov.max(), "{:,.0f}"),
            (ax[1], tq, "Tương quan (từ hiệp phương sai)", "RdYlGn_r", -1, 1, "{:.2f}")):
        im = a.imshow(M, cmap=cmap, vmin=vmin, vmax=vmax)
        a.set_xticks(range(len(ma)))
        a.set_xticklabels(ma, rotation=45)
        a.set_yticks(range(len(ma)))
        a.set_yticklabels(ma)
        for i in range(len(ma)):
            for j in range(len(ma)):
                a.text(j, i, dd.format(M[i, j]), ha="center", va="center", fontsize=9,
                       fontweight="bold" if i == j else "normal")
        fig.colorbar(im, ax=a, fraction=0.046)
        a.set_title(ten, fontsize=10)
    fig.suptitle(f"Đầu vào Markowitz – {mk['so_tuan']} tuần lợi suất, co Ledoit–Wolf", fontsize=12, fontweight="bold", color="#1B5E20")
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(file_png, dpi=110)
    plt.close(fig)
    print(f"  ✔ Hiệp phương sai: {file_png}")
