"""Voir la console sur le bus USB du Mac, sans dependance (ioreg) -- 07/11/2026.

Les modes possibles, du plus utile au plus muet :
  rcm        0955:7321  la console attend un payload (Hekate) : on peut injecter
  hekate_ums 11EC:A7E0  Hekate partage la carte SD ou l'eMMC en USB : le Mac la monte
  hekate     11EC:A7E1/2 Hekate est demarre (autre fonction USB)
  horizon    057E:2000  le systeme tourne (CFW ou d'origine)
  absente    rien       eteinte, batterie vide, cable de charge seule, ou port qui ne transmet pas
"""
from __future__ import annotations

import plistlib
import subprocess

from .connus import USB


def _marcher(n, out: list):
    if isinstance(n, dict):
        if "idVendor" in n and "idProduct" in n:
            out.append({"vid": int(n["idVendor"]), "pid": int(n["idProduct"]),
                        "nom": n.get("USB Product Name") or n.get("kUSBProductString"),
                        "fabricant": n.get("USB Vendor Name") or n.get("kUSBVendorString"),
                        "vitesse": n.get("Device Speed") or n.get("USBSpeed"),
                        "lieu": n.get("locationID")})
        for v in n.values():
            _marcher(v, out)
    elif isinstance(n, list):
        for v in n:
            _marcher(v, out)


def appareils() -> list[dict]:
    try:
        brut = subprocess.run(["ioreg", "-p", "IOUSB", "-l", "-a"], capture_output=True, timeout=8).stdout
        arbre = plistlib.loads(brut) if brut else {}
    except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException, ValueError):
        return []
    out: list[dict] = []
    _marcher(arbre, out)
    return out


def etat() -> dict:
    tous = appareils()
    switch = []
    for a in tous:
        m = USB.get((a["vid"], a["pid"]))
        if m:
            switch.append({**a, "mode": m[0], "libelle": m[1], "id": f"{a['vid']:04x}:{a['pid']:04x}"})
    ordre = ["rcm", "hekate_ums", "hekate", "horizon"]
    switch.sort(key=lambda a: ordre.index(a["mode"]))
    mode = switch[0]["mode"] if switch else "absente"
    return {"mode": mode, "switch": switch, "nb_appareils": len(tous)}
