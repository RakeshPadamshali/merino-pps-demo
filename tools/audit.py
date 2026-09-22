"""One basis: every figure that appears on more than one page must be the same number from the same plan.
Reads the KPI tiles (and a few tables) off each page and compares them with the engine result the pages read.
Usage:  python tools/audit.py [preset]        (default: the shipped live plan, Balanced)
"""
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8423
BASE = "http://localhost:%d/" % PORT
PRESET = sys.argv[1] if len(sys.argv) > 1 else None
fails = []
seen = 0

TILES = """(() => { const o = {}; document.querySelectorAll('.kpi').forEach(k => {
  const lab = k.querySelector('.k'), v = k.querySelector('.v'); if (!lab || !v) return;
  o[lab.textContent.trim().toLowerCase()] = v.textContent.trim(); }); return o; })()"""

EXPECT = """(() => { const st = MERX.settings(); const r = MERX.cachedPlan(st) || MERX.computePlan(st); const k = r.kpi, X = MERX;
  return { otif: X.pct(k.otif, 1), late: X.n(k.late), delay: X.rs(k.delayCost), sheets: X.n(k.sheets), cycles: X.n(k.cycles),
           swaps: X.n(k.swaps), cleaning: X.n(k.cleaning), util: X.pct(k.util, 1), fill: X.pct(k.fill, 1),
           contribution: X.rs(k.contribution), paperWait: X.n(k.paperWait), normBad: X.n(k.norm.BLACK + k.norm.RED),
           overdue: X.n(k.overdueAtAsOf), chgH: X.n(Math.round(k.chgMin / 60)), bandChanges: X.n(k.bandChanges),
           openLines: X.n(r.lines.filter(x => !x.norm && x.status !== 'Done' && x.status !== 'Cancelled').length),
           sets: X.n(r.m.setList.length), norms: X.n(r.m.norms.length) }; })()"""


def check(cond, name, detail=""):
    global seen
    seen += 1
    if not cond:
        fails.append(name + ((" — " + str(detail)) if detail else ""))
        print("  FAIL " + name + ((" — " + str(detail)) if detail else ""))


def num(s):
    if s is None:
        return None
    m = re.search(r"-?[\d,\.]+", str(s).replace("−", "-"))
    return float(m.group(0).replace(",", "")) if m else None


