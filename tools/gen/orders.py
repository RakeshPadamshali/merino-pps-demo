"""Sales orders and lines (FICTIONAL), sized against press capacity so the plan is tight and the five objectives trade off.
Classes: EXPORT (higher margin, vessel cut-off date), DOM_COMMITTED (confirmed delivery date), DOM_OPEN (no committed date).
Stock-norm replenishment is not an order — the engine derives it from the norms. Some OEM lines carry custom cut-piece
plans (req 2c): the sheet quantity is what the cut plan needs after nesting the pieces into the sheet."""
import math
from datetime import timedelta

from .common import R, ASOF, BASE, at, iso, rint, wpick, between
from .config import (PRESSES, CURE_BANDS, EFFICIENCY, RUN_HOURS, HISTORY_DAYS, FORWARD_DAYS, DEMAND_FACTOR, HISTORY_LOAD,
                     CLASS_MIX, MARGIN)
from .catalogue import nest_factor

PACK = 0.78                      # share of running press-minutes that turn into good sheets (fill, changeovers, cleaning) — calibrated on the engine
BANDS = {b["id"]: b for b in CURE_BANDS}
PRESS = {p["id"]: p for p in PRESSES}


def eff_cycle_min(band_id):
    return int(math.ceil(BANDS[band_id]["pressMin"] / EFFICIENCY))


def sheets_per_cycle(sku, press, size):
    lam = 2 if sku["sides"] == "S" else 1
    return press["daylights"] * BANDS[sku["bandId"]]["platesPerDaylight"] * lam * nest_factor(size, press["bedFt"])


def minutes_per_sheet(sku, sizes_by_id):
    size = sizes_by_id[sku["sizeId"]]
    vals = [eff_cycle_min(sku["bandId"]) / sheets_per_cycle(sku, PRESS[p], size) for p in sku["presses"]]
    return sum(vals) / len(vals)


def day_minutes():
    return len(PRESSES) * RUN_HOURS * 60


CUT_PIECES = [   # (name, w mm, h mm) kitchen / wardrobe shutters and panels — pieces are nested into the sheet
    ("Base shutter", 720, 450), ("Wall shutter", 720, 300), ("Tall shutter", 2100, 450), ("Drawer front", 180, 600),
    ("Side panel", 2100, 580), ("Shelf", 800, 560), ("Filler strip", 2100, 100), ("Wardrobe door", 1800, 600),
]


