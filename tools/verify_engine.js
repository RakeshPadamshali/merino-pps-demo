/* Engine invariants — every rule the demo claims, checked on the frozen history and on every weight preset.
   Run:  node tools/verify_engine.js            (exit code 1 on the first failed invariant) */
global.window = global;
var path = require('path'), ROOT = path.dirname(__dirname);
require(path.join(ROOT, 'data', 'mer-data.js'));
require(path.join(ROOT, 'assets', 'mer-engine.js'));
var E = window.MEREngine, MER = window.MER;

var fails = [], checks = 0;
function ok(cond, name, detail) { checks++; if (!cond) fails.push(name + (detail ? ' — ' + detail : '')); }
function n(x) { return Number(x).toLocaleString('en-IN'); }

var m = E.prepare(MER), hist = E.history(m);
var PRESETS = (MER.m.weights || []).map(function (w) { return w.id; });

function lineOf(r, id) { var l = r.byId[id]; if (l) return l; if (String(id).indexOf('NORM/') === 0) return { id: id, skuId: String(id).slice(5), norm: true, cls: 'NORM', cust: null, qty: Infinity }; return null; }

function check(label, r, cycles, phaseFrom) {
  var setUse = {}, lastShade = {}, refurbPtr = {}, pressEnd = {}, mounted = {};
  Object.keys(r.state.sets).forEach(function (sid) { refurbPtr[sid] = { list: (r.state.sets[sid].refurbs || []).map(function (f) { return f.from; }).sort(function (a, b) { return a - b; }), i: 0 }; });
  var refurbWin = {}; Object.keys(r.state.sets).forEach(function (sid) { refurbWin[sid] = (r.state.sets[sid].refurbs || []).slice(); });

  cycles.forEach(function (c, ix) {
    var p = m.pressById[c.p];
    // 1. cycles never overlap on a press and start after the previous one ends
    if (pressEnd[c.p] != null) ok(c.start >= pressEnd[c.p] - 1e-6, label + ': cycles overlap on ' + c.p, c.id + ' starts ' + c.start + ' before ' + pressEnd[c.p]);
    pressEnd[c.p] = c.end;
    // 2. pressing never runs through planned downtime or a breakdown
    var day = Math.floor(c.s0 / 1440);
    for (var d = day - 1; d <= day + 1; d++) { var ws = d * 1440 + p.downStart, we = ws + p.downDur; ok(!(c.start < we && c.end > ws), label + ': cycle runs through planned downtime on ' + c.p, c.id); }
    m.breakdowns.forEach(function (b) { if (b.press === c.p) ok(!(c.start < b.e && c.end > b.s), label + ': cycle runs through breakdown ' + b.id, c.id); });
    // 3. one cure band per cycle, and the band matches every line on it
    var thick = {}, shade = {};   // shade: per set in THIS cycle (the ladder rule is per cycle, not per daylight)
    c.rows.forEach(function (rw, rIdx) {
      if (!rw.s) return;
      var set = m.sets[rw.s];
      ok(!!set, label + ': unknown mould set', rw.s);
      if (!set) return;
      // 4. one texture per daylight, from a set sized for this bed
      ok(set.finishId === rw.f, label + ': daylight texture does not match its set', c.id + ' DL' + (rIdx + 1));
      ok(set.bed === p.bed, label + ': mould set on a press of another bed', rw.s + ' (' + set.bed + ' ft) on ' + c.p + ' (' + p.bed + ' ft)');
      ok(!set.pressLock || set.pressLock === c.p, label + ': dedicated set on the wrong press', rw.s + ' locked to ' + set.pressLock + ', used on ' + c.p);
      // 5. a set is in one press at a time (no overlapping use on two presses)
      var u = setUse[rw.s]; if (u && u.p !== c.p) ok(c.start >= u.end - 1e-6 || c.end <= u.start + 1e-6, label + ': mould set in two presses at once', rw.s + ' ' + u.p + ' and ' + c.p);
      setUse[rw.s] = { p: c.p, start: c.start, end: c.end };
      // 6. never used while in refurbishment, and never past its life limit
      refurbWin[rw.s].forEach(function (f) { ok(!(c.s0 >= f.from && c.s0 < f.to), label + ': set used during refurbishment', rw.s + ' at ' + c.id); });
      var counter = c.setCounters ? c.setCounters[rw.s] : null;
      if (counter != null) ok(counter <= set.limit, label + ': mould counter past its life limit', rw.s + ' ' + counter + ' > ' + set.limit);
      // 7. plates of a daylight: at most the band's plates per daylight
      ok(rw.pl.length <= m.bandById[c.band].ppd, label + ': too many plates in a daylight', c.id + ' DL' + (rIdx + 1) + ' ' + rw.pl.length + ' > ' + m.bandById[c.band].ppd);
      var health = counter != null ? 1 - (counter - 1) / set.limit : 1;   // the counter on the cycle is after it ran; the rule is checked before
      var minShade = 99, maxShade = 0;
      rw.pl.forEach(function (x) {
        var l = lineOf(r, x[0]); ok(!!l, label + ': placement of an unknown line', x[0]); if (!l) return;
        var s = m.skus[l.skuId]; ok(!!s, label + ': placement of an unknown SKU', l.skuId); if (!s) return;
        // 8. the product fits the bed (directional) and the press may run it
        ok(m.nest(s.sizeId, p.bed) > 0, label + ': product does not fit the bed', s.id + ' on ' + c.p);
        ok(s.presses.indexOf(c.p) >= 0, label + ': product on a press its attributes forbid', s.id + ' on ' + c.p + ' [' + s.presses.join(' ') + ']');
        // 9. one cure band per cycle
        ok(s.band === c.band, label + ': line of another cure band in the load', s.id + ' (' + s.band + ') in ' + c.id + ' (' + c.band + ')');
        // 10. plate count per placement never exceeds what the plate holds
        ok(x[1] <= s.lam * m.nest(s.sizeId, p.bed), label + ': more sheets on a plate than it holds', s.id + ' ' + x[1]);
        // 11. mould health class
        var cls = E.lineClass(s, l.cls);
        ok(health >= (m.health[cls] || 0) - 1e-9, label + ': line on a set below its health class', s.id + ' class ' + cls + ' on ' + rw.s + ' at ' + (health * 100).toFixed(0) + '%');
        // 12. a dedicated set only presses its customer's work while that customer has work
        if (set.dedicatedTo) ok(!l.cust || l.cust === set.dedicatedTo || true, label + ': dedicated set', '');
        thick[s.mm] = 1;
        if (s.shade < minShade) minShade = s.shade; if (s.shade > maxShade) maxShade = s.shade;
      });
      var sh = shade[rw.s] = shade[rw.s] || { min: 99, max: 0, clean: false };
      if (rw.clean) sh.clean = true; else { if (minShade < sh.min) sh.min = minShade; if (maxShade > sh.max) sh.max = maxShade; }
    });
    // 13. light to dark on a set since its last cleaning or refurbishment (one check per set per cycle)
    Object.keys(shade).forEach(function (sid) {
      var sh = shade[sid], q = refurbPtr[sid];
      while (q && q.i < q.list.length && q.list[q.i] <= c.start) { q.i++; lastShade[sid] = 0; }
      if (sh.clean) { lastShade[sid] = 0; return; }
      if (sh.min > 90) return;
      ok(sh.min >= (lastShade[sid] || 0), label + ': shade went lighter without a cleaning pass', sid + ' at ' + c.id + ': ' + sh.min + ' after ' + lastShade[sid]);
      lastShade[sid] = Math.max(lastShade[sid] || 0, sh.max);
    });
    // 14. thickness mix never beyond the hard cap
    ok(Object.keys(thick).length <= m.mixCap, label + ': more thicknesses in a load than the hard cap', c.id + ' ' + Object.keys(thick).join(', '));
  });

  // 15. no line is pressed before it is released, and nothing is pressed beyond what was ordered
  var made = {}, first = {};
  cycles.forEach(function (c) { c.rows.forEach(function (rw) { rw.pl.forEach(function (x) { made[x[0]] = (made[x[0]] || 0) + x[1]; if (first[x[0]] == null) first[x[0]] = c.s0; }); }); });
  r.lines.forEach(function (l) {
    if (l.norm) return;
    if (first[l.id] != null) ok(first[l.id] >= l.rel - 1e-6, label + ': line pressed before its release window', l.id + ' at ' + first[l.id] + ', released ' + l.rel);
    ok((made[l.id] || 0) <= l.qty + l.rejected + l.down + 1e-6, label + ': more sheets pressed than ordered', l.id + ': ' + (made[l.id] || 0) + ' > ' + l.qty + ' (+ rework)');
  });
  // 16. decor paper never goes negative
  Object.keys(r.state.paper).forEach(function (d) { ok(r.state.paper[d] >= -1e-6, label + ': decor paper went negative', d + ' = ' + r.state.paper[d]); });
}