def first(s):
    """the leading value of a tile, without the trailing hint text some tiles carry"""
    return re.split(r"(?<=[%\d])\s*(?:[a-zA-Z+−-])", str(s).strip())[0].strip() if s else s


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1600, "height": 1000})

            def open_page(name):
                for i in range(25):
                    try:
                        pg.goto(BASE + name, wait_until="load")
                        break
                    except Exception:
                        time.sleep(0.4)
                if PRESET:
                    pg.evaluate("(p) => { const s = JSON.parse(localStorage.getItem('mer-demo-state') || '{}'); s.plan = { preset: p }; localStorage.setItem('mer-demo-state', JSON.stringify(s)); }", PRESET)
                    pg.reload(wait_until="load")
                pg.wait_for_function("!document.getElementById('mer-busy') && !!window.MERX", timeout=120000)
                pg.wait_for_timeout(400)

            open_page("home.html")
            E = pg.evaluate(EXPECT)
            print("live plan: OTIF %s · late %s · delay %s · sheets %s in %s cycles · swaps %s · cleaning %s · util %s · paper waits %s"
                  % (E["otif"], E["late"], E["delay"], E["sheets"], E["cycles"], E["swaps"], E["cleaning"], E["util"], E["paperWait"]))

            # ---------------- dashboard ----------------
            t = pg.evaluate(TILES)
            check(t["otif — committed lines"].startswith(E["otif"]), "dashboard OTIF", "%s vs %s" % (t["otif — committed lines"], E["otif"]))
            check(t["late in the plan"] == E["late"], "dashboard late lines", "%s vs %s" % (t["late in the plan"], E["late"]))
            check(t["delay cost"] == E["delay"], "dashboard delay cost", "%s vs %s" % (t["delay cost"], E["delay"]))
            check(t["sheets planned"] == E["sheets"], "dashboard sheets", "%s vs %s" % (t["sheets planned"], E["sheets"]))
            check(t["contribution"] == E["contribution"], "dashboard contribution")
            check(t["press utilisation"] == E["util"], "dashboard utilisation", "%s vs %s" % (t["press utilisation"], E["util"]))
            check(t["cycle fill"] == E["fill"], "dashboard cycle fill")
            check(t["mould changeovers"] == E["swaps"], "dashboard swaps", "%s vs %s" % (t["mould changeovers"], E["swaps"]))
            check(t["cleaning passes"] == E["cleaning"], "dashboard cleaning passes")
            check(t["stock norms in red or black"] == E["normBad"], "dashboard norms in red or black")
            check(t["overdue at as-of"] == E["overdue"], "dashboard overdue at as-of")

            # ---------------- order book ----------------
            open_page("orders.html")
            t = pg.evaluate(TILES)
            check(t["open lines"] == E["openLines"], "order book open lines", "%s vs %s" % (t["open lines"], E["openLines"]))
            check(t["late in plan"] == E["late"], "order book late lines", "%s vs %s" % (t["late in plan"], E["late"]))
            check(t["delay cost"] == E["delay"], "order book delay cost")
            check(t["overdue at as-of"] == E["overdue"], "order book overdue at as-of")

            # ---------------- objective studio (live column of the comparison) ----------------
            open_page("objectives.html")
            pg.wait_for_selector("#cmp tbody tr", timeout=120000)
            live = pg.evaluate("""(() => { const st = MERX.settings(); const heads = [...document.querySelectorAll('#cmp thead th')].map(h => h.textContent.trim());
              let col = heads.findIndex(h => h.endsWith('●')); if (col < 0) col = 1;
              const out = {}; document.querySelectorAll('#cmp tbody tr').forEach(tr => { if (tr.classList.contains('grp')) return;
                const cells = [...tr.children]; out[cells[0].textContent.trim().toLowerCase()] = (cells[col] ? cells[col].textContent.trim() : ''); }); return out; })()""")
            check(live["otif — committed lines due in horizon"] == E["otif"], "objective studio OTIF", "%s vs %s" % (live.get("otif — committed lines due in horizon"), E["otif"]))
            check(live["late lines"] == E["late"], "objective studio late lines")
            check(live["delay cost"] == E["delay"], "objective studio delay cost")
            check(live["sheets planned"] == E["sheets"], "objective studio sheets")
            check(live["daylight plate swaps"] == E["swaps"], "objective studio swaps")
            check(live["cleaning passes"] == E["cleaning"], "objective studio cleaning passes")
            check(live["cure-band changes"] == E["bandChanges"], "objective studio band changes")
            check(live["contribution in horizon"] == E["contribution"], "objective studio contribution")
            check(num(live["changeover time"]) == num(E["chgH"]), "objective studio changeover hours", "%s vs %s h" % (live["changeover time"], E["chgH"]))
            check(live["plate fill"] == E["fill"], "objective studio plate fill")

            # ---------------- press schedule ----------------
            open_page("schedule.html")
            t = pg.evaluate(TILES)
            check(num(t["planned cycles"]) == num(E["cycles"]), "schedule planned cycles", "%s vs %s" % (t["planned cycles"], E["cycles"]))
            check(t["sheets planned"] == E["sheets"], "schedule sheets", "%s vs %s" % (t["sheets planned"], E["sheets"]))
            check(t["press utilisation"] == E["util"], "schedule utilisation", "%s vs %s" % (t["press utilisation"], E["util"]))
            check(num(t["changeover time"]) == num(E["chgH"]), "schedule changeover hours", "%s vs %s h" % (t["changeover time"], E["chgH"]))
            check(t["cleaning passes"] == E["cleaning"], "schedule cleaning passes")
            check(t["otif (plan)"] == E["otif"], "schedule OTIF", "%s vs %s" % (t["otif (plan)"], E["otif"]))

            # ---------------- colour & changeover ----------------
            open_page("sequence.html")
            t = pg.evaluate(TILES)
            check(num(first(t["daylight plate swaps"])) == num(E["swaps"]), "sequence swaps", "%s vs %s" % (t["daylight plate swaps"], E["swaps"]))
            check(num(first(t["changeover time"])) == num(E["chgH"]), "sequence changeover hours", "%s vs %s" % (t["changeover time"], E["chgH"]))
            check(num(first(t["cure-band changes"])) == num(E["bandChanges"]), "sequence band changes")
            check(num(first(t["cleaning passes"])) == num(E["cleaning"]), "sequence cleaning passes", "%s vs %s" % (t["cleaning passes"], E["cleaning"]))

            # ---------------- mould board ----------------
            open_page("moulds.html")
            t = pg.evaluate(TILES)
            check(t["mould sets"] == E["sets"], "mould board set count", "%s vs %s" % (t["mould sets"], E["sets"]))

            # ---------------- paper & materials ----------------
            open_page("materials.html")
            t = pg.evaluate(TILES)
            check(t["lines waiting for paper"] == E["paperWait"], "materials lines waiting for paper", "%s vs %s" % (t["lines waiting for paper"], E["paperWait"]))

            # ---------------- stock norms ----------------
            open_page("norms.html")
            t = pg.evaluate(TILES)
            check(t["make-to-stock skus"] == E["norms"], "norms SKU count")
            check(t["black or red at the end"] == E["normBad"], "norms black or red at the end", "%s vs %s" % (t["black or red at the end"], E["normBad"]))
            bands = pg.evaluate("""(() => { const r = MERX.cachedPlan(MERX.settings()); const k = r.kpi.norm;
              const bars = [...document.querySelectorAll('#bands .bandbar')][1]; const shown = [...bars.children].map(d => +d.textContent);
              const sum = shown.reduce((a, b) => a + b, 0); return { sum: sum, total: r.m.norms.length, kpi: k.BLACK + k.RED + k.YELLOW + k.GREEN + k.BLUE }; })()""")
            check(bands["sum"] == bands["total"] == bands["kpi"], "norm bands add up to every make-to-stock SKU", bands)

            # ---------------- shift work orders ⊂ the plan ----------------
            open_page("workorders.html")
            wo = pg.evaluate("""(() => { const r = MERX.cachedPlan(MERX.settings()); const t = [...document.querySelectorAll('#sum tbody tr')];
              const cyc = t.reduce((a, tr) => a + (+tr.children[1].textContent.replace(/[^0-9]/g, '') || 0), 0);
              const sheets = t.reduce((a, tr) => a + (+tr.children[2].textContent.replace(/[^0-9]/g, '') || 0), 0);
              const kpiCyc = +document.querySelectorAll('.kpi .v')[0].textContent.replace(/[^0-9]/g, '');
              const kpiSh = +document.querySelectorAll('.kpi .v')[1].textContent.replace(/[^0-9]/g, '');
              return { cyc: cyc, sheets: sheets, kpiCyc: kpiCyc, kpiSh: kpiSh, planCycles: r.kpi.cycles }; })()""")
            check(wo["cyc"] == wo["kpiCyc"], "work order press rows add up to the shift's cycles", wo)
            check(wo["sheets"] == wo["kpiSh"], "work order press rows add up to the shift's sheets", wo)
            check(wo["cyc"] <= wo["planCycles"], "a shift never holds more cycles than the whole plan", wo)

            # ---------------- plan vs actual (history is independent of the live plan) ----------------
            open_page("planactual.html")
            pa = pg.evaluate("""(() => { const rows = [...document.querySelectorAll('#heat tbody tr')];
              const good = []; rows.forEach(tr => good.push(tr.children[tr.children.length - 1].textContent.trim()));
              const t = {}; document.querySelectorAll('.kpi').forEach(k => { t[k.querySelector('.k').textContent.trim().toLowerCase()] = k.querySelector('.v').textContent.trim(); });
              return { att: t['output attainment'], rows: good.length }; })()""")
            check(pa["rows"] == 6, "plan vs actual covers every press", pa)
            check(num(pa["att"]) is not None and 80 <= num(pa["att"]) <= 100, "plan vs actual attainment is a sane percentage", pa)

            b.close()
    finally:
        srv.kill()
    print("\n%d cross-page checks" % seen)
    if fails:
        print("AUDIT FAIL (%d)" % len(fails))
        sys.exit(1)
    print("AUDIT PASS — every figure on more than one page is the same number")


main()
