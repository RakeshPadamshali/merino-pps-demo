"""Headless smoke test for the Merino PPS pages: zero JS errors, no missing assets, no request leaves the site (offline
by design), content rendered, screenshot per page, and the tab host opening every module.
Usage: python tools/verify.py [page.html ...]      (default: every page + index.html)"""
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("MER_SHOTS", os.path.join(ROOT, "..", "merino-shots"))
os.makedirs(OUT, exist_ok=True)
PORT = 8420
ALL = ["home.html", "orders.html", "objectives.html", "atp.html", "loadbuilder.html", "schedule.html", "workorders.html", "moulds.html",
       "sequence.html", "materials.html", "norms.html", "planactual.html", "trace.html", "masters.html", "index.html"]
PAGES = sys.argv[1:] or ALL
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    ok_all = True
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        for page in PAGES:
            if not os.path.exists(os.path.join(ROOT, page)):
                print("SKIP " + page + " (missing)")
                continue
            pg = b.new_page(viewport={"width": 1600, "height": 1000})
            errs, bad, offsite = [], [], []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda msg: errs.append("console: " + msg.text) if msg.type == "error" and "favicon" not in msg.text else None)
            pg.on("response", lambda r: bad.append("%d %s" % (r.status, r.url)) if r.status >= 400 and "favicon" not in r.url else None)
            pg.on("request", lambda r: offsite.append(r.url) if urlparse(r.url).hostname not in ("localhost", "127.0.0.1", None) and not r.url.startswith(("data:", "blob:")) else None)
            for i in range(25):
                try:
                    pg.goto("http://localhost:%d/%s?v=%d" % (PORT, page, int(time.time())), wait_until="load")
                    break
                except Exception:
                    time.sleep(0.4)
            t0 = time.time()
            try:
                pg.wait_for_function("!document.getElementById('mer-busy')", timeout=60000)
            except Exception:
                errs.append("still busy after 60 s")
            pg.wait_for_timeout(700)
            if page == "index.html":
                for pid in ["home", "orders", "objectives", "atp", "loadbuilder", "schedule", "workorders", "moulds", "sequence", "materials", "norms", "planactual", "trace", "masters"]:
                    if pg.query_selector("[data-page=%s]" % pid) and os.path.exists(os.path.join(ROOT, pid + ".html")):
                        pg.click("[data-page=%s]" % pid)
                        pg.wait_for_timeout(900)
                pg.click("[data-page=home]")
                pg.wait_for_timeout(500)
            txt = pg.evaluate("document.body.innerText") or ""
            ok = not errs and not bad and not offsite and len(txt) > 200
            ok_all = ok_all and ok
            print(("PASS " if ok else "FAIL ") + page + "  text=%d  ready=%.1fs" % (len(txt), time.time() - t0)
                  + ("  errors=%s" % errs[:3] if errs else "") + ("  bad=%s" % bad[:3] if bad else "") + ("  offsite=%s" % offsite[:2] if offsite else ""))
            pg.screenshot(path=os.path.join(OUT, page.replace(".html", "") + ".png"), full_page=True)
            pg.close()
        b.close()
    print("VERIFY", "PASS" if ok_all else "FAIL", "| shots in", os.path.abspath(OUT))
    sys.exit(0 if ok_all else 1)
finally:
    srv.kill()
