/* Injects the standalone header + sidebar into a Merino content page (hidden again when embedded in index.html).
   Each page sets window.MER_PAGE / MER_TITLE / MER_ICON before loading this. Needs mer-nav.js. */
(function () {
  var cur = window.MER_PAGE || '';
  var layout = document.querySelector('.bm-layout');
  if (!layout) return;
  var h = document.createElement('header'); h.className = 'bm-header';
  h.innerHTML =
    '<div class="logo"><img src="assets/img/merino-logo.png" alt="Merino Laminates"><span class="t">PPS</span><span class="sub">Production Planning &amp; Scheduling</span></div>' +
    '<div class="module-name"><i class="fa-solid ' + (window.MER_ICON || 'fa-diagram-project') + '"></i>' + (window.MER_TITLE || 'Production Planning &amp; Scheduling') + '</div>' +
    '<div class="spacer"></div>' +
    '<div class="plant-switch"><button class="active"><i class="fa-solid fa-industry" style="margin-right:4px"></i>HPL Press Shop</button></div>' +
    '<div class="right"><span class="plan-mode" id="mer-mode"></span><span class="asof" id="mer-asof"></span>' +
    '<button class="btn-reset" id="mer-reset" title="Clear every live-demo action and reload"><i class="fa-solid fa-rotate-left"></i> Reset demo</button><div class="avatar">RP</div></div>';
  document.body.insertBefore(h, layout);
  var side = document.createElement('aside'); side.className = 'bm-sidebar';
  var html = '';
  (window.MER_NAV || []).forEach(function (sec) {
    html += '<div class="nav-label">' + sec[0] + '</div>';
    sec[1].forEach(function (it) { html += '<a href="' + it[0] + '.html" class="' + (it[0] === cur ? 'active' : '') + '"><i class="fa-solid ' + it[2] + '"></i>' + it[1] + '</a>'; });
  });
  html += '<div class="powered">Powered by<img src="assets/img/bluemingo-logo.png" alt="Bluemingo"></div>';
  side.innerHTML = html;
  layout.insertBefore(side, layout.firstChild);
  var rb = document.getElementById('mer-reset');
  if (rb) rb.addEventListener('click', function () { if (window.MERState) { MERState.reset(); location.reload(); } });
})();
