#!/usr/bin/env python3
"""CORALIS - a flat vector travel poster, drawn deterministically with Pillow.

The program paints a 1024x1024 vintage travel poster for the fictional
lagoon destination CORALIS and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(or /output/entry.png).  Only the Python standard library and Pillow are
used; there is no network access and no randomness beyond a fixed seed,
so two runs produce byte-identical output.
"""
import math
import os
import random
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W = H = 1024
BORDER = 34                      # cream paper border around the scene
INNER = (BORDER, BORDER, W - BORDER, H - BORDER)
HORIZON = 640                    # y where the lagoon meets the sky

# ---------------------------------------------------------------- palette
CREAM = (243, 234, 211)          # vintage paper border
TEAL_LINE = (14, 74, 72)         # thin dark-teal inner rule
SKY_TOP = (79, 184, 181)         # bright turquoise sky, top
SKY_BOT = (178, 228, 220)        # sky near the horizon
WATER_TOP = (53, 181, 172)       # lagoon surface at the horizon
WATER_BOT = (13, 120, 116)       # lagoon depth at the bottom
STONE = (233, 220, 195)          # arch stone, warm ivory
STONE_DARK = (209, 192, 158)     # arch shading / joints
CORAL = (240, 161, 147)          # soft coral pink
CORAL_MID = (232, 138, 122)      # coral trim
CORAL_DEEP = (217, 106, 95)      # deep coral / pagoda roofs
TERRA = (122, 59, 46)            # dark terracotta-brown lettering
TERRA_DARK = (88, 40, 30)        # carved shadow of the lettering
ROCK = (14, 74, 72)              # deep ocean-teal coastal rocks
ROCK_MID = (19, 88, 85)
ROCK_LIGHT = (26, 104, 99)
IVORY = (245, 237, 216)          # sanctuary terraces / pagoda walls
IVORY_DARK = (238, 226, 198)
ROOF_DARK = (184, 74, 64)
WOOD = (138, 90, 59)             # rowboat hull
WOOD_LIGHT = (171, 115, 77)
GOLD = (242, 201, 107)           # morning sunbeams
WALK_TOP = (217, 205, 178)       # stone walkway, top surface
WALK_FRONT = (191, 174, 142)     # stone walkway, front face
SILHOUETTE = (14, 74, 72)       # visitors, rower
CLOUD = (255, 255, 255)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(w, h, top, bot):
    """A vertical gradient image of size w x h."""
    grad = Image.new("RGB", (1, h))
    px = grad.load()
    for y in range(h):
        px[0, y] = lerp(top, bot, y / max(1, h - 1))
    return grad.resize((w, h))


def load_serif(size):
    """A bold serif face; DejaVu Serif first so local and kit runs match."""
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf",
        "DejaVuSerif-Bold.ttf",
        "LiberationSerif-Bold.ttf",
        "NotoSerif-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def arc_points(cx, cy, r, a0, a1, n=64):
    """Points along a circular arc; angles in degrees, y-down coordinates."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def bezier(p0, p1, p2, n=24):
    """Points along a quadratic bezier curve."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts


def curved_word(base, word, cx, cy, radius, font, fill, shadow):
    """Render one word so each letter sits on a circular arc, rotated to
    follow the curve (letter tops point away from the arc centre)."""
    widths = [font.getlength(ch) for ch in word]
    gap = 10.0
    total = sum(widths) + gap * (len(word) - 1)
    span = total / radius                       # radians
    start = -math.pi / 2 - span / 2             # centre the word at the top
    tile = int(font.size * 2.4)
    dist = 0.0
    for i, ch in enumerate(word):
        w = widths[i]
        ang = start + (dist + w / 2.0) / radius
        px = cx + radius * math.cos(ang)
        py = cy + radius * math.sin(ang)
        rot = -math.degrees(ang) - 90.0
        layer = Image.new("RGBA", (tile, tile), (0, 0, 0, 0))
        td = ImageDraw.Draw(layer)
        bbox = td.textbbox((0, 0), ch, font=font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (tile - lw) // 2 - bbox[0]
        ty = (tile - lh) // 2 - bbox[1]
        td.text((tx + 1, ty + 2), ch, font=font, fill=shadow + (255,))
        td.text((tx, ty), ch, font=font, fill=fill + (255,))
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=False)
        base.paste(layer, (int(round(px - tile / 2)), int(round(py - tile / 2))),
                   layer)
        dist += w + gap


