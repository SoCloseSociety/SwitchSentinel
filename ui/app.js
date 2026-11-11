/* app.js -- SwitchSentinel, l'atelier dans le navigateur (11/11/2026).
 * Un seul fichier, aucune dependance. Il interroge le serveur local (meme dossier), peint l'etat vivant de la
 * console, et garde les deux gestes qui agissent (injecter, mettre a jour) derriere une confirmation. */
"use strict";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const octets = (n) => n == null ? "?" : n < 1024 ? n + " o" : n < 1048576 ? (n / 1024).toFixed(0) + " Ko"
  : n < 1073741824 ? (n / 1048576).toFixed(1) + " Mo" : (n / 1073741824).toFixed(1) + " Go";

async function jget(url) { const r = await fetch(url); return r.json(); }
async function jpost(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return r.json();
}

function toast(txt, type = "") {
  const el = document.createElement("div");
  el.className = "toast " + type; el.innerHTML = esc(txt);
  $("#toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .4s"; }, 5200);
  setTimeout(() => el.remove(), 5700);
}

function confirmer({ titre, corps, bouton, danger }) {
  return new Promise((res) => {
    $("#modale").innerHTML = `<h3>${esc(titre)}</h3>${corps}
      <div class="actions">
        <button class="btn fantome" id="m-non">Annuler</button>
        <button class="btn ${danger ? "danger" : "primaire"}" id="m-oui">${esc(bouton)}</button>
      </div>`;
    $("#voile").classList.add("on");
    const fin = (v) => { $("#voile").classList.remove("on"); res(v); };
    $("#m-non").onclick = () => fin(false);
    $("#m-oui").onclick = () => fin(true);
  });
}

/* ───────────────── l'etat vivant (poll) ───────────────── */
const CIELS = { rcm: "fond-rcm", hekate: "fond-hekate", hekate_ums: "fond-hekate", horizon: "fond-atmosphere", absente: "fond-veille" };
const MODES = {
  rcm: { pt: "bg-amber lueur-amber", gros: "En RCM, prête", c: "c-amber",
    dit: "La console attend un payload sur le câble. Un clic la réveille dans Hekate." },
  hekate_ums: { pt: "bg-cyan lueur-cyan", gros: "Hekate partage la carte", c: "c-cyan",
    dit: "Hekate expose la carte SD en USB : elle devrait apparaître dans le Finder." },
  hekate: { pt: "bg-cyan lueur-cyan", gros: "Hekate est lancé", c: "c-cyan",
    dit: "Le bootloader tourne sur la console." },
  horizon: { pt: "bg-mint lueur-mint", gros: "Console démarrée", c: "c-mint",
    dit: "Le système tourne (CFW ou d'origine). Pour injecter, repasse-la en RCM." },
  absente: { pt: "bg-t3", gros: "Console endormie", c: "c-t3",
    dit: "Rien sur le bus USB. Branche-la en USB-C et mets-la en RCM." },
};
let ETAT = null, EN_COURS = false;

async function pollEtat() {
  try {
    ETAT = await jget("/api/etat");
    peindreHero();
    const m = ETAT.usb.mode;
    $("#pt-usb").className = "pt " + (MODES[m]?.pt || "bg-t3");
    $("#ciel").style.backgroundImage = `url('/ui/visuels/brut/${CIELS[m] || "fond-veille"}.png')`;
  } catch (e) { /* le serveur redemarre : on reessaie au prochain tick */ }
}

function peindreHero() {
  if (!$("#accueil").classList.contains("cache") && !EN_COURS) rendreAccueil();
}

/* ───────────────── pages ───────────────── */
const PAGES = {
  accueil: rendreAccueil, carte: rendreCarte, bouclier: rendreBouclier,
  sauvegardes: rendreSauvegardes, maj: rendreMaj, manettes: rendreManettes,
  wifi: rendreWifi, catalogue: rendreCatalogue,
};

function aller(page) {
  $$(".onglet").forEach((o) => o.classList.toggle("actif", o.dataset.page === page));
  $$("#contenu > section").forEach((s) => s.classList.toggle("cache", s.id !== page));
  location.hash = page;
  (PAGES[page] || rendreAccueil)();
}

