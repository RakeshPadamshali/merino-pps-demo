"""Product catalogue: texture families, finishes, decors, grades, sizes, thicknesses -> cure bands, the attribute-decomposed
SKU master (req 5b), stock-norm SKUs, and the press eligibility rules (req 1a, 1d). Counts match the deck's published range
(500+ designs, 35+ finishes, 11 sizes, 0.5-30 mm, 1200+ SKUs); every name and value is GENERATED (fictional)."""
from .common import R, wpick, between, rint
from .config import (PRESSES, BEDS, SIZES, SIZE_WEIGHT, CURE_BANDS, THICKNESSES, IMPORTED_PAPER_SHARE, MTS_SKUS, HEALTH_CLASSES)

# ---------------------------------------------------------------- texture families & finishes (one finish = one mould texture)
FAMILIES = [
    ("SUE", "Suede & matt", "C"), ("GLS", "Gloss", "A"), ("WDG", "Woodgrain", "C"), ("LIN", "Linear", "C"),
    ("STN", "Stone", "C"), ("FAB", "Fabric & leather", "C"), ("EMB", "Emboss / 3D", "C"), ("SMO", "Smooth", "B"),
]
FINISHES = [   # code, name, family, popularity weight
    ("SU", "Suede", "SUE", 14), ("SM", "Super Matt", "SUE", 12), ("SF", "Soft Matt", "SUE", 6), ("VL", "Velvet Matt", "SUE", 4), ("AF", "Anti-Fingerprint Matt", "SUE", 5),
    ("HG", "High Gloss", "GLS", 10), ("MG", "Mirror Gloss", "GLS", 4), ("SG", "Semi Gloss", "GLS", 4), ("SA", "Satin Gloss", "GLS", 3),
    ("OP", "Oak Pore", "WDG", 11), ("TL", "Teak Line", "WDG", 8), ("WP", "Walnut Pore", "WDG", 6), ("AG", "Ash Grain", "WDG", 5), ("SY", "Synchro Wood", "WDG", 6), ("RW", "Rustic Wood", "WDG", 4), ("PN", "Pine Knot", "WDG", 3),
    ("LB", "Linear Brush", "LIN", 4), ("VT", "Vertical Line", "LIN", 3), ("HZ", "Horizontal Line", "LIN", 2), ("MB", "Metallic Brush", "LIN", 3),
    ("SL", "Slate", "STN", 4), ("RR", "Rough Rock", "STN", 3), ("CN", "Concrete", "STN", 3), ("SB", "Sand Blast", "STN", 2), ("TE", "Terra", "STN", 2),
    ("LE", "Leather", "FAB", 3), ("FA", "Fabric", "FAB", 3), ("KN", "Knit", "FAB", 2), ("ME", "Mesh", "FAB", 2), ("CA", "Cane", "FAB", 2),
    ("HM", "Hammered", "EMB", 2), ("DE", "Deep Emboss", "EMB", 2), ("WV", "Wave", "EMB", 2),
    ("PL", "Plain", "SMO", 5), ("SK", "Silk", "SMO", 4), ("PR", "Pearl", "SMO", 3),
]
FAM_CLASS = {f[0]: f[2] for f in FAMILIES}
FIN = {f[0]: dict(code=f[0], name=f[1], family=f[2], pop=f[3]) for f in FINISHES}
GLOSS_FAMILY = "GLS"

# which finish families a decor family is sold in (with weights)
DECOR_FINISH_FAMILIES = {
    "SOLID": {"SUE": 40, "SMO": 22, "GLS": 26, "FAB": 6, "EMB": 6},
    "WOOD": {"WDG": 62, "SUE": 22, "LIN": 10, "GLS": 6},
    "STONE": {"STN": 58, "SUE": 24, "GLS": 18},
    "ABSTRACT": {"SUE": 34, "SMO": 20, "EMB": 22, "FAB": 24},
    "METAL_TEXTILE": {"LIN": 48, "FAB": 40, "SUE": 12},
}
WOOD_FINISH = {"Oak": "OP", "Teak": "TL", "Walnut": "WP", "Ash": "AG", "Pine": "PN"}   # species with a matching pore texture

