"""Lire les versions directement dans les binaires de la carte SD (07/11/2026).

Signatures relevees sur les releases officielles (tests/fixtures/sd-officielle, Atmosphere 1.12.1 + Hekate 6.5.4) :

- Hekate  : `ICTC` puis trois chiffres ASCII (`ICTC654` = 6.5.4), a 0x118 de `bootloader/update.bin`.
- Nyx     : `GCTC` puis trois chiffres (`GCTC194` = 1.9.4), vers 0x9c de `bootloader/sys/nyx.bin`.
- package3: en-tete `FSS0` (0x20) ; +0x14 = firmware maximal supporte, +0x18 = version d'Atmosphere,
            +0x1c = debut du hash git, chacun en u32 petit-boutiste `(majeur << 24) | (mineur << 16) | (micro << 8)`.
- NRO/OVL : `NRO0` a 0x10, taille a 0x18 ; la section `ASET` suit, elle pointe la NACP (nom, auteur, version).

Une version illisible rend None : on dit « inconnue », on ne devine jamais.
"""
from __future__ import annotations

import os
import re
import struct


def _lire(chemin: str, taille: int, depuis: int = 0) -> bytes:
    try:
        with open(chemin, "rb") as f:
            f.seek(depuis)
            return f.read(taille)
    except OSError:
        return b""


def _trois_chiffres(b: bytes, magie: bytes) -> str | None:
    i = b.find(magie)
    if i < 0:
        return None
    v = b[i + 4:i + 7]
    if len(v) == 3 and all(48 <= c <= 57 for c in v):
        return ".".join(chr(c) for c in v)
    return None


def version_hekate(chemin: str) -> str | None:
    """Un payload Hekate (`bootloader/update.bin`, `hekate_ctcaer_*.bin`)."""
    return _trois_chiffres(_lire(chemin, 0x400), b"ICTC")


def version_nyx(chemin: str) -> str | None:
    return _trois_chiffres(_lire(chemin, 0x400), b"GCTC")


def _u32_version(v: int) -> str:
    return f"{(v >> 24) & 0xFF}.{(v >> 16) & 0xFF}.{(v >> 8) & 0xFF}"


def package3(chemin: str) -> dict | None:
    """`atmosphere/package3` -> {version, firmware_max, hash}."""
    b = _lire(chemin, 0x200)
    if not b.startswith(b"PK31"):
        return None
    i = b.find(b"FSS0")
    if i < 0 or len(b) < i + 0x20:
        return None
    fw, ams, h = struct.unpack_from("<III", b, i + 0x14)
    if not ams:
        return None
    return {"version": _u32_version(ams), "firmware_max": _u32_version(fw), "hash": f"{h:08x}"}


def _chaine(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()


def nacp(chemin: str) -> dict | None:
    """Nom, auteur et version d'un .nro ou d'un .ovl (les overlays Tesla sont des NRO)."""
    tete = _lire(chemin, 0x20)
    if len(tete) < 0x20 or tete[0x10:0x14] != b"NRO0":
        return None
    taille = struct.unpack_from("<I", tete, 0x18)[0]
    aset = _lire(chemin, 0x38, taille)
    if len(aset) < 0x38 or aset[:4] != b"ASET":
        return None
    off, long_ = struct.unpack_from("<QQ", aset, 0x18)
    if long_ < 0x3070:
        return None
    n = _lire(chemin, 0x4000, taille + off)
    if len(n) < 0x3070:
        return None
    nom = auteur = ""
    for k in range(16):
        e = n[k * 0x300:(k + 1) * 0x300]
        nom, auteur = _chaine(e[:0x200]), _chaine(e[0x200:0x300])
        if nom:
            break
    version = _chaine(n[0x3060:0x3070])
    return {"nom": nom or None, "auteur": auteur or None, "version": version or None}


def normaliser(v: str | None) -> tuple[int, ...] | None:
    """`v1.2.3`, `1.2.3-master`, `nxt-3.0.2`, `12/02/2025` -> tuple d'entiers ; None si rien a comparer."""
    if not v:
        return None
    nums = re.findall(r"\d+", v)
    return tuple(int(x) for x in nums) if nums else None


def comparer(installee: str | None, derniere: str | None) -> str:
    """'a_jour' | 'en_retard' | 'en_avance' | 'inconnu'. Les dates JJ/MM/AAAA (JKSV) se comparent a l'envers."""
    a, b = normaliser(installee), normaliser(derniere)
    if a is None or b is None:
        return "inconnu"
    if len(a) == 3 and len(b) == 3 and a[2] > 1900 and b[2] > 1900:   # une date : annee, mois, jour
        a, b = (a[2], a[1], a[0]), (b[2], b[1], b[0])
    n = max(len(a), len(b))
    a, b = a + (0,) * (n - len(a)), b + (0,) * (n - len(b))
    if a == b:
        return "a_jour"
    return "en_retard" if a < b else "en_avance"


def empreinte_courte(chemin: str) -> str | None:
    import hashlib
    try:
        h = hashlib.sha256()
        with open(chemin, "rb") as f:
            for bloc in iter(lambda: f.read(1 << 20), b""):
                h.update(bloc)
        return h.hexdigest()[:16]
    except OSError:
        return None


def taille(chemin: str) -> int:
    try:
        return os.path.getsize(chemin)
    except OSError:
        return 0