function voirPlus(sec, html, n) {
  return `<div id="${sec}-vu">${html.slice(0, n).join("")}</div>
    ${html.length > n ? `<div class="cache" id="${sec}-reste">${html.slice(n).join("")}</div>
    <button class="voirplus" onclick="document.getElementById('${sec}-reste').classList.toggle('cache');
      this.textContent = this.textContent.startsWith('Voir') ? 'Voir moins' : 'Voir plus (${html.length - n})'">Voir plus (${html.length - n})</button>` : ""}`;
}

/* --- Accueil : le hero + l'injecteur --- */
function rendreAccueil() {
  const u = ETAT?.usb?.mode || "absente", m = MODES[u], inj = ETAT?.injecteur;
  const peut = inj?.peut_injecter;
  const pay = inj?.payloads?.[0];
  const rcmAide = `<div class="carte pleine" style="margin-top:4px">
      <div class="titre-sec"><h2>Mettre la console en RCM</h2><span class="sous">3 gestes</span></div>
      <div class="rangee"><span class="cle">1</span><span class="val g">Éteindre la console (maintenir Power ~12 s, Éteindre).</span></div>
      <div class="rangee"><span class="cle">2</span><span class="val g">Glisser le jig RCM dans le rail droit (là où clipse le Joy-Con).</span></div>
      <div class="rangee"><span class="cle">3</span><span class="val g">Maintenir <b>Volume +</b>, puis appuyer sur <b>Power</b>. L'écran reste noir : c'est normal, c'est RCM.</span></div>
      <p class="sous" style="margin-top:10px">La console branchée en USB-C au Mac apparaîtra ici en « RCM, prête ».</p>
    </div>`;
  const manque = inj && !inj.pret.pret ? `<div class="pill"><span class="pt bg-red"></span>il manque : <b>${esc(inj.pret.manque.join(", "))}</b></div>` : "";

  $("#accueil").innerHTML = `
    <div class="hero">
      <div class="mode"><span class="gros-point ${m.pt}"></span><span class="gros ${m.c}">${m.gros}</span></div>
      <p class="dit">${m.dit}</p>
      <div class="actions">
        <button class="btn primaire" id="btn-inj" ${peut ? "" : "disabled"}>⚡ Réveiller en Hekate${pay ? " " + esc(pay.hekate || "") : ""}</button>
        <button class="btn fantome" onclick="aller('maj')">Mettre à jour la carte</button>
      </div>
      ${manque}
    </div>
    <div class="grille">
      ${tuileEtat("Bus USB", m.gros, m.c, ETAT?.usb?.switch?.[0]?.libelle || `${ETAT?.usb?.nb_appareils ?? 0} appareils vus`)}
      ${tuileEtat("Carte SD", ETAT?.carte_montee ? "Montée" : "Non montée", ETAT?.carte_montee ? "c-mint" : "c-t3", ETAT?.carte_montee?.nom || "branche-la pour l'auditer")}
      ${tuileEtat("Injecteur", inj?.pret?.pret ? "Prêt" : "Incomplet", inj?.pret?.pret ? "c-mint" : "c-amber", pay ? "Hekate " + esc(pay.hekate) : "aucun payload")}
    </div>
    ${u !== "rcm" && u !== "hekate" && u !== "hekate_ums" ? rcmAide : ""}`;

  const b = $("#btn-inj");
  if (b) b.onclick = injecter;
}

function tuileEtat(titre, val, c, sous) {
  return `<div class="carte"><p class="sous c-t3" style="font-size:12px;text-transform:uppercase;letter-spacing:.08em">${esc(titre)}</p>
    <p class="${c}" style="font-size:22px;font-weight:700;margin:6px 0 2px">${esc(val)}</p>
    <p class="sous">${esc(sous)}</p></div>`;
}

async function injecter() {
  const pay = ETAT?.injecteur?.payloads?.[0];
  const ok = await confirmer({
    titre: "Réveiller la console en Hekate",
    corps: `<p>La console va quitter le mode RCM et démarrer dans <b>Hekate ${esc(pay?.hekate || "")}</b>.</p>
      <p>Rien n'est écrit sur la carte : c'est un simple redémarrage. L'écran du Mac ne bougera pas, la console oui.</p>`,
    bouton: "Injecter maintenant", danger: false,
  });
  if (!ok) return;
  EN_COURS = true;
  const b = $("#btn-inj"); if (b) { b.disabled = true; b.innerHTML = `<span class="spin"></span> Injection...`; }
  const r = await jpost("/api/injecter", { confirmer: true, payload_id: pay?.id });
  EN_COURS = false;
  if (r.ok) toast("Hekate lancé sur la console ✓ — regarde son écran.", "ok");
  else toast("Échec : " + (r.sortie || r.erreur || "inconnu"), "mal");
  pollEtat();
}

