#!/usr/bin/env python3
"""Convertir les visuels kie.ai au format natif de la Switch, charte SentinelHouse (11/11/2026).

    .venv/bin/python outils/switch_visuels.py           # genere dans data/staging/switch-visuels/

Produit, depuis `ui/visuels/brut/` (zero generation payante, on recadre les images deja faites) :
  - `background.bmp` : le fond du menu Hekate/Nyx. BMP 32-bit, 1280x720 (verifie : README_RES de hekate).
  - `bootlogo.bmp`   : le logo de demarrage. BMP 32-bit, 720x1280 (tourne 90 deg, README_BOOTLOGO de hekate).
  - 7 PNG 1280x720   : les fonds des ecrans HOME (NXTheme) -> a injecter avec NXThemes Installer.

Le BMP 32-bit est ecrit a la main (BITMAPINFOHEADER, 32 bpp, BGRA bas-vers-haut, alpha 0xFF) : Pillow seul
n'ecrit pas un BMP alpha fiable, et Nyx veut exactement ce format.
"""
from __future__ import annotations

import os
import struct

from PIL import Image

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RACINE, "ui", "visuels", "brut")
OUT = os.path.join(RACINE, "data", "staging", "switch-visuels")

# Quel visuel kie.ai habille quel ecran (voir ui/ECRANS.md).
NXTHEME = [
    ("ResidentMenu", "fond-atmosphere", "Home menu"),
    ("Entrance",     "fond-veille",     "Ecran de verrouillage"),
    ("Set",          "carte-atelier",   "Reglages"),
    ("Flaunch",      "carte-maj",       "Tous les logiciels"),
    ("Psl",          "carte-reveil",    "Selection du joueur"),
    ("MyPage",       "carte-bouclier",  "Page profil"),
    ("Notification", "carte-sd",        "Actus"),
]


def charger(nom: str) -> Image.Image:
    return Image.open(os.path.join(SRC, nom + ".png")).convert("RGBA")


def cover(im: Image.Image, w: int, h: int) -> Image.Image:
    """Recadre-remplit : l'image couvre exactement w x h sans deformation (crop centre)."""
    src_r, dst_r = im.width / im.height, w / h
    if src_r > dst_r:                      # trop large : on rogne les cotes
        nw = int(im.height * dst_r)
        im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
    else:                                  # trop haute : on rogne haut/bas
        nh = int(im.width / dst_r)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    return im.resize((w, h), Image.LANCZOS)


def ecrire_bmp32(im: Image.Image, chemin: str) -> tuple[int, int]:
    """Ecrit un BMP 32-bit BGRA, lignes bas-vers-haut, alpha force a 0xFF (fond opaque)."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    lignes = bytearray()
    for y in range(h - 1, -1, -1):         # BMP : derniere ligne en premier
        for x in range(w):
            r, g, b, _ = px[x, y]
            lignes += bytes((b, g, r, 0xFF))
    taille_px = len(lignes)
    entete_fichier = struct.pack("<2sIHHI", b"BM", 14 + 40 + taille_px, 0, 0, 14 + 40)
    entete_info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0, taille_px, 2835, 2835, 0, 0)
    with open(chemin, "wb") as f:
        f.write(entete_fichier); f.write(entete_info); f.write(lignes)
    return w, h


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    faits = []

    # 1. Fond Nyx (menu Hekate) : 1280x720 BMP 32-bit.
    nyx = cover(charger("fond-hekate"), 1280, 720)
    w, h = ecrire_bmp32(nyx, os.path.join(OUT, "background.bmp"))
    faits.append(f"background.bmp (Nyx)        {w}x{h} BMP32")

    # 2. Boot logo : composition 1280x720 tournee 90 deg CCW -> 720x1280 BMP 32-bit.
    logo = cover(charger("fond-rcm"), 1280, 720).rotate(90, expand=True)
    w, h = ecrire_bmp32(logo, os.path.join(OUT, "bootlogo.bmp"))
    faits.append(f"bootlogo.bmp (demarrage)    {w}x{h} BMP32")

    # 3. Les 7 fonds HOME (NXTheme) : 1280x720 PNG.
    dth = os.path.join(OUT, "nxtheme")
    os.makedirs(dth, exist_ok=True)
    for cible, src, libelle in NXTHEME:
        img = cover(charger(src), 1280, 720).convert("RGB")
        p = os.path.join(dth, f"{cible}.png")
        img.save(p, "PNG")
        faits.append(f"nxtheme/{cible}.png  <- {src}  ({libelle})")

    print("Genere dans", os.path.relpath(OUT, RACINE), ":")
    for f in faits:
        print("  " + f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
