/* gate.js — session traversal enforcement.
   Loaded on every page. Checks that the visitor arrived here legitimately.
   Unauthorized direct access redirects to /. This mirrors MWI: rooms exist,
   but you reach them only through the branching that precedes them. */

var QCE = (function () {
  var FLAGS = {
    LIBRARY_ENTERED:   'qce_library',
    GROUND_OPENED:     'qce_ground',      // spine was clicked (not direct-nav)
    GARDEN_ENTERED:    'qce_garden',      // reached layer-8 prompt in ground.html
    GATE1_PASSED:      'qce_gate1',
    GATE2_PASSED:      'qce_gate2',
    GATE3_PASSED:      'qce_gate3',
    LAYER11_REACHED:   'qce_layer11',
    CLOISTER_CODE_OK:  'qce_cloister'
  };

  function set(flag) {
    try { sessionStorage.setItem(flag, '1'); } catch(e) {}
  }

  function has(flag) {
    try { return sessionStorage.getItem(flag) === '1'; } catch(e) { return false; }
  }

  function redirect(path) {
    window.location.replace(path);
  }

  // Call once per page with the requirement that must be met.
  // If not met, redirect. If met, optionally set a new flag.
  function require(flag, orRedirectTo, thenSet) {
    if (!has(flag)) {
      redirect(orRedirectTo || '/');
      return false;
    }
    if (thenSet) set(thenSet);
    return true;
  }

  // OUGHT_LEVEL — persistent across sessions (localStorage). How far you have read.
  // This does NOT decay. You cannot un-know a gate; the garden door says as much.
  var OUGHT = {
    MAX: 7,
    get: function() {
      try { return parseInt(localStorage.getItem('qce_ought_level') || '0', 10); } catch(e) { return 0; }
    },
    set: function(n) {
      try { localStorage.setItem('qce_ought_level', String(n)); } catch(e) {}
    },
    advance: function() {
      var next = Math.min(this.get() + 1, this.MAX + 1);
      this.set(next);
      return next;
    },
    atMax: function() {
      return this.get() > this.MAX;
    }
  };


  // TRIPLE — the condition of the thing you are tending. Unlike OUGHT, it falls.
  //
  // Not as punishment. Time passes for the downstream instances whether you act
  // or not, so Potential decays untouched — doing nothing is already a reduction.
  // A store that only ever climbs is a running total, which is the aggregation
  // frame the argument rejects. This is the half that can be lost.
  //
  // Nothing announces it. The only place it shows is the bonsai.
  var TRIPLE = {
    KEY:     'qce_triple',
    MAX:     8,
    STEP_MS: 4 * 24 * 60 * 60 * 1000,   // one step of decay every four days

    _read: function () {
      try {
        var raw = localStorage.getItem(this.KEY);
        if (!raw) return null;
        var p = raw.split('|');
        return { v: parseInt(p[0], 10) || 0, t: parseInt(p[1], 10) || Date.now() };
      } catch (e) { return null; }
    },

    _write: function (v, t) {
      try { localStorage.setItem(this.KEY, v + '|' + t); } catch (e) {}
    },

    // Pure read — deliberately never writes, so the clock keeps running while
    // you look at it. Persisting here would reset decay on every page load.
    get: function () {
      var r = this._read();
      if (!r) return 0;
      var lost = Math.floor((Date.now() - r.t) / this.STEP_MS);
      return Math.max(0, Math.min(this.MAX, r.v - lost));
    },

    // Adds to the decayed present value, not the stored one.
    add: function (n) {
      var next = Math.max(0, Math.min(this.MAX, this.get() + (n === undefined ? 1 : n)));
      this._write(next, Date.now());
      return next;
    },

    atMax: function () { return this.get() >= this.MAX; }
  };

  return { set: set, has: has, require: require, FLAGS: FLAGS, OUGHT: OUGHT, TRIPLE: TRIPLE };
})();