# ---------------------------------------------------------------- decor names + colours (fictional)
SOLID_BASES = [("White", "#f4f4f1"), ("Ivory", "#efe8d8"), ("Cream", "#ece2c9"), ("Beige", "#d9c7a7"), ("Sand", "#cdb895"), ("Stone", "#b7ad9c"),
               ("Grey", "#9ea3a6"), ("Slate", "#6f7880"), ("Graphite", "#4b5055"), ("Charcoal", "#35383b"), ("Black", "#1d1e20"), ("Blue", "#5a7fa8"),
               ("Navy", "#2c3e5c"), ("Teal", "#3f7f80"), ("Aqua", "#8fc3c4"), ("Green", "#6f9a6a"), ("Olive", "#77763f"), ("Sage", "#a3b09a"),
               ("Forest", "#3d5a40"), ("Red", "#b33a35"), ("Maroon", "#6e2a2e"), ("Terracotta", "#b8674a"), ("Orange", "#d9823b"), ("Mustard", "#c9a23d"),
               ("Yellow", "#e3c65a"), ("Pink", "#d99aa5"), ("Mauve", "#a07f8e"), ("Lilac", "#b9a6c9"), ("Purple", "#5d4677"), ("Brown", "#6f4e37"),
               ("Chocolate", "#4a3326"), ("Taupe", "#8d7b6d"), ("Mocha", "#7a5c48")]
SOLID_ADJ = [("Frost", .22), ("Arctic", .18), ("Pearl", .14), ("Pale", .12), ("Soft", .08), ("Light", .1), ("Classic", 0), ("Warm", .02),
             ("Urban", -.04), ("Dusty", .03), ("Smoky", -.1), ("Royal", -.08), ("Deep", -.16), ("Midnight", -.24)]
WOOD_SPECIES = [("Oak", "#b98a55"), ("Walnut", "#6b4a33"), ("Teak", "#9c6a3c"), ("Ash", "#cdb792"), ("Maple", "#d9b98a"), ("Cherry", "#9a5a3c"),
                ("Elm", "#a5835e"), ("Pine", "#d2ac72"), ("Wenge", "#4a3a2e"), ("Acacia", "#8e6a3e"), ("Sheesham", "#7b5236"), ("Mango", "#b08b5e"),
                ("Beech", "#c99d6b"), ("Birch", "#e0c9a3"), ("Larch", "#b88855"), ("Zebrano", "#a88c62"), ("Rosewood", "#5e3326"), ("Mahogany", "#6a2f22"),
                ("Sapele", "#7d4128"), ("Cedar", "#9b5b3a")]
WOOD_TONE = [("Natural", 0), ("Bleached", .24), ("Smoked", -.16), ("Nordic", .13), ("Rustic", -.05), ("Classic", 0), ("Honey", .06),
             ("Grey-washed", .1), ("Dark", -.22), ("Golden", .05), ("Burnt", -.13), ("Silver", .12), ("Antique", -.08), ("Coastal", .11)]
STONE_BASES = [("Carrara", "#e9e8e4"), ("Statuario", "#f1f0ec"), ("Calacatta", "#ece6da"), ("Marquina", "#26272a"), ("Emperador", "#6b4f3d"),
               ("Travertine", "#d6c7ad"), ("Slate", "#555c61"), ("Basalt", "#3b3e41"), ("Granite", "#7c7a78"), ("Terrazzo", "#c9c3b8"),
               ("Concrete", "#9a9a96"), ("Onyx", "#d8cdb5"), ("Quartz", "#dcd8d2"), ("Sandstone", "#c4a47c"), ("Limestone", "#d3c9b3")]
STONE_TONE = [("Vein", 0), ("Cloud", .08), ("Honed", .03), ("Grey", -.06), ("Gold", .02), ("Silver", .06), ("Nero", -.2), ("Bianco", .15)]
ABSTRACT = ["Linen Weave", "Terrazzo Pop", "Geo Lines", "Rattan", "Crosshatch", "Dune", "Ripple", "Mosaic", "Hexa", "Chevron", "Herringbone",
            "Bamboo Leaf", "Paper Grain", "Cement Art", "Brush Stroke", "Canvas Print", "Palm Shadow", "Wave Form"]
