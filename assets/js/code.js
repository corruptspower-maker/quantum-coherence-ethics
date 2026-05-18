/* code.js — shared month-code generator.
   Imported by both layer-11 (display) and cloister/gate.html (validate).
   One source of truth. If these diverge, the gate is broken. */

function getMonthCode() {
  var now = new Date();
  // Format: "MMYYYY" e.g. "052026"
  var seed = String(now.getMonth() + 1).padStart(2, '0') + String(now.getFullYear());
  return hashToCode(seed);
}

// Stable, deterministic 8-char alphanumeric from a seed string.
// Not cryptographic — just stable. Same seed, same code, every time.
function hashToCode(seed) {
  var h = 0;
  for (var i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  }
  // Make it positive, then base-36 encode, pad/trim to 8 chars
  var unsigned = (h >>> 0).toString(36).toUpperCase();
  // Ensure exactly 8 chars by cycling the seed through again if short
  var full = unsigned;
  var s2 = seed + seed;
  while (full.length < 8) {
    var h2 = 0;
    for (var j = 0; j < s2.length; j++) {
      h2 = (Math.imul(17, h2) + s2.charCodeAt(j)) | 0;
    }
    full += (h2 >>> 0).toString(36).toUpperCase();
  }
  return full.slice(0, 8);
}

function validateCode(input) {
  return input.trim().toUpperCase() === getMonthCode();
}
