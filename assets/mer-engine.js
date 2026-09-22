/* Merino PPS engine — one deterministic, explainable scheduler for press x mould x daylight batch loading.
   DOM-free: runs in the browser (window.MEREngine) and in Node for tests.

   One simulation, two phases:
   - HISTORY (base -> as-of): planned with Merino's current fixed sequence (export -> committed domestic -> stock norms),
     with the recorded execution events (breakdowns, cure overruns, QC downgrades, a cancellation, a rejection).
     Frozen: it never changes when the weights move. Its end state is the plant at the as-of moment.
   - PLAN (as-of -> end): the live plan, re-run from that snapshot with the user's objective weights and what-ifs.

   The rules it enforces (the Merino requirements):
   directional press fit + attribute rules (1a, 1d) · one texture per daylight from one mould set, a set on one press at a
   time (1b) · customer-dedicated sets locked to a press, spare capacity pooled (1c) · one cure band per press cycle, daylights
   x plates x laminates x nesting capacity (2a, 2b, 2c) · five objectives, sequential or weighted (3a, 3b) · mould life
   counter narrowing eligibility, refurbishment before exhaustion (4a) · light-to-dark per set with cleaning passes (4b) ·
   changeover minutes in the trade-off (4c) · decor paper availability (5a) · SKUs as attributes (5b) · delay penalty (6b) ·
   stateless balance-to-produce (6c). Times are integer minutes from the start of history (meta.base). */