def shelf_pack(sheet_l, sheet_w, pieces, kerf=4):
    """simple guillotine shelf packing: how many of each piece fit one sheet in the given mix (returns count per piece)"""
    placed = {p[0]: 0 for p in pieces}
    y = 0
    order = sorted(pieces, key=lambda p: -p[2])
    while True:
        progressed = False
        for name, w, h in order:
            ph, pw = min(w, h), max(w, h)           # lay the long edge along the sheet length
            if y + ph > sheet_w:
                continue
            n = int((sheet_l + kerf) // (pw + kerf))
            if n <= 0:
                continue
            placed[name] += n
            y += ph + kerf
            progressed = True
            if y >= sheet_w:
                break
        if not progressed or y >= sheet_w:
            break
    return placed


def build_orders(customers, skus, sizes, norms, dedicated_sets):
    sizes_by_id = {s["id"]: s for s in sizes}
    mps = {s["id"]: minutes_per_sheet(s, sizes_by_id) for s in skus}
    cap_day = day_minutes() * PACK
    norm_min = sum(n["usePerDay"] * mps[n["skuId"]] for n in norms) * (HISTORY_DAYS + FORWARD_DAYS)
    target = HISTORY_LOAD * HISTORY_DAYS * cap_day + DEMAND_FACTOR * FORWARD_DAYS * cap_day - norm_min
    by_seg = {}
    for c in customers:
        by_seg.setdefault(c["segment"], []).append(c)
    ded = {}
    for s in dedicated_sets:
        if s["dedicatedTo"]:
            ded.setdefault(s["dedicatedTo"], []).append(s)
    press_bed = {p["id"]: p["bedFt"] for p in PRESSES}

    def pool(pred):
        items = [s for s in skus if pred(s)]
        return items, [s["popularity"] for s in items]

    POOLS = {
        "EXPORT": pool(lambda s: s["gradeId"] in ("GP", "EX", "CP") and (s["mm"] <= 1.5 or s["gradeId"] == "EX")),
        "OEM": pool(lambda s: s["gradeId"] in ("GP", "PF", "AB") and s["mm"] <= 1.5),
        "DEALER": pool(lambda s: s["gradeId"] in ("GP", "PF") and s["mm"] <= 1.5),
    }
    for g in ("FR", "CR", "AB", "EX", "CP", "GP"):
        POOLS["PROJECT_" + g] = pool(lambda s, g=g: s["gradeId"] == g)

    def choose(items_w, n, avoid):
        items, w = items_w
        out = []
        guard = 0
        while len(out) < n and guard < n * 40:
            guard += 1
            s = R.choices(items, weights=w, k=1)[0]
            if s["id"] in avoid or s["id"] in [x["id"] for x in out]:
                continue
            out.append(s)
        return out

    orders, lines = [], []
    vol = {k: 0.0 for k in CLASS_MIX}
    seq = {"EX": 0, "SO": 0}
    total = 0.0
    horizon_days = 24.0
    ncut = 0
    while total < target:
        # pick the class furthest below its volume share
        tot = sum(vol.values()) or 1
        cls = min(CLASS_MIX, key=lambda k: vol[k] / tot - CLASS_MIX[k])
        if cls == "EXPORT":
            cust = R.choice(by_seg["EXPORT"])
        elif cls == "DOM_OPEN":
            cust = R.choice(by_seg["DEALER"])
        else:
            cust = R.choice(by_seg[wpick({"OEM": 40, "DEALER": 42, "PROJECT": 18})])
        seg = cust["segment"]
        odate = at(-horizon_days * R.random() ** 0.92, rint(9, 18), rint(0, 59))
        if odate > ASOF - timedelta(minutes=30):
            odate = ASOF - timedelta(hours=rint(1, 20))
        if seg == "EXPORT":
            nl, qlo, qhi, step = rint(6, 13), 120, 560, 10
            due = odate + timedelta(days=rint(20, 36))
        elif seg == "OEM":
            nl, qlo, qhi, step = rint(3, 7), 250, 1300, 50
            due = odate + timedelta(days=rint(11, 22))
        elif seg == "PROJECT":
            nl, qlo, qhi, step = rint(2, 5), 120, 700, 10
            due = odate + timedelta(days=rint(14, 28))
        else:
            nl, qlo, qhi, step = rint(6, 16), 20, 200, 10
            due = odate + timedelta(days=rint(8, 17))
        if cls == "DOM_OPEN":
            due = odate + timedelta(days=rint(24, 40))       # requested, not committed
        due = due.replace(hour=18, minute=0)
        # SKUs for this order
        if seg == "PROJECT":
            gs = cust["grades"].split()
            chosen = []
            for _ in range(nl):
                chosen += choose(POOLS["PROJECT_" + R.choice(gs)], 1, [x["id"] for x in chosen])
        else:
            chosen = choose(POOLS[seg], nl, [])
            if cust["id"] in ded and R.random() < 0.85:          # dedicated customers order their locked textures
                for ds in ded[cust["id"]]:
                    dp = [s for s in skus if s["finishId"] == ds["finishId"] and ds["pressLock"] in s["presses"] and s["gradeId"] in ("GP", "PF", "EX")]
                    if dp:
                        k = max(1, len(chosen) // 2)
                        chosen = choose((dp, [s["popularity"] for s in dp]), k, []) + chosen[:max(0, len(chosen) - k)]
        if not chosen:
            continue
        pfx = "EX" if cls == "EXPORT" else "SO"
        seq[pfx] += 1
        oid = "%s%s-%04d" % (pfx, ASOF.strftime("%y"), seq[pfx])
        o = dict(id=oid, customerId=cust["id"], cls=cls, segment=seg, orderDate=iso(odate), due=iso(due), customerPo="PO/%s/%d" % (cust["id"], rint(1000, 9999)),
                 lines=[])
        if cls == "EXPORT":
            o.update(incoterm=R.choice(["FOB Mundra", "FOB Nhava Sheva", "CIF"]), note="Vessel cut-off " + (due - timedelta(days=2)).strftime("%d %b"))
        for i, s in enumerate(chosen):
            compact = s["mm"] >= 2
            q = int(round(between(qlo, qhi) / (4 if compact else 1) / step)) * step or step
            lo, hi = MARGIN[cls]
            m = between(lo, hi) * (4.0 if s["gradeId"] == "EX" else 3.2 if compact else 1.4 if s["gradeId"] in ("FR", "CR") else 1.0)
            ln = dict(id="%s/%d0" % (oid, i + 1), orderId=oid, skuId=s["id"], qty=q, margin=int(round(m)), cls=cls, customerId=cust["id"])
            if seg == "OEM" and s["mm"] <= 1.0 and s["sizeId"] in ("S84", "S104", "S124") and ncut < 16 and R.random() < 0.18:
                ncut += 1
                pcs = R.sample(CUT_PIECES, rint(2, 3))
                size = sizes_by_id[s["sizeId"]]
                fit = shelf_pack(size["lenMm"], size["widMm"], pcs)
                per = sum(fit.values()) or 1
                need = rint(300, 900)
                ln["cutPlan"] = dict(pieces=[dict(name=p[0], w=p[1], h=p[2], perSheet=fit[p[0]]) for p in pcs], piecesPerSheet=per, piecesOrdered=need)
                ln["qty"] = int(math.ceil(need / per / 10.0) * 10)
            o["lines"].append(ln["id"])
            lines.append(ln)
            m_ = ln["qty"] * mps[s["id"]]
            vol[cls] += m_
            total += m_
        orders.append(o)
    stats = dict(targetMinutes=int(target), orderMinutes=int(total), normMinutes=int(norm_min), capacityPerDay=int(cap_day),
                 byClass={k: int(v) for k, v in vol.items()}, orders=len(orders), lines=len(lines), sheets=sum(l["qty"] for l in lines), cutLines=ncut)
    return orders, lines, stats, mps


RUSH_CUSTOMER = "Gulf Panel Trading LLC"


def rush_order_spec(customers, skus):
    """S1: an export container order that is NOT in the book; the Scenario launcher inserts it at the as-of moment"""
    cust = next(c for c in customers if c["name"] == RUSH_CUSTOMER)
    cand = [s for s in skus if s["gradeId"] == "GP" and s["sizeId"] == "S84" and s["mm"] in (0.8, 1.0) and s["finishId"] in ("SU", "SM", "HG", "OP") and s["sides"] == "S"]
    cand.sort(key=lambda s: -s["popularity"])
    pick_ = cand[:8]
    qtys = [480, 420, 360, 360, 300, 300, 240, 180]
    due = (ASOF + timedelta(days=6)).replace(hour=18, minute=0)
    oid = "EX%s-RUSH" % ASOF.strftime("%y")
    return dict(id=oid, customerId=cust["id"], cls="EXPORT", segment="EXPORT", orderDate=iso(ASOF), due=iso(due),
                customerPo="PO/%s/URGENT" % cust["id"], incoterm="FOB Mundra", note="Vessel cut-off " + (due - timedelta(days=2)).strftime("%d %b") + " — added container",
                lines=[dict(id="%s/%d0" % (oid, i + 1), orderId=oid, skuId=s["id"], qty=q, margin=int(round(between(470, 540))), cls="EXPORT", customerId=cust["id"])
                       for i, (s, q) in enumerate(zip(pick_, qtys))])
