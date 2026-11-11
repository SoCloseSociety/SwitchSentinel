#!/usr/bin/env python3
"""Fabrique les 7 fichiers .nxtheme SentinelHouse+SoClose, pour NXThemes Installer (11/11/2026).

Format verifie dans le code de l'installeur (exelix11/SwitchThemeInjector, NXTheme.cpp + SwitchThemesCommon.cs) :
  - un .nxtheme est un ZIP simple (TryLoad : debut "PK" -> zip::Extract) ;
  - a la racine : `info.json` + `image.jpg` (l'image JPG 1280x720 est convertie en DDS par l'installeur) ;
  - info.json = {"Version": 17, "ThemeName", "Author", "Target"} ; Target = nom court (CommonInfo.Parts) :
        home=ResidentMenu  lock=Entrance  apps=Flaunch  set=Set  news=Notification  user=MyPage  psl=Psl

    .venv/bin/python outils/fabriquer_nxtheme.py
"""
from __future__ import annotations

import io
import json
import os
import zipfile

from PIL import Image

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RACINE, "data", "staging", "switch-visuels-soclose", "nxtheme")   # les PNG brandes
OUT = os.path.join(RACINE, "data", "staging", "switch-visuels-soclose", "nxtheme-pret")
VERSION = 17
AUTEUR, NOM = "SoClose", "SentinelHouse"

# fichier PNG (nom szs) -> (Target court, libelle)
ECRANS = {
    "ResidentMenu": ("home", "Home menu"),
    "Entrance":     ("lock", "Ecran de verrouillage"),
    "Flaunch":      ("apps", "Tous les logiciels"),
    "Set":          ("set",  "Reglages"),
    "Notification": ("news", "Actus"),
    "MyPage":       ("user", "Page profil"),
    "Psl":          ("psl",  "Selection du joueur"),
}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for szs, (target, libelle) in ECRANS.items():
        img = Image.open(os.path.join(SRC, szs + ".png")).convert("RGB")
        tampon = io.BytesIO()
        img.save(tampon, "JPEG", quality=92)
        info = {"Version": VERSION, "ThemeName": f"{NOM} - {libelle}", "Author": AUTEUR, "Target": target}
        chemin = os.path.join(OUT, f"{szs}.nxtheme")
        with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("info.json", json.dumps(info))
            z.writestr("image.jpg", tampon.getvalue())
        print(f"  {szs}.nxtheme   Target={target:5} ({libelle})  {os.path.getsize(chemin)//1024} Ko")
    print("\n-> dossier", os.path.relpath(OUT, RACINE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
