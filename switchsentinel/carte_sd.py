"""L'audit de la carte SD : ce qui est installe, comment c'est regle, ce qui manque (07/11/2026).

Lecture seule. Rien n'est ecrit sur la carte ici ; les gestes qui ecrivent vivent dans `gestes.py` et demandent
toujours une confirmation. Les fichiers propres a LA console (PRODINFO, prod.keys, sauvegardes NAND) ne sont jamais
lus, seulement constates : leur nom, leur taille, leur date.
"""
from __future__ import annotations

import configparser
import os
import plistlib
import subprocess
import time

from . import connus, versions

TRACES_MAC_DOSSIERS = {".Spotlight-V100", ".fseventsd", ".Trashes", ".TemporaryItems", ".DocumentRevisions-V100"}
TRACES_MAC_FICHIERS = {".DS_Store", ".VolumeIcon.icns", ".apdisk"}
DOSSIERS_LOURDS = {"Nintendo", "emuMMC"}   # donnees des jeux : on ne les parcourt pas fichier par fichier


def ressemble_a_une_sd(racine: str) -> bool:
    return any(os.path.isdir(os.path.join(racine, d)) for d in ("atmosphere", "bootloader")) or \
        os.path.isdir(os.path.join(racine, "Nintendo"))


def candidats() -> list[dict]:
    """Les volumes montes qui ressemblent a une carte SD de Switch."""
    vus = []
    try:
        noms = sorted(os.listdir("/Volumes"))
    except OSError:
        noms = []
    for n in noms:
        p = os.path.join("/Volumes", n)
        if os.path.ismount(p) and ressemble_a_une_sd(p):
            vus.append({"chemin": p, "nom": n})
    return vus


def _ini(chemin: str) -> configparser.ConfigParser | None:
    if not os.path.isfile(chemin):
        return None
    c = configparser.ConfigParser(strict=False, interpolation=None, delimiters=("=",))
    c.optionxform = str
    try:
        with open(chemin, encoding="utf-8", errors="replace") as f:
            c.read_string(f.read())
    except configparser.Error:
        return None
    return c


def _volume(racine: str) -> dict:
    v = {"chemin": racine, "systeme": None, "taille": None, "libre": None, "nom_media": None, "appareil": None}
    demo = os.path.join(racine, "_demo_volume.json")
    if os.path.isfile(demo):          # la carte de demonstration dit quel volume elle imite
        import json
        v.update(json.load(open(demo, encoding="utf-8")))
        v["demo"] = True
        return v
    if not os.path.ismount(racine):   # un simple dossier : ses chiffres seraient ceux du disque du Mac
        return v
    try:
        s = os.statvfs(racine)
        v["taille"], v["libre"] = s.f_blocks * s.f_frsize, s.f_bavail * s.f_frsize
    except OSError:
        pass
    if racine.startswith("/Volumes/"):
        try:
            out = subprocess.run(["diskutil", "info", "-plist", racine], capture_output=True, timeout=10).stdout
            d = plistlib.loads(out) if out else {}
            v["systeme"] = d.get("FilesystemName") or d.get("FilesystemType")
            v["nom_media"] = d.get("MediaName")
            v["appareil"] = d.get("DeviceIdentifier")
        except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException):
            pass
    return v


def _traces_mac(racine: str, limite: int = 20000) -> dict:
    fichiers, dossiers, vus = [], [], 0
    for haut in sorted(os.listdir(racine)) if os.path.isdir(racine) else []:
        p = os.path.join(racine, haut)
        if haut in TRACES_MAC_DOSSIERS and os.path.isdir(p):
            dossiers.append(haut)
            continue
        if haut in TRACES_MAC_FICHIERS or haut.startswith("._"):
            fichiers.append(haut)
            continue
        if haut in DOSSIERS_LOURDS or not os.path.isdir(p):
            continue
        for base, ds, fs in os.walk(p):
            for d in ds:
                if d in TRACES_MAC_DOSSIERS:
                    dossiers.append(os.path.relpath(os.path.join(base, d), racine))
            ds[:] = [d for d in ds if d not in TRACES_MAC_DOSSIERS]
            for f in fs:
                vus += 1
                if f.startswith("._") or f in TRACES_MAC_FICHIERS:
                    fichiers.append(os.path.relpath(os.path.join(base, f), racine))
            if vus > limite:
                break
    return {"fichiers": fichiers, "dossiers": dossiers, "total": len(fichiers) + len(dossiers)}


