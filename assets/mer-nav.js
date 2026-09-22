/* The ONE navigation definition. index.html builds its sidebar and tab map from it, mer-chrome.js builds the standalone
   sidebar from it, and mer-embed.js routes in-page links to host tabs with it — so the three can never disagree. */
window.MER_NAV = [
  ['Planning', [
    ['home', 'PPS Dashboard', 'fa-gauge-high'],
    ['orders', 'Order Book & BTP', 'fa-file-invoice'],
    ['objectives', 'Objective Studio', 'fa-sliders'],
    ['atp', 'ATP & Capacity', 'fa-calculator']]],
  ['Scheduling', [
    ['loadbuilder', 'Press Load Builder', 'fa-layer-group'],
    ['schedule', 'Press Schedule', 'fa-chart-gantt'],
    ['workorders', 'Shift Work Orders', 'fa-clipboard-list'],
    ['moulds', 'Mould Board', 'fa-clone'],
    ['sequence', 'Colour & Changeover', 'fa-palette']]],
  ['Materials', [
    ['materials', 'Paper & Materials', 'fa-scroll'],
    ['norms', 'Stock Norms', 'fa-warehouse']]],
  ['Execution & Trace', [
    ['planactual', 'Plan vs Actual', 'fa-scale-balanced'],
    ['trace', 'Traceability', 'fa-fingerprint']]],
  ['Masters', [
    ['masters', 'Master Data', 'fa-database']]]
];
window.MER_PAGES = {};
window.MER_NAV.forEach(function (sec) { sec[1].forEach(function (it) { window.MER_PAGES[it[0]] = { label: it[1], icon: it[2], href: it[0] + '.html' }; }); });
