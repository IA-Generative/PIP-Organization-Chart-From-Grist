from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .model_builder import BuiltModel, EpicModel, TeamModel


@dataclass
class Box:
    x: int
    y: int
    w: int
    h: int


@dataclass
class Layout:
    cartouche: Box
    high_fragmentation_box: Optional[Box]
    unassigned_people_box: Optional[Box]
    team_boxes: Dict[int, Box]
    team_info_boxes: Dict[int, Box]
    epic_boxes: Dict[Tuple[int, int], Box]
    separate_epic_boxes: Dict[int, Box]


def _wrapped_lines(lines: List[str], max_chars: int) -> int:
    total = 0
    for line in lines:
        text = line or " "
        total += max(1, int(math.ceil(len(text) / max_chars)))
    return total


def _alert_box_height(title: str, items: List[str], max_chars: int = 64) -> int:
    lines = [title]
    if items:
        lines.extend([f"- {x}" for x in items])
    else:
        lines.append("- aucun")
    wrapped = _wrapped_lines(lines, max_chars=max_chars)
    return max(72, wrapped * 15 + 20)


def _sorted_members(members: set[str]) -> List[str]:
    return sorted([m for m in members if m and m != "UNKNOWN"])


def _epic_height(epic: EpicModel, team: TeamModel | None = None, max_chars: int = 52) -> int:
    lines: List[str] = [epic.name]
    if team is not None:
        lines.append(f"Equipe : {team.name}")
        lines.append(f"PO equipe : {', '.join(team.po_list) if team.po_list else '—'}")
        team_members = _sorted_members(team.people_team)
        members_text = ", ".join(team_members) if team_members else "—"
        lines.append(f"Membres equipe : {members_text}")
    lines.append(f"PO epic : {', '.join(epic.po_list) if epic.po_list else '—'}")
    lines.append("—")

    if epic.assignments:
        for a in epic.assignments:
            lines.append(f"{a.person} - {a.role} - {int(round(a.charge))}%")
    else:
        lines.append("(aucune affectation specifique)")

    if epic.features:
        lines.append("")
        lines.append("Features (PI) :")
        for f in epic.features:
            lines.append(f"- {f}")

    wrapped = _wrapped_lines(lines, max_chars=max_chars)
    return 28 + wrapped * 16 + 24


def _team_info_height(team: TeamModel) -> int:
    members = _sorted_members(team.people_team)
    lines = [
        f"PM : {', '.join(team.pm_list) if team.pm_list else '—'}",
        f"PO : {', '.join(team.po_list) if team.po_list else '—'}",
        "Membres :",
    ]
    lines.extend([f"- {m}" for m in members] if members else ["- aucun membre détecté"])
    wrapped = _wrapped_lines(lines, max_chars=58)
    return max(96, wrapped * 15 + 20)


def compute_layout(
    model: BuiltModel,
    high_fragmented_people: Optional[List[str]] = None,
    unassigned_people: Optional[List[str]] = None,
) -> Layout:
    margin = 20
    cartouche_h = 50
    team_w = 460
    team_header_h = 52
    epic_w = team_w - 30
    col_gap = 30
    row_gap = 20

    full_w = 3 * team_w + 2 * col_gap
    cartouche = Box(x=margin, y=margin, w=full_w, h=cartouche_h)
    high_fragmentation_box: Optional[Box] = None
    unassigned_people_box: Optional[Box] = None

    team_boxes: Dict[int, Box] = {}
    team_info_boxes: Dict[int, Box] = {}
    epic_boxes: Dict[Tuple[int, int], Box] = {}
    separate_epic_boxes: Dict[int, Box] = {}

    x = margin
    y0 = margin + cartouche_h + 20

    hfp = high_fragmented_people or []
    unassigned = unassigned_people or []
    if hfp or unassigned:
        alert_gap = 20
        half_w = (full_w - alert_gap) // 2
        left_h = _alert_box_height("Affecté sur plusieurs EPICS", hfp)
        right_h = _alert_box_height("Sans affectation ou total < 25%", unassigned)
        alert_h = max(left_h, right_h)
        high_fragmentation_box = Box(x=margin, y=y0, w=half_w, h=alert_h)
        unassigned_people_box = Box(x=margin + half_w + alert_gap, y=y0, w=half_w, h=alert_h)
        y0 += alert_h + 20

    # Teams in columns, wrap every 3 columns.
    col = 0
    row_max_h = 0
    for team in model.teams:
        tx = x + col * (team_w + col_gap)
        ty = y0
        info_h = _team_info_height(team)
        # compute team height by summing epics
        epics_h = 0
        for e in team.epics:
            epics_h += _epic_height(e, team=team) + row_gap
        team_h = team_header_h + info_h + max(120, epics_h + 20)

        team_boxes[team.id] = Box(tx, ty, team_w, team_h)
        team_info_boxes[team.id] = Box(tx + 15, ty + team_header_h + 10, epic_w, info_h)

        # place epics inside
        ey = ty + team_header_h + 10 + info_h + 12
        for e in team.epics:
            eh = _epic_height(e, team=team)
            epic_boxes[(team.id, e.id)] = Box(tx + 15, ey, epic_w, eh)
            ey += eh + row_gap

        row_max_h = max(row_max_h, team_h)
        col += 1
        if col >= 3:
            col = 0
            y0 += row_max_h + 40
            row_max_h = 0

    # If last row is incomplete, move y0 below the tallest box of that row.
    if col != 0:
        y0 += row_max_h + 40

    # Separate epics area below all teams
    sep_x = margin
    sep_y = y0 + 40
    for e in model.separate_epics:
        eh = _epic_height(e) + 10
        separate_epic_boxes[e.id] = Box(sep_x, sep_y, team_w, eh)
        sep_y += eh + 15

    return Layout(
        cartouche=cartouche,
        high_fragmentation_box=high_fragmentation_box,
        unassigned_people_box=unassigned_people_box,
        team_boxes=team_boxes,
        team_info_boxes=team_info_boxes,
        epic_boxes=epic_boxes,
        separate_epic_boxes=separate_epic_boxes,
    )