def _taille_dossier(p: str, limite_s: float = 4.0) -> int | None:
    total, debut = 0, time.time()
    for base, _, fs in os.walk(p):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
        if time.time() - debut > limite_s:
            return None
    return total


def _atmosphere(r: str) -> dict:
    a = {"present": os.path.isdir(os.path.join(r, "atmosphere"))}
    p3 = versions.package3(os.path.join(r, "atmosphere", "package3"))
    a.update({"version": p3["version"] if p3 else None, "firmware_max": p3["firmware_max"] if p3 else None,
              "hash": p3["hash"] if p3 else None})
    fusee = [x for x in ("bootloader/payloads/fusee.bin", "fusee.bin", "atmosphere/fusee.bin") if os.path.isfile(os.path.join(r, x))]
    a["fusee"] = fusee
    a["reboot_payload"] = None
    rp = os.path.join(r, "atmosphere", "reboot_payload.bin")
    if os.path.isfile(rp):
        hv = versions.version_hekate(rp)
        a["reboot_payload"] = f"Hekate {hv}" if hv else "fusee (d'origine)"
    a["configs"] = sorted(f for f in os.listdir(os.path.join(r, "atmosphere", "config"))) \
        if os.path.isdir(os.path.join(r, "atmosphere", "config")) else []
    hosts_dir = os.path.join(r, "atmosphere", "hosts")
    a["hosts"] = {}
    for nom in ("emummc.txt", "sysmmc.txt", "default.txt"):
        p = os.path.join(hosts_dir, nom)
        if os.path.isfile(p):
            txt = open(p, encoding="utf-8", errors="replace").read()
            lignes = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")]
            a["hosts"][nom] = {"lignes": len(lignes), "bloque_nintendo": any("nintendo" in l and l.startswith("127.0.0.1") for l in lignes)}
    exo = _ini(os.path.join(r, "exosphere.ini"))
    a["exosphere"] = dict(exo["exosphere"]) if exo and exo.has_section("exosphere") else None
    backups = os.path.join(r, "atmosphere", "automatic_backups")
    a["prodinfo_auto"] = [
        {"nom": f, "taille": versions.taille(os.path.join(backups, f))} for f in sorted(os.listdir(backups))
        if os.path.isfile(os.path.join(backups, f)) and not f.startswith("._")] if os.path.isdir(backups) else []
    return a


def _hekate(r: str) -> dict:
    h = {"present": os.path.isdir(os.path.join(r, "bootloader"))}
    h["version"] = versions.version_hekate(os.path.join(r, "bootloader", "update.bin"))
    h["nyx"] = versions.version_nyx(os.path.join(r, "bootloader", "sys", "nyx.bin"))
    ini = _ini(os.path.join(r, "bootloader", "hekate_ipl.ini"))
    h["ini_present"] = ini is not None
    h["config"] = dict(ini["config"]) if ini and ini.has_section("config") else {}
    entrees = []
    if ini:
        for s in ini.sections():
            if s == "config" or s.startswith("{"):
                continue
            d = dict(ini[s])
            entrees.append({"nom": s, "emummc": d.get("emummcforce") == "1",
                            "sysnand": d.get("emummc_force_disable") == "1",
                            "atmosphere": "pkg3" in d or "fss0" in d,
                            "payload": d.get("payload"), "cles": sorted(d)})
    # les entrees en plus de bootloader/ini/*.ini
    ini_dir = os.path.join(r, "bootloader", "ini")
    if os.path.isdir(ini_dir):
        for f in sorted(os.listdir(ini_dir)):
            c = _ini(os.path.join(ini_dir, f)) if f.endswith(".ini") else None
            for s in (c.sections() if c else []):
                d = dict(c[s])
                entrees.append({"nom": s, "emummc": d.get("emummcforce") == "1", "sysnand": d.get("emummc_force_disable") == "1",
                                "atmosphere": "pkg3" in d or "fss0" in d, "payload": d.get("payload"),
                                "cles": sorted(d), "fichier": f"bootloader/ini/{f}"})
    h["entrees"] = entrees
    pdir = os.path.join(r, "bootloader", "payloads")
    h["payloads"] = []
    if os.path.isdir(pdir):
        for f in sorted(os.listdir(pdir)):
            if f.lower().endswith(".bin") and not f.startswith("._"):
                p = os.path.join(pdir, f)
                hv = versions.version_hekate(p)
                h["payloads"].append({"nom": f, "taille": versions.taille(p), "hekate": hv})
    return h


