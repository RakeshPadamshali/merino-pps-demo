/* Node harness: run the engine exactly as the pages do (history once, then plans) and print timing + KPIs.
   Usage: node tools/run_engine.js [preset ...]      (default: today balanced) */
global.window = global;
require('../data/mer-data.js');
require('../assets/mer-engine.js');
var E = window.MEREngine, MER = window.MER;
var t0 = Date.now(), m = E.prepare(MER), t1 = Date.now(), h = E.history(m), t2 = Date.now();
console.log('prepare %d ms · history %d ms · %d history cycles · skus %d (with a press %d) · sets %d · lines %d',
  t1 - t0, t2 - t1, h.cycles.length, m.skuList.length, m.skuList.filter(function (s) { return s.presses.length; }).length, m.setList.length, m.lineList.length);
var presets = process.argv.slice(2); if (!presets.length) presets = ['today', 'balanced'];
function pct(x) { return (x * 100).toFixed(1) + '%'; }
presets.forEach(function (pr) {
  var r = E.plan(m, h, { preset: pr }), k = r.kpi;
  console.log('\n== %s  (%d ms, %d plan cycles)', pr, r.ms, k.cycles);
  console.log('  OTIF %s (%d/%d due in horizon)  export %s  domestic %s  | late lines %d  overdue at as-of %d  delay cost Rs %s',
    pct(k.otif), k.onTime, k.dueIn, pct(k.otifExport), pct(k.otifDomestic), k.late, k.overdueAtAsOf, Math.round(k.delayCost).toLocaleString('en-IN'));
  console.log('  sheets %s  contribution Rs %s  fill %s  util %s  | swaps %d (%d min)  band changes %d  cleaning %d  mix breaches %d/%d  paper waits %d',
    k.sheets.toLocaleString('en-IN'), Math.round(k.contribution / 1e5) / 10 + ' M', pct(k.fill), pct(k.util), k.swaps, k.chgMin, k.bandChanges, k.cleaning, k.mixBreach, k.cycles, k.paperWait);
  console.log('  norms at end', JSON.stringify(k.norm));
  var st = {}; r.lines.forEach(function (x) { st[x.status] = (st[x.status] || 0) + 1; }); console.log('  line status', JSON.stringify(st));
});
