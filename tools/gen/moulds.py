"""Mould sets (press plates of one texture, sized to one bed class) — the mould is a first-class schedulable resource (req 1b).
A set is used by one press at a time; its plates age together: every press cycle it is mounted in adds 1 to its counter,
eligible SKUs narrow as health falls (req 4a), and it goes for refurbishment before it is exhausted. Customer-dedicated
sets are locked to a customer and a press, with their spare capacity pooled for general orders (req 1c). GENERATED."""
from .common import R, rint, wpick
from .config import PRESSES, MOULD_LIFE_CYCLES
from .catalogue import FIN, FINISHES

BED_PRESSES = {b: [p["id"] for p in PRESSES if p["bedFt"] == b] for b in (8, 14, 16)}


def build_mould_sets(skus, dedicated_pairs):
    """one or two sets per (finish, bed class) that has work; plates 16/24/32 (= 2/3/4 HPL daylights at 8 plates)"""
    need = {}
    press_bed = {p["id"]: p["bedFt"] for p in PRESSES}
    for s in skus:
        for pid in s["presses"]:
            k = (s["finishId"], press_bed[pid])
            need[k] = need.get(k, 0) + s["popularity"]
    fin_rank = {f[0]: i for i, f in enumerate(sorted(FINISHES, key=lambda f: -f[3]))}
    sets = []
    for (fin, bed), pop in sorted(need.items(), key=lambda kv: (kv[0][1], fin_rank[kv[0][0]])):
        rank = fin_rank[fin]
        if bed != 8 and pop < 0.02 and rank > 20:
            continue          # rare texture on a big bed: that work waits for an 8 ft press or the texture's other bed
        n = 3 if (bed == 8 and rank < 5) else 2 if (bed == 8 and rank < 18) or (bed == 14 and rank < 10) or (bed == 16 and rank < 6) else 1
        for i in range(n):
            plates = 48 if rank < 6 else 40 if rank < 14 else 32 if rank < 24 else 24   # 6 / 5 / 4 / 3 HPL daylights
            sets.append(dict(id="%s-%02d-%s" % (fin, bed, "ABCD"[i]), finishId=fin, bedFt=bed, plates=plates, dedicatedTo=None, pressLock=None))
    # customer-dedicated sets (a customer's texture always comes from this set on this press)
    for cust, fin, bed, pid in dedicated_pairs:
        k = sum(1 for s in sets if s["finishId"] == fin and s["bedFt"] == bed)
        sets.append(dict(id="%s-%02d-%s" % (fin, bed, "XYZW"[k % 4]), finishId=fin, bedFt=bed, plates=24, dedicatedTo=cust, pressLock=pid))
    # life state at the start of history: counters spread so refurbishments fall throughout the fortnight
    for s in sets:
        s["lifeLimit"] = MOULD_LIFE_CYCLES
        s["counterAtBase"] = rint(0, MOULD_LIFE_CYCLES - 30)
        s["lastShadeAtBase"] = rint(1, 6)
        s["refurbUntilHours"] = rint(4, 40) if R.random() < 0.07 else 0     # in refurbishment at the start of history
        if s["refurbUntilHours"]:
            s["counterAtBase"] = 0
        s["family"] = FIN[s["finishId"]]["family"]
        s["lastRefurbDaysBeforeBase"] = rint(1, 8)
    return sets