/* --- Carte SD : l'audit --- */
let AUDIT = null;
async function rendreCarte() {
  const el = $("#carte");
  el.innerHTML = `<div class="titre-sec"><h2>Carte SD</h2><span class="sous"><span class="spin"></span> lecture...</span></div>`;
  const r = await jget("/api/audit");
  AUDIT = r.audit;
  if (!AUDIT) { el.innerHTML = vide("Aucune carte montée, et aucun audit en mémoire. Branche la carte SD."); return; }
  const a = AUDIT, v = a.volume || {};
  const constats = (a.constats || []).map((c) => `<div class="constat ${c.niveau}">
    <span class="marqueur ${c.niveau === "alerte" ? "bg-red" : c.niveau === "att" ? "bg-amber" : "bg-mint"}"></span>
    <div class="corps"><div class="t">${esc(c.titre)}</div><div class="d">${esc(c.detail)}</div></div></div>`);
  const hb = (a.homebrew || []).map((h) => `<div class="rangee"><span class="cle">${esc(h.nom)}</span>
    <span class="val">${esc(h.version || "—")} · ${octets(h.taille)}</span></div>`);
  const ovl = (a.overlays || []).map((o) => `<div class="rangee"><span class="cle">${esc(o.nom)}</span>
    <span class="val">${esc(o.version || "—")}</span></div>`);
  const sys = (a.sysmodules || []).map((s) => `<div class="rangee"><span class="cle">${esc(s.nom || s.tid)}</span>
    <span class="val">${s.demarre_seul ? "démarre seul" : "manuel"}</span></div>`);

  el.innerHTML = `
    <div class="titre-sec"><h2>Carte SD</h2><span class="sous">${esc(r.source)}${v.nom_media ? " · " + esc(v.nom_media) : ""}</span></div>
    <div class="grille">
      <div class="carte">
        <div class="titre-sec"><h2 style="font-size:17px">Le cœur</h2></div>
        <div class="rangee"><span class="cle">Atmosphère</span><span class="val ${a.atmosphere?.version ? "c-mint" : "c-red"}">${esc(a.atmosphere?.version || "absent")}</span></div>
        <div class="rangee"><span class="cle">Firmware max</span><span class="val">${esc(a.atmosphere?.firmware_max || "?")}</span></div>
        <div class="rangee"><span class="cle">Hekate</span><span class="val ${a.hekate?.version ? "c-mint" : "c-red"}">${esc(a.hekate?.version || "absent")}</span></div>
        <div class="rangee"><span class="cle">Nyx</span><span class="val">${esc(a.hekate?.nyx || "?")}</span></div>
        <div class="rangee"><span class="cle">emuMMC</span><span class="val ${a.emummc?.active ? "c-mint" : "c-amber"}">${a.emummc?.active ? "active" : "inactive"} · ${esc(a.emummc?.type || "—")}</span></div>
        <div class="rangee"><span class="cle">Redémarre sur</span><span class="val">${esc(a.atmosphere?.reboot_payload || "?")}</span></div>
      </div>
      <div class="carte">
        <div class="titre-sec"><h2 style="font-size:17px">Le volume</h2></div>
        <div class="rangee"><span class="cle">Format</span><span class="val ${/exfat/i.test(v.systeme||"") ? "c-amber" : ""}">${esc(v.systeme || "?")}</span></div>
        <div class="rangee"><span class="cle">Taille</span><span class="val">${octets(v.taille)}</span></div>
        <div class="rangee"><span class="cle">Libre</span><span class="val">${octets(v.libre)}</span></div>
        <div class="rangee"><span class="cle">Traces macOS</span><span class="val ${a.traces_mac?.total ? "c-amber" : "c-mint"}">${a.traces_mac?.total || 0}</span></div>
        <div class="rangee"><span class="cle">Homebrew (.nro)</span><span class="val">${(a.homebrew||[]).length}</span></div>
        <div class="rangee"><span class="cle">Overlays</span><span class="val">${(a.overlays||[]).length}</span></div>
      </div>
    </div>
    <div class="carte pleine" style="margin-top:16px">
      <div class="titre-sec"><h2 style="font-size:17px">Ce qui mérite un regard</h2><span class="sous">${constats.length} point(s)</span></div>
      ${constats.join("") || vide("Rien à signaler.")}
    </div>
    <div class="grille" style="margin-top:16px">
      <div class="carte"><div class="titre-sec"><h2 style="font-size:16px">Homebrew</h2></div>${hb.length ? voirPlus("hb", hb, 6) : vide("aucun")}</div>
      <div class="carte"><div class="titre-sec"><h2 style="font-size:16px">Overlays</h2></div>${ovl.length ? voirPlus("ovl", ovl, 6) : vide("aucun")}</div>
      <div class="carte"><div class="titre-sec"><h2 style="font-size:16px">Modules système</h2></div>${sys.length ? voirPlus("sys", sys, 6) : vide("aucun")}</div>
    </div>`;
}

