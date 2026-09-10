/* room.js — persistence for the interior.
   Rooms remember. What you leave is not shown back to you on the visit you
   leave it; it is furniture the next time you are here. That delay is the
   point, so nothing in this file reports a placement back to the page that
   made it.

   Storage: qce_room_<id> = JSON [{ o: objectId, t: epoch_ms }, ...]
*/

var ROOM = (function () {

  function key(id) { return 'qce_room_' + id; }

  function read(id) {
    try {
      var raw = localStorage.getItem(key(id));
      if (!raw) return [];
      var a = JSON.parse(raw);
      return Object.prototype.toString.call(a) === '[object Array]' ? a : [];
    } catch (e) { return []; }
  }

  function write(id, list) {
    try { localStorage.setItem(key(id), JSON.stringify(list)); } catch (e) {}
  }

  // Everything left on any visit before this one. The current visit's own
  // placement is deliberately excluded — see the note at the top.
  function inherited(id, visitStart) {
    return read(id).filter(function (r) { return r.t < visitStart; });
  }

  // One placement per visit. Returns false if this visit already left something.
  function leave(id, objectId, visitStart) {
    var list = read(id);
    for (var i = 0; i < list.length; i++) {
      if (list[i].t >= visitStart) return false;
    }
    list.push({ o: objectId, t: Date.now() });
    write(id, list);
    return true;
  }

  function count(id) { return read(id).length; }

  return { inherited: inherited, leave: leave, count: count, read: read };
})();
