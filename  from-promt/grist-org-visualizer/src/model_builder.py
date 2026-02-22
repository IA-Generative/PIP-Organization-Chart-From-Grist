"""
model_builder.py
----------------
Construit le modèle de données unifié à partir des tables brutes Grist.
Applique le mapping de colonnes défini dans config/mapping.yml.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def load_mapping() -> dict:
    mapping_path = Path("config/mapping.yml")
    if mapping_path.exists():
        with open(mapping_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def _get(row: dict, col: str, default=None):
    """Récupère une valeur de dict de manière tolérante."""
    return row.get(col, default)


def build_model(raw_data: Dict[str, List[Dict]], pi_num: str) -> dict:
    """
    Construit le modèle SDID à partir des données brutes.
    
    Args:
        raw_data: données chargées depuis Grist { table_logique: [rows] }
        pi_num: identifiant du PI (ex: "PI-10")
    
    Returns:
        dict avec clés : equipes, personnes, epics, features, affectations,
                         epics_separees, stats
    """
    mapping = load_mapping()
    cols_aff = mapping.get("columns", {}).get("affectations", {})
    cols_epic = mapping.get("columns", {}).get("epics", {})
    cols_feat = mapping.get("columns", {}).get("features", {})

    # ── Équipes
    equipes = {
        row.get("id", i): {
            "id": row.get("id", i),
            "nom": row.get("Nom", row.get("nom", f"Equipe-{i}")),
        }
        for i, row in enumerate(raw_data.get("equipes", []))
    }

    # ── Personnes
    personnes = {
        row.get("id", i): {
            "id": row.get("id", i),
            "nom": row.get("Nom", row.get("nom", f"Personne-{i}")),
        }
        for i, row in enumerate(raw_data.get("personnes", []))
    }

    # ── Epics
    epics = {}
    for i, row in enumerate(raw_data.get("epics", [])):
        eid = row.get("id", i)
        epics[eid] = {
            "id": eid,
            "nom": row.get(cols_epic.get("nom", "Nom"), f"Epic-{i}"),
            "description": row.get(cols_epic.get("description", "Description_EPIC"), ""),
            "intention_pi": row.get(cols_epic.get("intention_pi", "Intention_du_PI_en_cours"), ""),
            "intention_mvp": row.get(
                cols_epic.get("intention_mvp", "Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_"), ""
            ),
        }

    # ── Features du PI courant
    features = {}
    pi_normalized = pi_num.upper().replace(" ", "-")
    for i, row in enumerate(raw_data.get("features", [])):
        pi_val = str(row.get(cols_feat.get("pi_num", "pi_Num"), "")).strip()
        if pi_val.upper().replace(" ", "-") == pi_normalized or not pi_val:
            fid = row.get("id", i)
            features[fid] = {
                "id": fid,
                "epic_id": row.get(cols_feat.get("epic", "Epic")),
                "nom": row.get(cols_feat.get("nom", "Nom"), f"Feature-{i}"),
                "description": row.get(cols_feat.get("description", "Description"), ""),
                "pi_num": pi_val,
            }

    # ── Affectations
    affectations = []
    for row in raw_data.get("affectations", []):
        equipe_id = row.get(cols_aff.get("equipe", "Affecte_a_l_equipe"))
        epic_id   = row.get(cols_aff.get("epic",   "Affecte_a_l_Epic"))
        personne_id = row.get(cols_aff.get("personne", "Personne"))
        charge    = float(row.get(cols_aff.get("charge", "Charge"), 0) or 0)
        role      = row.get(cols_aff.get("role", "Role"), "")
        affectations.append({
            "equipe_id":   equipe_id,
            "epic_id":     epic_id,
            "personne_id": personne_id,
            "charge":      charge,
            "role":        role,
        })

    # ── Détection des Epics "séparées"
    # Une Epic est séparée si ses membres (PO) ne sont pas dans l'équipe principale
    epics_separees = _detect_epics_separees(equipes, epics, affectations)

    # ── Stats de base
    stats = _compute_stats(equipes, personnes, epics, features, affectations)

    return {
        "pi_num": pi_normalized,
        "equipes": equipes,
        "personnes": personnes,
        "epics": epics,
        "features": features,
        "affectations": affectations,
        "epics_separees": epics_separees,
        "stats": stats,
    }


def _detect_epics_separees(equipes: dict, epics: dict, affectations: list) -> List[int]:
    """
    Détecte les Epics dont les membres PO ne font pas partie de l'équipe principale.
    
    Règle : une Epic est "séparée" si people_epic ⊄ people_team
    """
    # Membres par équipe
    team_members: Dict[Any, set] = {}
    for aff in affectations:
        tid = aff["equipe_id"]
        pid = aff["personne_id"]
        if tid and pid:
            team_members.setdefault(tid, set()).add(pid)

    # Membres par epic
    epic_members: Dict[Any, set] = {}
    for aff in affectations:
        eid = aff["epic_id"]
        pid = aff["personne_id"]
        if eid and pid:
            epic_members.setdefault(eid, set()).add(pid)

    # Pour chaque epic, vérifie si ses membres sont couverts par au moins une équipe
    epics_separees = []
    for epic_id, members in epic_members.items():
        covered = False
        for team_id, team_m in team_members.items():
            if members.issubset(team_m):
                covered = True
                break
        if not covered:
            epics_separees.append(epic_id)

    return epics_separees


def _compute_stats(equipes, personnes, epics, features, affectations) -> dict:
    """Calcule les statistiques globales."""
    # Charge par personne
    charge_par_personne: Dict[Any, float] = {}
    equipes_par_personne: Dict[Any, set] = {}

    for aff in affectations:
        pid = aff["personne_id"]
        if pid:
            charge_par_personne[pid] = charge_par_personne.get(pid, 0.0) + aff["charge"]
            if aff["equipe_id"]:
                equipes_par_personne.setdefault(pid, set()).add(aff["equipe_id"])

    agents_surcharges = [
        pid for pid, c in charge_par_personne.items() if c > 100
    ]
    agents_multi_equipes = [
        pid for pid, eqs in equipes_par_personne.items() if len(eqs) > 1
    ]

    return {
        "nb_equipes": len(equipes),
        "nb_epics": len(epics),
        "nb_features_pi": len(features),
        "nb_affectations": len(affectations),
        "nb_personnes": len(personnes),
        "nb_agents_surcharges": len(agents_surcharges),
        "nb_agents_multi_equipes": len(agents_multi_equipes),
        "agents_surcharges": agents_surcharges,
        "agents_multi_equipes": agents_multi_equipes,
        "charge_par_personne": charge_par_personne,
        "equipes_par_personne": equipes_par_personne,
    }
