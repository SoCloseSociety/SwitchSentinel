"""Injecter un payload dans une V1 en RCM, depuis le Mac (Fusee Gelee, CVE-2018-6242) -- 07/11/2026.

On garde fusee-launcher tel quel (vendor/fusee-launcher, fork Smeat : le depot d'origine Qyriad n'existe plus sur
GitHub) et on l'appelle avec le Python du .venv (pyusb) et la libusb de Homebrew. Rien n'est envoye ailleurs que
sur le cable USB.
"""
from __future__ import annotations

import os
import subprocess

from . import versions

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANCEUR = os.path.join(RACINE, "vendor", "fusee-launcher", "fusee-launcher.py")
INTERMEZZO = os.path.join(RACINE, "vendor", "fusee-launcher", "intermezzo.bin")
PYTHON = os.path.join(RACINE, ".venv", "bin", "python")
DOSSIERS = [os.path.join(RACINE, "vendor", "payloads"), os.path.join(RACINE, "data", "payloads")]
LIBUSB = "/opt/homebrew/lib"


def payloads() -> list[dict]:
    out = []
    for d in DOSSIERS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".bin") or f.startswith("._"):
                continue
            p = os.path.join(d, f)
            hv = versions.version_hekate(p)
            out.append({"id": f, "nom": f"Hekate {hv}" if hv else f.rsplit(".", 1)[0], "hekate": hv,
                        "taille": versions.taille(p), "chemin": os.path.relpath(p, RACINE),
                        "origine": "carte SD" if "data" in d else "téléchargé"})
    def cle(x):
        return (0 if x["hekate"] else 1, tuple(-n for n in (versions.normaliser(x["hekate"]) or ())))
    return sorted(out, key=cle)


def pret() -> dict:
    manque = []
    if not os.path.isfile(LANCEUR) or not os.path.isfile(INTERMEZZO):
        manque.append("fusee-launcher (vendor/fusee-launcher)")
    if not os.path.isfile(PYTHON):
        manque.append("l'environnement .venv (python3.13 -m venv .venv && .venv/bin/pip install pyusb)")
    if not os.path.isfile(os.path.join(LIBUSB, "libusb-1.0.dylib")):
        manque.append("libusb (brew install libusb)")
    if not payloads():
        manque.append("un payload (Hekate) dans vendor/payloads")
    return {"pret": not manque, "manque": manque}


def injecter(payload_id: str) -> dict:
    p = next((x for x in payloads() if x["id"] == payload_id), None)
    if not p:
        return {"ok": False, "sortie": f"payload inconnu : {payload_id}"}
    etat = pret()
    if not etat["pret"]:
        return {"ok": False, "sortie": "il manque : " + ", ".join(etat["manque"])}
    env = dict(os.environ, DYLD_FALLBACK_LIBRARY_PATH=LIBUSB)
    try:
        r = subprocess.run([PYTHON, LANCEUR, "--relocator", INTERMEZZO, os.path.join(RACINE, p["chemin"])],
                           capture_output=True, text=True, timeout=30, env=env, cwd=os.path.dirname(LANCEUR))
    except subprocess.TimeoutExpired:
        return {"ok": False, "sortie": "aucune réponse en 30 s : la console est-elle bien en RCM ?"}
    sortie = (r.stdout + r.stderr).strip()
    # fusee-launcher termine par « The USB device stopped responding -- sure smells like we've smashed its stack. »
    ok = "Launch complete" in sortie
    return {"ok": ok, "code": r.returncode, "sortie": sortie[-1500:], "payload": p["nom"]}
