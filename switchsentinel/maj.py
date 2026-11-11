"""Mettre la carte SD a jour : un plan, une sauvegarde sur le Mac, puis l'ecriture (07/11/2026).

    .venv/bin/python -m switchsentinel.maj --sd "/Volumes/SWITCH SD" --plan       # dit ce qui changerait
    .venv/bin/python -m switchsentinel.maj --sd "/Volumes/SWITCH SD" --appliquer  # sauvegarde PUIS ecrit

Regles de pose (chacune vient d'un piege vu sur une vraie carte) :
  - un `.ini` deja present sous config/ n'est jamais ecrase : ce sont les reglages de la personne ;
  - `hbmenu.nro` n'est remplace que s'il est encore nx-hbmenu (sinon la personne a choisi un autre menu) ;
  - `atmosphere/reboot_payload.bin`, `payload.bin`, `start.bin` : s'ils sont Hekate, ils recoivent le NOUVEAU Hekate
    (et non le fusee du zip d'Atmosphere, qui changerait le redemarrage) ;
  - aucun chemin absolu, aucun `..`, rien de `__MACOSX` ni de `._*` ;
  - chaque fichier remplace est d'abord copie dans sauvegardes/<horodatage>/sd/, avec un manifeste.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import zipfile

from . import versions

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEL = os.path.join(RACINE, "data", "staging", "telechargements")
PAY = os.path.join(RACINE, "vendor", "payloads")
SAUV = os.path.join(RACINE, "sauvegardes")

# Ce qu'on met a jour sur CETTE carte (07/11/2026). `source` : un zip a l'arborescence de la SD, ou un fichier seul.
OPERATIONS = [
    {"id": "atmosphere", "nom": "Atmosphère", "apres": "1.12.1", "zip": os.path.join(PAY, "atmosphere-1.12.1-master-6b0c077b4+hbl-2.4.5+hbmenu-3.6.1.zip")},
    {"id": "hekate", "nom": "Hekate + Nyx", "apres": "6.5.4 / 1.9.4", "zip": os.path.join(PAY, "hekate_ctcaer_6.5.4_Nyx_1.9.4.zip"),
     "exclure": ["hekate_ctcaer_6.5.4.bin"]},
    {"id": "fusee", "nom": "fusee (payload d'Atmosphère)", "apres": "1.12.1", "fichier": os.path.join(TEL, "fusee.bin"),
     "vers": "bootloader/payloads/fusee.bin", "seulement_si_present": True},
    {"id": "payloads-hekate", "nom": "Copies du payload Hekate", "apres": "6.5.4", "fichier": os.path.join(PAY, "hekate_ctcaer_6.5.4.bin"),
     "vers_si_hekate": ["atmosphere/reboot_payload.bin", "payload.bin", "start.bin"]},
    {"id": "missioncontrol", "nom": "MissionControl", "apres": "0.16.0", "zip": os.path.join(TEL, "MissionControl-0.16.0-master-71bbe2d4.zip")},
    {"id": "ultrahand", "nom": "Ultrahand + nx-ovlloader+", "apres": "2.5.3 / 2.0.2", "zip": os.path.join(TEL, "ultrahand-sdout.zip")},
    {"id": "sys-con", "nom": "sys-con", "apres": "2.1.0", "zip": os.path.join(TEL, "sys-con-2.1.0.zip")},
    {"id": "status-monitor", "nom": "Status Monitor", "apres": "1.4.1", "zip": os.path.join(TEL, "Status-Monitor-Overlay.zip")},
    {"id": "edizon-ovl", "nom": "EdiZon (overlay)", "apres": "1.0.15", "fichier": os.path.join(TEL, "ovlEdiZon.ovl"),
     "vers": "switch/.overlays/ovlEdiZon.ovl"},
    {"id": "jksv", "nom": "JKSV", "apres": "12/02/2025", "fichier": os.path.join(TEL, "JKSV.nro"), "vers": "switch/JKSV/JKSV.nro"},
    {"id": "checkpoint", "nom": "Checkpoint", "apres": "5.3.0", "fichier": os.path.join(TEL, "Checkpoint.nro"),
     "vers": "switch/Checkpoint/Checkpoint.nro"},
    {"id": "nxthemes", "nom": "NXThemes Installer", "apres": "3.0.2", "fichier": os.path.join(TEL, "NXThemesInstaller.nro"),
     "vers": "switch/NXThemesInstaller.nro"},
    {"id": "ftpd", "nom": "ftpd", "apres": "3.2.1", "fichier": os.path.join(TEL, "ftpd.nro"), "vers": "switch/ftpd.nro"},
    {"id": "moonlight", "nom": "Moonlight", "apres": "1.5.0", "fichier": os.path.join(TEL, "Moonlight-Switch.nro"),
     "vers": "switch/Moonlight-Switch.nro"},
]

# Les reglages copies sur le Mac a chaque passage, en plus des fichiers remplaces (petits, et irremplacables).
A_GARDER = ["bootloader/hekate_ipl.ini", "bootloader/nyx.ini", "bootloader/patches.ini", "bootloader/ini",
            "exosphere.ini", "emuMMC/emummc.ini", "atmosphere/config", "atmosphere/hosts", "atmosphere/contents",
            "config", "boot.ini"]


def _sur(chemin: str) -> str | None:
    c = chemin.replace("\\", "/")
    if c.startswith("/") or ".." in c.split("/") or c.startswith("__MACOSX") or "/._" in "/" + c or c.endswith("/"):
        return None
    return c


def _poser(sd: str, rel: str, op: str, source: tuple) -> dict:
    cible = os.path.join(sd, rel)
    existe = os.path.isfile(cible)
    if existe and rel.startswith("config/") and rel.endswith(".ini"):
        return {"chemin": rel, "action": "garder", "op": op, "pourquoi": "réglage existant"}
    return {"chemin": rel, "action": "remplacer" if existe else "creer", "op": op, "source": source}


def plan(sd: str) -> dict:
    lignes, manquants = [], []
    for o in OPERATIONS:
        if o.get("zip"):
            if not os.path.isfile(o["zip"]):
                manquants.append(o["zip"]); continue
            with zipfile.ZipFile(o["zip"]) as z:
                for info in z.infolist():
                    rel = _sur(info.filename)
                    if not rel or info.is_dir() or rel in o.get("exclure", []):
                        continue
                    if rel == "hbmenu.nro":
                        n = versions.nacp(os.path.join(sd, rel)) or {}
                        if n.get("nom") and n["nom"] != "nx-hbmenu":
                            lignes.append({"chemin": rel, "action": "garder", "op": o["id"], "pourquoi": f"menu choisi : {n['nom']}"})
                            continue
                    if rel == "atmosphere/reboot_payload.bin" and versions.version_hekate(os.path.join(sd, rel)):
                        continue   # garde Hekate au redemarrage : traite par l'operation payloads-hekate
                    lignes.append(_poser(sd, rel, o["id"], ("zip", o["zip"], info.filename)))
        else:
            if not os.path.isfile(o["fichier"]):
                manquants.append(o["fichier"]); continue
            if o.get("vers_si_hekate"):
                for rel in o["vers_si_hekate"]:
                    if versions.version_hekate(os.path.join(sd, rel)):
                        lignes.append(_poser(sd, rel, o["id"], ("fichier", o["fichier"])))
                continue
            rel = o["vers"]
            if o.get("seulement_si_present") and not os.path.isfile(os.path.join(sd, rel)):
                continue
            lignes.append(_poser(sd, rel, o["id"], ("fichier", o["fichier"])))
    resume = {a: sum(1 for l in lignes if l["action"] == a) for a in ("creer", "remplacer", "garder")}
    return {"sd": sd, "lignes": lignes, "resume": resume, "manquants": manquants,
            "operations": [{k: o[k] for k in ("id", "nom", "apres")} for o in OPERATIONS]}


def _copier_vers(src: str, dst: str):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)   # les donnees seules : pas d'attributs etendus, donc aucun fichier ._ sur la FAT32


def sauvegarder(sd: str, p: dict, horodatage: str) -> dict:
    base = os.path.join(SAUV, f"sd-{horodatage}", "sd")
    copies = []
    for l in p["lignes"]:
        if l["action"] == "remplacer":
            _copier_vers(os.path.join(sd, l["chemin"]), os.path.join(base, l["chemin"]))
            copies.append(l["chemin"])
    for g in A_GARDER:
        src = os.path.join(sd, g)
        if os.path.isfile(src):
            _copier_vers(src, os.path.join(base, g)); copies.append(g)
        elif os.path.isdir(src):
            for r, ds, fs in os.walk(src):
                ds[:] = [d for d in ds if not d.startswith(".")]
                for f in fs:
                    if f.startswith("._"):
                        continue
                    s = os.path.join(r, f)
                    rel = os.path.relpath(s, sd)
                    _copier_vers(s, os.path.join(base, rel)); copies.append(rel)
    return {"dossier": os.path.dirname(base), "fichiers": sorted(set(copies))}


def appliquer(sd: str) -> dict:
    p = plan(sd)
    if p["manquants"]:
        return {"ok": False, "erreur": "téléchargements manquants", "manquants": p["manquants"]}
    horodatage = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    s = sauvegarder(sd, p, horodatage)
    ecrits, erreurs = [], []
    zips: dict[str, zipfile.ZipFile] = {}
    try:
        for l in p["lignes"]:
            if l["action"] == "garder":
                continue
            cible = os.path.join(sd, l["chemin"])
            tmp = cible + ".switchsentinel-tmp"
            try:
                os.makedirs(os.path.dirname(cible), exist_ok=True)
                if l["source"][0] == "zip":
                    z = zips.setdefault(l["source"][1], zipfile.ZipFile(l["source"][1]))
                    with z.open(l["source"][2]) as src, open(tmp, "wb") as out:
                        shutil.copyfileobj(src, out)
                else:
                    shutil.copyfile(l["source"][1], tmp)
                os.replace(tmp, cible)
                ecrits.append(l["chemin"])
            except OSError as e:
                erreurs.append({"chemin": l["chemin"], "erreur": str(e)})
                if os.path.exists(tmp):
                    os.remove(tmp)
    finally:
        for z in zips.values():
            z.close()
        os.sync()
    rapport = {"ok": not erreurs, "horodatage": horodatage, "sauvegarde": s["dossier"], "sauvegardes": len(s["fichiers"]),
               "ecrits": len(ecrits), "erreurs": erreurs, "resume": p["resume"],
               "gardes": [l for l in p["lignes"] if l["action"] == "garder"]}
    with open(os.path.join(s["dossier"], "MANIFESTE.json"), "w", encoding="utf-8") as f:
        json.dump({**rapport, "plan": [{k: v for k, v in l.items() if k != "source"} for l in p["lignes"]],
                   "copies": s["fichiers"]}, f, ensure_ascii=False, indent=1)
    return rapport


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--sd", required=True)
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--appliquer", action="store_true")
    x = a.parse_args()
    if x.plan:
        p = plan(x.sd)
        par_op = {}
        for l in p["lignes"]:
            par_op.setdefault(l["op"], {"creer": 0, "remplacer": 0, "garder": 0})[l["action"]] += 1
        for o in p["operations"]:
            print(f"{o['nom']:<28} -> {o['apres']:<14} {par_op.get(o['id'], {})}")
        for l in p["lignes"]:
            if l["action"] == "garder":
                print(f"  garde {l['chemin']} ({l['pourquoi']})")
        print("total", p["resume"], "manquants", p["manquants"])
    else:
        print(json.dumps(appliquer(x.sd), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