/* --- Bouclier --- */
async function rendreBouclier() {
  const el = $("#bouclier");
  el.innerHTML = `<div class="titre-sec"><h2>Bouclier</h2><span class="sous"><span class="spin"></span></span></div>`;
  const r = await jget("/api/audit"); const a = r.audit;
  if (!a?.bouclier) { el.innerHTML = vide("Aucun audit disponible. Branche la carte."); return; }
  const b = a.bouclier;
  const plots = Array.from({ length: b.sur }, (_, i) => `<div class="plot ${i < b.score ? "on" : ""}"></div>`).join("");
  const pts = b.points.map((p) => `<div class="constat">
    <span class="marqueur ${p.ok ? "bg-mint" : "bg-amber"}"></span>
    <div class="corps"><div class="t">${p.ok ? "✓ " : "○ "}${esc(p.titre)}</div><div class="d">${esc(p.pourquoi)}</div></div></div>`);
  const inc = (b.inconnus || []).map((i) => `<div class="rangee"><span class="val g c-t3">• ${esc(i)}</span></div>`);
  el.innerHTML = `
    <div class="titre-sec"><h2>Bouclier anti-ban</h2><span class="sous">${r.source}</span></div>
    <div class="carte pleine">
      <p style="font-size:30px;font-weight:700" class="${b.score === b.sur ? "c-mint" : b.score >= 3 ? "c-amber" : "c-red"}">${b.score} / ${b.sur}</p>
      <div class="jauge">${plots}</div>
      <p class="sous" style="margin:6px 0 14px">Cinq points vérifiables sur la carte. L'emuMMC isole ta mémoire interne ; les DNS bloquent Nintendo ; la sauvegarde NAND est l'assurance.</p>
      ${pts.join("")}
    </div>
    <div class="carte pleine" style="margin-top:16px">
      <div class="titre-sec"><h2 style="font-size:16px">Ce qui ne se voit pas d'ici</h2></div>
      ${inc.join("")}
    </div>`;
}

/* --- Sauvegardes --- */
async function rendreSauvegardes() {
  const el = $("#sauvegardes");
  el.innerHTML = `<div class="titre-sec"><h2>Sauvegardes</h2><span class="sous"><span class="spin"></span></span></div>`;
  const r = await jget("/api/audit"); const a = r.audit; const s = a?.sauvegardes || { nand: [], cles: [] };
  const complete = (s.nand || []).some((n) => n.boot0 && n.boot1 && n.rawnand);
  const nand = (s.nand || []).map((n) => `<div class="rangee"><span class="cle">${esc(n.id)}</span>
    <span class="val">${n.boot0 ? "BOOT0 " : ""}${n.boot1 ? "BOOT1 " : ""}${n.rawnand ? "rawnand " : ""}· ${octets(n.taille)}</span></div>`);
  el.innerHTML = `
    <div class="titre-sec"><h2>Sauvegardes NAND</h2><span class="sous">${r.source}</span></div>
    <div class="carte pleine" style="${complete ? "" : "border-color:rgba(255,94,94,.4)"}">
      ${complete
        ? `<p class="c-mint" style="font-size:18px;font-weight:650">✓ Une sauvegarde NAND complète existe sur la carte.</p>`
        : `<p class="c-red" style="font-size:18px;font-weight:650">Aucune sauvegarde NAND complète.</p>
           <p class="sous" style="margin-top:8px">BOOT0 + BOOT1 + rawnand.bin, c'est la seule assurance contre une brique. Hekate la fait en 20 à 40 min :
           <b>Hekate → Tools → Backup eMMC → eMMC BOOT0 & BOOT1</b> puis <b>eMMC RAW GPP</b>. Le résultat va dans <span class="mono">backup/</span> sur la carte.</p>`}
      ${nand.length ? `<div style="margin-top:12px">${nand.join("")}</div>` : ""}
    </div>
    <div class="carte pleine" style="margin-top:16px">
      <div class="titre-sec"><h2 style="font-size:16px">Clés & saves</h2></div>
      <div class="rangee"><span class="cle">Clés (prod.keys)</span><span class="val">${s.cles?.length ? esc(s.cles.join(", ")) : "aucune sur la carte"}</span></div>
      <div class="rangee"><span class="cle">PRODINFO auto (Atmosphère)</span><span class="val">${(a?.atmosphere?.prodinfo_auto||[]).length} copie(s)</span></div>
      <div class="rangee"><span class="cle">JKSV (saves de jeux)</span><span class="val">${s.jksv ? s.jksv.jeux + " jeu(x)" : "—"}</span></div>
    </div>`;
}

