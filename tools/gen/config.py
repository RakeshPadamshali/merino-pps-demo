"""Every GENERATED parameter of the Merino demo lives here, in one place, so each value is visible and easy to change.

Two kinds of value:
  CONFIRMED  - from the Bluemingo deck (21 Sept) or confirmed by the user (press fleet, one texture per daylight).
  GENERATED  - not from Merino; a plausible value chosen for the demo. The Master Data page marks these "generated".
"""

SEED = 2209

PLANT = dict(company="Merino Laminates", site="HPL Press Shop", title="PPS — Production Planning & Scheduling")
HISTORY_DAYS = 14            # GENERATED: frozen history simulated with Merino's current fixed sequence
FORWARD_DAYS = 21            # GENERATED: live plan horizon from the as-of moment
ASOF_HOUR, ASOF_MIN = 10, 30  # "now" in the demo = as-of day 10:30, shift A

# ---- presses: CONFIRMED fleet (6 presses: 3 x 8 ft, 2 x 14 ft, 1 x 16 ft) and daylights (13-14, deck) ----
BEDS = {   # usable platen size in mm per bed class (GENERATED values, directional fit = length <= bed length)
    8: dict(lenMm=2500, widMm=1300),
    14: dict(lenMm=4350, widMm=1550),
    16: dict(lenMm=4950, widMm=1550),
}
PRESSES = [   # capability flags are GENERATED attribute rules (req 1d)
    dict(id="P1", name="Press 1", bedFt=8, daylights=13, compact=False, gloss=True, special=False, exterior=False, downtimeStart="06:00"),
    dict(id="P2", name="Press 2", bedFt=8, daylights=13, compact=False, gloss=False, special=True, exterior=False, downtimeStart="08:00"),
    dict(id="P3", name="Press 3", bedFt=8, daylights=13, compact=True, gloss=False, special=False, exterior=False, downtimeStart="10:00"),
    dict(id="P4", name="Press 4", bedFt=14, daylights=14, compact=False, gloss=True, special=False, exterior=False, downtimeStart="12:00"),
    dict(id="P5", name="Press 5", bedFt=14, daylights=14, compact=True, gloss=False, special=True, exterior=True, downtimeStart="14:00"),
    dict(id="P6", name="Press 6", bedFt=16, daylights=14, compact=True, gloss=True, special=False, exterior=True, downtimeStart="16:00"),
]
RUN_HOURS = 22               # CONFIRMED (deck worked example)
DOWNTIME_MIN = 120           # 24 h - 22 running h: planned maintenance & platen cleaning, staggered per press (GENERATED times)
EFFICIENCY = 0.90            # CONFIRMED (deck worked example: 90% planned efficiency)
MOULDS_PER_DAYLIGHT = 8      # CONFIRMED
LAMINATES_PER_MOULD = 2      # CONFIRMED (single-sided); double-sided laminate takes 1 per mould (GENERATED rule)

# ---- cure bands: all daylights in one cycle share one cure profile (deck). ~60 min for 1 mm is CONFIRMED; the rest GENERATED ----
CURE_BANDS = [
    dict(id="B1", name="Thin HPL", minMm=0.5, maxMm=0.8, pressMin=55, platesPerDaylight=8),
    dict(id="B2", name="Standard HPL", minMm=1.0, maxMm=1.5, pressMin=60, platesPerDaylight=8),
    dict(id="B3", name="Thin compact", minMm=2.0, maxMm=6.0, pressMin=110, platesPerDaylight=4),
    dict(id="B4", name="Compact", minMm=8.0, maxMm=12.0, pressMin=180, platesPerDaylight=2),
    dict(id="B5", name="Thick compact", minMm=16.0, maxMm=30.0, pressMin=300, platesPerDaylight=1),
]
THICKNESSES = [0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2, 3, 4, 6, 8, 10, 12, 16, 20, 25, 30]   # range 0.5-30 mm CONFIRMED

# ---- sizes: 11 sizes CONFIRMED as a count; the actual list is GENERATED ----
SIZES = [   # code, length mm, width mm, label
    ("S73", 2135, 915, "7 x 3 ft"), ("S74", 2135, 1220, "7 x 4 ft"), ("S83", 2440, 915, "8 x 3 ft"), ("S84", 2440, 1220, "8 x 4 ft"),
    ("S104", 3050, 1220, "10 x 4 ft"), ("S1043", 3050, 1300, "10 x 4.25 ft"), ("S124", 3660, 1220, "12 x 4 ft"), ("S125", 3660, 1525, "12 x 5 ft"),
    ("S144", 4270, 1220, "14 x 4 ft"), ("S145", 4270, 1525, "14 x 5 ft"), ("S164", 4880, 1220, "16 x 4 ft"),
]
SIZE_WEIGHT = {"S84": 52, "S74": 8, "S83": 8, "S73": 4, "S104": 8, "S1043": 3, "S124": 7, "S125": 3, "S144": 3, "S145": 1.5, "S164": 2.5}

