"""Materials (req 5a): decor paper by design code — mostly imported from China with a long lead time, the rest domestic —
plus overlay, kraft and resins. Stock is sized from each decor's expected consumption so most designs are covered, a set of
designs runs short inside the horizon (their lines wait for the next receipt), and one popular woodgrain is the anchor for
Scenario 4 (its China PO slips 12 days). Suppliers are FICTIONAL."""
from datetime import timedelta

from .common import R, ASOF, BASE, at, iso, rint, between
from .config import HISTORY_DAYS, FORWARD_DAYS

SUPPLIERS = [
    dict(id="SUP-CN1", name="Zhejiang DecoPrint Co.", country="China", kind="Decor paper", leadDays=58, transit="Sea, Ningbo → Mundra"),
    dict(id="SUP-CN2", name="Guangdong Surface Papers Ltd", country="China", kind="Decor paper", leadDays=64, transit="Sea, Shekou → Nhava Sheva"),
    dict(id="SUP-CN3", name="Shandong Overlay Mills", country="China", kind="Overlay + decor paper", leadDays=52, transit="Sea, Qingdao → Mundra"),
    dict(id="SUP-IN1", name="Vapi Decor Papers Pvt Ltd", country="India", kind="Decor paper", leadDays=18, transit="Road"),
    dict(id="SUP-IN2", name="Kraftline Mills India", country="India", kind="Kraft paper", leadDays=12, transit="Road"),
    dict(id="SUP-IN3", name="Resichem Industries", country="India", kind="Phenolic + melamine resin", leadDays=7, transit="Tanker"),
]


def build_papers(decors, skus, lines, norms):
    """one decor paper per design; stock in sheet-equivalents (one decor sheet per laminate face)"""
    sku = {s["id"]: s for s in skus}
    faces = {s["id"]: (2 if s["sides"] == "D" else 1) for s in skus}
    use = {}
    for l in lines:
        s = sku[l["skuId"]]
        use[s["decorId"]] = use.get(s["decorId"], 0) + l["qty"] * faces[s["id"]]
    for n in norms:
        d = sku[n["skuId"]]["decorId"]
        use[d] = use.get(d, 0) + n["usePerDay"] * (HISTORY_DAYS + FORWARD_DAYS)
    span = 24 + FORWARD_DAYS
    papers, pos = [], []
    ranked = sorted([d for d in decors if use.get(d["id"])], key=lambda d: -use[d["id"]])
    s4 = next(d for d in ranked if d["family"] == "WOOD" and d["paperSource"] == "IMPORT")
    # a dozen designs genuinely run short inside the horizon (their lines wait for the next receipt); the rest are covered
    short = set(d["id"] for d in ranked[8:160] if d["id"] != s4["id"] and R.random() < 0.085)
    po_n = 0
    for d in decors:
        total = use.get(d["id"], 0)            # every open line + everything history makes + norm use over both windows
        daily = total / span
        imported = d["paperSource"] == "IMPORT"
        sup = R.choice(["SUP-CN1", "SUP-CN2", "SUP-CN3"]) if imported else "SUP-IN1"
        lead = next(s["leadDays"] for s in SUPPLIERS if s["id"] == sup)
        if d["id"] == s4["id"]:
            stock = total * 0.42                  # runs out around the as-of day; the next receipt lands at +3 days
        elif d["id"] in short:
            stock = total * between(0.35, 0.6)    # runs out inside the horizon
        else:
            stock = total * between(1.05, 1.45)   # covered through the horizon
        stock = int(round(stock / 10.0) * 10) if total else rint(40, 400)
        papers.append(dict(id=d["paperId"], decorId=d["id"], supplierId=sup, leadDays=lead, source=d["paperSource"], stockAtBase=max(stock, 0),
                           reorderSheets=int(round(max(daily * 30, 300) / 50.0) * 50), gsm=80 if imported else 70))
        if total:
            if d["id"] == s4["id"]:
                etas, qty = [3], total
            elif d["id"] in short:
                etas, qty = [rint(4, 13)], total
            else:
                etas, qty = [rint(-10, 30)] + ([rint(31, 40)] if R.random() < 0.3 else []), max(daily * rint(25, 45), 400)
            for e in etas:
                po_n += 1
                eta = at(e, rint(8, 17))
                pos.append(dict(id="PO-%s-%04d" % ("CN" if imported else "IN", po_n), paperId=d["paperId"], decorId=d["id"], supplierId=sup,
                                sheets=int(round(qty / 50.0) * 50), eta=iso(eta), placed=iso(eta - timedelta(days=lead)),
                                status="RECEIVED" if eta < ASOF else "IN TRANSIT" if imported else "CONFIRMED"))
    return papers, pos, dict(s4Decor=s4["id"], s4Po=next(p["id"] for p in pos if p["decorId"] == s4["id"]), shortDecors=len(short))


def build_other_materials():
    """overlay, kraft, resins, release paper, print-mark ink — shown with cover; not a planning constraint in the demo"""
    rows = [
        ("MAT-OV25", "Overlay paper 25 gsm (standard)", "Overlay", "SUP-CN3", "sheets", 185000, 5200),
        ("MAT-OV45", "Overlay paper 45 gsm (high abrasion)", "Overlay", "SUP-CN3", "sheets", 42000, 900),
        ("MAT-KR80", "Kraft 80 gsm", "Kraft", "SUP-IN2", "kg", 96000, 6400),
        ("MAT-KR135", "Kraft 135 gsm", "Kraft", "SUP-IN2", "kg", 128000, 8800),
        ("MAT-KR190", "Kraft 190 gsm (compact core)", "Kraft", "SUP-IN2", "kg", 54000, 2100),
        ("MAT-PHR", "Phenolic resin (kraft impregnation)", "Resin", "SUP-IN3", "kg", 61000, 4300),
        ("MAT-MMR", "Melamine resin (decor + overlay)", "Resin", "SUP-IN3", "kg", 38000, 2600),
        ("MAT-REL", "Release paper", "Consumable", "SUP-IN2", "sheets", 60000, 3900),
        ("MAT-INK", "Print-mark ink", "Consumable", "SUP-IN1", "L", 180, 9),
    ]
    return [dict(id=i, name=n, kind=k, supplierId=s, uom=u, stock=st, usePerDay=up, coverDays=round(st / up, 1)) for i, n, k, s, u, st, up in rows]
