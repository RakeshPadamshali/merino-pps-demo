"""Execution events recorded during the 14-day history (they turn the plan into 'actuals'), shift crews, and the seven
scenario anchors the dashboard's Scenario launcher uses. Overruns and QC downgrades are RULES the engine applies
deterministically per history cycle (seeded by cycle id), so actuals never depend on the order pages are opened in."""
from datetime import timedelta

from .common import R, ASOF, at, iso, rint

CREW = {"A": ["R. Yadav", "S. Kumar"], "B": ["M. Qureshi", "P. Rawat"], "C": ["D. Chauhan", "V. Negi"]}


def build_events(orders, lines, sets, skus):
    ev = dict(
        breakdowns=[
            dict(id="BD-01", pressId="P2", start=iso(at(-6, 13, 40)), durMin=300, category="Mechanical", reason="Main ram hydraulic seal leak"),
            dict(id="BD-02", pressId="P5", start=iso(at(-2, 3, 10)), durMin=150, category="Utility", reason="Thermal-oil circulation pump trip"),
            dict(id="BD-03", pressId="P6", start=iso(at(-9, 21, 20)), durMin=95, category="Process", reason="Platen temperature deviation, zone 4"),
        ],
        overrunRule=dict(share=0.04, minMin=6, maxMin=18, reason="Cure extended — platen temperature lag"),
        qcRule=dict(share=0.03, minShare=0.15, maxShare=0.6, defects=["Gloss streak", "Dry spot", "Pressure mark", "Colour variation", "Surface scratch"]),
        cancellations=[], rejections=[],
    )
    early_dom = [o for o in orders if o["cls"] == "DOM_COMMITTED" and o["segment"] == "DEALER" and o["orderDate"] < iso(at(-12))]
    for o in early_dom[:2]:
        ln = o["lines"][-1]
        ev["cancellations"].append(dict(lineId=ln, at=iso(at(-rint(4, 9), rint(10, 17))), reason="Dealer cancelled — project on hold"))
    exp = [o for o in orders if o["cls"] == "EXPORT" and o["orderDate"] < iso(at(-18))]
    if exp:
        ln = next(l for l in lines if l["id"] == exp[0]["lines"][0])
        ev["rejections"].append(dict(lineId=ln["id"], at=iso(at(-3, 11, 20)), sheets=min(120, ln["qty"]), reason="Customer claim: gloss variation across the pallet — replacement agreed"))
    return ev


def build_scenarios(orders, lines, sets, skus, decors, rush, papers_meta):
    sku = {s["id"]: s for s in skus}
    # S3: a busy twin-set texture on an 8 ft gloss press
    s3 = next((s for s in sets if s["id"] == "HG-08-A"), None) or next(s for s in sets if s["bedFt"] == 8 and not s["dedicatedTo"])
    # S5: a recent OEM order still untouched (cancel) + an early export line (downgrade part of what was produced)
    recent_oem = sorted([o for o in orders if o["segment"] == "OEM" and o["cls"] == "DOM_COMMITTED" and o["orderDate"] > iso(at(-2))], key=lambda o: o["orderDate"])
    cancel = recent_oem[0] if recent_oem else next(o for o in reversed(orders) if o["cls"] == "DOM_COMMITTED")
    early_exp = sorted([o for o in orders if o["cls"] == "EXPORT"], key=lambda o: o["orderDate"])[0]
    # S7: a new SKU the catalogue does not have yet — an existing decor in a finish / size it was never sold in
    have = set(skus_id for skus_id in sku)
    d = next(x for x in decors if x["family"] == "SOLID" and x["shade"] <= 4)
    new_sku = None
    for fin in ("VL", "SF", "PR"):
        for size in ("S104", "S124"):
            sid = "%s-%s-1-%s-GP" % (d["id"], fin, size[1:])
            if sid not in have:
                new_sku = dict(id=sid, decorId=d["id"], finishId=fin, mm=1.0, sizeId=size, gradeId="GP", sides="S")
                break
        if new_sku:
            break
    return dict(
        S1=dict(title="Rush export container", order=rush),
        S2=dict(title="Merino today vs weighted objectives", presets=["today", "balanced"]),
        S3=dict(title="Mould set taken off early for refurbishment", setId=s3["id"], hours=48),
        S4=dict(title="China paper PO slips 12 days", poId=papers_meta["s4Po"], decorId=papers_meta["s4Decor"], days=12),
        S5=dict(title="Cancellation + QC downgrade (stateless BTP)", cancelOrderId=cancel["id"], downgradeLineId=early_exp["lines"][0], downgradeSheets=180),
        S6=dict(title="Print-mark complaint → recall scope", pressId="P4", dayOffset=-5, family="GLS"),
        S7=dict(title="New SKU onboarded from Excel", sku=new_sku),
    )
