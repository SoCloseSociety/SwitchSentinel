"""Le serveur local de SwitchSentinel : l'app qui vit dans ce dossier (11/11/2026).

    .venv/bin/python -m switchsentinel app            # ouvre http://127.0.0.1:8787 dans le navigateur
    .venv/bin/python -m switchsentinel app --port 9000 --sans-ouvrir

Rien que la bibliotheque standard (http.server) : aucune dependance en plus de celles de l'injecteur. Le serveur
n'ecoute QUE sur 127.0.0.1 (jamais le reseau), et les deux gestes qui touchent le materiel ou la carte -- injecter
un payload, ecrire la mise a jour -- exigent un corps JSON `{"confirmer": true}` ET une verification cote serveur
(la console doit etre en RCM pour injecter ; la carte doit etre un volume monte pour ecrire). Lire est libre ; agir
est garde.
"""
from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import carte_sd, connus, depot, injecteur, usb, versions, wifi

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(RACINE, "ui")
AUDIT_CACHE = os.path.join(RACINE, "data", "audit-sd.json")

TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "application/javascript; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml", ".ico": "image/x-icon",
         ".json": "application/json; charset=utf-8", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}

# Les modules homebrew qui apportent les manettes (title IDs lus dans l'audit).
TID_MISSIONCONTROL = "010000000000BD00"   # PS5 (DualSense), PS4, Xbox, 8BitDo... en Bluetooth
TID_SYSCON = "690000000000000D"           # les memes manettes, mais branchees en USB


# ─────────────────────────── ce que l'app sait dire ───────────────────────────

def _sd_auto(sd: str | None) -> str | None:
    """Le chemin de carte demande, sinon la premiere carte montee qui ressemble a une SD de Switch."""
    if sd and os.path.isdir(sd):
        return sd
    cands = carte_sd.candidats()
    return cands[0]["chemin"] if cands else None


