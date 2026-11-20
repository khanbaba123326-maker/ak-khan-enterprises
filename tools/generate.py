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
    "drones":     {"label": "Drones",     "nav": "Drones",
                   "h1": "Camera Drones",
                   "intro": "Capture your moments from above with a mini drone, FPV, or professional aerial camera.",
                   "blurb": "Camera drones for creators, travellers and professionals."},
    "cctv":       {"label": "Cameras",    "nav": "Cameras",
                   "intro": "Security cameras, NVRs and video servers from Dahua, Hikvision, Tiandy, EZVIZ, IMOU, V380 Pro and iCSee — for homes, shops and full sites.",
                   "blurb": "CCTV cameras, NVRs and video servers."},
    "displays":   {"label": "Displays",   "nav": "Displays",
                   "intro": "LED TVs from Samsung, LG and Sony — from 43 inch to cinema-size 75 inch Bravia.",
                   "blurb": "LED TVs from Samsung, LG and Sony."},
    "networking": {"label": "Networking", "nav": "Networking",
                   "intro": "Routers, access points and switches from Ruijie, TP-Link, Tenda and Ubiquiti — home Wi-Fi to business networks.",
                   "blurb": "Routers, access points and switches."},
    "audio":      {"label": "Sound",      "nav": "Sound",
                   "intro": "Audionic sound — earbuds, Bluetooth speakers, soundbars, home theatre, party speakers and more.",
                   "blurb": "Audionic earbuds, speakers and sound systems."},
}
# NOTE: the old category banner images (cctv-hi.jpg, tv.jpg, networking.jpg,
# speaker.jpg) are deleted — no category except drones has a native-wide
# (≥1919×513) banner photo, so every other category uses DJI's text-led
# listing head (H1 + subtitle on white, no banner div) instead.
CAT_ORDER = ["drones", "cctv", "displays", "networking", "audio"]

# Audionic brand page: ONLY these 11 products (ids 30-40). Never rename
# them here — names are fixed by the shop's listing.
AUDIONIC_IDS = list(range(30, 41))

# ---------- ROUND 6 display order (boss order 19 Nov 22:57 — tarteeb) ----------
# Flagship / series first, newest -> oldest inside a series, brands
# grouped, never file order. products.json itself is NEVER reordered
# (id == array index, photo paths are id-based); order is applied at
# render time only, via order_category() in build_category /
# build_audionic and INNOVATION_IDS on the homepage. main() asserts
# every map covers exactly its category's ids — a missing or extra id
# fails the build loudly instead of silently mis-ordering.
# Drones: Mavic 3 Pro, Air 3S, Air 3, Mini 5 Pro, Mini 4 Pro, Mini 3 Pro,
# Mini 3, Mini 2, Mini 4K, Neo, Avata 2, Matrice 30T, Agras Series.
DRONE_ORDER = [4, 2, 3, 51, 0, 52, 1, 53, 7, 5, 6, 8, 9]
# CCTV: Dahua cameras (generics, DH-EPC, DH-HAC, DH-IPC, N-series
# ascending), Dahua recorders (DSS, IVSS, DHI-NVR ascending, NVR6A08
# trio in NUMERIC order 32/64/128, then N-series NVRs ascending),
# Hikvision, Tiandy (cameras then recorders), IMOU, EZVIZ, V380, iCSee.
CCTV_ORDER = [12, 13, 80, 54, 55, 56, 58, 82, 78, 77, 81, 79, 57, 76,
              84, 85, 83, 86, 87, 88, 89,
              99, 100, 90, 91, 66, 65, 64, 63, 92, 93, 103, 102, 101,
              107, 106, 105, 98, 95, 97, 104, 94, 96,
              10, 11, 59, 60, 14, 15, 68, 67, 69, 18, 74, 75, 16, 17,
              19, 61, 62]
# Networking: Ruijie (router, RG-EW300N, RG-EW300 PRO, AP), TP-Link
# (Archer, TL-WR840N, AP, switch), Tenda (router, N300, AP, switch),
# Ubiquiti (AP, switch).
NETWORKING_ORDER = [20, 70, 71, 21, 22, 72, 23, 24, 25, 73, 27, 26, 28, 29]
# Audio: Earbuds, Bluetooth Speaker, Multimedia Speaker, Vision 35 2.1,
# Mh-808 Plus Portable, Soundbar, Pace 8 Home Theater, Party Speaker,
# MEHFIL MH-1212 ADVANCE, Wireless Microphone, Amplifier.
AUDIO_ORDER = [30, 31, 36, 37, 38, 32, 33, 34, 40, 35, 39]
# Displays: Samsung 43/55/65, LG 43/55/65, Sony 43/55/65/75 — unchanged,
# already in order; listed explicitly so the map covers every category.
DISPLAYS_ORDER = [41, 42, 43, 44, 45, 46, 47, 48, 49, 50]
CAT_ORDER_MAP = {
    "drones": DRONE_ORDER,
    "cctv": CCTV_ORDER,
    "networking": NETWORKING_ORDER,
    "audio": AUDIO_ORDER,
    "displays": DISPLAYS_ORDER,
}
# Homepage Innovation tiles — flagship-first: Mavic 3 Pro (wide),
# Air 3S, Mini 4 Pro.
INNOVATION_IDS = [4, 2, 0]
def order_category(c, items):
    """Render-time display order for one category (ROUND 6)."""
    order = CAT_ORDER_MAP.get(c)
    if order is None:
        return items
    pos = {pid: i for i, pid in enumerate(order)}
    return sorted(items, key=lambda p: pos[p["id"]])

# Related-category tiles: the old banner images are deleted, so each tile
# uses a real, existing photo — the native-wide drones banner frame, or a
# >=800px product photo of that category (cover scale <= 1, never upscaled).
RELATED_TILE = {
    "drones": ("hero", "hero-drone.jpg"),
    "cctv": ("full", "p89.jpg"),
    "displays": ("full", "p41.jpg"),
    "networking": ("full", "p20.jpg"),
    "audio": ("full", "p32.jpg"),
}

# ---------- DJI copy (exact words from dji-copy-2026-11-19.md) ----------
# Hero eyebrow/tagline per DJI product page. Mini 4 Pro has NO eyebrow
# on DJI's page. Mini 3 Pro's page is retired — only its meta title /
# description are verified, so it gets no DJI hero copy here.
DJI_HERO = {
    "dji-mavic-3-pro": ("Triple-Lens Camera Drone", "Inspiration in Focus"),
    "dji-air-3s": ("Dual-Camera Drone for Travel Photography", "Chase the View"),
    "dji-mini-4-pro": (None, "Mini to the Max"),
}

# ---------- Round 8: detail-page heroes (DJI-style full-bleed moving hero) ----------
# Per-product cinematic hero frame, paths relative to staging/images/.
# Sources: round6/hero-dji.json (13) + hero-cctv.json (59, p65 none)
# + hero-other.json (34, p39 none) = 106 entries; p39/p65 have no photo
# and render the plain black hero. CCTV/other entries are UPDATED to
# the workers' hero-dark paths by the round-8 merge step (round8/
# merge_inputs.py). "pos" = CSS background-position.
# "video" = DJI hotlinked hero mp4 (ids 0/2/4/52; Mini 5 Pro has none).
DETAIL_HERO = {'audionic-bluetooth-speaker': {'hero': 'images/hero-dark/audionic-bluetooth-speaker.jpg',
                                'pos': 'center'},
 'audionic-conference-speaker': {'hero': 'images/hero-dark/audionic-conference-speaker.jpg',
                                 'pos': 'center'},
 'audionic-earbuds': {'hero': 'images/hero-dark/audionic-earbuds.jpg', 'pos': 'center'},
 'audionic-home-theater-system': {'hero': 'images/hero-dark/audionic-home-theater-system.jpg',
                                  'pos': 'center'},
 'audionic-multimedia-speaker': {'hero': 'images/hero-dark/audionic-multimedia-speaker.jpg',
                                 'pos': 'center'},
 'audionic-party-speaker': {'hero': 'images/hero-dark/audionic-party-speaker.jpg', 'pos': 'center'},
 'audionic-portable-speaker': {'hero': 'images/hero-dark/audionic-portable-speaker.jpg',
                               'pos': 'center'},
 'audionic-soundbar': {'hero': 'images/hero-dark/audionic-soundbar.jpg', 'pos': 'center'},
 'audionic-subwoofer': {'hero': 'images/hero-dark/audionic-subwoofer.jpg', 'pos': 'center'},
 'audionic-wireless-microphone': {'hero': 'images/hero-dark/audionic-wireless-microphone.jpg',
                                  'pos': 'center'},
 'dahua-2mp-dome-camera': {'hero': 'images/hero-dark/dahua-2mp-dome-camera.jpg', 'pos': 'center'},
 'dahua-4k-ir-epoe-mini-dome': {'hero': 'images/hero-dark/dahua-4k-ir-epoe-mini-dome.jpg',
                                'pos': 'center'},
 'dahua-5mp-bullet-camera': {'hero': 'images/hero-dark/dahua-5mp-bullet-camera.jpg',
                             'pos': 'center'},
 'dahua-dh-epc230u': {'hero': 'images/hero-dark/dahua-dh-epc230u.jpg', 'pos': 'center'},
 'dahua-dh-hac-hdw1209tlqp-led': {'hero': 'images/hero-dark/dahua-dh-hac-hdw1209tlqp-led.jpg',
                                  'pos': 'center'},
 'dahua-dh-hac-t1a41p-4mp-ir-eyeball': {'hero': 'images/hero-dark/dahua-dh-hac-t1a41p-4mp-ir-eyeball.jpg',
                                        'pos': 'center'},
 'dahua-dh-hac-t5e20p-2mp-economy-hd-indoor-eyeball': {'hero': 'images/hero-dark/dahua-dh-hac-t5e20p-2mp-economy-hd-indoor-eyeball.jpg',
                                                       'pos': 'center'},
 'dahua-dh-ipc-b1e49-a-il-smart-dual-light-camera': {'hero': 'images/hero-dark/dahua-dh-ipc-b1e49-a-il-smart-dual-light-camera.jpg',
                                                     'pos': 'center'},
 'dahua-dh-ipc-hdbw4231fn-e2-m': {'hero': 'images/hero-dark/dahua-dh-ipc-hdbw4231fn-e2-m.jpg',
                                  'pos': 'center'},
 'dahua-dh-ipc-hdbw4239rn-ase': {'hero': 'images/hero-dark/dahua-dh-ipc-hdbw4239rn-ase.jpg',
                                 'pos': 'center'},
 'dahua-dh-ipc-hdbw5231en-ze-hdmi': {'hero': 'images/hero-dark/dahua-dh-ipc-hdbw5231en-ze-hdmi.jpg',
                                     'pos': 'center'},
 'dahua-dh-ipc-hdbw8232en-z-sl': {'hero': 'images/hero-dark/dahua-dh-ipc-hdbw8232en-z-sl.jpg',
                                  'pos': 'center'},
 'dahua-dh-ipc-hfw4239tn-ase': {'hero': 'images/hero-dark/dahua-dh-ipc-hfw4239tn-ase.jpg',
                                'pos': 'center'},
 'dahua-dh-ipc-t1e29-a-il-2mp-dome': {'hero': 'images/hero-dark/dahua-dh-ipc-t1e29-a-il-2mp-dome.jpg',
                                      'pos': 'center'},
 'dahua-dhi-dss4004-s2': {'hero': 'images/hero-dark/dahua-dhi-dss4004-s2.jpg', 'pos': 'center'},
 'dahua-dhi-dss7016dr-s2': {'hero': 'images/hero-dark/dahua-dhi-dss7016dr-s2.jpg', 'pos': 'center'},
 'dahua-dhi-ivss7008-1t': {'hero': 'images/hero-dark/dahua-dhi-ivss7008-1t.jpg', 'pos': 'center'},
 'dahua-dhi-ivss7016dr-4t': {'hero': 'images/hero-dark/dahua-dhi-ivss7016dr-4t.jpg',
                             'pos': 'center'},
 'dahua-dhi-nvr1108hs-s3-h': {'hero': 'images/hero-dark/dahua-dhi-nvr1108hs-s3-h.jpg',
                              'pos': 'center'},
 'dahua-dhi-nvr2108hs-4ks3': {'hero': 'images/hero-dark/dahua-dhi-nvr2108hs-4ks3.jpg',
                              'pos': 'center'},
 'dahua-dhi-nvr4116hs-4ks3': {'hero': 'images/hero-dark/dahua-dhi-nvr4116hs-4ks3.jpg',
                              'pos': 'center'},
 'dahua-dhi-nvr4216-16p-i': {'hero': 'images/hero-dark/dahua-dhi-nvr4216-16p-i.jpg',
                             'pos': 'center'},
 'dahua-dhi-nvr5216-16p-i': {'hero': 'images/hero-dark/dahua-dhi-nvr5216-16p-i.jpg',
                             'pos': 'center'},
 'dahua-dhi-nvr6a08-128-4ks2': {'hero': 'images/hero-dark/dahua-dhi-nvr6a08-128-4ks2.jpg',
                                'pos': 'center'},
 'dahua-dhi-nvr6a08-32-4ks2': {'hero': 'images/hero-dark/dahua-dhi-nvr6a08-32-4ks2.jpg',
                               'pos': 'center'},
 'dahua-dhi-nvr6a08-64-4ks2': {'hero': 'images/hero-dark/dahua-dhi-nvr6a08-64-4ks2.jpg',
                               'pos': 'center'},
 'dahua-n22al12': {'hero': 'images/hero-dark/dahua-n22al12.jpg', 'pos': 'center'},
 'dahua-n24cb33': {'hero': 'images/hero-dark/dahua-n24cb33.jpg', 'pos': 'center'},
 'dahua-n24cg52': {'hero': 'images/hero-dark/dahua-n24cg52.jpg', 'pos': 'center'},
 'dahua-n24cl52': {'hero': 'images/hero-dark/dahua-n24cl52.jpg', 'pos': 'center'},
 'dahua-n25cb5z': {'hero': 'images/hero-dark/dahua-n25cb5z.jpg', 'pos': 'center'},
 'dahua-n25cl5z': {'hero': 'images/hero-dark/dahua-n25cl5z.jpg', 'pos': 'center'},
 'dahua-n42b2p': {'hero': 'images/hero-dark/dahua-n42b2p.jpg', 'pos': 'center'},
 'dahua-n42b3p': {'hero': 'images/hero-dark/dahua-n42b3p.jpg', 'pos': 'center'},
 'dahua-n52a4p': {'hero': 'images/hero-dark/dahua-n52a4p.jpg', 'pos': 'center'},
 'dahua-n52b2p': {'hero': 'images/gallery/dahua-n52b2p-g1.jpg', 'pos': 'center'},
 'dahua-n52b3p': {'hero': 'images/full/p95.jpg', 'pos': 'center'},
 'dahua-n52b5p': {'hero': 'images/hero-dark/dahua-n52b5p.jpg', 'pos': 'center'},
 'dahua-n54a4p': {'hero': 'images/hero-dark/dahua-n54a4p.jpg', 'pos': 'center'},
 'dahua-n54b3p': {'hero': 'images/hero-dark/dahua-n54b3p.jpg', 'pos': 'center'},
 'dahua-n54b5n': {'hero': 'images/hero-dark/dahua-n54b5n.jpg', 'pos': 'center'},
 'dahua-n84cg52': {'hero': 'images/hero-dark/dahua-n84cg52.jpg', 'pos': 'center'},
 'dji-agras-series': {'hero': 'images/gallery/dji-agras-series-g3.jpg', 'pos': 'center 40%', 'yt': 'qB0N4pwrjE8'},
 'dji-air-3': {'hero': 'images/full/p3.jpg', 'pos': 'center 70%', 'yt': 'xi85DAbv5oU'},
 'dji-air-3s': {'hero': 'images/hero/air3s.jpg',
                'pos': 'center',
                'video': 'https://www-cdn.djiits.com/reactor/assets/_next/static/videos/b7e5922b-6d8a-4534-a9a3-f22188af3795.mp4'},
 'dji-avata-2': {'hero': 'images/full/p6.jpg', 'pos': 'center', 'yt': 'RNhmV4yCP6M'},
 'dji-matrice-30t': {'hero': 'images/full/p8.jpg', 'pos': 'center 30%', 'yt': '1ucIm6g9llg'},
 'dji-mavic-3-pro': {'hero': 'images/hero/mavic3-cine.jpg',
                     'pos': 'center',
                     'video': 'https://www-cdn.djiits.com/reactor/assets/_next/static/videos/fdaa1941-2093-48eb-836a-913613397978.mp4'},
 'dji-mini-2': {'hero': 'images/full/p53.jpg', 'pos': 'center', 'yt': 'NMf4KI3kpZg'},
 'dji-mini-3': {'hero': 'images/gallery/dji-mini-3-g1.jpg', 'pos': 'center 25%', 'yt': '6VbOozPmbr4'},
 'dji-mini-3-pro': {'hero': 'images/gallery/dji-mini-3-pro-g1.jpg',
                    'pos': 'center 30%',
                    'video': 'https://www-cdn.djiits.com/reactor/assets/_next/static/videos/57398bd3-ab54-406c-96ed-00f848b647fa.mp4'},
 'dji-mini-4-pro': {'hero': 'images/gallery/dji-mini-4-pro-g1.jpg',
                    'pos': 'center 20%',
                    'video': 'https://www-cdn.djiits.com/reactor/assets/_next/static/videos/6dfe2cd8-e5ed-4d32-af86-9845f37450c7.mp4'},
 'dji-mini-4k': {'hero': 'images/gallery/dji-mini-4k-g7.jpg', 'pos': 'center'},
 'dji-mini-5-pro': {'hero': 'images/full/p51.jpg', 'pos': 'center', 'yt': 'jRzpagPx6uY'},
 'dji-neo': {'hero': 'images/full/p5.jpg', 'pos': 'center', 'yt': '7xHQIDYTHiw'},
 'ezviz-indoor-camera': {'hero': 'images/gallery/ezviz-indoor-camera-g3.jpg', 'pos': 'center'},
 'ezviz-outdoor-camera': {'hero': 'images/gallery/ezviz-outdoor-camera-g2.jpg', 'pos': 'center'},
 'hikvision-2mp-dome-camera': {'hero': 'images/hero-dark/hikvision-2mp-dome-camera.jpg',
                               'pos': 'center'},
 'hikvision-5mp-bullet-camera': {'hero': 'images/hero-dark/hikvision-5mp-bullet-camera.jpg',
                                 'pos': 'center'},
 'icsee-v1-single-lens': {'hero': 'images/hero-dark/icsee-v1-single-lens.jpg', 'pos': 'center'},
 'imou-ranger-2-2k-3mp': {'hero': 'images/scene/imou-ranger-2-hero.jpg', 'pos': 'center'},
 'imou-ranger-2-pro-2k': {'hero': 'images/scene/imou-ranger-2-pro-hero.jpg', 'pos': 'center'},
 'imou-ranger-series': {'hero': 'images/hero-dark/imou-ranger-series.jpg', 'pos': 'center'},
 'lg-43-inch-smart-led': {'hero': 'images/scene/lg-ua80-hero.jpg', 'pos': 'center'},
 'lg-55-inch-smart-led': {'hero': 'images/scene/lg-ua80-hero.jpg', 'pos': 'center'},
 'lg-65-inch-smart-led': {'hero': 'images/scene/lg-ua80-hero.jpg', 'pos': 'center'},
 'ruijie-access-point': {'hero': 'images/hero-dark/ruijie-access-point.jpg', 'pos': 'center'},
 'ruijie-rg-ew300-pro': {'hero': 'images/hero-dark/ruijie-rg-ew300-pro.jpg', 'pos': 'center'},
 'ruijie-rg-ew300n-n300-wireless-smart-router': {'hero': 'images/gallery/ruijie-rg-ew300n-n300-wireless-smart-router-g1.jpg',
                                                 'pos': 'center'},
 'ruijie-wifi-router': {'hero': 'images/gallery/ruijie-wifi-router-g2.jpg', 'pos': 'center'},
 'samsung-43-inch-led': {'hero': 'images/hero-dark/samsung-43-inch-led.jpg', 'pos': 'center'},
 'samsung-55-inch-led': {'hero': 'images/hero-dark/samsung-55-inch-led.jpg', 'pos': 'center'},
 'samsung-65-inch-led': {'hero': 'images/hero-dark/samsung-65-inch-led.jpg', 'pos': 'center'},
 'sony-43-inch-bravia': {'hero': 'images/scene/sony-bravia-43-hero.jpg', 'pos': '65% center'},
 'sony-55-inch-bravia': {'hero': 'images/scene/sony-bravia-5-hero.jpg', 'pos': 'center'},
 'sony-65-inch-bravia': {'hero': 'images/scene/sony-bravia-5-hero.jpg', 'pos': 'center'},
 'sony-75-inch-bravia': {'hero': 'images/scene/sony-bravia-5-hero.jpg', 'pos': 'center'},
 'tenda-access-point': {'hero': 'images/hero-dark/tenda-access-point.jpg', 'pos': 'center'},
 'tenda-n300-wireless-router': {'hero': 'images/hero-dark/tenda-n300-wireless-router.jpg',
                                'pos': 'center'},
 'tenda-network-switch': {'hero': 'images/gallery/tenda-network-switch-g2.jpg', 'pos': 'center'},
 'tenda-wifi-router': {'hero': 'images/hero-dark/tenda-wifi-router.jpg', 'pos': 'center'},
 'tiandy-5mp-camera': {'hero': 'images/hero-dark/tiandy-5mp-camera.jpg', 'pos': 'center'},
 'tiandy-ip-camera': {'hero': 'images/hero-dark/tiandy-ip-camera.jpg', 'pos': 'center'},
 'tiandy-nvr-tc-r3120': {'hero': 'images/hero-dark/tiandy-nvr-tc-r3120.jpg', 'pos': 'center'},
 'tiandy-tc-321-2mp': {'hero': 'images/hero-dark/tiandy-tc-321-2mp.jpg', 'pos': 'center'},
 'tiandy-tc-c331': {'hero': 'images/hero-dark/tiandy-tc-c331.jpg', 'pos': 'center'},
 'tiandy-tc-r3104': {'hero': 'images/hero-dark/tiandy-tc-r3104.jpg', 'pos': 'center'},
 'tiandy-tc-r3108': {'hero': 'images/hero-dark/tiandy-tc-r3108.jpg', 'pos': 'center'},
 'tp-link-archer-router': {'hero': 'images/hero-dark/tp-link-archer-router.jpg', 'pos': 'center'},
 'tp-link-network-switch': {'hero': 'images/hero-dark/tp-link-network-switch.jpg', 'pos': 'center'},
 'tp-link-tl-wr840n': {'hero': 'images/hero-dark/tp-link-tl-wr840n.jpg', 'pos': 'center'},
 'tp-link-wifi-access-point': {'hero': 'images/hero-dark/tp-link-wifi-access-point.jpg',
                               'pos': 'center'},
 'ubiquiti-unifi-access-point': {'hero': 'images/gallery/ubiquiti-unifi-access-point-g2.jpg',
                                 'pos': 'center'},
 'ubiquiti-unifi-switch': {'hero': 'images/gallery/ubiquiti-unifi-switch-g4.jpg', 'pos': 'center'},
 'v380-e27': {'hero': 'images/hero-dark/v380-e27.jpg', 'pos': 'center'},
 'v380-pro-wifi-camera': {'hero': 'images/hero-dark/v380-pro-wifi-camera.jpg', 'pos': 'center'}}

