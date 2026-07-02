from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "app" / "static" / "assets"

TERRAINS = {
    "forest": (45, 106, 79),
    "pasture": (144, 190, 109),
    "field": (233, 196, 106),
    "hill": (188, 108, 37),
    "mountain": (141, 153, 174),
    "desert": (212, 163, 115),
    "sea": (38, 100, 128),
}
RESOURCES = {
    "lumber": (45, 106, 79),
    "brick": (188, 108, 37),
    "wool": (144, 190, 109),
    "grain": (233, 196, 106),
    "ore": (110, 120, 140),
}
DEV_CARDS = {
    "knight": (80, 80, 95),
    "road_building": (176, 126, 74),
    "year_of_plenty": (42, 157, 143),
    "monopoly": (111, 78, 124),
    "victory_point": (244, 162, 97),
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def save(image: Image.Image, name: str, force: bool) -> None:
    path = ASSET_DIR / name
    if path.exists() and not force:
        print(f"skip {path}")
        return
    image.save(path)
    print(f"write {path}")


def add_label(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, size: int, fill=(255, 255, 255, 235)) -> None:
    text_font = font(size, bold=True)
    draw.multiline_text(box_center(box, text, text_font), text, font=text_font, fill=fill, align="center", stroke_width=2, stroke_fill=(0, 0, 0, 125))


def box_center(box: tuple[int, int, int, int], text: str, text_font: ImageFont.ImageFont) -> tuple[int, int]:
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), text, font=text_font, align="center")
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return (box[0] + (box[2] - box[0] - width) // 2, box[1] + (box[3] - box[1] - height) // 2)


def hex_points(cx: int, cy: int, radius: int) -> list[tuple[float, float]]:
    return [(cx + radius * math.cos(math.radians(60 * i - 30)), cy + radius * math.sin(math.radians(60 * i - 30))) for i in range(6)]


def terrain_asset(name: str, color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (512, 512), color + (255,))
    draw = ImageDraw.Draw(image)
    for i in range(0, 650, 32):
        shade = tuple(max(0, min(255, channel + (18 if (i // 32) % 2 else -12))) for channel in color)
        draw.line([(i - 180, 0), (i, 512)], fill=shade + (95,), width=22)
    if name == "forest":
        for x in range(60, 480, 90):
            for y in range(80, 470, 110):
                draw.polygon([(x, y - 35), (x - 30, y + 35), (x + 30, y + 35)], fill=(22, 82, 54, 180))
    elif name == "pasture":
        for x in range(40, 500, 80):
            draw.arc((x, 80, x + 70, 160), 200, 340, fill=(235, 245, 220, 140), width=5)
    elif name == "field":
        for x in range(20, 512, 42):
            draw.line((x, 40, x + 60, 480), fill=(255, 236, 150, 155), width=5)
    elif name == "hill":
        for x in range(-40, 520, 120):
            draw.ellipse((x, 310, x + 180, 620), fill=(143, 76, 27, 130))
    elif name == "mountain":
        for x in range(20, 520, 130):
            draw.polygon([(x, 430), (x + 65, 110), (x + 135, 430)], fill=(91, 99, 118, 130))
            draw.polygon([(x + 65, 110), (x + 35, 250), (x + 95, 250)], fill=(230, 235, 240, 145))
    elif name == "desert":
        for y in range(100, 470, 80):
            draw.arc((-20, y, 540, y + 120), 180, 360, fill=(245, 214, 160, 125), width=8)
    elif name == "sea":
        for y in range(30, 512, 70):
            draw.arc((-30, y, 150, y + 70), 0, 180, fill=(111, 211, 230, 110), width=6)
            draw.arc((130, y + 18, 310, y + 88), 0, 180, fill=(111, 211, 230, 95), width=6)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).polygon(hex_points(256, 256, 246), fill=255)
    if name != "sea":
        cut = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        cut.alpha_composite(image)
        cut.putalpha(mask)
        image = cut
    draw = ImageDraw.Draw(image)
    add_label(draw, (80, 208, 432, 304), name.upper(), 46)
    return image


def resource_card(name: str, color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (360, 500), (22, 31, 39, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 342, 482), radius=28, fill=color + (255,), outline=(255, 255, 255, 160), width=4)
    draw.rounded_rectangle((42, 54, 318, 312), radius=24, fill=tuple(min(255, c + 25) for c in color) + (255,))
    if name == "lumber":
        draw.rectangle((155, 140, 205, 305), fill=(101, 67, 33, 255))
        draw.polygon([(180, 70), (90, 220), (270, 220)], fill=(28, 105, 64, 230))
    elif name == "brick":
        for y in range(100, 280, 48):
            for x in range(70 + (y // 48 % 2) * 32, 280, 70):
                draw.rounded_rectangle((x, y, x + 62, y + 34), radius=6, fill=(132, 54, 31, 230), outline=(95, 34, 22, 255), width=2)
    elif name == "wool":
        for x, y, r in [(135, 160, 46), (185, 142, 52), (220, 190, 42), (160, 215, 50)]:
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(245, 245, 230, 235))
    elif name == "grain":
        for x in [130, 165, 200, 235]:
            draw.line((x, 290, x - 20, 110), fill=(120, 92, 27, 255), width=6)
            for y in range(130, 250, 34):
                draw.ellipse((x - 42, y - 16, x - 8, y + 16), fill=(255, 227, 126, 240))
    elif name == "ore":
        for points in [[(105,230),(155,120),(220,170),(205,265)], [(180,245),(235,145),(285,225),(250,300)], [(80,285),(145,210),(190,320)]]:
            draw.polygon(points, fill=(82, 90, 112, 240), outline=(235,235,240,120))
    add_label(draw, (38, 338, 322, 430), name.upper(), 38)
    return image


def dev_card(name: str, color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (360, 500), (15, 21, 28, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 342, 482), radius=28, fill=color + (255,), outline=(255, 255, 255, 150), width=4)
    draw.ellipse((92, 70, 268, 246), fill=(255, 255, 255, 56), outline=(255, 255, 255, 90), width=4)
    icon = {
        "knight": "⚔",
        "road_building": "🛣",
        "year_of_plenty": "✦",
        "monopoly": "♛",
        "victory_point": "★",
    }.get(name, "?")
    add_label(draw, (72, 82, 288, 238), icon, 92)
    add_label(draw, (34, 315, 326, 430), name.replace("_", "\n").upper(), 34)
    return image


def dice_asset(value: int) -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 24, 232, 232), radius=38, fill=(248, 246, 236, 255), outline=(25, 25, 25, 255), width=8)
    positions = {
        1: [(128, 128)],
        2: [(82, 82), (174, 174)],
        3: [(82, 82), (128, 128), (174, 174)],
        4: [(82, 82), (174, 82), (82, 174), (174, 174)],
        5: [(82, 82), (174, 82), (128, 128), (82, 174), (174, 174)],
        6: [(82, 70), (174, 70), (82, 128), (174, 128), (82, 186), (174, 186)],
    }[value]
    for x, y in positions:
        draw.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(25, 25, 25, 255))
    return image


def robber_asset() -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((86, 28, 170, 112), fill=(35, 35, 38, 255), outline=(255, 255, 255, 80), width=3)
    draw.rounded_rectangle((68, 102, 188, 222), radius=46, fill=(28, 28, 32, 255), outline=(255, 255, 255, 80), width=3)
    draw.rectangle((95, 74, 161, 88), fill=(245, 245, 245, 200))
    add_label(draw, (40, 205, 216, 250), "ROBBER", 25)
    return image


def piece_asset(kind: str) -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = (255, 255, 255, 120)
    outline = (0, 0, 0, 200)
    if kind == "settlement":
        draw.polygon([(128, 40), (50, 116), (70, 216), (186, 216), (206, 116)], fill=fill, outline=outline)
    elif kind == "city":
        draw.polygon([(48, 216), (48, 96), (94, 96), (94, 44), (148, 44), (148, 116), (208, 116), (208, 216)], fill=fill, outline=outline)
    else:
        draw.rounded_rectangle((36, 100, 220, 156), radius=24, fill=fill, outline=outline, width=5)
    return image


def token_asset() -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((18, 18, 238, 238), fill=(249, 239, 199, 255), outline=(85, 59, 35, 255), width=8)
    draw.ellipse((42, 42, 214, 214), outline=(180, 130, 70, 130), width=3)
    return image


def port_asset(kind: str) -> Image.Image:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 58, 232, 198), radius=24, fill=(20, 38, 48, 240), outline=(255, 255, 255, 150), width=5)
    label = "3:1" if kind == "3to1" else f"2:1\n{kind.upper()}"
    add_label(draw, (32, 68, 224, 188), label, 34)
    return image


def badge_asset(name: str) -> Image.Image:
    image = Image.new("RGBA", (320, 220), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((14, 32, 306, 188), radius=28, fill=(244, 162, 97, 245), outline=(255, 255, 255, 170), width=5)
    add_label(draw, (28, 58, 292, 162), name.replace("_", "\n").upper(), 34, fill=(40, 25, 15, 255))
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate placeholder PNG assets. Existing files are kept unless --force is used.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing PNGs.")
    args = parser.parse_args()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    for name, color in TERRAINS.items():
        save(terrain_asset(name, color), f"terrain_{name}.png", args.force)
    for name, color in RESOURCES.items():
        save(resource_card(name, color), f"resource_{name}.png", args.force)
    for name, color in DEV_CARDS.items():
        save(dev_card(name, color), f"dev_{name}.png", args.force)
    for value in range(1, 7):
        save(dice_asset(value), f"dice_{value}.png", args.force)
    save(robber_asset(), "icon_robber.png", args.force)
    save(piece_asset("settlement"), "piece_settlement.png", args.force)
    save(piece_asset("city"), "piece_city.png", args.force)
    save(piece_asset("road"), "piece_road.png", args.force)
    save(token_asset(), "number_token.png", args.force)
    save(dev_card("development", (58, 65, 82)), "card_back_development.png", args.force)
    save(port_asset("3to1"), "port_3to1.png", args.force)
    for resource in RESOURCES:
        save(port_asset(resource), f"port_{resource}.png", args.force)
    save(badge_asset("largest_army"), "largest_army.png", args.force)
    save(badge_asset("longest_road"), "longest_road.png", args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
