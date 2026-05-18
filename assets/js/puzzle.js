/* puzzle.js — gate puzzle logic. Hash-based, no server needed.
   Gate 2 (layer-5): w(omega|a) question
   Gate 3 (layer-8): Parfit identity question */

function checkGate2(input) {
  var v = input.trim().toLowerCase();
  return v.indexOf('born') !== -1 ||
         v.indexOf('weight') !== -1 ||
         v.indexOf('measure') !== -1 ||
         v.indexOf('reality') !== -1;
}

function checkGate3(input) {
  var v = input.trim().toLowerCase();
  return v.indexOf('substrate') !== -1 ||
         v.indexOf('substance') !== -1 ||
         v.indexOf('fiction') !== -1 ||
         v.indexOf('doer') !== -1 ||
         v.indexOf('underlying') !== -1;
}
