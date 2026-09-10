/* puzzle-engine.js — the shared gate machine.
   A gate is a flip-book of parchment plates followed by a test.
   No network, no model, no key. Everything is decided here in the page.

   PUZZLE.mount({
     mount:    element to build into
     meta:     'Gate 3 of 7 — The Borrowed Frame'
     title:    'The OUGHT: Beneath the Branches'
     imgBase:  '../../images/borrowed/page-'
     imgExt:   '.svg'
     pages:    5
     teaching: ['para one', 'para two']   // optional; shown above the question
     question: 'Tick the ones you brought.'
     hint:     'tick as many as apply'
     options:  [{ value:'a', text:'...' }, ...]
     check:    function(picked) -> html string to route, or null to pass
     level:    the OUGHT level this gate awards
     back:     '../../desk.html'
   })
*/

var PUZZLE = (function () {

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function mount(cfg) {
    var root = cfg.mount || document.body;
    var ext  = cfg.imgExt || '.svg';
    var page = 1;

    // Already through this one? The comics stay. The questions go.
    var cleared = (typeof cfg.level === 'number') &&
                  (typeof QCE !== 'undefined') &&
                  QCE.OUGHT.get() >= cfg.level;

    // ── chrome ──
    root.appendChild(el('p', 'pz-meta', cfg.meta + (cleared ? ' — you have been through this one' : '')));
    root.appendChild(el('h1', null, '<em>' + cfg.title + '</em>'));

    // ── flip-book ──
    var book  = el('div', 'pz-book');
    var plate = el('div', 'pz-plate');
    var img   = document.createElement('img');
    img.alt = '';
    plate.appendChild(img);
    book.appendChild(plate);

    var turn  = el('div', 'pz-turn');
    var count = el('span', 'pz-count');
    var btns  = el('span', 'pz-btns');
    var prev  = el('button', 'pz-btn pz-btn--quiet', '[ back ]');
    var next  = el('button', 'pz-btn', '[ next page ]');
    var skip  = el('button', 'pz-btn pz-btn--quiet', '[ skip to the test ]');
    btns.appendChild(prev); btns.appendChild(next); btns.appendChild(skip);
    turn.appendChild(count); turn.appendChild(btns);
    book.appendChild(turn);
    root.appendChild(book);

    // ── test ──
    var test = el('div', 'pz-test');
    if (cfg.teaching && cfg.teaching.length) {
      var teach = el('div', 'pz-teaching');
      cfg.teaching.forEach(function (para) { teach.appendChild(el('p', null, para)); });
      test.appendChild(teach);
      test.appendChild(el('hr', 'pz-rule'));
    }
    test.appendChild(el('p', 'pz-q', cfg.question));
    if (cfg.hint) test.appendChild(el('p', 'pz-hint', cfg.hint));

    var list = el('ul', 'pz-opts');
    cfg.options.forEach(function (o) {
      var li = document.createElement('li');
      var lab = el('label', 'pz-opt');
      var box = document.createElement('input');
      box.type = 'checkbox'; box.value = o.value;
      lab.appendChild(box);
      lab.appendChild(el('span', null, o.text));
      li.appendChild(lab);
      list.appendChild(li);
    });
    test.appendChild(list);

    var submit = el('button', 'pz-btn', '[ submit ]');
    test.appendChild(submit);
    var route = el('div', 'pz-route');
    test.appendChild(route);
    if (!cleared) root.appendChild(test);
    if (cleared) skip.style.display = 'none';

    var back = el('a', 'pz-back', '&larr; return to the desk');
    back.href = cfg.back || '../../desk.html';
    root.appendChild(back);

    // ── preload so turning never flickers ──
    for (var i = 1; i <= cfg.pages; i++) {
      var pre = new Image();
      pre.src = cfg.imgBase + i + ext;
    }

    function render() {
      img.src = cfg.imgBase + page + ext;
      count.textContent = page + ' / ' + cfg.pages;
      prev.disabled = (page === 1);
      next.textContent = (page === cfg.pages) ? (cleared ? '[ the desk ]' : '[ the test ]') : '[ next page ]';
    }

    function openTest() {
      book.classList.add('is-closed');
      test.classList.add('is-open');
      window.scrollTo(0, 0);
    }

    next.addEventListener('click', function () {
      if (page < cfg.pages) { page++; render(); }
      else if (cleared) { window.location.href = cfg.back || '../../desk.html'; }
      else { openTest(); }
    });
    prev.addEventListener('click', function () {
      if (page > 1) { page--; render(); }
    });
    skip.addEventListener('click', openTest);

    document.addEventListener('keydown', function (e) {
      if (book.classList.contains('is-closed')) return;
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); next.click(); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); prev.click(); }
    });

    submit.addEventListener('click', function () {
      var picked = {};
      var any = false;
      var boxes = test.querySelectorAll('.pz-opt input');
      for (var j = 0; j < boxes.length; j++) {
        picked[boxes[j].value] = boxes[j].checked;
        if (boxes[j].checked) any = true;
      }
      picked.__any = any;

      var msg = cfg.check(picked);
      if (msg) {
        route.innerHTML = msg;
        route.classList.add('is-open');
        return;
      }

      if (typeof cfg.level === 'number' && QCE.OUGHT.get() < cfg.level) {
        QCE.OUGHT.set(cfg.level);
        QCE.TRIPLE.add(1);
      }
      window.location.replace(cfg.back || '../../desk.html');
    });

    render();
  }

  return { mount: mount };
})();