def _emummc(r: str) -> dict:
    e = {"ini_present": False, "active": False, "type": None, "dossier": None, "taille": None}
    ini = _ini(os.path.join(r, "emuMMC", "emummc.ini"))
    if ini and ini.has_section("emummc"):
        d = dict(ini["emummc"])
        e.update({"ini_present": True, "active": d.get("enabled", "0") not in ("0", ""), "brut": d})
        secteur = d.get("sector", "0x0")
        if secteur and secteur not in ("0", "0x0"):
            e["type"] = "partition"
        elif d.get("path"):
            e["type"] = "fichiers"
            e["dossier"] = d.get("path")
            dp = os.path.join(r, d["path"])
            if os.path.isdir(dp):
                e["taille"] = _taille_dossier(dp)
        e["nintendo_path"] = d.get("nintendo_path")
    return e


def _sysmodules(r: str) -> list[dict]:
    base = os.path.join(r, "atmosphere", "contents")
    out = []
    if not os.path.isdir(base):
        return out
    for tid in sorted(os.listdir(base)):
        p = os.path.join(base, tid)
        if not os.path.isdir(p) or tid.startswith("."):
            continue
        exefs = os.path.isfile(os.path.join(p, "exefs.nsp"))
        boot2 = os.path.isfile(os.path.join(p, "flags", "boot2.flag"))
        if not exefs:
            continue   # contenu de jeu (mods LayeredFS, cheats) : pas un module systeme
        out.append({"tid": tid.upper(), "nom": connus.TIDS.get(tid.upper()), "demarre_seul": boot2,
                    "toolbox": os.path.isfile(os.path.join(p, "toolbox.json"))})
    return out


def _nros(r: str, dossier: str, ext: tuple[str, ...], profondeur: int = 0) -> list[dict]:
    """Les .nro / .ovl de `dossier`, et de ses sous-dossiers jusqu'a `profondeur` (dossiers caches ignores)."""
    out = []
    base = os.path.join(r, dossier) if dossier else r
    if not os.path.isdir(base):
        return out
    for racine, ds, fs in os.walk(base):
        niveau = 0 if racine == base else os.path.relpath(racine, base).count(os.sep) + 1
        ds[:] = sorted(d for d in ds if not d.startswith(".")) if niveau < profondeur else []
        for f in sorted(fs):
            if f.lower().endswith(ext) and not f.startswith("._"):
                p = os.path.join(racine, f)
                n = versions.nacp(p) or {}
                out.append({"fichier": os.path.relpath(p, r), "nom": n.get("nom") or f.rsplit(".", 1)[0],
                            "version": n.get("version"), "auteur": n.get("auteur"), "taille": versions.taille(p)})
    return out


def _sauvegardes(r: str) -> dict:
    s = {"nand": [], "cles": [], "jksv": None}
    b = os.path.join(r, "backup")
    if os.path.isdir(b):
        for ident in sorted(os.listdir(b)):
            p = os.path.join(b, ident)
            if not os.path.isdir(p) or ident.startswith("."):
                continue
            fichiers = []
            for racine, _, fs in os.walk(p):
                for f in fs:
                    if not f.startswith("._"):
                        q = os.path.join(racine, f)
                        fichiers.append({"nom": os.path.relpath(q, p), "taille": versions.taille(q),
                                         "date": int(os.path.getmtime(q))})
            noms = {x["nom"].split("/")[-1].lower() for x in fichiers}
            s["nand"].append({
                "id": ident, "fichiers": fichiers,
                "boot0": "boot0" in noms, "boot1": "boot1" in noms,
                "rawnand": any(n.startswith("rawnand.bin") for n in noms),
                "prodinfo": any("prodinfo" in n for n in noms),
                "taille": sum(x["taille"] for x in fichiers),
            })
    for c in ("switch/prod.keys", "switch/title.keys", "prod.keys"):
        if os.path.isfile(os.path.join(r, c)):
            s["cles"].append(c)
    j = os.path.join(r, "JKSV")
    if os.path.isdir(j):
        jeux = [d for d in os.listdir(j) if os.path.isdir(os.path.join(j, d)) and not d.startswith((".", "_"))]
        s["jksv"] = {"jeux": len(jeux)}
    return s


