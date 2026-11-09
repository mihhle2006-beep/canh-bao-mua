import json, re, urllib.request as u, urllib.parse as up
def lay(url, body=None, t=60):
    r = u.Request(url, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
    with u.urlopen(r, timeout=t) as x:
        return x.status, x.read()
def thu(ten, f):
    try: f()
    except Exception as e: print(ten, "LOI", str(e)[:150])
# 1. wayback
def wb():
    for q in ("api.fmarket.vn/res/products/*", "fmarket.vn/quy/*", "api.fmarket.vn/res/product*"):
        s, b = lay("https://web.archive.org/cdx/search/cdx?" + up.urlencode({"url": q, "output": "json", "limit": 400, "filter": "statuscode:200", "fl": "timestamp,original"}), t=150)
        j = json.loads(b or b"[]"); print("WB", q, len(j) - 1 if j else 0); [print("  ", r) for r in j[1:25]]
thu("wb", wb)
# 2. js fmarket
def js():
    seen, ep = set(), set()
    s, h = lay("https://fmarket.vn/quy/VESAF"); h = h.decode("utf-8", "ignore")
    nd = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    print("NEXT_DATA", len(nd.group(1)) if nd else None, (nd.group(1)[:600] if nd else ""))
    src = set(re.findall(r'(?:src|href)="([^"]+\.js)"', h))
    bm = [x for x in src if "buildManifest" in x]
    for b in bm:
        s, t = lay("https://fmarket.vn" + b if b.startswith("/") else b); src |= {"/_next/" + x for x in re.findall(r'"(static/chunks/[^"]+\.js)"', t.decode())}
    print("so js", len(src))
    for x in sorted(src):
        url = x if x.startswith("http") else "https://fmarket.vn" + x
        try: s, t = lay(url); t = t.decode("utf-8", "ignore")
        except Exception: continue
        for m in re.findall(r'["\'`]([^"\'`\s]{0,40}(?:holding|Holding|history|History|report|Report|nav|portfolio|Portfolio)[^"\'`\s]{0,60})["\'`]', t):
            if "/" in m or "-" in m: ep.add(m)
        for m in re.findall(r'["\'`](/?(?:res|api|home|product|products)/[A-Za-z0-9_\-/{}$.]+)', t): ep.add(m)
    print("EP\n" + "\n".join(sorted(ep)[:300]))
thu("js", js)
# 3. doan endpoint
for p in ["products/23/top-holding", "product/top-holding-history?productId=23", "product/23/holding-history", "products/23/holding?month=2026-06",
          "product/get-holding-history", "product/holding-history", "products/23/nav-report", "product/get-asset-holding-history", "products/top-holding?productId=23&reportTime=2026-06"]:
    for body in (None, {"productId": 23}):
        try: s, b = lay("https://api.fmarket.vn/res/" + p, body, 30); print("DOAN", p, "POST" if body else "GET", s, b[:200])
        except Exception as e: print("DOAN", p, "POST" if body else "GET", str(e)[:60])
# 4. tai lieu khac
for url in ["https://vietfin.readthedocs.io/en/stable/reference/funds/holdings.html", "https://chipheo00.github.io/wealth-vn/docs/development/vn-market/vn-market-api-specs"]:
    try:
        s, b = lay(url); t = re.sub(r"<[^>]+>", " ", b.decode("utf-8", "ignore"))
        for m in sorted(set(re.findall(r"https?://[A-Za-z0-9.\-]*(?:fmarket|fund|quy)[^\s\"'<>]*", t)))[:40]: print("TL", url[:30], m)
        i = t.find("holding"); print("TLX", url[:30], re.sub(r"\s+", " ", t[max(0, i - 300): i + 1500]))
    except Exception as e: print("TL LOI", url, e)
