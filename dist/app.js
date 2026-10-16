// Reads data.json and draws the page. data.json is written by ledger.py, edit nothing by hand there.
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var WORD = { OPEN: 'Open', DRAFT: 'Draft', MERGED: 'Merged', CLOSED: 'Closed' };
  var SHOW = [['ALL', 'All'], ['OPEN', 'Open'], ['MERGED', 'Merged'], ['CLOSED', 'Closed']];
  var data, show = 'ALL';

  function dayWords(iso) {
    var d = new Date(iso + 'T00:00:00Z');
    return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' });
  }
  function keep(r) {
    var q = $('#q').value.trim().toLowerCase();
    if (q && (r.repo + ' ' + r.title).toLowerCase().indexOf(q) < 0) return false;
    if (show === 'ALL') return true;
    if (show === 'OPEN') return r.state === 'OPEN' || r.state === 'DRAFT';
    return r.state === show;
  }
  function where(r) {
    var bits = [esc(r.repo) + ' #' + esc(r.number)];
    if (r.size) bits.push(esc(r.size));
    if (r.state === 'OPEN' || r.state === 'DRAFT') {
      if (r.cla === 'unsigned') bits.push('CLA not signed yet');
      if (r.failing && r.failing.length) bits.push('failing: ' + esc(r.failing.slice(0, 2).join(', ')));
      if (r.review === 'CHANGES_REQUESTED') bits.push('changes requested');
    }
    return bits.join(' · ');
  }
  function draw() {
    var rows = data.rows.filter(keep), days = {}, order = [];
    rows.forEach(function (r) { var k = r.updated || 'unknown'; if (!days[k]) { days[k] = []; order.push(k); } days[k].push(r); });
    order.sort().reverse();
    $('#shown').textContent = rows.length === data.rows.length ? '' : rows.length + ' of ' + data.rows.length + ' shown';
    if (!rows.length) { $('#log').innerHTML = '<p class="empty">Nothing matches. Clear the search or pick All.</p>'; return; }
    $('#log').innerHTML = order.map(function (k) {
      return '<div class="day"><h3>' + (k === 'unknown' ? 'Undated' : esc(dayWords(k))) + '</h3><ul>' +
        days[k].map(function (r) {
          return '<li class="entry"><span class="st s-' + r.state.toLowerCase() + '">' + WORD[r.state] + '</span><div><a class="title" href="' + esc(r.url) + '">' + esc(r.title) + '</a><span class="where">' + where(r) + '</span></div></li>';
        }).join('') + '</ul></div>';
    }).join('');
  }
  function start(d) {
    data = d; var c = d.counts;
    $('#counts').textContent = 'Since ' + d.since_label + ': ' + (c.OPEN + c.DRAFT) + ' open, ' + c.MERGED + ' merged, ' + c.CLOSED + ' closed.';
    $('#built').textContent = 'Last updated ' + d.built + ' UTC.';
    var owe = d.rows.filter(function (r) { return r.waiting && r.waiting.length; });
    if (owe.length) {
      $('#owe').hidden = false;
      $('#notes').innerHTML = owe.map(function (r) {
        return '<li><span><a href="' + esc(r.url) + '">' + esc(r.repo) + ' #' + esc(r.number) + '</a>: ' + esc(r.waiting.join(', ')) + '</span></li>';
      }).join('');
    }
    if (d.claims && d.claims.length) {
      $('#claims-section').hidden = false;
      $('#claims').innerHTML = d.claims.map(function (c) {
        return '<li><span class="cst c-' + esc(c.status.toLowerCase()) + '">' + esc(c.word) + '</span><div><a class="title" href="' + esc(c.url) + '">' + esc(c.title) + '</a><span class="where">' + esc(c.repo) + ' #' + esc(c.number) + ' \u00b7 asked on ' + esc(dayWords(c.claimed)) + '</span></div></li>';
      }).join('');
    }
    $('#filters').innerHTML = SHOW.map(function (f) { return '<button type="button" class="f" data-f="' + f[0] + '" aria-pressed="' + (f[0] === 'ALL') + '">' + f[1] + '</button>'; }).join('');
    $('#filters').addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return; show = b.dataset.f;
      document.querySelectorAll('.f').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); draw();
    });
    $('#q').addEventListener('input', draw);
    draw();
  }
  fetch('data.json', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(start)
    .catch(function () { $('#log').innerHTML = '<p class="empty">Could not load data.json. Open this folder through a web server, not as a file.</p>'; });
})();