def auditer(racine: str) -> dict:
    debut = time.time()
    r = os.path.abspath(racine)
    if not os.path.isdir(r):
        return {"ok": False, "erreur": f"dossier introuvable : {r}"}
    audit = {
        "ok": True, "racine": r, "lu_a": int(time.time()), "volume": _volume(r),
        "atmosphere": _atmosphere(r), "hekate": _hekate(r), "emummc": _emummc(r),
        "sysmodules": _sysmodules(r),
        "overlays": _nros(r, "switch/.overlays", (".ovl",)),
        "homebrew": _nros(r, "", (".nro",)) + _nros(r, "switch", (".nro",), profondeur=1),
        "sauvegardes": _sauvegardes(r), "traces_mac": _traces_mac(r),
        "nintendo": os.path.isdir(os.path.join(r, "Nintendo")),
    }
    tp = os.path.join(r, "config", "sys-clk", "config.ini")
    audit["sys_clk_config"] = os.path.isfile(tp)
    audit["constats"] = constats(audit)
    audit["bouclier"] = bouclier(audit)
    audit["duree_ms"] = int((time.time() - debut) * 1000)
    return audit


def _c(niveau: str, cle: str, titre: str, detail: str, action: str | None = None, page: str | None = None) -> dict:
    return {"niveau": niveau, "cle": cle, "titre": titre, "detail": detail, "action": action, "page": page}


def constats(a: dict) -> list[dict]:
    """Ce qui merite un regard, du plus grave au plus doux. 'alerte' > 'att' > 'ok'."""
    out = []
    v = a["volume"]
    if not a["atmosphere"]["present"]:
        out.append(_c("alerte", "sans_atmosphere", "Atmosphère est absent de cette carte",
                      "Sans le dossier atmosphere/, la console ne peut démarrer qu'en mode d'origine.", "Installer Atmosphère", "maj"))
    elif not a["atmosphere"]["version"]:
        out.append(_c("att", "atmosphere_illisible", "Version d'Atmosphère illisible",
                      "Le fichier atmosphere/package3 manque ou ne ressemble pas à une release officielle.", "Réinstaller Atmosphère", "maj"))
    if not a["hekate"]["present"]:
        out.append(_c("alerte", "sans_hekate", "Hekate est absent de cette carte",
                      "Une V1 en RCM a besoin du dossier bootloader/ pour démarrer Atmosphère.", "Installer Hekate", "maj"))
    elif a["hekate"]["version"] and a["hekate"]["nyx"] is None:
        out.append(_c("att", "sans_nyx", "Nyx manque", "bootloader/sys/nyx.bin est absent : l'interface tactile de Hekate ne s'ouvrira pas.",
                      "Réinstaller Hekate", "maj"))
    if not a["hekate"]["ini_present"] and a["hekate"]["present"]:
        out.append(_c("att", "sans_ini", "Pas de menu de démarrage",
                      "bootloader/hekate_ipl.ini manque : Hekate n'a aucune entrée « Atmosphère » à proposer.", "Créer le menu", "carte"))
    sys = (v.get("systeme") or "").lower()
    if "exfat" in sys:
        out.append(_c("att", "exfat", "Carte en exFAT",
                      "Le pilote exFAT de la Switch corrompt plus facilement les cartes. FAT32 est le format sûr (sauvegarder, reformater, recopier).",
                      None, "carte"))
    if v.get("taille") and v.get("libre") is not None and v["libre"] < 0.05 * v["taille"]:
        out.append(_c("att", "sd_pleine", "Carte presque pleine", "Moins de 5 % d'espace libre : les mises à jour et les saves peuvent échouer.", None, "carte"))
    t = a["traces_mac"]["total"]
    if t:
        out.append(_c("att", "traces_mac", f"{t} trace{'s' if t > 1 else ''} laissée{'s' if t > 1 else ''} par macOS",
                      "Les fichiers ._* et dossiers .Spotlight/.fseventsd gênent certains homebrews et Hekate.",
                      "Nettoyer", "carte"))
    e = a["emummc"]
    if not e["ini_present"] or not e["active"]:
        out.append(_c("alerte", "sans_emummc", "Pas d'emuMMC active",
                      "Le CFW tourne sur la mémoire interne (sysNAND) : c'est elle qui prend les risques et les bans.", None, "bouclier"))
    hosts = a["atmosphere"]["hosts"]
    if e.get("active") and not (hosts.get("emummc.txt", {}).get("bloque_nintendo") or hosts.get("default.txt", {}).get("bloque_nintendo")):
        out.append(_c("att", "sans_hosts", "Nintendo n'est pas bloqué dans l'emuMMC",
                      "Sans fichier atmosphere/hosts/emummc.txt, l'emuMMC peut parler aux serveurs Nintendo.", "Poser le bouclier DNS", "bouclier"))
    exo = a["atmosphere"]["exosphere"] or {}
    if e.get("active") and exo.get("blank_prodinfo_emummc") != "1":
        out.append(_c("att", "prodinfo_visible", "L'emuMMC montre l'identité de la console",
                      "exosphere.ini : blank_prodinfo_emummc=1 masque le numéro de série dans l'emuMMC.", "Masquer", "bouclier"))
    sv = a["sauvegardes"]
    if not any(n["boot0"] and n["boot1"] and n["rawnand"] for n in sv["nand"]):
        out.append(_c("alerte", "sans_nand", "Aucune sauvegarde NAND complète sur la carte",
                      "BOOT0, BOOT1 et rawnand.bin : la seule assurance contre une brique. Hekate la fait en 20 à 40 minutes.",
                      "Voir comment", "sauvegardes"))
    if not a["atmosphere"]["prodinfo_auto"] and a["atmosphere"]["present"]:
        out.append(_c("att", "sans_prodinfo", "Pas de copie automatique de PRODINFO",
                      "Atmosphère la fait au premier démarrage (atmosphere/automatic_backups). Démarre une fois en CFW.", None, "sauvegardes"))
    noms_ovl = {o["fichier"].split("/")[-1].lower() for o in a["overlays"]}
    if a["overlays"] and not any(m["tid"] == "420000000007E51A" for m in a["sysmodules"]):
        out.append(_c("att", "ovl_sans_loader", "Des overlays sans leur chargeur",
                      "nx-ovlloader manque : les overlays présents ne s'ouvriront pas.", "Installer nx-ovlloader", "maj"))
    if a["overlays"] and "ovlmenu.ovl" not in noms_ovl:
        out.append(_c("att", "ovl_sans_menu", "Des overlays sans le Tesla Menu", "switch/.overlays/ovlmenu.ovl manque.", "Installer", "maj"))
    if "quickntp.ovl" not in noms_ovl:
        out.append(_c("ok", "horloge", "L'horloge repart de zéro à chaque batterie vide",
                      "Sur ta V1, une batterie à 0 % remet la date à zéro. QuickNTP la recale en un geste.", "Ajouter QuickNTP", "atelier"))
    if not out:
        out.append(_c("ok", "rien", "Rien à signaler", "La carte est propre et complète.", None, None))
    ordre = {"alerte": 0, "att": 1, "ok": 2}
    return sorted(out, key=lambda c: ordre[c["niveau"]])


