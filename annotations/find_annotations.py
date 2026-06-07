"""
QCE Annotation Finder
Uses OpenRouter to find QCE-relevant passages in each bookshelf book.

Usage:
    py -3 annotations/find_annotations.py hume-treatise
    py -3 annotations/find_annotations.py parfit          # non-PD: quotes only
    py -3 annotations/find_annotations.py --all

Requires:
    OPENROUTER_API_KEY environment variable

Output:
    annotations/{slug}.yaml  (creates or overwrites)
"""

import os, sys, re, json, textwrap, requests, yaml
from pathlib import Path
from openai import OpenAI

ROOT      = Path(__file__).parent.parent
ANNOT_DIR = Path(__file__).parent
QCE_PDF   = ROOT / "assets" / "ground-beneath-the-ought.pdf"

MODEL_PRIMARY  = "deepseek/deepseek-v4-flash:free"
MODEL_FALLBACK = "meta-llama/llama-3.3-70b-instruct:free"

# ── Book registry ──────────────────────────────────────────────────────────
# gutenberg_id=None means non-PD: model uses training knowledge, short quotes only
BOOKS = {
    "bruno":          {"title": "On the Infinite Universe and Worlds", "author": "Giordano Bruno",       "gutenberg_id": None},
    "epictetus":      {"title": "Enchiridion",                          "author": "Epictetus",            "gutenberg_id": 45109},
    "hume-treatise":  {"title": "A Treatise of Human Nature",           "author": "David Hume",           "gutenberg_id": 4705},
    "attar":          {"title": "The Conference of the Birds",          "author": "Farid ud-Din Attar",   "gutenberg_id": 37590},
    "hobbes":         {"title": "Leviathan",                            "author": "Thomas Hobbes",        "gutenberg_id": 3207},
    "coleridge":      {"title": "Biographia Literaria",                 "author": "Samuel Taylor Coleridge", "gutenberg_id": 6081},
    "aristotle":      {"title": "Nicomachean Ethics",                   "author": "Aristotle",            "gutenberg_id": 8438},
    "nietzsche":      {"title": "On the Genealogy of Morality",         "author": "Friedrich Nietzsche",  "gutenberg_id": 52319},
    "spinoza":        {"title": "Ethics",                               "author": "Baruch Spinoza",       "gutenberg_id": 3800},
    "marcus-aurelius":{"title": "Meditations",                          "author": "Marcus Aurelius",      "gutenberg_id": 2680},
    "rumi":           {"title": "The Masnavi",                          "author": "Jalal al-Din Rumi",    "gutenberg_id": 39686},
    "hegel":          {"title": "Phenomenology of Spirit",              "author": "G.W.F. Hegel",         "gutenberg_id": 6763},
    "james-william":  {"title": "The Principles of Psychology",        "author": "William James",        "gutenberg_id": 57628},
    "russell":        {"title": "The Analysis of Mind",                 "author": "Bertrand Russell",     "gutenberg_id": 2529},
    "hafez":          {"title": "Divan of Hafez",                       "author": "Hafez",                "gutenberg_id": 36897},
    "wordsworth":     {"title": "The Prelude",                          "author": "William Wordsworth",   "gutenberg_id": 12383},
    "everett":        {"title": "Relative State Formulation of Quantum Mechanics", "author": "Hugh Everett III", "gutenberg_id": None},
    # Non-PD
    "rand":           {"title": "The Virtue of Selfishness",            "author": "Ayn Rand",             "gutenberg_id": None},
    "whitehead":      {"title": "Process and Reality",                  "author": "Alfred North Whitehead","gutenberg_id": None},
    "wilson":         {"title": "Divided by Infinity",                  "author": "Robert Charles Wilson", "gutenberg_id": None},
    "borges":         {"title": "Ficciones",                            "author": "Jorge Luis Borges",    "gutenberg_id": None},
    "parfit":         {"title": "Reasons and Persons",                  "author": "Derek Parfit",         "gutenberg_id": None},
    "wittgenstein":   {"title": "Philosophical Investigations",         "author": "Ludwig Wittgenstein",  "gutenberg_id": None},
    "danielewski":    {"title": "House of Leaves",                      "author": "Mark Z. Danielewski",  "gutenberg_id": None},
    "calvino":        {"title": "Invisible Cities",                     "author": "Italo Calvino",        "gutenberg_id": None},
    "deutsch":        {"title": "The Fabric of Reality",                "author": "David Deutsch",        "gutenberg_id": None},
    "serafini":       {"title": "Codex Seraphinianus",                  "author": "Luigi Serafini",       "gutenberg_id": None},
}

