from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from .rules import normalize_pi_value
from .ref_utils import parse_ref_id, parse_ref_list


@dataclass
class AssignmentLine:
    person: str
    role: str
    charge: float


@dataclass
class EpicModel:
    id: int
    name: str
    description: str
    intention_pi: str
    intention_next: str
    assignments: List[AssignmentLine]
    features: List[str]
    po_list: List[str]
    is_separate: bool = False


@dataclass
class TeamModel:
    id: int
    name: str
    pm_list: List[str]
    po_list: List[str]
    people_team: Set[str]
    epics: List[EpicModel]
    mission_summary: str = ""
    next_increment_summary: str = ""
    kpi_summary: str = ""
    kpi_ai_suggestion: str = ""
    summary_ai_used: bool = False
    summary_warning: str = ""


@dataclass
class BuiltModel:
    pi: str
    teams: List[TeamModel]
    separate_epics: List[EpicModel]
    stats: Dict[str, int]


def _safe_str(x) -> str:
    return "" if x is None else str(x)


def _is_blank_like(value) -> bool:
    s = _safe_str(value).strip()
    return not s or s.lower() == "nan"


def _norm_col_name(name: str) -> str:
    return "".join(ch for ch in name.lower().strip() if ch.isalnum())


def _resolve_column_name(df: pd.DataFrame, preferred: str, aliases: List[str]) -> Optional[str]:
    if preferred in df.columns:
        return preferred
    normalized = {_norm_col_name(c): c for c in df.columns}
    for candidate in [preferred] + aliases:
        key = _norm_col_name(candidate)
        if key in normalized:
            return normalized[key]
    return None


