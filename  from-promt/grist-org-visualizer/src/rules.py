"""
rules.py
--------
Règles métier SDID :
  - Détection des rôles (PM, PO, DEV)
  - Classement des personnes dans l'organigramme
  - Règles de placement dans draw.io
"""

from typing import Dict, List, Any


ROLE_PM = "PM"
ROLE_PO = "PO"
ROLE_DEV = "DEV"


def classify_person_role(role_str: str) -> str:
    """Normalise un rôle en PM/PO/DEV."""
    r = (role_str or "").upper().strip()
    if ROLE_PM in r:
        return ROLE_PM
    if ROLE_PO in r:
        return ROLE_PO
    return ROLE_DEV


def get_team_pms(team_id: Any, affectations: List[dict], personnes: dict) -> List[dict]:
    """Retourne les PM d'une équipe."""
    return [
        personnes[aff["personne_id"]]
        for aff in affectations
        if aff["equipe_id"] == team_id
        and classify_person_role(aff["role"]) == ROLE_PM
        and aff["personne_id"] in personnes
    ]


def get_epic_pos(epic_id: Any, affectations: List[dict], personnes: dict) -> List[dict]:
    """Retourne les PO d'une epic."""
    return [
        personnes[aff["personne_id"]]
        for aff in affectations
        if aff["epic_id"] == epic_id
        and classify_person_role(aff["role"]) == ROLE_PO
        and aff["personne_id"] in personnes
    ]


def get_team_epics(team_id: Any, affectations: List[dict]) -> List[Any]:
    """Retourne les IDs des epics rattachées à une équipe."""
    seen = set()
    result = []
    for aff in affectations:
        if aff["equipe_id"] == team_id and aff["epic_id"] not in seen:
            seen.add(aff["epic_id"])
            result.append(aff["epic_id"])
    return result


def get_epic_features(epic_id: Any, features: dict) -> List[dict]:
    """Retourne les features d'une epic."""
    return [f for f in features.values() if f["epic_id"] == epic_id]


def is_epic_separee(epic_id: Any, epics_separees: List[Any]) -> bool:
    return epic_id in epics_separees


def build_org_structure(model: dict) -> dict:
    """
    Construit la structure organisationnelle pour le rendu.
    
    Returns:
        dict avec structure hiérarchique équipes → epics → features → personnes
    """
    equipes = model["equipes"]
    personnes = model["personnes"]
    epics = model["epics"]
    features = model["features"]
    affectations = model["affectations"]
    epics_separees = model["epics_separees"]

    structure = {"equipes": [], "epics_separees": []}

    for team_id, team in equipes.items():
        team_epics_ids = get_team_epics(team_id, affectations)
        team_pms = get_team_pms(team_id, affectations, personnes)

        team_node = {
            "id": team_id,
            "nom": team["nom"],
            "pms": team_pms,
            "epics": [],
        }

        for epic_id in team_epics_ids:
            if epic_id not in epics:
                continue
            epic = epics[epic_id]
            epic_pos = get_epic_pos(epic_id, affectations, personnes)
            epic_features = get_epic_features(epic_id, features)
            separee = is_epic_separee(epic_id, epics_separees)

            epic_node = {
                "id": epic_id,
                "nom": epic["nom"],
                "description": epic["description"],
                "intention_pi": epic["intention_pi"],
                "intention_mvp": epic["intention_mvp"],
                "pos": epic_pos,
                "features": epic_features,
                "separee": separee,
            }

            if separee:
                structure["epics_separees"].append(epic_node)
            else:
                team_node["epics"].append(epic_node)

        structure["equipes"].append(team_node)

    return structure
