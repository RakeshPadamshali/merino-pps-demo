/* When a Merino page loads inside index.html (an iframe tab), render content-only (hide its own header + sidebar)
   and route in-content links to the host's tabs. Standalone: leave the page untouched. Needs mer-nav.js first. */
(function () {
  if (window.self === window.top) return;
  document.documentElement.className += ' embedded';
  var s = document.createElement('style');
  s.textContent = '.embedded .bm-header,.embedded .bm-sidebar{display:none!important}' +
                  '.embedded .bm-layout{height:100vh!important}' +
                  '.embedded .bm-content{padding-top:12px}';
  (document.head || document.documentElement).appendChild(s);
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var raw = a.getAttribute('href') || '', href = raw.split('#')[0].split('?')[0], hash = raw.split('#')[1] || '';
    var id = href.replace(/\.html$/, '');
    if (window.MER_PAGES && window.MER_PAGES[id]) {
      try { if (window.parent && window.parent.MERHost) { e.preventDefault(); window.parent.MERHost.open(id, hash); } } catch (err) {}
    }
  }, true);
})();
