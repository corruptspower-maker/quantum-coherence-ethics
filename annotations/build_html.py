"""
QCE Annotation HTML Builder
Converts annotations/{slug}.yaml -> library/books/{slug}.html

Usage:
    py -3 annotations/build_html.py hume-treatise
    py -3 annotations/build_html.py --all
"""

import sys, yaml
from pathlib import Path

ROOT      = Path(__file__).parent.parent
ANNOT_DIR = Path(__file__).parent
OUT_DIR   = ROOT / "library" / "books"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GUTENBERG_BASE = "https://www.gutenberg.org/ebooks/"
AMAZON_BASE    = "https://www.amazon.com/s?k="


def gutenberg_link(gutenberg_id, title, author):
    if gutenberg_id:
        return f'<a href="{GUTENBERG_BASE}{gutenberg_id}" target="_blank" rel="noopener">Read the full text on Project Gutenberg &rarr;</a>'
    query = f"{title} {author}".replace(" ", "+")
    return f'<a href="{AMAZON_BASE}{query}" target="_blank" rel="noopener">Find this book &rarr;</a>'


def build_page(doc):
    slug        = doc["book"]
    title       = doc["title"]
    author      = doc["author"]
    gutenberg_id= doc.get("gutenberg_id")
    annotations = doc.get("annotations", [])

    annotation_html = ""
    for a in annotations:
        passage = str(a.get("passage", "")).replace("\n", "<br>")
        notes   = str(a.get("notes", ""))
        section = str(a.get("section", ""))
        gbo_ref = str(a.get("gbo_ref", ""))
        label   = str(a.get("label", ""))

        annotation_html += f"""
    <div class="annotation-block">
      <div class="passage-wrap">
        <p class="section-label">{section}</p>
        <blockquote class="passage">{passage}</blockquote>
      </div>
      <aside class="margin-note">
        <p class="note-label">{label}</p>
        <p class="note-text">{notes}</p>
        <p class="gbo-ref">{gbo_ref}</p>
      </aside>
    </div>
"""

    full_text_link = gutenberg_link(gutenberg_id, title, author)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>{title} — QCE Library</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: 'EB Garamond', Georgia, serif;
      font-size: 1.05rem;
      line-height: 1.75;
      color: #1a1916;
      background: #fdfcf8;
      padding: 3rem 1.5rem 5rem;
    }}

    .page {{
      max-width: 860px;
      margin: 0 auto;
    }}

    header {{
      border-bottom: 1px solid #d3d1c7;
      padding-bottom: 1.5rem;
      margin-bottom: 3rem;
    }}

    header h1 {{
      font-size: 1.8rem;
      font-weight: 500;
      line-height: 1.2;
      margin-bottom: 0.3rem;
    }}

    header .author {{
      font-family: 'Courier New', monospace;
      font-size: 0.78rem;
      color: #888780;
      letter-spacing: 0.08em;
    }}

    .annotation-block {{
      display: grid;
      grid-template-columns: 1fr 260px;
      gap: 2rem;
      margin-bottom: 3.5rem;
      padding-bottom: 3.5rem;
      border-bottom: 0.5px solid #e0ddd4;
    }}

    .section-label {{
      font-family: 'Courier New', monospace;
      font-size: 0.72rem;
      color: #888780;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 0.8rem;
    }}

    blockquote.passage {{
      font-style: italic;
      color: #2a2820;
      padding-left: 1.2rem;
      border-left: 3px solid #d3d1c7;
      line-height: 1.8;
    }}

    .margin-note {{
      padding-left: 1.5rem;
      border-left: 2px solid #534AB7;
    }}

    .note-label {{
      font-family: 'Courier New', monospace;
      font-size: 0.72rem;
      color: #534AB7;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 0.5rem;
    }}

    .note-text {{
      font-size: 0.9rem;
      line-height: 1.65;
      color: #3a3830;
      margin-bottom: 0.8rem;
    }}

    .gbo-ref {{
      font-family: 'Courier New', monospace;
      font-size: 0.68rem;
      color: #888780;
      letter-spacing: 0.06em;
    }}

    footer {{
      margin-top: 2rem;
      padding-top: 2rem;
      border-top: 1px solid #d3d1c7;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }}

    footer a {{
      font-family: 'Courier New', monospace;
      font-size: 0.78rem;
      color: #534AB7;
      text-decoration: none;
      letter-spacing: 0.05em;
    }}

    footer a:hover {{ text-decoration: underline; }}

    @media (max-width: 640px) {{
      .annotation-block {{
        grid-template-columns: 1fr;
      }}
      .margin-note {{
        border-left: none;
        border-top: 2px solid #534AB7;
        padding-left: 0;
        padding-top: 1rem;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <h1>{title}</h1>
      <p class="author">{author}</p>
    </header>

    {annotation_html}

    <footer>
      <a href="../../shelf.html">&larr; back to the shelf</a>
      {full_text_link}
    </footer>
  </div>

  <script src="../../assets/js/gate.js"></script>
  <script>
    QCE.require(QCE.FLAGS.LIBRARY_ENTERED, '/');
  </script>
</body>
</html>
"""


def process(slug):
    yaml_path = ANNOT_DIR / f"{slug}.yaml"
    if not yaml_path.exists():
        print(f"  No YAML found for {slug} — run find_annotations.py first")
        return
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    html = build_page(doc)
    out  = OUT_DIR / f"{slug}.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Wrote {out}")


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: py -3 annotations/build_html.py <slug>")
        print("       py -3 annotations/build_html.py --all")
        sys.exit(1)

    if "--all" in args:
        slugs = [p.stem for p in ANNOT_DIR.glob("*.yaml") if p.stem not in ("hume-treatise",)]
        slugs = [p.stem for p in ANNOT_DIR.glob("*.yaml")]
    else:
        slugs = args

    for slug in slugs:
        process(slug)
    print("Done.")


if __name__ == "__main__":
    main()
