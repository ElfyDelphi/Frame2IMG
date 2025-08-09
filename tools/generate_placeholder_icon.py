"""
Generate a simple placeholder app icon for Frame2IMG.
Outputs:
 - icon-1024.png (master)
 - icon.png (256x256)
 - icon.ico (multi-size: 256,128,64,48,32,24,16)

Requires: Pillow
Run: python tools/generate_placeholder_icon.py
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_1024 = ROOT / "icon-1024.png"
OUT_PNG = ROOT / "icon.png"
OUT_ICO = ROOT / "icon.ico"

BG_TOP = (37, 108, 223, 255)   # #256CDF
BG_BOTTOM = (23, 71, 155, 255) # #17479B
FG = (255, 255, 255, 255)      # white text
SHADOW = (0, 0, 0, 100)
RADIUS = 220


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _vertical_gradient(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size))
    top = BG_TOP
    bottom = BG_BOTTOM
    for y in range(size):
        t = y / max(1, size - 1)
        r = _lerp(top[0], bottom[0], t)
        g = _lerp(top[1], bottom[1], t)
        b = _lerp(top[2], bottom[2], t)
        a = _lerp(top[3], bottom[3], t)
        ImageDraw.Draw(img).line([(0, y), (size, y)], fill=(r, g, b, a))
    return img


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=radius, fill=255)
    return mask


def _pick_font(px: int) -> ImageFont.ImageFont:
    # Prefer bold system fonts on Windows; fallback gracefully
    font_paths = [
        # Windows common fonts
        r"C:\\Windows\\Fonts\\segoeuib.ttf",
        r"C:\\Windows\\Fonts\\segoeui.ttf",
        r"C:\\Windows\\Fonts\\arialbd.ttf",
        r"C:\\Windows\\Fonts\\arial.ttf",
        r"C:\\Windows\\Fonts\\tahomabd.ttf",
        r"C:\\Windows\\Fonts\\tahoma.ttf",
        # Generic names (if mapped)
        "Segoe UI Bold",
        "Arial Bold",
        "Arial",
    ]
    for path in font_paths:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(path, px)
        except Exception:
            pass
    # Fallback
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", px)
    except Exception:
        return ImageFont.load_default()


def make_master(size: int = 1024) -> Image.Image:
    # Background with rounded gradient card
    bg = _vertical_gradient(size)
    mask = _rounded_mask(size, RADIUS)
    card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    card.paste(bg, (0, 0), mask)

    # Optional subtle inner highlight
    overlay = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    d_ov = ImageDraw.Draw(overlay)
    d_ov.rounded_rectangle(
        [(16, 16), (size - 17, size - 17)], radius=RADIUS - 20, outline=(255, 255, 255, 32), width=6
    )
    card = Image.alpha_composite(card, overlay)

    # Text "F2" centered
    txt = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    text = "F2"
    # Font size scaled to canvas
    font_size = int(size * 0.54)
    font = _pick_font(font_size)
    # Compute text bbox and center
    bbox = d.textbbox((0, 0), text, font=font, anchor="lt")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = size // 2
    cy = size // 2 + int(size * 0.03)  # slight optical adjustment
    # Shadow
    d.text((cx + 6, cy + 6), text, font=font, fill=SHADOW, anchor="mm")
    # Foreground
    d.text((cx, cy), text, font=font, fill=FG, anchor="mm")

    out = Image.alpha_composite(card, txt)
    return out


def main() -> None:
    img1024 = make_master(1024)
    img1024.save(OUT_1024)

    # Export a 256px PNG for window icon
    img256 = img1024.resize((256, 256), Image.LANCZOS)
    img256.save(OUT_PNG)

    # Export ICO multi-size
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    imgs = [img1024.resize(sz, Image.LANCZOS) for sz in sizes]
    # Pillow uses the first image as base; "save" supports list of sizes
    imgs[0].save(OUT_ICO, sizes=sizes)

    print(f"Wrote: {OUT_1024}")
    print(f"Wrote: {OUT_PNG}")
    print(f"Wrote: {OUT_ICO}")


if __name__ == "__main__":
    main()