def build_model(
    data,
    mapping: Dict,
    pi: str,
) -> BuiltModel:
    cols = mapping["columns"]
    roles = mapping.get("roles", {})
    pm_role = roles.get("pm", "PM")
    po_role = roles.get("po", "PO")

    equipes = data.equipes.copy()
    personnes = data.personnes.copy()
    epics = data.epics.copy()
    features = data.features.copy()
    affectations = data.affectations.copy()

    # Basic validation (minimal, user-friendly)
    required_tables = ["equipes", "personnes", "epics", "features", "affectations"]
    for t in required_tables:
        if t not in mapping["tables"]:
            raise ValueError(f"mapping.yml incomplet: tables.{t} manquant")

    # Build person id->label
    person_label_col = cols["personne_label"]
    if person_label_col not in personnes.columns:
        raise ValueError(f"Colonne Personnes.{person_label_col} introuvable")
    person_map = dict(zip(personnes["id"], personnes[person_label_col].astype(str)))

    # Affectations columns
    aff_team = cols["aff_team_ref"]
    aff_epic = cols["aff_epic_ref"]
    aff_person = cols["aff_person_ref"]
    aff_charge = cols["aff_charge"]
    aff_role = cols["aff_role"]

    for c in [aff_team, aff_person, aff_charge, aff_role]:
        if c not in affectations.columns:
            raise ValueError(f"Colonne Affectations.{c} introuvable")

    # Normalize Charge
    if affectations.empty:
        affectations[aff_charge] = pd.Series(dtype=float)
    else:
        affectations[aff_charge] = pd.to_numeric(affectations[aff_charge], errors="coerce").fillna(0.0)

    # Epic columns
    epic_name = cols["epic_name"]
    epic_desc = cols["epic_description"]
    epic_int_pi = cols["epic_intention_pi"]
    epic_int_next = _resolve_column_name(
        epics,
        cols["epic_intention_next"],
        aliases=[
            "Intention_prochain_Increment_a_3_mois",
            "Intention_du_prochain_Increment_ou_MVP_impact_a_3_mois_",
            "Intention prochain Increment a 3 mois",
        ],
    ) or cols["epic_intention_next"]

    for c in [epic_name]:
        if c not in epics.columns:
            raise ValueError(f"Colonne Epics.{c} introuvable")

    # Feature columns
    f_epic = cols["feature_epic_ref"]
    f_name = cols["feature_name"]
    f_pi = cols["feature_pi"]
    if not features.empty:
        for c in [f_epic, f_name, f_pi]:
            if c not in features.columns:
                raise ValueError(f"Colonne Features.{c} introuvable")
        features["_pi_norm"] = features[f_pi].apply(normalize_pi_value)
    else:
        features["_pi_norm"] = pd.Series(dtype=str)

    # Team columns
    team_name = _resolve_column_name(
        equipes,
        cols["equipe_name"],
        aliases=["Nom", "Name", "Libelle", "Label", "Titre", "Title"],
    )
    if team_name is None:
        raise ValueError(
            f"Colonne Equipes.{cols['equipe_name']} introuvable (et aucun alias standard trouvé)"
        )

    # Compute team people set
    team_people: Dict[int, Set[str]] = {}
    team_pms: Dict[int, List[str]] = {}
    team_pos: Dict[int, List[str]] = {}

    if not affectations.empty:
        # Resolve person label
        affectations["_person_id"] = affectations[aff_person].apply(parse_ref_id)
        affectations["_person_label"] = affectations["_person_id"].map(person_map).fillna("UNKNOWN")
        affectations["_role"] = affectations[aff_role].astype(str)
        affectations["_team_id"] = affectations[aff_team].apply(parse_ref_id)
        # Team-level actors should exclude zero-load assignments.
        affectations["_charge_positive"] = affectations[aff_charge] > 0

        for tid, grp in affectations.dropna(subset=["_team_id"]).groupby("_team_id"):
            grp_pos = grp.loc[grp["_charge_positive"]]
            team_people[int(tid)] = set(grp_pos["_person_label"].tolist())
            pms = grp_pos.loc[grp_pos["_role"] == pm_role, "_person_label"].unique().tolist()
            team_pms[int(tid)] = sorted([p for p in pms if p and p != "UNKNOWN"])
            pos = grp_pos.loc[grp_pos["_role"] == po_role, "_person_label"].unique().tolist()
            team_pos[int(tid)] = sorted([p for p in pos if p and p != "UNKNOWN"])
    else:
        # Empty: create empty sets for listed teams
        for tid in equipes["id"].tolist():
            team_people[int(tid)] = set()
            team_pms[int(tid)] = []
            team_pos[int(tid)] = []

    # Pre-compute epic assignments and PO lists
    epic_assignments: Dict[int, List[AssignmentLine]] = {}
    epic_pos: Dict[int, List[str]] = {}
    epic_people: Dict[int, Set[str]] = {}

    if not affectations.empty and aff_epic in affectations.columns:
        affectations["_epic_id"] = affectations[aff_epic].apply(parse_ref_id)
        for eid, grp in affectations.dropna(subset=["_epic_id"]).groupby("_epic_id"):
            lines: List[AssignmentLine] = []
            for _, r in grp.iterrows():
                lines.append(
                    AssignmentLine(
                        person=_safe_str(r["_person_label"]),
                        role=_safe_str(r["_role"]),
                        charge=float(r[aff_charge] or 0.0),
                    )
                )
            epic_assignments[int(eid)] = lines
            epic_people[int(eid)] = set([ln.person for ln in lines if ln.person and ln.person != "UNKNOWN"])
            pos = grp.loc[grp["_role"] == po_role, "_person_label"].unique().tolist()
            epic_pos[int(eid)] = sorted([p for p in pos if p and p != "UNKNOWN"])
    else:
        epic_assignments = {}
        epic_pos = {}
        epic_people = {}

    # Features per epic for this PI
    features_pi = features.loc[features["_pi_norm"] == pi] if not features.empty else features
    features_by_epic: Dict[int, List[str]] = {}
    if not features_pi.empty:
        for eid, grp in features_pi.groupby(f_epic):
            clean_features = [
                _safe_str(v).strip()
                for v in grp[f_name].tolist()
                if not _is_blank_like(v)
            ]
            if clean_features:
                features_by_epic[int(eid)] = clean_features

    # Epics name map
    epics_index = epics.set_index("id")

    def build_epic(eid: int, is_separate: bool) -> EpicModel:
        row = epics_index.loc[eid] if eid in epics_index.index else None
        name = _safe_str(row.get(epic_name)) if row is not None else f"Epic {eid}"
        desc = _safe_str(row.get(epic_desc)) if (row is not None and epic_desc in epics_index.columns) else ""
        int_pi = _safe_str(row.get(epic_int_pi)) if (row is not None and epic_int_pi in epics_index.columns) else ""
        int_next = _safe_str(row.get(epic_int_next)) if (row is not None and epic_int_next in epics_index.columns) else ""
        ass = epic_assignments.get(eid, [])
        feats = features_by_epic.get(eid, [])
        po_list = epic_pos.get(eid, [])
        return EpicModel(
            id=eid,
            name=name,
            description=desc,
            intention_pi=int_pi,
            intention_next=int_next,
            assignments=ass,
            features=feats,
            po_list=po_list,
            is_separate=is_separate,
        )

    # Build team->epics mapping with priority to Epics owner columns.
    team_ids: Set[int] = {int(x) for x in equipes["id"].tolist()}
    team_to_epics: Dict[int, List[int]] = {tid: [] for tid in team_ids}
    epic_owner_team: Dict[int, int] = {}

    # 1) Preferred source: Epics table owner link (Equipe / Equipe_portant_l_Epic).
    epic_owner_col = _resolve_column_name(
        epics,
        preferred="Equipe",
        aliases=["Equipe_portant_l_Epic", "EquipePortantLEpic", "Team", "OwnerTeam"],
    )
    if epic_owner_col and "id" in epics.columns:
        for _, erow in epics.iterrows():
            eid = parse_ref_id(erow.get("id"))
            if not eid:
                continue
            owner_refs = parse_ref_list(erow.get(epic_owner_col))
            owner_refs = [tid for tid in owner_refs if tid in team_ids]
            if owner_refs:
                epic_owner_team[eid] = owner_refs[0]

    # 2) Fallback source: Equipes.Epics mapping for epics not assigned above.
    if cols["equipe_epics"] in equipes.columns:
        for _, trow in equipes.iterrows():
            tid = int(trow["id"])
            epics_val = trow.get(cols["equipe_epics"])
            for eid in parse_ref_list(epics_val):
                if eid not in epic_owner_team:
                    epic_owner_team[eid] = tid

    # Build ordered list of epics per team from owner map.
    for eid, tid in epic_owner_team.items():
        if tid in team_to_epics:
            team_to_epics[tid].append(eid)

    # Deduplicate while preserving order.
    for tid in list(team_to_epics.keys()):
        seen_local: Set[int] = set()
        dedup_ids: List[int] = []
        for eid in team_to_epics[tid]:
            if eid in seen_local:
                continue
            seen_local.add(eid)
            dedup_ids.append(eid)
        team_to_epics[tid] = dedup_ids

    # Build teams with epics
    teams: List[TeamModel] = []
    separate_epics: List[EpicModel] = []
    epic_ids_seen: Set[int] = set()

    for _, trow in equipes.iterrows():
        tid = int(trow["id"])
        tname = _safe_str(trow.get(team_name)).strip() or f"Equipe {tid}"
        people_t = team_people.get(tid, set())
        pm_list = team_pms.get(tid, [])
        po_list = team_pos.get(tid, [])

        epic_ids = team_to_epics.get(tid, [])

        epic_models: List[EpicModel] = []
        for eid in epic_ids:
            epic_ids_seen.add(eid)
            em = build_epic(eid, False)
            epic_models.append(em)

        teams.append(
            TeamModel(
                id=tid,
                name=tname,
                pm_list=pm_list,
                po_list=po_list,
                people_team=people_t,
                epics=epic_models,
                mission_summary="",
                next_increment_summary="",
                summary_ai_used=False,
                summary_warning="",
            )
        )

    # Any epic referenced in features for this PI but not linked to a team -> separate epic
    for eid in features_by_epic.keys():
        if eid not in epic_ids_seen:
            separate_epics.append(build_epic(eid, True))

    # Deduplicate separate epics by id (keep first occurrence/order).
    dedup_separate: List[EpicModel] = []
    seen_sep: Set[int] = set()
    for e in separate_epics:
        if e.id in seen_sep:
            continue
        seen_sep.add(e.id)
        dedup_separate.append(e)
    separate_epics = dedup_separate

    # Stats
    stats = {
        "teams": len(teams),
        "epics_total": len({e.id for t in teams for e in t.epics} | {e.id for e in separate_epics}),
        "epics_separate": len({e.id for e in separate_epics}),
        "features_pi": int(len(features_pi)) if not features.empty else 0,
        "affectations": int(len(affectations)),
        "personnes": int(len(personnes)),
    }

    return BuiltModel(pi=pi, teams=teams, separate_epics=separate_epics, stats=stats)
