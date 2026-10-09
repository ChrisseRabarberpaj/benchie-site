#!/usr/bin/env python3
"""Bench of the week card, drawn server-side (same layout and copy as the app's share cards).

Usage: card.py --lat 60.17 --lng 24.94 --km 25 --out week   (needs SUPABASE_URL and SUPABASE_KEY in the env)
Writes <out>/latest.png and <out>/<iso-week>.png, prints a JSON line with the bench and the caption.
"""
import argparse, datetime, io, json, math, os, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
LOGOS = os.path.join(HERE, "logos")
W = 1080
PINE, INK, MUTED, BIRCH, GOLD, LINE = "#1f5a3f", "#1d2a24", "#5d6b64", "#f3f6f1", "#f2b63b", "#d6ddd4"

def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)

def score_line(v):
    return ("Flawless. We checked twice." if v >= 4.9 else "Among the finest seating in town." if v >= 4.5 else
            "A serious bench." if v >= 4 else "Adequate. The view does some of the work." if v >= 3 else
            "It is, technically, a bench." if v >= 2 else "We sat so you do not have to.")

def rpc(url, key, fn, params):
    req = urllib.request.Request(f"{url}/rest/v1/rpc/{fn}", data=json.dumps(params).encode(),
                                 headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def star(d, cx, cy, outer, inner, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = inner if i % 2 else outer
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=fill)

def wrap(d, text, x, y, max_w, lh, f, fill):
    line = ""
    for w in text.split(" "):
        t = (line + " " + w).strip()
        if d.textlength(t, font=f) > max_w and line:
            d.text((x, y), line, font=f, fill=fill); line = w; y += lh
        else:
            line = t
    if line:
        d.text((x, y), line, font=f, fill=fill)
    return y + lh

def svg_png(path, height):
    import cairosvg
    return Image.open(io.BytesIO(cairosvg.svg2png(url=path, output_height=height))).convert("RGBA")

def photo_for(url, key, bench_id):
    """Newest visible photo of the bench, as a PIL image, or None."""
    try:
        rows = rpc(url, key, "bench_photo_heads", {"p_ids": [bench_id]})
        if not rows:
            return None
        pub = f"{url}/storage/v1/object/public/bench-photos/{rows[0]['path']}"
        with urllib.request.urlopen(pub, timeout=30) as r:
            return Image.open(io.BytesIO(r.read())).convert("RGB")
    except Exception as e:
        print("photo:", e, file=sys.stderr)
        return None

def draw_photo(bench, week_n, photo):
    """Photo across the top half, chips on it, verdict below (same as the app's photo card)."""
    im = Image.new("RGB", (W, W), BIRCH)
    ph = 540
    s = max(W / photo.width, ph / photo.height)
    p = photo.resize((int(photo.width * s) + 1, int(photo.height * s) + 1), Image.LANCZOS)
    im.paste(p.crop(((p.width - W) // 2, (p.height - ph) // 2, (p.width - W) // 2 + W, (p.height - ph) // 2 + ph)), (0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle((48, 48, 318, 124), radius=38, fill=(243, 246, 241, 235))
    try:
        lk = svg_png(os.path.join(LOGOS, "benchie-lockup.svg"), 48); im.paste(lk, (74, 62), lk)
    except Exception as e:
        print("lockup:", e, file=sys.stderr)
    mono = font("DMMono-500.ttf", 28)
    place = bench.get("municipality") or ""
    if place:
        tw = d.textlength(place, font=mono)
        d.rounded_rectangle((W - 48 - tw - 48, 48, W - 48, 112), radius=32, fill=(243, 246, 241, 235))
        d.text((W - 48 - tw - 24, 66), place, font=mono, fill=MUTED)
    name = bench.get("name") or (f"Bench, {place}" if place else "Bench")
    y = wrap(d, name, 72, ph + 34, W - 144, 66, font("BricolageGrotesque-800.ttf", 60), INK) + 16
    avg = bench.get("avg")
    if avg is not None:
        fbig = font("DMMono-500.ttf", 104); big = f"{avg:.1f}"
        d.text((72, y), big, font=fbig, fill=INK)
        sx = 72 + d.textlength(big, font=fbig) + 28
        star(d, sx, y + 54, 30, 12, GOLD)
        n = bench.get("n") or 0
        d.text((sx + 50, y + 38), f"{n} rating{'' if n == 1 else 's'}", font=font("Figtree-500.ttf", 28), fill=MUTED)
        y += 128
        x = 72
        for label, v in (("COMFORT", bench.get("comfort")), ("VIEW", bench.get("view")), ("BUILD", bench.get("build"))):
            v = v or 0
            d.text((x, y), label, font=font("Figtree-700.ttf", 22), fill=MUTED)
            for i in range(1, 6):
                star(d, x + 14 + (i - 1) * 30, y + 46, 12, 5, GOLD if v >= i - 0.25 else LINE)
            d.text((x + 170, y + 34), f"{v:.1f}", font=font("DMMono-500.ttf", 22), fill=INK)
            x += 290
        y += 84
    line = f"Bench of the week. {week_n} {'person' if week_n == 1 else 'people'} sat here and said so."
    wrap(d, line, 72, y, W - 144, 44, font("Figtree-500.ttf", 34), PINE)
    d.rectangle((0, W - 88, W, W), fill=PINE)
    try:
        mk = svg_png(os.path.join(LOGOS, "benchie-mark-reverse.svg"), 56); im.paste(mk, (72, W - 72), mk)
    except Exception as e:
        print("mark:", e, file=sys.stderr)
    d.text((150, W - 62), "benchie.world", font=font("DMMono-500.ttf", 26), fill=BIRCH)
    ff = font("Figtree-500.ttf", 26); foot = "Bench of the week"
    d.text((W - 72 - d.textlength(foot, font=ff), W - 62), foot, font=ff, fill=BIRCH)
    return im, line

def draw(bench, week_n):
    im = Image.new("RGB", (W, W), BIRCH)
    d = ImageDraw.Draw(im)
    try:
        lk = svg_png(os.path.join(LOGOS, "benchie-lockup.svg"), 64); im.paste(lk, (72, 64), lk)
    except Exception as e:
        print("lockup:", e, file=sys.stderr)
    mono = font("DMMono-500.ttf", 28)
    place = bench.get("municipality") or ""
    d.text((W - 72 - d.textlength(place, font=mono), 110 - 28), place, font=mono, fill=MUTED)
    name = bench.get("name") or f"Bench, {place}" if place else "Bench"
    y = wrap(d, name, 72, 300 - 80, W - 144, 88, font("BricolageGrotesque-800.ttf", 80), INK)
    y = max(y, 520)
    avg = bench.get("avg")
    if avg is not None:
        big = f"{avg:.1f}"
        fbig = font("DMMono-500.ttf", 160)
        d.text((72, y + 120 - 160), big, font=fbig, fill=INK)
        bw = d.textlength(big, font=fbig)
        sx, sy = 72 + bw + 36, y + 60
        star(d, sx, sy, 44, 18, GOLD)
        n = bench.get("n") or 0
        d.text((sx + 44 + 28, y + 72 - 32), f"{n} rating{'' if n == 1 else 's'}", font=font("Figtree-500.ttf", 32), fill=MUTED)
        y += 180
        x = 72
        for label, v in (("COMFORT", bench.get("comfort")), ("VIEW", bench.get("view")), ("BUILD", bench.get("build"))):
            v = v or 0
            d.text((x, y + 30 - 26), label, font=font("Figtree-700.ttf", 26), fill=MUTED)
            for i in range(1, 6):
                star(d, x + 20 + (i - 1) * 36, y + 66, 15, 6.5, GOLD if v >= i - 0.25 else LINE)
            d.text((x + 206, y + 76 - 26), f"{v:.1f}", font=font("DMMono-500.ttf", 26), fill=INK)
            x += 310
        y += 120
    line = f"Bench of the week. {week_n} {'person' if week_n == 1 else 'people'} sat here and said so." + ("" if avg is None else " " + score_line(avg))
    wrap(d, line, 72, max(y + 40, 820) - 40, W - 144, 52, font("Figtree-500.ttf", 40), PINE)
    d.rectangle((0, W - 88, W, W), fill=PINE)
    try:
        mk = svg_png(os.path.join(LOGOS, "benchie-mark-reverse.svg"), 56); im.paste(mk, (72, W - 72), mk)
    except Exception as e:
        print("mark:", e, file=sys.stderr)
    d.text((150, W - 36 - 26), "benchie.world", font=font("DMMono-500.ttf", 26), fill=BIRCH)
    foot = "Bench of the week"
    ff = font("Figtree-500.ttf", 26)
    d.text((W - 72 - d.textlength(foot, font=ff), W - 36 - 26), foot, font=ff, fill=BIRCH)
    return im, line

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=60.17); ap.add_argument("--lng", type=float, default=24.94)
    ap.add_argument("--km", type=float, default=25); ap.add_argument("--out", default="site/week")
    a = ap.parse_args()
    url, key = os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]
    rows = rpc(url, key, "bench_of_week", {"p_lat": a.lat, "p_lng": a.lng, "p_km": a.km})
    if not rows:
        print(json.dumps({"bench": None})); sys.exit(0)
    b = rows[0]
    photo = photo_for(url, key, b["id"])
    im, caption = draw_photo(b, b.get("week_n", 0), photo) if photo else draw(b, b.get("week_n", 0))
    os.makedirs(a.out, exist_ok=True)
    wk = datetime.date.today().isocalendar()
    for fn in ("latest.png", f"{wk[0]}-w{wk[1]:02d}.png"):
        im.save(os.path.join(a.out, fn), optimize=True)
    print(json.dumps({"bench": b["id"], "name": b.get("name"), "municipality": b.get("municipality"), "avg": b.get("avg"), "week_n": b.get("week_n"), "caption": caption}))
