# Merino Laminates — PPS demo

A clickable demo of **production planning and scheduling for an HPL press shop**: six multi-daylight presses, mould sets
per texture, cure bands, light-to-dark colour sequencing, decor paper from China, stock norms and five competing
objectives — all running on a real scheduling engine in the browser, with no server and no internet.

Open `index.html` (the tab host) or any page on its own.

> **Everything in the dataset is fictional.** Customers, orders, designs, suppliers, people and volumes are generated for
> the demo. The numbers that come from Merino's own brief (13–14 daylights, 8 moulds × 2 sheets a plate, ~60 min for a
> 1 mm cycle, 22 h × 90 %, the 8 / 14 / 16 ft beds, weekly mould refurbishment, light-to-dark sequencing, the five
> objectives) and the press fleet confirmed with the user (3 × 8 ft, 2 × 14 ft, 1 × 16 ft, one texture per daylight) are
> modelled as given — every other value is a generated demo value, listed in `tools/gen/config.py` and marked
> **GENERATED** on the Master Data page.

## Run it

```bash
python serve.py            # http://localhost:8000  (any static server works)
```

The pages need no build step. Fonts, icons, ECharts and SheetJS are vendored in `assets/vendor/`, so the demo runs
completely offline (the verifier fails if any request leaves the site).

## The modules

| Page | What it shows |
|---|---|
| **PPS Dashboard** (`home.html`) | OTIF, late lines, delay cost, utilisation, fill, changeovers, thickness mix, norms; press status board; alerts; the **scenario launcher** |
| **Order Book & BTP** (`orders.html`) | Every order line with a stateless balance-to-produce, eligibility, projected ready date; rush / cancel / downgrade / reject with a priority-order impact report |
| **Objective Studio** (`objectives.html`) | Merino today (the fixed sequence) against the weighted plans, outcome by outcome, plus custom weights |
| **ATP & Capacity** (`atp.html`) | Capacity at daylight × plate × cycle level for any attribute combination, and a promise date quoted against the live plan |
| **Press Load Builder** (`loadbuilder.html`) | One press cycle as a daylight × plate grid: mould sets, health, shades, nesting, thickness mix, "why this slot" |
| **Press Schedule** (`schedule.html`) | The Gantt of all six presses with changeovers, downtime and breakdowns, coloured by status, class, cure band or one order |
| **Shift Work Orders** (`workorders.html`) | What each press runs this shift, daylight by daylight, with print marks and the book-building pick list (Excel) |
| **Mould Board** (`moulds.html`) | Every mould set: where it is, its life and health, what it may still press, refurbishment calendar, texture coverage |
| **Colour & Changeover** (`sequence.html`) | Shade ladders per set with cleaning resets, cure-band runs, texture campaigns and the changeover log |
| **Paper & Materials** (`materials.html`) | Decor paper by design: stock, China POs and ETAs, what the plan needs, and the lines that wait |
| **Stock Norms** (`norms.html`) | Make-to-stock SKUs in buffer bands now and at the end of the plan, with the replenishment the plan raised |
| **Plan vs Actual** (`planactual.html`) | The last 14 days: attainment by press and day, and every lost sheet attributed to a breakdown, an overrun or a downgrade |
| **Traceability** (`trace.html`) | A print mark to its cycle, daylight, mould set, paper lot and shift — and back out to the recall scope |
| **Master Data** (`masters.html`) | ~30 masters in six groups with Excel template → upload → validate → preview → apply → audit; applied rows re-plan the shop |

## Scenarios

The dashboard's launcher runs these on the live plan; every page then shows the same plan. **Reset demo** (top right)
clears everything.

