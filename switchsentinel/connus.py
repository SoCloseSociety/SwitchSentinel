"""Ce que SwitchSentinel connait : le catalogue des essentiels (re-verifie sur GitHub le 11/11/2026) et les title IDs.

Revisions des sources le 11/11/2026 (vues sur la carte de l'owner) :
  - sys-con : cathery/sys-con est fige a 0.6.5 (2024) -> fork actif o0Zz/sys-con (2.1.0), celui reellement installe.
  - Status Monitor : masagrator/Status-Monitor-Overlay est ARCHIVE (2026) -> fork Ultrahand ppkantorski/... maintenu.
  - Tesla Menu : legacy, remplace par Ultrahand (deja installe).

Regle : homebrew, sauvegarde, securite, confort. Aucune boutique, aucun installateur de jeux, aucun sigpatch.
`pose` dit comment une release se pose sur la SD :
  - "racine"           : le zip a deja l'arborescence de la SD (atmosphere/, switch/, config/...)
  - "fichier:<chemin>" : l'asset seul va a ce chemin
"""
from __future__ import annotations

COEUR = [
    {"id": "atmosphere", "nom": "Atmosphère", "repo": "Atmosphere-NX/Atmosphere", "famille": "coeur",
     "role": "Le firmware personnalisé : tout le reste repose dessus.",
     "asset": r"^atmosphere-.*\.zip$", "pose": "racine", "essentiel": True},
    {"id": "hekate", "nom": "Hekate", "repo": "CTCaer/hekate", "famille": "coeur",
     "role": "Le bootloader et la boîte à outils (emuMMC, sauvegardes NAND, carte SD en USB).",
     "asset": r"^hekate_ctcaer_[\d.]+_Nyx_[\d.]+\.zip$", "pose": "racine", "essentiel": True},
]