(function (root) {
  'use strict';
  var E = {};
  var CLS_RANK = { EXPORT: 0, DOM_COMMITTED: 1, DOM_OPEN: 2, NORM: 3 };
  var HC_ORDER = { A: 0, B: 1, C: 2 };

  function hash01(s) { var h = 2166136261; s = String(s); for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 100000) / 100000; }
  function minOf(iso, base) { return Math.round((new Date(iso) - base) / 60000); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }

  // =====================================================================================================================
  // MODEL — masters (+ Master Data uploads) turned into indexed structures. SKU eligibility is DERIVED from attributes here,
  // so a SKU added from Excel inherits its presses and mould sets automatically (req 5b).
  // =====================================================================================================================
  E.prepare = function (MER, overlay) {
    overlay = overlay || {};
    var m = {}, M = MER.m, cfg = MER.cfg;
    function rows(key) {
      var base = (M[key] || []).map(function (r) { return Object.assign({}, r); });
      var o = overlay[key]; if (!o || !o.rows) return base;
      var kf = o.kf || 'id', idx = {}; base.forEach(function (r, i) { idx[r[kf]] = i; });
      o.rows.forEach(function (r) { if (r[kf] in idx) base[idx[r[kf]]] = Object.assign({}, base[idx[r[kf]]], r); else base.push(Object.assign({}, r)); });
      return base;
    }
    m.MER = MER; m.cfg = cfg; m.base = new Date(MER.meta.base); m.asOf = MER.meta.asOfMinute; m.end = MER.meta.endMinute;
    m.bands = rows('cureBands').map(function (b) {
      var mm = String(b.thicknessMm).split('-');
      return { id: b.id, name: b.name, lo: +mm[0], hi: +mm[1], pressMin: +b.pressMin, eff: Math.ceil(+b.pressMin / cfg.efficiency), ppd: +b.platesPerDaylight };
    }).sort(function (a, b) { return a.lo - b.lo; });
    m.bandById = {}; m.bands.forEach(function (b) { m.bandById[b.id] = b; });
    m.bandOf = function (mm) { for (var i = 0; i < m.bands.length; i++) { var b = m.bands[i]; if (mm >= b.lo - 1e-9 && mm <= b.hi + 1e-9) return b.id; } return null; };
    m.beds = {}; Object.keys(cfg.beds).forEach(function (k) { m.beds[+k] = cfg.beds[k]; });
    var dt = {}; rows('downtime').forEach(function (d) { dt[d.pressId] = d; });
    m.presses = rows('presses').map(function (p) {
      var d = dt[p.id] || { start: cfg.pressFlags[p.id] ? cfg.pressFlags[p.id].downtimeStart : '06:00', durationMin: cfg.downtimeMin }, hm = String(d.start).split(':');
      return { id: p.id, name: p.name, bed: +p.bedFt, dl: +p.daylights, compact: !!p.compactCapable, gloss: !!p.glossHandling, special: !!p.specialResin,
               exterior: !!p.exteriorUv, downStart: (+hm[0]) * 60 + (+hm[1] || 0), downDur: +d.durationMin };
    });
    m.pressById = {}; m.presses.forEach(function (p) { m.pressById[p.id] = p; });
    m.sizes = {}; rows('sizes').forEach(function (s) { m.sizes[s.id] = { id: s.id, len: +s.lenMm, wid: +s.widMm, label: s.label }; });
    m.nest = function (sizeId, bed) { var s = m.sizes[sizeId], b = m.beds[bed]; if (!s || !b || s.len > b.lenMm || s.wid > b.widMm) return 0; return Math.min(2, Math.floor(b.lenMm / s.len)); };
    m.families = {}; rows('textureFamilies').forEach(function (f) { m.families[f.id] = f; });
    m.finishes = {}; rows('finishes').forEach(function (f) { m.finishes[f.id] = f; });
    m.decors = {}; rows('decors').forEach(function (d) { d.shade = +d.shade; m.decors[d.id] = d; });
    m.grades = {}; rows('grades').forEach(function (g) { m.grades[g.id] = g; });
    m.customers = {}; rows('customers').forEach(function (c) { m.customers[c.id] = c; });
    m.health = {}; (cfg.healthClasses || []).forEach(function (h) { m.health[h.id] = h.minHealth; });
    rows('mouldPolicy').forEach(function (r) { if (/^HEALTH-/.test(r.id)) m.health[r.id.slice(7)] = (+r.value) / 100; if (r.id === 'LIFE') m.life = +r.value; if (r.id === 'REFURB') m.refurbMin = (+r.value) * 60; });
    m.life = m.life || cfg.lifeCycles; m.refurbMin = m.refurbMin || cfg.refurbHours * 60;
    m.retireHealth = Math.min.apply(null, Object.keys(m.health).map(function (k) { return m.health[k]; }));
    var chg = {}; rows('changeover').forEach(function (c) { chg[c.id] = +c.minutes; });
    m.swapMin = chg.SWAP != null ? chg.SWAP : cfg.changeover.daylightSwapMin; m.bandMin = chg.BAND != null ? chg.BAND : cfg.changeover.bandChangeMin;
    var tm = {}; rows('thicknessMix').forEach(function (r) { tm[r.id] = +r.value; });
    m.mixTarget = tm.TARGET || cfg.thicknessMix.target; m.mixCap = tm['HARD-CAP'] || cfg.thicknessMix.hardCap;
    m.penalty = {}; rows('delayPenalty').forEach(function (r) { m.penalty[r.id] = +r.rsPerLineDay; });
    m.relWin = {}; rows('releaseWindow').forEach(function (r) { m.relWin[r.id] = +r.days; });
    if (!Object.keys(m.relWin).length && cfg.releaseWindow) m.relWin = Object.assign({}, cfg.releaseWindow);
    m.presets = {}; rows('weights').forEach(function (w) { m.presets[w.id] = w; });
    m.finishDays = cfg.finishingDays || 1;
    // SKUs: every rule is evaluated from attributes (never a SKU -> press lookup table)
    m.skus = {}; m.skuList = [];
    rows('skus').forEach(function (s) {
      var d = m.decors[s.decorId], f = m.finishes[s.finishId];
      if (!d || !f || !m.sizes[s.sizeId]) return;
      var o = { id: s.id, decorId: s.decorId, finishId: s.finishId, mm: +s.mm, sizeId: s.sizeId, gradeId: s.gradeId, sides: s.sides || 'S' };
      o.band = m.bandOf(o.mm); o.shade = d.shade; o.family = f.familyId; o.faces = o.sides === 'D' ? 2 : 1; o.lam = o.sides === 'D' ? 1 : 2;
      var fc = (m.families[o.family] || {}).healthClass || 'C';
      if (d.family === 'SOLID' && d.shade >= 8) fc = 'A'; else if (d.family === 'SOLID' && fc === 'C') fc = 'B';
      o.hc = fc; o.presses = E.eligible(m, o); o.new = !(MER.m.skus || []).some(function (x) { return x.id === s.id; });
      m.skus[o.id] = o; m.skuList.push(o);
    });
    // mould sets
    m.sets = {}; m.setList = [];
    rows('mouldSets').forEach(function (s) {
      var o = { id: s.id, finishId: s.finishId, bed: +s.bedFt, plates: +s.plates, limit: +s.lifeLimit || m.life, counter0: +s.counterAtBase || 0,
                shade0: 1, refurb0: (+s.refurbUntilHours || 0) * 60, dedicatedTo: s.dedicatedTo || null, pressLock: s.pressLock || null };
      var raw = (MER.m.mouldSets || []).filter(function (x) { return x.id === s.id; })[0];
      m.sets[o.id] = o; m.setList.push(o);
    });
    // dedicated (customer, finish) -> set, only where the lock press can run that texture's work
    m.dedicated = {}; m.setList.forEach(function (s) { if (s.dedicatedTo) m.dedicated[s.dedicatedTo + '|' + s.finishId] = s; });
    m.setsByKey = {}; m.setList.forEach(function (s) { var k = s.finishId + '|' + s.bed; (m.setsByKey[k] = m.setsByKey[k] || []).push(s); });
    // demand
    var base = m.base;
    m.orders = {}; (MER.orders || []).forEach(function (o) { m.orders[o.id] = o; });
    m.lineList = [];
    (MER.lines || []).forEach(function (l) { m.lineList.push(E.mkLine(m, l, m.orders[l.orderId])); });
    m.norms = rows('stockNorms').filter(function (n) { return m.skus[n.skuId]; }).map(function (n) { return { id: n.id, skuId: n.skuId, norm: +n.normSheets, use: +n.usePerDay, onHand0: +n.onHandAtBase }; });
    m.normBySku = {}; m.norms.forEach(function (n) { m.normBySku[n.skuId] = n; });
    m.paper0 = {}; rows('papers').forEach(function (p) { m.paper0[p.decorId] = +p.stockAtBase || 0; });
    m.pos = (MER.pos || []).map(function (p) { return { id: p.id, decorId: p.decorId, sheets: +p.sheets, eta: minOf(p.eta, base), supplierId: p.supplierId }; }).sort(function (a, b) { return a.eta - b.eta || (a.id < b.id ? -1 : 1); });
    var ev = MER.events || {};
    m.breakdowns = (ev.breakdowns || []).map(function (b) { return { id: b.id, press: b.pressId, s: minOf(b.start, base), e: minOf(b.start, base) + b.durMin, reason: b.reason, category: b.category }; });
    m.overrun = ev.overrunRule || { share: 0 }; m.qcRule = ev.qcRule || { share: 0 };
    m.cancels = (ev.cancellations || []).map(function (c) { return { lineId: c.lineId, at: minOf(c.at, base), reason: c.reason }; });
    m.rejects = (ev.rejections || []).map(function (r) { return { lineId: r.lineId, at: minOf(r.at, base), sheets: r.sheets, reason: r.reason }; });
    return m;
  };

  // a line is released to the presses at max(order date, due - release window of its class): nobody presses a container order a month early
  E.mkLine = function (m, l, o) {
    o = o || {};
    var ord = Math.max(0, minOf(o.orderDate || l.orderDate, m.base)), due = minOf(o.due || l.due, m.base), w = (m.relWin || {})[l.cls];
    return decorate(m, { id: l.id, orderId: l.orderId, skuId: l.skuId, qty: +l.qty, margin: +l.margin, cls: l.cls, cust: l.customerId || l.cust,
             ord: ord, rel: w != null ? Math.max(ord, due - w * 1440) : ord, due: due, cutPlan: l.cutPlan || null, rush: !!l.rush });
  };
  function decorate(m, l) {   // copy the SKU's attributes onto the line once: the scheduler's hot loops never look them up
    var s = m.skus[l.skuId]; if (!s) return l;
    l.fin = s.finishId; l.band = s.band; l.shade = s.shade; l.mm = s.mm; l.dec = s.decorId; l.faces = s.faces; l.lam = s.lam; l.size = s.sizeId;
    l.hc = E.lineClass(s, l.cls); l.minH = m.health[l.hc] || 0;
    var d = m.dedicated[(l.cust || '') + '|' + s.finishId];
    l.ded = d && s.presses.indexOf(d.pressLock) >= 0 ? d.id : null;
    return l;
  }

  // directional fit (product length <= bed length, nesting when two books fit) + attribute rules (req 1a, 1d)
  E.eligible = function (m, s) {
    return m.presses.filter(function (p) {
      if (!m.nest(s.sizeId, p.bed)) return false;
      if (s.mm >= 2 && !p.compact) return false;
      if (s.family === 'GLS' && !p.gloss) return false;
      if ((s.gradeId === 'FR' || s.gradeId === 'CR') && !p.special) return false;
      if (s.gradeId === 'EX' && !p.exterior) return false;
      return !!m.bandOf(s.mm);
    }).map(function (p) { return p.id; });
  };
  E.whyNot = function (m, s, p) {   // plain-language reason a press cannot run a SKU (Eligibility views)
    var out = [];
    if (!m.nest(s.sizeId, p.bed)) out.push('size ' + m.sizes[s.sizeId].label + ' is longer than a ' + p.bed + ' ft bed');
    if (s.mm >= 2 && !p.compact) out.push('compact needs a deep-daylight press');
    if (s.family === 'GLS' && !p.gloss) out.push('gloss plates need the plate-handling rig');
    if ((s.gradeId === 'FR' || s.gradeId === 'CR') && !p.special) out.push(s.gradeId + ' needs the special resin system');
    if (s.gradeId === 'EX' && !p.exterior) out.push('exterior grade needs the UV overlay line');
    return out;
  };
  E.sheetsPerCycle = function (m, s, p) { var b = m.bandById[s.band]; return p.dl * b.ppd * s.lam * m.nest(s.sizeId, p.bed); };
  E.lineClass = function (s, cls) { return cls === 'EXPORT' ? 'A' : s.hc; };

  // =====================================================================================================================
  // STATE — everything the plant knows at a moment: press mounts, mould counters, balance-to-produce, stock, paper
  // =====================================================================================================================
  function newState(m) {
    var st = { presses: {}, sets: {}, lines: {}, lineOrder: [], byPress: {}, pend: [], relIdx: 0, norm: {}, normT: 0, paper: {}, pos: m.pos, poIdx: 0, act: {}, actVer: 0 };
    m.presses.forEach(function (p) { var rows = []; for (var i = 0; i < p.dl; i++) rows.push({ set: null, fin: null }); st.presses[p.id] = { free: 0, band: null, rows: rows, dayNo: {} }; st.byPress[p.id] = []; });
    m.setList.forEach(function (s) { st.sets[s.id] = { counter: s.counter0, shade: s.shade0, refurbUntil: s.refurb0, on: null, refurbs: [] }; });
    m.lineList.forEach(function (l) { addLine(m, st, l); });
    m.norms.forEach(function (n) {
      st.norm[n.skuId] = { onHand: n.onHand0, pendingIn: [], line: 'NORM/' + n.skuId };
      addLine(m, st, decorate(m, { id: 'NORM/' + n.skuId, orderId: null, skuId: n.skuId, qty: 0, margin: 200, cls: 'NORM', cust: null, rel: 0, due: m.end + 1440 * 30, norm: true }));
    });
    sortPend(st);
    Object.keys(m.paper0).forEach(function (k) { st.paper[k] = m.paper0[k]; });
    return st;
  }
  function addLine(m, st, l) {
    st.lines[l.id] = { l: l, rem: 0, released: false, alloc: 0, down: 0, cancelled: 0, rejected: 0, planH: 0, planP: 0, cyc: [], firstStart: null, lastEnd: null, paperWait: null, normPos: 1 };
    st.lineOrder.push(l.id);
    if (!l.norm) st.pend.push([l.rel, l.id]);
    var s = m.skus[l.skuId];
    if (s) s.presses.forEach(function (pid) { st.byPress[pid].push(l.id); });
  }
  // Derived caches live in a non-enumerable property so JSON cloning of the state never copies them.
  function cache(st) {
    if (!st._c) Object.defineProperty(st, '_c', { value: {}, enumerable: false, writable: true });
    var c = st._c, n = st.lineOrder.length;
    if (!c.arr || c.arr.length !== n) {
      c.arr = st.lineOrder.map(function (id, i) { var L = st.lines[id]; L.ix = i; return L; });
      c.byPress = {}; Object.keys(st.byPress).forEach(function (pid) { c.byPress[pid] = st.byPress[pid].map(function (id) { return st.lines[id]; }); });
      var cap = n + 64; c.remW = new Float64Array(cap); c.remG = new Int32Array(cap); c.act = {}; c.gen = 0;
    }
    return c;
  }
  function sortPend(st) { var done = st.pend.slice(0, st.relIdx), rest = st.pend.slice(st.relIdx).sort(function (a, b) { return a[0] - b[0] || (a[1] < b[1] ? -1 : 1); }); st.pend = done.concat(rest); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  // =====================================================================================================================
  // SIMULATION
  // =====================================================================================================================
  function blocked(m, p, t, dur) {   // earliest start >= t where [start, start+dur) avoids planned downtime and breakdowns
    for (var guard = 0; guard < 20; guard++) {
      var moved = false, day = Math.floor(t / 1440);
      for (var d = day - 1; d <= day + 1; d++) { var ws = d * 1440 + p.downStart, we = ws + p.downDur; if (t < we && t + dur > ws) { t = we; moved = true; } }
      for (var i = 0; i < m.breakdowns.length; i++) { var b = m.breakdowns[i]; if (b.press === p.id && t < b.e && t + dur > b.s) { t = b.e; moved = true; } }
      if (!moved) return t;
    }
    return t;
  }

  function advance(m, st, t, ctx) {
    // order releases; make-to-stock SKUs are served from free FG stock first (BTP = ordered - good produced - allocated FG stock)
    while (st.relIdx < st.pend.length && st.pend[st.relIdx][0] <= t) {
      var L = st.lines[st.pend[st.relIdx++][1]];
      if (L.released) continue;
      L.released = true; L.rem = L.l.qty - L.cancelled;
      var n = st.norm[L.l.skuId];
      if (n && n.onHand >= 1) { var a = Math.min(L.rem, Math.floor(n.onHand)); n.onHand -= a; L.alloc += a; L.rem -= a; }
    }
    while (st.poIdx < st.pos.length && st.pos[st.poIdx].eta <= t) { var po = st.pos[st.poIdx++]; st.paper[po.decorId] = (st.paper[po.decorId] || 0) + po.sheets; }
    for (var i = 0; i < ctx.cancels.length; i++) { var c = ctx.cancels[i]; if (!c.done && c.at <= t && st.lines[c.lineId]) { var Lc = st.lines[c.lineId]; Lc.cancelled += Math.max(0, Lc.rem); Lc.rem = 0; c.done = true; } }
    for (var j = 0; j < ctx.rejects.length; j++) { var r = ctx.rejects[j]; if (!r.done && r.at <= t && st.lines[r.lineId]) { var Lr = st.lines[r.lineId]; Lr.rejected += r.sheets; Lr.rem += r.sheets; r.done = true; st.actVer++; } }
    // early refurbishment (req 4a): every 6 h, an idle set too worn for waiting class-A work (export grade, gloss, dark solids)
    // is sent for refurbishment before it is exhausted — one set of a texture at a time, so the texture keeps running
    if (Math.floor(t / 360) > Math.floor((st.refT || 0) / 360)) {
      st.refT = t;
      var needA = {}, inRef = {};
      for (var a = 0; a < st.lineOrder.length; a++) {
        var La = st.lines[st.lineOrder[a]]; if (!La.released || La.rem <= 0) continue;
        var ska = m.skus[La.l.skuId]; if (ska && E.lineClass(ska, La.l.cls) === 'A') needA[ska.finishId] = 1;
      }
      m.setList.forEach(function (x) { if (st.sets[x.id].refurbUntil > t) inRef[x.finishId + '|' + x.bed] = 1; });
      m.setList.forEach(function (x) {
        var S = st.sets[x.id], key = x.finishId + '|' + x.bed;
        if (S.on || S.refurbUntil > t || !needA[x.finishId] || inRef[key]) return;
        if (1 - S.counter / x.limit >= (m.health.A || 0.5) || S.counter < x.limit * 0.45) return;
        S.refurbs.push({ from: t, to: t + m.refurbMin, counter: S.counter, cycle: 'early', early: true });
        S.refurbUntil = t + m.refurbMin; S.counter = 0; S.shade = 0; inRef[key] = 1;
      });
    }
    // stock norms: hourly consumption; replenish to norm once below two thirds (yellow)
    if (Math.floor(t / 60) > Math.floor(st.normT / 60)) {
      var days = (t - st.normT) / 1440;
      for (var k = 0; k < m.norms.length; k++) {
        var nn = m.norms[k], s = st.norm[nn.skuId], pin = 0;
        while (s.pendingIn.length && s.pendingIn[0][0] <= t) { s.onHand += s.pendingIn[0][1]; s.pendingIn.shift(); }
        s.onHand -= nn.use * days;
        for (var q = 0; q < s.pendingIn.length; q++) pin += s.pendingIn[q][1];
        var pos = s.onHand + pin, NL = st.lines[s.line];
        NL.released = true;
        if (pos < nn.norm * 2 / 3) NL.rem = Math.max(NL.rem, Math.ceil((nn.norm - pos) / 10) * 10); else if (pos >= nn.norm) NL.rem = 0;
        NL.normPos = pos / nn.norm;
      }
      st.normT = t;
    }
  }

  function normBandScore(pos) { return pos <= 0 ? 0.9 : pos < 1 / 3 ? 0.6 : pos < 2 / 3 ? 0.25 : 0; }

  // priority — 'sequence' = Merino today (export -> committed domestic by date -> open domestic -> norms, lexicographic);
  //            'weighted' = the five objectives in one score. Urgency gates everything: a line with a week to spare scores
  //            ~0 on dates, and its margin counts for less the further off it is — so profit separates urgent lines instead of
  //            letting a far-off export push a committed order late. Lateness adds the delay penalty (Rs per line-day).
  function score(m, L, t, W) {
    var l = L.l;
    if (W.mode === 'sequence') return -(CLS_RANK[l.cls] * 1e7 + (l.cls === 'NORM' ? L.normPos * 1e5 : l.due / 10)) + (l.rush ? 5e7 : 0);
    var slack = (l.due - t) / 1440 - m.finishDays - 0.5;   // days to spare after pressing + finishing
    var committed = l.cls === 'EXPORT' || l.cls === 'DOM_COMMITTED';
    // a committed date matters from the day it is confirmed (standing 1.2 — above any stock-norm or open order), then
    // urgency ramps over its last two weeks, and lateness adds more
    var U = committed ? 1.2 + clamp(1 - slack / 14, 0, 1) + (slack < 0 ? Math.min(1, -slack / 5) : 0) : l.cls === 'DOM_OPEN' ? 0.3 * clamp(1 - slack / 20, 0, 1) : 0;
    var near = !committed ? 0.2 : clamp(1 - slack / 14, 0.2, 1);
    var P = (l.cls === 'NORM' ? 0.35 : clamp(l.margin / 520, 0.3, 1.2)) * near;
    var N = l.cls === 'NORM' ? normBandScore(L.normPos) : 0;
    var Lp = slack < 0 ? W.delayScale * (m.penalty[l.cls] || 0) * (-slack) / 6000 : 0;
    return (W.profit * P + W.dates * (U + Lp) + W.norms * N) / 100 + (l.rush ? 5 : 0);
  }

  // the same score, broken into its parts, for the Load Builder's "why this slot" panel
  E.scoreParts = function (m, l, t, W, normPos) {
    if (W.mode === 'sequence') return { mode: 'sequence', cls: l.cls, due: l.due, text: 'Fixed sequence: class ' + (CLS_RANK[l.cls] + 1) + ' of 4 (export → committed domestic → open domestic → stock norms), then earliest due date' };
    var slack = (l.due - t) / 1440 - m.finishDays - 0.5, committed = l.cls === 'EXPORT' || l.cls === 'DOM_COMMITTED';
    var U = committed ? 1.2 + clamp(1 - slack / 14, 0, 1) + (slack < 0 ? Math.min(1, -slack / 5) : 0) : l.cls === 'DOM_OPEN' ? 0.3 * clamp(1 - slack / 20, 0, 1) : 0;
    var near = !committed ? 0.2 : clamp(1 - slack / 14, 0.2, 1), P = (l.cls === 'NORM' ? 0.35 : clamp(l.margin / 520, 0.3, 1.2)) * near;
    var N = l.cls === 'NORM' ? normBandScore(normPos == null ? 0.5 : normPos) : 0, Lp = slack < 0 ? W.delayScale * (m.penalty[l.cls] || 0) * (-slack) / 6000 : 0;
    var parts = { profit: W.profit * P / 100, dates: W.dates * U / 100, delay: W.dates * Lp / 100, norms: W.norms * N / 100 };
    return { mode: 'weighted', slackDays: slack, parts: parts, total: parts.profit + parts.dates + parts.delay + parts.norms + (l.rush ? 5 : 0), rush: !!l.rush };
  };

  function setUsable(m, st, s, p, t) {
    var S = st.sets[s.id];
    return S.refurbUntil <= t && (!S.on || S.on === p.id) && (!s.pressLock || s.pressLock === p.id) && s.bed === p.bed;
  }

  // One press cycle = up to D daylights, each one texture from one mould set, all in one cure band.
  // Lines are taken in priority order: a line fills a daylight of its texture already open in this load, or opens one
  // (on the set already mounted in the press if there is one — no changeover — else on a free set of that texture).
  // Both modes first keep mounted textures that still have work: 'sequence' (Merino today) keeps a texture when it appears
  // in the next lines of the fixed priority list, as a sensible manual planner would; 'weighted' keeps a campaign unless
  // something more urgent than the saved changeover is waiting. A top-up pass then fills spare plates, and daylights that
  // are still idle reset dirty mould sets that have lighter work waiting (a cleaning pass that costs no output).
  function activeLines(st, p, bucket) {
    var c = cache(st), A = c.act[p.id];
    if (A && A.b === bucket && A.v === st.actVer) return A.ls;
    var all = c.byPress[p.id], out = [];
    for (var i = 0; i < all.length; i++) { var L = all[i]; if (L.l.norm || !L.released || L.rem > 0) out.push(L); }
    c.act[p.id] = { b: bucket, v: st.actVer, ls: out };
    return out;
  }

  function buildCycle(m, st, p, t, W, phase) {
    var P = st.presses[p.id], weighted = W.mode !== 'sequence', bucket = Math.floor(t / 360), ids = activeLines(st, p, bucket), C = cache(st), gen = ++C.gen;
    var swapPen = W.changeover / 100 * 0.45, mountedFree = {}, finInfo = {};
    for (var q = 0; q < P.rows.length; q++) { var ms = P.rows[q].set; if (ms) mountedFree[ms] = (mountedFree[ms] || 0) + 1; }
    function fi(fin) {
      var x = finInfo[fin]; if (x) return x;
      var sets = (m.setsByKey[fin + '|' + p.bed] || []).filter(function (s) { return setUsable(m, st, s, p, t); }), bestH = -1, mounted = false;
      for (var i = 0; i < sets.length; i++) { var h = 1 - st.sets[sets[i].id].counter / sets[i].limit; if (h > bestH) bestH = h; if (mountedFree[sets[i].id]) mounted = true; }
      return (finInfo[fin] = { sets: sets, bestH: bestH, mounted: mounted });
    }
    var cands = [];
    for (var i = 0; i < ids.length; i++) {
      var L = ids[i], l = L.l;
      if (!L.released || L.rem <= 0) continue;
      if ((st.paper[l.dec] || 0) < l.faces) { if (L.paperWait == null && t >= l.rel) L.paperWait = t; continue; }
      var F = fi(l.fin);
      if (!F.sets.length) continue;
      if (l.ded) { var ds = m.sets[l.ded]; if (ds.pressLock !== p.id || F.sets.indexOf(ds) < 0 || 1 - st.sets[ds.id].counter / ds.limit < l.minH) continue; }
      else if (F.bestH < l.minH) continue;
      if (L._b !== bucket || L._w !== W.key) { L._sc = score(m, L, t, W); L._b = bucket; L._w = W.key; }
      L._eff = weighted && !F.mounted ? L._sc - swapPen : L._sc;
      cands.push(L);
    }
    if (!cands.length) return null;
    // equal scores: earlier due date first, then first come first served (E.tieSeed lets the robustness test scramble ties)
    var tb = E.tieSeed | 0;
    cands.sort(function (a, b) {
      return b._eff - a._eff || (tb ? ((a.ix * 2654435761 + tb) >>> 0) % 1000003 - ((b.ix * 2654435761 + tb) >>> 0) % 1000003
                                    : a.l.due - b.l.due || a.l.rel - b.l.rel || a.ix - b.ix);
    });
    // cure band for the whole load
    var band, urgentBy = t + (4 + m.finishDays) * 1440;
    function isUrgent(L) { return (L.l.cls === 'EXPORT' || L.l.cls === 'DOM_COMMITTED') && L.l.due <= urgentBy; }
    if (!weighted || isUrgent(cands[0])) band = cands[0].l.band;   // the most urgent line never waits for a band change
    else {
      // a band is worth what one full press load of its best work is worth: score x sheets until the press is full, so a
      // band with a few urgent lines beats a band with many relaxed ones, and a band change still costs its changeover
      var bv = {}, cap = {}, best = -1e9;
      for (var c1 = 0; c1 < cands.length; c1++) {
        var Lc = cands[c1], bb = Lc.l.band, capB = cap[bb] != null ? cap[bb] : (cap[bb] = p.dl * m.bandById[bb].ppd * 2);
        var take = Math.min(Lc.rem, capB); if (take <= 0) continue;
        bv[bb] = (bv[bb] || 0) + Lc._eff * take; cap[bb] = capB - take;
      }
      Object.keys(bv).sort().forEach(function (b) {
        var v = bv[b] / (p.dl * m.bandById[b].ppd * 2) - (P.band && b !== P.band ? W.changeover / 100 * 0.3 : 0);
        if (v > best) { best = v; band = b; }
      });
    }
    var BD = m.bandById[band], ppd = BD.ppd, pap = {}, thick = {}, nThick = 0, rows = [], openByFin = {}, rowsBySet = {}, cleanSets = {}, owner = {}, fullRows = 0;
    var remW = C.remW, remG = C.remG;   // working balance per line for this load: generation-stamped, never cleared
    function remOf(L) { return remG[L.ix] === gen ? remW[L.ix] : L.rem; }
    function setRem(L, v) { remG[L.ix] = gen; remW[L.ix] = v; }
    function papOf(d) { var x = pap[d]; return x != null ? x : (st.paper[d] || 0); }
    function capRows(set) { return Math.floor(set.plates / ppd); }
    function ownerWaiting(set) {
      if (owner[set.id] == null) owner[set.id] = cands.some(function (L) { return L.l.cust === set.dedicatedTo && L.l.fin === set.finishId && remOf(L) > 0; });
      return owner[set.id];
    }
    function okOnSet(L, set) {   // plate wear (4a) and customer dedication (1c) for this line on this set
      var l = L.l;
      if (1 - st.sets[set.id].counter / set.limit < l.minH) return false;
      if (l.ded && l.ded !== set.id) return false;
      if (set.dedicatedTo && set.dedicatedTo !== l.cust && ownerWaiting(set)) return false;
      return true;
    }
    function openRow(set, why, clean) {
      if (rows.length >= p.dl || (rowsBySet[set.id] || 0) >= capRows(set)) return null;
      var free = (mountedFree[set.id] || 0) > 0; if (free) mountedFree[set.id]--;
      var rw = { set: set, pl: [], used: 0, clean: !!clean, free: free, why: why, shade: 0, floor: st.sets[set.id].shade };
      rows.push(rw); rowsBySet[set.id] = (rowsBySet[set.id] || 0) + 1;
      if (!clean) (openByFin[set.finishId] = openByFin[set.finishId] || []).push(rw); else fullRows++;
      return rw;
    }
    function pickSet(L) {             // mounted in this press first (no changeover), then the freshest free set
      var l = L.l, sets = fi(l.fin).sets.filter(function (x) { return okOnSet(L, x) && (rowsBySet[x.id] || 0) < capRows(x) && !cleanSets[x.id]; });
      var ok = sets.filter(function (x) { return l.shade >= st.sets[x.id].shade; });
      ok.sort(function (a, b) { return ((mountedFree[b.id] || 0) > 0) - ((mountedFree[a.id] || 0) > 0) || st.sets[a.id].counter - st.sets[b.id].counter || (a.id < b.id ? -1 : 1); });
      if (ok.length) return { set: ok[0] };
      sets.sort(function (a, b) { return ((mountedFree[b.id] || 0) > 0) - ((mountedFree[a.id] || 0) > 0) || (a.id < b.id ? -1 : 1); });
      return sets.length ? { set: sets[0], clean: true } : null;   // no set is light enough: clean one (in this press first)
    }
    var byFin = {}, byFinShade = {};
    for (var ci = 0; ci < cands.length; ci++) { var Lk = cands[ci]; Lk._rank = ci + 1; if (Lk.l.band === band) { var fk = Lk.l.fin; (byFin[fk] || (byFin[fk] = [])).push(Lk); } }
    var fwk = {};   // released work of a texture in this band, sheets (for the minimum-campaign rule)
    function finWork(f) { if (fwk[f] == null) { var x = 0, ls = byFin[f] || []; for (var i = 0; i < ls.length; i++) x += remOf(ls[i]); fwk[f] = x; } return fwk[f]; }
    function shadeList(f) { if (!byFinShade[f]) byFinShade[f] = (byFin[f] || []).slice().sort(function (a, b) { return a.l.shade - b.l.shade || b._sc - a._sc || a.ix - b.ix; }); return byFinShade[f]; }
    function place1(L, rw, cap) {      // put one line on one open daylight
      var l = L.l, id = l.id, r = remOf(L), pp = papOf(l.dec);
      if (rw.clean || rw.used >= ppd || r <= 0 || pp < l.faces || l.shade < rw.floor || (!thick[l.mm] && nThick >= cap) || !okOnSet(L, rw.set)) return 0;
      var per = l.lam * m.nest(l.size, p.bed), placed = 0;
      while (rw.used < ppd && r > 0 && pp >= l.faces) {
        var n = Math.min(per, r, Math.floor(pp / l.faces)); if (n <= 0) break;
        rw.pl.push([id, n]); rw.used++; r -= n; pp -= n * l.faces; placed += n; if (l.shade > rw.shade) rw.shade = l.shade;
        if (rw.used >= ppd) fullRows++;
      }
      setRem(L, r); pap[l.dec] = pp;
      if (placed && !thick[l.mm]) { thick[l.mm] = 1; nThick++; }
      return placed;
    }
    // fill a daylight light-to-dark: the trigger line, then same-texture lines no darker than it; spare plates never darken a set beyond what its trigger needed (a darker filler would block lighter committed work
    // next cycle); only a daylight that is still mostly empty climbs to the next-lightest shades
    function fillRow(rw, trigger, cap) {
      var f = rw.set.finishId, list = byFin[f] || [], ceil = Math.max(rw.floor, rw.shade, trigger ? trigger.l.shade : 0);
      if (trigger) place1(trigger, rw, cap);
      for (var i = 0; i < list.length && rw.used < ppd; i++) if (list[i].l.shade <= ceil) place1(list[i], rw, cap);
      if (rw.used * 2 >= ppd) return;
      var asc = shadeList(f);
      for (var j = 0; j < asc.length && rw.used < ppd; j++) place1(asc[j], rw, cap);
    }
    // keep mounted textures that still have work
    // both modes look ahead through the next 4 x D lines: a mounted texture that appears there keeps its daylight
    var look = Math.min(cands.length, p.dl * 4), want = {};
    for (var w1 = 0; w1 < look; w1++) if (cands[w1].l.band === band && !want[cands[w1].l.fin]) want[cands[w1].l.fin] = cands[w1];
    // weighted also continues a campaign whose best work is worth a share of the top line's score — the share falls as the
    // changeover weight rises (Utilisation-first keeps almost every campaign; OTIF-first breaks them for urgent work)
    var keepFrac = weighted ? Math.max(0, 0.75 - W.changeover / 100 * 2.5) : 1, topSc = cands[0]._sc;
    function pass(capIn, allowOpen, onlyUrgent) {
      for (var i = 0; i < cands.length; i++) {
        // thickness mix is a soft objective: a committed line due within ~4 days may add a thickness, never beyond the hard cap
        var L = cands[i], l = L.l, urg = isUrgent(L), cap = weighted && urg ? m.mixCap : capIn;
        if (onlyUrgent && !urg) continue;
        if (l.band !== band || remOf(L) <= 0 || (!thick[l.mm] && nThick >= cap)) continue;
        var ol = openByFin[l.fin] || [];
        for (var o = 0; o < ol.length && remOf(L) > 0; o++) place1(L, ol[o], cap);
        while (remOf(L) > 0 && allowOpen && rows.length < p.dl) {
          var pick = pickSet(L); if (!pick) break;
          if (pick.clean) {
            if (weighted && L._sc < 1.0) break;               // weighted: only an urgent lighter line justifies losing a daylight to cleaning
            cleanSets[pick.set.id] = 1;
            openRow(pick.set, weighted ? 'cleaning pass — ' + l.id + ' is lighter than the set\'s last shade and is due'
                                       : 'cleaning pass — next line in the fixed sequence (' + l.id + ') is lighter than the set\'s last shade', true);
            break;
          }
          // a changeover must pay for itself: a texture only gets a NEW daylight (a plate swap) when it has released work for at
          // least (changeover weight / 2) daylight-loads, unless the line is urgent — the minimum campaign grows with the weight
          if (weighted && !urg && !((mountedFree[pick.set.id] || 0) > 0) && finWork(l.fin) < W.changeover / 2 * ppd * l.lam * m.nest(l.size, p.bed)) break;
          var nrw = openRow(pick.set, weighted ? 'opened for ' + l.id + ' (score ' + L._sc.toFixed(2) + ')' : 'opened for ' + l.id + ' — rank ' + L._rank + ' in the fixed sequence', false);
          if (!nrw) break;
          var before = remOf(L); fillRow(nrw, L, cap); if (remOf(L) === before) break;
        }
        if (rows.length >= p.dl && fullRows >= rows.length) break;
      }
    }
    var keptRow = {};
    function keepMounted(campaigns) {
    P.rows.forEach(function (prow, pr) {
      if (!prow.set || rows.length >= p.dl || keptRow[pr]) return;
      var set = m.sets[prow.set]; if (!set || !setUsable(m, st, set, p, t) || (rowsBySet[set.id] || 0) >= capRows(set)) return;
      var bestL = null, fl = st.sets[set.id].shade, asc = shadeList(set.finishId);
      var lead = want[set.finishId], bestFin = (byFin[set.finishId] || [])[0];
      if (campaigns ? lead || !(weighted && bestFin && bestFin._sc >= keepFrac * topSc) : !lead) return;
      for (var k = 0; k < asc.length && !bestL; k++) {
        var L2 = asc[k], l2 = L2.l;
        if (remOf(L2) <= 0 || l2.shade < fl || !okOnSet(L2, set) || (!thick[l2.mm] && nThick >= (weighted ? m.mixTarget : m.mixCap))) continue;
        if (weighted || L2._rank <= look * 3) bestL = L2;
      }
      if (!bestL) return;
      var krw = openRow(set, lead ? 'kept the mounted texture — ' + lead.l.id + ' (' + (weighted ? 'score ' + lead._sc.toFixed(2) : 'rank ' + lead._rank) + ') is among the next ' + look + ' lines' + (weighted ? '' : ' of the fixed sequence')
                                  : 'kept the mounted texture campaign — its best work (score ' + bestFin._sc.toFixed(2) + ') is worth more than the changeover', false);
      if (krw) { keptRow[pr] = 1; fillRow(krw, bestL, weighted ? m.mixTarget : m.mixCap); }
    });
    }
    keepMounted(false);                                              // textures the next 4 x D lines need stay mounted
    if (weighted) pass(m.mixCap, true, true);                        // urgent committed work gets daylights before any campaign
    if (weighted) keepMounted(true);                                 // then campaigns worth more than their changeover
    pass(weighted ? m.mixTarget : m.mixCap, true);                   // priority order opens daylights
    if (weighted && rows.length < p.dl) pass(m.mixCap, true);        // weighted: a third thickness only if daylights are still idle
    rows.forEach(function (rw) { if (!rw.clean && rw.used < ppd) fillRow(rw, null, weighted ? Math.max(nThick, m.mixTarget) : m.mixCap); });   // top-up, light to dark
    if (rows.length < p.dl) {        // idle daylights reset dirty sets that have lighter work waiting — a cleaning pass that costs no output
      var wait = {};
      cands.forEach(function (L) {
        var l = L.l; if (l.band !== band || remOf(L) <= 0) return;
        fi(l.fin).sets.forEach(function (x) { if (!cleanSets[x.id] && !rowsBySet[x.id] && l.shade < st.sets[x.id].shade && okOnSet(L, x)) wait[x.id] = (wait[x.id] || 0) + L._sc; });
      });
      Object.keys(wait).sort(function (a, b) { return wait[b] - wait[a] || (a < b ? -1 : 1); }).forEach(function (sid) {
        if (rows.length >= p.dl) return;
        cleanSets[sid] = 1; openRow(m.sets[sid], 'cleaning pass in an idle daylight — lighter shades are waiting on this set', true);
      });
    }
    if (!rows.length) return null;
    // physical daylights: a set already mounted stays in its daylight; the rest take the remaining ones
    var slot = new Array(p.dl);
    rows.forEach(function (rw) { if (!rw.free) return; for (var r = 0; r < p.dl; r++) if (!slot[r] && P.rows[r].set === rw.set.id) { slot[r] = rw; return; } rw.free = false; });
    var keep = {}; rows.forEach(function (rw) { keep[rw.set.id] = 1; });
    var order = []; for (var r2 = 0; r2 < p.dl; r2++) order.push(r2);
    order.sort(function (a, b) { return (keep[P.rows[a].set] ? 1 : 0) - (keep[P.rows[b].set] ? 1 : 0) || a - b; });
    rows.forEach(function (rw) { if (rw.free) return; for (var k = 0; k < order.length; k++) if (!slot[order[k]]) { slot[order[k]] = rw; return; } });
    var outRows = [], sheets = 0, plates = 0, swaps = 0;
    for (var r3 = 0; r3 < p.dl; r3++) {
      var c = slot[r3];
      if (!c) { outRows.push({ s: null, f: null, clean: false, swap: false, pl: [], why: 'idle — no placeable work of this cure band for another daylight' }); continue; }
      var swap = P.rows[r3].set !== c.set.id; if (swap) swaps++;
      for (var z = 0; z < c.pl.length; z++) sheets += c.pl[z][1];
      plates += c.pl.length;
      outRows.push({ s: c.set.id, f: c.set.finishId, clean: c.clean, swap: swap, pl: c.pl, why: c.why });
    }
    if (!sheets && !outRows.some(function (rw) { return rw.clean; })) return null;
    var bandChg = P.band && P.band !== band ? 1 : 0;
    return { band: band, rows: outRows, sheets: sheets, platesUsed: plates, plates: p.dl * ppd, swaps: swaps, bandChg: bandChg,
             chg: swaps * m.swapMin + bandChg * m.bandMin, thick: Object.keys(thick).map(Number).sort(function (a, b) { return a - b; }), phase: phase };
  }

  function commit(m, st, p, c, start, ctx) {
    var P = st.presses[p.id], BD = m.bandById[c.band], over = 0, cid = p.id + '-' + ctx.seq[p.id]++, idx = ctx.offset + ctx.cycles.length;
    if (c.phase === 'H' && hash01('ov|' + cid) < (m.overrun.share || 0)) over = Math.round((m.overrun.minMin || 6) + hash01('ovm|' + cid) * ((m.overrun.maxMin || 18) - (m.overrun.minMin || 6)));
    var s0 = start + c.chg, end = s0 + BD.eff + over, day = Math.floor(s0 / 1440);
    P.dayNo[day] = (P.dayNo[day] || 0) + 1;
    c.id = cid; c.p = p.id; c.start = start; c.s0 = s0; c.end = end; c.over = over; c.day = day; c.no = P.dayNo[day];
    var usedSets = {};
    c.rows.forEach(function (rw, r) {
      var cur = P.rows[r].set;
      if (!rw.s) {                                  // idle daylight: plates stay parked for two cycles, then go back to the store
        if (cur) { P.rows[r].idle = (P.rows[r].idle || 0) + 1; if (P.rows[r].idle > 2) releaseRow(st, p, r); }
        return;
      }
      if (cur && cur !== rw.s) releaseRow(st, p, r);
      P.rows[r] = { set: rw.s, fin: rw.f, idle: 0 }; st.sets[rw.s].on = p.id;
      var u = usedSets[rw.s] = usedSets[rw.s] || { shade: 0, clean: false }; if (rw.clean) u.clean = true;
      rw.pl.forEach(function (x) {
        var L = st.lines[x[0]], l = L.l;
        L.rem -= x[1]; if (c.phase === 'H') L.planH += x[1]; else L.planP += x[1];
        if (L.cyc[L.cyc.length - 1] !== idx) L.cyc.push(idx);    // one entry per cycle (a line may fill several plates of it)
        if (L.firstStart == null) L.firstStart = s0; L.lastEnd = end;
        st.paper[l.dec] -= x[1] * l.faces;
        if (l.shade > u.shade) u.shade = l.shade;
        if (L.l.norm) st.norm[L.l.skuId].pendingIn.push([end + m.finishDays * 1440, x[1]]);
      });
    });
    Object.keys(usedSets).sort().forEach(function (sid) {    // mould life + light-to-dark ladder; refurbish before exhaustion (4a, 4b)
      var S = st.sets[sid], set = m.sets[sid];
      S.counter += 1;
      S.shade = usedSets[sid].clean ? 0 : Math.max(S.shade, usedSets[sid].shade);
      if (1 - S.counter / set.limit < m.retireHealth) {
        S.refurbs.push({ from: end, to: end + m.refurbMin, counter: S.counter, cycle: cid, press: p.id });
        S.refurbUntil = end + m.refurbMin; S.counter = 0; S.shade = 0; S.on = null;
        P.rows.forEach(function (rw) { if (rw.set === sid) { rw.set = null; rw.fin = null; } });
      }
    });
    c.setCounters = {}; Object.keys(usedSets).forEach(function (sid) { c.setCounters[sid] = st.sets[sid].counter; });
    if (c.phase === 'H' && m.qcRule.share) {                  // QC downgrades in history: part of a daylight goes B-grade -> BTP grows back
      c.rows.forEach(function (rw, r) {
        if (!rw.pl.length || hash01('qc|' + cid + '|' + r) >= m.qcRule.share) return;
        var x = rw.pl[0], L = st.lines[x[0]], lo = m.qcRule.minShare || 0.15, hi = m.qcRule.maxShare || 0.6;
        var n = Math.max(1, Math.round(x[1] * (lo + hash01('qcs|' + cid + r) * (hi - lo))));
        L.down += n; if (!L.l.norm) { L.rem += n; st.actVer++; }
        var defs = m.qcRule.defects || ['Surface defect'];
        (c.qc = c.qc || []).push({ row: r, lineId: x[0], sheets: n, defect: defs[Math.floor(hash01('qcd|' + cid + r) * defs.length)] });
      });
    }
    P.band = c.band; P.free = end;
    ctx.cycles.push(c);
  }
  function releaseRow(st, p, r) {
    var P = st.presses[p.id], old = P.rows[r].set; P.rows[r] = { set: null, fin: null };
    if (old && !P.rows.some(function (rw) { return rw.set === old; })) st.sets[old].on = null;
  }

  E.stats = { iter: 0, nulls: 0 };
  E.clock = typeof performance !== 'undefined' && performance.now ? function () { return performance.now(); } : function () { return Date.now(); };
  function run(m, st, until, W, phase, ctx) {
    for (var guard = 0; guard < 400000; guard++) {
      E.stats.iter++;
      var p = null, pf = 1e15;
      for (var i = 0; i < m.presses.length; i++) { var x = m.presses[i], f = st.presses[x.id].free; if (f < until && f < pf) { p = x; pf = f; } }
      if (!p) break;
      var t = pf;
      advance(m, st, t, ctx);
      var c = buildCycle(m, st, p, t, W, phase);
      if (!c) {   E.stats.nulls++;   // nothing loadable: idle rows give their plates back; wake at the next release / receipt / hour
        st.presses[p.id].rows.forEach(function (rw, r) { if (rw.set) releaseRow(st, p, r); });
        st.presses[p.id].free = nextEvent(st, t); continue;
      }
      var start = blocked(m, p, t, c.chg + m.bandById[c.band].eff);
      if (start !== t) { st.presses[p.id].free = start; continue; }
      commit(m, st, p, c, start, ctx);
    }
  }
  function nextEvent(st, t) {
    var n = t + 60;
    if (st.relIdx < st.pend.length && st.pend[st.relIdx][0] > t && st.pend[st.relIdx][0] < n) n = st.pend[st.relIdx][0];
    if (st.poIdx < st.pos.length && st.pos[st.poIdx].eta > t && st.pos[st.poIdx].eta < n) n = st.pos[st.poIdx].eta;
    return Math.max(n, t + 15);
  }

  // =====================================================================================================================
  // PUBLIC: history (frozen, cached by the caller) and the live plan
  // =====================================================================================================================
  E.history = function (m) {
    var st = newState(m), ctx = { cycles: [], seq: {}, offset: 0, cancels: clone(m.cancels), rejects: clone(m.rejects) };
    m.presses.forEach(function (p) { ctx.seq[p.id] = 1; });
    run(m, st, m.asOf, { mode: 'sequence', key: 'hist' }, 'H', ctx);
    advance(m, st, m.asOf, ctx);
    return { cycles: ctx.cycles, state: clone(st), seq: clone(ctx.seq) };
  };

  E.weightsFor = function (m, settings) {
    settings = settings || {};
    var pr = m.presets[settings.preset || 'balanced'] || m.presets.balanced;
    var w = settings.preset === 'custom' && settings.weights ? settings.weights : pr;
    var W = { mode: w.mode || pr.mode || 'weighted', profit: +w.profit || 0, dates: +w.dates || 0, norms: +w.norms || 0, changeover: +w.changeover || 0,
              mix: +w.mix || 0, delayScale: w.delayScale != null ? +w.delayScale : 1 };
    W.key = [W.mode, W.profit, W.dates, W.norms, W.changeover, W.mix, W.delayScale].join('|');
    return W;
  };

  E.plan = function (m, hist, settings) {
    settings = settings || {};
    var t0 = Date.now(), st = clone(hist.state), ctx = { cycles: [], seq: clone(hist.seq), offset: hist.cycles.length, cancels: [], rejects: [] };
    m.lineList.forEach(function (l) { if (!st.lines[l.id]) { l.rel = Math.max(l.rel, m.asOf); addLine(m, st, l); } else st.lines[l.id].l = l; });
    m.setList.forEach(function (s) { if (!st.sets[s.id]) st.sets[s.id] = { counter: s.counter0, shade: 1, refurbUntil: 0, on: null, refurbs: [] }; });
    st.pos = m.pos.slice(); st.poIdx = st.pos.filter(function (p) { return p.eta <= m.asOf; }).length;
    var applied = applyWhatifs(m, st, settings.whatifs || []);
    sortPend(st); st.act = {}; st.actVer++;
    var W = E.weightsFor(m, settings);
    run(m, st, m.end, W, 'P', ctx);
    advance(m, st, m.end, ctx);
    var res = assemble(m, hist, st, ctx, W, settings);
    res.applied = applied; res.ms = Date.now() - t0;
    return res;
  };

  function applyWhatifs(m, st, list) {
    var out = [];
    list.forEach(function (w) {
      if (w.type === 'rush' && w.order) {
        w.order.lines.forEach(function (l) { var L = E.mkLine(m, l, w.order); L.rush = true; L.rel = Math.max(L.rel, m.asOf); if (!st.lines[L.id] && m.skus[L.skuId]) addLine(m, st, L); });
        out.push(w);
      } else if (w.type === 'cancel') {
        st.lineOrder.forEach(function (id) { var L = st.lines[id]; if (L.l.orderId === w.orderId) { L.cancelled += Math.max(0, L.released ? L.rem : L.l.qty); L.rem = 0; L.released = true; L.whatifCancel = true; } });
        out.push(w);
      } else if (w.type === 'downgrade' && st.lines[w.lineId]) {
        var L = st.lines[w.lineId], n = Math.max(0, Math.min(w.sheets, L.planH - L.down));
        L.down += n; L.rem += n; L.whatifDown = n; out.push(Object.assign({}, w, { sheets: n }));
      } else if (w.type === 'reject' && st.lines[w.lineId]) {
        st.lines[w.lineId].rejected += w.sheets; st.lines[w.lineId].rem += w.sheets; out.push(w);
      } else if (w.type === 'refurb' && st.sets[w.setId]) {
        var S = st.sets[w.setId];
        S.refurbs.push({ from: m.asOf, to: m.asOf + (w.hours || 48) * 60, counter: S.counter, cycle: 'what-if', whatif: true });
        S.refurbUntil = m.asOf + (w.hours || 48) * 60; S.counter = 0; S.shade = 0; S.on = null;
        Object.keys(st.presses).forEach(function (pid) { st.presses[pid].rows.forEach(function (rw) { if (rw.set === w.setId) { rw.set = null; rw.fin = null; } }); });
        out.push(w);
      } else if (w.type === 'poDelay') {
        st.pos = st.pos.map(function (p) { return p.id === w.poId ? Object.assign({}, p, { eta: p.eta + w.days * 1440, delayed: w.days }) : p; })
                       .sort(function (a, b) { return a.eta - b.eta || (a.id < b.id ? -1 : 1); });
        st.poIdx = st.pos.filter(function (p) { return p.eta <= m.asOf; }).length;
        out.push(w);
      } else if (w.type === 'addLine' && w.line && m.skus[w.line.skuId]) {
        var L2 = E.mkLine(m, w.line, w.line); L2.rel = Math.max(L2.rel, m.asOf); if (!st.lines[L2.id]) addLine(m, st, L2); out.push(w);
      }
    });
    return out;
  }

  // =====================================================================================================================
  // RESULTS — the ONE basis every page reports from (per-line status, KPIs, cycles)
  // =====================================================================================================================
  function assemble(m, hist, st, ctx, W, settings) {
    var cycles = hist.cycles.concat(ctx.cycles), nH = hist.cycles.length, finMin = m.finishDays * 1440, lines = [];
    st.lineOrder.forEach(function (id) {
      var L = st.lines[id], l = L.l;
      if (l.norm && !L.planH && !L.planP) return;
      var goodMade = L.planH + L.planP - L.down, ready = null, status;
      if (!l.norm && L.rem <= 0) ready = L.lastEnd != null ? L.lastEnd + finMin : Math.max(l.rel, 0);
      if (l.norm) status = 'Norm';
      else if (L.whatifCancel || (L.cancelled > 0 && L.cancelled >= l.qty - L.alloc - (L.planH - L.down))) status = 'Cancelled';
      else if (L.rem > 0) status = l.due <= m.end ? 'Not in horizon' : 'Beyond horizon';
      else if (ready <= m.asOf) status = 'Done';
      else status = l.cls === 'DOM_OPEN' ? (ready <= l.due ? 'On track' : 'Open — after request date') : (ready <= l.due ? 'On track' : 'Late');
      var lateDays = 0;
      if (!l.norm && l.cls !== 'DOM_OPEN' && status !== 'Cancelled' && status !== 'Beyond horizon') {
        var rd = L.rem > 0 ? m.end + finMin : ready;
        if (rd > l.due) lateDays = Math.ceil((rd - l.due) / 1440);
      }
      lines.push({ id: l.id, orderId: l.orderId, skuId: l.skuId, cls: l.cls, cust: l.cust, qty: l.qty, margin: l.margin, ord: l.ord, rel: l.rel, due: l.due, rush: !!l.rush, norm: !!l.norm,
                   alloc: L.alloc, planH: L.planH, planP: L.planP, down: L.down, cancelled: L.cancelled, rejected: L.rejected, rem: Math.max(0, L.rem),
                   // stateless balance-to-produce: ordered - cancelled + rejected - allocated FG stock - good sheets already made (req 6c)
                   btp: l.norm ? Math.max(0, L.rem) : Math.max(0, l.qty - L.cancelled + L.rejected - L.alloc - (L.planH - L.down)),
                   firstStart: L.firstStart, lastEnd: L.lastEnd, ready: ready, status: status, lateDays: lateDays, delayCost: lateDays * (m.penalty[l.cls] || 0),
                   paperWait: L.paperWait, cycles: L.cyc, cutPlan: l.cutPlan, whatifDown: L.whatifDown || 0, whatifCancel: !!L.whatifCancel, goodMade: goodMade });
    });
    var byId = {}; lines.forEach(function (x) { byId[x.id] = x; });
    var fwd = ctx.cycles, commit = function (x) { return !x.norm && (x.cls === 'EXPORT' || x.cls === 'DOM_COMMITTED'); };
    var dueIn = lines.filter(function (x) { return commit(x) && x.due >= m.asOf && x.due <= m.end && x.status !== 'Cancelled' && x.status !== 'Done'; });
    var onTime = dueIn.filter(function (x) { return x.status === 'On track'; });
    var kp = {
      otif: dueIn.length ? onTime.length / dueIn.length : 1, dueIn: dueIn.length, onTime: onTime.length,
      otifExport: ratio(dueIn, 'EXPORT'), otifDomestic: ratio(dueIn, 'DOM_COMMITTED'),
      // the plan's lateness: open lines that finish after due (lines already made late before the as-of are history — Plan vs Actual)
      late: lines.filter(function (x) { return x.lateDays > 0 && x.status !== 'Done'; }).length,
      lateDone: lines.filter(function (x) { return x.lateDays > 0 && x.status === 'Done'; }).length,
      overdueAtAsOf: lines.filter(function (x) { return commit(x) && x.due < m.asOf && x.status !== 'Done' && x.status !== 'Cancelled'; }).length,
      delayCost: lines.reduce(function (a, x) { return a + (x.status !== 'Done' ? x.delayCost : 0); }, 0),
      contribution: 0, sheets: 0, cycles: fwd.length, swaps: 0, chgMin: 0, bandChanges: 0, cleaning: 0,
      mixBreach: fwd.filter(function (c) { return c.thick.length > m.mixTarget; }).length,
      fill: fwd.length ? fwd.reduce(function (a, c) { return a + c.platesUsed / c.plates; }, 0) / fwd.length : 0,
      paperWait: lines.filter(function (x) { return !x.norm && x.paperWait != null && x.paperWait >= m.asOf; }).length
    };
    fwd.forEach(function (c) {
      kp.sheets += c.sheets; kp.swaps += c.swaps; kp.chgMin += c.chg; kp.bandChanges += c.bandChg;
      c.rows.forEach(function (rw) { if (rw.clean) kp.cleaning++; rw.pl.forEach(function (x) { var ln = byId[x[0]]; kp.contribution += x[1] * (ln ? ln.margin : 200); }); });
    });
    var avail = 0, busy = 0;
    m.presses.forEach(function (p) { avail += (m.end - m.asOf) * (1440 - p.downDur) / 1440; });
    fwd.forEach(function (c) { busy += Math.max(0, Math.min(c.end, m.end) - Math.max(c.s0, m.asOf)); });   // pressing time: changeovers and idle excluded
    kp.util = avail ? busy / avail : 0;
    kp.norm = { BLACK: 0, RED: 0, YELLOW: 0, GREEN: 0, BLUE: 0 };
    m.norms.forEach(function (n) { var pos = st.norm[n.skuId].onHand / n.norm; kp.norm[pos <= 0 ? 'BLACK' : pos < 1 / 3 ? 'RED' : pos < 2 / 3 ? 'YELLOW' : pos <= 1 ? 'GREEN' : 'BLUE']++; });
    return { m: m, W: W, settings: settings, cycles: cycles, nHist: nH, lines: lines, byId: byId, kpi: kp, state: st, hist: hist };
  }
  function ratio(arr, cls) { var a = arr.filter(function (x) { return x.cls === cls; }); return a.length ? a.filter(function (x) { return x.status === 'On track'; }).length / a.length : 1; }

  E.hash01 = hash01;
  root.MEREngine = E;
})(typeof window !== 'undefined' ? window : globalThis);
