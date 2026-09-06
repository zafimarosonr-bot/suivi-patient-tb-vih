#!/usr/bin/env python3
"""Génère une icône PNG simple pour Suivi Patient."""

from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 128
OUTPUT = os.path.join(os.path.dirname(__file__), "suivi_patient.png")


def create_icon():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fond arrondi (bleu #007AFF)
    radius = 24
    draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill="#007AFF")

    # Lettre "SP" au centre
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 48)
        except (IOError, OSError):
            font = ImageFont.load_default()

    text = "SP"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - tw) // 2
    y = (SIZE - th) // 2 - 4
    draw.text((x, y), text, fill="#FFFFFF", font=font)

    img.save(OUTPUT, "PNG")
    print(f"Icône créée : {OUTPUT}")


if __name__ == "__main__":
    create_icon()
