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
from bs4 import BeautifulSoup
from openai import OpenAI

ROOT      = Path(__file__).parent.parent
ANNOT_DIR = Path(__file__).parent
QCE_HTML  = ROOT / "treatise.html"

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
    html = QCE_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Trim to ~8000 words so it fits comfortably in context
    words = text.split()
    if len(words) > 8000:
        text = " ".join(words[:8000]) + "\n[... truncated for context ...]"
    return text.strip()


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

QCE CONTEXT — read this carefully before annotating:
<qce>
{qce_context}
</qce>

Your task: find 3 to 5 passages in "{slug_label}" that are most relevant to QCE concepts — especially:
- The is/ought gap and how QCE resolves it through branching reality
- The nature of the self, identity, and continuity across branches
- Suffering as an ontological fact rather than a preference
- The canonical threshold for ethical action
- Many-worlds / branching consciousness
- The relationship between reason, ethics, and structure

{book_section}

For each passage, return a JSON object in this exact schema:
{{
  "id": "slug-NNN",
  "section": "Book/Part/Chapter name",
  "passage": "{quote_instruction}",
  "gbo_ref": "GBO X.Y",
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
