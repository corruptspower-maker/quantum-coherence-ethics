/* shelf.js — bookshelf render + spine click logic.
   Sets the LIBRARY_ENTERED flag on load (we're in the library).
   Handles the ground spine's 2-second pause before navigation. */

QCE.set(QCE.FLAGS.LIBRARY_ENTERED);

document.addEventListener('DOMContentLoaded', function () {
  var groundSpine = document.querySelector('.spine--ground');
  if (!groundSpine) return;

  groundSpine.addEventListener('click', function (e) {
    e.preventDefault();
    var href = groundSpine.getAttribute('href');
    // Mark the spine as intentionally clicked — not a direct URL visit
    QCE.set(QCE.FLAGS.GROUND_OPENED);
    // Fade out body, then navigate after 2s total
    document.body.style.transition = 'opacity 600ms ease';
    document.body.style.opacity = '0';
    setTimeout(function () {
      window.location.href = href;
    }, 700);
  });
});