def fade_alpha_down(layer, y0, y1):
    """Fade a layer's alpha from full at y0 to zero at y1."""
    alpha = layer.split()[3]
    grad = Image.new("L", (1, y1 - y0))
    gp = grad.load()
    for y in range(y1 - y0):
        gp[0, y] = round(255 * (1 - y / max(1, y1 - y0 - 1)))
    grad = grad.resize((layer.width, y1 - y0))
    full = Image.new("L", layer.size, 255)
    full.paste(grad, (0, y0))
    layer.putalpha(ImageChops.multiply(alpha, full))
    return layer


def wave_distort(layer, y0, y1, amp=5.0, wavelength=70.0):
    """Shift 2px horizontal strips by a sine wave (water ripple)."""
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.paste(layer.crop((0, 0, layer.width, y0)), (0, 0))
    out.paste(layer.crop((0, y1, layer.width, layer.height)), (0, y1))
    y = y0
    while y < y1:
        h = min(2, y1 - y)
        shift = int(round(amp * math.sin(2 * math.pi * (y - y0) / wavelength)))
        strip = layer.crop((0, y, layer.width, y + h))
        out.paste(strip, (shift, y))
        y += h
    return out


def fan_branch(draw, x, y, angle, length, width, depth, color, tip):
    """One branching coral limb; children fan out and shrink."""
    rad = math.radians(angle)
    x2 = x + length * math.cos(rad)
    y2 = y + length * math.sin(rad)
    draw.line([(x, y), (x2, y2)], fill=color, width=max(1, int(round(width))))
    if depth <= 0:
        r = max(2, int(round(width)))
        draw.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=tip)
        return
    spread = 24.0
    fan_branch(draw, x2, y2, angle - spread, length * 0.72, width * 0.68,
               depth - 1, color, tip)
    fan_branch(draw, x2, y2, angle + spread, length * 0.72, width * 0.68,
               depth - 1, color, tip)
    if depth >= 3:
        fan_branch(draw, x2, y2, angle, length * 0.70, width * 0.62,
                   depth - 1, color, tip)


def draw_cloud(draw, cx, cy, scale, alpha=235):
    """A soft flat cloud: a cluster of overlapping ellipses."""
    col = CLOUD + (alpha,)
    for dx, dy, rx, ry in ((-46, 6, 52, 20), (-18, -8, 46, 26), (14, -2, 52, 24),
                           (44, 8, 44, 18), (0, 10, 62, 18)):
        x0 = cx + dx * scale - rx * scale
        y0 = cy + dy * scale - ry * scale
        x1 = cx + dx * scale + rx * scale
        y1 = cy + dy * scale + ry * scale
        draw.ellipse([x0, y0, x1, y1], fill=col)


def draw_roof(draw, cx, y_top, y_bot, half_top, half_bot):
    """One pagoda roof: a trapezoid whose lower edge is a bezier that sags
    in the middle and kicks up at the corners (upturned eaves)."""
    bottom = bezier((cx - half_bot, y_bot - 12), (cx, y_bot + 12),
                    (cx + half_bot, y_bot - 12), 28)
    poly = [(cx - half_top, y_top), (cx + half_top, y_top)] + bottom[::-1]
    draw.polygon(poly, fill=CORAL_DEEP)
    draw.line(bottom, fill=ROOF_DARK, width=3, joint="curve")
    draw.line([(cx - half_top, y_top), (cx + half_top, y_top)],
              fill=ROOF_DARK, width=3)


