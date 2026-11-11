"""Les dernieres releases GitHub du catalogue, avec un cache local (data/releases.json, 6 h) -- 07/11/2026.

Appels REST simples au endpoint `releases/latest` de chaque depot (quota « core », 5 000/h authentifie).
`gh` est utilise s'il est connecte (jeton), sinon urllib anonyme.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import urllib.request

from . import connus

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RACINE, "data", "releases.json")
TTL = 6 * 3600
GH = shutil.which("gh") or "/opt/homebrew/bin/gh"


def _api(chemin: str) -> dict | None:
    if os.path.exists(GH):
        r = subprocess.run([GH, "api", chemin], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout)
    try:
        req = urllib.request.Request("https://api.github.com/" + chemin, headers={"Accept": "application/vnd.github+json",
                                                                                   "User-Agent": "SwitchSentinel"})
        with urllib.request.urlopen(req, timeout=30) as f:
            return json.loads(f.read().decode())
    except Exception:  # noqa: BLE001 -- hors ligne : on garde le cache
        return None


def _resume(e: dict, rel: dict) -> dict:
    assets = [{"nom": a["name"], "taille": a["size"], "url": a["browser_download_url"]} for a in rel.get("assets", [])]
    choisi = next((a for a in assets if re.match(e["asset"], a["nom"])), None)
    return {"id": e["id"], "repo": e["repo"], "tag": rel.get("tag_name"), "date": (rel.get("published_at") or "")[:10],
            "notes": (rel.get("body") or "")[:6000], "lien": rel.get("html_url"), "asset": choisi, "assets": assets}


def lire_cache() -> dict:
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return {"maj_a": 0, "releases": {}}


def releases(forcer: bool = False) -> dict:
    c = lire_cache()
    if not forcer and time.time() - c.get("maj_a", 0) < TTL and c.get("releases"):
        return c
    neuves, erreurs = {}, []
    for e in connus.COEUR + connus.CATALOGUE:
        rel = _api(f"repos/{e['repo']}/releases/latest")
        if rel and rel.get("tag_name"):
            neuves[e["id"]] = _resume(e, rel)
        elif e["id"] in c.get("releases", {}):
            neuves[e["id"]] = c["releases"][e["id"]]
            erreurs.append(e["id"])
        else:
            erreurs.append(e["id"])
    c = {"maj_a": int(time.time()), "releases": neuves, "erreurs": erreurs}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(c, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return c


def telecharger(url: str, chemin: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "SwitchSentinel"})
    with urllib.request.urlopen(req, timeout=300) as f:
        data = f.read()
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "wb") as out:
        out.write(data)
    return len(data)