# ── Helpers ────────────────────────────────────────────────────────────────

def load_qce_context():
    import pdfplumber
    with pdfplumber.open(QCE_PDF) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    text = "\n\n".join(pages).strip()
    words = text.split()
    # Full treatise is ~9400 words — fits entirely; cap at 12000 as a safety limit
    if len(words) > 12000:
        text = " ".join(words[:12000]) + "\n[... truncated ...]"
    return text


def fetch_gutenberg(gutenberg_id):
    url = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        text = r.text
    except Exception:
        # Fallback mirror
        url2 = f"https://gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt"
        r = requests.get(url2, timeout=30)
        r.raise_for_status()
        text = r.text
    # Strip Gutenberg header/footer boilerplate
    start = re.search(r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG", text, re.I)
    end   = re.search(r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG",   text, re.I)
    if start:
        text = text[start.end():]
    if end:
        text = text[:end.start()]
    # Trim to ~15000 words
    words = text.split()
    if len(words) > 15000:
        text = " ".join(words[:15000]) + "\n[... text continues ...]"
    return text.strip()


def build_prompt(book, qce_context, book_text=None):
    is_pd = book_text is not None
    slug_label = f"{book['title']} by {book['author']}"

    if is_pd:
        book_section = f"""
Here is the full text of the book (may be truncated):

<book_text>
{book_text}
</book_text>
"""
        quote_instruction = "Quote the exact passage from the text above."
    else:
        book_section = f"""
This book is not in the public domain. Work from your training knowledge of it.
You MUST use only SHORT quotes (1-3 sentences max) to avoid copyright infringement.
"""
        quote_instruction = "Give only a short 1-3 sentence quote from your training knowledge."

    return f"""You are an annotator for the Quantum Coherence Ethics (QCE) library.

QCE CONTEXT — the full treatise. Read it carefully:
<qce>
{qce_context}
</qce>

CRITICAL — KNOWN MISREADINGS OF QCE. Every model reads this wrong the first time.
Internalize these corrections before you annotate anything:

1. MOTIVATIONAL GAP / THRASYMACHUS
   Wrong: "The framework only closes the Thrasymachus problem if the agent identifies with their full distribution."
   Correct: You EXPERIENCE every branch. Identification is irrelevant. The unjust man will BE in the branches where he faces consequences — he doesn't get to choose. Both branches are him. There is nowhere to hide. (§6.3)

2. "YOUR IS BECOMES YOUR OUGHT"
   Wrong: "This is a universal normative command — it smuggles in an ought from an is, violating Hume."
   Correct: The POSSESSIVE is doing the work. YOUR is becomes YOUR ought. The normative force comes from the INDIVIDUAL'S OWN VALUES, made visible by the correct ontology. The framework is not telling you what to value. It is showing you the structure of what you already value, if you understood what you are. This does NOT cross Hume's guillotine. (§6.1)

3. GOOD AND EVIL (Principle 1)
   Wrong: "'Good is increasing Triple P, evil is decreasing it' is a normative claim that crosses the guillotine."
   Correct: It is a REFERENTIAL claim. Good and evil have never had a concrete referent in any ethical system — every prior attempt ended in circularity or faith. QCE identifies Triple P as the structural floor below which those words have no subject at all. He is GROUNDING the terms for the first time, not deriving an obligation. "If you are going to use the word good, this is what it refers to."

4. THE FRAMEWORK'S SCOPE
   Wrong: "QCE tells you what to do."
   Correct: QCE tells you HOW TO THINK ABOUT what you do. It is a lens, not a command. The ought in the framework is an EPISTEMIC ought — like "you ought to consider that the Earth orbits the Sun." It is the ought of accuracy. Whether you act on it is entirely yours.

5. TRIPLE P IS NOT A VALUE
   Wrong: "The framework says you should increase Triple P because it's good."
   Correct: Triple P is a PRECONDITION of valuation, not a value. Whatever your values are, they require Triple P to have a subject to be about at all. The framework does not tell you which values to have. It identifies what must be present for any values to mean anything.

6. SUFFERING
   Wrong: "The framework dissolves or ignores local suffering."
   Correct: Suffering is LOCAL and REAL. The branch-self in pain is in pain here. Non-Judgment is not indifference — it is epistemic humility about rendering verdict from a vantage point that cannot see the full distribution. "The suffering is seen. The judgment is withheld. These are different acts." (§6.4)

7. PRE-ETHICAL FRAMEWORK
   The document does not claim to be a complete moral system, a decision procedure, or a therapy.
   It identifies PRECONDITIONS. It describes STRUCTURE. It tells you what is actually at stake.
   Everything else — the feelings, the tradeoffs, the lived experience — is yours to find.

Your task: find 3 to 5 passages in "{slug_label}" that are most relevant to QCE — especially:
- The is/ought gap and how QCE resolves it (preconditions, not derivation)
- The nature of the self, identity, and continuity across branches
- Suffering as a structural, ontological fact — local, real, not dissolved
- Triple P as structural precondition of any ethical discourse
- Many-worlds / branching consciousness / distributed being
- The relationship between reason, ethics, and the correct physics

{book_section}

For each passage, return a JSON object in this exact schema:
{{
  "id": "slug-NNN",
  "section": "Book/Part/Chapter name",
  "passage": "{quote_instruction}",
  "gbo_ref": "Section from the QCE treatise most relevant to this connection (e.g. '§2.1', '§4.6', 'Chapter 5'). Only cite a section you actually see in the provided QCE text. If no specific section applies, write 'see treatise'.",
  "label": "short label (3-6 words)",
  "notes": "2-4 sentences explaining how this passage connects to QCE. Be specific — name the concept, name the tension or resonance."
}}

Return a JSON array of 3-5 such objects. No markdown, no explanation, just the raw JSON array.
"""


def call_model(prompt, api_key):
    import time
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    models = [MODEL_PRIMARY, MODEL_FALLBACK]
    for model in models:
        for attempt in range(3):
            try:
                print(f"  Calling {model} (attempt {attempt+1})...")
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=3000,
                )
                return resp.choices[0].message.content
            except Exception as e:
                msg = str(e)
                print(f"  {model} failed: {msg[:120]}")
                if "429" in msg:
                    wait = 45 * (attempt + 1)
                    print(f"  Rate limited — waiting {wait}s...")
                    time.sleep(wait)
                else:
                    break  # non-rate-limit error, try next model
    raise RuntimeError("All models failed after retries.")


def parse_response(text):
    # Strip markdown code fences if present
    text = re.sub(r"^```[a-z]*\n?", "", text.strip(), flags=re.M)
    text = re.sub(r"\n?```$", "", text.strip(), flags=re.M)
    return json.loads(text.strip())


def process_book(slug, api_key, qce_context):
    book = BOOKS[slug]
    out_path = ANNOT_DIR / f"{slug}.yaml"

    if out_path.exists():
        print(f"  {slug}.yaml already exists — skipping (delete to regenerate)")
        return

    print(f"\n{'='*60}")
    print(f"Processing: {book['title']} ({slug})")

    book_text = None
    if book["gutenberg_id"]:
        print(f"  Fetching Gutenberg #{book['gutenberg_id']}...")
        try:
            book_text = fetch_gutenberg(book["gutenberg_id"])
            print(f"  Fetched {len(book_text.split())} words")
        except Exception as e:
            print(f"  Gutenberg fetch failed: {e} — falling back to training knowledge")

    prompt = build_prompt(book, qce_context, book_text)
    raw = call_model(prompt, api_key)

    try:
        annotations = parse_response(raw)
    except json.JSONDecodeError:
        print(f"  JSON parse error. Raw response saved to {slug}-raw.txt")
        (ANNOT_DIR / f"{slug}-raw.txt").write_text(raw, encoding="utf-8")
        return

    doc = {
        "book": slug,
        "title": book["title"],
        "author": book["author"],
        "gutenberg_id": book["gutenberg_id"],
        "annotations": annotations,
    }
    out_path.write_text(yaml.dump(doc, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    print(f"  Wrote {len(annotations)} annotations to {out_path.name}")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("ERROR: Set the OPENROUTER_API_KEY environment variable first.")

    args = sys.argv[1:]
    if not args:
        print("Usage: py -3 annotations/find_annotations.py <slug>")
        print("       py -3 annotations/find_annotations.py --all")
        sys.exit(1)

    print("Loading QCE context...")
    qce_context = load_qce_context()
    print(f"  {len(qce_context.split())} words loaded")

    slugs = list(BOOKS.keys()) if "--all" in args else args

    import time
    for i, slug in enumerate(slugs):
        if slug not in BOOKS:
            print(f"Unknown slug: {slug}. Available: {', '.join(BOOKS)}")
            continue
        process_book(slug, api_key, qce_context)
        if i < len(slugs) - 1:
            time.sleep(8)  # brief pause between books

    print("\nDone.")


if __name__ == "__main__":
    main()
