#!/usr/bin/env python3
"""
Generate a simple Windows .ico for Frame2Image.

Creates assets/icons/frame2image.ico with multiple sizes (256..16).
Requires Pillow: pip install pillow

Usage:
  python tools/make_icon.py [output_path]
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except Exception as e:
    print("Pillow is required. Install with: pip install pillow", file=sys.stderr)
    raise


def draw_camera_icon(size: int) -> Image.Image:
    """Draw a simple camera glyph on a dark background at given size."""
    bg = (31, 31, 31, 255)  # dark
    body = (53, 53, 53, 255)  # camera body
    stroke = (74, 74, 74, 255)  # border stroke
    blue = (53, 132, 228, 255)  # lens blue
    white = (245, 245, 245, 255)

    img = Image.new("RGBA", (size, size), bg)
    d = ImageDraw.Draw(img)

    s = size
    # Camera body
    left = int(s * 0.16)
    top = int(s * 0.28)
    right = int(s * 0.84)
    bottom = int(s * 0.78)
    d.rounded_rectangle([left, top, right, bottom], radius=int(s * 0.06), fill=body, outline=stroke, width=max(1, s // 64))

    # Viewfinder bump
    vf_w = int(s * 0.18)
    vf_h = int(s * 0.12)
    vf_left = left + int(s * 0.02)
    vf_top = top - int(s * 0.10)
    d.rounded_rectangle([vf_left, vf_top, vf_left + vf_w, vf_top + vf_h], radius=int(s * 0.03), fill=body, outline=stroke, width=max(1, s // 64))

    # Lens ring and lens
    cx, cy = int(s * 0.5), int(s * 0.53)
    r_outer = int(s * 0.20)
    r_inner = int(s * 0.15)
    d.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=white)
    d.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=blue)

    # Lens highlight
    hl_r = max(1, int(r_inner * 0.35))
    d.ellipse([cx - int(r_inner * 0.45), cy - int(r_inner * 0.45), cx - int(r_inner * 0.45) + hl_r, cy - int(r_inner * 0.45) + hl_r], fill=(255, 255, 255, 160))

    return img


def make_icon(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base_size = 256
    base_img = draw_camera_icon(base_size)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    # Save as multi-size ICO from the 256 base
    base_img.save(out_path, format="ICO", sizes=sizes)
    print(f"Wrote icon: {out_path}")


if __name__ == "__main__":
    default_out = Path("assets/icons/frame2image.ico")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default_out
    make_icon(out)
