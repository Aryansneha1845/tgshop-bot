from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

W, H = 1080, 1350
BG_DARK = (15, 15, 30)
BG_GRAD2 = (35, 15, 60)
ACCENT_GREEN = (0, 208, 132)
ACCENT_PURPLE = (95, 44, 131)
GOLD = (255, 215, 0)

def _load_font(size, bold=False):
    # try DejaVu, fallback default
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf" if not bold else "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def _gradient_bg():
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_DARK[0] * (1-t) + BG_GRAD2[0]*t)
        g = int(BG_DARK[1] * (1-t) + BG_GRAD2[1]*t)
        b = int(BG_DARK[2] * (1-t) + BG_GRAD2[2]*t)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    # subtle glow circles
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W-400, 100, W+200, 600], fill=(95,44,131,40))
    gd.ellipse([-200, H-600, 400, H], fill=(0,208,132,30))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    return img

def generate_welcome_image(name: str, balance: float, wholesale: bool, out_path: str):
    name = (name or "Anonymous").strip()[:20]
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)

    # fonts
    f_title = _load_font(64, bold=True)
    f_sub = _load_font(34)
    f_bal = _load_font(38, bold=True)
    f_small = _load_font(26)
    f_tiny = _load_font(20)

    # top badge — TG STOCK BOT
    badge_w, badge_h = 420, 56
    bx = (W - badge_w)//2
    by = 90
    draw.rounded_rectangle([(bx, by),(bx+badge_w, by+badge_h)], radius=28, fill=(255,255,255,18), outline=(255,255,255,35), width=1)
    # navi n icon mini
    draw.rounded_rectangle([(bx+12, by+10),(bx+52, by+46)], radius=10, fill=ACCENT_GREEN)
    draw.text((bx+68, by+10), "TG STOCK BOT", font=_load_font(22, bold=True), fill=(255,255,255))
    draw.text((bx+68, by+32), "Secure • Real • Permanent", font=_load_font(12), fill=(255,255,255,180))

    # welcome
    y = 210
    draw.text((W//2, y), "👋 Welcome,", font=f_sub, fill=(255,255,255,200), anchor="mm")
    y+= 55
    draw.text((W//2, y), f"{name} ji!", font=f_title, fill=(255,255,255), anchor="mm", stroke_width=1, stroke_fill=(0,0,0,60))
    y+= 20
    # underline accent
    draw.rounded_rectangle([(W//2-90, y),(W//2+90, y+4)], radius=2, fill=ACCENT_GREEN)

    # card — balance
    y = 420
    card_w, card_h = 880, 420
    cx = (W-card_w)//2
    # card shadow
    shadow = Image.new("RGBA", (W, H), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([(cx+6, y+6),(cx+card_w+6, y+card_h+6)], radius=32, fill=(0,0,0,60))
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(cx,y),(cx+card_w, y+card_h)], radius=32, fill=(255,255,255,12), outline=(255,255,255,25), width=1)
    # left accent bar
    draw.rounded_rectangle([(cx, y),(cx+8, y+card_h)], radius=4, fill=ACCENT_GREEN)

    # inside card
    pad = 44
    # balance row
    draw.text((cx+pad, y+32), "💳  Balance", font=f_small, fill=(255,255,255,170))
    draw.text((cx+pad, y+72), f"₹{balance:.2f}", font=ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 52) if os.path.exists("C:/Windows/Fonts/segoeuib.ttf") else f_bal, fill=(255,255,255))
    # wholesale badge inside card
    ws_text = "✅ Wholesale Enabled 10% OFF" if wholesale else "❌ Wholesale Disabled"
    ws_bg = (0,208,132,30) if wholesale else (255,80,80,20)
    ws_w = 420 if wholesale else 360
    draw.rounded_rectangle([(cx+card_w - ws_w - pad, y+78),(cx+card_w - pad, y+118)], radius=20, fill=ws_bg, outline=(255,255,255,15))
    draw.text((cx+card_w - ws_w - pad + 18, y+87), ws_text, font=_load_font(16, bold=True), fill=(255,255,255))

    # divider
    draw.line([(cx+pad, y+148),(cx+card_w-pad, y+148)], fill=(255,255,255,30), width=1)

    # features rows
    feats = [
        ("🛒", "Purchase Tg Account", "Budget & Premium • 6 regions"),
        ("💵", "Add Funds", "UPI alphajip1@naviaxis • 12-digit UTR"),
        ("📦", "Order History", "Last 10 • auto-delete 5min"),
    ]
    fy = y + 170
    for emoji, title, sub in feats:
        draw.rounded_rectangle([(cx+pad, fy),(cx+pad+56, fy+56)], radius=14, fill=(255,255,255,10))
        draw.text((cx+pad+16, fy+10), emoji, font=_load_font(28), fill=(255,255,255))
        draw.text((cx+pad+76, fy+6), title, font=_load_font(22, bold=True), fill=(255,255,255))
        draw.text((cx+pad+76, fy+32), sub, font=_load_font(14), fill=(255,255,255,150))
        fy += 72

    # bottom — secure + support
    yb = y + card_h + 48
    draw.rounded_rectangle([(W//2-320, yb),(W//2+320, yb+56)], radius=28, fill=(255,255,255,10), outline=(255,255,255,15))
    draw.text((W//2, yb+16), "🔒 Secure • Real permanent only • No demo", font=_load_font(15), fill=(255,255,255,180), anchor="mm")
    draw.text((W//2, yb+34), "Support  @samosawithchatni  •  UPI alphajip1@naviaxis", font=_load_font(13), fill=(255,255,255,120), anchor="mm")

    # footer small
    draw.text((W//2, H-40), "TG STOCK BOT  •  @TgStockHubBOT  •  ARYAN SANTOSH SINGH", font=f_tiny, fill=(255,255,255,80), anchor="mm")

    # save
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return out_path

if __name__ == "__main__":
    generate_welcome_image("Anonymous", 0.00, True, "assets/welcome_demo.png")
    print("demo saved to assets/welcome_demo.png")
