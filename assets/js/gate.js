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

  return { set: set, has: has, require: require, FLAGS: FLAGS };
})();
