"""Pads an exported card to a wider aspect ratio without losing any of it.

Called only from script.py. XHS renders every 一键排版 card at 3:5; a wider
ratio such as 3:4 is reached by keeping the card's full height and adding
equal bands on the left and right, filled with the card's own edge colour
so they read as more background. Nothing is cropped or scaled.

Needs Pillow (`pip install pillow`).
"""

import io
from collections import Counter

from PIL import Image


def edge_colour(image):
    """The most common colour down the card's left and right edges."""
    width, height = image.size
    samples = [image.getpixel((x, y))
               for x in (0, 1, 2, width - 3, width - 2, width - 1)
               for y in range(0, height, 8)]
    return Counter(samples).most_common(1)[0][0]


def pad_to_aspect(data, ratio_w, ratio_h):
    """Return (jpeg_bytes, width, height) of the card padded to ratio_w:ratio_h.

    The card keeps its height; the canvas width becomes height * ratio_w /
    ratio_h. A card already at least that wide is returned unpadded.
    """
    card = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = card.size
    target_width = round(height * ratio_w / ratio_h)
    if target_width <= width:
        canvas = card
    else:
        canvas = Image.new("RGB", (target_width, height), edge_colour(card))
        canvas.paste(card, ((target_width - width) // 2, 0))
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=95)
    return out.getvalue(), canvas.size[0], canvas.size[1]
