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

  /* ── readings ──────────────────────────────────────────────────────────
     What the reader wrote is classified on submit and the verdict is stored.
     Nothing is reported back on the visit that produced it. The room changes
     on a later visit instead, and by then it cannot be attributed to anything
     in particular. That delay is the whole mechanism, so nothing in here
     returns a verdict to the page that just made one.

     Only the verdict is kept, never the text.
     Storage: qce_read_<id> = JSON [{ ok: bool, f: [modes], t: epoch_ms }, ...]
  */

  function rkey(id) { return 'qce_read_' + id; }

  function readings(id) {
    try {
      var raw = localStorage.getItem(rkey(id));
      if (!raw) return [];
      var a = JSON.parse(raw);
      return Object.prototype.toString.call(a) === '[object Array]' ? a : [];
    } catch (e) { return []; }
  }

  // True once a reading from some earlier visit entered the frame. This is what
  // opens the room, and it never closes again - you cannot un-see the structure.
  function opened(id, visitStart) {
    var r = readings(id);
    for (var i = 0; i < r.length; i++) {
      if (r[i].t < visitStart && r[i].ok) return true;
    }
    return false;
  }

  function wroteThisVisit(id, visitStart) {
    var r = readings(id);
    for (var i = 0; i < r.length; i++) if (r[i].t >= visitStart) return true;
    return false;
  }

  // Records and returns nothing. Deliberately.
  function record(id, verdict) {
    var r = readings(id);
    r.push({ ok: !!verdict.correct_frame,
             f: (verdict.failure_list || []).slice(0, 6),
             t: Date.now() });
    try { localStorage.setItem(rkey(id), JSON.stringify(r)); } catch (e) {}
  }

  return { inherited: inherited, leave: leave, count: count, read: read,
           opened: opened, wroteThisVisit: wroteThisVisit, record: record,
           readings: readings };
})();
