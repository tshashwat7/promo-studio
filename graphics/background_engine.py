try:
    import numpy as np
except ImportError:
    np = None
from PIL import Image, ImageDraw, ImageFilter

PALETTES = {
    "panchang": ((10, 27, 45), (56, 68, 78), (198, 112, 70)),
    "plan": ((255, 246, 226), (247, 223, 186), (221, 181, 133)),
    "festival": ((255, 242, 218), (248, 221, 185), (217, 172, 126)),
    "kundli": ((255, 247, 226), (244, 225, 196), (221, 193, 151)),
    "chakra": ((12, 28, 43), (32, 47, 68), (73, 41, 75)),
    "transit": ((9, 24, 39), (25, 49, 71), (67, 55, 80)),
}


class BackgroundEngine:
    @staticmethod
    def create(theme: str, width: int, height: int) -> Image.Image:
        if theme not in PALETTES:
            raise ValueError(f"Unknown background theme: {theme}")
        if np is None:
            top, middle, bottom = PALETTES[theme]
            image = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(image)
            mid_y = height // 2
            for y in range(mid_y):
                t = y / max(mid_y, 1)
                r = round(top[0] * (1 - t) + middle[0] * t)
                g = round(top[1] * (1 - t) + middle[1] * t)
                b = round(top[2] * (1 - t) + middle[2] * t)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            for y in range(mid_y, height):
                t = (y - mid_y) / max(height - mid_y, 1)
                r = round(middle[0] * (1 - t) + bottom[0] * t)
                g = round(middle[1] * (1 - t) + bottom[1] * t)
                b = round(middle[2] * (1 - t) + bottom[2] * t)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            return image.convert("RGBA")
        top, middle, bottom = [np.array(c, dtype=np.float32) for c in PALETTES[theme]]
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        t = yy / max(height-1, 1)
        blend = np.clip(t*2, 0, 1)[..., None]
        second = np.clip(t*2-1, 0, 1)[..., None]
        pixels = top*(1-blend) + middle*blend
        pixels = pixels*(1-second) + bottom*second
        warm = theme in {"plan", "festival", "kundli"}
        gx, gy = (width*.77, height*.55) if warm else (width*.78, height*.28)
        glow = np.exp(-((xx-gx)**2/(width*.39)**2 + (yy-gy)**2/(height*.28)**2))
        glow_rgb = np.array((17, 9, 0) if warm else (49, 27, 6))
        pixels += glow[..., None] * glow_rgb
        rng = np.random.default_rng(20261005)
        grain = rng.normal(0, 1.9, (height, width, 1)).astype(np.float32)
        pixels += grain
        image = Image.fromarray(np.uint8(np.clip(pixels, 0, 255)), "RGB").convert("RGBA")
        d = ImageDraw.Draw(image, "RGBA")
        # Small deterministic glints and blurred atmospheric light.
        if not warm:
            for x, y in zip(rng.integers(0, width, 120),
                            rng.integers(0, height, 120)):
                r = int(rng.choice((1, 1, 2, 3)))
                d.ellipse((int(x-r), int(y-r), int(x+r), int(y+r)), fill=(255, 222, 179, 92))
        else:
            bokeh = Image.new("RGBA", image.size)
            bd = ImageDraw.Draw(bokeh)
            for _ in range(37):
                x = int(rng.integers(0, width))
                y = int(rng.integers(min(180, height-1), height))
                r = int(rng.integers(8, 34))
                bd.ellipse((x-r, y-r, x+r, y+r), fill=(209, 147, 63, 50))
            image = Image.alpha_composite(image, bokeh.filter(ImageFilter.GaussianBlur(11)))
        return image