ABSTRACT_TONE = [("Beige", "#d7c7aa"), ("Grey", "#a3a5a6"), ("Sage", "#a7b39c"), ("Blush", "#d8b1ad"), ("Ink", "#3e4652"), ("Ochre", "#c49a4a"), ("Mist", "#c9ced2")]
METAL_TEXTILE = [("Brushed Steel", "#9aa0a4"), ("Brushed Aluminium", "#b8bcbf"), ("Copper Patina", "#8a6a4f"), ("Bronze Brush", "#7a5a38"),
                 ("Titanium", "#6e7275"), ("Corten Rust", "#8c4a2f"), ("Gold Leaf", "#c7a24e"), ("Silver Leaf", "#c4c6c8"), ("Tweed", "#8d8a82"),
                 ("Denim", "#4f6480"), ("Hessian", "#b39b74"), ("Nappa", "#2f2b2a"), ("Canvas", "#cfc3a8"), ("Jute", "#b59a6a"), ("Suede Tan", "#a07650"),
                 ("Chambray", "#8fa3b8"), ("Flannel", "#7f8285"), ("Pewter", "#8a8d8f")]


def _hx(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _mix(h, amt):
    """lighten (amt>0, towards white) or darken (amt<0, towards black)"""
    r, g, b = _hx(h)
    t = 255 if amt > 0 else 0
    a = abs(amt)
    return "#%02x%02x%02x" % tuple(int(round(c + (t - c) * a)) for c in (r, g, b))


def _shade(h):
    """1 (lightest) .. 10 (darkest) from relative luminance"""
    r, g, b = (c / 255 for c in _hx(h))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return max(1, min(10, 1 + int(round(9 * (1 - lum)))))


def build_decors():
    out = []

    def add(fam, prefix, name, hexc):
        out.append(dict(family=fam, name=name, hex=hexc, shade=_shade(hexc), prefix=prefix))

    combos = [(a, b) for b in SOLID_BASES for a in SOLID_ADJ]
    R.shuffle(combos)
    for (adj, amt), (base, hx) in combos[:150]:
        add("SOLID", 1, "%s %s" % (adj, base), _mix(hx, amt))
    combos = [(t, s) for s in WOOD_SPECIES for t in WOOD_TONE]
    R.shuffle(combos)
    for (tone, amt), (sp, hx) in combos[:190]:
        add("WOOD", 2, "%s %s" % (tone, sp), _mix(hx, amt))
    combos = [(s, t) for s in STONE_BASES for t in STONE_TONE]
    R.shuffle(combos)
    for (st, hx), (tone, amt) in combos[:90]:
        add("STONE", 3, "%s %s" % (st, tone), _mix(hx, amt))
    combos = [(p, t) for p in ABSTRACT for t in ABSTRACT_TONE]
    R.shuffle(combos)
    for p, (tone, hx) in combos[:55]:
        add("ABSTRACT", 4, "%s %s" % (p, tone), _mix(hx, between(-.05, .08)))
    combos = [(m, v) for m in METAL_TEXTILE for v in ("", " Light", " Dark")]
    R.shuffle(combos)
    for (m, hx), v in combos[:35]:
        add("METAL_TEXTILE", 5, m + v, _mix(hx, .12 if v == " Light" else -.14 if v == " Dark" else 0))
    seq = {}
    decors = []
    for d in out:
        seq[d["prefix"]] = seq.get(d["prefix"], 0) + 1
        did = "D%d%03d" % (d["prefix"], seq[d["prefix"]])
        imported = R.random() < IMPORTED_PAPER_SHARE
        decors.append(dict(id=did, name=d["name"], family=d["family"], shade=d["shade"], hex=d["hex"],
                           paperId="PP-" + did, paperSource="IMPORT" if imported else "DOMESTIC",
                           popularity=round(1.0 / (1 + R.random() * 9) ** 0.9, 4)))
    return decors


# ---------------------------------------------------------------- grades, sizes, thicknesses
GRADES = [
    dict(id="GP", name="General Purpose", kind="HPL", note="Decorative HPL for furniture and panelling"),
    dict(id="PF", name="Post-Forming", kind="HPL", note="0.5-0.8 mm, bends round edges"),
    dict(id="AB", name="Anti-Bacterial", kind="HPL", note="Healthcare and food areas"),
    dict(id="FR", name="Fire Retardant", kind="HPL / compact", note="Class-rated; special resin system (P2, P5)"),
    dict(id="CR", name="Chemical Resistant", kind="HPL / compact", note="Laboratory worktops; special resin system (P2, P5)"),
    dict(id="CP", name="Compact", kind="Compact", note="2-30 mm self-supporting panels"),
    dict(id="EX", name="Exterior Compact", kind="Compact", note="UV-stable overlay, 6-12 mm (P5, P6)"),
]


def band_of(t):
    for b in CURE_BANDS:
        if b["minMm"] <= t <= b["maxMm"]:
            return b["id"]
    raise ValueError(t)


def kraft_plies(t):
    return max(1, int(round((t - 0.25) / 0.17)))


def build_sizes():
    return [dict(id=c, lenMm=l, widMm=w, label=lab, weight=SIZE_WEIGHT[c]) for c, l, w, lab in SIZES]


def build_thicknesses():
    return [dict(id=("T%g" % t).replace(".", "_"), mm=t, bandId=band_of(t), kraftPlies=kraft_plies(t),
                 kind="HPL" if t < 2 else "Compact") for t in THICKNESSES]


def nest_factor(size, bed_ft):
    """how many books of this size fit one plate, side by side along the bed length (0 = does not fit)"""
    b = BEDS[bed_ft]
    if size["lenMm"] > b["lenMm"] or size["widMm"] > b["widMm"]:
        return 0
    return min(2, b["lenMm"] // size["lenMm"])


PRESS_RULES = [   # attribute-based machine eligibility (req 1d) — configured as attributes, not hard-coded SKU lists
    dict(id="R1", attribute="thickness", condition=">= 2 mm (compact)", pressFlag="compact", presses=None, reason="Compact books need the deep-daylight presses"),
    dict(id="R2", attribute="finish family", condition="Gloss", pressFlag="gloss", presses=None, reason="Polished gloss plates need the plate-handling rig"),
    dict(id="R3", attribute="grade", condition="FR or CR", pressFlag="special", presses=None, reason="Special resin systems are piped to these presses only"),
    dict(id="R4", attribute="grade", condition="EX", pressFlag="exterior", presses=None, reason="UV overlay line feeds these presses only"),
]
for r in PRESS_RULES:
    r["presses"] = ", ".join(p["id"] for p in PRESSES if p[r["pressFlag"]])


def eligible_presses(sku, sizes_by_id):
    size = sizes_by_id[sku["sizeId"]]
    out = []
    for p in PRESSES:
        if not nest_factor(size, p["bedFt"]):
            continue                                          # R0 directional fit: product length <= bed length
        if sku["mm"] >= 2 and not p["compact"]:
            continue
        if FIN[sku["finishId"]]["family"] == GLOSS_FAMILY and not p["gloss"]:
            continue
        if sku["gradeId"] in ("FR", "CR") and not p["special"]:
            continue
        if sku["gradeId"] == "EX" and not p["exterior"]:
            continue
        out.append(p["id"])
    return out


def health_class(finish_id, decor):
    """mould health a SKU needs: the stricter of its finish family and its decor (dark solids show plate wear)"""
    c = FAM_CLASS[FIN[finish_id]["family"]]
    if decor["family"] == "SOLID" and decor["shade"] >= 8:
        c = "A"
    elif decor["family"] == "SOLID" and c == "C":
        c = "B"
    return c


HPL_T = {0.8: 30, 1.0: 45, 0.6: 6, 0.7: 5, 1.25: 7, 1.5: 6, 0.5: 1}
COMPACT_T = {12: 30, 6: 20, 8: 8, 10: 8, 16: 10, 3: 5, 4: 5, 2: 4, 20: 5, 25: 3, 30: 2}


def build_skus(decors, sizes):
    sizes_by_id = {s["id"]: s for s in sizes}
    skus, seen = [], set()
    fam_fin = {}
    for f in FINISHES:
        fam_fin.setdefault(f[2], []).append((f[0], f[3]))

    def mk(decor, fin, t, size, grade, double):
        sid = "%s-%s-%g-%s-%s%s" % (decor["id"], fin, t, size[1:], grade, "-DS" if double else "")
        if sid in seen:
            return None
        s = dict(id=sid, decorId=decor["id"], finishId=fin, mm=t, sizeId=size, gradeId=grade, sides="D" if double else "S")
        s["bandId"] = band_of(t)
        s["presses"] = eligible_presses(s, sizes_by_id)
        if not s["presses"]:
            return None
        s["healthClass"] = health_class(fin, decor)
        pop = decor["popularity"] * FIN[fin]["pop"] * sizes_by_id[size]["weight"] * (HPL_T.get(t) or COMPACT_T.get(t, 3))
        s["popularity"] = round(pop / 1000.0, 5)
        seen.add(sid)
        skus.append(s)
        return s

    def pick_finish(decor):
        fam = wpick(DECOR_FINISH_FAMILIES[decor["family"]])
        if fam == "WDG":
            sp = decor["name"].split()[-1]
            if sp in WOOD_FINISH and R.random() < 0.65:
                return WOOD_FINISH[sp]
        return wpick(fam_fin[fam])

    for d in decors:
        nf = wpick({1: 34, 2: 46, 3: 20})
        fins = []
        for _ in range(nf * 3):
            f = pick_finish(d)
            if f not in fins:
                fins.append(f)
            if len(fins) >= nf:
                break
        for fin in fins:
            t = wpick(HPL_T)
            grade = "PF" if (t <= 0.8 and R.random() < 0.22) else "AB" if (t in (0.8, 1.0) and R.random() < 0.05) else \
                    "FR" if (t >= 1.0 and FIN[fin]["family"] != GLOSS_FAMILY and R.random() < 0.05) else \
                    "CR" if (t >= 1.25 and FIN[fin]["family"] != GLOSS_FAMILY and R.random() < 0.03) else "GP"
            size = wpick(SIZE_WEIGHT)
            if grade == "PF" and t > 0.8:
                grade = "GP"
            mk(d, fin, t, size, grade, t == 1.0 and grade == "GP" and R.random() < 0.06)
            if R.random() < 0.30:                             # a second size or thickness of the same decor + finish
                t2 = wpick(HPL_T)
                mk(d, fin, t2, wpick(SIZE_WEIGHT), "PF" if t2 <= 0.8 and R.random() < 0.2 else "GP", False)
            if d["family"] in ("SOLID", "STONE", "ABSTRACT", "WOOD") and FIN[fin]["family"] in ("SUE", "SMO", "STN", "WDG") and R.random() < 0.20:
                tc = wpick(COMPACT_T)
                g = "EX" if (6 <= tc <= 12 and R.random() < 0.22) else "CR" if (12 <= tc <= 20 and R.random() < 0.18) else \
                    "FR" if (6 <= tc <= 12 and R.random() < 0.06) else "CP"
                mk(d, fin, tc, wpick({"S84": 50, "S74": 14, "S104": 12, "S124": 16, "S164": 8}), g, True)
    return skus


def choose_mts(skus):
    """stock-norm (make-to-stock) SKUs: the most popular plain GP HPL sheets in standard sizes"""
    cands = [s for s in skus if s["gradeId"] == "GP" and s["sides"] == "S" and s["mm"] in (0.8, 1.0) and s["sizeId"] in ("S84", "S74")]
    cands.sort(key=lambda s: -s["popularity"])
    return cands[:MTS_SKUS]


def build_norms(mts):
    out = []
    bands = {"BLACK": 3, "RED": 12, "YELLOW": 30, "GREEN": 40, "BLUE": 15}
    top = max(s["popularity"] for s in mts)
    for s in mts:
        use = max(6, int(round(6 + 34 * (s["popularity"] / top) ** 0.6 + between(-2, 2))))
        norm = int(round(use * between(8, 14), -1))
        b = wpick(bands)
        share = 0 if b == "BLACK" else between(.05, .32) if b == "RED" else between(.34, .65) if b == "YELLOW" else between(.68, .98) if b == "GREEN" else between(1.02, 1.3)
        out.append(dict(id="NRM-" + s["id"], skuId=s["id"], normSheets=norm, usePerDay=use, onHandAtBase=int(round(norm * share)),
                        replenishRule="replenish to norm when below 2/3 (yellow)"))
    return out


HEALTH = {h["id"]: h for h in HEALTH_CLASSES}