| | Scenario | Lands on | What it proves |
|---|---|---|---|
| S1 | Rush export container order | `orders.html#impact` | Eligible presses and moulds are found, and the impact report names the orders that move |
| S2 | Merino today vs weighted objectives | `objectives.html` | Same order book, same plant — better delivery with far fewer changeovers, cleaning passes and stock-outs |
| S3 | Mould set off for refurbishment | `moulds.html#<set>` | Eligibility narrows, the work moves to the twin sets, the refurbishment calendar updates |
| S4 | China paper PO slips 12 days | `materials.html#<decor>` | Lines of that design wait for paper, the presses backfill, committed dates slip visibly |
| S5 | Cancellation + QC downgrade | `orders.html#btp` | Balance-to-produce recalculates itself — nothing is re-entered |
| S6 | Print-mark complaint | `trace.html#complaint` | One sheet → cycle, daylight, mould set, paper lot → the recall scope of that mould campaign |
| S7 | New SKU uploaded from Excel | `masters.html#skus` | A SKU is only its attributes: presses, cure band, mould sets and health class are inherited, then quoted in ATP |

## How the demo is put together

- **`data/mer-data.js`** — the whole dataset (`window.MER`), written by `tools/generate_data.py`. **Generated, never
  hand-edited**: change `tools/gen/*.py` and re-run.

  ```bash
  python tools/generate_data.py                 # as-of = today 10:30
  python tools/generate_data.py --asof 2026-09-22
  ```

  The generator re-bases every date on the as-of moment, checks its own output (unique ids, every reference resolves,
  every demanded SKU has an eligible press and a mould set, demand within a band of capacity, every scenario anchor
  present) and writes the data dictionary `data/README.md`.

- **`assets/mer-engine.js`** — the planning engine, plain JavaScript, no DOM, so it also runs in Node. Two runs:
  **history** (14 days, frozen, Merino's fixed sequence, with the recorded breakdowns, overruns and QC downgrades) and
  the **live plan** (21 days from the as-of, with the chosen objective weights and any what-ifs). Its rules: directional
  bed fit and nesting, attribute restrictions per press, one texture per daylight from a set sized for that bed, one cure
  band per cycle, mould life / health / refurbishment, dedicated sets, light-to-dark with cleaning resets, thickness-mix
  target and hard cap, decor-paper gating, release windows, stock-norm buffers and the delay penalty.

- **`assets/mer-core.js`** — one shared runtime for every page: the live-demo state (weights, what-ifs, master uploads)
  in `localStorage`, the host-shared plan (the tab host computes once, every tab reads it), formatting, colours, the
  Gantt with its window pager, Excel export and the scenario definitions.

## Look and feel

The demo follows the **Bluemingo MES v2 design system** (`UI-Style-Guide-Prompt.md`, kept with the MES workspace — not
copied into this public repo), the same one the other Bluemingo POCs use:

| | |
|---|---|
| Primary | `#25A9E0`, hover `#1E8FBF`, light `#E1F5FE` — interactive elements only |
| Chrome | header `#1a1a2e → #12121f`, sidebar `#1e1e32 → #16213e`, content `#f5f5f5`, cards white with a `#e0e0e0` border |
| Status | success `#388e3c`, warning `#f57c00`, danger `#d32f2f`, info `#2196f3` — always a `rgba(colour, .12)` tint with solid text, never a solid fill |
| Type | Roboto; tables 12 px with 10.5 px uppercase headers; 4 px spacing grid; radius 4 px inputs / 6 px panels |
| Focus | 3 px primary glow `rgba(37,169,224,.15)` |

`assets/mer-shell.css` holds those tokens; every page uses them, so a change there re-themes the whole demo. Merino's own
red stays on the client logo — it is never used as a UI colour.

**Data colours are a separate, validated set** (in `assets/mer-core.js`, `COLOR`): the categorical palette for order
classes (`#2a78d6` / `#eb6834` / `#1baf7a` / `#9e9e9e`, checked for colour-blind separation), a single-hue ramp for cure
bands, the design system's status steps for gauges and heat maps, and the TOC colour code (black / red / yellow / green /
blue) for stock-norm buffers, where the band names *are* the colours.

## Verify

```bash
node tools/verify_engine.js      # ~7M invariant checks on the history and every preset
python tools/verify.py           # all 15 pages headless: no JS errors, no external requests, screenshots
python tools/verify_flows.py     # the seven scenarios end to end, plus Reset demo
python tools/verify_masters.py   # Excel template → edit → upload → validate → apply → re-plan → reset
python tools/audit.py [preset]   # every figure shown on more than one page is the same number
```
