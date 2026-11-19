#!/usr/bin/env python3
"""AK Khan Enterprises — static site generator (BLACK + WHITE DJI-style rebuild).

Reads verified data from ~/workspace/ak-khan-github-site-redesign/staging/
and generates the complete static site into this folder (site root = parent
of tools/). No invented specs, prices, warranties, reviews or availability
anywhere. Images are embedded as base64 data URIs (GitHub snapshot pushes
are text-only); the two black/white logo SVGs stay real files.
Run: python3 tools/generate.py (byte-reproducible: run twice -> zero diff)
"""
import base64, html, io, json, os, re, shutil, urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
STAGING = Path.home() / "workspace" / "ak-khan-github-site-redesign" / "staging"

WA_NUM = "923067000682"
WA_DISPLAY = "0306-7000682"
EMAIL = "akkhanenterprises682@gmail.com"
ADDRESS = "Faiz Muhammad Street, Liaqat Bazar, Quetta"
TAGLINE = "Your One-Stop ELECTRONICS & SECURITY SOLUTION IN QUETTA"
FB_URL = "https://www.facebook.com/61595712927205"
IG1 = "https://www.instagram.com/ak_khan682"
IG2 = "https://www.instagram.com/akkhan.enterprises"
YT_URL = "https://www.youtube.com/@AkKhanEnterprises"

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
    """Hero image as data URI (max 1200px wide = source resolution, q70)."""
    p = STAGING / "images" / "hero" / name
    im = Image.open(p).convert("RGB")
    if im.width > 1200:
        im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70, optimize=True)
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
        # explicit space before "was" (never "Rs 275,000was ...")
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

# DJI-style tile: pale-grey panel, text centred at the TOP only, photo fills
# most of the tile below. One quiet text link per card — no repeated buttons.
# Photo is the FULL image (sharper than the 400px thumb at tile size),
# never upscaled beyond its real resolution by the generator.
def card(p, depth="", buy=False):
    if p.get("photo_full"):
        thumb = (f'<img src="{img_uri(p["photo_full"])}" alt="{esc(p["name"])}" loading="lazy">')
    else:
        thumb = ('<div class="no-photo"><span>Photo on request</span>'
                 '<small>Ask on WhatsApp and the shop will send a photo of the exact unit in stock.</small></div>')
    if buy:
        cta = (f'<div class="card-cta"><a class="btn btn-dark" href="{wa_link(p["name"])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>'
               f'<a class="more-link" href="{depth}{product_url(p)}">Learn more &rsaquo;</a></div>')
    else:
        cta = f'<a class="more-link" href="{depth}{product_url(p)}">Learn more &rsaquo;</a>'
    return f"""<article class="card" data-brand="{esc(p["brand"])}" data-name="{esc(p["name"].lower())}" data-price="{p["price_pkr"] or ''}">
  <div class="card-body">
    <p class="card-cat">{esc(p["brand"])} &middot; {esc(CATS[p["category"]]["label"])}</p>
    <h3><a href="{depth}{product_url(p)}">{esc(p["name"])}</a></h3>
    <p class="card-tag">{esc(p["tagline"])}</p>
    {price_html(p)}
    {cta}
  </div>
  <a class="card-img" href="{depth}{product_url(p)}" aria-label="{esc(p["name"])}">{thumb}</a>
</article>"""

# ---------- chrome ----------
# Inline-SVG line icons (replace the old ✓/✎/✆/⚑ text glyphs).
ICON_CHECK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
    '<path d="M8 12.5l2.6 2.6L16 9.5"/></svg>')
ICON_GUIDE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
    '<path d="M9.5 9.5l5 2-2 5-5-2z"/></svg>')
ICON_CHAT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z"/>'
    '<path d="M8.5 11h.01M12 11h.01M15.5 11h.01"/></svg>')
ICON_PIN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11z"/>'
    '<circle cx="12" cy="10" r="2.6"/></svg>')
ICON_WA = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5.1-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.6-6.1c-.3-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1-.2.3-.6.8-.8 1-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4 0-.5.1-.7l.4-.5c.1-.2.1-.3 0-.5l-.8-1.9c-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.3-.2.3-.9.9-.9 2.2s.9 2.5 1.1 2.7c.1.2 1.9 2.9 4.5 4 .6.3 1.1.4 1.5.6.6.2 1.2.2 1.6.1.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.2-.2-.5-.3z"/></svg>')
ICON_FB = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-7h2.4l.4-3h-2.8V9.1c0-.9.3-1.5 1.6-1.5h1.3V4.9c-.3 0-1.2-.1-2.2-.1-2.2 0-3.7 1.3-3.7 3.8V11H8v3h2.5v7h3z"/></svg>')
ICON_IG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1.2" fill="currentColor" stroke="none"/></svg>')
ICON_YT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10.5 9.5l4.5 2.5-4.5 2.5z" fill="currentColor" stroke="none"/></svg>')
DRONE_SVG = ('<svg viewBox="0 0 60 40" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><ellipse cx="30" cy="20" rx="7" ry="5"/><path d="M30 20L10 7M30 20L50 7M30 20L10 33M30 20L50 33"/><circle cx="10" cy="7" r="3.5"/><circle cx="50" cy="7" r="3.5"/><circle cx="10" cy="33" r="3.5"/><circle cx="50" cy="33" r="3.5"/></svg>')
COLS_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="4" y="4" width="7" height="16" rx="1"/><rect x="13" y="4" width="7" height="16" rx="1"/></svg>')
BAG_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M5 8h14l-1.2 12H6.2L5 8z"/><path d="M8.5 10V6.5a3.5 3.5 0 0 1 7 0V10"/></svg>')

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
<link rel="icon" href="{depth}assets/logo-mark-black.svg" type="image/svg+xml">
{extra_head}
</head>
<body>
<header class="site-header" id="siteHeader">
  <div class="header-inner">
    <a class="brand" href="{depth}index.html"><img src="{depth}assets/logo-mark-white.svg" alt="AK Khan Enterprises" class="logo logo-w"><img src="{depth}assets/logo-mark-black.svg" alt="AK Khan Enterprises" class="logo logo-b"><span class="brand-text"><strong>AK KHAN</strong><em>ENTERPRISES</em></span></a>
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
      <img src="{depth}assets/logo-mark-white.svg" alt="AK Khan Enterprises" class="logo">
      <p><strong>AK KHAN ENTERPRISES</strong></p>
      <p>{esc(TAGLINE)}</p>
      <p>Trusted since 2015.</p>
      <p class="foot-social">
        <a href="{FB_URL}" target="_blank" rel="noopener" aria-label="Facebook">{ICON_FB}</a>
        <a href="{IG1}" target="_blank" rel="noopener" aria-label="Instagram @ak_khan682">{ICON_IG}</a>
        <a href="{IG2}" target="_blank" rel="noopener" aria-label="Instagram @akkhan.enterprises">{ICON_IG}</a>
        <a href="{YT_URL}" target="_blank" rel="noopener" aria-label="YouTube">{ICON_YT}</a>
      </p>
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
    </div>
  </div>
  <div class="footer-bottom">
    <p>&copy; 2026 AK Khan Enterprises, Quetta. All rights reserved.</p>
    <p><a href="{depth}privacy.html">Privacy Policy</a> &middot; <a href="{depth}terms.html">Terms</a></p>
    <p class="foot-note">Orders are taken on WhatsApp only. There is no online checkout on this website.</p>
  </div>
</footer>
<a class="wa-float" href="{wa_link()}" target="_blank" rel="noopener" aria-label="Chat on WhatsApp">{ICON_WA}<span>WhatsApp</span></a>
<script src="{depth}assets/site.js"></script>
</body>
</html>
"""

def hero_section(img, kicker, title, sub, cta=""):
    # kicker is trusted internal copy and is inserted as-is so the real
    # "·" character renders (never an escaped entity like &MIDDOT;).
    return f"""<section class="hero" style="background-image:url('{img}')">
  <div class="hero-overlay"></div>
  <div class="hero-content reveal">
    <p class="kicker">{kicker}</p>
    <h1>{esc(title)}</h1>
    <p class="hero-sub">{esc(sub)}</p>
    {cta}
  </div>
  <a class="scroll-hint" href="#main-content" aria-label="Scroll down">&darr;</a>
