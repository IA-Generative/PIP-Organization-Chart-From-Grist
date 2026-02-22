from __future__ import annotations

from typing import Dict, List

from .model_builder import BuiltModel


def generate_readme(model: BuiltModel, out_path: str) -> None:
    lines: List[str] = []
    lines.append(f"# README généré — {model.pi}")
    lines.append("")
    lines.append("Ce document est généré automatiquement à partir du fichier Grist SDID.")
    lines.append("")
    lines.append("## Résumé")
    lines.append("")
    lines.append(f"- PI : **{model.pi}**")
    lines.append(f"- Équipes : **{model.stats.get('teams', 0)}**")
    lines.append(f"- Epics : **{model.stats.get('epics_total', 0)}** (dont séparées : **{model.stats.get('epics_separate', 0)}**)")
    lines.append(f"- Features (PI) : **{model.stats.get('features_pi', 0)}**")
    lines.append("")
    lines.append("## Lecture rapide")
    lines.append("")
    lines.append("- **PM** : affichés au niveau **Équipe** (container).")
    lines.append("- **PO** : affichés sur les **Epics séparées** (transverses/spécifiques).")
    lines.append("- **Epic séparée** : si les personnes affectées à l’epic ne sont pas un sous-ensemble des personnes de l’équipe.")
    lines.append("")
    lines.append("## Structure des sorties")
    lines.append("")
    lines.append("- `orgchart.drawio` : diagramme organisationnel")
    lines.append("- `multi_affectations.csv` + `synthesis.md` : fragmentation")
    lines.append(f"- `PI-{model.pi.split('-')[-1]}_Synthese_SDID.pptx` : PowerPoint de synthèse")
    lines.append("- `run_summary.md` : checklist d’exécution")
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