/* --- Mise à jour --- */
async function rendreMaj() {
  const el = $("#maj");
  el.innerHTML = `<div class="titre-sec"><h2>Mise à jour</h2><span class="sous"><span class="spin"></span> plan...</span></div>`;
  const r = await jget("/api/maj/plan");
  if (!r.carte) {
    el.innerHTML = `<div class="titre-sec"><h2>Mise à jour</h2></div>
      ${vide("Aucune carte montée. Branche la carte SD (ou démarre Hekate → Tools → USB Tools → SD Card) puis reviens ici.")}`;
    return;
  }
  const p = r.plan, ops = p.operations.map((o) => {
    const n = p.lignes.filter((l) => l.op === o.id && l.action !== "garder").length;
    return `<div class="rangee"><span class="cle">${esc(o.nom)}</span>
      <span class="val">${esc(o.apres)} · <b class="${n ? "c-mint" : "c-t3"}">${n} fichier(s)</b></span></div>`;
  });
  const total = p.resume;
  el.innerHTML = `
    <div class="titre-sec"><h2>Mise à jour de la carte</h2><span class="sous">${esc(r.carte)}</span></div>
    <div class="carte pleine">
      <p class="sous">Chaque fichier remplacé est d'abord copié dans <span class="mono">sauvegardes/</span> sur le Mac, avec un manifeste. Tes réglages (.ini, hosts, config) ne sont jamais écrasés.</p>
      <div style="margin-top:12px">${ops.join("")}</div>
      <div class="rangee"><span class="cle"><b>Total</b></span><span class="val"><b class="c-mint">${total.creer} à créer</b>, ${total.remplacer} à remplacer</span></div>
      ${p.manquants?.length ? `<div class="pill" style="margin-top:10px"><span class="pt bg-red"></span>téléchargements manquants : <b>${p.manquants.length}</b></div>` : ""}
      <div class="actions" style="display:flex;gap:10px;margin-top:18px;flex-wrap:wrap">
        <button class="btn primaire" id="btn-maj" ${p.manquants?.length ? "disabled" : ""}>Sauvegarder puis appliquer</button>
      </div>
    </div>`;
  const b = $("#btn-maj"); if (b) b.onclick = () => appliquerMaj(r.carte, total);
}

async function appliquerMaj(sd, total) {
  const ok = await confirmer({
    titre: "Appliquer la mise à jour",
    corps: `<p>SwitchSentinel va <b>${total.creer} créer</b> et <b>${total.remplacer} remplacer</b> sur <span class="mono">${esc(sd)}</span>.</p>
      <p>Avant d'écrire, chaque fichier remplacé et tous tes réglages sont copiés dans <span class="mono">sauvegardes/</span> sur le Mac. Tes .ini ne sont pas touchés.</p>`,
    bouton: "Sauvegarder puis écrire", danger: true,
  });
  if (!ok) return;
  const b = $("#btn-maj"); if (b) { b.disabled = true; b.innerHTML = `<span class="spin"></span> écriture...`; }
  const r = await jpost("/api/maj/appliquer", { confirmer: true, sd });
  if (r.ok) toast(`Mise à jour écrite ✓ — ${r.ecrits} fichier(s), sauvegarde : ${r.sauvegarde?.split("/").pop()}`, "ok");
  else toast("Échec : " + (r.erreur || JSON.stringify(r.erreurs || "")).slice(0, 160), "mal");
  rendreMaj();
}

