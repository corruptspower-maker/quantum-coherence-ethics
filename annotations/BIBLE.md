# QCE Annotated Library — Style Bible

The definitive specification for every annotated book in the QCE library.
All books follow this exactly. Update here first, then regenerate.

---

## Page Layout

- **Page size:** Letter (8.5 × 11 in) — 612 × 792 pt
- **Left margin:** 72 pt (1 in) — body text begins here
- **Right margin:** 216 pt (3 in) — annotation zone lives here
- **Top margin:** 72 pt
- **Bottom margin:** 72 pt
- **Text column width:** ~324 pt (~4.5 in)
- **Annotation zone width:** 180 pt (~2.5 in), starting 18 pt past text column

The wide right margin is the whole point. The book breathes left. The conversation happens right.

---

## Main Text Typography

- **Font:** EB Garamond (or Georgia as fallback) — same family as the site
- **Size:** 11 pt
- **Leading:** 16 pt (1.45 ratio)
- **Color:** #1a1916 (near-black, same as site ink color)
- **Paragraph indent:** 24 pt first line, no space between paragraphs
- **Section breaks:** Extra 12 pt space, centered em-dash separator

---

## Page Header / Footer

- **Header:** Book title (left) · Author (right) — 8 pt Courier, #888780, hairline rule below
- **Footer:** Page number centered — 8 pt Courier, #888780
- **Header/footer margin:** 36 pt from page edge

---

## Annotation Style

### Font
- **Family:** "Caveat" (Google Fonts) — natural handwriting, fully legible
- **Size:** 8.5 pt
- **Color:** #5c3a1e (warm dark brown — aged ink)
- **Leading:** 12 pt

### Format
Every annotation follows this exact pattern:

```
GBO X.X — Label text
```

- **GBO X.X** = citation prefix (bold or slightly larger, same color)
- **—** = em-dash separator
- **Label text** = one short clause, lowercase, no period
- The entire annotation is a hyperlink to the Connections Book entry for that GBO reference

### Placement
- Right margin, vertically aligned to the middle of the cited passage
- If two annotations are close, stack with 6 pt gap between them
- A thin hairline (0.25 pt, #b09070) runs from the end of the cited line to the annotation text — a lead line

### Cited passage
- The passage being annotated gets a faint underline in the main text: 0.4 pt, #c09040 (same gold as the site's parchment background)
- No highlighting, no brackets — just the underline

---

## Citation Prefix System

All annotations use GBO references — chapters and sections from *The Ground Beneath the Ought*.

| Prefix | Meaning |
|--------|---------|
| GBO 1.x | The Branching Postulate |
| GBO 2.x | Observer Identity Across Branches |
| GBO 3.x | Suffering Density and Moral Weight |
| GBO 4.x | The Canonical Threshold |
| GBO 5.x | Collapse of Standard Ethics |
| GBO 6.x | Preconditions and the Is/Ought Problem |
| GBO 7.x | The Coherence Criterion |
| GBO 8.x | Application and Edge Cases |
| GBO 9.x | Implications for Personal Identity |
| GBO 10.x | The Ground Itself |
| GBO 11.x | Layer Eleven (reserved) |

Sub-sections (.1, .2, .3 ...) to be assigned as the Connections Book grows.

---

## Page Background

- **Color:** #faf8f2 — pale ivory, slightly warm, not dramatically aged
- Not parchment. Not clinical white. The annotations are the aged element; the page is neutral.

---

## YAML Annotation Schema

Each book has its own YAML file in `/annotations/`. Schema:

```yaml
book: hume-treatise          # slug — matches filename
title: A Treatise of Human Nature
author: David Hume
gutenberg_id: 4705

annotations:
  - id: hume-001
    part: "Book III"
    section: "Part I, Section I"
    passage: "In every system of morality which I have hitherto met with..."
    passage_end: "...an ought, or an ought not."
    gbo_ref: "GBO 6.1"
    label: "preconditions before norm claim"
    connections_entry: gbo-6-1-is-ought
    notes: >
      The classic is/ought gap. QCE closes it not by deriving ought from
      is in the classical sense, but by grounding the canonical threshold
      in the ontological structure of branching — suffering IS the
      invariant across branches, and from that invariant the threshold
      emerges without a logical leap.
```

The `notes` field is for your working thinking — it feeds the Connections Book entry, not the margin itself.

---

## Connections Book

A single document: `connections/CONNECTIONS.md` (source) → `connections/connections.pdf` (generated).

### Entry format

```
GBO 6.1 — Preconditions Before a Norm Claim
────────────────────────────────────────────
The is/ought problem, as Hume states it: you cannot derive a normative
claim from purely descriptive premises without an unacknowledged step.
QCE addresses this by...

[full paragraph explanation]

Appears in:
  · Hume, A Treatise of Human Nature — Book III, Part I, §I (p. 302)
  · [other books as found]
```

The cross-reference list at the bottom of each entry is generated automatically from the YAML files.

---

## File Structure

```
annotations/
  BIBLE.md                  ← this document
  hume-treatise.yaml        ← Hume annotations
  aristotle-ethics.yaml     ← (future)
  ...

connections/
  CONNECTIONS.md            ← source for Connections Book
  connections.pdf           ← generated

assets/books/
  hume-treatise.pdf         ← generated annotated PDF
  ...
```

---

## Complete Workflow

### Adding a new annotation
1. Open `annotations/<book>.yaml`
2. Add an entry with: passage text, gbo_ref, label, connections_entry ID, notes
3. Run `py -3 annotations/build.py <book>` — PDF rebuilds in seconds
4. If the connections_entry ID is new, add the entry to `connections/CONNECTIONS.md`
5. Run `py -3 annotations/build_connections.py` — Connections Book PDF rebuilds
6. `git add -A && git commit && git push` — both PDFs live on the site

### Adding a new book
1. Drop the Gutenberg plain text into `annotations/<slug>.txt`
2. Create `annotations/<slug>.yaml` with book metadata and empty annotations list
3. Run `py -3 annotations/build.py <slug>` — generates `assets/books/<slug>.pdf`
4. Update `shelf.html` SVG rect for that book to point to `assets/books/<slug>.pdf`

### How the hyperlinks work
- Every annotation in a book PDF is a clickable region
- Clicking jumps to `connections/connections.pdf#<connections_entry>`
- The anchor is a named destination in the Connections PDF, one per GBO entry
- The Connections Book cross-reference list at the bottom of each entry is
  auto-generated from all YAML files at build time — no manual updating

### How the Connections Book is built
`build_connections.py` does three things:
1. Reads `connections/CONNECTIONS.md` for the full explanation of each entry
2. Scans all `annotations/*.yaml` files to collect every book/page that references each entry
3. Generates `connections/connections.pdf` with named destinations so hyperlinks land correctly

### Source of truth
- **The YAML files** are the source of truth for annotations
- **CONNECTIONS.md** is the source of truth for explanations
- **The PDFs** are generated artifacts — never edit them directly
- Everything is version-controlled; the intellectual work accumulates in plain text

---

## File Structure

```
annotations/
  BIBLE.md                   <- this document
  build.py                   <- typesets books + applies annotations
  build_connections.py       <- generates Connections Book PDF
  Caveat.ttf                 <- handwriting font
  hume-treatise.yaml         <- Hume annotations
  hume-treatise.txt          <- Gutenberg plain text (cached)

connections/
  CONNECTIONS.md             <- source for Connections Book entries
  connections.pdf            <- generated

assets/books/
  hume-treatise.pdf          <- generated annotated PDF
```

---

*Last updated: 2026*
*Authority: Power Corrupts & Bereal, Esq.*