# ---------- Round 8: image-led feature sections (DJI pattern) ----------
# FEATURES: product id (int -- products.json ids are ints; string keys would never match) -> [{h, b, img, source}] — verified facts only,
# filled from round8/*/features-*.json by the merge step (round8/
# merge_inputs.py). Products with no verified feature material get no
# sections (hero + gallery + about only). SHOWPIECE: product id -> gallery-
# main image (dark-stage / scene) replacing the light-stage primary as the
# gallery main photo. SHOWPIECE_THUMB: id -> 400x300 thumb for it.
FEATURES = {0: [{'b': 'Weighing less than 249 g, Mini 4 Pro was designed for convenience on the go, with no '
           'need for training or examinations in most countries and regions.',
      'h': 'Under 249 g — take it anywhere',
      'img': 'images/gallery/dji-mini-4-pro-g1.jpg',
      'source': "DJI Mini 4 Pro page, condensed from generator DJI_FEATURES block 'Take it Easy'; "
                'spec strip in dji-deep-study-2026-11-19.md §4'},
     {'b': 'A 1/1.3-inch CMOS sensor with Dual Native ISO Fusion, an f/1.7 aperture and 2.4μm '
           '4-in-1 pixels captures 4K/60fps HDR and 4K/100fps video, with 10-bit D-Log M and HLG '
           'for colour.',
      'h': 'Out-sized imaging: 1/1.3-inch CMOS, 4K/60fps HDR',
      'img': 'images/full/p0.jpg',
      'source': "DJI Mini 4 Pro page, condensed from generator DJI_FEATURES blocks 'Out-sized "
                "Imaging Performance' + 'Maximum Visual Impact'; deep-study §4"},
     {'b': 'Up to 34 minutes on the Intelligent Flight Battery, or 45 minutes with the Battery '
           'Plus, with DJI O4 video transmission up to 20 km and ActiveTrack 360° keeping your '
           'subject in frame.',
      'h': 'Fly longer, track smarter',
      'img': None,
      'source': "DJI Mini 4 Pro page, condensed from generator DJI_FEATURES blocks 'Fly Longer, "
                "Create More', '20 km Video Transmission', 'A Touch of Cinematics'; deep-study "
                '§4'}],
 1: [{'b': 'A compact, ultra-lightweight camera drone built for adventure, with detail-rich 4K HDR '
           'video and True Vertical Shooting for social-media-ready shots.',
      'h': 'So fly — light, simple, 4K HDR',
      'img': 'images/gallery/dji-mini-3-g1.jpg',
      'source': 'dji.com/mini-3 intro copy, fetched 20 Nov 2026'},
     {'b': 'Under 249 g with Smart RTH and DJI O2 video transmission up to 10 km, so everyday '
           'flights stay simple and connected.',
      'h': 'Easy flights, further reach',
      'img': None,
      'source': 'dji-deep-study-2026-11-19.md §4 comparison table, Mini 3 row'}],
 2: [{'b': 'A 1-inch-CMOS primary camera with a 24mm lens for expansive landscapes, plus a 70mm '
           'medium tele camera that compresses depth of field for portraits with a bolder, '
           'cinematic look.',
      'h': 'Dual cameras, unmatched imagery',
      'img': 'images/hero/air3s.jpg',
      'source': "DJI Air 3S page, condensed from generator DJI_FEATURES block 'Dual Cameras, "
                "Unmatched Imagery'; deep-study §3"},
     {'b': 'Nightscape Omnidirectional Obstacle Sensing and next-gen Smart RTH — including Non-GPS '
           'RTH and Nighttime RTH — for safer flights and a precise return home after dark.',
      'h': 'Safer night flying',
      'img': 'images/gallery/dji-air-3s-g1.jpg',
      'source': "DJI Air 3S page: deep-study §3 section headings + spec strip ('Nightscape "
                "Omnidirectional Obstacle Sensing', 'Next-Gen Smart RTH'); DJI_FEATURES 'Next-Gen "
                "Smart RTH' chips"},
     {'b': 'Up to 45 minutes of flight time and 10-bit O4 video transmission up to 20 km, with '
           '42GB of built-in storage so you can start recording right away.',
      'h': 'Serious air time: 45 minutes, 20 km',
      'img': None,
      'source': "DJI Air 3S page, condensed from generator DJI_FEATURES blocks 'Serious Air Time: "
                "45-Min Max', '10-bit O4 Video Transmission', 'Always Ready: 42GB of Built-in "
                "Storage'; deep-study §3"}],
 3: [{'b': 'A wide-angle and a medium tele camera, both 1/1.3-inch 48MP, cover sweeping scenery '
           'and closer zoom views from the same flight.',
      'h': 'Double up — two 48MP cameras',
      'img': 'images/full/p3.jpg',
      'source': 'dji-deep-study-2026-11-19.md §3/§4 comparison tables, Air 3 row (720 g, 1/1.3″ '
                '48MP + 48MP)'},
     {'b': '4K/60fps HDR video and 4K/100fps slow motion, with Night Shots and 10-bit D-Log M and '
           'HLG for flexible colour in post.',
      'h': '4K/60fps HDR, day and night',
      'img': 'images/gallery/dji-air-3-g1.jpg',
      'source': 'dji-deep-study-2026-11-19.md §4 comparison table, Air 3 row'},
     {'b': 'Up to 46 minutes of flight time, DJI O4 transmission up to 20 km, and omnidirectional '
           'obstacle sensing with APAS 5.0.',
      'h': '46 minutes, 20 km, sensing all around',
      'img': None,
      'source': 'dji-deep-study-2026-11-19.md §3/§4 comparison tables, Air 3 row (46 mins, 20 km, '
                'Omnidirectional APAS 5.0)'}],
 4: [{'b': 'A triple-camera system with three focal lengths — tap the display to switch between '
           'them and shape each shot, from wide landscapes to compressed telephoto scenes.',
      'h': 'One drone, three lenses',
      'img': 'images/hero/mavic3-cine.jpg',
      'source': "DJI Mavic 3 Pro page, condensed from generator DJI_FEATURES block 'Unrivaled "
                "Tri-Camera Flagship Imaging'; deep-study §2"},
     {'b': 'The Hasselblad camera shoots 12-bit RAW photos with a native dynamic range of up to '
           '12.8 stops, and its Natural Colour Solution restores colours as the eye sees them. '
           'Video runs to 5.1K/50fps and 4K/120fps.',
      'h': '4/3 CMOS Hasselblad camera, immense detail',
      'img': 'images/full/p4.jpg',
      'source': "DJI Mavic 3 Pro page, condensed from generator DJI_FEATURES block 'Hasselblad "
                "Camera, Immense Detail'; deep-study §2 body copy (verified verbatim there)"},
     {'b': 'Up to 43 minutes of flight time, DJI O3+ transmission up to 15 km with a 1080p/60fps '
           'live feed, and eight wide-angle vision sensors watching for obstacles in all '
           'directions.',
      'h': '43 minutes, 15 km, sensing in all directions',
      'img': None,
      'source': "DJI Mavic 3 Pro page, condensed from generator DJI_FEATURES blocks 'Extended "
                "Flight Time', 'Omnidirectional Obstacle Sensing and APAS 5.0', 'Flagship Video "
                "Transmission'; deep-study §2 spec strip"}],
 5: [{'b': "At 135 g, DJI Neo is DJI's lightest and most compact aerial videographer — take off "
           'and land on your palm, with no remote needed.',
      'h': "135 g — DJI's lightest drone",
      'img': 'images/full/p5.jpg',
      'source': 'dji.com/neo intro copy, fetched 20 Nov 2026'},
     {'b': 'Smart tracking turns Neo into your personal flying camera, capturing cinematic footage '
           'with you in focus, indoors and out — with full-cover prop guards keeping flights safe.',
      'h': 'You in focus',
      'img': 'images/gallery/dji-neo-g1.jpg',
      'source': 'dji.com/neo description, fetched 20 Nov 2026'},
     {'b': 'Stabilized 4K video, multiple control options and one-tap editing — effortless for all '
           'skill levels, with zero learning curve.',
      'h': 'Stabilized 4K, one-tap edits',
      'img': None,
      'source': 'dji.com/neo description, fetched 20 Nov 2026'}],
 6: [{'b': 'Step into immersive FPV flight with DJI Avata 2 — shoot dramatic, ultra-wide 4K '
           'footage close to the ground.',
      'h': 'Immersive flight, unbound',
      'img': 'images/full/p6.jpg',
      'source': 'dji.com/avata-2 description, fetched 20 Nov 2026'},
     {'b': 'Easy ACRO and gesture-based control via Goggles 3 and RC Motion 3 make FPV flying '
           'simple, while integrated propeller protection keeps agile flights safe.',
      'h': 'Easy ACRO, gesture control',
      'img': 'images/gallery/dji-avata-2-g2.jpg',
      'source': 'dji.com/avata-2 description, fetched 20 Nov 2026'},
     {'b': 'A 1/1.3-inch camera shooting 4K/60fps HDR, up to 23 minutes of flight time and 13 km '
           'of video transmission.',
      'h': '4K/60fps HDR, 23 minutes',
      'img': None,
      'source': 'dji-deep-study-2026-11-19.md §5 comparison table, Immersive Flight / Avata 2 '
                'row'}],
 7: [{'b': 'The palm-sized Mini 4K fits in any bag and needs no registration in most countries and '
           'regions — with a 1/2.3-inch CMOS camera delivering crisp 4K video.',
      'h': 'Under 249 g, real 4K',
      'img': 'images/gallery/dji-mini-4k-g7.jpg',
      'source': "DJI Store Mini 4K page (store.dji.com), 'Under 249 g' + 'Stunning Intelligent "
                "Features' blocks"},
     {'b': 'Up to 31 minutes of flight time and DJI O2 video transmission up to 10 km, with '
           'excellent anti-interference for a clear, easy flight.',
      'h': '31 minutes, 10 km link',
      'img': None,
      'source': "DJI Store Mini 4K page (store.dji.com), '10km Video Transmission' + '31-Min Max "
                "Flight Time' blocks"},
     {'b': 'Level 5 wind resistance up to 38 kph and a 4,000 m max takeoff altitude keep footage '
           'stable — with QuickShots and Panoramas for impressive shots at a tap.',
      'h': 'Steady in wind, smart in the air',
      'img': None,
      'source': "DJI Store Mini 4K page (store.dji.com), '38kph (Level 5) Wind Resistance' + "
                "'Stunning Intelligent Features' blocks"}],
 8: [{'b': 'A 12MP wide camera, a 48MP zoom camera, a 640×512 thermal imager and a laser '
           'rangefinder — wide, zoom, thermal and ranging in a single payload.',
      'h': 'Four sensors, one gimbal',
      'img': 'images/full/p8.jpg',
      'source': 'DJI Matrice 30 series published specs, via Skyebrowse / IGIDRONE / Uplink Imaging '
                "reproductions of DJI's official figures"},
     {'b': 'The thermal camera reads heat at 640×512, with a 1280×1024 super-resolution mode, and '
           'the laser rangefinder measures targets from 3 m out to 1,200 m.',
      'h': 'See heat, measure distance',
      'img': 'images/gallery/dji-matrice-30t-g4.jpg',
      'source': 'DJI Matrice 30 series published specs, via Skyebrowse / IGIDRONE / Ferntech '
                "reproductions of DJI's official figures"},
     {'b': 'IP55 weather sealing and a −20 °C to 50 °C operating range, with up to 41 minutes of '
           'flight time, for inspection, survey and public-safety missions.',
      'h': 'Built for bad-weather work',
      'img': None,
      'source': 'DJI Matrice 30 series published specs, via IGIDRONE / Uplink Imaging '
                "reproductions of DJI's official figures"}],
 9: [{'b': "DJI's smart agricultural equipment — spraying and spreading drones built to cover "
           'large fields quickly and evenly.',
      'h': 'Big drone, big jobs',
      'img': 'images/gallery/dji-agras-series-g3.jpg',
      'source': "dji-deep-study-2026-11-19.md §1 homepage slide 9 ('Smart Agricultural Equipment / "
                "Big Drone, Big Jobs'); staging product description"},
     {'b': 'Across the range, spray tanks run from 20 L on the T25 to 40 L on the T50, 70 L on the '
           'T70P and 100 L on the T100 — bigger tanks, fewer refills.',
      'h': 'Tanks from 20 L to 100 L',
      'img': 'images/full/p9.jpg',
      'source': "DJI Agras published specs, via AGX / Aegis / Uplink Imaging comparisons of DJI's "
                'official figures'},
     {'b': 'Phased-array radar and vision sensing with terrain following on slopes up to 50°, '
           'spraying up to 40 L/min across swaths up to 13 m wide.',
      'h': 'Radar, terrain follow, wide swaths',
      'img': None,
      'source': "DJI Agras published specs, via AGX / Aegis comparisons of DJI's official figures "
                '(T70P/T100 flow and T100 width as range maxima)'}],
 10: [{'b': 'A 2-megapixel dome camera in a compact ceiling-mount form — clear Full HD coverage '
            'without bulky hardware on show.',
       'h': '2MP dome, made to disappear on the ceiling',
       'img': None,
       'source': 'AK Khan product record — name/description (Hikvision 2MP Dome Camera)'},
      {'b': 'The dome shape sits tidy on a ceiling, watching the room while blending in — for '
            'security without bulky hardware.',
       'h': 'Discreet coverage for shops, offices and homes',
       'img': None,
       'source': 'AK Khan product record — name/description (Hikvision 2MP Dome Camera)'}],
 11: [{'b': '5-megapixel imaging (2560×1920) with EXIR 2.0 infrared up to 30 m, so gates and yards '
            'stay visible after dark.',
       'h': '5MP clarity, day and night',
       'img': 'images/gallery/hikvision-5mp-bullet-camera-g1.jpg',
       'source': 'Hikvision official datasheet — DS-2CD1053G0-I 5MP Fixed Bullet Network Camera'},
      {'b': 'IP67 weatherproof housing and 120 dB true WDR handle rain, dust and harsh backlight '
            'on building exteriors.',
       'h': 'Built for the outdoors',
       'img': 'images/gallery/hikvision-5mp-bullet-camera-g2.jpg',
       'source': 'Hikvision official datasheet — DS-2CD1053G0-I 5MP Fixed Bullet Network Camera'},
      {'b': 'H.265+ compression keeps the 5MP stream light on bandwidth and storage, powered by '
            'PoE or 12 V DC.',
       'h': 'Efficient H.265+ streaming',
       'img': None,
       'source': 'Hikvision official datasheet — DS-2CD1053G0-I 5MP Fixed Bullet Network Camera'}],
 12: [{'b': 'A dome sits close under a ceiling or eave and watches the room without standing out — '
            'the right shape for shops, offices and homes.',
       'h': 'Dome shape, discreet on the ceiling',
       'img': None,
       'source': "AK Khan listing (products.json) — 'Dahua 2MP Dome Camera'; exact Dahua model "
                 'unverified, see round-2 gap note in photo-replace-2026-11-19.md'},
      {'b': "Listed as a 2MP dome camera from Dahua's surveillance range, for reliable everyday "
            'coverage. The exact model is confirmed with the shop on WhatsApp before you buy.',
       'h': 'Listed as a 2MP Dahua dome',
       'img': None,
       'source': "AK Khan listing (products.json) — 'Dahua 2MP Dome Camera'; exact Dahua model "
                 'unverified, see round-2 gap note in photo-replace-2026-11-19.md'}],
 13: [{'b': 'A bullet on a wall bracket points exactly where it is aimed — the right shape for '
            'gates, streets and larger properties.',
       'h': 'Bullet shape, built for outdoors',
       'img': None,
       'source': "AK Khan listing (products.json) — 'Dahua 5MP Bullet Camera'; exact Dahua model "
                 'unverified, see round-2 gap note in photo-replace-2026-11-19.md'},
      {'b': "Listed as a 5MP bullet camera from Dahua's surveillance range, for clear, detailed "
            'outdoor pictures. The exact model is confirmed with the shop on WhatsApp before you '
            'buy.',
       'h': 'Listed as a 5MP Dahua bullet',
       'img': None,
       'source': "AK Khan listing (products.json) — 'Dahua 5MP Bullet Camera'; exact Dahua model "
                 'unverified, see round-2 gap note in photo-replace-2026-11-19.md'}],
 14: [{'b': "Five-megapixel imaging from Tiandy's professional range — finer detail than standard "
            'Full HD across wide areas.',
       'h': '5MP sharpness across wide areas',
       'img': 'images/gallery/tiandy-5mp-camera-g2.jpg',
       'source': 'AK Khan product record — name/description (Tiandy 5MP Camera)'},
      {'b': "From Tiandy's professional surveillance range, for businesses that want sharp images "
            'across wide areas.',
       'h': 'A professional-range Tiandy camera',
       'img': 'images/gallery/tiandy-5mp-camera-g3.jpg',
       'source': 'AK Khan product record — name/description (Tiandy 5MP Camera)'}],
 15: [{'b': 'An IP camera built for larger, managed security systems — one network, many cameras, '
            'one place to watch them.',
       'h': 'A network camera for managed systems',
       'img': 'images/gallery/tiandy-ip-camera-g1.jpg',
       'source': 'AK Khan product record — name/description (Tiandy IP Camera)'},
      {'b': 'Suited to offices, schools and warehouses running several cameras together on one '
            'system.',
       'h': 'Made for multi-camera sites',
       'img': 'images/gallery/tiandy-ip-camera-g2.jpg',
       'source': 'AK Khan product record — name/description (Tiandy IP Camera)'}],
 16: [{'b': "A smart indoor WiFi camera you can check from your phone, from anywhere — EZVIZ's own "
            'promise for this camera.',
       'h': 'Check home from your phone, from anywhere',
       'img': 'images/gallery/ezviz-indoor-camera-g1.jpg',
       'source': 'AK Khan product record — name/description (EZVIZ Indoor Camera)'},
      {'b': 'Best for keeping an eye on children, elders and pets at home — it connects over WiFi, '
            'so there is no network cable to run and no recorder box to install.',
       'h': 'Made for watching over family',
       'img': 'images/gallery/ezviz-indoor-camera-g3.jpg',
       'source': 'AK Khan product record — name/description (EZVIZ Indoor Camera)'}],
 17: [{'b': 'A weather-ready outdoor WiFi camera for gates and yards — phone-viewable security '
            'outside the house.',
       'h': 'Weather-ready watch over gates and yards',
       'img': 'images/gallery/ezviz-outdoor-camera-g1.jpg',
       'source': 'AK Khan product record — name/description (EZVIZ Outdoor Camera)'},
      {'b': 'Built for homes and shops that want outdoor coverage they can open on their phone at '
            'any time.',
       'h': 'Outdoor security you check from your phone',
       'img': 'images/gallery/ezviz-outdoor-camera-g2.jpg',
       'source': 'AK Khan product record — name/description (EZVIZ Outdoor Camera)'}],
 18: [{'b': 'Ranger cameras turn to follow the action around the room, so a single camera covers '
            'what fixed cameras cannot.',
       'h': 'Pan and tilt — one camera watches the whole room',
       'img': 'images/scene/imou-ranger-series-pan.jpg',
       'source': 'AK Khan product record — name/description (IMOU Ranger Series)'},
      {'b': 'Best for homes and small shops that want wide coverage from one camera instead of '
            'several fixed ones.',
       'h': 'Wide coverage from a single camera',
       'img': 'images/gallery/imou-ranger-series-g3.jpg',
       'source': 'AK Khan product record — name/description (IMOU Ranger Series)'}],
 19: [{'b': 'A budget-friendly WiFi camera with app viewing for simple home monitoring — V380 Pro '
            'app on your phone.',
       'h': 'Simple WiFi monitoring, checked on your phone',
       'img': None,
       'source': 'AK Khan product record — name/description (V380 Pro WiFi Camera)'},
      {'b': 'Made for small rooms, shop counters and first-time camera buyers who want monitoring '
            'without a big setup.',
       'h': 'First camera, no fuss',
       'img': None,
       'source': 'AK Khan product record — name/description (V380 Pro WiFi Camera)'}],
 20: [],
 21: [],
 22: [],
 23: [],
 24: [{'b': 'Twenty-four 10/100/1000 Mbps RJ45 ports with auto-negotiation — wire up PCs, cameras, '
            'printers and access points at full gigabit speed.',
       'h': '24 Gigabit ports',
       'img': 'images/gallery/tp-link-network-switch-g1.jpg',
       'source': 'TP-Link TL-SG1024D official product page (tp-link.com): '
                 'https://www.tp-link.com/sa/business-networking/unmanaged-switch/tl-sg1024d/'},
      {'b': 'An unmanaged switch: no configuration needed. Auto MDI/MDIX means any Ethernet cable '
            'works, and the fanless design runs silent.',
       'h': 'Plug and play, no setup',
       'img': None,
       'source': 'TP-Link TL-SG1024D official product page (tp-link.com): '
                 'https://www.tp-link.com/sa/business-networking/unmanaged-switch/tl-sg1024d/'},
      {'b': 'A 48 Gbps switching capacity and 35.7 Mpps forwarding rate keep all 24 ports moving '
            'at line rate, in a desktop or rackmount metal case.',
       'h': '48 Gbps switching capacity',
       'img': None,
       'source': 'TP-Link TL-SG1024D official product page (tp-link.com): '
                 'https://www.tp-link.com/sa/business-networking/unmanaged-switch/tl-sg1024d/'}],
 25: [],
 26: [],
 27: [],
 28: [],
 29: [],
 30: [],
 31: [],
 32: [],
 33: [{'b': 'Five 3-inch satellite speakers and an 8-inch subwoofer place sound all around the '
            'room — cinema-style surround for movie nights.',
       'h': 'True 5.1 surround sound',
       'img': 'images/gallery/audionic-home-theater-system-g1.jpg',
       'source': 'Audionic Pace 8 official product page (audionic.co): '
                 'https://audionic.co/products/pace-8-home-theater-system'},
      {'b': '120W total RMS output — a 60W subwoofer plus 15W in each of the five satellites — for '
            'loud, full sound in medium to large rooms.',
       'h': '120W RMS of power',
       'img': 'images/gallery/audionic-home-theater-system-g2.jpg',
       'source': 'Audionic Pace 8 official product page (audionic.co): '
                 'https://audionic.co/products/pace-8-home-theater-system'},
      {'b': 'Stream over Bluetooth 5.0 or play from USB and SD card, with AUX input, built-in FM '
            'radio, an LED display and a wireless remote.',
       'h': 'Bluetooth 5.0, USB, AUX and FM',
       'img': None,
       'source': 'Audionic Pace 8 official product page (audionic.co): '
                 'https://audionic.co/products/pace-8-home-theater-system'}],
 34: [],
 35: [],
 36: [],
 37: [{'b': 'A 5.25-inch subwoofer and two satellite speakers deliver enhanced bass and clear '
            "sound — the 2.1 setup Audionic sells as 'The Sound Master'.",
       'h': '2.1 channel with a 5.25-inch subwoofer',
       'img': 'images/gallery/audionic-subwoofer-g1.jpg',
       'source': "Audionic Vision 35 retail listings and retail box ('Enhanced Audio & Bass with "
                 "Elegant 2.1 Channel Speaker', 5.25-inch subwoofer): "
                 'https://store30944.store.link/product/audionic-vision-35'},
      {'b': 'Play wirelessly over Bluetooth or from USB and SD card, tune in FM radio, and control '
            'it all from the wireless remote with its LED display.',
       'h': 'Bluetooth, USB, FM and remote',
       'img': 'images/gallery/audionic-subwoofer-g2.jpg',
       'source': 'Audionic Vision 35 retail listings: '
                 'https://store30944.store.link/product/audionic-vision-35'}],
 38: [{'b': 'An 8-inch woofer in a take-anywhere cabinet with a handle — big sound for picnics, '
            'gatherings and outdoor use.',
       'h': '8-inch portable party speaker',
       'img': 'images/gallery/audionic-portable-speaker-g1.jpg',
       'source': 'Audionic MH-808 Plus specifications (NexGen Shop): '
                 'https://nexgenshop.pk/audionic-mehfil-mh-808-2/ — 8-inch woofer, Bluetooth, '
                 'USB/TF/AUX'},
      {'b': 'A wireless handheld microphone is included, with delay, repeat and echo voice effects '
            'and TWS pairing for a second speaker.',
       'h': 'Wireless mic and karaoke effects',
       'img': 'images/gallery/audionic-portable-speaker-g3.jpg',
       'source': 'Audionic MH-808 Plus specifications (NexGen Shop): '
                 'https://nexgenshop.pk/audionic-mehfil-mh-808-2/ — wireless mic, TWS, '
                 'delay/repeat/echo'},
      {'b': 'Stream over Bluetooth or play from USB and TF card, with AUX input, colourful RGB LED '
            'party lights, a remote and a rechargeable battery.',
       'h': 'Bluetooth, USB, TF card and RGB lights',
       'img': None,
       'source': 'Audionic MH-808 Plus retail box and listings: '
                 'https://nexgenshop.pk/audionic-mehfil-mh-808-2/'}],
 39: [],
 40: [{'b': 'A 12-inch woofer plus a 12-inch speaker deliver 150W RMS of party sound — built for '
            'halls, gatherings and outdoor functions.',
       'h': 'Twin 12-inch drivers, 150W RMS',
       'img': 'images/gallery/audionic-conference-speaker-g3.jpg',
       'source': 'Audionic MEHFIL MH-1212 ADVANCE official product page (audionic.co): '
                 'https://audionic.co/collections/1-0-tower/products/mehfil-mh-1212-advance'},
      {'b': 'Two wireless microphones and three karaoke ports, with delay, repeat and echo '
            'effects, turn it into a full karaoke and announcements system.',
       'h': 'Two wireless mics and karaoke ports',
       'img': 'images/gallery/audionic-conference-speaker-g1.jpg',
       'source': 'Audionic MEHFIL MH-1212 ADVANCE official product page (audionic.co): '
                 'https://audionic.co/collections/1-0-tower/products/mehfil-mh-1212-advance'},
      {'b': 'A rechargeable battery runs for 5–6 hours, so the party keeps going without a plug '
            'socket — with Bluetooth (7–10 m range), USB and a remote.',
       'h': '5–6 hours on battery',
       'img': None,
       'source': 'Audionic MEHFIL MH-1212 ADVANCE official product page (audionic.co): '
                 'https://audionic.co/collections/1-0-tower/products/mehfil-mh-1212-advance'}],
 41: [{'b': "Samsung's Crystal Processor 4K enhances picture and sound, with powerful 4K upscaling "
            'that sharpens lower-resolution content up to 4K.',
       'h': 'Crystal Processor 4K',
       'img': 'images/gallery/samsung-43-inch-led-g6.jpg',
       'source': 'Samsung Crystal UHD line (samsung.com, Crystal UHD U8000F/U8000H/UE100F pages): '
                 "Crystal Processor 4K, 4K upscaling, PurColor, HDR; 'Crystal UHD' text visible in "
                 "the listing's own gallery photos"},
      {'b': 'PurColor expresses a wide range of colours for a vivid, lifelike picture, with HDR '
            'and a Contrast Enhancer for deeper depth.',
       'h': 'PurColor — true-to-life colour',
       'img': 'images/scene/samsung-u8000f-purcolor.jpg',
       'source': 'Samsung Crystal UHD line (samsung.com, Crystal UHD U8000F/U8000H/UE100F pages): '
                 "Crystal Processor 4K, 4K upscaling, PurColor, HDR; 'Crystal UHD' text visible in "
                 "the listing's own gallery photos"}],
 42: [{'b': "Samsung's Crystal Processor 4K enhances picture and sound, with powerful 4K upscaling "
            'that sharpens lower-resolution content up to 4K.',
       'h': 'Crystal Processor 4K',
       'img': 'images/full/p42.jpg',
       'source': 'Samsung Crystal UHD line (samsung.com, Crystal UHD U8000F/U8000H/UE100F pages): '
                 "Crystal Processor 4K, 4K upscaling, PurColor, HDR; 'Crystal UHD' text visible in "
                 "the listing's own gallery photos"},
      {'b': 'PurColor expresses a wide range of colours for a vivid, lifelike picture, with HDR '
            'and a Contrast Enhancer for deeper depth.',
       'h': 'PurColor — true-to-life colour',
       'img': 'images/scene/samsung-u8000f-purcolor.jpg',
       'source': 'Samsung Crystal UHD line (samsung.com, Crystal UHD U8000F/U8000H/UE100F pages): '
                 "Crystal Processor 4K, 4K upscaling, PurColor, HDR; 'Crystal UHD' text visible in "
                 "the listing's own gallery photos"}],
 43: [{'b': "Samsung's Crystal Processor 4K enhances picture and sound, with powerful 4K upscaling "
            'that sharpens lower-resolution content up to 4K.',
       'h': 'Crystal Processor 4K',
       'img': 'images/gallery/samsung-65-inch-led-g3.jpg',
       'source': 'Samsung Crystal UHD line (samsung.com, Crystal UHD U8000F/U8000H/UE100F pages): '
                 "Crystal Processor 4K, 4K upscaling, PurColor, HDR; 'Crystal UHD' text visible in "
                 "the listing's own gallery photos"},
      {'b': 'PurColor expresses a wide range of colours for a vivid, lifelike picture, with HDR '
            'and a Contrast Enhancer for deeper depth.',
       'h': 'PurColor — true-to-life colour',
       'img': 'images/scene/samsung-u8000f-purcolor.jpg',
       'source': 'Samsung Crystal UHD line (samsung.com, Crystal UHD U8000F/U8000H/UE100F pages): '
                 "Crystal Processor 4K, 4K upscaling, PurColor, HDR; 'Crystal UHD' text visible in "
                 "the listing's own gallery photos"}],
 44: [{'b': 'A 4K UHD panel with four times the resolution of Full HD for crisp detail and vibrant '
            'colour on films, sports and dramas.',
       'h': 'LG UHD — 4K picture',
       'img': 'images/scene/lg-ua80-4k.jpg',
       'source': "LG UHD TV line — 4K UHD resolution, webOS smart platform; 'LG UHD' badge and "
                 'webOS home screen visible in listing photo '
                 'images/gallery/lg-43-inch-smart-led-g1.jpg'},
      {'b': "LG's webOS smart platform puts streaming apps on the home screen — the webOS home "
            "screen is shown in the listing's own photo.",
       'h': 'webOS — all your apps in one place',
       'img': None,
       'source': "LG UHD TV line — 4K UHD resolution, webOS smart platform; 'LG UHD' badge and "
                 'webOS home screen visible in listing photo '
                 'images/gallery/lg-43-inch-smart-led-g1.jpg'}],
 45: [],
 46: [],
 47: [{'b': 'Google TV puts streaming apps, recommendations and voice search in one place — the '
            "Google TV badge is on the TV's own screen in the listing photo.",
       'h': 'Google TV built in',
       'img': 'images/scene/sony-bravia-43-googletv.jpg',
       'source': 'Google TV badge visible in listing photo images/full/p47.jpg; Sony BRAVIA Google '
                 'TV smart platform'},
      {'b': "Sony's BRAVIA picture in a 43-inch screen — the right size for bedrooms and smaller "
            'rooms, with rich colour for films and dramas.',
       'h': 'BRAVIA picture in a 43-inch size',
       'img': 'images/scene/sony-bravia-43-picture.jpg',
       'source': 'BRAVIA badge visible in listing photo images/full/p47.jpg; 43-inch size from the '
                 'product name'}],
 48: [{'b': "Sony's XR Processor with AI enhances colour, contrast and clarity scene by scene, "
            'with XR Triluminos Pro for billions of accurate colours.',
       'h': 'BRAVIA XR picture processing',
       'img': 'images/full/p48.jpg',
       'source': "'BRAVIA XR' badge visible in listing photo images/full/p48.jpg; Sony BRAVIA XR "
                 'line (XR Processor, XR Triluminos Pro)'},
      {'b': "A 4K HDR panel for sharp, high-contrast images — the 4K HDR badge is on the TV's own "
            'screen in the listing photo.',
       'h': '4K HDR picture',
       'img': None,
       'source': "'4K HDR' badge visible in listing photo images/full/p48.jpg"}],
 49: [{'b': 'Thousands of Mini LEDs, precisely controlled by XR Backlight Master Drive, deliver '
            'bright highlights and authentic contrast.',
       'h': 'Mini LED brightness and contrast',
       'img': 'images/full/p49.jpg',
       'source': 'Sony BRAVIA 5 (XR50) Mini LED line — XR Backlight Master Drive, XR Triluminos '
                 'Pro, XR Processor with AI, Google TV, 120Hz: '
                 'https://techstevehd.com/reviews/sony-bravia-5-xr50-series and '
                 'https://www.abt.com/Sony-BRAVIA-5-Mini-LED-TV-65-Inch-4K-Smart-with-Google-TV-K65XR50/p/221624.html; '
                 "'BRAVIA 5 Mini LED' and 'Google TV' badges visible in the listing's own photo"},
      {'b': 'The XR Processor with AI enhances every scene in real time, with XR Triluminos Pro '
            'colour and AI Super Resolution upscaling.',
       'h': 'XR Processor with AI',
       'img': None,
       'source': 'Sony BRAVIA 5 (XR50) Mini LED line — XR Backlight Master Drive, XR Triluminos '
                 'Pro, XR Processor with AI, Google TV, 120Hz: '
                 'https://techstevehd.com/reviews/sony-bravia-5-xr50-series and '
                 'https://www.abt.com/Sony-BRAVIA-5-Mini-LED-TV-65-Inch-4K-Smart-with-Google-TV-K65XR50/p/221624.html; '
                 "'BRAVIA 5 Mini LED' and 'Google TV' badges visible in the listing's own photo"},
      {'b': 'Google TV gathers all streaming apps on one screen, and the native 120Hz panel with '
            'HDMI 2.1 (4K/120, VRR, ALLM) is ready for PS5 and Xbox.',
       'h': 'Google TV and 120Hz gaming',
       'img': 'images/scene/sony-bravia-5-googletv.jpg',
       'source': 'Sony BRAVIA 5 (XR50) Mini LED line — XR Backlight Master Drive, XR Triluminos '
                 'Pro, XR Processor with AI, Google TV, 120Hz: '
                 'https://techstevehd.com/reviews/sony-bravia-5-xr50-series and '
                 'https://www.abt.com/Sony-BRAVIA-5-Mini-LED-TV-65-Inch-4K-Smart-with-Google-TV-K65XR50/p/221624.html; '
                 "'BRAVIA 5 Mini LED' and 'Google TV' badges visible in the listing's own photo"}],
 50: [{'b': 'Thousands of Mini LEDs, precisely controlled by XR Backlight Master Drive, deliver '
            'bright highlights and authentic contrast.',
       'h': 'Mini LED brightness and contrast',
       'img': 'images/full/p50.jpg',
       'source': 'Sony BRAVIA 5 (XR50) Mini LED line — XR Backlight Master Drive, XR Triluminos '
                 'Pro, XR Processor with AI, Google TV, 120Hz: '
                 'https://techstevehd.com/reviews/sony-bravia-5-xr50-series and '
                 'https://www.abt.com/Sony-BRAVIA-5-Mini-LED-TV-65-Inch-4K-Smart-with-Google-TV-K65XR50/p/221624.html; '
                 "'BRAVIA 5 Mini LED' and 'Google TV' badges visible in the listing's own photo"},
      {'b': 'The XR Processor with AI enhances every scene in real time, with XR Triluminos Pro '
            'colour and AI Super Resolution upscaling.',
       'h': 'XR Processor with AI',
       'img': None,
       'source': 'Sony BRAVIA 5 (XR50) Mini LED line — XR Backlight Master Drive, XR Triluminos '
                 'Pro, XR Processor with AI, Google TV, 120Hz: '
                 'https://techstevehd.com/reviews/sony-bravia-5-xr50-series and '
                 'https://www.abt.com/Sony-BRAVIA-5-Mini-LED-TV-65-Inch-4K-Smart-with-Google-TV-K65XR50/p/221624.html; '
                 "'BRAVIA 5 Mini LED' and 'Google TV' badges visible in the listing's own photo"},
      {'b': 'Google TV gathers all streaming apps on one screen, and the native 120Hz panel with '
            'HDMI 2.1 (4K/120, VRR, ALLM) is ready for PS5 and Xbox.',
       'h': 'Google TV and 120Hz gaming',
       'img': 'images/scene/sony-bravia-5-googletv.jpg',
       'source': 'Sony BRAVIA 5 (XR50) Mini LED line — XR Backlight Master Drive, XR Triluminos '
                 'Pro, XR Processor with AI, Google TV, 120Hz: '
                 'https://techstevehd.com/reviews/sony-bravia-5-xr50-series and '
                 'https://www.abt.com/Sony-BRAVIA-5-Mini-LED-TV-65-Inch-4K-Smart-with-Google-TV-K65XR50/p/221624.html; '
                 "'BRAVIA 5 Mini LED' and 'Google TV' badges visible in the listing's own photo"}],
 51: [{'b': 'The first Mini with a 1-inch 50MP CMOS sensor — a 24mm f/1.8 lens in a 249.9 g body, '
            'shooting 4K/60fps HDR and 4K/120fps slow motion in 10-bit D-Log M.',
       'h': 'A 1-inch sensor under 250 g',
       'img': 'images/full/p51.jpg',
       'source': 'DJI Mini 5 Pro spec sheet + user manual v1.0 (Sep 2025), via DroneTrader / '
                 "DroneRanker / Amateur Photographer reproductions of DJI's published data. NOTE: "
                 "DJI's own US product page 404s (verified by direct fetch 20 Nov 2026), so no "
                 'dji.com page copy was available.'},
      {'b': 'A forward-facing LiDAR unit backed by omnidirectional vision sensing detects '
            'obstacles in near-darkness, where purely optical sensing stops working.',
       'h': 'LiDAR nightscape sensing',
       'img': None,
       'source': "DJI Mini 5 Pro spec sheet, via DroneTrader / DroneRanker reproductions of DJI's "
                 'published data (forward LiDAR + omnidirectional vision, Nightscape)'},
      {'b': 'Up to 36 minutes on the standard battery — 52 minutes with the Plus battery — plus '
            '42GB of built-in storage and a 225° rolling gimbal for true vertical shots.',
       'h': '36 minutes, 42GB on board',
       'img': None,
       'source': 'DJI Mini 5 Pro spec sheet, via DroneTrader / Amateur Photographer reproductions '
                 "of DJI's published data"}],
 52: [{'b': 'The mini-sized, mega-capable Mini 3 Pro is just as powerful as it is portable — under '
            '249 g, regulation-friendly, and the safest in its series.',
       'h': 'Fly Mini, create big',
       'img': 'images/gallery/dji-mini-3-pro-g1.jpg',
       'source': 'dji.com/mini-3-pro meta description (exact quote, recorded in '
                 "dji-copy-2026-11-19.md §'Mini 3 Pro — page retired'); live product page retired, "
                 'redirects to support'},
      {'b': 'A 1/1.3-inch sensor shooting 4K/60fps video and 4K/30fps HDR, with 1080p/120fps slow '
            'motion and D-Cinelike colour.',
       'h': '1/1.3-inch sensor, 4K/60fps',
       'img': None,
       'source': 'dji-deep-study-2026-11-19.md §4 comparison table, Mini 3 Pro row'},
      {'b': 'Forward, backward and downward obstacle sensing with APAS 4.0 and Smart RTH, on DJI '
            'O3 transmission up to 12 km with a 1080p/30fps live feed.',
       'h': 'Tri-directional sensing, 12 km link',
       'img': None,
       'source': 'dji-deep-study-2026-11-19.md §4 comparison table, Mini 3 Pro row'}],
 53: [{'b': 'At less than 249 g, Mini 2 weighs about as much as an apple and fits in the palm of '
            "your hand — a foldable classic that's effortless to carry.",
       'h': 'Less than 249 g — fits in your palm',
       'img': 'images/full/p53.jpg',
       'source': "DJI Mini 2 published specs, via IGIDRONE (DJI-published figures); DJI's own Mini "
                 '2 page copy as quoted by retailers'},
      {'b': 'A 12MP camera with a 1/2.3-inch CMOS sensor and 24mm f/2.8 lens captures smooth '
            '4K/30fps video and 12MP stills, steadied by a 3-axis motorized gimbal.',
       'h': '4K camera on a 3-axis gimbal',
       'img': 'images/gallery/dji-mini-2-g4.jpg',
       'source': 'DJI Mini 2 published specs, via IGIDRONE (DJI-published figures)'},
      {'b': 'Up to 31 minutes of flight time and DJI OcuSync 2.0 HD video transmission up to 10 '
            'km, with Level 5 wind resistance and 4x digital zoom.',
       'h': '31 minutes, 10 km OcuSync 2.0',
       'img': None,
       'source': "DJI Mini 2 published specs, via IGIDRONE / retailer listings of DJI's official "
                 'figures'}],
 54: [{'b': 'The -LED model carries its own white-light LED, so the picture can stay in colour '
            'after dark instead of switching to black-and-white infrared.',
       'h': 'LED light for colour at night',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — HAC-HDW1209TLQP(-A)-LED '
                 '(photo-replace-2026-11-19.md, round 1)'},
      {'b': 'HDCVI carries high-definition video over the same coaxial cable as older analogue '
            'systems, and the eyeball mount is aimed by hand to cover the exact corner.',
       'h': 'HDCVI — HD video over coax',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — HAC-HDW1209TLQP(-A)-LED '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 55: [{'b': 'A 4MP eyeball camera with infrared night vision, so the same point stays covered '
            'around the clock.',
       'h': '4MP IR eyeball — day and night',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — HAC-T1A41P 4MP IR Eyeball, '
                 'discontinued HDCVI cameras (photo-replace-2026-11-19.md, round 1)'},
      {'b': 'The ball-and-socket eyeball turns by hand, so one camera can be pointed at a door, a '
            'counter or a corridor without moving the mount.',
       'h': 'Eyeball mount aims anywhere',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — HAC-T1A41P 4MP IR Eyeball '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 56: [{'b': 'The official Dahua datasheet lists a 2MP CMOS sensor at 1920 x 1080 with an F2.0 lens '
            '— full high-definition pictures on a sensible budget.',
       'h': '2MP Full HD — 1920 x 1080',
       'img': None,
       'source': "Official Dahua datasheet 'Eco Series | DH-HAC-T5E20', Rev 002.000 © 2023 — 2MP "
                 'CMOS, 1920x1080, F2.0, 20 m IR (round3/manifest.md)'},
      {'b': 'Infrared night vision rated at 20 m in the datasheet, so rooms, counters and '
            'corridors stay covered after the lights go out.',
       'h': '20 m IR for dark rooms',
       'img': None,
       'source': "Official Dahua datasheet 'Eco Series | DH-HAC-T5E20', Rev 002.000 © 2023 — 20 m "
                 'IR (round3/manifest.md)'}],
 57: [{'b': 'An IP dome camera that joins the network recorder over the LAN — the right pick for '
            'offices and shops already running IP camera systems.',
       'h': 'IP dome for network systems',
       'img': None,
       'source': 'Dahua official previous site previous.dahuasecurity.com — IPC-T1E29-A-IL '
                 '(photo-replace-2026-11-19.md, round 1)'},
      {'b': "The -IL in the model name is Dahua's Smart Illumination: the camera lights the scene "
            'only as much as the moment needs, instead of glowing all night.',
       'h': 'Smart illumination (-IL)',
       'img': None,
       'source': 'Dahua official previous site previous.dahuasecurity.com — IPC-T1E29-A-IL '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 58: [{'b': 'Two lights work together — infrared and white light — so night footage can stay in '
            'colour, with the camera choosing the light that fits the scene.',
       'h': 'Smart Dual Light — colour after dark',
       'img': None,
       'source': 'Official Dahua datasheet DH-IPC-B1E49-A-IL on materialfile.dahuasecurity.com '
                 "(Dahua's own CDN) (photo-replace-2026-11-19.md, round 1)"},
      {'b': 'A bullet body on a bracket, made for entrances, gates and yards that need watching '
            'after dark.',
       'h': 'Bullet for gates and yards',
       'img': None,
       'source': 'Official Dahua datasheet DH-IPC-B1E49-A-IL on materialfile.dahuasecurity.com '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 59: [{'b': '2MP Full HD (1920×1080 at 30 fps) with Smart IR up to 30 m — clear in daylight and in '
            'complete darkness.',
       'h': 'Full HD with 30 m night vision',
       'img': 'images/gallery/tiandy-tc-321-2mp-g1.jpg',
       'source': 'Tiandy official spec sheet — TC-C321N AK series 2MP bullet (Spec '
                 'AK/I3W/E/Y/2.8mm/V2.0)'},
      {'b': 'Weatherproof IP67 housing, PoE power and a built-in microphone — video with sound, '
            'indoors or out.',
       'h': 'IP67 and a built-in mic',
       'img': 'images/gallery/tiandy-tc-321-2mp-g2.jpg',
       'source': 'Tiandy official spec sheet — TC-C321N AK series 2MP bullet (Spec '
                 'AK/I3W/E/Y/2.8mm/V2.0)'},
      {'b': 'S+265 / H.265 compression keeps the Full HD stream small on disk, with 120 dB WDR '
            'against harsh light.',
       'h': 'Light on storage, heavy on detail',
       'img': 'images/gallery/tiandy-tc-321-2mp-g3.jpg',
       'source': 'Tiandy official spec sheet — TC-C321N AK series 2MP bullet (Spec '
                 'AK/I3W/E/Y/2.8mm/V2.0)'}],
 60: [],
 61: [{'b': 'The E27 base fits a standard bulb holder, so the camera mounts where a bulb would — '
            'no drilling, no cables to run.',
       'h': 'Screws into a light socket — no wiring at all',
       'img': None,
       'source': 'AK Khan product record — name/description (V380 E27 bulb-socket WiFi camera)'},
      {'b': 'A bulb-socket WiFi camera you check from your phone — simple room monitoring without '
            'any wiring.',
       'h': 'Room monitoring from your phone',
       'img': None,
       'source': 'AK Khan product record — name/description (V380 E27 bulb-socket WiFi camera)'}],
 62: [{'b': 'A single-lens WiFi camera that works with the iCSee app — open your phone and the '
            'room is there.',
       'h': 'One lens, one app, straightforward monitoring',
       'img': None,
       'source': 'AK Khan product record — name/description (iCSee V1 Single Lens)'},
      {'b': 'Made for straightforward home and shop monitoring from your phone, with no recorder '
            'or extra hardware.',
       'h': 'For homes and shops that keep it simple',
       'img': None,
       'source': 'AK Khan product record — name/description (iCSee V1 Single Lens)'}],
 63: [{'b': 'A 16-channel compact 1U NVR that takes IP cameras up to 12MP, with HDMI output up to '
            '3840×2160.',
       'h': '16 channels of 4K-ready recording',
       'img': 'images/gallery/dahua-dhi-nvr4116hs-4ks3-g1.jpg',
       'source': 'Dahua official datasheet — DHI-NVR4116HS-4KS3, Rev 002.000'},
      {'b': 'Smart H.265+ / H.264+ keeps 16 channels light on disk, with one SATA bay holding up '
            'to 20 TB.',
       'h': 'Smart compression, smarter storage',
       'img': 'images/gallery/dahua-dhi-nvr4116hs-4ks3-g2.jpg',
       'source': 'Dahua official datasheet — DHI-NVR4116HS-4KS3, Rev 002.000'},
      {'b': 'AI by Recorder with 4-channel SMD Plus — the recorder itself tells people and '
            'vehicles apart, so you search less.',
       'h': 'AI that watches with you',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR4116HS-4KS3, Rev 002.000'}],
 64: [{'b': 'An 8-channel compact 1U NVR for IP cameras up to 12MP — every camera recorded in one '
            'place.',
       'h': '8 channels, one compact box',
       'img': 'images/gallery/dahua-dhi-nvr2108hs-4ks3-g1.jpg',
       'source': 'Dahua official datasheet — DHI-NVR2108HS-4KS3, Rev 002.000'},
      {'b': 'HDMI output up to 3840×2160 with Smart H.265+ compression, and a SATA bay for local '
            'recording storage.',
       'h': '4K display, efficient storage',
       'img': 'images/gallery/dahua-dhi-nvr2108hs-4ks3-g2.jpg',
       'source': 'Dahua official datasheet — DHI-NVR2108HS-4KS3, Rev 002.000'},
      {'b': '4-channel SMD Plus on the recorder cuts false alarms by telling people and vehicles '
            'apart from the rest.',
       'h': 'AI motion detection on board',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR2108HS-4KS3, Rev 002.000'}],
 65: [],
 66: [{'b': 'An 8-channel compact 1U NVR for IP cameras up to 8MP, with Smart H.265+ keeping '
            'recordings light on disk.',
       'h': '8 channels of H.265 recording',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR1108HS-S3/H, Rev 001.001 / Rev 002.000'},
      {'b': 'One SATA bay holds up to 8 TB, with HDMI and VGA outputs — a straightforward recorder '
            'for homes and small shops.',
       'h': 'Simple, reliable, one hard drive',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR1108HS-S3/H, Rev 001.001 / Rev 002.000'},
      {'b': 'Decodes 1 channel of 8MP at 30 fps, or 4 channels of 1080p — smooth playback of the '
            'cameras it records.',
       'h': 'Decodes what it records',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR1108HS-S3/H, Rev 001.001 / Rev 002.000'}],
 67: [{'b': 'Eight built-in PoE ports power and connect eight cameras over a single cable each — '
            'no separate power supplies.',
       'h': '8 cameras, 8 PoE ports — one cable each',
       'img': 'images/gallery/tiandy-tc-r3108-g1.jpg',
       'source': 'Tiandy TC-R3108 spec sheet via authorised reseller listings (tess.co.in / '
                 'runaitechnologies)'},
      {'b': 'Takes cameras up to 6MP and shows them on HDMI up to 4K, with S+265 compression '
            'keeping storage light.',
       'h': 'Up to 6MP cameras, 4K on screen',
       'img': None,
       'source': 'Tiandy TC-R3108 spec sheet via authorised reseller listings (tess.co.in / '
                 'runaitechnologies)'},
      {'b': 'One SATA bay holds up to 6 TB, and four channels play back in sync for quick review.',
       'h': 'One hard drive, four cameras at once',
       'img': None,
       'source': 'Tiandy TC-R3108 spec sheet via authorised reseller listings (tess.co.in / '
                 'runaitechnologies)'}],
 68: [{'b': 'Four built-in PoE ports: each camera takes power and picture over one cable, straight '
            'into the recorder.',
       'h': '4 cameras, 4 PoE ports — plug and play',
       'img': 'images/gallery/tiandy-tc-r3104-g1.jpg',
       'source': 'Tiandy TC-R3104 spec sheet via authorised reseller listings (tess.co.in / '
                 'runaitechnologies)'},
      {'b': 'One SATA bay holds up to 6 TB, with S+265 / H.265 compression and 4-channel sync '
            'playback.',
       'h': 'Compact recording for small sites',
       'img': None,
       'source': 'Tiandy TC-R3104 spec sheet via authorised reseller listings (tess.co.in / '
                 'runaitechnologies)'}],
 69: [{'b': 'A 20-channel NVR for larger installations — warehouses, schools and sites with many '
            'cameras on one system.',
       'h': '20 channels for the bigger site',
       'img': 'images/gallery/tiandy-nvr-tc-r3120-g1.jpg',
       'source': 'Tiandy TC-R3120 spec sheet via authorised reseller listings (runaitechnologies / '
                 'mmsrilanka)'},
      {'b': 'Takes cameras up to 8MP and outputs HDMI up to 4K, with S+265 compression and '
            '16-channel sync playback.',
       'h': 'Up to 8MP cameras, 4K display',
       'img': 'images/gallery/tiandy-nvr-tc-r3120-g2.jpg',
       'source': 'Tiandy TC-R3120 spec sheet via authorised reseller listings (runaitechnologies / '
                 'mmsrilanka)'},
      {'b': 'One SATA bay holds up to 10 TB of recordings from the whole camera system.',
       'h': 'Room for 10 TB of recordings',
       'img': 'images/gallery/tiandy-nvr-tc-r3120-g3.jpg',
       'source': 'Tiandy TC-R3120 spec sheet via authorised reseller listings (runaitechnologies / '
                 'mmsrilanka)'}],
 70: [{'b': 'Wi-Fi 4 (802.11n) at up to 300 Mbps on 2.4 GHz, with two 5 dBi external antennas for '
            'steady coverage around the house.',
       'h': 'N300 Wi-Fi for the whole home',
       'img': 'images/gallery/ruijie-rg-ew300n-n300-wireless-smart-router-g2.jpg',
       'source': 'Ruijie RG-EW300N official datasheet (ruijie.com): '
                 'https://eo-sgp-cos.ruijie.com/Document/pdf/2026/9/8/RG-EW300N_Datasheet_Official_2026-09-08.pdf'},
      {'b': 'Works as a router, repeater, access point or WISP, so the same box can extend an '
            'existing network or share a wireless ISP connection.',
       'h': 'Four modes in one box',
       'img': 'images/gallery/ruijie-rg-ew300n-n300-wireless-smart-router-g1.jpg',
       'source': 'Ruijie RG-EW300N official datasheet (ruijie.com): '
                 'https://eo-sgp-cos.ruijie.com/Document/pdf/2026/9/8/RG-EW300N_Datasheet_Official_2026-09-08.pdf'},
      {'b': 'Set up and manage it from the Reyee Router app or Ruijie Cloud, with lifetime free '
            'cloud management, parental control and guest Wi-Fi.',
       'h': 'Managed from your phone, free for life',
       'img': None,
       'source': 'Ruijie RG-EW300N official datasheet (ruijie.com): '
                 'https://eo-sgp-cos.ruijie.com/Document/pdf/2026/9/8/RG-EW300N_Datasheet_Official_2026-09-08.pdf'}],
 71: [{'b': 'Four 5 dBi external antennas with built-in signal amplifiers push N300 Wi-Fi (up to '
            '300 Mbps, 2.4 GHz) further through walls and across rooms.',
       'h': 'Stronger signal, four antennas',
       'img': 'images/gallery/ruijie-rg-ew300-pro-g2.jpg',
       'source': 'Ruijie RG-EW300 PRO official datasheet (ruijie.com): '
                 'https://eo-sgp-cos.ruijie.com/Document/pdf/2026/9/8/RG-EW300%20PRO_Datasheet_Official_2026-09-08.pdf'},
      {'b': 'Switches between router, AP, repeater and WISP modes, with 1 WAN and 3 LAN Fast '
            'Ethernet ports for wired PCs, TVs and printers.',
       'h': 'Router, repeater, access point or WISP',
       'img': 'images/gallery/ruijie-rg-ew300-pro-g1.jpg',
       'source': 'Ruijie RG-EW300 PRO official datasheet (ruijie.com): '
                 'https://eo-sgp-cos.ruijie.com/Document/pdf/2026/9/8/RG-EW300%20PRO_Datasheet_Official_2026-09-08.pdf'},
      {'b': 'Manage it from the Reyee Router app or Ruijie Cloud — free for life — and Ruijie '
            'backs the router with a three-year warranty.',
       'h': 'Free cloud management, 3-year warranty',
       'img': None,
       'source': 'Ruijie RG-EW300 PRO official datasheet (ruijie.com): '
                 'https://eo-sgp-cos.ruijie.com/Document/pdf/2026/9/8/RG-EW300%20PRO_Datasheet_Official_2026-09-08.pdf'}],
 72: [{'b': 'Up to 300 Mbps on 2.4 GHz (Wi-Fi 4, 802.11n) — enough for HD streaming, online gaming '
            'and large downloads around the home.',
       'h': 'N300 speed for everyday home Wi-Fi',
       'img': 'images/gallery/tp-link-tl-wr840n-g1.jpg',
       'source': 'TP-Link TL-WR840N official product page (tp-link.com): '
                 'https://www.tp-link.com/au/home-networking/wifi-router/tl-wr840n/'},
      {'b': 'Router, access point, range extender and WISP modes cover a new connection, a dead '
            'zone or a shared wireless link with one box.',
       'h': 'Four ways to use it',
       'img': None,
       'source': 'TP-Link TL-WR840N official product page (tp-link.com): '
                 'https://www.tp-link.com/au/home-networking/wifi-router/tl-wr840n/'},
      {'b': 'One 10/100 Mbps WAN port and four 10/100 Mbps LAN ports for wired devices, plus a '
            'separate 2.4 GHz guest network for visitors.',
       'h': 'Wired ports and a guest network',
       'img': 'images/gallery/tp-link-tl-wr840n-g2.jpg',
       'source': 'TP-Link TL-WR840N official product page (tp-link.com): '
                 'https://www.tp-link.com/au/home-networking/wifi-router/tl-wr840n/'}],
 73: [{'b': 'The N300 designation means up to 300 Mbps wireless on the 2.4 GHz band (802.11n) — '
            'the everyday speed for browsing, streaming and video calls.',
       'h': 'N300 Wi-Fi — 300 Mbps',
       'img': 'images/gallery/tenda-n300-wireless-router-g2.jpg',
       'source': 'Tenda N300 Wireless Router — N300 designation: 300 Mbps, 802.11n, 2.4 GHz (model '
                 'designation itself)'},
      {'b': 'Two external antennas, as shown in the listing photo, spread Wi-Fi across the rooms '
            'of a home or small shop.',
       'h': 'Two antennas, simple home coverage',
       'img': None,
       'source': 'Two external antennas visible in listing photo '
                 'images/gallery/tenda-n300-wireless-router-g2.jpg'}],
 74: [{'b': '3MP (2304×1296) live monitoring with 0–355° pan and −5–80° tilt — one camera covers '
            'every corner of the room.',
       'h': '3MP 2K that turns to follow the room',
       'img': 'images/scene/imou-ranger-2-pan.jpg',
       'source': 'IMOU official datasheet — Ranger 2 3MP, Rev 001.001 (imoulife.com)'},
      {'b': 'Human detection finds people in the frame and alerts your phone — not every curtain '
            'moving in the draught.',
       'h': 'Human detection, fewer false alarms',
       'img': None,
       'source': 'IMOU official datasheet — Ranger 2 3MP, Rev 001.001 (imoulife.com)'},
      {'b': 'Infrared night vision up to 10 m and auto-cruise that sweeps the room or moves '
            'between favourite points.',
       'h': 'Night vision to 10 m, auto-cruise patrols',
       'img': 'images/scene/imou-ranger-2-night.jpg',
       'source': 'IMOU official datasheet — Ranger 2 3MP, Rev 001.001 (imoulife.com)'}],
 75: [{'b': '3MP (2304×1296) pan-and-tilt coverage — 355° pan, −5–80° tilt — with human and pet '
            'detection that alerts your phone.',
       'h': '3MP 2K with human and pet detection',
       'img': 'images/scene/imou-ranger-2-pro-detect.jpg',
       'source': 'IMOU official datasheet — Ranger 2 Pro 3MP, Rev 001.001 '
                 '(static-website.imou.com)'},
      {'b': 'Smart tracking turns the camera to follow moving people and pets, so the action stays '
            'in frame.',
       'h': 'Smart tracking follows the movement',
       'img': 'images/scene/imou-ranger-2-pro-tracking.jpg',
       'source': 'IMOU official datasheet — Ranger 2 Pro 3MP, Rev 001.001 '
                 '(static-website.imou.com)'},
      {'b': 'A touch button lets family video-call your app, and Smart Full-Colour Night Vision '
            'keeps night footage in colour — with Wi-Fi 6 for a steady stream.',
       'h': 'One-touch call and full-colour night vision',
       'img': 'images/scene/imou-ranger-2-pro-call.jpg',
       'source': 'IMOU official datasheet — Ranger 2 Pro 3MP, Rev 001.001 '
                 '(static-website.imou.com)'}],
 76: [{'b': 'A compact fixed mini dome that sits quietly on a ceiling — full coverage without a '
            'bulky camera in the room.',
       'h': 'Mini dome, small and discreet',
       'img': 'images/gallery/dahua-n22al12-g1.jpg',
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N22AL12 own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A 2MP fixed-lens IP camera: point it once, and it holds the same view on the network, '
            'day after day.',
       'h': '2MP fixed-lens network camera',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N22AL12 own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 77: [{'b': 'This dome feeds a public-viewing monitor straight over HDMI, so the live picture '
            "shows on a screen without opening the recorder's menu.",
       'h': 'HDMI out — live view on a monitor',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — IPC-HDBW5231E-ZE-HDMI, page '
                 'lists EN-ZE-HDMI as its external model (photo-replace-2026-11-19.md, round 1)'},
      {'b': 'The -ZE in the model name is a motorised vari-focal zoom: the view is widened or '
            'tightened from the screen, instead of climbing a ladder to turn the lens.',
       'h': 'Motorised zoom (-ZE)',
       'img': 'images/gallery/dahua-dh-ipc-hdbw5231en-ze-hdmi-g1.jpg',
       'source': 'Dahua official product page dahuasecurity.com — IPC-HDBW5231E-ZE-HDMI '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 78: [{'b': 'Night Color technology keeps the night picture in colour, so clothes, cars and signs '
            'stay recognisable after dark.',
       'h': 'Night Color — colour in the dark',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — IPC-HDBW4239R-ASE, page lists '
                 'RN-ASE (photo-replace-2026-11-19.md, round 1)'},
      {'b': 'ePoE carries power and data over a single network cable across longer runs, so the '
            'dome can sit far from the recorder without a separate power point nearby.',
       'h': 'ePoE — power and video on one long cable',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — IPC-HDBW4239R-ASE '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 79: [{'b': 'Night Color technology keeps the night picture in colour, and the bullet body points '
            'it down a gate, a street or a yard.',
       'h': 'Night Color bullet — colour after dark',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — IPC-HFW4239T-ASE, page lists '
                 'TN-ASE (photo-replace-2026-11-19.md, round 1)'},
      {'b': 'ePoE carries power and data over a single network cable across longer runs, so the '
            'bullet can sit far from the recorder without a separate power point nearby.',
       'h': 'ePoE — power and video on one long cable',
       'img': None,
       'source': 'Dahua official product page dahuasecurity.com — IPC-HFW4239T-ASE '
                 '(photo-replace-2026-11-19.md, round 1)'}],
 80: [{'b': 'Built for hazardous sites — fuel stations, factories, chemical stores — where the '
            'housing must contain any spark so it can never reach the air outside.',
       'h': 'Explosion-protected housing',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — DH-EPC230U own page, infobox '
                 'image 3500x3500 (photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A 2MP infrared network bullet: night vision in a rugged metal body made for places '
            'ordinary cameras cannot go.',
       'h': 'IR bullet for harsh sites',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — DH-EPC230U own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 81: [{'b': 'Made for air that eats ordinary cameras — coastal sites and industrial halls — with a '
            'stainless housing that resists corrosion.',
       'h': 'Corrosion-resistant — stainless housing',
       'img': 'images/gallery/dahua-dh-ipc-hdbw8232en-z-sl-g2.jpg',
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — DH-IPC-HDBW8232E-Z-SL own page; '
                 'image pixel-matched to the EN-Z-SL datasheet hero (photo-replace-2026-11-19.md, '
                 'round 2)'},
      {'b': 'The -Z in the model name is a vari-focal lens: the focal length adjusts so the camera '
            'frames exactly the area that matters, wide or tight.',
       'h': 'Vari-focal zoom (-Z)',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — DH-IPC-HDBW8232E-Z-SL own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 82: [{'b': 'A dual-sensor dome — two 2MP sensors in a single housing — so one mount watches two '
            'directions at once.',
       'h': 'Two sensors, two views in one dome',
       'img': None,
       'source': 'Own datasheet p.1 hero (DahuaWiki-hosted) — DH-IPC-HDBW4231FN-E2-M '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'Infrared night vision in a dome that covers what two separate cameras would, from a '
            'single ceiling mount.',
       'h': 'IR dome for wide coverage',
       'img': None,
       'source': 'Own datasheet p.1 hero (DahuaWiki-hosted) — DH-IPC-HDBW4231FN-E2-M '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 83: [{'b': 'A Starlight sensor keeps the picture in colour when the light is too low for an '
            'ordinary camera — dusk, dim corridors, street light alone.',
       'h': 'Starlight — colour in very low light',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N24CL52 own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A 2.8 mm fixed lens gives a wide view of the room, and ePoE carries power and video '
            'on a single network cable.',
       'h': '2.8 mm wide view, one cable with ePoE',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N24CL52 own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 84: [{'b': 'A Starlight sensor keeps the picture in colour when the light is too low for an '
            'ordinary camera — dusk, dim yards, street light alone.',
       'h': 'Starlight — colour in very low light',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N24CB33 own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A 3.6 mm fixed lens looks a little narrower than a 2.8 mm, so it frames a door or a '
            'gate neatly, with IR night vision and ePoE on one cable.',
       'h': '3.6 mm mini bullet for doors and gates',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N24CB33 own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 85: [{'b': 'A Starlight sensor keeps the picture in colour when the light is too low for an '
            'ordinary camera — dusk, dim rooms, a single lamp.',
       'h': 'Starlight — colour in very low light',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N24CG52 own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A fixed-lens eyeball on a ball mount: turn it by hand to the exact corner, with IR '
            'night vision and ePoE on one cable.',
       'h': 'Eyeball — aim it by hand',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N24CG52 own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 86: [{'b': 'A Starlight sensor keeps the picture in colour when the light is too low for an '
            'ordinary camera — dusk, dim yards, street light alone.',
       'h': 'Starlight — colour in very low light',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N25CB5Z own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A vari-focal lens adjusts the view from wide to tight, so one bullet can cover a yard '
            'or focus on a gate, with IR night vision and ePoE on one cable.',
       'h': 'Vari-focal bullet — zoom to fit the scene',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N25CB5Z own page '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'The gallery shows the card slot inside the housing, so footage can also be stored in '
            'the camera itself on a memory card.',
       'h': 'On-board card slot',
       'img': 'images/gallery/dahua-n25cb5z-g2.jpg',
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N25CB5Z own page; card slot '
                 "visible in the product's own gallery image dahua-n25cb5z-g2.jpg"}],
 87: [{'b': 'A Starlight sensor keeps the picture in colour when the light is too low for an '
            'ordinary camera — dusk, dim rooms, a single lamp.',
       'h': 'Starlight — colour in very low light',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N25CL5Z own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A vari-focal lens adjusts the view from wide to tight, so one dome can cover a hall '
            'or focus on a till, with IR night vision and ePoE on one cable.',
       'h': 'Vari-focal dome — zoom to fit the scene',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N25CL5Z own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 88: [{'b': 'A 4K eyeball camera: the picture holds four times the detail of Full HD, so faces and '
            'number plates stay readable from further away.',
       'h': '4K detail — four times Full HD',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N84CG52 own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2)'},
      {'b': 'A 2.8 mm fixed lens gives a wide view of the room, with infrared night vision and '
            'power plus video on a single ePoE cable.',
       'h': '2.8 mm wide view, IR and ePoE',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N84CG52 own page '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 89: [{'b': 'The official datasheet lists this mini dome at 8 MP (3840 x 2160) — true 4K '
            'resolution, so fine detail survives even when the picture is zoomed in.',
       'h': 'True 4K — 8 MP, 3840 x 2160',
       'img': None,
       'source': "Official Dahua datasheet p.1 — 'Pro Series | N84CL52 — 4K IR 2.8 mm ePoE Mini "
                 "Dome — 8 MP (3840x2160), 2.8 mm Fixed Lens, ePoE' (photo-replace-2026-11-19.md, "
                 'round 2)'},
      {'b': 'A 2.8 mm fixed lens gives a wide view of the room, with infrared night vision and '
            'power plus video on a single ePoE cable.',
       'h': '2.8 mm wide view, IR and ePoE',
       'img': None,
       'source': 'Official Dahua datasheet p.1 — N84CL52, 2.8 mm Fixed Lens, ePoE '
                 '(photo-replace-2026-11-19.md, round 2)'}],
 90: [{'b': 'A 128-channel Intelligent Video Surveillance Server — one box that runs a whole '
            "site's cameras and AI.",
       'h': '128 channels on one intelligent server',
       'img': None,
       'source': 'Dahua official datasheet — DHI-IVSS7008-1T, Rev 001.001'},
      {'b': 'Face recognition on up to 4 video-stream channels, against a database of up to '
            '100,000 faces.',
       'h': 'Face recognition built in',
       'img': None,
       'source': 'Dahua official datasheet — DHI-IVSS7008-1T, Rev 001.001'},
      {'b': 'Eight SATA bays hold up to 10 TB each, with RAID 0/1/5/10 and 400 Mbps incoming '
            'bandwidth.',
       'h': '80 TB of storage, RAID protected',
       'img': None,
       'source': 'Dahua official datasheet — DHI-IVSS7008-1T, Rev 001.001'}],
 91: [{'b': 'A 256-channel Intelligent Video Surveillance Server with a quad-core processor for '
            'large, demanding sites.',
       'h': '256 channels of intelligent surveillance',
       'img': None,
       'source': 'Dahua official datasheet — DHI-IVSS7016DR-4T, Rev 001.001'},
      {'b': 'Face recognition on up to 16 video-stream channels, against a database of up to '
            '100,000 faces.',
       'h': 'Face recognition at scale',
       'img': None,
       'source': 'Dahua official datasheet — DHI-IVSS7016DR-4T, Rev 001.001'},
      {'b': 'Sixteen SAS/SATA bays hold up to 10 TB each, with RAID 0/1/5/10, redundant power and '
            '512 Mbps incoming bandwidth.',
       'h': '160 TB, redundant power, RAID',
       'img': None,
       'source': 'Dahua official datasheet — DHI-IVSS7016DR-4T, Rev 001.001'}],
 92: [{'b': 'A 16-channel 1U 4K NVR with 16 built-in PoE ports, so every camera takes power and '
            'picture over one cable.',
       'h': '16 channels, 16 PoE ports — cameras plug straight in',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR4216-16P-I (Analytics+ series)'},
      {'b': 'Face recognition on up to 2 channels and perimeter protection on up to 4, with a '
            '20,000-face database.',
       'h': 'Analytics+ that sees people and faces',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR4216-16P-I (Analytics+ series)'},
      {'b': 'Ports 1–8 support ePoE/EoC, reaching cameras up to 800 m away over a single cable.',
       'h': 'Long reach on the first eight ports',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR4216-16P-I (Analytics+ series)'}],
 93: [{'b': 'A 16-channel 1U 16PoE WizMind NVR — 4K recording with 320 Mbps incoming bandwidth for '
            'busy camera systems.',
       'h': 'WizMind AI on 16 PoE channels',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR5216-16P-I, Rev 001.001'},
      {'b': 'Face recognition on up to 4 channels at 24 face images per second, against a database '
            'of up to 100,000 faces.',
       'h': 'Face recognition on four channels',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR5216-16P-I, Rev 001.001'},
      {'b': 'Ports 1–8 support ePoE/EoC, so cameras up to 800 m away connect over a single cable.',
       'h': 'ePoE reach up to 800 m',
       'img': None,
       'source': 'Dahua official datasheet — DHI-NVR5216-16P-I, Rev 001.001'}],
 94: [{'b': 'A 16-channel network video recorder that records in 4K — sixteen cameras on one box, '
            'every stream stored in full detail.',
       'h': '16 channels of 4K recording',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N54B3P own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2, H2)'},
      {'b': 'ePoE ports power the cameras over the same network cable that carries their video, so '
            'each camera needs only one cable back to the recorder.',
       'h': 'ePoE recorder — power for the cameras',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N54B3P own page '
                 '(photo-replace-2026-11-19.md, round 2, H2)'}],
 95: [{'b': 'A 16-channel network video recorder that records in 4K — sixteen cameras on one box, '
            'every stream stored in full detail.',
       'h': '16 channels of 4K recording',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52B3P own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2, H2)'},
      {'b': 'A slim 1U-high recorder that fits a standard rack shelf, with ePoE ports that power '
            'the cameras over the same cable as their video.',
       'h': 'Slim 1U box, ePoE inside',
       'img': 'images/gallery/dahua-n52b3p-g2.jpg',
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52B3P own page; rear panel '
                 "with PoE ports visible in the product's own gallery image dahua-n52b3p-g2.jpg"}],
 96: [{'b': 'A 32-channel network video recorder that records in 4K — the recorder for large '
            'shops, warehouses and multi-floor buildings.',
       'h': '32 channels of 4K recording',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N54B5N own page '
                 '(photo-replace-2026-11-19.md, round 2, H2)'},
      {'b': 'Two network ports let the camera network and the viewing network run separately, so '
            'camera traffic never crowds the office network.',
       'h': 'Dual NIC — two network ports',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N54B5N own page '
                 '(photo-replace-2026-11-19.md, round 2, H2)'}],
 97: [{'b': 'A 32-channel network video recorder that records in 4K — the recorder for large '
            'shops, warehouses and multi-floor buildings.',
       'h': '32 channels of 4K recording',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52B5P own page, infobox image '
                 '(photo-replace-2026-11-19.md, round 2, H2)'},
      {'b': 'Thirty-two channels in a slim 1U-high box, with ePoE ports that power the cameras '
            'over the same cable as their video.',
       'h': 'Slim 1U box, ePoE inside',
       'img': 'images/gallery/dahua-n52b5p-g2.jpg',
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52B5P own page; rear panel '
                 "with PoE ports visible in the product's own gallery image dahua-n52b5p-g2.jpg"}],
 98: [{'b': 'An 8-channel network video recorder that records in 4K — the right size for a home or '
            'a small shop with a handful of cameras.',
       'h': '8 channels of 4K recording — the compact recorder',
       'img': None,
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52B2P own page; own datasheet '
                 'p.1 hero (photo-replace-2026-11-19.md, round 2, H2)'},
      {'b': 'A slim 1U-high recorder with ePoE ports that power the cameras over the same cable as '
            'their video — one cable per camera, nothing else to wire.',
       'h': 'Slim 1U box, ePoE inside',
       'img': 'images/gallery/dahua-n52b2p-g2.jpg',
       'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52B2P own page; rear panel '
                 "with PoE ports visible in the product's own gallery image dahua-n52b2p-g2.jpg"}],
 99: [{'b': 'A Video Management System server with DSS Express preinstalled, managing up to 512 IP '
            'cameras from one box.',
       'h': 'DSS Express — 512 cameras, one server',
       'img': None,
       'source': 'Dahua official datasheet — DHI-DSS4004-S2, Rev 001.001'},
      {'b': 'Real-time face recognition on up to 64 channels per overview, with 36-channel sync '
            'playback.',
       'h': 'Face recognition across the site',
       'img': None,
       'source': 'Dahua official datasheet — DHI-DSS4004-S2, Rev 001.001'},
      {'b': 'Access control and video intercom integrate with the same system — one platform for '
            'the whole site.',
       'h': 'Security beyond cameras',
       'img': None,
       'source': 'Dahua official datasheet — DHI-DSS4004-S2, Rev 001.001'}],
 100: [{'b': 'A Video Management System server with DSS Pro preinstalled: up to 512 IP devices and '
             '2,000 video channels per server.',
        'h': 'DSS Pro — 2,000 channels per server',
        'img': None,
        'source': 'Dahua official datasheet — DHI-DSS7016DR-S2, Rev 001.002'},
       {'b': 'Fifteen hot-plug HDD bays hold up to 200 TB, with RAID 0/1/5/6/10 and 700 Mbps video '
             'in, out and storage.',
        'h': '200 TB of hot-plug storage',
        'img': None,
        'source': 'Dahua official datasheet — DHI-DSS7016DR-S2, Rev 001.002'},
       {'b': 'A 7-inch HD LCD on the front panel shows the system at a glance, in a 3U rack-mount '
             'chassis.',
        'h': 'A screen on the box itself',
        'img': None,
        'source': 'Dahua official datasheet — DHI-DSS7016DR-S2, Rev 001.002'}],
 101: [{'b': 'A 128-channel Super 4K NVR with 384 Mbps incoming bandwidth — one box for the '
             'largest camera systems.',
        'h': '128 channels of Super 4K recording',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-128-4KS2, Rev 001.008'},
       {'b': 'Eight SATA III bays hold up to 10 TB each, with RAID 0/1/5/6/10/50/60 and N+M hot '
             'standby.',
        'h': '80 TB across eight SATA bays',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-128-4KS2, Rev 001.008'},
       {'b': 'Two HDMI outputs up to 3840×2160 can show different sources, plus a VGA output — and '
             'SMD+ on 32 channels.',
        'h': 'Two 4K HDMI outputs, different sources',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-128-4KS2, Rev 001.008'}],
 102: [{'b': 'A 64-channel Super 4K NVR with 384 Mbps incoming bandwidth and cameras up to 12MP.',
        'h': '64 channels of Super 4K recording',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-64-4KS2, Rev 001.010'},
       {'b': 'Eight SATA III bays with RAID 0/1/5/6/10/50/60, and SMD+ on 32 channels to cut false '
             'alarms.',
        'h': 'Eight SATA bays, full RAID',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-64-4KS2, Rev 001.010'},
       {'b': 'Two HDMI outputs up to 3840×2160 showing different sources, plus VGA — the control '
             'room sees more at once.',
        'h': 'Two 4K HDMI outputs',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-64-4KS2, Rev 001.010'}],
 103: [{'b': 'A 32-channel Super 4K NVR with 384 Mbps incoming bandwidth and IP cameras up to '
             '12MP.',
        'h': '32 channels of Super 4K recording',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-32-4KS2'},
       {'b': 'Eight SATA bays with RAID 0/1/5/6/10/50/60 and N+M hot standby — recordings stay '
             'safe if a drive fails.',
        'h': 'Eight SATA bays, enterprise RAID',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-32-4KS2'},
       {'b': 'Two HDMI outputs up to 3840×2160 plus VGA, with ONVIF support for third-party '
             'cameras.',
        'h': '4K display on two HDMI outputs',
        'img': None,
        'source': 'Dahua official datasheet — DHI-NVR6A08-32-4KS2'}],
 104: [{'b': 'A 24-channel network video recorder that records in 4K — the middle-size recorder '
             'for shops and offices with cameras on every floor.',
        'h': '24 channels of 4K recording',
        'img': None,
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N54A4P own page, infobox image '
                  '(photo-replace-2026-11-19.md, round 2, H2)'},
       {'b': 'A deeper 1.5U-high chassis for a 24-camera system, with room for the storage and '
             'cooling a bigger job needs.',
        'h': '1.5U recorder for bigger jobs',
        'img': 'images/gallery/dahua-n54a4p-g2.jpg',
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N54A4P own page; rear panel '
                  "visible in the product's own gallery image dahua-n54a4p-g2.jpg"}],
 105: [{'b': 'A 24-channel network video recorder that records in 4K — the middle-size recorder '
             'for shops and offices with cameras on every floor.',
        'h': '24 channels of 4K recording',
        'img': None,
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52A4P own page, infobox image '
                  '(photo-replace-2026-11-19.md, round 2, H2)'},
       {'b': 'Twenty-four channels in a slim 1U-high box that fits a standard rack shelf — big '
             'capacity without a big box.',
        'h': '24 channels in a slim 1U box',
        'img': 'images/gallery/dahua-n52a4p-g2.jpg',
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N52A4P own page; rear panel '
                  "visible in the product's own gallery image dahua-n52a4p-g2.jpg"}],
 106: [{'b': 'A 16-channel network video recorder that records in 4K — sixteen cameras on one box, '
             'every stream stored in full detail.',
        'h': '16 channels of 4K recording',
        'img': None,
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N42B3P own page; front-panel '
                  'photo from its own wiki page (photo-replace-2026-11-19.md, round 2, H2)'},
       {'b': 'A slim 1U-high recorder that fits a standard rack shelf — sixteen 4K channels '
             'without a big box.',
        'h': 'Slim 1U box for sixteen cameras',
        'img': 'images/gallery/dahua-n42b3p-g2.jpg',
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N42B3P own page; rear panel '
                  "visible in the product's own gallery image dahua-n42b3p-g2.jpg"}],
 107: [{'b': 'An 8-channel network video recorder that records in 4K — the right size for a home '
             'or a small shop with a handful of cameras.',
        'h': '8 channels of 4K recording — the small-site recorder',
        'img': None,
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N42B2P own page; own datasheet '
                  'p.1 hero (photo-replace-2026-11-19.md, round 2, H2)'},
       {'b': 'A compact 1U-high recorder that fits a standard rack shelf — small-site recording '
             'without a big box.',
        'h': 'Compact 1U box',
        'img': None,
        'source': 'DahuaWiki (Dahua Technology USA official wiki) — N42B2P own page '
                  '(photo-replace-2026-11-19.md, round 2, H2)'}]}
SHOWPIECE = {10: 'images/hero-dark/hikvision-2mp-dome-camera.jpg',
 11: 'images/hero-dark/hikvision-5mp-bullet-camera.jpg',
 12: 'images/hero-dark/dahua-2mp-dome-camera.jpg',
 13: 'images/hero-dark/dahua-5mp-bullet-camera.jpg',
 14: 'images/hero-dark/tiandy-5mp-camera.jpg',
 15: 'images/hero-dark/tiandy-ip-camera.jpg',
 16: 'images/gallery/ezviz-indoor-camera-g3.jpg',
 17: 'images/gallery/ezviz-outdoor-camera-g2.jpg',
 18: 'images/hero-dark/imou-ranger-series.jpg',
 19: 'images/hero-dark/v380-pro-wifi-camera.jpg',
 20: 'images/gallery/ruijie-wifi-router-g2.jpg',
 21: 'images/hero-dark/ruijie-access-point.jpg',
 22: 'images/hero-dark/tp-link-archer-router.jpg',
 23: 'images/hero-dark/tp-link-wifi-access-point.jpg',
 24: 'images/hero-dark/tp-link-network-switch.jpg',
 25: 'images/hero-dark/tenda-wifi-router.jpg',
 26: 'images/gallery/tenda-network-switch-g2.jpg',
 27: 'images/hero-dark/tenda-access-point.jpg',
 28: 'images/gallery/ubiquiti-unifi-access-point-g2.jpg',
 29: 'images/gallery/ubiquiti-unifi-switch-g4.jpg',
 30: 'images/hero-dark/audionic-earbuds.jpg',
 31: 'images/hero-dark/audionic-bluetooth-speaker.jpg',
 32: 'images/hero-dark/audionic-soundbar.jpg',
 33: 'images/hero-dark/audionic-home-theater-system.jpg',
 34: 'images/hero-dark/audionic-party-speaker.jpg',
 35: 'images/hero-dark/audionic-wireless-microphone.jpg',
 36: 'images/hero-dark/audionic-multimedia-speaker.jpg',
 37: 'images/hero-dark/audionic-subwoofer.jpg',
 38: 'images/hero-dark/audionic-portable-speaker.jpg',
 40: 'images/hero-dark/audionic-conference-speaker.jpg',
 41: 'images/hero-dark/samsung-43-inch-led.jpg',
 42: 'images/hero-dark/samsung-55-inch-led.jpg',
 43: 'images/hero-dark/samsung-65-inch-led.jpg',
 44: 'images/hero-dark/lg-43-inch-smart-led.jpg',
 46: 'images/hero-dark/lg-65-inch-smart-led.jpg',
 47: 'images/hero-dark/sony-43-inch-bravia.jpg',
 48: 'images/hero-dark/sony-55-inch-bravia.jpg',
 49: 'images/hero-dark/sony-65-inch-bravia.jpg',
 50: 'images/hero-dark/sony-75-inch-bravia.jpg',
 54: 'images/hero-dark/dahua-dh-hac-hdw1209tlqp-led.jpg',
 55: 'images/hero-dark/dahua-dh-hac-t1a41p-4mp-ir-eyeball.jpg',
 56: 'images/hero-dark/dahua-dh-hac-t5e20p-2mp-economy-hd-indoor-eyeball.jpg',
 57: 'images/hero-dark/dahua-dh-ipc-t1e29-a-il-2mp-dome.jpg',
 58: 'images/hero-dark/dahua-dh-ipc-b1e49-a-il-smart-dual-light-camera.jpg',
 59: 'images/hero-dark/tiandy-tc-321-2mp.jpg',
 60: 'images/hero-dark/tiandy-tc-c331.jpg',
 61: 'images/hero-dark/v380-e27.jpg',
 62: 'images/hero-dark/icsee-v1-single-lens.jpg',
 63: 'images/hero-dark/dahua-dhi-nvr4116hs-4ks3.jpg',
 64: 'images/hero-dark/dahua-dhi-nvr2108hs-4ks3.jpg',
 66: 'images/hero-dark/dahua-dhi-nvr1108hs-s3-h.jpg',
 67: 'images/hero-dark/tiandy-tc-r3108.jpg',
 68: 'images/hero-dark/tiandy-tc-r3104.jpg',
 69: 'images/hero-dark/tiandy-nvr-tc-r3120.jpg',
 70: 'images/gallery/ruijie-rg-ew300n-n300-wireless-smart-router-g1.jpg',
 71: 'images/hero-dark/ruijie-rg-ew300-pro.jpg',
 72: 'images/hero-dark/tp-link-tl-wr840n.jpg',
 73: 'images/hero-dark/tenda-n300-wireless-router.jpg',
 74: 'images/hero-dark/imou-ranger-2-2k-3mp.jpg',
 75: 'images/hero-dark/imou-ranger-2-pro-2k.jpg',
 76: 'images/hero-dark/dahua-n22al12.jpg',
 77: 'images/hero-dark/dahua-dh-ipc-hdbw5231en-ze-hdmi.jpg',
 78: 'images/hero-dark/dahua-dh-ipc-hdbw4239rn-ase.jpg',
 79: 'images/hero-dark/dahua-dh-ipc-hfw4239tn-ase.jpg',
 80: 'images/hero-dark/dahua-dh-epc230u.jpg',
 81: 'images/hero-dark/dahua-dh-ipc-hdbw8232en-z-sl.jpg',
 82: 'images/hero-dark/dahua-dh-ipc-hdbw4231fn-e2-m.jpg',
 83: 'images/hero-dark/dahua-n24cl52.jpg',
 84: 'images/hero-dark/dahua-n24cb33.jpg',
 85: 'images/hero-dark/dahua-n24cg52.jpg',
 86: 'images/hero-dark/dahua-n25cb5z.jpg',
 87: 'images/hero-dark/dahua-n25cl5z.jpg',
 88: 'images/hero-dark/dahua-n84cg52.jpg',
 89: 'images/hero-dark/dahua-4k-ir-epoe-mini-dome.jpg',
 90: 'images/hero-dark/dahua-dhi-ivss7008-1t.jpg',
 91: 'images/hero-dark/dahua-dhi-ivss7016dr-4t.jpg',
 92: 'images/hero-dark/dahua-dhi-nvr4216-16p-i.jpg',
 93: 'images/hero-dark/dahua-dhi-nvr5216-16p-i.jpg',
 94: 'images/hero-dark/dahua-n54b3p.jpg',
 95: 'images/full/p95.jpg',
 96: 'images/hero-dark/dahua-n54b5n.jpg',
 97: 'images/hero-dark/dahua-n52b5p.jpg',
 98: 'images/gallery/dahua-n52b2p-g1.jpg',
 99: 'images/hero-dark/dahua-dhi-dss4004-s2.jpg',
 100: 'images/hero-dark/dahua-dhi-dss7016dr-s2.jpg',
 101: 'images/hero-dark/dahua-dhi-nvr6a08-128-4ks2.jpg',
 102: 'images/hero-dark/dahua-dhi-nvr6a08-64-4ks2.jpg',
 103: 'images/hero-dark/dahua-dhi-nvr6a08-32-4ks2.jpg',
 104: 'images/hero-dark/dahua-n54a4p.jpg',
 105: 'images/hero-dark/dahua-n52a4p.jpg',
 106: 'images/hero-dark/dahua-n42b3p.jpg',
 107: 'images/hero-dark/dahua-n42b2p.jpg'}
SHOWPIECE_THUMB = {10: 'images/hero-dark-thumb/hikvision-2mp-dome-camera.jpg',
 11: 'images/hero-dark-thumb/hikvision-5mp-bullet-camera.jpg',
 12: 'images/hero-dark-thumb/dahua-2mp-dome-camera.jpg',
 13: 'images/hero-dark-thumb/dahua-5mp-bullet-camera.jpg',
 14: 'images/hero-dark-thumb/tiandy-5mp-camera.jpg',
 15: 'images/hero-dark-thumb/tiandy-ip-camera.jpg',
 16: 'images/gallery-thumb/ezviz-indoor-camera-g3.jpg',
 17: 'images/gallery-thumb/ezviz-outdoor-camera-g2.jpg',
 18: 'images/hero-dark-thumb/imou-ranger-series.jpg',
 19: 'images/hero-dark-thumb/v380-pro-wifi-camera.jpg',
 20: 'images/gallery-thumb/ruijie-wifi-router-g2.jpg',
 21: 'images/hero-dark-thumb/ruijie-access-point.jpg',
 22: 'images/hero-dark-thumb/tp-link-archer-router.jpg',
 23: 'images/hero-dark-thumb/tp-link-wifi-access-point.jpg',
 24: 'images/hero-dark-thumb/tp-link-network-switch.jpg',
 25: 'images/hero-dark-thumb/tenda-wifi-router.jpg',
 26: 'images/gallery-thumb/tenda-network-switch-g2.jpg',
 27: 'images/hero-dark-thumb/tenda-access-point.jpg',
 28: 'images/gallery-thumb/ubiquiti-unifi-access-point-g2.jpg',
 29: 'images/gallery-thumb/ubiquiti-unifi-switch-g4.jpg',
 30: 'images/hero-dark-thumb/audionic-earbuds.jpg',
 31: 'images/hero-dark-thumb/audionic-bluetooth-speaker.jpg',
 32: 'images/hero-dark-thumb/audionic-soundbar.jpg',
 33: 'images/hero-dark-thumb/audionic-home-theater-system.jpg',
 34: 'images/hero-dark-thumb/audionic-party-speaker.jpg',
 35: 'images/hero-dark-thumb/audionic-wireless-microphone.jpg',
 36: 'images/hero-dark-thumb/audionic-multimedia-speaker.jpg',
 37: 'images/hero-dark-thumb/audionic-subwoofer.jpg',
 38: 'images/hero-dark-thumb/audionic-portable-speaker.jpg',
 40: 'images/hero-dark-thumb/audionic-conference-speaker.jpg',
 41: 'images/hero-dark-thumb/samsung-43-inch-led.jpg',
 42: 'images/hero-dark-thumb/samsung-55-inch-led.jpg',
 43: 'images/hero-dark-thumb/samsung-65-inch-led.jpg',
 44: 'images/hero-dark-thumb/lg-43-inch-smart-led.jpg',
 46: 'images/hero-dark-thumb/lg-65-inch-smart-led.jpg',
 47: 'images/hero-dark-thumb/sony-43-inch-bravia.jpg',
 48: 'images/hero-dark-thumb/sony-55-inch-bravia.jpg',
 49: 'images/hero-dark-thumb/sony-65-inch-bravia.jpg',
 50: 'images/hero-dark-thumb/sony-75-inch-bravia.jpg',
 54: 'images/hero-dark-thumb/dahua-dh-hac-hdw1209tlqp-led.jpg',
 55: 'images/hero-dark-thumb/dahua-dh-hac-t1a41p-4mp-ir-eyeball.jpg',
 56: 'images/hero-dark-thumb/dahua-dh-hac-t5e20p-2mp-economy-hd-indoor-eyeball.jpg',
 57: 'images/hero-dark-thumb/dahua-dh-ipc-t1e29-a-il-2mp-dome.jpg',
 58: 'images/hero-dark-thumb/dahua-dh-ipc-b1e49-a-il-smart-dual-light-camera.jpg',
 59: 'images/hero-dark-thumb/tiandy-tc-321-2mp.jpg',
 60: 'images/hero-dark-thumb/tiandy-tc-c331.jpg',
 61: 'images/hero-dark-thumb/v380-e27.jpg',
 62: 'images/hero-dark-thumb/icsee-v1-single-lens.jpg',
 63: 'images/hero-dark-thumb/dahua-dhi-nvr4116hs-4ks3.jpg',
 64: 'images/hero-dark-thumb/dahua-dhi-nvr2108hs-4ks3.jpg',
 66: 'images/hero-dark-thumb/dahua-dhi-nvr1108hs-s3-h.jpg',
 67: 'images/hero-dark-thumb/tiandy-tc-r3108.jpg',
 68: 'images/hero-dark-thumb/tiandy-tc-r3104.jpg',
 69: 'images/hero-dark-thumb/tiandy-nvr-tc-r3120.jpg',
 70: 'images/gallery-thumb/ruijie-rg-ew300n-n300-wireless-smart-router-g1.jpg',
 71: 'images/hero-dark-thumb/ruijie-rg-ew300-pro.jpg',
 72: 'images/hero-dark-thumb/tp-link-tl-wr840n.jpg',
 73: 'images/hero-dark-thumb/tenda-n300-wireless-router.jpg',
 74: 'images/hero-dark-thumb/imou-ranger-2-2k-3mp.jpg',
 75: 'images/hero-dark-thumb/imou-ranger-2-pro-2k.jpg',
 76: 'images/hero-dark-thumb/dahua-n22al12.jpg',
 77: 'images/hero-dark-thumb/dahua-dh-ipc-hdbw5231en-ze-hdmi.jpg',
 78: 'images/hero-dark-thumb/dahua-dh-ipc-hdbw4239rn-ase.jpg',
 79: 'images/hero-dark-thumb/dahua-dh-ipc-hfw4239tn-ase.jpg',
 80: 'images/hero-dark-thumb/dahua-dh-epc230u.jpg',
 81: 'images/hero-dark-thumb/dahua-dh-ipc-hdbw8232en-z-sl.jpg',
 82: 'images/hero-dark-thumb/dahua-dh-ipc-hdbw4231fn-e2-m.jpg',
 83: 'images/hero-dark-thumb/dahua-n24cl52.jpg',
 84: 'images/hero-dark-thumb/dahua-n24cb33.jpg',
 85: 'images/hero-dark-thumb/dahua-n24cg52.jpg',
 86: 'images/hero-dark-thumb/dahua-n25cb5z.jpg',
 87: 'images/hero-dark-thumb/dahua-n25cl5z.jpg',
 88: 'images/hero-dark-thumb/dahua-n84cg52.jpg',
 89: 'images/hero-dark-thumb/dahua-4k-ir-epoe-mini-dome.jpg',
 90: 'images/hero-dark-thumb/dahua-dhi-ivss7008-1t.jpg',
 91: 'images/hero-dark-thumb/dahua-dhi-ivss7016dr-4t.jpg',
 92: 'images/hero-dark-thumb/dahua-dhi-nvr4216-16p-i.jpg',
 93: 'images/hero-dark-thumb/dahua-dhi-nvr5216-16p-i.jpg',
 94: 'images/hero-dark-thumb/dahua-n54b3p.jpg',
 96: 'images/hero-dark-thumb/dahua-n54b5n.jpg',
 97: 'images/hero-dark-thumb/dahua-n52b5p.jpg',
 98: 'images/gallery-thumb/dahua-n52b2p-g1.jpg',
 99: 'images/hero-dark-thumb/dahua-dhi-dss4004-s2.jpg',
 100: 'images/hero-dark-thumb/dahua-dhi-dss7016dr-s2.jpg',
 101: 'images/hero-dark-thumb/dahua-dhi-nvr6a08-128-4ks2.jpg',
 102: 'images/hero-dark-thumb/dahua-dhi-nvr6a08-64-4ks2.jpg',
 103: 'images/hero-dark-thumb/dahua-dhi-nvr6a08-32-4ks2.jpg',
 104: 'images/hero-dark-thumb/dahua-n54a4p.jpg',
 105: 'images/hero-dark-thumb/dahua-n52a4p.jpg',
 106: 'images/hero-dark-thumb/dahua-n42b3p.jpg',
 107: 'images/hero-dark-thumb/dahua-n42b2p.jpg'}

def features_html(p):
    """Image-led feature sections (DJI pattern: huge image + bold heading +
    1-2 lines). Wide scene shots fill the band; square/portrait product
    shots sit centred at full size so nothing is ever cropped.
    Round 9 -- PACING: the 108 pages were all the same shape (image band
    + centred text, twice each). Now wide scenes (>=1.78) go full-bleed
    with the text overlaid on a gradient scrim (DJI's own pattern), and
    the remaining sections alternate centred / left-aligned text, so no
    two neighbouring sections look alike."""
    secs = FEATURES.get(p["id"]) or []
    if not secs:
        return ""
    out = []
    for i, s in enumerate(secs):
        img_html = ""
        overlay = False
        if s.get("img") and (STAGING / s["img"]).is_file():
            im = Image.open(STAGING / s["img"])
            wide = im.width / im.height >= 1.25
            very_wide = im.width / im.height >= 1.78
            cls = "feature-img wide" if wide else "feature-img"
            img_html = (f'<div class="{cls}"><img src="{detail_hero_uri(s["img"])}" '
                        f'alt="{esc(s["h"])}" loading="lazy"></div>')
            overlay = very_wide
        if overlay:
            sec_cls = "feature-sec overlay"
        elif i % 2 == 1:
            sec_cls = "feature-sec alt"
        else:
            sec_cls = "feature-sec"
        out.append(f'<section class="{sec_cls}"{" id=\"features\"" if i == 0 else ""}>{img_html}'
                   f'<div class="wrap feature-text"><h2>{esc(s["h"])}</h2><p>{esc(s["b"])}</p></div></section>')
    return "\n".join(out)

# 6-item spec strips, footnote numbers exactly as DJI shows them.
DJI_SPECS = {
    "dji-mavic-3-pro": ["4/3 CMOS Hasselblad Camera", "Dual Tele Cameras",
        "Tri-Camera Apple ProRes Support [1]", "43-Min Max Flight Time [2]",
        "Omnidirectional Obstacle Sensing", "15km HD Video Transmission [3]"],
    "dji-air-3s": ["1″ CMOS Primary Camera",
        "Nightscape Omnidirectional Obstacle Sensing [2]",
        "Dual-Camera 4K/60fps HDR Video & 14 Stops of Dynamic Range [1]",
        "Free Panorama, Seamless and Detailed",
        "Next-Gen Smart RTH With Enhanced Precision",
        "45-Min Flight Time, [3] 20km Video Transmission [4]"],
    "dji-mini-4-pro": ["Under 249 g [1]", "Extended Battery Life [2]",
        "4K/60fps HDR True Vertical Shooting", "20km FHD Video Transmission [3]",
        "Omnidirectional Obstacle Sensing", "ActiveTrack 360°"],
}

# Verbatim intro paragraphs (heading, paragraph). Mavic and Air 3S have no
# intro heading on DJI's page; Mini 4 Pro's intro sits under "Go Big With Mini".
DJI_INTRO = {
    "dji-mavic-3-pro": (None,
        "The DJI Mavic 3 Series features next-level imaging performance. Mavic 3 Pro's triple-camera system ushers in a new era of camera drones by housing three sensors and lenses with different focal lengths. Equipped with a Hasselblad camera and dual tele cameras, Mavic 3 Pro is a triple-camera drone that unlocks new shooting perspectives, allowing you to embrace creative freedom further, capture fascinating scenery, explore photographic storytelling, and make cinematic masterpieces."),
    "dji-air-3s": (None,
        "A dual-camera drone designed for travel photography, DJI Air 3S integrates a suite of advanced technologies. Featuring a 1-inch-CMOS primary camera and a 70mm medium tele camera, each with up to 14 stops of dynamic range, [1] Air 3S captures landscapes, portraits, and more in stunning detail. Both cameras support the new Free panorama feature, which allows flexible shooting-range selections. Additional new highlights include nightscape obstacle sensing [2] and next-gen Smart RTH for enhanced safety during nighttime photography. In each and every way, DJI Air 3S is designed to maximize every aerial moment."),
    "dji-mini-4-pro": ("Go Big With Mini",
        "DJI Mini 4 Pro is our most advanced mini-camera drone to date. [4] It integrates powerful imaging capabilities, omnidirectional obstacle sensing, ActiveTrack 360° with the new Manual Mode, and 20km FHD video transmission, bringing even more things to love for pros and beginners alike."),
}

# Feature sections in DJI's order. Each block: h (heading or None), b (body
# copy or None), chips (spec values / tab names), items (named sub-points),
# quotes (creator cards). Where DJI's copy file has the heading but no
# verified body, the block is heading-only — body copy is never invented.
DJI_FEATURES = {
"dji-mavic-3-pro": [
    {"h": "Unrivaled Tri-Camera Flagship Imaging",
     "b": "One camera drone, three lenses, and infinite imagination. Mavic 3 Pro, with the triple-camera system's multiple focal lengths, can achieve an even richer camera language and fully express creativity with superior multi-scenario capabilities. You can tap the display to switch between various focal lengths and easily incorporate distinct composition styles for different scenarios. Turn your inspiration into ingenuity with the improved efficiency of tri-camera aerial photography."},
    {"h": "4/3 CMOS Hasselblad Camera",
     "chips": ["24mm eq.", "f/2.8–f/11", "20 MP"]},
    {"h": "1/1.3″ CMOS Medium Tele Camera",
     "chips": ["70mm eq.", "3x Optical Zoom", "f/2.8", "48 MP"]},
    {"h": "1/2″ CMOS Tele Camera",
     "chips": ["166mm eq.", "7x Optical Zoom", "28x Hybrid Zoom", "f/3.4", "12 MP"]},
    {"quotes": [
        ("Wildlife & Nature Photographer", "Paul Nicklen",
         "I capture images of endangered megafauna to inspire the protection of fragile ecosystems. It's critical for me to follow high standards while creating stunning photos. With Mavic 3 Pro's tele lenses, I can shoot high-res photos without disturbing wildlife."),
        ("SkyPixel Creator", "Jingyan",
         "Mavic 3 Pro puts three widely used focal lengths into a compact aircraft to make my work more efficient and creative. The new 70mm lets me shoot unique scenes and delivers stunning image quality and spatial compression along with the 166mm, which supports my visual expression."),
        ("Travel & Landscape Photographer", "Jason Charles Hill",
         "My work explores off-beat locales on every continent. The triple camera system allows me to tell rich stories and document the wild and unknown. Also, the 28x hybrid zoom of the Mavic 3 Pro helps me capture wildlife from a safe and ethical distance.")]},
    {"h": "Artistry From Every Angle",
     "chips": ["Nature", "Architecture", "Wildlife"]},
    {"h": "Hasselblad Camera, Immense Detail",
     "b": "Inheriting the 4/3 CMOS Hasselblad camera of the Mavic 3 Series, Mavic 3 Pro is the next step for professional creation. The Hasselblad camera supports shooting 12-bit RAW photos with a native dynamic range of up to 12.8 stops, presenting unforgettable image details. The Hasselblad Natural Colour Solution (HNCS) accurately restores the colors the human eye perceives, getting impressive shots without the need for heavy post-production or complex color presets.",
     "b2": "The Hasselblad camera and the 70mm medium tele camera of Mavic 3 Pro support FocusTrack, which includes ActiveTrack 5.0, Spotlight, and Point of Interest, enabling stable tracking shots in multiple directions.",
     "chips": ["Hasselblad Camera: 5.1K/50fps, 4K/120fps"]},
    {"h": "Professional Video Specification",
     "chips": ["5.1K/50fps [4]", "4K/120fps [4]", "10-bit D-Log"]},
    {"h": ["HLG", "Night Shots", "Hyperlapse"]},
    {"b": "The new 10-bit D-Log M color mode supports recording up to one billion colors. Even in high-contrast scenarios, like sunrises and sunsets, it delivers natural color gradations with delicate details for a full-spectrum visual experience. In addition, D-Log M mode reduces the difficulty of color grading, allowing you to fully enjoy efficient post-production without losing image quality or clarity."},
    {"h": "Mavic 3 Pro Cine",
     "b": "Mavic 3 Pro Cine provides extensive options for professional creators. All three cameras support Apple ProRes 422 HQ, ProRes 422, ProRes 422 LT encoding. It also has a built-in 1TB SSD [5] and a 10Gbps lightspeed data cable to facilitate professional creation further.",
     "chips": ["Apple ProRes — Codec", "1TB SSD — Internal Storage"]},
    {"h": "70mm Medium Tele Camera, Dynamic Framing",
     "b": "The medium tele camera suits various themes and scenarios. It compresses the depth of field and focus to highlight the subject and create a robust visual center of gravity, giving camera movement a unique sense of space. Additionally, the medium tele camera supports Night Shots, presenting brilliant nighttime scenes at a 70mm focal length. Just focus on inspiration, and let Mavic 3 Pro perform a concerto of light and shadow before your eyes.",
     "chips": ["70 mm, f/3.4, 1/4s, ISO 50"]},
    {"h": "Versatile Video Specification",
     "chips": ["4K/60fps", "10-bit D-Log M", "HLG", "Hyperlapse"]},
    {"h": "166mm Tele Camera, Go With Zoom",
     "b": "The upgraded tele camera features higher resolution and a wider f/3.4 aperture. It supports shooting 4K/60fps video with 7x optical zoom and 12MP photos. The hybrid zoom reaches up to 28x. Zoom in and immerse yourself in rich image details.",
     "chips": ["166 mm, f/3.4, 1/4s, ISO 50"]},
    {"h": "4K/60fps, Telephoto Creativity Unleashed",
     "b": "The upgraded tele camera features higher resolution and a wider f/3.4 aperture. It supports shooting 4K/60fps video with 7x optical zoom and 12MP photos. The hybrid zoom reaches up to 28x. Zoom in and immerse yourself in rich image details. The tele camera also supports HLG and 10-bit D-Log M color modes, enabling greater flexibility in post-production."},
    {"h": "Extended Flight Time",
     "b": "Mavic 3 Pro provides up to 43 minutes of flight time, [2] giving you more confidence to fly further and spend less time worrying about the battery level. Execute every step, from flight route planning to shot composition, all during a single flight.",
     "chips": ["43 mins — Flight Time"]},
    {"h": "Omnidirectional Obstacle Sensing and APAS 5.0",
     "b": "Mavic 3 Pro ensures you fly safely and create with peace of mind. Eight wide-angle vision sensors work seamlessly with a high-performance vision computing engine to precisely sense obstacles in all directions and plan a safe flight route to avoid them. [6]"},
    {"h": "Vision Assist - Aerial Creation With Enhanced Safety",
     "b": "Take your aerial creation to the next level with multi-directional visual assistance: front, back, left, and right. A simple tap on the screen swaps your view, helping you anticipate obstacles in every direction during your flight. This heightened awareness empowers you to chart a safer, more efficient course."},
    {"h": "Flagship Video Transmission",
     "b": "DJI O3+ features a transmission distance of up to 15 km [3] with stable signals, presenting a more coherent camera view. It can transmit a 1080p/60fps HD live feed, which makes Mavic 3 Pro more responsive to your control and gives you a more vibrant video feed on your monitor.",
     "chips": ["1080p/60fps — HD Live Feed", "15 km — Video Transmission Distance"]},
    {"h": "Automatic Flight Experience"},
    {"h": "Intelligent Creation, Infinite Inspiration",
     "items": [
        ("FocusTrack [7]", "The Hasselblad camera and the 70mm medium tele camera of Mavic 3 Pro support FocusTrack, which includes ActiveTrack 5.0, Spotlight, and Point of Interest, enabling stable tracking shots in multiple directions."),
        ("MasterShots [8]", "Tap to enable MasterShots, and Mavic 3 Pro will automatically shoot, edit, add soundtracks, and generate cinematic footage afterward."),
        ("QuickShots [8]", "QuickShots empowers Mavic 3 Pro to perform diverse camera movements like Dronie, Rocket, Circle, and Helix."),
        ("Panorama [8]", "Mavic 3 Pro can directly compose a 100MP lossless panorama photo to capture a more breathtaking landscape."),
        ("High-Speed QuickTransfer", "Quickly transfer photos and videos to your smartphone without linking the remote controller.")]},
    {"h": "LightCut",
     "b": "Connect Mavic 3 Pro wirelessly to the LightCut app on your phone for quick previewing of clips and AI-based One-Tap Edit without downloading the footage, saving storage on your phone. Try templates made especially for MasterShots and effortlessly create amazing aerial videos that impress and awe."},
    {"h": "Experiencing FPV Flight is Easy",
     "b": "The Mavic 3 Series camera drones can be used with DJI Goggles Integra, DJI Goggles 2, and DJI RC Motion 2, allowing you to enjoy the fun of FPV flight."},
    {"h": "Diverse Accessories, Stunning Flight",
     "note": "Accessories shown are DJI's official accessories for this drone — ask on WhatsApp which are in stock.",
     "items": [
        ("DJI RC Pro", "DJI RC Pro is an unmatched option for professional creation with a 1000-nit display, a high-performance processor, and 15km video transmission support."),
        ("DJI Mavic 3 Pro ND Filters Set", "The set provides ND8/16/32/64 filters, allowing you to create footage and images at slower shutter speeds."),
        ("DJI Mavic 3 Pro Wide-Angle Lens [9]", "Compatible with the Mavic 3 Pro Hasselblad camera to deliver a 108° super-wide FOV and capture more in every frame."),
        ("DJI Mavic 3 Series Intelligent Flight Battery", "Provides Mavic 3 Pro with up to 43 minutes of flight time. [2]"),
        ("DJI Mavic 3 Series 100W Battery Charging Hub", "When connected to the DJI 100W USB-C Power Adapter, the Battery Charging Hub can charge three batteries sequentially for enhanced efficiency."),
        ("DJI Goggles Integra Motion Combo [9]", "Experience immersive FPV when you use DJI goggles along with the DJI RC Motion 2. Enjoy true-to-life colors, accurate details, and motion controls that make flying captivating."),
        ("DJI 65W Car Charger [9]", "The car charger is lightweight and portable and uses a universal port. It can charge the battery, remote controller, smartphone, laptop, and other devices.") ]},
],
"dji-air-3s": [
    {"h": "Dual Cameras, Unmatched Imagery",
     "b": "DJI Air 3S features a dual-camera system consisting of a 1-inch-CMOS primary camera and a 1/1.3-inch-CMOS medium tele camera. The primary camera features a larger CMOS sensor and a 24mm lens, making it ideal for capturing expansive landscapes with enhanced clarity and a wide field of view. The 70mm medium tele camera excels at portrait and vehicle shots, offering compressed depth of field to highlight any subject with a bolder, more cinematic look."},
    {"h": "1″ CMOS Primary Wide-Angle Camera",
     "chips": ["3.2μm Large Pixel Size [5]", "24mm Format Equivalent", "50 MP", "f/1.8 Aperture"]},
    {"h": "1/1.3″ CMOS Medium Tele Camera",
     "chips": ["2.4μm Large Pixel Size [5]", "70mm Format Equivalent", "48 MP", "f/2.8 Aperture"]},
    {"h": "1″ CMOS Primary Camera: Breathtaking Detail for Travel Photography",
     "chips": ["Architecture", "Lakes", "Mountains"]},
    {"h": "Enhanced Imagery, Stunning Scenery",
     "chips": ["4K/60fps HDR Video", "4K/120fps Video [6]", "10-bit D-Log M & HLG Video"]},
    {"h": "Medium Tele Camera: Unforgettable Portraits"},
    {"h": "Focus on Details, Maximize Focal Power"},
    {"h": "Free Panorama",
     "b": "Both the primary camera and medium tele camera of DJI Air 3S offer Free panorama mode, letting you create seamless panoramic shots by stitching together multiple images with a manually selected subject or area. The wide-angle camera offers a broader FOV, boosting efficiency when capturing panorama photos. The medium tele camera significantly reduces image distortion, crafting your masterpieces into expansive shots with a wide perspective from multiple photos and rich details captured through its focal length advantages."},
    {"b": "Compared with the previous-generation DJI Air 3, DJI Air 3S employs a more advanced video encoding compression algorithm that reduces video file sizes by over 30% without compromising image quality, saving valuable storage space for creators. DJI Air 3S also supports user-favorite features like 2.7K vertical shooting, MasterShots, QuickShots, Hyperlapse, and more, putting a massive creative toolkit together in one compact drone."},
    {"h": "Safer Nighttime Flying for Expanded Creativity"},
    {"h": "Omnidirectional Vision Sensing System",
     "b": "DJI Air 3S supports the Advanced Pilot Assistance Systems (APAS). Additionally, as the first DJI drone to feature forward-facing LiDAR, Air 3S also features a downward infrared time-of-flight (ToF) sensor and six vision sensors (two at the front, rear, and bottom) to achieve nightscape omnidirectional obstacle sensing. [2] This feature enables the drone to automatically identify and circumvent obstacles, such as buildings, during its flight and return paths, ensuring robust safety for nighttime photography."},
    {"h": "Nightscape Omnidirectional Obstacle Sensing"},
    {"h": "Next-Gen Smart RTH",
     "chips": ["Non-GPS RTH", "Nighttime RTH"]},
    {"h": "Enhanced Vision Assist",
     "b": "DJI Air 3S's Vision Assist provides a downward view in addition to the front, back, left, and right views to help you better understand your surroundings.",
     "b2": "DJI Air 3S also provides Waypoint Flight and Cruise Control, among other advanced features, which allow you to pre-set flight paths and camera actions and quickly lock control stick inputs to unleash creativity."},
    {"h": "ActiveTrack 360° for Effortless Visual Appeal"},
    {"h": "A New Air Aesthetic",
     "b": "DJI Air 3S features ActiveTrack 360° to keep any subject optimally in frame. Based on the surrounding flight environment, it automatically plans a flight path and adjusts framing to ensure stronger shots that keep your subject the center of attention."},
    {"h": "ActiveTrack 360°",
     "b": "ActiveTrack 360° allows Air 3S to automatically avoid perspectives with cluttered backgrounds."},
    {"h": "Optimized Tracking Performance",
     "b": "Once tracking begins, DJI Air 3S can keep the subject in focus even if the lower half of their body is partially obscured by bushes or if they are standing on a bridge."},
    {"h": "Stay Focused",
     "b": "DJI Air 3S introduces a new Subject Focusing feature that keeps your subject in sharp focus, even during manual flight or when the subject moves off-center. This feature allows you to fully concentrate on the more creative aspects of your shots like composition and camera movement."},
    {"h": "Extended Flight & Transmission Distance"},
    {"h": "Serious Air Time: 45-Min Max [3]",
     "b": "With up to 45 minutes of flight time, [3] Air 3S gives you enough time to scout locations, compose, nail your shots, and do it all over again and again."},
    {"h": "10-bit O4 Video Transmission",
     "b": "Powered by DJI O4 FHD video transmission technology, Air 3S delivers 10-bit video transmission at 1080p/60fps over distances of up to 20 kilometers. [4] Live feeds are reliably smooth and vivid, with ultra-responsive control for an improved overall flight experience."},
    {"h": "DJI Cellular Dongle 2 Compatibility",
     "b": "The DJI Cellular Dongle 2 [8] can be inserted directly into DJI Air 3S for seamless integration without the need for any extra accessories. In case of O4 signal obstruction or interference, you can rely on 4G connectivity for stable video transmission and drone control, enhancing flight safety and reducing disconnection risks."},
    {"h": "Attention to Every Detail"},
    {"h": "Always Ready: 42GB of Built-in Storage",
     "b": "DJI Air 3S comes standard with 42GB of built-in storage. This allows you to start recording right away and avoid having to deal with microSD cards."},
    {"h": "Off-State QuickTransfer",
     "b": "You can now send files from your Air 3S to a smartphone even when the drone is powered off. [9] Transfers to a computer can also be done with the drone powered off—simply connect Air 3S via a compatible USB cable."},
    {"h": "Battery Charging Hub with Power Accumulation [10]",
     "b": "The Battery Charging Hub supports PD fast charging and a power accumulation function, which allows you to transfer the remaining power of multiple low-power batteries into the battery with the highest remaining power. [10]"},
    {"h": "Tailor to Your Needs",
     "b": "DJI Air 3S offers various combos and diverse accessories to meet your every need.",
     "note": "Accessories shown are DJI's official accessories for this drone — ask on WhatsApp which are in stock.",
     "items": [
        ("DJI Air 3S (DJI RC-N3)", "Includes the standard DJI RC-N3 remote controller. Use with your smartphone to check the live feed and flight status."),
        ("DJI Air 3S Intelligent Flight Battery", "Provides Air 3S with up to 45 minutes of flight time, allowing you to get the shots you want in a single flight."),
        ("DJI Air 3S Wide-Angle Lens", "Adopts a precise optical design that expands the FOV of the wide-angle camera to 114°, offering a wider filming perspective. [8]"),
        ("DJI Air 3S Fly More Combo (DJI RC-N3)", "Includes the DJI RC-N3 remote controller, an ND filter set, two additional batteries, a battery charging hub, a shoulder bag, and more."),
        ("DJI Air 3S ND Filter Set (ND8/32/128)", "Includes ND8/32/128 filters, enabling lower shutter speeds for smoother footage."),
        ("DJI Cellular Dongle 2", "Achieves integrated installation with DJI Air 3S, requiring no additional installation kit. This gives Air 3S a stable connection to a 4G network, reducing the risk of disconnection. [8]"),
        ("DJI Air 3S Fly More Combo (DJI RC 2)", "Includes DJI RC 2 with a 5.5-inch 1080p 700-nit high-bright screen, an ND filter set, two additional batteries, a battery charging hub, a shoulder bag, and more."),
        ("DJI Air 3 Series Battery Charging Hub", "Supports sequential fast charging for up to three batteries or fast charging for devices such as remote controllers and smartphones. It can also transfer the remaining power from multiple batteries to the one with the highest charge. [10]") ]},
],
"dji-mini-4-pro": [
    {"h": "Take it Easy",
     "b": "Take off whenever inspiration strikes. Weighing less than 249 g, Mini 4 Pro was designed for convenience on the go, [1] and the drone's weight means there's no need for training or examinations in most countries and regions."},
    {"h": "Out-sized Imaging Performance",
     "b": "Capture more complex details easily with Mini 4 Pro's camera, powered by a 1/1.3-inch CMOS sensor featuring Dual Native ISO Fusion, a f/1.7 aperture, and 2.4μm 4-in-1 pixels. [5] More highlight and shadow details with a high dynamic range means uncompromising results in every frame."},
    {"h": "Maximum Visual Impact",
     "b": "Give vibrant scenes the details they deserve with 4K/60fps HDR and 4K/100fps video, while 10-bit D-Log M and HLG help capture a stunning range of colors and provide more flexibility while editing and sharing."},
    {"h": "4K/60fps HDR",
     "b": "Preserve the natural wonder of any moment. 4K/60fps HDR lets you share the nuances of sunset or sunrise in true-to-life quality."},
    {"h": "Slo-Mo 4K/100fps",
     "b": "Immerse the audience in every frame. With slow motion in 4K clarity, capture the action on the trails, at the beach, or in your own backyard at 100fps."},
    {"h": "Highlight the Night",
     "b": "The improved noise reduction algorithm of Mini 4 Pro's Night Shots video effectively suppresses noise and facilitates clearer, cleaner footage right from the camera."},
    {"h": "1.07 Billion Colors",
     "b": "Record in 10-bit D-Log M. The natural color gradations and delicate full-spectrum details mean Mini 4 Pro unlocks pro-level post-production control and expert-level creative editing flexibility."},
    {"h": "Dynamic on Every Platform",
     "b": "No matter where you publish your content, HLG ensures the natural colors and brightness remain true-to-life without adjustment or format conversion due to its high dynamic range."},
    {"h": "RAW-Some Photos",
     "b": "It's often the little things that matter most. Preserve every intricate detail with 48MP RAW and next-gen SmartPhoto [6] which combines HDR imaging, scene recognition, and more for images that pop."},
    {"h": "More Ways to See it All",
     "chips": ["Large-Angle Tilt", "True Vertical Shooting", "Digital Zoom"]},
    {"h": "Intuitive Features, Enhanced Flights"},
    {"h": "Sense More, Fly Safe",
     "b": "Omnidirectional obstacle sensing makes Mini 4 Pro mighty safe. With four wide-angle vision sensors and a pair of downward vision sensors, it detects obstacles from all angles. Advanced Pilot Assistance Systems (APAS) ensures additional safety by enabling automatic braking and bypassing during flight."},
    {"h": "Fly Longer, Create More",
     "b": "Leave battery concerns behind and stay focused on creation with Mini 4 Pro's Intelligent Flight Battery. Enjoy up to 34 minutes of flight time, or upgrade to the Intelligent Flight Battery Plus [2] to enjoy an extra-long 45-minute max flight time.",
     "chips": ["34 mins — Intelligent Flight Battery", "45 mins — Intelligent Flight Battery Plus"]},
    {"h": "20 km Video Transmission",
     "b": "Mini 4 Pro features DJI's O4 video transmission. Enjoy ultra-responsive control and smooth 1080p/60fps FHD live feeds from distances of up to 20 km. [3]"},
    {"h": "Full-Fledged Features",
     "chips": ["Vision Assist", "Waypoint Flight", "Cruise Control", "Advanced RTH", "Immersive Flight Experience"]},
    {"h": "Simply Masterful"},
    {"h": "A Touch of Cinematics",
     "b": "Whether running, biking, or skateboarding, the newly upgraded ActiveTrack 360° can achieve diverse camera movements to fit each shooting scenario. With omnidirectional obstacle sensing, Mini 4 Pro can plan flight routes and bypass obstacles, achieving smoother and more stable dynamic shots. Even if you are a solo adventurer, you can still transform into a real-time director creating cinematic videos for yourself.",
     "items": [
        ("Manual Mode", "You can customize the flight route from multiple directions and use the Manual wheel to achieve cinematic camera movements like circling, pulling in, and pulling away."),
        ("Auto Mode", "Frame the subject, and Mini 4 Pro will automatically plan and execute the flight route. Even during the filming, it can intelligently switch between multiple perspectives and camera movements, helping you craft your aerial masterpiece.")]},
    {"h": "Full-Power Mini",
     "items": [
        ("MasterShots", "Delivers dynamic camera movement templates tailored for portrait, close-up, and long-range shots, ensuring you nail every shot!"),
        ("QuickShots", "Provides Dronie, Circle, Helix, Rocket, Boomerang, and Asteroid modes for more stylish results."),
        ("Hyperlapse", "Provides Free, Waypoint, Circle, and Course Lock modes with unlimited shooting time, and supports compositing while shooting."),
        ("Panorama", "Supports shooting 180°, Wide Angle, Vertical, and Sphere panoramic photos to capture magnificent landscapes."),
        ("QuickTransfer", "Quickly transfer photos and videos to your smartphone without linking the remote controller. Your creations will be instantly ready to share.")]},
    {"h": "Edit with LightCut",
     "b": "LightCut supports wireless connection and intelligent recognition of composition and flight routes, so you can edit quickly and generate eye-catching videos with one tap. By blending imported footage from ActiveTrack, MasterShots, and QuickShots, the app automatically matches sound effects and exclusive templates for quick, high-quality video production. Plus, there is no need to download footage during the editing process, saving storage space on your smartphone."},
    {"h": "Master Aerial Photography in a Snap: Join SkyPixel",
     "b": "The fully upgraded SkyPixel boasts extensive fly spots and fly tips. Ignite your creative inspiration with a single click, and capture stunning shots with peace of mind!"},
    {"h": "Get More out of Mini",
     "note": "Accessories shown are DJI's official accessories for this drone — ask on WhatsApp which are in stock.",
     "items": [
        ("DJI RC 2", "This lightweight and easy-to-use remote controller comes with the built-in DJI Fly app, eliminating the need for smartphone use during flight. The high-definition screen delivers a crisp and clear view even under direct sunlight, optimizing your entire Mini 4 Pro experience."),
        ("DJI Mini 4 Pro Intelligent Flight Battery Plus", "The same Intelligent Flight Battery Plus for the DJI Mini 3 Series provides a max flight time of 45 minutes, [2] ensuring a smooth and worry-free flight."),
        ("DJI Mini 4 Pro Two-Way Charging Hub", "The same Two-Way Charging Hub used for the DJI Mini 3 Series. It can charge a remote controller and three batteries sequentially. It can also be used as a mobile power source to charge remote controllers, smartphones, and other devices and can even store the batteries for convenient and secure carrying."),
        ("DJI Mini 4 Pro Wide-Angle Lens [7]", "Capture sweeping landscapes with the super-wide 100° FOV."),
        ("DJI Mini 4 Pro ND Filters Set (ND16/64/256) [7]", "Adapt to strong lighting conditions with ND16/64/256 filters and always be ready for the perfect shot."),
        ("DJI Mini 4 Pro 360° Propeller Guard [7]", "Fully covers the propellers and is easy to attach and detach, ensuring flight safety in a simple and efficient way.") ]},
],
}

# Drones category comparison — "Which camera drone is suitable for you?"
# Values are DJI's verified values from the copy file; prices are OUR real
# PKR prices where the shop has confirmed one, else "Price on request".
# Flight time is "—" where DJI's comparison tables do not list it for that
# model (Mini 3 Pro, Mini 3) — never invented. Never DJI USD prices.
DJI_COMPARE_ROWS = [
    ("Price", 0), ("Takeoff Weight", 1), ("Camera", 2),
    ("Max Video Resolution", 3), ("Max Flight Time", 4),
    ("Obstacle Sensing", 5), ("Transmission", 6),
]
DJI_COMPARE = [
    ("dji-mavic-3-pro", ["Price on request", "958 g",
        "4/3 CMOS Hasselblad Camera · 1/1.3″ Medium Tele Camera · 1/2″ Tele Camera",
        "5.1K/50fps", "43 mins", "Omnidirectional Obstacle Sensing",
        "DJI O3+ up to 15 km — 1080p/60fps Live Feed"]),
    ("dji-air-3s", ["From Rs 455,000", "724 g",
        "1″ CMOS Wide-Angle Camera · 1/1.3″ CMOS Medium Tele Camera",
        "4K/60fps HDR or 4K/120fps", "45 mins",
        "Nightscape Omnidirectional Obstacle Sensing",
        "DJI O4 up to 20 km (FCC) · 10 km (CE/SRRC/MIC)"]),
    ("dji-air-3", ["Price on request", "720 g",
        "1/1.3″ CMOS Wide-Angle Camera · 1/1.3″ CMOS Medium Tele Camera",
        "4K/60fps HDR or 4K/100fps", "46 mins", "Omnidirectional Obstacle Sensing",
        "DJI O4 up to 20 km (FCC) · 10 km (CE/SRRC/MIC)"]),
    ("dji-mini-4-pro", ["From Rs 275,000", "Under 249 g",
        "1/1.3″ CMOS Wide-Angle Camera · True Vertical Shooting",
        "4K/60fps HDR · Slow Motion 4K/100fps", "34/45 mins (depending on battery)",
        "Omnidirectional Obstacle Sensing, APAS 5.0",
        "DJI O4 up to 20 km — 1080p/60fps Live Feed"]),
    ("dji-mini-3-pro", ["Rs 230,000", "Under 249 g",
        "1/1.3″ CMOS Wide-Angle Camera · True Vertical Shooting",
        "4K/60fps · 4K/30fps HDR · Slow Motion 1080p/120fps", "34/47 mins (depending on battery)",
        "Forward/Backward/Downward Obstacle Sensing, APAS 4.0",
        "DJI O3 up to 12 km — 1080p/30fps Live Feed"]),
    ("dji-mini-3", ["Rs 185,000", "Under 249 g",
        "1/1.3″ CMOS Wide-Angle Camera · True Vertical Shooting",
        "4K/30fps HDR", "38/51 mins (depending on battery)", "Downward Obstacle Sensing · Smart RTH",
        "DJI O2 up to 10 km — 720p/30fps Live Feed"]),
]

# ---------- image embedding ----------
from PIL import Image

def _b64(data: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()

def hero_uri(name: str) -> str:
    """Hero image as data URI (max 2560px wide = DJI @1x, q70). Never upscale
    beyond the source's real resolution; the 1919px hero must never stretch
    a smaller image."""
    p = STAGING / "images" / "hero" / name
    im = Image.open(p).convert("RGB")
    if im.width > 2560:
        im = im.resize((2560, round(im.height * 2560 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70, optimize=True)
    return _b64(buf.getvalue())

def detail_hero_uri(rel: str, max_w: int = 1920) -> str:
    """Detail-hero background as a data URI (max 1920px wide, q70).
    hero_uri() only knows the hero/ dir and caps at 2560; detail heroes
    may come from gallery/ or full/ too, and 1920px is enough for the
    ~460-760px hero band (DJI @1x is 1919px wide). Never upscales.
    Byte impact vs hero_uri()'s 2560 cap (q70 JPEG, b64 in page):
    air3s 70->47KB, mavic3-cine 127->78KB, from-air 274->170KB,
    hero-drone 139->75KB -- roughly a third smaller per hero."""
    p = STAGING / rel
    im = Image.open(p).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70, optimize=True)
    return _b64(buf.getvalue())

def detail_hero_for(p):
    """(hero rel path, css background-position, hero video URL or None,
    YouTube hero video id or None).
    Priority: products.json "hero" / "hero_video" / "hero_yt" fields (with
    optional "hero_pos") > the DETAIL_HERO map by slug (entries may carry
    "video" or "yt") > the product's own photo_full.
    Video URLs are DJI's real hero-video URLs (external https, mp4) --
    supplied by the separate video worker; "yt" is a verified DJI
    official YouTube film id (Round 9: the 8 drones with no CDN hero
    video). The template renders mp4 first, yt second, Ken Burns still
    otherwise. Returns (None, "center", None, None) when the product has
    no photo at all -- the caller then renders the plain black hero."""
    if p.get("hero") or p.get("hero_video") or p.get("hero_yt"):
        return (p.get("hero") or p.get("photo_full"),
                p.get("hero_pos", "center"), p.get("hero_video"),
                p.get("hero_yt"))
    m = DETAIL_HERO.get(p["slug"])
    if m:
        return m["hero"], m.get("pos", "center"), m.get("video"), m.get("yt")
    return p.get("photo_full"), "center", None, None

def img_uri(rel: str) -> str:
    return _b64((STAGING / rel).read_bytes())

def search_uri(rel: str):
    """Search index image: max 800px on the long side (LANCZOS, q70),
    returned with its resized (w, h). Search tiles render at most ~652px
    wide, so 800px stays sharp on display, but embedding the full
    1000–1600px photo for all 108 products made search-data.js 6.2MB —
    too big for one GitHub push (proven push limit: 4.79MB OK, 6.48MB
    fails HTTP 413). The resized w/h keep the audit P3 #10 no-upscale
    cap honest: the card caps at the RESIZED native size."""
    p = STAGING / rel
    im = Image.open(p).convert("RGB")
    w, h = im.size
    if max(w, h) > 800:
        s = 800 / max(w, h)
        im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
        w, h = im.size
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70, optimize=True)
    return _b64(buf.getvalue()), w, h

# Audit P3 #10 — never display an image wider/taller than its native
# pixels. The <img> element is capped at the native size (CSS width/height
# 100% + object-fit:cover then fills that capped box without ever
# upscaling, whatever the tile/box size is).
_IMG_SIZE = {}
def native_size(rel: str):
    if rel not in _IMG_SIZE:
        with Image.open(STAGING / rel) as im:
            _IMG_SIZE[rel] = im.size
    return _IMG_SIZE[rel]

def img_cap(rel: str) -> str:
    w, h = native_size(rel)
    # min(native,100%): never wider than native pixels (audit #10) AND
    # never wider than the container — the old plain "max-width:Npx"
    # overrode the stylesheet's max-width:100% and blew the detail photo
    # to 1047px on a 390px phone (document 1067px wide, header and
    # WhatsApp float pushed off-screen).
    return f"max-width:min({w}px,100%);max-height:{h}px"

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

# ROUND 7 — DJI-style full-bleed tile: the photo fills the WHOLE tile
# edge-to-edge (object-fit:cover; NO img_cap here — the audit P3 #10
# no-upscale cap is deliberately lifted for CARD tiles only, so an 800px
# photo can fill a 936px tile; detail pages keep the cap). Text is OVERLAID
# on the photo — eyebrow/name/tagline at the top, price + CTAs at the
# bottom — white on twin gradient scrims (.card::before/::after), so it
# stays legible on white studio shots and black shots alike. One tile =
# one coherent card: no grey text box above the photo (round 6 "sasti").
def card(p, depth="", buy=False):
    if p.get("photo_full"):
        thumb = (f'<img src="{img_uri(p["photo_full"])}" alt="{esc(p["name"])}" loading="lazy">')
    else:
        thumb = ('<div class="no-photo"><span>Photo on request</span>'
                 '<small>Ask on WhatsApp and the shop will send a photo of the exact unit in stock.</small></div>')
    if buy:
        cta = (f'<div class="card-cta"><a class="btn btn-light" href="{wa_link(p["name"])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>'
               f'<a class="more-link" href="{depth}{product_url(p)}">Learn more &rsaquo;</a></div>')
    else:
        cta = f'<a class="more-link" href="{depth}{product_url(p)}">Learn more &rsaquo;</a>'
    return f"""<article class="card" data-brand="{esc(p["brand"])}" data-name="{esc(p["name"].lower())}" data-price="{p["price_pkr"] or ''}">
  <a class="card-img" href="{depth}{product_url(p)}" aria-label="{esc(p["name"])}">{thumb}</a>
  <div class="card-body">
    <div class="card-top">
      <p class="card-cat">{esc(p["brand"])} &middot; {esc(CATS[p["category"]]["label"])}</p>
      <h3><a href="{depth}{product_url(p)}">{esc(p["name"])}</a></h3>
      <p class="card-tag">{esc(p["tagline"])}</p>
    </div>
    <div class="card-foot">
      {price_html(p)}
      {cta}
    </div>
  </div>
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

def brand_links(depth):
    # Brands mega-menu: Audionic only (the one brand page that exists).
    items = [by_id(i) for i in AUDIONIC_IDS]
    prods = "".join(
        f'<a class="mega-prod" href="{depth}products/{x["slug"]}.html">{esc(x["name"])}</a>'
        for x in items[:3])
    return (f'<div class="mega-col"><a class="mega-cat" href="{depth}brands/audionic.html">Audionic</a>'
            f'<p>Audionic earbuds, speakers and sound systems.</p>{prods}'
            f'<a class="mega-all" href="{depth}brands/audionic.html">View all Audionic &rarr;</a></div>')

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
      <div class="nav-item has-mega"><button class="nav-link" aria-haspopup="true">Brands</button>
        <div class="mega-menu">{brand_links(depth)}</div>
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
      <p>Trusted electronics &amp; security shop.</p>
      <p class="foot-social">
        <a href="{FB_URL}" target="_blank" rel="noopener" aria-label="Facebook">{ICON_FB}</a>
        <a href="{IG1}" target="_blank" rel="noopener" aria-label="Instagram @ak_khan682">{ICON_IG}</a>
        <a href="{IG2}" target="_blank" rel="noopener" aria-label="Instagram @akkhan.enterprises">{ICON_IG}</a>
        <a href="{YT_URL}" target="_blank" rel="noopener" aria-label="YouTube">{ICON_YT}</a>
      </p>
    </div>
    <div class="foot-col"><h4>Shop</h4>
      {"".join(f'<a href="{depth}categories/{c}.html">{CATS[c]["nav"]}</a>' for c in CAT_ORDER)}
      <a href="{depth}compare.html">Compare Products</a>
    </div>
    <div class="foot-col"><h4>Explore</h4>
      <a href="{depth}explore.html">Explore</a>
      <a href="{depth}search.html">Search</a>
      <a href="{depth}about.html">About Us</a>
    </div>
    <div class="foot-col"><h4>Support</h4>
      <a href="{depth}support.html">Customer Support</a>
      <a href="{depth}faq.html">FAQ</a>
      <a href="{depth}privacy.html">Privacy Policy</a>
      <a href="{depth}terms.html">Terms</a>
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
<button class="to-top" id="toTop" type="button" aria-label="Back to top"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
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
    (img, kicker, title, sub, cta_href, cta_label). Still photos only.
    Both pills are outline-white on the homepage carousel (DJI homepage
    style); text sits in the top third, like DJI's."""
    parts = []
    for i, s in enumerate(slides):
        act = " active" if i == 0 else ""
        scrim = " strong" if s.get("scrim") else ""
        parts.append(f"""<div class="hero-slide{act}{scrim}" data-name="{esc(s['title'])}" style="background-image:url('{s['img']}')">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <p class="kicker">{s['kicker']}</p>
    <h1>{esc(s['title'])}</h1>
    <p class="hero-sub">{esc(s['sub'])}</p>
    <div class="hero-cta"><a class="btn btn-outline btn-lg" href="{esc(s['cta_href'])}">Learn More &rsaquo;</a><a class="btn btn-outline btn-lg" href="{esc(s['wa'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a></div>
  </div>
</div>""")
    return f"""<section class="hero hero-carousel" id="heroCarousel">
{''.join(parts)}
  <button class="hero-arrow prev" type="button" data-dir="-1" aria-label="Previous slide">&lsaquo;</button>
  <button class="hero-arrow next" type="button" data-dir="1" aria-label="Next slide">&rsaquo;</button>
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
/* hero — DJI ratio ~2.18:1 at desktop (1919x880). aspect-ratio lives ONLY in
   the desktop media query: at mobile widths the 520px min-height would
   otherwise force width = 520 x 2.18 = 1134px and overflow the viewport. */
.hero{position:relative;min-height:520px;background-size:cover;background-position:center;display:flex;align-items:center;justify-content:center;color:#fff;text-align:center}
@media(min-width:1101px){.hero{aspect-ratio:2.18/1;min-height:0}}
.hero-overlay{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.28),rgba(0,0,0,.18) 45%,rgba(0,0,0,.45))}
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
/* ROUND 7 — DJI full-bleed tiles: ONE card, photo fills the whole tile
   (4:3, ~936x702 at 1919px), text overlaid on it. Two gradient scrims —
   dark at the top (eyebrow/name/tagline) and dark at the bottom
   (price/CTAs) — fading to clear in the middle so the product stays fully
   visible. White text throughout: uniform across white studio shots and
   black shots alike, so the grid reads as one coherent set. 2 per row,
   16px gutters, no borders/shadows/radius. Full-bleed variant breaks out
   of the 1280px .wrap (16px side margins). */
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.grid-fullbleed{margin:0 16px;display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.card{position:relative;aspect-ratio:4/3;overflow:hidden;background:#111}
.card::before,.card::after{content:"";position:absolute;left:0;right:0;z-index:1;pointer-events:none}
.card::before{top:0;height:60%;background:linear-gradient(180deg,rgba(0,0,0,.62),rgba(0,0,0,.30) 55%,rgba(0,0,0,0))}
.card::after{bottom:0;height:55%;background:linear-gradient(0deg,rgba(0,0,0,.68),rgba(0,0,0,.32) 55%,rgba(0,0,0,0))}
.card-img{position:absolute;inset:0;display:block;padding:0;background:#111}
.card-img img{width:100%;height:100%;object-fit:cover;object-position:center;transition:transform .4s}
.card:hover .card-img img{transform:scale(1.04)}
.card-body{position:absolute;inset:0;z-index:2;display:flex;flex-direction:column;justify-content:space-between;align-items:center;text-align:center;padding:26px 28px;color:#fff;pointer-events:none}
.card-body a,.card-body .btn{pointer-events:auto}
.card-top{display:flex;flex-direction:column;gap:8px;align-items:center;min-width:0}
.card-foot{display:flex;flex-direction:column;gap:6px;align-items:center}
.card-cat{font-size:.78rem;text-transform:uppercase;letter-spacing:.16em;color:rgba(255,255,255,.85);font-weight:700}
.card-body h3{font-size:1.35rem;color:#fff;text-shadow:0 1px 12px rgba(0,0,0,.55);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-body h3 a{color:#fff}
.card-body h3 a:hover{color:rgba(255,255,255,.75)}
.card-tag{color:rgba(255,255,255,.92);font-size:.95rem;max-width:44ch;text-shadow:0 1px 10px rgba(0,0,0,.5);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card .price{color:#fff;text-shadow:0 1px 10px rgba(0,0,0,.5)}
.card .price .was{color:rgba(255,255,255,.7)}
.card .price-note{color:rgba(255,255,255,.75)}
.card .more-link{color:#fff}
.card .more-link:hover{color:rgba(255,255,255,.75)}
.card .card-cta{margin-top:8px}
.price{font-size:1.3rem;font-weight:800}
.price .was{font-size:.95rem;color:var(--mut);text-decoration:line-through;font-weight:400;margin-left:6px}
.price.por{font-size:1.1rem}
.price-note{font-size:.85rem;color:var(--mut)}
.more-link{display:inline-block;font-size:1rem;font-weight:600;color:var(--ink);padding:6px 0 2px}
.more-link:hover{color:var(--mut)}
.no-photo{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;background:var(--grey);color:var(--mut);text-align:center;padding:24px}
.no-photo span{font-size:1.05rem;font-weight:700;color:#1a1a1a}
.no-photo small{font-size:.88rem;max-width:34ch}
.card .no-photo{background:#1c1c1c;color:rgba(255,255,255,.8)}
.card .no-photo span{color:#fff}
/* ROUND 7 — Innovation tiles (DJI): same full-bleed overlay language as
   .card — photo fills the whole tile, text overlaid with twin scrims.
   2 per row inside the centred container; 3rd tile spans both columns as
   a wide horizontal feature — no orphan gap. .light keeps its class but
   renders the same white-on-scrim text (uniform set, no banded panel). */
.innov-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.feature-tile{position:relative;background:#000;color:#fff;overflow:hidden;min-height:615px}
.feature-tile.light{background:#111;color:#fff}
.feature-tile::before,.feature-tile::after{content:"";position:absolute;left:0;right:0;z-index:1;pointer-events:none}
.feature-tile::before{top:0;height:55%;background:linear-gradient(180deg,rgba(0,0,0,.72),rgba(0,0,0,.35) 55%,rgba(0,0,0,0))}
.feature-tile::after{bottom:0;height:50%;background:linear-gradient(0deg,rgba(0,0,0,.78),rgba(0,0,0,.4) 55%,rgba(0,0,0,0))}
.feature-tile .f-img{position:absolute;inset:0;background:#000}
.feature-tile .f-img img{width:100%;height:100%;object-fit:cover;object-position:center}
.feature-tile .f-body{position:relative;z-index:2;display:flex;flex-direction:column;justify-content:space-between;gap:10px;align-items:flex-start;text-align:left;padding:36px;min-height:615px}
.feature-tile .f-top{display:flex;flex-direction:column;gap:10px;align-items:flex-start}
.feature-tile.wide{grid-column:1/-1;min-height:380px}
.feature-tile.wide .f-body{min-height:380px;max-width:580px;padding:40px 48px}
.feature-tile.feat-banner{min-height:520px}
.feature-tile.feat-banner .f-body{min-height:520px}
.feature-tile .f-body p{color:rgba(255,255,255,.88)}
.feature-tile .f-body h2{font-size:clamp(1.7rem,3.4vw,2.4rem);color:#fff;text-shadow:0 1px 12px rgba(0,0,0,.45)}
.feature-tile .f-body .kicker{color:rgba(255,255,255,.8)}
.feature-tile .price .was{color:rgba(255,255,255,.7)}
.feature-tile .f-cta{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
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
/* hero carousel (DJI): rotating stills, ~5s autoplay, crossfade,
   bottom-left prev / current (bold + white bar) / next slide list.
   Text sits in the TOP third (DJI): huge THIN product name (~70px,
   weight 200), bold tagline ~24-28px, two outline-white pills. */
.hero-carousel{display:block;overflow:hidden;text-align:center}
.hero-slide{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transition:opacity 1s ease;display:flex;align-items:flex-start;justify-content:center}
.hero-slide.active{opacity:1;z-index:1}
.hero-slide .hero-content{padding:112px 20px 90px}
.hero-slide h1{font-size:clamp(2.6rem,5vw,4.4rem);font-weight:200;text-transform:uppercase;letter-spacing:.01em}
.hero-slide .hero-sub{font-size:clamp(1.4rem,2vw,1.75rem);font-weight:700}
.hero-slide.strong .hero-overlay{background:linear-gradient(180deg,rgba(0,0,0,.55),rgba(0,0,0,.32) 45%,rgba(0,0,0,.6))}
.hero-arrow{position:absolute;top:50%;transform:translateY(-50%);z-index:6;background:none;color:#fff;border:0;width:64px;height:96px;font-size:3.4rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;text-shadow:0 2px 14px rgba(0,0,0,.6);opacity:.9}
.hero-arrow:hover{opacity:1}
.hero-arrow.prev{left:8px}
.hero-arrow.next{right:8px}
.hero-list{position:absolute;left:48px;bottom:28px;z-index:5;display:flex;flex-direction:column;gap:8px;text-align:left}
.hero-list button{background:none;border:0;cursor:pointer;color:rgba(255,255,255,.65);font-size:14px;font-family:inherit;padding:2px 0 2px 16px;position:relative;text-align:left}
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
.video-thumb{position:relative;display:block;width:100%;aspect-ratio:16/9;padding:0;border:0;background:radial-gradient(120% 100% at 50% 0%,#2a2a2a 0%,#111 55%,#000 100%);cursor:pointer}
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
/* product subnav — second sticky black bar (DJI-style), 48px */
.subnav{position:sticky;top:64px;z-index:90;background:#000;color:#fff}
.subnav-inner{max-width:1280px;margin:0 auto;padding:0 20px;height:48px;display:flex;align-items:center;gap:22px}
.subnav-name{font-weight:800;font-size:1rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.subnav-links{display:flex;gap:22px;margin-left:auto}
.subnav-links a{font-size:.92rem;color:#cfcfcf}
.subnav-links a:hover{color:#fff}
.subnav .btn{padding:8px 16px;font-size:.88rem;margin-left:4px;flex:none}
/* product detail — black hero, one huge studio shot on a light-grey stage
   (audit P3 #12: ~78vh; #10: never wider than native — the img carries an
   inline max-width cap. White-background JPEGs sit on light grey, never
   as a white rectangle on black; the full image opens on tap via the
   existing lightbox). */
.detail-hero{position:relative;background:#000;color:#fff;text-align:center;padding:64px 20px 40px}
/* Round 6 -- DJI-style full-bleed hero photo (has-bg): the photo fills the
   band, text sits in the top third over a stronger scrim than the homepage
   hero (product photos are brighter). Desktop ~460-760px tall; the gallery
   now sits BELOW the hero on its own grey stage, not inside it. */
.detail-hero.has-bg{min-height:clamp(560px,86vh,860px);display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:110px 20px 80px;overflow:hidden}
/* Round 6b -- VIDEO-READY hero (boss 19 Nov 23:05: DJI's product hero is a
   LOOPING VIDEO, not a still). The hero image lives on .detail-hero-bg
   (not on the section) so it can move: with a video URL the <video>
   (autoplay muted loop playsinline, hero frame as poster) sits on top of
   it; without a video the bg div gets the slow Ken Burns zoom+pan so the
   hero still feels alive -- never a frozen still. Video URLs are external
   DJI mp4s (never base64); none assigned yet -- the video worker supplies
   them into products.json "hero_video" or DETAIL_HERO "video". */
.detail-hero-bg{position:absolute;inset:0;background-size:cover;background-position:center;z-index:0}
.detail-hero-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1}
/* Round 9 -- YouTube hero: the iframe covers the hero band exactly like
   object-fit:cover (16:9 video into any hero aspect). pointer-events:none
   so the hero text/buttons stay clickable and the video can never be
   paused by a stray tap; the cinematic still behind it covers the slow
   start while the player buffers. */
.detail-hero-yt{position:absolute;top:50%;left:50%;width:100%;height:56.25vw;min-width:177.78vh;min-height:100%;transform:translate(-50%,-50%);border:0;z-index:1;pointer-events:none}
/* Round 9 -- mobile: DJI's films carry burned-in captions in the bottom
   ~12% of the frame. On a portrait hero the 16:9 video shows its full
   height, so the captions collide with the hero's confirm-note (seen on
   Mini 3 mobile, 20 Nov). Overscan the video to 140% of the hero height
   (aspect-ratio keeps it 16:9) so the visible window always ends at
   ~86% of the frame -- the captions fall below the hero's bottom edge,
   the same crop the desktop cover fit already gives. A fixed vw
   overscan was tried first and failed: hero heights vary by content,
   so the crop must scale with the hero, not the viewport. */
@media(max-width:720px){.detail-hero-yt{width:auto;height:140%;min-width:0;min-height:140%;aspect-ratio:16/9}}
.detail-hero.has-bg .hero-overlay{z-index:2}
.detail-hero.has-bg .detail-hero-inner{z-index:3}
.detail-hero.has-bg.kenburns .detail-hero-bg{animation:kb-zoom 22s ease-in-out infinite alternate}
@keyframes kb-zoom{from{transform:scale(1) translate(0,0)}to{transform:scale(1.08) translate(-1.2%,-1%)}}
@media(prefers-reduced-motion:reduce){.detail-hero.has-bg.kenburns .detail-hero-bg{animation:none}}
.detail-hero.has-bg .hero-overlay{background:linear-gradient(180deg,rgba(0,0,0,.60),rgba(0,0,0,.45) 45%,rgba(0,0,0,.72))}
.detail-hero-inner{position:relative;z-index:1;width:100%}
.detail-hero.has-bg h1,.detail-hero.has-bg .tagline{text-shadow:0 2px 18px rgba(0,0,0,.6)}
/* Round 8 -- image-led feature sections (DJI pattern: huge image + bold
   heading + 1-2 lines). Wide scene shots fill the band; square/portrait
   product shots sit centred at full size so nothing is ever cropped. */
.feature-sec{background:#fff;text-align:center;padding:0 0 72px}
.feature-sec .feature-img.wide img{width:100%;height:72vh;object-fit:cover;display:block}
.feature-sec .feature-img:not(.wide) img{width:min(920px,100%);height:auto;display:block;margin:0 auto}
.feature-sec .feature-text{padding-top:40px}
.feature-sec h2{font-size:clamp(1.7rem,3.4vw,2.6rem);font-weight:700;margin:0 auto;max-width:24ch}
.feature-sec p{color:#425466;font-size:1.05rem;line-height:1.7;max-width:56ch;margin:16px auto 0}
/* Round 9 -- pacing variants. .alt: same shape, text left-aligned so
   neighbouring sections don't repeat. .overlay: wide scene goes
   full-bleed with the text overlaid bottom-left on a gradient scrim
   (DJI's own pattern) -- the image IS the section. */
.feature-sec.alt .feature-text{text-align:left}
.feature-sec.alt h2{margin:0;max-width:28ch}
.feature-sec.alt p{margin:16px 0 0}
.feature-sec.overlay{position:relative;padding:0;min-height:78vh;display:flex;align-items:flex-end;overflow:hidden;text-align:left}
.feature-sec.overlay .feature-img{position:absolute;inset:0}
.feature-sec.overlay .feature-img img{width:100%;height:100%;object-fit:cover}
.feature-sec.overlay::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 40%,rgba(0,0,0,.72));pointer-events:none}
.feature-sec.overlay .feature-text{position:relative;z-index:1;padding:0 40px 56px;text-align:left}
.feature-sec.overlay h2{color:#fff;margin:0;max-width:28ch;text-shadow:0 2px 18px rgba(0,0,0,.6)}
.feature-sec.overlay p{color:#e8e8e8;margin:16px 0 0;text-shadow:0 1px 12px rgba(0,0,0,.8)}

.detail-hero .kicker{color:#9a9a9a}
.detail-hero.has-bg .kicker{color:#d6d6d6;text-shadow:0 1px 12px rgba(0,0,0,.8)}
.detail-hero h1{margin:12px auto 0;max-width:22ch}
.detail-hero h1.dji-name{font-weight:200}
.detail-hero .tagline{font-size:clamp(1.05rem,2vw,1.25rem);font-weight:600;color:#d6d6d6;margin:14px auto 0;max-width:56ch}
.detail-hero .price{font-size:1.5rem;margin-top:18px}
.detail-hero .price .was{color:#9a9a9a}
.detail-hero .price-note{color:#9a9a9a}
.detail-hero.has-bg .price-note{color:#c8c8c8;text-shadow:0 1px 12px rgba(0,0,0,.8)}
.detail-actions{display:flex;gap:12px;flex-wrap:wrap;justify-content:center;margin:24px 0 0}
.detail-actions .btn{min-width:200px}
.detail-hero .confirm-note{color:#9a9a9a;font-size:.92rem;margin-top:16px}
.detail-hero.has-bg .confirm-note{color:#c8c8c8;text-shadow:0 1px 12px rgba(0,0,0,.8)}
/* Round 6 -- compare-link legibility over a bright hero photo. */
.detail-hero .compare-link{margin-top:26px!important}.detail-hero .compare-link button{color:#fff!important;text-shadow:0 1px 10px rgba(0,0,0,.9),0 0 6px rgba(0,0,0,.7)}
.detail-photo-wrap{background:#000;margin-top:0;min-height:78vh;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:zoom-in}
.detail-photo-wrap img{margin:0 auto;max-height:78vh !important;width:auto;max-width:100%;object-fit:contain}
.detail-photo-wrap .zoom-hint{color:#9a9a9a;font-size:.85rem;padding:14px 0 26px}
/* product gallery (audionic.co format): main image + thumb strip + dots
   + prev/next arrows. Single-photo products keep the plain block above.
   Gallery images are base64 data URIs (snapshot pushes are text-only). */
.g-main{position:relative;display:flex;align-items:center;justify-content:center;width:100%}
.g-main img{cursor:zoom-in}
.g-arrow{position:absolute;top:50%;transform:translateY(-50%);z-index:5;background:rgba(0,0,0,.55);color:#fff;border:0;width:48px;height:72px;font-size:2.4rem;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center}
.g-arrow.prev{left:12px}
.g-arrow.next{right:12px}
.g-thumbs{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;padding:20px 16px 0;max-width:960px;margin:0 auto}
.g-thumb{border:2px solid transparent;background:#fff;padding:2px;cursor:pointer}
.g-thumb img{width:72px;height:72px;object-fit:cover;display:block}
.g-thumb.active{border-color:#000}
.g-dots{display:flex;gap:8px;justify-content:center;padding:14px 0 0}
.g-dots button{width:8px;height:8px;border-radius:50%;border:0;background:#9a9a9a;cursor:pointer;padding:0}
.g-dots button.active{background:#000}
@media(max-width:720px){.g-thumb img{width:56px;height:56px}.g-arrow{width:38px;height:56px;font-size:2rem}}
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
#featured,#categories,#films,#why,#stories,#cta,#listing,#related-cats,#overview,#film,#about,#related,#innovation,#fields,#features,#compare,#endcard{scroll-margin-top:120px}
/* footer — compact, tidy, no tall empty dark block */
.site-footer{background:var(--black);color:#ddd;margin-top:0}
.footer-inner{max-width:1280px;margin:0 auto;padding:44px 20px 28px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1.4fr;gap:32px}
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
  .feature-tile,.feature-tile .f-body,.feature-tile.wide .f-body{min-height:0}
  .feature-tile .f-img{height:auto}
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
  .hero{min-height:360px}
  /* Mobile hero (boss's phone, 360-412px): title must fit on ONE line
     (small vw-based size, low floor — the old 2.6rem floor wrapped
     "DJI MAVIC 3 PRO" into two huge lines); pills auto-width, never
     full-width; slide list VISIBLE bottom-left (compact, ellipsis);
     chevrons parked bottom-right, clear of pills AND list; hero no
     longer a giant 520px block. Bottom content padding (118px) reserves
     the band the list + chevrons sit in. */
  .hero-content{padding:96px 16px 30px}
  .hero-content h1{font-size:clamp(1.55rem,7vw,2.3rem)}
  .hero-slide .hero-content{padding:88px 16px 118px}
  .hero-slide h1{font-size:clamp(1.55rem,7.2vw,2.4rem)}
  .hero-slide .hero-sub{font-size:clamp(1rem,4.4vw,1.25rem)}
  .hero-cta{gap:8px}
  .hero-cta .btn{min-width:0;width:auto;max-width:82vw;padding:10px 18px;font-size:.88rem}
  .hero-list{display:flex;left:16px;bottom:14px;gap:3px;max-width:56vw}
  .hero-list button{font-size:11px;padding:2px 0 2px 12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:56vw}
  .hero-carousel .scroll-hint{display:none}
  .hero-arrow{top:auto;bottom:12px;transform:none;width:44px;height:44px;font-size:1.9rem}
  .hero-arrow.prev{left:auto;right:60px}
  .hero-arrow.next{right:12px}
  /* ROUND 7 mobile cards: 4:3 tile at ~358px wide is ~268px tall — tighter
     type + padding so eyebrow/name/tagline + price/CTAs still fit. */
  .card-body{padding:18px 16px}
  .card-body h3{font-size:1.12rem;text-shadow:0 1px 3px rgba(0,0,0,.8),0 1px 12px rgba(0,0,0,.55)}
  .card-tag{font-size:.85rem;text-shadow:0 1px 3px rgba(0,0,0,.8),0 1px 12px rgba(0,0,0,.55)}
  .card .price{font-size:1.1rem;text-shadow:0 1px 3px rgba(0,0,0,.8),0 1px 12px rgba(0,0,0,.55)}
  .card .price-note{font-size:.78rem}
  .card-cta .btn{padding:8px 16px;font-size:.85rem}
  .feature-tile .f-body{padding:28px 24px}
  .feature-tile.wide .f-body{padding:28px 24px}
  /* Floating WhatsApp pill: icon-only circle on mobile (a labelled pill
     still covered card prices while scrolling — a fixed button can only
     be made minimal, never zero-footprint), and the footer gets safe
     bottom padding so the pill can never cover footer text. */
  .wa-float{right:12px;bottom:12px;width:44px;height:44px;padding:0;justify-content:center}
  .wa-float span{display:none}
  .wa-float svg{width:22px;height:22px}
  .to-top{right:12px;bottom:64px;width:44px;height:44px}
  .footer-bottom{padding-bottom:92px}
  .grid,.grid-fullbleed,.video-grid,.why-grid,.cat-tiles,.contact-grid{grid-template-columns:1fr}
  .cat-tile.wide{grid-column:auto;min-height:340px}
  .detail-actions .btn{min-width:0;width:100%}
  .subnav-links{display:none}
  .feature-tile .f-body{padding:28px 24px}
  .feature-tile.wide .f-body{padding:28px 24px}
}
/* fix-pass additions: category-card WhatsApp pill row, footer social icons,
   drones series strip, support pill row, grey pill. */
.card-cta{display:flex;gap:14px;align-items:center;justify-content:center;margin-top:14px;flex-wrap:wrap}
.card-cta .btn{padding:10px 20px;font-size:.92rem}
.foot-social{display:flex;gap:16px;margin-top:16px}
.foot-social a{color:#fff;opacity:.85}
.foot-social a:hover{opacity:1}
.foot-social svg{width:22px;height:22px;display:block}
.series-strip{background:#f2f3f5;padding:20px 0}
.series-strip-inner{max-width:1280px;margin:0 auto;display:flex;justify-content:center;gap:4px;flex-wrap:wrap}
.series-item{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 18px;color:#222;font-size:.9rem}
.series-item img{width:56px;height:40px;object-fit:contain}
.series-item svg{width:48px;height:32px}
.series-item:hover{color:#000}
.pill-row{display:flex;gap:10px;flex-wrap:wrap}
.pill-row .btn{padding:9px 18px}
.btn-grey{background:#f2f3f5;color:#111}
/* "Shot on" (DJI): small, centred, white on black above the films carousel */
.shot-on{font-size:1.35rem;font-weight:600;text-align:center;color:#fff}
.shot-on-sub{text-align:center;color:#bdbdbd;margin-top:8px}
/* films carousel dot indicators (DJI "Shot on") */
.films-dots{display:flex;gap:8px;justify-content:center;margin-top:20px}
.films-dots button{width:8px;height:8px;border-radius:50%;border:0;background:#5a5a5a;cursor:pointer;padding:0}
.films-dots button.active{background:#fff}
/* back-to-top (DJI floating button, bottom-right above the WhatsApp pill) */
.to-top{position:fixed;right:18px;bottom:84px;z-index:150;width:48px;height:48px;border-radius:50%;border:0;background:#000;color:#fff;cursor:pointer;box-shadow:0 10px 26px rgba(0,0,0,.35);display:none;align-items:center;justify-content:center}
.to-top.show{display:flex}
.to-top svg{width:22px;height:22px}
/* support head (DJI support is text-led): title + subtitle + search, no photo */
.support-head{padding:110px 20px 48px;text-align:center}
.support-head h1{font-size:clamp(2rem,4vw,3rem)}
.support-head p{font-size:1.15rem;color:var(--mut);margin-top:10px}
.support-head .support-search{border:1px solid var(--line)}
.support-head .support-search input{color:var(--txt)}
/* DJI product pages: 6-item spec strip on black, 2 rows x 3 */
.dji-top{background:#000;color:#fff;padding:0 0 56px;text-align:center}
.dji-intro-text{max-width:820px;margin:36px auto 0;padding:0 20px}
.dji-intro-text h2{font-size:clamp(1.5rem,3vw,2.1rem);margin-bottom:12px}
.dji-intro-text p{color:#cfcfcf;font-size:1.08rem}
.spec-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:18px 24px;max-width:960px;margin:0 auto;padding:56px 20px 8px;text-align:center}
.spec-strip .spec{font-size:1.02rem;font-weight:600;color:#e8e8e8;line-height:1.45}
.spec-strip .spec small{color:#9a9a9a}
.price-line{font-size:1.25rem;font-weight:800;margin-top:22px}
.price-line span{font-size:.95rem;color:#9a9a9a;font-weight:400}
/* DJI feature sections (black, stacked, headings in DJI's order) */
.dji-features{background:#000;color:#fff}
.dji-features .feat{max-width:820px;margin:0 auto;padding:34px 20px;border-top:1px solid #222;text-align:center}
.dji-features .feat:first-child{border-top:0}
.dji-features .feat h3{font-size:clamp(1.5rem,3vw,2.1rem);margin-bottom:12px}
.dji-features .feat p{color:#cfcfcf;font-size:1.02rem;max-width:70ch;margin:0 auto 10px}
.dji-features .feat p:last-child{margin-bottom:0}
.feat-chips{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:16px}
.feat-chips span{border:1px solid #444;border-radius:999px;padding:7px 16px;font-size:.92rem;color:#e8e8e8}
.feat-items{text-align:left;max-width:760px;margin:18px auto 0;display:grid;gap:14px}
.feat-items h4{font-size:1.05rem;margin-bottom:4px}
.feat-items p{color:#bdbdbd!important;font-size:.97rem}
.feat-quotes{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:1100px;margin:0 auto;padding:34px 20px}
.feat-quotes blockquote{border:1px solid #2a2a2a;padding:24px;text-align:left}
.feat-quotes .q-eye{color:#9a9a9a;text-transform:uppercase;letter-spacing:.16em;font-size:.75rem;font-weight:700}
.feat-quotes h4{margin:8px 0 10px;font-size:1.15rem}
.feat-quotes p{color:#cfcfcf;font-size:.97rem}
.dji-features .feat-note{color:#9a9a9a!important;font-size:.9rem}
.dji-footnote{max-width:820px;margin:0 auto;padding:30px 20px 8px;color:#9a9a9a;font-size:.9rem;text-align:center}
/* DJI end card: tagline + spec recap + price + WhatsApp */
.end-card{background:#000;color:#fff;text-align:center;padding:64px 20px;border-top:1px solid #222}
.end-card h2{font-size:clamp(1.9rem,4vw,2.75rem);margin-bottom:8px}
.end-card .end-specs{color:#bdbdbd;max-width:60ch;margin:12px auto 0;font-size:1rem}
.end-card .price-line{margin-top:20px}
.end-card .btn{margin-top:22px}
/* drones featured banner (DJI Camera Drones Flip banner, framed/inset):
   light-grey gradient, text top-centre, product photo bottom-centre */
@media(max-width:900px){.feat-quotes{grid-template-columns:1fr}.spec-strip{grid-template-columns:repeat(2,1fr)}}
@media(max-width:720px){.detail-photo-wrap{min-height:0}.detail-photo-wrap img{max-height:60vh !important}.detail-hero.has-bg{min-height:440px;padding:104px 20px 56px}.feature-tile.feat-banner,.feature-tile.feat-banner .f-body{min-height:460px}}
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
if(dp&&!document.getElementById('galleryMain')){dp.addEventListener('click',function(){openLB(dp.querySelector('img').src,dp.querySelector('img').alt);});}
// product gallery: switch the main image + active thumb/dot; the
// lightbox opens the CURRENTLY shown image. Thumbs carry data-full for
// extras (their base64 data URIs) — the primary image's data URI is
// never copied into an attribute (it is read once from the main img's src).
var gm=document.getElementById('galleryMain');
if(gm){
  var gThumbs=Array.prototype.slice.call(document.querySelectorAll('.g-thumb'));
  var gDots=Array.prototype.slice.call(document.querySelectorAll('.g-dot'));
  var gSrcs=gThumbs.map(function(t,i){return i===0?gm.src:(t.getAttribute('data-full')||gm.src);});
  var gIdx=0;
  function gShow(i){
    gIdx=(i+gSrcs.length)%gSrcs.length;
    gm.src=gSrcs[gIdx];
    var cap=gThumbs[gIdx].getAttribute('data-cap');
    if(cap){gm.style.cssText=cap;}
    gm.alt=gThumbs[gIdx].getAttribute('data-alt')||gm.alt;
    gThumbs.forEach(function(t,j){t.classList.toggle('active',j===gIdx);});
    gDots.forEach(function(d,j){d.classList.toggle('active',j===gIdx);});
  }
  gThumbs.forEach(function(t,i){t.addEventListener('click',function(e){e.stopPropagation();gShow(i);});});
  gDots.forEach(function(d,i){d.addEventListener('click',function(e){e.stopPropagation();gShow(i);});});
  document.querySelectorAll('.g-arrow').forEach(function(a){a.addEventListener('click',function(e){e.stopPropagation();gShow(gIdx+parseInt(a.getAttribute('data-dir'),10));});});
  gm.addEventListener('click',function(){openLB(gm.src,gm.alt);});
}
// category filter + sort
var grid=document.getElementById('catGrid');
if(grid){
  var brandSel=document.getElementById('brandFilter'),sortSel=document.getElementById('sortSel'),countEl=document.getElementById('resultCount');
  function applyFilter(){
    var cards=Array.prototype.slice.call(grid.querySelectorAll('.card'));
    var b=brandSel?brandSel.value:'';
    var visible=cards.filter(function(c){var ok=!b||c.dataset.brand===b;c.style.display=ok?'':'none';return ok;});
    var s=sortSel?sortSel.value:'featured';
    // 'featured' keeps the generator's order (drones are flagship-first
    // like DJI); any other value re-sorts the visible cards.
    if(s!=='featured')visible.sort(function(a,c){
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
// hero carousel: rotating stills, ~5s autoplay, crossfade, bottom-left
// prev / current / next slide list; click a list name to jump; pause on
// real mouse hover only — touch never pauses (see below).
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
  function hStart(){hStop();hTimer=setInterval(function(){hGo(hIdx+1);},5000);}
  function hStop(){if(hTimer){clearInterval(hTimer);hTimer=null;}}
  hList.forEach(function(b){b.addEventListener('click',function(){hGo(parseInt(b.dataset.go,10));hStart();});});
  hc.querySelectorAll('.hero-arrow').forEach(function(a){a.addEventListener('click',function(){hGo(hIdx+parseInt(a.dataset.dir,10));hStart();});});
  // Pause ONLY on a real mouse hover. On touch screens a tap fires an
  // emulated mouseenter with no matching mouseleave, which used to stop
  // the autoplay forever after the first tap on the hero.
  function hHover(e){if(e.pointerType==='mouse'){hStop();}}
  function hUnhover(e){if(e.pointerType==='mouse'){hStart();}}
  hc.addEventListener('pointerenter',hHover);
  hc.addEventListener('pointerleave',hUnhover);
  // Safety net: any touch end or scroll restarts autoplay, so a stray
  // pause can never freeze the hero on a phone.
  hc.addEventListener('touchend',hStart,{passive:true});
  window.addEventListener('scroll',function(){if(!hTimer){hStart();}},{passive:true});
  document.addEventListener('visibilitychange',function(){if(document.hidden){hStop();}else{hStart();}});
  hGo(0);hStart();
}
// films carousel: centre card ~1230px, side cards peeking, ‹ › arrows,
// dot indicators below (DJI "Shot on").
var fc=document.getElementById('filmsCarousel');
if(fc){
  var fTrack=fc.querySelector('.films-track');
  var fCards=Array.prototype.slice.call(fTrack.querySelectorAll('.video-card'));
  var fIdx=0;
  var fDotsWrap=document.createElement('div');
  fDotsWrap.className='films-dots';
  fCards.forEach(function(c,i){var d=document.createElement('button');d.type='button';d.setAttribute('aria-label','Go to film '+(i+1));d.addEventListener('click',function(){fGo(i);});fDotsWrap.appendChild(d);});
  fc.appendChild(fDotsWrap);
  var fDots=Array.prototype.slice.call(fDotsWrap.querySelectorAll('button'));
  function fLayout(){
    var cardW=fCards[0].getBoundingClientRect().width+16;
    var wrapW=fc.getBoundingClientRect().width;
    var off=(wrapW-fCards[0].getBoundingClientRect().width)/2-fIdx*cardW;
    fTrack.style.transform='translateX('+off+'px)';
  }
  function fGo(i){fIdx=(i+fCards.length)%fCards.length;fLayout();fDots.forEach(function(d,j){d.classList.toggle('active',j===fIdx);});}
  fc.querySelector('.films-arrow.prev').addEventListener('click',function(){fGo(fIdx-1);});
  fc.querySelector('.films-arrow.next').addEventListener('click',function(){fGo(fIdx+1);});
  window.addEventListener('resize',fLayout);
  fLayout();
}
// back-to-top button
var toTop=document.getElementById('toTop');
if(toTop){
  window.addEventListener('scroll',function(){toTop.classList.toggle('show',window.scrollY>600);},{passive:true});
  toTop.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
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
    # Innovation tiles — flagship-first (ROUND 6): Mavic 3 Pro (wide),
    # Air 3S, Mini 4 Pro. featured_ids / feats[3:] (homepage product
    # tiles) are NOT reordered.
    f1, f2, f3 = (by_id(i) for i in INNOVATION_IDS)
    def feature_tile(p, light=False, wide=False, eyebrow=None, tagline=None):
        # ROUND 7: full-bleed overlay — photo fills the tile, text over it
        # (f-top) with CTAs at the bottom; white pill on the dark scrim.
        cls = "feature-tile light" if light else "feature-tile"
        if wide: cls += " wide"
        view_cls = "btn-light"
        # DJI tile copy (eyebrow + tagline) where the product matches and
        # the copy is verified; otherwise the shop's own line.
        eyebrow = eyebrow if eyebrow is not None else (esc(p['brand']) + " &middot; " + esc(CATS[p['category']]['label']))
        tagline = tagline if tagline is not None else p['tagline']
        return f"""<div class="{cls} reveal">
  <div class="f-img"><img src="{img_uri(p['photo_full'])}" alt="{esc(p['name'])}" loading="lazy"></div>
  <div class="f-body"><div class="f-top"><p class="kicker">{eyebrow}</p>
  <h2>{esc(p['name'])}</h2><p>{esc(tagline)}</p>
  {price_html(p)}</div>
  <div class="f-cta"><a class="btn {view_cls}" href="products/{p['slug']}.html">View Details</a>
  <a class="more-link" style="color:inherit" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry &rsaquo;</a></div></div></div>"""
    # (a) hero carousel — DJI's exact slide copy for the matching products.
    # The Security Cameras slide is DROPPED (its photo is deleted — a
    # generic stock image, 2.04x upscaled). Mini 3 Pro's product page is
    # retired, so its slide uses DJI's listing eyebrow ("Mini Camera
    # Drone", live-browser study) and keeps the factual Fly More Combo
    # line — a product fact, not an invention. 4 slides remain.
    slides = [
        {"img": hero_uri('air3s.jpg'), "kicker": "Dual-Camera Drone for Travel Photography",
         "title": "DJI Air 3S", "sub": "Chase the View",
         "cta_href": "products/dji-air-3s.html", "wa": wa_link("DJI Air 3S")},
        {"img": hero_uri('mavic3-cine.jpg'), "kicker": "Triple-Lens Camera Drone",
         "title": "DJI Mavic 3 Pro", "sub": "Inspiration in Focus",
         "cta_href": "products/dji-mavic-3-pro.html", "wa": wa_link("DJI Mavic 3 Pro")},
        {"img": hero_uri('drone.jpg'), "kicker": "Mini Camera Drone",
         "title": "DJI Mini 3 Pro", "sub": "Mini 3 Pro Fly More Combo — pro features, Mini size.",
         "cta_href": "products/dji-mini-3-pro.html", "wa": wa_link("DJI Mini 3 Pro"),
         "scrim": True},
        {"img": hero_uri('from-air.jpg'), "kicker": "AK Khan Enterprises \u00b7 Quetta",
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
<h2 class="shot-on reveal">Shot on</h2>
<p class="shot-on-sub reveal">Official DJI films for the drones on our shelves.</p>
</div>
<div class="films-carousel" id="filmsCarousel">
<div class="films-track">{vids}</div>
<button class="films-arrow prev" type="button" aria-label="Previous film">&lsaquo;</button>
<button class="films-arrow next" type="button" aria-label="Next film">&rsaquo;</button>
</div>
<p style="text-align:center;margin-top:26px"><a class="btn btn-light" href="explore.html">Watch all 12 films on Explore</a></p>
</section>
<section class="sec" id="innovation"><div class="wrap">
{section_head('Innovation', 'Standing at the Forefront of Innovation', 'As we explore new technology, we push the capabilities of what is possible, driving progress through continuous innovation.')}
<div class="innov-grid">
{feature_tile(f1, wide=True, eyebrow="Multiple Focal Length Triple-Lens Flagship Camera Drone", tagline="Inspiration in Focus")}
{feature_tile(f2, light=True, eyebrow="Dual-Camera Drone for Travel Photography", tagline="Chase the View")}
{feature_tile(f3, eyebrow="All-In-One Mini Drone", tagline="Mini to the Max")}
</div>
</div></section>
<section class="sec grey" id="fields"><div class="wrap">
<div class="sec-head reveal"><h2>Explore DJI Products in Different Fields</h2></div>
<div class="field-grid">
<a class="field-tile reveal" style="background-image:url('{hero_uri('shot-canyon.jpg')}')" href="explore.html"><div><h3>Video Production</h3><p>Professional Aerial and Ground Filmmaking Tools</p><span class="more-link">Learn More &rsaquo;</span></div></a>
<a class="field-tile reveal" style="background-image:url('{hero_uri('field-enterprise.jpg')}')" href="categories/drones.html"><div><h3>Enterprise</h3><p>Drone Solutions for a New Generation of Work</p><span class="more-link">Learn More &rsaquo;</span></div></a>
<a class="field-tile reveal" style="background-image:url('{hero_uri('field-agri.jpg')}')" href="search.html?q=DJI+Agras"><div><h3>Agriculture</h3><p>Efficient and Intelligent Agricultural Solution</p><span class="more-link">Learn More &rsaquo;</span></div></a>
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
    # ROUND 6 display order (render-time only; products.json itself is
    # never reordered — id == array index).
    items = order_category(c, [p for p in products if p["category"] == c])
    brands = sorted(set(p["brand"] for p in items))
    opts = "".join(f'<option value="{esc(b)}">{esc(b)}</option>' for b in brands)
    # Related-category tiles: real existing photos only (the old banner
    # images are deleted). One representative photo per category.
    def rel_tile(o):
        kind, name = RELATED_TILE[o]
        uri = hero_uri(name) if kind == "hero" else img_uri(f"images/full/{name}")
        return (f'<a class="cat-tile" style="background-image:url(\'{uri}\');min-height:300px" href="{o}.html">'
                f'<div><h3>{CATS[o]["nav"]}</h3><p>{esc(CATS[o]["blurb"])}</p></div></a>')
    others = "".join(rel_tile(o) for o in CAT_ORDER if o != c)
    # DJI Camera Drones series strip (~120px): small REAL product
    # thumbnails per series (400px thumbs shown at ~56px — downscale
    # only), each linking to a real search for that DJI series. Compare
    # and Shop Now are real too. No quiz (no quiz content exists), no
    # Accessories/RC/Inspire (no such products in the catalogue).
    strip = ""
    if c == "drones":
        series = [("Mavic", 4), ("Air", 2), ("Mini", 0), ("Neo", 5),
                  ("Avata", 6), ("Matrice", 8), ("Agras", 9)]
        strip_items = "".join(
            f'<a class="series-item" href="../search.html?q={urllib.parse.quote("DJI " + s)}">'
            f'<img src="{img_uri(by_id(pid)["photo_thumb"])}" alt="DJI {s}" loading="lazy"><span>DJI {s}</span></a>'
            for s, pid in series)
        strip_items += ('<a class="series-item" href="../compare.html">' + COLS_SVG + '<span>Compare</span></a>'
                  '<a class="series-item" href="' + wa_link() + '" target="_blank" rel="noopener">' + BAG_SVG + '<span>Shop Now</span></a>')
        strip = f'<div class="series-strip"><div class="series-strip-inner">{strip_items}</div></div>'
    h1 = CATS[c].get("h1", CATS[c]["label"])
    # Banner slot (audit P3 #13): only when a native-wide (>=1919x513)
    # photo exists — drones only (hero-drone.jpg is a 2560x684 DJI frame).
    # Every other category gets DJI's text-led head and no banner div.
    banner = ""
    featured = ""
    if c == "drones":
        banner = ('<div class="cat-banner" style="background-image:url(\''
                  + hero_uri("hero-drone.jpg") + '\')" role="img" aria-label="Drones"></div>')
        m4p = by_id(0)
        # ROUND 7 FIX 1: full-bleed feature-tile banner (was a small
        # 600px photo centred in a wide light-grey void — read as
        # empty/cheap). Same photo, same scrims and text positions as
        # the DJI tiles, so the Mini 4 Pro fills the banner edge to
        # edge; WhatsApp stays the primary CTA.
        featured = f"""<div class="feature-tile feat-banner">
  <div class="f-img"><img src="{img_uri(m4p['photo_full'])}" alt="DJI Mini 4 Pro" loading="lazy"></div>
  <div class="f-body"><div class="f-top"><p class="kicker">All-In-One Mini Drone</p>
  <h2>DJI Mini 4 Pro</h2><p>Mini to the Max</p>
  {price_html(m4p)}</div>
  <div class="f-cta"><a class="btn btn-light" href="{wa_link(m4p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
  <a class="more-link" style="color:inherit" href="../products/{m4p['slug']}.html">Learn More &rsaquo;</a></div></div></div>"""
    # Drones comparison table (DJI: "Which camera drone is suitable for
    # you?") — verified DJI values + our real PKR prices, never DJI USD.
    compare_sec = ""
    if c == "drones":
        head_cells = "".join(
            f'<th><a href="../products/{slug}.html">{esc(next(p for p in products if p["slug"] == slug)["name"])}</a></th>'
            for slug, _ in DJI_COMPARE)
        rows = ""
        for label, idx in DJI_COMPARE_ROWS:
            cells = "".join(f"<td>{esc(vals[idx])}</td>" for _, vals in DJI_COMPARE)
            rows += f"<tr><th>{esc(label)}</th>{cells}</tr>"
        compare_sec = f"""<section class="sec grey" id="compare"><div class="wrap">
<div class="sec-head reveal"><h2>Which camera drone is suitable for you?</h2></div>
<div style="overflow-x:auto"><table class="compare-table"><tr><th></th>{head_cells}</tr>{rows}</table></div>
<p style="text-align:center;margin-top:22px"><a class="more-link" href="../compare.html">Consumer Drones Comparison — Compare Now &rsaquo;</a></p>
</div></section>"""
    brand_link = ""
    if c == "audio":
        brand_link = ('<div class="wrap" style="text-align:center;padding:0 20px 24px">'
                      '<a class="btn btn-dark" href="../brands/audionic.html">Audionic — view the brand page &rsaquo;</a></div>')
    body = f"""
{strip}<section class="cat-head"><div class="wrap">
<p class="kicker">AK Khan Enterprises</p>
<h1>{esc(h1)}</h1>
<p class="cat-sub">{esc(CATS[c]['intro'])}</p>
</div></section>
{brand_link}
{banner}{featured}
<section class="sec" id="listing"><div class="wrap">
{section_head(CATS[c]['label'], f"All {CATS[c]['label']} — {len(items)} products", 'Filter by brand or sort the list. Prices shown where the shop has confirmed one; everything else is confirmed on WhatsApp.')}
<div class="toolbar">
  <label>Brand <select id="brandFilter"><option value="">All brands</option>{opts}</select></label>
  <label>Sort <select id="sortSel"><option value="featured" selected>Featured</option><option value="name-asc">Name A–Z</option><option value="name-desc">Name Z–A</option><option value="price-asc">Price: low to high</option><option value="price-desc">Price: high to low</option></select></label>
  <span class="count" id="resultCount">{len(items)} products</span>
</div>
</div>
<div class="grid-fullbleed" id="catGrid">{''.join(card(p, depth="../", buy=True) for p in items)}</div>
</section>
{compare_sec}
<section class="sec grey" id="related-cats"><div class="wrap">
{section_head('Keep exploring', 'Related categories', '')}
<div class="cat-tiles">{others}</div>
</div></section>
{cta_band('../')}
"""
    write(f"categories/{c}.html", chrome("../", f"{CATS[c]['label']} — AK Khan Enterprises, Quetta",
        f"{CATS[c]['label']} at AK Khan Enterprises, Quetta. {CATS[c]['intro']}", body))

# ----- Audionic brand page (DJI-style brand header, B/W only) -----
# ONLY the 11 Audionic products (ids 30-40), each card linking to its
# detail page. Names are never changed here.
def build_audionic():
    # ROUND 6 display order: the same 11 Audionic products (ids 30-40),
    # flagship-first. AUDIONIC_IDS itself is unchanged (the nav
    # mega-menu takes its first 3 — deliberately NOT reordered).
    items = [by_id(i) for i in AUDIO_ORDER]
    body = f"""
<section class="cat-head"><div class="wrap">
<p class="kicker">Brands</p>
<h1>Audionic</h1>
<p class="cat-sub">Audionic sound — earbuds, Bluetooth speakers, soundbars, home theatre, party speakers and more.</p>
</div></section>
<section class="sec" id="listing"><div class="wrap">
{section_head('Audionic', 'All Audionic — 11 products', 'Prices shown where the shop has confirmed one; everything else is confirmed on WhatsApp.')}
</div>
<div class="grid-fullbleed">{''.join(card(p, depth="../", buy=True) for p in items)}</div>
</section>
{cta_band('../')}
"""
    write("brands/audionic.html", chrome("../", "Audionic — AK Khan Enterprises, Quetta",
        "Audionic at AK Khan Enterprises, Quetta — earbuds, Bluetooth speakers, soundbars, home theatre, party speakers and more.", body))

# ----- DJI product pages: spec strip, intro, feature sections, end card -----
def dji_price_line(p):
    if p.get("price_pkr"):
        return (f'<p class="price-line">From {fmt_pkr(p["price_pkr"])} '
                '<span>&mdash; confirmed on WhatsApp</span></p>')
    return ('<p class="price-line">Price on request '
            '<span>&mdash; confirmed on WhatsApp</span></p>')

def dji_features_html(slug):
    out = []
    for f in DJI_FEATURES[slug]:
        if "quotes" in f:
            cards = "".join(
                f'<blockquote><p class="q-eye">{esc(e)}</p><h4>{esc(n)}</h4><p>{esc(t)}</p></blockquote>'
                for e, n, t in f["quotes"])
            out.append(f'<div class="feat-quotes">{cards}</div>')
            continue
        parts = []
        h = f.get("h")
        if isinstance(h, list):
            parts.append("".join(f"<h3>{esc(x)}</h3>" for x in h))
        elif h:
            parts.append(f"<h3>{esc(h)}</h3>")
        if f.get("b"):
            parts.append(f"<p>{esc(f['b'])}</p>")
        if f.get("b2"):
            parts.append(f"<p>{esc(f['b2'])}</p>")
        if f.get("chips"):
            chips = "".join(f"<span>{esc(x)}</span>" for x in f["chips"])
            parts.append(f'<div class="feat-chips">{chips}</div>')
        if f.get("items"):
            items = "".join(
                f"<div><h4>{esc(t)}</h4><p>{esc(d)}</p></div>" for t, d in f["items"])
            parts.append(f'<div class="feat-items">{items}</div>')
        if f.get("note"):
            parts.append(f'<p class="feat-note">{esc(f["note"])}</p>')
        out.append('<div class="feat reveal">' + "".join(parts) + "</div>")
    out.append('<p class="dji-footnote">Photos and films on this page are DJI&rsquo;s official product images and films.</p>')
    return ('<section class="dji-features" id="features">'
            '<div class="sec-head reveal"><p class="kicker">DJI</p><h2>Features</h2></div>'
            + "".join(out) + "</section>")

# ----- product pages (DJI-style: black hero, huge shot, no invented specs) -----
def build_product(p):
    # Gallery = [primary photo] + p["gallery"] extras (audionic.co format).
    # Extras are embedded as base64 data URIs via img_uri(), exactly like
    # the primary photo: the GitHub snapshot push rejects binary files,
    # so no gallery photo may be referenced by URL (verified 19 Nov:
    # push-files errors "not UTF-8" on any JPEG). "file": True still means
    # the thumb carries data-full (the JS switches the main image from it);
    # the primary's data URI is read once from the main img's src.
    # One photo total -> exactly the old single-image block (no strip,
    # dots or arrows). Missing gallery files are skipped, never fatal.
    g_items = []
    if p.get("photo_full"):
        g_items.append({"src": img_uri(p["photo_full"]),
                        "thumb": img_uri(p["photo_thumb"]) if p.get("photo_thumb") else img_uri(p["photo_full"]),
                        "cap": img_cap(p["photo_full"]),
                        "alt": f"{p['name']} — product photo",
                        "file": False})
    for g in p.get("gallery", []) or []:
        full = g.get("full", "")
        thumb = g.get("thumb", "") or full
        if not full or not (STAGING / full).is_file():
            continue
        g_items.append({"src": img_uri(full),
                        "thumb": (img_uri(thumb)
                                  if thumb and (STAGING / thumb).is_file()
                                  else img_uri(full)),
                        "cap": img_cap(full),
                        "alt": f"{p['name']} — product photo",
                        "file": True})

    # Round 8 -- gallery main = dramatic showpiece (dark-stage / scene) when
    # one exists; the light-stage primary stays as a thumb (file=True so its
    # data-full switches the main back). JS restores the main from gm.src
    # for thumb 0 (the showpiece) and uses data-full for the rest.
    show = SHOWPIECE.get(p["id"])
    if show and g_items and show != p.get("photo_full") and (STAGING / show).is_file():
        g_items.insert(0, {"src": img_uri(show),
                           "thumb": img_uri(SHOWPIECE_THUMB.get(p["id"], show)),
                           "cap": img_cap(show),
                           "alt": f"{p['name']} — product photo",
                           "file": False})
        g_items[1]["file"] = True
    if len(g_items) > 1:
        thumbs = "".join(
            f'<button class="g-thumb{" active" if i == 0 else ""}" type="button"'
            + (f' data-full="{esc(it["src"])}"' if it["file"] else "")
            + f' data-cap="{esc(it["cap"])}" data-alt="{esc(it["alt"])}" aria-label="View photo {i + 1} of {len(g_items)}">'
              f'<img src="{it["thumb"]}" alt="Photo {i + 1} of {esc(p["name"])}" loading="lazy"></button>'
            for i, it in enumerate(g_items))
        dots = "".join(
            f'<button class="g-dot{" active" if i == 0 else ""}" type="button" aria-label="Go to photo {i + 1}"></button>'
            for i in range(len(g_items)))
        main = g_items[0]
        gallery = (f"""<div class="detail-photo-wrap" id="detailPhoto"><div class="g-main">"""
                   f"""<img id="galleryMain" src="{main["src"]}" alt="{esc(main["alt"])}" style="{esc(main["cap"])}">"""
                   f"""<button class="g-arrow prev" type="button" data-dir="-1" aria-label="Previous photo">&lsaquo;</button>"""
                   f"""<button class="g-arrow next" type="button" data-dir="1" aria-label="Next photo">&rsaquo;</button></div>"""
                   f"""<div class="g-thumbs">{thumbs}</div><div class="g-dots">{dots}</div>"""
                   f"""<p class="zoom-hint">Tap the photo to view fullscreen. Tap again to zoom.</p></div>""")
    elif g_items:
        it = g_items[0]
        gallery = f"""<div class="detail-photo-wrap" id="detailPhoto"><img src="{it["src"]}" alt="{esc(it["alt"])}" style="{esc(it["cap"])}"><p class="zoom-hint">Tap the photo to view fullscreen. Tap again to zoom.</p></div>"""
    else:
        gallery = ('<div class="detail-photo-wrap" style="cursor:default"><div class="no-photo" style="background:transparent;min-height:40vh;color:#555">'
                   '<span style="color:#1a1a1a">Photo on request</span>'
                   '<small style="color:#555">No photo of this exact unit is available yet. Ask on WhatsApp and the shop will send a photo of the exact unit in stock.</small></div></div>')
    rel = related(p)
    film_anchor = '<a href="#film">Film</a>' if p.get("video_ids") and any(v != FAILED_VIDEO and v in VID_TITLE for v in p["video_ids"]) else ""
    # DJI's product hero: solid Buy pill + outline Watch Video pill. The buy
    # action here is WhatsApp Inquiry (solid); products with a verified film
    # get the outline "Watch Film" pill instead of "Add to Compare" — the
    # compare action stays as a small link underneath, so nothing is lost.
    has_film = bool(film_anchor)
    if has_film:
        second_pill = '<a class="btn btn-outline btn-lg" href="#film">Watch Film &rsaquo;</a>'
        compare_link = f'<p class="compare-link" style="margin-top:14px"><button class="more-link" type="button" data-compare="{esc(p["slug"])}" style="background:none;border:0;cursor:pointer;font:inherit;color:#ccc">+ Add to Compare</button></p>'
    else:
        second_pill = f'<button class="btn btn-outline btn-lg" type="button" data-compare="{esc(p["slug"])}">Add to Compare</button>'
        compare_link = ""
    # DJI product pages (Mavic 3 Pro, Air 3S, Mini 4 Pro only): DJI's exact
    # hero copy, 6-item spec strip, price OUT of the hero into a slim line
    # under the spec strip, verbatim intro, DJI feature sections in order,
    # and an end card (tagline + spec recap + price + WhatsApp).
    is_dji = p["slug"] in DJI_HERO
    if is_dji:
        eyebrow, tagline = DJI_HERO[p["slug"]]
        kicker_html = f'<p class="kicker">{esc(eyebrow)}</p>' if eyebrow else ""
        hero_head = f"""{kicker_html}
  <h1 class="dji-name">{esc(p['name'])}</h1>
  <p class="tagline">{esc(tagline)}</p>
  {price_html(p)}"""
        intro_h, intro_p = DJI_INTRO[p["slug"]]
        if intro_h:
            intro_html = (f'<div class="dji-intro-text"><h2>{esc(intro_h)}</h2>'
                          f'<p>{esc(intro_p)}</p></div>')
        else:
            intro_html = f'<div class="dji-intro-text"><p>{esc(intro_p)}</p></div>'
        specs = "".join(f'<div class="spec">{esc(s)}</div>' for s in DJI_SPECS[p["slug"]])
        dji_top = f"""<section class="dji-top">
<div class="spec-strip">{specs}</div>
{dji_price_line(p)}
{intro_html}
</section>"""
        features = dji_features_html(p["slug"])
        endcard = f"""<section class="end-card" id="endcard">
<h2>{esc(tagline)}</h2>
<p class="end-specs">{esc(" · ".join(DJI_SPECS[p['slug']]))}</p>
{dji_price_line(p)}
<a class="btn btn-light btn-lg" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
</section>"""
        feat_anchor = '<a href="#features">Features</a>'
        confirm_html = ""
    else:
        hero_head = f"""<p class="kicker">{esc(p['brand'])} &middot; {esc(CATS[p['category']]['label'])}</p>
  <h1>{esc(p['name'])}</h1>
  <p class="tagline">{esc(p['tagline'])}</p>
  {price_html(p)}"""
        dji_top = ""
        features = ""
        endcard = ""
        feat_anchor = ""
        confirm_html = '<p class="confirm-note">Full specifications and today&rsquo;s price are confirmed on WhatsApp for this exact model.</p>'
    # Round 6 -- DJI-style full-bleed hero photo behind the name/tagline.
    # The gallery moves OUT of the hero section (it sits on its own grey
    # stage below); the hero keeps only the text + buttons, like DJI.
    # Round 6b -- VIDEO-READY: with a hero_video URL the hero is a looping
    # <video> (autoplay muted loop playsinline, hero frame as poster);
    # without one the bg div gets the Ken Burns class so the still moves.
    # Round 9 -- YOUTUBE HERO: with a "yt" id the hero is DJI's official
    # YouTube film in a cover-fit iframe (autoplay muted loop via the
    # playlist trick, no controls). TESTED 20 Nov in the VM browser:
    # plays + loops (Mini 2 film: t=60s film frame, t=80s re-buffer
    # spinner at the loop point, t=100s early-film frame again), no
    # player chrome. Slow start (~5-10s black through this VM's proxy)
    # is covered by the cinematic still behind the iframe. file://
    # previews show YouTube Error 153 -- the live https site does not.
    hero_rel, hero_pos, hero_video, hero_yt = detail_hero_for(p)
    if hero_rel and (STAGING / hero_rel).is_file():
        hero_uri_str = detail_hero_uri(hero_rel)
        bg_div = ('  <div class="detail-hero-bg" style="background-image:url(\'' + hero_uri_str + '\');'
                  'background-position:' + hero_pos + '"></div>')
        if hero_video:
            video_tag = ('  <video class="detail-hero-video" autoplay muted loop playsinline poster="' + hero_uri_str + '">'
                         '<source src="' + esc(hero_video) + '" type="video/mp4"></video>')
            hero_cls = "detail-hero has-bg has-video"
        elif hero_yt:
            yt_src = ("https://www.youtube.com/embed/" + hero_yt +
                      "?autoplay=1&mute=1&loop=1&playlist=" + hero_yt +
                      "&controls=0&playsinline=1&rel=0&modestbranding=1")
            video_tag = ('  <iframe class="detail-hero-yt" src="' + yt_src + '" '
                         'allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>')
            hero_cls = "detail-hero has-bg has-yt"
        else:
            video_tag = ""
            hero_cls = "detail-hero has-bg kenburns"
        hero_parts = ['<section class="' + hero_cls + '" id="overview">', bg_div]
        if video_tag:
            hero_parts.append(video_tag)
        hero_parts.append('  <div class="hero-overlay"></div>')
        hero_parts.append('  <div class="detail-hero-inner">')
        hero_open = "\n".join(hero_parts)
        hero_close = "  </div>\n</section>"
    else:
        hero_open = '<section class="detail-hero" id="overview">\n  <div class="detail-hero-inner">'
        hero_close = "  </div>\n</section>"

    # Round 8 -- image-led feature sections (FEATURES map, filled from the
    # workers' verified data). The subnav "Features" link appears when the
    # product has image-led sections or DJI's own feature blocks.
    features_new = features_html(p)
    if features_new or is_dji:
        feat_anchor = '<a href="#features">Features</a>'

    body = f"""
<div class="subnav"><div class="subnav-inner">
<span class="subnav-name">{esc(p['name'])}</span>
<nav class="subnav-links" aria-label="Product sections"><a href="#overview">Overview</a>{feat_anchor}{film_anchor}<a href="#about">About</a><a href="#related">Related</a></nav>
<a class="btn btn-light" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
</div></div>
{hero_open}
  {hero_head}
  <div class="detail-actions">
    <a class="btn btn-light btn-lg" href="{wa_link(p['name'])}" target="_blank" rel="noopener">WhatsApp Inquiry</a>
    {second_pill}
  </div>
  {compare_link}
  {confirm_html}
{hero_close}
{dji_top}
{gallery}
{features_new}
{features}
{dji_top}
{features}
{product_video(p)}
{endcard}
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
<div class="lightbox" id="lightbox"><img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt=""></div>
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
        # 12 films: first and last cards span both columns so the grid fills exactly.
        cards += video_card(v["video_id"], v["title_or_null"] or "DJI film", link, wide=(i == 0 or i == len(vids) - 1))
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
{section_head('The Films', '12 verified DJI films', 'Every film below is an official DJI film on YouTube, verified as publicly playable.')}
<div class="video-grid">{cards}</div>
</div></section>
{cta_band('')}
"""
    write("explore.html", chrome("", "Explore — Stories & Films — AK Khan Enterprises",
        "Explore AK Khan Enterprises: drone photography stories and 12 verified official DJI films.", body))

# ----- static info pages -----
FAQS = [
    ("Where is AK Khan Enterprises?", f"{ADDRESS}, Pakistan. Walk in during shop hours, or message us on WhatsApp ({WA_DISPLAY}) before you come."),
    ("Why do some products not show a price?", "Prices change with stock and the market. The shop confirms today's exact price personally on WhatsApp so you never rely on an old listed price."),
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

# ----- support page (DJI): photo-less head — title + subtitle + search,
# no photo. DJI's own support page is text-led and plain, so this is
# DJI-legit. All body copy is the shop's existing real copy.
def build_support():
    body = f"""
<section class="support-head">
  <div class="wrap">
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
        "About AK Khan Enterprises, Quetta — drones, cameras, networking, sound and displays.",
        "About Us", "AK Khan Enterprises",
        f"""<p><strong>{esc(TAGLINE)}</strong></p>
<p>AK Khan Enterprises is an electronics and security shop in Quetta. The shop stocks DJI drones, security cameras and recorders, networking equipment, Audionic sound systems and LED TVs — five ranges, under one roof, at {esc(ADDRESS)}.</p>
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
<div class="contact-card"><h3>Social media</h3><p><a href="{IG1}" target="_blank" rel="noopener">Instagram @ak_khan682</a><br><a href="{IG2}" target="_blank" rel="noopener">Instagram @akkhan.enterprises</a><br><a href="{FB_URL}" target="_blank" rel="noopener">Facebook 61595712927205</a></p></div>
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
        if p.get("photo_full"):
            uri, w, h = search_uri(p["photo_full"])
        else:
            uri, w, h = "", 0, 0
        data.append({"slug": p["slug"], "name": p["name"], "brand": p["brand"],
                     "cat": CATS[p["category"]]["label"], "catKey": p["category"],
                     "tag": p["tagline"], "price": price_text(p),
                     # resized size: the search card caps the image at
                     # these pixels (audit P3 #10), like the category cards.
                     "w": w, "h": h,
                     # 800px-max image, not the full photo and not the
                     # 400px thumb: search tiles are the same 2-per-row
                     # size as category tiles (~652px), so 800px stays
                     # sharp while search-data.js stays pushable.
                     "thumb": uri})
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
    return '<article class="card"><a class="card-img" href="products/'+p.slug+'.html">'+img+'</a><div class="card-body"><div class="card-top"><p class="card-cat">'+p.brand+' &middot; '+p.cat+'</p><h3><a href="products/'+p.slug+'.html">'+p.name+'</a></h3><p class="card-tag">'+p.tag+'</p></div><div class="card-foot"><p class="price">'+(p.price==='Price on request'?'<span class="price por">Price on request</span>':p.price)+'</p><a class="more-link" href="products/'+p.slug+'.html">Learn more &rsaquo;</a></div></div></article>';
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
    ['Price',function(p){return (p.slug==='dji-air-3s'||p.slug==='dji-mini-4-pro'||p.slug==='dji-mavic-3-pro')&&p.price.slice(0,2)==='Rs'?'From '+p.price:p.price;}],['About',function(p){return p.tag;}],
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
    # ROUND 6 order check (verified against products.json before use):
    # every order map must cover exactly its category's ids, and the
    # Innovation tiles must be real products — a missing, extra or
    # duplicate id fails the build loudly instead of silently
    # mis-ordering.
    for _c, _order in CAT_ORDER_MAP.items():
        _actual = sorted(p["id"] for p in products if p["category"] == _c)
        assert sorted(_order) == _actual, f"order mismatch in {_c}: {sorted(_order)} != {_actual}"
        assert len(_order) == len(set(_order)), f"duplicate id in {_c} order"
    assert len(INNOVATION_IDS) == len(set(INNOVATION_IDS)), "duplicate id in INNOVATION_IDS"
    for _i in INNOVATION_IDS:
        assert any(p["id"] == _i for p in products), f"bad innovation id {_i}"
    assert sorted(s for s, _ in DJI_COMPARE) == sorted(
        ["dji-mavic-3-pro", "dji-air-3s", "dji-air-3",
         "dji-mini-4-pro", "dji-mini-3-pro", "dji-mini-3"]), "DJI_COMPARE models changed"
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
    # Gallery photos are embedded as base64 data URIs in the product
    # pages (see build_product) — they are NEVER copied as files: the
    # GitHub snapshot push rejects binary files ("not UTF-8"). An earlier
    # file-based gallery build was reverted for exactly this reason
    # (19 Nov, batch 01 failed on a single JPEG). No assets/gallery/
    # dirs are produced.
    build_index()
    for c in CAT_ORDER:
        build_category(c)
    build_audionic()
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

- 108 product pages, 5 category pages, Audionic brand page
  (brands/audionic.html — only the 11 Audionic products, ids 30-40),
  homepage, explore, about, support, FAQ, contact, privacy, terms,
  search, compare.
- Product galleries (audionic.co format): main image + thumb strip +
  dots + prev/next arrows, lightbox opens the currently shown image.
  Gallery extras are base64 data URIs embedded in the product pages
  (the GitHub snapshot push rejects binary files, so gallery photos
  can never be separate files).
  One-photo products keep the plain single-image block.
- Mobile hero (360-412px): title fits on one line (vw-based size, low
  floor), pills auto-width, slide list visible bottom-left, chevrons
  parked bottom-right clear of pills and list, hero 360px not 520px.
  Floating WhatsApp pill is smaller on mobile and the footer has safe
  bottom padding so it never covers footer text.
- Black / white / grey only: no gold, navy, cream or green anywhere.
  WhatsApp CTAs are black or white pills, never green.
- Logos: assets/logo-mark-white.svg (dark header/footer) and
  assets/logo-mark-black.svg (light scrolled header, favicon). The old gold
  logo-mark.svg is gone. Wordmark "AK KHAN / ENTERPRISES" is styled HTML text.
- WhatsApp-only ordering (wa.me/923067000682). No cart, checkout or admin.
- Images are embedded as base64 data URIs (GitHub snapshot pushes are
  text-only); the logo SVGs are real files.
- Homepage hero: 4 rotating stills with DJI's exact slide copy, 5s
  autoplay, text in the top third, outline-white pills, edge ‹ ›
  arrows. No Security Cameras slide (its photo was a deleted generic
  stock image, 2.04x upscaled).
- DJI product pages (Mavic 3 Pro, Air 3S, Mini 4 Pro): DJI's exact hero
  copy, 6-item spec strip, verbatim intro, DJI feature sections in order
  (heading-only where DJI's copy is unverified — nothing invented), price
  under the spec strip, end card. Other products keep the shop's own copy.
- Drones listing: "Camera Drones" head (DJI's exact subhead),
  flagship-first order, series strip with real product thumbnails,
  framed Mini 4 Pro banner, "Which camera drone is suitable for you?"
  comparison table (verified DJI values + our real PKR prices, never
  DJI USD prices).
- Category heads are text-led (no banner) except drones, which has the
  native-wide 2560x684 DJI flight frame. Support is photo-less, text-led.
- Tiles are DJI-style: 2 large per row, pale-grey (#f2f3f5) panels, text
  centred at the top, one quiet "Learn more" link per card, photo fills
  the tile (cover, no side padding) on grey with a soft drop shadow.
  Cards use the FULL product image (sharper than the 400px thumb at tile
  size), never displayed wider than the source's real resolution
  (inline native-size cap on every image).
- Product detail photo sits on a light-grey stage at ~78vh, capped at
  native size, never a white rectangle on black; tap opens the full
  image in the lightbox.
- Only 28 products have a real PKR price; the other 80 show
  "Price on request — confirmed on WhatsApp".
- No specs table anywhere (the data contains no technical specs).
- Product 89 (Dahua 4K IR ePoE Mini Dome) shows the verified N84CL52 photo
  (official Dahua datasheet).
- Only the 12 verified DJI YouTube films are embedded, via a sharp
  maxresdefault thumbnail facade (click loads the player). The DJI Mini 3
  film (48_kEK9iFKU) is private and is never embedded -- Mini 3 now uses
  the verified 'Meet DJI Mini 3' film (6VbOozPmbr4).
- No Laptops / Photography / Accessories category pages: the data has no
  such products, so those pages would be empty. No "New Arrivals" or
  "Best Sellers" labels: the data has no dates or sales figures.
""")
    print("generated.")

if __name__ == "__main__":
    main()