/* --- Manettes (PS5 / PS4 / Xbox) --- */
async function rendreManettes() {
  const el = $("#manettes");
  el.innerHTML = `<div class="titre-sec"><h2>Manettes</h2><span class="sous"><span class="spin"></span></span></div>`;
  const m = await jget("/api/manettes");
  const bloc = (d, sous, pret) => `<div class="carte">
    <div class="titre-sec"><h2 style="font-size:17px">${esc(d.module)}</h2>
      <span class="pill"><span class="pt ${d.installe ? "bg-mint" : "bg-amber"}"></span>${d.installe ? "installé" : "à poser"}</span></div>
    <p class="sous" style="margin-bottom:10px">${esc(sous)}</p>
    <div class="rangee"><span class="cle">Manettes</span><span class="val g" style="text-align:left">${esc(d.manettes)}</span></div>
    <div class="rangee"><span class="cle">Démarre seul</span><span class="val">${d.installe ? (d.demarre_seul ? "oui" : "non") : "—"}</span></div>
    <div class="rangee"><span class="cle">Source</span><span class="val"><a href="https://github.com/${esc(d.repo)}" target="_blank">${esc(d.repo)}</a></span></div>
    <div class="rangee"><span class="cle">Prêt à poser</span><span class="val ${pret ? "c-mint" : "c-amber"}">${pret ? "oui (téléchargé)" : "non"}</span></div>
  </div>`;
  el.innerHTML = `
    <div class="titre-sec"><h2>Manettes PS5 · PS4 · Xbox</h2><span class="sous">${esc(m.source)}</span></div>
    <div class="carte pleine" style="margin-bottom:16px">
      <p>${esc(m.note)}</p>
    </div>
    <div class="grille">
      ${bloc(m.bluetooth, "Bluetooth, sans dongle. C'est LUI qui rend la DualSense PS5 compatible.", m.pret_a_poser.missioncontrol)}
      ${bloc(m.usb, "Filaire, au dock, en USB.", m.pret_a_poser["sys-con"])}
    </div>
    <div class="carte pleine" style="margin-top:16px">
      <div class="titre-sec"><h2 style="font-size:16px">Poser / mettre à jour</h2></div>
      <p class="sous">MissionControl et sys-con font partie du plan de mise à jour : ils seront écrits sur la carte au prochain « Appliquer ».</p>
      <div class="actions" style="display:flex;margin-top:14px"><button class="btn primaire" onclick="aller('maj')">Aller à la mise à jour</button></div>
      <p class="sous" style="margin-top:12px">Après l'écriture et un démarrage en CFW : <b>Réglages → Manettes → Changer la prise/l'ordre</b>, mets la DualSense en appairage (maintenir PS + Create jusqu'à ce qu'elle clignote).</p>
    </div>`;
}

