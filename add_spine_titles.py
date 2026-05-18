"""
Paint book spine titles onto bookshelf.png → bookshelf-titled.png
Run with:  py -3 add_spine_titles.py
"""
from PIL import Image, ImageDraw, ImageFont

SRC  = 'images/bookshelf.png'
DEST = 'images/bookshelf-titled.png'

FONT_PATH  = 'C:/Windows/Fonts/georgiab.ttf'
FONT_LARGE = 105   # short titles
FONT_MED   = 82    # medium titles
FONT_SMALL = 64    # long titles / multiline

TEXT_COLOR   = (245, 225, 165)   # warm cream-gold
SHADOW_COLOR = (20, 10, 0, 180)  # dark shadow for legibility

# ── Shelf definitions ──────────────────────────────────────────────────────
# (y_top, y_bottom, x_start, x_end)
# Measured in original 5344 × 3008 pixels.
SHELVES = [
    (110,  740,  380, 4600),   # top shelf
    (960, 1720,  380, 4600),   # middle shelf
    (1950, 2650, 380, 3680),   # bottom shelf (candle occupies right portion)
]

# ── Book lists ─────────────────────────────────────────────────────────────
BOOKS = [
    # Shelf 1
    [
        "Bruno",
        "Epictetus",
        "Hume",
        "Rand",
        "Attar",
        "Hobbes",
        "Whitehead",
        "Wilson",
        "Coleridge",
    ],
    # Shelf 2
    [
        "Aristotle",
        "Nietzsche",
        "Spinoza",
        "Borges",
        "M. Aurelius",
        "Parfit",
        "Rumi",
        "Hegel",
        "Wittgenstein",
        "Danielewski",
    ],
    # Shelf 3
    [
        "Calvino",
        "James",
        "Russell",
        "Hafez",
        "Everett",
        "Deutsch",
        "Wordsworth",
        "Serafini",
        "The Ground\nBeneath\nthe Ought",
    ],
]

# ── Helpers ────────────────────────────────────────────────────────────────

def make_spine_label(text, spine_width, spine_height, font_path):
    """
    Render `text` rotated 90° (reading bottom→top) into a transparent RGBA
    image sized to fit within (spine_width, spine_height).
    """
    lines = text.split('\n')

    # Pick font size
    if '\n' in text or len(text) > 12:
        size = FONT_SMALL
    elif len(text) > 8:
        size = FONT_MED
    else:
        size = FONT_LARGE

    font = ImageFont.truetype(font_path, size)

    # Measure each line
    dummy = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    line_bboxes = [dummy.textbbox((0, 0), l, font=font) for l in lines]
    line_heights = [b[3] - b[1] for b in line_bboxes]
    line_widths  = [b[2] - b[0] for b in line_bboxes]
    gap = int(size * 0.15)
    total_h = sum(line_heights) + gap * (len(lines) - 1)
    max_w   = max(line_widths)

    # The label image is horizontal; we'll rotate it 90° afterwards.
    # horizontal width = spine_height * 0.85 (text length along spine)
    # horizontal height = spine_width * 0.80 (text height across spine)
    canvas_w = int(spine_height * 0.85)
    canvas_h = int(spine_width  * 0.80)

    label = Image.new('RGBA', (canvas_w, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(label)

    # Center block of lines
    y = (canvas_h - total_h) // 2
    for i, line in enumerate(lines):
        x = (canvas_w - line_widths[i]) // 2
        # Shadow
        d.text((x + 3, y + 3), line, font=font, fill=SHADOW_COLOR)
        # Text
        d.text((x, y), line, font=font, fill=TEXT_COLOR)
        y += line_heights[i] + gap

    # Rotate so text reads bottom→top
    return label.rotate(90, expand=True)


def main():
    img = Image.open(SRC).convert('RGBA')

    for shelf_idx, (y_top, y_bot, x_start, x_end) in enumerate(SHELVES):
        shelf_books = BOOKS[shelf_idx]
        n = len(shelf_books)
        shelf_w = x_end - x_start
        shelf_h = y_bot - y_top
        spine_w  = shelf_w / n

        for book_idx, title in enumerate(shelf_books):
            x_center = int(x_start + spine_w * (book_idx + 0.5))
            label = make_spine_label(title, int(spine_w * 0.88), shelf_h, FONT_PATH)

            paste_x = x_center - label.width  // 2
            paste_y = y_top    + (shelf_h - label.height) // 2

            img.paste(label, (paste_x, paste_y), label)
            print(f"  [{shelf_idx+1}] {title!r:25s}  x={paste_x}  y={paste_y}")

    out = img.convert('RGB')
    out.save(DEST, quality=95)
    print(f"\nSaved → {DEST}")


if __name__ == '__main__':
    main()
