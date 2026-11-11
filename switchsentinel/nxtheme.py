"""Lire/ecrire les thèmes HOME Switch (.nxtheme) -- Yaz0 + SARC + ZIP (11/11/2026).

Un .nxtheme est soit un ZIP (magic "PK", format recent), soit un SARC (eventuellement compresse Yaz0, format
« legacy » de themezer). Les deux portent : `info.json` (Version, Target...), une image (`image.dds`/`image.jpg`),
et souvent `layout.json` / `common.json` (la DISPOSITION : dock, menus, transparences...).

Ici : decompression Yaz0 et lecture SARC (purs, sans dependance) pour EXTRAIRE les fichiers d'un .nxtheme existant,
et `ecrire_zip()` pour en reconstruire un au format ZIP (que l'installeur accepte) -- on garde ainsi le layout
cyberpunk de l'owner en ne remplacant que l'image de fond.
"""
from __future__ import annotations

import io
import json
import struct
import zipfile


def yaz0_decompresser(data: bytes) -> bytes:
    if data[:4] != b"Yaz0":
        return data
    taille = struct.unpack_from(">I", data, 4)[0]
    src, out = 16, bytearray()
    while len(out) < taille and src < len(data):
        code = data[src]; src += 1
        for _ in range(8):
            if len(out) >= taille:
                break
            if code & 0x80:
                out.append(data[src]); src += 1
            else:
                b1, b2 = data[src], data[src + 1]; src += 2
                n = b1 >> 4
                if n == 0:
                    n = data[src] + 0x12; src += 1
                else:
                    n += 2
                dist = ((b1 & 0xF) << 8 | b2) + 1
                debut = len(out) - dist
                for j in range(n):
                    out.append(out[debut + j])
            code = (code << 1) & 0xFF
    return bytes(out)


def sarc_lire(data: bytes) -> dict[str, bytes]:
    """Deballe un SARC (petit-boutiste, Switch) -> {nom: contenu}. Decompresse Yaz0 au besoin."""
    data = yaz0_decompresser(data)
    if data[:4] != b"SARC":
        raise ValueError("pas un SARC")
    data_offset = struct.unpack_from("<I", data, 0x0C)[0]
    if data[0x14:0x18] != b"SFAT":
        raise ValueError("SFAT manquant")
    node_count = struct.unpack_from("<H", data, 0x1A)[0]
    sfat = 0x20
    sfnt = sfat + node_count * 0x10
    noms_base = sfnt + 0x8                      # apres l'entete SFNT
    out = {}
    for i in range(node_count):
        off = sfat + i * 0x10
        attrs, start, end = struct.unpack_from("<III", data, off + 4)
        nom_off = (attrs & 0xFFFFFF) * 4
        p = noms_base + nom_off
        fin = data.index(b"\x00", p)
        nom = data[p:fin].decode("utf-8", "replace")
        out[nom] = data[data_offset + start:data_offset + end]
    return out


def lire(chemin: str) -> dict:
    """Lit un .nxtheme (ZIP ou SARC/Yaz0) -> {'fichiers': {nom: bytes}, 'info': dict|None}."""
    data = open(chemin, "rb").read()
    if data[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(data))
        fichiers = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    else:
        fichiers = sarc_lire(data)
    info = None
    if "info.json" in fichiers:
        try:
            info = json.loads(fichiers["info.json"].decode("utf-8", "replace"))
        except ValueError:
            pass
    return {"fichiers": fichiers, "info": info}


def ecrire_zip(chemin: str, fichiers: dict[str, bytes]) -> None:
    """Ecrit un .nxtheme au format ZIP (accepte par l'installeur) depuis {nom: bytes}."""
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, data in fichiers.items():
            z.writestr(nom, data)
