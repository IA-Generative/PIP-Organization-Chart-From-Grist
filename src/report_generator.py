from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from .model_builder import BuiltModel


def _df_to_markdown(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        # Fallback when optional dependency `tabulate` is unavailable.
        return f"```\n{df.to_string(index=False)}\n```"


def _sorted_members(members: set[str]) -> List[str]:
    return sorted([m for m in members if m and m != "UNKNOWN"])


def write_fragmentation_reports(df: pd.DataFrame, out_csv: str, out_md: str) -> Dict[str, int]:
    df.to_csv(out_csv, index=False)

    over_100 = df[df["Total_Charge"] > 100.0] if not df.empty else df
    multi_team = df[df["Nb_Equipes"] > 1] if not df.empty else df

    lines: List[str] = []
    lines.append("# Synthèse multi-affectations / fragmentation")
    lines.append("")
    if df.empty:
        lines.append("Aucune affectation trouvée (table Affectations vide).")
    else:
        lines.append("## Top 10 agents les plus fragmentés")
        lines.append("")
        lines.append(_df_to_markdown(df.head(10)))
        lines.append("")
        lines.append(f"## Agents > 100% de charge ({len(over_100)})")
        lines.append("")
        lines.append(_df_to_markdown(over_100) if len(over_100) else "_Aucun_")
        lines.append("")
        lines.append(f"## Agents multi-équipes ({len(multi_team)})")
        lines.append("")
        lines.append(_df_to_markdown(multi_team) if len(multi_team) else "_Aucun_")
        lines.append("")
        lines.append("## Recommandations de défragmentation (heuristiques)")
        lines.append("")
        lines.append("- Réduire le nombre de contextes (équipes/epics) par agent sur le PI.")
        lines.append("- Grouper les items de backlog par epic dominante et limiter les micro-affectations.")
        lines.append("- Prioriser la stabilité des équipes, rendre explicites les epics transverses.")
        lines.append("- Surveiller les agents >100% (risque de surcharge, baisse qualité, retards).")

    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {
        "agents_over_100": int(len(over_100)) if not df.empty else 0,
        "agents_multi_team": int(len(multi_team)) if not df.empty else 0,
    }


def write_run_summary(
    model: BuiltModel,
    frag_kpis: Dict[str, int],
    source_label: str,
    out_md: str,
    features_table_empty: bool,
    epics_missing_intentions: list[str],
) -> None:
    lines = []
    lines.append("=== RUN SUMMARY ===")
    lines.append(f"Source utilisée : {source_label}")
    lines.append(f"PI : {model.pi}")
    lines.append(f"Nb équipes : {model.stats.get('teams', 0)}")
    lines.append(f"Nb epics : {model.stats.get('epics_total', 0)}")
    lines.append(f"Nb epics séparées : {model.stats.get('epics_separate', 0)}")
    lines.append(f"Nb features du PI : {model.stats.get('features_pi', 0)}")
    lines.append(f"Nb affectations : {model.stats.get('affectations', 0)}")
    lines.append(f"Nb personnes : {model.stats.get('personnes', 0)}")
    lines.append(f"Agents >100% : {frag_kpis.get('agents_over_100', 0)}")
    lines.append(f"Agents multi-équipes : {frag_kpis.get('agents_multi_team', 0)}")
    lines.append(f"Features table vide : {'OUI' if features_table_empty else 'NON'}")
    lines.append("")
    lines.append("Membres par équipe :")
    if not model.teams:
        lines.append("- Aucune équipe trouvée")
    else:
        for team in model.teams:
            members = _sorted_members(team.people_team)
            if members:
                lines.append(f"- {team.name} ({len(members)}) : {', '.join(members)}")
            else:
                lines.append(f"- {team.name} (0) : aucun membre détecté")
    if epics_missing_intentions:
        lines.append("Epics sans intention/description (à compléter) :")
        for e in epics_missing_intentions[:20]:
            lines.append(f"- {e}")
        if len(epics_missing_intentions) > 20:
            lines.append(f"... +{len(epics_missing_intentions)-20} autres")
    content = "\n".join(lines)
    print(content)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(content + "\n")
