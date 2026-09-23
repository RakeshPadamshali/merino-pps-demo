/* Merino PPS demo — shared page runtime over window.MER (data/mer-data.js) and window.MEREngine (assets/mer-engine.js).

   ONE BASIS: every page reads the same plan. Inside the tab host (index.html) the plan is computed once by the host and
   every tab reads that result; a page opened on its own computes it itself. The live-demo state (objective weights,
   what-ifs, Master Data uploads) lives in localStorage, so an action on one page is the plan on every page; Reset demo
   clears it. Also here: formatting, lookups, colour roles, the busy overlay, a minute-based Gantt with a window pager,
   Excel export, and the seven scenario actions of the dashboard's launcher. */
(function () {
  var D = window.MER, E = window.MEREngine;
  if (!D || !E) { console.error('MER data / engine not loaded'); return; }
  var BASE = new Date(D.meta.base), ASOF = D.meta.asOfMinute, END = D.meta.endMinute;
  var WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function pad(n) { return (n < 10 ? '0' : '') + n; }

  // ---------------------------------------------------------------- time (engine minutes from the start of history)
  function dateOf(min) { return new Date(BASE.getTime() + min * 60000); }
  function minOf(iso) { return Math.round((new Date(iso) - BASE) / 60000); }
  function fmt(min) { if (min == null) return '—'; var d = dateOf(min); return WD[d.getDay()] + ' ' + d.getDate() + ' ' + MO[d.getMonth()] + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function fmtD(min) { if (min == null) return '—'; var d = dateOf(min); return WD[d.getDay()] + ' ' + d.getDate() + ' ' + MO[d.getMonth()]; }
  function fmtDM(min) { if (min == null) return '—'; var d = dateOf(min); return d.getDate() + ' ' + MO[d.getMonth()]; }
  function fmtT(min) { if (min == null) return '—'; var d = dateOf(min); return pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  // local 'YYYY-MM-DDTHH:MM:SS' (the engine reads timestamps without a zone as local time, like the generated data)
  function isoLocal(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds()); }
  function yymmdd(min) { var d = dateOf(min); return String(d.getFullYear()).slice(2) + pad(d.getMonth() + 1) + pad(d.getDate()); }
  function dur(mn) { mn = Math.round(mn); if (mn < 60) return mn + ' min'; var h = Math.floor(mn / 60), m = mn % 60; return h + ' h' + (m ? ' ' + m + ' m' : ''); }
  function days(mn) { return (mn / 1440).toFixed(1) + ' d'; }
  function shiftOf(min) { var h = dateOf(min).getHours(); return h >= 6 && h < 14 ? 'A' : h >= 14 && h < 22 ? 'B' : 'C'; }

  // ---------------------------------------------------------------- numbers + text
  function n(x, d) { if (x == null || isNaN(x)) return '—'; return Number(x).toLocaleString('en-IN', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); }
  function pct(x, d) { return x == null || isNaN(x) ? '—' : (x * 100).toFixed(d == null ? 1 : d) + '%'; }
  function rs(x) { if (x == null || isNaN(x)) return '—'; var a = Math.abs(x); return (x < 0 ? '−' : '') + '₹' + (a >= 1e7 ? (a / 1e7).toFixed(2) + ' Cr' : a >= 1e5 ? (a / 1e5).toFixed(1) + ' L' : n(a)); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var CLS_LABEL = { EXPORT: 'Export', DOM_COMMITTED: 'Committed domestic', DOM_OPEN: 'Open domestic', NORM: 'Stock norm', RUSH: 'Rush' };
  function cls(c, rush) { return '<span class="cls cls-' + (rush ? 'RUSH' : c) + '">' + esc(rush ? 'Rush export' : CLS_LABEL[c] || c) + '</span>'; }
  var BADGE = { 'Done': 'b-green', 'On track': 'b-green', 'Late': 'b-red', 'Not in horizon': 'b-red', 'Beyond horizon': 'b-grey', 'Cancelled': 'b-grey',
                'Open — after request date': 'b-amber', 'Norm': 'b-grey', 'Running': 'b-blue', 'Planned': 'b-grey', 'In refurbishment': 'b-amber' };
  function badge(s, label) { return '<span class="badge ' + (BADGE[s] || 'b-grey') + '">' + esc(label || s) + '</span>'; }
  function toast(msg, icon) { var t = document.createElement('div'); t.className = 'toast'; t.innerHTML = '<i class="fa-solid ' + (icon || 'fa-circle-check') + '"></i><span>' + msg + '</span>'; document.body.appendChild(t); setTimeout(function () { t.remove(); }, 4200); }

  // ---------------------------------------------------------------- colour roles (validated: dataviz reference palette)
  // Categorical — order class (3 slots validate all-pairs; stock norms take the neutral), cure bands — ordinal one-hue ramp,
  // status — reserved steps, always shown with a label. Merino red is brand chrome only, never a data colour.
  var COLOR = {
    cls: { EXPORT: '#2a78d6', DOM_COMMITTED: '#eb6834', DOM_OPEN: '#1baf7a', NORM: '#9e9e9e' },
    band: { B1: '#86b6ef', B2: '#5598e7', B3: '#2a78d6', B4: '#1c5cab', B5: '#104281' },
    // status steps are the design system's (success / warning / danger, with a deep-orange step between) — always with a label
    status: { good: '#388e3c', warning: '#f57c00', serious: '#e65100', critical: '#d32f2f', neutral: '#9e9e9e', hist: '#bdbdbd' },
    accent: '#2a78d6', primary: '#25A9E0', ink: '#333333'
  };
  function textOn(hex) { var h = String(hex || '#999').replace('#', ''), r = parseInt(h.substr(0, 2), 16), g = parseInt(h.substr(2, 2), 16), b = parseInt(h.substr(4, 2), 16); return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 130 ? '#333333' : '#ffffff'; }

  // ---------------------------------------------------------------- live-demo state (per browser)
  var KEY = 'mer-demo-state';
  var State = {
    all: function () { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } },
    get: function (k, d) { var a = State.all(); return k in a ? a[k] : d; },
    set: function (k, v) { var a = State.all(); a[k] = v; try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {} return v; },
    reset: function () { try { localStorage.removeItem(KEY); } catch (e) {} }
  };
  window.MERState = State;
  function settings() {
    var p = State.get('plan', { preset: 'balanced' });
    return { preset: p.preset || 'balanced', weights: p.weights || null, whatifs: State.get('whatifs', []) };
  }
  function mastersOverlay() { return State.get('masters', {}); }

  // ---------------------------------------------------------------- ONE basis: host-shared engine results
  var isHost = !!window.MER_IS_HOST;
  function hostX() { try { if (!isHost && window.parent !== window && window.parent.MERX && window.parent.MERX.isHost) return window.parent.MERX; } catch (e) {} return null; }
  var C = { hist: null, models: {}, plans: {}, order: [] };
  function modelFor(ovKey, ov) {
    if (!C.models[ovKey]) C.models[ovKey] = E.prepare(D, ov);
    return C.models[ovKey];
  }
  function histOf() { if (!C.hist) C.hist = E.history(modelFor('{}', {})); return C.hist; }
  function planKey(st, ovKey) { return JSON.stringify([st.preset, st.preset === 'custom' ? st.weights : null, st.whatifs, ovKey]); }
  function computeLocal(st) {
    var ov = mastersOverlay(), ovKey = JSON.stringify(ov), k = planKey(st, ovKey);
    if (C.plans[k]) return C.plans[k];
    var r = E.plan(modelFor(ovKey, ov), histOf(), { preset: st.preset, weights: st.weights, whatifs: st.whatifs });
    r.key = k; C.plans[k] = r; C.order.push(k);
    while (C.order.length > 10) delete C.plans[C.order.shift()];   // keep the last ten plans (presets, what-ifs, before/after)
    return r;
  }
  function cached(st) { var h = hostX(); if (h) return h._cached(st); var ov = mastersOverlay(); return C.plans[planKey(st, JSON.stringify(ov))] || null; }
  function compute(st) { var h = hostX(); return h ? h._compute(st) : computeLocal(st); }

  // busy overlay: the engine runs on this thread, so paint the overlay first, then compute
  function busy(on, msg) {
    var o = document.getElementById('mer-busy');
    if (!on) { if (o) o.remove(); return; }
    if (!o) { o = document.createElement('div'); o.id = 'mer-busy'; o.style.cssText = 'position:fixed;inset:0;background:rgba(244,245,247,.72);z-index:9998;display:flex;align-items:center;justify-content:center'; document.body.appendChild(o); }
    o.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:16px 22px;box-shadow:var(--shadow-lg);display:flex;gap:12px;align-items:center;font-size:13px">' +
      '<i class="fa-solid fa-gear fa-spin" style="color:var(--color-primary);font-size:18px"></i><div><b>' + esc(msg || 'Planning') + '</b><div class="hint" style="font-size:11px;margin-top:2px">6 presses · ' + D.meta.forwardDays + ' days · mould, paper and cure-band rules</div></div></div>';
  }
  // Get the plan for the current settings and hand it to cb (at once if cached, else after the overlay has painted).
  function withPlan(cb, st, msg) {
    st = st || settings();
    var r = cached(st);
    if (r) { cb(r); return; }
    busy(true, msg || 'Planning the press shop');
    setTimeout(function () { var t0 = Date.now(), res; try { res = compute(st); } finally { busy(false); } res.wallMs = Date.now() - t0; cb(res); }, 30);
  }
  function whenPlanChanges(fn) {
    window.addEventListener('mer:planchanged', function () { withPlan(fn); });
    window.addEventListener('storage', function (e) { if (e.key === KEY) withPlan(fn); });
  }
  // Change the plan (weights, what-ifs, master uploads): save, re-plan, tell the host (header + other tabs), re-render.
  function replan(mutate, msg, cb) {
    mutate();
    headerMode();
    withPlan(function (r) {
      try { if (window.parent !== window && window.parent.MERHost) window.parent.MERHost.planChanged(window); } catch (e) {}
      if (cb) cb(r);
    }, null, msg || 'Re-planning');
  }
  // open another module: a tab in the host, or the page itself when standalone
  function go(id, hash) {
    try { if (window.parent !== window && window.parent.MERHost) { window.parent.MERHost.open(id, hash || ''); return; } } catch (e) {}
    location.href = id + '.html' + (hash ? '#' + hash : '');
  }
  function addWhatif(w) { var list = State.get('whatifs', []); w.id = w.id || (w.type + '-' + Date.now()); list.push(w); State.set('whatifs', list); }
  function removeWhatif(id) { State.set('whatifs', State.get('whatifs', []).filter(function (w) { return w.id !== id; })); }
  function whatifLabel(w) {
    return w.type === 'rush' ? 'Rush export order ' + w.order.id + ' for ' + custName(w.order.customerId) + ' (' + n(w.order.lines.reduce(function (a, l) { return a + l.qty; }, 0)) + ' sheets)'
      : w.type === 'cancel' ? 'Order ' + w.orderId + ' cancelled'
      : w.type === 'downgrade' ? n(w.sheets) + ' sheets of ' + w.lineId + ' downgraded to B-grade'
      : w.type === 'reject' ? n(w.sheets) + ' sheets of ' + w.lineId + ' rejected by the customer'
      : w.type === 'refurb' ? 'Mould set ' + w.setId + ' off for refurbishment now (' + (w.hours || 48) + ' h)'
      : w.type === 'poDelay' ? 'Paper PO ' + w.poId + ' delayed ' + w.days + ' days'
      : w.type === 'addLine' ? 'New order line ' + w.line.id + ' (' + n(w.line.qty) + ' sheets of ' + w.line.skuId + ')' : w.type;
  }

  // ---------------------------------------------------------------- lookups (base masters; uploads are seen through the model)
  var by = {};
  function index(name, rows, key) { by[name] = {}; (rows || []).forEach(function (r) { by[name][r[key || 'id']] = r; }); }
  index('decors', D.m.decors); index('finishes', D.m.finishes); index('families', D.m.textureFamilies); index('sizes', D.m.sizes); index('grades', D.m.grades);
  index('customers', D.m.customers); index('presses', D.m.presses); index('sets', D.m.mouldSets); index('orders', D.orders); index('lines', D.lines);
  index('papers', D.m.papers, 'decorId'); index('suppliers', D.m.suppliers); index('bands', D.m.cureBands); index('pos', D.pos);
  function sku(m, id) { return (m && m.skus[id]) || null; }
  function decor(id) { return by.decors[id] || { id: id, name: id, hex: '#cccccc', shade: 5 }; }
  function finishName(id) { return (by.finishes[id] || {}).name || id; }
  function custName(id) { return (by.customers[id] || {}).name || (id ? id : 'Stock (make-to-stock)'); }
  function sizeLabel(id) { return (by.sizes[id] || {}).label || id; }
  function skuText(m, id) {
    var s = sku(m, id); if (!s) return id;
    return decor(s.decorId).name + ' · ' + finishName(s.finishId) + ' · ' + s.mm + ' mm · ' + sizeLabel(s.sizeId) + (s.sides === 'D' ? ' · 2-side' : '') + (s.gradeId !== 'GP' ? ' · ' + s.gradeId : '');
  }
  function swatch(decorId, title) { var d = decor(decorId); return '<span class="swatch" style="background:' + d.hex + '" title="' + esc(title || (d.name + ' · shade ' + d.shade)) + '"></span>'; }
  function printMark(c, r) { var rw = c.rows[r]; return 'MER ' + c.p + ' ' + (rw && rw.s ? rw.s : '—') + ' ' + yymmdd(c.s0) + '-C' + pad(c.no) + '-D' + pad(r + 1); }

  // ---------------------------------------------------------------- header plan-mode chip (standalone chrome + host)
  function headerMode() {
    var st = settings(), el = document.getElementById('mer-mode'), a = document.getElementById('mer-asof');
    var pr = (D.m.weights || []).filter(function (w) { return w.id === st.preset; })[0], label = st.preset === 'custom' ? 'Custom weights' : pr ? pr.label : st.preset;
    if (el) el.innerHTML = '<i class="fa-solid fa-sliders" style="margin-right:4px;color:var(--color-primary-light)"></i>Plan: <b>' + esc(label) + '</b>' + (st.whatifs.length ? ' · <b>' + st.whatifs.length + '</b> what-if' + (st.whatifs.length > 1 ? 's' : '') : '');
    if (a) a.innerHTML = '<i class="fa-regular fa-clock"></i> as of ' + fmt(ASOF) + ' · Shift ' + shiftOf(ASOF);
  }

  // ---------------------------------------------------------------- Gantt (minutes) + window pager
  // lanes [{id,label,sub}], bars [{lane,s,e,color,cls,tip,id,label}], opts {startMin,endMin,laneW,laneTitle,onClick}
  function gantt(el, lanes, bars, opts) {
    opts = opts || {};
    var laneW = opts.laneW || 150, s0 = opts.startMin != null ? opts.startMin : 0, e0 = opts.endMin != null ? opts.endMin : END, span = Math.max(60, e0 - s0);
    var avail = Math.max(300, (el.clientWidth || 1200) - laneW - 4), px = avail / span, W = Math.round(span * px);
    function x(mn) { return Math.round((mn - s0) * px); }
    var step = span > 20 * 1440 ? 1440 : span > 4 * 1440 ? 720 : span > 1440 ? 360 : 120, grid = '', head = '';
    for (var t = Math.ceil(s0 / step) * step; t <= e0; t += step) {
      var isDay = t % 1440 === 0; grid += '<div class="g-grid' + (isDay ? ' day' : '') + '" style="left:' + x(t) + 'px"></div>';
    }
    var nd = Math.ceil(span / 1440), every = Math.max(1, Math.ceil(nd / 16));
    for (var d = Math.floor(s0 / 1440), k = 0; d * 1440 < e0; d++, k++) {
      if (k % every) continue;
      var mid = Math.max(s0, d * 1440) + (Math.min(e0, (d + 1) * 1440) - Math.max(s0, d * 1440)) / 2;
      head += '<div class="g-day" style="left:' + x(mid) + 'px">' + WD[dateOf(d * 1440).getDay()] + '<span class="dm">' + fmtDM(d * 1440) + '</span></div>';
    }
    if (span <= 1440 * 1.01) for (var hh = Math.ceil(s0 / 240) * 240; hh < e0; hh += 240) head += '<div class="g-day" style="left:' + x(hh) + 'px;top:18px;font-weight:400;color:#9e9e9e">' + fmtT(hh) + '</div>';
    var now = ASOF >= s0 && ASOF <= e0 ? '<div class="g-now" style="left:' + x(ASOF) + 'px"></div>' : '';
    var html = '<div class="g-row head"' + (span <= 1440 * 1.01 ? ' style="min-height:40px"' : '') + '><div class="g-lane head-lane" style="width:' + laneW + 'px">' + esc(opts.laneTitle || 'Press') + '</div><div class="g-track" style="min-width:' + W + 'px">' + grid + head + now + '</div></div>';
    var byLane = {}; bars.forEach(function (b) { (byLane[b.lane] = byLane[b.lane] || []).push(b); });
    lanes.forEach(function (ln) {
      var bs = (byLane[ln.id] || []).map(function (b) {
        if (b.e <= s0 || b.s >= e0) return '';
        var l = x(Math.max(b.s, s0)), w = Math.max(2, x(Math.min(b.e, e0)) - l);
        return '<div class="g-bar ' + (b.cls || '') + '" style="left:' + l + 'px;width:' + w + 'px;background:' + (b.color || COLOR.accent) + ';color:' + textOn(b.color || COLOR.accent) + '" title="' + esc(b.tip || '') + '"' + (b.id != null ? ' data-id="' + esc(b.id) + '"' : '') + '>' + (w > 40 && b.label ? esc(b.label) : '') + '</div>';
      }).join('');
      html += '<div class="g-row"><div class="g-lane" style="width:' + laneW + 'px" title="' + esc(ln.label) + '">' + esc(ln.label) + (ln.sub ? '&nbsp;<span class="sub">' + esc(ln.sub) + '</span>' : '') + '</div><div class="g-track" style="min-width:' + W + 'px">' + grid + now + bs + '</div></div>';
    });
    el.innerHTML = html;
    if (opts.onClick) el.onclick = function (e) { var b = e.target.closest('.g-bar[data-id]'); if (b) opts.onClick(b.getAttribute('data-id'), e); };
  }
  // A window selector with paging: 1 / 3 / 7 / 14 days or the full plan; lands on the page holding the as-of moment.
  function pager(host, onChange, opts) {
    opts = opts || {}; var fromMin = opts.from != null ? opts.from : ASOF - 1440 * 2, toMin = opts.to != null ? opts.to : END;
    var dflt = opts.days != null ? opts.days : 7, pg = 0;
    host.innerHTML = '<span class="fl" style="font-size:10px;text-transform:uppercase;color:var(--color-text-muted);font-weight:600">Window</span> <select class="pw">' +
      [[1, '1 day'], [3, '3 days'], [7, '7 days'], [14, '14 days'], [0, 'Full plan']].map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === dflt ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select> ' +
      '<span class="pager"><button data-a="first" title="First window">&laquo;</button><button data-a="prev" title="Previous window">&lsaquo;</button><span class="plab"></span><button data-a="next" title="Next window">&rsaquo;</button><button data-a="last" title="Last window">&raquo;</button><button class="now" data-a="now" title="Back to the window with the as-of moment">Now</button></span>';
    var sel = host.querySelector('.pw'), pgr = host.querySelector('.pager'), lab = host.querySelector('.plab');
    function daysSel() { return +sel.value; }
    function startDay() { return Math.floor(fromMin / 1440); }
    function pages() { var d = daysSel(); return d ? Math.max(1, Math.ceil((Math.ceil(toMin / 1440) - startDay()) / d)) : 1; }
    function pageOfNow() { var d = daysSel(); return d ? Math.max(0, Math.min(pages() - 1, Math.floor((Math.floor(ASOF / 1440) - startDay()) / d))) : 0; }
    function win() { var d = daysSel(); if (!d) return { startMin: fromMin, endMin: toMin, days: 0 }; var s = (startDay() + pg * d) * 1440; return { startMin: s, endMin: s + d * 1440, days: d }; }
    function paint() {
      var d = daysSel(), np = pages(); pg = Math.max(0, Math.min(np - 1, pg)); pgr.style.display = d ? '' : 'none';
      var w = win(); lab.innerHTML = 'Page <b>' + (pg + 1) + '</b> of ' + np + ' · ' + fmtD(w.startMin) + (d > 1 ? ' – ' + fmtD(w.endMin - 1) : '');
      pgr.querySelector('[data-a=first]').disabled = pgr.querySelector('[data-a=prev]').disabled = pg === 0;
      pgr.querySelector('[data-a=last]').disabled = pgr.querySelector('[data-a=next]').disabled = pg >= np - 1;
      pgr.querySelector('[data-a=now]').disabled = pg === pageOfNow();
      onChange(w);
    }
    sel.addEventListener('change', function () { pg = pageOfNow(); paint(); });
    pgr.addEventListener('click', function (e) { var b = e.target.closest('button[data-a]'); if (!b) return; var a = b.getAttribute('data-a'); pg = a === 'first' ? 0 : a === 'prev' ? pg - 1 : a === 'next' ? pg + 1 : a === 'last' ? pages() - 1 : pageOfNow(); paint(); });
    pg = pageOfNow(); paint();
    return { win: win, repaint: paint };
  }

  // ---------------------------------------------------------------- Excel (SheetJS, vendored) — pages load assets/vendor/xlsx.full.min.js
  function xlsx(sheets, filename) {
    if (!window.XLSX) { toast('Excel library not loaded on this page', 'fa-triangle-exclamation'); return; }
    var wb = XLSX.utils.book_new();
    sheets.forEach(function (s) { var ws = XLSX.utils.aoa_to_sheet([s.cols].concat(s.rows)); ws['!cols'] = s.cols.map(function (c, i) { return { wch: (s.widths && s.widths[i]) || Math.max(10, String(c).length + 2) }; }); XLSX.utils.book_append_sheet(wb, ws, s.name.slice(0, 31)); });
    XLSX.writeFile(wb, filename);
  }

  // ---------------------------------------------------------------- scenarios (dashboard launcher; anchors in data.scenarios)
  var S = D.scenarios;
  var SCENARIOS = [
    { id: 'S1', icon: 'fa-ship', page: 'orders.html', hash: 'impact', title: 'Rush export container', req: '3a · 6c',
      desc: 'A ' + n(S.S1.order.lines.reduce(function (a, l) { return a + l.qty; }, 0)) + '-sheet order from ' + custName(S.S1.order.customerId) + ' due in 6 days. The engine finds eligible presses and moulds and shows exactly which orders move.',
      run: function () { addWhatif({ type: 'rush', order: S.S1.order }); } },
    { id: 'S2', icon: 'fa-sliders', page: 'objectives.html', title: 'Merino today vs weighted objectives', req: '3a · 3b · 4c · 6b',
      desc: 'The fixed sequence (export → committed domestic → norms) against the five objectives in one score — better delivery, far fewer mould changeovers, cleaning passes and stock-outs.',
      run: function () { } },
    { id: 'S3', icon: 'fa-clone', page: 'moulds.html', hash: S.S3.setId, title: 'Mould set off early for refurbishment', req: '1b · 4a',
      desc: 'Set ' + S.S3.setId + ' goes for refurbishment now (' + S.S3.hours + ' h). Its work moves to the twin set or another press; eligibility and the refurbishment calendar update.',
      run: function () { addWhatif({ type: 'refurb', setId: S.S3.setId, hours: S.S3.hours }); } },
    { id: 'S4', icon: 'fa-scroll', page: 'materials.html', hash: S.S4.decorId, title: 'China paper PO slips ' + S.S4.days + ' days', req: '5a',
      desc: 'PO ' + S.S4.poId + ' for decor ' + decor(S.S4.decorId).name + ' arrives ' + S.S4.days + ' days late. Lines of that design wait for paper; the press backfills with other work.',
      run: function () { addWhatif({ type: 'poDelay', poId: S.S4.poId, days: S.S4.days }); } },
    { id: 'S5', icon: 'fa-rotate', page: 'orders.html', hash: 'btp', title: 'Cancellation + QC downgrade', req: '6c',
      desc: 'Order ' + S.S5.cancelOrderId + ' is cancelled and ' + S.S5.downgradeSheets + ' pressed sheets of ' + S.S5.downgradeLineId + ' are downgraded. Balance-to-produce recalculates itself — nothing is re-entered.',
      run: function () { addWhatif({ type: 'cancel', orderId: S.S5.cancelOrderId }); addWhatif({ type: 'downgrade', lineId: S.S5.downgradeLineId, sheets: S.S5.downgradeSheets }); } },
    { id: 'S6', icon: 'fa-fingerprint', page: 'trace.html', hash: 'complaint', title: 'Print-mark complaint → recall scope', req: '5c',
      desc: 'A customer reports a gloss streak on a sheet pressed on ' + S.S6.pressId + ' five days ago. The print mark leads to the press cycle, daylight, mould set and every other sheet that set made.',
      run: function () { } },
    { id: 'S7', icon: 'fa-file-excel', page: 'masters.html', hash: 'skus', title: 'New SKU onboarded from Excel', req: '1d · 5b',
      desc: 'Add ' + (S.S7.sku ? decor(S.S7.sku.decorId).name + ' in ' + finishName(S.S7.sku.finishId) + ' ' + sizeLabel(S.S7.sku.sizeId) : 'a new SKU') + ' through the SKU master upload. It inherits its presses and mould sets from its attributes — no mapping table.',
      run: function () { } },
  ];

  headerMode();
  window.MERX = {
    D: D, E: E, BASE: BASE, ASOF: ASOF, END: END, isHost: isHost, by: by, COLOR: COLOR, CLS_LABEL: CLS_LABEL, State: State, SCENARIOS: SCENARIOS,
    dateOf: dateOf, minOf: minOf, isoLocal: isoLocal, fmt: fmt, fmtD: fmtD, fmtDM: fmtDM, fmtT: fmtT, dur: dur, days: days, shiftOf: shiftOf, yymmdd: yymmdd,
    n: n, pct: pct, rs: rs, esc: esc, cls: cls, badge: badge, toast: toast, textOn: textOn,
    settings: settings, go: go, withPlan: withPlan, whenPlanChanges: whenPlanChanges, replan: replan, addWhatif: addWhatif, removeWhatif: removeWhatif, whatifLabel: whatifLabel,
    cachedPlan: cached, computePlan: compute, busy: busy, headerMode: headerMode, hashParam: function () { return decodeURIComponent((location.hash || '').slice(1)); },
    sku: sku, decor: decor, finishName: finishName, custName: custName, sizeLabel: sizeLabel, skuText: skuText, swatch: swatch, printMark: printMark,
    gantt: gantt, pager: pager, xlsx: xlsx,
    // host-side API (the tab host computes once; tabs read)
    _cached: function (st) { var ov = mastersOverlay(); return C.plans[planKey(st, JSON.stringify(ov))] || null; },
    _compute: function (st) { return computeLocal(st); },
    model: function () { var ov = mastersOverlay(); var h = hostX(); if (h) return h.model(); return modelFor(JSON.stringify(ov), ov); },
    hist: function () { var h = hostX(); return h ? h.hist() : histOf(); }
  };
})();
