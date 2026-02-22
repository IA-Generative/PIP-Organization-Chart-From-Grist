"""
analytics.py
------------
Analyse des multi-affectations et calcul du score de fragmentation.

Score de fragmentation :
  fragmentation_score = nb_equipes + nb_epics + max(0, nb_assignments - 3)

Exports :
  - multi_affectations.csv
  - synthesis.md
"""

import csv
from pathlib import Path
from typing import Any, Dict, List


def compute_fragmentation(model: dict) -> List[dict]:
    """
    Calcule le score de fragmentation pour chaque personne.
    
    Returns:
        Liste de dicts triés par score décroissant
    """
    personnes = model["personnes"]
    affectations = model["affectations"]
    stats = model["stats"]

    # Agrégation par personne
    agg: Dict[Any, dict] = {}
    for aff in affectations:
        pid = aff["personne_id"]
        if not pid:
            continue
        if pid not in agg:
            agg[pid] = {
                "personne_id": pid,
                "nom": personnes.get(pid, {}).get("nom", f"ID:{pid}"),
                "equipes": set(),
                "epics": set(),
                "nb_assignments": 0,
                "charge_totale": 0.0,
                "roles": set(),
            }
        agg[pid]["equipes"].add(aff["equipe_id"])
        agg[pid]["epics"].add(aff["epic_id"])
        agg[pid]["nb_assignments"] += 1
        agg[pid]["charge_totale"] += aff["charge"]
        if aff["role"]:
            agg[pid]["roles"].add(aff["role"])

    results = []
    for pid, data in agg.items():
        nb_equipes = len(data["equipes"] - {None})
        nb_epics   = len(data["epics"]   - {None})
        nb_assignments = data["nb_assignments"]

        score = nb_equipes + nb_epics + max(0, nb_assignments - 3)

        results.append({
            "personne_id":    pid,
            "nom":            data["nom"],
            "nb_equipes":     nb_equipes,
            "nb_epics":       nb_epics,
            "nb_assignments": nb_assignments,
            "charge_totale":  round(data["charge_totale"], 1),
            "roles":          ", ".join(sorted(data["roles"])),
            "fragmentation_score": score,
            "multi_equipes":  nb_equipes > 1,
            "surcharge":      data["charge_totale"] > 100,
            "alerte":         score >= 5,
        })

    results.sort(key=lambda x: x["fragmentation_score"], reverse=True)
    return results


def export_csv(fragmentation_data: List[dict], output_path: str) -> str:
    """Exporte le CSV des multi-affectations."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "nom", "nb_equipes", "nb_epics", "nb_assignments",
        "charge_totale", "roles", "fragmentation_score",
        "multi_equipes", "surcharge", "alerte"
    ]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(fragmentation_data)

    print(f"  ✅  CSV exporté : {out}")
    return str(out)


def export_synthesis_md(fragmentation_data: List[dict], model: dict, output_path: str) -> str:
    """Génère le fichier synthesis.md avec analyse narrative."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    stats = model["stats"]
    pi_num = model["pi_num"]

    surcharges = [d for d in fragmentation_data if d["surcharge"]]
    multi_equipes = [d for d in fragmentation_data if d["multi_equipes"]]
    top_frag = fragmentation_data[:5]  # top 5

    lines = [
        f"# Analyse des Multi-Affectations – {pi_num}",
        "",
        "## Résumé Global",
        "",
        f"| Métrique | Valeur |",
        f"|----------|--------|",
        f"| Équipes | {stats['nb_equipes']} |",
        f"| Epics | {stats['nb_epics']} |",
        f"| Features PI | {stats['nb_features_pi']} |",
        f"| Personnes | {stats['nb_personnes']} |",
        f"| Affectations totales | {stats['nb_affectations']} |",
        f"| Agents >100% | **{stats['nb_agents_surcharges']}** |",
        f"| Agents multi-équipes | **{stats['nb_agents_multi_equipes']}** |",
        "",
        "---",
        "",
        "## Agents en Surcharge (>100%)",
        "",
    ]

    if surcharges:
        lines.append("| Nom | Charge Totale | Équipes | Score Fragmentation |")
        lines.append("|-----|--------------|---------|---------------------|")
        for d in surcharges:
            lines.append(f"| {d['nom']} | **{d['charge_totale']}%** | {d['nb_equipes']} | {d['fragmentation_score']} |")
    else:
        lines.append("✅ Aucun agent en surcharge.")

    lines += [
        "",
        "---",
        "",
        "## Agents Multi-Équipes",
        "",
    ]

    if multi_equipes:
        lines.append("| Nom | Nb Équipes | Nb Epics | Score Fragmentation |")
        lines.append("|-----|-----------|---------|---------------------|")
        for d in multi_equipes:
            lines.append(f"| {d['nom']} | {d['nb_equipes']} | {d['nb_epics']} | {d['fragmentation_score']} |")
    else:
        lines.append("✅ Aucun agent multi-équipes.")

    lines += [
        "",
        "---",
        "",
        "## Top 5 – Score de Fragmentation",
        "",
        "> 🔢 Score = nb_équipes + nb_epics + max(0, nb_affectations - 3)",
        "",
        "| Rang | Nom | Score | Équipes | Epics | Affectations | Charge |",
        "|------|-----|-------|---------|-------|-------------|--------|",
    ]

    for i, d in enumerate(top_frag, 1):
        emoji = "🔴" if d["fragmentation_score"] >= 8 else ("🟠" if d["fragmentation_score"] >= 5 else "🟢")
        lines.append(
            f"| {i} | {d['nom']} | {emoji} **{d['fragmentation_score']}** | "
            f"{d['nb_equipes']} | {d['nb_epics']} | {d['nb_assignments']} | {d['charge_totale']}% |"
        )

    lines += [
        "",
        "---",
        "",
        "## Légende",
        "",
        "- 🔴 Score ≥ 8 : fragmentation critique",
        "- 🟠 Score ≥ 5 : fragmentation élevée",
        "- 🟢 Score < 5 : fragmentation normale",
        "",
        "*Généré automatiquement par grist-org-visualizer*",
    ]

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅  Synthèse analytique : {out}")
    return str(out)