def bouclier(a: dict) -> dict:
    """Le score anti-ban, cinq points vérifiables sur la carte, et ce qu'on ne peut PAS vérifier d'ici."""
    e, at = a["emummc"], a["atmosphere"]
    hosts = at["hosts"]
    exo = at["exosphere"] or {}
    points = [
        {"cle": "emummc", "titre": "Le CFW tourne dans une emuMMC", "ok": bool(e.get("ini_present") and e.get("active")),
         "pourquoi": "La mémoire interne reste d'origine, propre, utilisable en ligne."},
        {"cle": "hosts", "titre": "Les serveurs Nintendo sont bloqués dans l'emuMMC",
         "ok": bool(hosts.get("emummc.txt", {}).get("bloque_nintendo") or hosts.get("default.txt", {}).get("bloque_nintendo")),
         "pourquoi": "dns.mitm d'Atmosphère renvoie *nintendo* vers 127.0.0.1 : rien ne sort."},
        {"cle": "prodinfo", "titre": "L'identité de la console est masquée dans l'emuMMC",
         "ok": exo.get("blank_prodinfo_emummc") == "1",
         "pourquoi": "exosphere.ini : le numéro de série n'est jamais présenté depuis le CFW."},
        {"cle": "sysnand_propre", "titre": "Une entrée « sysNAND d'origine » existe dans Hekate",
         "ok": any(x["sysnand"] and not x["atmosphere"] for x in a["hekate"]["entrees"]) or
               any(x.get("payload") is None and x["sysnand"] for x in a["hekate"]["entrees"]),
         "pourquoi": "Pour jouer en ligne sur la mémoire interne sans rien charger."},
        {"cle": "nand", "titre": "Une sauvegarde NAND complète existe",
         "ok": any(n["boot0"] and n["boot1"] and n["rawnand"] for n in a["sauvegardes"]["nand"]),
         "pourquoi": "Le retour arrière en cas de brique ou de ban."},
    ]
    inconnus = [
        "Le DNS 90DNS dans les réglages Wi-Fi de la console (il vit dans la console, pas sur la carte).",
        "L'AutoRCM (il vit dans BOOT0 : Hekate le montre dans Outils).",
        "Le firmware de la console et celui de l'emuMMC.",
    ]
    return {"points": points, "score": sum(1 for p in points if p["ok"]), "sur": len(points), "inconnus": inconnus}