CATALOGUE = [
    {"id": "sys-clk", "nom": "sys-clk", "repo": "retronx-team/sys-clk", "famille": "performance",
     "role": "Overclock ou underclock par jeu, profils dock et portable.", "tid": "00FF0000636C6BFF",
     "version_depuis": "switch/.overlays/sys-clk-overlay.ovl", "asset": r"^sys-clk-.*\.zip$", "pose": "racine"},
    {"id": "nx-ovlloader", "nom": "nx-ovlloader", "repo": "WerWolv/nx-ovlloader", "famille": "overlays",
     "role": "Le chargeur d'overlays Tesla (indispensable aux overlays).", "tid": "420000000007E51A",
     "asset": r"^nx-ovlloader\.zip$", "pose": "racine", "essentiel": True},
    {"id": "tesla-menu", "nom": "Tesla Menu", "repo": "WerWolv/Tesla-Menu", "famille": "overlays",
     "role": "Le menu des overlays (L + Bas + R3). Legacy : remplacé par Ultrahand, déjà installé.",
     "fichier": "switch/.overlays/ovlmenu.ovl", "version_depuis": "switch/.overlays/ovlmenu.ovl",
     "asset": r"^ovlmenu\.zip$", "pose": "racine", "essentiel": True},
    {"id": "status-monitor", "nom": "Status Monitor", "repo": "ppkantorski/Status-Monitor-Overlay", "famille": "overlays",
     "role": "Températures, fréquences, FPS et batterie en direct. Fork Ultrahand maintenu ; masagrator/... est archivé.",
     "fichier": "switch/.overlays/Status-Monitor-Overlay.ovl", "version_depuis": "switch/.overlays/Status-Monitor-Overlay.ovl",
     "asset": r"^Status-Monitor-Overlay\.ovl$", "pose": "fichier:switch/.overlays/Status-Monitor-Overlay.ovl"},
    {"id": "quickntp", "nom": "QuickNTP", "repo": "nedex/QuickNTP", "famille": "overlays",
     "role": "Remet l'horloge à l'heure par Internet : utile après chaque batterie à zéro.",
     "fichier": "switch/.overlays/quickntp.ovl", "version_depuis": "switch/.overlays/quickntp.ovl",
     "asset": r"^quickntp-[\d.]+\.zip$", "pose": "racine", "essentiel": True},
    {"id": "missioncontrol", "nom": "MissionControl", "repo": "ndeadly/MissionControl", "famille": "manettes",
     "role": "Manettes PS4, PS5, Xbox et autres en Bluetooth, sans adaptateur.", "tid": "010000000000BD00",
     "asset": r"^MissionControl-.*\.zip$", "pose": "racine"},
    {"id": "sys-con", "nom": "sys-con", "repo": "o0Zz/sys-con", "famille": "manettes",
     "role": "Manettes USB filaires (PS5, PS4, Xbox). Fork actif 2.x ; cathery/sys-con est fige a 0.6.5.",
     "tid": "690000000000000D", "asset": r"^sys-con-.*\.zip$", "pose": "racine"},
    {"id": "jksv", "nom": "JKSV", "repo": "J-D-K/JKSV", "famille": "sauvegarde",
     "role": "Sauvegarde et restauration des parties (saves) de tes jeux.",
     "fichier": "switch/JKSV.nro", "version_depuis": "switch/JKSV.nro",
     "asset": r"^JKSV\.nro$", "pose": "fichier:switch/JKSV.nro", "essentiel": True},
    {"id": "ftpd", "nom": "ftpd", "repo": "mtheall/ftpd", "famille": "fichiers",
     "role": "La carte SD par le Wi-Fi (FTP) : plus besoin de câble pour copier.",
     "fichier": "switch/ftpd.nro", "version_depuis": "switch/ftpd.nro",
     "asset": r"^ftpd\.nro$", "pose": "fichier:switch/ftpd.nro"},
    {"id": "nx-shell", "nom": "NX-Shell", "repo": "joel16/NX-Shell", "famille": "fichiers",
     "role": "Un explorateur de fichiers sur la console.",
     "fichier": "switch/NX-Shell.nro", "version_depuis": "switch/NX-Shell.nro",
     "asset": r"^NX-Shell\.nro$", "pose": "fichier:switch/NX-Shell.nro"},
    {"id": "hb-appstore", "nom": "Homebrew App Store", "repo": "fortheusers/hb-appstore", "famille": "fichiers",
     "role": "Le magasin d'apps homebrew (libres et gratuites).",
     "fichier": "switch/appstore/appstore.nro", "version_depuis": "switch/appstore/appstore.nro",
     "asset": r"^appstore\.nro$", "pose": "fichier:switch/appstore/appstore.nro"},
    {"id": "nxthemes", "nom": "NXThemes Installer", "repo": "exelix11/SwitchThemeInjector", "famille": "confort",
     "role": "Thèmes du menu HOME.",
     "fichier": "switch/NXThemesInstaller.nro", "version_depuis": "switch/NXThemesInstaller.nro",
     "asset": r"^NXThemesInstaller\.nro$", "pose": "fichier:switch/NXThemesInstaller.nro"},
    {"id": "fizeau", "nom": "Fizeau", "repo": "averne/Fizeau", "famille": "confort",
     "role": "Couleurs de l'écran et filtre de lumière bleue, à l'heure près.", "tid": "0100000000000F12",
     "asset": r"^Fizeau-.*\.zip$", "pose": "racine"},
    {"id": "edizon", "nom": "EdiZon", "repo": "WerWolv/EdiZon", "famille": "confort",
     "role": "Gestionnaire de cheats en overlay, pour tes propres jeux.",
     "fichier": "switch/.overlays/ovlEdiZon.ovl", "version_depuis": "switch/.overlays/ovlEdiZon.ovl",
     "asset": r"^ovlEdiZon\.ovl$", "pose": "fichier:switch/.overlays/ovlEdiZon.ovl"},
    {"id": "ldn_mitm", "nom": "ldn_mitm", "repo": "spacemeowx2/ldn_mitm", "famille": "reseau",
     "role": "Le jeu local en réseau (LAN play) entre consoles.", "tid": "4200000000000010",
     "asset": r"^ldn_mitm_.*\.zip$", "pose": "racine"},
    {"id": "sysdvr", "nom": "SysDVR", "repo": "exelix11/SysDVR", "famille": "reseau",
     "role": "Diffuser l'écran de la console sur le Mac (USB ou Wi-Fi).", "tid": "00FF0000A53BB665",
     "asset": r"^SysDVR\.zip$", "pose": "racine"},
    {"id": "emuiibo", "nom": "emuiibo", "repo": "XorTroll/emuiibo", "famille": "confort",
     "role": "Emule tes amiibo à partir de tes propres sauvegardes.", "tid": "0100000000000352",
     "asset": r"^emuiibo\.zip$", "pose": "racine"},
    {"id": "tegraexplorer", "nom": "TegraExplorer", "repo": "suchmememanyskill/TegraExplorer", "famille": "secours",
     "role": "Un explorateur hors système, en payload : le secours quand rien ne démarre.",
     "fichier": "bootloader/payloads/TegraExplorer.bin",
     "asset": r"^TegraExplorer\.bin$", "pose": "fichier:bootloader/payloads/TegraExplorer.bin"},
]

