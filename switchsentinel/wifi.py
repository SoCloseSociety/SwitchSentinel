"""Installer / mettre a jour la Switch par le Wi-Fi, sans cable ni carte (11/11/2026).

Quand la console tourne en CFW avec **ftpd** (deja installe), elle sert sa carte SD en FTP. Le Mac et la Switch
sont sur le meme Wi-Fi -> on pousse les fichiers (homebrew, overlays, thèmes, mises a jour) directement sur la
carte, a distance. Bibliotheque standard (ftplib) uniquement.

ftpd : port 5000 par defaut, connexion anonyme, la racine FTP = la racine de la carte SD. Donc pousser vers
`switch/moontlight.nro` ecrit `SD:/switch/moonlight.nro`. On reste dans le perimetre : homebrew, confort, thèmes.
"""
from __future__ import annotations

import ftplib
import os
import posixpath
import socket
import subprocess
import threading

PORT_DEFAUT = 5000
MARQUEURS_SD = ("atmosphere", "bootloader", "switch", "Nintendo", "themes")


def _mon_reseau() -> str | None:
    """Le prefixe /24 du Mac (ex: '192.168.1.') pour balayer le reseau local."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip.rsplit(".", 1)[0] + "."
    except OSError:
        return None


def scanner(port: int = PORT_DEFAUT, timeout: float = 0.3) -> list[dict]:
    """Balaye le /24 local : qui repond sur le port ftpd ? Renvoie les Switch probables."""
    prefixe = _mon_reseau()
    if not prefixe:
        return []
    trouves, verrou = [], threading.Lock()

    def sonder(n: int):
        ip = f"{prefixe}{n}"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                r = tester(ip, port, timeout=3)
                if r.get("ok"):
                    with verrou:
                        trouves.append(r)

    fils = [threading.Thread(target=sonder, args=(n,)) for n in range(1, 255)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    return sorted(trouves, key=lambda r: [int(x) for x in r["ip"].split(".")])


def _ouvrir(ip: str, port: int, timeout: float) -> ftplib.FTP:
    f = ftplib.FTP(timeout=timeout)
    f.connect(ip, port)
    f.login()                       # ftpd accepte l'anonyme
    return f


def tester(ip: str, port: int = PORT_DEFAUT, timeout: float = 8) -> dict:
    """Confirme qu'on joint bien une Switch (ftpd) et renvoie le contenu de la racine."""
    try:
        f = _ouvrir(ip, port, timeout)
        banniere = f.getwelcome()
        try:
            noms = f.nlst()
        except ftplib.error_perm:
            noms = []
        f.quit()
        return {"ok": True, "ip": ip, "port": port, "banniere": banniere,
                "ressemble_switch": any(m in noms for m in MARQUEURS_SD),
                "racine": sorted(n for n in noms if not n.startswith("."))[:25]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ip": ip, "port": port, "erreur": f"{type(e).__name__}: {e}"}


def _mkdirs(f: ftplib.FTP, chemin_distant: str) -> None:
    parts = chemin_distant.strip("/").split("/")[:-1]
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            f.mkd(cur)
        except ftplib.error_perm:
            pass                    # existe deja : tant mieux


def pousser(ip: str, fichiers: list[tuple[str, str]], port: int = PORT_DEFAUT, timeout: float = 30) -> dict:
    """Envoie une liste (chemin_local, chemin_sur_la_carte) sur la Switch par FTP."""
    try:
        f = _ouvrir(ip, port, timeout)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "erreur": f"connexion : {type(e).__name__}: {e}"}
    ecrits, erreurs, octets = [], [], 0
    try:
        for loc, rem in fichiers:
            rem = rem.replace("\\", "/").lstrip("/")
            if ".." in rem.split("/") or not os.path.isfile(loc):
                erreurs.append({"fichier": rem, "erreur": "chemin invalide ou source absente"})
                continue
            try:
                _mkdirs(f, rem)
                with open(loc, "rb") as fh:
                    f.storbinary("STOR " + rem, fh)
                ecrits.append(rem)
                octets += os.path.getsize(loc)
            except Exception as e:  # noqa: BLE001
                erreurs.append({"fichier": rem, "erreur": f"{type(e).__name__}: {e}"})
    finally:
        try:
            f.quit()
        except Exception:  # noqa: BLE001
            pass
    return {"ok": not erreurs, "ecrits": ecrits, "erreurs": erreurs, "octets": octets}


def pousser_dossier(ip: str, dossier_local: str, prefixe_distant: str = "", port: int = PORT_DEFAUT) -> dict:
    """Pousse tout un dossier (ex: un thème, un homebrew extrait) vers la carte, en gardant l'arborescence."""
    fichiers = []
    base = os.path.abspath(dossier_local)
    for racine, _, fs in os.walk(base):
        for nm in fs:
            if nm.startswith("._") or nm == ".DS_Store":
                continue
            loc = os.path.join(racine, nm)
            rel = os.path.relpath(loc, base)
            rem = posixpath.join(prefixe_distant, rel.replace(os.sep, "/")) if prefixe_distant else rel.replace(os.sep, "/")
            fichiers.append((loc, rem))
    return pousser(ip, fichiers, port=port)