def draw_figure(draw, x, y, h, color, hat=False):
    """A tiny visitor silhouette: head, shoulders and a simple robe."""
    r = h * 0.16
    draw.ellipse([x - r, y - h, x + r, y - h + 2 * r], fill=color)
    if hat:
        draw.ellipse([x - r * 1.7, y - h + r * 0.4, x + r * 1.7,
                      y - h + r * 1.1], fill=color)
    body = [(x - h * 0.13, y - h * 0.62), (x + h * 0.13, y - h * 0.62),
            (x + h * 0.17, y), (x - h * 0.17, y)]
    draw.polygon(body, fill=color)


def main():
    base = Image.new("RGBA", (W, H), CREAM + (255,))
    draw = ImageDraw.Draw(base)
    ix0, iy0, ix1, iy1 = INNER

    # --- sky and lagoon -------------------------------------------------
    sky = vgrad(ix1 - ix0, HORIZON - iy0, SKY_TOP, SKY_BOT)
    base.paste(sky, (ix0, iy0))
    sea = vgrad(ix1 - ix0, iy1 - HORIZON, WATER_TOP, WATER_BOT)
    base.paste(sea, (ix0, HORIZON))

    # soft sun glow, top left
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((260, 26), (200, 34), (140, 44), (80, 56)):
        gd.ellipse([70 - r, 30 - r, 70 + r, 30 + r], fill=GOLD + (a,))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(glow)

    # clouds
    clouds = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(clouds)
    draw_cloud(cd, 500, 128, 0.85)
    draw_cloud(cd, 830, 108, 0.7)
    draw_cloud(cd, 660, 205, 0.55, alpha=200)
    base.alpha_composite(clouds)

    # golden morning sunbeams, diagonal from the top left
    beams = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(beams)
    for (x0, x1, y1, a) in ((90, 170, 470, 52), (210, 280, 540, 44),
                            (330, 390, 600, 36)):
        bd.polygon([(x0, iy0), (x1, iy0), (x1 + 260, y1), (x0 + 260, y1)],
                   fill=GOLD + (a,))
    beams = beams.filter(ImageFilter.GaussianBlur(12))
    base.alpha_composite(beams)

    # distant islet seen through the arch opening, low on the horizon
    draw.polygon([(300, 640), (336, 624), (396, 624), (428, 640)],
                 fill=(20, 110, 108))
    draw.polygon([(360, 624), (372, 612), (384, 624)], fill=(20, 110, 108))

    # --- water reflections (arch + pagoda), wave-distorted --------------
    refl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for x, w, col, a in ((70, 22, STONE, 80), (120, 16, STONE_DARK, 70),
                         (180, 26, CORAL_MID, 60), (240, 18, STONE, 80),
                         (300, 22, STONE_DARK, 70), (360, 16, CORAL_MID, 60),
                         (420, 20, STONE, 75)):
        rd.rectangle([x, HORIZON + 4, x + w, 880], fill=col + (a,))
    for x, w, col, a in ((640, 24, IVORY, 70), (700, 18, CORAL_DEEP, 60),
                         (760, 26, ROCK_LIGHT, 65), (830, 20, IVORY, 70),
                         (900, 22, CORAL_DEEP, 60), (950, 16, ROCK_LIGHT, 65)):
        rd.rectangle([x, HORIZON + 4, x + w, 860], fill=col + (a,))
    refl = refl.filter(ImageFilter.GaussianBlur(3))
    refl = fade_alpha_down(refl, HORIZON + 4, 890)
    refl = wave_distort(refl, HORIZON + 4, 890, amp=5.0, wavelength=70.0)
    base.alpha_composite(refl)

    # --- the arch (left): pillars, band, joints, coral trim ------------
    acx, acy, ro, ri = 250, 500, 215, 145
    draw.rectangle([35, 500, 105, 832], fill=STONE)
    draw.rectangle([395, 500, 465, 832], fill=STONE)
    draw.rectangle([35, 500, 105, 512], fill=STONE_DARK)
    draw.rectangle([395, 500, 465, 512], fill=STONE_DARK)
    draw.rectangle([28, 806, 112, 832], fill=STONE_DARK)
    draw.rectangle([388, 806, 472, 832], fill=STONE_DARK)
    band = arc_points(acx, acy, ro, 180, 360, 72) + \
        arc_points(acx, acy, ri, 360, 180, 72)
    draw.polygon(band, fill=STONE)
    # voussoir joints radiating across the band
    for ang in range(195, 361, 15):
        a = math.radians(ang)
        x0 = acx + (ri + 4) * math.cos(a)
        y0 = acy + (ri + 4) * math.sin(a)
        x1 = acx + (ro - 4) * math.cos(a)
        y1 = acy + (ro - 4) * math.sin(a)
        draw.line([(x0, y0), (x1, y1)], fill=STONE_DARK, width=3)
    # coral trim along the outer and inner rims
    draw.arc([acx - ro, acy - ro, acx + ro, acy + ro], 180, 360,
             fill=CORAL_MID, width=7)
    draw.arc([acx - ri, acy - ri, acx + ri, acy + ri], 180, 360,
             fill=CORAL, width=5)
    # coral clusters growing on the arch feet
    for (cx, cy, r) in ((52, 800, 12), (70, 812, 9), (88, 798, 10),
                        (420, 802, 11), (440, 814, 9), (456, 800, 10)):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CORAL_MID)
        draw.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45,
                      cy + r * 0.45], fill=CORAL)

    # --- CORALIS, sculpted along the arch's upper curve ----------------
    font = load_serif(60)
    curved_word(base, "CORALIS", acx, acy, 180, font, TERRA, TERRA_DARK)

    # --- fan coral tree crowning the right-hand spire ------------------
    fx, fy = 790, 400
    fan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fan)
    fd.pieslice([fx - 185, fy - 185, fx + 185, fy + 185], 180, 360,
                fill=(243, 196, 184, 255))
    for ang in range(195, 346, 15):
        a = math.radians(ang)
        fd.line([(fx, fy), (fx + 178 * math.cos(a), fy + 178 * math.sin(a))],
                fill=(217, 123, 110, 255), width=3)
    base.alpha_composite(fan)
    fd2 = ImageDraw.Draw(base)
    for ang in (-150, -120, -90, -60, -30):
        fan_branch(fd2, fx, fy, ang, 70, 5, 3, CORAL_MID, CORAL)

    # --- coastal rocks, terraced sanctuary, pagoda spire (right) -------
    rocks = [(592, 762), (628, 664), (664, 622), (712, 642), (748, 602),
             (796, 630), (844, 600), (892, 634), (936, 608), (972, 650),
             (988, 700), (988, 762)]
    draw.polygon(rocks, fill=ROCK)
    draw.polygon([(628, 664), (664, 622), (712, 642), (700, 672), (648, 680)],
                 fill=ROCK_MID)
    draw.polygon([(796, 630), (844, 600), (892, 634), (872, 664), (820, 664)],
                 fill=ROCK_MID)
    draw.polygon([(664, 622), (712, 642), (748, 602), (730, 594)],
                 fill=ROCK_LIGHT)
    for (tx0, tx1, ty0, ty1) in ((640, 922, 560, 600), (680, 882, 520, 560),
                                 (720, 842, 485, 520)):
        draw.rectangle([tx0, ty0, tx1, ty1], fill=IVORY)
        draw.rectangle([tx0, ty1 - 6, tx1, ty1], fill=CORAL_MID)
        draw.rectangle([tx0, ty0, tx1, ty0 + 4], fill=IVORY_DARK)
    # pagoda: each tier is a wall with its roof sitting on top, so the
    # ivory walls stay visible between the eaves
    draw.rectangle([744, 455, 836, 485], fill=IVORY)
    draw.rectangle([764, 405, 816, 433], fill=IVORY)
    draw.rectangle([778, 361, 802, 383], fill=IVORY)
    draw.arc([778, 462, 802, 486], 180, 360, fill=TEAL_LINE, width=3)
    draw.arc([780, 410, 800, 434], 180, 360, fill=TEAL_LINE, width=3)
    draw_roof(draw, 790, 433, 455, 50, 82)
    draw_roof(draw, 790, 383, 405, 38, 62)
    draw_roof(draw, 790, 343, 361, 26, 44)
    draw.line([(790, 343), (790, 325)], fill=ROOF_DARK, width=4)
    draw.ellipse([784, 316, 796, 328], fill=GOLD)

    # --- rowboat with a single rower, gliding toward the arch ----------
    hull = [(478, 820), (492, 842)] + bezier((492, 842), (556, 862),
                                              (620, 842), 20) + \
        [(634, 820), (620, 812), (492, 812)]
    draw.polygon(hull, fill=WOOD)
    draw.polygon([(492, 812), (620, 812), (628, 820), (486, 820)],
                 fill=WOOD_LIGHT)
    draw.line([(512, 814), (512, 840)], fill=ROOF_DARK, width=3)
    draw.line([(592, 814), (592, 840)], fill=ROOF_DARK, width=3)
    # rower: seated figure facing left, one oar in the water
    draw_figure(draw, 560, 812, 38, SILHOUETTE, hat=True)
    draw.line([(550, 794), (522, 856)], fill=(60, 48, 36), width=4)
    draw.ellipse([512, 850, 532, 860], fill=(60, 48, 36))
    # wake ripples trailing behind the boat (it heads left)
    for (wx0, wx1, wy) in ((640, 700, 852), (652, 696, 862), (666, 692, 872)):
        draw.arc([wx0, wy, wx1, wy + 12], 0, 180, fill=(255, 255, 255, 180),
                 width=3)

    # --- stone waterfront walkway and three visitors (foreground) ------
    draw.rectangle([34, 875, 430, 906], fill=WALK_TOP)
    draw.rectangle([34, 906, 430, 960], fill=WALK_FRONT)
    draw.line([(34, 875), (430, 875)], fill=STONE_DARK, width=3)
    draw.line([(34, 906), (430, 906)], fill=STONE_DARK, width=2)
    draw.line([(34, 924), (430, 924)], fill=STONE_DARK, width=2)
    draw.line([(34, 942), (430, 942)], fill=STONE_DARK, width=2)
    for x in range(52, 420, 34):
        draw.rectangle([x, 856, x + 7, 875], fill=STONE_DARK)
    draw.rectangle([40, 852, 424, 858], fill=STONE_DARK)
    draw_figure(draw, 150, 876, 36, SILHOUETTE, hat=True)
    draw_figure(draw, 214, 876, 32, SILHOUETTE)
    draw_figure(draw, 272, 876, 34, SILHOUETTE, hat=False)
    # waterline ripples where the arch feet and rocks meet the lagoon
    for (rx0, rx1, ry) in ((20, 120, 834), (380, 480, 834), (600, 700, 762),
                           (900, 985, 762)):
        draw.arc([rx0, ry, rx1, ry + 12], 0, 180, fill=(255, 255, 255, 170),
                 width=3)

    # --- thin dark-teal inner rule framing the scene -------------------
    draw.rectangle([32, 32, 992, 992], outline=TEAL_LINE, width=3)

    # --- subtle paper grain (fixed seed, so it is deterministic) -------
    rng = random.Random(20261121)
    grain = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for _ in range(3600):
        x = rng.randrange(W)
        y = rng.randrange(H)
        if rng.random() < 0.5:
            gd.point((x, y), fill=(90, 58, 40, rng.randrange(8, 22)))
        else:
            gd.point((x, y), fill=(255, 255, 255, rng.randrange(8, 20)))
    base.alpha_composite(grain)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    base.convert("RGB").save(out_path, format="PNG", optimize=True)


if __name__ == "__main__":
    main()