def _audit_dernier() -> dict | None:
    try:
        with open(AUDIT_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def etat() -> dict:
    """L'etat vivant : le bus USB, la carte montee, ce qui est pret a injecter. Lu a chaque rafraichissement."""
    u = usb.etat()
    cands = carte_sd.candidats()
    pret = injecteur.pret()
    pay = injecteur.payloads()
    return {
        "usb": u,
        "carte_montee": cands[0] if cands else None,
        "cartes": cands,
        "injecteur": {"pret": pret, "payloads": pay,
                      "peut_injecter": u["mode"] == "rcm" and pret["pret"]},
        "dernier_audit_le": (_audit_dernier() or {}).get("lu_a"),
    }


def manettes(sd: str | None) -> dict:
    """L'etat des manettes : MissionControl (Bluetooth : PS5/PS4/Xbox) et sys-con (USB), lus sur la carte."""
    cible = _sd_auto(sd)
    a = carte_sd.auditer(cible) if cible else _audit_dernier()
    mods = {m["tid"]: m for m in (a or {}).get("sysmodules", [])}
    mc, sc = mods.get(TID_MISSIONCONTROL), mods.get(TID_SYSCON)
    return {
        "carte": cible,
        "source": "carte montee" if cible else "dernier audit",
        "bluetooth": {"module": "MissionControl", "tid": TID_MISSIONCONTROL, "installe": bool(mc),
                      "demarre_seul": bool(mc and mc.get("demarre_seul")),
                      "manettes": "PS5 (DualSense), PS4 (DualShock 4), Xbox One/Series, 8BitDo, et autres, sans dongle",
                      "repo": "ndeadly/MissionControl"},
        "usb": {"module": "sys-con", "tid": TID_SYSCON, "installe": bool(sc),
                "demarre_seul": bool(sc and sc.get("demarre_seul")),
                "manettes": "les memes manettes branchees au dock en USB filaire", "repo": "cathery/sys-con"},
        "pret_a_poser": {"missioncontrol": os.path.isfile(_src_maj("MissionControl-0.16.0-master-71bbe2d4.zip")),
                         "sys-con": os.path.isfile(_src_maj("sys-con-2.1.0.zip"))},
        "note": "Sur Switch, la compatibilite manette PS5 est un module homebrew (MissionControl) pose sur la carte, "
                "pas une app Mac : une fois pose et la console demarree en CFW, la DualSense s'appaire dans "
                "Reglages > Manettes > Changer la prise/l'ordre.",
    }


def _src_maj(nom: str) -> str:
    return os.path.join(RACINE, "data", "staging", "telechargements", nom)


# ─────────────────────────── le serveur HTTP ───────────────────────────

class _H(BaseHTTPRequestHandler):
    server_version = "SwitchSentinel"

    def log_message(self, *a):  # silence : le terminal reste lisible
        pass

    def _envoyer(self, code: int, corps: bytes, type_: str):
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corps)

    def _json(self, obj, code: int = 200):
        self._envoyer(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), TYPES[".json"])

    def _corps_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return {}

    # --- fichiers de l'interface (ui/) ---
    def _statique(self, chemin: str):
        rel = chemin.lstrip("/")
        if rel in ("", "index.html"):
            rel = "index.html"
        elif rel.startswith("ui/"):
            rel = rel[3:]
        plein = os.path.normpath(os.path.join(UI, rel))
        if not plein.startswith(UI) or not os.path.isfile(plein):   # pas de remontee hors de ui/
            self._envoyer(404, b"introuvable", TYPES[".txt"])
            return
        ext = os.path.splitext(plein)[1].lower()
        with open(plein, "rb") as f:
            self._envoyer(200, f.read(), TYPES.get(ext, "application/octet-stream"))

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        r = u.path
        try:
            if r == "/api/etat":
                self._json(etat())
            elif r == "/api/audit":
                cible = _sd_auto((q.get("sd") or [None])[0])
                if cible:
                    a = carte_sd.auditer(cible)
                    if a.get("ok"):
                        with open(AUDIT_CACHE, "w", encoding="utf-8") as f:
                            json.dump(a, f, ensure_ascii=False, indent=1)
                    self._json({"source": "carte montee", "audit": a})
                else:
                    self._json({"source": "dernier audit (aucune carte montee)", "audit": _audit_dernier()})
            elif r == "/api/payloads":
                self._json({"payloads": injecteur.payloads(), "pret": injecteur.pret()})
            elif r == "/api/manettes":
                self._json(manettes((q.get("sd") or [None])[0]))
            elif r == "/api/releases":
                self._json(depot.releases(forcer=(q.get("forcer") or ["0"])[0] == "1"))
            elif r == "/api/maj/plan":
                cible = _sd_auto((q.get("sd") or [None])[0])
                if cible:
                    from . import maj
                    self._json({"carte": cible, "plan": maj.plan(cible)})
                else:
                    self._json({"carte": None, "erreur": "aucune carte montee"})
            elif r == "/api/catalogue":
                self._json({"coeur": connus.COEUR, "catalogue": connus.CATALOGUE, "familles": connus.FAMILLES})
            elif r == "/api/wifi/scan":
                self._json({"switch": wifi.scanner()})
            elif r == "/api/wifi/test":
                self._json(wifi.tester((q.get("ip") or [""])[0]))
            else:
                self._statique(r)
        except Exception as e:  # noqa: BLE001 -- l'app ne doit jamais tomber ; elle dit l'erreur
            self._json({"erreur": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            corps = self._corps_json()
            if u.path == "/api/injecter":
                self._json(self._injecter(corps))
            elif u.path == "/api/maj/appliquer":
                self._json(self._appliquer(corps))
            elif u.path == "/api/wifi/pousser":
                if not corps.get("confirmer"):
                    self._json({"ok": False, "erreur": "geste non confirme (confirmer: true attendu)"})
                else:
                    self._json(wifi.pousser(corps.get("ip", ""), [tuple(x) for x in corps.get("fichiers", [])]))
            else:
                self._json({"erreur": "route inconnue"}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"erreur": f"{type(e).__name__}: {e}"}, 500)

    # --- les deux gestes gardes ---
    def _injecter(self, corps: dict) -> dict:
        if not corps.get("confirmer"):
            return {"ok": False, "sortie": "geste non confirme (confirmer: true attendu)"}
        mode = usb.etat()["mode"]
        if mode != "rcm":
            return {"ok": False, "sortie": f"la console n'est pas en RCM (mode lu : {mode}). "
                    "Mets-la en RCM (jig dans le rail droit, Volume + maintenu, puis Power) et reessaie."}
        pid = corps.get("payload_id")
        if not pid:
            pay = injecteur.payloads()
            if not pay:
                return {"ok": False, "sortie": "aucun payload dans vendor/payloads"}
            pid = pay[0]["id"]   # le plus recent Hekate par defaut
        return injecteur.injecter(pid)

    def _appliquer(self, corps: dict) -> dict:
        if not corps.get("confirmer"):
            return {"ok": False, "erreur": "geste non confirme (confirmer: true attendu)"}
        sd = corps.get("sd")
        cands = {c["chemin"] for c in carte_sd.candidats()}
        if not sd or sd not in cands:
            return {"ok": False, "erreur": "la carte visee n'est pas un volume monte reconnu",
                    "cartes_montees": sorted(cands)}
        from . import maj
        return maj.appliquer(sd)


def _port_libre(depart: int) -> int:
    import socket
    for p in range(depart, depart + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return depart


def demarrer(port: int = 8787, ouvrir: bool = True) -> None:
    port = _port_libre(port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), _H)
    url = f"http://127.0.0.1:{port}/"
    print(f"SwitchSentinel ecoute sur {url}  (Ctrl+C pour arreter)")
    if ouvrir:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\narret.")
    finally:
        srv.server_close()
