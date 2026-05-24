/* inquisitor.js — Grand Inquisitor gate logic for The Ought Beneath the Branches.
   Manages iteration state, calls the worker endpoint, returns verdict.
   Set window.QCE_WORKER_URL before this script loads to point at your
   Cloudflare Worker. */

var INQUISITOR = (function () {
  var MAX_ITER  = 8;
  var MODEL     = 'claude-haiku-4-5-20251001';
  var API_URL   = window.QCE_WORKER_URL || '';

  var PRESSURES = [
    'Read it again carefully.',
    'I push back on everything you said. Read it again.',
    'Are you sure that is what it says? Read it again.',
    'You are reading it in the wrong frame. The answers are in there. Read it again.',
    'You missed something important. Everything you need is in there.',
    'No. That is not what it says. Read it again from the beginning.',
    'If that were true, the whole argument would collapse. It does not. Read it again.',
    'The relationship runs in one direction. You have it backwards. Read it again.'
  ];

  function getIter() {
    try { return parseInt(sessionStorage.getItem('qce_ought_iter') || '0', 10); } catch(e) { return 0; }
  }

  function setIter(n) {
    try { sessionStorage.setItem('qce_ought_iter', String(n)); } catch(e) {}
  }

  function resetIter() { setIter(0); }

  function buildSystemPrompt(levelConfig, iter) {
    var pressure = PRESSURES[Math.min(iter - 1, PRESSURES.length - 1)];
    return [
      'You are the Grand Inquisitor. You do not explain, correct, or guide.',
      'You evaluate whether a reader has cleared a specific conceptual blockage.',
      'Respond ONLY with a single valid JSON object on one line. No explanation before or after.',
      'Format: {"verdict":"pass","message":"..."} or {"verdict":"pressure","message":"..."}',
      '',
      'BLOCKAGE THIS GATE TESTS:',
      levelConfig.blockage_description,
      '',
      'WHAT FAILURE LOOKS LIKE:',
      levelConfig.failure_description,
      '',
      'WHAT PASSAGE LOOKS LIKE:',
      levelConfig.passage_description,
      '',
      'ITERATION: ' + iter + ' of ' + MAX_ITER + '.',
      'If verdict is "pressure": the message MUST be exactly this — ' + pressure,
      'If verdict is "pass": the message is one brief sentence, present tense.',
      'No praise. No meta-commentary. No explanation of why they passed.',
      'Output ONLY the JSON object.'
    ].join('\n');
  }

  async function submit(levelConfig, responseText) {
    if (!API_URL) throw new Error('Worker URL not configured.');

    var iter = getIter() + 1;
    setIter(iter);

    var resp;
    try {
      resp = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: MODEL,
          max_tokens: 200,
          system: buildSystemPrompt(levelConfig, iter),
          messages: [{ role: 'user', content: responseText }]
        })
      });
    } catch(e) {
      throw new Error('Could not reach the gate. Check your connection.');
    }

    if (!resp.ok) {
      var errData = {};
      try { errData = await resp.json(); } catch(_) {}
      throw new Error('Gate error ' + resp.status + ': ' + (errData.error && errData.error.message || ''));
    }

    var data = await resp.json();
    var text = data.content && data.content[0] && data.content[0].text || '';

    // Strip code fences if model wrapped response
    text = text.replace(/```json\s*/gi, '').replace(/```\s*/g, '').trim();

    try {
      var result = JSON.parse(text);
      if (result.verdict !== 'pass' && result.verdict !== 'pressure') result.verdict = 'pressure';
      if (!result.message) result.message = PRESSURES[Math.min(iter - 1, PRESSURES.length - 1)];
      return { verdict: result.verdict, message: result.message, iter: iter };
    } catch(e) {
      // Fallback: if we can't parse JSON, check text for pass signal
      var verdict = /\bpass\b/i.test(text) ? 'pass' : 'pressure';
      return {
        verdict: verdict,
        message: verdict === 'pressure' ? PRESSURES[Math.min(iter - 1, PRESSURES.length - 1)] : text.slice(0, 120),
        iter: iter
      };
    }
  }

  function maxed() {
    return getIter() >= MAX_ITER;
  }

  return {
    submit: submit,
    resetIter: resetIter,
    maxed: maxed,
    MAX_ITER: MAX_ITER
  };
})();
