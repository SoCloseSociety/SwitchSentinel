# SwitchSentinel -- tous les écrans à habiller (charte SentinelHouse)

Inventaire complet des écrans de l'expérience brandée, en 3 niveaux, du démarrage aux pages tertiaires.
Palette : fond bleu-noir `#05070a`, accent menthe `#34e5a0` (le langage SentinelHouse). Source des images :
les 10 visuels kie.ai déjà générés dans `ui/visuels/brut/` (12/02 → 11/11/2026).

Deux mondes se partagent la même charte :
- **A. La console** (écrans natifs Switch, formats vérifiés ci-dessous) -- posés sur la carte SD.
- **B. L'app SwitchSentinel** (le tableau de bord Mac) -- déjà construite.

---

## A. La console -- chaîne de boot + HOME

### Niveau 0 -- DÉMARRAGE (avant Horizon)

| # | Écran | Format natif vérifié | Fichier sur la carte | Source kie.ai |
|---|-------|----------------------|----------------------|---------------|
| 0.1 | **Boot logo** (splash après RCM/payload) | BMP 32-bit, ≤ 720×1280, tourné 90° | `bootloader/bootlogo.bmp` + `logopath=` dans `hekate_ipl.ini` | `fond-rcm` |
| 0.2 | **Hekate / Nyx** (le menu du bootloader) | **BMP 32-bit, 1280×720** | `bootloader/res/background.bmp` | `fond-hekate` |
| 0.2.x | sous-pages Nyx *(tertiaire)* : Launch · More Configs · Tools (Backup/Restore eMMC, Partition SD, USB Tools, AutoRCM) · Console Info · Options | héritent du fond Nyx (0.2) | -- | `fond-hekate` |

### Niveau 1 -- CONSOLE HOME (thème NXTheme, via NXThemes Installer déjà présent)

| # | Écran | Format | Fichier (.szs → .nxtheme) | Source kie.ai |
|---|-------|--------|---------------------------|---------------|
| 1.1 | **Home menu** (l'accueil de la console) | fond 1280×720 | `ResidentMenu.szs` | `fond-atmosphere` |
| 1.2 | **Écran de verrouillage / veille** | fond 1280×720 | `Entrance.szs` | `fond-veille` |

### Niveau 2 -- APPLETS (pages secondaires, chacune son fond 1280×720)

| # | Écran | Fichier | Source kie.ai |
|---|-------|---------|---------------|
| 2.1 | **Réglages (Settings)** | `Set.szs` | `carte-atelier` |
| 2.2 | **Tous les logiciels (All apps)** | `Flaunch.szs` | `carte-maj` |
| 2.3 | **Sélection du joueur** | `Psl.szs` | `carte-reveil` |
| 2.4 | **Page profil (My Page)** | `MyPage.szs` | `carte-bouclier` |
| 2.5 | **Actus / Notifications (News)** | `Notification.szs` | `carte-sd` |

### Niveau 3 -- TERTIAIRE

Les sous-pages des Réglages (Internet, Manettes, Écran, Système…), l'album, le clavier logiciel :
en NXTheme **standard** elles **héritent du fond de leur applet** (pas de thème séparé). Idem les sous-pages Nyx
héritent du fond 0.2. Donc rien de plus à générer -- la cohérence vient des niveaux 0–2.

**Installation console** : dossier `themes/` à la racine de la carte (déjà présent chez toi) → NXThemes Installer
pose les `.nxtheme`. Le boot logo et le fond Nyx sont de simples BMP copiés aux chemins ci-dessus.

---

## B. L'app SwitchSentinel (Mac) -- déjà construite

| Niveau | Écran | Fond d'état |
|--------|-------|-------------|
| Primaire | **Accueil** (hero : état USB live + bouton ⚡ Réveiller en Hekate) | suit le mode USB |
| Primaire | **Carte SD** (audit), **Bouclier**, **Sauvegardes**, **Mise à jour**, **Manettes**, **Catalogue** | -- |
| Secondaire | modale *Confirmer l'injection*, modale *Confirmer la mise à jour* | -- |
| États (fond vivant) | veille → `fond-veille` · RCM → `fond-rcm` · Hekate → `fond-hekate` · Horizon → `fond-atmosphere` | ✓ en place |

---

## Ce qu'il reste à produire (par écran console)

1. **Boot logo** (0.1) -- 1 BMP 720×1280 tourné.
2. **Fond Nyx** (0.2) -- 1 BMP 1280×720 32-bit.
3. **7 fonds NXTheme** (1.1, 1.2, 2.1–2.5) -- 7 images 1280×720 → 7 `.nxtheme`.

Total : **9 écrans natifs** à habiller depuis les visuels kie.ai existants (aucune nouvelle génération payante
nécessaire : on recadre/convertit les 10 fonds déjà faits). Outil : `outils/switch_visuels.py` (Pillow), qui
produit les BMP/PNG aux bons formats dans `data/staging/switch-visuels/`, avant pose sur la carte avec l'accord de l'owner.