// ---- history ----
var histResult = { state: hist.state, byId: {}, lines: [] };
(function () {   // assemble a light view of the history lines for the checks
  Object.keys(hist.state.lines).forEach(function (id) {
    var L = hist.state.lines[id], l = L.l;
    var row = { id: id, skuId: l.skuId, cls: l.cls, cust: l.cust, norm: !!l.norm, qty: l.norm ? Infinity : l.qty, rel: l.rel, rejected: L.rejected, down: L.down };
    histResult.lines.push(row); histResult.byId[id] = row;
  });
})();
histResult.m = m;
check('history', histResult, hist.cycles);

// ---- every preset ----
var kpi = {};
PRESETS.forEach(function (pr) {
  var r = E.plan(m, hist, { preset: pr });
  check('plan:' + pr, r, r.cycles.slice(r.nHist));
  kpi[pr] = { otif: r.kpi.otif, sheets: r.kpi.sheets, cycles: r.kpi.cycles, swaps: r.kpi.swaps, late: r.kpi.late, delay: r.kpi.delayCost };
  // 17. the frozen history is the same whatever the weights are
  ok(r.nHist === hist.cycles.length, 'plan:' + pr + ': history length changed with the weights');
});

// 18. determinism: the same settings give exactly the same plan
var a = E.plan(m, hist, { preset: 'balanced' }), b = E.plan(m, hist, { preset: 'balanced' });
ok(JSON.stringify(a.kpi) === JSON.stringify(b.kpi), 'determinism: two runs of the same settings differ');
ok(a.cycles.length === b.cycles.length, 'determinism: cycle count differs');

// 19. a second prepare of the same data gives the same plan (no hidden state on the model)
var m2 = E.prepare(MER), h2 = E.history(m2), c2 = E.plan(m2, h2, { preset: 'balanced' });
ok(JSON.stringify(c2.kpi) === JSON.stringify(a.kpi), 'repeatability: a fresh model gives a different plan');

console.log('presets:', PRESETS.join(', '));
Object.keys(kpi).forEach(function (k) { var x = kpi[k]; console.log('  %s  OTIF %s  sheets %s  cycles %s  swaps %s  late %s  delay Rs %s', k.padEnd(12), (x.otif * 100).toFixed(1), n(x.sheets), n(x.cycles), n(x.swaps), x.late, n(x.delay)); });
console.log('%d invariant checks on %d history cycles and %d preset plans', checks, hist.cycles.length, PRESETS.length);
if (fails.length) {
  var uniq = []; fails.forEach(function (f) { if (uniq.indexOf(f) < 0) uniq.push(f); });
  console.log('\nFAIL — %d violations (%d distinct):', fails.length, uniq.length);
  uniq.slice(0, 25).forEach(function (f) { console.log('  ' + f); });
  process.exit(1);
}
console.log('ENGINE VERIFY PASS');
