"""SwitchSentinel test suite -- standard library only, no external assets (self-contained).

    python3 -m unittest discover -s tests -v

Everything runs against the reference card `tests/fixtures/sd-officielle` (Atmosphere 1.12.1, Hekate 6.5.4,
Nyx 1.9.4) and the bundled UI visuals. No real hardware, no SD card, no network.
"""
from __future__ import annotations

import os
import struct
import unittest

from switchsentinel import carte_sd, connus, maj, nxtheme, serveur, versions, wifi

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(RACINE, "tests", "fixtures", "sd-officielle")
VISUELS = os.path.join(RACINE, "ui", "visuels", "brut")


class Versions(unittest.TestCase):
    def test_hekate(self):
        self.assertEqual(versions.version_hekate(os.path.join(FIXTURE, "bootloader", "update.bin")), "6.5.4")

    def test_nyx(self):
        self.assertEqual(versions.version_nyx(os.path.join(FIXTURE, "bootloader", "sys", "nyx.bin")), "1.9.4")

    def test_package3(self):
        p = versions.package3(os.path.join(FIXTURE, "atmosphere", "package3"))
        self.assertEqual(p["version"], "1.12.1")

    def test_nacp(self):
        self.assertTrue((versions.nacp(os.path.join(FIXTURE, "hbmenu.nro")) or {}).get("nom"))

    def test_absent_rend_none(self):
        self.assertIsNone(versions.version_hekate(os.path.join(FIXTURE, "nope.bin")))

    def test_comparer(self):
        self.assertEqual(versions.comparer("6.5.3", "6.5.4"), "en_retard")
        self.assertEqual(versions.comparer("6.5.4", "6.5.4"), "a_jour")
        self.assertEqual(versions.comparer(None, "6.5.4"), "inconnu")


class Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = carte_sd.auditer(FIXTURE)

    def test_ok_et_versions(self):
        self.assertTrue(self.a["ok"])
        self.assertEqual(self.a["atmosphere"]["version"], "1.12.1")
        self.assertEqual(self.a["hekate"]["version"], "6.5.4")

    def test_constats_tries(self):
        ordre = {"alerte": 0, "att": 1, "ok": 2}
        niveaux = [ordre[c["niveau"]] for c in self.a["constats"]]
        self.assertEqual(niveaux, sorted(niveaux))

    def test_bouclier(self):
        b = self.a["bouclier"]
        self.assertEqual(b["sur"], len(b["points"]))
        self.assertTrue(0 <= b["score"] <= b["sur"])

    def test_dossier_introuvable(self):
        self.assertFalse(carte_sd.auditer(os.path.join(FIXTURE, "nope"))["ok"])


class MiseAJour(unittest.TestCase):
    def test_chemins_sur(self):
        self.assertIsNone(maj._sur("/etc/passwd"))
        self.assertIsNone(maj._sur("../evasion"))
        self.assertIsNone(maj._sur("__MACOSX/x"))
        self.assertEqual(maj._sur("switch\\JKSV.nro"), "switch/JKSV.nro")

    def test_reglages_ini_jamais_ecrases(self):
        l = maj._poser(FIXTURE, "config/sys-clk/config.ini", "x", ("fichier", "/dev/null"))
        self.assertIn(l["action"], ("garder", "creer"))


class Serveur(unittest.TestCase):
    def test_etat_forme(self):
        e = serveur.etat()
        self.assertIn("usb", e)
        self.assertIn("peut_injecter", e["injecteur"])

    def test_manettes(self):
        m = serveur.manettes(FIXTURE)
        self.assertEqual(m["bluetooth"]["module"], "MissionControl")
        self.assertEqual(m["usb"]["module"], "sys-con")

    def test_catalogue_coherent(self):
        ids = [e["id"] for e in connus.COEUR + connus.CATALOGUE]
        self.assertEqual(len(ids), len(set(ids)))
        for e in connus.COEUR + connus.CATALOGUE:
            self.assertIn(e["famille"], connus.FAMILLES)


class WiFi(unittest.TestCase):
    def test_constantes(self):
        self.assertEqual(wifi.PORT_DEFAUT, 5000)
        self.assertIn("atmosphere", wifi.MARQUEURS_SD)

    def test_hote_injoignable(self):
        self.assertFalse(wifi.tester("127.0.0.1", port=1, timeout=2)["ok"])


class NxTheme(unittest.TestCase):
    def test_yaz0_passthrough(self):
        self.assertEqual(nxtheme.yaz0_decompresser(b"plain"), b"plain")

    def test_zip_roundtrip(self):
        import json
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "t.nxtheme")
        nxtheme.ecrire_zip(p, {"info.json": json.dumps({"Version": 17, "Target": "home"}).encode(),
                               "image.jpg": b"\xff\xd8\xff"})
        r = nxtheme.lire(p)
        self.assertEqual(r["info"]["Target"], "home")
        self.assertIn("image.jpg", r["fichiers"])


class Visuels(unittest.TestCase):
    def test_fonds_presents_et_valides(self):
        for nom in ("fond-veille", "fond-rcm", "fond-hekate", "fond-atmosphere"):
            p = os.path.join(VISUELS, nom + ".png")
            self.assertTrue(os.path.isfile(p), f"manquant : {nom}")
            with open(p, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
