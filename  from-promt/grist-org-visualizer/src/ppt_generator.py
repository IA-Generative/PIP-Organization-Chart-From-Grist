"""
ppt_generator.py
----------------
Génère le PowerPoint de synthèse PI Planning SDID.
Utilise PptxGenJS via Node.js.

Slides :
  1. Synthèse globale (KPIs)
  2. Vue organisationnelle (équipes + epics séparées)
  3. Slide par équipe
  4. Slide par epic (avec ambition PI)
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


PPTXGEN_SCRIPT = """
const pptxgen = require("pptxgenjs");

const data = JSON.parse(process.argv[2]);
const outputPath = process.argv[3];

// ── Palette de couleurs
const C = {
  dark:    "1E2761",
  blue:    "4472C4",
  green:   "2D7A4F",
  orange:  "B85000",
  light:   "F5F7FA",
  white:   "FFFFFF",
  gray:    "64748B",
  accent:  "00A896",
  red:     "C0392B",
  yellow:  "F39C12",
};

let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.title = `PI Planning SDID – ${data.pi_num}`;

// ─────────────────────────────────────────────────────────
// SLIDE 1 – SYNTHÈSE GLOBALE
// ─────────────────────────────────────────────────────────
{
  let slide = pres.addSlide();
  slide.background = { color: C.dark };

  // Titre
  slide.addText(`PI Planning SDID – ${data.pi_num}`, {
    x: 0.5, y: 0.3, w: 9, h: 0.8,
    fontSize: 32, bold: true, color: C.white,
    align: "center",
  });
  slide.addText("Synthèse Globale", {
    x: 0.5, y: 1.0, w: 9, h: 0.4,
    fontSize: 16, color: C.accent, align: "center",
  });

  // KPI Cards (2 lignes x 3)
  const kpis = [
    { label: "Équipes",          value: data.stats.nb_equipes,            color: C.blue },
    { label: "Epics",            value: data.stats.nb_epics,              color: C.green },
    { label: "Epics Séparées",   value: data.stats.nb_epics_separees,     color: C.orange },
    { label: "Features PI",      value: data.stats.nb_features_pi,        color: C.accent },
    { label: "Agents >100%",     value: data.stats.nb_agents_surcharges,  color: C.red },
    { label: "Multi-Équipes",    value: data.stats.nb_agents_multi_equipes, color: C.yellow },
  ];

  const cols = 3, cardW = 2.8, cardH = 1.2, gapX = 0.3, gapY = 0.3;
  const startX = 0.6, startY = 1.7;

  kpis.forEach((kpi, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = startX + col * (cardW + gapX);
    const y = startY + row * (cardH + gapY);

    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w: cardW, h: cardH,
      fill: { color: "FFFFFF", transparency: 15 },
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.08, h: cardH,
      fill: { color: kpi.color },
    });
    slide.addText(String(kpi.value), {
      x: x + 0.2, y: y + 0.1, w: cardW - 0.3, h: 0.7,
      fontSize: 36, bold: true, color: kpi.color,
    });
    slide.addText(kpi.label, {
      x: x + 0.2, y: y + 0.75, w: cardW - 0.3, h: 0.35,
      fontSize: 11, color: C.gray,
    });
  });

  // Footer
  slide.addText("Généré automatiquement par grist-org-visualizer", {
    x: 0.5, y: 5.2, w: 9, h: 0.3,
    fontSize: 9, color: C.gray, align: "center", italic: true,
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 2 – VUE ORGANISATIONNELLE
// ─────────────────────────────────────────────────────────
{
  let slide = pres.addSlide();
  slide.background = { color: C.light };

  slide.addText(`Vue Organisationnelle – ${data.pi_num}`, {
    x: 0.5, y: 0.2, w: 9, h: 0.6,
    fontSize: 24, bold: true, color: C.dark,
  });

  // Table des équipes
  const headers = ["Équipe", "Epics", "Features", "Agents", "Surcharge"];
  const rows = [
    headers.map(h => ({ text: h, options: { bold: true, fill: { color: C.blue }, color: C.white } })),
    ...(data.equipes || []).map(eq => [
      eq.nom,
      String(eq.nb_epics || 0),
      String(eq.nb_features || 0),
      String(eq.nb_agents || 0),
      eq.has_surcharge ? "⚠️" : "✅",
    ]),
  ];

  if (rows.length > 1) {
    slide.addTable(rows, {
      x: 0.5, y: 1.0, w: 9, h: Math.min(3.5, 0.5 * rows.length),
      fontSize: 11,
      border: { pt: 1, color: "CCCCCC" },
      colW: [3, 1.5, 1.5, 1.5, 1.5],
    });
  }

  // Epics séparées
  if (data.stats.nb_epics_separees > 0) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 4.5, w: 9, h: 0.8,
      fill: { color: "FFE6CC" },
    });
    slide.addText(`⚠️  ${data.stats.nb_epics_separees} Epic(s) séparée(s) détectée(s) – membres hors équipe principale`, {
      x: 0.7, y: 4.55, w: 8.6, h: 0.7,
      fontSize: 12, color: C.orange, bold: true,
    });
  }
}

