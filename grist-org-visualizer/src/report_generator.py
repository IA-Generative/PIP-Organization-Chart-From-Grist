"""
report_generator.py
-------------------
Génère le run_summary.md (checklist de fin de run).
Affiche aussi un résumé console.
"""

from datetime import datetime
from pathlib import Path


def generate_run_summary(
    model: dict,
    source_used: str,
    outputs: dict,
    output_path: str,
) -> str:
    """
    Génère la checklist de fin de run.
    
    Args:
        model: modèle de données
        source_used: "api" ou chemin fichier
        outputs: dict des chemins produits
        output_path: chemin du fichier de sortie
    
    Returns:
        chemin du fichier généré
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    stats = model["stats"]
    pi_num = model["pi_num"]
    nb_sep = len(model["epics_separees"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Affichage console
    summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                        RUN SUMMARY                           ║
╠══════════════════════════════════════════════════════════════╣
║  Source utilisée   : {source_used:<38} ║
║  PI                : {pi_num:<38} ║
║  Date              : {now:<38} ║
╠══════════════════════════════════════════════════════════════╣
║  Nb équipes        : {str(stats['nb_equipes']):<38} ║
║  Nb epics          : {str(stats['nb_epics']):<38} ║
║  Nb epics séparées : {str(nb_sep):<38} ║
║  Nb features PI    : {str(stats['nb_features_pi']):<38} ║
║  Nb affectations   : {str(stats['nb_affectations']):<38} ║
║  Nb personnes      : {str(stats['nb_personnes']):<38} ║
║  Agents >100%      : {str(stats['nb_agents_surcharges']):<38} ║
║  Agents multi-éq.  : {str(stats['nb_agents_multi_equipes']):<38} ║
╠══════════════════════════════════════════════════════════════╣
║  FICHIERS PRODUITS                                           ║"""

    for label, path in outputs.items():
        status = "✅" if path and Path(path).exists() else "❌"
        fname = Path(path).name if path else "non généré"
        summary += f"\n║  {status} {label:<18} {fname:<36} ║"

    summary += "\n╚══════════════════════════════════════════════════════════════╝\n"
    print(summary)

    # Fichier Markdown
    md_lines = [
        f"# Run Summary – {pi_num}",
        "",
        f"**Date** : {now}  ",
        f"**Source** : {source_used}  ",
        "",
        "## Métriques",
        "",
        "| Métrique | Valeur |",
        "|----------|--------|",
        f"| Source utilisée | `{source_used}` |",
        f"| PI | {pi_num} |",
        f"| Nb équipes | {stats['nb_equipes']} |",
        f"| Nb epics | {stats['nb_epics']} |",
        f"| Nb epics séparées | **{nb_sep}** |",
        f"| Nb features PI | {stats['nb_features_pi']} |",
        f"| Nb affectations | {stats['nb_affectations']} |",
        f"| Nb personnes | {stats['nb_personnes']} |",
        f"| Agents >100% | **{stats['nb_agents_surcharges']}** |",
        f"| Agents multi-équipes | **{stats['nb_agents_multi_equipes']}** |",
        "",
        "## Fichiers Produits",
        "",
        "| Statut | Type | Fichier |",
        "|--------|------|---------|",
    ]

    for label, path in outputs.items():
        status = "✅" if path and Path(path).exists() else "❌"
        fname = path if path else "non généré"
        md_lines.append(f"| {status} | {label} | `{fname}` |")

    md_lines += [
        "",
        "---",
        "",
        "*Généré par grist-org-visualizer*",
    ]

    out.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  ✅  Run summary : {out}")
    return str(out)
