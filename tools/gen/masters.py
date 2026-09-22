"""Remaining masters for the Master Data page: shift calendar, planned downtime, the press x cure-band capacity matrix,
the size x bed fit matrix (directional fit + nesting), mould policy, changeover and colour-sequence rules, thickness-mix
cap, objective presets, delay penalties, print-mark format, roles and users. Each row carries `source`: CONFIRMED (deck /
user) or GENERATED (demo value), so the page can say which numbers came from Merino."""
import math

from .common import rint
from .config import (PRESSES, BEDS, CURE_BANDS, EFFICIENCY, SIZES, MOULD_LIFE_CYCLES, REFURB_HOURS, HEALTH_CLASSES, CHANGEOVER,
                     THICKNESS_MIX, OBJECTIVES, WEIGHT_PRESETS, DELAY_PENALTY, NORM_BANDS, DOWNTIME_MIN, RUN_HOURS, RELEASE_WINDOW_DAYS)
from .catalogue import nest_factor, FAMILIES, FINISHES, GRADES, PRESS_RULES
from .events import CREW

C, G = "CONFIRMED", "GENERATED"


def build_masters(sizes, thicknesses, decors, skus, sets, customers, norms, papers, materials, suppliers):
    m = {}
    m["presses"] = [dict(id=p["id"], name=p["name"], bedFt=p["bedFt"], bedMm="%d x %d" % (BEDS[p["bedFt"]]["lenMm"], BEDS[p["bedFt"]]["widMm"]),
                         daylights=p["daylights"], mouldsPerDaylight=8, runHours=RUN_HOURS, efficiency=EFFICIENCY,
                         compactCapable=p["compact"], glossHandling=p["gloss"], specialResin=p["special"], exteriorUv=p["exterior"],
                         source="CONFIRMED fleet (3 x 8 ft, 2 x 14 ft, 1 x 16 ft); capability flags GENERATED") for p in PRESSES]
    m["bedSizes"] = [dict(id="%d ft" % b, lenMm=v["lenMm"], widMm=v["widMm"], presses=", ".join(p["id"] for p in PRESSES if p["bedFt"] == b), source=G) for b, v in BEDS.items()]
    m["shifts"] = [dict(id="A", start="06:00", end="14:00", incharge=CREW["A"][0], relief=CREW["A"][1]), dict(id="B", start="14:00", end="22:00", incharge=CREW["B"][0], relief=CREW["B"][1]),
                   dict(id="C", start="22:00", end="06:00", incharge=CREW["C"][0], relief=CREW["C"][1])]
    m["downtime"] = [dict(id="DT-" + p["id"], pressId=p["id"], start=p["downtimeStart"], durationMin=DOWNTIME_MIN, reason="Planned maintenance & platen cleaning (22 running h/day)", source="22 h CONFIRMED; window GENERATED") for p in PRESSES]
    m["cureBands"] = [dict(id=b["id"], name=b["name"], thicknessMm="%g-%g" % (b["minMm"], b["maxMm"]), pressMin=b["pressMin"], effectiveMin=int(math.ceil(b["pressMin"] / EFFICIENCY)),
                           platesPerDaylight=b["platesPerDaylight"], source="~60 min for 1 mm CONFIRMED; others GENERATED") for b in CURE_BANDS]
    rows = []
    for b in CURE_BANDS:
        for p in PRESSES:
            rows.append(dict(id="%s-%s" % (b["id"], p["id"]), bandId=b["id"], pressId=p["id"], sheetsPerCycle=p["daylights"] * b["platesPerDaylight"] * 2,
                             effectiveMin=int(math.ceil(b["pressMin"] / EFFICIENCY)), allowed=(b["minMm"] < 2 or p["compact"])))
    m["bandPress"] = rows
    m["pressRules"] = [dict(r, source=G) for r in PRESS_RULES]
    m["textureFamilies"] = [dict(id=f[0], name=f[1], healthClass=f[2]) for f in FAMILIES]
    m["finishes"] = [dict(id=f[0], name=f[1], familyId=f[2], mouldSets=sum(1 for s in sets if s["finishId"] == f[0])) for f in FINISHES]
    m["mouldSets"] = [dict(id=s["id"], finishId=s["finishId"], bedFt=s["bedFt"], plates=s["plates"], daylightsHpl=s["plates"] // 8, lifeLimit=s["lifeLimit"],
                           counterAtBase=s["counterAtBase"], dedicatedTo=s["dedicatedTo"], pressLock=s["pressLock"], refurbUntilHours=s["refurbUntilHours"]) for s in sets]
    m["mouldPolicy"] = [dict(id="LIFE", value=MOULD_LIFE_CYCLES, unit="cycles", meaning="Cycle counter limit; refurbished before exhaustion", source="~weekly CONFIRMED; number GENERATED"),
                        dict(id="REFURB", value=REFURB_HOURS, unit="hours", meaning="Plate re-polish / re-chrome turnaround", source=G)] + \
                       [dict(id="HEALTH-" + h["id"], value=int(h["minHealth"] * 100), unit="% life left", meaning=h["meaning"], source=G) for h in HEALTH_CLASSES]
    m["sizes"] = [dict(id=s["id"], label=s["label"], lenMm=s["lenMm"], widMm=s["widMm"]) for s in sizes]
    fit = []
    for s in sizes:
        for b in BEDS:
            nf = nest_factor(s, b)
            fit.append(dict(id="%s-%d" % (s["id"], b), sizeId=s["id"], bed="%d ft" % b, fits=bool(nf), perPlate=nf or 0))
    m["sizeFit"] = fit
    m["thicknesses"] = [dict(t) for t in thicknesses]
    m["decors"] = [dict(id=d["id"], name=d["name"], family=d["family"], shade=d["shade"], hex=d["hex"], paperId=d["paperId"], paperSource=d["paperSource"]) for d in decors]
    m["grades"] = [dict(g) for g in GRADES]
    m["skus"] = [dict(id=s["id"], decorId=s["decorId"], finishId=s["finishId"], mm=s["mm"], sizeId=s["sizeId"], gradeId=s["gradeId"], sides=s["sides"]) for s in skus]
    m["objectives"] = [dict(o) for o in OBJECTIVES]
    m["weights"] = [dict(w) for w in WEIGHT_PRESETS]
    m["delayPenalty"] = [dict(id=k, rsPerLineDay=v) for k, v in DELAY_PENALTY.items()]
    m["changeover"] = [dict(id="SWAP", minutes=CHANGEOVER["daylightSwapMin"], meaning="Swap one daylight's 8 plates to another texture / set", source=G),
                       dict(id="BAND", minutes=CHANGEOVER["bandChangeMin"], meaning="Change the cure profile (temperature / pressure / time)", source=G),
                       dict(id="CLEAN", minutes=0, meaning="Reset after the darkest shade: that daylight runs one cleaning pass with no output", source="rule CONFIRMED (deck); form GENERATED")]
    m["sequenceRules"] = [dict(id="SEQ-1", rule="Light to dark", detail="On one mould set, each cycle's shade must be >= the last shade since its last cleaning", source=C),
                          dict(id="SEQ-2", rule="Reset", detail="A lighter shade after a darker one needs a cleaning pass first (or another set of the texture)", source=C),
                          dict(id="SEQ-3", rule="Shade index", detail="1 = lightest .. 10 = darkest, from the decor's colour", source=G)]
    m["thicknessMix"] = [dict(id="TARGET", value=THICKNESS_MIX["target"], meaning="Distinct thicknesses per press load the planner aims for (objective 5)", source=G),
                         dict(id="HARD-CAP", value=THICKNESS_MIX["hardCap"], meaning="Never more distinct thicknesses in one load — book assembly is manual", source=G)]
    m["releaseWindow"] = [dict(id=k, days=v, meaning="Pressed at the earliest %d days before the due date (finished-goods space, working capital)" % v, source=G)
                          for k, v in RELEASE_WINDOW_DAYS.items()]
    m["normBands"] = [dict(id=b["id"], fromShare=b["lo"], toShare=b["hi"], meaning=b["meaning"]) for b in NORM_BANDS]
    m["stockNorms"] = [dict(n) for n in norms]
    m["papers"] = [dict(p) for p in papers]
    m["materials"] = [dict(x) for x in materials]
    m["suppliers"] = [dict(s) for s in suppliers]
    m["customers"] = [dict(c) for c in customers]
    m["printMark"] = [dict(id="FORMAT", value="MER {press} {mouldSet} {yymmdd}-C{cycle}-D{daylight}", meaning="Ink-jet stamped on every sheet's back at book building"),
                      dict(id="EXAMPLE", value="MER P4 HG-14-A 260917-C07-D03", meaning="Press 4, mould set HG-14-A, 17 Sep 2026, 7th cycle of the day, daylight 3")]
    m["roles"] = [dict(id="R-PPC", role="PPC Head", rights="All planning pages; publish plan; change objective weights"),
                  dict(id="R-PLN", role="Press Planner", rights="Plan, what-ifs, load builder, work orders"),
                  dict(id="R-SUP", role="Press Supervisor", rights="Shift work orders, cycle confirmation, changeovers"),
                  dict(id="R-QC", role="QC Inspector", rights="Downgrades, traceability, recall scope"),
                  dict(id="R-STR", role="Stores (paper)", rights="Paper stock, receipts, PO follow-up"),
                  dict(id="R-SAL", role="Sales Coordinator", rights="Orders, ATP promise, rush requests"),
                  dict(id="R-ADM", role="PPS Admin", rights="Master data upload, users")]
    m["users"] = [dict(id=u, name=n, roleId=r) for u, n, r in [("amehra", "A. Mehra", "R-PPC"), ("sgupta", "S. Gupta", "R-PLN"), ("kverma", "K. Verma", "R-PLN"),
                                                               ("ryadav", "R. Yadav", "R-SUP"), ("mqureshi", "M. Qureshi", "R-SUP"), ("dchauhan", "D. Chauhan", "R-SUP"),
                                                               ("nbansal", "N. Bansal", "R-QC"), ("pkaur", "P. Kaur", "R-STR"), ("tmalik", "T. Malik", "R-SAL"),
                                                               ("ppsadmin", "PPS Administrator", "R-ADM")]]
    return m