FAMILLES = {
    "coeur": "Le cœur", "overlays": "Overlays", "performance": "Performance", "manettes": "Manettes",
    "sauvegarde": "Sauvegarde", "fichiers": "Fichiers", "confort": "Confort", "reseau": "Réseau", "secours": "Secours",
}

# Les title IDs connus. Tout autre module s'affiche « inconnu », avec son identifiant : on ne devine pas.
TIDS = {
    "00FF0000636C6BFF": "sys-clk",
    "420000000007E51A": "nx-ovlloader (Tesla)",
    "010000000000BD00": "MissionControl",
    "690000000000000D": "sys-con",
    "4200000000000010": "ldn_mitm",
    "0100000000000F12": "Fizeau",
    "00FF0000A53BB665": "SysDVR",
    "0100000000000352": "emuiibo",
    "420000000000000E": "sys-ftpd",
    "00FF747765616BFF": "sys-tweak",
    "0000000000534C56": "SaltyNX",
    "430000000000000B": "sys-botbase",
}

# Les identifiants USB (releves dans le code de Hekate et de fusee-launcher).
USB = {
    (0x0955, 0x7321): ("rcm", "Mode RCM (APX)"),
    (0x11EC, 0xA7E0): ("hekate_ums", "Hekate, carte SD ou eMMC en USB"),
    (0x11EC, 0xA7E1): ("hekate", "Hekate (manette USB)"),
    (0x11EC, 0xA7E2): ("hekate", "Hekate (USB)"),
    (0x057E, 0x2000): ("horizon", "Console démarrée (système)"),
    (0x057E, 0x3000): ("horizon", "Console démarrée (usbd)"),
}

# Les domaines a garder loin d'une console moddee (dns.mitm d'Atmosphere, fichier hosts).
HOSTS_RECOMMANDES = """# SwitchSentinel : bloque les serveurs Nintendo pour cette emuMMC (dns.mitm d'Atmosphere).
127.0.0.1 *nintendo.com
127.0.0.1 *nintendo.net
127.0.0.1 *nintendo.jp
127.0.0.1 *nintendo.co.jp
127.0.0.1 *nintendo.co.uk
127.0.0.1 *nintendo-europe.com
127.0.0.1 *nintendowifi.net
127.0.0.1 *nintendo.es
127.0.0.1 *nintendo.co.kr
127.0.0.1 *nintendo.tw
127.0.0.1 *nintendo.com.hk
127.0.0.1 *nintendo.com.au
127.0.0.1 *nintendo.co.nz
127.0.0.1 *nintendo.at
127.0.0.1 *nintendo.be
127.0.0.1 *nintendods.cz
127.0.0.1 *nintendo.dk
127.0.0.1 *nintendo.de
127.0.0.1 *nintendo.fi
127.0.0.1 *nintendo.fr
127.0.0.1 *nintendo.gr
127.0.0.1 *nintendo.hu
127.0.0.1 *nintendo.it
127.0.0.1 *nintendo.nl
127.0.0.1 *nintendo.no
127.0.0.1 *nintendo.pt
127.0.0.1 *nintendo.ru
127.0.0.1 *nintendo.co.za
127.0.0.1 *nintendo.se
127.0.0.1 *nintendo.ch
127.0.0.1 *nintendo.pl
127.0.0.1 *nintendoswitch.com
127.0.0.1 *nintendoswitch.com.cn
127.0.0.1 *nintendoswitch.cn
95.216.149.205 *conntest.nintendowifi.net
95.216.149.205 *ctest.cdn.nintendo.net
"""


def par_id(ident: str) -> dict | None:
    for e in COEUR + CATALOGUE:
        if e["id"] == ident:
            return e
    return None