</section>
<div id="main-content"></div>"""

def hero_carousel(slides):
    """DJI-style rotating-stills hero. slides: list of dicts
    (img, kicker, title, sub, cta_href, cta_label). Still photos only."""
    parts = []
    for i, s in enumerate(slides):
        act = " active" if i == 0 else ""
        parts.append(f"""<div class="hero-slide{act}" data-name="{esc(s['title'])}" style="background-image:url('{s['img']}')">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <p class="kicker">{s['kicker']}</p>
    <h1>{esc(s['title'])}</h1>
    <p class="hero-sub">{esc(s['sub'])}</p>
    <div class="hero-cta"><a class="btn btn-outline btn-lg" href="{esc(s['cta_href'])}">Learn More &rsaquo;</a><a class="btn btn-light btn-lg" href="{esc(s['wa'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a></div>
  </div>
</div>""")
    return f"""<section class="hero hero-carousel" id="heroCarousel">
{''.join(parts)}
  <div class="hero-list" role="tablist" aria-label="Hero slides">
    <button type="button" data-go="0"></button>
    <button type="button" class="current" data-go="0"></button>
    <button type="button" data-go="0"></button>
  </div>
  <a class="scroll-hint" href="#featured" aria-label="Scroll down">&darr;</a>
</section>
<div id="main-content"></div>"""

def section_head(kicker, title, sub=""):
    s = f'<p class="sec-sub">{esc(sub)}</p>' if sub else ""
    return f'<div class="sec-head reveal"><p class="kicker">{esc(kicker)}</p><h2>{esc(title)}</h2>{s}</div>'

def cta_band(depth):
    return f"""<section class="cta-band reveal" id="cta">
  <div class="wrap">
  <h2>Found something you like?</h2>
  <p>Message the shop on WhatsApp — today&rsquo;s price, availability and complete details, confirmed personally.</p>
  <a class="btn btn-light btn-lg" href="{wa_link()}" target="_blank" rel="noopener">Chat on WhatsApp &mdash; {WA_DISPLAY}</a>
  <p class="cta-addr">{esc(ADDRESS)} &middot; {EMAIL}</p>
  </div>
