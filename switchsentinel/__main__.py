"""SwitchSentinel en ligne de commande, et le lanceur de l'app (11/11/2026).

    .venv/bin/python -m switchsentinel app                 # ouvre l'app dans le navigateur (le defaut)
    .venv/bin/python -m switchsentinel etat                # le bus USB : RCM ? Hekate ? absente ?
    .venv/bin/python -m switchsentinel audit [--sd CHEMIN] # l'audit de la carte (la montee, sinon le dernier)
    .venv/bin/python -m switchsentinel manettes            # PS5/PS4/Xbox : MissionControl + sys-con
    .venv/bin/python -m switchsentinel payloads            # les payloads injectables
    .venv/bin/python -m switchsentinel injecter [--payload ID] [--oui]   # reveille la console en Hekate (RCM)
    .venv/bin/python -m switchsentinel maj --sd CHEMIN [--appliquer]     # plan, puis ecriture (sauvegarde avant)
    .venv/bin/python -m switchsentinel releases [--forcer] # les dernieres versions GitHub du catalogue

Lire ne demande rien. `injecter` et `maj --appliquer` touchent le materiel ou la carte : ils demandent `--oui`.
"""
from __future__ import annotations

import argparse
import json
import sys


def _p(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(prog="switchsentinel", description="L'atelier Switch, depuis ce dossier.")
    sub = a.add_subparsers(dest="cmd")

    pa = sub.add_parser("app", help="ouvrir l'app (serveur local + navigateur)")
    pa.add_argument("--port", type=int, default=8787)
    pa.add_argument("--sans-ouvrir", action="store_true")

    sub.add_parser("etat", help="l'etat du bus USB")
    pau = sub.add_parser("audit", help="auditer la carte SD"); pau.add_argument("--sd", default=None)
    pm = sub.add_parser("manettes", help="l'etat des manettes (PS5/PS4/Xbox)"); pm.add_argument("--sd", default=None)
    sub.add_parser("payloads", help="les payloads injectables")

    pi = sub.add_parser("injecter", help="injecter un payload (console en RCM)")
    pi.add_argument("--payload", default=None); pi.add_argument("--oui", action="store_true")

    pmaj = sub.add_parser("maj", help="mettre la carte a jour")
    pmaj.add_argument("--sd", required=True); pmaj.add_argument("--appliquer", action="store_true")

    pr = sub.add_parser("releases", help="les dernieres versions GitHub"); pr.add_argument("--forcer", action="store_true")

    pw = sub.add_parser("wifi", help="installer par Wi-Fi (ftpd sur la Switch)")
    pw.add_argument("--ip", required=True); pw.add_argument("--port", type=int, default=5000)
    pw.add_argument("--pousser", nargs=2, metavar=("LOCAL", "DISTANT"), action="append",
                    help="envoyer un fichier local vers un chemin de la carte (repetable)")

    x = a.parse_args(argv)
    cmd = x.cmd or "app"

    if cmd == "app":
        from .serveur import demarrer
        demarrer(port=x.port, ouvrir=not x.sans_ouvrir)
        return 0
    if cmd == "etat":
        from . import usb
        _p(usb.etat()); return 0
    if cmd == "audit":
        from . import carte_sd
        from .serveur import _sd_auto
        cible = _sd_auto(x.sd)
        if not cible:
            print("aucune carte montee (branche la carte, ou passe --sd CHEMIN)"); return 1
        _p(carte_sd.auditer(cible)); return 0
    if cmd == "manettes":
        from .serveur import manettes
        _p(manettes(x.sd)); return 0
    if cmd == "payloads":
        from . import injecteur
        _p({"pret": injecteur.pret(), "payloads": injecteur.payloads()}); return 0
    if cmd == "injecter":
        from . import injecteur, usb
        mode = usb.etat()["mode"]
        if mode != "rcm":
            print(f"la console n'est pas en RCM (mode : {mode}). RCM = jig dans le rail droit, Volume + maintenu, "
                  "puis Power. Puis relance."); return 1
        pay = injecteur.payloads()
        pid = x.payload or (pay[0]["id"] if pay else None)
        if not pid:
            print("aucun payload dans vendor/payloads"); return 1
        if not x.oui:
            print(f"injecterait : {pid}  (ajoute --oui pour reveiller vraiment la console)"); return 0
        _p(injecteur.injecter(pid)); return 0
    if cmd == "maj":
        from . import maj
        if not x.appliquer:
            return _maj_plan(maj, x.sd)
        print("sauvegarde puis ecriture...")
        _p(maj.appliquer(x.sd)); return 0
    if cmd == "releases":
        from . import depot
        _p(depot.releases(forcer=x.forcer)); return 0
    if cmd == "wifi":
        from . import wifi
        if x.pousser:
            _p(wifi.pousser(x.ip, [tuple(p) for p in x.pousser], port=x.port))
        else:
            _p(wifi.tester(x.ip, port=x.port))
        return 0
    a.print_help(); return 0


def _maj_plan(maj, sd: str) -> int:
    p = maj.plan(sd)
    for o in p["operations"]:
        n = sum(1 for l in p["lignes"] if l["op"] == o["id"] and l["action"] != "garder")
        print(f"{o['nom']:<28} -> {o['apres']:<14} {n} fichier(s)")
    print("total", p["resume"], "manquants", len(p["manquants"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
