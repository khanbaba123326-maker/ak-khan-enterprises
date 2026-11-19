#!/usr/bin/env python3
"""AK Khan Enterprises — static site generator.

Reads verified data from ~/workspace/ak-khan-github-site-staging/ and
generates the complete static site into this folder (site root = parent of tools/).
No invented specs, prices, warranties, reviews or availability anywhere.
Images are embedded as base64 data URIs (GitHub snapshot pushes are text-only);
the logo SVG stays a real file. Hero images are downscaled to max 1000px/q62
to keep page sizes sane. Run: python3 tools/generate.py
"""
import base64, html, io, json, os, re, shutil, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
STAGING = Path.home() / "workspace" / "ak-khan-github-site-staging"

WA_NUM = "923067000682"
WA_DISPLAY = "0306-7000682"
EMAIL = "akkhanenterprises682@gmail.com"
ADDRESS = "Faiz Muhammad Street, Liaqat Bazar, Quetta"
TAGLINE = "Your One-Stop ELECTRONICS & SECURITY SOLUTION IN QUETTA"
FB_URL = "https://www.facebook.com/61595712927205"
IG1 = "https://www.instagram.com/ak_khan682"
IG2 = "https://www.instagram.com/akkhan.enterprises"

products = json.load(open(STAGING / "products.json"))
prices = json.load(open(STAGING / "prices.json"))
videos = json.load(open(STAGING / "videos.json"))
WAS = {p["matched_product_id"]: p.get("was_pkr") for p in prices}
VID_TITLE = {v["video_id"]: v.get("title_or_null") or "DJI film"
             for v in videos if v.get("verified")}
FAILED_VIDEO = "48_kEK9iFKU"

CATS = {
    "drones":     {"label": "Drones",     "nav": "Drones",     "hero": "hero-drone.jpg",
                   "intro": "DJI camera drones — from pocket Minis to enterprise Matrice and Agras platforms. Aerial film, photography and professional work, from the shop floor in Quetta.",
                   "blurb": "Camera drones for creators, travellers and professionals."},
    "cctv":       {"label": "Cameras",    "nav": "Cameras",    "hero": "cctv-hi.jpg",
                   "intro": "Security cameras, NVRs and video servers from Dahua, Hikvision, Tiandy, EZVIZ, IMOU, V380 Pro and iCSee — for homes, shops and full sites.",
                   "blurb": "CCTV cameras, NVRs and video servers."},
    "displays":   {"label": "Displays",   "nav": "Displays",   "hero": "tv.jpg",
                   "intro": "LED TVs from Samsung, LG and Sony — from 43 inch to cinema-size 75 inch Bravia.",
                   "blurb": "LED TVs from Samsung, LG and Sony."},
    "networking": {"label": "Networking", "nav": "Networking", "hero": "networking.jpg",
                   "intro": "Routers, access points and switches from Ruijie, TP-Link, Tenda and Ubiquiti — home Wi-Fi to business networks.",
                   "blurb": "Routers, access points and switches."},
    "audio":      {"label": "Sound",      "nav": "Sound",      "hero": "speaker.jpg",
                   "intro": "Audionic sound — earbuds, Bluetooth speakers, soundbars, home theatre, party speakers and more.",
                   "blurb": "Audionic earbuds, speakers and sound systems."},
}
CAT_ORDER = ["drones", "cctv", "displays", "networking", "audio"]

# ---------- image embedding ----------
from PIL import Image

def _b64(data: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()

def hero_uri(name: str) -> str:
    """Downscaled hero image as data URI (max 1000px wide, q62)."""
    p = STAGING / "images" / "hero" / name
    im = Image.open(p).convert("RGB")
    if im.width > 1000:
        im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=62, optimize=True)
    return _b64(buf.getvalue())

def img_uri(rel: str) -> str:
    return _b64((STAGING / rel).read_bytes())

def fmt_pkr(n) -> str:
    return "Rs " + f"{n:,}"

# ---------- helpers ----------
def esc(s) -> str:
    return html.escape(str(s), quote=True)

def wa_link(product_name: str | None = None) -> str:
    if product_name:
        msg = (f"Assalam-o-Alaikum! I am interested in {product_name}. "
               "Please share its current price, availability and complete details.")
    else:
        msg = "Assalam-o-Alaikum! I would like to ask about a product at AK Khan Enterprises."
    return f"https://wa.me/{WA_NUM}?text=" + urllib.parse.quote(msg, safe="")

def price_html(p) -> str:
    if p.get("price_pkr"):
        was = WAS.get(p["id"])
        was_html = f' <span class="was">was {fmt_pkr(was)}</span>' if was else ""
        return (f'<p class="price">{fmt_pkr(p["price_pkr"])}{was_html}</p>'
                f'<p class="price-note">Today&rsquo;s price confirmed on WhatsApp.</p>')
    return ('<p class="price por">Price on request</p>'
            '<p class="price-note">Confirmed on WhatsApp.</p>')

def price_text(p) -> str:
    return fmt_pkr(p["price_pkr"]) if p.get("price_pkr") else "Price on request"

def product_url(p) -> str:
    return f"products/{p['slug']}.html"

def by_id(pid):
    return next(p for p in products if p["id"] == pid)

def related(p, n=4):
    same_brand = [x for x in products if x["category"] == p["category"]
                  and x["brand"] == p["brand"] and x["id"] != p["id"]]
    same_cat = [x for x in products if x["category"] == p["category"]
                and x["brand"] != p["brand"] and x["id"] != p["id"]]
    return (same_brand + same_cat)[:n]

def card(p, depth=""):
    thumb = (f'<img src="{img_uri(p["photo_thumb"])}" alt="{esc(p["name"])}" loading="lazy">'
             if p.get("photo_thumb") else
             '<div class="no-photo">Photo coming soon</div>')
    return f"""<article class="card" data-brand="{esc(p["brand"])}" data-name="{esc(p["name"].lower())}" data-price="{p["price_pkr"] or ''}">
  <a class="card-img" href="{depth}{product_url(p)}" aria-label="{esc(p["name"])}">{thumb}</a>
  <div class="card-body">
    <p class="card-cat">{esc(p["brand"])} &middot; {esc(CATS[p["category"]]["label"])}</p>
    <h3><a href="{depth}{product_url(p)}">{esc(p["name"])}</a></h3>
    <p class="card-tag">{esc(p["tagline"])}</p>
    {price_html(p)}
    <div class="card-actions">
      <a class="btn btn-dark" href="{depth}{product_url(p)}">View Details</a>
      <a class="btn btn-wa" href="{wa_link(p["name"])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
    </div>
  </div>
</article>"""

# ---------- chrome ----------
def nav_links(depth):
    out = []
    for c in CAT_ORDER:
        feats = [x for x in products if x["category"] == c][:3]
        prods = "".join(
            f'<a class="mega-prod" href="{depth}products/{x["slug"]}.html">{esc(x["name"])}</a>'
            for x in feats)
        out.append(
            f'<div class="mega-col"><a class="mega-cat" href="{depth}categories/{c}.html">{CATS[c]["nav"]}</a>'
            f'<p>{esc(CATS[c]["blurb"])}</p>{prods}'
            f'<a class="mega-all" href="{depth}categories/{c}.html">View all {CATS[c]["label"]} &rarr;</a></div>')
    return "".join(out)