# ---- mould (press plate) policy: life ~ weekly refurbishment is CONFIRMED (deck); numbers GENERATED ----
MOULD_LIFE_CYCLES = 130      # ~ 7 days at 19 cycles/day
REFURB_HOURS = 48
HEALTH_CLASSES = [   # remaining mould life a line needs: eligibility narrows as a set ages (req 4a)
    dict(id="A", minHealth=0.50, meaning="Export grade, gloss finishes and dark solids (shade 8-10) — defects show"),
    dict(id="B", minHealth=0.30, meaning="Solid colours and smooth / matt finishes"),
    dict(id="C", minHealth=0.05, meaning="Woodgrain, stone, fabric and emboss patterns — hide minor plate wear"),
]
CHANGEOVER = dict(daylightSwapMin=8, bandChangeMin=20, cleaningPass="one daylight runs a cleaning pass (no output) for one cycle")
THICKNESS_MIX = dict(target=2, hardCap=3)   # objective 5: distinct thicknesses per press load (GENERATED numbers)
FINISHING_DAYS = 1           # trim + back-sand + QC after pressing, before dispatch (GENERATED)

# ---- objectives: the 5 objectives and Merino's current fixed sequence are CONFIRMED (deck slide 5); weights GENERATED ----
OBJECTIVES = [
    dict(id="profit", n=1, label="Profitability — export first", side="Customer"),
    dict(id="dates", n=2, label="Committed delivery dates", side="Customer"),
    dict(id="norms", n=3, label="Stock-norm replenishment", side="Customer"),
    dict(id="changeover", n=4, label="Minimise changeovers", side="Manufacturing"),
    dict(id="mix", n=5, label="Control thickness mix", side="Manufacturing"),
]
WEIGHT_PRESETS = [
    dict(id="today", label="Merino today (fixed sequence)", mode="sequence", profit=0, dates=0, norms=0, changeover=0, mix=0, delayScale=0,
         note="Export first, then committed domestic by date, then stock norms; changeover and thickness only break ties — solved in sequence, as planned today."),
    dict(id="balanced", label="Balanced (recommended)", mode="weighted", profit=20, dates=50, norms=10, changeover=12, mix=8, delayScale=1.2,
         note="All five objectives in one score: committed dates first, margin separates urgent lines, texture campaigns and tidy thickness mixes kept wherever that costs no delivery."),
    dict(id="otif", label="OTIF first", mode="weighted", profit=10, dates=66, norms=8, changeover=8, mix=7, delayScale=1.6,
         note="The delivery promise dominates; margin only separates equals. Pays for it in mould swaps, cleaning passes and stock norms."),
    dict(id="utilisation", label="Utilisation first", mode="weighted", profit=20, dates=40, norms=10, changeover=48, mix=10, delayScale=1.0,
         note="Long mould campaigns: a texture gets a new daylight only when it has plenty of released work. Fewest swaps, most pressing time; accepts a little more lateness."),
]
# ---- release window (GENERATED): a line may be pressed at most this many days before its due date (finished-goods space,
# working capital). Merino's fixed sequence and the weighted plan both respect it; the rest of the capacity goes to stock norms ----
RELEASE_WINDOW_DAYS = {"EXPORT": 12, "DOM_COMMITTED": 8, "DOM_OPEN": 14}
DELAY_PENALTY = {"EXPORT": 6000, "DOM_COMMITTED": 2500, "DOM_OPEN": 400, "NORM": 0}          # Rs per line per day late (GENERATED)
MARGIN = {"EXPORT": (380, 520), "DOM_COMMITTED": (210, 300), "DOM_OPEN": (190, 260), "NORM": (180, 240)}   # Rs contribution / sheet (illustrative)

# ---- stock norms (colour bands CONFIRMED in principle, deck slide 5); values GENERATED ----
NORM_BANDS = [   # share of the norm (target buffer) on hand
    dict(id="BLACK", lo=None, hi=0.0, meaning="Stock-out"),
    dict(id="RED", lo=0.0, hi=1 / 3, meaning="Stock-out risk"),
    dict(id="YELLOW", lo=1 / 3, hi=2 / 3, meaning="Replenish"),
    dict(id="GREEN", lo=2 / 3, hi=1.0, meaning="Healthy"),
    dict(id="BLUE", lo=1.0, hi=None, meaning="Above norm"),
]
MTS_SKUS = 180

# ---- demand sizing (GENERATED): open demand at as-of vs the forward horizon's press capacity ----
DEMAND_FACTOR = 0.95         # calibrated so the plan is tight: trade-offs between the five objectives actually bite
HISTORY_LOAD = 0.95
CLASS_MIX = {"EXPORT": 0.29, "DOM_COMMITTED": 0.47, "DOM_OPEN": 0.12}   # of order volume; stock-norm replenishment is on top
IMPORTED_PAPER_SHARE = 0.70  # decor paper from China (CONFIRMED that it is imported; share GENERATED)