// ─────────────────────────────────────────────────────────
// SLIDES PAR ÉQUIPE
// ─────────────────────────────────────────────────────────
(data.equipes || []).forEach(equipe => {
  let slide = pres.addSlide();
  slide.background = { color: C.light };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.blue },
  });
  slide.addText(`🏢  ${equipe.nom}`, {
    x: 0.3, y: 0.1, w: 9.4, h: 0.8,
    fontSize: 22, bold: true, color: C.white,
  });

  // PMs
  if (equipe.pms && equipe.pms.length > 0) {
    slide.addText("PM(s) : " + equipe.pms.join(", "), {
      x: 0.5, y: 1.1, w: 9, h: 0.4,
      fontSize: 12, color: C.gray, italic: true,
    });
  }

  // Epics
  const estarY = 1.6;
  slide.addText("Epics rattachées :", {
    x: 0.5, y: estarY, w: 9, h: 0.35,
    fontSize: 13, bold: true, color: C.dark,
  });

  let ey = estarY + 0.4;
  (equipe.epics || []).forEach(epic => {
    if (ey > 5.0) return;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: ey, w: 9, h: 0.45,
      fill: { color: "D5E8D4" },
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: ey, w: 0.08, h: 0.45,
      fill: { color: C.green },
    });
    slide.addText(`📌 ${epic.nom}  ${epic.nb_features ? "(" + epic.nb_features + " features)" : ""}`, {
      x: 0.7, y: ey + 0.03, w: 8.6, h: 0.38,
      fontSize: 11, color: C.dark,
    });
    ey += 0.55;
  });
});

// ─────────────────────────────────────────────────────────
// SLIDES PAR EPIC (avec ambition PI)
// ─────────────────────────────────────────────────────────
(data.epics_detail || []).forEach(epic => {
  let slide = pres.addSlide();
  slide.background = { color: C.light };

  const isSep = epic.separee;
  const headerColor = isSep ? C.orange : C.green;

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: headerColor },
  });
  slide.addText(`📌  ${epic.nom}${isSep ? "  ⚠️ SÉPARÉE" : ""}`, {
    x: 0.3, y: 0.1, w: 9.4, h: 0.8,
    fontSize: 20, bold: true, color: C.white,
  });

  let y = 1.1;

  // Description
  if (epic.description) {
    slide.addText("Description", {
      x: 0.5, y, w: 9, h: 0.3,
      fontSize: 12, bold: true, color: C.dark,
    });
    y += 0.3;
    slide.addText(epic.description, {
      x: 0.5, y, w: 9, h: 0.6,
      fontSize: 10, color: C.gray,
    });
    y += 0.7;
  }

  // Intention PI
  if (epic.intention_pi) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 9, h: 0.8,
      fill: { color: "DAE8FC" },
    });
    slide.addText("🎯 Intention du PI en cours", {
      x: 0.7, y: y + 0.05, w: 8.6, h: 0.3,
      fontSize: 11, bold: true, color: C.blue,
    });
    slide.addText(epic.intention_pi, {
      x: 0.7, y: y + 0.35, w: 8.6, h: 0.4,
      fontSize: 10, color: C.dark,
    });
    y += 0.95;
  }

  // Intention MVP
  if (epic.intention_mvp) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 9, h: 0.8,
      fill: { color: "D5E8D4" },
    });
    slide.addText("🚀 Intention prochain incrément / MVP (impact 3 mois)", {
      x: 0.7, y: y + 0.05, w: 8.6, h: 0.3,
      fontSize: 11, bold: true, color: C.green,
    });
    slide.addText(epic.intention_mvp, {
      x: 0.7, y: y + 0.35, w: 8.6, h: 0.4,
      fontSize: 10, color: C.dark,
    });
    y += 0.95;
  }

  // Features
  if (epic.features && epic.features.length > 0) {
    slide.addText(`Features (${epic.features.length}) :`, {
      x: 0.5, y, w: 9, h: 0.3,
      fontSize: 11, bold: true, color: C.dark,
    });
    y += 0.35;
    epic.features.slice(0, 4).forEach(f => {
      if (y > 5.2) return;
      slide.addText(`⚡ ${f}`, {
        x: 0.7, y, w: 8.6, h: 0.3,
        fontSize: 10, color: C.gray,
        bullet: false,
      });
      y += 0.32;
    });
  }
});

