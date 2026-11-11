#!/bin/bash
# SwitchSentinel -- double-clique ce fichier dans le Finder pour ouvrir l'app.
# Il demarre le serveur local (127.0.0.1) et ouvre le navigateur. Ferme la fenetre du Terminal pour l'arreter.
cd "$(dirname "$0")" || exit 1

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "L'environnement .venv manque. Je le prepare..."
  python3.13 -m venv .venv 2>/dev/null || python3 -m venv .venv || { echo "python3 introuvable"; exit 1; }
  "$PY" -m pip install --quiet --upgrade pip pyusb || true
fi

# libusb (pour l'injection RCM) : un rappel, pas un blocage.
if [ ! -f "/opt/homebrew/lib/libusb-1.0.dylib" ] && [ ! -f "/usr/local/lib/libusb-1.0.dylib" ]; then
  echo "Note : libusb n'est pas installe (brew install libusb). L'audit et la mise a jour marchent ; l'injection RCM non."
fi

echo "Ouverture de SwitchSentinel..."
exec "$PY" -m switchsentinel app
