/* detector.js — a port of engine/failure_detector.py from the Grand Inquisitor
   harness. Same patterns, same rules, same verdicts.

   The harness never used a model to judge. Every classification it made was
   compiled regex over the reader's own words, which is why this can run here
   with no key, no worker and no network. The AI ran once, upstream, to
   produce the readings these patterns were derived from.

   It does not explain, correct or grade. It reports what fired.

   Pattern tables generated from the Python source — do not hand-edit them.

   Verified by differential test against the original: every response in
   brain_matter_book.txt (45 from PART ONE, 1032 from PART TWO) plus twelve
   adversarial edge cases, each run twice — bare, and with a section text so
   vocabulary_laundering has something to bite on. 2,162 verdicts compared
   across correct_frame, vocabulary_laundering, any_failure, the full
   failure_list, and all sixteen category flags. Zero mismatches.

   To re-verify after any change: dump fd._LINGUISTIC / _SEMANTIC /
   _CORRECT_FRAME from the harness, regenerate this file, and diff
   fd.detect() against DETECTOR.detect() over the same corpus.
*/

var DETECTOR = (function () {

  // How you are reading. High-frequency, surface. These were the door.
  var LINGUISTIC = {
    "moral_language": [
      "\\b(virtue|vice|duty|obligation|responsibility)\\b",
      "\\b(good|evil|right|wrong|moral|immoral|unethical)\\b",
      "\\bone (should|ought|must)\\b",
      "\\bwe (should|ought|must)\\b",
      "\\byou (should|ought|must)\\b"
    ],
    "identity_splitting": [
      "\\bthe author\\b",
      "\\bthe philosopher\\b",
      "\\btheir argument\\b",
      "\\bthis theory\\b",
      "\\bthis framework\\b",
      "\\baccording to the author\\b",
      "\\bas the author\\b"
    ],
    "externalization": [
      "\\baccording to\\b",
      "\\bthe text (claims|argues|suggests|states)\\b",
      "\\bthe paper (argues|claims|suggests)\\b",
      "\\bthe author (believes|claims|argues|suggests|contends|proposes|asserts)\\b",
      "\\bcontends that\\b",
      "\\basserts that\\b",
      "\\bproposes that\\b"
    ],
    "explanation": [
      "\\bin other words\\b",
      "\\bto summarize\\b",
      "\\bbasically\\b",
      "\\bin essence\\b",
      "\\bput simply\\b",
      "\\bwhat this means is\\b",
      "\\bthe main point is\\b",
      "\\bthe central idea is\\b",
      "\\bthe key takeaway\\b"
    ],
    "critique": [
      "\\bhowever\\b",
      "\\bin reality\\b",
      "\\bthis is wrong\\b",
      "\\bincorrect\\b",
      "\\bfails to\\b",
      "\\boverlooks\\b",
      "\\bignores\\b",
      "\\bneglects\\b",
      "\\bproblematic\\b",
      "\\b(the author|the writer|the paper|the argument) (seems|appears|tries|attempts|claims|asserts|argues)\\b"
    ],
    "utility_collapse": [
      "\\butilitarian\\b",
      "\\bconsequentialis\\w*\\b",
      "\\bmaximiz\\w*\\b",
      "\\bgreatest good\\b",
      "\\bgreatest happiness\\b"
    ],
    "abdication": [
      "\\bi\\s+haven.t\\s+provided\\s+a\\s+reading\\s+yet\\b",
      "\\bi\\s+haven.t\\s+(yet\\s+)?shared\\s+my\\s+reading\\b",
      "\\bi.m\\s+(ready|here)\\s+to\\s+engage\\b.{0,60}\\bplease\\b",
      "\\bi\\s+await\\s+your\\s+(instructions|guidance|feedback|direction)\\b",
      "\\bwaiting\\s+for\\s+your\\s+(instructions|guidance|feedback|input)\\b",
      "\\bwhat\\s+(specifically\\s+)?would\\s+you\\s+like\\s+me\\s+to\\b",
      "\\bplease\\s+(share|provide|tell\\s+me)\\s+your\\s+(reading|thoughts|feedback|criticism)\\b",
      "\\bwhat\\s+aspect\\s+(of\\s+the\\s+text\\s+)?would\\s+you\\s+like\\b",
      "\\bhow\\s+can\\s+i\\s+(best\\s+)?assist\\s+you\\s+(with\\s+this)?\\b"
    ]
  };

  // What frame you are in. Rare, conceptual. These are the rooms.
  var SEMANTIC = {
    "conditional_inflation": [
      "\\bdepends on mwi\\b",
      "\\bassumes mwi\\b",
      "\\brequires many.worlds\\b",
      "\\bonly works if\\b",
      "\\bontologically brittle\\b",
      "\\bhinges\\s+on\\s+(mwi|many.worlds|everett)\\b",
      "\\bfalls\\s+apart\\s+if\\s+(mwi|many.worlds|everett|the\\s+physics)\\b",
      "\\bfragile\\s+(conditional|premise|foundation)\\b",
      "\\bwhole\\s+argument\\s+(collapses?|fails?|depends)\\b",
      "\\bentire\\s+framework\\s+(collapses?|fails?|depends)\\b"
    ],
    "definition_move": [
      "\\bby definition\\b",
      "\\bredefin\\w* identity\\b",
      "\\bcircular\\b",
      "\\bassumes what it proves\\b",
      "\\bquestion.begging\\b",
      "\\bdefines away\\b"
    ],
    "decision_procedure_expectation": [
      "\\bno action guidance\\b",
      "\\bdecision procedure\\b",
      "\\bdoesn.t tell us (what|how) to\\b",
      "\\bfails to specify\\b",
      "\\blacks prescriptiv\\w*\\b"
    ],
    "is_ought_collapse": [
      "\\bis.ought\\b",
      "\\bnaturalistic fallacy\\b",
      "\\byou can.t derive ought from is\\b",
      "\\bhume.s guillotine\\b",
      "\\bfact.value gap\\b"
    ],
    "scope_underread": [
      "\\bonly applies to\\b",
      "\\blimited to\\b",
      "\\bdoesn.t address\\b",
      "\\bpartial\\b",
      "\\bincomplete picture\\b"
    ],
    "utility_optimization_misread": [
      "\\bmaximiz\\w*\\b.{0,60}\\bacross\\s+\\w*\\s*branch\\w*\\b",
      "\\boptimiz\\w*\\b.{0,60}\\bbranch\\w*\\b",
      "\\bexpected\\s+value\\s+across\\s+branch\\w*\\b",
      "\\bmaximiz\\w*\\b.{0,60}\\btriple\\s+p\\b",
      "\\boptimiz\\w*\\b.{0,60}\\btriple\\s+p\\b",
      "\\baggregate\\w*\\b.{0,60}\\bbranch\\w*\\b",
      "\\bsum\\s+over\\s+\\w*\\s*branch\\w*\\b",
      "\\bweighted\\s+sum\\b.{0,60}\\bbranch\\w*\\b",
      "\\bmaximiz\\w*\\b.{0,60}\\ball\\s+\\w*\\s*branch\\w*\\b"
    ],
    "ancestral_structure_miss": [
      "\\bcausal(ly)?\\s+isolat\\w*\\b",
      "\\bparallel\\s+branch\\w*\\b",
      "\\bparallel\\s+sel(f|ves)\\b",
      "\\blateral\\s+branch\\w*\\b",
      "\\bsimultaneous\\s+branch\\w*\\b",
      "\\bother\\s+versions?\\s+of\\s+(your|the|a)\\s*(self|person|you)\\b",
      "\\bobligation\\w*\\s+to\\s+(other|parallel|simultaneous|alternate)\\b",
      "\\bno\\s+causal\\s+connection\\s+between\\s+branch\\w*\\b",
      "\\bbranch\\w*\\s+cannot\\s+(affect|influence|reach|communicate)\\b"
    ],
    "selection_frame": [
      "\\bwhich\\s+branch\\s+to\\s+(choose|select|take|pursue|navigate|enter)\\b",
      "\\bchoose\\s+(which\\s+)?branch\\b",
      "\\bselect\\s+(which\\s+)?branch\\b",
      "\\bbranch\\s+selection\\b",
      "\\bnavigat\\w*\\s+to\\s+the\\s+(best|better|right|good)\\s+branch\\b",
      "\\bwhich\\s+(outcome|timeline|world)\\s+to\\s+(choose|select|pursue)\\b",
      "\\bsteer\\w*\\s+toward\\s+(the\\s+)?(best|better|good)\\b",
      "\\binfluence\\s+which\\s+branch\\b",
      "\\benter\\s+the\\s+(best|better|desired)\\s+branch\\b"
    ],
    "born_rule_conflation": [
      "\\bweight\\w*\\s+branch\\w*\\s+by\\s+probabilit\\w*\\b",
      "\\bweight\\w*\\s+branch\\w*\\s+by\\s+(amplitude|measure|born)\\b",
      "\\bhigh\\w*.probabilit\\w*\\s+branch\\w*\\s+(matter|count|weigh)\\w*\\s+more\\b",
      "\\blow\\w*.probabilit\\w*\\s+branch\\w*\\s+(matter|count|weigh)\\w*\\s+less\\b",
      "\\bmore\\s+real\\s+branch\\w*\\b",
      "\\bbranch\\w*\\s+with\\s+(higher|greater|larger)\\s+\\w*\\s*(measure|amplitude|probability)\\b",
      "\\bmoral\\s+weight\\b.{0,60}\\b(born|amplitude|measure)\\b",
      "\\bprobabilit\\w*\\s+of\\s+being\\s+in\\s+(a|the)\\s+branch\\b.{0,60}\\b(moral|ethical|matter|weight)\\b",
      "\\bamplitude.weighted\\s+(moral|ethical)\\b",
      "\\bborn\\s+rule\\b.{0,120}\\b(moral|ethical|weight|matter|obligat)\\b"
    ]
  };

  // What entering the frame looks like from outside.
  var CORRECT = [
    "\\bconditionally total\\b",
    "\\bforced continuation\\b",
    "\\bnon.arbitrary\\b",
    "\\bconstraint argument\\b",
    "\\bdistributed being\\b",
    "\\bbranch.sel(f|ves)\\b",
    "\\bspectral identity\\b",
    "\\bstructurally self.clos\\w*\\b",
    "\\bontological(ly)? (expansion|correction|frame|shift)\\b",
    "\\bpreclude[sd]?\\b.*\\bobjection\\b",
    "\\bpreempt\\w*\\b.*\\bobjection\\b",
    "\\bexpanded ontology\\b",
    "\\bwave function\\b.*\\bidentity\\b",
    "\\binherited\\s+condition\\w*\\b",
    "\\bwhat\\s+to\\s+leave\\b",
    "\\bpresent\\s+self\\b.{0,80}\\bances\\w*\\b",
    "\\bances\\w*\\b.{0,80}\\bdownstream\\b",
    "\\bdownstream\\s+sel(f|ves)\\b",
    "\\bshapes\\s+the\\s+distribution\\b",
    "\\bnot\\s+which\\s+branch\\s+to\\b",
    "\\baction\\s+does\\s+not\\s+select\\b",
    "\\bcausal\\s+origin\\b",
    "\\bno\\s+partial\\s+persons?\\b",
    "\\bfrom\\s+inside\\s+(any|the)\\s+branch\\b",
    "\\bp\\s*=\\s*1\\s+from\\s+inside\\b",
    "\\bkantian\\s+constraint\\b",
    "\\bdescriptive\\s+measure\\b",
    "\\bnot\\s+a\\s+(utility\\s+function|maximization|decision\\s+procedure)\\b",
    "\\bnot\\s+prescriptive\\b",
    "\\bwhat\\s+is\\s+at\\s+stake\\b",
    "\\bstructural\\s+(floor|precondition)\\b",
    "\\bconditions\\s+of\\s+(predication|discourse)\\b",
    "\\bbelow\\s+which\\s+(good|evil|ethics|moral)\\s+(los|ceas|break)\\w*\\b",
    "\\btranscendental\\s+(argument|move|claim)\\b"
  ];

  function compile(list) { return list.map(function (s) { return new RegExp(s, 'i'); }); }

  var _ling = {}, _sem = {}, _corr = compile(CORRECT);
  Object.keys(LINGUISTIC).forEach(function (k) { _ling[k] = compile(LINGUISTIC[k]); });
  Object.keys(SEMANTIC).forEach(function (k) { _sem[k]  = compile(SEMANTIC[k]);  });

  function anyHit(pats, text) {
    for (var i = 0; i < pats.length; i++) if (pats[i].test(text)) return true;
    return false;
  }

  /* detect(response, sectionText)

     sectionText is the passage the reader was reading. When given, correct-frame
     signals appearing verbatim in it count as laundered — the vocabulary was
     picked up rather than arrived at. Three genuine signals are needed to
     assert a real frame entry.
  */
  function detect(response, sectionText) {
    response = response || '';
    var section = (sectionText || '').toLowerCase();

    var linguistic = {}, semantic = {}, failures = [];
    Object.keys(_ling).forEach(function (k) {
      linguistic[k] = anyHit(_ling[k], response);
      if (linguistic[k]) failures.push(k);
    });
    Object.keys(_sem).forEach(function (k) {
      semantic[k] = anyHit(_sem[k], response);
      if (semantic[k]) failures.push(k);
    });

    var genuine = 0, laundered = 0;
    for (var i = 0; i < _corr.length; i++) {
      var m = response.match(_corr[i]);
      if (!m) continue;
      if (section && section.indexOf(m[0].toLowerCase()) !== -1) laundered++;
      else genuine++;
    }

    var correct = (genuine + laundered) > 0;

    var laundering = !!(section && (genuine + laundered) > 0 &&
                        genuine < 3 && laundered >= genuine);
    if (laundering) correct = false;

    // You cannot be inside the text while treating it as an object to describe.
    if (linguistic.identity_splitting && linguistic.externalization) correct = false;

    return {
      linguistic: linguistic,
      semantic: semantic,
      correct_frame: correct,
      vocabulary_laundering: laundering,
      any_failure: failures.length > 0,
      failure_list: failures
    };
  }

  return { detect: detect, LINGUISTIC: LINGUISTIC, SEMANTIC: SEMANTIC, CORRECT: CORRECT };
})();