/* --- WiFi : installer sans câble (ftpd) --- */
async function rendreWifi() {
  const el = $("#wifi");
  el.innerHTML = `
    <div class="titre-sec"><h2>Installer par WiFi</h2><span class="sous">sans câble, via ftpd</span></div>
    <div class="carte pleine">
      <p class="sous">La Switch en CFW avec <b>ftpd</b> ouvert (switch/ftpd.nro) partage sa carte SD sur le réseau. Le Mac pousse alors homebrew, overlays et thèmes directement dessus, à distance.</p>
      <div class="actions" style="display:flex;gap:10px;flex-wrap:wrap;margin-top:14px">
        <button class="btn primaire" id="wifi-scan">⇄ Scanner le réseau</button>
        <input id="wifi-ip" placeholder="ou IP (ex: 192.168.1.42)" style="flex:1 1 180px;min-width:0;padding:11px 14px;border-radius:12px;border:1px solid var(--line-strong);background:var(--surface-mini);color:var(--t1);font-size:14px">
        <button class="btn" id="wifi-test">Tester</button>
      </div>
      <div id="wifi-res" style="margin-top:14px"></div>
    </div>
    <div class="carte pleine" style="margin-top:16px">
      <div class="titre-sec"><h2 style="font-size:16px">Comment faire côté console</h2></div>
      <div class="rangee"><span class="cle">1</span><span class="val g">Démarre en CFW, ouvre <b>ftpd</b> (switch/ftpd.nro).</span></div>
      <div class="rangee"><span class="cle">2</span><span class="val g">Note l'IP et le port (5000) affichés par ftpd.</span></div>
      <div class="rangee"><span class="cle">3</span><span class="val g">Ici : Scanner (ou saisis l'IP) → Tester → l'app peut pousser sur la carte en WiFi.</span></div>
    </div>`;
  $("#wifi-scan").onclick = async () => {
    $("#wifi-res").innerHTML = `<span class="spin"></span> scan du réseau local...`;
    const r = await jget("/api/wifi/scan");
    if (!r.switch?.length) { $("#wifi-res").innerHTML = vide("Aucune Switch trouvée (ftpd ouvert ? même WiFi ?)"); return; }
    $("#wifi-res").innerHTML = r.switch.map((s) => wifiCarte(s)).join("");
    cablerWifi();
  };
  $("#wifi-test").onclick = async () => {
    const ip = $("#wifi-ip").value.trim();
    if (!ip) return;
    $("#wifi-res").innerHTML = `<span class="spin"></span> test de ${esc(ip)}...`;
    const r = await jget("/api/wifi/test?ip=" + encodeURIComponent(ip));
    $("#wifi-res").innerHTML = r.ok ? wifiCarte(r) : vide("Pas de réponse : " + (r.erreur || ""));
  };
}
function wifiCarte(s) {
  return `<div class="carte" style="margin-bottom:10px">
    <div class="titre-sec"><h2 style="font-size:16px">🎮 ${esc(s.ip)}:${s.port}</h2>
      <span class="pill"><span class="pt ${s.ressemble_switch ? "bg-mint" : "bg-amber"}"></span>${s.ressemble_switch ? "Switch détectée" : "FTP (à confirmer)"}</span></div>
    <p class="sous" style="overflow-wrap:anywhere">${esc(s.banniere || "")}</p>
    <p class="mono" style="margin-top:6px">racine : ${esc((s.racine || []).join("  ·  "))}</p>
  </div>`;
}
function cablerWifi() {}

/* --- Catalogue --- */
async function rendreCatalogue() {
  const el = $("#catalogue");
  el.innerHTML = `<div class="titre-sec"><h2>Catalogue</h2><span class="sous"><span class="spin"></span></span></div>`;
  const [cat, rel] = await Promise.all([jget("/api/catalogue"), jget("/api/releases").catch(() => ({ releases: {} }))]);
  const R = rel.releases || {};
  const tout = [...cat.coeur, ...cat.catalogue];
  const parFam = {};
  tout.forEach((e) => { (parFam[e.famille] ||= []).push(e); });
  const cartes = Object.entries(parFam).map(([fam, items]) => {
    const rows = items.map((e) => {
      const d = R[e.id];
      return `<div class="rangee"><span class="cle">${esc(e.nom)}${e.essentiel ? ' <span class="c-mint">·</span>' : ""}</span>
        <span class="val">${d?.tag ? esc(d.tag) : "—"}</span></div>
        <div class="rangee" style="border:0;padding-top:0"><span class="val g c-t3" style="font-size:12.5px">${esc(e.role)}</span></div>`;
    });
    return `<div class="carte"><div class="titre-sec"><h2 style="font-size:16px">${esc(cat.familles[fam] || fam)}</h2>
      <span class="sous">${items.length}</span></div>${rows.join("")}</div>`;
  });
  el.innerHTML = `
    <div class="titre-sec"><h2>Catalogue des essentiels</h2><span class="sous">homebrew, sauvegarde, confort · dernières versions GitHub</span></div>
    <div class="grille">${cartes.join("")}</div>`;
}

function vide(txt) { return `<div class="vide">${esc(txt)}</div>`; }

/* ───────────────── départ ───────────────── */
$$(".onglet").forEach((o) => o.addEventListener("click", () => aller(o.dataset.page)));
window.addEventListener("hashchange", () => { const p = location.hash.slice(1); if (PAGES[p]) aller(p); });
pollEtat().then(() => aller(location.hash.slice(1) in PAGES ? location.hash.slice(1) : "accueil"));
setInterval(pollEtat, 2500);
