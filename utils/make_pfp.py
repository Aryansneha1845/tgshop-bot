from PIL import Image, ImageDraw, ImageFont
import os

W, H = 800, 800

def _font(size, bold=False):
    for p in [ "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def make_pfp(out="assets/pfp.png"):
    # dark gradient bg
    img = Image.new("RGB", (W,H), (15,15,30))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t=y/H
        r=int(15*(1-t)+95*t)
        g=int(15*(1-t)+44*t)
        b=int(30*(1-t)+131*t)
        d.line([(0,y),(W,y)], fill=(r,g,b))
    # glow
    glow = Image.new("RGBA",(W,H),(0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([120,120, 680,680], fill=(255,255,255,12))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    # outer circle border
    d.ellipse([(18,18),(W-18,H-18)], outline=(255,255,255,30), width=3)
    d.ellipse([(24,24),(W-24,H-24)], outline=(255,255,255,12), width=1)

    # center badge circle
    cx, cy = W//2, H//2 - 40
    # green circle for TG
    d.ellipse([(cx-210, cy-210),(cx+210, cy+210)], fill=(0,208,132), outline=(255,255,255,40), width=4)
    d.ellipse([(cx-190, cy-190),(cx+190, cy+190)], fill=(15,15,30))

    # telegram plane icon (simplified)
    # white circle inner
    d.ellipse([(cx-90, cy-70),(cx+90, cy+70)], fill=(255,255,255))
    # plane shape
    # draw paper plane polygon
    plane = [(cx-55, cy-5),(cx+60, cy-15),(cx+40, cy+10),(cx+50, cy+30),(cx-10, cy+15),(cx-55, cy+35)]
    d.polygon(plane, fill=(0,208,132), outline=(0,0,0,20), width=1)
    d.polygon([(cx-55, cy-5),(cx-10, cy+15),(cx-55, cy+35)], fill=(0,160,110))

    # TG text below plane
    f_tg = _font(82, bold=True)
    d.text((cx, cy+155), "TG", font=f_tg, fill=(255,255,255), anchor="mm", stroke_width=2, stroke_fill=(0,0,0,50))
    f_stock = _font(38, bold=True)
    d.text((cx, cy+225), "STOCK BOT", font=f_stock, fill=(255,255,255), anchor="mm")
    f_sub = _font(20)
    d.text((cx, cy+265), "SECURE  •  REAL  •  PERMANENT", font=f_sub, fill=(255,255,255,180), anchor="mm")

    # top small badge
    d.rounded_rectangle([(W//2-140, 82),(W//2+140, 118)], radius=18, fill=(255,255,255,14), outline=(255,255,255,20))
    d.text((W//2, 99), "✦  @TgStockHubBOT  ✦", font=_font(16, bold=True), fill=(255,255,255), anchor="mm")

    # bottom UPI
    d.rounded_rectangle([(W//2-200, H-110),(W//2+200, H-70)], radius=20, fill=(255,255,255,10), outline=(255,255,255,15))
    d.text((W//2, H-89), "alphajip1@naviaxis", font=_font(16), fill=(255,255,255,170), anchor="mm")

    # hardcore: resolve relative to tgshop_bot
    if not os.path.isabs(out):
        out = os.path.join(os.path.dirname(os.path.dirname(__file__)), out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"saved {out} {W}x{H}")

if __name__ == "__main__":
    make_pfp("assets/pfp.png")