pres.writeFile({ fileName: outputPath })
  .then(() => { console.log("OK:" + outputPath); })
  .catch(err => { console.error("ERR:" + err); process.exit(1); });
"""


def _prepare_pptx_data(model: dict, structure: dict, fragmentation_data: list) -> dict:
    """Prépare les données JSON pour le script PptxGenJS."""
    stats = model["stats"]
    epics_separees_ids = set(model["epics_separees"])

    # Données par équipe
    equipes_data = []
    for team_node in structure["equipes"]:
        team_agents = set()
        team_epics_ids = [e["id"] for e in team_node.get("epics", [])]
        for aff in model["affectations"]:
            if aff["equipe_id"] == team_node["id"]:
                team_agents.add(aff["personne_id"])

        charge_par_personne = stats["charge_par_personne"]
        has_surcharge = any(
            charge_par_personne.get(pid, 0) > 100 for pid in team_agents
        )

        equipes_data.append({
            "nom": team_node["nom"],
            "pms": [pm["nom"] for pm in team_node.get("pms", [])],
            "epics": [
                {
                    "nom": e["nom"],
                    "nb_features": len(e.get("features", [])),
                }
                for e in team_node.get("epics", [])
            ],
            "nb_epics": len(team_node.get("epics", [])),
            "nb_features": sum(len(e.get("features", [])) for e in team_node.get("epics", [])),
            "nb_agents": len(team_agents),
            "has_surcharge": has_surcharge,
        })

    # Détail des epics (pour slides dédiées)
    epics_detail = []
    for epic_id, epic in model["epics"].items():
        feats = [
            f["nom"]
            for f in model["features"].values()
            if f["epic_id"] == epic_id
        ]
        epics_detail.append({
            "nom": epic["nom"],
            "description": epic.get("description", ""),
            "intention_pi": epic.get("intention_pi", ""),
            "intention_mvp": epic.get("intention_mvp", ""),
            "features": feats,
            "separee": epic_id in epics_separees_ids,
        })

    return {
        "pi_num": model["pi_num"],
        "stats": {
            **stats,
            "nb_epics_separees": len(epics_separees_ids),
            # Remove non-serializable sets
            "agents_surcharges": list(stats.get("agents_surcharges", [])),
            "agents_multi_equipes": list(stats.get("agents_multi_equipes", [])),
            "equipes_par_personne": {
                str(k): list(v) for k, v in stats.get("equipes_par_personne", {}).items()
            },
            "charge_par_personne": {
                str(k): v for k, v in stats.get("charge_par_personne", {}).items()
            },
        },
        "equipes": equipes_data,
        "epics_detail": epics_detail,
    }


def generate_pptx(model: dict, structure: dict, fragmentation_data: list, output_path: str) -> str:
    """
    Génère le fichier PowerPoint via Node.js + PptxGenJS.
    
    Returns:
        chemin du fichier généré
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Vérifie Node.js
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  ⚠️   Node.js non disponible, génération PPTX ignorée.")
        print("       Installez Node.js pour activer cette fonctionnalité.")
        return ""

    # Installe pptxgenjs si nécessaire
    try:
        subprocess.run(
            ["npm", "list", "-g", "pptxgenjs"],
            capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        print("  📦  Installation de pptxgenjs...")
        subprocess.run(["npm", "install", "-g", "pptxgenjs"], check=True)

    # Prépare les données
    pptx_data = _prepare_pptx_data(model, structure, fragmentation_data)
    data_json = json.dumps(pptx_data, ensure_ascii=False)

    # Écrit le script dans un fichier temp
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(PPTXGEN_SCRIPT)
        script_path = f.name

    try:
        result = subprocess.run(
            ["node", script_path, data_json, str(out_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0 or "ERR:" in result.stdout:
            print(f"  ❌  Erreur génération PPTX : {result.stderr or result.stdout}")
            return ""
        print(f"  ✅  PowerPoint généré : {out_path}")
        return str(out_path)
    except subprocess.TimeoutExpired:
        print("  ❌  Timeout génération PPTX")
        return ""
    finally:
        Path(script_path).unlink(missing_ok=True)