def chrome(depth, title, desc, body, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="stylesheet" href="{depth}assets/style.css">
<link rel="icon" href="{depth}assets/logo-mark.svg" type="image/svg+xml">
{extra_head}
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{depth}index.html"><img src="{depth}assets/logo-mark.svg" alt="AK Khan Enterprises — gold AK monogram" class="logo"><span class="brand-text"><strong>AK KHAN</strong><em>ENTERPRISES</em></span></a>
    <button class="menu-btn" id="menuBtn" aria-label="Open menu" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" id="mainNav" aria-label="Main navigation">
      <div class="nav-item has-mega"><button class="nav-link" aria-haspopup="true">Shop</button>
        <div class="mega-menu">{nav_links(depth)}</div>
      </div>
      <a class="nav-link" href="{depth}explore.html">Explore</a>
      <a class="nav-link" href="{depth}about.html">About Us</a>
      <a class="nav-link" href="{depth}support.html">Support</a>
      <a class="nav-link" href="{depth}contact.html">Contact</a>
      <a class="nav-link" href="{depth}search.html">Search</a>
      <a class="nav-link" href="{depth}compare.html">Compare</a>
      <a class="nav-link nav-wa" href="{wa_link()}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
    </nav>
  </div>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <div class="footer-inner">
    <div class="foot-brand">
      <img src="{depth}assets/logo-mark.svg" alt="AK Khan Enterprises logo" class="logo">
      <p><strong>AK KHAN ENTERPRISES</strong></p>
      <p>{esc(TAGLINE)}</p>
      <p>Trusted since 2015.</p>
    </div>
    <div class="foot-col"><h4>Shop</h4>
      {"".join(f'<a href="{depth}categories/{c}.html">{CATS[c]["nav"]}</a>' for c in CAT_ORDER)}
      <a href="{depth}explore.html">Explore</a>
      <a href="{depth}compare.html">Compare Products</a>
    </div>
    <div class="foot-col"><h4>Support</h4>
      <a href="{depth}support.html">Customer Support</a>
      <a href="{depth}faq.html">FAQ</a>
      <a href="{depth}about.html">About Us</a>
      <a href="{depth}contact.html">Contact</a>
    </div>
    <div class="foot-col"><h4>Contact</h4>
      <p>{esc(ADDRESS)}</p>
      <p>WhatsApp: <a href="{wa_link()}" target="_blank" rel="noopener">{WA_DISPLAY}</a></p>
      <p>Email: <a href="mailto:{EMAIL}">{EMAIL}</a></p>
      <p><a href="{IG1}" target="_blank" rel="noopener">Instagram @ak_khan682</a><br>
      <a href="{IG2}" target="_blank" rel="noopener">Instagram @akkhan.enterprises</a><br>
      <a href="{FB_URL}" target="_blank" rel="noopener">Facebook</a></p>
    </div>
  </div>
  <div class="footer-bottom">
    <p>&copy; 2026 AK Khan Enterprises, Quetta. All rights reserved.</p>
    <p><a href="{depth}privacy.html">Privacy Policy</a> &middot; <a href="{depth}terms.html">Terms</a></p>
    <p class="foot-note">Orders are taken on WhatsApp only. There is no online checkout on this website.</p>
  </div>
</footer>
<a class="wa-float" href="{wa_link()}" target="_blank" rel="noopener" aria-label="Chat on WhatsApp"><span>WhatsApp</span></a>
<script src="{depth}assets/site.js"></script>
</body>
</html>
"""

def hero_section(img, kicker, title, sub, cta=""):
    return f"""<section class="hero" style="background-image:url('{img}')">
  <div class="hero-overlay"></div>
  <div class="hero-content reveal">
    <p class="kicker">{esc(kicker)}</p>
    <h1>{esc(title)}</h1>
    <p class="hero-sub">{esc(sub)}</p>
    {cta}
  </div>
  <a class="scroll-hint" href="#main-content" aria-label="Scroll down">&darr;</a>
</section>
<div id="main-content"></div>"""

def section_head(kicker, title, sub=""):
    s = f'<p class="sec-sub">{esc(sub)}</p>' if sub else ""
    return f'<div class="sec-head reveal"><p class="kicker">{esc(kicker)}</p><h2>{esc(title)}</h2>{s}</div>'

def cta_band(depth):
    return f"""<section class="cta-band reveal">
  <h2>Found something you like?</h2>
  <p>Message the shop on WhatsApp — today&rsquo;s price, availability and complete details, confirmed personally.</p>
  <a class="btn btn-gold btn-lg" href="{wa_link()}" target="_blank" rel="noopener">Chat on WhatsApp — {WA_DISPLAY}</a>
  <p class="cta-addr">{esc(ADDRESS)} &middot; {EMAIL}</p>
</section>"""

# ---------- CSS ----------
CSS = """
:root{--gold:#C9A227;--gold-l:#EED488;--gold-d:#9A7414;--black:#0b0b0c;--navy:#0A1A2F;--char:#17181a;--grey:#f4f4f2;--line:#e4e2dc;--mut:#66655f;--txt:#141414}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--txt);background:#fff;line-height:1.6;overflow-x:hidden}
img{max-width:100%;height:auto;display:block}
a{color:inherit;text-decoration:none}
h1,h2,h3{line-height:1.15;font-weight:800;letter-spacing:-.02em}
h1{font-size:clamp(2rem,6vw,4rem)}
h2{font-size:clamp(1.6rem,4vw,2.5rem)}
.kicker{color:var(--gold-d);text-transform:uppercase;letter-spacing:.22em;font-size:.75rem;font-weight:700}
.wrap{max-width:1200px;margin:0 auto;padding:0 20px}
.sec{padding:64px 0}
.sec.dark{background:var(--black);color:#fff}
.sec.navy{background:var(--navy);color:#fff}
.sec.grey{background:var(--grey)}
.sec-head{max-width:760px;margin:0 auto 40px;text-align:center}
.sec-head h2{margin:8px 0 10px}
.sec-sub{color:var(--mut);font-size:1.05rem}
.dark .sec-sub,.navy .sec-sub{color:#c9c9c9}
/* header */
.site-header{position:sticky;top:0;z-index:100;background:rgba(11,11,12,.97);color:#fff;backdrop-filter:blur(6px)}
.header-inner{max-width:1280px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;gap:24px}
.brand{display:flex;align-items:center;gap:10px}
.logo{width:44px;height:32px}
.brand-text{display:flex;flex-direction:column;line-height:1.05}
.brand-text strong{font-size:1.05rem;letter-spacing:.08em}
.brand-text em{font-style:normal;font-size:.62rem;letter-spacing:.34em;color:var(--gold-l)}
.main-nav{margin-left:auto;display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.nav-link{color:#eee;padding:10px 12px;font-size:.95rem;border:0;background:none;cursor:pointer;font-family:inherit}
.nav-link:hover{color:var(--gold-l)}
.nav-wa{color:#1d1d1d;background:linear-gradient(135deg,var(--gold-l),var(--gold) 55%,var(--gold-d));border-radius:999px;font-weight:700;padding:9px 16px}
.nav-wa:hover{color:#000}
.menu-btn{display:none;background:none;border:0;color:#fff;font-size:1.7rem;cursor:pointer;margin-left:auto}
.nav-item{position:relative}
.mega-menu{position:absolute;left:50%;transform:translate(-50%,8px);top:100%;background:#fff;color:var(--txt);display:none;gap:0;width:min(860px,94vw);border-radius:14px;box-shadow:0 24px 60px rgba(0,0,0,.35);padding:22px;grid-template-columns:repeat(5,1fr)}
.nav-item:hover .mega-menu,.nav-item:focus-within .mega-menu{display:grid}
.mega-col{padding:0 12px;border-left:1px solid var(--line)}
.mega-col:first-child{border-left:0}
.mega-cat{font-weight:800;font-size:1rem;color:var(--gold-d)}
.mega-col p{font-size:.82rem;color:var(--mut);margin:6px 0 10px}
.mega-prod{display:block;font-size:.86rem;padding:5px 0;border-top:1px solid #f0efe9}
.mega-prod:hover{color:var(--gold-d)}
.mega-all{display:block;margin-top:10px;font-size:.85rem;font-weight:700;color:var(--gold-d)}
/* hero */
.hero{position:relative;min-height:88vh;background-size:cover;background-position:center;display:flex;align-items:flex-end;color:#fff}
.hero-overlay{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.25),rgba(0,0,0,.55) 55%,rgba(0,0,0,.82))}
.hero-content{position:relative;max-width:1200px;margin:0 auto;padding:90px 20px 110px;width:100%}
.hero-content h1{max-width:16ch}
.hero-content .kicker{color:var(--gold-l)}
.hero-sub{max-width:56ch;margin:16px 0 26px;font-size:clamp(1rem,2vw,1.2rem);color:#eee}
.hero-cta{display:flex;gap:12px;flex-wrap:wrap}
.scroll-hint{position:absolute;bottom:22px;left:50%;transform:translateX(-50%);color:#fff;font-size:1.4rem;opacity:.8}
.hero.small{min-height:52vh}
/* buttons */
.btn{display:inline-block;padding:12px 22px;border-radius:999px;font-weight:700;font-size:.95rem;text-align:center;border:1px solid transparent;cursor:pointer}
.btn-gold{background:linear-gradient(135deg,var(--gold-l),var(--gold) 55%,var(--gold-d));color:#161616}
.btn-dark{background:var(--black);color:#fff}
.btn-light{background:#fff;color:#111}
.btn-wa{background:#25D366;color:#fff}
.btn-outline{border-color:#fff;color:#fff}
.btn-lg{padding:15px 30px;font-size:1.05rem}
/* cards */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:22px}
.card{border:1px solid var(--line);border-radius:16px;overflow:hidden;background:#fff;display:flex;flex-direction:column;transition:transform .25s,box-shadow .25s}
.card:hover{transform:translateY(-4px);box-shadow:0 18px 40px rgba(0,0,0,.12)}
.card-img{display:block;background:#faf9f6;aspect-ratio:4/3;overflow:hidden}
.card-img img{width:100%;height:100%;object-fit:contain;transition:transform .4s}
.card:hover .card-img img{transform:scale(1.06)}
.card-body{padding:18px;display:flex;flex-direction:column;gap:8px;flex:1}
.card-cat{font-size:.75rem;text-transform:uppercase;letter-spacing:.14em;color:var(--gold-d);font-weight:700}
.card-body h3{font-size:1.08rem}
.card-body h3 a:hover{color:var(--gold-d)}
.card-tag{color:var(--mut);font-size:.92rem;flex:1}
.price{font-size:1.25rem;font-weight:800}
.price .was{font-size:.9rem;color:var(--mut);text-decoration:line-through;font-weight:400;margin-left:8px}
.price.por{font-size:1.05rem;color:var(--gold-d)}
.price-note{font-size:.82rem;color:var(--mut)}
.card-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
.card-actions .btn{flex:1;padding:10px 8px;font-size:.88rem;white-space:nowrap}
/* editorial feature */
.feature{display:grid;grid-template-columns:1fr 1fr;gap:0;align-items:stretch;border-radius:20px;overflow:hidden;margin-bottom:28px;background:#111;color:#fff}
.feature.light{background:#fff;color:var(--txt);border:1px solid var(--line)}
.feature .f-img{min-height:340px;background-size:cover;background-position:center}
.feature .f-img img{width:100%;height:100%;object-fit:cover}
.feature .f-body{padding:44px;display:flex;flex-direction:column;justify-content:center;gap:12px}
.feature.flip .f-img{order:2}
.feature .f-body p{color:#cfcfcf}
.feature.light .f-body p{color:var(--mut)}
/* category tiles */
.cat-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px}
.cat-tile{position:relative;border-radius:16px;overflow:hidden;min-height:260px;display:flex;align-items:flex-end;color:#fff;background-size:cover;background-position:center}
.cat-tile::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 30%,rgba(0,0,0,.85))}
.cat-tile div{position:relative;z-index:1;padding:20px}
.cat-tile h3{font-size:1.25rem}
.cat-tile p{font-size:.9rem;color:#ddd}
/* video */
.video-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.video-card{background:#111;border-radius:14px;overflow:hidden;color:#fff}
.video-card iframe{width:100%;aspect-ratio:16/9;border:0;display:block}
.video-card .v-body{padding:14px 16px}
.video-card .v-body p{font-size:.9rem;color:#bbb}
.video-card h3{font-size:1rem}
/* why */
.why-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px}
.why{border:1px solid var(--line);border-radius:14px;padding:26px;background:#fff}
.why h3{font-size:1.1rem;margin-bottom:8px}
.why p{color:var(--mut);font-size:.95rem}
.why .ic{font-size:1.6rem}
/* toolbar */
.toolbar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:0 0 26px}
.toolbar select,.toolbar input[type=search]{padding:11px 14px;border:1px solid var(--line);border-radius:999px;font-size:.95rem;font-family:inherit;background:#fff}
.toolbar .count{margin-left:auto;color:var(--mut);font-size:.92rem}
/* detail */
.detail-hero{display:grid;grid-template-columns:1.05fr 1fr;gap:44px;align-items:start}
.detail-photo{border:1px solid var(--line);border-radius:18px;overflow:hidden;background:#faf9f6;cursor:zoom-in}
.detail-photo img{width:100%;aspect-ratio:4/3;object-fit:contain}
.no-photo{border:2px dashed var(--gold);border-radius:18px;padding:60px 24px;text-align:center;color:var(--gold-d);background:#fdf8e7}
.no-photo strong{display:block;font-size:1.15rem;margin-bottom:8px}
.detail-info h1{font-size:clamp(1.7rem,4vw,2.6rem)}
.detail-info .tagline{font-size:1.15rem;color:var(--mut);margin:10px 0 18px}
.detail-info .price{font-size:1.7rem}
.detail-actions{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}
.spec-box{border:1px solid var(--line);border-radius:14px;padding:22px;background:#fbfaf7;margin-top:22px}
.spec-box h3{margin-bottom:8px}
.spec-box p{color:var(--mut)}
/* lightbox */
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;z-index:200;cursor:zoom-out}
.lightbox.open{display:flex}
.lightbox img{max-width:94vw;max-height:90vh;object-fit:contain}
.lightbox.zoomed img{transform:scale(1.8);cursor:zoom-out}
/* faq */
.faq-item{border:1px solid var(--line);border-radius:12px;margin-bottom:12px;background:#fff}
.faq-item summary{padding:18px 20px;font-weight:700;cursor:pointer;list-style:none}
.faq-item summary::-webkit-details-marker{display:none}
.faq-item .fa{padding:0 20px 18px;color:var(--mut)}
/* forms / misc */
.prose{max-width:760px;margin:0 auto}
.prose p{margin-bottom:14px;color:#333}
.prose h3{margin:26px 0 8px}
.contact-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px}
.contact-card{border:1px solid var(--line);border-radius:14px;padding:24px}
.contact-card h3{margin-bottom:8px}
.cta-band{background:var(--navy);color:#fff;text-align:center;padding:56px 20px;border-radius:20px;margin:20px 0}
.cta-band h2{margin-bottom:10px}
.cta-band p{color:#d5dbe4;margin-bottom:20px}
.cta-addr{font-size:.9rem;margin-top:16px;color:#aeb9c9!important}
.search-box{display:flex;gap:10px;max-width:640px;margin:0 auto 30px}
.search-box input{flex:1;padding:14px 18px;border:1px solid var(--line);border-radius:999px;font-size:1rem}
.compare-table{width:100%;border-collapse:collapse;overflow-x:auto}
.compare-table th,.compare-table td{border:1px solid var(--line);padding:12px;text-align:left;vertical-align:top}
.compare-table th{background:#f8f7f3}
.compare-table img{max-width:140px}
.compare-picks{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}
.compare-picks select{padding:11px 14px;border:1px solid var(--line);border-radius:999px;font-size:.95rem}
.reveal{opacity:0;transform:translateY(18px);transition:opacity .6s,transform .6s}
.reveal.visible{opacity:1;transform:none}
/* footer */
.site-footer{background:var(--black);color:#ddd;margin-top:0}
.footer-inner{max-width:1200px;margin:0 auto;padding:56px 20px 30px;display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;gap:32px}
.footer-inner h4{color:#fff;margin-bottom:12px}
.footer-inner a{display:block;padding:3px 0;color:#bbb}
.footer-inner a:hover{color:var(--gold-l)}
.foot-brand p{margin-top:8px;font-size:.92rem;color:#bbb}
.footer-bottom{border-top:1px solid #262626;text-align:center;padding:22px 20px;font-size:.88rem;color:#999}
.footer-bottom a{color:#ccc}
.foot-note{margin-top:6px}
.wa-float{position:fixed;right:18px;bottom:18px;z-index:150;background:#25D366;color:#fff;font-weight:800;padding:13px 20px;border-radius:999px;box-shadow:0 10px 26px rgba(0,0,0,.3)}
.wa-float:hover{transform:scale(1.04)}
/* responsive */
@media(max-width:900px){
  .feature{grid-template-columns:1fr}
  .feature.flip .f-img{order:0}
  .detail-hero{grid-template-columns:1fr}
  .footer-inner{grid-template-columns:1fr 1fr}
  .mega-menu{display:none!important}
}
@media(max-width:720px){
  .menu-btn{display:block}
  .main-nav{display:none;position:absolute;top:100%;left:0;right:0;background:#0b0b0c;flex-direction:column;align-items:stretch;padding:10px 20px 20px}
  .main-nav.open{display:flex}
  .nav-link{padding:13px 4px;border-top:1px solid #222;font-size:1.02rem}
  .nav-wa{text-align:center;margin-top:10px}
  .sec{padding:44px 0}
  .footer-inner{grid-template-columns:1fr}
  .card-actions .btn{flex:1 1 100%}
  .hero{min-height:78vh}
}
"""

# ---------- JS ----------
JS = """
// mobile menu
var btn=document.getElementById('menuBtn'),nav=document.getElementById('mainNav');
if(btn&&nav){btn.addEventListener('click',function(){var o=nav.classList.toggle('open');btn.setAttribute('aria-expanded',o?'true':'false');});}
// scroll reveal
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target);}});},{threshold:.12});
document.querySelectorAll('.reveal').forEach(function(el){io.observe(el);});
// lightbox (product photo)
var lb=document.getElementById('lightbox');
function openLB(src,alt){if(!lb)return;lb.querySelector('img').src=src;lb.querySelector('img').alt=alt||'';lb.classList.add('open');document.body.style.overflow='hidden';}
function closeLB(){if(!lb)return;lb.classList.remove('open');lb.classList.remove('zoomed');document.body.style.overflow='';}
if(lb){lb.addEventListener('click',function(e){if(e.target.tagName==='IMG'){lb.classList.toggle('zoomed');}else{closeLB();}});document.addEventListener('keydown',function(e){if(e.key==='Escape')closeLB();});}
var dp=document.getElementById('detailPhoto');
if(dp){dp.addEventListener('click',function(){openLB(dp.querySelector('img').src,dp.querySelector('img').alt);});}
// category filter + sort
var grid=document.getElementById('catGrid');
if(grid){
  var brandSel=document.getElementById('brandFilter'),sortSel=document.getElementById('sortSel'),countEl=document.getElementById('resultCount');
  function applyFilter(){
    var cards=Array.prototype.slice.call(grid.querySelectorAll('.card'));
    var b=brandSel?brandSel.value:'';
    var visible=cards.filter(function(c){var ok=!b||c.dataset.brand===b;c.style.display=ok?'':'none';return ok;});
    var s=sortSel?sortSel.value:'name-asc';
    visible.sort(function(a,c){
      if(s==='name-asc')return a.dataset.name.localeCompare(c.dataset.name);
      if(s==='name-desc')return c.dataset.name.localeCompare(a.dataset.name);
      if(s==='price-asc'){var pa=parseFloat(a.dataset.price)||Infinity,pb=parseFloat(c.dataset.price)||Infinity;return pa-pb;}
      if(s==='price-desc'){var pa=parseFloat(a.dataset.price)||0,pb=parseFloat(c.dataset.price)||0;return pb-pa;}
      return 0;
    });
    visible.forEach(function(c){grid.appendChild(c);});
    if(countEl)countEl.textContent=visible.length+' product'+(visible.length===1?'':'s');
  }
  if(brandSel)brandSel.addEventListener('change',applyFilter);
  if(sortSel)sortSel.addEventListener('change',applyFilter);
  applyFilter();
}
// compare: add from product pages
document.querySelectorAll('[data-compare]').forEach(function(b){
  b.addEventListener('click',function(){
    var slug=b.dataset.compare, list=[];
    try{list=JSON.parse(localStorage.getItem('akCompare')||'[]');}catch(e){list=[];}
    if(list.indexOf(slug)===-1){if(list.length>=3){alert('Compare holds up to 3 products. Remove one on the Compare page first.');return;}list.push(slug);localStorage.setItem('akCompare',JSON.stringify(list));}
    b.textContent='Added to compare ✓';
  });
});
"""


# ---------- page builders ----------
def write(rel, content):
    p = SITE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p

def video_embed(vid, title):
    return (f'<div class="video-card"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
            f'title="{esc(title)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
            f'allowfullscreen loading="lazy"></iframe><div class="v-body"><h3>{esc(title)}</h3>'
            f'<p>Official DJI film on YouTube.</p></div></div>')

def product_video(p):
    if not p.get("video_ids"):
        return ""
    vids = [v for v in p["video_ids"] if v != FAILED_VIDEO and v in VID_TITLE]
    if not vids:
        return ""
    cards = "".join(video_embed(v, VID_TITLE[v]) for v in vids)
    return f'<section class="sec"><div class="wrap">{section_head("Watch", "Product film", "The official film for this product.")}<div class="video-grid">{cards}</div></div></section>'

# ----- homepage -----
def build_index():
    featured_ids = [0, 2, 4, 51, 54, 70, 41, 30]  # DJI drones + spread across categories
    feats = [by_id(i) for i in featured_ids]
    # editorial features: alternate large showcases
    f1, f2, f3 = feats[0], feats[1], feats[2]
    def feature(p, hero_img, light=False, flip=False):
        cls = "feature light" if light else "feature"
        if flip: cls += " flip"
        return f"""<div class="{cls} reveal">
  <div class="f-img"><img src="{img_uri(p['photo_thumb'])}" alt="{esc(p['name'])}" loading="lazy"></div>
  <div class="f-body"><p class="kicker">{esc(p['brand'])} &middot; {esc(CATS[p['category']]['label'])}</p>
  <h2>{esc(p['name'])}</h2><p>{esc(p['tagline'])}</p><p>{esc(p['description'])}</p>
  {price_html(p)}
  <div class="hero-cta"><a class="btn btn-gold" href="products/{p['slug']}.html">View Details</a>
  <a class="btn btn-wa" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a></div></div></div>"""
    tiles = "".join(
        f'<a class="cat-tile reveal" style="background-image:url(\'{hero_uri(CATS[c]["hero"])}\')" href="categories/{c}.html">'
        f'<div><p class="kicker">{len([x for x in products if x["category"]==c])} products</p>'
        f'<h3>{CATS[c]["nav"]}</h3><p>{esc(CATS[c]["blurb"])}</p></div></a>'
        for c in CAT_ORDER)
    # brand story videos: all 11 verified films, first 4 on homepage
    vid_items = [(v, VID_TITLE[v]) for v in
                 ["nbXneZzFh8w", "4fhl9F8DZDU", "r5kukRMmZNI", "RNhmV4yCP6M"]]
    vids = "".join(video_embed(v, t) for v, t in vid_items)
    body = f"""
{hero_section(hero_uri('hero-drone.jpg'), 'AK Khan Enterprises &middot; Quetta',
  'Your One-Stop Electronics & Security Solution in Quetta',
  'DJI drones, security cameras, networking, sound and displays — genuine products, expert guidance, and ordering on WhatsApp.',
  '<div class="hero-cta"><a class="btn btn-gold btn-lg" href="#featured">Explore Products</a><a class="btn btn-outline btn-lg" href="explore.html">Discover More</a></div>')}
<section class="sec" id="featured"><div class="wrap">
{section_head('Featured Products', 'The range, up close', 'A selection from the shop floor — drones, cameras, networking, sound and displays.')}
{feature(f1, None)}
{feature(f2, None, light=True, flip=True)}
{feature(f3, None)}
<div class="grid">{''.join(card(p) for p in feats[3:])}</div>
</div></section>
<section class="sec grey"><div class="wrap">
{section_head('Shop by Category', 'Five ranges, one shop', 'Every product in the shop belongs to one of these five ranges.')}
<div class="cat-tiles">{tiles}</div>
</div></section>
<section class="sec dark"><div class="wrap">
{section_head('Cinematic Brand Story', 'Shot from the sky', 'Official DJI films for the drones on our shelves.')}
<div class="video-grid">{vids}</div>
<p style="text-align:center;margin-top:22px"><a class="btn btn-light" href="explore.html">Watch all 11 films on Explore</a></p>
</div></section>
<section class="sec"><div class="wrap">
{section_head('Why Choose Us', 'Why customers come to AK Khan', 'Only what the shop can stand behind.')}
<div class="why-grid">
<div class="why reveal"><p class="ic">&#10003;</p><h3>Genuine products</h3><p>Products from the brands on our shelves — DJI, Dahua, Hikvision, Tiandy, EZVIZ, IMOU, Ruijie, TP-Link, Audionic, Samsung, LG and Sony.</p></div>
<div class="why reveal"><p class="ic">&#9998;</p><h3>Expert guidance</h3><p>Talk to the shop before you buy — which model fits your home, shop or site, and what it will do for you.</p></div>
<div class="why reveal"><p class="ic">&#9990;</p><h3>WhatsApp support</h3><p>Price, availability and complete details confirmed personally on WhatsApp — {WA_DISPLAY}.</p></div>
<div class="why reveal"><p class="ic">&#9873;</p><h3>A real shop in Quetta</h3><p>Visit us at {esc(ADDRESS)} — see the product before you buy, or ask on WhatsApp for a photo of the exact unit in stock.</p></div>
</div></div></section>
<section class="sec grey"><div class="wrap">
{section_head('Explore & Discover', 'From the air', 'Aerial perspectives from the DJI range — the drone photography our customers create with these aircraft.')}
<div class="cat-tiles">
<a class="cat-tile reveal" style="background-image:url('{hero_uri('shot-canyon.jpg')}')" href="explore.html"><div><h3>Canyons from above</h3><p>Aerial photography with DJI drones.</p></div></a>
<a class="cat-tile reveal" style="background-image:url('{hero_uri('shot-desert.jpg')}')" href="explore.html"><div><h3>Desert light</h3><p>Wide open frames, golden hour.</p></div></a>
<a class="cat-tile reveal" style="background-image:url('{hero_uri('field-agri.jpg')}')" href="explore.html"><div><h3>Working from the sky</h3><p>Enterprise and agriculture aircraft.</p></div></a>
</div>
<p style="text-align:center;margin-top:26px"><a class="btn btn-dark" href="explore.html">Explore the stories</a></p>
</div></section>
<div class="wrap">{cta_band('')}</div>
"""
    write("index.html", chrome("", "AK Khan Enterprises — Drones, Cameras, Networking, Sound & Displays in Quetta",
        "AK Khan Enterprises, Quetta — DJI drones, Dahua & Hikvision cameras, networking, Audionic sound and LED TVs. Order on WhatsApp.", body))

# ----- category pages -----
def build_category(c):
    items = [p for p in products if p["category"] == c]
    brands = sorted(set(p["brand"] for p in items))
    feat = items[:3]
    opts = "".join(f'<option value="{esc(b)}">{esc(b)}</option>' for b in brands)
    others = "".join(
        f'<a class="cat-tile" style="background-image:url(\'{hero_uri(CATS[o]["hero"])}\');min-height:180px" href="{o}.html">'
        f'<div><h3>{CATS[o]["nav"]}</h3><p>{esc(CATS[o]["blurb"])}</p></div></a>'
        for o in CAT_ORDER if o != c)
    body = f"""
{hero_section(hero_uri(CATS[c]['hero']), 'AK Khan Enterprises', CATS[c]['label'], CATS[c]['intro'],
  '<div class="hero-cta"><a class="btn btn-gold" href="#listing">Browse all ' + CATS[c]['label'] + '</a></div>')}
<section class="sec" id="listing"><div class="wrap">
{section_head(CATS[c]['label'], f"All {CATS[c]['label']} — {len(items)} products", 'Filter by brand or sort the list. Prices shown where the shop has confirmed one; everything else is confirmed on WhatsApp.')}
<div class="toolbar">
  <label>Brand <select id="brandFilter"><option value="">All brands</option>{opts}</select></label>
  <label>Sort <select id="sortSel"><option value="name-asc">Name A–Z</option><option value="name-desc">Name Z–A</option><option value="price-asc">Price: low to high</option><option value="price-desc">Price: high to low</option></select></label>
  <span class="count" id="resultCount">{len(items)} products</span>
</div>
<div class="grid" id="catGrid">{''.join(card(p, depth="../") for p in items)}</div>
</div></section>
<section class="sec grey"><div class="wrap">
{section_head('Keep exploring', 'Related categories', '')}
<div class="cat-tiles">{others}</div>
</div></section>
<div class="wrap">{cta_band('../')}</div>
"""
    write(f"categories/{c}.html", chrome("../", f"{CATS[c]['label']} — AK Khan Enterprises, Quetta",
        f"{CATS[c]['label']} at AK Khan Enterprises, Quetta. {CATS[c]['intro']}", body))

# ----- product pages -----
def build_product(p):
    if p.get("photo_full"):
        gallery = f"""<div class="detail-photo" id="detailPhoto"><img src="{img_uri(p['photo_full'])}" alt="{esc(p['name'])} — product photo"></div>
<p style="font-size:.85rem;color:var(--mut);margin-top:8px">Tap the photo to view fullscreen. Tap again to zoom.</p>"""
    else:
        gallery = ('<div class="no-photo"><strong>Photo coming soon</strong>'
                   'No photo of this exact unit is available yet. Ask on WhatsApp and the shop will send a photo of the exact unit in stock.</div>')
    rel = related(p)
    body = f"""
<section class="sec"><div class="wrap">
<p style="margin-bottom:18px"><a href="../categories/{p['category']}.html">&larr; {esc(CATS[p['category']]['label'])}</a> &nbsp;/&nbsp; {esc(p['brand'])}</p>
<div class="detail-hero">
  <div>{gallery}</div>
  <div class="detail-info">
    <p class="kicker">{esc(p['brand'])} &middot; {esc(CATS[p['category']]['label'])}</p>
    <h1>{esc(p['name'])}</h1>
    <p class="tagline">{esc(p['tagline'])}</p>
    {price_html(p)}
    <div class="detail-actions">
      <a class="btn btn-wa btn-lg" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
      <button class="btn btn-dark" type="button" data-compare="{esc(p['slug'])}">Add to Compare</button>
    </div>
    <div class="spec-box"><h3>Full specifications &amp; today&rsquo;s price</h3>
    <p>Full specifications and today&rsquo;s price are confirmed on WhatsApp for this exact model — message the shop and they will confirm personally before you buy.</p></div>
  </div>
</div></div></section>
{product_video(p)}
<section class="sec grey"><div class="wrap">
{section_head('About this product', esc(p['name']), '')}
<div class="prose"><p>{esc(p['description'])}</p>
<p>Available at the shop in Liaqat Bazar, Quetta — walk in, or order on WhatsApp. The shop confirms price, availability and delivery personally.</p></div>
</div></section>
<section class="sec"><div class="wrap">
{section_head('Related Products', 'More from ' + CATS[p['category']]['label'], '')}
<div class="grid">{''.join(card(x, depth="../") for x in rel)}</div>
</div></section>
<div class="wrap">{cta_band('../')}</div>
<div class="lightbox" id="lightbox"><img src="" alt=""></div>
"""
    write(f"products/{p['slug']}.html", chrome("../", f"{p['name']} — AK Khan Enterprises, Quetta",
        f"{p['name']} ({p['brand']}) at AK Khan Enterprises, Quetta. {p['tagline']} Price and availability confirmed on WhatsApp.", body))

# ----- explore -----
def build_explore():
    vids = []
    for v in videos:
        if not v.get("verified"):
            continue
        prod = next((p for p in products if v["video_id"] in p.get("video_ids", [])), None)
        vids.append((v, prod))
    cards = "".join(video_embed(v["video_id"], v["title_or_null"] or "DJI film") +
                    (f'<p style="font-size:.85rem;color:#bbb;padding:0 16px 14px">Film for <a style="color:#fff;text-decoration:underline" href="products/{prod["slug"]}.html">{esc(prod["name"])}</a></p>' if prod else "")
                    for v, prod in vids)
    # rebuild as proper video-cards with link inside body: simpler — use video_embed then append link paragraph inside card div is invalid nesting; instead build custom:
    cards = ""
    for v, prod in vids:
        link = (f'<p>Film for <a href="products/{prod["slug"]}.html" style="color:#fff;text-decoration:underline">{esc(prod["name"])}</a></p>' if prod else "")
        cards += (f'<div class="video-card"><iframe src="https://www.youtube-nocookie.com/embed/{v["video_id"]}" '
                  f'title="{esc(v["title_or_null"] or "DJI film")}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen loading="lazy"></iframe>'
                  f'<div class="v-body"><h3>{esc(v["title_or_null"] or "DJI film")}</h3><p>Official DJI film on YouTube.</p>{link}</div></div>')
    stories = [
        ("shot-canyon.jpg", "Canyons from above", "Steep walls, long shadows — the kind of frame a folding DJI Mini makes possible on a walk, not a film set."),
        ("shot-desert.jpg", "Desert light", "Open ground and low sun. The Air and Mavic range is built for wide, clean aerial frames like this."),
        ("shot-ski.jpg", "Following the action", "Fast subjects, smooth tracking — Avata and the Mini range follow the moment instead of missing it."),
        ("shot-surf.jpg", "Over the water", "Coastlines and surf from above — aerial photography that turns a familiar beach into something new."),
        ("field-agri.jpg", "Working from the sky", "Agras aircraft work the fields — spraying and surveying across acres from the air."),
        ("field-enterprise.jpg", "Enterprise in the field", "Matrice platforms for inspection and enterprise work — the professional end of the drone range."),
    ]
    tiles = "".join(
        f'<div class="cat-tile reveal" style="background-image:url(\'{hero_uri(img)}\');min-height:300px"><div><h3>{t}</h3><p>{d}</p></div></div>'
        for img, t, d in stories)
    body = f"""
{hero_section(hero_uri('mavic3-cine.jpg'), 'Explore', 'Stories from the sky', 'Drone photography, enterprise work and the official films behind the aircraft on our shelves.')}
<section class="sec"><div class="wrap">
{section_head('Photography Stories', 'Explore & Discover', 'Editorial themes from the DJI range — what these drones are made for.')}
<div class="cat-tiles">{tiles}</div>
</div></section>
<section class="sec dark"><div class="wrap">
{section_head('The Films', '11 verified DJI films', 'Every film below is an official DJI film on YouTube, verified as publicly playable.')}
<div class="video-grid">{cards}</div>
</div></section>
<div class="wrap">{cta_band('')}</div>
"""
    write("explore.html", chrome("", "Explore — Stories & Films — AK Khan Enterprises",
        "Explore AK Khan Enterprises: drone photography stories and 11 verified official DJI films.", body))

# ----- static info pages -----
FAQS = [
    ("Where is AK Khan Enterprises?", f"{ADDRESS}, Pakistan. Walk in during shop hours, or message us on WhatsApp ({WA_DISPLAY}) before you come."),
    ("Why are there no prices on the website?", "Prices change with stock and the market. The shop confirms today's exact price personally on WhatsApp so you never rely on an old listed price."),
    ("How do I order?", "Open any product and press WhatsApp Inquiry. The message opens ready to send; the shop confirms availability, final price, delivery and payment with you directly."),
    ("Do you deliver outside Quetta?", "Ask on WhatsApp with your city and the product — the shop will confirm what delivery is possible for that item."),
    ("Can I see a product before buying?", "Yes. Visit the shop, or ask on WhatsApp for photos of the exact unit in stock."),
    ("Which brands do you stock?", "DJI, Dahua, Hikvision, Tiandy, EZVIZ, IMOU, V380 Pro, Ruijie, TP-Link, Tenda, Ubiquiti, Audionic, Samsung, LG, Sony and iCSee."),
]

def simple_page(fname, title, desc, kicker, h1, inner):
    body = f"""<section class="sec"><div class="wrap"><div class="prose">
<p class="kicker">{esc(kicker)}</p><h1 style="margin:8px 0 20px">{esc(h1)}</h1>
{inner}</div></div></section><div class="wrap">{cta_band('')}</div>"""
    write(fname, chrome("", title, desc, body))

def build_info():
    brands = sorted(set(p["brand"] for p in products))
    simple_page("about.html", "About Us — AK Khan Enterprises, Quetta",
        "About AK Khan Enterprises, Quetta — drones, cameras, networking, sound and displays since 2015.",
        "About Us", "AK Khan Enterprises",
        f"""<p><strong>{esc(TAGLINE)}</strong></p>
<p>AK Khan Enterprises is an electronics and security shop in Quetta, trusted since 2015. The shop stocks DJI drones, security cameras and recorders, networking equipment, Audionic sound systems and LED TVs — five ranges, under one roof, at {esc(ADDRESS)}.</p>
<p>Customers can walk into the shop to see a product before buying, or order on WhatsApp — the shop confirms today's price, availability and complete details personally for every product.</p>
<h3>What the shop stocks</h3>
<p>Drones ({len([p for p in products if p['category']=='drones'])} products), Cameras ({len([p for p in products if p['category']=='cctv'])} products), Displays ({len([p for p in products if p['category']=='displays'])} products), Networking ({len([p for p in products if p['category']=='networking'])} products) and Sound ({len([p for p in products if p['category']=='audio'])} products).</p>
<h3>Brands</h3><p>{esc(', '.join(brands))}.</p>
<h3>Visit or message</h3><p>{esc(ADDRESS)}<br>WhatsApp: {WA_DISPLAY}<br>Email: {EMAIL}</p>""")
    simple_page("support.html", "Customer Support — AK Khan Enterprises",
        "Customer support at AK Khan Enterprises, Quetta — how to order on WhatsApp, visit the shop, and get help.",
        "Support", "Customer Support",
        f"""<p>Need help choosing a product, or checking a price? The fastest way is WhatsApp — {WA_DISPLAY}. The shop confirms price, availability and complete details personally.</p>
<h3>How ordering works</h3><p>1. Find the product on this website.<br>2. Press WhatsApp Inquiry — your message opens ready to send.<br>3. The shop confirms availability, final price, delivery and payment with you directly. Nothing is charged or confirmed automatically on this website.</p>
<h3>Visit the shop</h3><p>{esc(ADDRESS)} — walk in to see a product before you buy, or ask on WhatsApp for photos of the exact unit in stock.</p>
<h3>Delivery</h3><p>Ask on WhatsApp with your city and the product — the shop will confirm what delivery is possible for that item.</p>
<p><a class="btn btn-dark" href="faq.html">Read the FAQ</a> &nbsp; <a class="btn btn-wa" href="{wa_link()}" target="_blank" rel="noopener">Chat on WhatsApp</a></p>""")
    faq_items = "".join(
        f'<details class="faq-item"><summary>{esc(q)}</summary><div class="fa">{esc(a)}</div></details>'
        for q, a in FAQS)
    simple_page("faq.html", "FAQ — AK Khan Enterprises",
        "Frequently asked questions — AK Khan Enterprises, Quetta: address, prices, ordering on WhatsApp, delivery.",
        "FAQ", "Frequently Asked Questions",
        f"""<p>Straight answers to the questions customers ask most.</p>{faq_items}""")
    simple_page("contact.html", "Contact — AK Khan Enterprises, Quetta",
        "Contact AK Khan Enterprises, Quetta — WhatsApp, email, shop address and social media.",
        "Contact", "Contact Us",
        f"""<div class="contact-grid">
<div class="contact-card"><h3>WhatsApp</h3><p><a href="{wa_link()}" target="_blank" rel="noopener">{WA_DISPLAY}</a></p><p>The fastest way to ask about any product, price or availability.</p></div>
<div class="contact-card"><h3>Email</h3><p><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div class="contact-card"><h3>Visit the shop</h3><p>{esc(ADDRESS)}</p></div>
<div class="contact-card"><h3>Social media</h3><p><a href="{IG1}" target="_blank" rel="noopener">Instagram @ak_khan682</a><br><a href="{IG2}" target="_blank" rel="noopener">Instagram @akkhan.enterprises</a><br><a href="{FB_URL}" target="_blank" rel="noopener">Facebook</a></p></div>
</div>""")
    simple_page("privacy.html", "Privacy Policy — AK Khan Enterprises",
        "Privacy policy — AK Khan Enterprises. This website has no online checkout and collects no payment details.",
        "Legal", "Privacy Policy",
        """<p>This website is a product catalogue for AK Khan Enterprises, Quetta. It has no online checkout, no accounts and no payment system.</p>
<p>When you press a WhatsApp button, your message opens in WhatsApp and is sent by you, to the shop's WhatsApp number, under WhatsApp's own privacy policy. This website does not collect, store or share your messages.</p>
<p>Product videos on this website are embedded from YouTube (youtube-nocookie.com); YouTube may set cookies under its own policy when you play a video.</p>
<p>Questions about this policy: message the shop on WhatsApp or email akkhanenterprises682@gmail.com.</p>""")
    simple_page("terms.html", "Terms — AK Khan Enterprises",
        "Terms — AK Khan Enterprises. Orders are taken on WhatsApp only; prices and availability are confirmed by the shop.",
        "Legal", "Terms",
        """<p>Products shown on this website are listed by AK Khan Enterprises, Quetta. There is no online checkout and no order is placed through this website.</p>
<p>Orders and purchases are made on WhatsApp or in the shop. Prices shown on this website, where shown, are the prices supplied by the shop; the shop confirms today's exact price and availability personally on WhatsApp before any sale. Products without a listed price are priced on request.</p>
<p>Product descriptions on this website come from the shop's own listings. Full specifications for any exact model are confirmed by the shop on WhatsApp before you buy.</p>
<p>Delivery, where available, is agreed with the shop on WhatsApp for each item.</p>""")

# ----- search & compare -----
def build_search():
    data = []
    for p in products:
        data.append({"slug": p["slug"], "name": p["name"], "brand": p["brand"],
                     "cat": CATS[p["category"]]["label"], "catKey": p["category"],
                     "tag": p["tagline"], "price": price_text(p),
                     "thumb": img_uri(p["photo_thumb"]) if p.get("photo_thumb") else ""})
    js = "window.AK_PRODUCTS=" + json.dumps(data, ensure_ascii=False) + ";"
    write("assets/search-data.js", js)
    head = section_head('Search', 'Search all 108 products', 'Search by product name, brand or category.')
    body = """
<section class="sec"><div class="wrap">
""" + head + """
<div class="search-box"><input type="search" id="searchInput" placeholder="Try &lsquo;Mini 4 Pro&rsquo;, &lsquo;Dahua&rsquo; or &lsquo;NVR&rsquo;&hellip;" aria-label="Search products"><button class="btn btn-dark" type="button" id="searchBtn">Search</button></div>
<p style="text-align:center;color:var(--mut)" id="searchCount"></p>
<div class="grid" id="searchResults"></div>
</div></section>
<script src="assets/search-data.js"></script>
<script>
var input=document.getElementById('searchInput'),res=document.getElementById('searchResults'),cnt=document.getElementById('searchCount');
function waMsg(n){return 'https://wa.me/__WA_NUM__?text='+encodeURIComponent('Assalam-o-Alaikum! I am interested in '+n+'. Please share its current price, availability and complete details.');}
function run(){
  var q=input.value.trim().toLowerCase();
  var list=window.AK_PRODUCTS.filter(function(p){return !q||p.name.toLowerCase().indexOf(q)>-1||p.brand.toLowerCase().indexOf(q)>-1||p.cat.toLowerCase().indexOf(q)>-1||p.tag.toLowerCase().indexOf(q)>-1;});
  cnt.textContent=list.length+' product'+(list.length===1?'':'s')+(q?' for \u201c'+input.value.trim()+'\u201d':'');
  res.innerHTML=list.map(function(p){
    var img=p.thumb?'<img src="'+p.thumb+'" alt="'+p.name+'" loading="lazy">':'<div class="no-photo">Photo coming soon</div>';
    return '<article class="card"><a class="card-img" href="products/'+p.slug+'.html">'+img+'</a><div class="card-body"><p class="card-cat">'+p.brand+' &middot; '+p.cat+'</p><h3><a href="products/'+p.slug+'.html">'+p.name+'</a></h3><p class="card-tag">'+p.tag+'</p><p class="price">'+(p.price==='Price on request'?'<span class="price por">Price on request</span>':p.price)+'</p><div class="card-actions"><a class="btn btn-dark" href="products/'+p.slug+'.html">View Details</a><a class="btn btn-wa" href="'+waMsg(p.name)+'" target="_blank" rel="noopener">WhatsApp Inquiry</a></div></div></article>';
  }).join('')||'<p>No products match that search. Try a brand name such as Dahua, DJI or Audionic.</p>';
}
input.addEventListener('input',run);document.getElementById('searchBtn').addEventListener('click',run);run();
</script>
""".replace("__WA_NUM__", WA_NUM)
    write("search.html", chrome("", "Search — AK Khan Enterprises",
        "Search all 108 products at AK Khan Enterprises, Quetta — by name, brand or category.", body))

def build_compare():
    opts = "".join(f'<option value="{esc(p["slug"])}">{esc(p["name"])} ({esc(p["brand"])})</option>' for p in products)
    head = section_head('Compare', 'Compare up to 3 products', 'Pick products below, or add them from any product page with \u201cAdd to Compare\u201d. Only real information is compared \u2014 name, brand, category, price and description.')
    body = """
<section class="sec"><div class="wrap">
""" + head + """
<div class="compare-picks">
  <select id="pick1"><option value="">Choose product 1</option>{opts}</select>
  <select id="pick2"><option value="">Choose product 2</option>{opts}</select>
  <select id="pick3"><option value="">Choose product 3</option>{opts}</select>
</div>
<div id="compareOut"><p style="color:var(--mut)">Choose at least one product to compare.</p></div>
</div></section>
<script src="assets/search-data.js"></script>
<script>
var picks=[document.getElementById('pick1'),document.getElementById('pick2'),document.getElementById('pick3')];
var out=document.getElementById('compareOut');
function render(){
  var slugs=picks.map(function(s){return s.value;}).filter(Boolean);
  if(!slugs.length){out.innerHTML='<p style="color:var(--mut)">Choose at least one product to compare.</p>';return;}
  var items=slugs.map(function(s){return window.AK_PRODUCTS.find(function(p){return p.slug===s;});}).filter(Boolean);
  var rows=[['Product',function(p){return '<a href="products/'+p.slug+'.html"><strong>'+p.name+'</strong></a>';}],
    ['Photo',function(p){return p.thumb?'<img src="'+p.thumb+'" alt="'+p.name+'">':'Photo coming soon';}],
    ['Brand',function(p){return p.brand;}],['Category',function(p){return p.cat;}],
    ['Price',function(p){return p.price;}],['About',function(p){return p.tag;}],
    ['Enquire',function(p){return '<a class="btn btn-wa" href="https://wa.me/__WA_NUM__?text='+encodeURIComponent('Assalam-o-Alaikum! I am interested in '+p.name+'. Please share its current price, availability and complete details.')+'" target="_blank" rel="noopener">WhatsApp Inquiry</a>';}]];
  out.innerHTML='<div style="overflow-x:auto"><table class="compare-table"><tr><th></th>'+items.map(function(){return '<th></th>';}).join('')+'</tr>'+
    rows.map(function(r){return '<tr><th>'+r[0]+'</th>'+items.map(function(p){return '<td>'+r[1](p)+'</td>';}).join('')+'</tr>';}).join('')+'</table></div>';
  try{localStorage.setItem('akCompare',JSON.stringify(slugs));}catch(e){}
}
picks.forEach(function(s){s.addEventListener('change',render);});
try{var saved=JSON.parse(localStorage.getItem('akCompare')||'[]');saved.slice(0,3).forEach(function(s,i){if(picks[i])picks[i].value=s;});}catch(e){}
render();
</script>
""".replace("{opts}", opts).replace("__WA_NUM__", WA_NUM)
    write("compare.html", chrome("", "Compare Products — AK Khan Enterprises",
        "Compare up to 3 products at AK Khan Enterprises — name, brand, category, price and description, all real.", body))

# ---------- main ----------
def main():
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    write("assets/style.css", CSS)
    write("assets/site.js", JS)
    shutil.copy(STAGING / "logo-mark.svg", SITE / "assets" / "logo-mark.svg")
    build_index()
    for c in CAT_ORDER:
        build_category(c)
    for p in products:
        build_product(p)
    build_explore()
    build_info()
    build_search()
    build_compare()
    # README
    write("README.md", """# AK Khan Enterprises — website (static build)

Generated by `tools/generate.py` from verified staging data
(`~/workspace/ak-khan-github-site-staging/`). Re-run the generator to rebuild.

- 108 product pages, 5 category pages, homepage, explore, about, support,
  FAQ, contact, privacy, terms, search, compare.
- WhatsApp-only ordering (wa.me/923067000682). No cart, checkout or admin.
- Images are embedded as base64 data URIs (GitHub snapshot pushes are
  text-only); the logo SVG is a real file at assets/logo-mark.svg.
- Only 28 products have a real PKR price; the other 80 show
  "Price on request — confirmed on WhatsApp".
- No specs table anywhere (the data contains no technical specs).
- Product 89 (Dahua 4K IR ePoE Mini Dome) has no photo — its page says so
  honestly instead of borrowing another product's photo.
- Only the 11 verified DJI YouTube films are embedded. The DJI Mini 3
  film (48_kEK9iFKU) is private and is never embedded.
- No Laptops / Photography / Accessories category pages: the data has no
  such products, so those pages would be empty. No "New Arrivals" or
  "Best Sellers" labels: the data has no dates or sales figures.
""")
    print("generated.")

if __name__ == "__main__":
    main()
