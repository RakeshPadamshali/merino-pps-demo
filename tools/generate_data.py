#!/usr/bin/env python3
"""Deterministic demo dataset for the Merino Laminates PPS demo.
Writes  data/mer-data.js  (window.MER, used by every page and by the engine),  data/mer-meta.js  (header stamp for the tab
host) and  data/README.md  (data dictionary). Everything is FICTIONAL except the numbers the deck confirms; every
generated parameter is in tools/gen/config.py.
Run:  python tools/generate_data.py            (as-of = today, 10:30)
      python tools/generate_data.py --asof 2026-09-22
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import config as CFG
from gen.common import ASOF, BASE, END, ASOF_MINUTE, END_MINUTE, iso
from gen.catalogue import (build_decors, build_sizes, build_thicknesses, build_skus, choose_mts, build_norms, eligible_presses, nest_factor,
                           FIN, FAMILIES, FINISHES, GRADES, health_class)
from gen.customers import build_customers, dedicated_pairs
from gen.moulds import build_mould_sets
from gen.orders import build_orders, rush_order_spec
from gen.materials import build_papers, build_other_materials, SUPPLIERS
from gen.events import build_events, build_scenarios
from gen.masters import build_masters

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JS, OUT_META, OUT_MD = (os.path.join(ROOT, "data", f) for f in ("mer-data.js", "mer-meta.js", "README.md"))

decors = build_decors()
sizes = build_sizes()
thicknesses = build_thicknesses()
skus = build_skus(decors, sizes)
mts = choose_mts(skus)
norms = build_norms(mts)
customers = build_customers()
dpairs = dedicated_pairs(customers)
sets = build_mould_sets(skus, dpairs)
orders, lines, stats, mps = build_orders(customers, skus, sizes, norms, sets)
rush = rush_order_spec(customers, skus)

# ---- mould coverage: every SKU someone wants must have a set on at least one press it may run on ----
sku_by = {s["id"]: s for s in skus}
bed_of = {p["id"]: p["bedFt"] for p in CFG.PRESSES}
demanded = {l["skuId"] for l in lines} | {n["skuId"] for n in norms} | {l["skuId"] for l in rush["lines"]}
added = 0
for sid in sorted(demanded):
    s = sku_by[sid]
    beds = sorted({bed_of[p] for p in s["presses"]})
    if not any(x["finishId"] == s["finishId"] and x["bedFt"] in beds and not x["dedicatedTo"] for x in sets):
        bed = beds[0]
        k = sum(1 for x in sets if x["finishId"] == s["finishId"] and x["bedFt"] == bed)
        sets.append(dict(id="%s-%02d-%s" % (s["finishId"], bed, "ABCDEFG"[k]), finishId=s["finishId"], bedFt=bed, plates=16, dedicatedTo=None, pressLock=None,
                         lifeLimit=CFG.MOULD_LIFE_CYCLES, counterAtBase=30, lastShadeAtBase=1, refurbUntilHours=0, family=FIN[s["finishId"]]["family"], lastRefurbDaysBeforeBase=3))
        added += 1

papers, pos, pmeta = build_papers(decors, skus, lines, norms)
materials = build_other_materials()
events = build_events(orders, lines, sets, skus)
scenarios = build_scenarios(orders, lines, sets, skus, decors, rush, pmeta)
m = build_masters(sizes, thicknesses, decors, skus, sets, customers, norms, papers, materials, SUPPLIERS)

# ---------------------------------------------------------------- integrity asserts
def uniq(name, rows, key="id"):
    ids = [r[key] for r in rows]
    dup = [k for k, n in Counter(ids).items() if n > 1]
    assert not dup, "duplicate ids in %s: %s" % (name, dup[:5])


for name, rows in (("decors", decors), ("skus", skus), ("sets", sets), ("customers", customers), ("orders", orders), ("lines", lines), ("pos", pos), ("papers", papers)):
    uniq(name, rows)
dec_by, cust_by, size_by = {d["id"]: d for d in decors}, {c["id"]: c for c in customers}, {s["id"]: s for s in sizes}
grade_ids, thk = {g["id"] for g in GRADES}, {t["mm"] for t in thicknesses}
for s in skus:
    assert s["decorId"] in dec_by and s["finishId"] in FIN and s["sizeId"] in size_by and s["gradeId"] in grade_ids and s["mm"] in thk, s["id"]
    assert s["presses"], "SKU with no eligible press: " + s["id"]
for l in lines + rush["lines"]:
    assert l["skuId"] in sku_by and l["customerId"] in cust_by, l["id"]
order_ids = {o["id"] for o in orders}
for l in lines:
    assert l["orderId"] in order_ids, l["id"]
for sid in demanded:   # runnable: some eligible press has a set of this texture sized for its bed
    s = sku_by[sid]
    assert any(x["finishId"] == s["finishId"] and x["bedFt"] == bed_of[p] and (not x["pressLock"] or x["pressLock"] == p) for p in s["presses"] for x in sets), "no mould set for " + sid
for x in sets:
    if x["pressLock"]:
        assert bed_of[x["pressLock"]] == x["bedFt"], "dedicated set on a press of another bed size: " + x["id"]
for d in pos:
    assert d["decorId"] in dec_by
assert all(k in scenarios for k in ("S1", "S2", "S3", "S4", "S5", "S6", "S7")) and scenarios["S7"]["sku"], "scenario anchors missing"
assert scenarios["S3"]["setId"] in {x["id"] for x in sets} and scenarios["S4"]["poId"] in {p["id"] for p in pos}
assert scenarios["S5"]["cancelOrderId"] in order_ids and scenarios["S5"]["downgradeLineId"] in {l["id"] for l in lines}
assert scenarios["S7"]["sku"]["id"] not in sku_by, "S7 SKU must be new"
assert 0.85 <= stats["orderMinutes"] / stats["targetMinutes"] <= 1.1, stats

# ---------------------------------------------------------------- write
meta = dict(company=CFG.PLANT["company"], site=CFG.PLANT["site"], title=CFG.PLANT["title"], asOf=iso(ASOF), base=iso(BASE), end=iso(END),
            asOfMinute=ASOF_MINUTE, endMinute=END_MINUTE, historyDays=CFG.HISTORY_DAYS, forwardDays=CFG.FORWARD_DAYS,
            generated=iso(datetime.now()), seed=CFG.SEED, fictional=True, stats=stats, mouldSetsAddedForCoverage=added)
cfg = dict(efficiency=CFG.EFFICIENCY, runHours=CFG.RUN_HOURS, downtimeMin=CFG.DOWNTIME_MIN, lifeCycles=CFG.MOULD_LIFE_CYCLES, refurbHours=CFG.REFURB_HOURS,
           healthClasses=CFG.HEALTH_CLASSES, changeover=CFG.CHANGEOVER, thicknessMix=CFG.THICKNESS_MIX, finishingDays=CFG.FINISHING_DAYS,
           delayPenalty=CFG.DELAY_PENALTY, releaseWindow=CFG.RELEASE_WINDOW_DAYS, normBands=CFG.NORM_BANDS, beds={str(k): v for k, v in CFG.BEDS.items()}, laminatesPerMould=CFG.LAMINATES_PER_MOULD,
           mouldsPerDaylight=CFG.MOULDS_PER_DAYLIGHT, pressFlags={p["id"]: dict(compact=p["compact"], gloss=p["gloss"], special=p["special"], exterior=p["exterior"],
                                                                                   downtimeStart=p["downtimeStart"]) for p in CFG.PRESSES})
data = dict(meta=meta, cfg=cfg, m=m, orders=orders, lines=lines, pos=pos, events=events, scenarios=scenarios)
os.makedirs(os.path.dirname(OUT_JS), exist_ok=True)
with open(OUT_JS, "w", encoding="utf-8") as f:
    f.write("/* GENERATED by tools/generate_data.py — do not hand-edit. As-of %s. Fictional data; see data/README.md */\n" % iso(ASOF))
    f.write("window.MER = ")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")
lab = ASOF.strftime("%a %d %b %Y %H:%M").replace(" 0", " ")
with open(OUT_META, "w", encoding="utf-8") as f:
    f.write("window.MER_META = %s;\n" % json.dumps(dict(asOf=iso(ASOF), asOfLabel=lab, shift="A", presets={w["id"]: w["label"] for w in CFG.WEIGHT_PRESETS})))

# data dictionary
def fields(rows):
    ks = []
    for r in rows[:50]:
        for k in r:
            if k not in ks:
                ks.append(k)
    return ", ".join("`%s`" % k for k in ks)


md = ["# Merino Laminates PPS demo — dataset (data dictionary)", "",
      "Generated by `tools/generate_data.py` (deterministic, seed %d). As-of **%s**; history from %s, plan to %s. "
      "All customers, orders, designs, suppliers and people are **fictional**. Numbers the Bluemingo deck confirms (13–14 daylights, 8 moulds × 2 sheets, "
      "~60 min cycle, 22 h × 90%%, 8/14/16 ft directional fit, weekly mould refurbishment, light→dark sequencing, five objectives) and the user-confirmed "
      "press fleet (3 × 8 ft, 2 × 14 ft, 1 × 16 ft) and one-texture-per-daylight rule are modelled as given; everything else is a generated value in "
      "`tools/gen/config.py`." % (CFG.SEED, iso(ASOF), iso(BASE), iso(END)), "",
      "## Volumes", "",
      "| Item | Count |", "|---|---|",
      "| Decors (designs) | %d |" % len(decors), "| Finishes (textures) | %d |" % len(FINISHES), "| Sizes | %d |" % len(sizes), "| Thicknesses | %d (%g–%g mm) |" % (len(thicknesses), CFG.THICKNESSES[0], CFG.THICKNESSES[-1]),
      "| SKUs | %d |" % len(skus), "| Stock-norm SKUs | %d |" % len(norms), "| Mould sets | %d (%d customer-dedicated) |" % (len(sets), sum(1 for x in sets if x["dedicatedTo"])),
      "| Customers | %d |" % len(customers), "| Orders / lines | %d / %d (%s sheets) |" % (len(orders), len(lines), "{:,}".format(stats["sheets"])),
      "| Paper purchase orders | %d |" % len(pos), "",
      "## Collections in `window.MER`", ""]
for name, rows in (("orders", orders), ("lines", lines), ("pos", pos)):
    md += ["### `%s` — %d records" % (name, len(rows)), "", "Fields: " + fields(rows), ""]
md += ["### `m` — masters (one key per master on the Master Data page)", ""]
for k, rows in m.items():
    md.append("- `m.%s` (%d): %s" % (k, len(rows), fields(rows)))
md += ["", "### `events` — history execution events", "", "Breakdowns, the cure-overrun and QC-downgrade rules (applied deterministically per history cycle), cancellations and a customer rejection.", "",
       "### `scenarios` — anchors for the dashboard's Scenario launcher", ""]
for k, v in scenarios.items():
    md.append("- **%s** %s" % (k, v["title"]))
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print("as-of %s | decors %d, SKUs %d, sets %d (+%d for coverage), customers %d, orders %d, lines %d, sheets %s, POs %d"
      % (iso(ASOF), len(decors), len(skus), len(sets), added, len(customers), len(orders), len(lines), "{:,}".format(stats["sheets"]), len(pos)))
print("demand press-minutes: orders %s (target %s) · norms %s · capacity/day %s · by class %s · cut-plan lines %d"
      % ("{:,}".format(stats["orderMinutes"]), "{:,}".format(stats["targetMinutes"]), "{:,}".format(stats["normMinutes"]), "{:,}".format(stats["capacityPerDay"]), stats["byClass"], stats["cutLines"]))
print("wrote %s (%d KB), %s, %s" % (OUT_JS, os.path.getsize(OUT_JS) // 1024, OUT_META, OUT_MD))
