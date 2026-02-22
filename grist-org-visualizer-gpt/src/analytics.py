from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd


@dataclass
class FragmentRow:
    agent: str
    nb_equipes: int
    nb_epics: int
    nb_roles: int
    nb_assignments: int
    total_charge: float
    fragmentation_score: int


def compute_fragmentation(data, mapping: Dict) -> pd.DataFrame:
    cols = mapping["columns"]
    aff = data.affectations.copy()
    if aff.empty:
        return pd.DataFrame(columns=[
            "Agent","Nb_Equipes","Nb_Epics","Nb_Roles","Nb_Affectations","Total_Charge","Score_Fragmentation"
        ])

    personnes = data.personnes
    person_label_col = cols["personne_label"]
    person_map = dict(zip(personnes["id"], personnes[person_label_col].astype(str)))

    aff_person = cols["aff_person_ref"]
    aff_team = cols["aff_team_ref"]
    aff_epic = cols["aff_epic_ref"]
    aff_role = cols["aff_role"]
    aff_charge = cols["aff_charge"]

    for c in [aff_person, aff_team, aff_role, aff_charge]:
        if c not in aff.columns:
            raise ValueError(f"Colonne Affectations.{c} introuvable")

    aff["_agent"] = aff[aff_person].map(person_map).fillna("UNKNOWN").astype(str)
    aff["_team"] = aff[aff_team]
    aff["_epic"] = aff[aff_epic] if aff_epic in aff.columns else None
    aff["_role"] = aff[aff_role].astype(str)
    aff["_charge"] = pd.to_numeric(aff[aff_charge], errors="coerce").fillna(0.0)

    rows = []
    for agent, grp in aff.groupby("_agent"):
        nb_equipes = int(grp["_team"].nunique(dropna=True))
        nb_epics = int(grp["_epic"].nunique(dropna=True)) if "_epic" in grp else 0
        nb_roles = int(grp["_role"].nunique(dropna=True))
        nb_assignments = int(len(grp))
        total_charge = float(grp["_charge"].sum())
        score = nb_equipes + nb_epics + max(0, nb_assignments - 3)
        rows.append({
            "Agent": agent,
            "Nb_Equipes": nb_equipes,
            "Nb_Epics": nb_epics,
            "Nb_Roles": nb_roles,
            "Nb_Affectations": nb_assignments,
            "Total_Charge": round(total_charge, 2),
            "Score_Fragmentation": int(score),
        })

    df = pd.DataFrame(rows).sort_values(["Score_Fragmentation","Total_Charge"], ascending=[False, False])
    return df
