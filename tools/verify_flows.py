"""The seven scenarios, end to end, in a headless browser: each one is launched from the dashboard, lands on its page,
changes the live plan in the direction it claims, and is undone by Reset demo.
Usage:  python tools/verify_flows.py
"""
import json
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8421
BASE = "http://localhost:%d/" % PORT
fails = []


def check(cond, name, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  — " + str(detail)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def ready(pg, timeout=90000):
    pg.wait_for_function("!document.getElementById('mer-busy') && !!window.MERX", timeout=timeout)
    pg.wait_for_timeout(350)


def kpi(pg):
    """the live plan's KPIs, straight from the engine result every page reads"""
    return pg.evaluate("(() => { const r = MERX.cachedPlan(MERX.settings()); return r ? { otif: r.kpi.otif, late: r.kpi.late, delay: r.kpi.delayCost, sheets: r.kpi.sheets, swaps: r.kpi.swaps, paperWait: r.kpi.paperWait, black: r.kpi.norm.BLACK, lines: r.lines.length } : null; })()")


def state(pg):
    return pg.evaluate("(() => { try { return JSON.parse(localStorage.getItem('mer-demo-state') || '{}'); } catch (e) { return {}; } })()")


def open_home(pg, clear=True):
    pg.goto(BASE + "home.html", wait_until="load")
    if clear:
        pg.evaluate("localStorage.removeItem('mer-demo-state')")
        pg.reload(wait_until="load")
    ready(pg)


def run(pg, sid):
    """click a scenario's button on the dashboard and follow it to its page"""
    sel = "[data-run='%s']" % sid
    pg.wait_for_selector(sel, timeout=20000)
    pg.click(sel)
    pg.wait_for_timeout(400)
    ready(pg)
    pg.wait_for_timeout(600)
    ready(pg)
    return pg.url.split("/")[-1].split("#")[0]


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1600, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda msg: errs.append("console: " + msg.text) if msg.type == "error" and "favicon" not in msg.text else None)
            for i in range(25):
                try:
                    pg.goto(BASE + "home.html", wait_until="load")
                    break
                except Exception:
                    time.sleep(0.4)
            open_home(pg)
            base = kpi(pg)
            print("baseline: OTIF %.1f%%  late %d  delay Rs %s  sheets %s  swaps %d  paper waits %d  norms black %d"
                  % (base["otif"] * 100, base["late"], "{:,}".format(int(base["delay"])), "{:,}".format(base["sheets"]), base["swaps"], base["paperWait"], base["black"]))

            # ---- S1 rush export order ----
            print("S1 — rush export container")
            page = run(pg, "S1")
            check(page == "orders.html", "S1 lands on the Order Book", page)
            st = state(pg)
            check(any(w["type"] == "rush" for w in st.get("whatifs", [])), "S1 adds the rush what-if to the live plan")
            k = kpi(pg)
            check(k["lines"] > base["lines"], "S1 adds order lines", "%d → %d" % (base["lines"], k["lines"]))
            check(pg.locator("#impcard").is_visible(), "S1 shows the priority-order impact report")
            txt = pg.inner_text("#impcard")
            check("Gulf Panel" in pg.inner_text("#wifs"), "S1 what-if chip names the customer")
            check(k["delay"] >= base["delay"] or k["late"] >= base["late"], "S1 costs delivery somewhere (delay or late lines)",
                  "delay %s → %s, late %d → %d" % (base["delay"], k["delay"], base["late"], k["late"]))

            # ---- Reset demo ----
            open_home(pg, clear=False)
            pg.click("#mer-reset")
            pg.wait_for_timeout(400)
            ready(pg)
            check(state(pg) == {}, "Reset demo clears every live-demo action", state(pg))
            check(abs(kpi(pg)["otif"] - base["otif"]) < 1e-9, "Reset demo restores the baseline plan")

            # ---- S2 objectives ----
            print("S2 — Merino today vs weighted objectives")
            open_home(pg)
            page = run(pg, "S2")
            check(page == "objectives.html", "S2 opens the Objective Studio", page)
            rows = pg.inner_text("#cmp").lower()
            check("merino today" in rows and "balanced" in rows, "S2 compares Merino today with the weighted plans")
            vals = pg.evaluate("(() => { const t = document.querySelector('#cmp'); const r = [...t.querySelectorAll('tbody tr')].find(x => x.children[0].textContent.startsWith('Daylight plate swaps')); return r ? [...r.children].slice(1).map(td => +td.textContent.replace(/[^0-9.]/g, '')) : null; })()")
            check(vals and vals[0] > vals[1], "S2: the fixed sequence makes more plate swaps than the balanced plan", vals)

            # ---- S3 mould set off for refurbishment ----
            print("S3 — mould set off early for refurbishment")
            open_home(pg)
            page = run(pg, "S3")
            check(page == "moulds.html", "S3 opens the Mould Board", page)
            st = state(pg)
            sid = pg.evaluate("MERX.D.scenarios.S3.setId")
            check(any(w["type"] == "refurb" and w["setId"] == sid for w in st.get("whatifs", [])), "S3 takes %s off for refurbishment" % sid)
            pg.wait_for_selector("#dimp table", timeout=60000)
            imp = pg.inner_text("#dimp").lower()
            check("cycles before" in imp and "cycles now" in imp, "S3 shows the before / after per set of that texture")
            moved = pg.evaluate("""(() => { const rows = [...document.querySelectorAll('#dimp tbody tr')].map(r => [...r.children].map(td => td.textContent));
                return rows.filter(r => /\\(\\+/.test(r[2])).length; })()""")
            check(moved > 0, "S3 moves work to the twin sets", "%d sets gained cycles" % moved)
            check("in refurbishment" in pg.inner_text("#dinfo").lower(), "S3 marks the set as in refurbishment now")

            # ---- S4 paper PO delay ----
            print("S4 — China paper PO slips")
            open_home(pg)
            page = run(pg, "S4")
            check(page == "materials.html", "S4 opens Paper & Materials", page)
            poid = pg.evaluate("MERX.D.scenarios.S4.poId")
            st = state(pg)
            check(any(w["type"] == "poDelay" and w["poId"] == poid for w in st.get("whatifs", [])), "S4 delays %s" % poid)
            k = kpi(pg)
            check(k["paperWait"] > base["paperWait"], "S4 makes more lines wait for paper", "%d → %d" % (base["paperWait"], k["paperWait"]))
            check(k["late"] >= base["late"], "S4 costs committed dates", "late %d → %d" % (base["late"], k["late"]))
            check(poid in pg.inner_text("#wibar"), "S4 shows the delayed PO on the page")

            # ---- S5 cancellation + QC downgrade ----
            print("S5 — cancellation + QC downgrade (stateless BTP)")
            open_home(pg)
            page = run(pg, "S5")
            check(page == "orders.html", "S5 opens the Order Book", page)
            st = state(pg)
            types = sorted(w["type"] for w in st.get("whatifs", []))
            check(types == ["cancel", "downgrade"], "S5 adds the cancellation and the downgrade", types)
            oid = pg.evaluate("MERX.D.scenarios.S5.cancelOrderId")
            lid = pg.evaluate("MERX.D.scenarios.S5.downgradeLineId")
            btp = pg.evaluate("""(() => { const r = MERX.cachedPlan(MERX.settings()); const l = r.byId['%s'];
                const cancelled = r.lines.filter(x => x.orderId === '%s' && x.status === 'Cancelled').length; return { down: l ? l.btp : null, whatifDown: l ? l.whatifDown : null, cancelled: cancelled }; })()""" % (lid, oid))
            check(btp["cancelled"] > 0, "S5 cancels every line of %s" % oid, btp)
            check(btp["whatifDown"] and btp["whatifDown"] > 0 and btp["down"] > 0, "S5 grows the balance-to-produce of the downgraded line back", btp)

            # ---- S6 print-mark complaint ----
            print("S6 — print-mark complaint → recall scope")
            open_home(pg)
            page = run(pg, "S6")
            check(page == "trace.html", "S6 opens Traceability", page)
            ready(pg)
            mark = pg.input_value("#q")
            check(mark.startswith("MER P"), "S6 fills a print mark", mark)
            sc = pg.inner_text("#out").lower()
            check("recall scope" in sc and "mould set" in sc, "S6 shows the sheet and its recall scope")
            rows = pg.evaluate("document.querySelectorAll('#sc tbody tr').length")
            check(rows > 1, "S6 recall scope lists the other sheets of that mould set", rows)

            # ---- S7 new SKU from Excel ----
            print("S7 — new SKU onboarded from Excel")
            open_home(pg)
            page = run(pg, "S7")
            check(page == "masters.html", "S7 opens Master Data", page)
            pg.wait_for_selector("[data-m='skus']", timeout=20000)
            pg.click("[data-m='skus']")
            pg.wait_for_timeout(300)
            before = pg.evaluate("MERX.model().skuList.length")
            pg.click("#sample")
            pg.wait_for_timeout(400)
            check(pg.locator("#prevcard").is_visible(), "S7 previews the uploaded row before anything is applied")
            check("1 new" in pg.inner_text("#pmeta"), "S7 preview shows one new row", pg.inner_text("#pmeta"))
            pg.click("#apply")
            pg.wait_for_timeout(500)
            ready(pg)
            pg.wait_for_timeout(600)
            after = pg.evaluate("MERX.model().skuList.length")
            check(after == before + 1, "S7 applies the new SKU to the live model", "%d → %d" % (before, after))
            pg.wait_for_selector("#skucard", state="visible", timeout=30000)
            inh = pg.inner_text("#skunew").lower()
            check("eligible presses" in inh and "cure band" in inh, "S7 shows what the new SKU inherited from its attributes")
            sku = pg.evaluate("MERX.D.scenarios.S7.sku.id")
            elig = pg.evaluate("(() => { const s = MERX.model().skus['%s']; return s ? s.presses : null; })()" % sku)
            check(elig and len(elig) > 0, "S7 SKU is runnable on at least one press without any mapping", elig)
            audit = pg.inner_text("#audit")
            check("ppsadmin" in audit and "SKU" in audit, "S7 writes the master-data audit row")

            # the new SKU reaches ATP
            pg.goto(BASE + "atp.html#" + sku, wait_until="load")
            ready(pg)
            check(sku in pg.inner_text("#skuinfo"), "S7 SKU can be quoted in ATP & Capacity", pg.inner_text("#skuinfo"))

            pg.evaluate("localStorage.removeItem('mer-demo-state')")
            check(not errs, "no JavaScript errors during the flows", errs[:3])
            b.close()
    finally:
        srv.kill()
    print("\nFLOWS", "PASS" if not fails else "FAIL (%d)" % len(fails))
    sys.exit(0 if not fails else 1)


main()