</section>"""

# ---------- CSS (black / white / grey only — DJI restraint) ----------
CSS = """
:root{--black:#000;--ink:#111;--grey:#f2f3f5;--grey2:#eef0f2;--line:#e5e5e5;--mut:#767676;--txt:#111}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--txt);background:#fff;line-height:1.6;overflow-x:hidden}
img{max-width:100%;height:auto;display:block}
a{color:inherit;text-decoration:none}
h1,h2,h3{line-height:1.15;font-weight:800;letter-spacing:-.02em}
h1{font-size:clamp(2.25rem,5.5vw,3.5rem)}
h2{font-size:clamp(1.9rem,4vw,2.75rem)}
.kicker{color:var(--mut);text-transform:uppercase;letter-spacing:.22em;font-size:.78rem;font-weight:700}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px}
.sec{padding:72px 0}
.sec.dark{background:var(--black);color:#fff}
.sec.grey{background:var(--grey)}
.sec-head{max-width:760px;margin:0 auto 44px;text-align:center}
.sec-head h2{margin:10px 0 12px}
.sec-sub{color:var(--mut);font-size:1.05rem}
.dark .sec-sub{color:#bdbdbd}
.dark .kicker{color:#9a9a9a}
/* header — transparent over the hero, solid white on scroll (JS toggles .solid) */
.site-header{position:fixed;top:0;left:0;right:0;z-index:100;background:transparent;color:#fff;transition:background .3s,color .3s,box-shadow .3s}
.site-header.solid{background:#fff;color:var(--ink);box-shadow:0 1px 0 rgba(0,0,0,.08)}
.header-inner{max-width:1280px;margin:0 auto;padding:0 20px 0 33px;height:64px;display:flex;align-items:center;gap:24px}
.brand{display:flex;align-items:center;gap:10px}
.logo{width:44px;height:36px}
.site-header .logo{height:26px;width:auto}
.foot-brand .logo{width:44px;height:36px}
.logo-b{display:none}
.site-header.solid .logo-b{display:block}
.site-header.solid .logo-w{display:none}
.brand-text{display:flex;flex-direction:column;line-height:1.05}
.brand-text strong{font-size:1.05rem;letter-spacing:.08em;color:#fff}
.brand-text em{font-style:normal;font-size:.62rem;letter-spacing:.34em;color:#cfcfcf}
.site-header.solid .brand-text strong{color:var(--ink)}
.site-header.solid .brand-text em{color:var(--mut)}
.main-nav{margin-left:auto;display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.nav-link{color:#fff;padding:10px 12px;font-size:.95rem;border:0;background:none;cursor:pointer;font-family:inherit}
.nav-link:hover{color:#bbb}
.site-header.solid .nav-link{color:var(--ink)}
.site-header.solid .nav-link:hover{color:var(--mut)}
.nav-wa{color:#000!important;background:#fff;border-radius:999px;font-weight:700;padding:9px 16px}
.nav-wa:hover{color:#000!important;opacity:.85}
.site-header.solid .nav-wa{background:#000;color:#fff!important}
.site-header.solid .nav-wa:hover{color:#fff!important;opacity:.85}
.menu-btn{display:none;background:none;border:0;color:#fff;font-size:1.7rem;cursor:pointer;margin-left:auto}
.site-header.solid .menu-btn{color:var(--ink)}
.nav-item{position:relative}
.mega-menu{position:absolute;left:50%;transform:translate(-50%,8px);top:100%;background:#fff;color:var(--txt);display:none;gap:0;width:min(860px,94vw);border-radius:0;box-shadow:0 24px 60px rgba(0,0,0,.25);padding:22px;grid-template-columns:repeat(5,1fr)}
.nav-item:hover .mega-menu,.nav-item:focus-within .mega-menu{display:grid}
.mega-col{padding:0 12px;border-left:1px solid var(--line)}
.mega-col:first-child{border-left:0}
.mega-cat{font-weight:800;font-size:1rem;color:var(--ink)}
.mega-col p{font-size:.82rem;color:var(--mut);margin:6px 0 10px}
.mega-prod{display:block;font-size:.86rem;padding:5px 0;border-top:1px solid var(--grey2);color:var(--txt)}
.mega-prod:hover{color:var(--mut)}
.mega-all{display:block;margin-top:10px;font-size:.85rem;font-weight:700;color:var(--ink)}
body.no-hero main{padding-top:64px}
/* hero — DJI ratio 2.34:1 at desktop (1919x820). aspect-ratio lives ONLY in
   the desktop media query: at mobile widths the 520px min-height would
   otherwise force width = 520 x 2.34 = 1217px and overflow the viewport. */
.hero{position:relative;min-height:520px;background-size:cover;background-position:center;display:flex;align-items:center;justify-content:center;color:#fff;text-align:center}
@media(min-width:1101px){.hero{aspect-ratio:2.34/1;min-height:0}}
.hero-overlay{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45),rgba(0,0,0,.35) 45%,rgba(0,0,0,.65))}
.hero-content{position:relative;max-width:1100px;margin:0 auto;padding:130px 20px 90px;width:100%}
.hero-content .kicker{color:#d6d6d6}
.hero-content h1{max-width:22ch;margin:14px auto 0}
.hero-sub{max-width:56ch;margin:18px auto 30px;font-size:clamp(1.05rem,2vw,1.25rem);font-weight:600;color:#eee}
.hero-cta{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}
.hero-cta .btn{min-width:200px}
.scroll-hint{position:absolute;bottom:22px;left:50%;transform:translateX(-50%);color:#fff;font-size:1.4rem;opacity:.8}
/* buttons — white pill on black, black pill on white; no colour anywhere */
.btn{display:inline-block;padding:12px 22px;border-radius:999px;font-weight:700;font-size:.95rem;text-align:center;border:1px solid transparent;cursor:pointer}
.btn-dark{background:var(--black);color:#fff}
.btn-light{background:#fff;color:#111}
.btn-outline{border-color:#fff;color:#fff;background:transparent}
.btn-outline:hover{background:rgba(255,255,255,.12)}
.btn-lg{padding:15px 30px;font-size:1.05rem}
/* DJI tiles: 2 large per row, 16px gutters, no borders/shadows/radius.
   Full-bleed variant breaks out of the 1280px .wrap (16px side margins).
   Tile aspect 1.38:1 (928x~672 at 1919px) applies at desktop widths only;
   below 1100px cards size naturally so the text never squeezes the photo. */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.grid-fullbleed{margin:0 16px;display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
@media(min-width:1101px){.grid-fullbleed .card{aspect-ratio:1.38/1}}
.card{background:#ebebeb;display:flex;flex-direction:column;overflow:hidden}
.card-body{padding:30px 24px 8px;text-align:center;display:flex;flex-direction:column;gap:8px;align-items:center}
.card-cat{font-size:.78rem;text-transform:uppercase;letter-spacing:.16em;color:var(--mut);font-weight:700}
.card-body h3{font-size:1.35rem}
.card-body h3 a:hover{color:var(--mut)}
.card-tag{color:var(--mut);font-size:.95rem;max-width:44ch}
.price{font-size:1.3rem;font-weight:800}
.price .was{font-size:.95rem;color:var(--mut);text-decoration:line-through;font-weight:400;margin-left:6px}
.price.por{font-size:1.1rem}
.price-note{font-size:.85rem;color:var(--mut)}
.more-link{display:inline-block;font-size:1rem;font-weight:600;color:var(--ink);padding:6px 0 2px}
.more-link:hover{color:var(--mut)}
.card-img{display:block;background:#ebebeb;aspect-ratio:4/3;overflow:hidden;padding:18px 22px 26px;flex:1;min-height:0}
.card-img img{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 18px 16px rgba(0,0,0,.18));transition:transform .4s}
.card:hover .card-img img{transform:scale(1.04)}
.no-photo{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;background:var(--grey);color:var(--mut);text-align:center;padding:24px}
.no-photo span{font-size:1.05rem;font-weight:700;color:#555}
.no-photo small{font-size:.88rem;max-width:34ch}
/* Innovation tiles (DJI): 2 per row inside the centred container, ~591x615.
   3rd tile spans both columns as a wide horizontal feature — no orphan gap. */
.innov-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.feature-tile{background:#000;color:#fff;display:flex;flex-direction:column;overflow:hidden;min-height:615px}
.feature-tile.light{background:#ebebeb;color:var(--txt)}
.feature-tile .f-img{height:320px;flex:none;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
.feature-tile.light .f-img{background:#ebebeb}
.feature-tile .f-img img{width:100%;height:100%;object-fit:contain}
.feature-tile .f-body{padding:28px 32px 32px;display:flex;flex-direction:column;justify-content:center;gap:10px;align-items:flex-start;flex:1}
.feature-tile.wide{grid-column:1/-1;flex-direction:row;min-height:380px}
.feature-tile.wide .f-img{flex:1;height:auto;min-height:380px}
.feature-tile.wide .f-body{flex:1;padding:48px}
.feature-tile .f-body p{color:#cfcfcf}
.feature-tile.light .f-body p{color:var(--mut)}
.feature-tile .f-body h2{font-size:clamp(1.7rem,3.4vw,2.4rem)}
.feature-tile .f-body .kicker{color:#9a9a9a}
.feature-tile.light .f-body .kicker{color:var(--mut)}
.feature-tile .f-cta{display:flex;gap:22px;align-items:center;flex-wrap:wrap;margin-top:8px}
/* Fields tiles (DJI): 3 per row inside the container, ~390x440, full-bleed
   photo, white title top-centre + subtitle + Learn More link. */
.field-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.field-tile{position:relative;overflow:hidden;min-height:440px;display:flex;color:#fff;background-size:cover;background-position:center}
.field-tile::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.62),rgba(0,0,0,0) 55%)}
.field-tile div{position:relative;z-index:1;padding:28px 22px;width:100%;text-align:center}
.field-tile h3{font-size:1.4rem}
.field-tile p{font-size:.95rem;color:#eee}
.field-tile .more-link{color:#fff;margin-top:8px}
/* Where to Buy / Support strip (DJI): 3 columns on very pale grey, thin
   grey line icons ~55x65, bold headings ~28px, Learn More links. */
.why-strip{background:#f7f7f7}
.why-strip-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:48px}
.why-col{text-align:center;padding:8px}
.why-col .ic{width:55px;height:65px;color:#555;margin:0 auto 16px}
.why-col .ic svg{width:100%;height:100%}
.why-col h3{font-size:1.75rem;margin-bottom:10px}
.why-col p{color:#555;font-size:.98rem}
.why-col .more-link{margin-top:12px}
/* hero carousel (DJI): rotating stills, ~4.5s autoplay, crossfade,
   bottom-left prev / current (bold + white bar) / next slide list. */
.hero-carousel{display:block;overflow:hidden;text-align:center}
.hero-slide{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transition:opacity 1s ease;display:flex;align-items:center;justify-content:center}
.hero-slide.active{opacity:1;z-index:1}
.hero-slide .hero-content{padding:110px 20px 90px}
.hero-list{position:absolute;left:48px;bottom:28px;z-index:5;display:flex;flex-direction:column;gap:8px;text-align:left}
.hero-list button{background:none;border:0;cursor:pointer;color:rgba(255,255,255,.65);font-size:.95rem;font-family:inherit;padding:2px 0 2px 16px;position:relative;text-align:left}
.hero-list button.current{color:#fff;font-weight:700}
.hero-list button.current::before{content:"";position:absolute;left:0;top:3px;bottom:3px;width:3px;background:#fff}
.hero-list button:hover{color:#fff}
.hero-carousel .scroll-hint{z-index:5}
/* films carousel (DJI "Shot on"): centre card ~1230px, side cards peeking,
   ‹ › arrows at mid-height on the centre card's edges. */
.films-sec{overflow:hidden}
.films-carousel{position:relative;margin-top:8px}
.films-track{display:flex;gap:16px;transition:transform .6s ease;will-change:transform}
.films-track .video-card{flex:0 0 min(1230px,88vw)}
.films-arrow{position:absolute;top:38%;z-index:5;background:none;color:#fff;border:0;width:64px;height:64px;font-size:3rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;text-shadow:0 2px 12px rgba(0,0,0,.65)}
.films-arrow:hover{opacity:.75}
.films-arrow.prev{left:calc(50% - 668px)}
.films-arrow.next{right:calc(50% - 668px)}
/* category listing head (DJI): H1 + grey subtitle centred on white,
   then a full-width banner photo (~513px visible). */
.cat-head{padding:56px 20px 40px;text-align:center}
.cat-head h1{font-size:clamp(2.5rem,5vw,3.75rem);margin:10px 0 12px}
.cat-head .cat-sub{color:var(--mut);font-size:1.2rem;max-width:56ch;margin:0 auto}
.cat-banner{height:513px;background-size:cover;background-position:center}
/* support hero banner (DJI): shorter, ~493px, centred title + subtitle + search */
.support-hero{position:relative;height:493px;background-size:cover;background-position:center;display:flex;align-items:center;justify-content:center;text-align:center;color:#fff}
.support-hero .support-inner{position:relative;z-index:1;padding:90px 20px 40px;max-width:760px;width:100%}
.support-hero h1{font-size:clamp(2rem,4vw,3rem)}
.support-hero p{font-size:1.15rem;color:#eee;margin-top:10px}
.support-search{display:flex;max-width:590px;margin:26px auto 0;background:#fff;border-radius:999px;padding:4px}
.support-search input{flex:1;border:0;outline:none;padding:12px 18px;font-size:1rem;font-family:inherit;border-radius:999px;min-width:0}
.support-search button{border:0;background:#000;color:#fff;border-radius:999px;padding:12px 26px;font-weight:700;font-size:.95rem;cursor:pointer;font-family:inherit}
/* homepage product tiles sit directly under the hero (DJI: no section head) */
.tiles-sec{padding:16px 0 0}
/* category tiles — 2 per row; first tile spans full width so 5 tiles fill the grid */
.cat-tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.cat-tile{position:relative;overflow:hidden;min-height:340px;display:flex;align-items:flex-end;color:#fff;background-size:cover;background-position:center}
.cat-tile.wide{grid-column:1/-1;min-height:420px}
.cat-tile::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 35%,rgba(0,0,0,.82))}
.cat-tile div{position:relative;z-index:1;padding:26px}
.cat-tile h3{font-size:1.5rem}
.cat-tile p{font-size:.95rem;color:#ddd}
.cat-tile .kicker{color:#d6d6d6}
/* video — sharp maxresdefault thumbnail facade; click loads the real player */
.video-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.video-card.wide{grid-column:1/-1}
.video-card{background:#111;overflow:hidden;color:#fff}
.video-thumb{position:relative;display:block;width:100%;aspect-ratio:16/9;padding:0;border:0;background:#000;cursor:pointer}
.video-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.video-thumb .play{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:68px;height:68px;border-radius:50%;background:rgba(255,255,255,.94);display:flex;align-items:center;justify-content:center}
.video-thumb .play svg{width:26px;height:26px;fill:#000;margin-left:3px}
.video-card iframe{width:100%;aspect-ratio:16/9;border:0;display:block}
.video-card .v-body{padding:16px 18px}
.video-card .v-body p{font-size:.9rem;color:#bbb}
.video-card .v-body a{color:#fff;text-decoration:underline}
.video-card h3{font-size:1.05rem}
/* why */
.why-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.why{background:var(--grey);padding:32px}
.why h3{font-size:1.15rem;margin-bottom:8px}
.why p{color:var(--mut);font-size:.95rem}
.why .ic{width:34px;height:34px;color:var(--ink);margin-bottom:14px}
.why .ic svg{width:100%;height:100%}
/* toolbar */
.toolbar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:0 0 26px}
.toolbar select,.toolbar input[type=search]{padding:11px 14px;border:1px solid var(--line);border-radius:999px;font-size:.95rem;font-family:inherit;background:#fff}
.toolbar .count{margin-left:auto;color:var(--mut);font-size:.92rem}
/* product subnav — second sticky black bar (DJI-style) */
.subnav{position:sticky;top:64px;z-index:90;background:#000;color:#fff}
.subnav-inner{max-width:1280px;margin:0 auto;padding:0 20px;height:64px;display:flex;align-items:center;gap:22px}
.subnav-name{font-weight:800;font-size:1rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.subnav-links{display:flex;gap:22px;margin-left:auto}
.subnav-links a{font-size:.92rem;color:#cfcfcf}
.subnav-links a:hover{color:#fff}
.subnav .btn{padding:8px 16px;font-size:.88rem;margin-left:4px;flex:none}
/* product detail — black hero, one huge studio shot */
.detail-hero{background:#000;color:#fff;text-align:center;padding:64px 20px 0}
.detail-hero .kicker{color:#9a9a9a}
.detail-hero h1{margin:12px auto 0;max-width:22ch}
.detail-hero .tagline{font-size:clamp(1.05rem,2vw,1.25rem);font-weight:600;color:#d6d6d6;margin:14px auto 0;max-width:56ch}
.detail-hero .price{font-size:1.5rem;margin-top:18px}
.detail-hero .price .was{color:#9a9a9a}
.detail-hero .price-note{color:#9a9a9a}
.detail-actions{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin:24px 0 0}
.detail-actions .btn{min-width:200px}
.detail-hero .confirm-note{color:#9a9a9a;font-size:.92rem;margin-top:16px}
.detail-photo-wrap{background:radial-gradient(ellipse 60% 55% at 50% 82%,rgba(255,255,255,.13),transparent 70%);padding:20px 0 0;cursor:zoom-in}
.detail-photo-wrap img{margin:0 auto;max-height:64vh;width:auto;max-width:100%;object-fit:contain;filter:drop-shadow(0 24px 28px rgba(0,0,0,.55))}
.detail-photo-wrap .zoom-hint{color:#767676;font-size:.85rem;padding:14px 0 26px}
/* lightbox */
.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.94);display:none;align-items:center;justify-content:center;z-index:200;cursor:zoom-out}
.lightbox.open{display:flex}
.lightbox img{max-width:94vw;max-height:90vh;object-fit:contain}
.lightbox.zoomed img{transform:scale(1.8);cursor:zoom-out}
/* faq */
.faq-item{border:1px solid var(--line);margin-bottom:12px;background:#fff}
.faq-item summary{padding:18px 20px;font-weight:700;cursor:pointer;list-style:none}
.faq-item summary::-webkit-details-marker{display:none}
.faq-item .fa{padding:0 20px 18px;color:var(--mut)}
/* forms / misc */
.prose{max-width:760px;margin:0 auto}
.prose p{margin-bottom:14px;color:#333}
.prose h3{margin:26px 0 8px}
.contact-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.contact-card{border:1px solid var(--line);padding:26px}
.contact-card h3{margin-bottom:8px}
.cta-band{background:var(--black);color:#fff;text-align:center;padding:64px 0}
.cta-band h2{margin-bottom:10px}
.cta-band p{color:#d5d5d5;margin-bottom:22px}
.cta-addr{font-size:.9rem;margin-top:18px;color:#9a9a9a!important}
.search-box{display:flex;gap:10px;max-width:640px;margin:0 auto 30px}
.search-box input{flex:1;padding:14px 18px;border:1px solid var(--line);border-radius:999px;font-size:1rem}
.compare-table{width:100%;border-collapse:collapse;overflow-x:auto}
.compare-table th,.compare-table td{border:1px solid var(--line);padding:12px;text-align:left;vertical-align:top}
.compare-table th{background:var(--grey)}
.compare-table img{max-width:140px}
.compare-picks{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}
.compare-picks select{flex:1 1 200px;min-width:0;max-width:100%;padding:11px 14px;border:1px solid var(--line);border-radius:999px;font-size:.95rem}
.reveal{opacity:0;transform:translateY(18px);transition:opacity .6s,transform .6s}
.reveal.visible{opacity:1;transform:none}
#featured,#categories,#films,#why,#stories,#cta,#listing,#related-cats,#overview,#film,#about,#related,#innovation,#fields{scroll-margin-top:130px}
/* footer — compact, tidy, no tall empty dark block */
.site-footer{background:var(--black);color:#ddd;margin-top:0}
.footer-inner{max-width:1280px;margin:0 auto;padding:44px 20px 28px;display:grid;grid-template-columns:2fr 1fr 1fr 1.4fr;gap:32px}
.footer-inner h4{color:#fff;margin-bottom:12px}
.footer-inner a{display:block;padding:3px 0;color:#bbb}
.footer-inner a:hover{color:#fff}
.foot-brand p{margin-top:8px;font-size:.92rem;color:#bbb}
.footer-bottom{border-top:1px solid #262626;text-align:center;padding:20px;font-size:.88rem;color:#999}
.footer-bottom a{color:#ccc}
.foot-note{margin-top:6px}
.wa-float{position:fixed;right:18px;bottom:18px;z-index:150;background:#000;color:#fff;font-weight:700;padding:13px 20px;border-radius:999px;box-shadow:0 10px 26px rgba(0,0,0,.35);display:flex;align-items:center;gap:8px}
.wa-float svg{width:20px;height:20px}
.wa-float:hover{transform:scale(1.04)}
/* responsive */
@media(max-width:900px){
  .innov-grid{grid-template-columns:1fr}
  .feature-tile.wide{flex-direction:column}
  .feature-tile.wide .f-img{min-height:300px}
  .feature-tile{min-height:0}
  .feature-tile .f-img{height:300px}
  .field-grid{grid-template-columns:1fr}
  .why-strip-grid{grid-template-columns:1fr;gap:36px}
  .films-arrow.prev{left:12px}
  .films-arrow.next{right:12px}
  .cat-banner{height:260px}
  .support-hero{height:420px}
  .footer-inner{grid-template-columns:1fr 1fr}
  .mega-menu{display:none!important}
}
@media(max-width:720px){
  .menu-btn{display:block}
  .main-nav{display:none;position:absolute;top:100%;left:0;right:0;background:#000;flex-direction:column;align-items:stretch;padding:10px 20px 20px}
  .site-header.solid .main-nav{background:#fff}
  .main-nav.open{display:flex}
  .nav-link{padding:13px 4px;border-top:1px solid #222;font-size:1.02rem}
  .site-header.solid .nav-link{border-top-color:var(--line)}
  .nav-wa{text-align:center;margin-top:10px}
  .sec{padding:48px 0}
  .footer-inner{grid-template-columns:1fr}
  .hero{min-height:520px}
  .hero-list{left:20px;bottom:20px}
  .grid,.grid-fullbleed,.video-grid,.why-grid,.cat-tiles,.contact-grid{grid-template-columns:1fr}
  .cat-tile.wide{grid-column:auto;min-height:340px}
  .hero-cta .btn,.detail-actions .btn{min-width:0;width:100%}
  .subnav-links{display:none}
  .feature-tile .f-body{padding:28px 24px}
  .feature-tile.wide .f-body{padding:28px 24px}
  .card-img{padding:12px 16px 20px}
}
/* fix-pass additions: category-card WhatsApp pill row, footer social icons,
   drones series strip, support pill row, grey pill. */
.card-cta{display:flex;gap:14px;align-items:center;justify-content:center;margin-top:14px;flex-wrap:wrap}
.card-cta .btn{padding:10px 20px;font-size:.92rem}
.foot-social{display:flex;gap:16px;margin-top:16px}
.foot-social a{color:#fff;opacity:.85}
.foot-social a:hover{opacity:1}
.foot-social svg{width:22px;height:22px;display:block}
.series-strip{background:#f2f3f5;padding:30px 0}
.series-strip-inner{max-width:1280px;margin:0 auto;display:flex;justify-content:center;gap:4px;flex-wrap:wrap}
.series-item{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 18px;color:#222;font-size:.9rem}
.series-item svg{width:48px;height:32px}
.series-item:hover{color:#000}
.pill-row{display:flex;gap:10px;flex-wrap:wrap}
.pill-row .btn{padding:9px 18px}
.btn-grey{background:#f2f3f5;color:#111}
"""

# ---------- JS ----------
JS = """
// header: transparent over the hero, solid white on scroll; solid from the
// start on pages without a hero.
var header=document.getElementById('siteHeader');
function headerState(){
  if(!header)return;
  if(!document.querySelector('.hero')){header.classList.add('solid');document.body.classList.add('no-hero');return;}
  header.classList.toggle('solid',window.scrollY>10);
}
window.addEventListener('scroll',headerState,{passive:true});
headerState();
// mobile menu
var btn=document.getElementById('menuBtn'),nav=document.getElementById('mainNav');
if(btn&&nav){btn.addEventListener('click',function(){var o=nav.classList.toggle('open');btn.setAttribute('aria-expanded',o?'true':'false');});}
// scroll reveal
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target);}});},{threshold:.12});
document.querySelectorAll('.reveal').forEach(function(el){io.observe(el);});
// video facade: sharp maxresdefault thumbnail; click loads the real player.
document.querySelectorAll('.video-thumb').forEach(function(t){
  t.addEventListener('click',function(){
    var vid=t.dataset.vid,title=t.dataset.title||'Video';
    var f=document.createElement('iframe');
    f.src='https://www.youtube-nocookie.com/embed/'+vid+'?autoplay=1';
    f.title=title;f.allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';f.allowFullscreen=true;
    t.replaceWith(f);
  });
});
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
// hero carousel: rotating stills, ~4.5s autoplay, crossfade, bottom-left
// prev / current / next slide list; click a list name to jump; pause on hover.
var hc=document.getElementById('heroCarousel');
if(hc){
  var hSlides=Array.prototype.slice.call(hc.querySelectorAll('.hero-slide'));
  var hList=hc.querySelectorAll('.hero-list button');
  var hIdx=0,hTimer=null;
  function hGo(i){
    hIdx=(i+hSlides.length)%hSlides.length;
    hSlides.forEach(function(s,j){s.classList.toggle('active',j===hIdx);});
    var prev=(hIdx-1+hSlides.length)%hSlides.length,next=(hIdx+1)%hSlides.length;
    if(hList.length===3){
      hList[0].textContent=hSlides[prev].dataset.name;hList[0].dataset.go=prev;
      hList[1].textContent=hSlides[hIdx].dataset.name;hList[1].dataset.go=hIdx;
      hList[2].textContent=hSlides[next].dataset.name;hList[2].dataset.go=next;
    }
  }
  function hStart(){hStop();hTimer=setInterval(function(){hGo(hIdx+1);},4500);}
  function hStop(){if(hTimer){clearInterval(hTimer);hTimer=null;}}
  hList.forEach(function(b){b.addEventListener('click',function(){hGo(parseInt(b.dataset.go,10));hStart();});});
  hc.addEventListener('mouseenter',hStop);
  hc.addEventListener('mouseleave',hStart);
  document.addEventListener('visibilitychange',function(){if(document.hidden){hStop();}else{hStart();}});
  hGo(0);hStart();
}
// films carousel: centre card ~1230px, side cards peeking, ‹ › arrows.
var fc=document.getElementById('filmsCarousel');
if(fc){
  var fTrack=fc.querySelector('.films-track');
  var fCards=Array.prototype.slice.call(fTrack.querySelectorAll('.video-card'));
  var fIdx=0;
  function fLayout(){
    var cardW=fCards[0].getBoundingClientRect().width+16;
    var wrapW=fc.getBoundingClientRect().width;
    var off=(wrapW-fCards[0].getBoundingClientRect().width)/2-fIdx*cardW;
    fTrack.style.transform='translateX('+off+'px)';
  }
  function fGo(i){fIdx=(i+fCards.length)%fCards.length;fLayout();}
  fc.querySelector('.films-arrow.prev').addEventListener('click',function(){fGo(fIdx-1);});
  fc.querySelector('.films-arrow.next').addEventListener('click',function(){fGo(fIdx+1);});
  window.addEventListener('resize',fLayout);
  fLayout();
}
// compare: add from product pages
document.querySelectorAll('[data-compare]').forEach(function(b){
  b.addEventListener('click',function(){
    var slug=b.dataset.compare, list=[];
    try{list=JSON.parse(localStorage.getItem('akCompare')||'[]');}catch(e){list=[];}
    if(list.indexOf(slug)===-1){if(list.length>=3){alert('Compare holds up to 3 products. Remove one on the Compare page first.');return;}list.push(slug);localStorage.setItem('akCompare',JSON.stringify(list));}
    b.textContent='Added to compare';
  });
});
"""


# ---------- page builders ----------
def write(rel, content):
    p = SITE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p

PLAY_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>')

def video_card(vid, title, extra="", wide=False):
    # Sharp maxresdefault thumbnail (falls back to hqdefault if absent);
    # the iframe only loads after a click, so the poster is never blurry.
    wide_cls = " wide" if wide else ""
    return (f'<div class="video-card{wide_cls}"><button class="video-thumb" type="button" data-vid="{vid}" '
            f'data-title="{esc(title)}" aria-label="Play {esc(title)}">'
            f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" alt="{esc(title)}" loading="lazy" '
            f'onerror="if(!this.dataset.fb){{this.dataset.fb=1;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\';}}else{{this.style.display=\'none\';}}">'
            f'<span class="play">{PLAY_SVG}</span></button>'
            f'<div class="v-body"><h3>{esc(title)}</h3>'
            f'<p>Official DJI film on YouTube.</p>{extra}</div></div>')

def video_embed(vid, title):
    return video_card(vid, title)

def product_video(p):
    if not p.get("video_ids"):
        return ""
    vids = [v for v in p["video_ids"] if v != FAILED_VIDEO and v in VID_TITLE]
    if not vids:
        return ""
    cards = "".join(video_embed(v, VID_TITLE[v]) if len(vids) > 1 else video_card(v, VID_TITLE[v], wide=True) for v in vids)
    return f'<section class="sec dark" id="film"><div class="wrap">{section_head("Watch", "Product film", "The official film for this product.")}<div class="video-grid">{cards}</div></div></section>'

# ----- homepage (DJI order) -----
# (a) hero carousel; (b) product tiles, full-bleed 2x2; (c) "Shot on" films
# carousel; (d) Innovation — 3 editorial features as 2-per-row tiles inside
# the container (3rd spans both columns, no orphan gap); (e) Fields — "From
# the air" stories, 3 per row inside the container; (f) Where to Buy /
# Support strip, 3 columns on very pale grey; (g) CTA band; (h) footer.
# NO "Shop by Category" section (DJI's homepage has none; categories stay
# reachable via nav, mega-menu, footer and search).
def build_index():
    featured_ids = [0, 2, 4, 51, 54, 70, 41]
    feats = [by_id(i) for i in featured_ids]
    f1, f2, f3 = feats[0], feats[1], feats[2]
    def feature_tile(p, light=False, wide=False):
        cls = "feature-tile light" if light else "feature-tile"
        if wide: cls += " wide"
        view_cls = "btn-light" if not light else "btn-dark"
        return f"""<div class="{cls} reveal">
  <div class="f-img"><img src="{img_uri(p['photo_full'])}" alt="{esc(p['name'])}" loading="lazy"></div>
  <div class="f-body"><p class="kicker">{esc(p['brand'])} &middot; {esc(CATS[p['category']]['label'])}</p>
  <h2>{esc(p['name'])}</h2><p>{esc(p['tagline'])}</p>
  {price_html(p)}
  <div class="f-cta"><a class="btn {view_cls}" href="products/{p['slug']}.html">View Details</a>
  <a class="more-link" style="color:inherit" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry &rsaquo;</a></div></div></div>"""
    # (a) hero carousel — 6 strongest existing real hero photos, each with
    # its REAL product/category name + tagline (nothing invented).
    slides = [
        {"img": hero_uri('air3s.jpg'), "kicker": "AK Khan Enterprises \u00b7 Quetta",
         "title": "DJI Air 3S", "sub": "The latest Air-series drone for serious creators.",
         "cta_href": "products/dji-air-3s.html", "wa": wa_link("DJI Air 3S")},
        {"img": hero_uri('mavic3-cine.jpg'), "kicker": "AK Khan Enterprises \u00b7 Quetta",
         "title": "DJI Mavic 3 Pro", "sub": "Triple-camera Mavic flagship for professional work.",
         "cta_href": "products/dji-mavic-3-pro.html", "wa": wa_link("DJI Mavic 3 Pro")},
        {"img": hero_uri('drone.jpg'), "kicker": "AK Khan Enterprises \u00b7 Quetta",
         "title": "DJI Mini 3 Pro", "sub": "Mini 3 Pro Fly More Combo — pro features, Mini size.",
         "cta_href": "products/dji-mini-3-pro.html", "wa": wa_link("DJI Mini 3 Pro")},
        {"img": hero_uri('cctv-hi.jpg'), "kicker": "AK Khan Enterprises \u00b7 Quetta",
         "title": "Security Cameras", "sub": "CCTV cameras, NVRs and video servers.",
         "cta_href": "categories/cctv.html", "wa": wa_link()},
        {"img": hero_uri('shot-canyon.jpg'), "kicker": "AK Khan Enterprises \u00b7 Quetta",
         "title": "From the Air", "sub": "Aerial perspectives from the DJI range — the drone photography our customers create with these aircraft.",
         "cta_href": "explore.html", "wa": wa_link()},
    ]
    vid_items = [(v, VID_TITLE[v]) for v in
                 ["nbXneZzFh8w", "4fhl9F8DZDU", "r5kukRMmZNI", "RNhmV4yCP6M"]]
    vids = "".join(video_embed(v, t) for v, t in vid_items)
    body = f"""
{hero_carousel(slides)}
<section class="tiles-sec" id="featured">
<div class="grid-fullbleed">{''.join(card(p) for p in feats[3:])}</div>
</section>
<section class="sec dark films-sec" id="films"><div class="wrap">
{section_head('Cinematic Brand Story', 'Shot from the sky', 'Official DJI films for the drones on our shelves.')}
</div>
<div class="films-carousel" id="filmsCarousel">
<div class="films-track">{vids}</div>
<button class="films-arrow prev" type="button" aria-label="Previous film">&lsaquo;</button>
<button class="films-arrow next" type="button" aria-label="Next film">&rsaquo;</button>
</div>
<p style="text-align:center;margin-top:26px"><a class="btn btn-light" href="explore.html">Watch all 11 films on Explore</a></p>
</section>
<section class="sec" id="innovation"><div class="wrap">
{section_head('Innovation', 'Standing at the forefront of innovation', 'The flagship aircraft on our shelves — the range, up close.')}
<div class="innov-grid">
{feature_tile(f1)}
{feature_tile(f2, light=True)}
{feature_tile(f3, wide=True)}
</div>
</div></section>
<section class="sec grey" id="fields"><div class="wrap">
{section_head('Explore DJI Products in Different Fields', 'From the air', 'Aerial perspectives from the DJI range — the drone photography our customers create with these aircraft.')}
<div class="field-grid">
<a class="field-tile reveal" style="background-image:url('{hero_uri('shot-canyon.jpg')}')" href="explore.html"><div><h3>Canyons from above</h3><p>Aerial photography with DJI drones.</p><span class="more-link">Learn More &rsaquo;</span></div></a>
<a class="field-tile reveal" style="background-image:url('{hero_uri('shot-desert.jpg')}')" href="explore.html"><div><h3>Desert light</h3><p>Wide open frames, golden hour.</p><span class="more-link">Learn More &rsaquo;</span></div></a>
<a class="field-tile reveal" style="background-image:url('{hero_uri('field-agri.jpg')}')" href="explore.html"><div><h3>Working from the sky</h3><p>Enterprise and agriculture aircraft.</p><span class="more-link">Learn More &rsaquo;</span></div></a>
</div>
</div></section>
<section class="sec why-strip" id="why"><div class="wrap">
<div class="why-strip-grid">
<div class="why-col reveal"><p class="ic">{ICON_PIN}</p><h3>Where to Buy</h3><p>Visit us at {esc(ADDRESS)} — see the product before you buy, or ask on WhatsApp for a photo of the exact unit in stock.</p><a class="more-link" href="contact.html">Learn More &rsaquo;</a></div>
<div class="why-col reveal"><p class="ic">{ICON_CHAT}</p><h3>Support</h3><p>Price, availability and complete details confirmed personally on WhatsApp — {WA_DISPLAY}. Talk to the shop before you buy — which model fits your home, shop or site, and what it will do for you.</p><a class="more-link" href="support.html">Learn More &rsaquo;</a></div>
<div class="why-col reveal"><p class="ic">{ICON_CHECK}</p><h3>Genuine Products</h3><p>Products from the brands on our shelves — DJI, Dahua, Hikvision, Tiandy, EZVIZ, IMOU, Ruijie, TP-Link, Audionic, Samsung, LG and Sony.</p><a class="more-link" href="about.html">Learn More &rsaquo;</a></div>
</div></div></section>
{cta_band('')}
"""
    write("index.html", chrome("", "AK Khan Enterprises — Drones, Cameras, Networking, Sound & Displays in Quetta",
        "AK Khan Enterprises, Quetta — DJI drones, Dahua & Hikvision cameras, networking, Audionic sound and LED TVs. Order on WhatsApp.", body))

# ----- category pages -----
def build_category(c):
    items = [p for p in products if p["category"] == c]
    brands = sorted(set(p["brand"] for p in items))
    opts = "".join(f'<option value="{esc(b)}">{esc(b)}</option>' for b in brands)
    others = "".join(
        f'<a class="cat-tile" style="background-image:url(\'{hero_uri(CATS[o]["hero"])}\');min-height:300px" href="{o}.html">'
        f'<div><h3>{CATS[o]["nav"]}</h3><p>{esc(CATS[o]["blurb"])}</p></div></a>'
        for o in CAT_ORDER if o != c)
    # DJI Camera Drones grey series strip (~140px): only the drones listing
    # has series. Each series links to a real search for that DJI series;
    # Compare and Shop Now are real too. No quiz (no quiz content exists),
    # no Accessories/RC/Inspire (no such products in the catalogue).
    strip = ""
    if c == "drones":
        series = ["Mavic", "Air", "Mini", "Neo", "Avata", "Matrice", "Agras"]
        strip_items = "".join(
            f'<a class="series-item" href="../search.html?q={urllib.parse.quote("DJI " + s)}">{DRONE_SVG}<span>DJI {s}</span></a>'
            for s in series)
        strip_items += ('<a class="series-item" href="../compare.html">' + COLS_SVG + '<span>Compare</span></a>'
                  '<a class="series-item" href="' + wa_link() + '" target="_blank" rel="noopener">' + BAG_SVG + '<span>Shop Now</span></a>')
        strip = f'<div class="series-strip"><div class="series-strip-inner">{strip_items}</div></div>'
    body = f"""
{strip}<section class="cat-head"><div class="wrap">
<p class="kicker">AK Khan Enterprises</p>
<h1>{CATS[c]['label']}</h1>
<p class="cat-sub">{esc(CATS[c]['intro'])}</p>
</div></section>
<div class="cat-banner" style="background-image:url('{hero_uri(CATS[c]['hero'])}')" role="img" aria-label="{esc(CATS[c]['label'])}"></div>
<section class="sec" id="listing"><div class="wrap">
{section_head(CATS[c]['label'], f"All {CATS[c]['label']} — {len(items)} products", 'Filter by brand or sort the list. Prices shown where the shop has confirmed one; everything else is confirmed on WhatsApp.')}
<div class="toolbar">
  <label>Brand <select id="brandFilter"><option value="">All brands</option>{opts}</select></label>
  <label>Sort <select id="sortSel"><option value="name-asc">Name A–Z</option><option value="name-desc">Name Z–A</option><option value="price-asc">Price: low to high</option><option value="price-desc">Price: high to low</option></select></label>
  <span class="count" id="resultCount">{len(items)} products</span>
</div>
</div>
<div class="grid-fullbleed" id="catGrid">{''.join(card(p, depth="../", buy=True) for p in items)}</div>
</section>
<section class="sec grey" id="related-cats"><div class="wrap">
{section_head('Keep exploring', 'Related categories', '')}
<div class="cat-tiles">{others}</div>
</div></section>
{cta_band('../')}
"""
    write(f"categories/{c}.html", chrome("../", f"{CATS[c]['label']} — AK Khan Enterprises, Quetta",
        f"{CATS[c]['label']} at AK Khan Enterprises, Quetta. {CATS[c]['intro']}", body))

# ----- product pages (DJI-style: black hero, huge shot, no invented specs) -----
def build_product(p):
    if p.get("photo_full"):
        gallery = f"""<div class="detail-photo-wrap" id="detailPhoto"><img src="{img_uri(p['photo_full'])}" alt="{esc(p['name'])} — product photo"><p class="zoom-hint">Tap the photo to view fullscreen. Tap again to zoom.</p></div>"""
    else:
        gallery = ('<div class="detail-photo-wrap" style="cursor:default"><div class="no-photo" style="background:transparent;min-height:40vh;color:#bbb">'
                   '<span style="color:#e0e0e0">Photo on request</span>'
                   '<small style="color:#9a9a9a">No photo of this exact unit is available yet. Ask on WhatsApp and the shop will send a photo of the exact unit in stock.</small></div></div>')
    rel = related(p)
    film_anchor = '<a href="#film">Film</a>' if p.get("video_ids") and any(v != FAILED_VIDEO and v in VID_TITLE for v in p["video_ids"]) else ""
    # DJI's product hero: solid Buy pill + outline Watch Video pill. The buy
    # action here is WhatsApp Inquiry (solid); products with a verified film
    # get the outline "Watch Film" pill instead of "Add to Compare" — the
    # compare action stays as a small link underneath, so nothing is lost.
    has_film = bool(film_anchor)
    if has_film:
        second_pill = '<a class="btn btn-outline btn-lg" href="#film">Watch Film &rsaquo;</a>'
        compare_link = f'<p style="margin-top:14px"><button class="more-link" type="button" data-compare="{esc(p["slug"])}" style="background:none;border:0;cursor:pointer;font:inherit;color:#ccc">+ Add to Compare</button></p>'
    else:
        second_pill = f'<button class="btn btn-outline btn-lg" type="button" data-compare="{esc(p["slug"])}">Add to Compare</button>'
        compare_link = ""
    body = f"""
<div class="subnav"><div class="subnav-inner">
<span class="subnav-name">{esc(p['name'])}</span>
<nav class="subnav-links" aria-label="Product sections"><a href="#overview">Overview</a>{film_anchor}<a href="#about">About</a><a href="#related">Related</a></nav>
<a class="btn btn-light" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
</div></div>
<section class="detail-hero" id="overview">
  <p class="kicker">{esc(p['brand'])} &middot; {esc(CATS[p['category']]['label'])}</p>
  <h1>{esc(p['name'])}</h1>
  <p class="tagline">{esc(p['tagline'])}</p>
  {price_html(p)}
  <div class="detail-actions">
    <a class="btn btn-light btn-lg" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
    {second_pill}
  </div>
  {compare_link}
  <p class="confirm-note">Full specifications and today&rsquo;s price are confirmed on WhatsApp for this exact model.</p>
  {gallery}
</section>
{product_video(p)}
<section class="sec" id="about"><div class="wrap">
{section_head('About this product', esc(p['name']), '')}
<div class="prose"><p>{esc(p['description'])}</p>
<p>Available at the shop in Liaqat Bazar, Quetta — walk in, or order on WhatsApp. The shop confirms price, availability and delivery personally.</p></div>
</div></section>
<section class="sec grey" id="related"><div class="wrap">
{section_head('Related Products', 'More from ' + CATS[p['category']]['label'], '')}
<div class="grid">{''.join(card(x, depth="../") for x in rel)}</div>
</div></section>
{cta_band('../')}
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
    cards = ""
    for i, (v, prod) in enumerate(vids):
        link = (f'<p>Film for <a href="products/{prod["slug"]}.html">{esc(prod["name"])}</a></p>' if prod else "")
        # 11 films: first card spans both columns so the grid fills exactly.
        cards += video_card(v["video_id"], v["title_or_null"] or "DJI film", link, wide=(i == 0))
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
<section class="sec" id="stories"><div class="wrap">
{section_head('Photography Stories', 'Explore & Discover', 'Editorial themes from the DJI range — what these drones are made for.')}
<div class="cat-tiles">{tiles}</div>
</div></section>
<section class="sec dark" id="films"><div class="wrap">
{section_head('The Films', '11 verified DJI films', 'Every film below is an official DJI film on YouTube, verified as publicly playable.')}
<div class="video-grid">{cards}</div>
</div></section>
{cta_band('')}
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
{inner}</div></div></section>{cta_band('')}"""
    write(fname, chrome("", title, desc, body))

# ----- support page (DJI): shorter hero banner ~493px, centred title +
# subtitle + search box that goes to search.html. All body copy is the
# shop's existing real copy. Banner photo is an existing real hero photo
# (field-enterprise.jpg — Matrice at work); no DJI support photo exists here.
def build_support():
    body = f"""
<section class="support-hero" style="background-image:url('{hero_uri('field-enterprise.jpg')}')">
  <div class="hero-overlay"></div>
  <div class="support-inner">
    <h1>Support</h1>
    <p>Welcome to AK Khan Enterprises Support</p>
    <form class="support-search" action="search.html" method="get" role="search">
      <input type="search" name="q" placeholder="Search products, brands or categories&hellip;" aria-label="Search products">
      <button type="submit">Search</button>
    </form>
  </div>
</section>
<section class="sec"><div class="wrap"><div class="prose">
<p class="kicker">Support</p><h1 style="margin:8px 0 20px">Customer Support</h1>
<p>Need help choosing a product, or checking a price? The fastest way is WhatsApp — {WA_DISPLAY}. The shop confirms price, availability and complete details personally.</p>
<h3 id="ordering">How ordering works</h3><p>1. Find the product on this website.<br>2. Press WhatsApp Inquiry — your message opens ready to send.<br>3. The shop confirms availability, final price, delivery and payment with you directly. Nothing is charged or confirmed automatically on this website.</p>
<h3>Visit the shop</h3><p>{esc(ADDRESS)} — walk in to see a product before you buy, or ask on WhatsApp for photos of the exact unit in stock.</p>
<h3 id="delivery">Delivery</h3><p>Ask on WhatsApp with your city and the product — the shop will confirm what delivery is possible for that item.</p>
<p><a class="btn btn-dark" href="faq.html">Read the FAQ</a> &nbsp; <a class="btn btn-light" style="border:1px solid #111" href="{wa_link()}" target="_blank" rel="noopener">Chat on WhatsApp</a></p>
</div></div></section>
<section class="sec grey"><div class="wrap">
{section_head('Helpful Guides', 'Guides that help', 'Straight answers and real links — nothing here is a placeholder.')}
<div class="contact-grid">
<div class="contact-card"><h3>How ordering works</h3><p>Find the product, press WhatsApp Inquiry, and the shop confirms everything with you directly.</p><p><a class="more-link" href="#ordering">Learn More &rsaquo;</a></p></div>
<div class="contact-card"><h3>Delivery</h3><p>Ask on WhatsApp with your city and the product — the shop confirms what delivery is possible.</p><p><a class="more-link" href="#delivery">Learn More &rsaquo;</a></p></div>
<div class="contact-card"><h3>Frequently Asked Questions</h3><p>Straight answers to the questions customers ask most.</p><p><a class="more-link" href="faq.html">Read the FAQ &rsaquo;</a></p></div>
<div class="contact-card"><h3>Contact the shop</h3><p>WhatsApp, email and the shop address — all in one place.</p><p><a class="more-link" href="contact.html">Contact Us &rsaquo;</a></p></div>
</div></div></section>
<section class="sec"><div class="wrap">
{section_head('Product Support', 'Find your product', 'Every product on this website, by range — pick one to open its page.')}
<div class="pill-row">
<a class="btn btn-dark" href="categories/drones.html">Drones</a>
<a class="btn btn-grey" href="categories/cctv.html">Cameras</a>
<a class="btn btn-grey" href="categories/displays.html">Displays</a>
<a class="btn btn-grey" href="categories/networking.html">Networking</a>
<a class="btn btn-grey" href="categories/audio.html">Sound</a>
<a class="btn btn-grey" href="search.html">Search all products &rsaquo;</a>
</div></div></section>
<section class="sec grey"><div class="wrap">
{section_head('Contact Us', 'Talk to the shop', 'The fastest way is WhatsApp — the shop answers personally.')}
<div class="contact-grid">
<div class="contact-card"><h3>WhatsApp</h3><p><a href="{wa_link()}" target="_blank" rel="noopener">{WA_DISPLAY}</a></p><p>The fastest way to ask about any product, price or availability.</p></div>
<div class="contact-card"><h3>Email</h3><p><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
<div class="contact-card"><h3>Visit the shop</h3><p>{esc(ADDRESS)}</p></div>
</div></div></section>{cta_band('')}"""
    write("support.html", chrome("", "Customer Support — AK Khan Enterprises",
        "Customer support at AK Khan Enterprises, Quetta — how to order on WhatsApp, visit the shop, and get help.", body))

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
    build_support()
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
                     # full image, not the 400px thumb: search tiles are
                     # the same 2-per-row size as category tiles.
                     "thumb": img_uri(p["photo_full"]) if p.get("photo_full") else ""})
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
function run(){
  var q=input.value.trim().toLowerCase();
  var list=window.AK_PRODUCTS.filter(function(p){return !q||p.name.toLowerCase().indexOf(q)>-1||p.brand.toLowerCase().indexOf(q)>-1||p.cat.toLowerCase().indexOf(q)>-1||p.tag.toLowerCase().indexOf(q)>-1;});
  cnt.textContent=list.length+' product'+(list.length===1?'':'s')+(q?' for \\u201c'+input.value.trim()+'\\u201d':'');
  res.innerHTML=list.map(function(p){
    var img=p.thumb?'<img src="'+p.thumb+'" alt="'+p.name+'" loading="lazy">':'<div class="no-photo"><span>Photo on request</span></div>';
    return '<article class="card"><div class="card-body"><p class="card-cat">'+p.brand+' &middot; '+p.cat+'</p><h3><a href="products/'+p.slug+'.html">'+p.name+'</a></h3><p class="card-tag">'+p.tag+'</p><p class="price">'+(p.price==='Price on request'?'<span class="price por">Price on request</span>':p.price)+'</p><a class="more-link" href="products/'+p.slug+'.html">Learn more &rsaquo;</a></div><a class="card-img" href="products/'+p.slug+'.html">'+img+'</a></article>';
  }).join('')||'<p>No products match that search. Try a brand name such as Dahua, DJI or Audionic.</p>';
}
input.addEventListener('input',run);document.getElementById('searchBtn').addEventListener('click',run);
try{var q=new URLSearchParams(location.search).get('q');if(q){input.value=q;}}catch(e){}
run();
</script>
"""
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
    ['Photo',function(p){return p.thumb?'<img src="'+p.thumb+'" alt="'+p.name+'">':'Photo on request';}],
    ['Brand',function(p){return p.brand;}],['Category',function(p){return p.cat;}],
    ['Price',function(p){return p.price;}],['About',function(p){return p.tag;}],
    ['Enquire',function(p){return '<a class="btn btn-dark" href="https://wa.me/__WA_NUM__?text='+encodeURIComponent('Assalam-o-Alaikum! I am interested in '+p.name+'. Please share its current price, availability and complete details.')+'" target="_blank" rel="noopener">WhatsApp Inquiry</a>';}]];
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
    # Black/white logos only: white monogram for dark header/footer,
    # black monogram for the light (scrolled) header and the favicon.
    # The old gold logo-mark.svg is NOT copied and is not referenced anywhere.
    shutil.copy(STAGING / "logo-mark-white.svg", SITE / "assets" / "logo-mark-white.svg")
    shutil.copy(STAGING / "logo-mark-black.svg", SITE / "assets" / "logo-mark-black.svg")
    old = SITE / "assets" / "logo-mark.svg"
    if old.exists():
        old.unlink()
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
    write("README.md", """# AK Khan Enterprises — website (static build, BLACK + WHITE DJI-style)

Generated by `tools/generate.py` from verified staging data
(`~/workspace/ak-khan-github-site-redesign/staging/`). Re-run the generator
to rebuild. Byte-reproducible: run twice, second run produces zero diff.

- 108 product pages, 5 category pages, homepage, explore, about, support,
  FAQ, contact, privacy, terms, search, compare.
- Black / white / grey only: no gold, navy, cream or green anywhere.
  WhatsApp CTAs are black or white pills, never green.
- Logos: assets/logo-mark-white.svg (dark header/footer) and
  assets/logo-mark-black.svg (light scrolled header, favicon). The old gold
  logo-mark.svg is gone. Wordmark "AK KHAN / ENTERPRISES" is styled HTML text.
- WhatsApp-only ordering (wa.me/923067000682). No cart, checkout or admin.
- Images are embedded as base64 data URIs (GitHub snapshot pushes are
  text-only); the logo SVGs are real files.
- Tiles are DJI-style: 2 large per row, pale-grey (#f2f3f5) panels, text
  centred at the top, one quiet "Learn more" link per card, photo fills
  the tile on grey with a soft drop shadow. Cards use the FULL product
  image (sharper than the 400px thumb at tile size), never upscaled
  beyond the source's real resolution.
- Only 28 products have a real PKR price; the other 80 show
  "Price on request — confirmed on WhatsApp".
- No specs table anywhere (the data contains no technical specs).
- Product 89 (Dahua 4K IR ePoE Mini Dome) has no photo — its page says so
  honestly instead of borrowing another product's photo.
- Only the 11 verified DJI YouTube films are embedded, via a sharp
  maxresdefault thumbnail facade (click loads the player). The DJI Mini 3
  film (48_kEK9iFKU) is private and is never embedded.
- No Laptops / Photography / Accessories category pages: the data has no
  such products, so those pages would be empty. No "New Arrivals" or
  "Best Sellers" labels: the data has no dates or sales figures.
""")
    print("generated.")

if __name__ == "__main__":
    main()
