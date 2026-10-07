"""Compositing primitives for soft, layered printed illustrations."""

try:
    import aggdraw
except ImportError:
    aggdraw = None
from PIL import Image, ImageDraw, ImageFilter


def shadow_panel(image: Image.Image, box: tuple[int, int, int, int], *,
                 radius: int = 26, fill: str = "#FFF4DF", blur: int = 25,
                 shadow: tuple[int, int, int, int] = (68, 36, 19, 55),
                 outline: str | None = None) -> None:
    mask = Image.new("L", image.size)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((box[0]+5, box[1]+13, box[2]+5, box[3]+13),
                        radius=radius, fill=shadow[3])
    blurred = mask.filter(ImageFilter.GaussianBlur(blur))
    shade = Image.new("RGBA", image.size, shadow[:3] + (0,))
    shade.putalpha(blurred)
    image.alpha_composite(shade)
    d = ImageDraw.Draw(image)
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def glow(image: Image.Image, center: tuple[int, int], radius: int,
         color: tuple[int, int, int] = (238, 175, 92)) -> None:
    layer = Image.new("RGBA", image.size)
    d = ImageDraw.Draw(layer)
    x, y = center
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*color, 120))
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius//2)))


def flourish(image: Image.Image, x: int, y: int, scale: float = 1,
             color: str = "#B17D43") -> None:
    if aggdraw is not None:
        ctx = aggdraw.Draw(image)
        path = aggdraw.Path()
        path.moveto(x, y)
        path.curveto(x+75*scale, y-48*scale, x+135*scale, y+58*scale,
                    x+207*scale, y-1*scale)
        path.curveto(x+245*scale, y-33*scale, x+245*scale, y-61*scale,
                    x+215*scale, y-53*scale)
        ctx.path(path, None, aggdraw.Pen(color, 2.2))
        ctx.flush()
    else:
        d = ImageDraw.Draw(image)
        d.arc((x, y - 20, int(x + 200 * scale), int(y + 60 * scale)), 0, 180, fill=color, width=2)
